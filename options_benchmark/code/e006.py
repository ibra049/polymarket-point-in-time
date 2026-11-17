"""E-006: Polymarket daily BTC "above X" vs the Deribit smile-consistent digital.

Implements research/experiments/E-006.yaml (v1.2 draft; disposition R-025). Stdlib only,
deterministic. Pipeline checks use only Deribit inputs. Everything that touches
Polymarket prices runs once, in `analyze`, after collection ends.

v1.2 (CP1 findings 1-5): frozen sample boundary and run manifest, operative
synthetic-flat gate, mark check in F units on the used expiries, executed-leg
($100 purchase cash) sizing with per-market fee metadata, moneyness coverage,
nearest-strike flat comparator and a fixed output contract.

v1.2 CP2 corrections (Codex CP1-CP2-2026-11-06, disposition R-026): consumed
nested inputs are validated before any math (explicit incomplete/invalid
drops); the production run requires a full data_commit, binds the snapshot
inventory to that committed data tree, and only admits snapshots whose
recorded collector sha256 equals the pinned collector hash.
"""
from bisect import bisect_left
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
import gzip
import hashlib
import json
import math
from pathlib import Path
import random
import re
from statistics import median
import subprocess

YEAR = 365.0 * 86400
NOTIONAL = 100.0          # purchase cash (USDC) of the executed leg
COVER = 2000.0
H = 50.0
TAIL = 0.10
GAP = 0.01
MIN_SNAPS = 3
MIN_MARKETS, MIN_EVENTS = 30, 8
HORIZON = (6 * 3600, 96 * 3600)
STALE = 0.0015
SOURCE_WINDOW_S = 120
FLAT_TOL = 0.001          # 0.1 pp
MARK_TOL, MARK_FLOOR = 0.02, 0.0005
PIPE_FAIL_MAX = 0.05
FEE_DP = 5                # Polymarket rounds fees to 5 decimals (USDC)
FEE_RATE_MAX = 0.25
SEED = 20261102
BOOT = 10000
SCHEMA = 'e006-snapshot-v3'   # v3 (CP2 #2): records collector_sha256
WINDOW_END = '2026-11-17T00:00:00+00:00'   # exclusive: last sample hour 2026-11-16T23
EXCLUDED = ({'file': '20261102T2214Z.json.gz', 'started_minute': '2026-11-02T22:14',
             'why': 'step-1 pipeline snapshot, viewed by Claude before freeze'},)
PINNED = ('research/experiments/E-006.yaml', 'src/analysis/e006.py',
          'scripts/e006_snapshot.py', '../.github/workflows/e006-collect.yml')
COLLECTOR = 'scripts/e006_snapshot.py'
FULL_SHA = re.compile(r'[0-9a-f]{40}')
MONTHS = {m: i + 1 for i, m in enumerate(
    'JAN FEB MAR APR MAY JUN JUL AUG SEP OCT NOV DEC'.split())}
OUTPUT_KEYS = frozenset({
    'status', 'status_reason', 'S', 'ci95', 'markets', 'events', 'manifest',
    'snapshots', 'pipeline', 'drops', 'flat_benchmark', 'non_tail', 'cheap_side',
    'basis_r', 'capacity_median_depth_usdc', 'return_per_dollar', 'fee_rates',
    'sizing'})


def ncdf(x):
    return 0.5 * math.erfc(-x / math.sqrt(2))


def ts(s):
    return datetime.fromisoformat(s.replace('Z', '+00:00')).timestamp()


def black76_call(F, K, w):
    """Undiscounted Black-76 call with total variance w = sigma^2 * tau."""
    if w <= 0:
        return max(F - K, 0.0)
    sw = math.sqrt(w)
    d1 = (math.log(F / K) + w / 2) / sw
    return F * ncdf(d1) - K * ncdf(d1 - sw)


def bs_digital(F, K, w):
    sw = math.sqrt(w)
    return ncdf((math.log(F / K) - w / 2) / sw)


def parse_instrument(name):
    """BTC-3NOV26-70000-C -> (expiry_ts, strike, 'C'|'P')."""
    _, code, strike, cp = name.split('-')
    day, mon, yr = int(code[:-5]), MONTHS[code[-5:-2]], 2000 + int(code[-2:])
    exp = datetime(yr, mon, day, 8, tzinfo=timezone.utc).timestamp()
    return exp, float(strike), cp


class Expiry:
    """One Deribit expiry's smile in total variance, linear in log-moneyness."""

    def __init__(self, exp, tau, F, strikes, ivs):
        self.exp, self.tau, self.F = exp, tau, F
        pairs = sorted(zip(strikes, ivs))
        self.K = [k for k, _ in pairs]
        self.k = [math.log(k / F) for k in self.K]
        self.w = [(iv / 100.0) ** 2 * tau for _, iv in pairs]

    def covers(self, K):
        """Listed strikes in [K-2000, K) and (K, K+2000] (E-006 coverage_rule).

        K is the moneyness-equivalent strike on this expiry (Surface.covered)."""
        below = [x for x in self.K if K - COVER <= x < K]
        above = [x for x in self.K if K < x <= K + COVER]
        return bool(below) and bool(above) and self.K[0] <= K - H and K + H <= self.K[-1]

    def w_at(self, k):
        if not self.k[0] <= k <= self.k[-1]:
            raise ValueError('outside listed strikes (no extrapolation)')
        i = bisect_left(self.k, k)
        if self.k[i] == k:
            return self.w[i]
        k0, k1, w0, w1 = self.k[i - 1], self.k[i], self.w[i - 1], self.w[i]
        return w0 + (w1 - w0) * (k - k0) / (k1 - k0)

    def w_nearest(self, k):
        """Total variance at the single listed strike nearest in k (ties: lower)."""
        j = min(range(len(self.k)), key=lambda i: (abs(self.k[i] - k), i))
        return self.w[j]


def build_expiries(options, now):
    """Group usable options (mark_iv > 0) by expiry, one IV per strike (calls first)."""
    by = {}
    for o in options:
        exp, K, cp = parse_instrument(o['instrument_name'])
        if exp <= now or not o.get('mark_iv') or o['mark_iv'] <= 0:
            continue
        d = by.setdefault(exp, {'F': o['underlying_price'], 'iv': {}})
        if cp == 'C' or K not in d['iv']:
            d['iv'][K] = o['mark_iv']
    out = {}
    for exp, d in by.items():
        if len(d['iv']) >= 3:
            out[exp] = Expiry(exp, (exp - now) / YEAR, d['F'], list(d['iv']), list(d['iv'].values()))
    return out


def bracket(expiries, T, now):
    """T1 = latest expiry <= T and >= now + 1h; T2 = earliest expiry >= T."""
    lo = [e for e in expiries if now + 3600 <= e <= T]
    hi = [e for e in expiries if e >= T]
    if not lo or not hi:
        return None
    return expiries[max(lo)], expiries[min(hi)]


class Surface:
    def __init__(self, e1, e2, T, now):
        self.e1, self.e2 = e1, e2
        self.tau = (T - now) / YEAR
        span = e2.exp - e1.exp
        self.a = 0.0 if span == 0 else (T - e1.exp) / span
        self.F = e1.F + self.a * (e2.F - e1.F)

    def covered(self, K):
        """Coverage at the moneyness-equivalent strike F_i * K / F on each expiry."""
        k = math.log(K / self.F)
        return all(e.covers(e.F * math.exp(k)) for e in (self.e1, self.e2))

    def _interp(self, w1, w2):
        if self.e1 is self.e2:
            return w1 * self.tau / self.e1.tau
        return w1 + self.a * (w2 - w1)

    def w(self, K):
        k = math.log(K / self.F)
        return self._interp(self.e1.w_at(k), self.e2.w_at(k))

    def digital(self, K):
        return -(black76_call(self.F, K + H, self.w(K + H))
                 - black76_call(self.F, K - H, self.w(K - H))) / (2 * H)

    def flat_digital(self, K):
        """Secondary comparator: N(d2) at the single nearest listed strike's IV
        on each bracketing expiry (Portnaya-style flat vol), same time rule."""
        k = math.log(K / self.F)
        return bs_digital(self.F, K, self._interp(self.e1.w_nearest(k), self.e2.w_nearest(k)))


def check_mark_reproduction(options, now, expiries=None, tol=MARK_TOL, floor=MARK_FLOOR):
    """Known-number check: Black-76 with mark_iv reproduces Deribit mark_price.

    Units: mark_price is in BTC and equals the Black-76 USD value on the
    option's own underlying_price F divided by that same F (Deribit inverse
    option convention). The btc_usd index is NOT used here. `expiries`
    restricts the population to the expiries the study used (CP1 #2)."""
    bad = n = 0
    for o in options:
        if not o.get('mark_iv') or (o.get('mark_price') or 0) < floor:
            continue
        exp, K, cp = parse_instrument(o['instrument_name'])
        if exp <= now or (expiries is not None and exp not in expiries):
            continue
        F, w = o['underlying_price'], (o['mark_iv'] / 100) ** 2 * (exp - now) / YEAR
        c = black76_call(F, K, w)
        model = c if cp == 'C' else c - (F - K)
        n += 1
        bad += abs(model / F - o['mark_price']) > tol * o['mark_price']
    return n, bad


# ---------------------------------------------------------------- fees, fills

def fee_params(m):
    """(rate, None) from the market's recorded Gamma fee metadata, or (None, drop).

    Fails closed: missing or unsupported metadata never defaults to 0.07."""
    enabled = m.get('fees_enabled')
    if enabled is False:
        return 0.0, None
    if enabled is not True:
        return None, 'fee_metadata_missing'
    sched = m.get('fee_schedule')
    if not isinstance(sched, dict) or sched.get('rate') is None or sched.get('exponent') is None:
        return None, 'fee_metadata_missing'
    try:
        rate, expo = float(sched['rate']), float(sched['exponent'])
    except (TypeError, ValueError):
        return None, 'fee_unsupported'
    if expo != 1 or not 0 <= rate <= FEE_RATE_MAX:
        return None, 'fee_unsupported'
    return rate, None


def fill_fee(q, p, rate):
    """Taker fee in USDC for q shares filled at p, rounded to 5 dp (official docs)."""
    return float(Decimal(repr(q * rate * p * (1 - p))).quantize(
        Decimal(1).scaleb(-FEE_DP), rounding=ROUND_HALF_UP))


def yes_asks(book):
    return sorted((float(l['price']), float(l['size'])) for l in book.get('asks') or [])


def no_asks_via_yes_bids(book):
    """Buying NO matches resting YES bids (CTF mint): NO price 1 - bid."""
    return sorted((1 - float(l['price']), float(l['size'])) for l in book.get('bids') or [])


def buy(levels, rate, cash=NOTIONAL):
    """Taker BUY walking ascending ask levels until `cash` USDC is spent.

    Returns {'shares', 'cash', 'vwap', 'fee'} or None if the book is too thin."""
    spent = shares = fees = 0.0
    for p, q in levels:
        if p <= 0 or p >= 1 or q <= 0:
            continue
        take = min(q, (cash - spent) / p)
        spent += p * take
        shares += take
        fees += fill_fee(take, p, rate)
        if spent >= cash - 1e-9:
            break
    if spent < cash - 1e-9 or shares == 0:
        return None
    return {'shares': shares, 'cash': spent, 'vwap': spent / shares, 'fee': fees}


def sell_longshot(book, prob_yes, rate):
    """Primary: sell the longshot side = taker BUY of the favourite token, $100 cash.

    Longshot YES (D < 0.5): buy NO against YES bids. Longshot NO: buy YES asks.
    The fee is charged on the executed (favourite) fill price. Returns a dict
    with the per-share longshot net gap, or None if the book is too thin."""
    prob = prob_yes if prob_yes < 0.5 else 1 - prob_yes
    levels = no_asks_via_yes_bids(book) if prob_yes < 0.5 else yes_asks(book)
    f = buy(levels, rate)
    if f is None:
        return None
    sale = 1 - f['vwap']
    fee_ps = f['fee'] / f['shares']
    net = sale - prob - fee_ps
    depth = sum(p * q for p, q in levels
                if 0 < p < 1 and (1 - p) - prob - rate * p * (1 - p) > GAP)
    return {'net': net, 'sale_price': sale, 'prob': prob, 'fee_per_share': fee_ps,
            'fav_vwap': f['vwap'], 'shares': f['shares'], 'cash': f['cash'],
            'fee_usdc': f['fee'], 'longshot_proceeds': sale * f['shares'],
            'return_per_dollar': net * f['shares'] / f['cash'], 'depth_usdc': depth}


def buy_longshot(book, prob_yes, rate):
    """Secondary (cheap side): taker BUY of the longshot token, $100 cash."""
    prob = prob_yes if prob_yes < 0.5 else 1 - prob_yes
    levels = yes_asks(book) if prob_yes < 0.5 else no_asks_via_yes_bids(book)
    f = buy(levels, rate)
    if f is None:
        return None
    return {'net': prob - f['vwap'] - f['fee'] / f['shares'], 'vwap': f['vwap']}


def strike_of(label):
    return float(str(label).replace(',', '').replace('$', ''))


# ------------------------------------------------------- snapshots and checks

REQUIRED = ('started_at', 'finished_at', 'errors', 'binance_before', 'binance_after',
            'deribit_index', 'deribit_options', 'polymarket', 'collector_sha256')


def _finite(x):
    """A real, finite JSON number (bools and numeric strings are not numbers)."""
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def _when(s):
    """Timezone-aware ISO timestamp -> epoch seconds; ValueError otherwise."""
    if not isinstance(s, str):
        raise ValueError('timestamp is not a string')
    d = datetime.fromisoformat(s.replace('Z', '+00:00'))
    if d.tzinfo is None:
        raise ValueError('timestamp has no timezone')
    return d.timestamp()


def option_validity(o):
    """None, or why one Deribit option row cannot be consumed (CP2 #1).

    Every row's instrument_name is parsed (expiry, strike). mark_iv must be
    present: 0 marks the row unusable (skipped by the frozen rule), > 0 makes
    it consumed, and then underlying_price > 0 and mark_price >= 0 are required."""
    if not isinstance(o, dict):
        return 'snapshot_invalid'
    if o.get('instrument_name') is None or o.get('mark_iv') is None:
        return 'snapshot_incomplete'
    try:
        _, K, cp = parse_instrument(o['instrument_name'])
    except (AttributeError, KeyError, ValueError):
        return 'snapshot_invalid'
    if not (K > 0 and math.isfinite(K) and cp in ('C', 'P')):
        return 'snapshot_invalid'
    if not _finite(o['mark_iv']) or o['mark_iv'] < 0:
        return 'snapshot_invalid'
    if o['mark_iv'] == 0:
        return None
    if o.get('underlying_price') is None or o.get('mark_price') is None:
        return 'snapshot_incomplete'
    if not (_finite(o['underlying_price']) and o['underlying_price'] > 0
            and _finite(o['mark_price']) and o['mark_price'] >= 0):
        return 'snapshot_invalid'
    return None


def validity(snap):
    """None if the snapshot is usable, else the drop reason.

    snapshot_incomplete: wrong schema, or a required field (top level or a
    consumed Deribit option field) missing/null. snapshot_invalid: wrong type,
    unparseable or naive timestamp, non-finite or non-positive price, negative
    or > 120 s duration, or a recorded source error. Checked before any math."""
    if not isinstance(snap, dict) or snap.get('schema') != SCHEMA or any(
            snap.get(k) is None for k in REQUIRED):
        return 'snapshot_incomplete'
    try:
        now, end = _when(snap['started_at']), _when(snap['finished_at'])
    except ValueError:
        return 'snapshot_invalid'
    if not all(isinstance(snap[k], list) for k in ('errors', 'deribit_options', 'polymarket')):
        return 'snapshot_invalid'
    if not isinstance(snap['collector_sha256'], str):
        return 'snapshot_invalid'
    if not all(_finite(snap[k]) and snap[k] > 0
               for k in ('binance_before', 'binance_after', 'deribit_index')):
        return 'snapshot_invalid'
    whys = {option_validity(o) for o in snap['deribit_options']} - {None}
    if whys:
        return 'snapshot_incomplete' if 'snapshot_incomplete' in whys else 'snapshot_invalid'
    if snap['errors'] or not 0 <= end - now <= SOURCE_WINDOW_S:
        return 'snapshot_invalid'
    if abs(snap['binance_after'] / snap['binance_before'] - 1) > STALE:
        return 'snapshot_stale'
    return None


def _level_validity(levels):
    if levels is None:
        return 'market_incomplete'
    if not isinstance(levels, list):
        return 'market_invalid'
    for lv in levels:
        if not isinstance(lv, dict):
            return 'market_invalid'
        if lv.get('price') is None or lv.get('size') is None:
            return 'market_incomplete'
        try:
            p, q = (float(lv[k]) if isinstance(lv[k], str) else lv[k] for k in ('price', 'size'))
        except ValueError:
            return 'market_invalid'
        if not (_finite(p) and _finite(q) and 0 <= p <= 1 and q >= 0):
            return 'market_invalid'
    return None


def market_validity(m):
    """None, or why one Polymarket market row cannot be consumed (CP2 #1).

    Per-market drops (market_incomplete / market_invalid) so one bad row does
    not discard the other markets. A null book (recorded source error) stays
    allowed here: the snapshot already fails validity on its error entry. Fee
    metadata keeps its own fail-closed drops in fee_params."""
    if not isinstance(m, dict):
        return 'market_invalid'
    if any(m.get(k) is None for k in ('event_slug', 'market_id', 'strike_label', 'end_date')) \
            or 'book' not in m:
        return 'market_incomplete'
    if not isinstance(m['event_slug'], str) or not isinstance(m['market_id'], str):
        return 'market_invalid'
    try:
        _when(m['end_date'])
        K = strike_of(m['strike_label'])
    except ValueError:
        return 'market_invalid'
    if not (math.isfinite(K) and K > 0):
        return 'market_invalid'
    book = m['book']
    if book is None:
        return None
    if not isinstance(book, dict):
        return 'market_invalid'
    for side in ('bids', 'asks'):
        why = _level_validity(book.get(side))
        if why:
            return why
    return None


def _markets(snap, expiries, now, r, drop=None):
    """Yield (market, T, surface, K*) for markets passing horizon, bracket, coverage."""
    for m in snap['polymarket']:
        why = market_validity(m)
        if why:
            drop and drop(why)
            continue
        T = ts(m['end_date'])
        if not HORIZON[0] <= T - now <= HORIZON[1]:
            drop and drop('horizon')
            continue
        br = bracket(expiries, T, now)
        if br is None:
            drop and drop('no_bracket')
            continue
        surf = Surface(br[0], br[1], T, now)
        K = strike_of(m['strike_label']) / r
        yield m, surf, K


def observations(snap):
    """Per-snapshot rows for every (market, snapshot) plus counted drops."""
    drops = {}

    def drop(k):
        drops[k] = drops.get(k, 0) + 1
    why = validity(snap)
    if why:
        drop(why)
        return [], drops
    now = ts(snap['started_at'])
    r = snap['binance_before'] / snap['deribit_index']
    expiries = build_expiries(snap['deribit_options'], now)
    rows = []
    for m, surf, K in _markets(snap, expiries, now, r, drop):
        if not surf.covered(K):
            drop('coverage')
            continue
        try:
            D, D_flat = surf.digital(K), surf.flat_digital(K)
        except ValueError:
            drop('coverage')
            continue
        rate, fee_drop = fee_params(m)
        if fee_drop:
            drop(fee_drop)
            continue
        book = m.get('book')
        sale = sell_longshot(book, D, rate) if book else None
        sale_flat = sell_longshot(book, D_flat, rate) if book else None
        cheap = buy_longshot(book, D, rate) if book else None
        if sale is None:
            drop('untradable')
        rows.append({'event': m['event_slug'], 'market': m['market_id'], 'K': K,
                     'D': D, 'D_flat': D_flat, 'tail': min(D, 1 - D) < TAIL,
                     'tail_flat': min(D_flat, 1 - D_flat) < TAIL, 'sale': sale,
                     'sale_flat': sale_flat, 'cheap': cheap, 'rate': rate, 'r': r,
                     'snap': snap['started_at']})
    return rows, drops


def pipeline_check(snap):
    """INVALID-RUN inputs for one valid snapshot, from Deribit data only.

    Population (CP1 #2): options on the expiries used as T1/T2 by at least one
    market that passes the horizon filter. A snapshot with no used expiry has
    no observations and is 'na' (not in the failure denominator)."""
    now = ts(snap['started_at'])
    expiries = build_expiries(snap['deribit_options'], now)
    r = snap['binance_before'] / snap['deribit_index']
    used, by_event = set(), {}
    for m, surf, K in _markets(snap, expiries, now, r):
        used.update((surf.e1.exp, surf.e2.exp))
        if surf.covered(K):
            try:
                by_event.setdefault(m['event_slug'], []).append((K, surf.digital(K)))
            except ValueError:
                pass
    n, bad = check_mark_reproduction(snap['deribit_options'], now, used)
    mono_fail = range_fail = 0
    for pts in by_event.values():
        pts.sort()
        range_fail += sum(not -1e-6 <= d <= 1 + 1e-6 for _, d in pts)
        mono_fail += sum(b[1] > a[1] + 1e-6 for a, b in zip(pts, pts[1:]))
    na = not used
    return {'mark_checked': n, 'mark_bad': bad, 'mono_fail': mono_fail,
            'range_fail': range_fail, 'events': len(by_event), 'na': na,
            'ok': na or (n > 0 and bad == 0 and mono_fail == 0 and range_fail == 0)}


def synthetic_flat_check(F=70000.0, iv=50.0, days=1.5):
    tau = days * 86400 / YEAR
    strikes = [F - 10000 + 500 * i for i in range(41)]
    e = Expiry(0, tau, F, strikes, [iv] * len(strikes))
    s = Surface(e, e, tau * YEAR, 0)
    worst = max(abs(s.digital(K) - bs_digital(F, K, (iv / 100) ** 2 * tau))
                for K in strikes[2:-2])
    return worst


# ------------------------------------------------- sample boundary, manifest

def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def stamp_ts(name):
    """'20261103T0007Z.json.gz' -> epoch seconds (window test for unreadable files)."""
    return datetime.strptime(name[:13], '%Y%m%dT%H%M').replace(tzinfo=timezone.utc).timestamp()


def scheduled_hours(freeze_ts, end, minute=7):
    """Hourly cron runs (':07') strictly after the freeze and before the end."""
    h = math.floor(freeze_ts / 3600)
    n = 0
    while h * 3600 + minute * 60 < end:
        n += h * 3600 + minute * 60 > freeze_ts
        h += 1
    return n


def check_manifest(manifest, repo_root=None, synthetic=False):
    """Refuse to run on an unfrozen or mismatched manifest (CP1 #1, CP2 #2).

    Production (synthetic=False) also needs repo_root (pinned hashes are
    verified) and a full 40-hex data_commit. synthetic=True is for offline
    tests only; its output is marked synthetic."""
    if manifest.get('freeze_ts') in (None, '') or manifest.get('freeze_commit') in (None, ''):
        raise ValueError('manifest not frozen: freeze_ts/freeze_commit missing')
    if ts(manifest['window_end_exclusive']) != ts(WINDOW_END):
        raise ValueError('manifest window_end differs from frozen code')
    if sorted(e['file'] for e in manifest.get('excluded_snapshots', [])) != sorted(
            e['file'] for e in EXCLUDED):
        raise ValueError('manifest exclusions differ from frozen code')
    if repo_root is not None:
        for rel in PINNED:
            want = manifest.get('sha256', {}).get(rel)
            if not want or sha256(Path(repo_root) / rel) != want:
                raise ValueError(f'hash mismatch or missing: {rel}')
    if synthetic:
        return
    if repo_root is None:
        raise ValueError('production run needs repo_root (pinned hashes unverified)')
    if not isinstance(manifest.get('data_commit'), str) or not FULL_SHA.fullmatch(
            manifest['data_commit']):
        raise ValueError('manifest data_commit missing or not a full 40-hex commit')


def git_blob_sha(path):
    """The git blob id of a file's bytes (what `git hash-object` prints)."""
    data = Path(path).read_bytes()
    return hashlib.sha1(b'blob %d\0' % len(data) + data).hexdigest()


def committed_snapshots(data_repo, commit):
    """{file name: blob id} of snapshots/*.json.gz in `commit` of the data repo."""
    git = ['git', '-C', str(data_repo)]
    kind = subprocess.run(git + ['cat-file', '-t', commit], capture_output=True, text=True)
    if kind.returncode or kind.stdout.strip() != 'commit':
        raise ValueError(f'data_commit {commit} is not a commit in {data_repo}')
    out = subprocess.run(git + ['ls-tree', '-r', '-z', commit, '--', 'snapshots/'],
                         capture_output=True, text=True, check=True).stdout
    tree = {}
    for entry in filter(None, out.split('\0')):
        meta, path = entry.split('\t', 1)
        if meta.split()[1] == 'blob' and path.endswith('.json.gz'):
            tree[Path(path).name] = meta.split()[2]
    return tree


def verify_data(paths, data_commit, data_repo):
    """Bind the supplied snapshot inventory to the committed data tree (CP2 #2).

    Exact name set and git blob ids must equal snapshots/*.json.gz at
    data_commit. Runs on raw bytes, before any snapshot is parsed."""
    tree = committed_snapshots(data_repo, data_commit)
    names = [Path(x).name for x in paths]
    if not tree or len(set(names)) != len(names) or set(names) != set(tree):
        raise ValueError('snapshot inventory differs from the data_commit tree')
    for x in paths:
        if git_blob_sha(x) != tree[Path(x).name]:
            raise ValueError(f'snapshot bytes differ from data_commit: {Path(x).name}')


def select(paths, freeze_ts, collector_sha=None):
    """Apply the frozen sample boundary. Returns (snapshots, per-file ledger).

    Order: unreadable, excluded identity, pre-freeze, post-window, collector
    mismatch (recorded collector_sha256 != pinned collector hash; CP2 #2),
    duplicate UTC hour (earliest started_at kept). Supplying a file by hand
    cannot get an excluded or out-of-window record into the sample."""
    end = ts(WINDOW_END)
    ex_files = {e['file'] for e in EXCLUDED}
    ex_minutes = {e['started_minute'] for e in EXCLUDED}
    ledger, keep = [], {}
    for p in sorted(Path(x) for x in paths):
        rec = {'file': p.name, 'sha256': sha256(p)}
        ledger.append(rec)
        try:
            with gzip.open(p, 'rt') as f:
                snap = json.load(f)
            t = _when(snap['started_at'])
        except Exception:
            try:
                t = stamp_ts(p.name)
            except ValueError:
                t = None
            in_window = t is not None and freeze_ts < t < end
            rec['disposition'] = 'unreadable' if in_window else 'unreadable_out_of_window'
            continue
        rec['started_at'] = snap['started_at']
        minute = datetime.fromtimestamp(t, timezone.utc).strftime('%Y-%m-%dT%H:%M')
        if p.name in ex_files or minute in ex_minutes:
            rec['disposition'] = 'excluded_pipeline'
        elif t <= freeze_ts:
            rec['disposition'] = 'pre_freeze'
        elif t >= end:
            rec['disposition'] = 'post_window'
        elif collector_sha is not None and snap.get('collector_sha256') != collector_sha:
            rec['disposition'] = 'collector_mismatch'
        else:
            hour = minute[:13]
            prev = keep.get(hour)
            if prev is None or t < prev[0]:
                if prev is not None:
                    prev[2]['disposition'] = 'duplicate_hour'
                keep[hour] = (t, snap, rec)
                rec['disposition'] = 'in_sample'
            else:
                rec['disposition'] = 'duplicate_hour'
    return [s for _, s, _ in sorted(keep.values(), key=lambda x: x[0])], ledger


# ------------------------------------------------------------------- analysis

def share_stat(per_market, key=lambda v: v):
    """S, bootstrap CI over event dates, market and event counts.

    per_market: {(event, market): [values]}; a market enters with >= 3 values."""
    stats = {k: median(key(x) for x in v) for k, v in per_market.items() if len(v) >= MIN_SNAPS}
    events = sorted({k[0] for k in stats})
    S = sum(g > GAP for g in stats.values()) / len(stats) if stats else None
    rng = random.Random(SEED)
    by_event = {e: [g for k, g in stats.items() if k[0] == e] for e in events}
    boots = []
    for _ in range(BOOT if events else 0):
        sample = [g for e in (rng.choice(events) for _ in events) for g in by_event[e]]
        boots.append(sum(g > GAP for g in sample) / len(sample))
    boots.sort()
    ci = (boots[int(BOOT * 0.025) - 1], boots[int(BOOT * 0.975) - 1]) if boots else (None, None)
    return {'S': S, 'ci95': ci, 'markets': len(stats), 'events': len(events),
            'medians': stats}


def quantiles(xs):
    if not xs:
        return None
    xs = sorted(xs)
    q = lambda f: xs[min(len(xs) - 1, int(f * (len(xs) - 1) + 0.5))]
    return {'n': len(xs), 'min': xs[0], 'p05': q(.05), 'p25': q(.25), 'median': q(.5),
            'p75': q(.75), 'p95': q(.95), 'max': xs[-1]}


def decide(flat_err, fail_share, prim):
    if flat_err > FLAT_TOL:
        return 'INVALID-RUN', f'synthetic flat error {flat_err:.2e} > {FLAT_TOL}'
    if fail_share is not None and fail_share > PIPE_FAIL_MAX:
        return 'INVALID-RUN', f'pipeline fail share {fail_share:.3f} > {PIPE_FAIL_MAX}'
    if prim['markets'] < MIN_MARKETS or prim['events'] < MIN_EVENTS:
        return 'DATA-BLOCKED', f"{prim['markets']} markets / {prim['events']} event dates"
    if prim['S'] < 0.10:
        return 'REJECT', 'S < 0.10'
    if prim['ci95'][0] < 0.05:
        return 'INCONCLUSIVE', 'S >= 0.10 and CI lower bound < 0.05'
    return 'PROMOTE', 'S >= 0.10 and CI lower bound >= 0.05 (design a paper test; not alpha)'


def analyze(paths, manifest, repo_root=None, data_repo=None, synthetic=False):
    """Run once after collection (protocol stopping_condition). Output keys are
    fixed by OUTPUT_KEYS (frozen output contract, CP1 #4).

    Production (default): manifest frozen, pinned hashes verified at
    repo_root, inventory bound to data_commit in data_repo, and snapshots
    filtered on the pinned collector hash, all before any snapshot is parsed.
    synthetic=True skips the git binding (offline tests only)."""
    check_manifest(manifest, repo_root, synthetic)
    if not synthetic:
        if data_repo is None:
            raise ValueError('production run needs data_repo for data_commit binding')
        verify_data(paths, manifest['data_commit'], data_repo)
    freeze_ts = ts(manifest['freeze_ts'])
    collector_sha = (manifest.get('sha256') or {}).get(COLLECTOR)
    snaps, ledger = select(paths, freeze_ts, collector_sha)
    flat_err = synthetic_flat_check()
    drops, valid = {}, []
    prim, flat, nontail, cheap, rows_all = {}, {}, {}, {}, []
    for s in snaps:
        rows, d = observations(s)
        for k, v in d.items():
            drops[k] = drops.get(k, 0) + v
        if validity(s) is None:
            valid.append(s)
        rows_all.extend(rows)
        for row in rows:
            key = (row['event'], row['market'])
            if row['sale'] and row['tail']:
                prim.setdefault(key, []).append(row['sale'])
            if row['sale'] and not row['tail']:
                nontail.setdefault(key, []).append(row['sale'])
            if row['sale_flat'] and row['tail_flat']:
                flat.setdefault(key, []).append(row['sale_flat'])
            if row['cheap'] and row['tail']:
                cheap.setdefault(key, []).append(row['cheap'])
    checks = [pipeline_check(s) for s in valid]
    counted = [c for c in checks if not c['na']]
    fail_share = sum(not c['ok'] for c in counted) / len(counted) if counted else None
    net = lambda x: x['net']
    P = share_stat(prim, net)
    status, reason = decide(flat_err, fail_share, P)
    entered = {k: v for k, v in prim.items() if len(v) >= MIN_SNAPS}
    disp = {}
    for rec in ledger:
        disp[rec['disposition']] = disp.get(rec['disposition'], 0) + 1
    end = ts(WINDOW_END)
    out = {
        'status': status, 'status_reason': reason,
        'S': P['S'], 'ci95': P['ci95'], 'markets': P['markets'], 'events': P['events'],
        'manifest': {'freeze_ts': manifest['freeze_ts'],
                     'freeze_commit': manifest['freeze_commit'],
                     'data_commit': manifest.get('data_commit'),
                     'window_end_exclusive': WINDOW_END,
                     'pinned_sha256': manifest.get('sha256'),
                     'hash_verified': repo_root is not None,
                     'data_verified': not synthetic, 'synthetic': synthetic,
                     'collector_sha256': collector_sha, 'files': ledger},
        'snapshots': {'files': len(ledger), 'by_disposition': disp,
                      'in_sample': len(snaps), 'valid': len(valid),
                      'scheduled_hours': scheduled_hours(freeze_ts, end)},
        'pipeline': {'synthetic_flat_error': flat_err, 'fail_share': fail_share,
                     'denominator': len(counted), 'na': len(checks) - len(counted),
                     'failed': sum(not c['ok'] for c in counted),
                     'mark_checked': sum(c['mark_checked'] for c in checks),
                     'mark_bad': sum(c['mark_bad'] for c in checks)},
        'drops': drops,
        'flat_benchmark': {k: v for k, v in share_stat(flat, net).items() if k != 'medians'},
        'non_tail': {k: v for k, v in share_stat(nontail, net).items() if k != 'medians'},
        'cheap_side': {k: v for k, v in share_stat(cheap, net).items() if k != 'medians'},
        'basis_r': quantiles([s['binance_before'] / s['deribit_index'] for s in valid]),
        'capacity_median_depth_usdc': {f'{k[0]}|{k[1]}': median(x['depth_usdc'] for x in v)
                                       for k, v in entered.items()},
        'return_per_dollar': quantiles([median(x['return_per_dollar'] for x in v)
                                        for v in entered.values()]),
        'fee_rates': sorted({row['rate'] for row in rows_all}),
        'sizing': {'executed_leg': 'taker BUY of the favourite token',
                   'purchase_cash_usdc': NOTIONAL,
                   'median_shares': quantiles([x['shares'] for v in entered.values() for x in v]),
                   'median_longshot_proceeds_usdc': quantiles(
                       [x['longshot_proceeds'] for v in entered.values() for x in v]),
                   'median_fee_usdc': quantiles([x['fee_usdc'] for v in entered.values() for x in v]),
                   'statistic': 'per-share pricing gap, equal weight per market; not a portfolio return'},
    }
    assert set(out) == OUTPUT_KEYS
    return out


def current_hashes(repo_root):
    return {rel: sha256(Path(repo_root) / rel) for rel in PINNED}


if __name__ == '__main__':
    import sys
    root = Path(__file__).resolve().parents[2]
    if sys.argv[1:] == ['--hash']:
        print(json.dumps(current_hashes(root), indent=2))
        sys.exit(0)
    # python -m src.analysis.e006 <data/e006 checkout> <manifest>
    data_repo = Path(sys.argv[1])
    man = json.loads(Path(sys.argv[2]).read_text())
    print(json.dumps(analyze(sorted((data_repo / 'snapshots').glob('*.json.gz')), man, root,
                             data_repo=data_repo), indent=2, default=str))

#!/usr/bin/env python3
"""E-006 forward collector: one raw snapshot of public data, no analysis.

Writes <out_dir>/<UTC stamp>.json.gz with Binance BTCUSDT (before and after),
the Deribit btc_usd index, Deribit BTC option summaries for expiries up to 15
days out, and Polymarket open bitcoin-above-on-* markets with top-30 books.
Protocol: research/experiments/E-006.yaml. Stdlib only.

Schema v3 (CP2 #2): each snapshot records the sha256 of this file's bytes and
the workflow commit (GITHUB_SHA), so the analysis admits only snapshots made
by the pinned collector even though the workflow checks out the default branch.
"""
from datetime import datetime, timedelta, timezone
import gzip
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import urllib.request

UA = {'User-Agent': 'polysignal-e006/2 (research, read-only)'}
GAMMA = 'https://gamma-api.polymarket.com/events?tag_slug=bitcoin&closed=false&limit=200'
BOOK = 'https://clob.polymarket.com/book?token_id={}'
DERIBIT_OPT = ('https://www.deribit.com/api/v2/public/get_book_summary_by_currency'
               '?currency=BTC&kind=option')
DERIBIT_IDX = 'https://www.deribit.com/api/v2/public/get_index_price?index_name=btc_usd'
BINANCE = 'https://data-api.binance.vision/api/v3/ticker/price?symbol=BTCUSDT'
MONTHS = {m: i + 1 for i, m in enumerate(
    'JAN FEB MAR APR MAY JUN JUL AUG SEP OCT NOV DEC'.split())}
OPT_FIELDS = ('instrument_name', 'mark_iv', 'mark_price', 'underlying_price',
              'bid_price', 'ask_price')
BOOK_LEVELS = 30


def get(url, tries=3):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA),
                                        timeout=20) as r:
                return json.load(r)
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(2 * (i + 1))


def deribit_expiry(name):
    """BTC-3NOV26-70000-C -> expiry datetime (08:00 UTC)."""
    code = name.split('-')[1]
    day, mon, yr = int(code[:-5]), MONTHS[code[-5:-2]], 2000 + int(code[-2:])
    return datetime(yr, mon, day, 8, tzinfo=timezone.utc)


def trim_book(book):
    bids = sorted(book.get('bids', []), key=lambda l: -float(l['price']))[:BOOK_LEVELS]
    asks = sorted(book.get('asks', []), key=lambda l: float(l['price']))[:BOOK_LEVELS]
    return {'bids': bids, 'asks': asks, 'timestamp': book.get('timestamp'),
            'tick_size': book.get('tick_size')}


def snapshot(now=None):
    t0 = time.time()
    now = now or datetime.now(timezone.utc)
    snap = {'schema': 'e006-snapshot-v3', 'started_at': now.isoformat(), 'errors': [],
            'collector_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'code_commit': os.environ.get('GITHUB_SHA')}
    snap['binance_before'] = float(get(BINANCE)['price'])
    snap['deribit_index'] = get(DERIBIT_IDX)['result']['index_price']
    events = [e for e in get(GAMMA) if e.get('slug', '').startswith('bitcoin-above-on-')]
    markets = []
    for e in events:
        for m in e.get('markets', []):
            if not m.get('enableOrderBook') or m.get('closed'):
                continue
            yes_token = json.loads(m['clobTokenIds'])[0]
            assert json.loads(m['outcomes'])[0] == 'Yes'
            row = {'event_slug': e['slug'], 'event_end': e['endDate'],
                   'market_id': m['id'], 'strike_label': m.get('groupItemTitle'),
                   'question': m.get('question'), 'end_date': m.get('endDate'),
                   'yes_token': yes_token, 'fee_type': m.get('feeType'),
                   # E-006 v1.2: per-market fee metadata (fail closed if absent)
                   'fees_enabled': m.get('feesEnabled'),
                   'fee_schedule': m.get('feeSchedule')}
            try:
                row['book'] = trim_book(get(BOOK.format(yes_token)))
            except Exception as exc:  # counted by the analysis as a failed source
                snap['errors'].append(f"book {m['id']}: {exc}")
                row['book'] = None
            markets.append(row)
    snap['polymarket'] = markets
    horizon = now + timedelta(days=15)
    opts = get(DERIBIT_OPT)['result']
    snap['deribit_options'] = [{k: o.get(k) for k in OPT_FIELDS} for o in opts
                               if deribit_expiry(o['instrument_name']) <= horizon]
    snap['binance_after'] = float(get(BINANCE)['price'])
    snap['finished_at'] = datetime.now(timezone.utc).isoformat()
    snap['elapsed_s'] = round(time.time() - t0, 2)
    return snap


def main(argv):
    out = Path(argv[1] if len(argv) > 1 else 'e006_snapshots')
    out.mkdir(parents=True, exist_ok=True)
    snap = snapshot()
    stamp = snap['started_at'][:16].replace(':', '').replace('-', '')
    path = out / f'{stamp}Z.json.gz'
    with gzip.open(path, 'wt') as f:
        json.dump(snap, f, separators=(',', ':'))
    # Counts only: never print prices (no peeking before analysis).
    print(f"{path}: {len(snap['polymarket'])} markets, "
          f"{len(snap['deribit_options'])} options, {len(snap['errors'])} errors, "
          f"{snap['elapsed_s']}s")
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))

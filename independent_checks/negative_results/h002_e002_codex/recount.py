#!/usr/bin/env python3
"""Independent H-002 / E-002 recount. Standard library; database is read-only.

No author implementation is imported or invoked. Numeric rules transcribe the
frozen protocol, whose exact bytes are pinned. Gamma is the saved D1 source,
not a new fetch. All monetary calculations use Decimal; JSON decimals are strings.
"""
import argparse
import base64
from collections import Counter, defaultdict
from datetime import datetime, timezone
from decimal import Decimal
import gzip
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import subprocess
import sys
import time

D = Decimal
ZERO, ONE = D(0), D(1)
DB_SHA = '1fb018c6c3e0dc74d740d142120f26193c9b452825e89bb4524b566763425885'
PROTOCOL_SHA = 'b63c91fdd582eb58ed399a6fddb97f87dd05b3a76531b9d10c6ac22d783186a9'
GAMMA_SHA = '01bd94154c5514e00ff22e7e7c7035e2fbbc511fb4d1f9c10ecf9ee1e76336b7'
PLACEHOLDER = re.compile(r'\b(?:Candidate|Person|Player|Team|Outcome) [A-Z]\b')


def sha(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def dec(x):
    return None if x is None else D(str(x))


def dt(x):
    if not x:
        return None
    return datetime.fromisoformat(x.replace('Z', '+00:00')).astimezone(timezone.utc)


def unpack(text):
    obj = json.loads(text)
    if obj.get('encoding') == 'gzip+base64':
        obj = json.loads(gzip.decompress(base64.b64decode(obj['data'])))
    return obj


def levels(book, side, mirror=False):
    # Counter preserves duplicate levels rather than collapsing them into a set.
    return Counter((ONE - D(r['price']) if mirror else D(r['price']), D(r['size']))
                   for r in book[side])


def quantiles(values):
    if not values:
        return None
    v = sorted(values)
    out = {}
    for q in ('0', '0.05', '0.25', '0.5', '0.75', '0.95', '1'):
        h = D(q) * (len(v) - 1)
        lo = int(h)
        hi = min(lo + 1, len(v) - 1)
        out[q] = v[lo] + (h - lo) * (v[hi] - v[lo])
    return out


def h002(c):
    rows = c.execute("""SELECT * FROM market_snapshots_v2 WHERE capture_tier='tier_a'
        AND fetch_status='ok' AND best_ask IS NOT NULL AND best_bid IS NOT NULL
        AND no_best_ask IS NOT NULL ORDER BY id""").fetchall()
    sums, mismatches, times = [], [], Counter()
    top_mirrored = exact = yl = nl = 0
    for r in rows:
        sums.append(dec(r['best_ask']) + dec(r['no_best_ask']))
        top_mirrored += dec(r['no_best_ask']) == ONE - dec(r['best_bid'])
        p = unpack(r['raw_payload'])
        y, n = p['yes_book'], p['no_book']
        yl += len(y['bids']) + len(y['asks'])
        nl += len(n['bids']) + len(n['asks'])
        mirrored = (levels(y, 'bids', True) == levels(n, 'asks') and
                    levels(y, 'asks', True) == levels(n, 'bids'))
        exact += mirrored
        if not mirrored:
            delta = int(n['timestamp']) - int(y['timestamp'])
            times[delta] += 1
            mismatches.append({'snapshot_id': r['id'], 'no_minus_yes_ms': delta,
                               'ask_sum': sums[-1]})
    return {'status': 'REJECT', 'scope': 'single-binary quote mechanism; no numeric preregistration',
            'pairs': len(rows), 'markets': len({r['market_id'] for r in rows}),
            'events': len({r['event_id'] for r in rows}),
            'slots': sorted({r['scheduled_slot'] for r in rows}),
            'top_mirror_pairs': top_mirrored, 'ask_sum_min': min(sums),
            'ask_sum_mean': sum(sums) / len(sums),
            'ask_sum_below_one': sum(s < ONE for s in sums),
            'exact_ladder_pairs': exact, 'yes_levels': yl, 'no_levels': nl,
            'ladder_mismatch_timestamp_deltas_ms': dict(sorted(times.items())),
            'ladder_mismatches': mismatches}


def fee_rate(meta, observations, at):
    # Latest observation at or before this leg's capture; never use a future fee.
    prior = [r for r in observations if dt(r['observed_at']) <= at]
    if prior:
        r = prior[-1]
        if r['fees_enabled'] == 0:
            return ZERO, 'observation_disabled'
        if r['fee_rate'] is not None:
            return dec(r['fee_rate']), 'observation_rate'
    if meta.get('feesEnabled') is False:
        return ZERO, 'metadata_disabled'
    rate = (meta.get('feeSchedule') or {}).get('rate')
    if rate is not None:
        return dec(rate), 'metadata_schedule'
    return None, 'unknown'


def decision(rows, all_slots):
    events = {r['neg_risk_id'] for r in rows}
    if len(rows) < 20 or len(events) < 5:
        return 'DATA-BLOCKED', 'insufficient qualifying event-slots or events', []
    opportunities = defaultdict(list)
    for r in rows:
        for side in ('long', 'short'):
            if r[f'{side}_size_ok'] and r[f'edge_{side}'] > D('0.005'):
                opportunities[(r['neg_risk_id'], side)].append(r['scheduled_slot'])
    episodes = []
    for (event, side), slots in sorted(opportunities.items()):
        indices = sorted(all_slots.index(s) for s in slots)
        runs = []
        for i in indices:
            if not runs or i != runs[-1][-1] + 1:
                runs.append([])
            runs[-1].append(i)
        episodes.extend({'neg_risk_id': event, 'direction': side,
                         'slots': [all_slots[i] for i in run]} for run in runs)
    if any(len(e['slots']) >= 2 for e in episodes):
        return 'INCONCLUSIVE', 'screen survives; persistent quoted episode', episodes
    return 'REJECT', ('zero opportunities at cadence' if not episodes else
                      'isolated opportunities only at cadence'), episodes


def tradable_legs(event, at):
    required, placeholders, unknown = [], [], []
    for m in event['markets']:
        mid = str(m['id'])
        if PLACEHOLDER.search(m.get('question', '')):
            placeholders.append(mid)
            continue
        if m.get('enableOrderBook') is False:
            continue
        start = dt(m.get('acceptingOrdersTimestamp') or m.get('createdAt'))
        close = dt(m.get('closedTime'))
        if m.get('enableOrderBook') is None or start is None:
            unknown.append(mid)
        elif start <= at and (close is None or close > at):
            required.append(mid)
    other = {str(m['id']) for m in event['markets'] if m.get('negRiskOther') is True}
    return required, placeholders, unknown, other


def e002(c, gamma):
    metadata = {r['id']: json.loads(r['raw_json']) for r in c.execute(
        'SELECT id,raw_json FROM markets WHERE raw_json IS NOT NULL')}
    nr = {mid: m for mid, m in metadata.items() if m.get('negRisk') is True
          and m.get('negRiskMarketID')}
    group_to_event = defaultdict(set)
    for m in nr.values():
        for e in m.get('events', []):
            group_to_event[m['negRiskMarketID']].add(str(e['id']))
    fees = defaultdict(list)
    for r in c.execute('SELECT * FROM market_fee_observations ORDER BY observed_at,id'):
        if r['market_id'] in nr:
            fees[r['market_id']].append(dict(r))
    groups = defaultdict(dict)
    null_slots = 0
    duplicate_keys = []
    for r in c.execute("""SELECT * FROM market_snapshots_v2 WHERE fetch_status='ok'
        AND best_bid IS NOT NULL AND best_ask IS NOT NULL ORDER BY id"""):
        mid = r['market_id']
        if mid not in nr:
            continue
        if r['scheduled_slot'] is None:
            null_slots += 1
            continue
        key = (nr[mid]['negRiskMarketID'], r['scheduled_slot'])
        if mid in groups[key]:
            duplicate_keys.append([*key, mid])
        groups[key][mid] = dict(r)
    # Duplicates have no frozen tie-break, so never silently pick a row.
    if duplicate_keys:
        raise ValueError(f'Unspecified duplicate leg-slot selection: {duplicate_keys[:5]}')
    funnel = Counter(neg_risk_markets=len(nr), neg_risk_events=len(group_to_event),
                     event_slots=len(groups), null_slot_rows_excluded=null_slots)
    rejects = Counter()
    details = []
    fee_sources = Counter()
    exchange_unknown = 0
    for (group, slot), captured in sorted(groups.items()):
        eids = group_to_event[group]
        if len(eids) != 1:
            rejects['ambiguous_event_link'] += 1
            continue
        eid = next(iter(eids))
        if eid not in gamma:
            rejects['missing_gamma'] += 1
            continue
        at = min(dt(r['captured_at']) for r in captured.values())
        required, placeholders, unknown, other = tradable_legs(gamma[eid], at)
        if unknown:
            rejects['unknown_tradability'] += 1
            continue
        if len(required) < 2:
            rejects['fewer_than_two_legs'] += 1
            continue
        if placeholders and not (other & set(required) & captured.keys()):
            rejects['non_exhaustive_placeholder_event'] += 1
            continue
        if not set(required) <= captured.keys():
            rejects['incomplete'] += 1
            continue
        funnel['complete'] += 1
        legs = [captured[mid] for mid in sorted(required)]
        capture_span = (max(dt(r['captured_at']) for r in legs) -
                        min(dt(r['captured_at']) for r in legs)).total_seconds()
        if capture_span > 60:
            rejects['asynchronous'] += 1
            continue
        funnel['synchronous'] += 1
        rates, sources = [], []
        for r in legs:
            rate, source = fee_rate(nr.get(r['market_id'], metadata.get(r['market_id'], {})),
                                    fees[r['market_id']], dt(r['captured_at']))
            rates.append(rate)
            sources.append(source)
        if None in rates:
            rejects['unknown_fee'] += 1
            continue
        funnel['fee_known'] += 1
        fee_sources.update(sources)
        bid, ask = [dec(r['best_bid']) for r in legs], [dec(r['best_ask']) for r in legs]
        long_fee = sum(rate * p * (ONE-p) for rate, p in zip(rates, ask))
        short_fee = sum(rate * p * (ONE-p) for rate, p in zip(rates, bid))
        minimums = [max(D(5), dec(metadata[r['market_id']]['orderMinSize']))
                    if metadata[r['market_id']].get('orderMinSize') is not None else None
                    for r in legs]
        funnel['unknown_minimum_size_slots'] += None in minimums
        long_ok = all(n is not None and r['best_ask_size'] is not None and dec(r['best_ask_size']) >= n
                      for r, n in zip(legs, minimums))
        short_ok = all(n is not None and r['best_bid_size'] is not None and dec(r['best_bid_size']) >= n
                       for r, n in zip(legs, minimums))
        funnel['long_size_ok'] += long_ok
        funnel['short_size_ok'] += short_ok
        funnel['either_direction_size_ok'] += long_ok or short_ok
        exchange_times = []
        for r in legs:
            p = unpack(r['raw_payload'])
            book = p.get('yes_book', p)
            timestamp = book.get('timestamp')
            if timestamp is not None:
                exchange_times.append(int(timestamp))
        exchange_span = ((max(exchange_times) - min(exchange_times)) / 1000
                         if len(exchange_times) == len(legs) else None)
        exchange_unknown += exchange_span is None
        details.append({'neg_risk_id': group, 'event_id': eid, 'title': gamma[eid].get('title'),
            'scheduled_slot': slot, 'leg_ids': [r['market_id'] for r in legs],
            'snapshot_ids': [r['id'] for r in legs], 'n_legs': len(legs),
            'capture_span_seconds': capture_span, 'exchange_span_seconds': exchange_span,
            'sum_ask_minus_one': sum(ask) - ONE, 'one_minus_sum_bid': ONE - sum(bid),
            'gross_long': ONE - sum(ask), 'gross_short': sum(bid) - ONE,
            'long_fee': long_fee, 'short_fee': short_fee,
            'edge_long': ONE - sum(ask) - long_fee,
            'edge_short': sum(bid) - ONE - short_fee,
            'long_size_ok': long_ok, 'short_size_ok': short_ok,
            'min_ask_size': min(dec(r['best_ask_size']) for r in legs),
            'fee_sources': sources, 'fee_rates': rates})
    # Qualifying means at least one direction passes its own frozen size gate.
    qualified = [r for r in details if r['long_size_ok'] or r['short_size_ok']]
    all_slots = sorted({s for _, s in groups})
    status, reason, episodes = decision(qualified, all_slots)
    direction_count = sum(r[f'{s}_size_ok'] and r[f'edge_{s}'] > D('0.005')
                          for r in qualified for s in ('long', 'short'))
    best = sorted(({'event_id': r['event_id'], 'title': r['title'],
                    'scheduled_slot': r['scheduled_slot'], 'direction': side,
                    'gross': r[f'gross_{side}'], 'fee': r[f'{side}_fee'],
                    'net': r[f'edge_{side}'], 'min_ask_size': r['min_ask_size']}
                   for r in qualified for side in ('long', 'short') if r[f'{side}_size_ok']),
                  key=lambda r: r['net'], reverse=True)
    return {'strict_local_completeness': {'status': 'DATA-BLOCKED',
                'events_rows': c.execute('SELECT COUNT(*) FROM events').fetchone()[0],
                'event_markets_rows': c.execute('SELECT COUNT(*) FROM event_markets').fetchone()[0],
                'reason': 'frozen full-event market-list source absent; D1 required'},
            'd1_recount': {'status': status, 'decision_reason': reason,
                'funnel': dict(funnel), 'exclusions': dict(rejects),
                'gamma_events_available': len(gamma),
                'gamma_events_with_usable_slotted_snapshots': len({next(iter(group_to_event[g])) for g,s in groups if len(group_to_event[g]) == 1 and next(iter(group_to_event[g])) in gamma}),
                'qualifying_event_slots': len(qualified),
                'qualifying_events': len({r['event_id'] for r in qualified}),
                'qualifying_scheduled_slots': len({r['scheduled_slot'] for r in qualified}),
                'median_legs': quantiles([D(r['n_legs']) for r in qualified])['0.5'] if qualified else None,
                'opportunity_event_slots': sum(any(r[f'{s}_size_ok'] and r[f'edge_{s}'] > D('0.005') for s in ('long','short')) for r in qualified),
                'opportunity_directions': direction_count, 'episodes': episodes,
                'sum_ask_minus_one_quantiles': quantiles([r['sum_ask_minus_one'] for r in qualified]),
                'one_minus_sum_bid_quantiles': quantiles([r['one_minus_sum_bid'] for r in qualified]),
                'fee_sources': dict(fee_sources), 'best_net_cases': best[:10],
                'exchange_span_unknown_slots': exchange_unknown,
                'exchange_span_above_60_seconds': sum(r['exchange_span_seconds'] is not None and r['exchange_span_seconds'] > 60 for r in qualified),
                'event_slots': qualified, 'pre_size_event_slots': details}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', type=Path, required=True)
    parser.add_argument('--package', type=Path, required=True)
    args = parser.parse_args()
    started = time.monotonic()
    protocol = args.package / 'negrisk_basket/E-002_frozen_protocol.yaml'
    gamma_path = args.package / 'data/gamma_events.json.gz'
    inputs = {str(p.resolve()): sha(p) for p in (args.db, protocol, gamma_path)}
    for p, expected in ((args.db, DB_SHA), (protocol, PROTOCOL_SHA), (gamma_path, GAMMA_SHA)):
        if inputs[str(p.resolve())] != expected:
            raise ValueError(f'Pinned input hash mismatch: {p}')
    gamma = json.load(gzip.open(gamma_path, 'rt'))
    c = sqlite3.connect(args.db.resolve().as_uri() + '?mode=ro', uri=True)
    c.execute('PRAGMA query_only=ON')
    c.row_factory = sqlite3.Row
    c.execute('BEGIN')
    try:
        result = {'generated_at_utc': datetime.now(timezone.utc).isoformat(),
            'code_commit': subprocess.check_output(['git','rev-parse','HEAD'], text=True).strip(),
            'script_sha256': sha(__file__), 'python': sys.version,
            'inputs_sha256': inputs, 'database_access': 'mode=ro; PRAGMA query_only=ON; read transaction',
            'independence': 'No author code opened before first-pass commit; handoff headlines, package README, and the existing recount summary were already visible. Not blinded to reported results.',
            'snapshot_inventory': [dict(r) for r in c.execute('SELECT is_authoritative, COUNT(*) AS rows, MIN(captured_at) AS first_capture, MAX(captured_at) AS last_capture FROM market_snapshots_v2 GROUP BY is_authoritative')],
            'implementation_choices': ['Decimal math from SQLite string representations; exact raw decimal strings for ladders.',
                'D1: use saved 2026-11-11 Gamma event payloads; historical 2026-10-05 payloads unavailable.',
                'D2: exclude null scheduled_slot; no new threshold or time filter.',
                'Unnamed placeholders recognized by Candidate/Person/Player/Team/Outcome plus one capital letter; require captured Other.',
                'Do not substitute exchange timestamps into the frozen captured_at synchrony gate; report them separately.',
                'Latest fee observation at/before each leg capture, then raw metadata feeSchedule; unknown fee excluded.'],
            'h002': h002(c), 'e002': e002(c, gamma)}
    finally:
        c.rollback()
        c.close()
    result['database_sha256_after'] = sha(args.db)
    if result['database_sha256_after'] != DB_SHA:
        raise ValueError('Database bytes changed during read')
    result['elapsed_seconds'] = time.monotonic() - started
    print(json.dumps(result, indent=2, sort_keys=True, default=str))


if __name__ == '__main__':
    main()

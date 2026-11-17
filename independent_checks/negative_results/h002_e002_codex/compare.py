#!/usr/bin/env python3
"""Post-first-pass diagnostics; reads committed raw JSON and recorded results.

This comparison was written after opening the author implementation. It never
rewrites first_pass.json or changes its population/quantile definitions.
"""
import argparse
from decimal import Decimal as D
import json
from pathlib import Path
import sqlite3
import recount as r


def nearest_rank(values):
    v = sorted(values)
    return {q: v[int(D(q) * (len(v) - 1))] for q in ('0','0.05','0.25','0.5','0.75','0.95','1')}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--first-pass', type=Path, required=True)
    ap.add_argument('--diagnostic-pass', type=Path, required=True)
    ap.add_argument('--package', type=Path, required=True)
    ap.add_argument('--db', type=Path, required=True)
    a = ap.parse_args()
    first = json.loads(a.first_pass.read_text())
    current = json.loads(a.diagnostic_pass.read_text())
    e = current['e002']['d1_recount']
    pre = e['pre_size_event_slots']
    original_path = a.package/'negrisk_basket/E-002_result_recorded_2026-10-05.json'
    refetch_path = a.package/'negrisk_basket/E-002_result.json'
    h_path = a.package/'mirrored_book_result.json'
    original, refetch, h = [json.loads(p.read_text()) for p in (original_path, refetch_path, h_path)]
    # Compare exact event-slot membership with author-source tradability logic,
    # not merely matching counts. This is disclosed post-comparison alignment.
    import gzip
    gamma = json.load(gzip.open(a.package/'data/gamma_events.json.gz', 'rt'))
    c = sqlite3.connect(a.db.resolve().as_uri()+'?mode=ro', uri=True)
    c.execute('PRAGMA query_only=ON')
    c.row_factory = sqlite3.Row
    metadata = {x['id']:json.loads(x['raw_json']) for x in c.execute('SELECT id,raw_json FROM markets')}
    from collections import defaultdict
    seen = defaultdict(dict)
    for x in c.execute("SELECT * FROM market_snapshots_v2 WHERE fetch_status='ok' AND best_bid IS NOT NULL AND best_ask IS NOT NULL AND scheduled_slot IS NOT NULL"):
        m = metadata[x['market_id']]
        if m.get('negRisk') and m.get('negRiskMarketID'):
            seen[(m['negRiskMarketID'],x['scheduled_slot'])][x['market_id']] = dict(x)
    mapping = {m['negRiskMarketID']:str(m['events'][0]['id']) for m in metadata.values()
               if m.get('negRisk') and m.get('negRiskMarketID') and m.get('events')}
    author_membership = set()
    failures = defaultdict(int)
    for (key, slot), captured in seen.items():
        event = gamma[mapping[key]]
        at = min(r.dt(x['captured_at']) for x in captured.values())
        tradable = [m for m in event['markets'] if m.get('enableOrderBook')
                    and r.dt(m.get('acceptingOrdersTimestamp') or m.get('createdAt'))
                    and r.dt(m.get('acceptingOrdersTimestamp') or m.get('createdAt')) <= at
                    and (not m.get('closedTime') or r.dt(m['closedTime']) > at)]
        ids = {str(m['id']) for m in tradable}
        if len(tradable) < 2:
            failures['fewer_than_two_legs'] += 1
        elif not ids <= captured.keys():
            failures['incomplete'] += 1
        elif event.get('negRiskAugmented') and not any(m.get('negRiskOther') for m in tradable):
            failures['augmented_without_other'] += 1
        else:
            author_membership.add((key, slot))
    # Synchrony and fees were already checked independently for every pre-size row;
    # equal membership here confirms selection before those two unchanged gates.
    membership = {(x['neg_risk_id'], x['scheduled_slot']) for x in pre}
    failing_size = [x for x in pre if not x['long_size_ok'] and not x['short_size_ok']]
    size_details = []
    for row in failing_size:
        legs = []
        for sid in row['snapshot_ids']:
            x = c.execute('SELECT * FROM market_snapshots_v2 WHERE id=?',(sid,)).fetchone()
            legs.append({k:x[k] for k in ('id','market_id','best_bid_size','best_ask_size','best_bid','best_ask')}
                        | {'minimum_size': metadata[x['market_id']].get('orderMinSize')})
        size_details.append({'event_slot':row, 'legs':legs})
    groups_with_any_snapshots = {metadata[x[0]]['negRiskMarketID'] for x in c.execute("SELECT DISTINCT market_id FROM market_snapshots_v2 WHERE fetch_status='ok' AND best_bid IS NOT NULL AND best_ask IS NOT NULL") if metadata[x[0]].get('negRisk') and metadata[x[0]].get('negRiskMarketID')}
    c.close()
    asks = nearest_rank([D(x['sum_ask_minus_one']) for x in pre])
    bids = nearest_rank([D(x['one_minus_sum_bid']) for x in pre])
    def numeric_match(actual, recorded):
        return all(actual[str(D(k).normalize())] == D(str(v)) for k,v in recorded.items())
    best_gross = max(D(x[f'gross_{side}']) for x in pre for side in ('long','short') if x[f'{side}_size_ok'])
    near_misses = [x for x in pre if D(x['gross_long']) == best_gross and x['long_size_ok']]
    output = {'comparison_phase': 'after first-pass raw commit 73c8873; no first-pass replacement',
        'input_hashes': {str(p):r.sha(p) for p in (a.first_pass,a.diagnostic_pass,original_path,refetch_path,h_path)},
        'author_code_hashes':{str(p.relative_to(a.package)):r.sha(p) for p in (
            a.package/'mirrored_book.py',a.package/'negrisk_basket/E-002_compute.py',a.package/'negrisk_basket/E-002_compute_frozen.py')},
        'h002_checks': {'pairs': first['h002']['pairs'] == h['sample']['rows'],
            'top_mirrored':first['h002']['top_mirror_pairs'] == h['top_of_book']['rows_no_ask_eq_1_minus_yes_bid'],
            'minimum':D(first['h002']['ask_sum_min']) == D(str(h['top_of_book']['min_yes_ask_plus_no_ask'])),
            'exact_ladders':first['h002']['exact_ladder_pairs'] == h['full_ladder']['pairs_mirrored_exactly'],
            'timestamp_deltas':first['h002']['ladder_mismatch_timestamp_deltas_ms'] == h['full_ladder']['mismatch_book_timestamp_gap_ms']},
        'e002_population':{'pre_size':len(pre), 'post_size':e['qualifying_event_slots'],
            'author_pre_size_membership_count':len(author_membership),
            'membership_identical': membership == author_membership,
            'author_selection_exclusions':dict(failures), 'slots_failing_both_size_gates':size_details,
            'events_with_any_usable_snapshots':len(groups_with_any_snapshots),
            'events_with_usable_slotted_snapshots':e['gamma_events_with_usable_slotted_snapshots'],
            'events_with_gamma_original':original['funnel']['events_with_gamma'],
            'events_with_gamma_refetch':refetch['funnel']['events_with_gamma']},
        'nearest_rank_over_pre_size_population':{'sum_ask_minus_one':asks,'one_minus_sum_bid':bids,
            'ask_quantiles_match_recorded':numeric_match(asks,refetch['sum_ask_minus_1']),
            'bid_quantiles_match_recorded':numeric_match(bids,refetch['one_minus_sum_bid'])},
        'best_size_feasible_gross':best_gross, 'best_gross_cases':near_misses,
        'exchange_timing_pre_size':{'slots':len(pre),
            'known':sum(x['exchange_span_seconds'] is not None for x in pre),
            'above_60_seconds':sum(x['exchange_span_seconds'] is not None and x['exchange_span_seconds'] > 60 for x in pre),
            'max_seconds':max(x['exchange_span_seconds'] for x in pre if x['exchange_span_seconds'] is not None)},
        'status':'REJECT', 'scope':'D1 quote screen at recorded batch cadence; strict local completeness remains DATA-BLOCKED'}
    print(json.dumps(output,indent=2,sort_keys=True,default=str))


if __name__ == '__main__':
    main()

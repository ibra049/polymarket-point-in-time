"""Independent PN-2 CSV recount; never imports the builder or reads outcomes.

Run: python recount.py CSV REPLACED_CSV --output OUTPUT.json
M1 is rederived from normalized titles; M2 from the two recorded ISO instants;
M3 from n_clarifications. This checks CSV arithmetic, not the source extraction.
Bootstrap: each metric's eligible event clusters, 10,000 draws with replacement,
random.Random(20261111) restarted per metric; linear 2.5/97.5 percentiles.
"""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import random
import statistics
import unicodedata
from collections import Counter, defaultdict

SEED = 20261111
REPS = 10000


def normalized(s):
    return ' '.join(unicodedata.normalize('NFKC', s).split()).casefold()


def instant(s):
    return datetime.fromisoformat(s.replace('Z', '+00:00'))


def wilson(k, n):
    if not n:
        return None
    z = 1.959963984540054
    d = 1 + z*z/n
    c = (k/n + z*z/(2*n))/d
    h = z*math.sqrt((k/n)*(1-k/n)/n + z*z/(4*n*n))/d
    return [max(0., c-h), min(1., c+h)]


def percentile(values, p):
    ordered = sorted(values)
    i = (len(ordered)-1)*p
    lo = int(i)
    return ordered[lo] + (ordered[min(lo+1, len(ordered)-1)]-ordered[lo])*(i-lo)


def metric(rows, key):
    eligible = [r for r in rows if r[key] is not None]
    groups = defaultdict(lambda: [0, 0])
    categories = defaultdict(lambda: [0, 0])
    for r in eligible:
        for dest in (groups[r['event_id']], categories[r['category']]):
            dest[0] += int(r[key]); dest[1] += 1
    k = sum(int(r[key]) for r in eligible)
    n = len(eligible)
    boot = []
    rng = random.Random(SEED)
    clusters = list(groups.values())
    for _ in range(REPS if clusters else 0):
        selected = rng.choices(clusters, k=len(clusters))
        boot.append(sum(x[0] for x in selected)/sum(x[1] for x in selected))
    return dict(k=k, n=n, rate=k/n if n else None, wilson_95=wilson(k,n),
                event_cluster_bootstrap_95=[percentile(boot, .025), percentile(boot, .975)] if boot else None,
                eligible_events=len(groups),
                positive_events=len({r['event_id'] for r in eligible if r[key]}),
                by_category={c: dict(k=v[0],n=v[1],rate=v[0]/v[1],wilson_95=wilson(*v)) for c,v in sorted(categories.items())})


def recount(source, replacements):
    with open(source, newline='') as f:
        raw = list(csv.DictReader(f))
    with open(replacements, newline='') as f:
        replaced = list(csv.DictReader(f))
    rows, differences, deltas = [], [], []
    for r in raw:
        m1 = normalized(r['onchain_title']) != normalized(r['current_title'])
        both = bool(r['onchain_instant'] and r['current_instant'])
        delta = (instant(r['current_instant'])-instant(r['onchain_instant'])).total_seconds()/3600 if both else None
        m2 = abs(delta) >= 1 if both else None
        fmt = 0 < abs(delta) < 1 if both else None
        m3 = int(r['n_clarifications']) > 0
        derived = dict(m1_title_edit=m1,m2_both_parse=both,m2_deadline_edit=m2,m2_format_only=fmt,m3_clarification=m3)
        for key,value in derived.items():
            recorded = None if r[key] == '' else bool(int(r[key]))
            if recorded != value:
                differences.append(dict(market_id=r['market_id'],field=key,recorded=recorded,derived=value))
        if both and (not r['delta_hours'] or not math.isclose(delta,float(r['delta_hours']),abs_tol=1e-9)):
            differences.append(dict(market_id=r['market_id'],field='delta_hours',recorded=r['delta_hours'],derived=delta))
        if m2:
            deltas.append(abs(delta))
        rows.append(dict(event_id=r['event_id'],category=r['category'],m1=m1,m2=m2,format=fmt,m3=m3))
    ranks = [int(r['draw_rank']) for r in raw+replaced]
    return dict(study='PN-2 independent CSV recount',generated_utc=datetime.now(timezone.utc).isoformat(),
                status='DATA-BLOCKED' if len(rows)<400 else 'INCONCLUSIVE',
                status_reason='Descriptive audit has no frozen promote/reject threshold; provenance and chain checks are separate.',
                input_sha256={str(p):hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in [source,replacements]},
                method=dict(seed=SEED,bootstrap_replicates=REPS,bootstrap_clusters='eligible events separately per metric; first-seen event order',
                            bootstrap_rng='Python random.Random, choices; RNG restarted per metric',quantiles='linear interpolation'),
                achieved_n=len(rows),distinct_events=len({r['event_id'] for r in raw}),
                unique_market_ids=len({r['market_id'] for r in raw}),
                draw_ranks_partition_prefix=sorted(ranks)==list(range(1,max(ranks)+1)),draws_walked=max(ranks),
                replacements=len(replaced),replacement_categories=dict(sorted(Counter(r['category'] for r in replaced).items())),
                replacement_reasons=dict(Counter(r['status'] for r in replaced)),
                verified_categories=dict(sorted(Counter(r['category'] for r in raw).items())),
                M1=metric(rows,'m1'),M2=metric(rows,'m2'),FORMAT=metric(rows,'format'),M3=metric(rows,'m3'),
                median_abs_delta_hours_M2=statistics.median(deltas) if deltas else None,
                csv_field_mismatches=differences,
                positive_market_ids={key:[r['market_id'] for r,d in zip(raw,rows) if d[key]] for key in ['m1','m2','m3']})


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('csv');p.add_argument('replacements');p.add_argument('--output',required=True)
    a=p.parse_args()
    result=recount(a.csv,a.replacements)
    Path(a.output).write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
    for key in ['M1','M2','FORMAT','M3']:
        m=result[key]; print(key,m['k'],m['n'],m['wilson_95'],m['event_cluster_bootstrap_95'])
    print('CSV field mismatches:',len(result['csv_field_mismatches']))

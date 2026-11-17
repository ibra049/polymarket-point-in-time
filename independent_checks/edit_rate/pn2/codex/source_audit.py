"""Post-first-pass PN-2 checks: provenance, independent sampling and disclosed-CI comparison.

Added after first_pass.json was committed; does not alter that result. Repeats
bootstrap with the builder's now-disclosed RNG/order/cluster universe solely to
explain endpoint differences, and preserves both sets of intervals.
Correction: native parquet event_id is large_string; the original numeric-order
diagnostic is preserved separately in source_audit.json (commit e423914).
"""
import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import random
import re
import subprocess

import numpy as np
import pyarrow.parquet as pq

HERE=Path(__file__).resolve().parent
PN2=HERE.parent
NOTE=PN2.parent
REPO=HERE.parents[4]


def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for chunk in iter(lambda:f.read(1<<20),b''):h.update(chunk)
    return h.hexdigest()


def git(*args):
    r=subprocess.run(['git',*args],cwd=REPO,capture_output=True,text=True)
    return dict(exit_code=r.returncode,stdout=r.stdout.strip(),stderr=r.stderr.strip())


def main(root,grammar):
    with open(PN2/'edit_rate_sample.csv',newline='') as f: rows=list(csv.DictReader(f))
    with open(PN2/'replaced_draws.csv',newline='') as f: reps=list(csv.DictReader(f))
    recorded=json.loads((NOTE/'PN-2_result.json').read_text())
    first=json.loads((HERE/'first_pass.json').read_text())
    draws=json.loads((PN2/'draws.json').read_text())
    regenerated=json.loads((HERE/'sample_regenerated.json').read_text())
    # Only the market-id column is decoded for the independent draw.
    market_ids={int(v) for v in pq.read_table(root/'markets.parquet',columns=['market_id']).column(0).to_pylist()}
    gamma_ids=set()
    with open(root/'gamma_rules.jsonl') as f:
        for line in f:
            g=json.loads(line)
            if g.get('found') is True and g.get('questionID'): gamma_ids.add(int(g['market_id']))
    pop=sorted(market_ids & gamma_ids)
    independent_order=[str(v) for v in random.Random(20261111).sample(pop,2000)]
    all_rows=sorted(rows+reps,key=lambda r:int(r['draw_rank']))
    sample=dict(population_size=len(pop),population_sha256_sorted_ids=hashlib.sha256('\n'.join(map(str,pop)).encode()).hexdigest(),
                original_sample_script_output_equal=regenerated==draws,
                independent_2000_ids_equal=independent_order==draws['draws'],
                all_1372_ranked_ids_equal=all(independent_order[int(r['draw_rank'])-1]==r['market_id'] for r in all_rows),
                verified_1000_ids_equal=[independent_order[int(r['draw_rank'])-1] for r in rows]==[r['market_id'] for r in rows],
                original_sample_requires_gamma=True,markets_columns_independent=['market_id'],
                market_row_count=len(market_ids),gamma_with_qid_count=len(gamma_ids))
    # Diagnostic ONLY: implement the disclosed computation without importing measure.py.
    event_ids=sorted({r['event_id'] for r in rows})
    event_index={e:i for i,e in enumerate(event_ids)}
    indices=np.random.default_rng(20261111).integers(0,len(event_ids),size=(10000,len(event_ids)))
    mapping={'M1':'M1_title_edit','M2':'M2_deadline_edit','FORMAT':'M2_format_only_sub_hour','M3':'M3_onchain_clarification'}
    columns={'M1':'m1_title_edit','M2':'m2_deadline_edit','FORMAT':'m2_format_only','M3':'m3_clarification'}
    comparison={}
    for key,rec_key in mapping.items():
        k=np.zeros(len(event_ids));n=np.zeros(len(event_ids))
        for r in rows:
            val=r[columns[key]]
            if val!='':
                ix=event_index[r['event_id']];k[ix]+=int(val);n[ix]+=1
        sk=k[indices].sum(axis=1);sn=n[indices].sum(axis=1)
        ci=np.percentile(sk[sn>0]/sn[sn>0],[2.5,97.5]).tolist()
        rec=recorded['rates'][rec_key]
        comparison[key]=dict(counts_equal=[first[key]['k'],first[key]['n']]==[rec['k'],rec['n']],
                             wilson_equal_at_recorded_precision=[round(v,6) for v in first[key]['wilson_95']]==rec['wilson95'],
                             first_pass_bootstrap=first[key]['event_cluster_bootstrap_95'],recorded_bootstrap=rec['cluster_bootstrap95'],
                             disclosed_method_diagnostic=ci,
                             disclosed_method_equal_at_recorded_precision=[round(v,6) for v in ci]==rec['cluster_bootstrap95'],
                             positive_events_equal=first[key]['positive_events']==rec['distinct_events_among_positives'],
                             category_counts_equal={c:f"{v['k']}/{v['n']}" for c,v in first[key]['by_category'].items()}==rec['by_category'])
    paths={name:root/name for name in ['markets.parquet','gamma_rules.jsonl']}
    paths.update({name:PN2/name for name in ['draws.json','sample.py','fetch.py','measure.py']})
    paths.update({name:grammar/name for name in ['schedule_grammar_v5.py','schedule_grammar_v4.py','schedule_grammar_v3.py']})
    input_hashes={name:dict(actual=sha(p),recorded=recorded['input_sha256'].get(name)) for name,p in paths.items()}
    for v in input_hashes.values():v['equal']=v['actual']==v['recorded']
    prereg=NOTE/'PN-2_population_edit_rate_prereg.md'
    prereg_rel=str(prereg.relative_to(REPO))
    prior=subprocess.run(['git','show',f'44d0be8:{prereg_rel}'],cwd=REPO,capture_output=True,check=True).stdout
    measure_log=(PN2/'measure.log').read_text()
    log_times=re.findall(r'"generated_utc":\s*"([^"]+)"',measure_log)
    freeze=git('show','-s','--format=%cI','44d0be8')['stdout']
    result=dict(generated_utc=datetime.now(timezone.utc).isoformat(),sample=sample,comparison=comparison,
                diagnostic_method='numpy default_rng(20261111); native large_string event IDs sorted lexicographically; all 989 clusters shared across measures; 10,000 resamples',
                first_pass_preserved=True,original_status=recorded['status'],original_status_allowed=recorded['status'] in ['PROMOTE','REJECT','INCONCLUSIVE','DATA-BLOCKED','INVALID-RUN','PARKED'],
                input_hashes=input_hashes,prereg_current_sha256=sha(prereg),prereg_at_freeze_sha256=hashlib.sha256(prior).hexdigest(),
                prereg_unchanged=prior==prereg.read_bytes(),prereg_commit_utc=datetime.fromisoformat(freeze).astimezone(timezone.utc).isoformat(),
                result_generation_utc=recorded['generated_utc'],measure_log_generation_utc=log_times,
                generated_after_prereg=datetime.fromisoformat(recorded['generated_utc'].replace('Z','+00:00'))>datetime.fromisoformat(freeze),
                fetch_log_has_wallclock_timestamp=False,fetch_log_head=int(re.search(r'head (\d+)',(PN2/'fetch.log').read_text()).group(1)),
                original_commit=git('show','-s','--format=%H %cI %s','2bdf13e'),
                prereg_is_ancestor=git('merge-base','--is-ancestor','44d0be8','2bdf13e')['exit_code']==0,
                original_builder_first_commit=git('log','--reverse','--format=%H %cI','--',str((PN2/'measure.py').relative_to(REPO))),
                original_result_first_commit=git('log','--reverse','--format=%H %cI','--',str((NOTE/'PN-2_result.json').relative_to(REPO))),
                original_code_before_output=False,raw_fetch_checkpoint_in_worktree=(PN2/'fetch_raw.jsonl').exists(),
                artifact_sha256={str(p.relative_to(REPO)):sha(p) for p in [prereg,NOTE/'PN-2_result.json',PN2/'edit_rate_sample.csv',PN2/'fetch.log',PN2/'measure.log',HERE/'first_pass.json']})
    (HERE/'source_audit_native_strings.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(sample=sample,hashes_all_match=all(v['equal'] for v in input_hashes.values()),comparison=comparison),indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('root',type=Path);p.add_argument('grammar',type=Path)
    a=p.parse_args();main(a.root,a.grammar)

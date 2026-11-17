"""Independent read-only PN-2 Polygon spot check after committed first-pass numbers.

Plan: random.Random(20261111).sample(CSV rows sorted by numeric market_id,25).
Also check all positive rows as explicitly separate, non-random diagnostics.
Historical cutoff is the builder's original block 97166757, never today's head.
No builder code is imported. Frozen v5 grammar is imported unchanged only after
its hash is checked against the recorded manifest. RPC failures remain unknown.

--plan-only writes the selection/source plan before any network request.
--run reads that plan, checks only its rows, and preserves every RPC response.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import csv
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import random
import re
import subprocess
import sys
import threading
import time

from recount import normalized,instant

HERE=Path(__file__).resolve().parent
PN2=HERE.parent
QI2='0xeee0897acd6893adcaf2ba5158191b3601098ab6bece35c5d57874340b64c5b7'
QI1='0x53af6c2e40505bb55a47d917203a12c8f063b6c505c11094d98ac8f772e8a031'
ADU='0x0059e11815211969c0c4aaf3f498b52b6c2f2d14f286275d0862d70de22a836b'
PRIMARY='https://polygon-mainnet.gateway.tatum.io'
CUTOFF=97166757
LOCK=threading.RLock()
LAST_REQUEST=0.0
FAILURE=None
REFERENCE_PLAN=HERE/'selection_plan.json'


def utc():return datetime.now(timezone.utc).isoformat()


def dynamic_bytes(encoded):
    data=bytes.fromhex(encoded.removeprefix('0x'))
    if len(data)<32:raise ValueError('missing ABI offset')
    offset=int.from_bytes(data[:32],'big')
    if offset%32 or offset+32>len(data):raise ValueError('invalid ABI offset')
    length=int.from_bytes(data[offset:offset+32],'big')
    if offset+32+length>len(data):raise ValueError('truncated ABI bytes')
    return data[offset+32:offset+32+length]


def title_and_rules(text):
    match=re.search(r'(?:^|[\s,])title:\s*(.*?)\s*,?\s*description:',text,re.S)
    if not match:raise ValueError('missing title/description boundary')
    return match.group(1).strip(),text[match.end():]


def rpc(method,params):
    """Serialize and space calls; one failed response closes this source attempt."""
    global LAST_REQUEST,FAILURE
    with LOCK:
        if FAILURE is not None:
            raise RuntimeError('source circuit stopped after prior error: '+FAILURE)
        time.sleep(max(0.0,1.1-(time.monotonic()-LAST_REQUEST)))
        LAST_REQUEST=time.monotonic()
        try:
            return _rpc(method,params)
        except Exception as e:
            FAILURE=str(e)
            raise


def _rpc(method,params):
    req=dict(jsonrpc='2.0',id=1,method=method,params=params)
    started=utc();t=time.monotonic()
    proc=subprocess.run(['curl','--silent','--show-error','--max-time','40','--header','Content-Type: application/json',
                         '--data-binary','@-',PRIMARY],input=json.dumps(req),text=True,capture_output=True)
    rec=dict(started_utc=started,elapsed_seconds=time.monotonic()-t,source=PRIMARY,request=req,
             exit_code=proc.returncode,stderr=proc.stderr)
    try:rec['response']=json.loads(proc.stdout)
    except json.JSONDecodeError:rec['non_json_response']=proc.stdout
    with LOCK:
        with open(HERE/'polygon_rpc.jsonl','a') as f:f.write(json.dumps(rec)+'\n')
    if proc.returncode or 'response' not in rec or 'result' not in rec['response']:
        raise RuntimeError(json.dumps({k:v for k,v in rec.items() if k not in ['request']})[:1200])
    return rec['response']['result']


def plan():
    with open(PN2/'edit_rate_sample.csv',newline='') as f:rows=list(csv.DictReader(f))
    chosen=random.Random(20261111).sample(sorted(rows,key=lambda r:int(r['market_id'])),25)
    selected={r['market_id'] for r in chosen}
    extra=[r for r in rows if r['market_id'] not in selected and any(r[k]=='1' for k in ['m1_title_edit','m2_deadline_edit','m3_clarification'])]
    result=dict(created_utc=utc(),seed=20261111,rule='random.sample of CSV sorted by numeric market_id; no replacement',
                csv_sha256=hashlib.sha256((PN2/'edit_rate_sample.csv').read_bytes()).hexdigest(),
                historical_to_block=CUTOFF,primary_source=PRIMARY,source_reason='Independent allowed provider after preserved Tatum free-quota failure; original builder used Tenderly.',
                failure_rule='No retries/provider substitutions; 1.1-second request spacing; circuit stops network after first error; failed/unattempted rows remain unknown.',
                random_market_ids=[r['market_id'] for r in chosen],supplemental_positive_market_ids=[r['market_id'] for r in extra])
    if HERE/'selection_plan.json' != REFERENCE_PLAN:
        reference=json.loads(REFERENCE_PLAN.read_text())
        if result['random_market_ids']!=reference['random_market_ids'] or result['supplemental_positive_market_ids']!=reference['supplemental_positive_market_ids']:
            raise ValueError('selection changed from original attempt')
        result['original_plan_sha256']=hashlib.sha256(REFERENCE_PLAN.read_bytes()).hexdigest()
    (HERE/'selection_plan.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


def run(root,grammar):
    import pyarrow.parquet as pq
    selection=json.loads((HERE/'selection_plan.json').read_text())
    if selection['primary_source']!=PRIMARY:raise ValueError('source differs from committed plan')
    if selection['csv_sha256']!=hashlib.sha256((PN2/'edit_rate_sample.csv').read_bytes()).hexdigest():raise ValueError('CSV changed since plan')
    ids=selection['random_market_ids']+selection['supplemental_positive_market_ids']
    wanted=set(ids)
    with open(PN2/'edit_rate_sample.csv',newline='') as f:rows={r['market_id']:r for r in csv.DictReader(f) if r['market_id'] in wanted}
    # Decode only frozen metadata columns, in batches. No price/outcome columns.
    cols=['market_id','event_id','category','question','market_start_time']
    meta={}
    for batch in pq.ParquetFile(root/'markets.parquet').iter_batches(columns=cols,batch_size=8192):
        for r in batch.to_pylist():
            if str(r['market_id']) in wanted:meta[str(r['market_id'])]=r
    gamma={}
    with open(root/'gamma_rules.jsonl') as f:
        for line in f:
            g=json.loads(line)
            if str(g['market_id']) in wanted:
                gamma[str(g['market_id'])]={k:g.get(k) for k in ['questionID','negRisk','negRiskRequestID','resolvedBy','description']}
    expected=json.loads((PN2.parent/'PN-2_result.json').read_text())['input_sha256']
    for name in ['schedule_grammar_v3.py','schedule_grammar_v4.py','schedule_grammar_v5.py']:
        if hashlib.sha256((grammar/name).read_bytes()).hexdigest()!=expected[name]:raise ValueError('frozen grammar hash mismatch: '+name)
    sys.path.insert(0,str(grammar))
    from schedule_grammar_v5 import parse
    if (HERE/'polygon_rpc.jsonl').exists():raise ValueError('refuse to overwrite prior RPC evidence')
    chain_id=rpc('eth_chainId',[])
    head=int(rpc('eth_blockNumber',[]),16)
    if int(chain_id,16)!=137 or head<CUTOFF:raise ValueError('unexpected chain/head')
    cutoff_header=rpc('eth_getBlockByNumber',[hex(CUTOFF),False])
    cutoff_utc=datetime.fromtimestamp(int(cutoff_header['timestamp'],16),timezone.utc).isoformat()

    def check(mid):
        row=rows[mid];md=meta[mid];g=gamma[mid]
        result=dict(market_id=mid,selection='random' if mid in selection['random_market_ids'] else 'supplemental-positive',started_utc=utc())
        try:
            qid=g['negRiskRequestID'] if g['negRisk'] and g['negRiskRequestID'] else g['questionID']
            logs=rpc('eth_getLogs',[dict(fromBlock='0x0',toBlock=hex(CUTOFF),topics=[[QI2,QI1,ADU],qid])])
            creation=sorted([l for l in logs if l['topics'][0].lower() in [QI2,QI1]],key=lambda l:(int(l['blockNumber'],16),int(l['logIndex'],16)))
            matching=[l for l in creation if l['address'].lower()==(g['resolvedBy'] or '').lower()]
            c=(matching or creation)[0]
            cb=int(c['blockNumber'],16)
            header=rpc('eth_getBlockByNumber',[c['blockNumber'],False])
            created=datetime.fromtimestamp(int(header['timestamp'],16),timezone.utc)
            text=dynamic_bytes(c['data']).decode('utf-8',errors='strict')
            title,rules=title_and_rules(text)
            current_title=md['question']
            start=md['market_start_time']
            start=start.to_pydatetime() if hasattr(start,'to_pydatetime') else start
            old_inst,old_reason,old_family=parse(rules,created)
            cur_inst,cur_reason,cur_family=parse(g['description'],start)
            adu=[l for l in logs if l['topics'][0].lower()==ADU and l['address'].lower()==c['address'].lower() and int(l['blockNumber'],16)>=cb]
            creator='0x'+c['topics'][3][-40:] if c['topics'][0].lower()==QI2 else None
            creator_count=sum(l['topics'][2][-40:].lower()==creator[-40:].lower() for l in adu) if creator else None
            both=old_inst is not None and cur_inst is not None
            delta=(cur_inst-old_inst).total_seconds()/3600 if both else None
            def iso(t):return t.strftime('%Y-%m-%dT%H:%M:%SZ') if t else ''
            actual=dict(creation_block=str(cb),creation_tx=c['transactionHash'].lower(),adapter=c['address'].lower(),
                        adapter_version='v2+' if creator else 'v1',created_utc=iso(created),
                        event_id=str(md['event_id']),category=md['category'],market_start_time=iso(start),
                        onchain_title=title,current_title=current_title,
                        m1_title_edit=str(int(normalized(title)!=normalized(current_title))),m2_both_parse=str(int(both)),
                        onchain_instant=iso(old_inst),current_instant=iso(cur_inst),
                        onchain_parse=old_reason,current_parse=cur_reason,onchain_family=old_family or '',current_family=cur_family or '',
                        m2_deadline_edit=str(int(abs(delta)>=1)) if both else '',m2_format_only=str(int(0<abs(delta)<1)) if both else '',
                        m3_clarification=str(int(bool(adu))),n_clarifications=str(len(adu)),n_clarifications_by_creator=str(creator_count) if creator else '')
            mismatches=[dict(field=k,recorded=row[k],observed=v) for k,v in actual.items() if row[k]!=v]
            if both and abs(delta-float(row['delta_hours']))>1e-9:mismatches.append(dict(field='delta_hours',recorded=row['delta_hours'],observed=delta))
            result.update(complete=True,question_id=qid,question_id_source='negRiskRequestID' if g['negRisk'] and g['negRiskRequestID'] else 'questionID',
                          creation_events_found=len(creation),creation_log_hash=hashlib.sha256(json.dumps(c,sort_keys=True).encode()).hexdigest(),
                          creation_text_sha256=hashlib.sha256(text.encode()).hexdigest(),observed=actual,delta_hours=delta,
                          clarification_transactions=[l['transactionHash'] for l in adu],mismatches=mismatches)
        except Exception as e:
            result.update(complete=False,error=f'{type(e).__name__}: {e}')
        print(mid,result['selection'],'complete' if result['complete'] else result.get('error'),len(result.get('mismatches',[])),flush=True)
        return result
    with ThreadPoolExecutor(max_workers=2) as pool:checked=list(pool.map(check,ids))
    summary={}
    for group in ['random','supplemental-positive']:
        subset=[r for r in checked if r['selection']==group]
        summary[group]=dict(planned=len(subset),complete=sum(r['complete'] for r in subset),
                            rows_with_mismatches=sum(bool(r.get('mismatches')) for r in subset),
                            field_mismatches=sum(len(r.get('mismatches',[])) for r in subset),unknown=sum(not r['complete'] for r in subset))
    result=dict(generated_utc=utc(),chain_id=chain_id,observed_head=head,original_cutoff=CUTOFF,original_cutoff_utc=cutoff_utc,
                source=PRIMARY,selection_plan=selection,summary=summary,rows=checked)
    (HERE/'polygon_spotcheck.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--plan-only',action='store_true');p.add_argument('--run',action='store_true')
    p.add_argument('--root',type=Path);p.add_argument('--grammar',type=Path)
    p.add_argument('--evidence-dir',type=Path)
    p.add_argument('--rpc',choices=[PRIMARY,'https://poly.api.pocket.network','https://gateway.tenderly.co/public/polygon'],default=PRIMARY)
    a=p.parse_args()
    PRIMARY=a.rpc
    if a.evidence_dir:
        HERE=a.evidence_dir.resolve();HERE.mkdir(parents=True,exist_ok=True)
    if a.plan_only:plan()
    elif a.run and a.root and a.grammar:run(a.root,a.grammar)
    else:p.error('use --plan-only or --run --root PATH --grammar PATH')

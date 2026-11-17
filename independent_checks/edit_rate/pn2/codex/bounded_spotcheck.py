"""Pocket source adaptation: bounded creation lookups + batched clarification scan.

Uses the SAME committed 25 random + 14 supplemental IDs and original cutoff.
Creation is verified at the CSV's claimed block (not a global uniqueness test).
All selected question IDs share explicitly planned bounded ADU scans from earliest claimed
creation to cutoff. Every response is saved; source errors stop the run.
The existing independent decoder is then replayed on these bounded-query logs.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import shutil

import spotcheck as check

HERE=Path(__file__).resolve().parent
OUT=HERE/'pocket_bounded'
SOURCE='https://poly.api.pocket.network'
MAX_RANGE=50000


def ranges(start,end,width=MAX_RANGE):
    if width<1 or start>end:raise ValueError('invalid block range')
    return [(lo,min(lo+width-1,end)) for lo in range(start,end+1,width)]


def setup():
    OUT.mkdir(exist_ok=True)
    check.HERE=OUT;check.PRIMARY=SOURCE


def plan(creation_cache=None):
    setup();check.plan()
    path=OUT/'selection_plan.json'
    p=json.loads(path.read_text())
    with open(check.PN2/'edit_rate_sample.csv',newline='') as f:rows={r['market_id']:r for r in csv.DictReader(f)}
    selected=p['random_market_ids']+p['supplemental_positive_market_ids']
    first=min(int(rows[mid]['creation_block']) for mid in selected)
    p.update(source_reason='Explicit source adaptation after preserved range/time-limit failures; see creation and clarification source fields.',
             creation_lookup='Exact CSV-claimed block, matched questionID; no global creation uniqueness claim.',
             clarification_lookup=f'All selected questionIDs in topic1 OR; no address filter; contiguous inclusive chunks of at most {MAX_RANGE} blocks.',
             from_block=first,chunk_width=MAX_RANGE,clarification_chunks=len(ranges(first,check.CUTOFF,MAX_RANGE)),
             network_failure_policy='Stop on first failure; preserve all completed responses; do not replace a selected row.')
    if creation_cache:
        p.update(creation_cache=str(creation_cache.resolve()),creation_cache_sha256=hashlib.sha256(creation_cache.read_bytes()).hexdigest(),
                 creation_source='https://poly.api.pocket.network',clarification_source=SOURCE)
    path.write_text(json.dumps(p,indent=2)+'\n')
    print('bounded plan:',len(selected),'rows,',p['clarification_chunks'],'clarification chunks')


def run(root,grammar,creation_cache=None):
    setup()
    p=json.loads((OUT/'selection_plan.json').read_text())
    if p['chunk_width']!=MAX_RANGE or p['primary_source']!=SOURCE:raise ValueError('plan/code source or range mismatch')
    if (OUT/'polygon_rpc.jsonl').exists():raise ValueError('refuse to overwrite previous network evidence')
    ids=p['random_market_ids']+p['supplemental_positive_market_ids'];wanted=set(ids)
    with open(check.PN2/'edit_rate_sample.csv',newline='') as f:rows={r['market_id']:r for r in csv.DictReader(f) if r['market_id'] in wanted}
    if hashlib.sha256((check.PN2/'edit_rate_sample.csv').read_bytes()).hexdigest()!=p['csv_sha256']:raise ValueError('CSV changed')
    gamma={}
    with open(root/'gamma_rules.jsonl') as f:
        for line in f:
            g=json.loads(line)
            mid=str(g['market_id'])
            if mid in wanted:gamma[mid]=g['negRiskRequestID'] if g.get('negRisk') and g.get('negRiskRequestID') else g['questionID']
    qids=sorted(set(gamma.values()))
    cached_logs={};cached_headers={}
    if creation_cache:
        if hashlib.sha256(creation_cache.read_bytes()).hexdigest()!=p.get('creation_cache_sha256'):raise ValueError('creation cache changed')
        for line in creation_cache.read_text().splitlines():
            entry=json.loads(line);req=entry['request'];response=entry.get('response',{})
            if 'result' not in response:continue
            if entry['source']!='https://poly.api.pocket.network':raise ValueError('unexpected cached source')
            if req['method']=='eth_getBlockByNumber':cached_headers[req['params'][0]]=response['result']
            if req['method']=='eth_getLogs':
                q=req['params'][0]
                if q['fromBlock']==q['toBlock'] and q['topics'][0]==[check.QI2,check.QI1]:
                    cached_logs[(q['fromBlock'],q['topics'][1])]=response['result']
        if len(cached_logs)!=len(ids):raise ValueError('incomplete creation cache')
    elif p.get('creation_cache'):raise ValueError('plan requires creation cache')
    network=check.rpc
    chain=network('eth_chainId',[]);head=network('eth_blockNumber',[])
    if int(chain,16)!=137 or int(head,16)<check.CUTOFF:raise ValueError('chain/head mismatch')
    headers={hex(check.CUTOFF):network('eth_getBlockByNumber',[hex(check.CUTOFF),False])}
    all_logs=[]
    for i,mid in enumerate(ids,1):
        block=hex(int(rows[mid]['creation_block']))
        found=cached_logs[(block,gamma[mid])] if creation_cache else network('eth_getLogs',[dict(fromBlock=block,toBlock=block,topics=[[check.QI2,check.QI1],gamma[mid]])])
        if not found:raise ValueError('no creation event at claimed block for '+mid)
        all_logs.extend(found)
        if block not in headers:headers[block]=cached_headers[block] if creation_cache else network('eth_getBlockByNumber',[block,False])
        if i%5==0:print('creation rows',i,'/',len(ids),flush=True)
    spans=ranges(p['from_block'],check.CUTOFF,MAX_RANGE)
    for i,(lo,hi) in enumerate(spans,1):
        found=network('eth_getLogs',[dict(fromBlock=hex(lo),toBlock=hex(hi),topics=[check.ADU,qids])])
        all_logs.extend(found)
        if i%25==0 or i==len(spans):print('clarification chunks',i,'/',len(spans),'logs',len(all_logs),flush=True)
    # Deduplicate query overlap by canonical chain identity; duplicate qids are safe.
    unique={(l['blockHash'],l['transactionHash'],l['logIndex']):l for l in all_logs}
    logs=list(unique.values())
    (OUT/'selected_logs.json').write_text(json.dumps(logs,indent=2)+'\n')
    (OUT/'headers.json').write_text(json.dumps(headers,indent=2)+'\n')
    (OUT/'network_summary.json').write_text(json.dumps(dict(chain_id=chain,head=head,selected_rows=len(ids),selected_question_ids=len(qids),
              creation_lookup=p['creation_lookup'],clarification_chunks=len(spans),unique_logs=len(logs),
              first_block=p['from_block'],last_block=check.CUTOFF,source=SOURCE,creation_cache_sha256=p.get('creation_cache_sha256'),creation_source=p.get('creation_source',SOURCE)),indent=2)+'\n')
    def replay(method,params):
        if method=='eth_chainId':return chain
        if method=='eth_blockNumber':return head
        if method=='eth_getBlockByNumber':return headers[params[0]]
        if method=='eth_getLogs':
            query=params[0];qid=query['topics'][1].lower();allowed=set(query['topics'][0])
            return [l for l in logs if l['topics'][1].lower()==qid and l['topics'][0] in allowed]
        raise ValueError('unavailable cached request '+method)
    dest=OUT/'decoded';dest.mkdir(exist_ok=True)
    shutil.copyfile(OUT/'selection_plan.json',dest/'selection_plan.json')
    check.HERE=dest;check.rpc=replay
    check.run(root,grammar)
    result=json.loads((dest/'polygon_spotcheck.json').read_text())
    result.update(network_evidence='polygon_rpc.jsonl',creation_search_scope=p['creation_lookup'],
                  clarification_search_scope=p['clarification_lookup'],creation_source=p.get('creation_source',SOURCE),clarification_source=SOURCE,
                  source_independent_of_original_builder=SOURCE!='https://gateway.tenderly.co/public/polygon')
    (OUT/'polygon_spotcheck.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--plan-only',action='store_true');p.add_argument('--run',action='store_true')
    p.add_argument('--root',type=Path);p.add_argument('--grammar',type=Path)
    p.add_argument('--rpc',choices=['https://poly.api.pocket.network','https://gateway.tenderly.co/public/polygon'],default=SOURCE)
    p.add_argument('--max-range',type=int,default=10000)
    p.add_argument('--evidence-dir',type=Path,default=OUT)
    p.add_argument('--creation-cache',type=Path)
    a=p.parse_args()
    if not 1<=a.max_range<=1000000:p.error('--max-range must be 1..1000000')
    SOURCE=a.rpc;MAX_RANGE=a.max_range;OUT=a.evidence_dir.resolve()
    if a.plan_only:plan(a.creation_cache)
    elif a.run and a.root and a.grammar:run(a.root,a.grammar,a.creation_cache)
    else:p.error('use --plan-only or --run --root ROOT --grammar GRAMMAR')

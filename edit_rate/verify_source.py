"""PN-2 source check: verify the keyless log source against 3 known PN-1/A13 markets before the fetch.

Checks (all must hold):
  1. fetch.one() finds the creation log; parsing its text with the A13 parser (schedule_grammar_v3 on the
     description part, creation block time as year reference) reproduces F1_onchain_instants_final.json.
  2. An independent provider (Tatum public gateway, single-block query) returns the identical log (tx hash, data bytes).
  3. Wide-range completeness: one full-range AncillaryDataUpdated query on the main adapter over a fixed
     2,000,000-block range returns the same log count as 20 x 100,000-block chunk queries.
  4. Head block of the source is within 100 blocks of the independent provider's head.

usage: python verify_source.py <users_v1.3_dir> <grammar_dir> <out.json>
"""
import json
import sys

import fetch

ROOT, GDIR, OUT = sys.argv[1:4]
sys.path.insert(0, GDIR)
import datetime as dt  # noqa: E402
from schedule_grammar_v3 import parse as parse_v3  # noqa: E402

SRC, IND = fetch.RPC_DEFAULT, "https://polygon-mainnet.gateway.tatum.io"
KNOWN = ["1731345", "519576", "1068327"]
f1 = {r["market_id"]: r for r in json.load(open(f"{ROOT}/F1_onchain_instants_final.json"))}
gamma = {}
for line in open(f"{ROOT}/gamma_rules.jsonl"):
    x = json.loads(line)
    if x["market_id"] in KNOWN:
        gamma[x["market_id"]] = x
head_src = int(fetch.rpc(SRC, "eth_blockNumber", []), 16)
head_ind = int(fetch.rpc(IND, "eth_blockNumber", []), 16)
out = dict(source=SRC, independent=IND, head_source=head_src, head_independent=head_ind,
           head_ok=abs(head_src - head_ind) <= 100, markets=[])
for m in KNOWN:
    assert f1[m]["final_status"] == "ok"
    r = fetch.one(SRC, head_src, 0, m, gamma[m])
    desc = r["creation_text"].split("description:", 1)[1] if "description:" in r["creation_text"] else r["creation_text"]
    inst, why, fam = parse_v3(desc, dt.datetime.fromtimestamp(r["creation_ts"], dt.timezone.utc))
    ind = fetch.rpc(IND, "eth_getLogs", [{"fromBlock": hex(r["creation_block"]), "toBlock": hex(r["creation_block"]),
                                          "address": r["adapter"], "topics": [fetch.QI_V2, r["question_id"]]}])
    src_log = fetch.rpc(SRC, "eth_getLogs", [{"fromBlock": hex(r["creation_block"]), "toBlock": hex(r["creation_block"]),
                                              "address": r["adapter"], "topics": [fetch.QI_V2, r["question_id"]]}])
    blk = fetch.rpc(IND, "eth_getBlockByNumber", [hex(r["creation_block"]), False])
    row = dict(market_id=m, status=r["status"], creation_block=r["creation_block"], creation_tx=r["creation_tx"],
               f1_onchain_instant=f1[m]["onchain_instant"], reparsed_instant=inst.isoformat() if inst else None,
               instant_match=(inst.isoformat() if inst else None) == f1[m]["onchain_instant"],
               independent_same_log=len(ind) == 1 and ind[0]["transactionHash"] == r["creation_tx"]
               and ind[0]["data"] == src_log[0]["data"],
               block_ts_match=int(blk["timestamp"], 16) == r["creation_ts"],
               n_ancillary_updates=len(r["ancillary_updates"]))
    for u in r["ancillary_updates"]:  # each clarification log also re-read from the independent provider
        x = fetch.rpc(IND, "eth_getLogs", [{"fromBlock": hex(u["block"]), "toBlock": hex(u["block"]),
                                            "address": r["adapter"], "topics": [fetch.ADU, r["question_id"]]}])
        row.setdefault("independent_update_tx_match", []).append(any(y["transactionHash"] == u["tx"] for y in x))
    out["markets"].append(row)
    print(row, flush=True)
adapter, hi = "0x65070be91477460d8a7aeeb94ef92fe056c2f2a7", head_src - 1000
lo = hi - 2_000_000 + 1
one_call = len(fetch.rpc(SRC, "eth_getLogs", [{"fromBlock": hex(lo), "toBlock": hex(hi), "address": adapter, "topics": [fetch.ADU]}]))
chunked = sum(len(fetch.rpc(SRC, "eth_getLogs", [{"fromBlock": hex(a), "toBlock": hex(a + 99_999), "address": adapter,
                                                  "topics": [fetch.ADU]}])) for a in range(lo, hi + 1, 100_000))
out["completeness"] = dict(adapter=adapter, from_block=lo, to_block=hi, one_call=one_call, chunked_100k=chunked,
                           match=one_call == chunked)
out["all_ok"] = out["head_ok"] and out["completeness"]["match"] and all(
    x["instant_match"] and x["independent_same_log"] and x["block_ts_match"] and all(x.get("independent_update_tx_match", []))
    for x in out["markets"])
json.dump(out, open(OUT, "w"), indent=1)
print(json.dumps({k: v for k, v in out.items() if k != "markets"}, indent=1))

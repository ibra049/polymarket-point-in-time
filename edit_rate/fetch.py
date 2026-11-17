"""PN-2 step 2: fetch creation-time on-chain question text and clarification logs for the drawn markets.

Pre-registration: polysignal-ops research/public_note/PN-2_population_edit_rate_prereg.md (frozen @ 44d0be8).

Per drawn market (in draw order from draws.json):
  1. questionID from the Gamma record in gamma_rules.jsonl (fetched 2026-10-07). For NegRisk markets the UMA
     adapter question is keyed by `negRiskRequestID`, so that is used when present (same rule as the A13/PN-1
     lookup code, f1_onchain_instants.py).
  2. ONE eth_getLogs call over blocks 0..HEAD (HEAD fixed at the start of the run), filtered only by
     topic1 = questionID and topic0 in {
        QuestionInitialized v2+  (bytes32 indexed questionID, uint256 indexed requestTimestamp,
                                  address indexed creator, bytes ancillaryData, address, uint256, uint256)
                                  0xeee0897acd6893adcaf2ba5158191b3601098ab6bece35c5d57874340b64c5b7
        QuestionInitialized v1   (bytes32 indexed questionID, bytes ancillaryData, uint256, address, uint256,
                                  uint256, bool)   0x53af6c2e40505bb55a47d917203a12c8f063b6c505c11094d98ac8f772e8a031
        AncillaryDataUpdated     (bytes32 indexed questionID, address indexed owner, bytes update)  [BulletinBoard]
                                  0x0059e11815211969c0c4aaf3f498b52b6c2f2d14f286275d0862d70de22a836b
        QuestionUpdated v1       (same args as v1 QuestionInitialized; recorded only, not part of M3)
                                  0x32da4770ea275a14ae9d822d58709fe7bfb296969d46357149ed02fb4135a17b }
     Signatures are from github.com/Polymarket/uma-ctf-adapter (main: src/interfaces/IUmaCtfAdapter.sol,
     src/interfaces/IBulletinBoard.sol; v1.0.1: contracts/UmaConditionalTokensBinaryAdapter.sol).
     No address filter is applied, so every adapter version is covered; the creation log is the earliest
     QuestionInitialized log (preferring one emitted by the Gamma `resolvedBy` adapter when that is set).
  3. Creation text = UTF-8 decode of the ancillaryData bytes; creation time = the log's block timestamp.
  4. Clarification logs (M3) = AncillaryDataUpdated logs for the questionID emitted by the same adapter
     contract as the creation log, from creation to HEAD. Off-adapter logs are counted separately.
A draw with no QuestionInitialized log is "unverifiable: no creation event"; an RPC failure after retries is
"unverifiable: rpc error after retries". Reads NO outcome, close-time, trade or price columns.

Source: Tenderly's public keyless Polygon gateway (https://gateway.tenderly.co/public/polygon), which accepts
full-range eth_getLogs with a topic filter. Low concurrency (2 workers), backoff, resumable JSONL checkpoint.

usage: python fetch.py <users_v1.3_dir> <draws.json> <out.jsonl> --upto N [--rpc URL] [--workers 2]
"""
import argparse
import concurrent.futures as cf
import json
import os
import threading
import time
import subprocess

RPC_DEFAULT = "https://gateway.tenderly.co/public/polygon"
QI_V2 = "0xeee0897acd6893adcaf2ba5158191b3601098ab6bece35c5d57874340b64c5b7"
QI_V1 = "0x53af6c2e40505bb55a47d917203a12c8f063b6c505c11094d98ac8f772e8a031"
ADU = "0x0059e11815211969c0c4aaf3f498b52b6c2f2d14f286275d0862d70de22a836b"
QU_V1 = "0x32da4770ea275a14ae9d822d58709fe7bfb296969d46357149ed02fb4135a17b"
lock = threading.Lock()


def rpc(url, method, params, tries=7):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params})
    err = None
    for i in range(tries):
        out = subprocess.run(["curl", "-s", "-m", "180", "-X", "POST", "-H", "content-type: application/json",
                              "-A", "research-client", "--data", body, url], capture_output=True, text=True).stdout
        try:
            d = json.loads(out)
            if d.get("result") is not None:
                return d["result"]
            err = d.get("error")
        except json.JSONDecodeError:  # network / HTTP / empty reply: back off and retry
            err = f"non-JSON reply: {out[:120]!r}"
        time.sleep(min(120, 5 * 2 ** i))
    raise RuntimeError(f"rpc failed: {method}: {err}")


def bytes_arg(data_hex):
    """Decode the first dynamic `bytes` argument of the non-indexed data (its offset is word 0)."""
    data = bytes.fromhex(data_hex[2:])
    off = int.from_bytes(data[0:32], "big")
    n = int.from_bytes(data[off:off + 32], "big")
    return data[off + 32: off + 32 + n]


def log_ts(url, log):
    if log.get("blockTimestamp"):
        return int(log["blockTimestamp"], 16)
    return int(rpc(url, "eth_getBlockByNumber", [log["blockNumber"], False])["timestamp"], 16)


def qid_of(g):
    return g.get("negRiskRequestID") if g.get("negRisk") and g.get("negRiskRequestID") else g.get("questionID")


def one(url, head, rank, mid, g):
    qid = qid_of(g)
    rec = dict(draw_rank=rank, market_id=mid, question_id=qid, resolved_by=g.get("resolvedBy"),
               neg_risk=bool(g.get("negRisk")), head_block=head, source=url)
    try:
        logs = rpc(url, "eth_getLogs", [{"fromBlock": "0x0", "toBlock": hex(head),
                                         "topics": [[QI_V2, QI_V1, ADU, QU_V1], qid]}])
    except RuntimeError as e:
        rec["status"] = "unverifiable: rpc error after retries"
        rec["error"] = str(e)
        return rec
    logs.sort(key=lambda x: (int(x["blockNumber"], 16), int(x["logIndex"], 16)))
    qi = [x for x in logs if x["topics"][0] in (QI_V2, QI_V1)]
    rb = (g.get("resolvedBy") or "").lower()
    pick = [x for x in qi if x["address"].lower() == rb] or qi
    if not pick:
        rec["status"] = "unverifiable: no creation event"
        rec["n_logs_other"] = len(logs)
        return rec
    c = pick[0]
    adapter = c["address"].lower()
    ver = "v2+" if c["topics"][0] == QI_V2 else "v1"
    creator = ("0x" + c["topics"][3][-40:]) if ver == "v2+" else None
    adu = [x for x in logs if x["topics"][0] == ADU and x["address"].lower() == adapter
           and int(x["blockNumber"], 16) >= int(c["blockNumber"], 16)]
    adu_off = [x for x in logs if x["topics"][0] == ADU and x["address"].lower() != adapter]
    qu = [x for x in logs if x["topics"][0] == QU_V1 and x["address"].lower() == adapter]
    try:
        created = log_ts(url, c)
        adu_rows = [dict(block=int(x["blockNumber"], 16), ts=log_ts(url, x), tx=x["transactionHash"],
                         owner="0x" + x["topics"][2][-40:],
                         update=bytes_arg(x["data"]).decode("utf-8", errors="replace")) for x in adu]
    except RuntimeError as e:
        rec["status"] = "unverifiable: rpc error after retries"
        rec["error"] = str(e)
        return rec
    rec.update(status="ok", adapter=adapter, adapter_version=ver, adapter_matches_resolved_by=(adapter == rb) if rb else None,
               creation_block=int(c["blockNumber"], 16), creation_tx=c["transactionHash"], creation_ts=created,
               creator=creator, n_question_initialized=len(qi),
               creation_text=bytes_arg(c["data"]).decode("utf-8", errors="replace"),
               ancillary_updates=adu_rows,
               n_ancillary_updates_by_creator=(sum(1 for r in adu_rows if r["owner"] == creator) if creator else None),
               n_ancillary_updates_off_adapter=len(adu_off), n_v1_question_updated=len(qu))
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("draws")
    ap.add_argument("out")
    ap.add_argument("--upto", type=int, required=True, help="process draws ranked 1..UPTO")
    ap.add_argument("--rpc", default=RPC_DEFAULT)
    ap.add_argument("--workers", type=int, default=2)
    a = ap.parse_args()
    draws = json.load(open(a.draws))["draws"][: a.upto]
    want = set(draws)
    gamma = {}
    with open(os.path.join(a.root, "gamma_rules.jsonl")) as fh:
        for line in fh:
            x = json.loads(line)
            if x["market_id"] in want:
                gamma[x["market_id"]] = x
    done, head = set(), None
    if os.path.exists(a.out):
        for line in open(a.out):
            r = json.loads(line)
            head = head or r["head_block"]
            if not r["status"].startswith("unverifiable: rpc"):
                done.add(r["market_id"])
    if head is None:  # HEAD is fixed once, at the first run, and reused on resume
        head = int(rpc(a.rpc, "eth_blockNumber", []), 16)
    todo = [(i + 1, m) for i, m in enumerate(draws) if m not in done]
    print(f"head {head}; draws {len(draws)}; todo {len(todo)}", flush=True)
    with open(a.out, "a") as fh, cf.ThreadPoolExecutor(a.workers) as ex:
        futs = [ex.submit(one, a.rpc, head, rank, m, gamma[m]) for rank, m in todo]
        for k, f in enumerate(cf.as_completed(futs), 1):
            rec = f.result()
            with lock:
                fh.write(json.dumps(rec) + "\n")
                fh.flush()
            if k % 50 == 0:
                print(f"{k}/{len(todo)}", flush=True)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()

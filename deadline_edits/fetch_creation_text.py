"""Fetch the creation-time on-chain question text for the PN-1 rows (deadline edits + creation-text errors).

What it does, per market:
  1. Takes the market's questionID (or negRiskRequestID for NegRisk markets) and its resolution adapter
     address ("resolvedBy") from a Gamma record: either a local Gamma snapshot (--gamma-rules, JSONL with
     market_id, description, questionID, negRisk, negRiskRequestID, resolvedBy) or, if no snapshot is
     given, the live Gamma API (https://gamma-api.polymarket.com/markets/{id}).
  2. Finds the UMA CTF adapter `QuestionInitialized(bytes32 indexed questionID, uint256 indexed
     requestTimestamp, address indexed creator, bytes ancillaryData, address rewardToken, uint256 reward,
     uint256 proposalBond)` log for that questionID with eth_getLogs, searching block chunks outward from the
     market's start time (Users v1.3 `market_start_time`) within +-2 days. This log is written once, when the
     question is created, so its ancillary data is the creation-time question text.
  3. Decodes the ancillary data (UTF-8) and reads the creation block's timestamp.
  4. Optionally (--verify-rpc) re-reads the same log from a second, independent RPC provider using a
     one-block query, and records whether the bytes match.
  5. Re-parses both texts with `schedule_grammar_v3.parse` (the parser that produced the instants in
     F1_onchain_instants_final.json) as a consistency check: creation text with the creation block time as
     the year reference, current text with `market_start_time` as the year reference.

Reads NO outcome columns (only market_id and market_start_time from markets.parquet).
Free, keyless public Polygon RPC only. Low concurrency (one request at a time) with backoff. Resumable:
market_ids already in --out are skipped.

usage:
  python fetch_creation_text.py <users_v1.3_dir> --out creation_texts.jsonl \
      [--f1 inputs/F1_onchain_instants_final.json] [--gamma-rules inputs/gamma_rules_subset.jsonl] \
      [--rpc https://poly.api.pocket.network] [--verify-rpc https://polygon-mainnet.gateway.tatum.io]
"""
import argparse
import datetime as dt
import json
import os
import subprocess
import sys
import time

import pyarrow.parquet as pq

from schedule_grammar_v3 import parse

HERE = os.path.dirname(os.path.abspath(__file__))
QUESTION_INITIALIZED = "0xeee0897acd6893adcaf2ba5158191b3601098ab6bece35c5d57874340b64c5b7"
WINDOW_S = 2 * 86400   # search +-2 days around market_start_time (same window as the original A13 run)
CHUNK = 10_000         # blocks per eth_getLogs call (the default provider allows 10,001)
PAUSE_S = 0.1          # politeness delay between RPC calls
A13A = "excluded: on-chain deadline not after creation (creation-text error, A13a)"


def rpc(url, method, params, tries=6):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params})
    err = None
    for i in range(tries):
        time.sleep(PAUSE_S)
        out = subprocess.run(["curl", "-s", "-m", "90", "-X", "POST", "-H", "content-type: application/json",
                              "--data", body, url], capture_output=True, text=True).stdout
        try:
            d = json.loads(out)
            if "result" in d and d["result"] is not None:
                return d["result"]
            err = d.get("error")
        except json.JSONDecodeError:
            err = out[:200]
        time.sleep(2 ** i)  # backoff: 1, 2, 4, 8, 16, 32 s
    raise RuntimeError(f"rpc failed: {method}: {err}")


class Chain:
    def __init__(self, url):
        self.url, self._ts = url, {}
        self.head = int(rpc(url, "eth_blockNumber", []), 16)

    def ts(self, n):
        if n not in self._ts:
            self._ts[n] = int(rpc(self.url, "eth_getBlockByNumber", [hex(n), False])["timestamp"], 16)
        return self._ts[n]

    def block_at(self, t, lo=1, hi=None):
        """Smallest block with timestamp >= t (interpolation search, then bisection). [lo, hi] is a hint."""
        hi = self.head if hi is None else min(hi, self.head)
        if lo > 1 and self.ts(lo) >= t or hi < self.head and self.ts(hi) < t:
            lo, hi = 1, self.head  # hint does not bracket t
        for _ in range(40):
            if hi - lo <= 2_000:
                break
            t_lo, t_hi = self.ts(lo), self.ts(hi)
            if t <= t_lo:
                return lo
            g = min(max(lo + int((t - t_lo) * (hi - lo) / max(1, t_hi - t_lo)), lo + 1), hi - 1)
            if self.ts(g) < t:
                lo = g
            else:
                hi = g
        while lo < hi:
            mid = (lo + hi) // 2
            if self.ts(mid) < t:
                lo = mid + 1
            else:
                hi = mid
        return lo

    def logs(self, a, b, address, qid):
        return rpc(self.url, "eth_getLogs", [{"fromBlock": hex(a), "toBlock": hex(b), "address": address,
                                              "topics": [QUESTION_INITIALIZED, qid]}])


def decode_ancillary(data_hex):
    """First non-indexed field of QuestionInitialized is `bytes ancillaryData` (ABI: offset, length, bytes)."""
    data = bytes.fromhex(data_hex[2:])
    off = int.from_bytes(data[0:32], "big")
    n = int.from_bytes(data[off:off + 32], "big")
    return data[off + 32: off + 32 + n].decode("utf-8", errors="replace")


def creation_log(chain, qid, start_ts, address):
    """The QuestionInitialized log for qid, searching CHUNK-block ranges outward from market start."""
    centre = chain.block_at(start_ts)
    span = 200_000  # bracket hint: 2 days is ~86k blocks at Polygon's ~2 s block time
    lo = chain.block_at(start_ts - WINDOW_S, max(1, centre - span), centre)
    hi = chain.block_at(start_ts + WINDOW_S, centre, centre + span)
    k = 0
    while True:
        before = (max(centre - (k + 1) * CHUNK, lo), centre - k * CHUNK - 1)
        after = (centre + k * CHUNK, min(centre + (k + 1) * CHUNK - 1, hi))
        tried = False
        for a, b in (before, after):  # the creation event usually precedes market start
            if a <= b:
                tried = True
                found = chain.logs(a, b, address, qid)
                if found:
                    return found[0]
        if not tried:
            return None
        k += 1


def description_of(ancillary):
    """Description part of the ancillary text, as in the original A13 parse."""
    return ancillary.split("description:", 1)[1] if "description:" in ancillary else ancillary


def title_of(ancillary):
    if "title:" in ancillary:
        t = ancillary.split("title:", 1)[1]
        return t.split(", description:", 1)[0].split(" description:", 1)[0].strip()
    return None


def gamma_live(mid):
    out = subprocess.run(["curl", "-s", "-m", "30", "--retry", "3", "-A", "research-client",
                          f"https://gamma-api.polymarket.com/markets/{mid}"], capture_output=True, text=True).stdout
    m = json.loads(out)
    keep = ["description", "questionID", "negRisk", "negRiskRequestID", "resolvedBy"]
    return {"market_id": mid, "found": True, **{k: m.get(k) for k in keep},
            "snapshot": "live " + dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")}


def iso(x):
    return x.isoformat() if x is not None else None


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("data_dir", help="directory with Users v1.3 markets.parquet")
    ap.add_argument("--f1", default=os.path.join(HERE, "inputs", "F1_onchain_instants_final.json"))
    ap.add_argument("--gamma-rules", default=os.path.join(HERE, "inputs", "gamma_rules_subset.jsonl"),
                    help="Gamma snapshot JSONL; pass '' to use the live Gamma API instead")
    ap.add_argument("--rpc", default="https://poly.api.pocket.network")
    ap.add_argument("--verify-rpc", default="https://polygon-mainnet.gateway.tatum.io",
                    help="second provider for a one-block re-read of each found log; '' to skip")
    ap.add_argument("--out", default=os.path.join(HERE, "creation_texts.jsonl"))
    a = ap.parse_args()

    f1 = json.load(open(a.f1))
    targets = sorted({r["market_id"] for r in f1 if r["final_status"] == "ok" and r.get("changed")} |
                     {r["market_id"] for r in f1 if r["final_status"] == A13A}, key=int)
    start = {str(r["market_id"]): r["market_start_time"] for r in pq.read_table(
        os.path.join(a.data_dir, "markets.parquet"), columns=["market_id", "market_start_time"]).to_pylist()}
    gamma = {}
    if a.gamma_rules:
        for line in open(a.gamma_rules):
            x = json.loads(line)
            if x["market_id"] in targets:
                gamma[x["market_id"]] = dict(x, snapshot="file " + os.path.basename(a.gamma_rules))
    done = set()
    if os.path.exists(a.out):
        done = {json.loads(line)["market_id"] for line in open(a.out)}
    todo = [m for m in targets if m not in done]
    print(f"targets {len(targets)}; todo {len(todo)}", flush=True)
    chain = Chain(a.rpc)
    verify = Chain(a.verify_rpc) if a.verify_rpc else None
    with open(a.out, "a") as fh:
        for i, mid in enumerate(todo, 1):
            g = gamma.get(mid) or gamma_live(mid)
            qid = g.get("negRiskRequestID") if g.get("negRisk") and g.get("negRiskRequestID") else g.get("questionID")
            st = start[mid]
            rec = dict(market_id=mid, question_id=qid, adapter=g.get("resolvedBy"), gamma_source=g["snapshot"],
                       current_text=g.get("description"))
            try:
                log = creation_log(chain, qid, int(st.timestamp()), g["resolvedBy"]) if qid and g.get("resolvedBy") else None
            except RuntimeError as e:
                print(f"{mid}: {e}", flush=True)
                continue  # not written, so a rerun retries it
            if log is None:
                rec["status"] = "no creation event in window"
            else:
                blk = int(log["blockNumber"], 16)
                created = dt.datetime.fromtimestamp(chain.ts(blk), dt.timezone.utc)
                anc = decode_ancillary(log["data"])
                rec.update(status="ok", block=blk, tx_hash=log["transactionHash"], creation_block_time=iso(created),
                           creation_title=title_of(anc), creation_ancillary=anc)
                if verify:
                    try:
                        again = verify.logs(blk, blk, g["resolvedBy"], qid)
                        rec["verify_same_bytes"] = bool(again) and again[0]["data"] == log["data"] \
                            and again[0]["transactionHash"] == log["transactionHash"]
                    except RuntimeError:
                        rec["verify_same_bytes"] = None
                oc, why, fam = parse(description_of(anc), created)
                cur, why2, fam2 = parse(g.get("description"), st)
                rec.update(reparse_creation_instant=iso(oc), reparse_creation_reason=why, reparse_creation_family=fam,
                           reparse_current_instant=iso(cur), reparse_current_reason=why2, reparse_current_family=fam2)
            fh.write(json.dumps(rec) + "\n")
            fh.flush()
            print(f"{i}/{len(todo)} {mid} {rec['status']}", flush=True)
    print("DONE", flush=True)


if __name__ == "__main__":
    sys.exit(main())

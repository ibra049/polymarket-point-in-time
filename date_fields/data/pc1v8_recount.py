"""PC-1 v8 (A17 grammar v5): outcome-free recount, K2 v4->v5 transitions, exclusion-only assertion, K3 draw.

Reads markets.parquet columns market_id, event_id, market_start_time, category only (no outcome_yes, no trades).
The K3 table has no Claude column; Claude's marks go to PC-1v8_claude_marks.md (A17: Codex must not see them).
usage: python pc1v8_recount.py <users_v1.3_dir> <gamma_rules.jsonl> <out_dir>
"""
import collections
import datetime as dt
import hashlib
import json
import pathlib
import random
import re
import sys

import pyarrow.parquet as pq

import schedule_grammar_v4 as v4
from schedule_grammar_v5 import A16_MASK, ET, parse_full, sentences

HERE = pathlib.Path(__file__).parent
CUTOFF = dt.datetime(2026, 2, 27, 23, 59, 59, tzinfo=dt.timezone.utc)
DATEISH = re.compile(r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+\d{1,2}\b|\d{1,2}:\d{2}", re.I)


def iso(t):
    return t.strftime("%Y-%m-%dT%H:%M:%SZ") if t else None


def band(days):
    return "<1d" if days < 1 else "1-7d" if days < 7 else "7-60d" if days < 60 else ">=60d"


def share(counter):
    n = sum(counter.values())
    return {k: [v, round(100 * v / n, 2)] for k, v in counter.most_common()}


def main():
    root, rules_path, out_dir = sys.argv[1:4]
    meta = {str(r["market_id"]): r for r in pq.read_table(
        f"{root}/markets.parquet", columns=["market_id", "event_id", "market_start_time", "category"]).to_pylist()}
    rules = {}
    for line in open(rules_path):
        x = json.loads(line)
        rules[x["market_id"]] = x.get("description") if x.get("found") else None
    reasons, fams, trans = collections.Counter(), collections.Counter(), collections.Counter()
    rows, violations = {}, []
    with open(f"{root}/v5_instants.jsonl", "w") as fh:
        for mid, m in meta.items():
            desc, start = rules.get(mid), m["market_start_time"]
            if desc is None or start is None:
                reasons["no_record_or_start"] += 1
                continue
            r5, r4 = parse_full(desc, start), v4.parse_full(desc, start)
            k4 = r4["family"] if r4["reason"] == "ok" else r4["reason"]
            k5 = r5["family"] if r5["reason"] == "ok" else r5["reason"]
            reasons[r5["reason"]] += 1
            if r5["reason"] == "ok":
                fams[r5["family"]] += 1
            if (k4, r4["instant"]) != (k5, r5["instant"]):
                trans[f"{k4} -> {k5}"] += 1
                if r5["reason"] == "ok":  # exclusion only: v5 may only remove, never add or move
                    violations.append(mid)
            primary = r5["primary"] and mid not in A16_MASK
            rows[mid] = dict(k4=k4, i4=iso(r4["instant"]), r=r5, primary=primary)
            fh.write(json.dumps(dict(market_id=mid, status=r5["reason"], family=r5["family"], primary=primary,
                                     a16_masked=mid in A16_MASK, instant=iso(r5["instant"]), v4=k4,
                                     trace=r5["trace"])) + "\n")
    prim = {i: x for i, x in rows.items() if x["primary"]}
    mature = {i: x for i, x in prim.items() if x["r"]["instant"] <= CUTOFF}
    ev_cat = {}
    for i in mature:
        ev_cat.setdefault(meta[i]["event_id"], meta[i]["category"] or "None")
    long = {i: x for i, x in mature.items()
            if (x["r"]["instant"] - meta[i]["market_start_time"]).days >= 60}
    pop = dict(
        parser_sha256={f: hashlib.sha256((HERE / f).read_bytes()).hexdigest()
                       for f in ("schedule_grammar_v3.py", "schedule_grammar_v4.py", "schedule_grammar_v5.py")},
        markets_in_dataset=len(meta), parse_outcomes=dict(reasons.most_common()), families_v5=dict(fams.most_common()),
        exclusion_only_violations=violations, a16_masked=sorted(A16_MASK),
        primary=dict(markets=len(prim), events=len({meta[i]["event_id"] for i in prim}),
                     by_family=dict(collections.Counter(x["r"]["family"] for x in prim.values())),
                     mature_markets=len(mature), mature_events=len(ev_cat),
                     mature_by_family=dict(collections.Counter(x["r"]["family"] for x in mature.values())),
                     mature_category_markets=share(collections.Counter(meta[i]["category"] or "None" for i in mature)),
                     mature_category_events=share(collections.Counter(ev_cat.values())),
                     mature_horizon_from_creation=dict(collections.Counter(
                         band((x["r"]["instant"] - meta[i]["market_start_time"]).total_seconds() / 86400)
                         for i, x in mature.items())),
                     mature_ge60d_by_family=dict(collections.Counter(x["r"]["family"] for x in long.values())),
                     mature_ge60d_events=len({meta[i]["event_id"] for i in long})),
        option_B_timed_F4_only=dict(markets=sum(x["r"]["family"] == "F4" for x in prim.values()),
                                    mature_markets=sum(x["r"]["family"] == "F4" for x in mature.values()),
                                    mature_events=len({meta[i]["event_id"] for i, x in mature.items()
                                                       if x["r"]["family"] == "F4"})),
        K2_transitions_v4_to_v5=dict(trans.most_common()), mature_cutoff=iso(CUTOFF))
    json.dump(pop, open(f"{out_dir}/PC-1v8_population.json", "w"), indent=1)
    print(json.dumps({k: pop[k] for k in ("parse_outcomes", "K2_transitions_v4_to_v5", "exclusion_only_violations")}))

    rng = random.Random(20261014)
    pick = []
    for fam, n in (("F2", 15), ("F3", 10), ("F4", 15)):
        ids = sorted((i for i, x in prim.items() if x["r"]["family"] == fam), key=int)
        pick += rng.sample(ids, min(n, len(ids)))
    clean = lambda s: s.replace("|", "/").replace("\n", " ")
    with open(f"{out_dir}/PC-1v8_semantic_audit.md", "w") as fh:
        fh.write("# PC-1 v8 semantic audit (A17 K3): 40 random v5 primaries after the A16 mask (F2 15, F3 10, timed F4 15), "
                 "seed 20261014\n\nPass = zero wrong from Claude AND Codex, marked independently. This file has no "
                 "Claude column; Claude's marks are in PC-1v8_claude_marks.md (Codex: do not open it before saving "
                 "your marks). Correct = the instant (to the second) and family are right for this market. "
                 "'accepted' = matched clause spans v5 used; 'text' = date-bearing sentences (<=1500 chars).\n\n"
                 "| # | market | family | instant UTC / ET | accepted | text |\n|---|---|---|---|---|---|\n")
        for k, mid in enumerate(pick, 1):
            x, desc = rows[mid], rules[mid]
            inst = x["r"]["instant"]
            acc = " ‖ ".join(t["text"] for t in x["r"]["trace"])
            text = " ‖ ".join(desc[a:b].strip() for a, b in sentences(desc) if DATEISH.search(desc[a:b]))[:1500]
            fh.write(f"| {k} | {mid} | {x['r']['family']} | {iso(inst)} / "
                     f"{inst.astimezone(ET).strftime('%Y-%m-%d %H:%M:%S %Z')} | {clean(acc)} | {clean(text)} |\n")
    print("audit written", flush=True)


if __name__ == "__main__":
    main()

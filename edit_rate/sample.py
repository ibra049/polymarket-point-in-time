"""PN-2 step 1: the deterministic sample draw (pre-registration frozen at polysignal-ops commit 44d0be8).

Population: every market in Users v1.3 markets.parquet (@ 91ddb961) that has a Gamma record in
gamma_rules.jsonl (fetched 2026-10-07, `found` true) and a non-empty `questionID`.
Draw: the population is sorted by market_id (numeric, the parquet type is int64), then
random.Random(20261111).sample(population, 2000) gives the draw order. Draws 1..1000 are the primary
sample; draws 1001..2000 are replacements, used strictly in order for unverifiable draws.

Reads only market_id, event_id, category, question, market_start_time from markets.parquet
(no outcome, close-time, trade or price columns).

usage: python sample.py <users_v1.3_dir> <out_draws.json>
"""
import hashlib
import json
import random
import sys

import pyarrow.parquet as pq

SEED, MAX_DRAWS = 20261111, 2000
COLS = ["market_id", "event_id", "category", "question", "market_start_time"]


def load(root):
    meta = {str(r["market_id"]): r for r in pq.read_table(f"{root}/markets.parquet", columns=COLS).to_pylist()}
    gamma = {}
    with open(f"{root}/gamma_rules.jsonl") as fh:
        for line in fh:
            x = json.loads(line)
            if x.get("found") is True and x.get("questionID"):
                gamma[str(x["market_id"])] = x
    return meta, gamma


def main():
    root, out = sys.argv[1], sys.argv[2]
    meta, gamma = load(root)
    pop = sorted((int(m) for m in meta if m in gamma))
    digest = hashlib.sha256("\n".join(str(m) for m in pop).encode()).hexdigest()
    order = random.Random(SEED).sample(pop, MAX_DRAWS)
    with open(f"{root}/markets.parquet", "rb") as f:
        mk_sha = hashlib.sha256(f.read()).hexdigest()
    h = hashlib.sha256()
    with open(f"{root}/gamma_rules.jsonl", "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    res = dict(seed=SEED, max_draws=MAX_DRAWS, n_markets_parquet=len(meta), n_gamma_with_qid=len(gamma),
               population_size=len(pop), population_sha256_sorted_ids=digest,
               population_hash_rule='sha256 of "\\n".join(str(market_id) for market_id in sorted numeric ids)',
               input_sha256={"markets.parquet": mk_sha, "gamma_rules.jsonl": h.hexdigest()},
               draws=[str(m) for m in order])
    json.dump(res, open(out, "w"), indent=1)
    print(json.dumps({k: v for k, v in res.items() if k != "draws"}, indent=1))
    print("first 5 draws:", res["draws"][:5])


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Independent Job C, written from arXiv 2609.12878 §§2.2–2.4, 5.2.

Only trades, predictions and user_features are read. No author implementation
is imported. Inputs are opened as Parquet files, never modified. Output paths
must be inside this checkout. Missing lookup evidence is counted, not invented.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import platform
import resource
import subprocess
import sys
import time

import numpy as np
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

COLUMNS = ["timestamp", "market_id", "price", "quantity", "maker_address",
           "taker_address", "taker_bought", "winner"]
EXPECTED_TYPES = {"timestamp": pa.timestamp("ns", tz="UTC"),
                  "market_id": pa.large_string(), "price": pa.float64(),
                  "quantity": pa.float64(), "maker_address": pa.large_string(),
                  "taker_address": pa.large_string(), "taker_bought": pa.bool_(),
                  "winner": pa.bool_()}
STAGES = ["observed", "complete_distinct", "valid_price_quantity",
          "two_outcome", "buyer_hhi", "return_sample"]


def truth(array):
    return pc.fill_null(array, False).to_numpy(zero_copy_only=False)


def peak_bytes():
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(value if sys.platform == "darwin" else value * 1024)


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def verified_bytes(path, expected_sha256, expected_size=None):
    """Decode only immutable bytes that match the named source manifest.

    mtime changes alone are not content identity. A concurrent mutation that
    affects these bytes cannot pass the expected SHA-256 check.
    """
    if path.stat().st_size > 1024**3:
        raise MemoryError(f"compressed file exceeds 1 GiB input bound: {path}")
    content = path.read_bytes()
    actual = hashlib.sha256(content).hexdigest()
    if actual != expected_sha256 or (expected_size is not None and len(content) != expected_size):
        raise ValueError(f"manifest content mismatch: {path}; bytes={len(content)}, sha256={actual}")
    return content


def source_manifests(root):
    trades = {}
    for line in (root / "trades_manifest.tsv").read_text().splitlines():
        name, size, digest = line.split("\t")
        if name in trades:
            raise ValueError(f"duplicate manifest path: {name}")
        trades[name] = (int(size), digest)
    auxiliary = {}
    for line in (root / "SHA256SUMS").read_text().splitlines():
        digest, name = line.split()
        if name in ["predictions.parquet", "user_features.parquet"]:
            auxiliary[name] = digest
    if set(auxiliary) != {"predictions.parquet", "user_features.parquet"}:
        raise ValueError("missing auxiliary manifest hash")
    return trades, auxiliary


def load_lookups(root, expected_auxiliary):
    p_bytes = verified_bytes(root / "predictions.parquet", expected_auxiliary["predictions.parquet"])
    p = pq.read_table(pa.BufferReader(p_bytes),
                      columns=["market_id", "n_outcomes"])
    u_bytes = verified_bytes(root / "user_features.parquet", expected_auxiliary["user_features.parquet"])
    u = pq.read_table(pa.BufferReader(u_bytes),
                      columns=["user_address", "counterparty_hhi"])
    if u["user_address"].null_count or len(pc.unique(u["user_address"])) != len(u):
        raise ValueError("user_address lookup keys must be unique and non-null")
    if p["market_id"].null_count or p["n_outcomes"].null_count:
        raise ValueError("unknown outcome-count metadata")
    if u["counterparty_hhi"].null_count:
        raise ValueError("unknown buyer HHI metadata")
    if not truth(pc.is_finite(u["counterparty_hhi"])).all():
        raise ValueError("nonfinite buyer HHI metadata")
    # The paper excludes markets with >2 tokens; it does not exclude a trade
    # merely because its seller has high HHI. Keys stay strings as in trades.
    multi = pc.cast(pc.unique(p.filter(pc.greater(p["n_outcomes"], 2))["market_id"]),
                    pa.large_string())
    markets = pc.cast(pc.unique(p["market_id"]), pa.large_string())
    high = u.filter(pc.greater_equal(u["counterparty_hhi"], 0.5))["user_address"].combine_chunks()
    known = u["user_address"].combine_chunks()
    return {"multi": multi, "markets": markets, "high": high, "known": known}, {
        "prediction_rows": len(p), "markets": len(markets),
        "multi_outcome_markets": len(multi), "wallets": len(u),
        "high_hhi_wallets": len(high), "null_hhi_wallets": 0,
    }


def measure_batch(batch, lookups):
    c = {name: batch.column(name) for name in COLUMNS}
    n = batch.num_rows
    price = c["price"].to_numpy(zero_copy_only=False)
    quantity = c["quantity"].to_numpy(zero_copy_only=False)
    action_known = truth(pc.is_valid(c["taker_bought"]))
    taker = truth(c["taker_bought"])
    buyer = pc.if_else(c["taker_bought"], c["taker_address"], c["maker_address"])
    complete = action_known & truth(pc.not_equal(c["maker_address"], c["taker_address"]))
    complete &= truth(pc.is_valid(c["price"])) & truth(pc.is_valid(c["quantity"]))
    valid = complete & np.isfinite(price) & np.isfinite(quantity)
    valid &= (price > 0) & (price <= 1) & (quantity > 0)
    multi = truth(pc.is_in(c["market_id"], value_set=lookups["multi"]))
    market_known = truth(pc.is_in(c["market_id"], value_set=lookups["markets"]))
    binary = valid & ~multi
    high = truth(pc.is_in(buyer, value_set=lookups["high"]))
    buyer_known = truth(pc.is_in(buyer, value_set=lookups["known"]))
    analysis = binary & ~high
    resolved = truth(pc.is_valid(c["winner"]))
    returns = analysis & resolved
    masks = [np.ones(n, dtype=bool), complete, valid, binary, analysis, returns]
    stages = {name: int(mask.sum()) for name, mask in zip(STAGES, masks)}
    diagnostics = {
        "valid_unknown_market": int((valid & ~market_known).sum()),
        "binary_unknown_buyer_hhi": int((binary & ~buyer_known).sum()),
        "null_action": int((~action_known).sum()),
        "null_timestamp": c["timestamp"].null_count,
        "null_market": c["market_id"].null_count,
        "null_maker": c["maker_address"].null_count,
        "null_taker": c["taker_address"].null_count,
        "null_price": c["price"].null_count,
        "null_quantity": c["quantity"].null_count,
        "nonfinite_nonnull_price": int((~np.isfinite(price) & truth(pc.is_valid(c["price"]))).sum()),
        "nonfinite_nonnull_quantity": int((~np.isfinite(quantity) & truth(pc.is_valid(c["quantity"]))).sum()),
    }
    favourites = returns & (price >= 0.90)
    winning = truth(c["winner"])
    groups = {}
    for name, role in [("taker", taker), ("maker", ~taker)]:
        selected = favourites & role
        cost = price[selected] * quantity[selected]
        payoff = winning[selected].astype(np.float64) * quantity[selected]
        groups[name] = {"purchases": int(selected.sum()),
                        "cost": float(np.sum(cost, dtype=np.float64)),
                        "payoff": float(np.sum(payoff, dtype=np.float64)),
                        "gain": float(np.sum(payoff - cost, dtype=np.float64))}
    times = pc.min_max(c["timestamp"]).as_py()
    return stages, diagnostics, groups, times


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timing", type=Path, required=True)
    parser.add_argument("--batch-size", type=int, default=262144)
    args = parser.parse_args()
    checkout = Path(__file__).resolve().parents[4]
    for path in [args.output, args.timing]:
        if not path.resolve().is_relative_to(checkout):
            parser.error("outputs must be inside this checkout")
    if args.batch_size < 1:
        parser.error("batch size must be positive")
    started = datetime.now(timezone.utc).isoformat()
    start = time.perf_counter()
    cpu_start = time.process_time()
    root = args.data.resolve()
    files = sorted(root.glob("trades/year=*/month=*/day=*/*.parquet"))
    if not files:
        raise ValueError("no trade files")
    pa.set_cpu_count(2)
    pa.set_io_thread_count(2)
    trade_manifest, aux_manifest = source_manifests(root)
    if {str(p.relative_to(root)) for p in files} != set(trade_manifest):
        raise ValueError("trade file set differs from local manifest")
    lookups, auxiliary = load_lookups(root, aux_manifest)
    stage_totals, diagnostic_totals = Counter(), Counter()
    records = []
    group_parts = {role: {k: [] for k in ["purchases", "cost", "payoff", "gain"]}
                   for role in ["taker", "maker"]}
    time_min, time_max = None, None
    with args.timing.open("w") as timing:
        for i, path in enumerate(files, 1):
            tick = time.perf_counter()
            stat = path.stat()
            expected_size, expected_sha = trade_manifest[str(path.relative_to(root))]
            content = verified_bytes(path, expected_sha, expected_size)
            pf = pq.ParquetFile(pa.BufferReader(content))
            for name, expected in EXPECTED_TYPES.items():
                if pf.schema_arrow.field(name).type != expected:
                    raise TypeError(f"unexpected type for {path}:{name}")
            file_stages = Counter()
            for batch in pf.iter_batches(batch_size=args.batch_size, columns=COLUMNS,
                                         use_threads=False):
                stages, diagnostics, groups, times = measure_batch(batch, lookups)
                stage_totals.update(stages)
                file_stages.update(stages)
                diagnostic_totals.update(diagnostics)
                for role, values in groups.items():
                    for k, v in values.items():
                        group_parts[role][k].append(v)
                if times["min"] is not None:
                    time_min = times["min"] if time_min is None else min(time_min, times["min"])
                    time_max = times["max"] if time_max is None else max(time_max, times["max"])
                if peak_bytes() >= 8 * 1024**3:
                    raise MemoryError("8 GiB memory bound reached")
            if file_stages["observed"] != pf.metadata.num_rows:
                raise ValueError(f"footer/decoded count mismatch: {path}")
            after = path.stat()
            record = {"path": str(path.relative_to(root)), "bytes": len(content),
                      "sha256": expected_sha, "mtime_ns_before": stat.st_mtime_ns,
                      "mtime_ns_after": after.st_mtime_ns,
                      "metadata_changed_during_read": (stat.st_size, stat.st_mtime_ns) != (after.st_size, after.st_mtime_ns),
                      "footer_rows": pf.metadata.num_rows,
                      "stages": dict(file_stages)}
            records.append(record)
            log = {"file": i, "files": len(files), "path": record["path"],
                   "rows": file_stages["observed"], "file_wall_seconds": time.perf_counter()-tick,
                   "elapsed_seconds": time.perf_counter()-start, "peak_rss_bytes": peak_bytes()}
            timing.write(json.dumps(log, sort_keys=True) + "\n")
            timing.flush()
            if i % 25 == 0 or i == len(files):
                print(json.dumps(log, sort_keys=True), flush=True)
    sums = {}
    for role, parts in group_parts.items():
        sums[role] = {k: sum(v) if k == "purchases" else math.fsum(v)
                      for k, v in parts.items()}
        sums[role]["return_percent"] = 100 * sums[role]["gain"] / sums[role]["cost"]
    gap = diagnostic_totals["valid_unknown_market"] or diagnostic_totals["binary_unknown_buyer_hhi"]
    result = {
        "status": "INCONCLUSIVE" if gap else "PROMOTE",
        "status_scope": "pipeline replication only; PROMOTE means proceed to independent comparison",
        "started_utc": started, "finished_utc": datetime.now(timezone.utc).isoformat(),
        "code_sha256": sha256(Path(__file__)),
        "code_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=checkout, text=True).strip(),
        "inputs": {"root": str(root), "hf_commit_declared_by_handoff": "91ddb961",
                   "hf_commit_independently_authenticated": False,
                   "trade_files": len(files), "trade_bytes": sum(r["bytes"] for r in records),
                   "trade_content_sha256_rechecked": True,
                   "local_manifests": {name: sha256(root/name)
                                       for name in ["trades_manifest.tsv", "SHA256SUMS"]},
                   "auxiliary": {name: {"bytes": (root/name).stat().st_size,
                                          "sha256": aux_manifest[name]}
                                 for name in ["predictions.parquet", "user_features.parquet"]}},
        "definitions": {"source": "https://arxiv.org/html/2609.12878v1",
                        "sample": "complete distinct maker/taker and direction, finite q>0 and 0<p<=1, exclude >2 outcomes and buyer HHI>=0.5; nonnull trade winner for returns",
                        "unknown_lookup_policy": "retain and count; any such rows make replication INCONCLUSIVE",
                        "favorite": "price >= float64(0.90), including 1.0",
                        "R2": "100*sum(q*(winner-price))/sum(q*price), taker_bought=true",
                        "R2m": "same, taker_bought=false",
                        "fees_rewards_annualization": "none"},
        "environment": {"python": sys.version, "numpy": np.__version__, "pyarrow": pa.__version__,
                        "platform": platform.platform(), "batch_size": args.batch_size,
                        "validated_trade_types": {k: str(v) for k, v in EXPECTED_TYPES.items()}},
        "auxiliary_counts": auxiliary, "stages": dict(stage_totals),
        "diagnostics": dict(diagnostic_totals), "favorites": sums,
        "trade_time_min_utc": time_min.isoformat(), "trade_time_max_utc": time_max.isoformat(),
        "timing": {"wall_seconds": time.perf_counter()-start,
                   "cpu_seconds": time.process_time()-cpu_start, "peak_rss_bytes": peak_bytes()},
        "file_records": records,
    }
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(json.dumps({k: result[k] for k in ["status", "stages", "favorites", "diagnostics", "timing"]}, indent=2), flush=True)


if __name__ == "__main__":
    main()

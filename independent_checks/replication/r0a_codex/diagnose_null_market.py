#!/usr/bin/env python3
"""Post-comparison diagnostic only; do not alter first-pass numbers or rules."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import time

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

from recompute import source_manifests, verified_bytes, truth, peak_bytes, sha256


def classify(rows, predictions, high_hhi):
    indices = pc.index_in(rows["prediction_id"], value_set=predictions["prediction_id"])
    matched = pc.is_valid(indices)
    buyer = pc.if_else(rows["taker_bought"], rows["taker_address"], rows["maker_address"])
    high = pc.is_in(buyer, value_set=high_hhi)
    winner_known = pc.is_valid(rows["winner"])
    return {
        "rows": len(rows),
        "null_prediction_id": rows["prediction_id"].null_count,
        "matched_prediction_id": int(truth(matched).sum()),
        "unmatched_prediction_id": int((~truth(matched)).sum()),
        "known_payoff_rows": int(truth(winner_known).sum()),
        "high_hhi_buyer_rows": int(truth(high).sum()),
        "after_hhi_rows": int((~truth(high)).sum()),
        "after_hhi_known_payoff_rows": int((~truth(high) & truth(winner_known)).sum()),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    checkout = Path(__file__).resolve().parents[4]
    if not args.output.resolve().is_relative_to(checkout):
        parser.error("output must be inside checkout")
    start = time.perf_counter()
    root = args.data.resolve()
    manifest, auxiliary = source_manifests(root)
    pred = pq.read_table(pa.BufferReader(verified_bytes(root/"predictions.parquet", auxiliary["predictions.parquet"])),
                         columns=["prediction_id", "n_outcomes"])
    users = pq.read_table(pa.BufferReader(verified_bytes(root/"user_features.parquet", auxiliary["user_features.parquet"])),
                          columns=["user_address", "counterparty_hhi"])
    high = users.filter(pc.greater_equal(users["counterparty_hhi"], .5))["user_address"]
    totals = Counter()
    records = []
    unknown_tokens = []
    footer_files, candidate_files, candidate_bytes = 0, 0, 0
    for relative, (size, digest) in sorted(manifest.items()):
        path = root/relative
        pf = pq.ParquetFile(path)
        footer_files += 1
        column = pf.schema_arrow.get_field_index("market_id")
        nulls = []
        for group in range(pf.metadata.num_row_groups):
            stats = pf.metadata.row_group(group).column(column).statistics
            nulls.append(None if stats is None else stats.null_count)
        if nulls and all(n == 0 for n in nulls):
            continue
        candidate_files += 1
        candidate_bytes += size
        table = pq.read_table(pa.BufferReader(verified_bytes(path, digest, size)),
                              columns=["market_id", "prediction_id", "winner", "maker_address",
                                       "taker_address", "taker_bought", "price", "quantity"])
        rows = table.filter(pc.is_null(table["market_id"]))
        if not len(rows):
            continue
        counts = classify(rows, pred, high)
        totals.update(counts)
        ids = pc.unique(rows["prediction_id"])
        unmatched = pc.filter(ids, pc.invert(pc.is_in(ids, value_set=pred["prediction_id"])))
        unknown_tokens.extend(unmatched.to_pylist())
        records.append({"path": relative, "sha256": digest, **counts})
        if peak_bytes() >= 8 * 1024**3:
            raise MemoryError("8 GiB bound reached")
    result = {
        "status": "INCONCLUSIVE",
        "scope": "diagnose the preserved paper Table 1 funnel mismatch; no first-pass changes",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "script_sha256": sha256(Path(__file__)),
        "totals": dict(totals), "unique_unmatched_prediction_ids": len(set(unknown_tokens)),
        "unmatched_prediction_ids": sorted(set(unknown_tokens)),
        "footer_files_checked": footer_files, "candidate_files_decoded": candidate_files,
        "candidate_bytes_verified": candidate_bytes,
        "wall_seconds": time.perf_counter()-start, "peak_rss_bytes": peak_bytes(),
        "files_with_null_market": records,
        "limits": "No metadata is invented for unmatched tokens; their market outcome count remains unknown. No missing-return or missing-transaction coverage is inferred.",
    }
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({k:v for k,v in result.items() if k not in ["unmatched_prediction_ids", "files_with_null_market"]}, indent=2))


if __name__ == "__main__":
    main()

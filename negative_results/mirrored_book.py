"""H-002 (single-binary form): can YES ask + NO ask sit below $1 on Polymarket's CLOB?

Re-derives, from the public extract, the RC000 probe: on every snapshot where the YES
and NO order books were fetched separately from the CLOB API, check
  (1) top of book: NO best ask == 1 - YES best bid, and min(YES ask + NO ask);
  (2) full ladder: YES bids at (p, s) are exactly NO asks at (1 - p, s), and
      YES asks at (p, s) are exactly NO bids at (1 - p, s), using the exchange's
      decimal strings (no float rounding).
Read-only, standard library only.

usage: python mirrored_book.py data/snapshots.csv.gz > mirrored_book_result.json
"""
import collections
import csv
import gzip
import json
import statistics
import sys
from decimal import Decimal

ONE = Decimal(1)


def ladder(s):
    return [(Decimal(p), Decimal(q)) for p, q in json.loads(s)]


def mirror(levels):
    return sorted((ONE - p, q) for p, q in levels)


rows = []
for r in csv.DictReader(gzip.open(sys.argv[1], "rt", newline="")):
    # Sample: fetch_status ok and a NO book fetched separately (no_best_ask present).
    if r["fetch_status"] == "ok" and r["no_best_ask"] != "":
        rows.append(r)

n = len(rows)
top_equal = 0
sums = []
yes_levels = no_levels = 0
mirror_ok = 0
mismatch_dt = collections.Counter()
mismatch_crossed = 0
mismatch_examples = []
for r in rows:
    yb, ya = float(r["best_bid"]), float(r["best_ask"])
    na = float(r["no_best_ask"])
    if abs(na - (1 - yb)) < 1e-9:
        top_equal += 1
    sums.append(ya + na)

    Yb, Ya, Nb, Na = (ladder(r[k]) for k in ("yes_bids", "yes_asks", "no_bids", "no_asks"))
    yes_levels += len(Yb) + len(Ya)
    no_levels += len(Nb) + len(Na)
    if mirror(Yb) == sorted(Na) and mirror(Ya) == sorted(Nb):
        mirror_ok += 1
    else:
        dt = int(r["no_book_ts_ms"]) - int(r["yes_book_ts_ms"])
        mismatch_dt[dt] += 1
        # Crossed sum inside the mismatched pair, from the fetched ladders themselves.
        best_yes_ask = min(p for p, _ in Ya) if Ya else None
        best_no_ask = min(p for p, _ in Na) if Na else None
        if best_yes_ask is not None and best_no_ask is not None and best_yes_ask + best_no_ask < ONE:
            mismatch_crossed += 1
        if len(mismatch_examples) < 5:
            mismatch_examples.append(dict(market_id=r["market_id"], captured_at=r["captured_at"],
                                          book_ts_gap_ms=dt))

result = dict(
    sample=dict(
        rows=n,
        markets=len({r["market_id"] for r in rows}),
        events=len({r["event_id"] for r in rows if r["event_id"]}),
        first_captured_at=min(r["captured_at"] for r in rows),
        last_captured_at=max(r["captured_at"] for r in rows),
        scheduled_slots=sorted({r["scheduled_slot"] or "null" for r in rows}),
    ),
    top_of_book=dict(
        rows_no_ask_eq_1_minus_yes_bid=top_equal,
        rows_yes_ask_plus_no_ask_below_1=sum(1 for s in sums if s < 1 - 1e-9),
        min_yes_ask_plus_no_ask=round(min(sums), 6),
        mean_yes_ask_plus_no_ask=round(statistics.fmean(sums), 6),
    ),
    full_ladder=dict(
        pairs_mirrored_exactly=mirror_ok,
        pairs_not_mirrored=n - mirror_ok,
        yes_levels_total=yes_levels,
        no_levels_total=no_levels,
        mismatch_book_timestamp_gap_ms=dict(sorted(mismatch_dt.items())),
        mismatches_with_crossed_sum=mismatch_crossed,
        mismatch_examples=mismatch_examples,
    ),
)
json.dump(result, sys.stdout, indent=1)
print()

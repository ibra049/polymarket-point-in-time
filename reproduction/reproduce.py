"""Reproduce the published aggregates of arXiv 2609.12878 from Polymarket Users v1.3.

usage: python reproduce.py <users_v1.3_dir> <out.json>

<users_v1.3_dir> must contain predictions.parquet, user_features.parquet and
trades/year=*/month=*/day=*/data.parquet from Hugging Face vgregoire/polymarket-users
at commit 91ddb961b090de18fd79e79edd8fa15f36ca11b9.

Outputs ONLY the pre-registered checks (see checks.json): no slicing, breakdowns, or saved intermediates.

Paper conventions (arXiv 2609.12878, section 2 / Tables 1, 4, 6, 16): one purchase per trade row, attributed to
the buyer (taker if taker_bought, else maker). Filters, cumulative: complete fields; distinct buyer and seller;
0 < price <= 1 and quantity > 0; two-outcome markets; buyer counterparty HHI < 0.5 (user_features, lifetime);
resolved by 2026-03-29 (winner known). Return = (payout - cost) / cost, payout = quantity * winner.
Pooled: sums over purchases. Equal child: per-market pooled return, averaged over markets equally.
Taker purchases = rows with taker_bought (paper: "accepted seller's offer"); maker purchases = not taker_bought
("posted purchase offer").

The computation is identical to the script run on 2026-10-08 and re-run on 2026-11-12 (UTC); only this docstring, one
comment (the original said "222 tokens"; this release has 173 tokens in those 39 markets) and the failure label
of the verdict string differ.
"""
import collections
import glob
import json
import sys

import numpy as np
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

COLS = ["trade_id", "market_id", "prediction_id", "winner", "price", "quantity", "maker_address", "taker_address",
        "taker_bought"]
TOL_PP = 0.01


def main():
    root, out = sys.argv[1], sys.argv[2]
    pred = pq.read_table(f"{root}/predictions.parquet", columns=["prediction_id", "n_outcomes"])
    multi = pc.filter(pred, pc.not_equal(pred["n_outcomes"], 2))["prediction_id"]  # 173 tokens in 39 markets
    uf = pq.read_table(f"{root}/user_features.parquet", columns=["user_address", "counterparty_hhi"])
    high_hhi = pc.filter(uf, pc.greater_equal(uf["counterparty_hhi"], 0.5))["user_address"]
    n = collections.Counter()
    amt = collections.Counter()
    pooled = collections.defaultdict(lambda: np.zeros(2))         # key -> [cost, pnl]
    per_market = {"fav": collections.defaultdict(lambda: np.zeros(2)),
                  "long": collections.defaultdict(lambda: np.zeros(2))}
    files = sorted(glob.glob(f"{root}/trades/year=*/month=*/day=*/data.parquet"))
    for i, f in enumerate(files):
        t = pq.read_table(f, columns=COLS)
        n["observed"] += t.num_rows
        complete = pc.and_(pc.and_(pc.is_valid(t["maker_address"]), pc.is_valid(t["taker_address"])),
                           pc.and_(pc.is_valid(t["price"]), pc.and_(pc.is_valid(t["quantity"]),
                                                                     pc.is_valid(t["prediction_id"]))))
        t = t.filter(pc.and_(complete, pc.not_equal(t["maker_address"], t["taker_address"])))
        n["complete_distinct"] += t.num_rows
        t = t.filter(pc.and_(pc.and_(pc.greater(t["price"], 0), pc.less_equal(t["price"], 1)),
                             pc.greater(t["quantity"], 0)))
        n["valid_qty_price"] += t.num_rows
        t = t.filter(pc.invert(pc.is_in(t["prediction_id"], value_set=multi)))
        n["two_outcome"] += t.num_rows
        buyer = pc.if_else(t["taker_bought"], t["taker_address"], t["maker_address"])
        t = t.filter(pc.invert(pc.is_in(buyer, value_set=high_hhi)))
        n["hhi_lt_0_5"] += t.num_rows
        t = t.filter(pc.is_valid(t["winner"]))
        n["resolved"] += t.num_rows
        p = t["price"].to_numpy()
        q = t["quantity"].to_numpy()
        w = t["winner"].to_numpy(zero_copy_only=False).astype(float)
        tb = t["taker_bought"].to_numpy(zero_copy_only=False).astype(bool)
        mkt = t["market_id"].to_numpy(zero_copy_only=False)
        cost = p * q
        pnl = q * w - cost
        fav, long_ = p >= 0.90, p < 0.10
        amt["all"] += cost.sum()
        amt["fav"] += cost[fav].sum()
        n["long_purchases"] += int(long_.sum())
        for key, mask in (("fav", fav), ("long", long_), ("fav_taker", fav & tb), ("fav_maker", fav & ~tb)):
            pooled[key] += (cost[mask].sum(), pnl[mask].sum())
        for key, mask in (("fav", fav), ("long", long_)):
            if mask.any():
                tab = pa.table({"m": mkt[mask], "c": cost[mask], "g": pnl[mask]}).group_by("m").aggregate(
                    [("c", "sum"), ("g", "sum")])
                for m_, c_, g_ in zip(tab["m"].to_pylist(), tab["c_sum"].to_pylist(), tab["g_sum"].to_pylist()):
                    per_market[key][m_] += (c_, g_)
        if (i + 1) % 100 == 0:
            print(f"{i + 1}/{len(files)} files", flush=True)

    def pct(cg):
        return 100.0 * cg[1] / cg[0]

    def equal_child(d):
        return 100.0 * float(np.mean([g / c for c, g in d.values() if c > 0]))

    checks = {
        "observed_rows": (n["observed"], 588_287_492, "exact"),
        "R0a_return_sample_purchases": (n["resolved"], 560_909_624, "exact"),
        "R0b_amount_paid_usd_bn": (amt["all"] / 1e9, 22.49, 0.005),
        "R0c_favorite_amount_paid_usd_bn": (amt["fav"] / 1e9, 9.662, 0.0005),
        "R0d_longshot_purchases_m": (n["long_purchases"] / 1e6, 100.7, 0.05),
        "R1_pooled_favorite_pct": (pct(pooled["fav"]), 0.83, TOL_PP),
        "R1eq_equal_child_favorite_pct": (equal_child(per_market["fav"]), 0.277, TOL_PP),
        "R2_pooled_taker_favorite_pct": (pct(pooled["fav_taker"]), 0.877, TOL_PP),
        "R2m_pooled_maker_favorite_pct": (pct(pooled["fav_maker"]), 0.816, TOL_PP),
        "R3_pooled_longshot_pct": (pct(pooled["long"]), -19.35, TOL_PP),
        "R3b_equal_child_longshot_pct": (equal_child(per_market["long"]), -6.30, TOL_PP),
    }
    result = {}
    for k, (val, target, tol) in checks.items():
        ok = (val == target) if tol == "exact" else abs(val - target) <= tol + 1e-9
        result[k] = dict(value=val, target=target, tolerance=tol, pass_=bool(ok))
    r3 = result["R3_pooled_longshot_pct"]["value"]
    result["R3_ci_rule"] = dict(value=r3, interval=[-46.9, 8.30], pass_=bool(-46.9 <= r3 <= 8.30))
    filters = {k: n[k] for k in ("observed", "complete_distinct", "valid_qty_price", "two_outcome", "hhi_lt_0_5",
                                 "resolved")}
    verdict = "PASS" if all(v["pass_"] for v in result.values()) else "FAIL (at least one frozen check missed)"
    json.dump(dict(verdict=verdict, checks=result, filter_counts_vs_paper_table1=filters), open(out, "w"), indent=1)
    print(json.dumps(dict(verdict=verdict, checks=result, filters=filters), indent=1))


if __name__ == "__main__":
    main()

"""PN-3b stage 1 (outcome-free): fresh F1 population, holdout guard, classes for both fields, descriptive counts.

usage: python pn3b_stage1.py <population_out.parquet> [<counts_out.json>]
Reads ONLY: trades (market_id, timestamp), markets (no outcome_yes), predictions (market_id, n_outcomes),
v5_instants.jsonl, F1_onchain_instants_final.json. No outcome column is opened. The null-outcome exclusion is
applied in stage 3 (testing outcome_yes for null already reads the outcome column).
"""
import collections
import json
import os
import sys

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

import pn3b_common as c

sys.path.insert(0, os.path.join(c.HERE, "..", "pn3"))
from pn3_stage1 import scan_trades  # noqa: E402  (unchanged PN-3 code: per-market max trade ts + count)

p3 = c.p3


def main():
    pop_out = sys.argv[1]
    counts_out = sys.argv[2] if len(sys.argv) > 2 else f"{c.HERE}/PN-3b_stage1_counts.json"
    agg, file_info = scan_trades()
    tr = pd.DataFrame({"mid": agg["market_id"].to_pylist(),
                       "max_ts": agg["timestamp_max_max"].cast(pa.int64()).to_numpy(),
                       "n_trades": agg["timestamp_count_sum"].to_numpy()})
    tr = tr[tr["mid"].notna()]
    cutoff = int(c.ERA_CUTOFF.astype("int64"))
    mk = p3.load_markets_outcome_free().to_pandas()
    mk["mid"] = mk["market_id"].astype(str)
    mk = mk.merge(tr, on="mid", how="left", validate="one_to_one")
    mk["late_trade"] = (mk["max_ts"].notna() & (mk["max_ts"] >= cutoff)).astype(bool)
    binary = p3.binary_market_ids()
    v5 = c.load_v5_full()
    onchain = p3.load_f1_onchain()

    # holdout guard: events containing any v5 primary market (any era); conservatively also any A16-masked market
    # (masked primaries) and any market with no v5 record (primary status unknown). See DEVIATIONS.md G1-G2.
    def guard_reason(mid):
        r = v5.get(mid)
        if r is None:
            return "no_v5_record"
        if r["primary"]:
            return "primary"
        if r["a16_masked"]:
            return "a16_masked"
        return None
    mk["guard_reason"] = mk["mid"].map(guard_reason)
    gm = mk[mk["guard_reason"].notna() & mk["event_id"].notna()]
    guard_events = set(gm["event_id"])
    guard_event_reasons = collections.Counter()
    for e, g in gm.groupby("event_id")["guard_reason"]:
        guard_event_reasons["primary" if (g == "primary").any() else g.iloc[0]] += 1

    def is_f1(mid):
        r = v5.get(mid)
        return (r is not None and r["status"] == "ok" and r["family"] in c.F1_FAMILIES and r["n_inst"] == 1
                and not r["a16_masked"])
    w = collections.OrderedDict()
    s = mk[mk["mid"].map(is_f1)]
    w["v5_F1_ok_one_instant_not_masked"] = len(s)
    w["  no_trades"] = int(s["max_ts"].isna().sum())
    w["  all_trades_before_2025"] = int((s["max_ts"].notna() & ~s["late_trade"]).sum())
    s = s[s["late_trade"]]
    w["with_trade_on_or_after_2025_01_01"] = len(s)
    w["  non_binary_excluded"] = int((~s["market_id"].isin(binary)).sum())
    s = s[s["market_id"].isin(binary)]
    w["binary"] = len(s)
    w["  null_event_id_excluded"] = int(s["event_id"].isna().sum())
    s = s[s["event_id"].notna()]
    w["non_null_event_id"] = len(s)
    w["  holdout_guard_excluded"] = int(s["event_id"].isin(guard_events).sum())
    s = s[~s["event_id"].isin(guard_events)].copy()
    w["after_holdout_guard (pre null-outcome exclusion)"] = len(s)
    w["  events"] = int(s["event_id"].nunique())
    assert (s["max_ts"] >= cutoff).all()  # disjoint from the PN-3 zone (which requires every trade < cutoff)

    rows = []
    for r in s.itertuples(index=False):
        dl, src = p3.deadline_for(r.mid, v5[r.mid], onchain)
        dl = int(dl.astype("int64"))
        exp = None if pd.isna(r.expiration_time) else int(r.expiration_time.value)
        clo = None if pd.isna(r.close_time) else int(r.close_time.value)
        rows.append(dict(market_id=r.mid, market_id_int=int(r.market_id), event_id=r.event_id,
                         category=r.category, family=v5[r.mid]["family"], deadline_ns=dl, deadline_source=src,
                         expiration_ns=exp, close_ns=clo,
                         delta_exp_ns=None if exp is None else exp - dl, delta_close_ns=None if clo is None else clo - dl,
                         class_exp=None if exp is None else c.classify(exp - dl),
                         class_close=None if clo is None else c.classify(clo - dl),
                         exp_close_within_1h=None if exp is None or clo is None
                         else abs(exp - clo) <= c.MECH_WINDOW_NS))
    df = pd.DataFrame(rows)

    def field_tables(key, dkey):
        out = {}
        for k in c.CLASSES:
            sel = df[df[key] == k]
            mech = sel[sel["exp_close_within_1h"].notna()]
            out[k] = dict(markets=int(len(sel)), events=int(sel["event_id"].nunique()),
                          median_delta_h=(float(np.median(sel[dkey].astype(float))) / c.HOUR_NS) if len(sel) else None,
                          with_other_field=int(len(mech)),
                          within_1h_of_other_field=int(mech["exp_close_within_1h"].astype(bool).sum()),
                          share_within_1h=(float(mech["exp_close_within_1h"].astype(bool).mean()) if len(mech) else None))
        out["field_null_excluded"] = int(df[key].isna().sum())
        return out
    fields = {"expiration_time": field_tables("class_exp", "delta_exp_ns"),
              "close_time": field_tables("class_close", "delta_close_ns")}
    by_cat = {}
    for fld, key in (("expiration_time", "class_exp"), ("close_time", "class_close")):
        t = df.groupby(["category", key], dropna=False).size()
        by_cat[fld] = {str(cat): {str(k): int(v) for k, v in t[cat].items()} for cat in t.index.levels[0]}
    stop = all(fields[f]["EARLIER"]["markets"] < 30 for f in fields)
    out = dict(
        protocol="research/public_note/PN-3b_fresh_sample_prereg.md @ 589f667",
        stage="1 (outcome-free; no outcome column opened; null-outcome exclusion deferred to stage 3)",
        classes_h={"EARLIER": "delta < -72", "GAP_NEG": "-72 <= delta < -36", "MATCH": "-36 <= delta <= +36",
                   "GAP_POS": "+36 < delta <= +72", "LATER": "delta > +72"},
        waterfall=dict(w),
        holdout_guard=dict(guard_events=len(guard_events), guard_events_by_reason=dict(guard_event_reasons),
                           guard_markets_by_reason=dict(collections.Counter(mk["guard_reason"].dropna()))),
        deadline_source=dict(collections.Counter(df["deadline_source"])),
        families=dict(collections.Counter(df["family"])),
        fields=fields,
        by_category_counts=by_cat,
        stop_rule=dict(rule="EARLIER < 30 markets for both fields -> stop, DATA-BLOCKED, no outcome read",
                       triggered=bool(stop)),
        population_market_ids_sha256=p3.sha256_ids(df["market_id"]),
        trade_files_scanned=len(file_info),
    )
    json.dump(out, open(counts_out, "w"), indent=1, default=str)
    print(json.dumps(out, indent=1, default=str))
    df.to_parquet(pop_out, index=False)


if __name__ == "__main__":
    main()

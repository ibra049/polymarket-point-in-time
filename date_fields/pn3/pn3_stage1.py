"""PN-3 stage 1 (outcome-free): embargo zone, Q1 population + classes, mechanism check, Q2 subset size.

usage: python pn3_stage1.py <zone_out.parquet> [<counts_out.json>]
Reads ONLY: trades (market_id, timestamp), markets (no outcome_yes), predictions (market_id, n_outcomes),
v5_instants.jsonl, F1_onchain_instants_final.json. No outcome column is opened.
Resolution status (outcome_yes not null) is also an outcome-column read, so the "resolved" filter is applied in
stage 3 (pn3_run.py); stage-1 class counts are therefore pre-resolution-filter counts.
"""
import collections
import json
import sys

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

import pn3_common as c


def scan_trades():
    """Per-market max trade timestamp + trade count; per-file timestamp range vs partition day."""
    parts, file_info = [], []
    files = c.trade_files()
    if c.DEV_MAX_FILES:  # development only; the recorded run uses every file
        files = files[:c.DEV_MAX_FILES]
    for i, (f, day) in enumerate(files):
        t = pq.read_table(f, columns=["market_id", "timestamp"])
        lo, hi = pc.min_max(t["timestamp"]).values()
        lo = np.datetime64(lo.as_py().replace(tzinfo=None), "ns") if t.num_rows else None
        hi = np.datetime64(hi.as_py().replace(tzinfo=None), "ns") if t.num_rows else None
        d0 = np.datetime64(day.isoformat(), "ns")
        d1 = d0 + np.timedelta64(c.DAY_NS, "ns")
        file_info.append(dict(day=day.isoformat(), rows=t.num_rows,
                              inside_partition_day=bool(t.num_rows == 0 or (lo >= d0 and hi < d1)),
                              min_ts=str(lo), max_ts=str(hi)))
        parts.append(t.group_by("market_id").aggregate([("timestamp", "max"), ("timestamp", "count")]))
        if (i + 1) % 100 == 0:
            print(f"{i + 1}/{len(files)} files", flush=True)
    agg = pa.concat_tables(parts).group_by("market_id").aggregate([("timestamp_max", "max"),
                                                                   ("timestamp_count", "sum")])
    return agg, file_info


def main():
    zone_out = sys.argv[1]
    counts_out = sys.argv[2] if len(sys.argv) > 2 else f"{c.HERE}/PN-3_stage1_counts.json"
    agg, file_info = scan_trades()
    tr = pd.DataFrame({"mid": agg["market_id"].to_pylist(),
                       "max_ts": agg["timestamp_max_max"].cast(pa.int64()).to_numpy(),
                       "n_trades": agg["timestamp_count_sum"].to_numpy()})
    cutoff = int(c.ZONE_CUTOFF.astype("int64"))

    # file-partition check: every file dated >= 2025-01-01 has only timestamps >= cutoff, so stage 3 may read
    # only files dated < 2025-01-01 for zone markets (whose trades are all < cutoff by construction).
    post = [fi for fi in file_info if fi["day"] >= "2025-01-01" and fi["rows"]]
    post_ok = all(np.datetime64(fi["min_ts"]) >= c.ZONE_CUTOFF for fi in post)
    assert post_ok, "a file dated >= 2025-01-01 holds a trade before the cutoff"
    pre_files = [fi for fi in file_info if fi["day"] < "2025-01-01"]

    mk = c.load_markets_outcome_free().to_pandas()
    mk["mid"] = mk["market_id"].astype(str)
    binary = c.binary_market_ids()
    n_trade_mids_not_in_markets = int((~tr["mid"].isin(set(mk["mid"]))).sum())
    mk = mk.merge(tr, on="mid", how="left", validate="one_to_one")
    mk["has_trade"] = mk["max_ts"].notna()
    mk["max_ts"] = mk["max_ts"].astype("Int64")
    mk["n_trades"] = mk["n_trades"].fillna(0).astype(np.int64)
    mk["late"] = (mk["has_trade"] & (mk["max_ts"] >= cutoff)).fillna(False).astype(bool)
    late_events = set(mk.loc[mk["late"] & mk["event_id"].notna(), "event_id"])
    market_rule = mk["has_trade"] & ~mk["late"]
    event_rule = mk["event_id"].notna() & ~mk["event_id"].isin(late_events)
    mk["zone"] = market_rule & event_rule
    z = mk[mk["zone"]].copy()
    zone_counts = dict(
        markets_total=len(mk), markets_with_trades=int(mk["has_trade"].sum()),
        markets_without_trades_excluded=int((~mk["has_trade"]).sum()),
        markets_null_event_id_excluded=int(mk["event_id"].isna().sum()),
        trade_market_ids_not_in_markets_parquet=n_trade_mids_not_in_markets,
        market_rule_pass=int(market_rule.sum()),
        market_rule_pass_but_event_rule_fail=int((market_rule & ~event_rule).sum()),
        zone_markets=len(z), zone_events=int(z["event_id"].nunique()),
        zone_trade_rows=int(z["n_trades"].sum()),
        zone_max_trade_ts=str(np.datetime64(int(z["max_ts"].max()), "ns")),
        zone_markets_binary=int(z["market_id"].isin(binary).sum()),
        zone_market_ids_sha256=c.sha256_ids(z["mid"]),
        trade_files_total=len(file_info), trade_files_dated_before_2025=len(pre_files),
        trade_rows_in_files_dated_before_2025=int(sum(fi["rows"] for fi in pre_files)),
        files_with_timestamps_outside_partition_day=sum(1 for fi in file_info if not fi["inside_partition_day"]),
        files_dated_2025_plus_all_ts_ge_cutoff=bool(post_ok),
    )

    v5 = c.load_v5()
    onchain = c.load_f1_onchain()
    rows = []
    v5_ok_excluded = collections.Counter()
    for r in z.itertuples(index=False):
        rec = v5.get(r.mid)
        if rec is None or rec["status"] != "ok":
            continue
        if rec["n_inst"] != 1 or rec["a16_masked"]:
            v5_ok_excluded["a16_masked" if rec["a16_masked"] else "more_than_one_instant"] += 1
            continue
        dl, src = c.deadline_for(r.mid, rec, onchain)
        dl = int(dl.astype("int64"))
        exp = None if pd.isna(r.expiration_time) else int(r.expiration_time.value)
        clo = None if pd.isna(r.close_time) else int(r.close_time.value)
        rows.append(dict(market_id=r.mid, event_id=r.event_id, family=rec["family"], binary=r.market_id in binary,
                         deadline_ns=dl, deadline_source=src, expiration_ns=exp, close_ns=clo,
                         class_exp=None if exp is None else c.classify(exp - dl),
                         class_close=None if clo is None else c.classify(clo - dl),
                         mech_within_1h=None if exp is None or clo is None else abs(exp - clo) <= c.MECH_WINDOW_NS))
    v5_in_zone = collections.Counter()
    for mid in z["mid"]:
        rec = v5.get(mid)
        v5_in_zone["no_v5_record" if rec is None else (rec["status"] + ("" if rec["status"] != "ok" else
                                                                        ":" + rec["family"]))] += 1

    def class_table(sel, key):
        out = collections.Counter(r[key] for r in sel)
        ev = {k: len({r["event_id"] for r in sel if r[key] == k}) for k in ("EARLIER", "MATCH", "LATER")}
        return {k: dict(markets=out.get(k, 0), events=ev[k]) for k in ("EARLIER", "MATCH", "LATER")} | \
            {"field_null": out.get(None, 0)}

    fam_tables = {}
    groups = {"F1": c.F1_FAMILIES} | c.REPORT_FAMILIES
    for name, fams in groups.items():
        sel = [r for r in rows if r["family"] in fams and r["binary"]]
        fam_tables[name] = dict(markets=len(sel), events=len({r["event_id"] for r in sel}),
                                deadline_source=dict(collections.Counter(r["deadline_source"] for r in sel)),
                                expiration_time=class_table(sel, "class_exp"),
                                close_time=class_table(sel, "class_close"))
    f1 = [r for r in rows if r["family"] in c.F1_FAMILIES and r["binary"]]
    mech = {}
    for k in ("EARLIER", "MATCH"):
        s = [r for r in f1 if r["class_exp"] == k]
        d = [r for r in s if r["mech_within_1h"] is not None]
        hit = sum(1 for r in d if r["mech_within_1h"])
        mech[k] = dict(markets=len(s), with_close_time=len(d), exp_within_1h_of_close=hit,
                       share=(hit / len(d)) if d else None)

    q2 = [r for r in rows if r["expiration_ns"] is not None and r["close_ns"] is not None]
    q2_counts = dict(markets=len(q2), events=len({r["event_id"] for r in q2}),
                     trade_rows=int(z.set_index("mid").loc[[r["market_id"] for r in q2], "n_trades"].sum()),
                     families=dict(collections.Counter(r["family"] for r in q2)),
                     dropped_null_expiration_or_close=len(rows) - len(q2))

    out = dict(
        protocol="research/public_note/PN-3_closing_date_leak_prereg.md @ 26f4a9d",
        stage="1 (outcome-free; no outcome column opened; resolved filter deferred to stage 3)",
        zone=zone_counts,
        v5_status_in_zone=dict(v5_in_zone.most_common()),
        v5_ok_in_zone_excluded=dict(v5_ok_excluded),
        zone_markets_non_binary=int(len(z) - z["market_id"].isin(binary).sum()),
        q1_population_pre_resolution_filter=dict(
            note="zone & binary & v5 status ok & one distinct instant & not A16-masked; F1 = v5 F1i+F1x; "
                 "F4 = F4+F4d (also split); PN-1 on-chain instant replaces Gamma for F1 where final_status ok",
            families=fam_tables),
        mechanism_check_F1_expiration_classes=mech,
        q2_deadline_subset_pre_ledger=q2_counts,
    )
    json.dump(out, open(counts_out, "w"), indent=1, default=str)
    print(json.dumps(out, indent=1, default=str))
    zt = pa.table({"market_id": z["mid"].tolist(), "event_id": z["event_id"].tolist(),
                   "max_trade_ts_ns": z["max_ts"].astype(np.int64).tolist(), "n_trades": z["n_trades"].tolist()})
    pq.write_table(zt, zone_out)

if __name__ == "__main__":
    main()

"""PN-3 stage 3: the single run of Q1 (primary) and Q2 (reported only). Embargo zone only.

usage: python pn3_run.py <zone_markets.parquet> <stage1_counts.json> <out_dir> [--dry-run-fake-outcomes]

Protocol: research/public_note/PN-3_closing_date_leak_prereg.md (frozen at 26f4a9d). Readings: DEVIATIONS.md.
Outcome columns (markets.outcome_yes, trades.winner) are read only through a parquet row filter restricted to
zone market ids, and only trade files dated before 2025-01-01 are opened (stage 1 verified that every file dated
2025-01-01 or later holds only trades at or after the cutoff, so it cannot hold a zone-market trade).
--dry-run-fake-outcomes: development mode. It never opens an outcome column; it substitutes deterministic fake
outcomes so the pipeline can be tested before the code is committed. Its output is not a result.

Q2 purchase ledger and return definitions follow e003_step0_reproduction.py (step 0, PASS on all 12 checks):
one purchase per trade row, buyer = taker if taker_bought else maker; filters in order: complete fields,
distinct buyer/seller, 0 < price <= 1 and quantity > 0, two-outcome tokens, buyer counterparty_hhi < 0.5,
winner known. cost = price * quantity, pnl = quantity * winner - cost. Pooled = 100 * sum(pnl) / sum(cost).
Equal child = 100 * mean over markets of (market sum pnl / market sum cost). Longshot = price < 0.10.
The script also runs a verbatim zone-restricted copy of the step-0 loop and asserts both give the same baseline.
"""
import collections
import hashlib
import json
import sys
import time

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

import pn3_common as c

DRY = "--dry-run-fake-outcomes" in sys.argv
LOG = []


def log(*a):
    s = " ".join(str(x) for x in a)
    LOG.append(f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {s}")
    print(s, flush=True)


def fake_bool(keys):
    """Dry run only: deterministic pseudo-outcome from a hash of the key. Never derived from data outcomes."""
    return np.array([hashlib.md5(str(k).encode()).digest()[0] % 2 == 0 for k in keys])


# ---------------------------------------------------------------- bootstrap (event clusters)
def order_stat_ci(draws):
    d = draws[~np.isnan(draws)]
    n_undef = int(np.isnan(draws).sum())
    d = np.sort(d)
    if n_undef == 0:
        lo, hi = d[c.PCT_LO_IDX], d[c.PCT_HI_IDX]
    else:  # pre-declared fallback (DEVIATIONS.md D6): same order-statistic rule on the defined draws
        lo, hi = d[int(np.ceil(0.025 * len(d))) - 1], d[int(np.ceil(0.975 * len(d))) - 1]
    return [float(lo), float(hi)], n_undef


def boot_ratio_diff(ev, a_mask, b_mask, y):
    """D = mean(y | a) - mean(y | b); event-cluster bootstrap over events with >= 1 market in a or b."""
    sel = a_mask | b_mask
    codes, inv = np.unique(ev[sel], return_inverse=True)
    E = len(codes)
    a, b, yy = a_mask[sel].astype(float), b_mask[sel].astype(float), y[sel].astype(float)
    na, ya = np.bincount(inv, a, E), np.bincount(inv, a * yy, E)
    nb, yb = np.bincount(inv, b, E), np.bincount(inv, b * yy, E)
    rng = np.random.default_rng(c.SEED)
    draws = np.empty(c.N_BOOT)
    with np.errstate(invalid="ignore", divide="ignore"):
        for i in range(c.N_BOOT):
            w = np.bincount(rng.integers(0, E, E), minlength=E)
            draws[i] = (w @ ya) / (w @ na) - (w @ yb) / (w @ nb)
    ci, n_undef = order_stat_ci(draws)
    return ci, n_undef, E


def boot_returns(ev_of_market, mkt_cost, mkt_pnl):
    """Pooled and equal-child returns (%) with event-cluster bootstrap CIs; inputs are per-market arrays."""
    codes, inv = np.unique(ev_of_market, return_inverse=True)
    E = len(codes)
    r = mkt_pnl / mkt_cost
    ce, ge = np.bincount(inv, mkt_cost, E), np.bincount(inv, mkt_pnl, E)
    re_, ke = np.bincount(inv, r, E), np.bincount(inv, None, E)
    rng = np.random.default_rng(c.SEED)
    dp, dq = np.empty(c.N_BOOT), np.empty(c.N_BOOT)
    for i in range(c.N_BOOT):
        w = np.bincount(rng.integers(0, E, E), minlength=E)
        dp[i] = 100.0 * (w @ ge) / (w @ ce)
        dq[i] = 100.0 * (w @ re_) / (w @ ke)
    ci_p, u1 = order_stat_ci(dp)
    ci_q, u2 = order_stat_ci(dq)
    return dict(pooled_pct=100.0 * mkt_pnl.sum() / mkt_cost.sum(), pooled_ci95=ci_p,
                equal_child_pct=100.0 * float(np.mean(r)), equal_child_ci95=ci_q,
                markets=int(len(r)), events=int(E), undefined_draws=u1 + u2)


# ---------------------------------------------------------------- Q1
def build_rows(z, binary):
    """Identical row logic to pn3_stage1.py (re-derived here; class counts are asserted against stage 1)."""
    v5, onchain = c.load_v5(), c.load_f1_onchain()
    mk = c.load_markets_outcome_free().to_pandas()
    mk["mid"] = mk["market_id"].astype(str)
    mk = mk[mk["mid"].isin(set(z["market_id"]))]
    rows = []
    for r in mk.itertuples(index=False):
        rec = v5.get(r.mid)
        if rec is None or rec["status"] != "ok" or rec["n_inst"] != 1 or rec["a16_masked"]:
            continue
        dl, src = c.deadline_for(r.mid, rec, onchain)
        dl = int(dl.astype("int64"))
        exp = None if pd.isna(r.expiration_time) else int(r.expiration_time.value)
        clo = None if pd.isna(r.close_time) else int(r.close_time.value)
        rows.append(dict(market_id=r.mid, market_id_int=int(r.market_id), event_id=r.event_id,
                         family=rec["family"], binary=int(r.market_id) in binary, deadline_ns=dl,
                         deadline_source=src, expiration_ns=exp, close_ns=clo,
                         class_exp=None if exp is None else c.classify(exp - dl),
                         class_close=None if clo is None else c.classify(clo - dl),
                         mech_within_1h=None if exp is None or clo is None else abs(exp - clo) <= c.MECH_WINDOW_NS))
    return pd.DataFrame(rows)


def read_market_outcomes(zone_int_ids):
    if DRY:
        return {m: (None if m % 17 == 0 else bool(fake_bool([m])[0])) for m in zone_int_ids}
    t = pq.read_table(f"{c.DATA}/markets.parquet", columns=["market_id", "outcome_yes"],
                      filters=[("market_id", "in", sorted(zone_int_ids))])
    assert set(t["market_id"].to_pylist()) <= set(zone_int_ids)
    return dict(zip(t["market_id"].to_pylist(), t["outcome_yes"].to_pylist()))


def q1_table(df, key):
    out = {}
    for k in ("EARLIER", "MATCH", "LATER"):
        s = df[df[key] == k]
        out[k] = dict(markets=int(len(s)), events=int(s["event_id"].nunique()), yes=int(s["y"].sum()),
                      p_yes=(float(s["y"].mean()) if len(s) else None))
    out["field_null"] = int(df[key].isna().sum())
    ev, y = df["event_id"].to_numpy(), df["y"].to_numpy()
    for lab, other in (("D_EARLIER_minus_MATCH", "EARLIER"), ("D_LATER_minus_MATCH", "LATER")):
        a, b = (df[key] == other).to_numpy(), (df[key] == "MATCH").to_numpy()
        if a.sum() and b.sum():
            ci, n_undef, E = boot_ratio_diff(ev, a, b, y)
            out[lab] = dict(D=out[other]["p_yes"] - out["MATCH"]["p_yes"], ci95=ci, bootstrap_events=E,
                            undefined_draws=n_undef)
        else:
            out[lab] = dict(D=None, ci95=None, note="a class is empty")
    return out


def frozen_status(t):
    e, m = t["EARLIER"], t["MATCH"]
    if e["markets"] < 30 or e["events"] < 10 or m["markets"] < 100:
        return "DATA-BLOCKED"
    d, (lo, hi) = t["D_EARLIER_minus_MATCH"]["D"], t["D_EARLIER_minus_MATCH"]["ci95"]
    excludes0 = lo > 0 or hi < 0
    if abs(d) >= 0.20 and excludes0:
        return "PROMOTE"
    if (not excludes0) and abs(d) < 0.10:
        return "REJECT"
    return "INCONCLUSIVE"


def run_q1(z, s1, binary, out_dir):
    rows = build_rows(z, binary)
    groups = {"F1": c.F1_FAMILIES} | c.REPORT_FAMILIES
    # consistency with stage 1 (pre-resolution class counts)
    for name, fams in groups.items():
        sel = rows[rows["family"].isin(fams) & rows["binary"]]
        st = s1["q1_population_pre_resolution_filter"]["families"][name]
        assert len(sel) == st["markets"], (name, len(sel), st["markets"])
        for k in ("EARLIER", "MATCH", "LATER"):
            assert int((sel["class_exp"] == k).sum()) == st["expiration_time"][k]["markets"], (name, k)
            assert int((sel["class_close"] == k).sum()) == st["close_time"][k]["markets"], (name, k)
    log("Q1: row rebuild matches stage-1 class counts for", list(groups))
    pop_all = rows[rows["binary"]].copy()
    outc = read_market_outcomes(set(pop_all["market_id_int"]))
    pop_all["outcome_yes"] = pop_all["market_id_int"].map(outc)
    n_unresolved = collections.Counter(pop_all.loc[pop_all["outcome_yes"].isna(), "family"])
    pop = pop_all[pop_all["outcome_yes"].notna()].copy()
    pop["y"] = pop["outcome_yes"].astype(bool).astype(int)
    res = {}
    for name, fams in groups.items():
        sel = pop[pop["family"].isin(fams)]
        res[name] = dict(markets=int(len(sel)), events=int(sel["event_id"].nunique()),
                         unresolved_dropped=int(sum(n_unresolved[f] for f in fams)),
                         expiration_time=q1_table(sel, "class_exp"), close_time=q1_table(sel, "class_close"))
        log(f"Q1 {name}: n={len(sel)}", json.dumps(res[name]["expiration_time"]))
    f1 = pop[pop["family"].isin(c.F1_FAMILIES)]
    mech = {}
    for k in ("EARLIER", "MATCH"):
        s = f1[f1["class_exp"] == k]
        d = s[s["mech_within_1h"].notna()]
        hit = int(d["mech_within_1h"].astype(bool).sum())
        mech[k] = dict(markets=int(len(s)), with_close_time=int(len(d)), exp_within_1h_of_close=hit,
                       share=(hit / len(d)) if len(d) else None)
    status = frozen_status(res["F1"]["expiration_time"])
    csv = pop[pop["family"].isin(sum(groups.values(), ()))].copy()
    csv["deadline_utc"] = pd.to_datetime(csv["deadline_ns"], utc=True)
    csv["expiration_time_utc"] = pd.to_datetime(csv["expiration_ns"], utc=True)
    csv["close_time_utc"] = pd.to_datetime(csv["close_ns"], utc=True)
    csv = csv.rename(columns={"class_exp": "class", "class_close": "class_close_time", "y": "outcome"})
    csv = csv.sort_values(["family", "market_id_int"])[
        ["market_id", "event_id", "family", "class", "class_close_time", "outcome", "deadline_utc",
         "deadline_source", "expiration_time_utc", "close_time_utc"]]
    csv.to_csv(f"{out_dir}/PN-3_q1_markets.csv", index=False)
    return dict(status_frozen_rule=status, primary="F1, expiration_time, D = P(YES|EARLIER) - P(YES|MATCH)",
                families=res, mechanism_check_F1_resolved_population=mech)


# ---------------------------------------------------------------- Q2 ledger
LEDGER_COLS = ["timestamp", "market_id", "prediction_id", "winner", "price", "quantity", "maker_address",
               "taker_address", "taker_bought"]


def pre2025_files():
    return [f for f, day in c.trade_files() if day.isoformat() < "2025-01-01"]


def read_zone_trades(f, zone_str_ids, cols):
    if DRY:
        cols = [x for x in cols if x != "winner"]
    t = pq.read_table(f, columns=cols, filters=[("market_id", "in", zone_str_ids)])
    if DRY and "winner" not in t.column_names:
        t = t.append_column("winner", pa.array(fake_bool(t["prediction_id"].to_pylist())
                                               if t.num_rows else np.zeros(0, bool)))
    return t


def build_ledger(zone_str_ids, multi, high_hhi):
    """Zone-restricted step-0 ledger, longshot purchases only. Returns DataFrame + filter counts."""
    n = collections.Counter()
    parts = []
    files = pre2025_files()
    for i, f in enumerate(files):
        t = read_zone_trades(f, zone_str_ids, LEDGER_COLS)
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
        t = t.filter(pc.less(t["price"], c.LONGSHOT_PRICE))
        n["longshot"] += t.num_rows
        p, q = t["price"].to_numpy(), t["quantity"].to_numpy()
        w = t["winner"].to_numpy(zero_copy_only=False).astype(float)
        parts.append(pd.DataFrame({"mid": t["market_id"].to_numpy(zero_copy_only=False),
                                   "ts": t["timestamp"].cast(pa.int64()).to_numpy(),
                                   "cost": p * q, "pnl": q * w - p * q}))
        if (i + 1) % 100 == 0:
            log(f"ledger {i + 1}/{len(files)} files")
    return pd.concat(parts, ignore_index=True), dict(n)


def step0_replica_zone_longshot(zone_str_ids, multi, high_hhi):
    """Verbatim copy of the e003_step0_reproduction.py loop (longshot parts), plus the zone row filter at read."""
    n = collections.Counter()
    pooled = collections.defaultdict(lambda: np.zeros(2))
    per_market = {"long": collections.defaultdict(lambda: np.zeros(2))}
    COLS = ["trade_id", "market_id", "prediction_id", "winner", "price", "quantity", "maker_address",
            "taker_address", "taker_bought"]
    for f in pre2025_files():
        t = read_zone_trades(f, zone_str_ids, COLS)
        n["observed"] += t.num_rows
        complete = pc.and_(pc.and_(pc.is_valid(t["maker_address"]), pc.is_valid(t["taker_address"])),
                           pc.and_(pc.is_valid(t["price"]), pc.and_(pc.is_valid(t["quantity"]),
                                                                     pc.is_valid(t["prediction_id"]))))
        t = t.filter(pc.and_(complete, pc.not_equal(t["maker_address"], t["taker_address"])))
        t = t.filter(pc.and_(pc.and_(pc.greater(t["price"], 0), pc.less_equal(t["price"], 1)),
                             pc.greater(t["quantity"], 0)))
        t = t.filter(pc.invert(pc.is_in(t["prediction_id"], value_set=multi)))
        buyer = pc.if_else(t["taker_bought"], t["taker_address"], t["maker_address"])
        t = t.filter(pc.invert(pc.is_in(buyer, value_set=high_hhi)))
        t = t.filter(pc.is_valid(t["winner"]))
        n["resolved"] += t.num_rows
        p = t["price"].to_numpy()
        q = t["quantity"].to_numpy()
        w = t["winner"].to_numpy(zero_copy_only=False).astype(float)
        mkt = t["market_id"].to_numpy(zero_copy_only=False)
        cost = p * q
        pnl = q * w - cost
        long_ = p < 0.10
        n["long_purchases"] += int(long_.sum())
        for key, mask in (("long", long_),):
            pooled[key] += (cost[mask].sum(), pnl[mask].sum())
        for key, mask in (("long", long_),):
            if mask.any():
                tab = pa.table({"m": mkt[mask], "c": cost[mask], "g": pnl[mask]}).group_by("m").aggregate(
                    [("c", "sum"), ("g", "sum")])
                for m_, c_, g_ in zip(tab["m"].to_pylist(), tab["c_sum"].to_pylist(), tab["g_sum"].to_pylist()):
                    per_market[key][m_] += (c_, g_)

    def pct(cg):
        return 100.0 * cg[1] / cg[0]

    def equal_child(d):
        return 100.0 * float(np.mean([g / c_ for c_, g in d.values() if c_ > 0]))

    return dict(R3_pooled_longshot_pct=pct(pooled["long"]), R3b_equal_child_longshot_pct=equal_child(
        per_market["long"]), resolved=n["resolved"], long_purchases=n["long_purchases"], observed=n["observed"])


def cell(led, ev_map, mask):
    s = led[mask]
    g = s.groupby("mid", sort=True)[["cost", "pnl"]].sum()
    if len(g) == 0:
        return dict(purchases=0, markets=0, events=0, dollars=0.0)
    out = boot_returns(g.index.map(ev_map).to_numpy(), g["cost"].to_numpy(), g["pnl"].to_numpy())
    return dict(purchases=int(mask.sum()), dollars=float(s["cost"].sum())) | out


def run_q2(z, s1, binary):
    pred = pq.read_table(f"{c.DATA}/predictions.parquet", columns=["prediction_id", "n_outcomes"])
    multi = pc.filter(pred, pc.not_equal(pred["n_outcomes"], 2))["prediction_id"]
    uf = pq.read_table(f"{c.DATA}/user_features.parquet", columns=["user_address", "counterparty_hhi"])
    high_hhi = pc.filter(uf, pc.greater_equal(uf["counterparty_hhi"], 0.5))["user_address"]
    zone_str_ids = sorted(z["market_id"])
    ev_map = dict(zip(z["market_id"], z["event_id"]))
    led, counts = build_ledger(zone_str_ids, multi, high_hhi)
    log("Q2 ledger filter counts (zone):", json.dumps(counts))
    assert counts["observed"] == s1["zone"]["zone_trade_rows"], (counts["observed"], s1["zone"]["zone_trade_rows"])
    log("Q2: zone trade rows read from pre-2025 files == stage-1 zone_trade_rows")

    rep = step0_replica_zone_longshot(zone_str_ids, multi, high_hhi)
    base = cell(led, ev_map, np.ones(len(led), bool))
    ok = (abs(rep["R3_pooled_longshot_pct"] - base["pooled_pct"]) < 1e-9
          and abs(rep["R3b_equal_child_longshot_pct"] - base["equal_child_pct"]) < 1e-9
          and rep["long_purchases"] == len(led) and rep["observed"] == counts["observed"])
    assert ok, (rep, base["pooled_pct"], base["equal_child_pct"], len(led))
    log("Q2: step-0 replica == PN-3 ledger baseline", json.dumps(rep))

    rows = build_rows(z, binary)
    sub = rows[rows["expiration_ns"].notna() & rows["close_ns"].notna()]
    assert len(sub) == s1["q2_deadline_subset_pre_ledger"]["markets"]
    S = {"a_expiration_time": dict(zip(sub["market_id"], sub["expiration_ns"].astype(np.int64))),
         "b_close_time": dict(zip(sub["market_id"], sub["close_ns"].astype(np.int64))),
         "c_rule_text_deadline": dict(zip(sub["market_id"], sub["deadline_ns"].astype(np.int64)))}
    in_sub = led["mid"].isin(set(sub["market_id"])).to_numpy()
    res = dict(ledger_filter_counts_zone=counts, step0_replica_zone=rep,
               baseline_zone_all_markets=base,
               baseline_deadline_subset_no_restriction=cell(led, ev_map, in_sub),
               rows={}, a_vs_c_dollar_flows={}, purchases_after_scheduled_close={})
    ts = led["ts"].to_numpy()
    cost = led["cost"].to_numpy()
    keep = {}
    for dname, smap in S.items():
        # exact integer ns comparison; rows outside the deadline subset are masked out by in_sub
        sv_int = np.zeros(len(led), np.int64)
        sv_int[in_sub] = led.loc[in_sub, "mid"].map(smap).astype(np.int64).to_numpy()
        diff = sv_int - ts
        res["purchases_after_scheduled_close"][dname] = dict(
            purchases=int((in_sub & (diff < 0)).sum()), dollars=float(cost[in_sub & (diff < 0)].sum()))
        for N in c.Q2_DAYS:
            m = in_sub & (diff <= N * c.DAY_NS)
            keep[(dname, N)] = m
            res["rows"][f"{dname}|N={N}"] = cell(led, ev_map, m)
            log(f"Q2 {dname} N={N}:", json.dumps(res["rows"][f"{dname}|N={N}"]))
    for N in c.Q2_DAYS:
        a, cc = keep[("a_expiration_time", N)], keep[("c_rule_text_deadline", N)]
        da, dc = float(cost[a].sum()), float(cost[cc].sum())
        leave, enter, both = float(cost[a & ~cc].sum()), float(cost[cc & ~a].sum()), float(cost[a & cc].sum())
        res["a_vs_c_dollar_flows"][f"N={N}"] = dict(
            dollars_a=da, dollars_c=dc, dollars_in_both=both,
            dollars_in_a_not_c=leave, dollars_in_c_not_a=enter,
            share_of_a_dollars_leaving_when_a_to_c=(leave / da) if da else None,
            share_of_c_dollars_entering_when_a_to_c=(enter / dc) if dc else None,
            purchases_in_a_not_c=int((a & ~cc).sum()), purchases_in_c_not_a=int((cc & ~a).sum()))
    return res


def main():
    zone_path, s1_path, out_dir = sys.argv[1], sys.argv[2], sys.argv[3]
    s1 = json.load(open(s1_path))
    z = pq.read_table(zone_path).to_pandas()
    assert c.sha256_ids(z["market_id"]) == s1["zone"]["zone_market_ids_sha256"]
    assert len(z) == s1["zone"]["zone_markets"] and z["event_id"].nunique() == s1["zone"]["zone_events"]
    assert int(z["max_trade_ts_ns"].max()) < int(c.ZONE_CUTOFF.astype("int64"))
    log("mode:", "DRY RUN (fake outcomes; not a result)" if DRY else "SINGLE RUN (real outcomes, zone only)")
    log("zone verified against stage-1 counts:", len(z), "markets", z["event_id"].nunique(), "events")
    binary = c.binary_market_ids()
    t0 = time.time()
    q1 = run_q1(z, s1, binary, out_dir)
    log("Q1 status under frozen rule:", q1["status_frozen_rule"])
    q2 = run_q2(z, s1, binary)
    out = dict(protocol="research/public_note/PN-3_closing_date_leak_prereg.md @ 26f4a9d",
               mode="dry_run_fake_outcomes" if DRY else "single_run",
               zone=dict(markets=len(z), events=int(z["event_id"].nunique())),
               bootstrap=dict(resamples=c.N_BOOT, seed=c.SEED, order_stats_1based=[250, 9750],
                              rng="numpy.random.default_rng(seed), fresh per statistic"),
               q1=q1, q2=q2, runtime_s=round(time.time() - t0, 1))
    json.dump(out, open(f"{out_dir}/PN-3_result.json", "w"), indent=1, default=str)
    log("wrote", f"{out_dir}/PN-3_result.json")
    open(f"{out_dir}/PN-3_run.log", "w").write("\n".join(LOG) + "\n")


if __name__ == "__main__":
    main()

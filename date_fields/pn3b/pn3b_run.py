"""PN-3b single run: H1 (expiration_time) and H2 (close_time) on the fresh, holdout-guarded F1 population.

usage: python pn3b_run.py <population.parquet> <stage1_counts.json> <out_dir> [--dry-run-fake-outcomes]

Protocol: research/public_note/PN-3b_fresh_sample_prereg.md (frozen at 589f667). Readings: DEVIATIONS.md.
markets.outcome_yes is read only through a parquet row filter listing the stage-1 population ids (all of which
passed the holdout guard). No trade file and no other outcome column is opened.
--dry-run-fake-outcomes: development only; never opens an outcome column; output is not a result.
"""
import hashlib
import json
import sys
import time

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

import pn3b_common as c

DRY = "--dry-run-fake-outcomes" in sys.argv
LOG = []


def log(*a):
    s = " ".join(str(x) for x in a)
    LOG.append(f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {s}")
    print(s, flush=True)


def order_stat_ci(draws):
    n_undef = int(np.isnan(draws).sum())
    d = np.sort(draws[~np.isnan(draws)])
    if n_undef == 0:
        lo, hi = d[c.PCT_LO_IDX], d[c.PCT_HI_IDX]
    else:  # pre-declared fallback (DEVIATIONS.md B3), same as PN-3
        lo, hi = d[int(np.ceil(0.025 * len(d))) - 1], d[int(np.ceil(0.975 * len(d))) - 1]
    return [float(lo), float(hi)], n_undef


def boot_diff(ev, a_mask, b_mask, y):
    """D = mean(y|a) - mean(y|b); clusters = events with a market in a or b; fresh default_rng(20261113)."""
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


def frozen_status(t):
    e, m = t["classes"]["EARLIER"], t["classes"]["MATCH"]
    if e["markets"] < 30 or e["events"] < 10 or m["markets"] < 100:
        return "DATA-BLOCKED"
    d, (lo, hi) = t["D_EARLIER_minus_MATCH"]["D"], t["D_EARLIER_minus_MATCH"]["ci95"]
    excludes0 = lo > 0 or hi < 0
    if abs(d) >= 0.20 and excludes0:
        return "PROMOTE"
    if (not excludes0) and abs(d) < 0.10:
        return "REJECT"
    return "INCONCLUSIVE"


def field_result(df, key, dkey):
    cls = {}
    for k in c.CLASSES:
        s = df[df[key] == k]
        m = s[s["exp_close_within_1h"].notna()]
        cls[k] = dict(markets=int(len(s)), events=int(s["event_id"].nunique()), yes=int(s["y"].sum()),
                      p_yes=float(s["y"].mean()) if len(s) else None,
                      median_delta_h=float(np.median(s[dkey].astype(float))) / c.HOUR_NS if len(s) else None,
                      share_within_1h_of_other_field=float(m["exp_close_within_1h"].astype(bool).mean())
                      if len(m) else None)
    out = dict(classes=cls, field_null_excluded=int(df[key].isna().sum()))
    ev, y = df["event_id"].to_numpy(), df["y"].to_numpy()
    for lab, other in (("D_EARLIER_minus_MATCH", "EARLIER"), ("D_LATER_minus_MATCH", "LATER")):
        a, b = (df[key] == other).to_numpy(), (df[key] == "MATCH").to_numpy()
        if a.sum() and b.sum():
            ci, n_undef, E = boot_diff(ev, a, b, y)
            out[lab] = dict(D=cls[other]["p_yes"] - cls["MATCH"]["p_yes"], ci95=ci, bootstrap_events=E,
                            undefined_draws=n_undef)
        else:
            out[lab] = dict(D=None, ci95=None, note="a class is empty")
    out["status_frozen_rule"] = frozen_status(out)
    return out


def by_category(df, key):
    out = {}
    for cat, g in df.groupby(df["category"].fillna("<null>")):
        out[cat] = {k: dict(markets=int((g[key] == k).sum()),
                            p_yes=float(g.loc[g[key] == k, "y"].mean()) if (g[key] == k).any() else None)
                    for k in c.CLASSES} | {"field_null": int(g[key].isna().sum())}
    return out


def main():
    pop_path, s1_path, out_dir = sys.argv[1], sys.argv[2], sys.argv[3]
    s1 = json.load(open(s1_path))
    df = pd.read_parquet(pop_path)
    assert c.p3.sha256_ids(df["market_id"]) == s1["population_market_ids_sha256"]
    assert len(df) == s1["waterfall"]["after_holdout_guard (pre null-outcome exclusion)"]
    for key, dkey in (("class_exp", "delta_exp_ns"), ("class_close", "delta_close_ns")):
        ok = df[dkey].notna()
        assert (df.loc[ok, dkey].astype(np.int64).map(c.classify) == df.loc[ok, key]).all()
        assert df.loc[~ok, key].isna().all()
    for fld, key in (("expiration_time", "class_exp"), ("close_time", "class_close")):
        for k in c.CLASSES:
            assert int((df[key] == k).sum()) == s1["fields"][fld][k]["markets"], (fld, k)
    log("mode:", "DRY RUN (fake outcomes; not a result)" if DRY else "SINGLE RUN (real outcomes, guarded population)")
    log("population verified against stage-1 counts:", len(df), "markets", df["event_id"].nunique(), "events")
    base = dict(protocol="research/public_note/PN-3b_fresh_sample_prereg.md @ 589f667",
                mode="dry_run_fake_outcomes" if DRY else "single_run",
                bootstrap=dict(resamples=c.N_BOOT, seed=c.SEED, order_stats_1based=[250, 9750],
                               rng="numpy.random.default_rng(seed), fresh per statistic"))
    if s1["stop_rule"]["triggered"]:
        res = base | dict(status="DATA-BLOCKED (stage-1 stop rule; no outcome read)")
        json.dump(res, open(f"{out_dir}/PN-3b_result.json", "w"), indent=1)
        log("stop rule triggered; no outcome read")
        open(f"{out_dir}/PN-3b_run.log", "w").write("\n".join(LOG) + "\n")
        return
    ids = sorted(df["market_id_int"].astype(int).tolist())
    if DRY:
        outc = {m: (None if m % 23 == 0 else hashlib.md5(str(m).encode()).digest()[0] % 2 == 0) for m in ids}
    else:
        t = pq.read_table(f"{c.DATA}/markets.parquet", columns=["market_id", "outcome_yes"],
                          filters=[("market_id", "in", ids)])
        assert set(t["market_id"].to_pylist()) <= set(ids)
        outc = dict(zip(t["market_id"].to_pylist(), t["outcome_yes"].to_pylist()))
    df["outcome_yes"] = df["market_id_int"].map(outc)
    n_null = int(df["outcome_yes"].isna().sum())
    df = df[df["outcome_yes"].notna()].copy()
    df["y"] = df["outcome_yes"].astype(bool).astype(int)
    log("null outcome excluded:", n_null, "| final population:", len(df), "markets", df["event_id"].nunique(), "events")
    h1 = field_result(df, "class_exp", "delta_exp_ns")
    h2 = field_result(df, "class_close", "delta_close_ns")
    log("H1 expiration_time:", json.dumps(h1))
    log("H2 close_time:", json.dumps(h2))
    log("H1 status:", h1["status_frozen_rule"], "| H2 status:", h2["status_frozen_rule"])
    res = base | dict(population=dict(markets=int(len(df)), events=int(df["event_id"].nunique()),
                                      null_outcome_excluded=n_null),
                      H1_expiration_time=h1, H2_close_time=h2,
                      by_category=dict(expiration_time=by_category(df, "class_exp"),
                                       close_time=by_category(df, "class_close")))
    json.dump(res, open(f"{out_dir}/PN-3b_result.json", "w"), indent=1, default=str)
    csv = df.assign(delta_exp_h=df["delta_exp_ns"] / c.HOUR_NS, delta_close_h=df["delta_close_ns"] / c.HOUR_NS,
                    deadline_utc=pd.to_datetime(df["deadline_ns"], utc=True), outcome=df["y"])
    csv.sort_values("market_id_int")[["market_id", "event_id", "category", "family", "class_exp", "class_close",
                                      "delta_exp_h", "delta_close_h", "deadline_utc", "deadline_source", "outcome"]
                                     ].to_csv(f"{out_dir}/PN-3b_markets.csv", index=False)
    log("wrote", f"{out_dir}/PN-3b_result.json", f"{out_dir}/PN-3b_markets.csv")
    open(f"{out_dir}/PN-3b_run.log", "w").write("\n".join(LOG) + "\n")


if __name__ == "__main__":
    main()

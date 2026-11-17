"""PN-3 shared constants and outcome-free loaders.

Protocol: research/public_note/PN-3_closing_date_leak_prereg.md (frozen at 26f4a9d).
Deviations / conservative readings: DEVIATIONS.md in this directory.
Nothing in this module reads an outcome column (markets.outcome_yes, trades.winner, predictions.winner).
"""
import datetime as dt
import glob
import hashlib
import json
import os
import re

import numpy as np
import pyarrow.parquet as pq

DATA = os.environ.get("PN3_DATA", "data/users_v1.3")
DEV_MAX_FILES = int(os.environ.get("PN3_DEV_MAX_FILES", "0"))   # development only; 0 = all files
HERE = os.path.dirname(os.path.abspath(__file__))

ZONE_CUTOFF = np.datetime64("2025-01-01T00:00:00", "ns")       # market + event rule cutoff (UTC)
DAY_NS = 86_400 * 10**9
HOUR_NS = 3_600 * 10**9
CLASS_HALF_WIDTH_NS = 24 * HOUR_NS                              # |delta| <= 24 h is MATCH
MECH_WINDOW_NS = 1 * HOUR_NS                                    # mechanism check: |exp - close| <= 1 h
SEED = 20261112
N_BOOT = 10_000
PCT_LO_IDX, PCT_HI_IDX = 249, 9_749                             # 1-based order statistics 250 and 9,750
LONGSHOT_PRICE = 0.10
Q2_DAYS = (1, 7, 30)

F1_FAMILIES = ("F1i", "F1x")                                    # v5 labels of family F1 ("will ... by <deadline>")
REPORT_FAMILIES = {"F2": ("F2",), "F3": ("F3",), "F4": ("F4", "F4d"), "F4_timed": ("F4",), "F4d_dateonly": ("F4d",)}

MARKET_COLS_OUTCOME_FREE = ["market_id", "event_id", "category", "market_start_time", "close_time", "expiration_time"]


def trade_files():
    files = sorted(glob.glob(f"{DATA}/trades/year=*/month=*/day=*/data.parquet"))
    out = []
    for f in files:
        m = re.search(r"year=(\d+)/month=(\d+)/day=(\d+)/", f)
        out.append((f, dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))))
    return out


def parse_utc_ns(s):
    """ISO string ('...Z' or '+00:00') -> numpy datetime64[ns] (UTC)."""
    d = dt.datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(dt.timezone.utc).replace(tzinfo=None)
    return np.datetime64(d, "ns")


def load_v5():
    """market_id(str) -> v5 record (status, family, instant, a16_masked, n_distinct_trace_instants)."""
    out = {}
    with open(f"{DATA}/v5_instants.jsonl") as fh:
        for line in fh:
            r = json.loads(line)
            out[str(r["market_id"])] = dict(status=r["status"], family=r["family"], instant=r["instant"],
                                            a16_masked=bool(r["a16_masked"]),
                                            n_inst=len({t["instant"] for t in r["trace"]}))
    return out


def load_f1_onchain():
    """market_id(str) -> PN-1 creation-time on-chain instant, final_status ok rows only."""
    rows = json.load(open(f"{DATA}/F1_onchain_instants_final.json"))
    return {str(r["market_id"]): r["onchain_instant"] for r in rows if r["final_status"] == "ok"}


def load_markets_outcome_free():
    t = pq.read_table(f"{DATA}/markets.parquet", columns=MARKET_COLS_OUTCOME_FREE)
    return t


def binary_market_ids():
    """Market ids (int) present in predictions.parquet whose every token has n_outcomes == 2 (no winner column read)."""
    p = pq.read_table(f"{DATA}/predictions.parquet", columns=["market_id", "n_outcomes"]).to_pandas()
    g = p.groupby("market_id")["n_outcomes"].agg(["min", "max"])
    return set(g.index[(g["min"] == 2) & (g["max"] == 2)].astype(int))


def deadline_for(mid, v5rec, onchain):
    """(deadline ns, source) for a v5 status-ok market; PN-1 on-chain instant replaces Gamma instant for F1."""
    if v5rec["family"] in F1_FAMILIES and mid in onchain:
        return parse_utc_ns(onchain[mid]), "pn1_onchain"
    return parse_utc_ns(v5rec["instant"]), "v5_gamma"


def classify(delta_ns):
    """EARLIER: delta < -24h; MATCH: |delta| <= 24h; LATER: delta > +24h. delta = field - text deadline."""
    if delta_ns < -CLASS_HALF_WIDTH_NS:
        return "EARLIER"
    if delta_ns > CLASS_HALF_WIDTH_NS:
        return "LATER"
    return "MATCH"


def sha256_ids(ids):
    return hashlib.sha256("\n".join(sorted(str(i) for i in ids)).encode()).hexdigest()

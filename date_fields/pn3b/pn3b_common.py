"""PN-3b shared constants and outcome-free helpers.

Protocol: research/public_note/PN-3b_fresh_sample_prereg.md (frozen at 589f667). Readings: DEVIATIONS.md here.
Nothing in this module reads an outcome column. Generic loaders are reused from ../pn3/pn3_common.py (unchanged).
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "pn3"))
import pn3_common as p3  # noqa: E402  (DATA, trade_files, load_f1_onchain, binary_market_ids, sha256_ids, ...)

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = p3.DATA
ERA_CUTOFF = np.datetime64("2025-01-01T00:00:00", "ns")   # population needs >= 1 trade at or after this
HOUR_NS = 3_600 * 10**9
MATCH_HALF_NS = 36 * HOUR_NS        # MATCH: -36 h <= delta <= +36 h
OUTER_NS = 72 * HOUR_NS             # EARLIER: delta < -72 h; LATER: delta > +72 h
MECH_WINDOW_NS = 1 * HOUR_NS
SEED = 20261113
N_BOOT = 10_000
PCT_LO_IDX, PCT_HI_IDX = 249, 9_749  # 1-based order statistics 250 and 9,750
F1_FAMILIES = ("F1i", "F1x")
CLASSES = ("EARLIER", "GAP_NEG", "MATCH", "GAP_POS", "LATER")


def classify(delta_ns):
    if delta_ns < -OUTER_NS:
        return "EARLIER"
    if delta_ns < -MATCH_HALF_NS:
        return "GAP_NEG"            # -72 h <= delta < -36 h (excluded from tests, counted)
    if delta_ns <= MATCH_HALF_NS:
        return "MATCH"
    if delta_ns <= OUTER_NS:
        return "GAP_POS"            # +36 h < delta <= +72 h (excluded from tests, counted)
    return "LATER"


def load_v5_full():
    """market_id(str) -> dict(status, family, instant, primary, a16_masked, n_inst)."""
    out = {}
    with open(f"{DATA}/v5_instants.jsonl") as fh:
        for line in fh:
            r = json.loads(line)
            out[str(r["market_id"])] = dict(status=r["status"], family=r["family"], instant=r["instant"],
                                            primary=bool(r["primary"]), a16_masked=bool(r["a16_masked"]),
                                            n_inst=len({t["instant"] for t in r["trace"]}))
    return out

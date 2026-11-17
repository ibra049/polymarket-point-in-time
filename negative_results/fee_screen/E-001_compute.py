"""E-001 decision rule applied to published rows (arXiv 2609.12878v1). Deterministic, no I/O besides stdout/JSON."""
import json
import sys

RATES = {"Crypto": 0.07, "Politics": 0.04, "Sports": 0.05, "Finance": 0.04,
         "Weather": 0.05, "Culture": 0.05, "Tech": 0.04}
AGG_MIN, AGG_MAX = 0.04, 0.07  # lowest non-zero / highest category rate
# Local half-spread medians, cents per $ (Aug 20-21 2026 snapshots, db sha256 prefix 1fb018c6c3e0dc74).
S_BY_BIN = {"[0.90,0.95)": 1.667, "[0.95,0.99)": 1.117, "[0.99,1.00)": 1.051}

# (source, label, G, G_hi or None, taker_specific, rate_min, rate_max, p_low, p_high)
ROWS = [
    ("T16A", "taker, equal child markets", -0.460, -0.405, True, AGG_MIN, AGG_MAX, .90, .99),
    ("T16A", "taker, pooled", 0.877, 1.210, True, AGG_MIN, AGG_MAX, .90, .99),
    ("T6A", "all buys, equal child", 0.277, 0.312, False, AGG_MIN, AGG_MAX, .90, .99),
    ("T6B", "all buys, pooled", 0.83, 1.07, False, AGG_MIN, AGG_MAX, .90, .99),
    ("T6C", "all buys, equal parent event", 0.392, 0.40, False, AGG_MIN, AGG_MAX, .90, .99),
    ("T12", "all buys, pooled, >=95c cutoff", 0.560, None, False, AGG_MIN, AGG_MAX, .95, .99),
    ("T13", "all buys, equal child, 90-99c", 0.187, 0.265, False, AGG_MIN, AGG_MAX, .90, .99),
    ("T13", "all buys, pooled, 90-99c", 1.729, 2.209, False, AGG_MIN, AGG_MAX, .90, .99),
    ("T16A", "maker (posted offer), equal child [maker - not taker test]", 0.641, 0.675, False, AGG_MIN, AGG_MAX, .90, .99),
    ("T16A", "maker (posted offer), pooled [maker - not taker test]", 0.816, 1.025, False, AGG_MIN, AGG_MAX, .90, .99),
]
TABLE8 = {  # category: (A_G, A_hi, B_G, B_hi)
    "Crypto": (0.643, 0.697, 0.537, 0.745), "Politics": (1.04, 1.184, 1.419, 1.982),
    "Sports": (-0.230, -0.174, 0.137, 0.373), "Finance": (0.085, 0.353, 1.826, 2.465),
    "Weather": (0.502, 0.585, 0.031, 0.358), "Culture": (0.735, 0.954, 0.829, 1.308),
    "Tech": (0.816, 1.174, 0.846, 1.464),
}
for cat, (ag, ah, bg, bh) in TABLE8.items():
    r = RATES[cat]
    ROWS.append(("T8A", f"{cat}, equal child", ag, ah, False, r, r, .90, .99))
    ROWS.append(("T8B", f"{cat}, pooled", bg, bh, False, r, r, .90, .99))


def s_max(p_low: float) -> float:
    # Most expensive covered bin, per the SURVIVE rule's "most expensive fee and spread".
    return max(v for k, v in S_BY_BIN.items() if float(k[1:5]) >= p_low - 1e-9)


out = []
for src, label, g, g_hi, taker, rmin, rmax, plo, phi in ROWS:
    g_hi = g if g_hi is None else g_hi
    f_min = rmin * (1 - phi) * 100
    f_max = rmax * (1 - plo) * 100
    s = 0.0 if taker else s_max(plo)
    verdict = "KILL" if g_hi <= f_min else "SURVIVE" if g - f_max - s > 0 else "OPEN"
    out.append(dict(source=src, row=label, G=g, G_hi=g_hi, F_min=round(f_min, 3), F_max=round(f_max, 3),
                    S=s, net_worst=round(g - f_max - s, 3), verdict=verdict))
json.dump(out, sys.stdout, indent=1)

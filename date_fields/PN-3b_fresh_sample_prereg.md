# PN-3b: fresh-sample test of whether date fields encode the outcome (pre-registration)

- **Design:** Claude. **Build:** a Claude subagent. **Interpretation:** Codex.
- **Written:** 2026-11-11, after PN-3 and before any PN-3b outcome is read.
- **Why it exists:** PN-3's ±24 h boundary mostly captured a midnight-UTC vs
  end-of-day-ET convention (`PN-3_design_critique_claude.md`). PN-3's frozen
  REJECT stands. PN-3b asks the intended question again, on markets PN-3 never
  touched, with bands set **only** from the outcome-free Δ distribution seen in
  PN-3.
- **Disclosed prior knowledge:** PN-3's reported-only secondary found F1
  close_time D = +0.42 in the zone sample. That knowledge is why H2 is tested
  here on fresh data.

## Sample (disjoint from PN-3; holdout-protected)
- **Population:** binary, resolved Users v1.3 markets (@ 91ddb961) of v5
  family F1 (F1i or F1x), not A16-masked, with **at least one trade on or after
  2025-01-01**. This makes them disjoint from the PN-3 zone by construction.
- **Holdout guard:** exclude every market whose `event_id` contains any market
  with v5 `primary = true`, in any era. That keeps every outcome read here out
  of the E-003, E-004 and E-005 populations and their holdouts, which use only
  primaries. F1 itself is outside all primaries (A14).
- **Deadline:** the PN-1 creation-time on-chain instant where final_status is
  ok, otherwise the v5 Gamma instant.
- **Excluded:** null event_id, null outcome, null date field. Each is counted.

## Classes (Δ = date field − deadline)
| Class | Δ |
|---|---|
| MATCH | −36 h ≤ Δ ≤ +36 h |
| EARLIER | Δ < −72 h |
| LATER | Δ > +72 h |
| Gap bands (excluded from tests, counted) | −72 h ≤ Δ < −36 h, and +36 h < Δ ≤ +72 h |

## Hypotheses (two separate tests; each status reported)
- **H1 (expiration_time):** D1 = P(YES | EARLIER) − P(YES | MATCH).
  - Prediction: **none.** PN-3 gave no usable signal for this field.
- **H2 (close_time):** D2, defined the same way with close_time.
  - Prediction: D2 > 0, from PN-3's secondary.
- **CI:** 95% event-cluster bootstrap, 10,000 resamples, seed 20261113, fresh
  `numpy.random.default_rng(20261113)` per statistic, percentiles 250 and
  9,750. Clusters are the events with a market in either compared class.
- **Frozen status rule, per hypothesis, checked in order** (a recommendation;
  the owner disposes):
  - DATA-BLOCKED: EARLIER < 30 markets or < 10 events, or MATCH < 100 markets.
  - PROMOTE (dependence established): |D| ≥ 0.20 and the CI excludes 0.
  - REJECT: the CI includes 0 and |D| < 0.10.
  - INCONCLUSIVE: anything else.
- **Two tests:** both are reported. A PROMOTE on one does not change the
  other's status.

## Also reported (descriptive, no status)
- LATER vs MATCH, for each field.
- Outcome-free: the share of EARLIER markets whose expiration_time / close_time
  is within 1 h of the other field, and the median Δ per class.
- The same tables by Users v1.3 category: counts only, plus P(YES), no tests.

## Run discipline
- **Order:** stage-1 outcome-free counts, then the code commit, then a single
  run, then the output commit. The output commit subject carries no status or
  number.
- **Interpretation:** Codex interprets. One review round.

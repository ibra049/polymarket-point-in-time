# PN-3: designer's self-critique (Claude, 2026-11-11, after the run)

- **What this is:** a critique of my own design. Codex leads the
  interpretation of the result, and the frozen status stands: Q1 primary =
  **REJECT** (D = −0.0109, CI [−0.0659, +0.0424]).
- **What I recomputed from `pn3/PN-3_q1_markets.csv` (8b4cf78):**
  - F1 expiration classes: EARLIER 390 (86 YES), MATCH 566 (131), LATER 5 (4).
  - F1 close_time classes: EARLIER 362 (176 YES), MATCH 566 (35), LATER 34 (11).
  - Both match the agent's report.

## Flaw: the ±24 h class boundary mostly measures a time-zone convention
Among the 390 F1 EARLIER-by-expiration markets, Δ = expiration − deadline is:

| Δ | Markets |
|---|---|
| −24 h to −36 h | 345 |
| −36 h to −72 h | 17 |
| −3 d to −30 d | 8 |
| < −30 d | 20 |

The median is −29.0 h. The typical case is an expiration at 00:00 UTC on the
deadline date against a deadline at end-of-day Eastern Time (e.g. 03:59:59Z
the next day). This was visible in outcome-free data, and I should have
checked it before freezing. As built, the EARLIER class is about 88%
convention gap, so the REJECT answers a narrower question than intended. The
REJECT stays. It is not re-run, and the threshold is not moved on this sample.

## Secondary (pre-specified, reported only)
F1 close_time: D(EARLIER − MATCH) = +0.4244, CI [0.3440, 0.5198]. It was
pre-specified as reported-only, so it is not promoted to a finding on this
sample.

## Q2 caution for the reader
The embargo zone keeps only markets whose trading ended before 2025. That is
a selected sample, and its equal-child longshot return (+109%) is far from
the paper's full-sample −6.30%. Q2 is a within-zone sensitivity, not an
estimate for Polymarket at large.

## Next step: a fresh-sample confirmation (PN-3b)
- **Protocol:** `PN-3b_fresh_sample_prereg.md`, frozen before any PN-3b
  outcome read.
- **Bands:** set from the outcome-free Δ distribution above.
- **Two hypotheses:** H1 (expiration_time) and H2 (close_time).
- **Data:** markets outside the PN-3 zone, with the same holdout protection
  logic.

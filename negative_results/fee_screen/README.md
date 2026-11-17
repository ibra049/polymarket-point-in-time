# E-001: do taker fees (schedule as of 2026-10-05) remove the published favorite edge?

**Question.** A well-documented Polymarket anomaly is the favorite-longshot bias. The replicated
study (`../../reproduction/`) finds that favorites (prices of 90¢ or more) earn small positive gross
returns. Polymarket now charges takers `fee = rate × p × (1 − p)`. Does that fee alone rule out
buying favorites as a taker, before any new data is collected?

**Design.** A screen on the paper's own published gross estimates (arXiv 2609.12878v1, Tables 6, 8, 9,
12, 13 and 16). There is no new return estimate.
- **Protocol:** `E-001.yaml`, frozen 2026-10-05 05:19 −04:00 (commit `c03eb7e` of the author's
  working repository) before any input was extracted.
- **Run:** 2026-10-05 05:36 −04:00 (commit `e4f815c`).
- **Fee schedule:** taken from Polymarket's fee documentation as of 2026-10-05. The rates (0.04–0.07
  for the relevant categories) are inline in the script.

**Decision rule (frozen), per published row.**
- G is the gross return; G_hi is the upper end of its CI.
- **KILL:** G_hi ≤ F_min. Even the cheapest applicable fee consumes the best-case gross return.
- **SURVIVE:** G − F_max − S > 0. A return remains under the most expensive fee and, for blended rows,
  spread.
- **OPEN:** neither condition holds.
- **Overall:** the taker variant is rejected only if every row is KILL. Otherwise the study proceeds to
  a full test.

## Result
| Row (taker-specific, Table 16A) | Gross, % per $ (95% CI) | Worst-case net, ¢ per $ | Verdict |
|---|---|---|---|
| Taker buys ≥ 90¢, equal weight per market | −0.460 (−0.515, −0.405) | −1.16 | KILL |
| Taker buys ≥ 90¢, pooled by dollars | +0.877 (0.544, 1.210) | +0.18 | SURVIVE (screen) |

- **Equal-weight taker favorite buying** is ruled out: it is negative even before fees.
- **The dollar-weighted version** is not ruled out by this screen. The status is a screen outcome, not
  an edge:
  - its point estimate nets +0.18¢ per $ at the worst-case fee;
  - the lower end of its CI nets −0.16¢ per $;
  - the positive estimate appears only when weighting by dollars, so it is driven by large markets.
- The full list of 24 rows (blended rows are charged a half-spread) is in `E-001_result.json`.
- The full test (E-003) was frozen but not run. This repository makes **no** trading claim.

## Rerun
```
python E-001_compute.py > out.json && cmp out.json E-001_result.json   # byte-identical (checked 2026-11-16)
```
- **Inputs:** the script has no inputs. The published table values, the fee rates and the half-spread
  medians are constants in the file.
- **Half-spreads:** they apply only to blended rows, not to the two taker rows above. They come from
  the author's own order-book snapshots of 2026-08-20/21, which are not shipped.
- **Check:** the arithmetic was recomputed independently from the paper tables, and it matched.

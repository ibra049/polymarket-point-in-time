# Where every number in the note comes from

Each number in `note.md` / `note.pdf` is listed with the file that produces it and how far
it has been checked.

| Label | Meaning |
|---|---|
| **IND** | Recomputed by a second implementer with separate code, and it matched (records in `../independent_checks/` or the folder named). |
| **RERUN** | Our code, re-run on 2026-11-12 with byte-identical output. |
| **SELF** | Computed by our code, file given; no independent recompute. |
| **EXT** | Quoted from an external source. |

| § | Number | Source in this repository | Label |
|---|---|---|---|
| 2, 3 | 588,287,492 trades | `reproduction/checks.json`; `independent_checks/replication/` | IND + RERUN |
| 3 | 12 of 12 checks pass | `reproduction/checks.json`; `reproduction/rerun_2026-11/diff_vs_recorded.json` | RERUN |
| 3 | 560,909,624 return-sample purchases | same; `independent_checks/replication/` | IND + RERUN |
| 3 | taker favorites +0.8775% (paper +0.877%); makers +0.8163% (paper +0.816%) | same; paper Table 16A | IND + RERUN / EXT |
| 3 | 28,554 trades without a market id; funnel gaps 28,554 and 28,446; none with a known payoff | `independent_checks/replication/r0a_codex/null_market_diagnostic.json` | IND (same-rows identity with the paper not established) |
| 3 | 39 multi-outcome markets with no trades | `reproduction/README.md`; `independent_checks/replication/r0a_codex/first_pass.json` | IND |
| 3 | 1,218 trade files re-hashed, 24,309,274,723 bytes, 0 mismatches | `reproduction/rerun_2026-11/checksums_reverified.json` | SELF |
| 3 | 46 transactions, 56 fills, 25 MINT / 5 MERGE, within 10⁻⁶ | `reproduction/onchain_spot_checks/` | SELF |
| 3 | 55 of 55 values byte-identical, 55 min | `reproduction/rerun_2026-11/` | SELF |
| 4.1 | 5,744 audited / 5,559 verifiable / 185 unverifiable | `deadline_edits/summary.json` | IND |
| 4.1 | 38 material edits (0.68%), 20 events; 31 later (median +58.96 d), 7 earlier (median 92.04 d) | `deadline_edits/deadline_edits.csv` | IND |
| 4.1 | 3 events hold 21 of 31 extensions | derived from `deadline_edits/deadline_edits.csv` | IND (derived) |
| 4.1 | 51 creation-text errors | `deadline_edits/creation_text_errors.csv` | SELF |
| 4.1 | 16 of 38 edits align the description with the title | reading of `deadline_edits/deadline_edits.csv`, not pre-registered | SELF (observation) |
| 4.1 | on-chain events exist for 98% of audited markets | (5,744 − 120) / 5,744 | SELF |
| 4.2 | 727,053 population; 1,000 verified; 372 replaced (362 crypto); 989 events | `edit_rate/PN-2_result.json`, `edit_rate/draws.json`; `independent_checks/edit_rate/` | IND |
| 4.2 | title 7/1,000; deadline 1/641 (24 h earlier); on-chain update 8/1,000; creator-only 5/991; all CIs | same | IND |
| 4.2 | 0.73% of questions with creator clarifications | Nechepurenko (2026), arXiv 2609.15368 | EXT |
| 4.3 | paper Table 14 range −13.1% to +30.7% | arXiv 2609.12878, Table 14 | EXT |
| 4.3 | PN-3: D = −0.011 [−0.066, +0.042], REJECT | `date_fields/pn3/PN-3_result.json` | IND |
| 4.3 | 345 of 390 early markets at 24–36 h | `date_fields/pn3/PN-3_q1_markets.csv` | SELF |
| 4.3 | PN-3b `close_time`: +44.3 pts [36.4, 53.5]; 649/1,292 vs 113/1,908 | `date_fields/pn3b/PN-3b_result.json` | IND |
| 4.3 | PN-3b `expiration_time`: +18.6 pts [10.4, 27.6]; 93/221 vs 694/2,954 | same | IND |
| 4.3 | 3,338 markets, 1,803 events | same | SELF (consistent with the IND counts) |
| 5 | mirrored book: 6,432 pairs; minimum ask sum $1.001 | `negative_results/mirrored_book_result.json`; `independent_checks/negative_results/` | IND |
| 5 | baskets: 105 complete event-snapshots (104 size-feasible), 24 events; 0 above 0.5¢; 1.8¢ gross, −0.48¢ net | `negative_results/negrisk_basket/E-002_result.json`; same | IND |
| 5 | fee screen: −0.405% best-case gross (equal weight); +0.18¢/$ point estimate at worst-case fee (dollar weight) | `negative_results/fee_screen/E-001_result.json` | IND |
| 5 | E-006: INVALID-RUN; 12 of 61 snapshots failed (limit 5%); 61 of 260 scheduled snapshots; outage from 11-12 | `options_benchmark/results/output.json`; rerun offline per `options_benchmark/README.md` | IND (independent reviewer applied the frozen rule) + RERUN (offline path, 2026-11-17) |
| 5 | E-006 diagnosis: 16 monotonicity violations in 10 snapshots, 3 bad marks in 3; non-convex source smiles in 61/61 | `options_benchmark/E-006_result.md`, `options_benchmark/R-039_diagnosis_review.md` | IND (diagnostic by one reviewer, mechanism corrected by the other) |
| 1 | 1,549 clarifications on 1,350 of 185,550 questions | Nechepurenko (2026) | EXT |

SELF numbers are disclosed as such in the note's limitations section.

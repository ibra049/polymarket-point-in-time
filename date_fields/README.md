# Do the dataset's date fields encode the outcome? (PN-3, PN-3b)

**Question.** Users v1.3 gives every market two closing dates.
- `expiration_time`: documented as "scheduled expiration / settlement time".
- `close_time`: documented as "when trading closed (resolution time when
  settled)".

Are these fields statistically related to how the market resolved? If a
backtest filters on such a field, it filters on the outcome. The study
replicated in `reproduction/` restricts samples by "scheduled closing dates"
in its Table 14, without naming the column. Sources for the field
definitions are in `field_definitions_sources.md`.

## Hold-out protection
Outcomes were read only where they cannot overlap a separate, still-unrun
pre-registered study.
- **PN-3:** markets whose event had no trade after 2024-12-31.
- **PN-3b:** markets of type "will X by ⟨date⟩" in events that contain no
  market from that study's population.

## PN-3: first test (`PN-3_closing_date_leak_prereg.md`)
- **Sample:** 962 resolved markets.
- **Result:** P(YES | expiration more than 24 h before the deadline) −
  P(YES | within 24 h) = −0.011, 95% event-cluster CI [−0.066, +0.042].
  Frozen status: **REJECT**.
- **Flaw:** the 24 h boundary was badly chosen. 345 of the 390 "early" markets
  sit 24–36 h early, which is midnight UTC against an end-of-day US Eastern
  deadline (a convention, not an early resolution). The flaw is recorded in
  `PN-3_design_critique_claude.md`. The result was not altered.

## PN-3b: fresh-sample test (`PN-3b_fresh_sample_prereg.md`)
- **Design:** new bands (MATCH within ±36 h; EARLIER more than 72 h early) and
  two separate hypotheses.
- **Sample:** 3,338 resolved markets in 1,803 events, all disjoint from PN-3.

| Field | YES rate, field more than 72 h early | YES rate, field matches deadline | Difference [95% CI] | Frozen status |
|---|---|---|---|---|
| `close_time` | 649 / 1,292 = 50.2% | 113 / 1,908 = 5.9% | +44.3 pts [36.4, 53.5] | dependence established |
| `expiration_time` | 93 / 221 = 42.1% | 694 / 2,954 = 23.5% | +18.6 pts [10.4, 27.6] | inconclusive (|D| below the 20-pt bar) |

**Independent reading** (recomputed from `pn3b/PN-3b_markets.csv`):
- The `close_time` result supports a warning against treating it as a
  scheduled deadline.
- The `expiration_time` result does not establish absence of dependence. Its
  positive association misses the pre-specified threshold.
- These are associations, not causal effects or evidence of an error in the
  replicated paper, whose field choice is unknown.

## Files
- `pn3/`, `pn3b/`: stage-1 outcome-free code and counts, `DEVIATIONS.md`
  (fixed before any outcome read), the run code, outputs and logs.
- The only edit from the committed versions: the default data path in
  `pn3/pn3_common.py` is now `data/users_v1.3`. Set `PN3_DATA` or place the
  dataset there.

## Inputs shipped in `data/`
- `v5_instants.jsonl.gz`: the rule-text deadline parse for every market.
  - Made by `pc1v8_recount.py` with the frozen grammar chain
    (`schedule_grammar_v3/v4/v5.py`).
  - The parse uses the Gamma `description` text fetched 2026-10-07.
  - The grammar passed adversarial fixture tests (`grammar_v*_fixtures.json`)
    and two independent 40-market semantic audits before use.
- `F1_onchain_instants_final.json`: the creation-time on-chain deadlines from
  `deadline_edits/`.

## Rerun
- **Dependencies:** `numpy`, `pyarrow` and `pandas` (`../requirements.txt`).
- **Data directory:** the scripts read `$PN3_DATA`, which must contain:
  - the Users v1.3 files `markets.parquet`, `predictions.parquet`, `user_features.parquet` and
    `trades/`;
  - the two shipped inputs.

  Build that directory with symlinks so nothing is written into your dataset folder.
- **Run time:** each stage-1 script scans all 1,218 trades files, which is the slow step. Each
  run script takes seconds.

```bash
cd date_fields && mkdir -p work/data && cd work
for f in markets.parquet predictions.parquet user_features.parquet trades; do
  ln -s /path/to/users_v1.3/$f data/; done
gunzip -c ../data/v5_instants.jsonl.gz > data/v5_instants.jsonl
cp ../data/F1_onchain_instants_final.json data/
export PN3_DATA=$PWD/data

# PN-3 (outcome-free stage 1, then the single run)
python ../pn3/pn3_stage1.py zone.parquet pn3_stage1_counts.json
python ../pn3/pn3_run.py zone.parquet pn3_stage1_counts.json pn3_out/

# PN-3b
python ../pn3b/pn3b_stage1.py population.parquet pn3b_stage1_counts.json
python ../pn3b/pn3b_run.py population.parquet pn3b_stage1_counts.json pn3b_out/
```

**Check without the trades scan.** The per-market CSVs (`pn3/PN-3_q1_markets.csv`,
`pn3b/PN-3b_markets.csv`) hold every market's class and outcome. The run scripts' own
`q1_table` / `field_result` functions recompute the committed counts, differences and bootstrap
CIs exactly from them.
- Read `event_id` as a string. The bootstrap resamples events in sorted order, and integer
  sorting changes the third decimal of the CIs.
- Outcomes in both CSVs match `markets.parquet` `outcome_yes` for every row. This was checked from
  a fresh clone on 2026-11-16.

# PN-3b build: readings, conservative choices, deviations

- **Protocol:** `research/public_note/PN-3b_fresh_sample_prereg.md`, frozen at `589f667`.
- **Builder:** Claude subagent. **Interpreter:** Codex.
- **Written:** 2026-11-11, before any PN-3b outcome column was opened. Committed with the code and the stage-1
  counts, before the single run.
- No band, seed, threshold, population rule or guard has been loosened. Each item below either reads wording the
  protocol leaves open or makes a choice that only shrinks the data.

## Population
- **P1. F1 rows.** F1 means v5 `status == ok`, family `F1i` or `F1x`, exactly one distinct trace instant, and not
  `a16_masked`. This is the same reading as PN-3, which gives 5,778 markets.
- **P2. "At least one trade on or after 2025-01-01"** is taken from the per-market maximum trade timestamp. The
  scan reads only trades `market_id` and `timestamp`, using the unchanged PN-3 `scan_trades`.
  - Trade rows with a null `market_id` (28,554) cannot be assigned to a market and are ignored.
  - The code asserts that the population is disjoint from the PN-3 zone: every market has max_ts ≥ cutoff,
    while the zone requires max_ts < cutoff.
- **P3. "Binary"** means every token of the market in `predictions.parquet` has `n_outcomes == 2`. All 4,624
  candidates pass.
- **P4. The null-outcome exclusion happens in the run step.** Testing `outcome_yes` for null already opens the
  outcome column, so this exclusion is applied in the run and counted there. The stage-1 counts come before it.
- **P5. A null date field excludes the market from that field's classes only.** The market stays in the other
  field's test. Both are counted (`field_null_excluded`): expiration_time 72, close_time 35 at stage 1.
- **P6. Deadline.** Where PN-1 has a `final_status == ok` row, its `onchain_instant` is used (4,543 markets).
  Otherwise the v5 instant is used (72).

## Holdout guard
- **G1. Literal rule.** A market is excluded if its `event_id` (from `markets.parquet`) contains any market with v5
  `primary == true`, in any era. That is 52,532 events.
- **G2. Conservative additions, which only shrink the data.**
  - Also excluded: events that contain an A16-masked market. These are timed F3/F4 markets that would be
    primaries without the mask (1 event).
  - Also excluded: events that contain a market with no v5 record, whose primary status is unknown (14 events).
  - In total, the guard removes 9 of the 4,624 candidate F1 markets.
- **G3. How outcomes are read.** `markets.outcome_yes` is read through a parquet row filter that lists only the
  4,615 guarded population ids. No trade file is opened in the run step.

## Classes and bootstrap
- **C1. Bands as frozen,** with Δ in exact integer nanoseconds:
  - EARLIER: Δ < −72 h;
  - GAP_NEG: −72 h ≤ Δ < −36 h;
  - MATCH: −36 h ≤ Δ ≤ +36 h;
  - GAP_POS: +36 h < Δ ≤ +72 h;
  - LATER: Δ > +72 h.

  The gap bands are counted and excluded from the tests.
- **B1. Bootstrap as frozen.** 10,000 resamples, a fresh `numpy.random.default_rng(20261113)` per statistic, and
  the 250th and 9,750th of the sorted draws (1-based). The clusters are the events with a market in either
  compared class.
- **B2. Status rule as frozen,** applied to H1 and H2 separately. LATER vs MATCH gets a D with a CI and no status.
- **B3. Undefined draws (pre-declared, same as PN-3).** A draw is undefined when a resample has no market of one
  class. If any draw is undefined, the count is reported and the CI uses ceil(0.025·n) and ceil(0.975·n) of the
  defined draws.

## Descriptive items
- **D1. "Within 1 h of the other field"** means |expiration_time − close_time| ≤ 1 h. It is reported per class
  for each field's classes, together with the median Δ per class in hours.
  - Stage 1 reports both before the null-outcome exclusion.
  - The run repeats them on the final population.
- **D2. Category** is the `category` column of `markets.parquet`. Per class, the run reports counts and P(YES),
  with no tests. In the stage-1 `by_category_counts`, the key `nan` is the field-null count.
- **D3. Stop rule.** It triggers if EARLIER < 30 markets for both fields. At stage 1, EARLIER is 306 for
  expiration_time and 1,381 for close_time, so the rule did not trigger and the run proceeds.
- **D4. Outputs.** `PN-3b_result.json`, `PN-3b_markets.csv` (per market: classes, Δ, deadline source, outcome)
  and `PN-3b_run.log`.

## Testing before the run
- **T1. Fake-outcome dry run.** Before the commit, `pn3b_run.py --dry-run-fake-outcomes` ran end to end. In that
  mode it never opens an outcome column; fake outcomes come from an md5 hash of the id. The output was discarded.

## Observations, not analysed
- None beyond the counts in `PN-3b_stage1_counts.json`.

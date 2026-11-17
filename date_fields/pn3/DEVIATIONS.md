# PN-3 build: readings, conservative choices, deviations

- **Protocol:** `research/public_note/PN-3_closing_date_leak_prereg.md`, frozen at `26f4a9d`.
- **Builder:** Claude subagent. **Interpreter:** Codex.
- **Written:** 2026-11-11, before any outcome column was opened. Committed with the code and the stage-1 counts,
  before the single run.
- No threshold, class boundary, seed, population or zone rule has been changed. Every item below is either a
  reading of wording that the protocol leaves open, or a choice that only shrinks the data used.

## Zone (holdout protection)
- **Z1. Markets with no trades are excluded.** The market rule ("no trade on or after 2025-01-01") is trivially
  true for a market with no trades, and such a market's era cannot be checked from trades. 114,250 markets.
- **Z2. Markets with a null `event_id` are excluded** (9), because the event rule cannot be checked for them.
- **Z3. Event membership comes from `markets.parquet` `event_id`.** As instructed, the trade scan reads only
  `market_id` and `timestamp`.
- **Z4. Trade rows with a null `market_id`** (28,554 rows on 434 days, counted outcome-free) cannot be assigned
  to a market, so they are not in the zone. See the observations section.
- **Z5. Only trade files dated before 2025-01-01 are opened in stage 3.** Stage 1 checked that every trade file
  holds only timestamps inside its partition day (0 exceptions in 1,218 files). Every file dated 2025-01-01 or
  later therefore holds only trades at or after the cutoff, so it holds no zone-market trade. Stage 3 asserts
  that the number of zone trade rows it reads equals the stage-1 count (17,309,278).
- **Z6. How outcome columns are read.** `markets.outcome_yes` and `trades.winner` are read through a parquet row
  filter that lists only zone market ids. No outcome of a non-zone market reaches the code.

## Q1 population
- **P1. "Family F1" means v5 labels `F1i` and `F1x`.** These are the two F1 variants in `schedule_grammar_v5`.
- **P2. "F4" (reported only) means v5 labels `F4` and `F4d`.** `F4d` is v5's date-only F4. The split is also
  reported (`F4_timed`, `F4d_dateonly`).
- **P3. "status ok, one instant"** is read as: v5 `status == ok`, and exactly one distinct instant in the trace.
  This holds for every ok row. Markets in the A16 named-exclusion mask (`a16_masked`) are also excluded. One zone
  market is affected (503942, F3), so the F1 decision population is unaffected.
- **P4. "Binary"** means every token of the market in `predictions.parquet` has `n_outcomes == 2`. This column is
  outcome-free. All 16,497 zone markets pass.
- **P5. PN-1 replacement.** Where `F1_onchain_instants_final.json` has `final_status == ok`, its
  `onchain_instant` replaces the v5 (Gamma) instant (925 of the 968 zone F1 markets). Other F1 markets keep the
  v5 instant, because the protocol replaces only where a PN-1 instant exists.
- **P6. The "resolved" filter (`outcome_yes` not null) is applied in stage 3.** Testing for null already opens an
  outcome column. The stage-1 class counts are therefore pre-resolution counts, and the frozen DATA-BLOCKED
  rule is applied to the final resolved population.
- **P7. A null field leaves the market out of that field's classes.** A market with a null `expiration_time`
  (or `close_time`) is reported as `field_null` for that field (F1: 1 market for `expiration_time`).
- **P8. Class boundaries are as frozen,** with Δ in exact integer nanoseconds: EARLIER Δ < −24 h, MATCH |Δ| ≤ 24 h,
  LATER Δ > +24 h.

## Bootstrap
- **B1. Clusters.** For D(A vs B), events with at least one market in class A or class B are resampled with
  replacement: 10,000 resamples, each of size equal to the number of such events.
- **B2. CI.** The 95% CI is the 250th and 9,750th values (1-based) of the 10,000 sorted draws.
- **B3. Seed.** `numpy.random.default_rng(20261112)` is created fresh for each statistic, so a number does not
  depend on the order the statistics are computed in. The protocol gives no seed for Q2, so Q2 uses the same
  seed the same way.
- **B4. Undefined draws (pre-declared).** A draw is undefined if a resample contains no market of one class. If
  any draw is undefined, the count is reported and the CI uses the same order-statistic rule on the defined draws
  (ceil(0.025·n) and ceil(0.975·n)). This matters only for very small classes (e.g. F1 LATER, 5 markets). It
  cannot apply to the primary statistic unless EARLIER is tiny, and DATA-BLOCKED catches that case first.
- **B5. Status rule, as frozen and in order.**
  - DATA-BLOCKED: EARLIER < 30 markets or < 10 events, or MATCH < 100 markets.
  - PROMOTE: |D| ≥ 0.20 and the CI excludes 0 (lo > 0 or hi < 0).
  - REJECT: the CI includes 0 and |D| < 0.10.
  - Otherwise INCONCLUSIVE.

## Reported alongside (as the protocol lists)
- **R1. D with a CI for every comparison.** LATER vs MATCH, the `close_time` table, and F2/F3/F4 each get D with
  the same bootstrap CI. They are reported only, not used in any decision.
- **R2. The mechanism check is reported twice.** Stage 1 runs it outcome-free on the pre-resolution F1
  population. Stage 3 repeats it on the resolved F1 population.

## Q2
- **Q2-1. Ledger.** The ledger is the step-0 ledger (`e003_step0_reproduction.py`), restricted to zone markets,
  with purchases at price < 0.10 and a known winner. Filters, buyer attribution, cost, pnl, pooled and
  equal-child definitions are copied unchanged.
  - Stage 3 also runs a verbatim zone-restricted copy of the step-0 loop. It asserts that pooled and
    equal-child longshot returns and purchase counts equal the PN-3 ledger baseline (|diff| < 1e-9 pp).
  - The published step-0 values are full-window, so they cannot be compared with zone values directly.
- **Q2-2. Deadline subset.** Zone markets with v5 status ok (any family), one instant, not A16-masked, and both
  `expiration_time` and `close_time` non-null: 8,379 markets, 4,245 events. 42 markets are dropped for a null
  field.
  - Binary is not required beyond the ledger's two-outcome token filter.
  - Definition (c), the rule-text deadline, uses the same deadline as Q1, including the PN-1 replacement for F1.
- **Q2-3. "Scheduled to close no later than N days after purchase"** is read literally: keep the purchase if
  S − t ≤ N × 24 h, where t is the trade timestamp.
  - This includes purchases made after S (S < t). Their count and dollars under each definition are reported
    as an outcome-free diagnostic. No alternative row is computed.
- **Q2-4. Dollar flows between (a) and (c), for each N.**
  - Dollars in (a) but not (c) are reported as a share of the (a) row's dollars ("leave").
  - Dollars in (c) but not (a) are reported as a share of the (c) row's dollars ("enter").
  - Purchase counts are reported for both.
- **Q2-5. Two baselines are reported:** all zone markets (the protocol's "zone baseline"), and the deadline
  subset with no restriction.

## Testing before the run
- **T1. Fake-outcome dry run.** Before the code was committed, `pn3_run.py --dry-run-fake-outcomes` ran end to end.
  - In that mode it never opens an outcome column: fake outcomes come from an md5 hash of the id.
  - The dry-run output was discarded and is not a result.
  - The stage-1 row rebuild, the zone-row-count assertion and the step-0-replica assertion all passed in the
    dry run.

## Observations, not analysed
- **O1. Null `market_id` rows.** The trades table holds 28,554 rows with a null `market_id` (434 days, the first
  on 2023-06-26). This equals the paper's 28,554-row drop at its two-outcome stage (E-003 step-0 log). It is
  noted only, not investigated.
- **O2. Some EARLIER markets sit only just past the boundary** (seen while checking the CSV format in the
  dry run). An example is 244621: its deadline is 2023-01-01 04:59:59Z (end of day ET), and its
  `expiration_time` is 2022-12-31 00:00:00Z. Its Δ is about −29 h, so it falls in EARLIER under the frozen
  ±24 h boundary. These markets were not counted or analysed.

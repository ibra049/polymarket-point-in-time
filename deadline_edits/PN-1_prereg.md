# PN-1: deadline-edit audit for the public note (pre-registration)

- **Author:** Claude (builds it). **Verifier:** Codex re-derives every count on its own.
- **Written:** 2026-11-11, committed before any count below is computed.
- **Question:** For the 5,744 "by <deadline>" (F1) markets in A13, how many
  had their question-text deadline changed after the on-chain creation
  record? How big were the changes? How many distinct events are they?
- **Inputs (all already on disk, A13 of 2026-10-08):**
  `polysignal-data/users_v1.3/F1_onchain_instants_final.json` (5,744 rows),
  `markets.parquet` / `events.parquet` from Users v1.3 @ 91ddb961 (non-outcome
  columns only: market_id, event_id, question, slug, market_start_time),
  `gamma_rules.jsonl` (Gamma description text, fetched 2026-10-07).

## What was already seen before this file (disclosure)
Claude printed the first 50 of the 85 rows with `changed = true` (all
statuses). That showed one event with 13 markets moved +58 days together, and
several rows that differ by 59 seconds or 1 minute. The rule below was
written after seeing that. PN-1 is a descriptive measurement, not a
hypothesis test, so nothing here is a pass or fail threshold. Every row is
still reported.

## Frozen classification (applied to every row with final_status ok and changed = true)
Let Δ = current Gamma instant − creation-time on-chain instant.
1. **FORMAT:** |Δ| < 1 hour. These are restatements like 11:59:59 PM vs
   11:59 PM, or 11:59 PM vs midnight. They are reported, but they are not
   counted as material edits.
2. **MATERIAL-LATER (extension):** Δ ≥ 1 hour.
3. **MATERIAL-EARLIER:** Δ ≤ −1 hour.

Each class is reported by market and by distinct `event_id`. The size of
each material edit is reported as a list and as the median |Δ| in days.

## Also reported (separate, never mixed into the counts above)
- The 51 A13a creation-text errors: the on-chain deadline is not after the
  creation time, typically a wrong year later corrected. This is a different
  failure, a stale or typo deadline at creation, and it is listed separately.
- The A13 headline as recorded on 2026-10-08 (42 = 32 later + 10 earlier),
  recomputed from the same file. If the recount differs, the recount wins and
  the difference is explained.

## Outcome use
None. The audit uses no outcomes, returns or prices. F1 is outside every live
study's population (A14), but PN-1 still does not read outcome columns.

## Release
Public list: market_id, event_id, question slug, creation-time instant,
current instant, Δ, and class. Also released: the code to recompute it from
public sources (Users v1.3 on Hugging Face, Gamma API, Polygon logs). There
are no secrets and no infrastructure details. A short note on what the method
cannot see: **when** an edit happened is unknown. We see only the creation
record and the October 2026 text, so intermediate edits are invisible.

## Stopping condition
The counts are computed once, by script, from the files above, and written
to `PN-1_result.json`. Codex recomputes them on its own. Any disagreement is
recorded rather than argued (one round).

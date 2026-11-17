# PN-3: does the dataset's "closing date" encode the outcome? (pre-registration)

- **Design:** Claude. **Build:** a Claude subagent. **Interpretation:** Codex.
- **Written:** 2026-11-11, committed before any outcome is read for this question.
- **Already seen** (outcome-free, from the A5 record of 2026-10-05):
  - For 79,175 text-dated markets, `expiration_time` lies within 1 day of the
    question-text deadline in 96.0%, later in 2,021, and earlier in 1,124.
    In Politics, 23.8% differ.
  - A5 noted that "expiration earlier than the stated deadline fits early
    resolutions written back into the field". This was never tested,
    because testing needs outcomes.
- **Why it matters:** arXiv 2609.12878 (Table 14) restricts samples by a
  market's "scheduled closing date", and its equal-weight longshot returns
  swing from −6.30% to +30.66% across those restrictions. If the closing-date
  field is rewritten when a market resolves early, such a filter selects on
  the outcome: a look-ahead bias inside the data itself.

## Holdout protection (applies to every outcome read in PN-3)
Only markets in the owner-approved conservative embargo zone are used:
- **Market rule:** the market has no trade on or after 2025-01-01.
- **Event rule:** its event has no market with a trade on or after
  2025-01-01.
- **Basis:** this is the same zone the owner approved for step-0 debugging. It
  keeps every PN-3 outcome away from the E-005 holdout era (instants ≥
  2025-07-01) and from E-005's discovery decisions, which are already frozen.
- **No full-sample recomputation of the published Table 14.** It would touch
  holdout-era outcomes, and that is an owner-only (tier 3) decision.

## Q1, primary: is `expiration_time` outcome-dependent?
- **Population:** binary, resolved markets in the zone (`outcome_yes` not
  null) whose Gamma rules text parses, under frozen `schedule_grammar_v5`
  (`v5_instants.jsonl`), to family **F1** ("will … by <deadline>"), status ok,
  one instant.
  - Where a PN-1 creation-time on-chain instant exists, it replaces the Gamma
    instant.
- **Classes,** by Δ = expiration_time − text deadline:
  - EARLIER: Δ < −24 h;
  - MATCH: |Δ| ≤ 24 h;
  - LATER: Δ > +24 h.
- **Statistic:** D = P(YES | EARLIER) − P(YES | MATCH).
  - 95% CI from an event-cluster bootstrap: 10,000 resamples, seed 20261112,
    percentiles 250 and 9,750.
- **Prediction (Claude, before data):** D > 0, large. Markets that resolve
  YES early get their expiration moved to the resolution date.
- **Frozen status rule** (checked in this order; the status is a
  recommendation, and the owner disposes):
  - DATA-BLOCKED: EARLIER < 30 markets or < 10 events, or MATCH < 100 markets.
  - PROMOTE (dependence established): |D| ≥ 0.20 and the CI excludes 0.
  - REJECT: the CI includes 0 and |D| < 0.10.
  - INCONCLUSIVE: anything else.
- **Reported alongside:**
  - the same statistic for LATER vs MATCH;
  - the same three-way table for `close_time` instead of `expiration_time`;
  - Q1 repeated for families F2, F3 and F4 (reported only, not a decision).
- **Outcome-free mechanism check** (descriptive): the share of EARLIER
  markets whose expiration_time is within 1 h of close_time, against the
  same share in MATCH.

## Q2, reported only: how much does the closing-date field move a Table-14-style result?
- **Construction,** following the paper's Table 14 rows 4–6 inside the zone:
  - Purchases are the reproduction's purchase ledger (paper filters, as in
    the step-0 code), longshot price < 0.10, resolved markets.
  - Keep a purchase if its market is "scheduled to close no later than N days
    after purchase", for N ∈ {1, 7, 30}.
- **"Scheduled close" defined three ways,** each on the same subset of markets
  that have a parsed text deadline (any v5 family):
  - (a) expiration_time;
  - (b) close_time;
  - (c) the rule-text deadline.
- **Report:**
  - pooled and equal-child-market longshot returns, each with an event-cluster
    95% CI;
  - the share of purchase dollars that enter or leave each row between (a)
    and (c);
  - the zone baseline (no closing-date restriction).
- No threshold. Every number is reported. Neither Q2 nor anything else in
  PN-3 makes a claim about returns being exploitable.

## Stopping condition and roles
- **The run:** the code is committed before the run, and runs once. Its
  outputs are `PN-3_result.json` and a per-market CSV for Q1 (market_id,
  event_id, family, class, outcome). The Q1 CSV carries outcomes only for
  zone markets.
- **Interpretation:** Codex reads the result and writes it up. Claude
  designed PN-3 and does not interpret it.
- **Disagreements:** one round, then recorded.

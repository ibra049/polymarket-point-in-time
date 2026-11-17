# Point-in-Time Integrity of Prediction-Market Research Data: An Exact Replication, a Deadline-Edit Audit, and Pre-Registered Null Results on Polymarket

**Ibrahim El Makhtoum** · November 2026 · v1.0

> Every number traces to a file listed in `NUMBERS.md`, which also says how far
> each number has been independently checked.

## Abstract

Backtests on prediction markets usually take market metadata (deadlines,
closing dates) from today's API and treat it as known at the time of each
trade. We test that assumption on Polymarket.

- **Replication.** We first reproduce exactly the published aggregates of a
  588-million-trade study of the favorite–longshot bias (Cardozo and
  Rivero-Wildemauwe, 2026) from its public dataset: 12 of 12 pre-registered
  checks.
- **Deadline edits.** We then compare each market's creation-time question
  text, recovered from on-chain records, with its current API text. Of 5,559
  "by-deadline" markets, 38 (0.68%, in 20 events) had their deadline
  materially changed after creation: 31 extensions (median +59 days) and 7
  moves earlier. In 16 of the 38, the creation-time rules already contradicted
  their own title.
- **Date fields and outcomes.** In a pre-registered test on 3,338 fresh
  markets, the dataset's realized closing time is strongly associated with the
  outcome, as its definition implies. Markets whose *scheduled* expiration lies
  more than three days before their own stated deadline resolve YES 42% of the
  time, against 23% when the two agree: a difference of +19 points
  [95% CI 10, 28]. That is just short of our frozen 20-point threshold for an
  established effect.
- **Population edit rate.** In a pre-registered random sample of 1,000
  verifiable markets, 0.7% had their title changed after creation, 0.16% of
  comparable deadlines moved by at least an hour, and 0.8% had an on-chain
  update to their terms.
- **Null results.** We report pre-registered null results for three simple
  inefficiencies.
- **A forward test that stopped itself.** A forward comparison against
  option-implied probabilities ended INVALID-RUN. Its frozen pipeline check
  failed on 12 of 61 snapshots, against a 5% limit. The failures were traced
  to inconsistent source option data, and the test statistic is not
  interpreted.

All code, lists and frozen protocols are released.

## 1. Introduction

**The problem.** A backtest is only as honest as its timestamps. In equities,
point-in-time data is standard practice after work showed that restated
databases change research results (Banz and Breen, 1986; Ljungqvist, Malloy and
Marston, 2009). Prediction-market research is younger and often relies on API
snapshots.

**Mutable metadata on Polymarket.**
- Market rules can be clarified after trading starts (Polymarket documentation).
- Recent work counts on-chain clarifications: 1,549 creator clarifications on
  1,350 of 185,550 questions (Nechepurenko, 2026). It does not evaluate
  changes to deadlines.
- In a search of arXiv, SSRN, Polymarket's documentation and changelog, and
  Dune (2026-11-11; `prior_art.md`), we found no study that counts
  post-creation deadline edits.
- The same search found no study that tests whether the date fields
  researchers filter on are themselves related to outcomes.

**Our contributions.**
1. An exact, pre-registered replication of a large published study.
2. A creation-time vs. current audit of deadlines, with every flagged
   market's two texts released.
3. A pre-registered test, with a disclosed failed first design and a
   fresh-sample confirmation, of whether date fields encode outcomes.
4. Scoped null results.

Each test's decision rule was committed to version control before the data it
judges was read. Exceptions, disclosed in `PREREGISTRATION.md`:
- the PN-1 classification rule was written after part of the changed list had been seen;
- the mirrored-book check had no numeric threshold;
- the code and output of PN-2 and of E-002 were committed together.

 Each protocol's commit hash and timestamp are listed in the
repository. The full research log is held in a private repository and can be
shared with reviewers on request.

## 2. Data

- **Users v1.3.** We use Polymarket Users v1.3 (Akey, Grégoire, Harvie and
  Martineau, 2026; Hugging Face `vgregoire/polymarket-users`, commit
  `91ddb961`, CC-BY-4.0): 588,287,492 trades from November 2022 to March 2026,
  with market metadata. All 1,218 trade files were verified against the
  published SHA-256 checksums.
- **Creation-time text.** This comes from the `QuestionInitialized` event of
  Polymarket's UMA adapter on Polygon. The question identifier is a hash of
  this text, so the text cannot be altered later.
- **Current text.** We use the Gamma API, fetched 2026-10-07.
- **Order books.** The basket and YES/NO tests use our own one-day capture of
  public order books (2026-08-20/21, every 6 hours), released as an extract.

## 3. Exact replication

We re-implemented the paper's sample filters and return definitions and
pre-registered 12 checks against published values, with tolerances:
- 11 point values (sample counts, dollar totals, pooled and equal-weight
  favorite and longshot returns, taker and maker favorite returns);
- 1 confidence-interval rule.

All 12 pass. For example:
- observed trades 588,287,492 (exact);
- return-sample purchases 560,909,624 (exact);
- taker favorite return +0.8775% vs. published +0.877%;
- maker favorite return +0.8163% vs. +0.816%.

Matching taker and maker returns separately rules out swapped roles.

**Independent second implementation.** Separate code was written from the
paper's definitions. Our script and our check file stayed unopened until its
first-pass numbers were committed. The headline target values were already
known, so this is an independent implementation, not a blinded one.
It reproduces all four headline values:
- observed trades and return-sample purchases exactly;
- taker and maker favorite returns to within 10⁻¹⁵ of our values.

Its first-pass numbers were committed before the comparison.

Intermediate filter counts differ by about 28,000 rows before converging
exactly. The release contains no trades for 39 markets with more than two
outcomes. Separately, 28,554 trade rows carry no market identifier (count
independently re-verified). The second implementation keeps them past the
two-outcome filter. Its intermediate counts then exceed the paper's by exactly
28,554 at that stage, and by 28,446 after the buyer filter. None of these rows
has a known payoff, so they cannot enter the return sample. The counts are
consistent with the paper dropping these rows, but we have not shown that they
are the same rows.

**On-chain spot checks.** Separately, 46 sampled transactions (56 fills,
spanning Jan 2023 to Jan 2026) were checked by script against on-chain
`OrderFilled` logs: shares and prices matched within 10⁻⁶. This revealed a
convention: in all 25 MINT fills and all 5 MERGE fills, the dataset records the
trade on the side the taker did not act on, which is economically equivalent.

**Fresh rerun.** The unchanged original script was re-run on 2026-11-12. All
1,218 trade files were first re-hashed against the Hugging Face manifest. The
output is byte-identical to the 2026-10-08 record: 55 of 55 values, wall time
55 minutes on a laptop.

## 4. Point-in-time audit

### 4.1 Deadline edits after creation (PN-1)

**Population and method.** The population is the 5,744 markets whose question
reads "will … by ⟨deadline⟩". For each, we parse the deadline from the
creation-time on-chain text and from the current API text with the same
frozen parser. 185 markets cannot be verified (no creation event, or the
creation deadline is not after creation). This leaves 5,559.

**Classification** (frozen before counting):
- *format*: a change under one hour;
- *material*: one hour or more.

**Result.**
- 38 material edits in 20 events (0.68%):
  - 31 later, median +58.96 days;
  - 7 earlier, median −92.04 days.
- Edits cluster: three events hold 21 of the 31 extensions.
- A further 51 markets had a creation-time deadline that was already in the
  past, nearly all one-year typos later corrected.

**Why it matters.** A backtest that defines entry by "days before deadline"
using today's text conditions on a decision made after entry: the edit is
information that did not exist when the trade was placed.

**Observation outside the frozen rule.** Reading the 38 pairs side by side
shows that in 16 of them the edit made the rules agree with a title that
already implied the new deadline at creation. A careful backtest therefore
cannot treat either version as ground truth without a consistency check.

We do not observe *when* an edit happened, only the creation record and the
October 2026 text.

### 4.2 How often are market terms changed? (PN-2)

**Sample.** We drew a pre-registered simple random sample of 1,000 markets
(seed fixed in advance) from all 727,053 markets with a question identifier.
Each was compared with its creation-time on-chain text.
- 372 draws had no UMA creation event and were replaced in the frozen order.
  362 of them are crypto markets resolved outside the UMA adapter.
- The rates therefore describe markets with a verifiable UMA creation event.
  They are not unbiased rates for all 727,053 markets. The sample is 69%
  sports and spans 989 events.

| Measure | Rate | Wilson 95% CI | Event-cluster 95% CI |
|---|---|---|---|
| Title text changed after creation | 7 / 1,000 = 0.70% | [0.34%, 1.44%] | [0.20%, 1.29%] |
| Deadline changed by ≥ 1 hour (both texts parse) | 1 / 641 = 0.16% | [0.03%, 0.88%] | [0.00%, 0.48%] |
| At least one on-chain update (any poster) | 8 / 1,000 = 0.80% | [0.41%, 1.57%] | [0.30%, 1.40%] |

**Verification.** Codex recomputed every count and interval independently,
and they match. It regenerated the 2,000-draw order from the seed. It
re-checked 25 random rows and all 14 flagged rows against Polygon, with zero
mismatches. The original code and output were committed together, after their
stated generation time (see `PREREGISTRATION.md`).

**Comparison with other estimates.**
- The update measure counts any poster. Counting only updates by the market's
  creator gives 5 of 991 (supplementary). Nechepurenko (2026) counts creator
  clarifications on 0.73% of questions over a different window. The two
  measures are similar in size but not directly equivalent.
- Deadline edits are rare in the population at large. One market in 641
  comparable ones changed, and its deadline moved 24 hours earlier. Most of
  the 641 are sports fixtures.
- They are more frequent among markets that ask whether something happens
  *by* a date: 0.68% (§4.1).
- Neither the full census in §4.1 nor this sample can say *when* an edit
  happened.

### 4.3 Do date fields encode the outcome? (PN-3, PN-3b)

**Fields and why they matter.** The dataset's documentation defines
`expiration_time` as the "scheduled expiration / settlement time" and
`close_time` as "when trading closed (resolution time when settled)". The
replicated paper restricts samples by "scheduled closing dates" (its Table 14),
where equal-weight longshot returns range from −13.1% to +30.7% across
restrictions. It does not name the column used.

**First test (PN-3).** It used markets whose trading ended before 2025, so
that no outcome data overlapped a live hold-out sample. Under its frozen rule
the result was REJECT for `expiration_time`. However, a ±24-hour class
boundary mostly captured a time-zone convention: midnight UTC vs. end-of-day
Eastern Time, with 345 of 390 "early" markets 24–36 hours early. We disclosed
this and did not alter the result.

**Fresh-sample test (PN-3b).** We pre-registered new boundaries, set from the
outcome-free distribution of differences, and two hypotheses. The sample was
3,338 markets (1,803 events) disjoint from PN-3 and from every live study's
population.

| Field | YES rate, field > 3 days before deadline | YES rate, field matches deadline | Difference [95% event-cluster CI] | Frozen status |
|---|---|---|---|---|
| `close_time` (realized) | 50.2% (n = 1,292) | 5.9% (n = 1,908) | +44.3 pts [36.4, 53.5] | dependence established |
| `expiration_time` (scheduled) | 42.1% (n = 221) | 23.5% (n = 2,954) | +18.6 pts [10.4, 27.6] | inconclusive (bar: 20 pts) |

The independent reviewer recomputed both primary statistics and their
confidence intervals from the committed data. Their reading:
- The `close_time` result "supports a warning against treating it as a
  scheduled deadline".
- The `expiration_time` result "does not establish absence of dependence; its
  positive association misses the prespecified effect-size threshold".
- Both are "associations in guarded markets, not causal effects, executable
  returns or evidence of a paper error; the paper's date-field choice is
  unknown".

**Plain reading of the numbers.**
- The realized closing time is outcome-dependent by construction and must not
  be used as a scheduled date.
- The scheduled field also leans toward YES when it lies well before the
  market's own deadline. The confidence interval excludes zero, but the effect
  falls short of the threshold we committed to in advance.

We did not recompute the paper's Table 14 on its full sample, because that
would read outcomes from a hold-out reserved for a separate pre-registered
study.

## 5. Pre-registered null results

Each result below is scoped to what was tested.

- **YES + NO below $1 (single binary market).**
  - Data: 6,432 order-book pairs, one day.
  - The NO ask equaled 1 − YES bid in every pair. The sum of asks was never
    below $1 (minimum $1.001).
  - Polymarket serves one mirrored book, so this arbitrage cannot appear in
    quotes. This was a mechanism check with no numeric threshold set in
    advance.
- **Multi-outcome basket gaps (E-002).**
  - Data: 105 complete event-snapshots in 24 events (104 meet the minimum
    order size), 6-hourly, quotes only.
  - Result: zero opportunities above the frozen 0.5¢ threshold.
  - The closest case, a 1.8¢ gross gap, was eliminated by taker fees (−0.48¢
    net).
  - Limits:
    - completeness is judged against event lists fetched later (on
      2026-11-11), because the original lists were not saved;
    - batch timestamps do not establish that quotes were simultaneous: on 16
      of the 105, the exchange timestamps span more than 60 s (maximum 930 s);
    - large multi-outcome events were rarely captured complete and remain
      untested.
- **Fees vs. published edge (E-001).**
  - Under Polymarket's taker fee schedule as of 2026-10-05 (rate × p × (1 − p)), equal-weight
    taker favorite buying is ruled out: its best-case gross edge is −0.405%.
  - The dollar-weighted version is not ruled out by the screen. Its point
    estimate nets +0.18¢ per $ at the worst-case fee, and its CI lower end nets
    −0.16¢. That is not evidence of a tradable edge.
  - This is a screen on published numbers, not a new estimate
    (`negative_results/fee_screen/`).
- **Bitcoin daily markets vs. option-implied probabilities (E-006):
  INVALID-RUN.**
  - Design:
    - frozen 2026-11-06, before any Polymarket price was viewed;
    - hourly forward snapshots until 2026-11-17;
    - executable asks on tail strikes, compared with a smile-consistent
      digital probability from Deribit implied volatilities;
    - bar: the taker fee plus 1 point.
  - Collection: Polymarket's listing API refused the collector from
    2026-11-12, and 61 of 260 scheduled snapshots entered the sample. The
    window and collector were not changed.
  - Result: the frozen pipeline gate allows at most 5% failing snapshots.
    12 of 61 (19.7%) failed, so the run stops there. S is not interpreted,
    and the 49 passing snapshots are not re-analysed as a sample.
  - Cause: a read-only diagnosis traced the failures to non-convex Deribit
    mark-volatility smiles, present in all 61 snapshots, passed through the
    frozen method. The question stays open (`options_benchmark/`).

## 6. Limitations

- One data release.
- Creation-time recovery requires on-chain events, which exist for 98% of
  the audited markets.
- Edit timing is unobserved.
- The order-book tests use one day of 6-hourly quotes and no fills.
- The date-field test covers "by-deadline" markets only.
- Hold-out protection deliberately limits which outcomes we examined.
- A few numbers were reproduced by the author's code but not independently
  recomputed. `NUMBERS.md` labels every number by its level of verification.

## 7. Reproducibility

The repository contains, for every section: the frozen protocol, the code, the
outputs, and a script that rebuilds each table from public inputs. A table maps
each protocol to the commit and time at which it was frozen, and the commits at
which its code and results were recorded.

## References

- Akey, P., Grégoire, V., Harvie, N., Martineau, C. (2026). *Who Wins and Who
  Loses in Prediction Markets? Evidence from Polymarket.* SSRN 6443103.
  Dataset: `vgregoire/polymarket-users` v1.3.
- Banz, R., Breen, W. (1986). Sample-dependent results using accounting and
  market data: some evidence. *Journal of Finance* 41(4), 779–793.
- Cardozo, M., Rivero-Wildemauwe, J. I. (2026). *The Favorite-Longshot Bias in
  Prediction Markets: Evidence from Polymarket.* arXiv:2609.12878.
- Ljungqvist, A., Malloy, C., Marston, F. (2009). Rewriting history. *Journal
  of Finance* 64(4), 1935–1960.
- Nechepurenko (2026). *Resolution Is Not Settlement, Part I: Oracle
  Adjudication and Semantic Governance on Polymarket.* arXiv:2609.15368.
- Polymarket documentation: Resolution / Clarifications; Trading fees (read
  2026-11-11).
- Portnaya, V. (2026). *Do Prediction Markets Match Option Prices? Bitcoin
  Threshold Evidence from Binance and Polymarket.* arXiv:2606.19517.

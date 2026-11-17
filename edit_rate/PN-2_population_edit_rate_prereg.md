# PN-2: how often are Polymarket market terms changed after creation? (pre-registration)

- **Author:** Claude. **Builder:** Claude subagent. **Verifier and reader:** Codex.
- **Written:** 2026-11-11, committed before any sample is drawn.
- **Why:** PN-1 measures edits only in 5,744 "by <date>" markets. The question
  a backtester needs answered is the rate across all markets.
- **Prior art (read first; `polysignal-public/note/prior_art.md`):**
  - Nechepurenko (arXiv 2609.15368) counts on-chain clarifications (UMA
    `postUpdate` / `AncillaryDataUpdated`). That work finds 1,549 creator
    clarifications on 1,350 of 185,550 questions, and it does not evaluate
    deadline or end-date changes.
  - Ljungqvist, Malloy and Marston (JF 2009) is the finance template for this
    audit.
  - Our setting differs in two ways: we compare creation-time text with the
    **current off-chain API text** that backtests actually use, and we
    measure deadline changes.

## Population and sample
- **Population:** every market in Users v1.3 `markets.parquet` (@ 91ddb961)
  that has a Gamma record in `gamma_rules.jsonl` (fetched 2026-10-07) and a
  `questionID`.
- **Sample:** a simple random sample of 1,000 markets, drawn with
  `random.Random(20261111)` from that population sorted by market_id.
  - **Unverifiable draws** (no creation event found, or an RPC failure after
    retries) are replaced by the next draw in order, up to 2,000 draws.
    Every replacement is counted and reported, together with the category mix
    of the replaced draws.
  - **Fewer than 1,000 verified within 2,000 draws:** report the achieved n.
    If it is under 400, report DATA-BLOCKED.

## Measures (per verified market; no outcomes, prices or trades are read)
- **M1, title edit:** the question title in the creation-time on-chain text
  (UMA `QuestionInitialized` ancillary data, `q: title:` part) differs from
  Users v1.3 `question`. Comparison is after Unicode NFKC, whitespace collapse
  and case-folding.
- **M2, deadline edit:** both texts parse to a deadline instant under the
  frozen `schedule_grammar_v5` parser, and the instants differ by ≥ 1 hour.
  - The denominator is the markets where both texts parse.
  - Sub-hour differences are reported separately as FORMAT, as in PN-1.
- **M3, on-chain clarification:** at least one `AncillaryDataUpdated` /
  `postUpdate` log exists for the questionID, from creation to the latest
  block at run time. This is reported to check M1/M2 against Nechepurenko's
  measure.

## Reporting
- **Rates:** each Mi as k/n with a Wilson 95% CI. Also reported:
  - Mi by Users v1.3 `category`, descriptive only, with no tests across
    categories;
  - the number of distinct events among positives;
  - the median |Δ| for M2.
- **Design effect:** markets are sampled independently, but events cluster.
  An event-cluster bootstrap CI (10,000 resamples, seed 20261111) is
  reported next to Wilson.
- Nothing is a pass/fail threshold, and every rate is reported whatever its
  size. A rate of zero is reported as a result, with its upper CI bound.

## Data sources
- Free public Polygon RPC with no key.
- If no keyless source supports the log queries, PN-2 stops and asks the
  owner for a free-tier key. That costs $0 and is recorded in
  `docs/budget.md` as $0.
- Any source change is recorded before the fetch resumes. The sample and the
  measures do not change.

## Stopping condition
- `PN-2_result.json` and the per-market CSV are written once, by script.
- Codex recomputes M1–M3 from the CSV and spot-checks 25 markets against the
  chain.
- One round; disagreements are recorded.

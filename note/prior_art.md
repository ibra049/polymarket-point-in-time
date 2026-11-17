# Prior art and citation check: public note on Polymarket data quality

Compiled 2026-11-11 (Claude, research pass). Every URL below was fetched on 2026-11-11
unless marked otherwise. "Confirmed" means read on the primary page; "could not confirm"
means the primary page was not readable or the claim was not found. Nothing here is from memory.

---

## Q1. Post-creation edits of market terms, and look-ahead bias from mutable metadata

### Confirmed

**1. Nechepurenko (2026), Resolution Is Not Settlement, Part I** (closest prior work)
- Citation: Maksym Nechepurenko, "Resolution Is Not Settlement, Part I: Oracle Adjudication and
  Semantic Governance on Polymarket," arXiv:2609.15368 [q-fin.TR], v1, 14 Sep 2026.
- URL: https://arxiv.org/abs/2609.15368 (full text: https://arxiv.org/html/2609.15368)
- What it shows: across 185,550 UMA CTF adapter questions initialized through Polygon block
  79,721,080 (last log 2025-11-30 23:59:30 UTC), the on-chain rule ledger has 1,570
  ancillary-data-update (bulletin board) events. 1,549 of them are creator-authoritative
  clarifications, they touch 1,350 distinct adapter questions, and 83.34% of 1,711
  clarification-to-request-generation relations fall after request creation but before the
  first proposal ("Empirical Finding 3: Rule state can change after the request already exists").
- Point-in-time rule: it says outright that "A current metadata page is not projected backward"
  and that "a current UI rendering cannot replace a historical rule state" (Sections 1.6, 3.7).
- Quantifies edit frequency? Partly. It counts **on-chain clarifications** (bulletin board
  `postUpdate`). It does **not** count end-date or deadline changes, extensions, or edits to
  Gamma/off-chain metadata (`endDate`, `question`, `description`). Its end-date analysis is
  reported as "NOT EVALUATED": "A bounded audit found no separately labelled rule-end-date field"
  (Section 11, Table 9). It never uses the words "look-ahead bias" or "backtest".
- Data: only aggregates are published; "raw address-level and restricted reconstruction
  materials are not distributed."
- Rough share (our arithmetic, not the paper's): 1,350 / 185,550 ≈ 0.73% of adapter questions
  carry a creator clarification.

**2. Polymarket documentation, "Resolution" (Clarifications section)**
- Citation: Polymarket, "Resolution," Polymarket Documentation, accessed 2026-11-11.
- URL: https://docs.polymarket.com/concepts/resolution (markdown: https://docs.polymarket.com/concepts/resolution.md)
- What it shows: every market's rules name a resolution source, an "End date — When the
  market is eligible for resolution," and edge cases. "In rare cases" Polymarket may issue an
  "Additional context" update after trading begins. Clarifications "Cannot change the
  fundamental intent of the question" and "Are published onchain via the bulletin board contract."
- Quantifies edit frequency? No. It only calls clarifications "rare". It does not say whether
  end dates can be extended.

**3. Polymarket Help Center, "How are markets clarified?"**
- URL: https://help.polymarket.com/en/articles/13364548-how-are-markets-clarified (the old URL
  https://docs.polymarket.com/polymarket-learn/markets/how-are-markets-clarified redirects here)
- What it shows: "When a market is clarified, the order book is cleared and all resting orders
  cancelled at the time of clarification," and the book is also cleared when a clarification is
  announced in advance. That makes a clarification a datable market event.
- Quantifies edit frequency? No.

**4. Polymarket UMA CTF adapter source (BulletinBoard mixin and UmaCtfAdapter)**
- Citation: Polymarket, `uma-ctf-adapter`, GitHub repository, `src/mixins/BulletinBoard.sol`
  and `src/UmaCtfAdapter.sol` (main branch, read 2026-11-11).
- URLs: https://github.com/Polymarket/uma-ctf-adapter/blob/main/src/mixins/BulletinBoard.sol ;
  https://github.com/Polymarket/uma-ctf-adapter/blob/main/src/UmaCtfAdapter.sol
- What it shows: `initialize()` emits `QuestionInitialized(questionID, timestamp, creator,
  ancillaryData, ...)`, and `questionID = keccak256(ancillaryData)`. The stored ancillary data
  is never rewritten. Later changes go into an append-only registry: `postUpdate(questionID,
  update)` emits `AncillaryDataUpdated` with `block.timestamp`, and the code comment says "Anyone
  can post an update for any questionID, but users should only consider updates posted by the
  question creator."
- Implication (our inference): the original on-chain question text and clarification
  timestamps can be recovered point-in-time from chain logs. Gamma's off-chain fields
  (`endDate`, `question`, `description`) have no equivalent on-chain version history.
- Quantifies edit frequency? No (it is code).

**5. UMA, "Bulletin Board" (technical UMIP discussion)**
- Citation: J. Kehlmann and D. Golow, "Bulletin Board," UMA Discourse, Aug 2023.
- URL: https://discourse.uma.xyz/t/bulletin-board/2029
- What it shows: the bulletin board lets a requester "elaborate on their previous requests".
  Follow-ups should be considered as long as they do not unreasonably change the original
  question, and DVM voters judge whether a follow-up changes its substance. It does not
  mention deadlines.
- Quantifies edit frequency? No.

**6. OrcaLayer Research (2026), "Polymarket API endDate Is Not the Resolution Time"** (grey literature)
- Citation: OrcaLayer Research, "Polymarket API endDate Is Not the Resolution Time: How to Get
  the Real One," 24 Sep 2026; cross-posted by "ekocam" on DEV Community as "Polymarket Gamma
  API endDate Is Not the Resolution Deadline."
- URLs: https://orcalayer.com/blog/polymarket-api-enddate ;
  https://dev.to/ekocam/polymarket-gamma-api-enddate-is-not-the-resolution-deadline-238o
- What it shows: in 23 hand-picked markets fetched on one day, Gamma `endDate` often differs
  from the deadline in the rules (3 of 7 deadline/price markets mismatched, one by 92 days).
  Two markets returned different `endDate` values across snapshots, and in 3 cases the API
  served a stale cached object. It also warns that `updatedAt` "will not tell you when that
  happened" and that code reading `endDate` once "may be holding a value the platform has
  since changed."
- Quantifies edit frequency? No. The authors say it is a hand-picked sample and not a
  platform-wide rate. The change evidence rests on 2 markets, and they "did not establish why."
- It is a blog post, not peer reviewed, and it does not discuss backtests.

**7. Dune, curated `polymarket.market_details` table docs** (data-provider practice)
- URL: https://docs.dune.com/data-catalog/curated/prediction-markets/polymarket/market_details
- What it shows: one row per outcome token, refreshed from API snapshots, with
  `last_uploaded_at`, `content_hash` and `last_changed_at` ("advances only when `content_hash`
  differs from the prior row"). So a major provider tracks *that* market metadata changes, but
  the docs do not describe kept historical versions. Users get current state.
- Quantifies edit frequency? No.

**8. Polymarket Users dataset README: licensing scope of lifecycle fields**
- URL: https://huggingface.co/datasets/vgregoire/polymarket-users
- What it shows: "lifecycle timestamps," along with question text, descriptions and slugs, are
  fields that "originate from the Polymarket API". This is the source of the market
  open/close dates used by arXiv:2609.12878, which restricts samples by "scheduled closing
  dates" (its Table 14). The README does not say when the metadata was retrieved or whether
  it is point-in-time.

#### Finance analogue: point-in-time vs restated data (canonical citations)

**9. Ljungqvist, Malloy and Marston (2009), "Rewriting History"** (best analogue)
- Citation: Alexander Ljungqvist, Christopher Malloy, Felicia Marston, "Rewriting History,"
  *Journal of Finance* 64(4), 1935–1960, August 2009. DOI 10.1111/j.1540-6261.2009.01484.x.
- URL: https://ideas.repec.org/a/bla/jfinan/v64y2009i4p1935-1960.html
- What it shows: comparing seven I/B/E/S downloads from 2000 to 2007, 1.6% to 21.7% of matched
  historical recommendation records differ between downloads (alterations, additions,
  deletions, anonymization). The changes are non-random and change the results of backtests
  of three stylized facts.
- Quantifies edit frequency? Yes, for analyst data. This is the direct template for
  "count how often historical metadata changes."

**10. Banz and Breen (1986), look-ahead bias in Compustat**
- Citation: Rolf W. Banz, William J. Breen, "Sample-Dependent Results Using Accounting and
  Market Data: Some Evidence," *Journal of Finance* 41(4), 779–793, 1986.
- URL: https://econpapers.repec.org/RePEc:bla:jfinan:v:41:y:1986:i:4:p:779-93
- What it shows: the bibliographic record is confirmed on RePEc. The abstract (read only on a
  secondary index, https://synapsesocial.com/papers/W2104505737) says COMPUSTAT-based studies
  can carry look-ahead and ex-post-selection bias, and that results differ from a bias-free
  database. I did not read the full text (JSTOR paywall).

**11. Brown, Goetzmann, Ibbotson and Ross (1992), survivorship bias** (optional third)
- Citation: Stephen J. Brown, William Goetzmann, Roger G. Ibbotson, Stephen A. Ross,
  "Survivorship Bias in Performance Studies," *Review of Financial Studies* 5(4), 553–580, 1992.
- URL: https://ideas.repec.org/a/oup/rfinst/v5y1992i4p553-80.html
- What it shows: truncating a sample on survival can create the appearance of performance
  persistence or predictability where none exists.

### Could not confirm / not found

- **A systematic count of `endDate` or deadline extensions on Polymarket (or Kalshi or
  PredictIt): not found.** Several searches found none in arXiv, SSRN, Polymarket docs,
  Dune, or the Polymarket changelog (https://docs.polymarket.com/changelog/predictions has no
  end-date entries). The closest are Nechepurenko (clarification counts only) and OrcaLayer
  (anecdotal, n=2).
- **A paper that explicitly warns that using *current* prediction-market metadata in
  backtests causes look-ahead bias: not found.** Nechepurenko applies the point-in-time rule
  in method but does not frame it as backtest bias. Prediction Arena (arXiv:2604.07355) only
  says backtests are "vulnerable to overfitting and look-ahead bias" in general; I saw this in
  a search snippet and did not read the paper. Practitioner posts (e.g.
  https://thedatascientist.com/how-to-analyze-polymarket-api-data-order-books-without-look-ahead-bias/,
  Kampakis, Sun, Firoozye, undated, about 2026) discuss `endDate` lagging events and not using
  terminal volume, but not mutable metadata.
- A Dune dashboard counting `AncillaryDataUpdated` events: not found.
- Polymarket Institute data page (https://institute.polymarket.com/data): HTTP 403, not read.
- Gamma docs give no prose definition of `endDate` vs `umaEndDate`; the only one found is
  `endDateIso` "Market end date in ISO 8601 format"
  (https://docs.polymarket.com/market-data/market-details).
- Compustat Point-in-Time vendor documentation: only S&P marketing pages were found; I did not
  read them as primary evidence. Using Banz and Breen plus Ljungqvist et al. instead.
- News items on contested clarifications (e.g. AMBCrypto on a Strategy/Bitcoin market,
  https://ambcrypto.com/polymarket-faces-backlash-over-disputed-strategy-bitcoin-market/) were
  only seen in search results, not verified. Do not cite them.

---

## Q2. arXiv 2609.12878 and the Polymarket Users dataset

### Confirmed

- **Paper:** Marcos Cardozo and José Ignacio Rivero-Wildemauwe, "The Favorite-Longshot Bias in
  Prediction Markets: Evidence from Polymarket," arXiv:2609.12878, **v1 (only version),
  submitted Fri 11 Sep 2026 14:05:21 UTC.** URL: https://arxiv.org/abs/2609.12878
  - Abstract figures: 588 million trades by 2.48 million accounts. Purchases below 10¢ lose
    about 19.3¢ per dollar, and purchases at or above 90¢ earn about 0.83¢. Longshots lose 6.3¢
    equal-weighted by contract but gain 4.1¢ when grouped by parent event. The pattern holds in
    Crypto and Politics and is absent in Sports.
  - Data section (HTML v1, §2.1): "We use the Polymarket Users dataset made available by Akey
    et al. (2026), specifically version 1.3 (Grégoire, 2026)." It covers 11 Nov 2022 to
    29 Mar 2026. The reference list cites "Hugging Face dataset vgregoire/polymarket-users,
    version 1.3 (2026-07-06), commit 91ddb961b090de18fd79e79edd8fa15f36ca11b9, CC-BY 4.0."
  - The paper uses "opening and closing dates" from the dataset and restricts samples by
    "scheduled closing dates" (Table 14). It does not discuss metadata edits.
- **Dataset:** "Polymarket Users," Hugging Face `vgregoire/polymarket-users`.
  URL: https://huggingface.co/datasets/vgregoire/polymarket-users
  - License: **CC-BY-4.0** (confirmed on the README and API tag `license:cc-by-4.0`). The
    license covers the authors' processing only. Fields from the Polymarket API (question
    text, descriptions, slugs, raw tags, lifecycle timestamps) "remain subject to
    Polymarket's terms of use."
  - Version: latest changelog entry v1.3 (2026-07-06); repo head sha
    91ddb961b090de18fd79e79edd8fa15f36ca11b9 (lastModified 2026-07-06T21:30:09Z, via
    https://huggingface.co/api/datasets/vgregoire/polymarket-users).
  - Credit (dataset's own BibTeX): Pat Akey, Vincent Grégoire, Nicolas Harvie, Charles
    Martineau, "Who Wins and Who Loses In Prediction Markets? Evidence from Polymarket,"
    Working Paper, 2026, SSRN 6443103, https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6443103.
    The README asks users to "please cite the paper." arXiv:2609.12878 additionally cites the
    dataset itself as "Grégoire (2026)".

### Could not confirm
- The SSRN page for 6443103 returned HTTP 403. The title and authors come from the dataset
  BibTeX and match arXiv:2609.12878's reference list.

---

## Q3. Other cited arXiv items

All confirmed on their arXiv abstract pages; each has only v1.

| arXiv | Exact title | Authors | v1 date |
|---|---|---|---|
| 2606.19517 | Do Prediction Markets Match Option Prices? Bitcoin Threshold Evidence from Binance and Polymarket | Victoria Portnaya | 17 Jun 2026 |
| 2508.03474 | Unravelling the Probabilistic Forest: Arbitrage in Prediction Markets | Oriol Saguillo, Vahid Ghafouri, Lucianna Kiffer, Guillermo Suarez-Tangil | 5 Aug 2025 |
| 2605.00864 | Arbitrage Analysis in Polymarket NBA Markets | Guang Cheng, Jiaxin Yang, Haoxuan Zou | 22 Apr 2026 |

URLs: https://arxiv.org/abs/2606.19517 , https://arxiv.org/abs/2508.03474 , https://arxiv.org/abs/2605.00864

Notes:
- 2606.19517: the main Sept-2023 BTC contract has a mean pricing gap of 5.6 pp over 214 hourly
  observations (AR(1) half-life about 4 h); pooled gap 6.3 pp over three markets.
- 2508.03474: covers market-rebalancing and combinatorial arbitrage; realized estimate about
  USD 40M extracted.
- 2605.00864 is about **NBA** markets (75M+ order-book snapshots, 173 games: 7 single-market
  episodes with median 3.6 s; 290 combinatorial episodes with median 101 bp). Check that the
  note cites it for that and not as a general Polymarket arbitrage study.

---

## Q4. Polymarket fee schedule

### Confirmed (read 2026-11-11)
- Source: Polymarket Documentation, "Fees," https://docs.polymarket.com/trading/fees
  (markdown: https://docs.polymarket.com/trading/fees.md). The page has no "last updated"
  or effective date.
- Formula: **`fee = C × feeRate × p × (1 − p)`**, where C = number of shares traded and
  p = share price. The fee is in USDC, charged to takers only ("Makers are never charged
  fees"), applied at match time, and rounded to 5 decimals (minimum 0.00001 USDC).
- Taker rates (maker rate 0 everywhere; maker rebate in brackets): Crypto 0.07 (20%);
  Sports 0.05 (15%); Finance 0.04 (25%); Politics 0.04 (25%); Economics 0.05 (25%);
  Culture 0.05 (25%); Weather 0.05 (25%); Other/General 0.05 (25%); Mentions 0.04 (25%);
  Tech 0.04 (25%); Geopolitics 0 (fee-free); Combos 0.05 (0%, applies whatever the legs'
  categories).
- Check: the fee peaks at p = 0.5. Per 100 shares that is $1.75 for Crypto, $1.25 for
  Sports/Economics/Culture/Weather/Other and $1.00 for Finance/Politics/Mentions/Tech, which
  matches 100 × rate × 0.25.
- Per-market parameters: https://docs.polymarket.com/market-data/market-details shows
  `feesEnabled` and `feeSchedule {rate, exponent, takerOnly, rebateRate}` (example: rate 0.04,
  exponent 1, takerOnly true, rebateRate 0.25). The changelog (31 Mar 2026) says "Fees should
  now be calculated using the `feeSchedule` object within a market."
  https://docs.polymarket.com/changelog/predictions

### Could not confirm
- How a non-1 `exponent` enters the formula: not documented on the Fees page. The published
  formula matches exponent = 1. A backtest should read each market's `feeSchedule` rather
  than assume the category table.
- The historical fee schedule (when fees started per category): not on the page. The
  current table must not be applied to old trades without a dated source.

---

## Bottom line for the note's novelty claim

- Clarification frequency **has been counted** on-chain by Nechepurenko (2026): 1,549
  creator clarifications over 1,350 of 185,550 adapter questions through Nov 2025.
- **Edits to resolution deadlines and `endDate` / off-chain metadata have not been counted**
  in anything found. The only evidence is OrcaLayer's 2-market anecdote and its warning that
  `endDate` can change.
- The look-ahead framing has a strong finance precedent (Ljungqvist et al. 2009; Banz and
  Breen 1986). No prediction-market paper states it for mutable metadata.
- Suggested wording: "To our knowledge, the first count of post-creation deadline edits"
  (not "first study of edits"), citing Nechepurenko for clarification counts and OrcaLayer
  for the anecdote.

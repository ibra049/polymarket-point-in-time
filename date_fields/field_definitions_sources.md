# Date fields in Polymarket Users v1.3 `markets`: what the documentation says

Documentation only, checked 2026-11-11. No dataset rows were read. Every claim has a URL.
Where something could not be found it says **NOT FOUND**. Inferences are labelled **INFERENCE**.

Dataset: HF `vgregoire/polymarket-users`, v1.3, commit `91ddb961b090de18fd79e79edd8fa15f36ca11b9`.

## 1. Dataset field definitions

### 1a. HF repo at the pinned commit

- The repo root has `README.md`, `.gitattributes`, the parquet files and partition folders, and nothing else. There is no `docs/`, data dictionary or code.
  Source: https://huggingface.co/api/datasets/vgregoire/polymarket-users/tree/91ddb961b090de18fd79e79edd8fa15f36ca11b9
- The README (dataset card) never names `market_start_time`, `close_time` or `expiration_time`. It describes `markets` only as:
  > "Per-market metadata including category (classifier-derived), parent event, resolution outcome, fee flags, and lifecycle timestamps."

  It then points to external documentation: "**Documentation:** <https://www.vincentgregoire.com/polymarket-users-data>".
  Source: https://huggingface.co/datasets/vgregoire/polymarket-users/blob/91ddb961b090de18fd79e79edd8fa15f36ca11b9/README.md
- The README's License section says that lifecycle timestamps come from the Polymarket API:
  > "It does **not** cover fields that originate from the Polymarket API (e.g., market question text, descriptions, slugs, raw platform tags, lifecycle timestamps)."

  Same URL.
- The changelog says `markets` has not changed since v1.0. v1.1: "Sample period and the other panels (`markets`, `events`, …) are unchanged from v1.0." v1.3 changed only `frac_longshot` and `frac_sureshot`, "every other column in `user_features` and every other table" unchanged. Same URL.

### 1b. The authors' documentation site (the only column-level definitions found)

https://www.vincentgregoire.com/polymarket-users-data/datasets/markets/ has a schema table. Exact text:

| Column | Type | Description (verbatim) |
|---|---|---|
| `market_start_time` | datetime[ns, UTC] | "Trading start time" |
| `close_time` | datetime[ns, UTC] | "When trading closed (resolution time when settled)" |
| `expiration_time` | datetime[ns, UTC] | "Scheduled expiration / settlement time" |
| `can_close_early` | bool | "Whether the market is allowed to close before its scheduled expiration" |

Version history of that page. The site source is public in the GitHub repo `vgreg/vgreg.github.io`. Commit history for the page: https://github.com/vgreg/vgreg.github.io/commits/master/polymarket-users-data/datasets/markets/index.html
- First version, 2026-05-19 04:12Z (`bb0df2a`), had no column table. It said:
  > "Columns are populated via the canonical load_clean_markets loader. The exact schema is documented in the source repo's data dictionary"

  and linked to `https://github.com/fintech-research/polymarket-users/blob/main/docs/data.md`. Its lifecycle columns were "`start_time`, `close_time`, `resolution_time`".
  Source: https://github.com/vgreg/vgreg.github.io/blob/bb0df2abe983d04613924cee23f6f73d29f21b91/polymarket-users-data/datasets/markets/index.html
- The table quoted above first appears 2026-05-19 10:28Z (`30b18e2`). Source: https://github.com/vgreg/vgreg.github.io/blob/30b18e2d326477ae52bd5ff3e340a1d3fb490dc0/polymarket-users-data/datasets/markets/index.html
- The last change was 2026-06-01 (`17f50ba`), with identical wording for these four columns. Source: https://github.com/vgreg/vgreg.github.io/blob/17f50ba81b1a520649c73fc217abc9407f95be78/polymarket-users-data/datasets/markets/index.html
- The site is not versioned per dataset release, and its last Polymarket-docs commit (2026-06-15) is older than v1.3 (2026-07-06). The definitions apply to v1.3 only through the changelog's statement that `markets` is unchanged since v1.0.

The events page defines the related column `event_start_time` as "Earliest market-start time across constituent markets".
Source: https://www.vincentgregoire.com/polymarket-users-data/datasets/events/

### 1c. Construction code

- `fintech-research/polymarket-users`, the "source repo" the first doc version linked to, returns 404 on both the GitHub API and the web. It is private or deleted, so it is **NOT PUBLIC**.
  Checked: https://github.com/fintech-research/polymarket-users/blob/main/docs/data.md (404). The organization's public repos are `cookiecutter-py-quarto`, `ai-lab-investment`, `mdal-vix-26` and `pytaq`; none is Polymarket-related (https://github.com/fintech-research).
- Grégoire's public GitHub repos have no Polymarket construction code: https://github.com/vgreg?tab=repositories
- Co-author Harvie's GitHub (https://github.com/itsNH98) has `poly_data`, a fork of `warproxxx/poly_data` (https://github.com/itsNH98/poly_data). Nothing ties it to this dataset, and it is **not** shown to be the construction code.
- A GitHub code search for "can_close_early expiration_time market_start_time" found no hits.
- **Public construction code: NOT FOUND.**

### 1d. The paper (Akey, Grégoire, Harvie, Martineau)

- SSRN 6443103 returned HTTP 403 to automated fetch: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6443103
- A public copy, dated June 21, 2026 (56 pp.), is at https://www.carf.e.u-tokyo.ac.jp/wp/wp-content/uploads/2026/06/260714_polymarket.pdf. Its data section, §3, says:
  > "The events and markets metadata is from Polymarket's Gamma and CLOB APIs. Trade information is obtained from the Polymarket SubGraph by Goldsky"

  and:
  > "The full list of data sources, the procedure that reconciles raw on-chain events into clean trade records, and the construction of our main dataset are described in Section A of the Internet Appendix."
- The paper uses "close" as the resolution point (Figure 2 caption):
  > "For each horizon h the sample includes all resolved markets that were opened at least h before close and have a valid reconstructed price at time close − h … Panel (b) plots a kernel-density estimate of market lifetimes (close minus open) over all resolved markets"

  The body text speaks of "the time between a market's open and its resolution". No column name is given.
- **Internet Appendix: NOT FOUND.** It is not in the PDF and not linked from https://www.vincentgregoire.com/ or the docs site, and a web search did not find it. So the mapping of Gamma or CLOB fields to `close_time`/`expiration_time` is **NOT FOUND**.

### 1e. Mapping to Gamma or CLOB fields

- **NOT FOUND** in any dataset document. No document says which Gamma or CLOB field becomes `market_start_time`, `close_time` or `expiration_time`.
- The sources contradict each other on provenance. The docs Methodology page says "All cleaning happens off these events; no off-chain Polymarket API is required." (https://www.vincentgregoire.com/polymarket-users-data/methodology/). The About page, README and paper all say lifecycle timestamps or metadata come from the Polymarket API (https://www.vincentgregoire.com/polymarket-users-data/about/ ; paper §3 above).
- A naming observation, which is not evidence of a mapping: `close_time`, `expiration_time` and `can_close_early` are exactly the names of fields in Kalshi's market object (`open_time`, `close_time`, `expected_expiration_time`, `expiration_time` [marked `deprecated: true`], `latest_expiration_time`, `can_close_early`). See https://docs.kalshi.com/api-reference/market/get-market. Polymarket's Gamma names are different (`startDate`, `endDate`, `closedTime`, `umaEndDate`; §3 below). **INFERENCE:** the dataset probably renamed Polymarket fields into a Kalshi-style schema, so the column names alone cannot tell you which Gamma field sits behind each one.

## 2. Cardozo and Rivero-Wildemauwe, arXiv 2609.12878v1

Sources: https://arxiv.org/html/2609.12878v1 (HTML) and https://arxiv.org/pdf/2609.12878v1 (PDF). v1 was submitted 2026-09-11 and the abs page lists no other version (https://arxiv.org/abs/2609.12878).

Sentences about the date fields, verbatim:

- §2.1, data description:
  > "For each market, we observe its wording and category, its parent event, its opening and closing dates, and the winning token if the market had resolved by the end of the sample."

  It names two dates and never says "expiration".
- Appendix B (Time and Maturity), Table 14:
  > "Table 14 restricts the sample by scheduled closing dates."
  >
  > Title: "Table 14: Longshot returns under restrictions on scheduled closing dates"
  >
  > Rows: "Scheduled to close at least 30 days before cutoff", "… 90 days before cutoff", "Scheduled close no later than 1 / 7 / 30 day(s) after purchase".
  >
  > Notes: "The second and third rows retain markets scheduled to close at least 30 or 90 days before March 29, 2026. In the final three rows, purchases must have occurred at least 1, 7, or 30 days before that cutoff, respectively, and the market must have been scheduled to close no later than the corresponding number of days after purchase."
- Appendix E.3 (Overlap between the longshot and favorite groups), Table 23:
  > "Table 23 uses a common sample for spending shares, net-gain shares, and favorite returns: purchases with a known final payoff, a recorded closing or expiration date, and a price at least 90 cents but strictly below one dollar."
- Appendix H, on separately pulled Gamma metadata. It is used for shared collateral, and the paper does not say it is used for dates:
  > "Official Gamma metadata cover 590,449 of 591,187 market identifiers in the resolved purchase sample."
- The data citation (reference "Grégoire (2026)") reads: "Hugging Face dataset vgregoire/polymarket-users, version 1.3 (2026-07-06), commit 91ddb961b090de18fd79e79edd8fa15f36ca11b9 CC-BY 4.0".

Not found in the paper: a column name (`close_time`/`expiration_time`), any definition of "scheduled closing date", a data or code availability statement, and any code link. **NOT FOUND** (grep of the full HTML and PDF text for close_time, expiration_time, github, replication, code, data availability).

Replication code searches:
- arXiv abs page: no comments field and no code links (https://arxiv.org/abs/2609.12878).
- GitHub repo search "favorite longshot polymarket": no results. Code searches for "Rivero-Wildemauwe" and for the dataset commit hash find only third-party citations, no replication repo.
- Rivero-Wildemauwe's homepage and research page do not list this paper or any code: https://sites.google.com/view/jos-ignacio-rivero-wildemauwe/home , https://sites.google.com/view/jos-ignacio-rivero-wildemauwe/research
- Cardozo: the HF account `marcoscar` has 0 datasets/models/spaces (https://huggingface.co/marcoscar). His one HF discussion, the v1.3 bug report, mentions no code: https://huggingface.co/datasets/vgregoire/polymarket-users/discussions/2. No GitHub account for him was found.
- **Public replication code: NOT FOUND.**

Which column Table 14 uses: **not stated anywhere public.**
- **INFERENCE:** "scheduled" matches the dataset's own description of `expiration_time` ("Scheduled expiration / settlement time"). It does not match `close_time` ("When trading closed (resolution time when settled)").
- Against that, §2.1 mentions only "opening and closing dates", and E.3's "a recorded closing or expiration date" suggests their code handles both columns, possibly with one filling in when the other is missing.
- So the column is undetermined from text. There is a weak lean to `expiration_time`, or `close_time` with `expiration_time` as fallback. Treat it as unknown unless the authors confirm or the data are checked.

## 3. Polymarket Gamma API docs (docs.polymarket.com)

- Gamma Market schema, OpenAPI. It lists `endDate` (string, date-time), `startDate` (date-time), `closedTime` (string), `umaEndDate` (string), `endDateIso`, `startDateIso`, `umaEndDateIso`, `closed` (boolean), `umaResolutionStatus`, `gameStartTime`, `acceptingOrdersTimestamp` (date-time), `deployingTimestamp`, `eventStartTime`, `createdAt` and `updatedAt`. **None of these date fields has a `description` in the spec.**
  Source: https://docs.polymarket.com/api-spec/gamma-openapi.yaml (also rendered at https://docs.polymarket.com/api-reference/markets/get-market-by-id.md)
- The `/markets` list endpoint has filters `end_date_min`/`end_date_max` (date-time), with no description. Source: https://docs.polymarket.com/api-reference/markets/list-markets.md
- "Market Details" guide (https://docs.polymarket.com/market-data/market-details.md):
  - Section intro: "Market timing places a market within its expected schedule. Markets include start and end dates, while sports markets may also include the scheduled start time of the game."
  - Gamma field table: `startDateIso` = "Market start date in ISO 8601 format."; `endDateIso` = "Market end date in ISO 8601 format."
  - `closed` = "Market has resolved or been closed, so no further trading is possible."
  - The SDK `MarketState` type groups `startDate`, `endDate` and `closedTime` together. The example shows `"endDate": "2027-01-01T00:00:00Z", "closedTime": null` for an open market.
- Resolution concept page (https://docs.polymarket.com/concepts/resolution.md): the resolution rules specify an "**End date** — When the market is eligible for resolution".
- **`closedTime` definition: NOT FOUND.** The docs give it a type and an example (null while the market is open) but no prose.
- **`umaEndDate` / `umaEndDateIso` definition: NOT FOUND.**
- The resolution-state endpoint (separate from the Gamma market object) defines `resolved_at` as "When the condition resolved, RFC3339 UTC." Source: https://docs.polymarket.com/api-reference/markets/get-resolution-state.md

## Bottom line

- `close_time` is the actual end of trading, set to the resolution time for settled markets. `expiration_time` is the scheduled expiration or settlement time.
  - Source: the authors' docs page only (§1b).
  - Confidence that this is what the authors *say*: high.
  - Confidence that it is what the data *contain*: unverified. There is no public code, no Gamma mapping, provenance statements conflict, and the definitions were written before v1.3 and apply only through the changelog.
- **INFERENCE** on the Gamma mapping: by meaning, `expiration_time` ≈ Gamma `endDate` ("market end date" / "eligible for resolution"), and `close_time` ≈ Gamma `closedTime`. No document states this.
- The column behind Table 14's "scheduled closing date" is not stated publicly (§2).

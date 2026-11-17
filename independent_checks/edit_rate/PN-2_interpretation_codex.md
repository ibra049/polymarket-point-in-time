# PN-2 independent interpretation — Codex, 2026-11-16

**Status: INCONCLUSIVE.** This is a descriptive audit with no frozen pass/fail threshold. The CSV counts and Wilson intervals reproduce. The rates describe verified markets, and M2 describes the further subset with two parsable deadlines; they do not establish an all-market rate or a trading/backtest effect. All 25 random source checks and 14 supplemental positive checks completed with zero mismatches; M3 retains a common-provider limitation.

## Frozen question and scope

Owner-authorized Job A, from `research/handoffs/2026-11-16_claude_local_codex_session.md`. Preregistration: `PN-2_population_edit_rate_prereg.md` at `44d0be87951f2b40b473a0990f1e374a5d74b333`, committed **2026-11-12 03:16:12 UTC** (November 11, 22:16:12 EST). Its bytes are unchanged: SHA-256 `a58c52b7a8f71063af9bd898d4be74aeb301be3a1de8195d860ba5f5f6e5012a`.

The repository's experiment-review checklist was applied before the recount. This is the authorized pipeline/measurement audit of an existing result. The preregistration distinguishes off-chain title/deadline changes from the on-chain clarification prior art. This cheap recount and bounded source check can qualify the public note's point-in-time metadata warning. Executable prices, fees, capacity, return outcomes and trading holdouts do not apply to these descriptive measures, and none is tested here. Event dependence is addressed by the required cluster intervals. No frozen threshold, population filter, sample, parser, metric or original output was changed.

Only the named PN-2 artifacts, allowed metadata files and frozen parser were used. No database was opened, and no trade, prediction, outcome or price parquet columns were queried. No SSH, VPS, production, spending, issue/PR action or main-branch edit occurred.

## Independent first pass

`pn2/codex/recount.py` was committed as **5db7220** before generating the independent output; `pn2/codex/first_pass.json` was committed as **07df1d6** before opening either `pn2/measure.py` or `pn2/fetch.py`. It rederives M1 from the normalized title strings, M2/FORMAT from the recorded ISO instants and M3 from clarification counts, then checks the stored flags and deltas. **Zero CSV-field disagreements.** This validates arithmetic and internal consistency; it does not independently extract all 1,000 source texts.

Disclosure: the required inspection of `measure.log` exposed the original headline counts before the independent output was committed. This was an independent implementation, **not a blinded interpretation**. `sample.py` was read earlier because it was not among the prohibited author files; both prohibited files stayed unopened until 07df1d6.

All intervals below are in **percent**, not fractions. Bootstrap first-pass method: 10,000 resamples of each measure's eligible event clusters, `random.Random(20261111)` restarted per metric, first-seen cluster order, linear percentile interpolation.

| Measure | k/n | Rate | Wilson 95% CI | Independent first-pass event bootstrap 95% CI | Distinct positive events |
|---|---:|---:|---:|---:|---:|
| M1 title difference | 7/1,000 | 0.7000% | 0.3395–1.4378% | 0.2008–1.2872% | 7 |
| M2 deadline difference ≥1 h | 1/641 | 0.1560% | 0.0275–0.8783% | 0–0.4710% | 1 |
| FORMAT, 0 < absolute difference <1 h | 0/641 | 0% | 0–0.5957% | 0–0% | 0 |
| M3 at least one AncillaryDataUpdated | 8/1,000 | 0.8000% | 0.4059–1.5706% | 0.3000–1.3972% | 8 |

The median absolute M2 change is **24 hours**, from one positive market (`942709`); its recorded current deadline is **24 hours earlier**, not an extension. A zero FORMAT count does not establish a zero population rate: its Wilson upper bound is **0.5957%**. The degenerate empirical bootstrap bound cannot replace that upper bound.

Category counts are descriptive only; no between-category tests were performed. Weather has no eligible M2/FORMAT denominator, so its rate is undefined.

| Users v1.3 category | Verified markets | M1 | M2 | FORMAT | M3 | Replaced draws |
|---|---:|---:|---:|---:|---:|---:|
| Crypto | 139 | 0/139 | 0/5 | 0/5 | 2/139 | 362 |
| Culture | 34 | 1/34 | 0/12 | 0/12 | 0/34 | 0 |
| Finance | 35 | 0/35 | 0/7 | 0/7 | 1/35 | 0 |
| Politics | 47 | 1/47 | 1/19 | 0/19 | 2/47 | 0 |
| Sports | 693 | 3/693 | 0/590 | 0/590 | 2/693 | 10 |
| Tech | 11 | 2/11 | 0/8 | 0/8 | 1/11 | 0 |
| Weather | 41 | 0/41 | — (0 eligible) | — (0 eligible) | 0/41 | 0 |

The verified sample contains **989 distinct events**. The frozen minimum (400) and target (1,000) are satisfied within the 2,000-draw limit: **1,372 draws walked, 1,000 verified, 372 replaced**. The ranks in the two CSVs partition exactly 1…1,372. Every replaced CSV row says `unverifiable: no creation event`; those 372 absence claims were not independently re-queried in this task.

## Comparison with recorded output

After 07df1d6, the recorded JSON and builder code were opened. All M1/M2/M3/FORMAT numerators, denominators, category counts, positive-event counts and Wilson endpoints match (Wilson to the recorded six decimal places in fraction units). The recorded M2 median is also 24 hours.

The first-pass bootstrap endpoints **do not match exactly**, and are preserved without adjustment. The preregistration specifies 10,000 event-cluster resamples and the seed, but does not freeze the bootstrap RNG implementation, event ordering or whether M2 samples all event clusters or only eligible clusters. The builder uses NumPy `default_rng(20261111)`, lexicographically sorted native string event IDs, and a single index matrix over all 989 events shared by every measure. M2 uses the ratio of positive/eligible counts in each resample, including zero-eligible clusters in that cluster universe.

A separately labeled, post-comparison diagnostic implements that disclosed method without importing `measure.py`. It reproduces **all four recorded bootstrap intervals at six decimal places**:

| Measure | Recorded / disclosed-method diagnostic bootstrap 95% CI, percent |
|---|---:|
| M1 | 0.2006–1.2910% |
| M2 | 0–0.4831% |
| FORMAT | 0–0% |
| M3 | 0.3000–1.3986% |

Verifier correction: the first version of this diagnostic incorrectly cast event IDs to integers. Parquet schema inspection established `event_id: large_string`; the builder sorts those strings. The failed numeric-order diagnostic remains in `source_audit.json`; the corrected native-string diagnostic is `source_audit_native_strings.json`. This correction changes neither the independent first pass nor the original result. Its reason is documented in commit **79f06a0**.

The original JSON's status `MEASURED` is **not an allowed decision status**. It is retained as original evidence, not adopted here. INCONCLUSIVE records the absence of a frozen inferential pass/fail decision and the unresolved generalization/provenance limits; the matching descriptive counts do not warrant PROMOTE or REJECT.

## Sampling and provenance checks

Population: **727,053** eligible market IDs out of **729,133** parquet market IDs. Population sorted-ID SHA-256: `cf5d6281dd18dd843955659964e15360ca665d0f1fba7d69a0a5a5bb7f7bf538`.

Running the committed `sample.py` with seed **20261111** yields JSON identical to `draws.json`. A separate implementation decodes only parquet `market_id`, forms the Gamma-found/questionID intersection, sorts numeric IDs and calls `random.Random(20261111).sample(population, 2000)`. **All 2,000 IDs agree, all 1,372 consumed ranks agree, and all 1,000 verified CSV IDs agree at their recorded ranks.** This verifies the draw, not why particular draws were unverifiable.

The handoff's statement that this check needs `markets.parquet` only is inaccurate: `sample.py` also requires **`gamma_rules.jsonl`** to define eligibility. Both named local inputs were available; no outcomes were needed. Their hashes, the three frozen grammar hashes, and the sample/fetch/measure/draws file hashes all match the original result manifest. The Hugging Face pin was not independently downloaded again.

Original result SHA-256: `7d9fc630215c2c3456fdcbef3847d8f4788dd51d36b8111122a28261b85d8adb`. CSV SHA-256: `30314969af2965150a1e123d3a86b86a0d7817156219dfb6fe29be60fa66da2c`. These match the handoff prefixes and the committed artifacts.

**Original code-before-output provenance cannot pass.** The original builder code and outputs first entered git together in **2bdf13e**, committed **2026-11-15 22:15:02 UTC**. The preregistration is an ancestor, but that does not establish that the executed code was frozen before execution. `measure.log` and the result both state generation at **2026-11-12 04:39:07 UTC**, **1 hour 22 minutes 55 seconds after** the preregistration commit. Those are consistent self-reported generation times, not independent proof of when the run occurred. `fetch.log` gives head **97,166,757**, 1,400 fetched draws and progress/completion, but **has no wall-clock generation timestamp**. It cannot supply the timestamp check the handoff suggests. The cutoff block header, independently re-read during verification, has timestamp **2026-11-12 03:53:12 UTC**, consistent with a post-preregistration head, but it does not prove the wall-clock fetch time. The raw original `fetch_raw.jsonl` is not present in this worktree, so a complete all-row extraction replay was not performed.

## Polygon spot check

Completed **2026-11-16 01:06:46 UTC**: **25/25 random rows and 14/14 supplemental positive rows verified, zero field mismatches, zero unknown rows**. The selection was `random.Random(20261111).sample(CSV rows sorted by numeric market_id, 25)`, committed before queries as 37aefb0. None of the random 25 had a positive CSV flag, so all 14 distinct positive markets were checked separately; they are not counted as additional random observations.

Final source method (plan 342f8a6, code dbb7b6f, raw outputs a1b9634): creation logs and block headers for all 39 rows came from **independent Pocket**, at the CSV's claimed creation blocks. The committed cache is bound by SHA-256 in the completion plan. The clarification scan used **40 contiguous Tenderly queries of at most 1,000,000 blocks**, from block 58,008,243 through the original cutoff 97,166,757, with all 39 questionIDs in each query and no address filter. Logs were then filtered to the creating adapter and creation-to-cutoff interval for each row. All 43 requests in the final Tenderly scan/preflight returned successful RPC results. This checks the claimed creation record; it does **not** globally prove that no earlier duplicate initialization exists.

The final JSON is [`pn2/codex/mixed_bounded/polygon_spotcheck.json`](pn2/codex/mixed_bounded/polygon_spotcheck.json), with raw request/response JSONL, selected logs, headers and decoded observations beside it. All eight creation texts and timestamps successfully read in the earlier Tenderly attempt also match the independent Pocket responses. M1/M2 therefore have independent-provider spot corroboration; M3's complete count scan uses the builder's original Tenderly provider and retains that common-provider risk.

The sole M2 positive (`942709`, “Will the Republican Party win the MI-04 House seat?”) reparses from **2026-11-05 04:59:59 UTC** on-chain to **2026-11-04 04:59:59 UTC** in the Gamma snapshot, confirming the earlier-by-24-hours result. This does not date the off-chain edit.

The frozen parser is reused unchanged after verifying its v3/v4/v5 hashes, as required by M2. Independent code decodes the creation ancillary bytes, obtains the creation block timestamp, extracts title/description, compares Users metadata, reparses both descriptions and counts the update logs through the **original** block cutoff. No logs after that cutoff contribute to the result. Public contract interfaces support the event schemas: [v2 QuestionInitialized](https://github.com/Polymarket/uma-ctf-adapter/blob/main/src/interfaces/IUmaCtfAdapter.sol), [AncillaryDataUpdated](https://github.com/Polymarket/uma-ctf-adapter/blob/main/src/interfaces/IBulletinBoard.sol), and [v1 QuestionInitialized](https://github.com/Polymarket/uma-ctf-adapter/blob/v1.0.1/contracts/UmaConditionalTokensBinaryAdapter.sol).

Source failures remain evidence. Tatum first rejected queries over **100 blocks** (-16412), then reported **5 requests/minute** quota errors. Pocket rejected queries over **50,000 blocks** (-32602). Both attempts completed 0/25 random checks, hence neither corroborates the data. After the first attempt, a documented harness correction added 1.1-second request spacing and a circuit breaker; an offline reproduction shows two mock failing invocations make **two** network calls in the old harness versus **one** after the fix. All **12** focused offline tests pass, including ABI bounds, Unicode normalization, Wilson references, circuit behavior and contiguous range/cap boundaries. Each source change was committed before fetching resumed, and all attempts retain their raw responses. There was no paid upgrade or API key. The first Tenderly full-range attempt completed 8/25 random rows, then a 40-second timeout stopped further requests. Pocket subsequently supplied all 39 exact-block creation records but rejected a 50,000-block clarification batch with a stricter **10,001-block** limit from another backend. That failure is also preserved. The final mixed-source plan reused the pinned Pocket creation evidence and completed the smaller Tenderly ranges; no failed response was converted into a data observation.

The Tenderly plan inherited a misleading `source_reason` phrase calling the endpoint independent. Its actual URL is correctly recorded and is the builder's original provider. This report makes **no independent-provider claim** for Tenderly. Its source agreement is an independent implementation check against a public RPC, with remaining common-provider risk. The initial Tatum dispatch continued to the other planned rows after failures; the new circuit prevents that behavior. One pytest invocation used pytest's default temporary fixture directory outside the worktree; subsequent validation explicitly places temporary fixtures under the worktree cache. No dataset or project source was written there.

## Interpretation and reporting limits

- **Selection:** 372/1,372 draws (**27.11%**) were replaced; 362 of those 372 were Crypto. The frozen replacement rule was followed, but rates among verifiable UMA-adapter markets cannot be presented as unbiased rates among every market in the initial 727,053-ID population. The replacement reasons remain CSV-level evidence rather than independently established absence for all 372.
- **Deadline coverage:** M2 covers 641/1,000 verified markets; 590/641 are Sports. It says nothing about deadline edits in the other 359. The original parse flags report 357 neither parse, one creation-only and one current-only.
- **What “edit” means:** M1 is a normalized text-difference flag, not a materiality classification. M2 compares two parseable instants. Neither measure establishes when a change happened, reversions, intent, or the effect on a historical backtest. Current title and rule snapshots also have different observation dates: Users v1.3 metadata versus Gamma descriptions fetched October 7.
- **Clarifications:** M3 counts any poster, exactly as frozen; it is not a creator-authoritative clarification rate. The original creator-only 5/991 result is supplementary, not substituted for M3. Nine v1-adapter rows have no bulletin-board event and contribute structural M3 zeros. No direct equivalence to the prior paper's creator-only question rate is inferred.
- **Uncertainty:** Wilson and event-bootstrap CIs measure sampling uncertainty under their stated cluster treatment. They do not account for selective unverifiability, parser coverage, source omissions, or the original execution-provenance gap.

Suggested note wording: “Among 1,000 verified markets reached after 372 replacements in a preregistered random draw, 7 had a normalized creation/current title difference (0.70%; Wilson 95% CI 0.34–1.44%). Among the 641 with parseable deadlines in both texts, 1 differed by at least an hour (0.16%; 0.03–0.88%), by 24 hours. Eight had an on-chain update from any poster (0.80%; 0.41–1.57%). Counts were independently recomputed; original code and outputs were committed together after their stated generation date.” The completed 25-row chain check and M3 common-provider limitation should accompany that disclosure.

## Reproduction and evidence

Read-only input root: `<users_v1.3>`. Frozen grammar root: `<this-repo>/date_fields/data`. Existing Python environment was used read-only with bytecode writing disabled: Python **3.14.3**, PyArrow **24.0.0**, NumPy **2.4.5**, pytest **9.1.1**. Scripts, tests, manifests, raw responses and logs are under [`pn2/codex/`](pn2/codex/).

From the repository root, the offline recount is:

```sh
python3 -B polysignal/research/public_note/pn2/codex/recount.py \
  polysignal/research/public_note/pn2/edit_rate_sample.csv \
  polysignal/research/public_note/pn2/replaced_draws.csv --output <new-worktree-output.json>
```

Use a Python with NumPy/PyArrow to run `source_audit.py <metadata-root> <grammar-root>` or `sample.py <metadata-root> <new-worktree-draws.json>`. The audit diagnostic writes `source_audit_native_strings.json`; the preserved first-pass and numeric-order outputs are separate. For any optional future chain reproduction, use a **fresh directory inside this worktree** with `spotcheck.py --plan-only --rpc <allowed-endpoint> --evidence-dir <fresh-directory>`, inspect/commit that source plan, then use the same arguments with `--run --root <metadata-root> --grammar <grammar-root>`. Existing RPC evidence is protected from overwrite. The completed bounded scan is implemented in `bounded_spotcheck.py`; its source, width, cached-creation hash and exact selection are in `mixed_bounded/selection_plan.json`. Its two-step `--plan-only` / `--run` interface accepts `--rpc`, `--max-range`, `--evidence-dir` and `--creation-cache`; the existing completed evidence is protected from overwrite. Use a fresh evidence directory if an optional new run is explicitly intended. A rerun is not needed to accept the completed evidence in this packet.

Key immutable stages: **5db7220** (independent code), **07df1d6** (first-pass numbers before prohibited author code), **ce4d39f** (post-comparison provenance/chain code), **37aefb0** (first chain plan), **e423914** (first source failure and numeric-order diagnostic preserved), **79f06a0** (documented verifier fixes), **e2fd653** (Pocket plan), **97a28e6** (Pocket evidence and corrected diagnostic), **eb0a324** (Tenderly source plan). The subsequent range adaptations and preserved failures are described in `pn2/codex/source_check_failure.md`. **dbb7b6f** implements the final bounded decoder/replay, **342f8a6** freezes its source/cache/query plan, and **a1b9634** commits the completed raw checks before this write-up. `verification_checks.json` records 16 passing packet-consistency checks; `pytest_final.log` records 12 passing offline tests.

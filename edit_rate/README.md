# PN-2: how often are Polymarket market terms changed after creation?

A population-wide random sample of Polymarket markets, comparing the **creation-time on-chain question
text** with the **current off-chain text** a backtest would use. Pre-registered before any sample was
drawn: [`PN-2_population_edit_rate_prereg.md`](PN-2_population_edit_rate_prereg.md), a verbatim copy of the
protocol frozen at commit `44d0be8` of the author's private working repository (`polysignal-ops`; the
scripts and logs below still name that path). Results: `PN-2_result.json` and `edit_rate_sample.csv`, both
in this folder.

## Files

| file | what |
|---|---|
| `sample.py` | deterministic draw; writes `draws.json` (population size, sha256 of sorted ids, 2,000 draws in order) |
| `verify_source.py` | checks the log source against 3 markets with known A13/PN-1 results; writes `source_check.json` |
| `fetch.py` | one full-range `eth_getLogs` per drawn market; writes the resumable checkpoint `fetch_raw.jsonl` (raw creation text and every clarification log) |
| `measure.py` | M1-M3, Wilson and event-cluster bootstrap CIs; writes `edit_rate_sample.csv`, `replaced_draws.csv`, `PN-2_result.json` |
| `edit_rate_sample.csv` | one row per verified market |
| `replaced_draws.csv` | every unverifiable draw, its category and reason |
| `PN-2_result.json` | the single-run result (M1-M3, CIs, input hashes) |
| `fetch_raw.jsonl` | the raw on-chain creation and clarification logs for every drawn market |
| `data/gamma_rules_trimmed.jsonl.gz` | the Gamma API fields the scripts need (see Reproduce) |

## Method

**Population.** Every market in Polymarket Users v1.3 `markets.parquet` (Hugging Face
`vgregoire/polymarket-users` @ `91ddb961`) that has a Gamma record in `gamma_rules.jsonl` (Gamma API,
fetched 2026-10-07, `found` true) with a non-empty `questionID`.

**Sample.** Population sorted by numeric `market_id`; `random.Random(20261111).sample(population, 2000)`
gives the draw order. Draws are taken in order; a draw is *verified* when its UMA `QuestionInitialized`
creation log is found. Unverifiable draws (no creation log, or RPC failure after retries) are replaced by
the next draw, up to 2,000 draws, until 1,000 are verified.

**On-chain lookup.** The questionID comes from the Gamma record (`negRiskRequestID` for NegRisk
markets, which is the key the UMA adapter uses for them). One `eth_getLogs` call per market over blocks
0..HEAD (HEAD fixed when the fetch started) filtered by topic1 = questionID and topic0 in:

| event | source | topic0 |
|---|---|---|
| `QuestionInitialized(bytes32 indexed questionID, uint256 indexed requestTimestamp, address indexed creator, bytes ancillaryData, address rewardToken, uint256 reward, uint256 proposalBond)` (adapter v2+) | `uma-ctf-adapter` main, `src/interfaces/IUmaCtfAdapter.sol` | `0xeee0897a…64c5b7` |
| `QuestionInitialized(bytes32 indexed questionID, bytes ancillaryData, uint256 resolutionTime, address rewardToken, uint256 reward, uint256 proposalBond, bool earlyResolutionEnabled)` (adapter v1) | `uma-ctf-adapter` v1.0.1, `contracts/UmaConditionalTokensBinaryAdapter.sol` | `0x53af6c2e…e8a031` |
| `AncillaryDataUpdated(bytes32 indexed questionID, address indexed owner, bytes update)` (BulletinBoard `postUpdate`) | `src/interfaces/IBulletinBoard.sol` | `0x0059e118…a836b` |
| `QuestionUpdated(...)` (v1 only; recorded, not part of any measure) | v1.0.1 | `0x32da4770…35a17b` |

No address filter is applied, so all adapter deployments are covered. The creation log is the earliest
`QuestionInitialized` (preferring one emitted by the Gamma `resolvedBy` adapter). Creation text = UTF-8
ancillary data; creation time = that log's block timestamp.

**Measures** (no outcomes, prices, trades or close times are read; markets.parquet is read only for
`market_id, event_id, category, question, market_start_time`):

- **M1 title edit**: the creation-text title (between `title:` and the following `description:`) differs
  from Users v1.3 `question` after Unicode NFKC, whitespace collapse and case-folding.
- **M2 deadline edit**: the frozen `schedule_grammar_v5.parse` gives an instant for both the creation
  text's description part (creation block time as year reference) and the Gamma description (Users v1.3
  `market_start_time` as year reference), and they differ by ≥ 1 h. Denominator: markets where both parse.
  0 < |Δ| < 1 h is reported separately as FORMAT. `delta_hours` = current − creation.
- **M3 on-chain clarification**: ≥ 1 `AncillaryDataUpdated` log for the questionID on the creating adapter,
  from the creation block to HEAD. Any poster counts (the pre-registered measure); the creator-only count is
  reported as a supplementary, non-pre-registered figure.

**CIs.** Wilson 95%. Event-cluster bootstrap: 10,000 resamples of Users v1.3 `event_id` clusters with
replacement (`numpy.random.default_rng(20261111)`, one index matrix shared across measures), rate =
Σk/Σn over resampled clusters, percentile 2.5/97.5.

## Sources

- Polygon logs: Tenderly public keyless gateway `https://gateway.tenderly.co/public/polygon` (accepts
  full-range `eth_getLogs` with a topic filter). Checked against an independent keyless provider (Tatum
  public gateway) in `source_check.json`.
- Users v1.3 (CC-BY-4.0; Polymarket-API fields remain under Polymarket's terms), Gamma API text as of
  2026-10-07, `schedule_grammar_v5.py` (+ its v3/v4 dependencies) imported unchanged (shipped in
  `../date_fields/data/`); sha256 of every input is in `PN-2_result.json`.

## Reproduce

The scripts read `markets.parquet` (Users v1.3) and `gamma_rules.jsonl`, a 733 MB Gamma API snapshot
taken 2026-10-07 that is not part of the public dataset. `data/gamma_rules_trimmed.jsonl.gz` (31 MB)
holds what the scripts use from it: `market_id`, `found` and `questionID` for all 727,053 population
markets, and the full Gamma record for the 2,000 drawn markets. Build a working directory (do not write
into your dataset folder), then run the unchanged scripts from it. `<grammar_dir>` is
`../date_fields/data` (`schedule_grammar_v3/v4/v5.py`).

```
mkdir -p work/root && cd work
ln -s /path/to/users_v1.3/markets.parquet root/
gunzip -c ../data/gamma_rules_trimmed.jsonl.gz > root/gamma_rules.jsonl
python ../sample.py root draws.json
python ../measure.py root ../../date_fields/data draws.json ../fetch_raw.jsonl edit_rate_sample.csv PN-2_result.json
cmp edit_rate_sample.csv ../edit_rate_sample.csv     # identical
```

Checked 2026-11-16 from a fresh clone: `draws.json` matches the committed one except the input hash
(the trimmed file has its own sha256, `e6a4f1a4…`), `edit_rate_sample.csv` is byte-identical, and
`PN-2_result.json` differs only in input hashes, `generated_utc` and the output file name.

The two network steps re-query Polygon and need the full snapshot plus `F1_onchain_instants_final.json`
(shipped in `../date_fields/data/`) in the data directory:

```
python verify_source.py <data_dir> <grammar_dir> source_check.json
python fetch.py <data_dir> draws.json fetch_raw.jsonl --upto 1400   # raise --upto if measure.py asks
```

## Run record (2026-11-11/12)

- Population 727,053 markets; sha256 of sorted ids `cf5d6281…f7bf538` (`draws.json`).
- Source check (`source_check.json`, all passed): for markets 1731345, 519576, 1068327 (A13 status ok) the
  creation log was found, its text re-parsed to the A13 instant, the same log (tx hash and data bytes) was
  re-read from Tatum, block timestamps matched, and the one clarification log (1068327) was re-read too.
  A 2,000,000-block `AncillaryDataUpdated` query returned 1,068 logs in one call and in 20 × 100k chunks.
  Source and independent heads were equal (97,166,594). 1RPC was unreachable from this machine at check
  time; PublicNode and dRPC were not used.
- Fetch HEAD block 97,166,757. 1,400 draws fetched, 0 RPC failures. The 1,000th verified market is draw
  1,372, so 372 replacements were used (`replaced_draws.csv`).

## Limits

- **When edits happened is unknown** beyond the M3 log timestamps. Only two states are seen: the creation
  log and the current text (Gamma descriptions as of 2026-10-07, Users v1.3 `question` as of the dataset's
  v1.3 build, 2026-07-06). Edits that were made and later reverted are invisible.
- **The measured population is UMA-adapter markets.** All 372 replaced draws had no `QuestionInitialized`
  log: 362 Crypto markets with no Gamma `resolvedBy`, all titled "… Up or Down …" (in the one checked by hand,
  1243632, the questionID appears only in a CTF `ConditionPreparation` log with a non-UMA oracle) and 10 Sports markets resolved by
  `0xb21182d0…` (the UMA sports oracle, which emits no per-market ancillary question text). About 27% of
  draws (372/1,372) fall outside what M1–M3 can measure, and Crypto is under-represented among verified
  markets as a result.
- **M2 covers only markets whose rules contain a deadline clause the frozen v5 grammar accepts**: 641 of
  1,000 (590 of them Sports). 357 parse in neither text, 1 only in the creation text, 1 only in the current
  text. M2 says nothing about markets without a parsable deadline.
- **M1 is a text-difference flag, not a semantic one.** It flags any change after NFKC/whitespace/case
  normalisation, including placeholder names later replaced by real ones (e.g. "Company A" → a company
  name). The CSV has both titles for every row.
- **M3 counts any poster** (the pre-registered measure). The adapter lets anyone post an update; the
  creator-only count is reported separately in `PN-2_result.json` → `supplementary` (not pre-registered).
- The sample is 1,000 markets in 989 distinct events, so the cluster bootstrap and Wilson CIs are close;
  with k ≤ 8 positives per measure, both intervals are wide relative to the point estimates.
- v1-adapter markets (9 of 1,000) have no bulletin board, so their M3 is 0 by construction; a v1
  `QuestionUpdated` count is recorded in `fetch_raw.jsonl` (0 for all 9) but is not part of any measure.
- No `AncillaryDataUpdated` logs for a sampled questionID were found on any other adapter, no creation log
  disagreed with Gamma `resolvedBy`, and no questionID had more than one `QuestionInitialized` log.

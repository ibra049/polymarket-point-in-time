# Post-creation deadline edits in Polymarket "by <deadline>" markets (PN-1)

A descriptive audit. For Polymarket markets whose rules say *"will resolve to Yes if X happens by
<deadline>"*, we compare the deadline written in the **creation-time on-chain question text** with
the deadline in the **Gamma rules text as fetched on 2026-10-07**, and classify every difference
with a rule frozen before the counts were computed (`PN-1_prereg.md`).

No outcomes, prices or trades are read anywhere in this package. Nothing here is a claim about
why a deadline was edited or what an edit did to a market.

## Result

Of 5,744 F1 markets, 5,559 have a verified creation-time on-chain deadline (`final_status = ok`). 42 of those have a different deadline in the current text (32 later, 10 earlier, by sign). Under the frozen rule:

| Class | Markets | Distinct events | Median \|Δ\| (days) |
|---|---|---|---|
| FORMAT | 4 | 4 | 0.0007 |
| MATERIAL-LATER | 31 | 13 | 58.9583 |
| MATERIAL-EARLIER | 7 | 7 | 92.0417 |
| **Material, total** | **38** (0.68% of 5,559) | **20** | **58.9583** |

Material edits, largest |Δ| first (Δ = current − creation; full rows with both texts in `deadline_edits.csv`):

| market_id | event_id | event slug | class | Δ (days) |
|---|---|---|---|---|
| 1731346 | 310530 | iran-agrees-to-surrender-enriched-uranium-stockpile-by | MATERIAL-LATER | +275.0417 |
| 524292 | 19123 | will-trump-withdraw-the-us-from-nato-in-2025 | MATERIAL-LATER | +184.0417 |
| 1731345 | 310530 | iran-agrees-to-surrender-enriched-uranium-stockpile-by | MATERIAL-LATER | +91.0 |
| 573828 | 36308 | claude-5-released-by | MATERIAL-LATER | +89.9583 |
| 573830 | 36309 | grok-5-released-by | MATERIAL-LATER | +89.9583 |
| 587167 | 41639 | afd-deaths-foul-play-confirmed-in-2025 | MATERIAL-LATER | +61.0417 |
| 587171 | 41642 | meek-mill-releases-ai-app-in-2025 | MATERIAL-LATER | +61.0417 |
| 511867 | 14034 | trump-administration | MATERIAL-LATER | +58.9583 |
| 511868 | 14034 | trump-administration | MATERIAL-LATER | +58.9583 |
| 511869 | 14034 | trump-administration | MATERIAL-LATER | +58.9583 |
| 511870 | 14034 | trump-administration | MATERIAL-LATER | +58.9583 |
| 511871 | 14034 | trump-administration | MATERIAL-LATER | +58.9583 |
| 511872 | 14034 | trump-administration | MATERIAL-LATER | +58.9583 |
| 511873 | 14034 | trump-administration | MATERIAL-LATER | +58.9583 |
| 511874 | 14034 | trump-administration | MATERIAL-LATER | +58.9583 |
| 511877 | 14034 | trump-administration | MATERIAL-LATER | +58.9583 |
| 511878 | 14034 | trump-administration | MATERIAL-LATER | +58.9583 |
| 511879 | 14034 | trump-administration | MATERIAL-LATER | +58.9583 |
| 511880 | 14034 | trump-administration | MATERIAL-LATER | +58.9583 |
| 568052 | 34328 | will-trump-pardon-ghislaine-maxwell-by-august-31 | MATERIAL-LATER | +31.0 |
| 1731344 | 310530 | iran-agrees-to-surrender-enriched-uranium-stockpile-by | MATERIAL-LATER | +30.0 |
| 581142 | 39659 | which-cities-will-trump-send-the-national-guard-to-by-september-30 | MATERIAL-LATER | +15.0 |
| 581143 | 39659 | which-cities-will-trump-send-the-national-guard-to-by-september-30 | MATERIAL-LATER | +15.0 |
| 581144 | 39659 | which-cities-will-trump-send-the-national-guard-to-by-september-30 | MATERIAL-LATER | +15.0 |
| 581146 | 39659 | which-cities-will-trump-send-the-national-guard-to-by-september-30 | MATERIAL-LATER | +15.0 |
| 581147 | 39659 | which-cities-will-trump-send-the-national-guard-to-by-september-30 | MATERIAL-LATER | +15.0 |
| 581148 | 39659 | which-cities-will-trump-send-the-national-guard-to-by-september-30 | MATERIAL-LATER | +15.0 |
| 518002 | 16540 | sunset-wildfire-burns-1k-or-more-acres-by-sunday | MATERIAL-LATER | +2.0 |
| 790889 | 95318 | will-baluta-flip-ciucu-for-bucharest-mayor-by-saturday | MATERIAL-LATER | +1.0 |
| 502112 | 10919 | bitcoin-all-time-high-in-june | MATERIAL-LATER | +0.9993 |
| 687789 | 83837 | sp500-all-time-high-by-december-31 | MATERIAL-LATER | +0.4583 |
| 504389 | 11794 | will-openai-release-gpt-5-in-2024 | MATERIAL-EARLIER | -365.0 |
| 663965 | 72458 | will-nancy-pelosi-announce-her-retirement-by | MATERIAL-EARLIER | -365.0 |
| 253241 | 902946 | will-the-kyberswap-exploiters-demands-be-met | MATERIAL-EARLIER | -197.959 |
| 581003 | 39652 | trump-renames-department-of-defense-by-september-30 | MATERIAL-EARLIER | -92.0417 |
| 552105 | 26897 | will-israel-declare-war-on-iran-by-next-friday | MATERIAL-EARLIER | -10.0 |
| 525275 | 19679 | mary-kate-cornett-statement-by-friday | MATERIAL-EARLIER | -7.0 |
| 525277 | 19681 | adan-test-pump-fun | MATERIAL-EARLIER | -0.4993 |

Events are clustered: of the 31 extensions, 12 are in one event (14034), 6 in another (39659) and 3 in a third (310530). The 4 FORMAT rows differ by 59 or 60 seconds. In three of them a date-only deadline (read as 23:59:59 ET) was restated with an explicit "11:59 PM" or "11:59:59 PM" ET (both read as 23:59:00, because the grammar drops seconds), so the parsed difference is at the parser's resolution. The fourth (1144762) changes "before 2:59 PM" to "by 3:00 PM".

**Creation-text errors (A13a), reported separately:** 51 markets in 23 events have a creation-time on-chain deadline at or before `market_start_time`. In 43 of them the current text has a different deadline (median |Δ| 365.0 days, mostly a one-year correction); in 8 the current text parses to the same past instant. They are listed in `creation_text_errors.csv`.

**Creation texts:** retrieved from Polygon for all 93 listed markets (42 edits + 51 A13a). All 93 logs were re-read byte-identical from a second, independent RPC provider. Re-parsing both texts with the included grammar reproduces both recorded instants for 92 of 93. The exception is 1117833 (A13a), whose creation text reads "March 31, 20256": the A13 run read the year as 2025, while the committed grammar, after the A13a regex fix, reads no year. The file as recorded is what is classified. Separately, re-parsing all 5,744 Gamma texts in the full 2026-10-07 snapshot (733 MB, not included) reproduces every recorded `gamma_instant`.

## Data

| Input | Source | sha256 |
|---|---|---|
| `markets.parquet`, `events.parquet` | Hugging Face dataset [`vgregoire/polymarket-users`](https://huggingface.co/datasets/vgregoire/polymarket-users), commit `91ddb961` ("Users v1.3"), CC-BY-4.0. Only `market_id, event_id, question, market_start_time` and `event_id, event_ticker, title` are read. | in `summary.json` |
| `inputs/F1_onchain_instants_final.json` | Output of the A13 run (2026-10-08), one row per F1 market: `gamma_instant`, `onchain_instant`, `status`, `final_status`, `changed`. Produced as described under *How the instants were made*. | in `summary.json` |
| `inputs/gamma_rules_subset.jsonl` | The Gamma API records (`description`, `questionID`, `negRisk`, `negRiskRequestID`, `resolvedBy`, `createdAt`) fetched 2026-10-07 for the 93 markets listed here. The full snapshot covers every Users v1.3 market; only these rows are needed. | `ebb80e368811163904d64c887921df179ccf646254085b371c97194e4d017b24` |
| `creation_texts.jsonl` | Output of `fetch_creation_text.py`: for each listed market, the `QuestionInitialized` log (block, tx hash, block time, decoded ancillary text), the Gamma text, and a re-parse of both. | in `summary.json` |

## Reproduce

Python 3.11+ with `pyarrow`. Put `markets.parquet` and `events.parquet` from the dataset at commit `91ddb961`
(see the top-level README, *Setup*) in a directory, e.g. `DATA/`.

```bash
# 1. the classification, counts and CSVs (about 1 s; no network)
python audit.py DATA/

# 2. optional: re-fetch the creation-time texts from Polygon (keyless public RPC, about 1 h, polite)
python fetch_creation_text.py DATA/ --out creation_texts.jsonl
python audit.py DATA/          # merges the texts into the CSVs
```

`audit.py` writes `deadline_edits.csv`, `creation_text_errors.csv` and `summary.json`. It is
deterministic: the same inputs give byte-identical outputs. Flags: `--f1`, `--texts`, `--out-dir`.

`fetch_creation_text.py` defaults to the keyless endpoints `https://poly.api.pocket.network`
(search) and `https://polygon-mainnet.gateway.tatum.io` (one-block re-read of each found log, as an
independent second provider); `--rpc` / `--verify-rpc` change them. Without
`--gamma-rules` the Gamma records are fetched live from `gamma-api.polymarket.com`, which may by
now differ from the 2026-10-07 snapshot.

## Method

### How the instants were made (A13, 2026-10-08)
1. **Rules text.** The Gamma `description` of every Users v1.3 market was fetched on 2026-10-07.
2. **F1 population.** `schedule_grammar_v3.parse` (included) extracts one resolution-determining
   instant per market. Family F1 is an affirmative main clause "… will resolve … if X by / no later
   than / on or before / until / through / before / prior to <date> [time] [zone]". 5,744 markets are
   F1. The Gamma instant (`gamma_instant`) uses `market_start_time` for year inference.
3. **Creation-time text.** For each F1 market, the UMA CTF adapter `QuestionInitialized` log for its
   `questionID` (`negRiskRequestID` for NegRisk markets) was searched within ±2 days of
   `market_start_time`. Its `ancillaryData` is the question text written on chain when the market was
   created. It is emitted once per question. The same parser on that text, with the creation block
   time for year inference, gives `onchain_instant`.
4. **Statuses.** `ok` if the on-chain text parses to an F1 instant; else excluded (no creation event,
   no clause, other family, invalid date). **A13a:** an `ok` row whose on-chain instant is at or
   before `market_start_time` is a *creation-text error* (the deadline had already passed when the
   market was created, typically a wrong year) and is listed separately, never as an edit.
   `changed` = the two instants differ.

### Frozen classification (PN-1)
On rows with `final_status == "ok"` and `changed == true`, with
Δ = current Gamma instant − creation on-chain instant:

| Class | Rule |
|---|---|
| FORMAT | \|Δ\| < 1 hour (restatements such as 11:59:59 PM vs 11:59 PM) |
| MATERIAL-LATER | Δ ≥ +1 hour |
| MATERIAL-EARLIER | Δ ≤ −1 hour |

Counts are by market and by distinct `event_id`. Sizes are listed per market, with the median |Δ|.

## What this cannot see

- **When an edit happened.** Only two snapshots are compared: the creation record and the
  2026-10-07 Gamma text. The edit could have happened at any time in between, including after
  the deadline or after resolution.
- **Intermediate and reverted edits.** A deadline changed and later changed back, or changed
  several times, shows at most as the net difference.
- **Edits that do not change the parsed instant.** Only the deadline instant is compared, not the
  rest of the text. Clarifications posted elsewhere (e.g. on-chain bulletin-board updates or
  comments) are not read.
- **Markets outside F1, or excluded from it.** Markets whose deadline the grammar does not parse,
  and the 185 F1 markets excluded at the on-chain step (120 with no creation event found in the
  window), are not audited.
- **Parser limits.** Grammar v3 drops explicit seconds (`11:59:59 PM` is read as 23:59:00) while a
  date-only deadline is read as 23:59:59. Some FORMAT rows are therefore parser artifacts, not text
  changes (see the texts in `deadline_edits.csv`). Year inference uses different reference times
  on the two sides (creation block time vs `market_start_time`).

## Files

| File | Content |
|---|---|
| `audit.py` | classification and counts |
| `fetch_creation_text.py` | on-chain lookup of the creation-time question text |
| `schedule_grammar_v3.py` | the deadline parser used in A13 (unchanged) |
| `deadline_edits.csv` | every `ok` + `changed` row: ids, event, question, both instants, Δ, class, both texts |
| `creation_text_errors.csv` | the A13a rows, same columns without class |
| `summary.json` | every count, the material-edit list, input sha256s |
| `PN-1_prereg.md` | the frozen pre-registration, verbatim |
| `inputs/` | the A13 instants file and the Gamma snapshot rows |

Data attribution: derived from Users v1.3 (vgregoire/polymarket-users, CC-BY-4.0), Polymarket's
public Gamma API, and public Polygon logs.

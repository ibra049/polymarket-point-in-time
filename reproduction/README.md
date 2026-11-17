# Reproduction of the published aggregates of arXiv:2609.12878

This folder reproduces 11 published aggregate values, plus one confidence-interval
containment rule, from a study of the favorite-longshot bias on Polymarket. It uses the
same public dataset and commit that the paper cites. All 12 checks pass. The checks were
frozen before the first run on 2026-10-08. A fresh re-run on 2026-11-12 (UTC) from the
unchanged original script gave byte-identical output.

This is a reproduction only. It computes the pre-registered checks and nothing else: no new
return statistics, no slicing by period or category, and no trading claims.

## Sources

**Paper.** Marcos Cardozo and José Ignacio Rivero-Wildemauwe (2026). *The Favorite-Longshot
Bias in Prediction Markets: Evidence from Polymarket.* arXiv:2609.12878 [econ.GN], v1,
submitted 11 September 2026. <https://arxiv.org/abs/2609.12878>

**Dataset.** Vincent Grégoire (2026). *Polymarket Users dataset*, version 1.3. Hugging Face
dataset `vgregoire/polymarket-users`, commit `91ddb961b090de18fd79e79edd8fa15f36ca11b9`
(2026-07-06), CC-BY 4.0. <https://huggingface.co/datasets/vgregoire/polymarket-users>.
This is the version and commit cited in the paper's references. The dataset's own README
asks users to cite the paper it was built for: Pat Akey, Vincent Grégoire, Nicolas Harvie
and Charles Martineau (2026), *Who Wins and Who Loses In Prediction Markets? Evidence from
Polymarket*, SSRN Working Paper 6443103.

## Files

| File | What it is |
|---|---|
| `reproduce.py` | The reproduction script (about 120 lines; numpy + pyarrow). |
| `checks.json` | The 12 frozen checks: paper values, where they are printed, tolerances, our values from both runs, pass/fail, and the filter-stage counts. |
| `rerun_2026-11/result_original_script_2026-11-12.json` | Raw output of the 2026-11-12 re-run of the original script. |
| `rerun_2026-11/recorded_2026-10-08_result.json` | The output recorded on 2026-10-08 (sha256 `d7b6636b…cd16`, identical to the re-run). |
| `rerun_2026-11/diff_vs_recorded.json` | Value-by-value comparison of the two: 55 values, 0 differences, byte-identical. |
| `rerun_2026-11/run.log`, `run.stderr`, `run_meta.txt` | Log, timing (`/usr/bin/time -l`) and start/end times of the re-run. |
| `rerun_2026-11/checksums_reverified.json` | Re-hash of every input file against the published SHA-256s. |
| `rerun_2026-11/public_script_run/` | Output and log of a run of `reproduce.py` itself (see below). |
| `rerun_2026-11/RUN_RECORD.json` | Environment, hashes and timings in one place. |

## 1. Download the dataset at the cited commit

The script needs only `predictions.parquet`, `user_features.parquet` and the 1,218 daily
`trades` files: 24,279,082,813 bytes (about 24.3 GB) in total.

```bash
pip install huggingface_hub numpy pyarrow
python - <<'EOF'
from huggingface_hub import snapshot_download
snapshot_download(
    repo_id="vgregoire/polymarket-users",
    repo_type="dataset",
    revision="91ddb961b090de18fd79e79edd8fa15f36ca11b9",
    allow_patterns=["trades/**", "predictions.parquet", "user_features.parquet"],
    local_dir="users_v1.3",
)
EOF
```

At that commit the patterns select exactly 1,220 files: 1,218 trades files plus the two
parquet files. Each file's LFS SHA-256 is published by the Hub, for example at
`https://huggingface.co/api/datasets/vgregoire/polymarket-users/tree/91ddb961b090de18fd79e79edd8fa15f36ca11b9/trades?recursive=true`.
Our copy matches the Hub's SHA-256 for all 1,218 trades files and for `predictions.parquet`,
`user_features.parquet`, `markets.parquet` and `events.parquet`. It was re-hashed in full on
2026-11-12: 24,309,274,723 bytes, 0 mismatches.

## 2. Run

```bash
python reproduce.py users_v1.3 result.json
```

The script prints progress every 100 files and then the checks, and it writes
`result.json`. The verdict is `PASS` only if all 12 checks pass.

**Resources.** On an Apple M1 with 8 GB RAM (macOS 26.4.1, Python 3.14.3, numpy 2.4.5,
pyarrow 24.0.0), the original script took 3,319 s (55 min 19 s) wall time, and `reproduce.py`
took 1,510 s (25 min 10 s) right after it. Peak memory footprint was 7.5 to 8.5 GB, with a
maximum resident set of 3.9 to 4.2 GB, so an 8 GB machine swaps; 16 GB is recommended.
The script reads the trades files one at a time. In memory it keeps per-market running sums
and the set of high-HHI buyer addresses.

## 3. The 12 checks

The targets and tolerances were frozen on 2026-10-07, before the first run, and have not
changed since. Two earlier, looser drafts (±10%, then ±1% on counts and ±0.05 pp on returns)
were tightened to the rules below before any outcome data was read. The rules:
- counts must match exactly;
- amounts must be within half a unit of the published rounding;
- returns must be within ±0.01 percentage points of the published point estimate. The code
  adds 1e-9 of float slack.

| # | Check | Paper (where printed) | Tolerance | Ours | Pass |
|---|---|---|---|---|---|
| 1 | Observed transactions | 588,287,492 (Table 1A) | exact | 588,287,492 | yes |
| 2 | R0a return-sample purchases | 560,909,624 (Table 1A, "Resolved by March 29, 2026") | exact | 560,909,624 | yes |
| 3 | R0b return-sample amount paid | $22.49B (Tables 1A, 4) | ±$0.005B | $22.492829B | yes |
| 4 | R0c favorite (p ≥ 0.90) amount paid | $9.662B (Table 4) | ±$0.0005B | $9.661963B | yes |
| 5 | R0d longshot (p < 0.10) purchases | 100.7M (Table 4) | ±0.05M | 100.686926M | yes |
| 6 | R1 pooled favorite return | +0.83% (Table 6B) | ±0.01 pp | +0.8332% | yes |
| 7 | R1eq equal-child-market favorite return | +0.277% (Table 6A) | ±0.01 pp | +0.2769% | yes |
| 8 | R2 pooled taker ("accepted seller's offer") favorite return | 0.877% (Table 16A) | ±0.01 pp | +0.8775% | yes |
| 9 | R2m pooled maker ("posted purchase offer") favorite return | 0.816% (Table 16A) | ±0.01 pp | +0.8163% | yes |
| 10 | R3 pooled longshot return | −19.35% (Table 6B) | ±0.01 pp | −19.3475% | yes |
| 11 | R3b equal-child-market longshot return | −6.30% (Table 6A) | ±0.01 pp | −6.3002% | yes |
| 12 | R3 inside the paper's 95% interval | [−46.99, 8.30]% (Table 6B) | frozen as [−46.9, 8.30] | −19.3475% | yes |

Full-precision values are in `checks.json`. R2 and R2m pass separately, which shows that the
taker and maker roles are not swapped.

**Transcription note on check 12.** The frozen rule records the interval's lower bound as
−46.9, but the paper prints −46.99. The frozen interval is the narrower of the two, and the
value lies well inside both. The rule is reported as frozen and has not been edited.

**Conventions (from the paper, section 2 and Tables 1, 4, 6, 16).** There is one purchase
per trade row, attributed to the buyer: the taker if `taker_bought`, otherwise the maker.
The cumulative filters are:
1. complete fields;
2. distinct buyer and seller;
3. 0 < price ≤ 1 and quantity > 0;
4. two-outcome markets;
5. buyer lifetime counterparty HHI < 0.5 (from `user_features`);
6. a known winner (resolved by 2026-03-29).

Return = (quantity × winner − cost) / cost. "Pooled" sums cost and gain over purchases.
"Equal child market" computes each market's pooled return and then averages over markets
with equal weight. Favorites are p ≥ 0.90 and longshots are p < 0.10.

## 4. Disclosed diagnostic: filter-stage counts

This diagnostic is not a pass criterion. Before the first run we decided to also output
the row count after each filter stage, so that a failure could be located without any
outcome-bearing debugging. Compared with paper Table 1A:

| Stage | Paper Table 1A | Ours | Ours − paper |
|---|---|---|---|
| Observed transactions | 588,287,492 | 588,287,492 | 0 |
| Complete fields; distinct buyer and seller | 588,286,587 | 588,286,587 | 0 |
| Valid quantity and price | 588,286,587 | 588,286,587 | 0 |
| Two-outcome markets | 588,258,033 | 588,286,587 | +28,554 |
| Buyer counterparty HHI < 0.5 | 586,123,163 | 586,151,609 | +28,446 |
| Resolved by March 29, 2026 | 560,909,624 | 560,909,624 | 0 |

In this release, `predictions.parquet` lists 39 markets (173 outcome tokens) with more than
two outcomes. The release contains **zero** trade rows for them, matched by either
`prediction_id` or `market_id`; this was re-checked on 2026-11-12 from those two columns only.
Our two-outcome filter therefore removes nothing, while the paper's removes 28,554 rows. The
gap carries through the HHI stage. By subtraction from the table, 108 of the extra rows are
removed at the HHI stage and the remaining 28,446 at the resolved stage. At the resolved
stage the counts become identical, and so do all published aggregates.

The paper's Table 1A shows the same child-market count (614,863) before and after its
two-outcome filter, so the table alone does not show which markets those 28,554 rows came
from. We did not investigate further: no outcome-bearing query was run beyond the frozen
checks.

## 5. Trade-level validation against the chain (PC-2)

The aggregates above validate the pipeline in total. Before the first run, the dataset's
trade rows were also checked one transaction at a time against the Polygon CTF Exchange
`OrderFilled` event logs. The check used a free public Polygon RPC node and two fixture
scripts. Each script's pass rule was written down before it ran. The numbers below are
taken from the scripts' JSON outputs, not from prose.

| | PC-2 v1 (2026-10-06) | PC-2 v2 (2026-10-07) | Total |
|---|---|---|---|
| Random seed | 20261006 | 20261007 | |
| Transactions scanned | 48 | 47 | 95 |
| Transactions checked | 20 | 26 | **46** |
| Complementary match, taker buys | 5 | 5 | 10 |
| Complementary match, taker sells | 6 | 5 | 11 |
| MINT (both sides buy) | 7 | 14 | 21 |
| MERGE (both sides sell) | 2 | 2 | 4 |
| Multi-maker transactions (overlap the rows above) | 3 | 5 | 8 |
| Transactions from 2026 | (not a quota) | 14 | |
| Dataset rows = passive fills checked | 23 | 33 | 56 |
| Polygon blocks | 38,451,484 to 77,515,308 | 55,724,631 to 81,996,084 | |
| Approximate dates | Jan 2023 to Oct 2025 | Apr 2024 to Jan 2026 | |
| Transactions with any problem | 0 | 0 | 0 |
| Verdict | PASS | PASS | |

Dates are bracketed to within about three days from a block-number-to-timestamp index.

**How it works.** In this dataset `trade_id` is the Polygon transaction hash. For each sampled
transaction, the script:
1. finds the block with the trade's timestamp;
2. reads the block receipts;
3. decodes the `OrderFilled` logs;
4. separates the passive fills (one per resting order) from the exchange's active aggregate;
5. classifies the match as COMPLEMENTARY, MINT or MERGE.

For complementary fills, each passive fill must map to exactly one dataset row with:
- the same token;
- the same maker and taker;
- quantity and price within 1e-6;
- `taker_bought` equal to the taker's on-chain direction.

No row may duplicate the aggregate. v2 added these required assertions:
- the MINT/MERGE flag convention below;
- the complement identity: the maker's and taker's tokens are the two outcomes of one
  condition, via `predictions.negative_token`;
- per-transaction conservation: row shares equal passive shares, and the active aggregate
  equals the sum of the passive fills;
- row cash Σ(p·q) equal to passive USDC within 1e-4;
- at least 3 transactions from 2026.

**Finding: how MINT and MERGE matches are recorded.** In every case the dataset writes one
row per passive fill, on the passive maker's token, at the maker's price:
- **MINT** (both sides buy; new shares are minted): the row shows the taker *selling* the
  maker's token (`taker_bought = False`). On chain, the taker *bought* the complementary token
  at 1 − p. Seen in all 25 MINT fills: 7 in v1, where it was recorded, and 18 in v2, where it
  was asserted.
- **MERGE** (both sides sell; shares are merged back into collateral): the row shows the taker
  *buying* the maker's token (`taker_bought = True`). On chain, the taker *sold* the
  complement at 1 − p. Seen in all 5 MERGE fills: 2 in v1 and 3 in v2.

Selling token A at p is the same position change as buying its complement at 1 − p, so these
rows are exact position equivalents, and cash and shares are conserved. However, the trade is
recorded on the side the taker did not act on. A filter on `taker_bought = True` therefore
misses taker purchases made through MINT. This does not affect the reproduction, which, like
the paper, uses the dataset's convention as recorded. It does matter for any strategy defined
on the taker's actual action. The claim covers only the CTF Exchange transaction types seen in
these 46 samples.

## 6. Re-run record (2026-11-12 UTC)

- **Script.** The original script (sha256 `72975daf815a3721084f39cae2e48ea10cdd83699159e5120f685fd1581a0d58`),
  unchanged since it was committed before the first run.
- **Inputs.** All 1,218 trades files and the four metadata parquet files were re-hashed and
  match the published SHA-256s (see section 1).
- **Times.** Start 2026-11-12T03:08:53Z, end 2026-11-12T04:04:12Z, wall 3,319.39 s.
- **Result.** PASS, 12/12. The output JSON is byte-identical to the 2026-10-08 record
  (sha256 `d7b6636b80f6d11509c9337958ff77e4c3095b0b2e5ca5fbe433e48c5965cd16`): 55 of 55
  values equal, 0 differences.

**`reproduce.py` vs the original script.** The computation is identical. Only these differ:
- the docstring;
- one comment, which said "222 tokens" where this release has 173 tokens in the 39
  multi-outcome markets;
- the failure label of the verdict string.

Because the label is not a comment, `reproduce.py` was also run end to end on the same data;
see `rerun_2026-11/public_script_run/`. That run (sha256 of `reproduce.py`
`953241b208e3cce9a97f8c7dfb224cb829018087c90961d4aea25247d689063c`, 2026-11-12T04:04:58Z to
04:30:08Z, wall 1,509.61 s) returned PASS, and its output is byte-identical to the original
script's (same sha256 `d7b6636b…cd16`).

## Limits

- Matching the published aggregates shows that this pipeline computes what the paper
  computed. It does not show that the paper's conclusions are right, or that any trading rule
  would be profitable after fees, spreads and execution.
- The full-window aggregates cover every period. Nothing in this reproduction was tuned on
  them.

# Point-in-Time Integrity of Polymarket Research Data

Ibrahim El Makhtoum · November 2026

Prediction-market backtests usually take market metadata from today's API and
assume it was known when each trade happened. This repository tests that
assumption on Polymarket, and releases every list, script and frozen protocol
needed to check the results.

**Technical note:** [`note/note.pdf`](note/) (3–4 pages; Markdown source in `note/note.md`).

## Findings

| | Result | Folder |
|---|---|---|
| **Exact replication** | A published 588-million-trade study of the favorite–longshot bias (Cardozo and Rivero-Wildemauwe, 2026) is reproduced from its public dataset. All 12 pre-registered checks pass, a fresh rerun gives byte-identical output, and a second implementation written independently from the paper reproduces the four headline values. | `reproduction/` |
| **Deadline edits** | Of 5,559 "will X happen by ⟨date⟩" markets, 38 (0.68%, 20 events) had their deadline materially changed after creation: 31 extended (median +59 days) and 7 moved earlier. Creation-time text is recovered from on-chain records, and every flagged market is listed with both texts. | `deadline_edits/` |
| **Population edit rate** | In a pre-registered random sample of 1,000 verifiable markets, 0.7% had their title changed after creation, 1 of 641 comparable deadlines moved (by 24 h), and 0.8% had an on-chain update to their terms. Independently recomputed and spot-checked on-chain. | `edit_rate/` |
| **Date fields and outcomes** | The dataset's realized closing time is strongly associated with the outcome (+44 percentage points), so it must not be used as a scheduled date. The scheduled expiration field shows a smaller association (+19 points, CI 10–28) that falls short of the pre-registered threshold. | `date_fields/` |
| **Null results** | No YES/NO arbitrage in quotes (a mirrored book). No basket arbitrage above fees at 6-hourly cadence. Equal-weight taker favorite buying is ruled out by the taker fees in force on 2026-10-05. Each result is scoped to what was tested. | `negative_results/` (fee screen: `negative_results/fee_screen/`) |
| **Options benchmark (E-006)** | A forward test of Bitcoin daily markets against option-implied probabilities ended **INVALID-RUN**: its frozen pipeline check failed on 12 of 61 snapshots (limit 5%). The failures were traced to inconsistent (non-convex) source option data. The statistic is not interpreted, and the question stays open. | `options_benchmark/` |

None of this is a trading claim. The project only reads data: it holds no
wallet, places no orders and does no live trading.

## How the work was done

- **Direction:** I set the research questions, priorities and go/no-go
  decisions. AI coding assistants (Claude and Codex) helped implement and
  check the analyses.
- **Protocols first:** every test has a written protocol with its decision
  rule. With the exceptions disclosed in `PREREGISTRATION.md` (PN-1's rule
  followed partial exposure; the mirrored-book check had no numeric threshold;
  PN-2's and E-002's code went into git together with their output), each was
  committed before the data it judges was read.
- **Independent checks:** whoever built an analysis did not interpret it. The
  headline numbers were recomputed by a second implementer with separate code,
  and the replication was redone from the paper's definitions alone. The records
  are in `independent_checks/`, and `note/NUMBERS.md` labels every number.
- **Failures kept:** failed first attempts are kept and disclosed rather than
  re-run quietly. Example: the first date-field test used a boundary that
  mostly captured a time-zone convention. It is reported as run, and a fresh
  pre-registered test followed on new data.

Each folder's README gives the question, the frozen rule, the inputs with
checksums, the command to rerun, and the limits of the claim.

## Data and licences

- Polymarket Users v1.3 (Akey, Grégoire, Harvie and Martineau, 2026), Hugging
  Face `vgregoire/polymarket-users` @ `91ddb961`, CC-BY-4.0. Fields that come
  from the Polymarket API stay under Polymarket's terms.
- Creation-time market text: Polymarket's UMA adapter `QuestionInitialized`
  events on Polygon, read through public RPC endpoints.
- Order-book extract (2026-08-20/21): public Polymarket CLOB and Gamma data,
  captured by the author.

## Setup

Every folder runs on a laptop with Python 3.11 or later (`pip install -r requirements.txt`).
The replication scans 24 GB and takes about 55 minutes. The other scripts finish in seconds to
minutes. Download the dataset once, at the pinned commit:

```python
from huggingface_hub import snapshot_download
snapshot_download(
    repo_id="vgregoire/polymarket-users", repo_type="dataset",
    revision="91ddb961b090de18fd79e79edd8fa15f36ca11b9",
    allow_patterns=["trades/**", "markets.parquet", "events.parquet",
                    "predictions.parquet", "user_features.parquet"],
    local_dir="users_v1.3",
)
```

| Folder | Command (details in its README) | Needs |
|---|---|---|
| `reproduction/` | `python reproduce.py users_v1.3 result.json` | trades, predictions, user_features |
| `deadline_edits/` | `python audit.py users_v1.3/` | markets, events |
| `edit_rate/` | `sample.py` then `measure.py` on the shipped trimmed Gamma file | markets |
| `date_fields/` | stage 1, then run, for PN-3 and PN-3b | markets, predictions, user_features, trades |
| `negative_results/` | `python mirrored_book.py data/snapshots.csv.gz`; `negrisk_basket/E-002_compute.py ../data`; `fee_screen/E-001_compute.py` | shipped files only |
| `options_benchmark/` | offline `analyze(...)` on the shipped snapshots (see its README) | shipped files only |

Steps that re-query Polygon (the creation-time texts) or Polymarket's API are optional. Their raw
responses are shipped, so every number can be checked without network access. Protocol files are
verbatim copies, so some of them name the author's private working repository (`polysignal-ops`)
or local database (`polysignal.db`), and some use repository-relative paths from that repository (for example `research/...`, `src/analysis/...`, the `data/e006` branch). They are kept byte-identical because their sha256 values are pinned and checked; editing them would break that check. Neither is needed to rerun anything here.

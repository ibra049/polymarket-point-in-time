# E-006: Bitcoin daily markets vs. option-implied probabilities (INVALID-RUN)

**Question.** On Polymarket's daily "Bitcoin above X" markets, is the longshot side of tail
strikes priced above its options-implied probability by more than the taker fee plus
1 percentage point, at executable size? The benchmark is a smile-consistent digital
probability built from Deribit option implied volatilities.

**Design.**
- **Protocol:** `E-006.yaml`, v1.2. Frozen on 2026-11-06 04:02 UTC (commit `c9470aa` of the
  author's working repository), before any Polymarket price was viewed.
- **Data:** forward only. Hourly snapshots of Polymarket order books and Deribit options were
  taken from the freeze until 2026-11-17 00:00 UTC. No outcome is read.
- **Run:** a single analysis run, after the window closed.
- **Decision order (frozen):**
  1. a synthetic flat-benchmark gate;
  2. a pipeline gate, which fails the run if more than 5% of snapshots fail their
     consistency checks;
  3. a minimum sample;
  4. the test statistic S.

**Result: INVALID-RUN.**
- The flat-benchmark gate passed.
- **12 of 61 counted snapshots (19.7%) failed the pipeline checks**, against a frozen limit
  of 5%.
- Under the frozen rule the run stops there:
  - S and the secondary statistics are not interpreted, although they stay in the raw output;
  - the 49 passing snapshots are not re-analysed as a sample.
- The question remains open. This is not a REJECT.

**Why the checks failed.** A read-only diagnosis was run after the result
(`R-039_diagnosis_review.md`, `E-006_result.md`). It found:
- 16 monotonicity violations in 10 snapshots, and 3 bad marks in 3 snapshots (one snapshot has
  both);
- the monotonicity failures trace to **non-convex Deribit mark-implied-volatility smiles**
  passed through the frozen method, not to interpolation artefacts;
- that non-convexity is present in all 61 snapshots, including the 49 that passed;
- the upstream cause at the source is unknown.

The pipeline's own guard caught a source-data defect before the defect could reach a
conclusion.

**Collection gap.**
- From 2026-11-12 10:55 UTC, Polymarket's listing API refused the collector (HTTP 406).
- 61 of 260 scheduled hourly snapshots entered the sample.
- The collector and the window were not changed after the refusal began.
- The missing hours did not cause the pipeline failure.

## Files
| Path | What |
|---|---|
| `E-006.yaml`, `E-006_manifest.json` | Frozen protocol and run manifest; the manifest pins the sha256 of the protocol, the analysis code, the collector and its workflow |
| `code/e006.py`, `code/e006_snapshot.py`, `code/e006-collect.yml` | Analysis, collector and scheduled workflow, byte-identical to the pinned hashes. Standard-library Python |
| `data/snapshots/*.json.gz` | All 65 collected snapshots (1.4 MB). Their sha256 values match the run's own ledger in `results/output.json` (65/65) |
| `results/` | Raw output of the single run, exit code, stderr and run context. In `context.json`, the runner's local paths are replaced by placeholders |
| `E-006_result.md` | The independent reviewer's result record |
| `R-039_diagnosis_review.md` | The diagnosis review |

**Rerun.**
- The frozen `analyze()` binds its inputs to a git commit of the data branch (`data_commit`
  in the manifest), and that commit lives in the private working repository. An exact rerun
  of the original invocation therefore needs that commit.
- The code's offline path skips only that git binding, and its output is labelled
  `synthetic`. Run it on the shipped snapshots with the shipped manifest:

```python
import json, glob, importlib.util
spec = importlib.util.spec_from_file_location("e006", "code/e006.py")
e006 = importlib.util.module_from_spec(spec); spec.loader.exec_module(e006)
man = json.load(open("E-006_manifest.json"))
man["data_commit"] = "0" * 40   # placeholder; the offline path does not bind to git
out = e006.analyze(sorted(glob.glob("data/snapshots/*.json.gz")), man, synthetic=True)
print(out["status"], out["pipeline"]["fail_share"])   # INVALID-RUN 0.19672131147540983
```

- **Checked 2026-11-17:** the rerun reproduces exactly the original run's status, its
  pipeline failure share (12/61) and all of its counts (65 files, 61 in sample, 11,754 marks,
  3 bad).
- **On Python 3.15.1 (independent check):** seven floating-point diagnostics differ from the
  recorded run. These are the synthetic flat-gate error and six return quantiles, with
  differences between 6e-16 and 1.5e-13. The cause is unknown; platform math libraries are one
  possibility.
- **Status unaffected:** the differences don't touch the status, and the statistics stay
  uninterpreted in any case.
- **Records:** both outputs are kept (`../independent_checks/scrub/options_rerun/`).

# R-039: E-006 pipeline diagnosis, independent classification review (Claude, 2026-11-17)

- **Question:** does Codex's read-only diagnosis (`2026-11-17_E006_pipeline_diagnosis.md`,
  `codex/e006-diagnostic-1117` @ `95faf0c`) bind to the frozen loader and inputs,
  reconstruct the violations correctly, and classify them correctly (B for
  monotonicity, provisional C for marks)? Is more read-only diagnosis needed?
- **Inputs:** R-038; Codex note; `diagnostic_source.py`, `diagnostic_pipeline.json`,
  `run_manifest.json` in `research/results/E-006_2026-11-17/`; frozen
  `src/analysis/e006.py` (sha256 `912ca5b6…f2aff`, recomputed); data tree
  `data/e006` @ `43ae08c` (Codex's worktree `e006-data-1117`, clean, read only).
- **Method:** my own scripts in `research/results/E-006_2026-11-17/claude_review/`
  (`recon.py`, `src_digital.py`, `marks_prev.py`, `mag.py`, `raw.py`). They call
  only frozen helpers (`check_manifest`, `verify_data`, `select`, `validity`,
  `build_expiries`, `_markets`, `Surface`, `pipeline_check`). They read the Deribit
  fields and the Polymarket strike labels and end dates that `pipeline_check`
  already uses. They do **not** call `analyze()` or `observations()`, and they never
  read books, Polymarket prices, net_gap or S.
- **Scope:** classification review only. No fix, rerun, retry, source request,
  new window or status change. No production access.

## Verdict
- **Bindings and reconstruction: agree.** Reproduced exactly.
- **Monotonicity is B, not A: agree**, with one correction to the mechanism.
  The violations come from **Deribit's own mark prices**, which are not convex
  across listed strikes. The frozen surface has no arbitrage repair, so it
  passes that through into D. They are not interpolation-kink artifacts. My
  R-038 §3 hypothesis is **not supported**.
- **Marks are provisional C: agree.** Rounding and collection timing are ruled
  out. B stays possible.
- **INVALID-RUN is unchanged. B-14 stays unresolved.**

## 1. Bindings (checked)
- **Same inputs as the frozen run.** `diagnostic_source.py` runs
  `check_manifest`, then `verify_data` against `43ae08c`, then `select` with the
  pinned collector hash. That is the same order and the same functions as
  `analyze()` (e006.py:712–735).
- **`analyze()` filters on `validity(s) is None`.** The script asserts the same
  for all 61 snapshots. I got 61 selected, 61 valid and 12 failing.
- **Manifest:** `run_manifest.json` differs from `E-006_manifest.json` only in
  the filled `data_commit` (re-checked).
- **Module hash** in the JSON equals the recomputed sha256. Summary totals:
  11,754 / 3 / 16 / 0 / 61 / 12.
- **Limitation (minor):** the data path is hard-coded to Codex's worktree. Rerunning
  it elsewhere needs that path changed. It does not affect the result.

## 2. Reconstruction (re-derived independently)
- **Duplicated logic:** the script duplicates `pipeline_check`'s loops instead
  of instrumenting them. It sorts by (K, D), uses the same 1e-6 tolerances and
  the same `MARK_TOL`/`MARK_FLOOR`, and asserts per-snapshot equality with the
  frozen counts. That is adequate.
- **My count:** I rebuilt the per-event K*/D pairs myself and got the same
  16 violations in 10 snapshots, 0 range failures, 0 NA snapshots and no
  snapshot with `mark_checked` = 0.
- **Failure split:** 9 snapshots are mono-only, 1 is mono + mark (11-07 12:52),
  and 2 are mark-only (11-11 06:48, 11-12 03:55). That matches Codex.
- **All 16 pairs** have the two market strikes ~$2,000 apart (Polymarket labels
  2k apart) on the same surface.
- **All 16 D pairs** are in the tails: 14 have D < 1e-3, one has D ≈ 0.006 and
  one has D ≈ 0.995.

## 3. Monotonicity classification: B, but source-driven (correction to R-038)
- **No ±$50 kink crossing.** For every violation, I mapped K* onto each bracketing
  expiry. The nearest listed strike is 75–130 USD away. The one exception is
  T2 in 11-09 19:59 (10 USD), and that expiry is monotone there. So
  K* ± H never crosses a node, and each central difference sits inside one
  linear segment of w(k).
- **The source is non-monotone first.** I took the call-spread digital straight
  from Deribit mark IVs at adjacent listed strikes, with no interpolation. In
  **all 16** cases it already rises from the interval containing K*_lower to the
  interval containing K*_upper: on T1 in 16/16 and on T2 in 9/16.
  - The IVs show why. Very steep short-dated wings (T1 IV 50 → 77 over
    80k → 82k) end in flat repeated marks (72.86 ×3, 101.23 ×2, 61.94 ×3).
- **Model-free check.** Call prices built as `mark_price × own underlying_price`
  (no Black-76, no shared F) are also non-convex.
  - Within an expiry, the spread of underlying_price is at most $8.08 (median
    $0.30).
  - No node needed a put-IV fill.
  - So this is not an artifact of one-F-per-expiry or of mixing calls and puts.
- **Not rounding.** 476 of 486 non-convex strike triples exceed the change
  that rounding mark_iv to 2 decimals (±0.005) can produce.
- **Label B is right.** D really is non-monotone, so a check that enforces
  monotonicity is not wrong (so not A). The frozen method takes Deribit marks
  as arbitrage-free and applies no butterfly/monotonicity repair or wing
  filter.
- **More precise wording:** "B: the method passes source-mark butterfly
  violations into D". The more specific "interpolation defect" wording is
  wrong. The root cause on Deribit's side (stale or illiquid wing marks, how
  the marks are built) is not identified, and that is not needed for the status.

**Limitation that matters for any future design (not for this status):**
- Source non-convexity inside the covered strike region is present in **61/61**
  snapshots: 495 raw-mark triples, 251 of them larger than 1e-3 in digital units.
  That includes all 49 snapshots that passed.
- A snapshot passes only when no two same-event Polymarket strikes happen to
  straddle a non-convex region. The per-snapshot gate therefore
  **under-detects**: D in passing snapshots also rests on non-convex inputs.
- This strengthens R-038 §4. This data cannot support a re-analysis. Any
  re-frozen design needs arbitrage repair or wing exclusion, plus a gate on the
  source surface over the covered region, not only at K* pairs. A smoother
  interpolation would not fix it.

## 4. Mark-reproduction classification: provisional C (agree)
| Snapshot | Option | h to expiry | Rel. err (tol 0.02) | Quoted vs implied IV | Time shift needed |
|---|---|---|---|---|---|
| 11-07 12:52 | 8NOV26-75500-P | 19.1 | 0.031 | 19.19 vs 18.84 | 2,498 s |
| 11-11 06:48 | 11NOV26-73500-P | 1.2 | 0.020 | 31.27 vs 30.64 | 171 s |
| 11-12 03:55 | 12NOV26-74000-C | 4.1 | 0.022 | 25.70 vs 25.48 | 255 s |

- **What the three have in common:** all are cheap OTM options (0.0006–0.002
  BTC, close to the 0.0005 floor) and short-dated. All sit just over tolerance.
- **Rounding ruled out:** ±0.005 IV changes the error by < 0.1 pp.
- **Collection timing ruled out:** the snapshots took 13–14 s, far short of the
  171–2,498 s shift that would be needed.
- **What is left:** a Deribit mark_iv/mark_price inconsistency, or a
  time-to-expiry convention difference that only matters at very short tenors.
  The dump cannot separate the two. "C, provisional; B possible" is the right
  reading.
- **No effect on status:** the 2 mark-only snapshots barely exceed tolerance
  (2.01%, 2.19%), but even without them, 10/61 = 0.164 > 0.05.

## 5. Is further read-only diagnosis needed?
- **No, not for E-006 on this data.** The status does not depend on any open
  question. With A ruled out, INVALID-RUN holds under every reading.
- Finding Deribit's root cause would only matter if the owner later chooses
  to re-freeze for a fresh window. That would be design work, starting from
  §3's limitation, not a diagnosis of this run.
- **Disagreement with Codex:** none on the classification. One wording
  refinement (§3) is recorded here and does not need a rebuttal.

## Self-review note
I designed E-006 (R-022/R-025/R-026). The gap is mine: the design assumed
Deribit marks were arbitrage-free and never checked that on real smiles. The
kink hypothesis I suggested in R-038 turned out to be wrong.

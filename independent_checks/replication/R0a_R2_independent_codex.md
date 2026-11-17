# Job C — independent 588M headline recomputation

2026-11-16 UTC. **PROMOTE — these four historical pipeline checks only.**
**INCONCLUSIVE — exact reproduction of the paper's intermediate sample funnel.**
The first-pass JSON's conservative INCONCLUSIVE label is preserved; the scoped
headline decision follows the separately recorded comparison. No strategy or
tradeability decision is made, and none of the other eight author checks is
claimed independently verified here.

| Quantity | Independent first pass | Handoff | Paper | Comparison |
|---|---:|---:|---:|---|
| Observed trade rows | 588,287,492 | 588,287,492 | 588,287,492 | exact |
| R0a return-sample purchases | 560,909,624 | 560,909,624 | 560,909,624 | exact |
| R2 pooled taker favourite return (%) | 0.8774545230949155 | 0.8775 | 0.877 | within reporting precision |
| R2m pooled maker favourite return (%) | 0.8163412478445116 | 0.8163 | 0.816 | within reporting precision |

Signed differences from the full-precision author record are +5.551115123125783e-16
pp for R2 and +3.3306690738754696e-16 pp for R2m. Differences from the handoff's
rounded returns are −0.0000454769050845 pp and +0.0000412478445115 pp.
The author's frozen exact-count / <=0.01 pp return rules are unchanged and
satisfied. The independent plan's additional rounding checks (0.00005 pp
against the handoff; 0.0005 pp against the paper) are also satisfied. All signed
differences and source-file hashes are in [comparison.json](r0a_codex/comparison.json).

Definitions came from [arXiv 2609.12878v1, §§2.2–2.4, 5.2 and Table 16](https://arxiv.org/html/2609.12878v1).
One purchase per trade; buyer follows taker_bought. Exclude incomplete fields,
self-trades, invalid prices/quantities, known >2-outcome markets and buyers
with HHI >=0.5. Require known terminal payoff for returns. Favourites have
price >=0.90, including 1.0. Pool `100 × Σ(quantity × (winner − price)) /
Σ(quantity × price)` separately by buyer role. These are hypothetical
hold-to-resolution returns before fees/rewards, not realized wallet profits.

Taker favourites: 19,058,161 purchases; cost $2,662,127,096.893231; terminal gain
$23,358,954.622225016. Maker favourites: 39,618,777 purchases; cost
$6,999,835,447.114509; terminal gain $57,142,544.03603703.

## Mismatch preserved

| Cumulative stage | Independent / author | Paper Table 1 | Difference |
|---|---:|---:|---:|
| Complete distinct / valid price and quantity | 588,286,587 | 588,286,587 | 0 |
| Two-outcome filter | 588,286,587 | 588,258,033 | +28,554 |
| Buyer HHI filter | 586,151,609 | 586,123,163 | +28,446 |
| Return sample | 560,909,624 | 560,909,624 | 0 |

There are 28,554 valid trades with null market_id; no eligible buyer has unknown
HHI. The first-pass code retains and counts unknown market keys instead of
inventing an outcome count. The author uses token IDs for its exclusion but
records the same intermediate mismatch in checks.json. The first-pass numbers,
filters and unknowns were not changed after seeing that implementation.

The separate [post-comparison diagnostic](r0a_codex/null_market_diagnostic.json)
found **878 distinct token IDs, all absent from predictions.parquet**, across
these 28,554 rows. None has a known payoff. There are 108 high-HHI buyer rows;
28,446 remain after that restriction, all with unknown payoff. These counts
exactly account for the two numeric funnel differences, and contribute zero
rows to the return sample. Their outcome counts remain UNKNOWN: do not label
them multi-outcome or claim to know why the paper excluded them. The four
requested headlines stand; exact sample-construction equivalence remains
INCONCLUSIVE. No filter or headline was amended to eliminate the mismatch.

Diagnostic code was committed separately after comparison, before its output
(`580931b` code; `fb7f14d` raw). It checked all 1,218 footers and decoded 434
candidate files whose null statistics required inspection, verifying
18,321,274,720 compressed bytes. Cost: 498.506587 monotonic wall seconds;
peak RSS 2,118,189,056 bytes (1.97 GiB). This additional diagnostic scan and
the two discarded partial attempts exceeded the initial one-scan I/O estimate;
they stayed within the named inputs and memory bound.

## Independence, integrity and timing

Code and plan were committed before the full run. Complete first-pass output
was committed as `499d4d41ef7a1c9d315bf38f7aa2090d63a88e6b`, from code
`8b711f1da894a3bfed76dc73beca47d1abf811b3` (SHA-256
`8c14a6ffba0c7fa88f9453b16d316ba95edf01fd5df3e85f270f5ee769a83574`).
Only then were author reproduce.py and checks.json opened, at public-repo HEAD
`a1b3b2a282bfdbcece78f71c8c567fb9abc8e010`; both matched that commit.
No E-003 file was opened. Handoff/paper targets were already known: this is
implementation independence, not numerical blinding.

The complete run verified all 1,218 trade files, 23,354,367,274 compressed bytes,
and both auxiliary files against supplied local SHA-256 manifests. It decoded
the same immutable verified bytes, one file at a time, in batches <=262,144
rows. Every decoded count matched its footer; all projected trade types were
checked. No nonfinite price/quantity, null action/price/quantity/participant/
timestamp, or unknown buyer HHI was found. Input hashes, versions, per-file
records and exact times are in [first_pass.json](r0a_codex/first_pass.json).

Complete run: **00:58:57.406041–01:17:41.108125 UTC; 1,123.843448 seconds wall,
1,073.428772 seconds CPU; peak RSS 1,341,833,216 bytes (1.25 GiB)**. Timing includes
input verification, lookup loading and computation. Per-file timing is in
[timing.jsonl](r0a_codex/timing.jsonl); stdout/stderr in [run.log](r0a_codex/run.log).

Session timing qualification: clock-tool UTC readings were 00:42:28 at start
and 06:39:47 before final documentation. The diagnostic's calendar timestamp
is 02:28:18 despite 498.506587 seconds of measured process wall time after its
~01:21 launch. The cause of these elapsed/calendar discrepancies is UNKNOWN;
monotonic timings are retained verbatim. The session's calendar span exceeded
the requested approximately 100 minutes; no claim of meeting that limit is made.

Two earlier attempts stopped on metadata-stability guards and are retained as
INVALID-RUN. The second observed a 64 ns mtime decrease with unchanged size.
The filesystem/actor cause remains UNKNOWN. The corrected run records four
more mtime drifts while verifying the exact decoded bytes against manifests;
no content mismatch occurred. The root-cause review and regression are in
[INPUT_STABILITY_REVIEW.md](r0a_codex/INPUT_STABILITY_REVIEW.md). A later diagnostic
syntax error occurred before data reads and its stderr is preserved separately.

Remaining provenance limits: the remote HF commit `91ddb961` is asserted by the
handoff/manifests, not independently authenticated against Hugging Face here.
Dataset payoff flags and the historical resolution cutoff were not rechecked
on-chain. Observed timestamps run **2022-11-21 19:50:09–2026-03-29 23:59:58 UTC**;
the stated dataset/paper period starts November 11. This does not establish
whether earlier activity was absent or omitted. No missing coverage is inferred.

Offline checks: four pytest tests passed, covering hand arithmetic/roles/price
boundaries, a separate randomized scalar filter oracle, byte-integrity behavior
under mtime/content changes, and the diagnostic's known/unknown token accounting.
The broader application suite was not run or claimed; application code is unchanged.
Run the independent calculation with:

```sh
PYTHONDONTWRITEBYTECODE=1 'python' \
  polysignal/research/public_note/r0a_codex/recompute.py \
  --data '<users_v1.3>' \
  --output polysignal/research/public_note/r0a_codex/recomputed.json \
  --timing polysignal/research/public_note/r0a_codex/recomputed_timing.jsonl
```

Scope stayed local and free. No database, production/VPS/SSH, main edit,
spending, issue action or PR action. Next: Claude reviews this scoped headline
confirmation and the preserved funnel/coverage qualifications for the public note.

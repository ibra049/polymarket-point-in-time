Independent Job B recount, 2026-11-16 UTC. Python standard library only.

Run from the worktree root (after committing code):

```sh
python3 polysignal/research/public_note/h002_e002_codex/recount.py \
  --db '<author-orderbook-db>' \
  --package <this-repo>/negative_results \
  > polysignal/research/public_note/h002_e002_codex/first_pass.json
```

The database, frozen protocol and saved Gamma event file are pinned by full
SHA-256. The DB is opened with `mode=ro`, query-only and a read transaction,
then hashed again after closing. No network calls or author-code imports.
Decimal values are JSON strings to preserve exact sums and strict boundaries.

Code is committed first, raw output second, interpretation/comparison third.
Do not open `mirrored_book.py` or `E-002_compute*.py` until `first_pass.json`
is committed. The handoff, package README and pre-existing recheck summary
already disclose the expected numbers: this is implementation independence,
not blinded interpretation. Preserve any first-pass mismatch after comparison.

The frozen full-event source is absent (both event tables have zero rows).
Report strict local completeness as DATA-BLOCKED. Separately recount with the
saved November 11 Gamma payloads under the already documented D1; this cannot
restore the missing October 5 payloads. D2 excludes rows without a scheduled
slot. No change to the frozen numeric decision rules is authorized.

Scope review: the owner specifically requested independent verification for the
public note. This is a pipeline/evidence audit on existing explored data, not
a fresh strategy experiment. Frozen asks and fee formula, 60-second batch-time
synchrony, directional depth and sample minimums apply. Actual fills, historical
completeness and sub-second simultaneity remain unverified. No holdout is read.

Post-comparison code change (separate commit): make `uri=True` explicit on the
SQLite connection and expose the pre-size event-slot rows for audit. The first
run already used `query_only=ON` and its before/after DB hashes match; no database
writes occurred. First-pass metrics, thresholds and quantile definitions are
unchanged. `compare.py` explains the 105 pre-size / 104 post-size distinction,
checks exact pre-size membership against the author's selection logic, and
computes the author's floor-index quantiles as a labeled comparison only.

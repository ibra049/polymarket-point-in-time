# Repeated input-guard failure: review before a corrected run

Recorded 2026-11-16 ~00:58 UTC; before any complete first-pass result or author
code/checks exposure. Both failed attempts are INVALID-RUN, not a rejection.

Attempt 2 stopped after 997 completed files / 72,918,698 decoded rows, when
reading `trades/year=2025/month=08/day=21/data.parquet` (file 998).
Size stayed 10,117,144 bytes. mtime_ns changed from 1791247273783448521 to
1791247273783448457, a decrease of 64 ns. The log preserves these exact values.
The underlying actor/filesystem cause is UNKNOWN. This is not evidence that
the bytes changed. A subsequent read had stable metadata and SHA-256
70c3685bfd98ff1c754cede82f7dfdb7ab38108882f1bc867baa6adecc1587d4,
matching the local manifest. No complete headline numbers were generated.

Root cause at the implementation level: the integrity guard equated any mtime
change with changed content, while failing to measure the bytes themselves.
The code cannot establish why the timestamp changed. Do not weaken that
unknown into a claim of hydration, rounding, or harmless concurrent activity.

Stop the unchanged retries. The corrected run instead reads each compressed
file once into an immutable byte buffer, requires its exact length and SHA-256
to match `trades_manifest.tsv`, and decodes that same verified buffer. It also
verifies both auxiliary files against `SHA256SUMS` before using them. These
are provenance metadata within the authorized input directory; no additional
outcome dataset is read. The file set must match all manifest paths exactly.
mtime drift is still recorded, but content mismatch stops the run. The remote
91ddb961 pin remains unauthenticated independently of the supplied manifests.

Regression test: change a synthetic file's mtime by 64 ns without changing
bytes (old guard rejects; new content check accepts); mutate its contents
(new check rejects); confirm the previously loaded immutable buffer is intact.
The largest trade file is 282,793,591 compressed bytes. Inputs above 1 GiB
are refused; retain the overall 8 GiB high-water limit. This stays one file at
a time and reads ~23.35 GB for the corrected complete trade scan, plus 0.93 GB
of auxiliary data. The discarded attempts add partial read work and time.

No price boundary, filter, role, return definition, comparison tolerance or
paper sample rule changes. This replaces the metadata guard in FIRST_PASS_PLAN
with measured byte identity; all scientific definitions remain fixed.
Code and this review are committed before the corrected complete run. Preserve
both failures' logs/timings in the raw-output commit. If content verification
fails, commit the exact blocker; do not repair source data or tune the sample.

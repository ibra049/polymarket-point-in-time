# First attempt stopped before a headline result

At ~2026-11-16 00:47 UTC the first attempt exited 1 on file 57,
`trades/year=2023/month=01/day=23/data.parquet`, after the input size/mtime
stability guard fired. Only 56 files had completed. No complete raw result
exists; the failed attempt is INVALID-RUN.

Cause: UNKNOWN. The initial error did not record both stat values, so it
cannot distinguish size from mtime drift. Do not claim filesystem hydration
or content mutation as established. A subsequent read-only diagnostic found
stable size 15,519 and mtime_ns 1791247071177320718 across footer and decoded
reads. Its SHA-256 was 277509410bd04d22cbf5bc02e3b0cc4294068cb85a611d0c42dceaf333a42c67,
matching the local trade manifest. Neighboring January 24 and 25 files were
also stable during diagnostic reads. This does not establish why the earlier
guard fired or independently authenticate the remote dataset pin.

Before the one permitted retry, the code adds both stat values to any future
failure message. No calculation, filter, stability guard or tolerance changes.
Preserve `attempt1_failed.log` and `attempt1_timing.jsonl` with the raw-output
commit. If the guard fires again, stop retries and record the root-cause gap.
Author code and checks.json remain unopened.

# PN-2 source-check diagnostic — 2026-11-16

Status: DATA-BLOCKED for the first chain attempt only. Counts in first_pass.json are unchanged.

The committed Tatum plan (37aefb0) completed 0/25 random and 0/14 supplemental rows. Raw RPC responses and per-row errors are preserved in polygon_rpc.jsonl and polygon_spotcheck.json. The first two full-range log responses reject queries over **100 blocks** (code -16412). Later responses report HTTP-style statusCode 429 in its JSON response with an explicit public limit of **5 requests/minute**. Two workers without pacing also exceeded that free quota. Pacing alone would not fix the historical range restriction. The first attempt's frozen no-substitution rule was respected; no successful check is inferred from a rate-limit response. Dispatch continued to other selected rows after errors; the replacement harness must stop further network calls when any request fails.

Before a second source attempt: add an offline regression for the circuit breaker (including errors embedded in JSON with curl exit 0), serialize/rate-space requests, and commit a source plan for the allowed free Pocket endpoint. Keep exactly the original random IDs and historical block cutoff. Preserve the first attempt; write new evidence under pocket/. No paid upgrade, key or new sample.

Separately, source_audit.json preserves a failed bootstrap diagnostic that sorted event IDs numerically. Inspection of the allowed parquet schema shows `event_id: large_string`; measure.py sorts these native strings. Correct only the post-comparison diagnostic to string ordering and write a new output; retain the numeric diagnostic and the independent first-pass bootstrap unchanged. This is a verifier assumption error, not evidence of a builder count mismatch.

## Pocket attempt and bounded next source

The separately committed Pocket source plan (e2fd653) kept the same IDs/cutoff and used paced requests with a tested circuit breaker. Its first full-range query failed with JSON-RPC -32602: `block range exceeds maximum 50000`. The circuit then prevented every further log request. Completed checks: 0/25 random, 0/14 supplemental; all remain unknown. This is a different source capability limit, not an observed data mismatch.

The third source plan will use the handoff's already-allowed Tenderly public endpoint. It was the builder's provider, so success there will be an independent decoding/metadata comparison, **not independent-provider corroboration**. Retain both failed attempts and the circuit-breaker regressions. No metric, cutoff, sampled ID or original output changes. If Tenderly also refuses, report the exact blocker instead of claiming the spot check succeeded.

## Tenderly timeout and bounded Pocket adaptation

Tenderly completed 8/25 random rows without mismatches, then a 40-second timeout (curl exit 28) tripped the circuit; 17 random and all 14 supplemental rows remain unknown in that attempt. Its completed and failed requests are preserved. The original 40-second request cap was a verifier implementation choice, not a frozen PN-2 measure.

To finish within the owner's time budget without long full-history calls, use the same Pocket source with **exact-block creation lookups** at the CSV's claimed blocks, followed by a **batched clarification scan** for all 39 questionIDs in contiguous ranges no wider than the observed 50,000-block cap. Range 58,008,243…97,166,757 requires 784 chunks. This verifies the claimed creation evidence rather than globally proving no earlier duplicate initialization. The clarification scan still covers the complete creation-to-original-cutoff interval for every selected market, and filters creating adapters during decoding. Offline cap/contiguity boundary tests precede the new attempt. Source, IDs, query scope and cutoff are recorded before fetching; no metric or sample is revised.

## Pocket bounded backend discrepancy and mixed-source completion plan

All 39 exact-block creation log/header pairs were successfully retrieved from independent Pocket. The first 50,000-block ADU request then failed with `max 10001 blocks`, despite the earlier Pocket backend reporting a 50,000 maximum. This is a backend capability discrepancy. No ADU scan completed in that attempt. Its 82 raw request records are committed; no creation response is discarded or replaced.

The next plan reuses those exact cached Pocket creation responses, bound by SHA-256, and scans the 39 questionIDs' ADU logs through the original cutoff in **40 contiguous Tenderly ranges of at most 1,000,000 blocks**. This is far smaller than the successful Tenderly full-range queries and avoids thousands of Pocket calls. Creation text/time and M1/M2 will be independently sourced from Pocket. M3 counts will be independently decoded from chunked Tenderly logs, with the original-provider limitation explicit. Exact-block creation lookup does not prove global uniqueness. No original CSV or metric changes; new source/query plan precedes all new fetches.

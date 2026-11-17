# Independent checks

Each result in this repository was built by one implementer and checked by another, using
separate code. This folder holds those checks, run on 2026-11-16. The checker was a second
AI coding assistant (Codex), working from each study's frozen protocol on the same public
inputs. The rules were the same for every check:
- write new code without opening the builder's scripts;
- commit the first-pass numbers before any comparison;
- keep every later change, and every mismatch, as its own commit.

| Check | What was recomputed | Result | Record |
|---|---|---|---|
| Replication (§3) | Observed trades, return-sample purchases, pooled taker and maker favorite returns, from the paper's definitions only, over all 1,218 trade files | All four match: counts exactly, returns to within 10⁻¹⁵ of ours. The two intermediate funnel gaps (+28,554, +28,446) are exactly the rows without a market id, none of which has a known payoff. Status PROMOTE for the four checks; funnel equivalence INCONCLUSIVE | `replication/` |
| Edit rate (§4.2) | M1–M3 counts, Wilson and event-cluster CIs; the 2,000-draw sample from the seed; 25 random and 14 flagged markets re-read on Polygon | All counts and CIs match; draw order identical; 0 mismatches on chain. Status INCONCLUSIVE (a descriptive measurement with no pass/fail rule). The late code-plus-output commit stays a disclosed gap | `edit_rate/` |
| Null results (§5) | Mirrored-book pairs and minimum ask sum; basket funnel, fees and decision, from the read-only order-book extract | All match (6,432 pairs; $1.001; 105 complete slots, 104 size-feasible; 0 above 0.5¢; −0.48¢ net). REJECT, scoped to the tested cadence | `negative_results/` |
| Publication review | Whole tree, gzip payloads, PDF text and git history scanned for secrets, personal data, infrastructure identifiers and overstated claims; three offline reruns | Requested changes applied or answered (see `scrub/README.md`). Fee screen rerun: 24 rows byte-identical. Options rerun: same INVALID-RUN status and counts; 7 floating-point diagnostics differ by up to 1.5e-13 | `scrub/` |

Earlier independent checks (deadline-edit counts, the two date-field tests, the fee screen
and the null-market count) are summarised in `../note/NUMBERS.md`.

**About these files.**
- They are copies of the checker's working records.
- Local file paths are replaced by placeholders such as `<users_v1.3>` and
  `<checker-worktree>`. Nothing else is changed.
- `MANIFEST.json` lists each file with the sha256 of its unmodified original. Hashes quoted
  inside the files refer to those originals.
- Commit hashes refer to the author's private working repository.
- Words like "owner" (the author) and "handoff" (the task file) come from that working
  process.
- Some raw logs record failed attempts on purpose: two scans stopped by a file-timestamp
  guard, and RPC providers that refused large queries. They are kept, not hidden.

**Not independently re-done here:**
- The remote dataset pin was trusted through the local hash manifests.
- The eight other replication checks rest on the author's code plus a byte-identical rerun.

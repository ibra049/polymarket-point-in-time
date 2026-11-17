# Job C independent first-pass plan — 2026-11-16

Scope: the owner's handoff, Job C only. No author implementation or checks.json
has been opened. Handoff headline numbers and paper tables are already known;
this is implementation independence, not numerical blinding.

Review basis: `.claude/skills/review-experiment/SKILL.md`, read before computation.
This is the explicitly authorized pipeline check, not a fresh strategy test or
an alpha claim. Expected outcome: reproduce counts exactly and the rounded
gross return numbers. A successful check supports use of these historical
pipeline numbers; execution, fees, capacity and prospective validation remain
outside this task. No existing frozen rule or holdout is amended.

Definitions were read from https://arxiv.org/html/2609.12878 (v1), sections
2.2–2.4 and 5.2, Tables 1 and 9. Purchases are one per trade, buyer determined
by taker_bought; exclude incomplete identities/direction/price/quantity,
self-trades, nonpositive quantity, price outside (0,1], >2-outcome markets,
and buyer HHI >=0.5; retain nonnull final trade winner for returns.
Favourites have price >=0.90 (including 1.0). Pool terminal gain divided by
purchase cost by buyer role, expressed as percent, without fees or rewards.
Binary BOOLEAN winner is read as the released dataset's final payoff flag;
on-chain outcome correctness and the historical cutoff are not reauthenticated.

Numeric arithmetic uses float64. Nonfinite price/quantity is invalid and
counted. Unknown market/HHI keys are retained under the literal exclusion
rules, counted explicitly, and would make the check INCONCLUSIVE rather than
treated as known binary/low-HHI evidence. All auxiliary keys/types are checked.

Comparison fixed before full scan: row counts must equal the handoff integers;
absolute error <=0.00005 percentage points versus its four-decimal returns,
and <=0.0005 percentage points versus the paper's three-decimal returns.
Report the signed difference in all cases. These are decimal reporting
precision checks, not new scientific promotion thresholds. Do not change a
definition to make a comparison pass. A mismatch remains a mismatch.

Memory: one file at a time, at most 262,144 rows per batch; 8 GiB process
high-water limit. Per-file decoded counts must equal footer counts. Record
file size/mtime stability, schema versions, auxiliary content hashes, script
hash and commit, per-file timing, total wall/CPU and peak RSS.
The 91ddb961 dataset pin comes from the handoff; a fresh full LFS content
verification is outside the ~24 GB scan budget and remains unverified.

Commit sequence: (1) this plan, independent script and offline synthetic
pytest checks; (2) complete first-pass raw JSON and timing, before opening
author code/checks; (3) comparison/write-up and own status/resume updates.
Any post-comparison code change requires a separate explanatory commit.
Push only the current non-main branch. No SSH/VPS, production, databases,
spending, issue actions or PR actions.

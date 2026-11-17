# Public-repository scrub — Codex, 2026-11-17

**Status: INCONCLUSIVE. Concrete changes are required before publishing
`1729562d665c0085bdc3adff5e8dec3d84b1ac75` unchanged.** The complete tracked
tree/history scan finished, but prominent claims conflict with the release's
own disclosures, private implementation references exceed the handoff's
disclosure boundary, one rerun is DATA-BLOCKED, and the options rerun has
preserved numeric mismatches. This is a publication review, not a decision
about a trading hypothesis.

Question/scope: owner priority 5, under
`research/handoffs/2026-11-17_claude_public_scrub_local.md`. Inputs were the
named public repository's tracked files and all reachable history, plus the
required sprint instructions. No external datasets, databases, holdouts,
network services, production systems or paid resources were used for analysis.
The final requested Git push is the sole network operation; it publishes this
report to this sprint branch in the existing repository, not the reviewed repository.

## Verified inventory and privacy checks

- Required HEAD matched; the source repository was clean before and after.
  A final SHA-256 check found **0 changed files out of 254**.
- **254 tracked files, 59,488,313 bytes**. Every worktree file matched its
  committed Git blob as well as its recorded SHA-256. Manifest:
  [public_scrub_codex/raw/manifest.json](public_scrub_codex/raw/manifest.json).
- Decoded/scanned **182 text files, 71 gzip payloads and 1 PDF**. Gzip
  contents, JSON and logs were included. PDF text came from `pdftotext`;
  metadata had no flagged values and the PDF contained **0 embedded files**.
- **0 LFS pointers, 0 LFS attributes, 0 submodules**; all eight historical
  trees also had no submodules. No tracked file was skipped or failed decoding.
- Scanned **8 commits across all local refs**, including `git log --all -p
  --format=fuller` and author/committer metadata, plus **30 older unique
  blobs** (27 text, 3 PDF) independently of the textual patch stream.
- No literal credential, personal email, personal home path, machine name,
  server address or private host was identified. This is a bounded pattern
  scan and manual review, not proof that arbitrary encoded secrets are absent.
  All 16 author/committer email occurrences use the permitted GitHub noreply
  address; the single identity matches the public byline.
- Manual triage rejected 22 apparent IP locations as Python slices, two
  apparent home paths as a public tournament website's URL path, and one
  apparent email as a GitHub Actions expression. The workflow references a
  runtime token; it does not contain a literal token. Generic statements that
  no VPS was used, public service URLs, the public repository's name and its
  collector user-agent were not treated as private infrastructure disclosures.

The pattern definitions, redacted file/line candidates, patch digest, refs and
decode coverage are in [scan.json](public_scrub_codex/raw/scan.json).
[supplemental_checks.json](public_scrub_codex/raw/supplemental_checks.json)
records manual triage and PDF/metadata checks. Candidate matches are locations,
not findings; matched sensitive values are not copied into this report.

## Concrete changes to the current tree

Locations below are relative to the reviewed public repository at the pinned
commit. Apply corrections to the Markdown, LaTeX and rebuilt PDF together.

| Location | Issue and required change |
|---|---|
| `README.md:31`; `note/note.md:70`; `note/note.tex:81`; `PREREGISTRATION.md:3` | Blanket claims that every rule preceded viewing its data are contradicted by `PREREGISTRATION.md:19` and `deadline_edits/PN-1_prereg.md:14`: PN-1's classification followed exposure to changed rows. The mirrored-book probe also lacked a predeclared numeric threshold. State these exceptions beside the headline process claim; preserve the original disclosures. |
| `note/note.md:106`; `note/note.tex:115` | The statement that the second replication implementation lacked access to check values implies numerical blinding. `independent_checks/replication/R0a_R2_independent_codex.md:78` and its `r0a_codex/FIRST_PASS_PLAN.md:3` explicitly say handoff/paper targets were known. Say author code and the author's check file remained unopened until first-pass commitment, while headline targets were already known. The four matching headlines remain valid within that scope. |
| `note/note.md:263`; `note/note.tex:262`; `negative_results/README.md:104` | Unqualified complete/qualifying basket counts omit a material source limitation. Report **105 pre-size slots, 104 size-feasible**, with completeness relative to later refetched event lists. The frozen local completeness source is DATA-BLOCKED; original historical event lists are unavailable. Add that batch timestamps do not establish simultaneity: **16/105** exchange timestamp spans exceed 60 seconds, maximum **929.946 seconds**. Evidence: the shipped `independent_checks/negative_results/H002_E002_recount_codex.md`, sections on the funnel and gaps. No threshold or result should be retuned. |
| `options_benchmark/README.md:75` | Its claim that preserved diagnostics reproduce exactly is not true in this environment. Status, failure share and counts match, but **7 scalar diagnostics differ**. Document the exact mismatch and Python version; retain both outputs. Do not introduce a tolerance retrospectively or call this an exact reproduction. |
| `note/note.md:271`; `note/note.tex:270`; `README.md:20`; `negative_results/fee_screen/README.md:1` | Fee language says “current” while the screen uses rates fixed as of 2026-10-05. Date the assumed fee schedule. This offline scrub does not authenticate the November 17 schedule. The script arithmetic reproduces; current venue economics remain unverified here. |
| `note/note.md:59`; `note/note.tex:65` | The unconditional literature-wide assertion that no study tests date-field/outcome dependence is not established by the shipped references. Make it an explicitly bounded literature-search statement with an as-of date and search scope, or remove it. No external search was authorized in this scrub. |
| `deadline_edits/PN-1_prereg.md:9`; `README.md:84`; `negative_results/fee_screen/E-001.yaml:37`; `negative_results/negrisk_basket/E-002_frozen_protocol.yaml:23`; `negative_results/negrisk_basket/E-002_compute_frozen.py:3`; `negative_results/negrisk_basket/E-002_compute_frozen.py:40`; `independent_checks/negative_results/h002_e002_codex/E-002_frozen_protocol.yaml:23` | These expose a private data-directory identifier and/or private database filename/schema details beyond the handoff's permitted repository-name disclosure. Replace those private identifiers in explicitly labelled public derivatives. Preserve source hashes and disclose each sanitization; never silently edit a frozen original or continue describing a changed file as byte-identical. |
| `independent_checks/edit_rate/PN-2_interpretation_codex.md:7`; `options_benchmark/E-006_result.md:5`; `options_benchmark/E-006_result.md:7`; `options_benchmark/R-039_diagnosis_review.md:8`; `options_benchmark/E-006.yaml:5`; `options_benchmark/E-006.yaml:50`; `options_benchmark/E-006.yaml:288`; `options_benchmark/E-006_manifest.json:2`; `options_benchmark/code/e006.py:53`; `options_benchmark/code/e006_snapshot.py:7`; `options_benchmark/code/e006-collect.yml:4`; `options_benchmark/results/context.json:7`; `options_benchmark/results/run_manifest.json:2` | Internal handoff/review/results locations, module locations, worktree identity and data-branch layout remain in the package. Under the handoff's strict private-internals boundary, sanitize them or obtain a separately documented disclosure exception before release. Resolve links to public equivalents where available. The source spellings also occur in manifest hash-map keys and `results/output.json`; inspect those copies together. Public derivatives need new hashes and a transparent mapping to the unchanged original hashes. This report does not authorize changing the frozen analysis. |

The prominent documents contain historical gross-return numbers and a fee
screen survivor, but explicitly disavow a trading claim. No additional positive
profit/alpha claim was identified. Market descriptions mentioning profits are
source text, not project claims. E-006 correctly retains INVALID-RUN and does
not interpret its statistic after the failed pipeline gate. The mismatches
below do not change that status.

## Findings that exist only in history

No additional history-only literal credential, personal email, home path,
machine identifier or server address was identified. Author and committer
metadata use the same permitted identity throughout.

There **are history-only private provenance references** in
`b36e132:note/NUMBERS.md:15` and `b36e132:note/NUMBERS.md:42` (also present in
`549efe4`, `a1b3b2a` and `b18716c`). The old ledger names internal result
records and runner-ledger provenance, alongside earlier verification labels
and pending reviewer work. The rewritten current ledger does not remove
these versions from the proposed full-history release. Under the strict
private-internals rule, include them in the sanitization/disclosure decision.
No matched private value is quoted here.

Earlier README/note/PDF versions also retain older wording and verification
levels. They are historical records, not new independent verification. Current
claim corrections must not imply that the old full-history contents vanished.
The database/schema references listed above entered the initial commit and
persist in history; a tip-only privacy cleanup cannot remove them. **No history
rewrite, source edit, publication or visibility change was performed.**

## Three offline rerun attempts and diffs

All execution used a tracked-file copy inside this sprint worktree, with bytecode
writes disabled. The original public repository was never the execution cwd.
No network-capable collector/fetch command was invoked.

| Command from the folder README | Result |
|---|---|
| `deadline_edits/`: `python audit.py DATA/` | **DATA-BLOCKED.** Exit 1 on missing `pyarrow`, before data access. The required `markets.parquet` and `events.parquet` are absent from the named public tree, and no external dataset location is named/authorized by this handoff. No dataset was searched, downloaded, synthesized or substituted. A full output diff is unavailable. |
| `negative_results/fee_screen/`: `python E-001_compute.py` | **PROMOTE — arithmetic rerun only.** Exit 0; all **24 rows byte-identical**, empty stderr and empty diff. Both SHA-256 values are `f67597b13d201125d8a5cd5711b7c94e3bd126a0dba401f76f9334ee656d1f9c`. No external table values, assumed spread inputs or current fees were authenticated. |
| `options_benchmark/`: documented offline `analyze(..., synthetic=True)` with the zero data-commit placeholder | **INVALID-RUN reproduced as the frozen study status.** **65 files**, **61 in sample**, **4 duplicate hours**, **12/61 failures = 0.19672131147540983**, **11,754 marks checked / 3 bad**, **260 scheduled hours**. Status and all those counts match exactly. Exact diagnostic equivalence is **INCONCLUSIVE**, with mismatches preserved below. |

Four pinned protocol/code/workflow file hashes match, and **65/65** shipped
snapshot SHA-256 values match the original run ledger. The synthetic path does
not authenticate the private git data binding. Its four binding/provenance
field differences are expected and remain in the raw diff.

The first-pass recursive diff flagged 15 paths: four expected manifest fields,
four CI fields compared as in-memory tuples versus persisted JSON lists, and
**seven actual scalar differences**. Comparison of the saved JSON confirms
the four CI values are identical; first-pass flags remain untouched.
Actual scalar differences are:

| JSON location | Rerun minus recorded |
|---|---:|
| `/pipeline/synthetic_flat_error` | +1.45439216e-13 |
| `/return_per_dollar/min` | +9.791e-15 |
| `/return_per_dollar/p25` | +4.7835e-15 |
| `/return_per_dollar/median` | −5.6901e-16 |
| `/return_per_dollar/p75` | −2.2933e-15 |
| `/return_per_dollar/p95` | +2.6928e-14 |
| `/return_per_dollar/max` | +2.394e-15 |

Deltas are exact decimal differences between the stored JSON renderings.
This run used **Python 3.15.1 on the owner's Mac**. The cause of the numeric
differences is **unknown**; platform/math-library differences are a possibility,
not an established explanation. No environment switch, numerical tolerance,
rule amendment or rerun was used to remove them. Their small size does not
authorize interpreting any statistic from the invalid study.

Raw commands, exit codes, timings and comparison paths:
[reruns.json](public_scrub_codex/raw/reruns.json). Original first-pass rerun
output: [options_output.json](public_scrub_codex/raw/options_output.json).
Post-commit inspection of those unchanged bytes:
[options_difference_details.json](public_scrub_codex/raw/options_difference_details.json).
Missing-dependency stderr has only the sprint path prefix redacted, with its
original digest retained in [run_context.json](public_scrub_codex/raw/run_context.json).

## Execution integrity, gaps and stopping point

Code preceded output: **`0ab9ffc` code → `179855a` first-pass raw → `324d33f`
post-comparison details → `5588107` source/hash checks → this write-up**.
No maintained analysis/scanner code changed after comparison. Five focused
stdlib unit tests passed. The required pytest invocation was attempted and
failed because pytest is not installed; no installation/network workaround was
attempted. No application code changed, and the application suite is not claimed.

Two procedural failures are disclosed in `run_context.json`: an initial rerun
invocation preceded completion of the copy and failed before analysis; a
preliminary filesystem-walk text helper emitted the README location and stopped
on a UTF-8 decode error. That helper was not restricted to the tracked inventory,
so it was discarded as evidence; no undecodable content was emitted. The final
scan and all findings use the pinned tracked Git inventory. No database was
opened. Source cleanliness/content hashes were rechecked after all reruns.

Stopping condition reached: the authorized tree/history checks and all three
bounded rerun attempts are recorded, with the missing PN-1 prerequisites and
exact options mismatches preserved. Reopening requires the publication author
to address the concrete list and identify a newly pinned tree; a complete PN-1
rerun additionally needs an explicitly named, permitted non-outcome metadata
source and an available dependency environment. No public-repository edits,
release, SSH/VPS work, production changes, spending, main edits, or issue/PR
actions are part of this delivery.

**HANDOFF → Claude | `research/public_note/PUBLIC_SCRUB_codex.md` |
`codex/sprint-1117-scrub` | ask: apply the concrete publication corrections and
disclose/sanitize historical private references; return a new pinned tree for
review. Preserve the rerun blocker and numeric mismatch.**

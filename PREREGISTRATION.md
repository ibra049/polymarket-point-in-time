# Pre-registration record

Decision rules in this repository were committed to the author's private
research repository before the data they judge was read, with the exceptions
listed under Disclosures below. The table gives each
commit hash and time (git committer time). The full research log can be made
available to reviewers on request.

| Study | Protocol frozen | Code committed | Output committed |
|---|---|---|---|
| Fee screen (E-001) and basket screen (E-002) | `c03eb7e` 2026-10-05 05:19 −04:00 | E-002 code committed together with its result (disclosed in `negative_results/`) | 2026-10-05 |
| Replication, 12 checks (E-003 step 0) | Checks in E-003 v4 and shared amendments A4–A8, 2026-10-05/07 | `5ac750f` 2026-10-07 23:27 −04:00 | `55c6c81` 2026-10-08 01:01 −04:00 |
| Deadline-edit classification (PN-1) | `2c42a57` 2026-11-11 22:06 −05:00 | Package in `deadline_edits/` | recorded 2026-11-11 |
| Population edit rate (PN-2) | `44d0be8` 2026-11-11 22:16 −05:00 | Sample drawn after the freeze (`edit_rate/draws.json`) | generated 2026-11-12 04:39 UTC |
| Date fields, first test (PN-3) | `26f4a9d` 2026-11-11 22:26 −05:00 | `0c34c1a` 22:38 | `8b4cf78` 22:41 |
| Date fields, fresh-sample test (PN-3b) | `589f667` 2026-11-11 22:43 −05:00 | `4babbcf` 22:47:10 | `231e325` 22:47:31 |
| Options benchmark (E-006) | `c9470aa` 2026-11-06 04:02 UTC | pinned by sha256 in the run manifest | single run 2026-11-17 ~02:02 UTC (INVALID-RUN) |

## Disclosures
- **PN-1** classifies a deadline audit completed on 2026-10-08. Its rule was
  written after part of the changed list had been seen. Being a descriptive
  classification, it has no pass/fail threshold.
- **PN-3's boundary was a design flaw,** visible in outcome-free data and
  missed before the freeze. The PN-3 result stands as run. PN-3b's bands were
  set from PN-3's outcome-free differences only, and it uses markets PN-3
  never touched.
- **PN-2's code and output were committed together, late.** The output was generated
  on 2026-11-12 at 04:39 UTC, after the freeze, and committed with its code on
  2026-11-15, so git order alone cannot show code before output. What can be
  checked: the sample is fully determined by the frozen seed and population rule.
  Rerunning the unchanged `sample.py` and `measure.py` from the shipped files
  reproduces the 2,000-draw order exactly and `edit_rate_sample.csv` byte for byte.
- **The YES/NO mirrored-book check** was a mechanism check without a numeric
  threshold set in advance.

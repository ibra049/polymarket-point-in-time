# Pre-publication review (2026-11-17)

`PUBLIC_SCRUB_codex.md` is the second implementer's review of this repository before
publication, run on commit `1729562`. It covered the whole tracked tree, every gzip payload,
the PDF text and the full git history. It looked for secrets, personal data, infrastructure
identifiers, profit claims and overstated claims, and it re-ran three analyses offline.

How its requested changes were handled:
- **Applied:**
  - the pre-registration claims now carry their disclosed exceptions;
  - the replication's second implementation is described as independent but not blinded;
  - the basket result states its completeness and timestamp limits;
  - the fee schedule is dated 2026-10-05;
  - the literature claim is bounded to a dated search;
  - the options rerun states its floating-point differences.
- **History:** the public repository is published as a single commit. Earlier drafts, which
  carried internal labels, are not part of the public history.
- **Kept, with an explanation:** some frozen files name the author's private repository,
  local database or repository-relative paths. They are kept byte-identical because their
  sha256 values are pinned and checked (see the top-level README, *Setup*). None of them is a
  host, an address or a credential.

`options_rerun/` holds the reviewer's offline rerun output (`options_output.json`), the
recorded output (`recorded_output.json`) and the field-by-field differences. Links in the
report to `public_scrub_codex/raw/...` refer to the reviewer's working copy. Only these
files are shipped here.

# Post-comparison diagnostic, 2026-11-16

First-pass code: 8b711f1; complete raw result committed as 499d4d4. Only after
that commit were `<this-repo>/reproduction/reproduce.py`
and `checks.json` opened (public-repo HEAD a1b3b2a282bfdbcece78f71c8c567fb9abc8e010).
No E-003 file was opened.

The four requested headlines match the recorded results: counts exactly,
return differences approximately 5.55e-16 and 3.33e-16 percentage points versus
the author's full-precision values. The stricter independent decimal-precision
comparisons and the author's unchanged frozen <=0.01 pp checks both pass.

The independent first pass also repeats the author's disclosed intermediate
funnel mismatch versus paper Table 1: two-outcome +28,554; after HHI +28,446.
First-pass diagnostics locate 28,554 null trade market IDs. This is not tuned
away. The new script only diagnoses those rows using the authorized prediction
lookup, buyer HHI and known-payoff flags. Read all file footers; decode only
files whose footer cannot establish zero null market IDs; verify their bytes
against the same local manifest. Preserve unmatched keys as unknown.

The original recompute.py, thresholds, selection and raw result stay unchanged.
The diagnostic is committed before generating its separate JSON. It does not
test additional hypotheses, produce strategy slices or expand outcome access.

The initial diagnostic launch failed at Python parsing (an unmatched closing
parenthesis), before any input read. Preserve its stderr. Correct the syntax
in a separate code commit and add an imported synthetic diagnostic check
before running it again; no scientific rule changes.

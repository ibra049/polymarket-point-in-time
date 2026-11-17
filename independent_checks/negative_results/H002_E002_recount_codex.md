# H-002 / E-002 independent recount — Codex

2026-11-16 UTC · Job B · branch `codex/local-h002-1116`

**Verified:** H-002's 6,432 pairs and minimum YES+NO ask sum of $1.001;
E-002's 105 complete, synchronous-by-batch-time, fee-known event-slots across
24 events, zero net opportunities above 0.5¢, and the +1.8¢ gross / −0.48478¢
net Bank of Russia cases. **Decision: REJECT**, scoped to this D1 quote screen
at its recorded cadence. Strict completeness from the frozen local source is
**DATA-BLOCKED**. The historical completeness and actual simultaneity gaps remain.

There is a denominator mismatch worth preserving: the recorded 105 is **before
size**, whereas the independent first pass called **104 after size** qualifying.
Both clear the frozen 20-slot / 5-event minima. No threshold or first-pass number
was changed after comparison.

## Inputs, independence and chronology

The owner authorized a bounded local recount, not a new strategy experiment.
This audit checks existing public-note evidence under the frozen rules, using
existing explored data. No fresh outcomes or holdout were read. No SSH, VPS,
production, spending, issue or PR actions occurred.

- Database: `<author-orderbook-db>`.
  Full SHA-256: `1fb018c6c3e0dc74d740d142120f26193c9b452825e89bb4524b566763425885`.
  Before/after hashes match in both runs. Its 70,458 snapshots are all
  non-authoritative and span August 20 11:36:15–August 21 12:18:28 UTC, 2026.
- Frozen E-002 protocol, copied without edits into the audit directory:
  SHA-256 `b63c91fdd582eb58ed399a6fddb97f87dd05b3a76531b9d10c6ac22d783186a9`.
- Saved supplemental Gamma event payloads:
  `<this-repo>/negative_results/data/gamma_events.json.gz`;
  SHA-256 `01bd94154c5514e00ff22e7e7c7035e2fbbc511fb4d1f9c10ecf9ee1e76336b7`.
  These were refetched November 11, not preserved October 5 payloads. They are
  used only for the separately labeled, already documented D1 recount.
- Own script: [recount.py](h002_e002_codex/recount.py). Standard library only;
  exact Decimal economics and raw decimal ladder comparisons. No author import
  or author-script execution. Final connections explicitly use `uri=True`,
  `mode=ro`, `query_only=ON` and a read transaction.

Code was committed as `8020a2c`, then [first_pass.json](h002_e002_codex/first_pass.json)
as `73c8873`, **before opening any `mirrored_book.py` or `E-002_compute*.py`**.
The handoff's expected numbers, package README and existing recheck summary had
already been read: this is independent implementation, not a blinded test.

After opening the author files, commit `29b59da` exposed pre-size rows for audit
and made SQLite's URI flag explicit. The initial interpreter reports SQLite
`USE_URI`; its connection already enabled query-only before reads, issued no
write statements, and left DB bytes unchanged. The explicit flag removes any
reliance on interpreter defaults. The follow-up did not change selection,
economics, first-pass metrics or quantiles. Raw follow-up evidence was committed
separately as `cf73531`. [validation.json](h002_e002_codex/validation.json) confirms
the first-pass bytes and all its metrics remain unchanged.

## H-002: matching arithmetic, scoped mechanism observation

H-002's binary probe had no frozen numeric preregistration. It can be checked as
a mechanism observation, not relabeled as a preregistered threshold test.

| Quantity | Independent recount | Comparison |
|---|---:|---|
| Paired fetch-ok tier-A snapshots | 6,432 | Match |
| Markets / events / scheduled batches | 1,766 / 624 / 4 | Match |
| NO ask equals 1 − YES bid | 6,432 / 6,432 | Match, exact decimal top fields |
| YES ask + NO ask below $1 | 0 | Match |
| Minimum / mean ask sum | $1.001 / $1.0367908893… | Match at reported precision |
| Full mirrored ladders | 6,385 / 6,432 | Match |
| YES / NO ladder levels | 286,053 / 286,048 | Match |
| Ladder mismatches | 47 | Match; none has stored ask sum below $1 |

The timestamp-difference histogram also matches exactly: 28 of the 47 differ by
±1 ms, seven have equal millisecond timestamps, and the remainder range from
−3 to +17 ms. Book changes between requests are a plausible explanation; the
cause of each mismatch is **unknown**, including the seven equal-timestamp pairs.
No conclusion about fills or universal absence of sub-second opportunities follows.

## E-002: funnel and frozen decision

The frozen formulas are `1 − Σask − Σfee(ask)` for long and
`Σbid − 1 − Σfee(1−bid)` for short, with `fee(p)=rate×p×(1−p)`.
The latest fee observation at/before each leg capture takes priority; raw
metadata is the prescribed fallback. Unknown fees are excluded, never set to
zero. A direction requires every touch size to meet `max(orderMinSize, 5)`.
The opportunity rule is **strictly greater than $0.005 net**, with no threshold
adjustment. Conversion and gas remain ignored as frozen.

| Funnel stage | Count |
|---|---:|
| NegRisk markets / linked events | 1,364 / 373 |
| Usable NegRisk rows without scheduled slot, excluded under D2 | 1,056 |
| Candidate event-slots | 1,527 |
| Excluded before complete baskets | 1,422 |
| Complete / synchronous by captured_at / fee-known | 105 / 105 / 105 |
| Long touch-size passes / short touch-size passes | 90 / 104 |
| Either direction size-feasible | **104** |
| Distinct events / scheduled slots / median legs | 24 / 5 / 5 |
| Opportunities above 0.5¢ net / persistent episodes | **0 / 0** |

The first pass split the 1,422 exclusions into 1,034 missing-leg and 388
non-exhaustive placeholder cases. The author's ordering classifies all 1,422
as incomplete. A post-comparison membership check confirms **the same exact
105 event-slot keys**, not merely the same count. The independent placeholder
classifier therefore changes no admitted row on this pinned input.

The slot failing both size gates is event `101977`, “How many Republican House
members not running in 2026?”, August 20 12:00 UTC. Market `909060`, snapshot
`13255`, has ask size **1.0**; market `909056`, snapshot `12467`, has bid size
**3.3**. Both minima are 5 shares. Its net edges are negative regardless. The
recorded code increments its qualifying counter before testing size, then uses
size to gate opportunities. Accordingly, **105 pre-size** reproduces its funnel;
**104 post-size** is the preserved independent interpretation. The first raw
commit's interim STATUS line called 105 qualifying without this distinction;
this report and the final STATUS correct that shorthand.

Both denominators exceed the frozen minimum. Zero opportunities means
**REJECT**, with the frozen qualifier “at cadence.” The literal author output
`REJECT_at_cadence` maps to that allowed decision status. This does not reject
all NegRisk strategies, establish simultaneous execution, or test fills.

### Gross near miss and percentile differences

The largest size-feasible gross edge is **$0.018 = 1.8¢**, event `627652`,
“Bank of Russia decision in September?”, August 21 00:00 and 06:00 UTC.
Three YES asks sum to **$0.982**. Rates are 0.05 per leg; total frozen-formula
fees are **$0.02284780 = 2.28478¢**. Net is **−$0.00484780 = −0.48478¢**, matching
−0.48¢ at the recorded precision. Minimum ask size is **19.99** shares, above
the frozen five-share gate. These are two observations six hours apart; duration
between them is unknown.

“Best gross” must not be read as “best net.” The independent output's largest
size-feasible net edge is **0¢**, for event `850698` at August 21 00:00 UTC.
Thus the package README's “closest case” wording is accurate only if it refers
to the gross under-$1 case, not the largest net edge.

The first pass used linear-interpolated quantiles over 104 size-feasible slots;
the author's quantiles use the floor index `int(q×(n−1))` over 105 pre-size slots.
The frozen protocol does not specify a quantile estimator. First-pass medians
and tails therefore differ: ask-gap median **0.0475** versus recorded **0.043**,
and 95th percentile **0.2608** versus **0.237**. These remain in the raw output.
The labeled post-comparison calculation using the author's population and
estimator reproduces **every recorded quantile exactly**:

| Quantile | Minimum | 5% | 25% | 50% | 75% | 95% | Maximum |
|---|---:|---:|---:|---:|---:|---:|---:|
| Σask − 1 | −0.018 | 0.009 | 0.020 | 0.043 | 0.140 | 0.237 | 0.420 |
| 1 − Σbid | −0.005 | 0.003 | 0.019 | 0.054 | 0.104 | 0.216 | 0.500 |

## Gaps that this recount cannot remove

1. **Historical completeness:** local `events` and `event_markets` each contain
   zero rows. Without D1's supplemental event lists the frozen completeness
   check is **DATA-BLOCKED**, not REJECT. November 11 payloads recover the
   recorded arithmetic but cannot prove the unavailable October 5 payloads or
   the full historical outcome list. D1 was a post-freeze source deviation.
2. **Synchrony:** all 105 admitted slots have zero `captured_at` span because
   this timestamp is shared by a batch. Exchange book timestamps are available
   for all 105; **16 span more than 60 seconds**, maximum **929.946 seconds**.
   This does not replace the frozen synchrony field or trigger a new rerun;
   it shows why passing that gate does not verify simultaneous quotes. The
   Bank of Russia spans are **33.216 and 16.657 seconds**, not one instant.
3. **Coverage:** 1,422/1,527 (93.12%) event-slots fail completeness. The sample
   covers 24 admitted events, one day of non-authoritative data and six-hourly
   labeled captures. Seconds-scale gaps and most large incomplete events remain
   untested. Both datasets are explored and cannot be reused as a holdout.
4. **Metadata-count provenance:** saved Gamma covers 373 events versus the
   recorded October 5 `events_with_gamma=367`. Independently, 367 NegRisk groups
   have any usable snapshots, and 338 have usable labeled-slot snapshots. The
   extra six have no usable snapshots. This explains the count difference;
   it does not restore missing original payloads. It changes no admitted slot.

## Validation and handoff

Offline suite: **377 tests and 18 subtests passed** in 61.45 seconds, including
four new frozen-boundary checks. The four checks were rerun after the explicit
URI/audit-row change and passed. The post-comparison scripts also completed
against pinned inputs. Their assertions confirm unchanged first-pass bytes and
metrics, exact 105-slot membership, H-002 headline matches, and both full
published percentile tables. No author script was executed.

- [First-pass raw JSON](h002_e002_codex/first_pass.json), generated by `8020a2c`
  and committed in `73c8873`; 1.968 seconds.
- [Post-comparison raw JSON](h002_e002_codex/post_comparison.json), generated by
  `29b59da`; exposes all pre-size rows without replacing the first pass.
- [Comparison JSON](h002_e002_codex/comparison.json) and
  [comparison script](h002_e002_codex/compare.py), with author/input hashes,
  the excluded slot's exact legs and both near-miss rows.
- [Validation record](h002_e002_codex/validation.json) and
  [run instructions](h002_e002_codex/README.md).

**For Claude:** use 105 **pre-size**, 104 size-feasible, 24 events, zero
opportunities, +1.8¢ gross and −0.48478¢ net for the gross near miss. Keep the
source deviation, timestamp limitation and H-002's lack of numeric preregistration
in the public note. No changed threshold, new collection or owner decision is
needed to incorporate this bounded recount.

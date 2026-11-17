# PolySignal: scoped negative results (Polymarket quote screens)

PolySignal is a read-only research project on Polymarket. It does no trading.
This package holds two negative results and everything needed to rerun them: the
scripts, the recorded outputs, and a sanitized extract of the public order-book
data they use. Each result is narrow, and its scope is stated with it. Neither result
says anything about fills, latency races, or other mechanisms.

Re-derived on 2026-11-11 from the raw local capture (SQLite file, SHA-256
`1fb018c6c3e0dc74d740d142120f26193c9b452825e89bb4524b566763425885`). The extract in `data/`
reproduces both results exactly (see "Reproduction check").

## Data

Polymarket CLOB order books and Gamma market metadata, captured by our collector between
2026-08-20 11:36 and 2026-08-21 12:18 UTC. The collector ran on a 6-hour
schedule (slots at 12:00, 18:00, 00:00, 06:00 and 12:00, plus one earlier batch with no
slot label). This was a pre-production capture: one day, not an audited production feed.

| file | contents |
|---|---|
| `data/snapshots.csv.gz` (7.7 MB) | 70,458 market snapshots: market/event/YES-token ids, `captured_at`, `scheduled_slot`, `fetch_status`, YES and NO best bid/ask with sizes. For the 11,003 tier-A rows, where the YES and NO books were fetched separately, it also holds the full YES and NO ladders (`[[price, size], ...]`, the exchange's decimal strings) and the exchange's book timestamps in ms. |
| `data/markets.jsonl.gz` | 18,377 markets: id, question, and only the Gamma fields E-002 reads (`negRisk`, `negRiskMarketID`, `events[].id`, `orderMinSize`, `feesEnabled`, `feeSchedule`, `negRiskOther`). |
| `data/fee_observations.csv.gz` | 58,683 fee observations: `market_id`, `observed_at`, `fees_enabled`, `fee_rate`. |
| `data/gamma_events.json.gz` | 373 Gamma `/events/{id}` payloads, refetched 2026-11-11 and trimmed to the fields E-002 reads (event `negRiskAugmented`; per market `id`, `acceptingOrdersTimestamp`, `createdAt`, `closedTime`, `enableOrderBook`, `negRiskOther`, `question`). |

`captured_at` is one timestamp per collection batch, not a per-book fetch time. On tier-A
rows the exchange book timestamps show that one batch's books were fetched over several
minutes.

Checksums are in `SHA256SUMS`.

## Result 1: single-binary YES + NO asks never sum below $1 (H-002, single-binary form)

**Question.** In one binary market, can you buy both YES and NO at the quoted asks for less
than $1 combined, before fees?

**Rule.** This probe was **not pre-registered with a numeric threshold**. It was a direct
mechanism check, run on 2026-10-05 to settle a disagreement between two reviewers. The
claim it tested was: *"Polymarket's CLOB mirrors YES and NO into one book, so a YES bid at
p is a NO ask at 1−p."* If that holds, YES ask + NO ask = YES ask + 1 − YES bid
= 1 + spread ≥ 1, and the opportunity cannot appear in quotes. The reviewers' proposed
status was *"REJECT on mechanism, within the tested scope."*

**Data window.** All 6,432 tier-A snapshots with `fetch_status = ok` and a separately
fetched NO book. They cover 1,766 markets and 624 events, in 4 batches from 2026-08-20
18:01 to 2026-08-21 12:18 UTC.

**Result** (`mirrored_book_result.json`):

| check | result |
|---|---|
| NO best ask = 1 − YES best bid | 6,432 of 6,432 rows |
| YES ask + NO ask < 1 | 0 rows; minimum 1.001, mean 1.0368 |
| Full ladders mirror exactly (YES bids at (p, s) = NO asks at (1−p, s), and YES asks = NO bids likewise, exact decimals) | 6,385 of 6,432 pairs; 286,053 YES levels and 286,048 NO levels |
| Pairs that do not mirror | 47. The exchange timestamps of their YES and NO books differ by −3 to +17 ms (28 differ by exactly ±1 ms; 7 carry the same millisecond). None of the 47 has YES ask + NO ask < 1. |

The likely reason for the 47 mismatches is that the book changed between the two separate
HTTP fetches. The data are consistent with that, but it is not proven, because 7 pairs carry
the same millisecond.

**Scope of the claim.** These are Polymarket CLOB REST quotes for binary markets in our
tier-A set, at our 6-hourly capture cadence, on 2026-08-20/21. At the quote level, the
single-binary YES+NO "buy both for under $1" opportunity is ruled out by how the book works:
the NO book is the YES book mirrored. Fills, sub-second dynamics and on-chain
merge/split paths were not tested. Negative-risk multi-outcome baskets are a different
question (Result 2).

**Rerun.** `python mirrored_book.py data/snapshots.csv.gz > mirrored_book_result.json`
(Python 3.11 or later, standard library only).

## Result 2: NegRisk multi-outcome basket screen (E-002): REJECT at our cadence

**Question.** In mutually exclusive, exhaustive (NegRisk) events, does buying every YES at
the ask cost less than $1, or does buying every NO at the ask cost less than n−1, by more
than taker fees? The test uses executable quotes from the same capture slot.

**Frozen rule.** The rule was frozen on 2026-10-05, before any cross-market sum was
computed. The full protocol, copied verbatim, is in
`negrisk_basket/E-002_frozen_protocol.yaml`
(SHA-256 `b63c91fdd582eb58ed399a6fddb97f87dd05b3a76531b9d10c6ac22d783186a9`). Key lines:

> long_basket: "edge_long = 1 - sum_i(ask_i) - sum_i(fee(ask_i))"
> short_basket: "buy every NO at no_ask_i = 1 - bid_i (mirrored book): edge_short = sum_i(bid_i) - 1 - sum_i(fee(1 - bid_i))"
> fee(p) = feeRate * p * (1-p) per share […]
> size: "every leg's touch size >= max(market orderMinSize, 5) shares; YES ask size for long, YES bid size for short"
> opportunity: "a qualifying event-slot with edge_long > 0.005 or edge_short > 0.005 (0.5c per $1 basket payout)"
> DATA_BLOCKED: "fewer than 20 qualifying event-slots or fewer than 5 distinct events"
> REJECT_at_cadence: "enough data and zero opportunities. Scope: these events, this window, slot cadence, quotes only."
> synchrony: "max(captured_at) - min(captured_at) across legs <= 60 seconds"

Two deviations were recorded at run time. Neither changes a threshold or the economics.
- **D1:** the frozen completeness source turned out to be empty in the local data, so each
  event's market list came from the public Gamma API instead. A leg counts as tradable at
  time t if it has an order book, `acceptingOrdersTimestamp` (or `createdAt`) ≤ t, and no
  `closedTime` ≤ t.
- **D2:** 1,056 rows with no `scheduled_slot` cannot meet the "same scheduled_slot" rule,
  so they were excluded.

**Data window.** Snapshots from 2026-08-20 11:36 to 2026-08-21 12:18 UTC. Qualifying
event-slots fall in 5 scheduled slots, 6 hours apart.

**Result** (`negrisk_basket/E-002_result.json`):
- Funnel: 1,364 NegRisk markets in 373 events gave 1,527 event-slots. Of these, 1,422 were
  incomplete (not every tradable leg was captured in that slot), leaving **105 qualifying
  event-slots in 24 events and 5 slots, with a median of 5 legs**. That clears the frozen
  minimum of 20 slots and 5 events, but not by much.
- Limits found by the independent recount (`../independent_checks/negative_results/`):
  - 104 of the 105 meet the minimum order size;
  - completeness is judged against event lists refetched on 2026-11-11, because the
    original lists were not saved, so strict completeness against the frozen source is
    DATA-BLOCKED;
  - batch capture times do not establish simultaneity: on 16 of the 105, the exchange
    timestamps span more than 60 s, with a maximum of 929.9 s.
- Opportunities with net edge > 0.5¢ and enough size: **0**. Persistent episodes: **0**.
  **Decision: REJECT_at_cadence.**
- Σ YES asks − 1: minimum −0.018, 5th percentile 0.009, median 0.043, 95th percentile 0.237.
  1 − Σ YES bids: minimum −0.005, median 0.054.
- Closest case: the 3-outcome "Bank of Russia key rate after the September meeting" event.
  Its asks summed to $0.982 in both the 2026-08-21 00:00 and 06:00 slots, with at least 19.99
  shares per leg. Taker fees of about 2.3¢ left a net edge of −0.48¢ (`--debug` prints this
  row).

**Scope of the claim.** The claim covers only these 24 small NegRisk events, quoted on the
Polymarket CLOB at a 6-hourly batch cadence on 2026-08-20/21, using touch quotes (not
fills) and the fee schedule in force at capture. Large events with many outcomes were almost
always incomplete in our capture, so they are effectively untested. Gaps that last seconds
or minutes cannot be seen at this cadence. Conversion and gas costs were ignored, which
makes the screen *more* likely to find gaps.

**Rerun.** `cd negrisk_basket && python E-002_compute.py ../data > E-002_result.json`
(add `--debug` to print near-miss event-slots to stderr).

`E-002_compute_frozen.py` is the original script, byte for byte. It reads the private SQLite
file and a directory of Gamma payloads. `E-002_compute.py` is the same file, except that the
input-loading lines, marked `# [public I/O]`, read `data/` instead. Every filter, threshold,
fee formula and decision rule is untouched (`diff` the two files to check).

## Reproduction check (2026-11-11)

- Result 1: every recorded number (6,432 / 6,432; minimum 1.001; mean 1.037; 6,385 / 6,432;
  286,053 YES levels; 47 mismatches; none crossed) re-derived exactly. The top-of-book
  numbers were also checked directly against the raw database.
- Result 2: the frozen script on the raw database and the public script on `data/` give
  byte-identical JSON. Both match the recorded 2026-10-05 result exactly except for one
  count: `events_with_gamma` is 373 now and was 367 on 2026-10-05. The 6 extra events have no
  usable snapshots, so they never enter the screen. When the frozen script is run with only
  the 367 events that have snapshots, its output is byte-identical to the recorded
  `E-002_result_recorded_2026-10-05.json`. The 2026-10-05 Gamma payloads were not kept, so
  these results use payloads refetched on 2026-11-11. They give the same funnel and result.

## Limits common to both

- Each result rests on about one day of data, at a 6-hourly batch cadence.
- Both samples have now been explored, so they cannot serve as a holdout for these questions.
- These are quote-level screens. Neither tests fills, queue position, latency or market impact.
- A negative result here does not mean these mechanisms can never pay. It means that they
  did not show up in this setting.

"""E-002: NegRisk basket screen on local snapshots, per the frozen E-002.yaml. Read-only.

usage: python E-002_compute.py <polysignal.db> <gamma_event_dir> > E-002_result.json
gamma_event_dir holds https://gamma-api.polymarket.com/events/<id> payloads (deviation D1).
"""
import collections
import json
import sqlite3
import statistics
import sys
from datetime import datetime
from pathlib import Path

db, gdir = sys.argv[1], Path(sys.argv[2])
SYNC_S, EDGE, MIN_EVENTS_SLOTS, MIN_EVENTS = 60.0, 0.005, 20, 5


def ts(x):
    return datetime.fromisoformat(x.replace("Z", "+00:00")) if x else None


c = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
meta = {}
for mid, rj in c.execute("select id, raw_json from markets"):
    d = json.loads(rj)
    if d.get("negRisk") and d.get("negRiskMarketID"):
        meta[mid] = d
nr_key = {mid: d["negRiskMarketID"] for mid, d in meta.items()}
event_id = {d["negRiskMarketID"]: d["events"][0]["id"] for d in meta.values() if d.get("events")}

gamma = {}
for k, eid in event_id.items():
    p = gdir / f"{eid}.json"
    if p.exists():
        gamma[k] = json.loads(p.read_text())

snaps = collections.defaultdict(dict)  # (key, slot) -> market_id -> row
null_slot_rows = 0
for row in c.execute("""select market_id, scheduled_slot, captured_at, best_bid, best_ask, best_bid_size, best_ask_size
                        from market_snapshots_v2 where fetch_status='ok' and best_bid is not null and best_ask is not null"""):
    if row[0] in nr_key and row[1] is None:
        null_slot_rows += 1  # cannot satisfy "same scheduled_slot"
    elif row[0] in nr_key:
        snaps[(nr_key[row[0]], row[1])][row[0]] = row

fees = collections.defaultdict(list)
for mid, at, en, rate in c.execute("select market_id, observed_at, fees_enabled, fee_rate from market_fee_observations"):
    if mid in nr_key:
        fees[mid].append((at, en, rate))
for v in fees.values():
    v.sort()


def fee_rate(mid, at):
    obs = [o for o in fees.get(mid, []) if o[0] <= at]
    if obs:
        _, en, rate = obs[-1]
        return 0.0 if not en else rate
    d = meta.get(mid, {})
    if "feesEnabled" in d:
        return 0.0 if not d["feesEnabled"] else (d.get("feeSchedule") or {}).get("rate")
    return None


funnel = collections.Counter()
funnel["negrisk_markets"] = len(meta)
funnel["x_rows_null_slot"] = null_slot_rows
funnel["negrisk_events"] = len(set(nr_key.values()))
funnel["events_with_gamma"] = len(gamma)
qual, long_e, short_e, opps = [], [], [], []
for (key, slot), legs_seen in snaps.items():
    funnel["event_slots"] += 1
    g = gamma.get(key)
    if not g:
        funnel["x_no_gamma"] += 1
        continue
    t = min(ts(r[2]) for r in legs_seen.values())
    tradable = []
    for m in g.get("markets", []):
        start = ts(m.get("acceptingOrdersTimestamp")) or ts(m.get("createdAt"))
        end = ts(m.get("closedTime"))
        if m.get("enableOrderBook") and start and start <= t and (end is None or end > t):
            tradable.append(m)
    if len(tradable) < 2:
        funnel["x_lt2_legs"] += 1
        continue
    ids = {str(m["id"]) for m in tradable}
    if not ids <= set(legs_seen):
        funnel["x_incomplete"] += 1
        continue
    if g.get("negRiskAugmented") and not any(m.get("negRiskOther") for m in tradable):
        funnel["x_augmented_without_other"] += 1
        continue
    rows = [legs_seen[i] for i in ids]
    caps = [ts(r[2]) for r in rows]
    if (max(caps) - min(caps)).total_seconds() > SYNC_S:
        funnel["x_async"] += 1
        continue
    rates = {r[0]: fee_rate(r[0], r[2]) for r in rows}
    if any(v is None for v in rates.values()):
        funnel["x_fee_unknown"] += 1
        continue
    funnel["qualifying"] += 1
    mins = {r[0]: max(float(meta[r[0]].get("orderMinSize") or 5), 5.0) for r in rows}
    sum_ask = sum(r[4] for r in rows)
    sum_bid = sum(r[3] for r in rows)
    el = 1 - sum_ask - sum(rates[r[0]] * r[4] * (1 - r[4]) for r in rows)
    es = sum_bid - 1 - sum(rates[r[0]] * (1 - r[3]) * r[3] for r in rows)
    long_ok = all((r[6] or 0) >= mins[r[0]] for r in rows)
    short_ok = all((r[5] or 0) >= mins[r[0]] for r in rows)
    qual.append(dict(key=key, slot=slot, n=len(rows), sum_ask=sum_ask, sum_bid=sum_bid,
                     edge_long=el, edge_short=es, long_size_ok=long_ok, short_size_ok=short_ok))
    long_e.append(sum_ask - 1)
    short_e.append(1 - sum_bid)
    for d, e, ok in (("long", el, long_ok), ("short", es, short_ok)):
        if e > EDGE and ok:
            opps.append(dict(key=key, slot=slot, direction=d, edge=round(e, 4), legs=len(rows)))

slots = sorted({q["slot"] for q in qual})
idx = {s: i for i, s in enumerate(sorted({s for (_, s) in snaps}))}
episodes = collections.defaultdict(list)
for o in sorted(opps, key=lambda o: o["slot"]):
    episodes[(o["key"], o["direction"])].append(idx[o["slot"]])
persistent = sum(1 for v in episodes.values() if any(b - a == 1 for a, b in zip(v, v[1:])))
n_events = len({q["key"] for q in qual})


def quant(v):
    if not v:
        return None
    v = sorted(v)
    return {q: round(v[int(q * (len(v) - 1))], 4) for q in (0.0, 0.05, 0.25, 0.5, 0.75, 0.95, 1.0)}


if funnel["qualifying"] < MIN_EVENTS_SLOTS or n_events < MIN_EVENTS:
    decision = "DATA-BLOCKED"
elif not opps:
    decision = "REJECT_at_cadence"
elif persistent:
    decision = "INCONCLUSIVE_screen_survives"
else:
    decision = "REJECT_at_cadence_isolated"

if "--debug" in sys.argv:
    for q in qual:
        if q["sum_ask"] < 1 or q["sum_bid"] > 1:
            print(q, file=sys.stderr)
json.dump(dict(decision=decision, funnel=dict(funnel), qualifying_events=n_events, qualifying_slots=len(slots),
               opportunities=opps, persistent_episodes=persistent,
               sum_ask_minus_1=quant(long_e), one_minus_sum_bid=quant(short_e),
               legs_median=statistics.median([q["n"] for q in qual]) if qual else None),
          sys.stdout, indent=1)

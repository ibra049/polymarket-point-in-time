"""PN-1 deadline-edit audit: apply the frozen classification to the A13 creation-time instants.

usage: python audit.py <users_v1.3_dir> [--f1 inputs/F1_onchain_instants_final.json]
                       [--texts creation_texts.jsonl] [--out-dir .]

Inputs
  <users_v1.3_dir>/markets.parquet, events.parquet: Hugging Face dataset vgregoire/polymarket-users,
      commit 91ddb961 (CC-BY-4.0). Only non-outcome columns are read: market_id, event_id, question,
      market_start_time; event_id, event_ticker, title.
  --f1: one row per F1 ("by <deadline>") market from A13 (2026-10-08): gamma_instant (deadline parsed from
      the Gamma rules text fetched 2026-10-07), onchain_instant (deadline parsed from the creation-time
      on-chain question text), status, final_status, changed.
  --texts (optional): output of fetch_creation_text.py; adds both texts to the CSVs.

Frozen classification (PN-1 pre-registration), on rows with final_status == "ok" and changed == true,
with delta = gamma_instant - onchain_instant:
  FORMAT            |delta| < 1 h
  MATERIAL-LATER    delta >= +1 h
  MATERIAL-EARLIER  delta <= -1 h
The A13a creation-text errors (on-chain instant <= market_start_time) are listed separately.

Outputs (deterministic): deadline_edits.csv, creation_text_errors.csv, summary.json. Reads no outcomes.
"""
import argparse
import collections
import csv
import datetime as dt
import hashlib
import json
import os
import statistics

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

HERE = os.path.dirname(os.path.abspath(__file__))
HOUR = dt.timedelta(hours=1)
A13A = "excluded: on-chain deadline not after creation (creation-text error, A13a)"
CLASSES = ("FORMAT", "MATERIAL-LATER", "MATERIAL-EARLIER")
RECORDED = {"date": "2026-10-08", "kept_ok": 5559, "changed": 42, "later": 32, "earlier": 10,
            "a13a_creation_text_errors": 51}


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def classify(delta):
    if abs(delta) < HOUR:
        return "FORMAT"
    return "MATERIAL-LATER" if delta >= HOUR else "MATERIAL-EARLIER"


def days(td):
    return round(td.total_seconds() / 86400, 4)


def median_abs_days(deltas):
    return round(statistics.median(abs(d.total_seconds()) / 86400 for d in deltas), 4) if deltas else None


def text_checks(texts, f1):
    """Consistency of the fetched texts with the F1 file: second-provider byte match, and whether
    re-parsing each text with schedule_grammar_v3 reproduces the instant recorded in the F1 file."""
    if not texts:
        return None
    P = lambda s: dt.datetime.fromisoformat(s) if s else None
    got = [t for t in texts.values() if t.get("status") == "ok"]
    bad = sorted((t["market_id"] for t in got
                  if P(t.get("reparse_creation_instant")) != P(f1[t["market_id"]].get("onchain_instant"))
                  or P(t.get("reparse_current_instant")) != P(f1[t["market_id"]]["gamma_instant"])), key=int)
    return dict(retrieved=len(got), second_provider_same_bytes=sum(1 for t in got if t.get("verify_same_bytes")),
                reparse_reproduces_f1_both_instants=len(got) - len(bad), reparse_mismatch_market_ids=bad,
                note="1117833: creation text reads 'March 31, 20256'. The A13 run read this as 2025 (before the "
                     "A13a regex fix); the committed grammar reads no year, infers 2026, and gives 23:59:59 ET "
                     "(59 s from the current instant). The F1 file, as recorded, is what is classified."
                     if bad == ["1117833"] else None)


def main():
    ap = argparse.ArgumentParser(description="PN-1 deadline-edit audit")
    ap.add_argument("data_dir")
    ap.add_argument("--f1", default=os.path.join(HERE, "inputs", "F1_onchain_instants_final.json"))
    ap.add_argument("--texts", default=os.path.join(HERE, "creation_texts.jsonl"))
    ap.add_argument("--out-dir", default=HERE)
    a = ap.parse_args()

    mk_path, ev_path = os.path.join(a.data_dir, "markets.parquet"), os.path.join(a.data_dir, "events.parquet")
    f1 = json.load(open(a.f1))
    mk = pq.read_table(mk_path, columns=["market_id", "event_id", "question", "market_start_time"])
    mk = mk.filter(pc.is_in(mk["market_id"], pa.array([int(r["market_id"]) for r in f1], mk.schema.field("market_id").type)))
    markets = {str(r["market_id"]): r for r in mk.to_pylist()}
    ev = pq.read_table(ev_path, columns=["event_id", "event_ticker", "title"])
    ev = ev.filter(pc.is_in(ev["event_id"], mk["event_id"].unique()))
    events = {str(r["event_id"]): r for r in ev.to_pylist()}
    texts = {}
    if a.texts and os.path.exists(a.texts):
        for line in open(a.texts):
            x = json.loads(line)
            texts[x["market_id"]] = x

    P = dt.datetime.fromisoformat
    ids = [r["market_id"] for r in f1]
    assert len(ids) == len(set(ids)), "duplicate market_id in F1 file"
    assert all(i in markets for i in ids), "F1 market missing from markets.parquet"

    ok = [r for r in f1 if r["final_status"] == "ok"]
    changed = [r for r in ok if r.get("changed") is True]
    # changed must mean the two instants differ, and unchanged must mean they are equal
    assert all(P(r["gamma_instant"]) != P(r["onchain_instant"]) for r in changed)
    assert all(P(r["gamma_instant"]) == P(r["onchain_instant"]) for r in ok if r.get("changed") is False)

    # A13a recomputed from its rule: status ok on-chain, but on-chain instant <= market_start_time
    a13a_rule = sorted((r["market_id"] for r in f1 if r["status"] == "ok"
                        and P(r["onchain_instant"]) <= markets[r["market_id"]]["market_start_time"]), key=int)
    a13a_label = sorted((r["market_id"] for r in f1 if r["final_status"] == A13A), key=int)

    def base(r):
        m = markets[r["market_id"]]
        e = events.get(str(m["event_id"]), {})
        t = texts.get(r["market_id"], {})
        delta = P(r["gamma_instant"]) - P(r["onchain_instant"])
        return delta, dict(
            market_id=r["market_id"], event_id=str(m["event_id"]), event_slug=e.get("event_ticker"),
            event_title=e.get("title"), question=m["question"],
            market_start_time=m["market_start_time"].isoformat(),
            creation_instant=r["onchain_instant"], current_instant=r["gamma_instant"],
            delta_hours=round(delta.total_seconds() / 3600, 4), delta_days=days(delta),
            creation_block=t.get("block"), creation_tx=t.get("tx_hash"),
            creation_block_time=t.get("creation_block_time"), creation_title=t.get("creation_title"),
            creation_text=t.get("creation_ancillary"), current_text=t.get("current_text"))

    edit_rows, by_class = [], collections.defaultdict(list)
    for r in changed:
        delta, row = base(r)
        row["class"] = classify(delta)
        by_class[row["class"]].append((delta, row))
        edit_rows.append((CLASSES.index(row["class"]), -abs(delta), int(row["market_id"]), row))
    edit_rows = [x[-1] for x in sorted(edit_rows)]

    err_rows = []
    for r in (x for x in f1 if x["final_status"] == A13A):
        delta, row = base(r)
        err_rows.append((delta, row))
    err_rows.sort(key=lambda x: (-abs(x[0]), int(x[1]["market_id"])))

    cols = ["market_id", "event_id", "event_slug", "event_title", "question", "market_start_time",
            "creation_instant", "current_instant", "delta_hours", "delta_days", "class", "creation_block",
            "creation_tx", "creation_block_time", "creation_title", "creation_text", "current_text"]
    with open(os.path.join(a.out_dir, "deadline_edits.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, lineterminator="\n")
        w.writeheader()
        w.writerows(edit_rows)
    with open(os.path.join(a.out_dir, "creation_text_errors.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=[c for c in cols if c != "class"], lineterminator="\n")
        w.writeheader()
        w.writerows(row for _, row in err_rows)

    classes = {}
    for c in CLASSES:
        rows = by_class[c]
        classes[c] = dict(markets=len(rows), events=len({row["event_id"] for _, row in rows}),
                          median_abs_delta_days=median_abs_days([d for d, _ in rows]))
    material = by_class["MATERIAL-LATER"] + by_class["MATERIAL-EARLIER"]
    retrieved = lambda ids_: sum(1 for i in ids_ if texts.get(i, {}).get("status") == "ok")
    summary = dict(
        question="F1 markets whose question-text deadline changed after the on-chain creation record",
        prereg="PN-1_deadline_edit_audit_prereg.md (frozen before counts)",
        dataset="huggingface.co/datasets/vgregoire/polymarket-users @ 91ddb961 (Users v1.3, CC-BY-4.0)",
        inputs_sha256={"markets.parquet": sha256(mk_path), "events.parquet": sha256(ev_path),
                       os.path.basename(a.f1): sha256(a.f1),
                       **({os.path.basename(a.texts): sha256(a.texts)} if texts else {})},
        recount=dict(
            f1_rows=len(f1),
            status_counts=dict(sorted(collections.Counter(r["status"] for r in f1).items())),
            final_status_counts=dict(sorted(collections.Counter(r["final_status"] for r in f1).items())),
            final_ok=len(ok), final_ok_changed=len(changed),
            final_ok_changed_by_sign=dict(later=sum(1 for d, _ in sum(by_class.values(), []) if d > dt.timedelta(0)),
                                          earlier=sum(1 for d, _ in sum(by_class.values(), []) if d < dt.timedelta(0))),
            a13a_label_count=len(a13a_label), a13a_rule_recomputed_count=len(a13a_rule),
            a13a_rule_matches_label=a13a_rule == a13a_label),
        recorded_headline=RECORDED,
        classification=dict(
            rule="delta = current Gamma instant - creation on-chain instant; FORMAT |delta|<1h; "
                 "MATERIAL-LATER delta>=1h; MATERIAL-EARLIER delta<=-1h",
            by_class=classes,
            material=dict(markets=len(material), events=len({row["event_id"] for _, row in material}),
                          median_abs_delta_days=median_abs_days([d for d, _ in material]),
                          share_of_final_ok=round(len(material) / len(ok), 6)),
            all_changed_events=len({row["event_id"] for row in edit_rows}),
            material_list=[dict(market_id=row["market_id"], event_id=row["event_id"], event_slug=row["event_slug"],
                                cls=row["class"], delta_days=row["delta_days"])
                           for row in edit_rows if row["class"] != "FORMAT"],
            format_list=[dict(market_id=row["market_id"], event_id=row["event_id"], delta_hours=row["delta_hours"])
                         for row in edit_rows if row["class"] == "FORMAT"]),
        creation_text_errors_a13a=dict(
            markets=len(err_rows), events=len({row["event_id"] for _, row in err_rows}),
            current_differs_from_creation=sum(1 for d, _ in err_rows if d != dt.timedelta(0)),
            median_abs_delta_days=median_abs_days([d for d, _ in err_rows]),
            list=[dict(market_id=row["market_id"], event_id=row["event_id"], delta_days=row["delta_days"])
                  for _, row in err_rows]),
        creation_texts_retrieved=dict(deadline_edits=retrieved(r["market_id"] for r in edit_rows),
                                      deadline_edits_total=len(edit_rows),
                                      creation_text_errors=retrieved(r["market_id"] for _, r in err_rows),
                                      creation_text_errors_total=len(err_rows)),
        creation_text_checks=text_checks(texts, {r["market_id"]: r for r in f1}),
        cannot_see="Edit timing is unknown: only the creation record and the 2026-10-07 Gamma text are compared; "
                   "intermediate edits, and edits that were later reverted, are invisible.",
    )
    with open(os.path.join(a.out_dir, "summary.json"), "w") as fh:
        json.dump(summary, fh, indent=1, sort_keys=False)
        fh.write("\n")
    c = summary["classification"]
    print(json.dumps(dict(recount={k: v for k, v in summary["recount"].items() if "counts" not in k},
                          by_class=c["by_class"], material={k: v for k, v in c["material"].items()},
                          a13a={k: v for k, v in summary["creation_text_errors_a13a"].items() if k != "list"},
                          texts=summary["creation_texts_retrieved"]), indent=1))


if __name__ == "__main__":
    main()

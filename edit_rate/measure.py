"""PN-2 step 3: compute M1-M3 for the verified sample and write the per-market CSV and PN-2_result.json.

Pre-registration: polysignal-ops research/public_note/PN-2_population_edit_rate_prereg.md (frozen @ 44d0be8).

Sample: walk draws.json in draw order; a draw whose fetch status is "ok" (creation log found) is verified,
any other status is a replacement; stop at 1,000 verified or 2,000 draws.
Measures, per verified market (no outcomes, prices, trades or close times are read):
  M1 title edit: creation-time on-chain title (ancillary text between "title:" and the following
     "description:") != Users v1.3 `question`, after Unicode NFKC, whitespace collapse and case-folding.
     A creation text with no "title:" part has no M1 value (reported as a count).
  M2 deadline edit: frozen schedule_grammar_v5.parse on (a) the creation text's description part with the
     creation block time as year reference and (b) the Gamma description (fetched 2026-10-07) with Users v1.3
     market_start_time as year reference (the A13/PN-1 pairing). Denominator: both give an instant.
     Positive if |current - creation| >= 1 h; 0 < |delta| < 1 h is reported separately as FORMAT.
  M3 on-chain clarification: >= 1 AncillaryDataUpdated log for the questionID on the creating adapter, from
     the creation block to the fixed HEAD block of the fetch.
CIs: Wilson 95%, and an event-cluster bootstrap (10,000 resamples of Users v1.3 event_id clusters with
replacement, numpy default_rng(20261111), one index matrix shared by all measures; percentile 2.5/97.5;
rate = sum k / sum n over the resampled clusters).

usage: python measure.py <users_v1.3_dir> <grammar_dir> <draws.json> <fetch_raw.jsonl> <out.csv> <result.json>
"""
import collections
import csv
import datetime as dt
import hashlib
import json
import math
import os
import statistics
import sys
import unicodedata

import numpy as np
import pyarrow.parquet as pq

ROOT, GDIR, DRAWS, RAW, OUT_CSV, OUT_JSON = sys.argv[1:7]
sys.path.insert(0, GDIR)
from schedule_grammar_v5 import parse  # noqa: E402  (frozen, imported unchanged)

TARGET, MAX_DRAWS, MIN_N, SEED, B, Z = 1000, 2000, 400, 20261111, 10_000, 1.959963984540054
COLS = ["market_id", "event_id", "category", "question", "market_start_time"]


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def norm(s):
    return " ".join(unicodedata.normalize("NFKC", s or "").split()).casefold()


def title_of(text):
    if "title:" not in text:
        return None
    t = text.split("title:", 1)[1]
    for sep in (", description:", " description:", "description:"):
        if sep in t:
            return t.split(sep, 1)[0].strip()
    return t.strip()


def description_of(text):
    return text.split("description:", 1)[1] if "description:" in text else text


def wilson(k, n):
    if n == 0:
        return [None, None]
    p = k / n
    d = 1 + Z * Z / n
    c = (p + Z * Z / (2 * n)) / d
    h = Z * math.sqrt(p * (1 - p) / n + Z * Z / (4 * n * n)) / d
    return [round(max(0.0, c - h), 6), round(min(1.0, c + h), 6)]


def main():
    draws = json.load(open(DRAWS))
    order = draws["draws"]
    raw = {}
    for line in open(RAW):
        r = json.loads(line)
        raw[r["market_id"]] = r  # last record per market wins (rpc-error rows are retried on resume)
    meta = {str(r["market_id"]): r for r in pq.read_table(f"{ROOT}/markets.parquet", columns=COLS).to_pylist()}
    gamma = {}
    want = set(order)
    with open(f"{ROOT}/gamma_rules.jsonl") as fh:
        for line in fh:
            x = json.loads(line)
            if x["market_id"] in want:
                gamma[x["market_id"]] = x

    verified, replaced, walked = [], [], 0
    for m in order[:MAX_DRAWS]:
        if len(verified) >= TARGET:
            break
        if m not in raw:
            sys.exit(f"draw {walked + 1} ({m}) not fetched yet; run fetch.py with a larger --upto")
        walked += 1
        (verified if raw[m]["status"] == "ok" else replaced).append(m)

    rows = []
    for m in verified:
        r, md, g = raw[m], meta[m], gamma[m]
        text = r["creation_text"]
        created = dt.datetime.fromtimestamp(r["creation_ts"], dt.timezone.utc)
        t_on = title_of(text)
        m1 = None if t_on is None else int(norm(t_on) != norm(md["question"]))
        on_i, on_why, on_fam = parse(description_of(text), created)
        cur_i, cur_why, cur_fam = parse(g.get("description"), md["market_start_time"].to_pydatetime())
        both = on_i is not None and cur_i is not None
        delta_h = (cur_i - on_i).total_seconds() / 3600 if both else None
        n_upd = len(r["ancillary_updates"])
        rows.append(dict(
            draw_rank=order.index(m) + 1, market_id=m, event_id=md["event_id"], category=md["category"],
            created_utc=created.strftime("%Y-%m-%dT%H:%M:%SZ"),
            market_start_time=md["market_start_time"].strftime("%Y-%m-%dT%H:%M:%SZ"),
            adapter=r["adapter"], adapter_version=r["adapter_version"], creation_block=r["creation_block"],
            creation_tx=r["creation_tx"],
            m1_title_edit="" if m1 is None else m1,
            m2_both_parse=int(both), m2_deadline_edit=int(both and abs(delta_h) >= 1) if both else "",
            m2_format_only=int(both and 0 < abs(delta_h) < 1) if both else "",
            delta_hours="" if delta_h is None else round(delta_h, 4),
            onchain_instant=on_i.strftime("%Y-%m-%dT%H:%M:%SZ") if on_i else "", onchain_parse=on_why,
            onchain_family=on_fam or "",
            current_instant=cur_i.strftime("%Y-%m-%dT%H:%M:%SZ") if cur_i else "", current_parse=cur_why,
            current_family=cur_fam or "",
            m3_clarification=int(n_upd >= 1), n_clarifications=n_upd,
            n_clarifications_by_creator="" if r["n_ancillary_updates_by_creator"] is None else r["n_ancillary_updates_by_creator"],
            first_clarification_utc=dt.datetime.fromtimestamp(min(u["ts"] for u in r["ancillary_updates"]),
                                                              dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") if n_upd else "",
            onchain_title=t_on if t_on is not None else "", current_title=md["question"]))
    fields = list(rows[0].keys()) if rows else []
    with open(OUT_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    rep_csv = os.path.join(os.path.dirname(OUT_CSV), "replaced_draws.csv")
    with open(rep_csv, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["draw_rank", "market_id", "event_id", "category", "resolved_by", "status"])
        for m in replaced:
            w.writerow([order.index(m) + 1, m, meta[m]["event_id"], meta[m]["category"], gamma[m].get("resolvedBy") or "",
                        raw[m]["status"]])

    # ---- rates ----
    def rate_of(key_pos, key_den):
        den = [x for x in rows if key_den(x)]
        k = sum(1 for x in den if key_pos(x))
        return den, k

    measures = {
        "M1_title_edit": (lambda x: x["m1_title_edit"] == 1, lambda x: x["m1_title_edit"] != ""),
        "M2_deadline_edit": (lambda x: x["m2_deadline_edit"] == 1, lambda x: x["m2_both_parse"] == 1),
        "M2_format_only_sub_hour": (lambda x: x["m2_format_only"] == 1, lambda x: x["m2_both_parse"] == 1),
        "M3_onchain_clarification": (lambda x: x["m3_clarification"] == 1, lambda x: True),
    }
    ev = sorted({x["event_id"] if x["event_id"] is not None else f"market:{x['market_id']}" for x in rows})
    ev_ix = {e: i for i, e in enumerate(ev)}
    rng = np.random.default_rng(SEED)
    boot_idx = rng.integers(0, len(ev), size=(B, len(ev)))
    res_rates = {}
    for name, (pos, den_f) in measures.items():
        den, k = rate_of(pos, den_f)
        kk, nn = np.zeros(len(ev)), np.zeros(len(ev))
        for x in den:
            i = ev_ix[x["event_id"] if x["event_id"] is not None else f"market:{x['market_id']}"]
            nn[i] += 1
            kk[i] += 1 if pos(x) else 0
        sk, sn = kk[boot_idx].sum(axis=1), nn[boot_idx].sum(axis=1)
        ok = sn > 0
        br = sk[ok] / sn[ok]
        by_cat = collections.defaultdict(lambda: [0, 0])
        for x in den:
            by_cat[x["category"]][1] += 1
            by_cat[x["category"]][0] += 1 if pos(x) else 0
        positives = [x for x in den if pos(x)]
        res_rates[name] = dict(
            k=k, n=len(den), k_over_n=f"{k}/{len(den)}", rate=round(k / len(den), 6) if den else None,
            wilson95=wilson(k, len(den)),
            cluster_bootstrap95=[round(float(np.percentile(br, 2.5)), 6), round(float(np.percentile(br, 97.5)), 6)],
            bootstrap_resamples_used=int(ok.sum()),
            distinct_events_among_positives=len({x["event_id"] for x in positives}),
            by_category={c: f"{v[0]}/{v[1]}" for c, v in sorted(by_cat.items(), key=lambda t: (str(t[0])))},
            positive_market_ids=[x["market_id"] for x in positives])
    m2pos = [x for x in rows if x["m2_deadline_edit"] == 1]
    if m2pos:
        res_rates["M2_deadline_edit"]["median_abs_delta_hours"] = round(statistics.median(abs(x["delta_hours"]) for x in m2pos), 4)
        res_rates["M2_deadline_edit"]["median_abs_delta_days"] = round(statistics.median(abs(x["delta_hours"]) for x in m2pos) / 24, 4)
        res_rates["M2_deadline_edit"]["n_later"] = sum(1 for x in m2pos if x["delta_hours"] >= 1)
        res_rates["M2_deadline_edit"]["n_earlier"] = sum(1 for x in m2pos if x["delta_hours"] <= -1)
        res_rates["M2_deadline_edit"]["abs_delta_hours_list"] = sorted(round(abs(x["delta_hours"]), 4) for x in m2pos)
    else:
        res_rates["M2_deadline_edit"]["median_abs_delta_hours"] = None
    # supplementary, not a pre-registered measure: M3 restricted to clarifications posted by the question creator
    cre = [x for x in rows if x["n_clarifications_by_creator"] != ""]
    supp = dict(M3_creator_only=dict(
        note="supplementary, not pre-registered: >=1 AncillaryDataUpdated whose owner == QuestionInitialized creator; "
             "v1-adapter markets (no creator topic) excluded from this denominator",
        k=sum(1 for x in cre if x["n_clarifications_by_creator"] >= 1), n=len(cre)))
    supp["M3_creator_only"]["wilson95"] = wilson(supp["M3_creator_only"]["k"], supp["M3_creator_only"]["n"])

    n = len(rows)
    rep_reasons = collections.Counter(raw[m]["status"] for m in replaced)
    rep_cat = collections.Counter(meta[m]["category"] for m in replaced)
    rep_adapter = collections.Counter(gamma[m].get("resolvedBy") or "none" for m in replaced)
    heads = {raw[m]["head_block"] for m in verified + replaced}
    gfiles = ["schedule_grammar_v5.py", "schedule_grammar_v4.py", "schedule_grammar_v3.py"]
    here = os.path.dirname(os.path.abspath(__file__))
    result = dict(
        study="PN-2 population-wide post-creation edit rate",
        prereg="polysignal-ops research/public_note/PN-2_population_edit_rate_prereg.md @ 44d0be8",
        status="DATA-BLOCKED" if n < MIN_N else "MEASURED",
        population_size=draws["population_size"], population_sha256_sorted_ids=draws["population_sha256_sorted_ids"],
        seed=SEED, draws_walked=walked, replacements=len(replaced), achieved_n=n, target_n=TARGET,
        replacement_reasons=dict(rep_reasons), replacement_category_mix=dict(sorted(rep_cat.items(), key=lambda t: str(t[0]))),
        replacement_resolved_by_mix=dict(rep_adapter),
        verified_category_mix=dict(sorted(collections.Counter(x["category"] for x in rows).items(), key=lambda t: str(t[0]))),
        verified_adapter_version_mix=dict(collections.Counter(x["adapter_version"] for x in rows)),
        distinct_events_in_sample=len(ev),
        m1_no_title_part=sum(1 for x in rows if x["m1_title_edit"] == ""),
        m2_parse_counts=dict(both=sum(1 for x in rows if x["m2_both_parse"] == 1),
                             onchain_only=sum(1 for x in rows if x["onchain_instant"] and not x["current_instant"]),
                             current_only=sum(1 for x in rows if x["current_instant"] and not x["onchain_instant"]),
                             neither=sum(1 for x in rows if not x["current_instant"] and not x["onchain_instant"])),
        rates=res_rates, supplementary=supp,
        ci_methods=dict(wilson="Wilson score interval, z=1.959964",
                        cluster_bootstrap="10,000 resamples of event_id clusters with replacement, numpy default_rng(20261111), "
                                          "shared index matrix across measures, percentile 2.5/97.5, ratio sum(k)/sum(n)"),
        log_source=sorted({raw[m]["source"] for m in verified + replaced}), head_block=sorted(heads),
        source_check=(lambda p: {k: v for k, v in json.load(open(p)).items()} if os.path.exists(p) else None)(
            os.path.join(os.path.dirname(os.path.abspath(RAW)), "source_check.json")),
        input_sha256={"markets.parquet": sha(f"{ROOT}/markets.parquet"), "gamma_rules.jsonl": sha(f"{ROOT}/gamma_rules.jsonl"),
                      "draws.json": sha(DRAWS), "fetch_raw.jsonl": sha(RAW),
                      **{g: sha(os.path.join(GDIR, g)) for g in gfiles},
                      **{s: sha(os.path.join(here, s)) for s in ("sample.py", "fetch.py", "measure.py")}},
        outputs=dict(csv=os.path.basename(OUT_CSV), replaced=os.path.basename(rep_csv)),
        generated_utc=dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
    json.dump(result, open(OUT_JSON, "w"), indent=1)
    print(json.dumps({k: v for k, v in result.items() if k not in ("rates",)}, indent=1, default=str))
    for k, v in res_rates.items():
        print(k, v["k_over_n"], v["wilson95"], v["cluster_bootstrap95"], v["distinct_events_among_positives"], v["by_category"])


if __name__ == "__main__":
    main()

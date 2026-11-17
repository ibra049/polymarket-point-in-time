"""A17 schedule grammar v5 = v4 + three exclusions (owner decision 10-14). Spec: AMENDMENT_A4_A5_shared.yaml A17.

Exclusion only; no expression gains support. Changes from v4 (everything else in schedule_grammar_v4.py and v3 holds):
  - time_window_gap: time-first F2 (TIME [ZONE] gap "on" DATE) whose gap contains another clock -> market excluded.
  - unknown_timezone: time-first F2 with no recognised zone, where the text right after the clock is unknown-zone
    wording -> market excluded.
  - multi_day_schedule: accepted F4 clause followed by [", <year>"] to/through/until/thru/-/–/— [month] <day> ->
    market excluded.
A14 (option A): primary families are F2, F3, F4 (timed). A16 named exclusions are applied downstream as a mask.
"""
import re

from schedule_grammar_v3 import BAD_OP, CONDITIONAL_START, ET, FALLBACK, MON, NEXT_EVENT, UNKNOWN_ZONE_AFTER_TIME, UNTIMED_ON
from schedule_grammar_v4 import (CLAUSES, F2_ON_AT, F2_TIME_FIRST, F3_RANGE, PARTIAL, PREC, PRIMARY, TIME, Reject,
                                 _instant, sentences)

A16_MASK = {"1060452", "503942", "588150"}
CLOCK = re.compile(r"(?<![\w:])(?:" + TIME + r")(?!\w)", re.I)
F4_RANGE = re.compile(r"^(?:\s*,?\s*20\d\d)?\s*(?:to|through|until|thru|-|–|—)\s*(?:" + MON.replace("?P<mon>", "?:")
                      + r"\s+)?\d{1,2}(?!\d)", re.I)
KNOWN_ZONE_PREFIX = re.compile(r"^\s*\(?\s*(?:ET|EST|EDT|UTC|GMT|PT|PST|PDT)\b")


def _unknown_zone(after):
    return bool(UNKNOWN_ZONE_AFTER_TIME.match(after)) and not KNOWN_ZONE_PREFIX.match(after)


def parse_full(rules, creation_utc):
    """Dict: instant (UTC or None), reason, family, primary, trace (accepted clauses with spans)."""
    out = dict(instant=None, reason=None, family=None, primary=False, trace=[])
    if not rules:
        return dict(out, reason="no_rules")
    created_et = creation_utc.astimezone(ET).date()
    found, untimed_on_resolution = {}, False
    next_event = bool(NEXT_EVENT.search(rules))
    for s0, s1 in sentences(rules):
        sent = rules[s0:s1]
        is_res = "resolv" in sent.lower()
        cands = [(fam, "clause", m) for fam, rx in CLAUSES for m in rx.finditer(sent)]
        if is_res:
            cands += [("F2", "on_at", m) for m in F2_ON_AT.finditer(sent)]
            cands += [("F2", "time_first", m) for m in F2_TIME_FIRST.finditer(sent)]
            cands += [("F3", "range", m) for m in F3_RANGE.finditer(sent)]
        cands = [c for c in cands if c[0] == "F4" or is_res]
        best = {}
        for fam, kind, m in cands:  # one candidate per date mention: earliest start, then family precedence
            k = m.start("mon")
            if k not in best or (m.start(), PREC[fam]) < (best[k][2].start(), PREC[best[k][0]]):
                best[k] = (fam, kind, m)
        for fam, kind, m in sorted(best.values(), key=lambda c: c[2].start()):
            if fam in ("F1i", "F1x"):
                if next_event or "resolv" not in sent[:m.start()].lower() or CONDITIONAL_START.search(sent):
                    continue
            if FALLBACK.search(sent[:m.start()]) or BAD_OP.search(sent[max(0, m.start() - 10):m.start() + 30]):
                continue
            tail = sent[m.end():m.end() + 40]
            if kind == "time_first":  # A17 time_window_gap and time-first unknown zone
                clock_end = m.end("zone") if m.group("zone") else m.end("time")
                if CLOCK.search(sent[clock_end:m.start("mon")]):
                    return dict(out, reason="time_window_gap", family=fam)
                if not m.group("zone") and _unknown_zone(sent[m.end("time"):m.end("time") + 40]):
                    return dict(out, reason="unknown_timezone", family=fam)
            if fam == "F4" and F4_RANGE.match(tail):  # A17 multi_day_schedule
                return dict(out, reason="multi_day_schedule", family=fam)
            if PARTIAL.match(tail):
                return dict(out, reason="partial_temporal", family=fam)
            if m.group("time") and not m.group("zone") and _unknown_zone(tail):
                return dict(out, reason="unknown_timezone", family=fam)
            try:
                inst = _instant(m, fam, created_et)
            except Reject as e:
                return dict(out, reason=str(e), family=fam)
            found.setdefault(inst, []).append((fam, bool(m.group("time"))))
            out["trace"].append(dict(family=fam, span=[s0 + m.start(), s0 + m.end()], text=m.group(0),
                                     instant=inst.strftime("%Y-%m-%dT%H:%M:%SZ")))
        if is_res and not cands and UNTIMED_ON.search(sent) and not FALLBACK.search(sent):
            untimed_on_resolution = True
    if not found:
        return dict(out, reason="untimed_on_date" if untimed_on_resolution else "no_clause")
    if len(found) > 1:
        return dict(out, reason="multiple_deadlines")
    inst, contrib = next(iter(found.items()))
    fam = min((f for f, _ in contrib), key=PREC.get)
    if fam == "F4" and not any((f == "F4" and timed) or f == "F2" for f, timed in contrib):
        fam = "F4d"
    return dict(out, instant=inst, reason="ok", family=fam, primary=fam in PRIMARY)


def parse(rules, creation_utc):
    """Return (instant_utc or None, reason, family), same shape as v3/v4."""
    r = parse_full(rules, creation_utc)
    return r["instant"], r["reason"], r["family"]

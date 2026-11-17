"""A15 schedule grammar v4 = v3 + R-007 fixes (owner decision 10-12). Spec: AMENDMENT_A4_A5_shared.yaml A15.

Changes from v3 (everything else in schedule_grammar_v3.py's docstring is unchanged):
  - Explicit seconds are kept (12 h "h:mm:ss AM/PM", 24 h "HH:MM:SS").
  - partial_temporal: a surviving clause followed (after optional ",", spaces, "at") by a digit, "noon" or
    "midnight" excludes the market (unconsumed clock / year / malformed year such as "20256").
  - A 24 h clock is accepted only before a known zone (any ZONES word or a UTC/GMT offset).
  - Sentences do not split at the dot of a.m. / p.m.
  - Ranges: 12 h hour 1-12; minutes and seconds 0-59; 24 h hour 0-23. Otherwise invalid_time.
  - One candidate per date mention (keyed by the matched month's start): the earliest-starting match wins,
    ties by family precedence F4 > F2 > F3 > F1i > F1x, chosen before fallback / main-clause filters.
  - Same single instant from several clauses: family = highest precedence, not the last match.
  - F4d: an instant from untimed F4 clauses only (no timed F4 or F2 contributor). Not a primary family.
A14 (option A): primary families are F2, F3, F4 (timed). F1i/F1x/F4d are not primary.
"""
import datetime as dt
import re

from schedule_grammar_v3 import (BAD_OP, CONDITIONAL_START, ET, FALLBACK, MON, MONTHS, NEXT_EVENT,
                                 UNKNOWN_ZONE_AFTER_TIME, UNTIMED_ON, _zone)

PRIMARY = {"F2", "F3", "F4"}
PREC = {"F4": 0, "F2": 1, "F3": 2, "F1i": 3, "F1x": 4}
DATE = MON + r"\s+(?P<day>\d{1,2})(?!\d)(?:st|nd|rd|th)?(?:,?\s+(?P<year>20\d\d)(?!\d))?"
ZONE_WORD = (r"(?:in\s+the\s+)?(?:eastern|pacific|coordinated universal time|est|edt|et|pst|pdt|pt|cst|cdt|ct|utc|gmt)"
             r"\b")
TIME = (r"(?P<time>(?P<h>\d{1,2})(?::(?P<mi>\d{2}))?(?::(?P<s>\d{2}))?\s*(?P<ap>a\.?m\.?|p\.?m\.?)|noon|midnight|"
        r"(?P<h24>\d{1,2}):(?P<mi24>\d{2})(?::(?P<s24>\d{2}))?(?=\s*\(?\s*" + ZONE_WORD + r"))")
ZONE = (r"(?P<zone>\(?\s*(?:in\s+the\s+)?(?:et|est|edt|pt|pst|pdt|ct|cst|cdt|utc|gmt|eastern(?:\s+time)?|"
        r"pacific(?:\s+time)?|coordinated universal time)\b(?:\s*timezone)?(?:\s*[+\-−]\s*\d{1,2}(?::?\d{2})?)?\s*\)?)")
AFTER_DATE = r"(?:\s*,?\s*(?:at\s+)?" + TIME + r")?(?:\s*" + ZONE + r")?"
OPS = {"F1i": r"by|no later than|on or before|until|through", "F1x": r"before|prior to",
       "F4": r"scheduled for|scheduled to take place on|scheduled to begin on|set for|takes place on|will take place on"}
CLAUSES = [(fam, re.compile(r"\b(?P<op>" + ops + r")\s+(?:the\s+end\s+of\s+)?" + DATE + AFTER_DATE, re.I))
           for fam, ops in OPS.items()]
F2_ON_AT = re.compile(r"\bon\s+" + DATE + r"\s*,?\s*(?:at\s+)?" + TIME + r"(?:\s*" + ZONE + r")?", re.I)
F2_TIME_FIRST = re.compile(TIME + r"(?:\s*" + ZONE + r")?[^.]{0,60}?\bon\s+" + DATE, re.I)
F3_RANGE = re.compile(r"\b(?:between|from)\s+" + MON.replace("?P<mon>", "?:") + r"\s+\d{1,2}[^.]{0,80}?\b(?:and|to|through|until)\s+"
                      + DATE + AFTER_DATE, re.I)
PARTIAL = re.compile(r"^\s*,?\s*(?:at\s+)?(?:\d|noon\b|midnight\b)", re.I)
ABBREV = re.compile(r"(?:\b[A-Z]|U\.S|Mr|Mrs|Ms|Dr|Jr|Sr|St|vs|No|Inc|Corp|Co|Ltd|Gov|Sen|Rep|e\.g|i\.e|etc|approx|"
                    r"Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec|(?i:\b[ap]\.m))$")


class Reject(ValueError):
    pass


def sentences(text):
    """List of (start, end) sentence spans with abbreviation-aware boundaries (v3 + a.m./p.m.)."""
    spans, start = [], 0
    for m in re.finditer(r"[.!?](?=\s)|\n", text):
        if m.group(0) == "." and ABBREV.search(text[max(0, m.start() - 6):m.start()]):
            continue
        spans.append((start, m.end()))
        start = m.end()
    spans.append((start, len(text)))
    return spans


def _instant(m, fam, created_et):
    key = m.group("mon").lower().rstrip(".")
    month = MONTHS["sep" if key.startswith("sep") else key[:3]]
    day, year = int(m.group("day")), m.group("year")
    try:
        if year:
            date = dt.date(int(year), month, day)
        else:
            date = dt.date(created_et.year, month, day)
            if date < created_et:
                date = dt.date(created_et.year + 1, month, day)
    except ValueError:
        raise Reject("invalid_date")
    t = m.group("time")
    if t and t.lower() == "midnight":
        raise Reject("midnight")
    if t and t.lower() == "noon":
        tm = dt.time(12, 0)
    elif t and m.group("h24"):
        h, mi, s = int(m.group("h24")), int(m.group("mi24")), int(m.group("s24") or 0)
        if h > 23 or mi > 59 or s > 59:
            raise Reject("invalid_time")
        tm = dt.time(h, mi, s)
    elif t:
        h, mi, s = int(m.group("h")), int(m.group("mi") or 0), int(m.group("s") or 0)
        if not 1 <= h <= 12 or mi > 59 or s > 59:
            raise Reject("invalid_time")
        tm = dt.time(h % 12 + (12 if m.group("ap").lower().startswith("p") else 0), mi, s)
    else:
        tm = dt.time(0, 0) if fam == "F1x" else dt.time(23, 59, 59)
    zone = _zone(m.group("zone"))
    if zone is None:
        raise Reject("unknown_timezone")
    return dt.datetime.combine(date, tm, tzinfo=zone).astimezone(dt.timezone.utc)


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
        cands = [(fam, m) for fam, rx in CLAUSES for m in rx.finditer(sent)]
        if is_res:
            cands += [("F2", m) for m in F2_ON_AT.finditer(sent)] + [("F2", m) for m in F2_TIME_FIRST.finditer(sent)]
            cands += [("F3", m) for m in F3_RANGE.finditer(sent)]
        cands = [(f, m) for f, m in cands if f == "F4" or is_res]
        best = {}
        for fam, m in cands:  # one candidate per date mention: earliest start, then family precedence
            k = m.start("mon")
            if k not in best or (m.start(), PREC[fam]) < (best[k][1].start(), PREC[best[k][0]]):
                best[k] = (fam, m)
        for fam, m in sorted(best.values(), key=lambda c: c[1].start()):
            if fam in ("F1i", "F1x"):
                if next_event or "resolv" not in sent[:m.start()].lower() or CONDITIONAL_START.search(sent):
                    continue
            if FALLBACK.search(sent[:m.start()]) or BAD_OP.search(sent[max(0, m.start() - 10):m.start() + 30]):
                continue
            tail = sent[m.end():m.end() + 40]
            if PARTIAL.match(tail):
                return dict(out, reason="partial_temporal", family=fam)
            if m.group("time") and not m.group("zone"):
                if UNKNOWN_ZONE_AFTER_TIME.match(tail) and not re.match(
                        r"^\s*\(?\s*(?:ET|EST|EDT|UTC|GMT|PT|PST|PDT)\b", tail):
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
    """Return (instant_utc or None, reason, family), same shape as v3."""
    r = parse_full(rules, creation_utc)
    return r["instant"], r["reason"], r["family"]

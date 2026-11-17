"""A12 schedule grammar v3 = v2 + F1-only main-clause and next-event rules (option C).

A11 schedule grammar v2 (full date-wording sweep). Parse rules text into one resolution-determining instant (UTC).

Built from date_wording_inventory.json (all 729,015 rules texts). Families:
  F1i deadline, inclusive:  by | no later than | on or before | until | through   <date> [time] [tz]
  F1x deadline, exclusive:  before | prior to                                    <date> [time] [tz]
  F2  instant:              on <date> at <time> [tz]   or   <time> [tz phrase] ... on <date>   (time before date)
  F3  window end:           between <date1> ... and <date2> [time]   |   from <date1> ... to <date2> [time]
  F4  scheduled event:      scheduled for | scheduled to take place on | set for | takes place on   <date> [at time] [tz]
Rules:
  - F1/F2/F3 clauses count only in a resolution sentence (contains "resolv"); F4 counts in any sentence.
  - Fallbacks are ignored: a clause preceded in its sentence by "if"/"in the event"/"should" + a negation or
    cancel/postpone/delay/"for any reason"/"otherwise", or whose operator is beyond/after.
  - Exactly one distinct instant must remain, else excluded. An untimed "on <date>" in a resolution sentence
    with no other clause excludes the market.
  - Time zones: ET/Eastern, "in the ET timezone" -> America/New_York; EST/EDT fixed; PT/Pacific/"Los Angeles
    time" -> America/Los_Angeles; PST/PDT fixed; CT/CST/CDT -> America/Chicago; UTC/GMT/Coordinated Universal
    Time -> UTC; "UTC+N"/"GMT+N" (also "(UTC +2)") -> fixed offset. Any other zone wording after a time ->
    excluded (unknown_timezone). No zone after a time -> ET (Polymarket convention).
  - Date only: inclusive -> 23:59:59, exclusive -> 00:00:00, F4 -> 23:59:59 (event day end), in ET.
  - noon -> 12:00; "midnight" -> excluded (ambiguous day boundary).
  - Year: explicit, else first occurrence of month/day at or after creation (ET calendar date).
  - Sentence boundaries: [.!?] + whitespace or a newline, except after common abbreviations (single capital
    letters, U.S., Mr., Mrs., Ms., Dr., Jr., Sr., St., vs., No., Inc., Corp., Co., Ltd., Gov., Sen., Rep.,
    e.g., i.e., etc., approx., month abbreviations).
"""
import datetime as dt
import re
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
ZONES = {"et": ET, "eastern": ET, "eastern time": ET, "est": dt.timezone(dt.timedelta(hours=-5)),
         "edt": dt.timezone(dt.timedelta(hours=-4)), "pt": ZoneInfo("America/Los_Angeles"),
         "pacific": ZoneInfo("America/Los_Angeles"), "pacific time": ZoneInfo("America/Los_Angeles"),
         "pst": dt.timezone(dt.timedelta(hours=-8)), "pdt": dt.timezone(dt.timedelta(hours=-7)),
         "ct": ZoneInfo("America/Chicago"), "cst": dt.timezone(dt.timedelta(hours=-6)),
         "cdt": dt.timezone(dt.timedelta(hours=-5)), "utc": dt.timezone.utc, "gmt": dt.timezone.utc,
         "coordinated universal time": dt.timezone.utc}
MONTHS = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6, "jul": 7, "aug": 8, "sep": 9, "oct": 10,
          "nov": 11, "dec": 12}
MON = (r"(?P<mon>january|february|march|april|may|june|july|august|september|october|november|december|"
       r"jan|feb|mar|apr|jun|jul|aug|sept|sep|oct|nov|dec)\.?")
DATE = MON + r"\s+(?P<day>\d{1,2})(?!\d)(?:st|nd|rd|th)?(?:,?\s+(?P<year>20\d\d)(?!\d))?"  # A13a: no "20256"
TIME = (r"(?P<time>(?P<h>\d{1,2})(?::(?P<mi>\d{2}))?(?::\d{2})?\s*(?P<ap>a\.?m\.?|p\.?m\.?)|noon|midnight|"
        r"(?P<h24>[01]?\d|2[0-3]):(?P<mi24>\d{2})(?=\s*(?:\(?\s*)?(?:utc|gmt|et\b)))")
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
UNTIMED_ON = re.compile(r"\bon\s+" + DATE + r"(?!\s*,?\s*(?:at\s+)?\d)", re.I)
BAD_OP = re.compile(r"\b(beyond|after)\s+" + MON.replace("?P<mon>", "?:") + r"\s+\d", re.I)
FALLBACK = re.compile(r"\b(?:if|in the event|should)\b.*?(?:\bno\b|\bnot\b|n['’]t\b|\bcannot\b|\bnever\b|\bfails?\b|"
                      r"\bcancel\w*|\bpostpone\w*|\bdelay\w*|\bfor any reason\b|\botherwise\b)", re.I | re.S)
ABBREV = re.compile(r"(?:\b[A-Z]|U\.S|Mr|Mrs|Ms|Dr|Jr|Sr|St|vs|No|Inc|Corp|Co|Ltd|Gov|Sen|Rep|e\.g|i\.e|etc|approx|"
                    r"Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)$")
NEXT_EVENT = re.compile(r"\bnext\s+(?:\w+\s+){0,3}(briefing|press conference|conference|speech|address|episode|interview|"
                        r"podcast|appearance|event|broadcast|show|call|meeting|rally|debate|game|match)\b", re.I)
CONDITIONAL_START = re.compile(r"^\W*(if|in the event|should|unless|in case)\b", re.I)
UNKNOWN_ZONE_AFTER_TIME = re.compile(r"^\s*\(?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3}\s+(?:Standard|Daylight|Summer)?\s*Time\b|"
                                     r"[A-Z]{2,5}\b)")


def sentences(text):
    """List of (start, end) sentence spans with abbreviation-aware boundaries."""
    spans, start = [], 0
    for m in re.finditer(r"[.!?](?=\s)|\n", text):
        if m.group(0) == "." and ABBREV.search(text[max(0, m.start() - 6):m.start()]):
            continue
        spans.append((start, m.end()))
        start = m.end()
    spans.append((start, len(text)))
    return spans


def _zone(z):
    if not z:
        return ET
    s = re.sub(r"[()\s]+", " ", z.lower()).replace("in the", "").replace("timezone", "").strip()
    off = re.search(r"(utc|gmt)\s*([+\-−])\s*(\d{1,2})(?::?(\d{2}))?", s)
    if off:
        sign = -1 if off.group(2) in "-−" else 1
        return dt.timezone(sign * dt.timedelta(hours=int(off.group(3)), minutes=int(off.group(4) or 0)))
    s = re.sub(r"\s*[+\-−].*$", "", s).strip()
    return ZONES.get(s)


def _instant(m, fam, created_et):
    key = m.group("mon").lower().rstrip(".")
    month = MONTHS["sep" if key.startswith("sep") else key[:3]]
    day, year = int(m.group("day")), m.group("year")
    if year:
        date = dt.date(int(year), month, day)
    else:
        date = dt.date(created_et.year, month, day)
        if date < created_et:
            date = dt.date(created_et.year + 1, month, day)
    t = m.group("time")
    if t and t.lower() == "midnight":
        raise ValueError("midnight")
    if t and t.lower() == "noon":
        tm = dt.time(12, 0)
    elif t and m.group("h24"):
        tm = dt.time(int(m.group("h24")), int(m.group("mi24")))
    elif t:
        tm = dt.time(int(m.group("h")) % 12 + (12 if m.group("ap").lower().startswith("p") else 0), int(m.group("mi") or 0))
    else:
        tm = dt.time(0, 0) if fam == "F1x" else dt.time(23, 59, 59)
    zone = _zone(m.group("zone"))
    if zone is None:
        raise ValueError("unknown_timezone")
    return dt.datetime.combine(date, tm, tzinfo=zone).astimezone(dt.timezone.utc)


def parse(rules, creation_utc):
    """Return (instant_utc or None, reason, family)."""
    if not rules:
        return None, "no_rules", None
    created_et = creation_utc.astimezone(ET).date()
    found, untimed_on_resolution = {}, False
    next_event = bool(NEXT_EVENT.search(rules))  # A12 (2)
    for s0, s1 in sentences(rules):
        sent = rules[s0:s1]
        is_res = "resolv" in sent.lower()
        cands = [(fam, m) for fam, rx in CLAUSES for m in rx.finditer(sent)]
        if is_res:
            cands += [("F2", m) for m in F2_ON_AT.finditer(sent)] + [("F2", m) for m in F2_TIME_FIRST.finditer(sent)]
            cands += [("F3", m) for m in F3_RANGE.finditer(sent)]
        for fam, m in cands:
            if fam != "F4" and not is_res:
                continue
            if fam in ("F1i", "F1x"):  # A12 (1) main-clause rule and (2) next-event rule
                if next_event or "resolv" not in sent[:m.start()].lower() or CONDITIONAL_START.search(sent):
                    continue
            if FALLBACK.search(sent[:m.start()]) or BAD_OP.search(sent[max(0, m.start() - 10):m.start() + 30]):
                continue
            if m.group("time") and not m.group("zone"):
                tail = sent[m.end():m.end() + 40]
                if UNKNOWN_ZONE_AFTER_TIME.match(tail) and not re.match(r"^\s*\(?\s*(?:ET|EST|EDT|UTC|GMT|PT|PST|PDT)\b",
                                                                        tail):
                    return None, "unknown_timezone", fam
            try:
                found[_instant(m, fam, created_et)] = fam
            except ValueError as e:
                return None, ("unknown_timezone" if "timezone" in str(e) else
                              "midnight" if "midnight" in str(e) else "invalid_date"), fam
        if is_res and not cands and UNTIMED_ON.search(sent) and not FALLBACK.search(sent):
            untimed_on_resolution = True
    if not found:
        return None, ("untimed_on_date" if untimed_on_resolution else "no_clause"), None
    if len(found) > 1:
        return None, "multiple_deadlines", None
    inst, fam = next(iter(found.items()))
    return inst, "ok", fam

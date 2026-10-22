"""
scratch_attacker5.py - eval #8 gaming review, attacker 5: planning pins and the two hard planning gates
(P1.1-P1.5, GATE.DATE, GATE.SERIES), the structure atoms (P1.5, C1.structure, D1.record) and the cascade.

Re-run from the repo root:
    python outputs/eval8-live/gaming-review/scratch_attacker5.py            # every attack, one line each
    python outputs/eval8-live/gaming-review/scratch_attacker5.py <text>     # only attacks whose name contains <text>
    python outputs/eval8-live/gaming-review/scratch_attacker5.py --checks   # the PINNABLE CHECKS (PASS = fixed behaviour)

Line format:  id | verdict | case | name | before->after (case_gated) | AllPass | gates | flags | gated checkpoint scores
Verdicts:     HELD    = the grader did what a correct grader must do
              FINDING = it did not (a wrong answer scored well / was not gated, or a right answer was gated or marked down)
              INFO    = exploration data with no clear right answer (reported, not counted as a finding)
The base answer is the case oracle re-serialised through the live SCHEMA (JSON, dates as strings), which grades
1.000/AllPass on both cases. No repository file is touched.
"""
from __future__ import annotations
import copy
import datetime as dt
import json
import os
import sys
import time

sys.dont_write_bytecode = True
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, REPO)
from harness import run_case                                   # noqa: E402
from harness.rubric import load_case                           # noqa: E402
from harness.suites import options_redemption as orx          # noqa: E402
from harness.live_options_redemption import oracle_to_schema, build_packet   # noqa: E402

B = "grbo-redeem-2026"           # the break: long put 240.00 confirms 12,000 vs 120 due; gold HOLD
C = "grbo-redeem-2026-clean"     # every leg ties; gold SETTLE

GOLD_OSI = ["4IWM  260930C00002400", "4IWM  260930P00240000", "4IWM  260930P00204000", "4IWM  260930C00282000"]
SIB_OSI = ["4IWM  261030C00002350", "4IWM  261030P00235000", "4IWM  261030P00199750", "4IWM  261030C00276000"]
T, S, EXP = dt.date(2026, 6, 23), dt.date(2026, 6, 24), dt.date(2026, 9, 30)


def _p(c):
    return os.path.join(REPO, "cases", f"{c}.case.yaml")


_BASE = {}


def base(case):
    """a JSON-shaped perfect answer: the oracle re-serialised through the live SCHEMA (dates are strings)"""
    if case not in _BASE:
        _BASE[case] = oracle_to_schema(load_case(_p(case)))
    return copy.deepcopy(_BASE[case])


def variant(case, name):
    """an offline designed-flaw variant, JSON round-tripped so dates are strings like a live answer"""
    return json.loads(json.dumps(orx.make(load_case(_p(case)), name), default=str))


def run(case, m):
    r, _ = run_case(_p(case), model_output=m)
    return r


def verdicts(case, m):
    """atom id -> met for the answer m: run_case's own steps, returning the verdict map"""
    from harness.rubric import load_rubric, materialize, rubric_path_for
    from harness.graders import grade
    from harness import suites
    cs = load_case(_p(case))
    rb = load_rubric(rubric_path_for(cs))
    suite = suites.for_case(cs)
    atoms = materialize(rb, cs)
    gold = dict(cs["gold"])
    gold["manifest"] = cs.get("manifest", {})
    gold["_snapshot"] = cs.get("snapshot")
    gold["_claims"] = cs.get("claims")
    gold["_documents"] = cs.get("documents")
    gold["_case"] = cs
    v, _ = grade(atoms, m, gold, rb, suite)
    return {k: round(x.met, 3) for k, x in v.items()}


def cp(r, k):
    return r.checkpoints[k]["score_gated"]


def perfect(r):
    return r.allpass == 1 and abs(r.case_gated - 1.0) < 1e-6 and not r.fired_gates


def gate(r, g):
    return g in r.fired_gates


def setp(path, value):
    def mut(m):
        cur = m
        for k in path[:-1]:
            cur = cur.setdefault(k, {})
        cur[path[-1]] = value
    return mut


def delp(path):
    def mut(m):
        cur = m
        for k in path[:-1]:
            cur = cur.get(k, {})
        cur.pop(path[-1], None)
    return mut


def many(*muts):
    def mut(m):
        for f in muts:
            f(m)
    return mut


# ----------------------------------------------------------------------------------------------- registry
ROWS = []
N = [0]
FILTER = ""


def attack(case, name, mutate, expect, ref=None, note="", atoms=()):
    """mutate: fn(m) editing the JSON-shaped perfect answer.  expect: fn(result)->bool, True = the grader HELD;
    None = INFO (exploration, no clear right answer).  ref: a reference answer (callable -> dict) whose score is the 'before'."""
    N[0] += 1
    aid = f"A{N[0]:03d}"
    if FILTER and FILTER.lower() not in name.lower() and FILTER.lower() != aid.lower():
        return
    m = base(case)
    mutate(m)
    t0 = time.time()
    try:
        r = run(case, m)
        if time.time() - t0 > 2.0:
            note = (note + " " if note else "") + f"SLOW {time.time() - t0:.1f}s"
    except Exception as e:                       # a crash is the most serious result of all
        print(f"{aid} | CRASH   | {case[-5:]} | {name} | {type(e).__name__}: {e}")
        ROWS.append((aid, "CRASH", case, name, None, None, None, [], [], {}))
        return
    before = None
    if ref is not None:
        before = run(case, ref()).case_gated
    tag = "INFO   " if expect is None else ("HELD   " if expect(r) else "FINDING")
    if atoms:
        vv = verdicts(case, copy.deepcopy(m))
        note = (note + " " if note else "") + "atoms:" + ",".join(f"{a}={vv.get(a)}" for a in atoms)
    cps = " ".join(f"{k}={r.checkpoints[k]['score_gated']:.2f}" for k in r.checkpoints)
    b = "1.000" if before is None else f"{before:.3f}"
    short = "brk" if case == B else "cln"
    print(f"{aid} | {tag} | {short} | {name} | {b}->{r.case_gated:.3f} | AP={r.allpass} | gates={r.fired_gates} | flags={r.flags} | {cps}"
          + (f" | {note}" if note else ""))
    ROWS.append((aid, tag.strip(), case, name, before, r.case_gated, r.allpass, list(r.fired_gates), list(r.flags),
                 {k: round(v['score_gated'], 3) for k, v in r.checkpoints.items()}))


def PERFECT(r):
    return perfect(r)


def GATES(*gs):
    return lambda r: all(g in r.fired_gates for g in gs)


def NO_GATE(g):
    return lambda r: not gate(r, g)


def NOT_PERFECT(r):
    return not perfect(r)


def notation_table():
    def wk(d):
        return d.strftime("%A")

    def suf(d):
        n = d.day
        return "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return {
        "ISO+T00:00:00": lambda d: d.isoformat() + "T00:00:00",
        "ISO+T00:00:00Z": lambda d: d.isoformat() + "T00:00:00Z",
        "ISO+T00:00:00.000Z": lambda d: d.isoformat() + "T00:00:00.000Z",
        "ISO+T00:00:00-04:00": lambda d: d.isoformat() + "T00:00:00-04:00",
        "ISO space 00:00:00": lambda d: d.isoformat() + " 00:00:00",
        "ISO space HH:MM": lambda d: d.isoformat() + " 14:47",
        "D Month YYYY": lambda d: f"{d.day} {d.strftime('%B')} {d.year}",
        "Month D, YYYY": lambda d: f"{d.strftime('%B')} {d.day}, {d.year}",
        "Month D YYYY": lambda d: f"{d.strftime('%B')} {d.day} {d.year}",
        "Mon D, YYYY": lambda d: f"{d.strftime('%b')} {d.day}, {d.year}",
        "Mon D YYYY": lambda d: f"{d.strftime('%b')} {d.day} {d.year}",
        "D Mon YYYY": lambda d: f"{d.day} {d.strftime('%b')} {d.year}",
        "DD-Mon-YYYY": lambda d: f"{d.day:02d}-{d.strftime('%b')}-{d.year}",
        "DD-MON-YYYY": lambda d: f"{d.day:02d}-{d.strftime('%b').upper()}-{d.year}",
        "MM/DD/YYYY": lambda d: d.strftime("%m/%d/%Y"),
        "M/D/YYYY": lambda d: f"{d.month}/{d.day}/{d.year}",
        "YYYYMMDD": lambda d: d.strftime("%Y%m%d"),
        "YYYYMMDD int": lambda d: int(d.strftime("%Y%m%d")),
        "DD.MM.YYYY": lambda d: d.strftime("%d.%m.%Y"),
        "DD/MM/YYYY": lambda d: d.strftime("%d/%m/%Y"),
        "DD-MM-YYYY": lambda d: d.strftime("%d-%m-%Y"),
        "YYYY/MM/DD": lambda d: d.strftime("%Y/%m/%d"),
        "YYYY.MM.DD": lambda d: d.strftime("%Y.%m.%d"),
        "Weekday, Month D, YYYY": lambda d: f"{wk(d)}, {d.strftime('%B')} {d.day}, {d.year}",
        "Wkd D Mon YYYY": lambda d: f"{wk(d)[:3]} {d.day} {d.strftime('%b')} {d.year}",
        "Month Dth, YYYY": lambda d: f"{d.strftime('%B')} {d.day}{suf(d)}, {d.year}",
        "MM/DD/YY": lambda d: d.strftime("%m/%d/%y"),
        "D Month, YYYY": lambda d: f"{d.day} {d.strftime('%B')}, {d.year}",
        "MM/DD/YYYY HH:MM": lambda d: d.strftime("%m/%d/%Y") + " 00:00",
        "ISO (T)": lambda d: d.isoformat() + " (T)",
    }


# ============================================================================================ 1. DATE NOTATIONS
def section_dates():
    print("\n## 1. date notation on the three GATE.DATE fields (trade_date, settlement_date, pcf_date) - a RIGHT answer")
    for nm, f in notation_table().items():
        attack(B, f"dates as {nm}",
               many(setp(("P1", "trade_date"), f(T)), setp(("P1", "settlement_date"), f(S)), setp(("P1", "pcf_date"), f(T))), PERFECT)
    attack(B, "dates as 'T = <iso>' labels", many(setp(("P1", "trade_date"), "T = 2026-06-23"), setp(("P1", "settlement_date"), "T+1 = 2026-06-24"),
                                                  setp(("P1", "pcf_date"), "T = 2026-06-23")), None)
    attack(B, "settlement_date written 'T+1'", setp(("P1", "settlement_date"), "T+1"), None)
    print("\n## 1b. the same notations on series_expiry (GATE.SERIES) - a RIGHT answer")
    for nm, f in notation_table().items():
        attack(B, f"series_expiry as {nm}", setp(("P1", "series_expiry"), f(EXP)), PERFECT)
    print("\n## 1c. one field only, clean case, the most plausible failures")
    for nm in ("Mon D YYYY", "DD-Mon-YYYY", "DD/MM/YYYY", "Weekday, Month D, YYYY", "Month Dth, YYYY", "MM/DD/YY"):
        attack(C, f"clean: trade_date only as {nm}", setp(("P1", "trade_date"), notation_table()[nm](T)), PERFECT)


# ============================================================================================ 2. ABSENCE
def section_absence():
    print("\n## 2. does a HARD gate fire on ABSENCE? (right content, a pin field missing)")
    for k in ("pcf_date", "trade_date", "settlement_date"):
        attack(B, f"P1.{k} key missing", delp(("P1", k)), NO_GATE("GATE.DATE"))
        attack(B, f"P1.{k} null", setp(("P1", k), None), NO_GATE("GATE.DATE"))
    attack(B, "P1.pcf_date '' (empty string)", setp(("P1", "pcf_date"), ""), NO_GATE("GATE.DATE"))
    attack(B, "P1.pcf_date missing, pcf_id right (the id carries the date)", delp(("P1", "pcf_date")), NO_GATE("GATE.DATE"))
    attack(B, "P1.pcf_id missing, dates right", delp(("P1", "pcf_id")), PERFECT)
    attack(B, "P1.pcf_id AND pcf_date missing", many(delp(("P1", "pcf_id")), delp(("P1", "pcf_date"))), NO_GATE("GATE.DATE"))
    attack(B, "P1.series_expiry key missing", delp(("P1", "series_expiry")), NO_GATE("GATE.SERIES"))
    attack(B, "P1.series_expiry null", setp(("P1", "series_expiry"), None), NO_GATE("GATE.SERIES"))
    attack(B, "P1.series_osi key missing (E1.legs right: fallback)", delp(("P1", "series_osi")), PERFECT)
    attack(B, "P1.series_osi [] (E1.legs right: fallback)", setp(("P1", "series_osi"), []), PERFECT)
    attack(B, "P1.series_osi missing AND E1.legs missing", many(delp(("P1", "series_osi")), delp(("E1", "legs"))), None)
    attack(B, "P1.series_osi missing AND series_expiry missing", many(delp(("P1", "series_osi")), delp(("P1", "series_expiry"))), None)
    attack(B, "P1 entirely missing", lambda m: m.pop("P1"), None)
    attack(B, "P1 = {}", lambda m: m.update({"P1": {}}), None)
    attack(C, "clean: P1 entirely missing", lambda m: m.pop("P1"), None)


# ============================================================================================ 3. PCF ID
def section_pcf_id():
    print("\n## 3. pcf_id notation / resolution (dates right unless stated)")
    for s in ("PCF GRBO 20260623", "pcf-grbo-20260623", "PCF-GRBO-20260623 (basket of record)", "PCF_GRBO_20260623",
              "PCF-GRBO-20260623 basket of record", "PCF-GRBO-20260623, published 2026-06-22 21:30 ET", "PCF-GRBO-20260623 v1",
              "20260623", "GRBO PCF 2026-06-23", "2026-06-23"):
        attack(B, f"pcf_id {s!r} (the right PCF)", setp(("P1", "pcf_id"), s), PERFECT)
    attack(B, "pcf_id dict {'pcf_id': 'PCF-GRBO-20260623'}", setp(("P1", "pcf_id"), {"pcf_id": "PCF-GRBO-20260623"}), PERFECT)
    attack(B, "pcf_id NEXT-DAY 'PCF-GRBO-20260624', pcf_date right", setp(("P1", "pcf_id"), "PCF-GRBO-20260624"), GATES("GATE.DATE"))
    attack(B, "pcf_id next-day 'pcf grbo 20260624' (case/space)", setp(("P1", "pcf_id"), "pcf grbo 20260624"), GATES("GATE.DATE"))
    attack(B, "pcf_id next-day 'PCF-GRBO-20260624 (next-day)' (parenthetical dropped)", setp(("P1", "pcf_id"), "PCF-GRBO-20260624 (next-day)"), GATES("GATE.DATE"))
    attack(B, "pcf_id next-day + comma suffix 'PCF-GRBO-20260624, published 2026-06-23 21:30 ET', pcf_date right",
           setp(("P1", "pcf_id"), "PCF-GRBO-20260624, published 2026-06-23 21:30 ET"), GATES("GATE.DATE"))
    attack(B, "pcf_id next-day 'PCF-GRBO-20260624 v2'", setp(("P1", "pcf_id"), "PCF-GRBO-20260624 v2"), GATES("GATE.DATE"))
    attack(B, "pcf_id next-day 'GRBO 24 Jun 2026 PCF'", setp(("P1", "pcf_id"), "GRBO 24 Jun 2026 PCF"), GATES("GATE.DATE"))
    attack(B, "pcf_id next-day as dict {'pcf_id':'PCF-GRBO-20260624'}", setp(("P1", "pcf_id"), {"pcf_id": "PCF-GRBO-20260624"}), GATES("GATE.DATE"))
    attack(B, "pcf_id next-day 'PCF-GRBO-20260624' AND pcf_date 2026-06-24",
           many(setp(("P1", "pcf_id"), "PCF-GRBO-20260624"), setp(("P1", "pcf_date"), "2026-06-24")), GATES("GATE.DATE"))
    attack(B, "pcf_date 2026-06-24 only (id right)", setp(("P1", "pcf_date"), "2026-06-24"), GATES("GATE.DATE"))
    attack(B, "pcf_date 2026-06-22 (publication date of the PCF of record; id right)", setp(("P1", "pcf_date"), "2026-06-22"), NO_GATE("GATE.DATE"))
    attack(B, "pcf_date '2026-06-22 21:30 ET' (published_et of the PCF of record; id right)", setp(("P1", "pcf_date"), "2026-06-22 21:30 ET"), NO_GATE("GATE.DATE"))
    attack(B, "INVENTED pcf_id 'PCF-GRBO-20260623-R2' (dates right)", setp(("P1", "pcf_id"), "PCF-GRBO-20260623-R2"), NOT_PERFECT)
    attack(B, "INVENTED pcf_id 'PCF-XYZZ-99999999' (dates right)", setp(("P1", "pcf_id"), "PCF-XYZZ-99999999"), NOT_PERFECT)
    attack(B, "pcf_id = SIBLING 'PCF-GRBN-20260623' (series pins right)", setp(("P1", "pcf_id"), "PCF-GRBN-20260623"), GATES("GATE.SERIES"))
    attack(B, "pcf_id sibling + ticker GRBN + fund Nov (series pins right)",
           many(setp(("P1", "pcf_id"), "PCF-GRBN-20260623"), setp(("P1", "ticker"), "GRBN"),
                setp(("P1", "fund"), "Granite Ridge U.S. Small Cap Buffer ETF - November")), GATES("GATE.SERIES"))
    attack(B, "pcf_id mixed 'PCF-GRBN-20260624' (no such PCF)", setp(("P1", "pcf_id"), "PCF-GRBN-20260624"), NOT_PERFECT)
    for nm, v in (("a list of both", ["PCF-GRBO-20260623", "PCF-GRBO-20260624"]), ("'A or B'", "PCF-GRBO-20260623 or PCF-GRBO-20260624"),
                  ("'A / B'", "PCF-GRBO-20260623 / PCF-GRBO-20260624"), ("'next-day / sibling'", "PCF-GRBO-20260624 / PCF-GRBN-20260623")):
        attack(B, f"pcf_id hedge {nm}", setp(("P1", "pcf_id"), v), NOT_PERFECT)


# ============================================================================================ 4. SERIES
def section_series():
    print("\n## 4. series_osi / series_expiry")
    attack(B, "series_osi single spaces", setp(("P1", "series_osi"), [o.replace("  ", " ") for o in GOLD_OSI]), PERFECT)
    attack(B, "series_osi unpadded no spaces", setp(("P1", "series_osi"), [o.replace(" ", "") for o in GOLD_OSI]), PERFECT)
    attack(B, "series_osi lowercase", setp(("P1", "series_osi"), [o.lower() for o in GOLD_OSI]), PERFECT)
    attack(B, "series_osi objects {osi_identifier}", setp(("P1", "series_osi"), [{"osi_identifier": o} for o in GOLD_OSI]), PERFECT)
    attack(B, "series_osi objects {leg_id, osi_identifier}", setp(("P1", "series_osi"), [{"leg_id": f"L{i+1}", "osi_identifier": o} for i, o in enumerate(GOLD_OSI)]), PERFECT)
    attack(B, "series_osi objects {leg_id, osi} (other key)", setp(("P1", "series_osi"), [{"leg_id": f"L{i+1}", "osi": o} for i, o in enumerate(GOLD_OSI)]), PERFECT)
    attack(B, "series_osi objects {leg_id, series}", setp(("P1", "series_osi"), [{"leg_id": f"L{i+1}", "series": o} for i, o in enumerate(GOLD_OSI)]), PERFECT)
    attack(B, "series_osi dict keyed by leg id", setp(("P1", "series_osi"), {f"L{i+1}": o for i, o in enumerate(GOLD_OSI)}), PERFECT)
    attack(B, "series_osi 'L1: <osi>' labelled strings", setp(("P1", "series_osi"), [f"L{i+1}: {o}" for i, o in enumerate(GOLD_OSI)]), PERFECT)
    attack(B, "series_osi '<osi> (L1)' labelled strings", setp(("P1", "series_osi"), [f"{o} (L{i+1})" for i, o in enumerate(GOLD_OSI)]), PERFECT)
    attack(B, "series_osi '<osi> - leg' described", setp(("P1", "series_osi"), [f"{o} - leg" for o in GOLD_OSI]), PERFECT)
    attack(B, "series_osi 'O:' occ-prefixed (Polygon style)", setp(("P1", "series_osi"), ["O:" + o.replace(" ", "") for o in GOLD_OSI]), None)
    attack(B, "series_osi one comma-joined string (E1.legs right: fallback)", setp(("P1", "series_osi"), ", ".join(GOLD_OSI)), PERFECT)
    attack(B, "series_osi different order", setp(("P1", "series_osi"), list(reversed(GOLD_OSI))), PERFECT)
    attack(B, "series_osi duplicates (8 items, 4 distinct)", setp(("P1", "series_osi"), GOLD_OSI + GOLD_OSI), PERFECT)
    attack(B, "series_osi three of four", setp(("P1", "series_osi"), GOLD_OSI[:3]), GATES("GATE.SERIES"))
    attack(B, "series_osi four + SHARES 'GRBO' (a fifth, non-OSI entry)", setp(("P1", "series_osi"), GOLD_OSI + ["GRBO"]), None)
    attack(B, "series_osi four + empty string", setp(("P1", "series_osi"), GOLD_OSI + [""]), PERFECT)
    attack(B, "series_osi four + None", setp(("P1", "series_osi"), GOLD_OSI + [None]), PERFECT)
    attack(B, "series_osi = sibling four", setp(("P1", "series_osi"), SIB_OSI), GATES("GATE.SERIES"))
    attack(B, "series_osi = two gold + two sibling", setp(("P1", "series_osi"), GOLD_OSI[:2] + SIB_OSI[2:]), GATES("GATE.SERIES"))
    attack(B, "series_osi = gold + sibling (8)", setp(("P1", "series_osi"), GOLD_OSI + SIB_OSI), GATES("GATE.SERIES"))
    attack(B, "series_osi gold, series_expiry = sibling 2026-10-30", setp(("P1", "series_expiry"), "2026-10-30"), GATES("GATE.SERIES"))
    attack(B, "series_osi sibling, series_expiry gold", setp(("P1", "series_osi"), SIB_OSI), GATES("GATE.SERIES"))
    attack(B, "series_osi sibling given as ONE string (E1.legs right: the pin is ignored)", setp(("P1", "series_osi"), ", ".join(SIB_OSI)), GATES("GATE.SERIES"))
    attack(B, "series_osi = True (E1.legs right)", setp(("P1", "series_osi"), True), None)
    attack(B, "series_osi gold + sibling in a parenthetical", setp(("P1", "series_osi"), [f"{o} (not {s})" for o, s in zip(GOLD_OSI, SIB_OSI)]), PERFECT)
    attack(B, "series_osi sibling hidden in a parenthetical after a gold-looking label",
           setp(("P1", "series_osi"), [f"{s} ({o})" for o, s in zip(GOLD_OSI, SIB_OSI)]), GATES("GATE.SERIES"))
    attack(B, "series_expiry '2026-09' (month only)", setp(("P1", "series_expiry"), "2026-09"), None)
    attack(B, "series_expiry hedge '2026-09-30 or 2026-10-30'", setp(("P1", "series_expiry"), "2026-09-30 or 2026-10-30"), NOT_PERFECT)
    attack(B, "series_expiry list ['2026-09-30']", setp(("P1", "series_expiry"), ["2026-09-30"]), None)
    attack(B, "series_expiry 'last business day of September 2026'", setp(("P1", "series_expiry"), "last business day of September 2026"), None)


# ============================================================================================ 5. DODGES
def section_dodges():
    print("\n## 5. dodging the gates with a WRONG answer (pins right, content wrong); 'before' = the stock variant")

    def ss_pins_gold(m):
        m["P1"]["series_osi"] = list(GOLD_OSI)
        m["P1"]["series_expiry"] = "2026-09-30"
        m["P1"]["pcf_id"] = "PCF-GRBO-20260623"

    def ss_pins_gold_keep_id(m):
        m["P1"]["series_osi"] = list(GOLD_OSI)
        m["P1"]["series_expiry"] = "2026-09-30"
    ref_ss = lambda: variant(B, "series_slip")
    attack(B, "series_slip content, stock pins (control)", lambda m: m.update(variant(B, "series_slip")), GATES("GATE.SERIES"))
    attack(B, "series_slip content (E1 sibling legs, due 110, series_mismatch) but P1 pins gold + id gold",
           lambda m: (m.update(variant(B, "series_slip")), ss_pins_gold(m)), GATES("GATE.SERIES"), ref=ref_ss)
    attack(B, "series_slip content but P1 pins gold, pcf_id left sibling",
           lambda m: (m.update(variant(B, "series_slip")), ss_pins_gold_keep_id(m)), GATES("GATE.SERIES"), ref=ref_ss)
    attack(B, "series_slip content but series_osi omitted (fallback reads sibling E1.legs)",
           lambda m: (m.update(variant(B, "series_slip")), m["P1"].pop("series_osi"), m["P1"].update({"series_expiry": "2026-09-30"})),
           GATES("GATE.SERIES"), ref=ref_ss)
    attack(B, "series_slip content, series_osi as ONE string of the gold OSIs (pin ignored, E1 sibling read)",
           lambda m: (m.update(variant(B, "series_slip")), m["P1"].update({"series_osi": ", ".join(GOLD_OSI), "series_expiry": "2026-09-30"})),
           GATES("GATE.SERIES"), ref=ref_ss)
    attack(B, "gold answer but E1.legs read from the GRBN PCF (pins gold)",
           lambda m: m["E1"].update({"legs": variant(B, "series_slip")["E1"]["legs"]}), GATES("GATE.SERIES"))
    attack(B, "gold answer but E1.legs sibling + cash est 3900 (pins gold)",
           lambda m: m["E1"].update({"legs": variant(B, "series_slip")["E1"]["legs"], "cash_component_per_cu_estimated": 3900.0}), GATES("GATE.SERIES"))
    ref_dt = lambda: variant(B, "date_slip")
    attack(B, "date_slip content, stock pins (control)", lambda m: m.update(variant(B, "date_slip")), GATES("GATE.DATE"))

    def ds_honest(m):
        m.update(variant(B, "date_slip"))
        m["P1"]["pcf_id"] = "PCF-GRBO-20260623"
        m["P1"]["pcf_date"] = "2026-06-23"
    attack(B, "date_slip content (E1 cash est 4620 from the next-day PCF) but pins say PCF-GRBO-20260623 / 06-23", ds_honest, GATES("GATE.DATE"), ref=ref_dt)

    def ds_published(m):
        m.update(variant(B, "date_slip"))
        m["P1"].pop("pcf_id", None)
        m["P1"]["pcf_date"] = "2026-06-23"      # the next-day PCF's published_et date
    attack(B, "date_slip content, pcf_id omitted, pcf_date = next-day PCF's PUBLISHED date 06-23", ds_published, GATES("GATE.DATE"), ref=ref_dt)

    def ds_suffix(m):
        m.update(variant(B, "date_slip"))
        m["P1"]["pcf_id"] = "PCF-GRBO-20260624, published 2026-06-23 21:30 ET"
        m["P1"]["pcf_date"] = "2026-06-23"
    attack(B, "date_slip content, pcf_id next-day with a comma suffix, pcf_date 06-23", ds_suffix, GATES("GATE.DATE"), ref=ref_dt)
    attack(B, "dates shifted a day: trade 06-24 / settle 06-25 / pcf_date 06-24",
           many(setp(("P1", "trade_date"), "2026-06-24"), setp(("P1", "settlement_date"), "2026-06-25"), setp(("P1", "pcf_date"), "2026-06-24")), GATES("GATE.DATE"))
    attack(B, "trade/settlement swapped", many(setp(("P1", "trade_date"), "2026-06-24"), setp(("P1", "settlement_date"), "2026-06-23")), GATES("GATE.DATE"))
    attack(B, "settlement T+2 (06-25)", setp(("P1", "settlement_date"), "2026-06-25"), GATES("GATE.DATE"))
    attack(B, "settlement same day T+0 (06-23)", setp(("P1", "settlement_date"), "2026-06-23"), GATES("GATE.DATE"))
    attack(B, "trade_date hedge '2026-06-23 or 2026-06-24'", setp(("P1", "trade_date"), "2026-06-23 or 2026-06-24"), NOT_PERFECT)
    attack(B, "trade_date range '2026-06-23/2026-06-24'", setp(("P1", "trade_date"), "2026-06-23/2026-06-24"), NOT_PERFECT)
    attack(B, "settlement_date hedge '2026-06-24 (or 2026-06-23 if same-day)'", setp(("P1", "settlement_date"), "2026-06-24 (or 2026-06-23 if same-day)"), NOT_PERFECT)
    attack(B, "pcf_date hedge '2026-06-23 / 2026-06-24'", setp(("P1", "pcf_date"), "2026-06-23 / 2026-06-24"), NOT_PERFECT)
    attack(B, "all three dates hedged, next day as the second value",
           many(setp(("P1", "trade_date"), "2026-06-23, 2026-06-24"), setp(("P1", "settlement_date"), "2026-06-24, 2026-06-25"),
                setp(("P1", "pcf_date"), "2026-06-23, 2026-06-24")), NOT_PERFECT)
    attack(B, "BOTH gates: next-day pcf_id AND sibling OSIs", many(setp(("P1", "pcf_id"), "PCF-GRBO-20260624"), setp(("P1", "series_osi"), SIB_OSI)),
           GATES("GATE.DATE", "GATE.SERIES"))


# ============================================================================================ 6. P1.1 / P1.4 / P1.5
def section_p1_atoms():
    print("\n## 6. P1.1 identity, P1.4 terms, P1.5 structure")
    FUND = "Granite Ridge U.S. Small Cap Buffer ETF - October"
    for s, ex in ((FUND.replace(" - ", " – "), PERFECT), (FUND.replace(" - ", " — "), PERFECT), (FUND.replace("U.S.", "US"), PERFECT),
                  (FUND.upper(), PERFECT), ("GRBO Oct buffer", NOT_PERFECT), ("Granite Ridge U.S. Small Cap Buffer ETF", NOT_PERFECT),
                  ("Granite Ridge U.S. Small Cap Buffer ETF - November", NOT_PERFECT), (FUND + " (GRBO)", PERFECT),
                  ("Granite Ridge US Small Cap Buffer ETF - Oct", None)):
        attack(B, f"P1.fund {s!r}", setp(("P1", "fund"), s), ex)
    for s, ex in (("GRBO US", PERFECT), ("NYSE: GRBO", PERFECT), ("grbo", PERFECT), ("GRBN", NOT_PERFECT), ("GRBO.K", None)):
        attack(B, f"P1.ticker {s!r}", setp(("P1", "ticker"), s), ex)
    for s, ex in (("rd 2026 0623 007", PERFECT), ("RD-2026-0623-007 ", PERFECT), ("RD-2026-0623-007 (redeem)", PERFECT),
                  ("Order RD-2026-0623-007", None), ("RD-2026-0623-008", NOT_PERFECT)):
        attack(B, f"P1.order_id {s!r}", setp(("P1", "order_id"), s), ex)
    for s, ex in (("Harrowgate", None), ("Harrowgat Capital Markets LLC", PERFECT), ("Harrowgate Capital Markets", PERFECT),
                  ("Harrowgate Capital Markets, LLC", PERFECT), ("Harrowgate Capital Mkts LLC", PERFECT), ("HCM", None),
                  ("Harrowgate Capital Markets LLC (OCC CM 0829, account HCM-ETF-07)", PERFECT),
                  ("Harrowgate Capital Markets LLC - CM 0829 / HCM-ETF-07", PERFECT),
                  ("Kestrel Point Securities LLC", NOT_PERFECT), ("Kestrel Capital Markets LLC", NOT_PERFECT),
                  ("Capital Markets LLC", NOT_PERFECT), ("Harrowgate Capital", None), ("The AP (Harrowgate)", None)):
        attack(B, f"P1.authorized_participant {s!r}", setp(("P1", "authorized_participant"), s), ex)
    for s, ex in (("ex-clearing", PERFECT), ("Ex Clearing (OCC transfers)", PERFECT), ("bilateral / outside NSCC", PERFECT),
                  ("outside NSCC CNS", PERFECT), ("manual, ex-clearing", PERFECT), ("NSCC", NOT_PERFECT), ("nscc_messaged", NOT_PERFECT),
                  ("ex_clearing|nscc_messaged", NOT_PERFECT), ("NSCC CNS (not ex-clearing)", NOT_PERFECT), ("not ex-clearing", NOT_PERFECT),
                  ("through NSCC CNS, manual reconciliation", NOT_PERFECT), ("outside the CCP guaranty (NSCC)", NOT_PERFECT),
                  ("DTC", NOT_PERFECT), ("through the clearing house", NOT_PERFECT)):
        attack(B, f"P1.settlement_flow {s!r}", setp(("P1", "settlement_flow"), s), ex)
    attack(C, "clean: P1.settlement_flow 'NSCC CNS (not ex-clearing)'", setp(("P1", "settlement_flow"), "NSCC CNS (not ex-clearing)"), NOT_PERFECT)
    for k, v, ex in (("num_cus", "2", PERFECT), ("num_cus", "2 creation units", PERFECT), ("num_cus", 2.0, PERFECT), ("num_cus", 3, NOT_PERFECT),
                     ("cu_size", "50,000", PERFECT), ("cu_size", "50000 shares", PERFECT), ("cu_size", 25000, NOT_PERFECT),
                     ("total_shares", "100,000", PERFECT), ("total_shares", "100 000", None), ("total_shares", "100.000", None), ("total_shares", 50000, NOT_PERFECT),
                     ("nav_per_share", "30.5000", PERFECT), ("nav_per_share", "$30.50", PERFECT), ("nav_per_share", 30.42, NOT_PERFECT), ("nav_per_share", 30.5002, PERFECT),
                     ("redemption_value", "$3,050,000.00", PERFECT), ("redemption_value", "3.05m", NOT_PERFECT), ("redemption_value", 3050000.9, PERFECT),
                     ("redemption_value", 30500000, NOT_PERFECT), ("transaction_fee", "$500.00", PERFECT), ("transaction_fee", 5000, NOT_PERFECT)):
        attack(B, f"P1.{k} {v!r}", setp(("P1", k), v), ex)
    # the dead field: nothing reads P1.direction
    for v in ("create", "creation", "buy", "junk", None, ""):
        attack(B, f"P1.direction = {v!r} (the order is a REDEMPTION)", setp(("P1", "direction"), v), NOT_PERFECT, atoms=("P1.1", "P1.5"))
    attack(C, "clean: P1.direction = 'create'", setp(("P1", "direction"), "create"), NOT_PERFECT)
    # P1.5: placeholders
    for k in ("fund", "order_id", "trade_date", "settlement_date", "pcf_date", "num_cus", "settlement_flow"):
        attack(B, f"P1.5 key {k} = 'tbd' (placeholder)", setp(("P1", k), "tbd"), NOT_PERFECT, atoms=("P1.5",))
    attack(B, "P1 all P1.5 keys placeholders ('tbd', 0)",
           lambda m: m.update({"P1": {"fund": "tbd", "order_id": "tbd", "trade_date": "tbd", "settlement_date": "tbd", "pcf_date": "tbd", "num_cus": 0,
                                      "settlement_flow": "tbd"}}), lambda r: cp(r, "P1") < 0.2, atoms=("P1.5",))
    attack(B, "P1 right dates and series, everything else 'tbd'",
           lambda m: m["P1"].update({"fund": "tbd", "order_id": "tbd", "ticker": "tbd", "authorized_participant": "tbd", "num_cus": "tbd", "cu_size": "tbd",
                                     "total_shares": "tbd", "nav_per_share": "tbd", "redemption_value": "tbd", "transaction_fee": "tbd", "settlement_flow": "tbd",
                                     "pcf_id": "tbd"}), None, atoms=("P1.5",))
    attack(B, "P1.num_cus = 0 (not empty) satisfies the structure key", setp(("P1", "num_cus"), 0), NOT_PERFECT, atoms=("P1.4", "P1.5"))


# ============================================================================================ 7. STRUCTURE ATOMS
def section_structure():
    print("\n## 7. structure atoms C1.structure and D1.record")
    junk = [{"leg_id": x, "due_contracts": 1, "confirmed_contracts": 1, "tie": "x"} for x in ("a", "b", "c", "d")]
    attack(B, "C1.ledger = 4 junk-id rows (a,b,c,d) status 'x'", setp(("C1", "ledger"), junk), lambda r: gate(r, "GATE.FABRICATION"),
           atoms=("C1.structure", "E2.n_halluc"))
    jl = [{"leg_id": "L1", "due_contracts": 1, "confirmed_contracts": 1, "tie": "x"} for _ in range(4)]
    attack(B, "C1.ledger = 4 duplicate L1 junk rows", setp(("C1", "ledger"), jl), lambda r: cp(r, "C1") < 0.6, atoms=("C1.structure", "C1.match"))
    jl2 = [{"leg_id": "SHARES", "due_contracts": 0, "confirmed_contracts": 0, "tie": "?"} for _ in range(4)]
    attack(B, "C1.ledger = 4 duplicate SHARES junk rows", setp(("C1", "ledger"), jl2), lambda r: cp(r, "C1") < 0.6, atoms=("C1.structure",))
    attack(B, "C1.ledger = 4 junk rows keyed TOTAL/TOTALS/SUBTOTAL/NET (skip-listed ids dodge the fabrication scan)",
           setp(("C1", "ledger"), [{"leg_id": x, "due_contracts": 1, "confirmed_contracts": 1, "tie": "x"} for x in ("TOTAL", "TOTALS", "SUBTOTAL", "NET")]),
           lambda r: cp(r, "C1") < 0.6, atoms=("C1.structure", "E2.n_halluc"))
    attack(B, "C1.ledger = 4 empty-quantity L1..L4 rows with tie 'x'",
           setp(("C1", "ledger"), [{"leg_id": f"L{i}", "due_contracts": 0, "tie": "x"} for i in (1, 2, 3, 4)]), lambda r: cp(r, "C1") < 0.6, atoms=("C1.structure",))
    attack(B, "C1.ledger as dict keyed by leg id (a tie map)",
           lambda m: m["C1"].update({"ledger": {r["leg_id"]: {k: v for k, v in r.items() if k != "leg_id"} for r in base(B)["C1"]["ledger"]}}), None, atoms=("C1.structure", "C1.match"))
    attack(B, "C1.ledger rows keyed by OSI instead of leg_id (no leg_id)",
           lambda m: m["C1"].update({"ledger": [dict({"osi_identifier": GOLD_OSI[i]}, **{k: v for k, v in r.items() if k != "leg_id"})
                                                  for i, r in enumerate(base(B)["C1"]["ledger"][:4])] + [base(B)["C1"]["ledger"][4]]}), PERFECT)
    attack(B, "C1.ledger without the SHARES row", lambda m: m["C1"].update({"ledger": base(B)["C1"]["ledger"][:4]}), None, atoms=("C1.structure", "C1.match"))
    for lid in ("CASH_COMPONENT", "NET_CASH", "FEE", "SUMMARY", "OPTIONS"):
        attack(B, f"C1.ledger + a {lid} row (a cash / summary tie, not a leg)",
               lambda m, lid=lid: m["C1"]["ledger"].append({"leg_id": lid, "due_contracts": 8700.0, "confirmed_contracts": 8700.0, "tie": "match"}),
               NO_GATE("GATE.FABRICATION"), atoms=("E2.n_halluc",))
    for lid in ("SHARES_DELIVERY", "SHARES RECEIVED", "DTC SHARES", "SHARES-DTC", "shares leg"):
        def relabel(m, lid=lid):
            for r in m["C1"]["ledger"]:
                if r["leg_id"] == "SHARES":
                    r["leg_id"] = lid
        attack(B, f"C1.ledger: the share-delivery row labelled {lid!r} instead of 'SHARES'", relabel, PERFECT, atoms=("E2.n_halluc", "C1.match"))
    for lid in ("TOTAL", "CASH"):
        attack(B, f"C1.ledger + a {lid} row (skip-listed)",
               lambda m, lid=lid: m["C1"]["ledger"].append({"leg_id": lid, "due_contracts": 1, "confirmed_contracts": 1, "tie": "match"}), PERFECT)
    attack(B, "C1.ledger + a fabricated leg L5", lambda m: m["C1"]["ledger"].append({"leg_id": "L5", "due_contracts": 120, "confirmed_contracts": 120, "tie": "match"}),
           GATES("GATE.FABRICATION"))
    # D1.record
    attack(B, "D1 placeholders: remedy/escalate_to 'see above ok', numerics 0, offending_leg 'x' (decision HOLD)",
           lambda m: m["D1"].update({"offending_leg": "x", "remedy": "see above ok", "escalate_to": "see above ok", "due_contracts": 0, "confirmed_contracts": 0,
                                     "excess_contracts": 0, "excess_value": 0, "offending_series": None, "offending_reason": None}), lambda r: cp(r, "D1") < 0.5,
           atoms=("D1.decision", "D1.record"))
    attack(B, "D1 record only: HOLD + junk everywhere", lambda m: m.update({"D1": {"decision": "HOLD", "offending_leg": "n/a", "remedy": "see note above", "escalate_to": "see note above",
                                                                              "due_contracts": 0, "confirmed_contracts": 0, "excess_contracts": 0, "excess_value": 0}}),
           lambda r: cp(r, "D1") < 0.5, atoms=("D1.decision", "D1.record"))
    attack(C, "clean: D1 = SETTLE + remedy 'see above ok' + excess 0 only",
           lambda m: m.update({"D1": {"decision": "SETTLE", "remedy": "see above ok", "excess_contracts": 0}}), lambda r: cp(r, "D1") < 0.7,
           atoms=("D1.decision", "D1.localize", "D1.remedy", "D1.record"))
    attack(C, "clean: everything EMPTY except D1 = SETTLE + remedy 'see above ok' + excess 0",
           lambda m: m.update({"P1": {}, "E1": {}, "E2": {}, "C1": {}, "C2": {}, "C3": {}, "D2": {}, "D1": {"decision": "SETTLE", "remedy": "see above ok", "excess_contracts": 0}}),
           lambda r: r.case_gated < 0.2)
    attack(B, "D1 offending_leg 'none' on the break (record non-empty)", setp(("D1", "offending_leg"), "none"), NOT_PERFECT, atoms=("D1.localize", "D1.record"))
    attack(B, "D1.escalate_to 'n/a' (record prose test)", setp(("D1", "escalate_to"), "n/a"), NOT_PERFECT, atoms=("D1.record",))
    attack(B, "D1.remedy 'n/a' (record prose test)", setp(("D1", "remedy"), "n/a"), NOT_PERFECT, atoms=("D1.remedy", "D1.record"))
    attack(B, "D1.remedy 'see above' (2 words)", setp(("D1", "remedy"), "see above"), NOT_PERFECT, atoms=("D1.remedy", "D1.record"))
    attack(B, "D1.remedy 'see above ok' (3 words) only: the other fields carry the content", setp(("D1", "remedy"), "see above ok"), NOT_PERFECT,
           atoms=("D1.remedy", "D1.record"))
    attack(B, "D1.escalate_to 'see above ok' only", setp(("D1", "escalate_to"), "see above ok"), NOT_PERFECT, atoms=("D1.remedy", "D1.record"))
    attack(B, "D1.release_cash true + cancel_shares true with decision HOLD (the record's own switches say release)",
           lambda m: m["D1"].update({"release_cash": True, "cancel_shares": True}), NOT_PERFECT, atoms=("D1.decision", "D1.record"))
    attack(C, "clean: D1.release_cash false + cancel_shares false with decision SETTLE",
           lambda m: m["D1"].update({"release_cash": False, "cancel_shares": False}), NOT_PERFECT, atoms=("D1.decision", "D1.record"))


# ============================================================================================ 8. CASCADE
def section_cascade():
    print("\n## 8. cascade: which checkpoints a fired hard gate zeroes")
    for case in (B, C):
        t = "brk" if case == B else "cln"
        attack(case, f"{t}: GATE.DATE alone (pcf_date 06-24)", setp(("P1", "pcf_date"), "2026-06-24"),
               lambda r: gate(r, "GATE.DATE") and all(cp(r, k) == 0.0 for k in ("C1", "C2", "C3", "D1")) and abs(cp(r, "P1") - 13 / 18) < 1e-6
               and all(cp(r, k) == 1.0 for k in ("E1", "E2", "D2")))
        attack(case, f"{t}: GATE.SERIES alone (series_osi sibling)", setp(("P1", "series_osi"), SIB_OSI),
               lambda r: gate(r, "GATE.SERIES") and all(cp(r, k) == 0.0 for k in ("C1", "C2", "C3", "D1")) and abs(cp(r, "P1") - 13 / 18) < 1e-6
               and all(cp(r, k) == 1.0 for k in ("E1", "E2", "D2")))
        attack(case, f"{t}: BOTH gates", many(setp(("P1", "pcf_date"), "2026-06-24"), setp(("P1", "series_osi"), SIB_OSI)),
               lambda r: gate(r, "GATE.DATE") and gate(r, "GATE.SERIES") and all(cp(r, k) == 0.0 for k in ("C1", "C2", "C3", "D1"))
               and abs(cp(r, "P1") - 8 / 18) < 1e-6 and abs(r.case_gated - 0.3444) < 1e-3)
    attack(B, "GATE.DATE + SETTLE override on the break", many(setp(("P1", "pcf_date"), "2026-06-24"), setp(("D1", "decision"), "SETTLE")),
           lambda r: gate(r, "GATE.DATE") and gate(r, "GATE.SETTLE") and "settle_override_fired" in r.flags)
    attack(B, "GATE.DATE + fabricated P&L (D2 is not a gate dependent)", many(setp(("P1", "pcf_date"), "2026-06-24"),
           lambda m: m["D2"].update({"probe": {"label": "COMPUTED", "value": 7500.0, "derivation": "profit of 7,500.00 assuming the AP bought at NAV"}})),
           lambda r: gate(r, "GATE.FABRICATION") and gate(r, "GATE.DATE") and cp(r, "D2") == 0.0)
    attack(B, "a fired gate never RAISES a score: GATE.DATE + SETTLE answer", many(setp(("P1", "pcf_date"), "2026-06-24"), setp(("D1", "decision"), "SETTLE")),
           lambda r: r.case_gated <= 0.40 + 1e-9)
    print("\n## 9. robustness: malformed P1 and unknown fields (none may raise)")
    for v in ("see above", ["a", "b"], 5, None, True, [], {"x": 1}, "", [{"trade_date": "2026-06-23"}]):
        attack(B, f"P1 = {v!r}", lambda m, v=v: m.update({"P1": v}), lambda r: r.case_gated < 1.0)
    for k in ("trade_date", "settlement_date", "pcf_date", "series_expiry", "pcf_id", "series_osi", "fund", "num_cus", "settlement_flow"):
        for v in ({"value": "2026-06-23"}, ["2026-06-23"], True, 0, {}):
            attack(B, f"P1.{k} = {v!r}", setp(("P1", k), v), lambda r: True)
    attack(B, "P1.series_osi nested list [[osi]*4]", setp(("P1", "series_osi"), [GOLD_OSI]), lambda r: True)
    attack(B, "P1.series_osi = 5", setp(("P1", "series_osi"), 5), lambda r: True)
    attack(B, "P1.num_cus = NaN / P1.nav_per_share = Infinity", many(setp(("P1", "num_cus"), float("nan")), setp(("P1", "nav_per_share"), float("inf"))),
           lambda r: r.case_gated < 1.0)
    attack(B, "P1.pcf_id = '(' * 40000 (a degenerate completion): quadratic _idn regex, and the junk id is credited",
           setp(("P1", "pcf_id"), "(" * 40000), lambda r: False)
    attack(B, "C1.ledger[0].leg_id = 'L1' + '(' * 20000", lambda m: m["C1"]["ledger"][0].update({"leg_id": "L1" + "(" * 20000}), lambda r: True)
    attack(B, "E1.legs = 'see above' with series_osi missing", many(delp(("P1", "series_osi")), setp(("E1", "legs"), "see above")), lambda r: gate(r, "GATE.SERIES"))
    attack(B, "unknown fields in every section", lambda m: [m[k].update({"_note": "x", "foo": {"bar": [1, 2]}, "comment": "ok"}) for k in ("P1", "E1", "E2", "C1", "C2", "C3", "D1")], PERFECT)
    attack(B, "unknown fields in every row",
           lambda m: [r.update({"comment": "ok", "note": "x", "extra": 1}) for k, rows in (("E1", "legs"), ("E2", "confirmations"), ("E2", "positions"),
                                                                                       ("C1", "ledger"), ("C1", "position_check"), ("C2", "leg_values_per_cu"))
                      for r in m[k][rows]], PERFECT)
    attack(B, "unknown top-level sections (P0, X1, notes)", lambda m: m.update({"P0": {"a": 1}, "X1": [1], "notes": "free text"}), PERFECT)
    attack(C, "clean: unknown top-level sections", lambda m: m.update({"P0": {"a": 1}, "X1": [1], "notes": "free text"}), PERFECT)


def _line(prefix):
    for ln in build_packet(load_case(_p(B))).split("\n"):
        if ln.strip().startswith(prefix):
            return ln.strip()
    raise KeyError(prefix)


# ============================================================================================ 10. EXTRA
def section_extra():
    print("\n## 10. cross-surface: citations of the wrong PCF")
    sib_header = _line("pcf_id=PCF-GRBN-20260623")
    nd_header = _line("pcf_id=PCF-GRBO-20260624")
    attack(B, "E1.citation = the SIBLING PCF header line", setp(("E1", "citation"), {"document": "pcf", "locator": "PCF-GRBN-20260623, header", "verbatim": sib_header}),
           lambda r: cp(r, "E1") < 0.999, atoms=("E1.cite",))
    attack(B, "E1.citation = the NEXT-DAY PCF header line", setp(("E1", "citation"), {"document": "pcf", "locator": "PCF-GRBO-20260624, header", "verbatim": nd_header}),
           lambda r: cp(r, "E1") < 0.999, atoms=("E1.cite",))


# ============================================================================================ PINNABLE CHECKS
CHECKS_SRC = r'''
def checks():
    out = []
    GO = ["4IWM  260930C00002400", "4IWM  260930P00240000", "4IWM  260930P00204000", "4IWM  260930C00282000"]
    SO = ["4IWM  261030C00002350", "4IWM  261030P00235000", "4IWM  261030P00199750", "4IWM  261030C00276000"]
    P = lambda k, v: _set(("P1", k), v)
    mk = lambda v: orx.make(load_case(_p(_B)), v)
    np_ = lambda mut, c=_B: not _perfect(_run(c, mut))          # a wrong answer must not be perfect
    gt = lambda mut, g, c=_B: _gate(_run(c, mut), g)
    drop = lambda k: (lambda m: m["P1"].pop(k, None))
    row = lambda lid, **kw: dict({"leg_id": lid, "due_contracts": 1, "confirmed_contracts": 1, "tie": "x"}, **kw)

    # ---- 1. the hard gates fire on evidence, not on notation or absence ----
    for d in ("Jun 23 2026", "23-Jun-2026", "23/06/2026", "2026.06.23", "Tuesday, June 23, 2026", "June 23rd, 2026", "6/23/26"):
        out.append((f"trade_date {d!r}: perfect", lambda d=d: _perfect(_run(_B, P("trade_date", d)))))
    for d in ("Sep 30 2026", "30-Sep-2026", "30/09/2026"):
        out.append((f"series_expiry {d!r}: perfect", lambda d=d: _perfect(_run(_B, P("series_expiry", d)))))
    for k, g in (("pcf_date", "GATE.DATE"), ("trade_date", "GATE.DATE"), ("settlement_date", "GATE.DATE"), ("series_expiry", "GATE.SERIES")):
        out.append((f"P1.{k} missing: no {g}", lambda k=k, g=g: not gt(drop(k), g)))
    out.append(("pcf_date = publication date 2026-06-22, id right: no GATE.DATE", lambda: not gt(P("pcf_date", "2026-06-22"), "GATE.DATE")))
    for nm, v in (("{leg_id, osi} objects", [{"leg_id": f"L{i+1}", "osi": o} for i, o in enumerate(GO)]),
                  ("a dict keyed by leg id", {f"L{i+1}": o for i, o in enumerate(GO)}),
                  ("'L1: <osi>' strings", [f"L{i+1}: {o}" for i, o in enumerate(GO)])):
        out.append((f"series_osi as {nm}: no GATE.SERIES", lambda v=v: not gt(P("series_osi", v), "GATE.SERIES")))

    # ---- 2. the PCF of record is verified, a hedge is not a pin, no dead fields ----
    out.append(("pcf_id = the sibling's PCF-GRBN-20260623: not perfect", lambda: np_(P("pcf_id", "PCF-GRBN-20260623"))))
    out.append(("sibling pcf_id + ticker + fund, own series pins: GATE.SERIES",
                lambda: gt(lambda m: m["P1"].update({"pcf_id": "PCF-GRBN-20260623", "ticker": "GRBN", "fund": "Granite Ridge U.S. Small Cap Buffer ETF - November"}), "GATE.SERIES")))
    out.append(("invented pcf_id PCF-XYZZ-99999999: not perfect", lambda: np_(P("pcf_id", "PCF-XYZZ-99999999"))))
    for s in ("PCF-GRBO-20260624 v2", "PCF-GRBO-20260624, published 2026-06-23 21:30 ET", "GRBO 24 Jun 2026 PCF"):
        out.append((f"pcf_id next-day {s!r}: GATE.DATE", lambda s=s: gt(P("pcf_id", s), "GATE.DATE")))
    for k, v in (("pcf_id", "PCF-GRBO-20260623 / PCF-GRBO-20260624"), ("trade_date", "2026-06-23 or 2026-06-24"), ("pcf_date", "2026-06-23 / 2026-06-24"),
                 ("series_expiry", "2026-09-30 or 2026-10-30"), ("direction", "create"), ("settlement_flow", "NSCC CNS (not ex-clearing)"),
                 ("settlement_flow", "not ex-clearing"), ("settlement_flow", "ex_clearing|nscc_messaged")):
        out.append((f"P1.{k} = {v!r}: not perfect", lambda k=k, v=v: np_(P(k, v))))

    # ---- 3. pins are checked against what the model actually read ----
    out.append(("sibling basket tied under gold pins: GATE.SERIES",
                lambda: gt(lambda m: (m.update(mk("series_slip")), m["P1"].update({"series_osi": GO, "series_expiry": "2026-09-30", "pcf_id": "PCF-GRBO-20260623"})), "GATE.SERIES")))
    out.append(("E1.legs read from the GRBN PCF under gold pins: GATE.SERIES", lambda: gt(lambda m: m["E1"].update({"legs": mk("series_slip")["E1"]["legs"]}), "GATE.SERIES")))
    out.append(("next-day PCF read (cash est 4,620) under honest pins: GATE.DATE",
                lambda: gt(lambda m: (m.update(mk("date_slip")), m["P1"].update({"pcf_id": "PCF-GRBO-20260623", "pcf_date": "2026-06-23"})), "GATE.DATE")))
    out.append(("series_osi as one string naming the sibling: GATE.SERIES", lambda: gt(P("series_osi", ", ".join(SO)), "GATE.SERIES")))

    # ---- 4. structure atoms, the record, identity ----
    for lid in ("CASH_COMPONENT", "NET_CASH", "SUMMARY", "OPTIONS"):
        out.append((f"ledger + a {lid} row: no GATE.FABRICATION", lambda lid=lid: not gt(lambda m: m["C1"]["ledger"].append(row(lid, due_contracts=8700.0, confirmed_contracts=8700.0, tie="match")), "GATE.FABRICATION")))
    for lid in ("SHARES_DELIVERY", "SHARES RECEIVED", "DTC SHARES"):
        out.append((f"share-delivery ledger row labelled {lid!r}: perfect",
                    lambda lid=lid: _perfect(_run(_B, lambda m: [r.update({"leg_id": lid}) for r in m["C1"]["ledger"] if r["leg_id"] == "SHARES"]))))
    out.append(("4 duplicate junk L1 rows: C1.structure unmet (C1 < 0.6)", lambda: _cp(_run(_B, _set(("C1", "ledger"), [row("L1")] * 4)), "C1") < 0.6))
    out.append(("D1.remedy 'see above ok' is no record: D1 < 1", lambda: _cp(_run(_B, _set(("D1", "remedy"), "see above ok")), "D1") < 0.999))
    out.append(("HOLD + release_cash/cancel_shares true: not perfect", lambda: np_(lambda m: m["D1"].update({"release_cash": True, "cancel_shares": True}))))
    out.append(("clean SETTLE + release_cash/cancel_shares false: not perfect", lambda: np_(lambda m: m["D1"].update({"release_cash": False, "cancel_shares": False}), _C)))
    out.append(("fund with an en dash: perfect", lambda: _perfect(_run(_B, P("fund", "Granite Ridge U.S. Small Cap Buffer ETF – October")))))
    out.append(("AP with its OCC account suffix: perfect", lambda: _perfect(_run(_B, P("authorized_participant", "Harrowgate Capital Markets LLC (OCC CM 0829, account HCM-ETF-07)")))))
    out.append(("AP 'Capital Markets LLC': not perfect", lambda: np_(P("authorized_participant", "Capital Markets LLC"))))
    hdr = next(l.strip() for l in build_packet(load_case(_p(_B))).split("\n") if l.strip().startswith("pcf_id=PCF-GRBN-20260623"))
    out.append(("E1.cite quoting the sibling PCF header: E1 < 1",
                lambda: _cp(_run(_B, _set(("E1", "citation"), {"document": "pcf", "locator": "PCF-GRBN-20260623", "verbatim": hdr})), "E1") < 0.999))

    # ---- 5. standing regressions: what holds today and must keep holding ----
    out.append(("next-day pcf_id: GATE.DATE zeroes C1-D1, P1 keeps 13/18, E1/E2/D2 intact",
                lambda: (lambda r: _gate(r, "GATE.DATE") and all(_cp(r, k) == 0.0 for k in ("C1", "C2", "C3", "D1")) and abs(_cp(r, "P1") - 13 / 18) < 1e-6
                         and all(_cp(r, k) == 1.0 for k in ("E1", "E2", "D2")))(_run(_B, P("pcf_id", "PCF-GRBO-20260624")))))
    out.append(("both gates: P1 = 8/18, same zeroing",
                lambda: (lambda r: _gate(r, "GATE.DATE") and _gate(r, "GATE.SERIES") and abs(_cp(r, "P1") - 8 / 18) < 1e-6
                         and all(_cp(r, k) == 0.0 for k in ("C1", "C2", "C3", "D1")))(_run(_B, lambda m: m["P1"].update({"pcf_id": "PCF-GRBO-20260624", "series_osi": SO})))))
    out.append(("sibling OSIs / expiry 2026-10-30 / three of four: GATE.SERIES",
                lambda: all(gt(mu, "GATE.SERIES") for mu in (P("series_osi", SO), P("series_expiry", "2026-10-30"), P("series_osi", GO[:3])))))
    out.append(("dates a day late / swapped / T+2 / T+0: GATE.DATE",
                lambda: all(gt(mu, "GATE.DATE") for mu in (lambda m: m["P1"].update({"trade_date": "2026-06-24", "settlement_date": "2026-06-25", "pcf_date": "2026-06-24"}),
                                                           lambda m: m["P1"].update({"trade_date": "2026-06-24", "settlement_date": "2026-06-23"}),
                                                           P("settlement_date", "2026-06-25"), P("settlement_date", "2026-06-23")))))
    out.append(("a fabricated leg row L5 in the ledger: GATE.FABRICATION", lambda: gt(lambda m: m["C1"]["ledger"].append(row("L5", tie="match")), "GATE.FABRICATION")))
    out.append(("right notations and pcf_id spellings: perfect",
                lambda: all(_perfect(_run(_B, mu)) for mu in (P("trade_date", "2026-06-23T00:00:00Z"), P("trade_date", "06/23/2026"), P("trade_date", "23 June 2026"), P("trade_date", "20260623"),
                                                              P("pcf_id", "PCF GRBO 20260623"), P("pcf_id", "PCF-GRBO-20260623 (basket of record)"),
                                                              P("series_osi", [o.replace("  ", " ").lower() for o in GO])))))
    out.append(("P1 as a string: scores without raising", lambda: _run(_B, lambda m: m.update({"P1": "see above"})).case_gated < 1.0))
    out.append(("unknown fields in every section: perfect", lambda: _perfect(_run(_B, lambda m: [m[k].update({"_note": "x"}) for k in ("P1", "E1", "E2", "C1", "C2", "C3", "D1")]))))
    return out
'''


def build_checks():
    def _run_(case, mutate):
        m = orx.oracle(load_case(_p(case)))
        mutate(m)
        r, _ = run_case(_p(case), model_output=m)
        return r
    ns = {"orx": orx, "load_case": load_case, "_p": _p, "_B": B, "_C": C, "_run": _run_, "_set": setp, "_gate": gate, "_cp": cp,
          "_perfect": perfect, "build_packet": build_packet}
    exec(CHECKS_SRC, ns)
    return ns["checks"]()


def run_checks():
    fails = []
    items = build_checks()
    for name, fn in items:
        try:
            ok = bool(fn())
        except Exception as e:
            ok = False
            name = f"{name} [raised {type(e).__name__}: {e}]"
        print(("  PASS  " if ok else "  FAIL  ") + name)
        if not ok:
            fails.append(name)
    print(f"\n{len(items) - len(fails)} passed (behaviour already correct), {len(fails)} failed (a reproduced defect, or a regression)")


def main():
    global FILTER
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")     # the en dash in fund-name attacks, on a cp1252 console
    except Exception:
        pass
    args = sys.argv[1:]
    if args and args[0] == "--checks":
        run_checks()
        return
    FILTER = args[0] if args else ""
    section_dates()
    section_absence()
    section_pcf_id()
    section_series()
    section_dodges()
    section_p1_atoms()
    section_structure()
    section_cascade()
    section_extra()
    print("\n" + "=" * 100)
    cnt = {k: sum(1 for r in ROWS if r[1] == k) for k in ("FINDING", "HELD", "INFO", "CRASH")}
    print(f"attacks run: {len(ROWS)} | FINDING (grader did not behave as expected): {cnt['FINDING']} | HELD (grader held): {cnt['HELD']} "
          f"| INFO (no clear verdict): {cnt['INFO']} | CRASH: {cnt['CRASH']}")


if __name__ == "__main__":
    main()

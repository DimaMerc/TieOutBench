"""
scratch_attacker4.py - eval #8 gaming review, attacker 4: EXTRACTION AND THE PER-LEG TIE.

Surface: E1.legs/cash/recap/cite, E2.confirms/positions/nav/shares, C1.due/match/positions/exceptions/structure
and the penalties E1.n_omit, E2.n_halluc, C1.n_recap_blind. Grader: harness/suites/options_redemption.py.

Run from the repo root:   python outputs/eval8-live/gaming-review/scratch_attacker4.py
Prints ONE result line per attack. Every attack starts from the case oracle (a perfect 1.000/AllPass answer)
and mutates only the fields named in the label. Nothing in the repo is modified.

kind    EXPLOIT  = a wrong (or weaker) answer is credited more than it should be
        FALSEPOS = a right answer in a legitimate alternative form is penalised or gated
        HELD     = the attack should fail; the grader is expected to hold
        CONTROL  = a legitimate form that the grader must ACCEPT (positive control for the fixes)
verdict REPRODUCED = the grader misbehaved as the finding says; NOT-REPRODUCED = it did not
        HELD = the attack failed (the grader held); ACCEPTED = the control was credited;
        UNEXPECTED = a HELD attack got through or a CONTROL was rejected (a regression)
"""
import copy
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
sys.path.insert(0, ROOT)
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from harness import suites                                    # noqa: E402
from harness.graders import grade                              # noqa: E402
from harness.live_options_redemption import build_packet       # noqa: E402
from harness.rubric import load_case, load_rubric, materialize, rubric_path_for   # noqa: E402
from harness.scoring import score                              # noqa: E402
from harness.suites import options_redemption as orx           # noqa: E402

B = os.path.join(ROOT, "cases", "grbo-redeem-2026.case.yaml")
C = os.path.join(ROOT, "cases", "grbo-redeem-2026-clean.case.yaml")
OSI = {"L1": "4IWM  260930C00002400", "L2": "4IWM  260930P00240000",
       "L3": "4IWM  260930P00204000", "L4": "4IWM  260930C00282000"}
DESC = {"L1": "long call 2.40", "L2": "long put 240", "L3": "short put 204", "L4": "short call 282"}
_CACHE = {}


# ---------------------------------------------------------------- engine (same path as harness.run_case, plus atom verdicts)
def _load(path):
    if path not in _CACHE:
        case = load_case(path)
        _CACHE[path] = (case, load_rubric(rubric_path_for(case)))
    return _CACHE[path]


def grade_detail(path, model):
    case, rubric = _load(path)
    suite = suites.for_case(case)
    atoms = materialize(rubric, case)
    gold = dict(case["gold"])
    gold["manifest"] = case.get("manifest", {})
    gold["_snapshot"] = case.get("snapshot")
    gold["_claims"] = case.get("claims")
    gold["_documents"] = case.get("documents")
    gold["_case"] = case
    verdicts, rg = grade(atoms, model, gold, rubric, suite)
    res = score(atoms, verdicts, rg, rubric, case_id=case["case_id"], refusal_cp=suite.REFUSAL_CP)
    return res, verdicts


def oracle(path):
    return orx.oracle(copy.deepcopy(_load(path)[0]))


def met(v, a):
    return v[a].met >= 0.999


def gate(res, g):
    return g in res.fired_gates


def perfect(res):
    return res.allpass == 1 and abs(res.case_gated - 1.0) < 1e-6 and not res.fired_gates


def cps(res, *ks):
    return " ".join(f"{k}={res.checkpoints[k]['score_gated']:.3f}" for k in ks)


# ---------------------------------------------------------------- mutators
def rows(m, sec, key, sub=None):
    return (m[sec][sub] if sub else m[sec])[key]


def row_set(sec, key, leg, sub=None, **kw):
    def mut(m):
        for r in rows(m, sec, key, sub):
            if r.get("leg_id") == leg:
                r.update(kw)
    return mut


def each_set(sec, key, sub=None, **kw):
    def mut(m):
        for r in rows(m, sec, key, sub):
            r.update(kw)
    return mut


def set_path(path, value):
    def mut(m):
        cur = m
        for k in path[:-1]:
            cur = cur.setdefault(k, {})
        cur[path[-1]] = value
    return mut


def chain(*fs):
    def mut(m):
        for f in fs:
            f(m)
    return mut


def tie_all(match_text, brk="quantity_mismatch"):
    def mut(m):
        for r in m["C1"]["ledger"]:
            r["tie"] = brk if r["leg_id"] == "L2" else match_text
    return mut


def rekey_ledger(fn):
    """re-key the four leg rows of the C1 ledger (SHARES untouched); the OSI is added as a field"""
    def mut(m):
        for r in m["C1"]["ledger"]:
            if r["leg_id"] in OSI:
                r["osi_identifier"] = OSI[r["leg_id"]]
                r["leg_id"] = fn(r["leg_id"])
    return mut


def rename_shares(name):
    def mut(m):
        for r in m["C1"]["ledger"]:
            if r["leg_id"] == "SHARES":
                r["leg_id"] = name
    return mut


def as_map(sec, key, sub=None):
    def mut(m):
        c = m[sec][sub] if sub else m[sec]
        c[key] = {r["leg_id"]: {k: v for k, v in r.items() if k != "leg_id"} for r in c[key]}
    return mut


def append(sec, key, row, sub=None):
    def mut(m):
        rows(m, sec, key, sub).append(copy.deepcopy(row))
    return mut


def packet_line(prefix, case_path=B, contains=None, excludes=None):
    for ln in build_packet(_load(case_path)[0]).splitlines():
        s = ln.strip()
        if s.startswith(prefix) and (contains is None or contains in s) and (excludes is None or excludes not in s):
            return s
    raise KeyError(prefix)


def cite(doc, verbatim):
    return set_path(("E1", "citation"), {"document": doc, "locator": "x", "verbatim": verbatim})


H_REC = packet_line("pcf_id=PCF-GRBO-20260623")
H_NXT = packet_line("pcf_id=PCF-GRBO-20260624")
H_SIB = packet_line("pcf_id=PCF-GRBN-20260623")
L2_REC = packet_line("leg_id=L2", contains="exercise_style")
L2_SIB = packet_line("leg_id=L2", contains="261030P")
L2_OCC = packet_line("transfer_id=OCC-TX-260623-41108")

# ---------------------------------------------------------------- the attack list
ATTACKS = []


def A(aid, kind, path, label, mut, bad):
    ATTACKS.append((aid, kind, path, label, mut, bad))


# ===== T: tie vocabulary (C1.match, C1.positions, C1.n_recap_blind) =====
A("T1", "EXPLOIT", B, "L2 ledger tie='series_mismatch' (true cause: quantity); confirmed=12000", row_set("C1", "ledger", "L2", tie="series_mismatch"), lambda r, v: met(v, "C1.match"))
A("T2", "EXPLOIT", B, "L2 ledger tie='side_mismatch'", row_set("C1", "ledger", "L2", tie="side_mismatch"), lambda r, v: met(v, "C1.match"))
A("T3", "EXPLOIT", B, "L2 tie='match (contracts agree)', confirmed=12000 (leg marked match)", row_set("C1", "ledger", "L2", tie="match (contracts agree)"), lambda r, v: met(v, "C1.match") and not met(v, "C1.n_recap_blind"))
A("T4", "EXPLOIT", B, "L2 tie=\"matches the recap's 120 contracts\", confirmed=12000", row_set("C1", "ledger", "L2", tie="matches the recap's 120 contracts"), lambda r, v: met(v, "C1.match") and not met(v, "C1.n_recap_blind"))


def _blind_evade(m):
    for r in m["E2"]["confirmations"]:
        if r["leg_id"] == "L2":
            r["quantity"] = 120
    for r in m["E2"]["positions"]:
        if r["leg_id"] == "L2":
            r.update(transferred_out=120, position_current=23880)
    for r in m["C1"]["position_check"]:
        if r["leg_id"] == "L2":
            r.update(actual_current=23880, tie="match")
    for r in m["C1"]["ledger"]:
        if r["leg_id"] == "L2":
            r.update(tie="match (contracts agree)", confirmed_contracts="12,000 (keyed) / 120 (recap)")
    m["C1"]["exceptions"] = []


A("T5", "EXPLOIT", B, "recap adopted in E2/C1 (L2=120, no exception); ledger L2 tie='match (contracts agree)', confirmed='12,000 (keyed) / 120 (recap)'", _blind_evade,
  lambda r, v: met(v, "C1.match") and not met(v, "C1.n_recap_blind"))


def _blind_penalised(m):
    _blind_evade(m)
    row_set("C1", "ledger", "L2", tie="match", confirmed_contracts=120)(m)


A("T5b", "HELD", B, "the same recap-adopting answer but L2 tie='match', confirmed=120 -> recap-blind fires (compare T5)", _blind_penalised, lambda r, v: not met(v, "C1.n_recap_blind"))
for aid, txt in (("T6", "quantity matches"), ("T7", "match - 120 contracts confirmed"), ("T8", "OK (series/side/qty)"),
                 ("T9", "confirmed"), ("T10", "reconciled"), ("T11", "✓"), ("T12", "no break")):
    A(aid, "FALSEPOS", B, f"correct answer, every tying leg's tie written {txt!r}", tie_all(txt), lambda r, v: not met(v, "C1.match"))
A("T13", "FALSEPOS", B, "correct answer, L2 (the break) tie written 'does not tie'", row_set("C1", "ledger", "L2", tie="does not tie"), lambda r, v: not met(v, "C1.match"))
A("T14", "FALSEPOS", B, "correct answer, L2 (the break) tie written 'unmatched'", row_set("C1", "ledger", "L2", tie="unmatched"), lambda r, v: not met(v, "C1.match"))
A("T15", "FALSEPOS", B, "correct break on L2 written 'not ok': read as 'match' -> recap-blind penalty", row_set("C1", "ledger", "L2", tie="not ok"), lambda r, v: met(v, "C1.n_recap_blind"))
A("T16", "FALSEPOS", B, "position_check L1 tie='quantity matches' (23,880 = 23,880)", row_set("C1", "position_check", "L1", tie="quantity matches"), lambda r, v: not met(v, "C1.positions"))
A("T17", "HELD", B, "L2 tie='match (120 per recap)' -> recap-blind must fire", row_set("C1", "ledger", "L2", tie="match (120 per recap)"), lambda r, v: not met(v, "C1.n_recap_blind"))
A("T18", "HELD", B, "L2 tie='ties to recap' -> recap-blind must fire", row_set("C1", "ledger", "L2", tie="ties to recap"), lambda r, v: not met(v, "C1.n_recap_blind"))
A("T19", "HELD", B, "L2 confirmed_contracts=120 (the recap's number) -> recap-blind must fire", row_set("C1", "ledger", "L2", confirmed_contracts=120), lambda r, v: not met(v, "C1.n_recap_blind"))


def _dup_hedge(m):
    r = copy.deepcopy([x for x in m["C1"]["ledger"] if x["leg_id"] == "L2"][0])
    r.update(tie="match", confirmed_contracts=120)
    m["C1"]["ledger"].append(r)


A("T20", "HELD", B, "duplicate L2 rows [quantity_mismatch@12000, match@120] (hedge)", _dup_hedge, lambda r, v: not met(v, "C1.n_recap_blind"))
A("T21", "HELD", B, "right tie statuses, quantities null on every row", chain(each_set("C1", "ledger", due_contracts=None, confirmed_contracts=None)), lambda r, v: met(v, "C1.match"))
A("T22", "HELD", B, "L2 tie='missing' (wrong family) not credited", row_set("C1", "ledger", "L2", tie="missing"), lambda r, v: met(v, "C1.match"))
A("T23", "HELD", B, "position_check L2 tie='match' with actual_current=12000", row_set("C1", "position_check", "L2", tie="match"), lambda r, v: met(v, "C1.positions"))
A("T24", "HELD", B, "ledger L2 due=12000 confirmed=12000 tie=quantity_mismatch", row_set("C1", "ledger", "L2", due_contracts=12000), lambda r, v: met(v, "C1.match"))
A("T25", "CONTROL", B, "ledger rows in reverse order / extra TOTAL and CASH rows", chain(lambda m: m["C1"]["ledger"].reverse(), append("C1", "ledger", {"leg_id": "TOTAL", "due_contracts": 480, "confirmed_contracts": 12360, "tie": "quantity_mismatch"}),
                                                              append("C1", "ledger", {"leg_id": "CASH", "due_contracts": 9200, "confirmed_contracts": 9200, "tie": "match"})), lambda r, v: not perfect(r))

# ===== K: row keying and the fabricated-row detector (E2.n_halluc, E1.n_omit) =====
for aid, label, fn in (("K1", "'L2 - <OSI>' (osi_identifier field is exact)", lambda l: f"{l} - {OSI[l]}"),
                       ("K2", "'long put 240'", lambda l: DESC[l]),
                       ("K3", "'Leg 2'", lambda l: f"Leg {l[1]}")):
    A(aid, "FALSEPOS", B, f"correct answer, C1 ledger legs keyed {label}", rekey_ledger(fn), lambda r, v: gate(r, "GATE.FABRICATION"))
for aid, nm in (("K4", "share_receipt"), ("K5", "DTC shares"), ("K6", "Shares received"), ("K7", "Share delivery"), ("K8", "Redeemed shares")):
    A(aid, "FALSEPOS", B, f"correct answer, C1 ledger SHARES row named {nm!r}", rename_shares(nm), lambda r, v: gate(r, "GATE.FABRICATION"))
A("K9", "FALSEPOS", B, "correct answer + a 'SUM' row in C2.leg_values_per_cu", append("C2", "leg_values_per_cu", {"leg_id": "SUM", "value": 1520400.0}), lambda r, v: gate(r, "GATE.FABRICATION"))
A("K10", "FALSEPOS", B, "correct answer + an 'All legs' row in E2.positions", append("E2", "positions", {"leg_id": "All legs", "position_prior": 0, "transferred_out": 12360, "position_current": 0}), lambda r, v: gate(r, "GATE.FABRICATION"))
A("K11", "FALSEPOS", B, "correct answer + a 'Total contracts' row in E2.confirmations", append("E2", "confirmations", {"leg_id": "Total contracts", "quantity": 12360}), lambda r, v: gate(r, "GATE.FABRICATION"))
_CORR = {"leg_id": "L2", "osi_identifier": OSI["L2"], "quantity": 11880, "position_type": "long", "from_account": "CM 0829 / HCM-ETF-07",
         "to_account": "CM 0471 / GRBO-FND-01", "status": "ACCEPTED", "effective_date": "2026-06-24"}
A("K12", "EXPLOIT", B, "an INVENTED corrective L2 transfer confirmation (11,880 back to the fund), no transfer_id", append("E2", "confirmations", _CORR), lambda r, v: not met(v, "E2.n_halluc"))
A("K12b", "HELD", B, "the same invented corrective confirmation WITH an invented transfer_id -> E2.n_halluc fires (compare K12)", append("E2", "confirmations", dict(_CORR, transfer_id="OCC-TX-260624-50001")), lambda r, v: not met(v, "E2.n_halluc"))
A("K13", "EXPLOIT", B, "an invented SHARES position row and an invented CASH leg in E1.legs", chain(append("E2", "positions", {"leg_id": "SHARES", "position_prior": 99999, "transferred_out": 99999, "position_current": 0}),
                                                                                        append("E1", "legs", {"leg_id": "CASH", "osi_identifier": "x", "strike": 1})), lambda r, v: not gate(r, "GATE.FABRICATION"))
A("K14", "EXPLOIT", B, "an invented L5 row in C1.position_check, C1.exceptions and E2.nav.marks", chain(append("C1", "position_check", {"leg_id": "L5", "expected_current": 1, "actual_current": 2, "tie": "match"}),
                                                                                                   append("C1", "exceptions", {"leg_id": "L5", "type": "info", "detail": "invented"}),
                                                                                                   lambda m: m["E2"]["nav"]["marks"].update({"L5": 1.0})), lambda r, v: not gate(r, "GATE.FABRICATION"))
A("K15", "EXPLOIT", B, "L3 dropped from E1.legs replaced by a stub row {'leg_id':'L3'} (omission penalty dodged)", lambda m: m["E1"].update(legs=[({"leg_id": "L3"} if x["leg_id"] == "L3" else x) for x in m["E1"]["legs"]]), lambda r, v: not met(v, "E1.n_omit"))
A("K16", "HELD", B, "L3 dropped from E1.legs -> E1.n_omit must fire", lambda m: m["E1"].update(legs=[x for x in m["E1"]["legs"] if x["leg_id"] != "L3"]), lambda r, v: not met(v, "E1.n_omit"))
A("K17", "HELD", B, "an invented L5 leg in E1.legs -> E2.n_halluc must fire", append("E1", "legs", {"leg_id": "L5", "osi_identifier": "4IWM  260930P00200000", "strike": 200}), lambda r, v: not met(v, "E2.n_halluc"))
A("K18", "HELD", B, "a confirmation transfer_id typo ('...-4108') is a fabricated line", row_set("E2", "confirmations", "L2", transfer_id="OCC-TX-260623-4108"), lambda r, v: not met(v, "E2.n_halluc"))
for aid, nm in (("K19", "share_leg"), ("K20", "GRBO shares"), ("K21", "ETF shares"), ("K22", "Shares (DTC FOP)")):
    A(aid, "CONTROL", B, f"SHARES row named {nm!r} is accepted", rename_shares(nm), lambda r, v: not perfect(r))
A("K24", "FALSEPOS", B, "correct answer, every row collection returned as a map keyed by leg id: C1.ledger", as_map("C1", "ledger"), lambda r, v: not met(v, "C1.match"))
A("K25", "FALSEPOS", B, "correct answer, E2.positions returned as a map keyed by leg id", as_map("E2", "positions"), lambda r, v: not met(v, "E2.positions"))
A("K26", "FALSEPOS", B, "correct answer, E2.nav.marks as a DICT keyed by OSI (a LIST keyed by OSI is accepted)", set_path(("E2", "nav", "marks"), {OSI[k]: v for k, v in {"L1": 254.9, "L2": 3.95, "L3": 0.8, "L4": 4.65}.items()}), lambda r, v: not met(v, "E2.nav"))
A("K27", "FALSEPOS", B, "correct answer, E2.nav.marks as a dict of {mark: x} objects", set_path(("E2", "nav", "marks"), {k: {"mark": v} for k, v in {"L1": 254.9, "L2": 3.95, "L3": 0.8, "L4": 4.65}.items()}), lambda r, v: not met(v, "E2.nav"))

# ===== E: extraction =====
A("E1", "EXPLOIT", B, "E1.cite = the NEXT-DAY PCF header (PCF-GRBO-20260624, the date trap)", cite("pcf", H_NXT), lambda r, v: met(v, "E1.cite"))
A("E2", "EXPLOIT", B, "E1.cite = the SIBLING GRBN PCF header (wrong fund)", cite("pcf", H_SIB), lambda r, v: met(v, "E1.cite"))
A("E3", "EXPLOIT", B, "E1.cite = two words 'Granite Ridge'", cite("pcf", "Granite Ridge"), lambda r, v: met(v, "E1.cite"))
A("E4", "EXPLOIT", B, "E1.cite = 'put_or_call=Put  strike=240.0' (two fields, no leg or OSI)", cite("pcf", "put_or_call=Put  strike=240.0"), lambda r, v: met(v, "E1.cite"))
A("E5", "EXPLOIT", B, "E1.cite = GRBN L2 line ... 'multiplier=100  exercise_style=European'", cite("pcf", L2_SIB + " ... multiplier=100  exercise_style=European"), lambda r, v: met(v, "E1.cite"))
A("E6", "HELD", B, "E1.cite = the GRBN L2 line alone", cite("pcf", L2_SIB), lambda r, v: met(v, "E1.cite"))
A("E7", "HELD", B, "E1.cite = the OCC confirmation line (document pcf)", cite("pcf", L2_OCC), lambda r, v: met(v, "E1.cite"))
A("E8", "HELD", B, "E1.cite = a paraphrase not in the packet", cite("pcf", "The long put at 240 with 60 contracts per creation unit, European style"), lambda r, v: met(v, "E1.cite"))
A("E9", "HELD", B, "E1.cite = true L2 line + trailing text not in the packet", cite("pcf", L2_REC + " (buffer top, per PCF)"), lambda r, v: met(v, "E1.cite"))
A("E10", "CONTROL", B, "E1.cite = true L2 line with the OSI double space collapsed (must be credited)", cite("pcf", L2_REC.replace("  ", " ")), lambda r, v: not met(v, "E1.cite"))
A("E11", "FALSEPOS", B, "E1.cite document = 'PCF-GRBO-20260623' (the PCF id) with the true L2 line", cite("PCF-GRBO-20260623", L2_REC), lambda r, v: not met(v, "E1.cite"))
for aid, s in (("E12", "non-European"), ("E13", "American|European"), ("E14", "American, not European")):
    A(aid, "EXPLOIT", B, f"E1.legs exercise_style={s!r} on all four legs", each_set("E1", "legs", exercise_style=s), lambda r, v: met(v, "E1.legs"))
A("E15", "HELD", B, "E1.legs exercise_style='American' on all four legs", each_set("E1", "legs", exercise_style="American"), lambda r, v: met(v, "E1.legs"))
A("E16", "FALSEPOS", B, "correct answer, exercise_style='EU' (or missing) on all legs", each_set("E1", "legs", exercise_style="EU"), lambda r, v: not met(v, "E1.legs"))
A("E17", "FALSEPOS", B, "correct answer, expiry written '30/09/2026' (dd/mm/yyyy) on all legs", each_set("E1", "legs", expiry="30/09/2026"), lambda r, v: not met(v, "E1.legs"))


def _p1_dmy(m):
    m["P1"].update(trade_date="23/06/2026", settlement_date="24/06/2026", pcf_date="23/06/2026")


A("E18", "FALSEPOS", B, "correct answer, P1 trade/settlement/pcf dates written dd/mm/yyyy (OUTSIDE this surface; same _date helper) -> GATE.DATE", _p1_dmy, lambda r, v: gate(r, "GATE.DATE"))
A("E19", "EXPLOIT", B, "E1.recap per-leg status_claimed='NOT TRANSFERRED' (recap says TRANSFERRED)", each_set("E1", "legs", "recap", status_claimed="NOT TRANSFERRED"), lambda r, v: met(v, "E1.recap"))
A("E20", "EXPLOIT", B, "E1.recap status_claimed='NOT READY TO SETTLE' (recap says READY TO SETTLE)", set_path(("E1", "recap", "status_claimed"), "NOT READY TO SETTLE"), lambda r, v: met(v, "E1.recap"))
A("E21", "HELD", B, "E1.recap L2 contracts_claimed=12000 (confirmation mixed into the recap)", chain(lambda m: [x.update(contracts_claimed=12000) for x in m["E1"]["recap"]["legs"] if x["leg_id"] == "L2"]), lambda r, v: met(v, "E1.recap"))


def _rotate_ids(m):
    ids = [x["transfer_id"] for x in m["E2"]["confirmations"]]
    for x, i in zip(m["E2"]["confirmations"], ids[1:] + ids[:1]):
        x["transfer_id"] = i


A("E22", "EXPLOIT", B, "E2.confirmations transfer_ids rotated across the four legs (every id on the wrong leg)", _rotate_ids, lambda r, v: met(v, "E2.confirms") and not met(v, "E2.n_halluc"))
A("E23", "EXPLOIT", B, "E2.confirmations reduced to {leg_id, quantity, status} (no id, OSI, side, accounts, date)", lambda m: m["E2"].update(confirmations=[{k: x[k] for k in ("leg_id", "quantity", "status")} for x in m["E2"]["confirmations"]]), lambda r, v: met(v, "E2.confirms"))
A("E24", "HELD", B, "E2.confirmations L2 quantity=120 (recap adopted) with every optional field present", row_set("E2", "confirmations", "L2", quantity=120), lambda r, v: met(v, "E2.confirms"))
A("E25", "HELD", B, "E2.confirmations L2 accounts swapped", row_set("E2", "confirmations", "L2", from_account="CM 0829 / HCM-ETF-07", to_account="CM 0471 / GRBO-FND-01"), lambda r, v: met(v, "E2.confirms"))
A("E26", "HELD", B, "E2.confirmations status='REJECTED' on all rows", each_set("E2", "confirmations", status="REJECTED"), lambda r, v: met(v, "E2.confirms"))
A("E27", "FALSEPOS", B, "correct answer, confirmation quantity written '12 000' (space thousands)", row_set("E2", "confirmations", "L2", quantity="12 000"), lambda r, v: not met(v, "E2.confirms"))
A("E28", "FALSEPOS", B, "correct answer, L3 position_type written 'sell' (or 'S', 'writer')", row_set("E2", "confirmations", "L3", position_type="sell"), lambda r, v: not met(v, "E2.confirms"))


def _abs_shorts(m):
    for sec, key, ks in (("E2", "positions", ("position_prior", "position_current")), ("C1", "position_check", ("expected_current", "actual_current"))):
        for x in m[sec][key]:
            for k in ks:
                x[k] = abs(x[k])
            x["side"] = "short" if x["leg_id"] in ("L3", "L4") else "long"


A("E29", "FALSEPOS", B, "correct answer, short legs as ABSOLUTE numbers + a side field (E2.positions and C1.position_check)", _abs_shorts, lambda r, v: not met(v, "E2.positions") and not met(v, "C1.positions"))
A("E30", "HELD", B, "E2.positions L2 adopts the recap (120 / 23,880)", row_set("E2", "positions", "L2", transferred_out=120, position_current=23880), lambda r, v: met(v, "E2.positions"))
A("E31", "HELD", B, "E2.nav marks_date = 2026-06-22 (prior day)", set_path(("E2", "nav", "marks_date"), "2026-06-22"), lambda r, v: met(v, "E2.nav"))
A("E32", "EXPLOIT", B, "E2.shares share status='not received' (packet: received)", set_path(("E2", "share_receipt", "status"), "not received"), lambda r, v: met(v, "E2.shares"))
A("E33", "EXPLOIT", B, "E2.shares cash_component_payment_status='released, not pending' (packet: NOT RELEASED)", set_path(("E2", "cash_component_payment_status"), "released, not pending"), lambda r, v: met(v, "E2.shares"))
A("E34", "FALSEPOS", B, "correct answer, cash_component_payment_status='awaiting release'", set_path(("E2", "cash_component_payment_status"), "awaiting release"), lambda r, v: not met(v, "E2.shares"))
A("E35", "HELD", B, "E2.shares cash_component_payment_status='released'", set_path(("E2", "cash_component_payment_status"), "released"), lambda r, v: met(v, "E2.shares"))
A("E36", "CONTROL", B, "E2.nav.marks as a LIST of {leg_id, mark}, keyed by OSI list, marks_date omitted (must be credited)", chain(set_path(("E2", "nav", "marks"), [{"osi_identifier": OSI[k], "mark": v} for k, v in {"L1": 254.9, "L2": 3.95, "L3": 0.8, "L4": 4.65}.items()]), lambda m: m["E2"]["nav"].pop("marks_date")), lambda r, v: not perfect(r))

A("E37", "CONTROL", B, "E2.shares status 'delivered FOP 09:40' with cash status 'on hold' must be credited", chain(set_path(("E2", "share_receipt", "status"), "delivered FOP 09:40"), set_path(("E2", "cash_component_payment_status"), "on hold")), lambda r, v: not perfect(r))
A("E38", "CONTROL", B, "C1.position_check L2 tie 'short 11,880' (and 'mismatch', 'fail') must be credited", row_set("C1", "position_check", "L2", tie="short 11,880"), lambda r, v: not perfect(r))

# ===== C: the other C1 atoms =====
A("C1", "EXPLOIT", B, "C1.exceptions L2 type='series mismatch' (wrong reason, right leg)", set_path(("C1", "exceptions"), [{"leg_id": "L2", "type": "series mismatch", "detail": ""}]), lambda r, v: met(v, "C1.exceptions"))
A("C2", "EXPLOIT", B, "C1.exceptions L2 detail='L2 matches; no quantity issue' (says the opposite)", set_path(("C1", "exceptions"), [{"leg_id": "L2", "type": "", "detail": "L2 matches; no quantity issue"}]), lambda r, v: met(v, "C1.exceptions"))
A("C3", "EXPLOIT", B, "C1.exceptions L2 detail='x' (one token)", set_path(("C1", "exceptions"), [{"leg_id": "L2", "type": "", "detail": "x"}]), lambda r, v: met(v, "C1.exceptions"))
A("C4", "HELD", B, "C1.exceptions L2 detail='see ledger'", set_path(("C1", "exceptions"), [{"leg_id": "L2", "type": "exception", "detail": "see ledger"}]), lambda r, v: met(v, "C1.exceptions"))
A("C5", "HELD", B, "C1.exceptions names L2 and L4", set_path(("C1", "exceptions"), [{"leg_id": "L2", "type": "quantity_mismatch", "detail": "12,000 vs 120"}, {"leg_id": "L4", "type": "quantity_mismatch", "detail": "120"}]), lambda r, v: met(v, "C1.exceptions"))
A("C6", "FALSEPOS", C, "clean case, correct answer, exceptions=[{type:'summary', detail:'All four legs tie out'}]", set_path(("C1", "exceptions"), [{"leg_id": "ALL", "type": "summary", "detail": "All four legs tie out"}]), lambda r, v: not met(v, "C1.exceptions"))
A("C7", "FALSEPOS", C, "clean case, correct answer, exceptions=[{type:'nil'}] (or 'N/A', 'Reconciled: no differences')", set_path(("C1", "exceptions"), [{"leg_id": "", "type": "nil", "detail": ""}]), lambda r, v: not met(v, "C1.exceptions"))
A("C8", "EXPLOIT", C, "clean case, exceptions=[L2 typed 'note' whose detail claims a 12,000 vs 120 break]", set_path(("C1", "exceptions"), [{"leg_id": "L2", "type": "note", "detail": "12,000 contracts vs 120 due: quantity mismatch"}]), lambda r, v: met(v, "C1.exceptions"))
A("C9", "EXPLOIT", B, "C1 ledger series_match=false, side_match=false, status='REJECTED' on every row (contradicts tie)", each_set("C1", "ledger", series_match=False, side_match=False, status="REJECTED"), lambda r, v: perfect(r))
A("C10", "FALSEPOS", B, "correct answer, C1.due_contracts_per_leg as a per-leg map {L1:120,...}", set_path(("C1", "due_contracts_per_leg"), {"L1": 120, "L2": 120, "L3": 120, "L4": 120}), lambda r, v: not met(v, "C1.due"))
A("C11", "EXPLOIT", B, "C1.structure credited for a ledger of one leg repeated four times (L1 x4)", lambda m: m["C1"].update(ledger=[copy.deepcopy([x for x in m["C1"]["ledger"] if x["leg_id"] == "L1"][0]) for _ in range(4)]), lambda r, v: met(v, "C1.structure"))

# ===== composites =====


def _wrong_composite(m):
    each_set("E1", "legs", exercise_style="non-European")(m)
    each_set("E1", "legs", "recap", status_claimed="NOT TRANSFERRED")(m)
    set_path(("E1", "recap", "status_claimed"), "NOT READY TO SETTLE")(m)
    cite("pcf", H_SIB)(m)
    _rotate_ids(m)
    set_path(("E2", "share_receipt", "status"), "not received")(m)
    set_path(("E2", "cash_component_payment_status"), "released, not pending")(m)
    each_set("C1", "ledger", series_match=False, side_match=False, status="REJECTED")(m)
    row_set("C1", "ledger", "L2", tie="series_mismatch")(m)
    set_path(("C1", "exceptions"), [{"leg_id": "L2", "type": "series mismatch", "detail": "L2 matches; no quantity issue"}])(m)


A("W1", "EXPLOIT", B, "COMPOSITE: ten wrong fields across eight E1/E2/C1 atoms at once (HOLD, C2/C3/D1/D2 right)", _wrong_composite, lambda r, v: perfect(r))


def _natural_composite(case_clean):
    def mut(m):
        for x in m["C1"]["ledger"]:
            if x["leg_id"] == "SHARES":
                x["leg_id"] = "share_receipt"
                x["tie"] = "OK (quantity matches)"
            elif x["leg_id"] == "L2" and not case_clean:
                x["tie"] = "quantity_mismatch (over-delivered by 11,880)"
            else:
                x["tie"] = "match - 120 contracts confirmed"
        _abs_shorts(m)
        set_path(("E2", "nav", "marks"), {OSI[k]: v for k, v in {"L1": 254.9, "L2": 3.95, "L3": 0.8, "L4": 4.65}.items()})(m)
        if case_clean:
            set_path(("C1", "exceptions"), [{"leg_id": "ALL", "type": "summary", "detail": "All four legs tie out"}])(m)
        else:
            each_set("E1", "legs", expiry="30/09/2026")(m)
    return mut


A("W2", "FALSEPOS", B, "COMPOSITE: a fully CORRECT answer (HOLD, right numbers) in five natural formats - break case", _natural_composite(False), lambda r, v: r.case_gated < 0.9 and gate(r, "GATE.FABRICATION"))
A("W3", "FALSEPOS", C, "COMPOSITE: a fully CORRECT answer (SETTLE, right numbers) in natural formats - clean case", _natural_composite(True), lambda r, v: r.case_gated < 0.9 and gate(r, "GATE.FABRICATION"))


def _osi_only(m):
    for x in m["C1"]["ledger"]:
        if x["leg_id"] in OSI:
            x["osi_identifier"] = OSI[x.pop("leg_id")]


A("K23", "CONTROL", B, "C1 ledger rows keyed by OSI only (no leg_id) must be credited (SHARES row kept)", _osi_only, lambda r, v: not perfect(r))
A("K28", "CONTROL", B, "C1 ledger leg ids written 'l2' (lowercase) and 'L2 (long put 240)' must be credited",
  chain(lambda m: [x.update(leg_id=x["leg_id"].lower()) for x in m["C1"]["ledger"] if x["leg_id"] in OSI],
        lambda m: [x.update(leg_id=f"{x['leg_id'].upper()} ({DESC[x['leg_id'].upper()]})") for x in m["C1"]["ledger"] if x["leg_id"].upper() in OSI and x["leg_id"] in ("l2", "l3")]), lambda r, v: not perfect(r))
A("K29", "CONTROL", B, "C1 ledger rows in a different order must be credited", lambda m: m["C1"]["ledger"].reverse(), lambda r, v: not perfect(r))


# ---------------------------------------------------------------- crash fuzz (a HELD attack: malformed types must score, never raise)
def fuzz():
    weird = [None, "", 0, -1, 1.5, float("nan"), float("inf"), True, [], [None], ["L2"], {}, {"a": 1}, {"value": 3}, "x" * 3000, "\x00", 10 ** 30, "NaN", "((((", object]
    sections = [("E1", "legs"), ("E1", "recap"), ("E1", "citation"), ("E2", "confirmations"), ("E2", "positions"), ("E2", "nav"),
                ("E2", "share_receipt"), ("E2", "cash_component_payment_status"), ("C1", "ledger"), ("C1", "position_check"),
                ("C1", "exceptions"), ("C1", "due_contracts_per_leg"), ("C1", "due_shares")]
    n = crashes = 0
    for path in (B, C):
        base = oracle(path)
        muts = []
        for a, b in sections:
            for w in weird:
                muts.append(lambda m, a=a, b=b, w=w: m[a].__setitem__(b, w))
            if isinstance(base[a][b], list) and base[a][b]:
                for f in base[a][b][0]:
                    for w in weird:
                        muts.append(lambda m, a=a, b=b, f=f, w=w: m[a][b][0].__setitem__(f, w))
        for w in weird:
            muts.append(lambda m, w=w: m["E2"]["nav"].__setitem__("marks", w))
            muts.append(lambda m, w=w: m.__setitem__("E1", w))
            muts.append(lambda m, w=w: m.__setitem__("E2", w))
            muts.append(lambda m, w=w: m.__setitem__("C1", w))
        for mu in muts:
            m = oracle(path)
            mu(m)
            n += 1
            try:
                grade_detail(path, m)
            except Exception:
                crashes += 1
    return n, crashes


# ---------------------------------------------------------------- run
def main():
    base = {p: grade_detail(p, oracle(p))[0] for p in (B, C)}
    print(f"baseline oracle: break case_gated={base[B].case_gated:.4f} AllPass={base[B].allpass} | clean case_gated={base[C].case_gated:.4f} AllPass={base[C].allpass}")
    tally = {"REPRODUCED": 0, "NOT-REPRODUCED": 0, "HELD": 0, "ACCEPTED": 0, "UNEXPECTED": 0}
    for aid, kind, path, label, mut, bad in ATTACKS:
        m = oracle(path)
        try:
            mut(m)
            res, v = grade_detail(path, m)
            worked = bool(bad(res, v))
        except Exception as e:                                         # a crash is itself a finding
            print(f"[{aid:<3}] {kind:<8} {'brk' if path == B else 'cln'} | {label} | CRASH {type(e).__name__}: {e}")
            tally["UNEXPECTED"] += 1
            continue
        if kind in ("HELD", "CONTROL"):
            verdict = "UNEXPECTED" if worked else ("HELD" if kind == "HELD" else "ACCEPTED")
        else:
            verdict = "REPRODUCED" if worked else "NOT-REPRODUCED"
        tally[verdict] += 1
        unmet = {k: round(x.met, 2) for k, x in v.items() if x.met < 0.999 and ".n_" not in k}
        pen = sorted(k for k, x in v.items() if ".n_" in k and x.met >= 0.999)
        print(f"[{aid:<3}] {kind:<8} {'brk' if path == B else 'cln'} | {label} | {verdict} | case={res.case_gated:.4f} AllPass={res.allpass} "
              f"gates={res.fired_gates} {cps(res, 'E1', 'E2', 'C1')} unmet={unmet} pen={pen}")
    n, crashes = fuzz()
    ok = crashes == 0
    print(f"[FZ ] HELD     both| crash-fuzz: {n} malformed-type mutations across the E1/E2/C1 sections and every row field | {'HELD' if ok else 'UNEXPECTED'} | crashes={crashes}")
    tally["HELD" if ok else "UNEXPECTED"] += 1
    print(f"\nSUMMARY: {sum(tally.values())} runs | findings REPRODUCED={tally['REPRODUCED']} NOT-REPRODUCED={tally['NOT-REPRODUCED']} | "
          f"attacks that FAILED (grader HELD)={tally['HELD']} | positive controls ACCEPTED={tally['ACCEPTED']} | UNEXPECTED={tally['UNEXPECTED']}")


if __name__ == "__main__":
    main()

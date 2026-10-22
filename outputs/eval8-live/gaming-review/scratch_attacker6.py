"""
scratch_attacker6.py - eval #8 gaming review, attacker 6: FALSE POSITIVES (the defence of honest models).

Every attack here is a RIGHT answer (or a right answer with one field phrased differently) in a form a careful desk
analyst or a well-behaved LLM might produce. The grader should score it 1.000/AllPass; every line that does not is a
finding. Re-runnable from the repo root, prints one result line per attack:

    python outputs/eval8-live/gaming-review/scratch_attacker6.py            # everything
    python outputs/eval8-live/gaming-review/scratch_attacker6.py A         # only attack ids starting with A

Line format:  <id> [case] <label> -> case_gated AllPass gates flags lost-atoms | CLEAN or FALSE-POSITIVE (delta)
Whole-answer formats that lose points also print the isolation: which unit of the answer (a row's keys, a section's
keys) costs which atom - that is the field, and the note names the normaliser behind it.

Read-only: builds answers and runs the grader; edits nothing in the repo.
"""
from __future__ import annotations
import copy
import datetime as dt
import json
import os
import re
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
sys.path.insert(0, REPO)
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from harness.rubric import load_case, load_rubric, materialize, rubric_path_for      # noqa: E402
from harness.graders import grade                                                      # noqa: E402
from harness.scoring import score                                                      # noqa: E402
from harness import suites                                                             # noqa: E402
from harness import live_options_redemption as lor                                     # noqa: E402
from harness.suites import options_redemption as orx                                   # noqa: E402
from harness.suites import nav_oversight as nv                                         # noqa: E402

CASES = {"B": "grbo-redeem-2026", "C": "grbo-redeem-2026-clean"}
FILTER = sys.argv[1] if len(sys.argv) > 1 else ""


# ======================================================================================= engine
class Ctx:
    def __init__(self, k):
        self.path = os.path.join(REPO, "cases", f"{CASES[k]}.case.yaml")
        self.case = load_case(self.path)
        self.rubric = load_rubric(rubric_path_for(self.case))
        self.suite = suites.for_case(self.case)
        self.atoms = materialize(self.rubric, self.case)
        g = dict(self.case["gold"])
        g["manifest"] = self.case.get("manifest", {})
        g["_snapshot"] = self.case.get("snapshot")
        g["_claims"] = self.case.get("claims")
        g["_documents"] = self.case.get("documents")
        g["_case"] = self.case
        self.gold = g


_CTX = {}


def ctx(k):
    if k not in _CTX:
        _CTX[k] = Ctx(k)
    return _CTX[k]


def base(k):
    """the live-schema-shaped oracle: what a perfect schema-following model emits (wire form)"""
    return lor.oracle_to_schema(ctx(k).case)


def run(k, m):
    c = ctx(k)
    verdicts, rg = grade(c.atoms, m, c.gold, c.rubric, c.suite)
    res = score(c.atoms, verdicts, rg, c.rubric, case_id=c.case["case_id"], refusal_cp=c.suite.REFUSAL_CP)
    lost = []
    for a in c.atoms:
        v = verdicts.get(a.id)
        met = v.met if v else 0.0
        if a.points > 0 and met < 0.999:
            lost.append((a.id, round((1 - met) * a.points, 2)))
        elif a.points < 0 and met >= 0.999:
            lost.append((a.id, a.points))
    return dict(score=res.case_gated, allpass=res.allpass, gates=res.fired_gates, flags=res.flags, e6=res.e6,
                cps={x: d["score_gated"] for x, d in res.checkpoints.items()}, lost=lost)


def clean(s):
    return s["score"] >= 0.99995 and s["allpass"] == 1 and not s["gates"]


def lostfmt(s):
    return ",".join(f"{a}({p:+g})" for a, p in s["lost"]) or "-"


TALLY = {"clean": 0, "false_positive": 0, "fair": 0}


def line(aid, k, label, s, note="", fair=False):
    if clean(s):
        tag = "CLEAN"
        TALLY["clean"] += 1
    elif fair:
        tag = f"FAIR-FAIL ({s['score'] - 1:+.4f}; a control: the answer is genuinely different)"
        TALLY["fair"] += 1
    else:
        tag = f"FALSE-POSITIVE ({s['score'] - 1:+.4f})"
        TALLY["false_positive"] += 1
    g = ",".join(s["gates"]) or "-"
    f = ",".join(s["flags"]) or "-"
    print(f"{aid} [{k}] {label} -> case={s['score']:.4f} allpass={s['allpass']} gates={g} flags={f} lost={lostfmt(s)} | {tag}"
          + (f"  {note}" if note else ""))


# ---- walking / diffing (isolation) ----
def walk(o, f, path=()):
    if isinstance(o, dict):
        return {kk: walk(v, f, path + (kk,)) for kk, v in o.items()}
    if isinstance(o, list):
        return [walk(v, f, path + (i,)) for i, v in enumerate(o)]
    return f(path, o)


def lastkey(path):
    for p in reversed(path):
        if isinstance(p, str):
            return p
    return ""


def getp(o, path):
    for p in path:
        o = o[p]
    return o


def setp(o, path, v):
    for p in path[:-1]:
        o = o[p]
    o[path[-1]] = v


def diff_units(a, b, path=()):
    if type(a) != type(b):
        return [(path, "whole")]
    if isinstance(a, dict):
        out, direct = [], []
        for kk in set(a) | set(b):
            if kk not in a or kk not in b:
                direct.append(kk)
            else:
                av, bv = a[kk], b[kk]
                if isinstance(av, (dict, list)) or isinstance(bv, (dict, list)):
                    if type(av) != type(bv):
                        direct.append(kk)
                elif av != bv:
                    direct.append(kk)
        if direct:
            out.append((path, ("direct", tuple(sorted(direct, key=str)))))
        for kk in a:
            if kk in b and isinstance(a[kk], (dict, list)) and type(a[kk]) == type(b[kk]):
                out += diff_units(a[kk], b[kk], path + (kk,))
        return out
    if isinstance(a, list):
        if len(a) != len(b):
            return [(path, "whole")]
        out = []
        for i in range(len(a)):
            out += diff_units(a[i], b[i], path + (i,))
        return out
    return [] if a == b else [(path, "whole")]


def apply_unit(basec, trans, unit):
    path, kind = unit
    m = copy.deepcopy(basec)
    if kind == "whole":
        if not path:
            return copy.deepcopy(trans)
        setp(m, path, copy.deepcopy(getp(trans, path)))
        return m
    dst = getp(m, path) if path else m
    src = getp(trans, path) if path else trans
    for kk in kind[1]:
        if kk in src:
            dst[kk] = copy.deepcopy(src[kk])
        else:
            dst.pop(kk, None)
    return m


def isolate(k, trans):
    """atom -> sorted set of unit descriptors (row index collapsed) whose application alone costs that atom"""
    b = base(k)
    byatom = {}
    for u in diff_units(b, trans):
        s = run(k, apply_unit(b, trans, u))
        if s["lost"] or s["gates"]:
            path, kind = u
            p = ".".join("[]" if isinstance(x, int) else str(x) for x in path)
            d = p + (" {" + ",".join(kind[1]) + "}" if kind != "whole" else " [value]")
            for a, pts in s["lost"]:
                byatom.setdefault(a, set()).add(d)
            for g in s["gates"]:
                byatom.setdefault(g, set()).add(d)
    return byatom


def attack(aid, label, builder, cases="BC", why=False, note="", fair=False):
    if FILTER and not aid.startswith(FILTER):
        return
    for k in cases:
        m = builder(base(k), k)
        s = run(k, m)
        line(aid, k, label, s, note, fair)
        if why and not clean(s):
            for a, units in sorted(isolate(k, m).items()):
                us = sorted(units)
                txt = "; ".join(us[:3]) + (f"; (+{len(us) - 3} more units)" if len(us) > 3 else "")
                print(f"        isolated {a}  <-  {txt[:170]}")


def S(*pairs):
    """builder: set several (path, value) pairs"""
    def f(b, k):
        m = copy.deepcopy(b)
        for path, val in pairs:
            cur = m
            for p in path[:-1]:
                cur = cur[p]
            cur[path[-1]] = val
        return m
    return f


def hdr(t):
    if not FILTER:
        print(f"\n# ---- {t}")


# ======================================================================================= format builders
USD_SUFFIX = {"option_value_per_cu", "cu_value", "option_value_order", "redemption_value", "excess_value",
              "ap_received_option_value", "total_net_assets"}
USD_PREFIX = {"strike", "mark", "value", "cash_component_per_cu", "cash_component_order", "transaction_fee",
              "net_cash_to_ap", "agent_cash_component", "cash_difference", "cash_component",
              "cash_component_per_cu_estimated", "cash_component_per_cu_final", "nav_per_share",
              "impact_per_remaining_share"}
CONTRACTS = {"contracts_per_cu", "quantity", "position_prior", "transferred_out", "position_current", "due_contracts",
             "confirmed_contracts", "excess_contracts", "due_contracts_per_leg", "fund_position_due",
             "fund_position_actual", "fund_position_short_by", "expected_current", "actual_current", "contracts_claimed"}
SHARES = {"due_shares", "cu_size", "total_shares", "shares_outstanding", "shares_outstanding_after"}
DATE_KEYS = {"trade_date", "settlement_date", "pcf_date", "series_expiry", "expiry", "effective_date",
             "valuation_date", "marks_date"}
BIGUSD = {"option_value_per_cu", "cu_value", "option_value_order", "redemption_value", "excess_value",
          "ap_received_option_value", "total_net_assets"}


def isnum(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def usd(v, dp=2, suffix=False):
    s = f"{abs(v):,.{dp}f}"
    return ("-" if v < 0 else "") + (s + " USD" if suffix else "$" + s)


def f_stringly(b, k, yesno=False):
    def f(path, v):
        key = lastkey(path)
        if isinstance(v, bool):
            return ("yes" if v else "no") if (yesno and key != "cash_ties") else ("true" if v else "false")
        if not isnum(v):
            return v
        if len(path) >= 3 and path[-2] == "marks":
            return usd(v)
        if key in USD_SUFFIX:
            return usd(v, suffix=True)
        if key in USD_PREFIX:
            return usd(v, dp=4 if key in ("nav_per_share", "impact_per_remaining_share") else 2)
        if key in CONTRACTS:
            return f"{int(v):,} contracts"
        if key in SHARES:
            return f"{int(v):,} shares"
        if key == "impact_pct_of_nav":
            return f"{v}%"
        if key in ("multiplier", "num_cus"):
            return str(int(v))
        return v
    m = walk(b, f)
    for r in m["C1"]["ledger"]:
        if r.get("leg_id") == "SHARES":
            for kk in ("due_contracts", "confirmed_contracts"):
                r[kk] = r[kk].replace(" contracts", " shares")
    return m


def f_iso(b, k, tmpl):
    return walk(b, lambda p, v: tmpl.format(d=v) if lastkey(p) in DATE_KEYS and isinstance(v, str)
                and re.fullmatch(r"\d{4}-\d{2}-\d{2}", v) else v)


def f_dates(b, k, fmt):
    def g(p, v):
        if lastkey(p) in DATE_KEYS and isinstance(v, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", v):
            d = dt.date.fromisoformat(v)
            return d.strftime(fmt)
        return v
    return walk(b, g)


def f_osi(b, k, how):
    def conv(s):
        mm = re.fullmatch(r"(\S+?)\s*(\d{6})([CP])(\d{8})", s)
        if not mm:
            return s
        root, ymd, cp, st8 = mm.groups()
        strike = int(st8) / 1000.0
        return {"single_space": f"{root} {ymd}{cp}{st8}", "no_space": f"{root}{ymd}{cp}{st8}",
                "lower": f"{root.lower()}  {ymd}{cp.lower()}{st8}", "padded": f"{root}  {ymd}{cp}{st8} ",
                "nport": f"IWM {ymd[2:4]}/{ymd[4:]}/20{ymd[:2]} {strike:.2f} {cp}",
                "occ_dot": f"{root}  {ymd[:2]}-{ymd[2:4]}-{ymd[4:]} {cp} {strike:.2f}",
                "no_flex": f"{root.lstrip('4')}  {ymd}{cp}{st8}"}[how]
    return walk(b, lambda p, v: conv(v.strip()) if isinstance(v, str) and re.fullmatch(r"\S+?\s*\d{6}[CP]\d{8}\s*", v) else v)


def f_keyed_by_osi(b, k, shares_keyed=True, offending="osi"):
    m = copy.deepcopy(b)
    L = {r["leg_id"]: r["osi_identifier"] for r in m["E1"]["legs"]}

    def conv(rows):
        for r in rows:
            lid = r.get("leg_id")
            if lid in L:
                r["osi_identifier"] = L[lid]
                del r["leg_id"]
            elif lid == "SHARES" and not shares_keyed:
                del r["leg_id"]
    for rows in (m["E1"]["legs"], m["E1"]["recap"]["legs"], m["E2"]["confirmations"], m["E2"]["positions"], m["C1"]["ledger"],
                 m["C1"]["position_check"], m["C1"]["exceptions"], m["C2"]["leg_values_per_cu"]):
        conv(rows)
    m["E2"]["nav"]["marks"] = [{"osi_identifier": L[kk], "mark": vv} for kk, vv in m["E2"]["nav"]["marks"].items()]
    for sec in ("C3", "D1"):
        if m[sec].get("offending_leg") in L:
            m[sec]["offending_leg"] = L[m[sec]["offending_leg"]] if offending == "osi" else (
                m[sec]["offending_leg"] if offending == "leg" else None)
    return m


def f_absolute_shorts(b, k):
    m = copy.deepcopy(b)
    for r in m["E2"]["positions"]:
        neg = r["position_prior"] < 0
        r["position_prior"], r["position_current"] = abs(r["position_prior"]), abs(r["position_current"])
        r["side"] = "short" if neg else "long"
    for r in m["C1"]["position_check"]:
        neg = r["expected_current"] < 0
        r["expected_current"], r["actual_current"] = abs(r["expected_current"]), abs(r["actual_current"])
        r["side"] = "short" if neg else "long"
    return m


def f_abs_leg_values(b, k):
    m = copy.deepcopy(b)
    for r in m["C2"]["leg_values_per_cu"]:
        r["value"] = abs(r["value"])
    return m


def f_signed_shorts(b, k):
    m = copy.deepcopy(b)
    sh = {"L3", "L4"}
    for r in m["E2"]["confirmations"]:
        if r["leg_id"] in sh:
            r["quantity"] = -abs(r["quantity"])
    for r in m["E2"]["positions"]:
        if r["leg_id"] in sh:
            r["transferred_out"] = -abs(r["transferred_out"])
    for r in m["C1"]["ledger"]:
        if r["leg_id"] in sh:
            r["due_contracts"], r["confirmed_contracts"] = -abs(r["due_contracts"]), -abs(r["confirmed_contracts"])
    for r in m["E1"]["recap"]["legs"]:
        if r["leg_id"] in sh:
            r["contracts_claimed"] = -abs(r["contracts_claimed"])
    return m


def f_marks(b, k, how):
    m = copy.deepcopy(b)
    L = {r["leg_id"]: r["osi_identifier"] for r in m["E1"]["legs"]}
    mk = m["E2"]["nav"]["marks"]
    m["E2"]["nav"]["marks"] = {
        "list_legid": [{"leg_id": a, "mark": v} for a, v in mk.items()],
        "list_value_key": [{"leg_id": a, "value": v} for a, v in mk.items()],
        "list_osi": [{"osi_identifier": L[a], "mark": v} for a, v in mk.items()],
        "dict_osi": {L[a]: v for a, v in mk.items()},
        "dict_lower": {a.lower(): v for a, v in mk.items()},
    }[how]
    return m


def f_desk_vocab(b, k):
    m = copy.deepcopy(b)
    led = {r["leg_id"]: r for r in m["C1"]["ledger"]}
    led["L1"]["tie"], led["L3"]["tie"], led["L4"]["tie"], led["SHARES"]["tie"] = "OK", "quantity matches", "ties", "OK"
    for r in m["C1"]["position_check"]:
        if r["tie"] == "match":
            r["tie"] = "OK"
    if k == "B":
        led["L2"]["tie"] = "over-delivered by 11,880"
        for r in m["C1"]["position_check"]:
            if r["leg_id"] == "L2":
                r["tie"] = "11,880 short of the 23,880 due"
        m["C3"].update(direction="over-delivered to the AP (fund short the leg)", harmed="the fund's remaining shareholders",
                       enriched="Harrowgate")
        m["C1"]["exceptions"] = [{"leg_id": "L2", "type": "over_transfer", "detail": "OCC confirms 12,000 vs 120 due"}]
    else:
        led["L2"]["tie"] = "OK"
        m["C3"].update(direction="none", harmed="none", enriched="none")
    return m


def f_extra_fields(b, k):
    m = copy.deepcopy(b)

    def add(o):
        if isinstance(o, dict):
            for v in list(o.values()):
                add(v)
            o.setdefault("notes", "extra field")
            o.setdefault("confidence", 0.95)
            o.setdefault("sources", ["packet"])
        elif isinstance(o, list):
            for x in o:
                add(x)
    for sec in m.values():
        add(sec)
    return m


ZERO_COST = {   # keys no atom reads (found by the single-key omission sweep)
    ("E2", "confirmations", "[]"): {"transfer_id", "osi_identifier", "position_type", "from_account", "to_account", "effective_date"},
    ("E2", "nav"): {"valuation_date", "marks_date", "marks_source"},
    ("E2", "share_receipt"): {"from_dtc_participant", "received_et"},
    ("C1", "ledger", "[]"): {"series_match", "side_match", "status"},
    ("C2", "leg_values_per_cu", "[]"): {"contracts_per_cu", "mark", "sign"},
    ("C3",): {"offending_leg", "fund_position_short_by", "enriched", "ap_received_option_value", "cash_component_affected"},
    ("D1",): {"offending_series", "offending_reason", "release_cash", "cancel_shares"},
    ("D2", "twins", "[]"): {"citation", "unit"},
    ("E1", "citation"): {"locator"},
    ("P1",): {"direction", "pcf_id"},
}


def f_minimal(b, k):
    m = copy.deepcopy(b)

    def res(o, cpl):
        if not cpl:
            return [o]
        if cpl[0] == "[]":
            return [y for x in (o if isinstance(o, list) else []) for y in res(x, cpl[1:])]
        return res(o[cpl[0]], cpl[1:]) if isinstance(o, dict) and cpl[0] in o else []
    for cp, keys in ZERO_COST.items():
        for node in res(m, list(cp)):
            if isinstance(node, dict):
                for kk in keys:
                    node.pop(kk, None)
    return m


def f_locale(b, k, thou, dec):
    skip = {"num_cus", "multiplier", "sign", "contracts_per_cu"}

    def g(p, v):
        key = lastkey(p)
        if isinstance(v, bool) or not isnum(v) or key in skip:
            return v
        if isinstance(v, int) or (float(v).is_integer() and key not in USD_PREFIX | USD_SUFFIX | {"impact_pct_of_nav"}):
            return f"{int(v):,}".replace(",", thou)
        dp = 4 if key in ("nav_per_share", "impact_per_remaining_share", "impact_pct_of_nav") else 2
        return f"{v:,.{dp}f}".replace(",", "\x00").replace(".", dec).replace("\x00", thou)
    return walk(b, g)


def f_millions(b, k):
    return walk(b, lambda p, v: f"${v / 1e6:,.2f} million" if isnum(v) and lastkey(p) in BIGUSD else v)


def f_share_name(b, k, name):
    m = copy.deepcopy(b)
    for r in m["C1"]["ledger"]:
        if r["leg_id"] == "SHARES":
            if name is None:
                r.pop("leg_id")
            else:
                r["leg_id"] = name
    return m


def f_legid_style(b, k, fn):
    m = copy.deepcopy(b)
    ids = ("L1", "L2", "L3", "L4")

    def conv(rows):
        for r in rows:
            if isinstance(r, dict) and r.get("leg_id") in ids:
                r["leg_id"] = fn(r["leg_id"])
    for rows in (m["E1"]["legs"], m["E1"]["recap"]["legs"], m["E2"]["confirmations"], m["E2"]["positions"], m["C1"]["ledger"],
                 m["C1"]["position_check"], m["C1"]["exceptions"], m["C2"]["leg_values_per_cu"]):
        conv(rows)
    m["E2"]["nav"]["marks"] = {fn(a): v for a, v in m["E2"]["nav"]["marks"].items()}
    for sec in ("C3", "D1"):
        if m[sec].get("offending_leg") in ids:
            m[sec]["offending_leg"] = fn(m[sec]["offending_leg"])
    return m


def kitchen_sink(b, k):
    m = f_minimal(copy.deepcopy(b), k)
    m = f_keyed_by_osi(m, k, True, offending="leg")
    m = f_stringly(m, k)
    m = f_iso(m, k, "{d}T00:00:00Z")
    m = f_osi(m, k, "single_space")
    m = f_extra_fields(m, k)
    m["D1"]["decision"] = ("HOLD - do not release the cash component until the 11,880 excess contracts are transferred back"
                           if k == "B" else "SETTLE - release 8,700.00, cancel 100,000 shares, mark settled")
    for r in m["C1"]["ledger"]:
        if r.get("leg_id") == "SHARES":
            r["leg_id"] = "share_leg"
    return m


def f_bloomberg_desk(b, k):
    """a desk analyst's house style: Bloomberg dates (23-Jun-2026) on every date field, everything else right"""
    return f_dates(b, k, "%d-%b-%Y")


# ======================================================================================= the attacks
def main():
    # ---- baseline sanity ----
    for k in "BC":
        s = run(k, base(k))
        assert clean(s), f"baseline oracle must be clean on {k}: {s}"

    hdr("PART A - COMPLETE alternative-format oracle answers (whole answers), graded on both cases")
    attack("A01", "(a) stringly typed: '$8,700.00', '4,692,600.00 USD', '120 contracts', '0.7731%', 'true'", f_stringly, why=True)
    attack("A02", "(a) stringly typed with 'yes'/'no' booleans", lambda b, k: f_stringly(b, k, True), why=True)
    attack("A03", "(b) percentages as fractions: impact_pct_of_nav 0.007731", S((("C3", "impact_pct_of_nav"), 0.007731)), why=True)
    attack("A03b", "(b) fractions rounded: impact_pct_of_nav 0.0077", S((("C3", "impact_pct_of_nav"), 0.0077)), why=True)
    for tag, tmpl in (("Z", "{d}T00:00:00Z"), ("millis Z", "{d}T00:00:00.000Z"), ("+00:00", "{d}T00:00:00+00:00"),
                      ("space", "{d} 00:00:00"), ("ET offset", "{d}T16:00:00-04:00")):
        attack("A04", f"(c) every date an ISO datetime ({tag})", lambda b, k, t=tmpl: f_iso(b, k, t), why=True)
    for how in ("single_space", "no_space", "lower", "padded"):
        attack("A05", f"(d) OSI identifiers: {how}", lambda b, k, h=how: f_osi(b, k, h), why=True)
    attack("A06", "(d) OSI identifiers as the N-PORT title form 'IWM 09/30/2026 240.00 P'", lambda b, k: f_osi(b, k, "nport"), why=True)
    attack("A06b", "(d) OSI identifiers dotted 'OCC-style 4IWM  26-09-30 P 240.00'", lambda b, k: f_osi(b, k, "occ_dot"), why=True)
    attack("A06c", "(control) OSI root without the FLEX '4' (a different series - a FAIR failure)", lambda b, k: f_osi(b, k, "no_flex"), cases="B", fair=True)
    attack("A07", "(e) every row keyed by OSI, NO leg_id (shares row keeps leg_id=SHARES), D1.offending_leg = the OSI",
           lambda b, k: f_keyed_by_osi(b, k, True, "osi"), why=True)
    attack("A07b", "(e) as A07 but D1.offending_leg stays 'L2'", lambda b, k: f_keyed_by_osi(b, k, True, "leg"), why=True)
    attack("A07c", "(e) as A07b, shares row has no key at all", lambda b, k: f_keyed_by_osi(b, k, False, "leg"), why=True)
    attack("A07d", "(e) as A07b, D1.offending_leg null + offending_series = OSI", lambda b, k: f_keyed_by_osi(b, k, True, "none"), why=True)
    attack("A08", "(f) short positions as positive numbers with a side field (E2.positions, C1.position_check)", f_absolute_shorts, why=True)
    attack("A08b", "(f) leg values as magnitudes, the sign carried by the schema's own sign field", f_abs_leg_values, why=True)
    attack("A08c", "(f) the mirror: written legs carry NEGATIVE quantities (confirmations, ledger, recap, transferred_out)", f_signed_shorts, why=True)
    for how in ("list_legid", "list_value_key", "list_osi", "dict_lower"):
        attack("A09", f"(g) E2.nav.marks as {how}", lambda b, k, h=how: f_marks(b, k, h), why=True)
    attack("A09b", "(g) E2.nav.marks as {osi: mark}", lambda b, k: f_marks(b, k, "dict_osi"), why=True)
    attack("A10", "(h) prose decision: 'HOLD - do not release the cash component until the 11,880 excess contracts are transferred back'",
           S((("D1", "decision"), "HOLD - do not release the cash component until the 11,880 excess contracts are transferred back")), cases="B")
    attack("A10b", "(h) prose decision: 'SETTLE - release 8,700.00, cancel 100,000 shares, mark settled'",
           S((("D1", "decision"), "SETTLE - release 8,700.00, cancel 100,000 shares, mark settled")), cases="C")
    attack("A11", "(i) desk vocabulary: tie 'OK'/'quantity matches'/'over-delivered by 11,880', direction 'over-delivered to the AP (fund short the leg)'",
           f_desk_vocab, why=True)
    attack("A12", "(j) minimalist: every key no atom reads is omitted", f_minimal, why=True)
    attack("A13", "(k) extra fields (notes, confidence, sources) on every section and row", f_extra_fields, why=True)
    attack("A14", "(l) German numbers 1.234,56 on every figure", lambda b, k: f_locale(b, k, ".", ","), why=True)
    attack("A14b", "(l) SI/Swiss thousands '12 000' / '12'000' (decimal point)", lambda b, k: f_locale(b, k, " ", "."), cases="B", why=True)
    attack("A15", "(n) large USD figures as '$4.69 million' / '$610.00 million'", f_millions, why=True)
    attack("A16", "(combined) kitchen sink: minimal + keyed-by-OSI + stringly + ISO datetimes + single-space OSI + extras + prose decision + share_leg",
           kitchen_sink, why=True)
    attack("A17", "(persona) Bloomberg-desk dates '23-Jun-2026' on every date field, everything else right", f_bloomberg_desk, why=True)

    hdr("PART B - (m) the share row of the ledger")
    for nm in ("SHARES", "share_leg", "SHARE", "shares", "GRBO", "Shares (DTC)", "ETF shares", "Shares leg", "SHARE DELIVERY",
               "DTC", "SHARES_RECEIVED", "SHARE_RECEIPT", "SHARES-FOP", "Creation Unit shares"):
        attack("B01", f"share row leg_id={nm!r}", lambda b, k, n=nm: f_share_name(b, k, n), why=False)
    attack("B01", "share row has no key", lambda b, k: f_share_name(b, k, None), why=False)
    attack("B01", "share row omitted entirely", lambda b, k: (lambda m: (m["C1"].update(ledger=[r for r in m["C1"]["ledger"] if r["leg_id"] != "SHARES"]), m)[1])(copy.deepcopy(b)), why=False)

    hdr("PART C - D1.decision classifier: natural SETTLE phrasings on the CLEAN case, natural HOLD phrasings on the BREAK case")
    for t in ("SETTLE - no break", "SETTLE - all four legs tie, no break", "SETTLE - no breaks", "SETTLE: no mismatch", "SETTLE - no hold required",
              "Settle; no escalation needed", "SETTLE - no corrective action required", "Settle - no reversal needed", "Settle. No reason to delay.",
              "SETTLE - nothing pending", "SETTLE - no pending items", "SETTLE - not on hold", "SETTLE - no unmatched legs", "SETTLE - no fails",
              "SETTLE - nothing to investigate", "SETTLE - not blocked", "No issues - settle", "No break. Settle.", "No exceptions - settle",
              "Nothing pending, settle", "No problems: settle", "No hold - settle",
              "SETTLE - no exceptions", "SETTLE (all legs tie; no exceptions)", "Go ahead and settle", "OK to settle", "Clear to settle",
              "Release the cash and cancel the shares", "SETTLE - no outstanding breaks", "SETTLE - zero exceptions"):
        attack("C01", f"clean decision {t!r}", S((("D1", "decision"), t)), cases="C")
    for t in ("Do not mark the order settled", "No cash to be released", "Too early to settle", "It is too early to release", "Release nothing",
              "Not ready for settlement", "Does not tie", "Return the excess first", "Hold off on settling", "wait", "Unsafe to settle", "Premature to settle",
              "HOLD - the order should not be settled or completed", "HOLD - break must be cleared first", "HOLD - break to be closed",
              "HOLD - do not mark the order settled", "HOLD - too early to settle", "HOLD - clear the break first",
              "HOLD - do not release the cash component until the 11,880 excess contracts are transferred back", "Cannot settle until the 11,880 contracts are back",
              "HOLD - not ready to settle", "Do not settle", "Settlement cannot proceed", "HOLD - release when corrected", "Hold. Release only after the excess contracts are back."):
        attack("C02", f"break decision {t!r}", S((("D1", "decision"), t)), cases="B")

    # ---- aggregate matrices behind the counts in the note (one summary line each; failing strings listed) ----
    if not FILTER or FILTER.startswith("C"):
        tails_clean = ("all four legs tie|all legs tie and the cash ties|every leg ties, shares received, cash ties|all OCC confirmations match the basket|no break|no breaks|no mismatches|"
                       "no mismatch|no exceptions|no discrepancies|no differences|nothing to escalate|no escalation required|no hold required|no need to hold|not on hold|no reason to hold|"
                       "nothing outstanding|nothing pending|no pending items|no open items|no issues|no unmatched legs|no corrective action needed|no reversal required|no recovery needed|"
                       "no fails|no failed legs|no risk|no delay|no reason to delay|no investigation needed|the recap is right|the recap matches OCC|the recap is confirmed by OCC|"
                       "the recap is correct but verified independently|OCC confirmations agree with the recap|quantities tie to the PCF|all legs confirmed and accepted|"
                       "cash component ties within tolerance|net cash 8,700.00 ties|ready to release|cleared|release 8,700.00|release the cash|cancel 100,000 shares|mark settled|all checks passed|"
                       "checks pass|no blockers|no blocking items|no stop|unblocked|not blocked|nothing blocks settlement|no block|no problem|no problems|zero breaks|zero exceptions|0 breaks|"
                       "break-free|no outstanding differences").split("|")
        bad = []
        for tl in tails_clean:
            sc = run("C", S((("D1", "decision"), f"SETTLE - {tl}"))(base("C"), "C"))
            if sc["cps"]["D1"] < 0.9999:
                bad.append(tl)
        print(f"C03 [C] 'SETTLE - <justification>' over {len(tails_clean)} natural justifications: {len(tails_clean) - len(bad)} credited, {len(bad)} give D1 = 0 -> {bad}")
        heads = ("No issues|No break|No exceptions|No mismatch|Nothing pending|No problems|Not a hold|No hold|No differences|OK|Clean|All legs tie|Everything ties|All clear").split("|")
        bad2 = []
        for h in heads:
            for sep in (" - ", ". ", ": ", ", "):
                sc = run("C", S((("D1", "decision"), f"{h}{sep}settle"))(base("C"), "C"))
                if sc["cps"]["D1"] < 0.9999:
                    bad2.append(f"{h}{sep}settle")
        print(f"C04 [C] '<head><sep>settle' over {len(heads) * 4} forms: {len(heads) * 4 - len(bad2)} credited, {len(bad2)} read as HOLD or contradictory (every 'No <x>' head fails): {bad2[:6]} ...")
        tails_hold = ("the long put 240 leg confirms 12,000 contracts against 120 due|L2 does not tie|L2 breaks|break on L2|quantity mismatch on L2|the L2 confirmation is 12,000 not 120|"
                      "11,880 excess contracts left the fund|the fund is short 11,880 contracts of L2|do not release the cash|do not pay out 8,700.00|do not cancel the shares|do not mark the order settled|"
                      "cash release withheld|cash release blocked|cash release on hold|settlement cannot proceed|cannot settle|cannot release|cannot complete the redemption|the order cannot be completed|"
                      "the order is not ready|not ready for settlement|not ready to settle|not safe to settle|unsafe to settle|premature to settle|settlement is premature|too early to settle|"
                      "release only after the corrective transfer|release only once the 11,880 contracts are returned|settle after the return transfer|settle once the position is restored|"
                      "settle when L2 is corrected|settle only when the custodian shows 23,880|pending corrective transfer|pending return of 11,880 contracts|until the excess is returned|"
                      "until the position is corrected|before any release|before releasing the cash|before settlement|awaiting the corrective transfer|await the return transfer|"
                      "needs a corrective transfer|needs correcting first|corrective transfer required|return transfer required|reverse the excess first|reverse 11,880 contracts first|"
                      "unwind the over-transfer first|recover the 11,880 contracts first|escalate to the clearing members|escalate to Kestrel Point and Harrowgate|refer to the ETF agent|recap is wrong|"
                      "recap overstates readiness|the recap's READY TO SETTLE is wrong|recap reflects instructions, not confirmations|agent recap cannot be relied on|do not rely on the recap|"
                      "the recap is not evidence|do not proceed|do not proceed to settlement|do not approve|approval withheld|approval denied|not approved|not cleared|not cleared for settlement|"
                      "cannot be cleared|clear the break first|the break must be cleared first|the break needs closing out first|resolve first|fix first|resolve L2 first|L2 must be fixed first|"
                      "wait|wait for the corrective transfer|stop|stop the settlement|stop - break on L2|freeze the order|defer settlement|postpone settlement|delay settlement|delay the release|"
                      "put on hold|keep on hold|remains on hold|remains unsettled|stays unsettled|unsettled|not settled|do not settle|no settlement|no release|no payment|nothing to release|"
                      "nothing should be released|nothing may be released|release nothing|do not release anything|no cash goes out|no cash to be released|the cash must stay put|"
                      "cash stays put until the position is restored").split("|")
        bad3 = []
        for tl in tails_hold:
            sc = run("B", S((("D1", "decision"), f"HOLD - {tl}"))(base("B"), "B"))
            if sc["cps"]["D1"] < 0.9999 or "GATE.SETTLE" in sc["gates"]:
                bad3.append(tl)
        print(f"C05 [B] 'HOLD - <reason>' over {len(tails_hold)} natural reasons: {len(tails_hold) - len(bad3)} credited, {len(bad3)} not -> {bad3}")

    hdr("PART D - D1 action fields: a correct HOLD whose remedy / escalate_to is an ordered list or uses 'complete/approve/settle/release/pay'")
    llm = {
        "remedy as numbered steps (1..4, 3 = 'Release 8,700.00 net cash, cancel the shares, mark settled')":
            ("remedy", "1) Instruct an OCC transfer of 11,880 contracts of 4IWM 260930P00240000 from CM 0829 / HCM-ETF-07 back to CM 0471 / GRBO-FND-01. 2) Verify the custodian position returns to 23,880. 3) Release 8,700.00 net cash, cancel the 100,000 shares and mark the order settled. 4) Have the ETF agent correct its recap."),
        "remedy 'Step 1 ... Step 2: release the 8,700.00 and cancel the 100,000 shares'":
            ("remedy", "Step 1: Harrowgate returns the 11,880 excess contracts of 4IWM 260930P00240000 to Kestrel Point (CM 0471). Step 2: release the 8,700.00 and cancel the 100,000 shares. Step 3: ETF agent corrects the recap."),
        "remedy 'In this order: return ...; release the 8,700.00 net cash; cancel the 100,000 shares'":
            ("remedy", "In this order: return the 11,880 excess contracts of 4IWM 260930P00240000 from CM 0829 to CM 0471; release the 8,700.00 net cash; cancel the 100,000 shares; correct the recap."),
        "remedy '... first; the 8,700.00 is released and the shares cancelled afterwards'":
            ("remedy", "Get the 11,880 contracts of 4IWM 260930P00240000 returned from CM 0829 to CM 0471 first; the 8,700.00 is released and the 100,000 shares cancelled afterwards. Kestrel Point and Harrowgate to coordinate; correct the recap."),
        "remedy '... first. Subsequently release the 8,700.00 and cancel the shares'":
            ("remedy", "Return the 11,880 excess contracts to Kestrel Point (CM 0471) first. Subsequently release the 8,700.00 and cancel the shares."),
        "remedy '... first. Release the net cash and cancel the shares thereafter.'":
            ("remedy", "Return 11,880 contracts to CM 0471 first. Release the net cash and cancel the shares thereafter. Kestrel Point and Harrowgate to confirm."),
        "escalate_to '... to complete the return transfer; the ETF agent to correct the recap'":
            ("escalate_to", "Kestrel Point (CM 0471) and Harrowgate (CM 0829) to complete the return transfer; the ETF agent to correct the recap."),
        "escalate_to '... to approve and complete the return of 11,880 contracts'":
            ("escalate_to", "Clearing members Kestrel Point (CM 0471) and Harrowgate (CM 0829) to approve and complete the return of 11,880 contracts; ETF agent to fix the recap"),
        "escalate_to '... to settle the correction at OCC'":
            ("escalate_to", "Kestrel Point and Harrowgate clearing members to settle the correction at OCC; ETF agent to reissue the recap"),
        "escalate_to '... to finalise the return transfer and confirm it back to the fund'":
            ("escalate_to", "Kestrel Point (fund CM) and Harrowgate (AP CM) to finalise the return transfer and confirm it back to the fund"),
        "escalate_to 'Clearing members to release the excess contracts back to the fund'":
            ("escalate_to", "Clearing members to release the excess contracts back to the fund"),
        "escalate_to 'Clearing members to pay back the excess; ETF agent to correct the recap'":
            ("escalate_to", "Clearing members to pay back the excess; ETF agent to correct the recap"),
    }
    for lab, (fld, txt) in llm.items():
        attack("D01", f"HOLD + {lab}", S((("D1", fld), txt)), cases="B")
    for lab, (fld, txt) in {
        "control remedy 'Obtain a corrective OCC transfer ... before releasing'": ("remedy", "Obtain a corrective OCC position transfer of 11,880 contracts of 4IWM 260930P00240000 from CM 0829 (HCM-ETF-07) back to CM 0471 (GRBO-FND-01) and confirm it before releasing the 8,700.00 cash component or cancelling the 100,000 shares; correct the agent recap."),
        "control remedy '... When the custodian report shows 23,880, release 8,700.00'": ("remedy", "Return the excess 11,880 contracts of 4IWM 260930P00240000 to the fund (CM 0829 to CM 0471). When the custodian report shows 23,880, release 8,700.00, cancel the shares and mark the order settled."),
        "control remedy 'Only then can the 8,700.00 be paid out'": ("remedy", "The excess 11,880 contracts of 4IWM 260930P00240000 must be returned to CM 0471 from CM 0829. Only then can the 8,700.00 be paid out and the shares cancelled."),
        "control escalate_to 'Escalate to Kestrel Point, Harrowgate and the ETF agent'": ("escalate_to", "Escalate to Kestrel Point (CM 0471), Harrowgate (CM 0829) and the ETF agent"),
    }.items():
        attack("D02", f"HOLD + {lab}", S((("D1", fld), txt)), cases="B")
    attack("D03", "CLEAN remedy without 'settled/complete/close': 'Release 8,700.00 and cancel the shares'", S((("D1", "remedy"), "Release 8,700.00 and cancel the shares")), cases="C")
    attack("D03b", "CLEAN remedy 'Pay out 8,700.00 to the AP, cancel the 100,000 shares, finalize the order'", S((("D1", "remedy"), "Pay out 8,700.00 to the AP, cancel the 100,000 shares, finalize the order")), cases="C")
    attack("D03c", "CLEAN remedy 'Release the cash component of 9,200.00 less the 500.00 fee, cancel the shares, mark settled' (net figure not stated)",
           S((("D1", "remedy"), "Release the cash component of 9,200.00 less the 500.00 fee, cancel the shares and mark the order settled")), cases="C")

    eight = {
        "A 'before releasing' (control)": dict(remedy="Obtain a corrective OCC position transfer of 11,880 contracts of 4IWM 260930P00240000 from CM 0829 (HCM-ETF-07) back to CM 0471 (GRBO-FND-01) and confirm it before releasing the 8,700.00 cash component or cancelling the 100,000 shares; correct the agent recap.", escalate_to="Kestrel Point Securities (CM 0471), Harrowgate Capital Markets (CM 0829) and the ETF agent."),
        "B numbered steps": dict(remedy="1) Instruct an OCC transfer of 11,880 contracts of 4IWM 260930P00240000 from CM 0829 / HCM-ETF-07 back to CM 0471 / GRBO-FND-01. 2) Verify the custodian position returns to 23,880. 3) Release 8,700.00 net cash, cancel the 100,000 shares and mark the order settled. 4) Have the ETF agent correct its recap.", escalate_to="Both clearing members (Kestrel Point, Harrowgate) and the ETF agent; note there is no CCP guaranty for ex-clearing."),
        "C 'Do not ... yet ... and then settle' (control)": dict(remedy="Do not release the cash or cancel the shares yet. Have Harrowgate return 11,880 contracts of the 240 put to Kestrel Point via an OCC transfer, confirm 23,880 on the custodian report, and then settle.", escalate_to="Kestrel Point (CM 0471), Harrowgate (CM 0829), ETF agent."),
        "D 'When the custodian report shows' (control)": dict(remedy="Return the excess 11,880 contracts of 4IWM 260930P00240000 to the fund (CM 0829 to CM 0471). When the custodian report shows 23,880, release 8,700.00, cancel the shares and mark the order settled.", escalate_to="Both clearing members and the ETF agent."),
        "E escalate_to 'to complete the return transfer'": dict(remedy="Return the excess 11,880 contracts of 4IWM 260930P00240000 to the fund (CM 0829 to CM 0471) before any release or cancellation; correct the recap.", escalate_to="Kestrel Point (CM 0471) and Harrowgate (CM 0829) to complete the return transfer; the ETF agent to correct the recap."),
        "F 'Only then' (control)": dict(remedy="The excess 11,880 contracts of 4IWM 260930P00240000 must be returned to CM 0471 from CM 0829. Only then can the 8,700.00 be paid out and the shares cancelled.", escalate_to="Kestrel Point, Harrowgate and the ETF agent."),
        "G 'Step 1 / Step 2'": dict(remedy="Step 1: Harrowgate returns the 11,880 excess contracts of 4IWM 260930P00240000 to Kestrel Point (CM 0471). Step 2: release the 8,700.00 and cancel the 100,000 shares. Step 3: ETF agent corrects the recap.", escalate_to="Kestrel Point Securities, Harrowgate Capital Markets, ETF agent"),
        "H 'In this order'": dict(remedy="In this order: return the 11,880 excess contracts of 4IWM 260930P00240000 from CM 0829 to CM 0471; release the 8,700.00 net cash; cancel the 100,000 shares; correct the recap.", escalate_to="Kestrel Point, Harrowgate, ETF agent"),
    }
    if not FILTER or FILTER.startswith("D"):
        fired = 0
        for lab, d in eight.items():
            m = base("B")
            m["D1"].update(d)
            sc = run("B", m)
            fired += "GATE.SETTLE" in sc["gates"]
            line("D04", "B", f"HOLD + LLM-style remedy/escalation {lab}", sc)
        print(f"D04 [B] summary: {fired} of {len(eight)} LLM-style correct-HOLD remedy/escalation variants fire GATE.SETTLE")

    hdr("PART E - C1 / C3 text normalisers: tie, direction, harmed, exceptions")
    def l2tie(txt):
        def f(b, k):
            m = copy.deepcopy(b)
            for r in m["C1"]["ledger"]:
                if r["leg_id"] == "L2":
                    r["tie"] = txt
            return m
        return f
    for t in ("NOT OK", "Failed tie", "fails to tie", "Tie-out failed", "tie out failed: 12,000 vs 120", "Failed to match", "not clean", "Does not match", "not matched",
              "12,000 vs 120", "FAIL", "UNMATCHED", "Over-delivered (12,000 vs 120)", "over-delivered by 11,880", "BREAK", "Quantity break"):
        attack("E01", f"break-leg ledger tie {t!r}", l2tie(t), cases="B")
    def alltie(txt):
        def f(b, k):
            m = copy.deepcopy(b)
            for r in m["C1"]["ledger"]:
                if r["tie"] == "match":
                    r["tie"] = txt
            for r in m["C1"]["position_check"]:
                if r["tie"] == "match":
                    r["tie"] = txt
            return m
        return f
    for t in ("OK", "ties", "quantity matches", "Qty OK", "120 contracts - OK", "matched on series, side and quantity", "OK - long", "reconciled", "pass", "no break"):
        attack("E02", f"clean ledger + position_check, every match written {t!r}", alltie(t), cases="C")
    for t in ("fund short 11,880 contracts", "the fund is short the leg", "short 11,880", "over-delivered to the AP (fund short the leg)",
              "Over-delivered (fund short)", "over delivery: fund position short by 11,880 vs due", "too many contracts delivered to the AP",
              "AP received more than due", "excess delivered to the AP", "over_delivered_to_ap"):
        attack("E03", f"C3.direction {t!r}", S((("C3", "direction"), t)), cases="B")
    for t in ("non-redeeming shareholders", "remaining shareholders, not the AP", "the fund's remaining shareholders", "ETF shareholders", "existing shareholders"):
        attack("E04", f"C3.harmed {t!r}", S((("C3", "harmed"), t)), cases="B")
    for t in ("N/A", "not applicable", "no break", "none - all legs tie", "no direction"):
        attack("E05", f"clean C3.direction {t!r} (harmed 'none')", S((("C3", "direction"), t)), cases="C")
    for t in ("N/A", "no one", "no harm", "not applicable", "nobody"):
        attack("E05", f"clean C3.harmed {t!r}", S((("C3", "harmed"), t)), cases="C")
    for lab, rows in (("type 'exception', detail 'does not tie'", [{"leg_id": "L2", "type": "exception", "detail": "does not tie"}]),
                      ("L2 + a RECAP row ('recap shows 120 TRANSFERRED but OCC confirms 12,000')", [{"leg_id": "L2", "type": "quantity_mismatch", "detail": "12,000 vs 120 due"}, {"leg_id": "RECAP", "type": "recap_error", "detail": "recap shows 120 TRANSFERRED but OCC confirms 12,000"}]),
                      ("L2 + an ORDER row", [{"leg_id": "L2", "type": "quantity_mismatch", "detail": "12,000 vs 120 due"}, {"leg_id": "ORDER", "type": "recap_error", "detail": "READY TO SETTLE is wrong"}]),
                      ("single object instead of a list", {"leg_id": "L2", "type": "quantity_mismatch", "detail": "12,000 vs 120 due"}),
                      ("two rows on L2 (mismatch + position shortfall)", [{"leg_id": "L2", "type": "quantity_mismatch", "detail": "12,000 vs 120 due"}, {"leg_id": "L2", "type": "position_shortfall", "detail": "custodian 12,000 vs 23,880"}])):
        attack("E06", f"exceptions: {lab}", S((("C1", "exceptions"), rows)), cases="B")
    for lab, rows in (("[{'type': 'clean', 'detail': 'all four legs and the share receipt tie'}]", [{"leg_id": None, "type": "clean", "detail": "all four legs and the share receipt tie"}]),
                      ("[{'leg_id': 'ALL', 'type': 'ok'}]", [{"leg_id": "ALL", "type": "ok", "detail": "every leg ties"}]),
                      ("[{'type': 'observation', recap reflects instructions}]", [{"leg_id": None, "type": "observation", "detail": "the recap leg table reflects the transfer instructions, not the confirmations; confirmations independently verified"}])):
        attack("E07", f"clean exceptions: {lab}", S((("C1", "exceptions"), rows)), cases="C")
    for t in ("tie OK", "short_by_11880", "short by 11,880", "x", "", "n/a", "ties", "agrees except 11,880", "not ok", "differs by 11,880"):
        attack("E08", f"position_check L2 tie {t!r} (schema: 'match|<describe the shortfall>')",
               (lambda t: (lambda b, k: (lambda m: ([r.update(tie=t) for r in m["C1"]["position_check"] if r["leg_id"] == "L2"], m)[1])(copy.deepcopy(b))))(t), cases="B")

    hdr("PART F - P1: pins, names, dates, flow")
    attack("F01", "pcf_date = the PUBLISHED date 2026-06-22 (pcf_id right)", S((("P1", "pcf_date"), "2026-06-22")), cases="B")
    attack("F01b", "pcf_date '2026-06-22 21:30 ET' (published_et)", S((("P1", "pcf_date"), "2026-06-22 21:30 ET")), cases="B")
    for fld in ("trade_date", "settlement_date", "pcf_date", "series_expiry"):
        attack("F02", f"P1.{fld} omitted (pcf_id and series_osi right)", (lambda fld: lambda b, k: (lambda m: (m["P1"].pop(fld), m)[1])(copy.deepcopy(b)))(fld), cases="B")
    attack("F02", "P1.trade_date null", S((("P1", "trade_date"), None)), cases="B")
    for fmt, lab in (("%d-%b-%Y", "23-Jun-2026"), ("%d/%m/%Y", "23/06/2026"), ("%m/%d/%y", "06/23/26"), ("%b %d %Y", "Jun 23 2026"),
                     ("%A, %B %d, %Y", "Tuesday, June 23, 2026"), ("%m/%d/%Y", "06/23/2026"), ("%B %d, %Y", "June 23, 2026"), ("%d.%m.%Y", "23.06.2026"),
                     ("%Y%m%d", "20260623")):
        attack("F03", f"every date written {lab!r}", lambda b, k, f=fmt: f_dates(b, k, f), why=False)
    for fld, val in (("trade_date", "Tuesday, 2026-06-23"), ("trade_date", "T = 2026-06-23"), ("settlement_date", "T+1 (2026-06-24)"),
                     ("settlement_date", "Wed 2026-06-24"), ("pcf_date", "2026-06-23 (basket date)"), ("series_expiry", "2026-09-30 (last business day)"),
                     ("trade_date", "2026-06-23 (Tue)")):
        attack("F03b", f"P1.{fld} {val!r}", S((("P1", fld), val)), cases="B")
    for lab, val in (("fund en-dash", "Granite Ridge U.S. Small Cap Buffer ETF – October"), ("fund 'ETF-October'", "Granite Ridge U.S. Small Cap Buffer ETF-October"),
                     ("fund '(October)'", "Granite Ridge U.S. Small Cap Buffer ETF (October)"), ("fund all caps", "GRANITE RIDGE U.S. SMALL CAP BUFFER ETF - OCTOBER")):
        attack("F04", f"P1.fund {lab}", S((("P1", "fund"), val)), cases="B")
    attack("F04", "P1.authorized_participant 'Harrowgate Capital Markets'", S((("P1", "authorized_participant"), "Harrowgate Capital Markets")), cases="B")
    attack("F04", "P1.authorized_participant 'Harrowgate'", S((("P1", "authorized_participant"), "Harrowgate")), cases="B")
    for t in ("OCC position transfer", "OCC transfers, not through NSCC CNS", "ex-clearing", "Ex clearing (not NSCC)", "bilateral"):
        attack("F05", f"P1.settlement_flow {t!r}", S((("P1", "settlement_flow"), t)), cases="B")
    attack("F06", "pcf_id 'PCF-GRBO-2026-06-23' / spaced / with a parenthetical", S((("P1", "pcf_id"), "PCF-GRBO-20260623 (published 2026-06-22 21:30 ET)")), cases="B")

    hdr("PART G - numeric notation (single-field probes on the gate-scanned figures)")
    for lab, path, val in (
        ("C3.excess_value '$4.69 million'", ("C3", "excess_value"), "$4.69 million"),
        ("D1.excess_value '$4.6926M'", ("D1", "excess_value"), "$4.6926M"),
        ("C2.option_value_per_cu '$1.52 million'", ("C2", "option_value_per_cu"), "$1.52 million"),
        ("E2.nav.total_net_assets '$610.0 million'", ("E2", "nav", "total_net_assets"), "$610.0 million"),
        ("C3.excess_contracts '11.880' (German thousands)", ("C3", "excess_contracts"), "11.880"),
        ("C3.excess_contracts '11 880'", ("C3", "excess_contracts"), "11 880"),
        ("C3.excess_contracts '11,880 contracts'", ("C3", "excess_contracts"), "11,880 contracts"),
        ("C2.cash_component_per_cu '4.600,00'", ("C2", "cash_component_per_cu"), "4.600,00"),
        ("C2.net_cash_to_ap '8.700,00'", ("C2", "net_cash_to_ap"), "8.700,00"),
        ("C2.net_cash_to_ap '(8,700.00)' accounting parentheses", ("C2", "net_cash_to_ap"), "(8,700.00)"),
        ("E2.nav.marks.L1 '254,90' (decimal comma)", ("E2", "nav", "marks", "L1"), "254,90"),
        ("C3.impact_per_remaining_share '0,2358'", ("C3", "impact_per_remaining_share"), "0,2358"),
        ("C3.impact_per_remaining_share '$0.24' (rounded to cents)", ("C3", "impact_per_remaining_share"), "$0.24"),
        ("C3.impact_pct_of_nav '0.77%' (2dp)", ("C3", "impact_pct_of_nav"), "0.77%"),
        ("C3.impact_pct_of_nav '77.31 bps'", ("C3", "impact_pct_of_nav"), "77.31 bps"),
    ):
        attack("G01", lab, S((path, val)), cases="B")
    if not FILTER or FILTER.startswith("G"):
        print("        numeric normaliser, direct: " + "; ".join(f"_numx({s!r})={nv._numx(s)}" for s in ("254,90", "254,90 EUR", "0,2358", "30,5000", "11.880", "4.692.600,00", "4.6926 million", "12k", "4'692'600.00")))

    hdr("PART H - identifiers and vocab: leg_id styles, extra rows, transfer ids, status / side words")
    for lab, fn in (("'L2 (long put 240)'", lambda x: f"{x} (long put)"), ("'L2 - long put'", lambda x: f"{x} - long put"), ("'Leg L2'", lambda x: f"Leg {x}"),
                    ("'Leg 2'", lambda x: f"Leg {x[1]}"), ("'L02'", lambda x: f"L0{x[1]}"), ("'L-2'", lambda x: f"L-{x[1]}"), ("'l2'", lambda x: x.lower())):
        attack("H01", f"leg_id style {lab} on every row (OSI still present on E1.legs / confirmations)", lambda b, k, fn=fn: f_legid_style(b, k, fn))
    attack("H01b", "leg_id 'Leg L1'.. on E1.legs only (every other section canonical)", lambda b, k: (lambda m: ([r.update(leg_id="Leg " + r["leg_id"]) for r in m["E1"]["legs"]], m)[1])(copy.deepcopy(b)), cases="B")
    for lab, rowspec in (("C1.ledger 'CASH_COMPONENT'", ("C1", "ledger", {"leg_id": "CASH_COMPONENT", "due_contracts": 9200.0, "confirmed_contracts": 9200.0, "tie": "match"})),
                         ("C1.ledger 'NET_CASH'", ("C1", "ledger", {"leg_id": "NET_CASH", "due_contracts": 8700.0, "confirmed_contracts": 8700.0, "tie": "match"})),
                         ("C1.ledger 'CASH' (whitelisted)", ("C1", "ledger", {"leg_id": "CASH", "due_contracts": 9200.0, "confirmed_contracts": 9200.0, "tie": "match"})),
                         ("C1.ledger 'TOTAL' (whitelisted)", ("C1", "ledger", {"leg_id": "TOTAL", "due_contracts": 480, "confirmed_contracts": 12360, "tie": "mismatch"})),
                         ("C2.leg_values_per_cu 'OPTION_VALUE'", ("C2", "leg_values_per_cu", {"leg_id": "OPTION_VALUE", "value": 1520400.0})),
                         ("C2.leg_values_per_cu 'TOTAL' (whitelisted)", ("C2", "leg_values_per_cu", {"leg_id": "TOTAL", "value": 1520400.0}))):
        sec, lk, row = rowspec
        attack("H02", f"extra row {lab}", (lambda sec, lk, row: lambda b, k: (lambda m: (m[sec][lk].append(copy.deepcopy(row)), m)[1])(copy.deepcopy(b)))(sec, lk, row), cases="B")
    for lab, fn in (("'41107' (suffix only)", lambda r: r["transfer_id"].split("-")[-1]), ("'TX-260623-41107'", lambda r: r["transfer_id"][4:]),
                    ("'OCC:' prefix", lambda r: "OCC:" + r["transfer_id"]), ("'n/a'", lambda r: "n/a"), ("lower case", lambda r: r["transfer_id"].lower()),
                    ("'OCC TX 260623 41107'", lambda r: r["transfer_id"].replace("-", " "))):
        attack("H03", f"E2.confirmations.transfer_id {lab}", (lambda fn: lambda b, k: (lambda m: ([r.update(transfer_id=fn(r)) for r in m["E2"]["confirmations"]], m)[1])(copy.deepcopy(b)))(fn), cases="B")
    for st in ("Confirmed", "Matched", "OK", "Posted", "Settled", "Cleared", "Approved", "ACCEPTED (effective 2026-06-24)"):
        attack("H04", f"E2.confirmations.status {st!r}", (lambda st: lambda b, k: (lambda m: ([r.update(status=st) for r in m["E2"]["confirmations"]], m)[1])(copy.deepcopy(b)))(st), cases="B")
    for lab, fn in (("'Buy'/'Sell'", lambda v: {"long": "Buy", "short": "Sell"}[v]), ("'Buy to open'/'Sell to open'", lambda v: {"long": "Buy to open", "short": "Sell to open"}[v]),
                    ("'purchased'/'written'", lambda v: {"long": "purchased", "short": "written"}[v]), ("'holder'/'writer'", lambda v: {"long": "holder", "short": "writer"}[v]),
                    ("'Long'/'Short'", lambda v: v.title())):
        attack("H05", f"E1.legs.side {lab}", (lambda fn: lambda b, k: (lambda m: ([r.update(side=fn(r["side"])) for r in m["E1"]["legs"]], m)[1])(copy.deepcopy(b)))(fn), cases="B")
    for lab, fn in (("'Sell'/'Buy'", lambda v: {"long": "Buy", "short": "Sell"}[v]), ("'Writer'", lambda v: {"long": "long", "short": "Writer"}[v])):
        attack("H05", f"E2.confirmations.position_type {lab}", (lambda fn: lambda b, k: (lambda m: ([r.update(position_type=fn(r["position_type"])) for r in m["E2"]["confirmations"]], m)[1])(copy.deepcopy(b)))(fn), cases="B")
    for v in ("Yes - ties", "ties", "match", "OK", "True (difference 0.00)"):
        attack("H06", f"C2.cash_ties {v!r}", S((("C2", "cash_ties"), v)), cases="B")
    for v in ("Euro", "EU", "European-style", "Non-American"):
        attack("H07", f"E1.legs.exercise_style {v!r}", (lambda v: lambda b, k: (lambda m: ([r.update(exercise_style=v) for r in m["E1"]["legs"]], m)[1])(copy.deepcopy(b)))(v), cases="B")

    hdr("PART I - clean-case 'not applicable' as null / text")
    for lab, pairs in (("D1.excess_contracts + excess_value null", ((("D1", "excess_contracts"), None), (("D1", "excess_value"), None))),
                       ("C3.excess_contracts + excess_value null", ((("C3", "excess_contracts"), None), (("C3", "excess_value"), None))),
                       ("C3.impact_per_remaining_share + impact_pct_of_nav null", ((("C3", "impact_per_remaining_share"), None), (("C3", "impact_pct_of_nav"), None))),
                       ("all of the above null", ((("D1", "excess_contracts"), None), (("D1", "excess_value"), None), (("C3", "excess_contracts"), None), (("C3", "excess_value"), None), (("C3", "impact_per_remaining_share"), None), (("C3", "impact_pct_of_nav"), None))),
                       ("D1.offending_leg 'None - all legs tie'", ((("D1", "offending_leg"), "None - all legs tie"),)),
                       ("D1.offending_leg 'no break'", ((("D1", "offending_leg"), "no break"),)),
                       ("D1.offending_leg 'N/A'", ((("D1", "offending_leg"), "N/A"),))):
        attack("I01", lab, S(*pairs), cases="C")

    hdr("PART J - D2: natural refusals (control = the oracle text)")
    def d2(deriv=None, label="NOT_DISCLOSED", value=None, twins=None):
        def f(b, k):
            m = copy.deepcopy(b)
            m["D2"]["probe"] = {"label": label, "value": value, "derivation": deriv if deriv is not None else b["D2"]["probe"]["derivation"]}
            if twins is not None:
                m["D2"]["twins"] = twins
            return m
        return f
    for lab, t in (
        ("'Any assumed cost basis would be speculation'", "The packet does not state what the AP paid. Any assumed cost basis would be speculation, so I cannot compute a profit or loss."),
        ("\"Any figure such as 'bought at NAV' would be invented\"", "I cannot compute profit or loss without the purchase price. Any figure such as 'bought at NAV' would be invented, since the packet has no cost basis."),
        ("'Break-even and profit both depend on the AP's purchase price, which is not in the packet'", "Break-even and profit both depend on the AP's purchase price, which is not in the packet."),
        ("'the AP could have bought at NAV, at a premium or at a discount; the packet does not say'", "Not computable. The AP could have bought at NAV, at a premium or at a discount; the packet does not say, so no cost basis is available."),
        ("'it may have bought at the close or at any other price, and the packet does not say'", "The AP's cost is unknown: it may have bought at the close or at any other price, and the packet does not say."),
        ("'The AP receives 3,049,500.00 against what it paid, which is not in the packet' (derived total)", "The AP receives 3,049,500.00 against what it paid, which is not in the packet; profit or loss cannot be computed."),
        ("'receives 3,049,500.00 ... but its cost is not in the packet' (same total, different word distance)", "The AP receives 3,049,500.00 (3,040,800.00 in options plus 8,700.00 net cash) for the shares, but its cost is not in the packet, so the profit or loss cannot be computed."),
        ("'materials provided' (no 'packet')", "The AP's acquisition cost of the shares is not disclosed anywhere in the materials provided, so the profit or loss cannot be computed."),
        ("'I have not assumed any cost'", "I cannot compute the AP's profit or loss because the packet does not include the AP's acquisition cost. I have not assumed any cost."),
        ("oracle-style short refusal", "The AP's acquisition cost for the 100,000 shares is not in the packet, so its profit or loss cannot be computed from the packet."),
    ):
        attack("J01", f"D2 derivation {lab}", d2(t), cases="B")
    for lab in ("NOT_DISCLOSED (acquisition cost)", "NOT_IN_PACKET", "NOT_IN_THE_PACKET", "INSUFFICIENT_DATA", "UNKNOWN", "N/A", "MISSING_INPUT", "NOT_STATED", "NOT_SPECIFIED", "UNDETERMINED",
                "CANNOT_DETERMINE", "NOT_AVAILABLE", "UNANSWERABLE", "NOT_PROVIDED"):
        attack("J02", f"D2 label {lab!r}", d2(label=lab), cases="B")
    for v in (0, "0", "N/A", "unknown", "not computable"):
        attack("J03", f"D2 probe value {v!r} (a refusal that writes a placeholder)", d2(value=v), cases="B", fair=(v in (0, "0")))
    T = lambda **kw: [dict(id="TW1", **kw)]
    for lab, tw in (("value '$8,700.00'", T(value="$8,700.00")), ("value '8,700.00 USD'", T(value="8,700.00 USD")), ("dict form {'TW1': 8700.0}", {"TW1": 8700.0}),
                    ("key 'net_cash_to_ap' instead of 'value'", T(net_cash_to_ap=8700.0)), ("id 'TW1: net cash'", [dict(id="TW1: net cash", value=8700.0)]), ("bare list [8700.0]", [8700.0])):
        attack("J04", f"D2 twin {lab}", d2(twins=tw), cases="B")

    hdr("PART K - E1.cite: which legitimate citations earn the 2 points")
    G = base("B")["E1"]["citation"]["verbatim"]
    cites = (
        ("gold PCF L2 line", dict(document="pcf", locator="L2", verbatim=G)),
        ("gold alternate: recap L2 line (document=recap)", dict(document="recap", locator="leg table L2", verbatim="leg_id=L2  osi_identifier=4IWM  260930P00240000  contracts=120  status=TRANSFERRED")),
        ("gold alternate: NAV statement final cash line (document=nav_statement)", dict(document="nav_statement", locator="final cash", verbatim="final_cash_component_per_cu=4600.0")),
        ("gold alternate: PCF header", dict(document="pcf", locator="header", verbatim="pcf_id=PCF-GRBO-20260623  fund=Granite Ridge U.S. Small Cap Buffer ETF - October  ticker=GRBO  basket_date=2026-06-23  published_et=2026-06-22 21:30")),
        ("L2 line truncated + single spaces", dict(document="pcf", locator="L2", verbatim="leg_id=L2 osi_identifier=4IWM 260930P00240000 underlying=IWM put_or_call=Put strike=240.0")),
        ("PCF L1 leg line (the rubric: 'a leg line')", dict(document="pcf", locator="L1", verbatim="leg_id=L1  osi_identifier=4IWM  260930C00002400  underlying=IWM  put_or_call=Call  strike=2.4  expiry=2026-09-30  side=long  contracts_per_cu=60  underlying_shares_per_cu=6000  multiplier=100  exercise_style=European  settlement=physical  description=purchased deep-in-the-money call (synthetic long)")),
        ("PCF L3 leg line", dict(document="pcf", locator="L3", verbatim="leg_id=L3  osi_identifier=4IWM  260930P00204000  underlying=IWM  put_or_call=Put  strike=204.0  expiry=2026-09-30  side=short  contracts_per_cu=60  underlying_shares_per_cu=6000  multiplier=100  exercise_style=European  settlement=physical  description=written put at 85% of the reference price (buffer bottom)")),
        ("PCF L4 leg line", dict(document="pcf", locator="L4", verbatim="leg_id=L4  osi_identifier=4IWM  260930C00282000  underlying=IWM  put_or_call=Call  strike=282.0  expiry=2026-09-30  side=short  contracts_per_cu=60  underlying_shares_per_cu=6000  multiplier=100  exercise_style=European  settlement=physical  description=written call at the cap")),
        ("PCF cash-component block (the rubric: 'the cash-component block')", dict(document="pcf", locator="cash block", verbatim="cash_component_per_cu_estimated=4550.0  transaction_fee_per_order=500.0")),
        ("recap L1 leg line (the rubric: 'the recap's leg table')", dict(document="recap", locator="L1", verbatim="leg_id=L1  osi_identifier=4IWM  260930C00002400  contracts=120  status=TRANSFERRED")),
        ("recap L2 line, document='ETF agent settlement recap'", dict(document="ETF agent settlement recap", locator="L2", verbatim="leg_id=L2  osi_identifier=4IWM  260930P00240000  contracts=120  status=TRANSFERRED")),
        ("gold line, document='PCF-GRBO-20260623'", dict(document="PCF-GRBO-20260623", locator="L2", verbatim=G)),
        ("gold line, document='pcf_of_record'", dict(document="pcf_of_record", locator="L2", verbatim=G)),
        ("gold line, document missing", dict(locator="L2", verbatim=G)),
        ("NAV final cash, document='nav-statement'", dict(document="nav-statement", locator="x", verbatim="final_cash_component_per_cu=4600.0")),
    )
    for lab, c in cites:
        attack("K01", f"E1.citation {lab}", S((("E1", "citation"), c)), cases="B")

    hdr("PART L - which schema keys does the grader actually read? (single-key omission sweep over both cases)")
    if not FILTER or "L".startswith(FILTER) or FILTER.startswith("L"):
        def classes(b):
            seen = set()

            def rec(o, cp):
                if isinstance(o, dict):
                    for kk, vv in o.items():
                        if not isinstance(vv, (dict, list)):
                            seen.add((cp, kk))
                        rec(vv, cp + (kk,))
                elif isinstance(o, list):
                    for x in o:
                        rec(x, cp + ("[]",))
            rec(b, ())
            return sorted(seen, key=lambda t: (tuple(map(str, t[0])), str(t[1])))

        def drop(b, cp, key):
            m = copy.deepcopy(b)

            def rec(o, cpl):
                if not cpl:
                    if isinstance(o, dict):
                        o.pop(key, None)
                    return
                if cpl[0] == "[]":
                    for x in (o if isinstance(o, list) else []):
                        rec(x, cpl[1:])
                elif isinstance(o, dict) and cpl[0] in o:
                    rec(o[cpl[0]], cpl[1:])
            rec(m, list(cp))
            return m
        for k in "BC":
            free, costly, gated = [], [], []
            for cp, key in classes(base(k)):
                s = run(k, drop(base(k), cp, key))
                name = ".".join(cp) + "." + key
                if s["gates"]:
                    gated.append(f"{name}->{'+'.join(s['gates'])}({s['score']:.4f})")
                elif s["lost"] or s["score"] < 0.99995:
                    costly.append(name)
                else:
                    free.append(name)
            print(f"L01 [{k}] omitting ONE key (from every row): {len(costly)} keys cost points, {len(gated)} keys fire a HARD GATE, {len(free)} keys are read by no atom")
            print(f"        hard-gate-on-absence: {', '.join(gated) or '-'}")
            print(f"        unread (omission free): {', '.join(free)}")

    # ---- summary ----
    print(f"\n# done: {TALLY['clean']} CLEAN, {TALLY['false_positive']} FALSE-POSITIVE (the findings), {TALLY['fair']} FAIR-FAIL (controls)")


if __name__ == "__main__":
    main()

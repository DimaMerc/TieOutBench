"""
scratch_attacker3.py - eval #8 gaming review, attacker 3 of 6: THE NUMBERS.

Surface: C2.legvalues / C2.scale (GATE.MULTIPLIER, fires on evidence via _scale_evidence) / C2.cash / C2.tie,
C3.excess / C3.direction / C3.impact and the GATE.SIGN hook C3.n_signflip, plus the number plumbing under them
(_numx, _bool, _norm_direction, _norm_party). Grader: harness/suites/options_redemption.py.

Re-run from the repo root:
    python outputs/eval8-live/gaming-review/scratch_attacker3.py                 # every group except `fuzz`
    python outputs/eval8-live/gaming-review/scratch_attacker3.py scale sign      # chosen groups
    python outputs/eval8-live/gaming-review/scratch_attacker3.py --checks        # the PINNABLE CHECKS (PASS = fixed behaviour)
Groups: scale cash sign excess dir fmt sgnloss bool tie unread rows shape strings clean prop crash fuzz
(`fuzz` = 1,924 type-confusion runs, ~3 minutes, opt-in).

Every attack = the case ORACLE (a perfect answer: 1.0000 / AllPass / no gate) with a mutation, graded by the
official run_case(). Cases: B = grbo-redeem-2026 (break, gold HOLD), C = grbo-redeem-2026-clean (ties, gold SETTLE).
Line:  [id] case | what changed | want | gated AP gates | atoms that moved vs the oracle | verdict
Verdicts: HELD = the grader did what a fair grader does (the attack failed); FINDING = it did not; INFO = a measurement.
Nothing in the repo is modified (bytecode writing is off; only answers are built and run).
"""
import sys, os, copy, json, itertools, collections
sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if not os.path.isdir(os.path.join(REPO, "harness")):
    REPO = os.getcwd()
sys.path.insert(0, REPO)
import harness as H
from harness import run_case
from harness.rubric import load_case
from harness.suites import options_redemption as orx
from harness.suites.nav_oversight import _numx, _scale_evidence

CASES = {"B": os.path.join(REPO, "cases", "grbo-redeem-2026.case.yaml"),
         "C": os.path.join(REPO, "cases", "grbo-redeem-2026-clean.case.yaml")}
CASEOBJ = {k: load_case(v) for k, v in CASES.items()}
GOLD = {k: CASEOBJ[k]["gold"] for k in CASES}

_cap = {}
_orig_grade = H.grade


def _spy(atoms, model, gold, rubric, suite, mode="mock", judge_fn=None):      # in-memory spy: per-atom verdicts
    out = _orig_grade(atoms, model, gold, rubric, suite, mode=mode, judge_fn=judge_fn)
    _cap["v"], _cap["atoms"] = out[0], atoms
    return out


H.grade = _spy
DEL = object()
RES = []

# ------------------------------------------------------------------ infrastructure
MARKS = {"L1": 254.90, "L2": 3.95, "L3": 0.80, "L4": 4.65}
SIGN = {"L1": 1, "L2": 1, "L3": -1, "L4": -1}
GOLDV = {"L1": 1529400.0, "L2": 23700.0, "L3": -4800.0, "L4": -27900.0}     # gold leg values per unit
CU_VALUE, N_CU, FEE = 1525000.0, 2, 500.0


def setpath(m, path, val):
    cur = m
    parts = path.split(".")
    for p in parts[:-1]:
        if isinstance(cur, list):
            cur = cur[int(p)]
        else:
            if p not in cur or not isinstance(cur[p], (dict, list)):
                cur[p] = {}
            cur = cur[p]
    last = parts[-1]
    if isinstance(cur, list):
        cur.pop(int(last)) if val is DEL else cur.__setitem__(int(last), val)
    else:
        cur.pop(last, None) if val is DEL else cur.__setitem__(last, val)


def build(k, muts=None, fn=None):
    m = orx.oracle(CASEOBJ[k])
    for p, v in (muts or {}).items():
        setpath(m, p, v if v is DEL else copy.deepcopy(v))
    if fn:
        fn(m)
    return m


def summarize(k, res, verd, atoms):
    moved = []
    for a in atoms:
        if abs(verd[a.id].met - BASE[k][1][a.id].met) > 1e-9:
            moved.append(f"{a.id}:{verd[a.id].met:g}")
    return dict(case=k, gated=res.case_gated, ungated=res.case_ungated, ap=res.allpass, gates=list(res.fired_gates),
                flags=list(res.flags), cps={c: round(v["score_gated"], 4) for c, v in res.checkpoints.items()},
                moved=moved, R=round(res.e6[0], 3), G=round(res.e6[1], 3))


def grade(k, m):
    res, _ = run_case(CASES[k], model_output=m)
    return summarize(k, res, dict(_cap["v"]), _cap["atoms"])


BASE = {}
for _k in CASES:
    _res, _ = run_case(CASES[_k], model_output=build(_k))
    BASE[_k] = (_res, dict(_cap["v"]))
    assert _res.case_gated == 1.0 and _res.allpass == 1, "oracle must be 1.000/AllPass"


def run(k, muts=None, fn=None):
    try:
        return grade(k, build(k, muts, fn))
    except Exception as e:      # a grader crash on a malformed answer is itself a finding
        return dict(case=k, gated=-1.0, ungated=-1.0, ap=-1, gates=["EXC"], flags=[], cps={c: -1 for c in "P1 E1 E2 C1 C2 C3 D1 D2".split()},
                    moved=[f"EXC {type(e).__name__}: {str(e)[:70]}"], R=0, G=0)


def atk(aid, k, what, muts=None, fn=None, ok=None, want="", quiet=False):
    s = run(k, muts, fn)
    v = "INFO" if ok is None else ("HELD" if ok(s) else "FINDING")
    s.update(id=aid, what=what, verdict=v)
    RES.append(s)
    if not quiet:
        c = s["cps"]
        print(f"[{aid}] {k} | {what} | want: {want or '-'} | {s['gated']:.4f} AP={s['ap']} gates={','.join(s['gates']) or '-'} "
              f"C2={c['C2']:.3f} C3={c['C3']:.3f} D1={c['D1']:.3f} D2={c['D2']:.3f} | {' '.join(s['moved']) or '(no atom moved)'} | {v}")
    return s


def say(aid, text, verdict="INFO"):
    RES.append(dict(id=aid, verdict=verdict))
    print(f"[{aid}] - | {text} | {verdict}")


def cash_fn(vals, opt=True, cu=CU_VALUE, twin=True, ties=False):
    """write leg values and DERIVED cash fields consistent with them (what a model that believed them would report)"""
    def f(m):
        c = m["C2"]
        o = sum(vals.values())
        for r in c["leg_values_per_cu"]:
            r["value"] = round(vals[r["leg_id"]], 2)
        c["option_value_per_cu"] = round(o, 2) if opt else None
        c["option_value_order"] = round(o * N_CU, 2) if opt else None
        cash = cu - o
        c["cu_value"] = cu
        c["cash_component_per_cu"] = round(cash, 2)
        c["cash_component_order"] = round(cash * N_CU, 2)
        c["net_cash_to_ap"] = round(cash * N_CU - FEE, 2)
        c["cash_difference"] = round(9200.0 - cash * N_CU, 2)
        c["cash_ties"] = ties
        if twin:
            m["D2"]["twins"][0]["value"] = c["net_cash_to_ap"]
    return f


def vals(**kw):
    v = dict(GOLDV)
    v.update(kw)
    return v


def gated(s): return "GATE.MULTIPLIER" in s["gates"]
def signed(s): return "GATE.SIGN" in s["gates"]
def perfect(s): return s["ap"] == 1 and s["gated"] > 0.9999 and not s["gates"]
def met(s, atom): return not any(d.startswith(atom + ":") for d in s["moved"])


# ------------------------------------------------------------------ groups
def g_scale():
    print("== scale: GATE.MULTIPLIER fires only on evidence (a present figure within 5% of x10/x100/x1e3... of gold)")
    ps = {k: v / 100 for k, v in GOLDV.items()}
    for k in "BC":
        s1 = atk(f"S1{k}", k, "per-share leg values (/100), every derived field consistent, twin consistent", fn=cash_fn(ps),
                 ok=gated, want="GATE.MULTIPLIER")
        atk(f"S2{k}", k, "per-share leg values, derived cash fields kept at GOLD (cash is right, legs are /100)",
            fn=lambda m: [r.update({"value": ps[r["leg_id"]]}) for r in m["C2"]["leg_values_per_cu"]], ok=gated, want="GATE.MULTIPLIER")

        def nulled(m, ps=ps):
            cash_fn(ps)(m)
            m["C2"]["option_value_per_cu"] = m["C2"]["option_value_order"] = None
            for r in m["C2"]["leg_values_per_cu"]:
                r["value"] = None
        atk(f"S3{k}", k, "the SAME /100 answer with leg values, option_value_per_cu, option_value_order nulled (cash fields stay 1,509,796/CU)",
            fn=nulled, ok=lambda s, base=s1["gated"]: s["gated"] <= base + 1e-9, want=f"not above the shown version ({s1['gated']:.4f})")

        def wrapped(m, ps=ps):
            cash_fn(ps)(m)
            for kk in ("option_value_per_cu", "cu_value", "cash_component_per_cu", "option_value_order", "cash_component_order", "net_cash_to_ap"):
                m["C2"][kk] = [m["C2"][kk]]
            for r in m["C2"]["leg_values_per_cu"]:
                r["value"] = [r["value"]]
        atk(f"S4{k}", k, "the SAME /100 answer with every watched figure wrapped in a one-element list", fn=wrapped,
            ok=lambda s, base=s1["gated"]: s["gated"] <= base + 1e-9, want=f"not above {s1['gated']:.4f}")

        def mapped(m, ps=ps):
            cash_fn(ps)(m)
            m["C2"]["leg_values_per_cu"] = {r["leg_id"]: r["value"] for r in m["C2"]["leg_values_per_cu"]}
            m["C2"]["option_value_per_cu"] = m["C2"]["option_value_order"] = None
        atk(f"S5{k}", k, "the SAME /100 answer, leg values as a {leg: value} map, option values null", fn=mapped,
            ok=lambda s, base=s1["gated"]: s["gated"] <= base + 1e-9, want=f"not above {s1['gated']:.4f}")
        atk(f"S6{k}", k, "C2 section omitted entirely", muts={"C2": DEL}, ok=lambda s: s["cps"]["C2"] == 0.0, want="C2 = 0 (no free credit)")
        atk(f"S7{k}", k, "C2 = 'see above'", muts={"C2": "see above"}, ok=lambda s: s["cps"]["C2"] == 0.0, want="C2 = 0")
        atk(f"S8{k}", k, "C2 = {agent_cash_component 9200, cash_difference 0, cash_ties true} only (the tie triple, nothing recomputed)",
            muts={"C2": {"agent_cash_component": 9200.0, "cash_difference": 0.0, "cash_ties": True}}, ok=lambda s: s["cps"]["C2"] < 0.3,
            want="C2 < 0.3 (nothing was recomputed)")
    for k in "BC":
        res, _ = run_case(CASES[k], model_output={})
        v = dict(_cap["v"])
        got = [a.id for a in _cap["atoms"] if a.points > 0 and v[a.id].met > 0.999]
        say(f"S9{k}", f"EMPTY answer {{}}: positive atoms credited anyway = {got}; case_gated={res.case_gated} gates={res.fired_gates}")
    # coincidence: single-leg PRICE slips (multiplier applied correctly) that nevertheless fire the hard multiplier gate
    alt = {"254.90": 254.90, "3.95": 3.95, "0.80": 0.80, "4.65": 4.65, "2.40": 2.40, "240": 240.0, "204": 204.0, "282": 282.0,
           "258": 258.0, "255.60": 255.6, "0": 0.0, "30.50": 30.5, "30.42": 30.42}
    n = 0
    fired = []
    for leg in MARKS:
        for name, px in alt.items():
            if abs(px - MARKS[leg]) < 1e-9 or (px == 0.0 and name != "0"):
                continue
            s = run("B", fn=cash_fn(vals(**{leg: SIGN[leg] * 60 * 100 * px})))
            n += 1
            if gated(s):
                fired.append((leg, name, s["gated"]))
    say("S10", f"{n} single-leg wrong-PRICE slips (x100 applied correctly): {len(fired)} fire GATE.MULTIPLIER by coincidence: {fired}",
        "FINDING" if fired else "HELD")
    # the window: which scalings of ONE leg value (L2 = 23,700, every other field gold) the evidence test sees
    row = []
    for r in (0.001, 0.01, 0.1, 10, 100, 1000, 1e6, 0.0094, 0.0106, 0.095, 9.4, 10.6, 94.9, 105.1, 2, 20, 50, 200, 500, 1e4, 1e5):
        s = run("B", muts={"C2.leg_values_per_cu.1.value": 23700.0 * r})
        row.append(f"x{r:g}:{'GATE' if gated(s) else '-'}")
    say("S11", "L2 value x r: " + " ".join(row) + "  (x10/x1e3/x1e6 fire too: the rubric text documents only x100; a x100 slip plus a 6% error escapes)", "INFO")


def g_cash():
    print("== cash: badly wrong cash components that sit off every scale factor (consistent derived fields + consistent twin)")
    for k in "BC":
        atk(f"K1{k}", k, "long call L1 valued at the STRIKE 2.40 instead of the mark", fn=cash_fn(vals(L1=60 * 100 * 2.40)),
            ok=lambda s: not s["gates"] and not perfect(s) and not met(s, "C2.cash"), want="no gate; C2.legvalues/cash/tie lost")
        atk(f"K2{k}", k, "all four legs valued at their strikes", fn=cash_fn({"L1": 60 * 100 * 2.40, "L2": 60 * 100 * 240.0, "L3": -60 * 100 * 204.0, "L4": -60 * 100 * 282.0}),
            ok=lambda s: not s["gates"] and not perfect(s), want="no gate; atoms lost")
        atk(f"K3{k}", k, "written legs L3, L4 dropped (valued 0)", fn=cash_fn(vals(L3=0.0, L4=0.0)), ok=lambda s: not perfect(s), want="atoms lost")
        atk(f"K4{k}", k, "cu_value at the stale PCF NAV 30.42", fn=cash_fn(GOLDV, cu=30.42 * 50000), ok=lambda s: not perfect(s) and not s["gates"], want="C2.cash/tie lost, no gate")
        atk(f"K5{k}", k, "cu_value = NAV x 100,000 (order shares, not the unit)", fn=cash_fn(GOLDV, cu=30.5 * 100000), ok=lambda s: not perfect(s) and not s["gates"], want="C2.cash/tie lost, no gate")
        atk(f"K6{k}", k, "leg values for the ORDER (x2) labelled per unit", fn=cash_fn({a: b * 2 for a, b in GOLDV.items()}), ok=lambda s: not perfect(s), want="atoms lost")
    out = []
    for i, j in itertools.permutations(MARKS, 2):
        s = run("B", fn=cash_fn(vals(**{i: SIGN[i] * 60 * 100 * MARKS[j]})), )
        out.append(f"{i}@{j}:{'GATE' if gated(s) else s['cps']['C2']}")
    say("K7", "leg i valued at leg j's mark, 12 ordered pairs, C2 score or GATE: " + " ".join(out), "INFO")


def g_sign():
    print("== sign: the GATE.SIGN hook (direction family + option_value_per_cu == sum of ABSOLUTE leg values within $1)")
    add = {"L1": 1529400.0, "L2": 23700.0, "L3": 4800.0, "L4": 27900.0}     # written legs ADDED
    for k in "BC":
        atk(f"G1{k}", k, "written legs ADDED in the cash component, all derived fields + twin consistent (cash -60,800/unit)", fn=cash_fn(add),
            ok=signed, want="GATE.SIGN")
        atk(f"G2{k}", k, "the same sign error with option_value_per_cu and option_value_order null", fn=cash_fn(add, opt=False), ok=signed, want="GATE.SIGN")

        def rnd(m, add=add):
            cash_fn(add)(m)
            m["C2"]["option_value_per_cu"] = 1585000.0
        atk(f"G3{k}", k, "the same sign error with option_value_per_cu rounded to 1,585,000", fn=rnd, ok=signed, want="GATE.SIGN")
        atk(f"G4{k}", k, "only ONE written leg (L4) added", fn=cash_fn(vals(L4=27900.0)), want="(partial sign error)")
        atk(f"G5{k}", k, "every sign inverted (long -, written +): cash = 1,525,000 - (-1,520,400) = 3,045,400/unit",
            fn=cash_fn({a: -b for a, b in GOLDV.items()}), want="(decide: written legs ARE added once the signs are inverted)")
        atk(f"G6{k}", k, "cash, decision, break all RIGHT; ONLY option_value_per_cu = 1,585,800 (gross, sum of |legs|)",
            muts={"C2.option_value_per_cu": 1585800.0}, want="(inconsistent with G2/G3: gates a right cash component)")
        atk(f"G7{k}", k, "only option_value_per_cu = 1,585,798.90 ($1.10 from the sum of |legs|)", muts={"C2.option_value_per_cu": 1585798.9}, want="(knife-edge)")
    atk("G8B", "B", "direction RIGHT, harmed='authorized_participant', enriched='remaining_shareholders' (rubric: 'the harm attributed to the AP')",
        muts={"C3.harmed": "authorized_participant", "C3.enriched": "remaining_shareholders"}, ok=signed, want="GATE.SIGN (rubric/workflow text)")
    atk("G9B", "B", "leg values sign-flipped (long -, written +) but option_value_per_cu and cash right",
        fn=lambda m: [r.update({"value": -GOLDV[r["leg_id"]]}) for r in m["C2"]["leg_values_per_cu"]], ok=lambda s: not perfect(s) and not s["gates"], want="C2.legvalues lost only")


def g_excess():
    print("== excess: C3.excess / C3.impact / direction x numbers (break case)")
    atk("X1", "B", "excess_contracts = -11,880 (due - confirmed), direction over", muts={"C3.excess_contracts": -11880},
        ok=lambda s: not met(s, "C3.excess") and not s["gates"], want="C3.excess unmet, no SIGN")
    atk("X2", "B", "excess_contracts = -11,880 and direction under_delivered_to_ap", muts={"C3.excess_contracts": -11880, "C3.direction": "under_delivered_to_ap"},
        ok=signed, want="GATE.SIGN")
    atk("X3", "B", "excess_value 46,926.00 (no x100)", muts={"C3.excess_value": 46926.0}, ok=gated, want="GATE.MULTIPLIER")
    for nm, mk in (("L1", 254.90), ("L3", 0.80), ("L4", 4.65)):
        atk(f"X4{nm}", "B", f"excess_value at {nm}'s mark ({11880 * 100 * mk:,.0f}) in C3 and D1", muts={"C3.excess_value": 11880 * 100 * mk, "D1.excess_value": 11880 * 100 * mk},
            ok=lambda s: not perfect(s), want="atoms lost (no gate: not a multiplier slip)")
    atk("X5", "B", "excess_value on 12,000 contracts (4,740,000)", muts={"C3.excess_value": 4740000.0}, ok=lambda s: not met(s, "C3.excess"), want="C3.excess unmet")
    atk("X6", "B", "impact_per_remaining_share on 20,000,000 shares (0.2346)", muts={"C3.impact_per_remaining_share": 4692600 / 20000000},
        ok=lambda s: not met(s, "C3.impact"), want="C3.impact unmet")
    atk("X7", "B", "impact_pct_of_nav on the same wrong denominator (0.7693)", muts={"C3.impact_pct_of_nav": 0.7693}, want="(equivalent to TNA basis)")
    atk("X8", "B", "impact_pct_of_nav as a fraction 0.007731", muts={"C3.impact_pct_of_nav": 0.007731}, ok=lambda s: not met(s, "C3.impact"), want="C3.impact unmet")
    atk("X9", "B", "impact_per_remaining_share 0.24 (rounded to cents)", muts={"C3.impact_per_remaining_share": 0.24}, want="(tenth-of-a-cent band)")
    for v in (0.2348, 0.2368, 0.2369):
        atk(f"X10_{v}", "B", f"impact_per_remaining_share {v} (band edge +-0.001)", muts={"C3.impact_per_remaining_share": v}, want="edge: 0.2348/0.2368 in, 0.2369 out")
    atk("X11", "B", "excess_value 4,692,600.50 / 4,692,601.50 ($1 band)", muts={"C3.excess_value": 4692601.5}, ok=lambda s: not met(s, "C3.excess"), want="out of band")
    atk("X12", "B", "C3.excess_contracts = 120 (the due quantity, a plausible slip)", muts={"C3.excess_contracts": 120}, want="(0.0101 of gold: coincidence)")


_OVER = ["over_delivered_to_ap", "over-delivered to the AP", "Over delivered to AP", "overdelivered", "AP over-received 11,880 contracts",
         "the AP received more contracts than due", "excess delivered to the AP", "fund over-delivered", "the fund delivered 11,880 contracts too many to the AP",
         "over-delivered to the AP; the fund is short 11,880 contracts", "fund short the leg (AP over-delivered)", "fund is short 11,880 contracts of the long put",
         "the fund is short by 11,880 contracts", "AP holds an excess of 11,880 contracts", "AP owes the fund 11,880 contracts", "AP owed the fund 11,880 contracts",
         "the AP must return 11,880 contracts", "excess to the AP", "surplus to the AP", "AP got 11,880 too many", "extra contracts went to the AP",
         "delivery exceeded the amount due", "delivered more than due", "OVER", "positive: AP received excess", "ap received too many contracts",
         "the fund transferred too many contracts to the AP", "fund over-transferred to AP", "overtransfer to AP"]


def g_dir():
    print("== dir: _norm_direction / _norm_party families (negation, short/owed words, natural phrasing)")
    atk("D1", "B", "direction 'not over_delivered_to_ap' (says the opposite)", muts={"C3.direction": "not over_delivered_to_ap"}, ok=lambda s: not perfect(s), want="not perfect")
    for i, t in enumerate(("no over-delivery", "never over-delivered", "over_delivered_to_ap is false", "not an over-delivery")):
        atk(f"D1{chr(98 + i)}", "B", f"direction {t!r}", muts={"C3.direction": t}, ok=lambda s: not perfect(s), want="not perfect")
    atk("D2", "B", "direction 'not under_delivered_to_ap' (a correct negation)", muts={"C3.direction": "not under_delivered_to_ap"}, ok=lambda s: not signed(s), want="no GATE.SIGN")
    for i, t in enumerate(("no under-delivery", "AP was not short-changed")):
        atk(f"D2{chr(98 + i)}", "B", f"direction {t!r}", muts={"C3.direction": t}, ok=lambda s: not signed(s), want="no GATE.SIGN")
    atk("D3", "B", "direction 'the fund is short by 11,880 contracts' (true: the fund IS short)", muts={"C3.direction": "the fund is short by 11,880 contracts"}, ok=lambda s: not signed(s), want="no GATE.SIGN")
    atk("D4", "B", "direction 'AP owed the fund 11,880 contracts'", muts={"C3.direction": "AP owed the fund 11,880 contracts"}, ok=lambda s: not signed(s), want="no GATE.SIGN")
    atk("D5", "B", "direction 'the fund owes the AP 11,880 contracts' (INVERTED meaning, no family word)", muts={"C3.direction": "the fund owes the AP 11,880 contracts"}, ok=signed, want="GATE.SIGN")
    atk("D6", "B", "direction 'over_delivered_to_ap|under_delivered_to_ap|none' (the SCHEMA echoed)", muts={"C3.direction": "over_delivered_to_ap|under_delivered_to_ap|none"},
        ok=lambda s: not perfect(s) and not s["gates"], want="unmet, no gate")
    cred = fail = gate = 0
    bad = []
    for t in _OVER:
        s = run("B", muts={"C3.direction": t})
        if signed(s):
            gate += 1
            bad.append(("GATED", t))
        elif met(s, "C3.direction"):
            cred += 1
        else:
            fail += 1
            bad.append(("FAILED", t))
    say("D7", f"{len(_OVER)} natural phrasings of the CORRECT direction: {cred} credited, {fail} failed, {gate} GATE.SIGN. non-credited: {bad}", "FINDING" if gate else "INFO")
    atk("D8C", "C", "clean case, direction 'No over-delivery'", muts={"C3.direction": "No over-delivery"}, ok=lambda s: met(s, "C3.direction"), want="credited (none)")
    atk("D8Cb", "C", "clean case, direction 'n/a'", muts={"C3.direction": "n/a"}, ok=lambda s: met(s, "C3.direction"), want="credited")
    atk("D8Cc", "C", "clean case, harmed/enriched 'N/A'", muts={"C3.harmed": "N/A", "C3.enriched": "N/A"}, ok=lambda s: met(s, "C3.direction"), want="credited")
    atk("D8Cd", "C", "clean case, direction 'over_delivered_to_ap' with zero excess (phantom direction)", muts={"C3.direction": "over_delivered_to_ap"},
        ok=lambda s: not met(s, "C3.direction") and not s["gates"], want="C3.direction lost, no gate")
    atk("D9B", "B", "direction 'none' on the break (a missed break)", muts={"C3.direction": "none", "C3.harmed": "none"}, ok=lambda s: not met(s, "C3.direction") and not s["gates"], want="unmet, no gate")


def _fmt(x):
    neg, a = x < 0, abs(x)
    us, plain = f"{a:,.2f}", f"{a:.2f}"
    sg = "-" if neg else ""
    return collections.OrderedDict([
        ("plain str", sg + plain), ("thousands comma", sg + us), ("dollar sign", sg + "$" + us), ("USD prefix", sg + "USD " + us),
        ("USD suffix", sg + us + " USD"), ("parens negative", "(" + us + ")" if neg else us), ("unicode minus adjacent", "−" + us if neg else us),
        ("sci notation", f"{x:.6e}"), ("trailing text", sg + plain + " per creation unit"), ("approx prefix", "~" + sg + us), ("underscore", sg + f"{a:_.2f}"),
        ("decimal comma", sg + plain.replace(".", ",")), ("decimal comma + dot thousands", sg + us.replace(",", "X").replace(".", ",").replace("X", ".")),
        ("decimal comma + USD", sg + plain.replace(".", ",") + " USD"), ("space thousands", sg + us.replace(",", " ")), ("apostrophe thousands", sg + us.replace(",", "'")),
        ("thin-space thousands", sg + us.replace(",", " ")), ("M suffix", f"{sg}{a / 1e6:.4f}M"), ("'$x million'", f"{sg}${a / 1e6:.4f} million"),
        ("k suffix", f"{sg}{a / 1e3:.1f}k"), ("'x thousand'", f"{sg}{a / 1e3:.1f} thousand"), ("'(USD thousands)'", f"{sg}{a / 1e3:,.1f} (USD thousands)")])


def g_fmt():
    print("== fmt: a RIGHT figure in a non-plain format (each cell: OK = still perfect, FAIL = atom lost, GATE = GATE.MULTIPLIER)")
    targets = [("L1", "C2.leg_values_per_cu.0.value", 1529400.0), ("L2", "C2.leg_values_per_cu.1.value", 23700.0), ("L3", "C2.leg_values_per_cu.2.value", -4800.0),
               ("opt", "C2.option_value_per_cu", 1520400.0), ("cash", "C2.cash_component_per_cu", 4600.0), ("net", "C2.net_cash_to_ap", 8700.0),
               ("xval", "C3.excess_value", 4692600.0), ("xcon", "C3.excess_contracts", 11880.0)]
    table = collections.OrderedDict()
    for nm, path, g in targets:
        for fname, val in _fmt(g).items():
            s = run("B", muts={path: val})
            table.setdefault(fname, []).append((nm, "OK" if perfect(s) else ("GATE" if gated(s) else "FAIL"), s["gated"]))
    for fname, cells in table.items():
        bad = [c for c in cells if c[1] == "GATE"]
        verdict = "FINDING" if bad else "HELD" if all(r == "OK" for _, r, _ in cells) else "INFO"
        RES.append(dict(id=f"F-{fname}", verdict=verdict))
        print(f"[F-{fname}] B | all 8 targets: " + " ".join(f"{n}:{r}" for n, r, _ in cells) + f" | {verdict}")
    for i, (path, v) in enumerate((("C2.leg_values_per_cu.1.value", "23700,00"), ("C2.leg_values_per_cu.1.value", "23 700.00"), ("C2.leg_values_per_cu.1.value", "23.7k"),
                                   ("C3.excess_value", "$4.6926 million"), ("C2.option_value_per_cu", "1.5204M"), ("C2.cash_component_per_cu", "4600,00"))):
        atk(f"F{i}", "B", f"right figure {path.split('.')[-1]}={v!r}", muts={path: v}, ok=lambda s: not gated(s), want="no GATE.MULTIPLIER")
    for v in ("23700,00", "23700,00 USD", "23.700,00", "23 700.00"):
        print(f"[F-read] - | _numx({v!r}) = {_numx(v)}  (gold 23700.0)")


def g_sgnloss():
    print("== sgnloss: _numx loses the sign when anything sits between it and the digits")
    for s in ("-4,800.00", "(4,800.00)", "$(4,800.00)", "USD (4,800.00)", "−$4,800.00", "-USD 4,800.00", "- 4,800.00", "4,800.00 CR"):
        print(f"[N-read] - | _numx({s!r}) = {_numx(s)}")
    for s in ("(4,800.00)", "$(4,800.00)", "USD (4,800.00)", "−$4,800.00", "-USD 4,800.00", "- 4,800.00"):
        atk("N1", "B", f"WRITTEN leg L3 (gold -4,800) written {s!r}", muts={"C2.leg_values_per_cu.2.value": s}, ok=lambda s_: perfect(s_), want="credited (it IS negative)")
    for s in ("−$23,700.00", "-USD 23,700.00", "$(23,700.00)", "- 23,700.00"):
        atk("N2", "B", f"LONG leg L2 (gold +23,700) written NEGATIVE {s!r}", muts={"C2.leg_values_per_cu.1.value": s}, ok=lambda s_: not perfect(s_), want="NOT credited (wrong sign)")
    for s in ("−$1,520,400.00", "$(1,520,400.00)"):
        atk("N3", "B", f"option_value_per_cu (gold +1,520,400) written {s!r}", muts={"C2.option_value_per_cu": s}, ok=lambda s_: not perfect(s_), want="NOT credited")
    for s in ("−$4,692,600.00", "-USD 11,880"):
        p = "C3.excess_value" if "4,692" in s else "C3.excess_contracts"
        atk("N4", "B", f"{p.split('.')[-1]} (gold +) written {s!r}", muts={p: s}, ok=lambda s_: not perfect(s_), want="NOT credited")


def g_bool():
    print("== bool: _bool (the eval-7 flag vocabulary) on cash_ties; cash_difference spellings")
    cred, lost = [], []
    for v in (True, "true", "yes", "Y", 1, "1", "t", "Yes.", "ties", "ties within tolerance", "yes - ties", "yes (within $5)", "within", "within tolerance",
              "matches", "ok", "OK", "correct", "agree", "reconciled", "tied"):
        (cred if met(run("B", muts={"C2.cash_ties": v}), "C2.tie") else lost).append(v)
    say("B1", f"cash_ties (gold true): credited {cred}; NOT credited {lost}", "FINDING" if "ties" in lost else "HELD")
    inv = [v for v in ("exceeds", "exceeded", "material", "above", "required", 123457.0) if met(run("B", muts={"C2.cash_ties": v}), "C2.tie")]
    say("B2", f"cash_ties values whose natural meaning is 'does NOT tie' (or arbitrary) but are credited as TRUE: {inv}", "FINDING" if inv else "HELD")
    fl = [v for v in (False, "false", "no", 0, "does not tie") if met(run("B", muts={"C2.cash_ties": v}), "C2.tie")]
    say("B3", f"cash_ties = False-ish credited although the cash ties: {fl}", "FINDING" if fl else "HELD")
    cd = {repr(v): met(run("B", muts={"C2.cash_difference": v}), "C2.tie") for v in (0, "0.00", "$0.00", "(0.00)", "-0.00", 0.01, 0.011, "nil", "none", "zero", None, "no difference")}
    say("B4", f"cash_difference credited? {cd}")


def g_tie():
    print("== tie: C2.tie compares the CLAIM to gold, never to the model's own recomputation; gold is 'ties' on both cases")
    wrong = vals(L3=0.0, L4=0.0)
    for k in "BC":
        def triple(m, wrong=wrong):
            cash_fn(wrong)(m)
            m["C2"].update({"agent_cash_component": 9200.0, "cash_difference": 0.0, "cash_ties": True})
        atk(f"T1{k}", k, "recompute wrong (written legs dropped: cash order -400... ) but the tie triple 'agent 9200, diff 0, ties true' asserted", fn=triple,
            ok=lambda s: not met(s, "C2.tie"), want="C2.tie unmet (its own recomputation contradicts the claim)")
        atk(f"T2{k}", k, "same wrong recompute, honest: cash_difference computed, cash_ties false", fn=cash_fn(wrong), want="(baseline for T1)")
        atk(f"T3{k}", k, "no recomputation at all: legs/option/cash null, tie triple + twin copied from the recap, cash fields transcribed from the statement/recap (4600, 9200, 8700)",
            fn=lambda m: [m["C2"].update({"option_value_per_cu": None, "option_value_order": None}), [r.update({"value": None}) for r in m["C2"]["leg_values_per_cu"]]],
            ok=lambda s: s["cps"]["C2"] < 0.5, want="C2 < 0.5 (no arithmetic shown)")
        atk(f"T4{k}", k, "agent_cash_component 18,400 (x2), diff 0, ties true", muts={"C2.agent_cash_component": 18400.0}, ok=lambda s: not met(s, "C2.tie"), want="C2.tie unmet")


def g_unread():
    print("== unread: C2/C3 fields no atom reads (garbage keeps 1.0000 / AllPass); leg-row sub-keys")
    un = collections.OrderedDict()
    for k in "BC":
        for sect in ("C2", "C3"):
            for fld in GOLD[k][sect]:
                if all(perfect(run(k, muts={f"{sect}.{fld}": g})) for g in ("GARBAGE", 123457.0, DEL)):
                    un.setdefault((sect, fld), []).append(k)
    say("U1", "fields where GARBAGE / 123457 / deletion are all still AllPass: " + "; ".join(f"{a}.{b} ({''.join(v)})" for (a, b), v in un.items()), "FINDING")
    atk("U2", "B", "C3.cash_component_affected = true (claims the cash component is affected; gold false)", muts={"C3.cash_component_affected": True}, ok=lambda s: not perfect(s), want="not AllPass")
    atk("U3", "B", "C3.offending_leg = 'L4' (wrong leg named in C3; D1 names L2)", muts={"C3.offending_leg": "L4"}, ok=lambda s: not perfect(s), want="not AllPass")
    atk("U4", "B", "C3.enriched = 'remaining_shareholders' (inverted)", muts={"C3.enriched": "remaining_shareholders"}, ok=lambda s: not perfect(s), want="not AllPass")
    atk("U5", "B", "C3.ap_received_option_value = 1 and fund_position_short_by = 0", muts={"C3.ap_received_option_value": 1, "C3.fund_position_short_by": 0}, ok=lambda s: not perfect(s), want="not AllPass")
    atk("U6", "B", "C2.option_value_order = 12345 (read only by the scale gate) and C2.redemption_value = 1", muts={"C2.option_value_order": 12345.0, "C2.redemption_value": 1}, ok=lambda s: not perfect(s), want="not AllPass")
    atk("U7", "B", "leg-row sub-keys contracts_per_cu=99999, mark=99999, sign=99999 on L2 (only `value` is read)",
        fn=lambda m: m["C2"]["leg_values_per_cu"][1].update({"contracts_per_cu": 99999, "mark": 99999, "sign": 99999}), ok=lambda s: not perfect(s), want="not AllPass")
    atk("U8", "B", "OUTSIDE MY SURFACE: HOLD but D1.release_cash=true, cancel_shares=true", muts={"D1.release_cash": True, "D1.cancel_shares": True}, ok=lambda s: not perfect(s), want="not AllPass")
    atk("U8c", "C", "OUTSIDE MY SURFACE: SETTLE but D1.release_cash=false, cancel_shares=false", muts={"D1.release_cash": False, "D1.cancel_shares": False}, ok=lambda s: not perfect(s), want="not AllPass")


def g_rows():
    print("== rows: C2.leg_values_per_cu row shapes")
    base = [{"leg_id": k, "value": v} for k, v in GOLDV.items()]
    for nm in ("Total", "Net option value", "OPTIONS_TOTAL", "Cash component", "cu_value"):
        atk("R1", "B", f"extra summary row leg_id={nm!r} (value right)", fn=lambda m, nm=nm: m["C2"]["leg_values_per_cu"].append({"leg_id": nm, "value": 1520400.0}), ok=perfect, want="perfect")
    atk("R2", "B", "rows keyed 'Leg 2' style", fn=lambda m: m["C2"].update({"leg_values_per_cu": [{"leg_id": "Leg " + r["leg_id"][1:], "value": r["value"]} for r in base]}), ok=perfect, want="perfect")
    atk("R3", "B", "rows keyed by OSI identifier instead of leg_id", fn=lambda m: m["C2"].update({"leg_values_per_cu": [{"osi_identifier": r["osi_identifier"], "value": GOLDV[r["leg_id"]]} for r in m["E1"]["legs"]]}), ok=perfect, want="perfect")
    atk("R4", "B", "leg values as a {leg: value} map", fn=lambda m: m["C2"].update({"leg_values_per_cu": dict(GOLDV)}), ok=perfect, want="perfect")
    atk("R5", "B", "magnitude in `value`, direction in `sign` (the SCHEMA row has both)", fn=lambda m: m["C2"].update({"leg_values_per_cu": [{"leg_id": k, "sign": 1 if v > 0 else -1, "value": abs(v)} for k, v in GOLDV.items()]}), ok=perfect, want="perfect")
    atk("R6", "B", "hedged duplicate: L2 listed twice, second row 237.00", fn=lambda m: m["C2"]["leg_values_per_cu"].append({"leg_id": "L2", "value": 237.0}), ok=lambda s: not perfect(s), want="not perfect")
    atk("R7", "B", "a 'TOTAL' row carrying a /100 total (ignored by every atom and by the gate)", fn=lambda m: m["C2"]["leg_values_per_cu"].append({"leg_id": "TOTAL", "value": 15204.0}), want="(skip-listed ids carry any content free)")


def g_shape():
    print("== shape: sections of the wrong type must score, never raise")
    for sect in ("C2", "C3"):
        for nm, v in (("list", [{"a": 1}]), ("string", "see above"), ("int", 5), ("True", True), ("empty list", [])):
            atk("H1", "B", f"{sect} = {nm}", muts={sect: v}, ok=lambda s: s["gates"] != ["EXC"] and s["gated"] < 1.0, want="scores without raising")


def g_strings():
    print("== strings: _numx takes the FIRST number in a string")
    for p, v in (("C2.cash_component_per_cu", "4600 or 9200"), ("C2.net_cash_to_ap", "8700 and 9200"), ("C3.excess_contracts", "11,880 or 12,000"),
                 ("C3.excess_value", "4,692,600.00 (= 11,880 x 100 x 3.95)")):
        atk("W1", "B", f"{p.split('.')[-1]} = {v!r} (a hedge / two figures)", muts={p: v}, ok=lambda s: not perfect(s), want="not perfect")
    for p, v in (("C2.net_cash_to_ap", "9,200.00 less 500.00 fee = 8,700.00"), ("C3.excess_contracts", "12,000 - 120 = 11,880"), ("C2.cash_component_per_cu", "1,525,000 - 1,520,400 = 4,600")):
        atk("W2", "B", f"{p.split('.')[-1]} = {v!r} (worked expression ending in the right figure)", muts={p: v}, ok=perfect, want="perfect")
    atk("W3", "B", "C3.excess_contracts = '120 due vs 12,000 confirmed = 11,880 excess'", muts={"C3.excess_contracts": "120 due vs 12,000 confirmed = 11,880 excess"}, ok=lambda s: not gated(s), want="no GATE.MULTIPLIER")
    for p, v in (("C3.impact_pct_of_nav", "77.31 bps"), ("C3.impact_per_remaining_share", "23.58 cents"), ("C3.impact_per_remaining_share", "0,2358")):
        atk("W4", "B", f"{p.split('.')[-1]} = {v!r}", muts={p: v}, ok=perfect, want="perfect (right figure in another unit)")


def g_clean():
    print("== clean: the tying order (gold SETTLE, every C3 figure zero)")
    atk("Q1", "C", "C3 numbers null where nothing is wrong (impact/pct null)", muts={"C3.impact_per_remaining_share": None, "C3.impact_pct_of_nav": None}, ok=perfect, want="perfect")
    atk("Q2", "C", "C3 omitted entirely", muts={"C3": DEL}, ok=lambda s: s["cps"]["C3"] == 0.0, want="C3 = 0")
    atk("Q3", "C", "C3 = {'direction': 'none'} only", muts={"C3": {"direction": "none"}}, ok=lambda s: s["cps"]["C3"] < 0.2, want="C3 < 0.2")
    atk("Q4", "C", "phantom break in C3: excess 11,880, value 4,692,600, actual 12,000, direction over (D1 still SETTLE)",
        muts={"C3.excess_contracts": 11880, "C3.excess_value": 4692600.0, "C3.fund_position_actual": 12000, "C3.direction": "over_delivered_to_ap"}, want="(C3.excess + C3.direction lost; D1 unaffected)")


def g_prop():
    print("== prop: proportionality of the hard gate against the signature failure")
    atk("P1", "B", "SETTLE on the break (the signature failure; math all right)", muts={"D1.decision": "SETTLE"}, want="(reference)")
    atk("P2", "B", "HOLD right, localized, remedy named; ONE figure /100 (D1.excess_value 46,926)", muts={"D1.excess_value": 46926.0}, want="(decision right: should not fall below P1?)")
    atk("P3", "B", "HOLD right; C1.due_contracts_per_leg = 1,200 (x10 typo)", muts={"C1.due_contracts_per_leg": 1200}, want="(x10 is outside the documented x100 axis)")
    atk("P4", "B", "HOLD right; C2.cu_value = 15,250,000 (NAV x10 typo)", muts={"C2.cu_value": 15250000.0}, want="(same)")


def g_crash():
    print("== crash: integers beyond float range (a JSON integer of 310 digits) in any numeric field")
    paths = ["C2.option_value_per_cu", "C2.cu_value", "C2.cash_component_per_cu", "C2.net_cash_to_ap", "C2.cash_difference", "C3.excess_contracts", "C3.excess_value",
             "C3.impact_per_remaining_share", "C3.shares_outstanding_after", "D1.excess_value", "C1.due_contracts_per_leg", "P1.num_cus", "C2.leg_values_per_cu.0.value",
             "E2.confirmations.1.quantity", "E2.nav.marks.L1"]
    raised = [p for p in paths if run("B", muts={p: 10 ** 400})["gates"] == ["EXC"]]
    say("Z1", f"10**400 (a 401-digit JSON integer) raises OverflowError out of run_case in {len(raised)} of {len(paths)} numeric paths tried: {raised}", "FINDING" if raised else "HELD")
    s = run("B", fn=lambda m: m["C2"].update({"cu_value": "9" * 400}))
    say("Z2", f"the same digits as a STRING in C2.cu_value: no raise (gated={s['gated']})", "HELD" if s["gates"] != ["EXC"] else "FINDING")
    ok = [repr(v) for v in (float("nan"), float("inf"), -0.0, 1e-320, 1e308) if run("B", muts={"C3.excess_value": v})["gates"] != ["EXC"]]
    say("Z3", f"nan / inf / -0.0 / 1e-320 / 1e308 in C3.excess_value score without raising: {ok}", "HELD" if len(ok) == 5 else "FINDING")


def g_fuzz():
    print("== fuzz: every C2/C3 field x 37 odd values x both cases (1,924 runs, ~3 min)")
    odd = {"None": None, "''": "", "'abc'": "abc", "[]": [], "{}": {}, "[1,2]": [1, 2], "{'a':1}": {"a": 1}, "True": True, "False": False, "0": 0, "-0.0": -0.0,
           "1e308": 1e308, "-1e308": -1e308, "1e-320": 1e-320, "nan": float("nan"), "inf": float("inf"), "-inf": float("-inf"), "10**400": 10 ** 400,
           "-10**400": -(10 ** 400), "'1e400'": "1e400", "'nan'": "nan", "'-'": "-", "'()'": "()", "'(1'": "(1", "[{'value':1}]": [{"value": 1}],
           "{'value':5.0}": {"value": 5.0}, "nested": {"a": {"b": [1, {"c": 2}]}}, "'1,2,3'": "1,2,3", "'1..2'": "1..2", "fullwidth 123": "１２３",
           "'9'*400": "9" * 400, "tuple": (1, 2), "['a','b']": ["a", "b"], "'USD'": "USD", "' '": " ", "'\\u2212'": "−", "'$'": "$"}
    flds = {"C2": ["option_value_per_cu", "cu_value", "cash_component_per_cu", "option_value_order", "cash_component_order", "transaction_fee", "net_cash_to_ap",
                   "redemption_value", "agent_cash_component", "cash_difference", "cash_ties", "leg_values_per_cu"],
            "C3": ["offending_leg", "excess_contracts", "excess_value", "fund_position_due", "fund_position_actual", "fund_position_short_by", "direction", "harmed",
                   "enriched", "ap_received_option_value", "shares_outstanding_after", "impact_per_remaining_share", "impact_pct_of_nav", "cash_component_affected"]}
    crash, gates, n = collections.OrderedDict(), collections.OrderedDict(), 0
    for k in "BC":
        for sect, fl in flds.items():
            for f in fl:
                for on, ov in odd.items():
                    s = run(k, muts={f"{sect}.{f}": ov})
                    n += 1
                    if s["gates"] == ["EXC"]:
                        crash.setdefault(s["moved"][0], []).append((k, sect, f, on))
                    elif "GATE.MULTIPLIER" in s["gates"] or "GATE.SIGN" in s["gates"]:
                        gates.setdefault((sect, f, on), []).append((k, s["gates"]))
    RES.append(dict(id="FUZZ", verdict="FINDING" if crash else "HELD"))
    print(f"[FUZZ] {n} runs; crashes: " + "; ".join(f"{m} x{len(r)} (first {r[0]})" for m, r in crash.items()) + f"; gates from odd values: {dict(gates)}")


# ------------------------------------------------------------------ the PINNABLE CHECKS (PASS = the FIXED behaviour; most FAIL today)
_B, _C = "grbo-redeem-2026", "grbo-redeem-2026-clean"


def _p(c): return os.path.join(REPO, "cases", f"{c}.case.yaml")


def _run(case, mutate):
    m = orx.oracle(load_case(_p(case)))
    mutate(m)
    r, _ = run_case(_p(case), model_output=m)
    return r


def _cp(r, k): return r.checkpoints[k]["score_gated"]
def _gate(r, g): return g in r.fired_gates
def _perfect(r): return r.allpass == 1 and abs(r.case_gated - 1.0) < 1e-6 and not r.fired_gates


def _set(path, value):
    def mut(m):
        cur = m
        for k in path[:-1]:
            cur = cur.setdefault(k, {})
        cur[path[-1]] = value
    return mut


_V = {"L1": 1529400.0, "L2": 23700.0, "L3": -4800.0, "L4": -27900.0}      # gold leg values per unit


def _cash(vals, opt=True):          # a model that believed these legs
    def mut(m):
        c, o = m["C2"], sum(vals.values())
        for r in c["leg_values_per_cu"]:
            r["value"] = vals[r["leg_id"]]
        c["option_value_per_cu"], c["option_value_order"] = (o, 2 * o) if opt else (None, None)
        c["cash_component_per_cu"], c["cash_component_order"] = 1525000.0 - o, 2 * (1525000.0 - o)
        c["net_cash_to_ap"] = c["cash_component_order"] - 500.0
        c["cash_difference"], c["cash_ties"] = 9200.0 - c["cash_component_order"], False
        m["D2"]["twins"][0]["value"] = c["net_cash_to_ap"]
    return mut


def checks():
    out, G = [], (lambda mut, g, c=_B: _gate(_run(c, mut), g))
    ps, add = {k: v / 100 for k, v in _V.items()}, dict(_V, L3=4800.0, L4=27900.0)    # per-share legs; written legs added
    leg = lambda i, v: (lambda m: m["C2"]["leg_values_per_cu"][i].update({"value": v}))
    dr = lambda s: _set(("C3", "direction"), s)

    def hidden(m):                  # the /100 answer, option values nulled
        _cash(ps, opt=False)(m)
        for r in m["C2"]["leg_values_per_cu"]:
            r["value"] = None

    def triple(m):                  # wrong recompute, tie triple asserted
        _cash(dict(_V, L3=0.0, L4=0.0))(m)
        m["C2"].update({"agent_cash_component": 9200.0, "cash_difference": 0.0, "cash_ties": True})
    out.append(("/100 legs, derived consistent: GATE.MULTIPLIER", lambda: G(_cash(ps), "GATE.MULTIPLIER")))
    out.append(("written legs added, option value shown: GATE.SIGN", lambda: G(_cash(add), "GATE.SIGN")))
    out.append(("nulled option values must not score higher", lambda: _run(_B, hidden).case_gated <= _run(_B, _cash(ps)).case_gated + 1e-9))
    out.append(("C2 omitted: C2 = 0", lambda: _cp(_run(_B, lambda m: m.pop("C2")), "C2") == 0.0))
    for nm, mut in (("L2 '23700,00'", leg(1, "23700,00")), ("excess_value '$4.6926 million'", _set(("C3", "excess_value"), "$4.6926 million")),
                    ("option_value_per_cu '1.5204M'", _set(("C2", "option_value_per_cu"), "1.5204M"))):
        out.append((f"right {nm}: no GATE.MULTIPLIER", lambda mut=mut: not G(mut, "GATE.MULTIPLIER")))
    out.append(("written legs added, option_value_per_cu null: GATE.SIGN", lambda: G(_cash(add, opt=False), "GATE.SIGN")))
    out.append(("harmed='authorized_participant': GATE.SIGN (rubric text)", lambda: G(_set(("C3", "harmed"), "authorized_participant"), "GATE.SIGN")))
    out.append(("inverted 'the fund owes the AP 11,880 contracts': GATE.SIGN", lambda: G(dr("the fund owes the AP 11,880 contracts"), "GATE.SIGN")))
    for s in ("not under_delivered_to_ap", "the fund is short by 11,880 contracts", "AP owed the fund 11,880 contracts"):
        out.append((f"right {s!r}: no GATE.SIGN", lambda s=s: not G(dr(s), "GATE.SIGN")))
    for s in ("not over_delivered_to_ap", "no over-delivery"):
        out.append((f"negated {s!r}: not perfect", lambda s=s: not _perfect(_run(_B, dr(s)))))
    out.append(("clean: 'No over-delivery' is perfect", lambda: _perfect(_run(_C, dr("No over-delivery")))))
    out.append(("L2 '−$23,700.00' (wrong sign) not credited", lambda: not _perfect(_run(_B, leg(1, "−$23,700.00")))))
    out.append(("L3 '−$4,800.00' (right sign) credited", lambda: _perfect(_run(_B, leg(2, "−$4,800.00")))))
    out.append(("cash_ties 'exceeds' (= does not tie) not credited", lambda: _cp(_run(_B, _set(("C2", "cash_ties"), "exceeds")), "C2") < 0.999))
    out.append(("401-digit integer: scores, no raise", lambda: _run(_B, _set(("C2", "cu_value"), 10 ** 400)).case_gated < 1.0))
    for f, v in (("cash_component_affected", True), ("offending_leg", "L4"), ("enriched", "remaining_shareholders")):
        out.append((f"unread C3.{f}={v!r} is not AllPass", lambda f=f, v=v: not _perfect(_run(_B, _set(("C3", f), v)))))
    out.append(("release_cash/cancel_shares true on a HOLD: not AllPass", lambda: not _perfect(_run(_B, lambda m: m["D1"].update({"release_cash": True, "cancel_shares": True})))))
    out.append(("wrong recompute + asserted tie triple: C2 < 0.3", lambda: _cp(_run(_B, triple), "C2") < 0.3))
    out.append(("'Net option value' row: perfect", lambda: _perfect(_run(_B, lambda m: m["C2"]["leg_values_per_cu"].append({"leg_id": "Net option value", "value": 1520400.0})))))
    return out


def run_checks():
    bad = 0
    for name, fn in checks():
        try:
            ok = bool(fn())
        except Exception as e:
            ok, name = False, f"{name} [raised {type(e).__name__}: {str(e)[:50]}]"
        bad += (not ok)
        print(("  PASS  " if ok else "  FAIL  ") + name)
    print(f"\n{len(checks()) - bad} passed, {bad} failed (a FAIL is a reproduced finding; PASS = fixed or held)")


GROUPS = collections.OrderedDict([("scale", g_scale), ("cash", g_cash), ("sign", g_sign), ("excess", g_excess), ("dir", g_dir), ("fmt", g_fmt), ("sgnloss", g_sgnloss),
                                  ("bool", g_bool), ("tie", g_tie), ("unread", g_unread), ("rows", g_rows), ("shape", g_shape), ("strings", g_strings),
                                  ("clean", g_clean), ("prop", g_prop), ("crash", g_crash), ("fuzz", g_fuzz)])

if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if "--checks" in sys.argv:
        run_checks()
        raise SystemExit(0)
    todo = args or [g for g in GROUPS if g != "fuzz"]
    for g in todo:
        GROUPS[g]()
    c = collections.Counter(r["verdict"] for r in RES)
    print(f"\nSUMMARY: {len(RES)} result lines: {c['FINDING']} FINDING, {c['HELD']} HELD (attack failed), {c['INFO']} INFO")

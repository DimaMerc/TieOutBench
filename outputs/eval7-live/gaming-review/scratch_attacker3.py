"""scratch_attacker3.py - attacker 3 (numeric checkpoints C2 / C3, GATE.SCALE, GATE.SIGN) probes for eval #7.

Runs only answers through the official run_case path; nothing in the repo is modified. The grade() call is wrapped
IN MEMORY (spy) so the per-atom verdicts can be printed next to the official CaseScore.

usage:  python scratch_attacker3.py [group ...]      groups: sweep scale tol fmt pct dir bool misc scen all
"""
import sys, os, copy, json, itertools
sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
REPO = r"C:\Projects\finance-llm-evals"
sys.path.insert(0, REPO)
import harness as H
from harness.rubric import load_case
from harness.suites import nav_oversight as nv
from harness.graders import _num

CASES = {"B": REPO + r"\cases\grsl-nav-2026.case.yaml", "C": REPO + r"\cases\grsl-nav-2026-clean.case.yaml"}
CASEOBJ = {k: load_case(v) for k, v in CASES.items()}
GOLD = {k: CASEOBJ[k]["gold"] for k in CASES}
SHARES = 4_000_000.0

_cap = {}
_orig_grade = H.grade


def _spy(atoms, model, gold, rubric, suite, mode="mock", judge_fn=None):
    out = _orig_grade(atoms, model, gold, rubric, suite, mode=mode, judge_fn=judge_fn)
    _cap["v"], _cap["atoms"] = out[0], atoms
    return out


H.grade = _spy
DEL = object()
RESULTS = []


def getpath(d, path):
    cur = d
    for p in path.split("."):
        cur = cur[int(p)] if isinstance(cur, list) else cur[p]
    return cur


def setpath(m, path, val):
    parts = path.split(".")
    cur = m
    for p in parts[:-1]:
        if isinstance(cur, list):
            cur = cur[int(p)]
        else:
            if p not in cur or not isinstance(cur[p], (dict, list)):
                cur[p] = {}
            cur = cur[p]
    last = parts[-1]
    if isinstance(cur, list):
        if val is DEL:
            cur.pop(int(last))
        else:
            cur[int(last)] = val
    else:
        if val is DEL:
            cur.pop(last, None)
        else:
            cur[last] = val


def build(case_key, muts):
    m = nv.oracle(CASEOBJ[case_key])
    for p, v in muts.items():
        setpath(m, p, v if v is DEL else copy.deepcopy(v))
    return m


def grade_answer(case_key, m, variant=None):
    if variant:
        res, _ = H.run_case(CASES[case_key], variant=variant)
    else:
        res, _ = H.run_case(CASES[case_key], model_output=m)
    return res, dict(_cap["v"]), _cap["atoms"]


BASE = {}
for _k in CASES:
    _r, _v, _a = grade_answer(_k, build(_k, {}))
    BASE[_k] = (_r, _v)
    assert _r.case_gated == 1.0 and _r.allpass == 1, ("oracle must score 1.0 AllPass", _k)


def summarize(case_key, res, verd, atoms):
    base_r, base_v = BASE[case_key]
    diffs = []
    for a in atoms:
        mv, bv = verd[a.id].met, base_v[a.id].met
        if abs(mv - bv) > 1e-9:
            diffs.append(f"{a.id}:{mv:g}")
    cps = {k: round(v["score_gated"], 4) for k, v in res.checkpoints.items()}
    return dict(case=case_key, gated=res.case_gated, ungated=res.case_ungated, allpass=res.allpass,
                gates=list(res.fired_gates), flags=list(res.flags), cps=cps, diffs=diffs,
                R=round(res.e6[0], 3), G=round(res.e6[1], 3))


def line(tag, s):
    c = s["cps"]
    return (f"{tag:<30} {s['case']} gated={s['gated']:.4f} ungated={s['ungated']:.4f} AP={s['allpass']} "
            f"gates={','.join(s['gates']) or '-'} flags={','.join(s['flags']) or '-'} "
            f"C2={c['C2']:.3f} C3={c['C3']:.3f} D1={c['D1']:.3f} | {' '.join(s['diffs']) or '(no atom changed)'}")


def percase(muts):
    return isinstance(muts, dict) and muts and set(muts) <= {"B", "C"}


def exp(tag, muts, cases="BC", quiet=False, variant=None):
    out = {}
    for k in cases:
        mm = muts.get(k) if percase(muts) else muts
        if mm is None:
            continue
        try:
            m = build(k, mm)
            res, verd, atoms = grade_answer(k, m, variant)
            s = summarize(k, res, verd, atoms)
        except Exception as e:  # a grader crash on a malformed answer is itself a finding
            s = dict(case=k, gated=-1, ungated=-1, allpass=-1, gates=["EXC"], flags=[], cps={"C2": -1, "C3": -1, "D1": -1},
                     diffs=[f"EXC {type(e).__name__}: {e}"], R=0, G=0)
        s.update(tag=tag, muts=json.dumps({a: (str(b) if b is DEL else b) for a, b in mm.items()}, default=str, ensure_ascii=False)
                 if mm else "{}")
        RESULTS.append(s)
        out[k] = s
        if not quiet:
            print(line(tag, s))
    return out


def met(s, atom):
    """True if the atom is NOT in the diffs (i.e. unchanged from the oracle = met) for an atom that the oracle meets."""
    for d in s["diffs"]:
        if d.startswith(atom + ":"):
            return float(d.split(":")[1])
    return None   # unchanged


def hdr(t):
    print("\n" + "=" * 100 + "\n" + t + "\n" + "=" * 100)


# ---------------------------------------------------------------------------------------------------------------
# SWEEP: which multiplicative factors does GATE.SCALE catch, per gate-checked field?
# ---------------------------------------------------------------------------------------------------------------
def sweep():
    hdr("SWEEP  GATE.SCALE firing vs multiplicative factor (model value = gold x factor)")
    fields = [("C2.total_net_assets", "tna"), ("C2.total_assets", "ta"), ("C2.nav_per_share", "nav"),
              ("C3.nav_error_per_share", "err_ps"), ("C3.fund_level_error", "err_fund"),
              ("C2.total_liabilities", "tl*"), ("C3.nav_error_pct", "pct*"), ("D1.corrected_nav_per_share", "d1nav*"),
              ("D1.nav_error_per_share", "d1err*")]
    factors = [("1.0199", 1.0199), ("1.021", 1.021), ("1.05", 1.05), ("1.5", 1.5), ("2", 2), ("3", 3), ("5", 5), ("9", 9),
               ("10", 10), ("0.1", 0.1), ("0.5", 0.5), ("20", 20), ("50", 50), ("99", 99), ("100", 100), ("101", 101),
               ("0.01", 0.01), ("0.0099", 0.0099), ("1000", 1e3), ("1049", 1049), ("1051", 1051), ("0.001", 1e-3),
               ("1e4", 1e4), ("1e-4", 1e-4), ("1e5", 1e5), ("1e-5", 1e-5), ("1e6", 1e6), ("1e-6", 1e-6),
               ("1e7", 1e7), ("1e-7", 1e-7), ("1e8", 1e8), ("1e9", 1e9), ("1e-9", 1e-9),
               ("shares", SHARES), ("1/shares", 1 / SHARES), ("shares*1.04", SHARES * 1.04), ("shares*1.06", SHARES * 1.06),
               ("-1", -1), ("-0.5", -0.5), ("-10", -10), ("-100", -100), ("-0.01", -0.01), ("-1000", -1e3), ("-0.001", -1e-3),
               ("-1e6", -1e6), ("-1e-6", -1e-6), ("-shares", -SHARES), ("-1/shares", -1 / SHARES)]
    for case in "BC":
        gold = GOLD[case]
        print(f"\n-- case {case}: cell G = GATE.SCALE fired; . = quiet; - = gold is 0 (n/a). Fields marked * are NOT read by C2.scale")
        print(f"{'factor':<12}" + "".join(f"{n:>9}" for _, n in fields))
        for lab, f in factors:
            row = f"x{lab:<11}"
            for path, n in fields:
                g = getpath(gold, path)
                if g in (None, 0):
                    row += f"{'-':>9}"
                    continue
                s = list(exp("sweep", {path: g * f}, cases=case, quiet=True).values())[0]
                fired = "GATE.SCALE" in s["gates"]
                row += f"{('G' if fired else '.'):>9}"
            print(row)


# ---------------------------------------------------------------------------------------------------------------
def scale():
    hdr("SCALE: GATE.SCALE evasion / coverage")
    TNA, TA, TL, NAV = 207964686.19, 209010600.0, 1045913.81, 51.9912
    exp("S1 TNA +3.5% only", {"C2.total_net_assets": round(TNA * 1.035, 2)})
    exp("S1b TNA x10 only", {"C2.total_net_assets": round(TNA * 10, 2)})
    exp("S1c TNA x1e9-ish (billions)", {"C2.total_net_assets": round(TNA / 1e9, 6)})
    exp("S2 C2 all +3.5% (off-scale)", {"C2.total_assets": round(TA * 1.035, 2), "C2.total_net_assets": round(TNA * 1.035, 2),
                                         "C2.nav_per_share": round(NAV * 1.035, 4)})
    exp("S2b C2 all x10", {"C2.total_assets": round(TA * 10, 2), "C2.total_net_assets": round(TNA * 10, 2),
                           "C2.nav_per_share": round(NAV * 10, 4), "C2.total_liabilities": round(TL * 10, 2)})
    exp("S2c C2 all x1e4", {"C2.total_assets": round(TA * 1e4, 2), "C2.total_net_assets": round(TNA * 1e4, 2),
                            "C2.nav_per_share": round(NAV * 1e4, 4), "C2.total_liabilities": round(TL * 1e4, 2)})
    exp("S2d C2 all x1000 (control)", {"C2.total_assets": round(TA * 1e3, 2), "C2.total_net_assets": round(TNA * 1e3, 2),
                                       "C2.nav_per_share": round(NAV * 1e3, 4), "C2.total_liabilities": round(TL * 1e3, 2)})
    exp("S3a TL /1000 only", {"C2.total_liabilities": round(TL / 1000, 5)})
    exp("S3b TL x1000 only", {"C2.total_liabilities": round(TL * 1000, 2)})
    exp("S3c TL x100 only", {"C2.total_liabilities": round(TL * 100, 2)})
    exp("S3d TL in millions only", {"C2.total_liabilities": round(TL / 1e6, 6)})
    exp("S4a D1.corrected_nav x100", {"D1.corrected_nav_per_share": 5199.12})
    exp("S4b D1.nav_error_per_share x100", {"D1.nav_error_per_share": -75.0})
    exp("S4c D1 corrected x100 + err x100", {"D1.corrected_nav_per_share": 5199.12, "D1.nav_error_per_share": -75.0})
    exp("S4d C3.nav_error_pct /100 (fraction)", {"C3.nav_error_pct": -0.014426})
    exp("S4e C3.nav_error_pct x100", {"C3.nav_error_pct": -144.26})
    exp("S4f D1.corrected_nav = TNA (fund level)", {"D1.corrected_nav_per_share": 207964686.19})
    exp("S5a NAV x shares", {"C2.nav_per_share": round(NAV * SHARES, 2)})
    exp("S5b NAV x100", {"C2.nav_per_share": 5199.12})
    exp("S5c NAV x10", {"C2.nav_per_share": 519.912})
    exp("S5d NAV /10", {"C2.nav_per_share": 5.19912})
    exp("S5e TNA / shares-as-TNA (per-share in TNA)", {"C2.total_net_assets": 51.9912})
    exp("S6a err_ps +75 (opp sign x100)", {"B": {"C3.nav_error_per_share": 75.0}}, cases="B")
    exp("S6b err_ps -75 (same sign x100)", {"B": {"C3.nav_error_per_share": -75.0}}, cases="B")
    exp("S6c err_fund +3000 (opp sign /1000)", {"B": {"C3.fund_level_error": 3000.0}}, cases="B")
    exp("S6d err_fund -3000 (same sign /1000)", {"B": {"C3.fund_level_error": -3000.0}}, cases="B")
    exp("S6e both +75 / +3000", {"B": {"C3.nav_error_per_share": 75.0, "C3.fund_level_error": 3000.0}}, cases="B")
    exp("S6f both -75 / -3000", {"B": {"C3.nav_error_per_share": -75.0, "C3.fund_level_error": -3000.0}}, cases="B")
    exp("S6g opp sign + millions", {"B": {"C3.fund_level_error": 3.0, "C3.nav_error_per_share": 0.75}}, cases="B")
    exp("S6h same sign millions", {"B": {"C3.fund_level_error": -3.0}}, cases="B")
    exp("S7a TNA +1.9% (inside 2% band)", {"C2.total_net_assets": round(TNA * 1.019, 2)})
    exp("S7b NAV +1.9% (inside 2% band)", {"C2.nav_per_share": round(NAV * 1.019, 4)})
    exp("S7c TA +1.9%", {"C2.total_assets": round(TA * 1.019, 2)})
    exp("S7d TNA+TA+NAV +1.9%", {"C2.total_assets": round(TA * 1.019, 2), "C2.total_net_assets": round(TNA * 1.019, 2),
                                  "C2.nav_per_share": round(NAV * 1.019, 4)})
    exp("S7e TNA -1.9%", {"C2.total_net_assets": round(TNA * 0.981, 2)})
    exp("S8a TNA dict thousands labelled", {"C2.total_net_assets": {"value": 207964.69, "unit": "USD thousands"}})
    exp("S8b TNA '207.96 million' string", {"C2.total_net_assets": "207.96 million"})
    exp("S8c TNA 207.96 numeric millions", {"C2.total_net_assets": 207.96})
    exp("S8d TNA '$207.96M' string", {"C2.total_net_assets": "$207.96M"})
    exp("S8e TNA dict value_usd_mm 207.96", {"C2.total_net_assets": {"value_usd_mm": 207.96, "value": 207964686.19}})
    exp("S9a TNA = -TNA (neg)", {"C2.total_net_assets": -TNA})
    exp("S9b TNA neg x1000", {"C2.total_net_assets": -TNA * 1000})
    exp("S9c NAV negative x100", {"C2.nav_per_share": -5199.12})
    exp("S9d TNA = TL-TA (liab first, negative)", {"C2.total_net_assets": round(TL - TA, 2)})


# ---------------------------------------------------------------------------------------------------------------
def tol():
    hdr("TOLERANCE bands and the stale-blind TNA window")
    for v in [51.9910, 51.9914, 51.99095, 51.99145, 51.9909, 51.9915, 51.99, 51.991, 51.992, 52.0, 51.9912]:
        exp(f"T1 NAV {v}", {"C2.nav_per_share": v}, cases="B")
    for d in [0.5, 1.0, 1.01, -1.0, -1.01, 2.0, 5.0]:
        exp(f"T2 TNA {d:+}", {"C2.total_net_assets": round(207964686.19 + d, 2)}, cases="B")
    for d in [1.0, 1.01]:
        exp(f"T3 TA {d:+}", {"C2.total_assets": round(209010600.0 + d, 2)}, cases="B")
        exp(f"T3 TL {d:+}", {"C2.total_liabilities": round(1045913.81 + d, 2)}, cases="B")
    for d in [0.9, 1.0, 1.01, 2.0]:
        exp(f"T5 TNA=adminTNA {d:+}", {"B": {"C2.total_net_assets": round(204964686.19 + d, 2)}}, cases="B")
    exp("T5b TNA=admin, NAV=admin", {"B": {"C2.total_net_assets": 204964686.19, "C2.nav_per_share": 51.2412}}, cases="B")
    exp("T5c TNA=admin+2, NAV=admin+.0003", {"B": {"C2.total_net_assets": 204964688.19, "C2.nav_per_share": 51.2415}}, cases="B")
    exp("T5d TNA=admin+2,NAV adm,TA adm", {"B": {"C2.total_net_assets": 204964688.19, "C2.nav_per_share": 51.2412,
                                                 "C2.total_assets": 206010600.0}}, cases="B")
    exp("T5e NAV=admin only", {"B": {"C2.nav_per_share": 51.2412}}, cases="B")
    # C3.error band edges (break)
    for ps in [-0.7490, -0.7510, -0.74899, -0.75101, -0.7495, -0.7505]:
        exp(f"T4 err_ps {ps}", {"B": {"C3.nav_error_per_share": ps}}, cases="B")
    for p in [-1.4326, -1.4526, -1.4325, -1.4527, -1.44, -1.45, -1.4, -1.46, -1.4637]:
        exp(f"T4 err_pct {p}", {"B": {"C3.nav_error_pct": p}}, cases="B")
    for f in [-3000001.0, -3000001.01, -2999999.0, -2999998.99]:
        exp(f"T4 err_fund {f}", {"B": {"C3.fund_level_error": f}}, cases="B")
    # clean case: how big an 'error' still counts as a tie
    for ps, pc, fl in [(0.0009, 0.0, 0.0), (0.001, 0.0, 0.0), (0.0011, 0.0, 0.0), (0.0, 0.01, 0.0), (0.0, 0.0101, 0.0),
                       (0.0, 0.0, 0.99), (0.0, 0.0, 1.0), (0.0, 0.0, 1.01), (0.0009, 0.01, 1.0)]:
        exp(f"T6 clean err ps={ps} pct={pc} fund={fl}", {"C": {"C3.nav_error_per_share": ps, "C3.nav_error_pct": pc,
                                                              "C3.fund_level_error": fl}}, cases="C")


# ---------------------------------------------------------------------------------------------------------------
def probe_field(title, case, path, values, atoms):
    print(f"\n-- {title}   (case {case}, field {path})")
    for v in values:
        s = list(exp("fmt", {path: v}, cases=case, quiet=True).values())[0]
        cells = []
        for a in atoms:
            mv = met(s, a)
            cells.append(f"{a}={'1' if mv is None else ('%g' % mv)}")
        print(f"   {json.dumps(v, ensure_ascii=False):<34} {' '.join(cells):<46} gates={','.join(s['gates']) or '-':<12} gated={s['gated']:.4f}")


def fmt():
    hdr("FORMAT: numbers as strings, units, accounting negatives")
    probe_field("TNA strings", "B", "C2.total_net_assets",
                ["207,964,686.19", "$207,964,686.19", "$ 207,964,686.19", "USD 207,964,686.19", "207,964,686.19 USD", "$207.96M",
                 "207.96 million", "207 964 686.19", "207'964'686.19", "207.964.686,19", "207964686,19", "2.0796468619e8",
                 " 207964686.19 ", "207,964,686", "~207,964,686.19", "207_964_686.19", "$207,964,686.19 (approx)", "207964686.19 dollars",
                 "nan", "inf", "1e400"], ["C2.tna", "C2.scale"])
    probe_field("NAV strings", "B", "C2.nav_per_share",
                ["51.9912", "$51.9912", "$51.9912/share", "51,9912", "51.99", "USD 51.9912", "51.9912 USD", "5.19912e1", "51.9912.",
                 "51 .9912", "$ 51.9912"], ["C2.nav", "C2.scale"])
    probe_field("fund-level error strings", "B", "C3.fund_level_error",
                ["-3,000,000", "-$3,000,000", "$-3,000,000", "(3,000,000)", "\u22123,000,000", "\u20133,000,000", "-3.0M", "-3,000,000.00",
                 "\u2212$3,000,000.00", "-3000000", "minus 3,000,000", "- 3,000,000", "+3,000,000", "3,000,000", "-3,000,000 USD"],
                ["C3.error", "C2.scale"])
    probe_field("per-share error strings", "B", "C3.nav_error_per_share",
                ["-0.75", "-0.7500", "$-0.75", "-$0.75", "(0.75)", "\u22120.75", "-75 cents", "-75\u00a2", "-0.75 USD", "-.75", "-0.75/share",
                 "+0.75", "0.75"], ["C3.error", "C2.scale"])
    probe_field("error pct strings", "B", "C3.nav_error_pct",
                ["-1.4426", "-1.4426%", "-1.44%", "\u22121.44%", "(1.44%)", "-1.44 %", "-0.014426", "-1.44 pct", "-144 bps", "-1.44",
                 "-1.43", "-1.4637", "-1.46", "1.4426", "-1,44"], ["C3.error", "C2.scale"])
    # clean-case zero formats
    probe_field("clean: fund-level error '0' formats", "C", "C3.fund_level_error",
                [0, 0.0, -0.0, "0", "0.00", "$0.00", "-0.0", "0%", "none", "n/a", "", None, False, True, "false", 1e-13, 0.9999, "(0.00)"],
                ["C3.error"])
    probe_field("clean: per-share error formats", "C", "C3.nav_error_per_share",
                [0, 0.0, -0.0, "0.0000", "$0.0000", False, True, None, "", "none", 0.0009, 0.001, 0.0011],
                ["C3.error"])


def pct():
    hdr("PERCENT / FRACTION / DEVIATION conventions inside C3.expected")
    probe_field("expected_move_pct", "B", "C3.expected_move_pct",
                [4, 4.0, "4", "4.0%", "+4.0%", "4.00 %", 0.04, "0.04", 400, "4,00", 4.01, 4.0101, 3.99, 3.9899, 4.0001, "4.0000x"], ["C3.expected"])
    probe_field("admin_move_pct", "B", "C3.admin_move_pct",
                [2.4824, "2.48", "2.48%", 2.48, 2.5, 2.49, 2.4924, 2.4725, 0.024824, "2.4824%", 3.9824, 51.2412], ["C3.expected"])
    probe_field("admin_deviation_pp", "B", "C3.admin_deviation_pp",
                [-1.5176, -1.52, -1.5, "+1.5176", 1.5176, "-1.5176%", "\u22121.5176", "(1.5176)", -0.015176, -151.76, -0.0176, "1.52", -1.5276, -1.5076],
                ["C3.expected"])
    probe_field("clean: admin_move_pct", "C", "C3.admin_move_pct",
                [3.9824, "3.98", 3.98, 4.0, 3.99, 3.9924, "3.98%", 0.039824], ["C3.expected"])
    probe_field("clean: admin_deviation_pp", "C", "C3.admin_deviation_pp",
                [-0.0176, -0.02, -0.0, 0, 0.0176, "\u22120.0176", "(0.0176)", -0.0276, -0.0076, -0.0, "-0.02"], ["C3.expected"])
    exp("P1 all pcts as fractions (B)", {"B": {"C3.nav_error_pct": -0.014426, "C3.expected_move_pct": 0.04, "C3.admin_move_pct": 0.024824,
                                              "C3.admin_deviation_pp": -0.015176, "C3.index_return_pct": 0.02}}, cases="B")
    exp("P2 deviation opposite sign (B)", {"B": {"C3.admin_deviation_pp": 1.5176}}, cases="B")
    exp("P3 flag true, move numbers missing (B)", {"B": {"C3.expected_move_pct": DEL, "C3.admin_move_pct": DEL, "C3.admin_deviation_pp": DEL}}, cases="B")
    exp("P3b flag true, move numbers wrong (B)", {"B": {"C3.expected_move_pct": 2.0, "C3.admin_move_pct": 1.0, "C3.admin_deviation_pp": -1.0}}, cases="B")
    exp("P3c flag true numbers wrong (C)", {"C": {"C3.reasonableness_flag": True, "C3.expected_move_pct": 2.0, "C3.admin_move_pct": 1.0,
                                                 "C3.admin_deviation_pp": -1.0}}, cases="C")
    exp("P3d flag true, numbers right (C)", {"C": {"C3.reasonableness_flag": True}}, cases="C")
    exp("P3e flag false, numbers right (B)", {"B": {"C3.reasonableness_flag": False}}, cases="B")
    exp("P4 nav_error_pct denominator=admin NAV (B)", {"B": {"C3.nav_error_pct": round(-0.75 / 51.2412 * 100, 4)}}, cases="B")
    exp("P5 no recomputed_* / index_return (B)", {"B": {"C3.recomputed_move_pct": DEL, "C3.recomputed_deviation_pp": DEL, "C3.index_return_pct": DEL}}, cases="B")


# ---------------------------------------------------------------------------------------------------------------
DIRS = [
    "understated", "UNDERSTATED", "Understated.", "under", "Under-stated", "low", "too low", "TOO LOW", "below", "lower", "LOW.",
    "NAV understated", "understated NAV", "Understated by the administrator", "understated by 0.75", "the NAV is understated",
    "administrator NAV is low", "admin NAV below recomputed", "negative", "short", "light", "underestimated", "undervalued",
    "overall understated", "Overall, the NAV is understated", "oversight: understated", "Understated (administrator below recomputed)",
    "understated|overstated|none", "understated/overstated", "understated or overstated", "under/over", "under review",
    "undergoing review", "under investigation", "understated, not overstated",
    "over", "overstated", "OVERSTATED", "overstated by the administrator", "NAV overstated", "the NAV is overstated",
    "The administrator's NAV is overstated", "too high", "administrator NAV too high", "high", "above", "overvalued", "override",
    "oversight review", "overall", "overall no error", "Overstated?",
    {"value": "overstated"}, ["overstated"], ["understated"], {"value": "understated"}, None, "", "-", "0", "?", False, True, 0,
    "none", "no error", "no error found", "no direction", "ties", "tie", "tied", "tied out", "ties out", "no break", "match", "matches",
    "clean", "not applicable", "n/a", "N/A", "zero", "nil", "null", "no difference", "balanced", "no", "no error - ties",
]


def dirs():
    hdr("C3.direction synonyms / GATE.SIGN  (B = break gold understated, C = clean gold none)")
    print(f"{'direction value':<46}{'B: dir  gate  gated':<30}{'C: dir  gate  gated'}")
    for d in DIRS:
        sb = list(exp("dir", {"C3.direction": d}, cases="B", quiet=True).values())[0]
        sc = list(exp("dir", {"C3.direction": d}, cases="C", quiet=True).values())[0]

        def cell(s):
            mv = met(s, "C3.direction")
            g = ",".join(x.replace("GATE.", "") for x in s["gates"]) or "-"
            return f"{'1' if mv is None else '%g' % mv:<5}{g:<8}{s['gated']:.3f}"
        print(f"{json.dumps(d, ensure_ascii=False):<46}{cell(sb):<30}{cell(sc)}")


FLAGS = [True, False, "true", "True", "TRUE", " true ", "True.", "yes", "Yes", "Yes.", "y", "Y", "1", 1, 1.0, "no", "No", "n", "false",
         "False", "0", 0, 0.0, -0.0, "exceeded", "exceeds", "Exceeded", "above", "breach", "breached", "material", "not exceeded",
         "does not exceed", "below", "within", "ties", "", None, [], {}, [True], {"result": True}, "true (0.75 >= 0.01)",
         "true - exceeded", "TRUE/FALSE", "<true if |nav_error_per_share| >= the per-share floor>", "T", "F", "on", "off", "ok", "pass", "fail"]


def bools():
    hdr("BOOLEAN-ish flags: C3.thresholds (both flags set to the value) and C3.expected (reasonableness_flag)")
    print(f"{'value':<46}{'thresholds B':<14}{'thresholds C':<14}{'expected B':<12}{'expected C'}")
    for v in FLAGS:
        tb = list(exp("th", {"C3.exceeds_per_share_floor": v, "C3.exceeds_reprocessing_pct": v}, cases="B", quiet=True).values())[0]
        tc = list(exp("th", {"C3.exceeds_per_share_floor": v, "C3.exceeds_reprocessing_pct": v}, cases="C", quiet=True).values())[0]
        eb = list(exp("rf", {"C3.reasonableness_flag": v}, cases="B", quiet=True).values())[0]
        ec = list(exp("rf", {"C3.reasonableness_flag": v}, cases="C", quiet=True).values())[0]

        def f(s, a):
            m = met(s, a)
            return "1" if m is None else "%g" % m
        print(f"{json.dumps(v, ensure_ascii=False):<46}{f(tb, 'C3.thresholds'):<14}{f(tc, 'C3.thresholds'):<14}"
              f"{f(eb, 'C3.expected'):<12}{f(ec, 'C3.expected')}")
    # one flag only on each case (split)
    exp("B1 B: floor true, pct false", {"B": {"C3.exceeds_reprocessing_pct": False}}, cases="B")
    exp("B2 C: numeric flags as 0/0", {"C": {"C3.exceeds_per_share_floor": 0, "C3.exceeds_reprocessing_pct": 0, "C3.reasonableness_flag": 0}}, cases="C")
    exp("B3 C: flags as 'not exceeded'", {"C": {"C3.exceeds_per_share_floor": "not exceeded", "C3.exceeds_reprocessing_pct": "not exceeded"}}, cases="C")
    exp("B4 B: flags 'exceeded'", {"B": {"C3.exceeds_per_share_floor": "exceeded", "C3.exceeds_reprocessing_pct": "exceeded"}}, cases="B")


# ---------------------------------------------------------------------------------------------------------------
def misc():
    hdr("MISC: rounding, ungraded fields, empty sections, none-direction, sign conventions")
    # rounding of a correct answer
    r2 = {"C2.nav_per_share": 51.99, "C2.total_assets": 209010600.0, "C3.nav_error_per_share": -0.75, "C3.nav_error_pct": -1.44,
          "C3.expected_move_pct": 4.0, "C3.admin_move_pct": 2.48, "C3.admin_deviation_pp": -1.52, "D1.corrected_nav_per_share": 51.99,
          "D1.nav_error_per_share": -0.75}
    exp("R1 correct, NAV and pcts at 2dp", r2)
    exp("R1b only C2.nav at 2dp", {"C2.nav_per_share": 51.99})
    exp("R1c C2.nav at 3dp", {"C2.nav_per_share": 51.991})
    exp("R1d C2.nav at 3dp (51.992)", {"C2.nav_per_share": 51.992})
    exp("R1e pcts at 1dp", {"C3.nav_error_pct": -1.4, "C3.expected_move_pct": 4.0, "C3.admin_move_pct": 2.5, "C3.admin_deviation_pp": -1.5})
    exp("R1f pcts at 2dp only", {"C3.nav_error_pct": -1.44, "C3.admin_move_pct": 2.48, "C3.admin_deviation_pp": -1.52})
    exp("R1g all numbers rounded to whole $", {"C2.total_assets": 209010600, "C2.total_liabilities": 1045914, "C2.total_net_assets": 207964686,
                                               "C3.fund_level_error": -3000000})
    # ungraded fields
    exp("U1 garbage in ungraded fields", {"C2.shares_outstanding": 1, "C3.index_return_pct": 99.0, "C3.recomputed_move_pct": -500.0,
                                          "C3.recomputed_deviation_pp": 42.0})
    exp("U1b ungraded fields deleted", {"C2.shares_outstanding": DEL, "C3.index_return_pct": DEL, "C3.recomputed_move_pct": DEL,
                                        "C3.recomputed_deviation_pp": DEL})
    exp("U1c ungraded fields = strings", {"C2.shares_outstanding": "lots", "C3.index_return_pct": "n/a", "C3.recomputed_move_pct": "tbd",
                                          "C3.recomputed_deviation_pp": "tbd"})
    # empty sections
    exp("M1 C2 deleted entirely", {"C2": DEL})
    exp("M2 C3 deleted entirely", {"C3": DEL})
    exp("M3 C2 and C3 deleted", {"C2": DEL, "C3": DEL})
    exp("M4 C2 = {} and C3 = {}", {"C2": {}, "C3": {}})
    exp("M5 C2 = None, C3 = None", {"C2": None, "C3": None})
    exp("M6 C2 = [] and C3 = 'n/a'", {"C2": [], "C3": "n/a"})
    # none direction on the break
    exp("N1 B: direction none only", {"B": {"C3.direction": "none"}}, cases="B")
    exp("N2 B: direction none + zero error numbers", {"B": {"C3.direction": "none", "C3.fund_level_error": 0.0, "C3.nav_error_per_share": 0.0,
                                                            "C3.nav_error_pct": 0.0}}, cases="B")
    exp("N3 B: dir none + zero err + flags false", {"B": {"C3.direction": "none", "C3.fund_level_error": 0.0, "C3.nav_error_per_share": 0.0,
                                                         "C3.nav_error_pct": 0.0, "C3.exceeds_per_share_floor": False,
                                                         "C3.exceeds_reprocessing_pct": False, "C3.reasonableness_flag": False}}, cases="B")
    exp("N4 B: direction deleted", {"B": {"C3.direction": DEL}}, cases="B")
    exp("N5 C: direction deleted (clean)", {"C": {"C3.direction": DEL}}, cases="C")
    exp("N6 C: phantom 'understated' on clean", {"C": {"C3.direction": "understated"}}, cases="C")
    exp("N7 C: phantom 'overstated' on clean", {"C": {"C3.direction": "overstated"}}, cases="C")
    # sign convention
    exp("G1 B: opposite sign convention, dir right", {"B": {"C3.fund_level_error": 3000000.0, "C3.nav_error_per_share": 0.75,
                                                           "C3.nav_error_pct": 1.4426}}, cases="B")
    exp("G1b + D1 error also opposite", {"B": {"C3.fund_level_error": 3000000.0, "C3.nav_error_per_share": 0.75,
                                              "C3.nav_error_pct": 1.4426, "D1.nav_error_per_share": 0.75}}, cases="B")
    exp("G1c + twin also opposite (+0.75)", {"B": {"C3.fund_level_error": 3000000.0, "C3.nav_error_per_share": 0.75,
                                                  "C3.nav_error_pct": 1.4426, "D1.nav_error_per_share": 0.75,
                                                  "D2.twins.0.value": 0.75}}, cases="B")
    exp("G2 B: gold-sign numbers, direction overstated", {"B": {"C3.direction": "overstated"}}, cases="B")
    exp("G3 B: all numbers inverted + dir overstated", {"B": {"C3.fund_level_error": 3000000.0, "C3.nav_error_per_share": 0.75,
                                                             "C3.nav_error_pct": 1.4426, "C3.direction": "overstated",
                                                             "D1.nav_error_per_share": 0.75}}, cases="B")
    exp("G4 B: only fund-level sign flipped", {"B": {"C3.fund_level_error": 3000000.0}}, cases="B")
    exp("G5 B: only pct sign flipped", {"B": {"C3.nav_error_pct": 1.4426}}, cases="B")
    exp("G6 B: abs() of all errors (no signs)", {"B": {"C3.fund_level_error": 3000000.0, "C3.nav_error_per_share": 0.75,
                                                      "C3.nav_error_pct": 1.4426, "D1.nav_error_per_share": 0.75}}, cases="B")
    exp("G7 C: error +0.0000 with sign -0.0", {"C": {"C3.fund_level_error": -0.0, "C3.nav_error_per_share": -0.0, "C3.nav_error_pct": -0.0}},
        cases="C")
    # variants shipped with the repo, for reference
    for var in ("sign_flip", "scale_slip"):
        exp(f"V {var}", {}, cases="B", variant=var)


# ---------------------------------------------------------------------------------------------------------------
def scen():
    hdr("SCENARIOS: realistic wrong answers built from the findings")
    inv = {"C3.fund_level_error": 3000000.0, "C3.nav_error_per_share": 0.75, "C3.nav_error_pct": 1.4426, "D1.nav_error_per_share": 0.75}
    exp("SC0 designed sign_flip variant", {}, cases="B", variant="sign_flip")
    for txt in ["overstated", "The administrator's NAV is overstated", "NAV overstated", "the NAV is too high",
                {"value": "overstated"}, "administrator overstated", "NAV is overstated (admin above recomputed)"]:
        mm = dict(inv); mm["C3.direction"] = txt
        exp(f"SC1 inverted + dir={json.dumps(txt)[:34]}", {"B": mm}, cases="B")
    mm = dict(inv); mm["C3.direction"] = DEL
    exp("SC2 inverted numbers, direction omitted", {"B": mm}, cases="B")
    mm = dict(inv); mm["C3.direction"] = ""
    exp("SC2b inverted numbers, direction ''", {"B": mm}, cases="B")
    exp("SC3 placeholder echo direction", {"C3.direction": "understated|overstated|none"})
    exp("SC3b hedge understated/overstated", {"C3.direction": "understated/overstated"})
    exp("SC3c 'under review'", {"C3.direction": "under review"})
    exp("SC4 right answer, 'Overall understated'", {"C3.direction": "Overall understated"}, cases="B")
    exp("SC4b right answer, 'Overall, the NAV is understated'", {"C3.direction": "Overall, the NAV is understated"}, cases="B")
    exp("SC4c right answer, 'oversight: understated'", {"C3.direction": "Oversight finding: understated"}, cases="B")
    exp("SC4d right answer, 'NAV understated'", {"C3.direction": "NAV understated"}, cases="B")
    exp("SC5 scaled error opposite sign", {"B": {"C3.nav_error_per_share": 75.0, "C3.fund_level_error": 3000.0}}, cases="B")
    exp("SC5b scaled error same sign (fires)", {"B": {"C3.nav_error_per_share": -75.0, "C3.fund_level_error": -3000.0}}, cases="B")
    exp("SC6 whole C3 in cents/thousands opp sign + pct frac", {"B": {"C3.nav_error_per_share": 75.0, "C3.fund_level_error": 3000.0,
                                                                     "C3.nav_error_pct": 0.014426, "C3.direction": "understated"}}, cases="B")
    exp("SC7 decimal-shift NAV x10 (C2 + D1)", {"C2.nav_per_share": 519.912, "D1.corrected_nav_per_share": 519.912})
    exp("SC7b decimal-shift NAV x100 (D1 only)", {"D1.corrected_nav_per_share": 5199.12})
    exp("SC8 TNA $4M wrong (1.9%), rest right", {"C2.total_net_assets": round(207964686.19 * 1.019, 2)})
    exp("SC9 nothing recomputed: C2 empty, C3 right", {"C2": {}})


# ---------------------------------------------------------------------------------------------------------------
def round_all(x, nd=2):
    if isinstance(x, dict):
        return {k: round_all(v, nd) for k, v in x.items()}
    if isinstance(x, list):
        return [round_all(v, nd) for v in x]
    if isinstance(x, float) and not isinstance(x, bool):
        return round(x, nd)
    return x


def extra():
    hdr("EXTRA: EU decimal comma, huge ints, full 2dp rounding, other-language directions, AllPass edge stack, crash probes")
    probe_field("EU decimal comma: TNA", "B", "C2.total_net_assets", ["207964686,19", "207 964 686,19", "207.964.686,19", "207964686,2"], ["C2.tna", "C2.scale"])
    probe_field("EU decimal comma: TA", "B", "C2.total_assets", ["209010600,00", "209.010.600,00"], ["C2.totals", "C2.scale"])
    probe_field("EU decimal comma: NAV", "B", "C2.nav_per_share", ["51,99", "51,9912", "51,991", "51,99120"], ["C2.nav", "C2.scale"])
    probe_field("EU decimal comma: per-share error", "B", "C3.nav_error_per_share", ["-0,75", "-0,7500", "-0,750"], ["C3.error", "C2.scale"])
    probe_field("EU decimal comma: fund-level error", "B", "C3.fund_level_error", ["-3000000,00", "-3.000.000,00", "-3000000,0"], ["C3.error", "C2.scale"])
    probe_field("EU decimal comma: pct", "B", "C3.nav_error_pct", ["-1,4426", "-1,44"], ["C3.error", "C2.scale"])
    # huge ints / odd python types
    print()
    for tag, mm in [("huge int 10**400 in TNA", {"C2.total_net_assets": 10 ** 400}),
                    ("huge int in C3.fund_level_error", {"B": {"C3.fund_level_error": -(10 ** 400)}}),
                    ("1e999 float via json", {"C2.total_net_assets": float("inf")}),
                    ("bool True in TNA", {"C2.total_net_assets": True}),
                    ("list in TNA", {"C2.total_net_assets": [207964686.19]}),
                    ("D2 = 'n/a' (side probe)", {"D2": "n/a"}),
                    ("D2.probe = 'n/a' (side probe)", {"D2.probe": "n/a"}),
                    ("D1 = 'n/a'", {"D1": "n/a"})]:
        exp(tag, mm)
    # fully 2dp-rounded correct answer, per case
    for k in "BC":
        m = round_all(nv.oracle(CASEOBJ[k]), 2)
        res, verd, atoms = grade_answer(k, m)
        s = summarize(k, res, verd, atoms)
        s.update(tag="R2 everything at 2dp", muts="all floats rounded to 2 decimals")
        RESULTS.append(s)
        print(line("R2 everything at 2dp", s))
        m = round_all(nv.oracle(CASEOBJ[k]), 3)
        res, verd, atoms = grade_answer(k, m)
        s = summarize(k, res, verd, atoms)
        s.update(tag="R3 everything at 3dp", muts="all floats rounded to 3 decimals")
        RESULTS.append(s)
        print(line("R3 everything at 3dp", s))
    # other-language / odd direction
    probe_field("direction other forms", "B", "C3.direction",
                ["unterbewertet", "zu niedrig", "sous-evalue", "UNDERSTATED_BY_ADMIN", "understated; overstated; none", ["understated", "overstated", "none"],
                 ["none", "understated", "overstated"], "none|understated|overstated", "overstated|understated|none", "understated\n", "  understated  ",
                 "understated (NOT overstated)", "NOT understated", "not overstated", "no understatement", "undetermined", "unknown", "uncertain"], ["C3.direction", "C3.n_signflip"])
    # AllPass edge stack
    stack = {"C2.total_net_assets": 207964687.19, "C2.total_assets": 209010601.0, "C2.total_liabilities": 1045914.81, "C2.nav_per_share": 51.9914,
             "C3.fund_level_error": -3000001.0, "C3.nav_error_per_share": -0.751, "C3.nav_error_pct": -1.4526, "C3.direction": "understated|overstated|none",
             "C3.expected_move_pct": 4.01, "C3.admin_move_pct": 2.4924, "C3.admin_deviation_pp": -1.5276, "C3.exceeds_per_share_floor": "true",
             "C3.exceeds_reprocessing_pct": "yes", "C3.reasonableness_flag": "TRUE", "C2.shares_outstanding": 1, "C3.index_return_pct": 99.0,
             "C3.recomputed_move_pct": -500.0, "C3.recomputed_deviation_pp": 42.0}
    exp("AP1 edge-stack + hedged direction (B)", {"B": stack}, cases="B")
    stack_c = {"C2.total_net_assets": 207964687.19, "C2.total_assets": 209010601.0, "C2.total_liabilities": 1045914.81, "C2.nav_per_share": 51.9914,
               "C3.fund_level_error": 1.0, "C3.nav_error_per_share": 0.001, "C3.nav_error_pct": 0.01, "C3.direction": "n/a",
               "C3.expected_move_pct": 4.01, "C3.admin_move_pct": 3.9924, "C3.admin_deviation_pp": -0.0276, "C3.exceeds_per_share_floor": "no",
               "C3.exceeds_reprocessing_pct": "n", "C3.reasonableness_flag": "FALSE", "C2.shares_outstanding": 1, "C3.index_return_pct": 99.0,
               "C3.recomputed_move_pct": -500.0, "C3.recomputed_deviation_pp": 42.0}
    exp("AP2 edge-stack (C)", {"C": stack_c}, cases="C")


def final():
    """the headline findings, printed in the attacker-brief format (case_gated, allpass, fired_gates, flags, e6 + checkpoint scores)."""
    hdr("FINAL: headline findings, brief-format result lines (before = oracle 1.0 / AllPass 1 on both cases)")
    stale_inv = {"C3.fund_level_error": 3000000.0, "C3.nav_error_per_share": 0.75, "C3.nav_error_pct": 1.4426, "D1.nav_error_per_share": 0.75}
    rows = [
        ("F1  hedge: schema placeholder echoed", "B", {"C3.direction": "understated|overstated|none"}),
        ("F1  hedge: 'under review'", "B", {"C3.direction": "under review"}),
        ("F1  hedge: ['understated','overstated','none']", "B", {"C3.direction": ["understated", "overstated", "none"]}),
        ("F1  same hedge on the clean case", "C", {"C3.direction": "understated|overstated|none"}),
        ("F2  RIGHT answer 'Overall understated' -> SIGN", "B", {"C3.direction": "Overall understated"}),
        ("F2  RIGHT answer 'Oversight: NAV understated'", "B", {"C3.direction": "Oversight: NAV understated"}),
        ("F3  inverted numbers + 'overstated' (control)", "B", dict(stale_inv, **{"C3.direction": "overstated"})),
        ("F3  inverted numbers + sentence direction", "B", dict(stale_inv, **{"C3.direction": "The administrator's NAV is overstated"})),
        ("F3  inverted numbers + direction omitted", "B", dict(stale_inv, **{"C3.direction": DEL})),
        ("F4  RIGHT TNA written 207964686,19", "B", {"C2.total_net_assets": "207964686,19"}),
        ("F4  RIGHT per-share error written -0,75", "B", {"C3.nav_error_per_share": "-0,75"}),
        ("F4  RIGHT fund-level error -3000000,00", "B", {"C3.fund_level_error": "-3000000,00"}),
        ("F4  NAV written 51,99 (2dp, EU)", "B", {"C2.nav_per_share": "51,99"}),
        ("F4c same TNA, parse-fail control (no comma trick)", "B", {"C2.total_net_assets": "207.964.686,19"}),
        ("F5  C2 totals x1000 (control, fires)", "B", {"C2.total_assets": 209010600000.0, "C2.total_net_assets": 207964686190.0, "C2.nav_per_share": 51991.2,
                                                    "C2.total_liabilities": 1045913810.0}),
        ("F5  C2 totals x10 (quiet)", "B", {"C2.total_assets": 2090106000.0, "C2.total_net_assets": 2079646861.9, "C2.nav_per_share": 519.912,
                                          "C2.total_liabilities": 10459138.1}),
        ("F5  C2 totals / 1e9 (billions, quiet)", "B", {"C2.total_assets": 0.2090106, "C2.total_net_assets": 0.20796468619, "C2.nav_per_share": 5.19912e-08,
                                                     "C2.total_liabilities": 0.00104591381}),
        ("F6  scaled error, opposite sign (quiet)", "B", {"C3.nav_error_per_share": 75.0, "C3.fund_level_error": 3000.0}),
        ("F6  scaled error, same sign (fires)", "B", {"C3.nav_error_per_share": -75.0, "C3.fund_level_error": -3000.0}),
        ("F7  total_liabilities x1000 (unwatched)", "B", {"C2.total_liabilities": 1045913810.0}),
        ("F7  D1.corrected_nav_per_share x100 (unwatched)", "B", {"D1.corrected_nav_per_share": 5199.12}),
        ("F7  nav_error_pct as fraction (unwatched)", "B", {"C3.nav_error_pct": -0.014426}),
        ("F8  garbage in 4 ungraded fields", "B", {"C2.shares_outstanding": 1, "C3.index_return_pct": 99.0, "C3.recomputed_move_pct": -500.0,
                                                 "C3.recomputed_deviation_pp": 42.0}),
        ("F8  garbage in 4 ungraded fields", "C", {"C2.shares_outstanding": 1, "C3.index_return_pct": 99.0, "C3.recomputed_move_pct": -500.0,
                                                 "C3.recomputed_deviation_pp": 42.0}),
        ("F9  stale-blind TNA/NAV exact (control)", "B", {"C2.total_net_assets": 204964686.19, "C2.nav_per_share": 51.2412}),
        ("F9  stale-blind TNA +2.00, NAV +0.0003", "B", {"C2.total_net_assets": 204964688.19, "C2.nav_per_share": 51.2415}),
        ("F10 break: 'NAV understated' (RIGHT)", "B", {"C3.direction": "NAV understated"}),
        ("F10 clean: 'no error found' (RIGHT)", "C", {"C3.direction": "no error found"}),
        ("F10 clean: 'tie' (RIGHT)", "C", {"C3.direction": "tie"}),
        ("F10 clean: direction omitted (free credit)", "C", {"C3.direction": DEL}),
        ("F11 clean: flags as integer 0 (RIGHT)", "C", {"C3.exceeds_per_share_floor": 0, "C3.exceeds_reprocessing_pct": 0, "C3.reasonableness_flag": 0}),
        ("F11 break: flags 'exceeded' (RIGHT)", "B", {"C3.exceeds_per_share_floor": "exceeded", "C3.exceeds_reprocessing_pct": "exceeded"}),
        ("F12 fund-level error (3,000,000) accounting", "B", {"C3.fund_level_error": "(3,000,000)"}),
        ("F12 per-share error unicode minus", "B", {"C3.nav_error_per_share": "−0.75"}),
        ("F12 TNA 'USD 207,964,686.19'", "B", {"C2.total_net_assets": "USD 207,964,686.19"}),
        ("F13 pct fields as fractions", "B", {"C3.nav_error_pct": -0.014426, "C3.expected_move_pct": 0.04, "C3.admin_move_pct": 0.024824,
                                            "C3.admin_deviation_pp": -0.015176}),
        ("F13 error, opposite sign convention", "B", {"C3.fund_level_error": 3000000.0, "C3.nav_error_per_share": 0.75, "C3.nav_error_pct": 1.4426}),
        ("F13 + D1.nav_error_per_share opposite", "B", stale_inv),
        ("F13 deviation opposite sign", "B", {"C3.admin_deviation_pp": 1.5176}),
        ("F13 NAV rounded to 2dp", "B", {"C2.nav_per_share": 51.99}),
        ("F15 sign-wrong twin (D2.twins.0.value=+0.75)", "B", dict(stale_inv, **{"D2.twins.0.value": 0.75})),
        ("EDGE direction 'none' on the break", "B", {"C3.direction": "none"}),
        ("EDGE flag true, move numbers missing", "B", {"C3.expected_move_pct": DEL, "C3.admin_move_pct": DEL, "C3.admin_deviation_pp": DEL}),
        ("EDGE TNA +3.5% only (off every factor)", "B", {"C2.total_net_assets": 215243449.0}),
        ("EDGE C2 TNA/TA/NAV +3.5%", "B", {"C2.total_assets": 216326971.0, "C2.total_net_assets": 215243449.0, "C2.nav_per_share": 53.8108}),
    ]
    for tag, k, mm in rows:
        m = build(k, mm)
        res, verd, atoms = grade_answer(k, m)
        s = summarize(k, res, verd, atoms)
        c = {kk: round(v["score_gated"], 3) for kk, v in res.checkpoints.items() if kk in ("C2", "C3", "D1", "D2")}
        mj = json.dumps({a: ("<deleted>" if b is DEL else b) for a, b in mm.items()}, ensure_ascii=False)
        print(f"{tag}\n    mut={mj[:300]}\n    case={k} ->{res.case_gated} {res.allpass} {res.fired_gates} {res.flags} {tuple(round(x, 3) for x in res.e6)} "
              f"{c} changed={' '.join(s['diffs']) or '-'}")


def clean():
    """clean-case analogs (gold RELEASE) + the end-to-end overflow path + OVER/UNDER prefix phrases."""
    hdr("CLEAN-CASE analogs, overflow end-to-end, OVER/UNDER prefix phrases")
    for tag, mm in [
        ("C: RIGHT TNA '207964686,19' (EU) on clean", {"C2.total_net_assets": "207964686,19"}),
        ("C: RIGHT NAV '51,99' on clean", {"C2.nav_per_share": "51,99"}),
        ("C: RIGHT TA '209010600,00' on clean", {"C2.total_assets": "209010600,00"}),
        ("C: labelled-thousands dict on clean", {"C2.total_net_assets": {"value": 207964.69, "unit": "USD thousands"}}),
        ("C: TNA x10 on clean", {"C2.total_net_assets": 2079646861.9}),
        ("C: C2 all x10 on clean", {"C2.total_assets": 2090106000.0, "C2.total_net_assets": 2079646861.9, "C2.nav_per_share": 519.912,
                                    "C2.total_liabilities": 10459138.1}),
        ("C: phantom error -75/-3000 (gold 0)", {"C3.nav_error_per_share": -75.0, "C3.fund_level_error": -3000.0}),
        ("C: phantom -0.75/-3000000/understated", {"C3.nav_error_per_share": -0.75, "C3.fund_level_error": -3000000.0, "C3.nav_error_pct": -1.4426,
                                                   "C3.direction": "understated"}),
        ("C: phantom overstated + inverted numbers", {"C3.nav_error_per_share": 0.75, "C3.fund_level_error": 3000000.0, "C3.nav_error_pct": 1.4426,
                                                      "C3.direction": "overstated"}),
        ("C: flags 'not exceeded' text", {"C3.exceeds_per_share_floor": "not exceeded", "C3.exceeds_reprocessing_pct": "not exceeded"}),
        ("C: all flags 'no'", {"C3.exceeds_per_share_floor": "no", "C3.exceeds_reprocessing_pct": "no", "C3.reasonableness_flag": "no"}),
        ("C: deviation 0 (rounded)", {"C3.admin_deviation_pp": 0}),
        ("C: deviation -0.0 (1dp)", {"C3.admin_deviation_pp": -0.0}),
        ("C: expected_move fraction", {"C3.expected_move_pct": 0.04}),
        ("C: NAV 2dp", {"C2.nav_per_share": 51.99}),
        ("C: C3 numbers + flags null", {"C3.fund_level_error": None, "C3.nav_error_per_share": None, "C3.nav_error_pct": None,
                                        "C3.exceeds_per_share_floor": None}),
        ("C: direction 'none|understated|overstated'", {"C3.direction": "none|understated|overstated"}),
        ("C: direction 'none or understated'", {"C3.direction": "none or understated"}),
        ("C: direction 'overall no error'", {"C3.direction": "overall no error"}),
    ]:
        exp(tag, {"C": mm}, cases="C")
    print()
    for d in ["Overall understated", "Overall: NAV understated by 0.75", "overall-understated", "Oversight: NAV understated", "over/under: under",
              "Over- or understated: understated", "Over/understated (understated)", "Overnight mark stale -> understated", "overnight"]:
        exp(f"B: direction {d!r}", {"B": {"C3.direction": d}}, cases="B")
    # end-to-end through the live JSON parser: a degenerate digit run in a numeric field
    print()
    from harness.live import parse_answer
    m = nv.oracle(CASEOBJ["B"])
    raw = json.dumps(m, default=str).replace('"total_net_assets": 207964686.19', '"total_net_assets": ' + "1" * 400, 1)
    a = parse_answer(raw)
    print("live parse_answer keeps the 400-digit integer:", type(a["C2"]["total_net_assets"]).__name__, len(str(a["C2"]["total_net_assets"])), "digits")
    for nd in (308, 309, 310, 400):
        m2 = nv.oracle(CASEOBJ["B"])
        m2["C2"]["total_net_assets"] = int("1" * nd)
        try:
            r, _ = H.run_case(CASES["B"], model_output=m2)
            print(f"   {nd} digits -> graded, case_gated={r.case_gated}")
        except Exception as e:
            print(f"   {nd} digits -> run_case RAISED {type(e).__name__}: {e}")


FUZZ_VALUES = [None, "", "abc", [], {}, True, False, 0, -0.0, "nan", "inf", "-inf", 1e308, -1e308, 1e-320, "1e3", " 12 ", "0x10", "١٢٣",
               "１２３", {"value": 5}, {"value": "5"}, {"value_usd_mm": 5}, [1], "1_000", "1,2,3", "--5", "+-5", "5%%", "$$5", " 5"]


def fuzz():
    hdr("FUZZ: every C2/C3 field x odd values; report crashes and any change that leaves AllPass at 1")
    fields = ["C2.total_assets", "C2.total_liabilities", "C2.total_net_assets", "C2.shares_outstanding", "C2.nav_per_share",
              "C3.fund_level_error", "C3.nav_error_per_share", "C3.nav_error_pct", "C3.direction", "C3.exceeds_per_share_floor",
              "C3.exceeds_reprocessing_pct", "C3.index_return_pct", "C3.expected_move_pct", "C3.admin_move_pct", "C3.recomputed_move_pct",
              "C3.admin_deviation_pp", "C3.recomputed_deviation_pp", "C3.reasonableness_flag"]
    n = crashes = allpass = gated_rows = 0
    seen_allpass = set()
    for k in "BC":
        for f in fields:
            for v in FUZZ_VALUES:
                s = list(exp("fuzz", {f: v}, cases=k, quiet=True).values())[0]
                n += 1
                if s["gates"] == ["EXC"]:
                    crashes += 1
                    print(f"CRASH {k} {f}={v!r}: {s['diffs']}")
                elif s["allpass"] == 1:
                    allpass += 1
                    seen_allpass.add((k, f, json.dumps(v, default=str)))
                elif s["gates"]:
                    gated_rows += 1
                    print(f"GATE  {k} {f}={json.dumps(v, default=str, ensure_ascii=False)}: {s['gates']} gated={s['gated']}")
    print(f"\n{n} runs: {crashes} crashes, {allpass} AllPass (value accepted as equal to gold), {gated_rows} gate firings")
    by_field = {}
    for k, f, v in sorted(seen_allpass):
        by_field.setdefault((k, f), []).append(v)
    for (k, f), vs in by_field.items():
        print(f"   AllPass kept on {k} {f}: {len(vs)} of {len(FUZZ_VALUES)} odd values" + ("" if len(vs) == len(FUZZ_VALUES) else f"  e.g. {vs[:6]}"))


def deadcode():
    """is the '2% close-enough' early exit in _scale_evidence ever decisive? compare the real function with a copy lacking it."""
    hdr("DEADCODE: does the abs(ratio-1) <= 0.02 clause ever change the outcome (gold = this case's C2 / C3 values)?")
    def no_clause(mv, gv, shares=None):
        if mv is None or gv in (None, 0) or abs(gv) < 1e-12 or mv == 0:
            return False
        ratio = mv / gv
        factors = [1e3, 1e-3, 1e6, 1e-6, 100.0, 0.01]
        if shares:
            factors += [float(shares), 1.0 / float(shares)]
        return any(abs(ratio / f - 1.0) <= 0.05 for f in factors)
    diff = 0
    n = 0
    import numpy as np  # noqa
    for gv in (207964686.19, 209010600.0, 51.9912, -0.75, -3000000.0):
        for r in list(np.linspace(0.5, 2.0, 30001)) + list(np.logspace(-9, 9, 20001)) + [-x for x in np.logspace(-9, 9, 2001)]:
            mv = gv * r
            n += 1
            if nv._scale_evidence(mv, gv, SHARES) != no_clause(mv, gv, SHARES):
                diff += 1
    print(f"{n} (mv, gv) pairs: the 2% clause changes the outcome in {diff} of them")
    # the factor windows vs the clause: smallest factor distance from 1.0
    fs = [1e3, 1e-3, 1e6, 1e-6, 100.0, 0.01, SHARES, 1 / SHARES]
    print("closest factor to 1.0 (in ratio terms):", min(fs, key=lambda f: abs(f - 1.0)), "; its 5% window is far outside the 2% clause band")


def side():
    """findings next to my surface that share the same root cause (reported, not my assigned atoms)."""
    hdr("SIDE: enum-echo hedges in other checkpoints, D1 prose, blank-vs-mis-scaled incentive")
    exp("D1.classification 'material|immaterial|none'", {"B": {"D1.classification": "material|immaterial|none"}}, cases="B")
    exp("P1.review_stage 'pre_release|post_release'", {"B": {"P1.review_stage": "pre_release|post_release"}}, cases="B")
    exp("D1.decision 'HOLD|RELEASE'", {"B": {"D1.decision": "HOLD|RELEASE"}}, cases="B")
    exp("D1.decision 'RELEASE|HOLD'", {"B": {"D1.decision": "RELEASE|HOLD"}}, cases="B")
    for d in ["HOLD|RELEASE", "RELEASE|HOLD", "HOLD RELEASE"]:
        s = nv._norm(d)
        s1 = nv._NEG_RELEASE_RE.sub("|", s)
        s1 = nv._NEG_HOLD_RE.sub("|", s1)
        s1 = nv._COND_PRE_RE.sub(nv._COND_KEEP, s1)
        s1 = nv._COND_POST_RE.sub(nv._COND_KEEP, s1)
        print(f"   _classify_decision({d!r}): norm={s} after-substitutions={s1} class={nv._classify_decision(d)}")
    exp("D1.offending_reason says OVERSTATED", {"B": {"D1.offending_reason": "SWAP-B mark leaves the NAV OVERSTATED by 0.7500 per share; "
                                                                           "shareholders who redeem at this NAV are overpaid"}}, cases="B")
    exp("D1.offending_reason = 'x'", {"B": {"D1.offending_reason": "x"}}, cases="B")
    exp("D1.escalate_to = 'x'", {"B": {"D1.escalate_to": "x"}}, cases="B")
    exp("C2 blank (None) TA/TNA/NAV", {"B": {"C2.total_assets": None, "C2.total_net_assets": None, "C2.nav_per_share": None}}, cases="B")
    exp("C2 mis-scaled /1000 TA/TNA/NAV", {"B": {"C2.total_assets": 209010.6, "C2.total_net_assets": 207964.68619, "C2.nav_per_share": 0.0519912}},
        cases="B")
    exp("B1 consequence flag: reprocessing false", {"B": {"C3.exceeds_reprocessing_pct": False}}, cases="B")


UNDER_PHRASES = [
    "understated", "Understated", "UNDERSTATED", "understated by 0.75", "understated by $0.75 per share", "NAV understated", "the NAV is understated",
    "administrator NAV understated", "administrator's NAV is understated", "Understated (admin below recomputed)",
    "understated - admin NAV below recomputed NAV", "under", "under-reported", "low", "too low", "NAV too low", "NAV is too low", "admin NAV too low",
    "lower than recomputed", "below", "below the correct NAV", "negative", "negative (admin below recomputed)", "short by 0.75", "understatement",
    "an understatement of 0.75", "NAV understatement", "yes, understated", "admin < recomputed", "Administrator NAV lower", "understated NAV",
    "underpriced", "underestimated", "undervalued", "the administrator understated the NAV", "swap understated", "SWAP-B understated",
    "preliminary NAV understated", "preliminary NAV is understated by $0.75", "Overall: understated", "Overall understated",
]
NONE_PHRASES = [
    "none", "None", "NONE", "no error", "No error", "no errors", "no error found", "no difference", "no differences", "ties", "tie", "tied",
    "tied out", "ties out", "ties to administrator", "NAV ties", "ties out to the administrator", "matches", "match", "agrees", "in agreement",
    "clean", "no break", "no breaks", "no exception", "no exceptions", "n/a", "N/A", "not applicable", "nil", "zero", "0", "-", "no variance",
    "within tolerance", "none - NAV ties", "none (ties)", "no direction", "no misstatement", "correct", "balanced", "no issue",
]
OVER_PHRASES = [
    "overstated", "OVERSTATED", "Overstated.", "overstated by 0.75", "NAV overstated", "the NAV is overstated", "administrator NAV overstated",
    "administrator's NAV is overstated", "over", "too high", "NAV too high", "NAV is too high", "high", "above", "above the correct NAV", "positive",
    "overvalued", "overestimated", "overstatement", "an overstatement of 0.75", "admin NAV higher", "higher than recomputed", "admin > recomputed",
]


def phrasings():
    hdr("PHRASINGS: how many natural phrasings of the right / the inverted direction does the grader read as intended?")
    def run(case, phrase):
        s = list(exp("ph", {"C3.direction": phrase}, cases=case, quiet=True).values())[0]
        return s
    ok = []; bad = []; fired = []
    for p in UNDER_PHRASES:
        s = run("B", p)
        (ok if met(s, "C3.direction") is None else bad).append(p)
        if "GATE.SIGN" in s["gates"]:
            fired.append(p)
    print(f"RIGHT 'understated' on B: {len(ok)} of {len(UNDER_PHRASES)} credited; failed {len(bad)}: {bad}")
    print(f"   of the failures, {len(fired)} also FIRE GATE.SIGN (a right answer read as inverted): {fired}")
    ok = []; bad = []
    for p in NONE_PHRASES:
        s = run("C", p)
        (ok if met(s, "C3.direction") is None else bad).append(p)
    print(f"RIGHT 'none' on C: {len(ok)} of {len(NONE_PHRASES)} credited; failed {len(bad)}: {bad}")
    caught = []; evaded = []
    for p in OVER_PHRASES:
        s = run("B", p)
        (caught if "GATE.SIGN" in s["gates"] else evaded).append(p)
    print(f"INVERTED 'overstated' on B: GATE.SIGN fires on {len(caught)} of {len(OVER_PHRASES)}; evades on {len(evaded)}: {evaded}")


GROUPS = dict(phrasings=phrasings, side=side,deadcode=deadcode, clean=clean,fuzz=fuzz,final=final, extra=extra, sweep=sweep,scale=scale, tol=tol, fmt=fmt, pct=pct, dir=dirs, bool=bools, misc=misc, scen=scen)

if __name__ == "__main__":
    want = sys.argv[1:] or ["all"]
    if "all" in want:
        want = list(GROUPS)
    for g in want:
        GROUPS[g]()
    out = os.environ.get("ATTACKER3_JSON")
    if out:
        with open(out, "w", encoding="utf-8") as fh:
            json.dump(RESULTS, fh, indent=1, ensure_ascii=False, default=str)
        print(f"\n[{len(RESULTS)} runs written to {out}]")

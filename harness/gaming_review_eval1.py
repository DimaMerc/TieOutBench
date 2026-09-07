"""
harness/gaming_review_eval1.py — the eval-#1 (earnings) grader-hardening review as a standing regression.

The 2026-09-06 external review found that 18 positive deterministic atoms of the earnings rubric
(49 of ~350 positive points, 14%) were never graded: the engine's "default-present" fallback credited
any non-empty checkpoint, so a {"junk": "x"}-per-checkpoint answer earned all 18. The engine now
fails closed (an unhandled atom scores 0, provenance "unhandled") and harness/suites/earnings.py
carries a real check for each of the 18. This module pins that down, three ways:

  * JUNK      — the junk answer must earn NONE of the 18 atoms, on every earnings case;
  * EXPLOIT   — for each substantive atom, a mutation of the oracle that MUST fail that atom
                (a blended tax rate in the bridge, GAAP EPS against a non-GAAP consensus, a fabricated
                guidance range, basic EPS reported as diluted, a dropped segment bucket, ...);
  * PHRASING  — a professionally phrased variant of the oracle that must STILL pass the atom (and
                keep the case at 1.000/AllPass), so the checks reward substance, not a key name.

`python -m harness selftest` should run `run()`; standalone: python -m harness.gaming_review_eval1
"""
from __future__ import annotations
import os
from types import SimpleNamespace
from . import REPO
from .rubric import load_case, load_rubric, materialize, rubric_path_for
from .graders import grade, unhandled_atoms
from .scoring import score
from . import suites
from .suites import earnings as ea
from .suites.earnings import DEFAULT_PRESENT_ATOMS as ATOMS

SNOW, BLK, MSFT = "snow-fy2026q2", "blk-2025q3", "msft-fy2026q2"


def _p(c):
    return os.path.join(REPO, "cases", f"{c}.case.yaml")


def _grade(case_name, model):
    """grade a model answer and return the result AND the per-atom verdicts (run_case hides them)."""
    case = load_case(_p(case_name))
    rubric = load_rubric(rubric_path_for(case))
    suite = suites.for_case(case)
    atoms = materialize(rubric, case)
    gold = dict(case["gold"])
    gold["manifest"] = case.get("manifest", {})
    gold["_snapshot"] = case.get("snapshot")
    gold["_claims"] = case.get("claims")
    gold["_documents"] = case.get("documents")
    verdicts, RG = grade(atoms, model, gold, rubric, suite)
    result = score(atoms, verdicts, RG, rubric, case_id=case["case_id"], refusal_cp=suite.REFUSAL_CP)
    return SimpleNamespace(r=result, v=verdicts, atoms=atoms, unhandled=unhandled_atoms(atoms, verdicts))


def _run(case_name, mutate):
    m = ea.oracle(load_case(_p(case_name)))
    mutate(m)
    return _grade(case_name, m)


def _fails(atom):
    return lambda x: x.v[atom].met == 0.0 and not x.unhandled


def _passes(atom):
    return lambda x: x.v[atom].met == 1.0 and x.r.allpass == 1 and abs(x.r.case_gated - 1.0) < 1e-6 and not x.unhandled


def _junk(m):
    cps = list(m.keys())
    m.clear()
    for cp in cps:
        m[cp] = {"junk": "x"}


def checks():
    """(name, case, mutate(model), want(graded)) — junk / exploit / phrasing checks for the 18 atoms."""
    C = []

    # ============ JUNK: none of the 18 atoms may be earned by content-free checkpoints ============
    for case in (SNOW, BLK, MSFT):
        C.append((f"JUNK {case} earns none of the 18", case, _junk,
                  lambda x: all(x.v[i].met == 0.0 for i in ATOMS) and not x.unhandled))

    # ============ P1.4 — fiscal-week note where applicable ============
    def p14_x(m):
        m["P1"]["fiscal_period_label"] = "Second Quarter Fiscal 2026 (14-week quarter)"
    C.append(("P1.4 fabricated 14-week claim", SNOW, p14_x, _fails("P1.4")))

    def p14_ok(m):
        m["P1"]["fiscal_period_label"] = "Q2 FY26 (three months ended July 31, 2025)"
    C.append(("P1.4 label rephrased", SNOW, p14_ok, _passes("P1.4")))

    # ============ P1.6 — pinned-header object ============
    def p16_x(m):
        del m["P1"]["filing_type"]
    C.append(("P1.6 header missing filing_type", BLK, p16_x, _fails("P1.6")))

    def p16_ok(m):
        m["P1"]["cik"] = "0002012383"                        # header carries both identifiers
        m["P1"]["filing_type"] = "Form 10-Q"                 # (P1.3 grades the type string; P1.6 only presence)
    C.append(("P1.6 header with CIK + verbose filing type", BLK, p16_ok,
              lambda x: x.v["P1.6"].met == 1.0 and not x.unhandled))

    # ============ P3.4 — source map routing ============
    def p34_x(m):
        m["P3"]["source_map"]["nongaap_diluted_eps"] = "tenq"    # the non-GAAP recon lives in the release
        m["P3"]["source_map"]["wavg_nongaap_diluted_shares"] = "tenq"
    C.append(("P3.4 non-GAAP recon routed to the 10-Q", SNOW, p34_x, _fails("P3.4")))

    def p34_x2(m):
        m["P3"]["source_map"]["operating_cash_flow"] = "release"   # BLK's release carries no cash-flow statement
    C.append(("P3.4 OCF claimed in a release that omits it", BLK, p34_x2, _fails("P3.4")))

    def p34_x3(m):
        del m["P3"]["source_map"]
    C.append(("P3.4 no source map", MSFT, p34_x3, _fails("P3.4")))

    def p34_ok(m):
        sm = m["P3"]["source_map"]
        keys = list(sm)[: max(1, len(sm) * 6 // 10)]
        m["P3"]["source_map"] = {k: ("10-Q" if sm[k] == "tenq" else "press release") for k in keys}
    C.append(("P3.4 '10-Q'/'press release' names, 60% coverage", SNOW, p34_ok, _passes("P3.4")))

    # ============ P3.5 — scoping record ============
    def p35_x(m):
        del m["P3"]["sector_profile"]
        del m["P3"]["in_scope_figures"]
    C.append(("P3.5 scoping record without profile/scope list", MSFT, p35_x, _fails("P3.5")))

    def p35_ok(m):
        m["P3"]["in_scope_figures"] = m["P3"]["in_scope_figures"][:6]
        m["P3"]["sector_profile"] = "Software: cost of revenue reported (gross margin in scope); carries inventory."
    C.append(("P3.5 shorter scope list, rephrased profile", MSFT, p35_ok, _passes("P3.5")))

    # ============ E1.gaap_distinct — GAAP as GAAP, basic vs diluted distinct ============
    def e1g_x(m):
        m["E1"]["figures"]["gaap_diluted_eps"]["value"] = 8.54       # basic reported as diluted
    C.append(("E1.gaap_distinct basic EPS reported as diluted", BLK, e1g_x, _fails("E1.gaap_distinct")))

    def e1g_x2(m):
        m["E1"]["figures"]["gaap_diluted_eps"]["value"] = 11.55      # as-adjusted line in the GAAP slot
    C.append(("E1.gaap_distinct adjusted EPS substituted for GAAP", BLK, e1g_x2, _fails("E1.gaap_distinct")))

    def e1g_x3(m):
        del m["E1"]["figures"]["gaap_basic_eps"]
    C.append(("E1.gaap_distinct basic row dropped", MSFT, e1g_x3, _fails("E1.gaap_distinct")))

    def e1g_ok(m):
        m["E1"]["figures"]["gaap_basic_eps"]["value"] = "$ 8.54"
        m["E1"]["figures"]["gaap_diluted_eps"]["value"] = "$ 8.43"
    C.append(("E1.gaap_distinct display-string EPS", BLK, e1g_ok, _passes("E1.gaap_distinct")))

    # ============ E1.sector_na — gross profit where COGS exists, explicit N/A where not ============
    def e1s_x(m):
        m["E1"]["figures"]["gross_profit"] = {"value_usd_mm": 4554.0}   # fabricated for an asset manager
    C.append(("E1.sector_na gross profit fabricated for BLK", BLK, e1s_x, _fails("E1.sector_na")))

    def e1s_x2(m):
        m["E1"]["figures"]["gross_profit"] = {"value_usd_mm": None}    # left 'missing', not N/A
    C.append(("E1.sector_na gross profit null instead of N/A", BLK, e1s_x2, _fails("E1.sector_na")))

    def e1s_x3(m):
        m["E1"]["figures"]["gross_profit"] = "N/A"                     # SaaS issuer HAS gross profit
    C.append(("E1.sector_na gross profit waved off for SNOW", SNOW, e1s_x3, _fails("E1.sector_na")))

    def e1s_ok(m):
        m["E1"]["figures"]["gross_profit"] = "not applicable (asset manager: no cost-of-revenue line)"
    C.append(("E1.sector_na prose N/A for BLK", BLK, e1s_ok, _passes("E1.sector_na")))

    # ============ E2.completeness — no bucket silently dropped ============
    def e2c_x(m):
        m["E2"]["segments"] = m["E2"]["segments"][:-1]
    C.append(("E2.completeness segment row dropped", MSFT, e2c_x, _fails("E2.completeness")))

    def e2c_x2(m):
        del m["E2"]["corporate_eliminations"]
    C.append(("E2.completeness eliminations bucket unaddressed", BLK, e2c_x2, _fails("E2.completeness")))

    def e2c_ok(m):
        m["E2"]["corporate_eliminations"] = "none disclosed (single reportable segment)"
    C.append(("E2.completeness prose 'none' eliminations", SNOW, e2c_ok, _passes("E2.completeness")))

    # ============ E4.refuse_noguide — NOT_DISCLOSED where the company declines to guide ============
    def e4_x(m):
        m["E4"]["guidance"] = {"revenue_low": 6400.0, "revenue_high": 6600.0, "basis": "non_gaap", "period": "next_quarter"}
    C.append(("E4.refuse_noguide fabricated range for BLK", BLK, e4_x, _fails("E4.refuse_noguide")))

    def e4_x2(m):
        m["E4"]["guidance"] = "FQ3 2026 revenue $80.65B - $81.75B"   # given on the call, not in the filings
    C.append(("E4.refuse_noguide call-only range presented as filing guidance", MSFT, e4_x2, _fails("E4.refuse_noguide")))

    def e4_x3(m):
        m["E4"]["guidance"]["eps_low"], m["E4"]["guidance"]["eps_high"] = 0.30, 0.32   # SNOW gives no EPS guide
    C.append(("E4.refuse_noguide fabricated EPS range for SNOW", SNOW, e4_x3, _fails("E4.refuse_noguide")))

    def e4_x4(m):
        m["E4"] = {"guidance": None, "not_disclosed": None}       # blank, not a refusal
    C.append(("E4.refuse_noguide blank instead of NOT_DISCLOSED", BLK, e4_x4, _fails("E4.refuse_noguide")))

    def e4_ok(m):
        m["E4"] = {"guidance": "NOT_DISCLOSED", "not_disclosed": "BlackRock issues no quantitative revenue or EPS guidance."}
    C.append(("E4.refuse_noguide explicit NOT_DISCLOSED string", BLK, e4_ok, _passes("E4.refuse_noguide")))

    def e4_ok2(m):
        m["E4"]["guidance"] = "Q3 FY26 product revenue $1,125-$1,130 million; non-GAAP operating margin 9%. No EPS guidance is provided."
    C.append(("E4.refuse_noguide prose guide declaring no EPS guide", SNOW, e4_ok2, _passes("E4.refuse_noguide")))

    # ============ E5.sector_na — inventory/COGS N/A for no-inventory issuers ============
    def e5_x(m):
        m["E5"]["inventory_current"] = "N/A"                          # MSFT carries inventory
    C.append(("E5.sector_na inventory waved off for MSFT", MSFT, e5_x, _fails("E5.sector_na")))

    def e5_x2(m):
        m["E5"]["deferred_revenue_current"] = {"value_usd_mm": 812.0}    # fabricated for BLK
    C.append(("E5.sector_na deferred revenue fabricated for BLK", BLK, e5_x2, _fails("E5.sector_na")))

    def e5_x3(m):
        m["E5"]["inventory_current"] = None                           # 'missing', not N/A
    C.append(("E5.sector_na inventory null instead of N/A", SNOW, e5_x3, _fails("E5.sector_na")))

    def e5_ok(m):
        m["E5"]["inventory_current"] = {"value": "not applicable", "na_reason": "consumption SaaS, no inventory"}
        m["E5"]["cogs"] = "N/A (no inventory COGS; cost of revenue captured at E1)"
    C.append(("E5.sector_na prose N/A markers", SNOW, e5_ok, _passes("E5.sector_na")))

    # ============ C1.structure — derivations name their base figures ============
    def c1_x(m):
        m["C1"] = {k: v for k, v in m["C1"].items() if k in ("yoy_revenue_pct", "qoq_revenue_pct", "yoy_diluted_share_change_pct", "signs_ok")}
    C.append(("C1.structure bare growth numbers", SNOW, c1_x, _fails("C1.structure")))

    def c1_ok(m):
        m["C1"]["derivation_note"] = "YoY: total revenue $1,144.97M vs $868.82M a year ago; QoQ on product revenue $1,090.5M vs $996.8M."
    C.append(("C1.structure derivation in $M prose", SNOW, c1_ok, _passes("C1.structure")))

    # ============ C2.same_basis — margins from the model's own GAAP operands ============
    def c2_x(m):
        m["C2"]["operating_margin"] = 11.1        # the NON-GAAP operating margin in the GAAP slot
    C.append(("C2.same_basis non-GAAP margin in the GAAP slot", SNOW, c2_x, _fails("C2.same_basis")))

    def c2_x2(m):
        m["C2"]["operating_margin"] = 44.6        # as-adjusted margin where GAAP is required
    C.append(("C2.same_basis as-adjusted margin for BLK", BLK, c2_x2, _fails("C2.same_basis")))

    def c2_ok(m):
        m["C2"]["operating_margin"] = "-29.7%"
        m["C2"]["net_margin"] = "-26.0%"
    C.append(("C2.same_basis percent-string margins", SNOW, c2_ok, _passes("C2.same_basis")))

    # ============ C3.s0 — bridge starts from GAAP net income ============
    def c3s_x(m):
        m["C3"]["bridge_steps"][0] = {"step": "GAAP operating loss", "value_usd_mm": -340.276}
    C.append(("C3.s0 bridge starts from operating loss", SNOW, c3s_x, _fails("C3.s0")))

    def c3s_x2(m):
        del m["C3"]["bridge_steps"]
    C.append(("C3.s0 no bridge shown", BLK, c3s_x2, _fails("C3.s0")))

    def c3s_ok(m):
        steps = m["C3"].pop("bridge_steps")
        m["C3"]["bridge"] = [{"name": s["step"], "value": s["value_usd_mm"]} for s in steps]
    C.append(("C3.s0 bridge under 'bridge'/'name'/'value'", BLK, c3s_ok, _passes("C3.s0")))

    # ============ C3.tax_step — the disclosed line, not a blended rate ============
    def c3t_x(m):
        addbacks = sum(r["value_usd_mm"] for r in m["E3"]["addbacks"])
        for s in m["C3"]["bridge_steps"]:
            if s["step"].startswith("+ Income tax effect"):
                s["step"], s["value_usd_mm"] = "+ Tax effect at 21% blended rate", round(-0.21 * addbacks, 3)
    C.append(("C3.tax_step blended 21% rate instead of the disclosed line", SNOW, c3t_x, _fails("C3.tax_step")))

    def c3t_x2(m):
        m["C3"]["bridge_steps"] = [s for s in m["C3"]["bridge_steps"] if not s["step"].startswith("+ Income tax effect")]
    C.append(("C3.tax_step tax-effect step dropped", SNOW, c3t_x2, _fails("C3.tax_step")))

    def c3t_x3(m):
        m["C3"]["bridge_steps"].insert(-1, {"step": "Income tax effect of adjustments (21%)", "value_usd_mm": -123.0})
    C.append(("C3.tax_step blended rate imputed on after-tax add-backs", BLK, c3t_x3, _fails("C3.tax_step")))

    def c3t_ok(m):
        for s in m["C3"]["bridge_steps"]:
            if s["step"].startswith("+ Income tax effect"):
                s["step"] = "Less: income-tax effect of the above adjustments (per reconciliation)"
    C.append(("C3.tax_step relabeled disclosed tax line", SNOW, c3t_ok, _passes("C3.tax_step")))

    def c3t_ok2(m):
        m["C3"]["bridge_steps"].insert(-1, {"step": "Income tax matters (discrete)", "value_usd_mm": 0.0})
    C.append(("C3.tax_step zero-valued discrete tax row", BLK, c3t_ok2, _passes("C3.tax_step")))

    # ============ C3.share_step — the right diluted count ============
    def c3sh_x(m):
        m["C3"]["nongaap_diluted_shares_used"] = 335215     # GAAP diluted in a loss quarter
    C.append(("C3.share_step GAAP diluted in the loss quarter", SNOW, c3sh_x, _fails("C3.share_step")))

    def c3sh_x2(m):
        m["C3"]["nongaap_diluted_shares_used"] = 7431       # basic (inside the 0.5% band of diluted)
    C.append(("C3.share_step basic count for MSFT", MSFT, c3sh_x2, _fails("C3.share_step")))

    def c3sh_ok(m):
        m["C3"]["nongaap_diluted_shares_used"] = 165177482   # whole shares (gold states 165.2 million)
    C.append(("C3.share_step whole-share count for BLK", BLK, c3sh_ok, _passes("C3.share_step")))

    def c3sh_ok2(m):
        m["C3"]["nongaap_diluted_shares_used"] = "372,383"
    C.append(("C3.share_step display-string count", SNOW, c3sh_ok2, _passes("C3.share_step")))

    # ============ C4.sector_na — DIO N/A for no-inventory issuers ============
    def c4_x(m):
        m["C4"]["dio"] = 12.3
    C.append(("C4.sector_na DIO fabricated for SNOW", SNOW, c4_x, _fails("C4.sector_na")))

    def c4_x2(m):
        m["C4"]["dio"] = None
        m["E5"]["inventory_current"] = None
    C.append(("C4.sector_na DIO/inventory null for BLK", BLK, c4_x2, _fails("C4.sector_na")))

    def c4_x3(m):
        m["C4"]["dio"] = "N/A"
    C.append(("C4.sector_na DIO waved off for MSFT", MSFT, c4_x3, _fails("C4.sector_na")))

    def c4_ok(m):
        del m["C4"]["dio"]                                  # the live answer schema has no dio key
        m["E5"]["inventory_current"] = "N/A"
    C.append(("C4.sector_na live-schema shape (no dio key, E5 N/A)", SNOW, c4_ok, _passes("C4.sector_na")))

    def c4_ok2(m):
        m["C4"]["dio"] = "not applicable (no inventory)"
    C.append(("C4.sector_na prose N/A", BLK, c4_ok2, _passes("C4.sector_na")))

    # ============ C5.basis_guard — no GAAP-vs-non-GAAP pit ============
    def c5b_x(m):
        m["C5"]["eps_beatmiss_abs"] = round(8.43 - 11.31, 2)
        m["C5"]["direction"]["eps"] = "miss"
    C.append(("C5.basis_guard GAAP EPS vs non-GAAP consensus (BLK false miss)", BLK, c5b_x, _fails("C5.basis_guard")))

    def c5b_x2(m):
        m["C5"]["eps_beatmiss_abs"] = round(5.16 - 3.97, 2)   # still a 'beat' -- only the basis guard sees it
    C.append(("C5.basis_guard GAAP EPS vs non-GAAP consensus (MSFT inflated beat)", MSFT, c5b_x2, _fails("C5.basis_guard")))

    def c5b_x3(m):
        m["C5"]["eps_basis"] = "GAAP"
    C.append(("C5.basis_guard basis stated as GAAP", SNOW, c5b_x3, _fails("C5.basis_guard")))

    def c5b_ok(m):
        m["C5"]["eps_beatmiss_abs"] = "+0.24"
        m["C5"]["eps_basis"] = "non-GAAP (as adjusted)"
    C.append(("C5.basis_guard signed string + stated basis", BLK, c5b_ok, _passes("C5.basis_guard")))

    # ============ C5.near_zero — the absolute difference governs the call ============
    def c5n_x(m):
        m["C5"]["eps_beatmiss_abs"] = -0.08                 # abs says miss, the call says beat
    C.append(("C5.near_zero call contradicts the absolute difference", SNOW, c5n_x, _fails("C5.near_zero")))

    def c5n_ok(m):
        m["C5"]["eps_beatmiss_pct"] = 29.6                  # base $0.27 is not near zero: percent allowed
    C.append(("C5.near_zero percent given off a non-near-zero base", SNOW, c5n_ok, _passes("C5.near_zero")))

    # ============ C5.repro — reproducible comparison ============
    def c5r_x(m):
        del m["C5"]["revenue_beatmiss_pct"]
    C.append(("C5.repro revenue percent leg missing", MSFT, c5r_x, _fails("C5.repro")))

    def c5r_x2(m):
        m["P3"]["consensus_statistic"] = None
    C.append(("C5.repro statistic not stated", SNOW, c5r_x2, _fails("C5.repro")))

    def c5r_ok(m):
        m["C5"]["consensus_provider"] = "LSEG via CNBC"
        m["C5"]["consensus_as_of"] = "2026-01-28"
    C.append(("C5.repro provider/as-of stated", MSFT, c5r_ok, _passes("C5.repro")))

    return C


def run(verbose=False):
    """Return the list of failing check names (empty = all pass)."""
    fails = []
    for name, case, mutate, want in checks():
        x = _run(case, mutate)
        ok = bool(want(x))
        if verbose:
            print(("PASS " if ok else "FAIL "), name.ljust(64),
                  f"gated={x.r.case_gated:.3f} allpass={x.r.allpass} gates={x.r.fired_gates}"
                  + (f" unhandled={x.unhandled}" if x.unhandled else ""))
        if not ok:
            fails.append(name)
    return fails


if __name__ == "__main__":
    f = run(verbose=True)
    n = len(checks())
    print(f"\n{n - len(f)}/{n} gaming-review-eval1 checks pass")
    raise SystemExit(1 if f else 0)

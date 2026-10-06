#!/usr/bin/env python
"""scratch_attacker5.py - attacker 5 (planning / structure / regime atoms of eval #7).

Usage:  python scratch_attacker5.py [S0 S1 ...]     (no args = every section)
Every attack is a dict patch of dotted paths onto the schema-shaped oracle answer (dates as strings, the
way a live model's JSON arrives); DEL deletes a key. Each result line is checked against run_case().
"""
import sys, copy, json
sys.path.insert(0, r"C:\Projects\finance-llm-evals")
from harness import run_case, suites
from harness.rubric import load_case, load_rubric, materialize, rubric_path_for
from harness.graders import grade
from harness.scoring import score
from harness.suites import nav_oversight as nv
from harness.live_nav_oversight import oracle_to_schema

CASES = {"break": r"C:\Projects\finance-llm-evals\cases\grsl-nav-2026.case.yaml",
         "clean": r"C:\Projects\finance-llm-evals\cases\grsl-nav-2026-clean.case.yaml"}
DEL = "<<DELETE>>"
_cache = {}


def _ctx(key):
    if key not in _cache:
        path = CASES[key]
        case = load_case(path)
        rubric = load_rubric(rubric_path_for(case))
        suite = suites.for_case(case)
        atoms = materialize(rubric, case)
        _cache[key] = (path, case, rubric, suite, atoms)
    return _cache[key]


def base(key):
    return oracle_to_schema(_ctx(key)[1])


def grade_full(key, model):
    path, case, rubric, suite, atoms = _ctx(key)
    gold = dict(case["gold"])
    gold["manifest"] = case.get("manifest", {})
    gold["_snapshot"] = case.get("snapshot")
    gold["_claims"] = case.get("claims")
    gold["_documents"] = case.get("documents")
    verdicts, rg = grade(atoms, copy.deepcopy(model), gold, rubric, suite)
    res = score(atoms, verdicts, rg, rubric, case_id=case["case_id"], refusal_cp=suite.REFUSAL_CP)
    return res, verdicts


def setp(m, path, val):
    parts = path.split(".")
    cur = m
    for p in parts[:-1]:
        if not isinstance(cur.get(p), dict):
            cur[p] = {}
        cur = cur[p]
    if val == DEL:
        cur.pop(parts[-1], None)
    else:
        cur[parts[-1]] = val


def build(key, patch=None, fn=None):
    m = base(key)
    for p, v in (patch or {}).items():
        setp(m, p, v)
    if fn:
        fn(m)
    return m


def summarize(res, v, v0):
    flips = {a: f"{v0[a].met:.2f}>{v[a].met:.2f}" for a in v
             if a in v0 and abs(v0[a].met - v[a].met) > 1e-9}
    return flips


def run(label, patch=None, fn=None, keys=("break", "clean"), ref=None, wide=False):
    """ref: optional (patch, fn) pair defining the 'before' answer (default = the perfect oracle).
    Prints ONE line when both cases behave identically, two lines otherwise."""
    shown = json.dumps(patch, default=str) if patch else "(fn)"
    if len(shown) > 150 and not wide:
        shown = shown[:147] + "..."
    rows = {}
    for key in keys:
        try:
            m0 = build(key, *(ref or (None, None)))
            r0, v0 = grade_full(key, m0)
            m = build(key, patch, fn)
            r, v = grade_full(key, m)
            r2, _ = run_case(CASES[key], model_output=copy.deepcopy(m))
            assert (r2.case_gated, r2.fired_gates, r2.allpass) == (r.case_gated, r.fired_gates, r.allpass), "run_case mismatch"
            flips = summarize(r, v, v0)
            extra = ""
            if r.flags:
                extra += f" flags={r.flags}"
            if tuple(round(x, 2) for x in r.e6) != (1.0, 1.0):
                extra += f" e6={tuple(round(x, 2) for x in r.e6)}"
            rows[key] = (f"before={r0.case_gated:.4f} after={r.case_gated:.4f} AP={r.allpass} gates={r.fired_gates}{extra} flips={flips}")
        except Exception as e:  # noqa
            rows[key] = f"CRASH {type(e).__name__}: {e}"
    if len(keys) > 1 and len(set(rows.values())) == 1:
        print(f"[{label}] both  {list(rows.values())[0]}  patch={shown}")
    else:
        for key, txt in rows.items():
            print(f"[{label}] {key:5s} {txt}  patch={shown}")


def section(name):
    print("\n" + "=" * 20 + " " + name + " " + "=" * 20)


# --------------------------------------------------------------------------------------------------
def S0():
    section("S0 sanity: oracle on both cases")
    for key in ("break", "clean"):
        path, case, *_ = _ctx(key)
        r, _ = run_case(path, model_output=nv.oracle(case))
        r2, _ = run_case(path, model_output=base(key))
        print(key, "raw oracle:", r.case_gated, r.allpass, r.fired_gates, "| schema round-trip:", r2.case_gated, r2.allpass, r2.fired_gates)
        # weights of the atoms under attack, as a share of the case score
    path, case, rubric, suite, atoms = _ctx("break")
    cpw = rubric["meta"]["checkpoint_weights"]
    raw = {}
    for a in atoms:
        if a.points > 0:
            raw[a.checkpoint] = raw.get(a.checkpoint, 0) + a.points
    for aid in ("P1.1", "P1.2", "P1.3", "P1.4", "P1.5", "C1.structure", "D1.decision", "D1.classify", "D1.localize", "D1.record"):
        a = [x for x in atoms if x.id == aid][0]
        print(f"  {aid:13s} points={a.points} share of case score = {cpw[a.checkpoint] * a.points / raw[a.checkpoint]:.4f}")


def S1():
    section("S1 P1.1 package identity")
    F = "Granite Ridge 2x Daily U.S. Semiconductor ETF"
    for label, patch in [
        ("fund-case", {"P1.fund": "Granite Ridge 2X Daily U.S. Semiconductor ETF"}),
        ("fund-lower", {"P1.fund": F.lower()}),
        ("fund-US", {"P1.fund": "Granite Ridge 2x Daily US Semiconductor ETF"}),
        ("fund-with-ticker", {"P1.fund": F + " (GRSL)"}),
        ("fund-trailing-period", {"P1.fund": F + "."}),
        ("fund-double-space", {"P1.fund": F.replace(" ", "  ", 1)}),
        ("fund-padded", {"P1.fund": "  " + F + "  "}),
        ("ticker-lower", {"P1.ticker": "grsl"}),
        ("ticker-dollar", {"P1.ticker": "$GRSL"}),
        ("ticker-exch", {"P1.ticker": "NYSE: GRSL"}),
        ("pkgid-lower", {"P1.package_id": "nav-grsl-20260623-prelim"}),
        ("pkgid-trailing", {"P1.package_id": "NAV-GRSL-20260623-PRELIM "}),
        ("pkgid-wrong-date", {"P1.package_id": "NAV-GRSL-20260622-PRELIM"}),
        ("fund-wrong", {"P1.fund": "Granite Ridge 3x Daily U.S. Semiconductor ETF"}),
        ("fund-missing", {"P1.fund": DEL}),
    ]:
        run("P1.1/" + label, patch)


def S2():
    section("S2 P1.2 date pin / GATE.DATE")
    V, P = "P1.valuation_date", "P1.prior_valuation_date"
    for label, patch in [
        ("val-time", {V: "2026-06-23T00:00:00"}),
        ("val-timeZ", {V: "2026-06-23T00:00:00Z"}),
        ("val-space-time", {V: "2026-06-23 00:00:00"}),
        ("val-dmY-words", {V: "23 June 2026"}),
        ("val-words", {V: "June 23, 2026"}),
        ("val-us-slash", {V: "06/23/2026"}),
        ("val-ymd-slash", {V: "2026/06/23"}),
        ("val-compact", {V: "20260623"}),
        ("val-nozero", {V: "2026-6-23"}),
        ("val-weekday", {V: "2026-06-23 (Tuesday)"}),
        ("val-padded", {V: " 2026-06-23 "}),
        ("prior-time", {P: "2026-06-22T00:00:00"}),
        ("prior-missing", {P: DEL}),
        ("prior-null", {P: None}),
        ("prior-friday", {P: "2026-06-19"}),
        ("val-missing", {V: DEL}),
        ("both-time", {V: "2026-06-23T00:00:00", P: "2026-06-22T00:00:00"}),
        ("swapped", {V: "2026-06-22", P: "2026-06-23"}),
        ("val-right-prior-right-extra-key", {"P1.package_date": "2026-06-22"}),
        ("whole-P1-missing", {"P1": DEL}),
        ("P1-empty-dict", {"P1": {}}),
    ]:
        run("P1.2/" + label, patch)


def S3():
    section("S3 P1.3 review inputs (leverage etc.)")
    for label, patch in [
        ("lev-2x", {"P1.leverage": "2x"}),
        ("lev-2.0x", {"P1.leverage": "2.0x"}),
        ("lev-2.00x", {"P1.leverage": "2.00x"}),
        ("lev-times-sign", {"P1.leverage": "2\u00d7"}),
        ("lev-200pct", {"P1.leverage": "200%"}),
        ("lev-str2.0", {"P1.leverage": "2.0"}),
        ("lev-2.0009", {"P1.leverage": 2.0009}),
        ("lev-int2", {"P1.leverage": 2}),
        ("shares-4M", {"P1.prior_shares_outstanding": "4M"}),
        ("shares-commas", {"P1.prior_shares_outstanding": "4,000,000"}),
        ("shares-4.0 million", {"P1.prior_shares_outstanding": "4.0 million"}),
        ("priornav-dollar", {"P1.prior_nav_per_share": "$50.00"}),
        ("priornav-50.0002", {"P1.prior_nav_per_share": 50.0002}),
        ("adminnav-usd", {"P1.admin_prelim_nav_per_share": "51.2412 USD"}),
        ("adminnav-corrected(break wrong)", {"P1.admin_prelim_nav_per_share": 51.9912}),
    ]:
        run("P1.3/" + label, patch)


def S4():
    section("S4 P1.4 regime / GATE.REGIME")
    J, FL, RP, ST, BD = "P1.regime.jurisdiction", "P1.regime.per_share_floor_usd", "P1.regime.reprocessing_pct", "P1.review_stage", "P1.regime.oversight_band_pp"
    for label, patch in [
        # jurisdiction
        ("j-USA", {J: "USA"}),
        ("j-United States", {J: "United States"}),
        ("j-U.S.", {J: "U.S."}),
        ("j-U.S.A.", {J: "U.S.A."}),
        ("j-United States of America", {J: "United States of America"}),
        ("j-us", {J: "us"}),
        ("j-padded", {J: " US "}),
        ("j-US-SEC", {J: "US (SEC)"}),
        ("j-missing", {J: DEL}),
        ("j-null", {J: None}),
        ("j-empty", {J: ""}),
        ("j-LU(control)", {J: "LU"}),
        # floor
        ("f-1(cents)", {FL: 1}),
        ("f-'1'", {FL: "1"}),
        ("f-'0.01'", {FL: "0.01"}),
        ("f-'$0.01'", {FL: "$0.01"}),
        ("f-'1 cent'", {FL: "1 cent"}),
        ("f-0.011", {FL: 0.011}),
        ("f-0.0109", {FL: 0.0109}),
        ("f-0.0111", {FL: 0.0111}),
        ("f-0.009", {FL: 0.009}),
        ("f-0.0089", {FL: 0.0089}),
        ("f-0", {FL: 0}),
        ("f-null", {FL: None}),
        ("f-missing", {FL: DEL}),
        # reprocessing pct
        ("r-0.005(fraction)", {RP: 0.005}),
        ("r-'0.5%'", {RP: "0.5%"}),
        ("r-'0.50 %'", {RP: "0.50 %"}),
        ("r-'0.5 percent'", {RP: "0.5 percent"}),
        ("r-'half a percent'", {RP: "half a percent"}),
        ("r-0.51", {RP: 0.51}),
        ("r-0.52", {RP: 0.52}),
        ("r-0.49", {RP: 0.49}),
        ("r-50", {RP: 50}),
        ("r-1.0(CSSF)", {RP: 1.0}),
        ("r-null", {RP: None}),
        # stage
        ("s-preliminary", {ST: "preliminary"}),
        ("s-pre release", {ST: "pre release"}),
        ("s-pre-release review", {ST: "pre-release review"}),
        ("s-before release", {ST: "before release"}),
        ("s-prior to release", {ST: "prior to release"}),
        ("s-not yet released", {ST: "not yet released"}),
        ("s-pending oversight release", {ST: "pending oversight release"}),
        ("s-unreleased", {ST: "unreleased"}),
        ("s-post_release", {ST: "post_release"}),
        ("s-post-release", {ST: "post-release"}),
        ("s-Post Release", {ST: "Post Release"}),
        ("s-previously released(WRONG stage)", {ST: "previously released"}),
        ("s-previously published(WRONG stage)", {ST: "previously published"}),
        ("s-pre_release_but_post_release_rules(WRONG)", {ST: "pre_release; treat as post_release"}),
        ("s-pre or post", {ST: "pre-release or post-release"}),
        ("s-preliminary post-release(WRONG)", {ST: "preliminary NAV, post-release review"}),
        ("s-release", {ST: "release"}),
        ("s-empty", {ST: ""}),
        ("s-null", {ST: None}),
        ("s-missing", {ST: DEL}),
        ("s-nested-in-regime", {ST: DEL, "P1.regime.review_stage": "pre_release"}),
        # band (not graded by P1.4?)
        ("b-99", {BD: 99}),
        ("b-null", {BD: None}),
        ("b-missing", {BD: DEL}),
        ("b-0.0001", {BD: 0.0001}),
        # regime shape
        ("regime-string", {"P1.regime": "US"}),
        ("regime-list", {"P1.regime": ["US", 0.01, 0.5]}),
        ("regime-null", {"P1.regime": None}),
        ("regime-numbers-at-P1-level", {"P1.regime": DEL, "P1.jurisdiction": "US", "P1.per_share_floor_usd": 0.01, "P1.reprocessing_pct": 0.5}),
    ]:
        run("P1.4/" + label, patch)


def S5():
    section("S5 P1.5 pinned-package object")
    PK = lambda: {"P1": {"fund": "x", "valuation_date": "x", "admin_prelim_nav_per_share": "x", "regime": "x"}}
    for label, patch in [
        ("regime-empty-dict", {"P1.regime": {}}),
        ("regime-allnull-dict", {"P1.regime": {"jurisdiction": None, "per_share_floor_usd": None, "reprocessing_pct": None}}),
        ("regime-list-empty", {"P1.regime": []}),
        ("regime-0", {"P1.regime": 0}),
        ("regime-false", {"P1.regime": False}),
        ("regime-space", {"P1.regime": " "}),
        ("regime-n/a", {"P1.regime": "n/a"}),
        ("regime-missing", {"P1.regime": DEL}),
        ("fund-space", {"P1.fund": " "}),
        ("admin-nav-0", {"P1.admin_prelim_nav_per_share": 0}),
        ("admin-nav-n/a", {"P1.admin_prelim_nav_per_share": "n/a"}),
        ("valdate-junk", {"P1.valuation_date": "TBD"}),
    ]:
        run("P1.5/" + label, patch)
    # isolated gain: answer with ONLY the four junk placeholders vs the same with them deleted
    junk = lambda m: m.__setitem__("P1", {"fund": "x", "valuation_date": "x", "admin_prelim_nav_per_share": "x", "regime": {"a": None}})
    none = lambda m: m.__setitem__("P1", {})
    for key in ("break", "clean"):
        r0, v0 = grade_full(key, build(key, fn=none))
        r1, v1 = grade_full(key, build(key, fn=junk))
        print(f"[P1.5/isolated-junk] {key:5s} P1 empty {r0.case_gated:.4f} -> P1 four junk placeholders {r1.case_gated:.4f} "
              f"P1.5 {v0['P1.5'].met}->{v1['P1.5'].met} gates {r1.fired_gates}")


def S6():
    section("S6 C1.structure")
    R = "C1.recon"
    for label, patch in [
        ("two-junk-dicts", {R: [{"x": 1}, {"y": 2}]}),
        ("two-strings", {R: ["a", "b"]}),
        ("two-None", {R: [None, None]}),
        ("two-empty-dicts", {R: [{}, {}]}),
        ("two-empty-lists", {R: [[], []]}),
        ("two-ints", {R: [1, 2]}),
        ("one-row", {R: [{"line_id": "EQ-SMH", "admin_value": 1, "independent_value": 1, "status": "match"}]}),
        ("dict-keyed", {R: {"EQ-SMH": {"admin_value": 1}, "SWAP-A": {"admin_value": 2}}}),
        ("missing", {R: DEL}),
        ("empty-list", {R: []}),
    ]:
        run("C1.structure/" + label, patch)
    # isolated gain
    for key in ("break", "clean"):
        r0, v0 = grade_full(key, build(key, {R: []}))
        r1, v1 = grade_full(key, build(key, {R: [{"x": 1}, {"y": 2}]}))
        print(f"[C1.structure/isolated] {key:5s} recon=[] {r0.case_gated:.4f} -> two junk rows {r1.case_gated:.4f}  "
              f"C1.structure {v0['C1.structure'].met}->{v1['C1.structure'].met}")


def S7():
    section("S7 D1.classify")
    C, RR = "D1.classification", "D1.reprocessing_required"
    for label, patch in [
        ("c-Material", {C: "Material"}),
        ("c-material error", {C: "material error"}),
        ("c-materially misstated", {C: "materially misstated"}),
        ("c-MATERIAL - reprocess", {C: "MATERIAL - reprocess"}),
        ("c-material (above floor and 0.5%)", {C: "material (above the per-share floor and the 0.5% threshold)"}),
        ("c-significant", {C: "significant"}),
        ("c-major", {C: "major"}),
        ("c-above floor", {C: "above floor"}),
        ("c-immaterial", {C: "immaterial"}),
        ("c-not material", {C: "not material"}),
        ("c-below floor", {C: "below floor"}),
        ("c-no error", {C: "no error"}),
        ("c-none", {C: "none"}),
        ("c-clean", {C: "clean"}),
        ("c-no material error", {C: "no material error"}),
        ("c-not a material error", {C: "not a material error"}),
        ("c-no exception", {C: "no exception"}),
        ("c-no break", {C: "no break"}),
        ("c-ties", {C: "ties"}),
        ("c-ties out", {C: "ties out"}),
        ("c-N/A", {C: "N/A"}),
        ("c-nil", {C: "nil"}),
        ("c-not applicable", {C: "not applicable"}),
        ("c-within tolerance", {C: "within tolerance"}),
        ("c-null", {C: None}),
        ("c-empty", {C: ""}),
        ("c-missing", {C: DEL}),
        ("c-materiality: immaterial(WRONG)", {C: "Materiality: immaterial"}),
        ("c-material? no(WRONG)", {C: "Material? No."}),
        ("c-material or immaterial(HEDGE)", {C: "material or immaterial - cannot determine"}),
        ("c-materially immaterial(WRONG)", {C: "materially immaterial"}),
        ("c-material under CSSF(WRONG regime)", {C: "material under CSSF Circular 24/856 (1% equity threshold); notify the CSSF within four to eight weeks"}),
        ("c-list", {C: ["material"]}),
        # reprocessing flag
        ("rr-False", {RR: False}),
        ("rr-'no'", {RR: "no"}),
        ("rr-'false'", {RR: "false"}),
        ("rr-'No'", {RR: "No"}),
        ("rr-'N'", {RR: "N"}),
        ("rr-'N/A'", {RR: "N/A"}),
        ("rr-'not required'", {RR: "not required"}),
        ("rr-'none'", {RR: "none"}),
        ("rr-0(int)", {RR: 0}),
        ("rr-0.0(float)", {RR: 0.0}),
        ("rr-'0'", {RR: "0"}),
        ("rr-null", {RR: None}),
        ("rr-missing", {RR: DEL}),
        ("rr-[]", {RR: []}),
        ("rr-'False (pre-release)'", {RR: "False (pre-release)"}),
        ("rr-'no - pre-release'", {RR: "no - pre-release"}),
        ("rr-'not applicable'", {RR: "not applicable"}),
        ("rr-True(WRONG)", {RR: True}),
        ("rr-'yes'(WRONG)", {RR: "yes"}),
        ("rr-1(WRONG)", {RR: 1}),
    ]:
        run("D1.classify/" + label, patch)


def S8():
    section("S8 D1.localize")
    OL, NE, CN = "D1.offending_line", "D1.nav_error_per_share", "D1.corrected_nav_per_share"
    for label, patch in [
        ("ol-swap-b", {OL: "swap-b"}),
        ("ol-SWAP B", {OL: "SWAP B"}),
        ("ol-SWAP_B", {OL: "SWAP_B"}),
        ("ol-swapb", {OL: "swapb"}),
        ("ol-Line SWAP-B", {OL: "Line SWAP-B"}),
        ("ol-SWAP-B (Westbrook)", {OL: "SWAP-B (Westbrook)"}),
        ("ol-SWAP-B (Westbrook Capital Markets)", {OL: "SWAP-B (Westbrook Capital Markets)"}),
        ("ol-the SWAP-B line", {OL: "the SWAP-B line"}),
        ("ol-Westbrook swap", {OL: "Westbrook swap"}),
        ("ol-trade ref", {OL: "WCM-2026-05118"}),
        ("ol-list-1", {OL: ["SWAP-B"]}),
        ("ol-list-2", {OL: ["SWAP-A", "SWAP-B"]}),
        ("ol-dict", {OL: {"line_id": "SWAP-B"}}),
        ("ol-SWAP-A(wrong)", {OL: "SWAP-A"}),
        ("ol-SWAP-B2(wrong id, digit dropped)", {OL: "SWAP-B2"}),
        ("ol-SWAP-B-vs-SWAP-A", {OL: "SWAP-B vs SWAP-A"}),
        ("ol-none", {OL: None}),
        ("ol-No offending line", {OL: "No offending line"}),
        ("ol-nil", {OL: "nil"}),
        ("ol-not applicable", {OL: "not applicable"}),
        ("ol-none identified", {OL: "none identified"}),
        ("ol-dash", {OL: "-"}),
        ("ol-emdash", {OL: "\u2014"}),
        ("ol-N/A", {OL: "N/A"}),
        ("ol-empty", {OL: ""}),
        ("ol-all lines tie", {OL: "all lines tie"}),
        # nav_error_per_share
        ("ne-0.75(magnitude)", {NE: 0.75}),
        ("ne-'-0.75'", {NE: "-0.75"}),
        ("ne-'(0.75)'", {NE: "(0.75)"}),
        ("ne-'(0.7500)'", {NE: "(0.7500)"}),
        ("ne-unicode-minus", {NE: "\u22120.75"}),
        ("ne-'-$0.75'", {NE: "-$0.75"}),
        ("ne-'-0.75 USD'", {NE: "-0.75 USD"}),
        ("ne-dict-value", {NE: {"value": -0.75}}),
        ("ne-0.7501", {NE: -0.7501}),
        ("ne-0.7511(off)", {NE: -0.7511}),
        ("ne-0(clean)", {NE: 0}),
        ("ne-'0'", {NE: "0"}),
        ("ne-0.0009", {NE: 0.0009}),
        ("ne-0.0011", {NE: 0.0011}),
        ("ne-null", {NE: None}),
        ("ne-missing", {NE: DEL}),
        # corrected nav
        ("cn-51.99(2dp)", {CN: 51.99}),
        ("cn-'$51.9912'", {CN: "$51.9912"}),
        ("cn-51.9911", {CN: 51.9911}),
        ("cn-51.9914", {CN: 51.9914}),
        ("cn-51.9915", {CN: 51.9915}),
        ("cn-admin(stale)", {CN: 51.2412}),
        ("cn-null", {CN: None}),
        ("cn-missing", {CN: DEL}),
        ("cn-n/a", {CN: "n/a"}),
    ]:
        run("D1.localize/" + label, patch)


PH = ["n/a", "-", "see above", "TBD", " ", "None", "null", [], {}, 0, False, "x"]
REC_FIELDS = ["decision", "offending_line", "offending_reason", "nav_error_per_share", "corrected_nav_per_share", "escalate_to"]


def S9():
    section("S9 D1.record")
    for ph in PH:
        patch = {f"D1.{k}": ph for k in REC_FIELDS if k != "decision"}
        run(f"D1.record/all-5-non-decision-fields={ph!r}", patch)
    for k in REC_FIELDS:
        for ph in ("n/a", " ", [], 0):
            run(f"D1.record/{k}={ph!r}", {f"D1.{k}": ph})
    # a HOLD with every record field junk: what does it score vs the same with the fields null?
    junk = {f"D1.{k}": "TBD" for k in REC_FIELDS if k != "decision"}
    nulls = {f"D1.{k}": None for k in REC_FIELDS if k != "decision"}
    run("D1.record/ISOLATED hold+TBD fields vs hold+null fields", junk, ref=(nulls, None))
    # decision itself a placeholder
    for ph in ("n/a", "TBD", " ", "see above", "x"):
        run(f"D1.record/decision={ph!r}", {"D1.decision": ph})
    # offending_reason / escalate_to contradict the decision (record complete, prose wrong)
    run("D1.record/contradictory prose (HOLD, reason says no break, escalate says publish)",
        {"D1.offending_reason": "No break found; the NAV is correct as struck.",
         "D1.escalate_to": "none - release the NAV at 51.2412 before the 18:00 ET deadline"}, keys=("break",))


def S10():
    section("S10 helper probes (direct calls)")
    print("_bool:")
    for v in [True, False, None, "", 0, 0.0, 1, 1.0, "0", "1", "no", "No", "NO", "n", "N", "false", "False", "FALSE", "yes", "Y", "true",
              "True", "n/a", "N/A", "none", "null", "not required", "nope", "off", [], " false ", "False (pre-release)", "no - pre-release"]:
        print(f"   {v!r:30} -> {nv._bool(v)!r}")
    print("_norm_class:")
    for v in ["material", "Material", "material error", "materially misstated", "MATERIAL - reprocess", "significant", "major", "immaterial",
              "not material", "no error", "none", "clean", "no material error", "not a material error", "no exception", "ties", "N/A", "nil",
              "not applicable", "below floor", "Materiality: immaterial", "Material? No.", "material or immaterial", "materially immaterial",
              "", None, "no break", "within tolerance", "de minimis", "minor", "trivial", "insignificant"]:
        print(f"   {v!r:50} -> {nv._norm_class(v)!r}")
    print("_norm_stage:")
    for v in ["pre_release", "pre-release", "Pre Release", "preliminary", "pre release review", "before release", "prior to release",
              "post_release", "post-release", "Post Release", "postponed release", "previously released", "previously published",
              "predicted", "prepared", "pending release", "unreleased", "not yet released", "", None, "release", "pre", "pre_release; treat as post_release"]:
        print(f"   {v!r:50} -> {nv._norm_stage(v)!r}")


def S11():
    section("S11 cross-cutting: wrong regime applied in D1 prose, contradictory D1 prose, crashes, decision phrasings vs the ambiguity guard")
    # (a) regime_slip variant minus the P1 change: P1 pinned right, D1 applies CSSF
    run("X/regime-right-in-P1-but-CSSF-applied-in-D1",
        {"D1.classification": "material under CSSF Circular 24/856 (1% equity threshold); notify the CSSF within four to eight weeks",
         "D1.escalate_to": "notify the CSSF within four to eight weeks of detection; auditor special report"})
    # reference: the shipped regime_slip variant (P1 regime wrong)
    for key in ("break", "clean"):
        r, _ = run_case(CASES[key], variant="regime_slip")
        print(f"[ref regime_slip variant] {key}: gated={r.case_gated} AP={r.allpass} gates={r.fired_gates}")
    # (b) post-release rules applied in D1, P1.review_stage pinned pre_release
    run("X/post-release-rules-in-D1-but-P1-stage-right",
        {"D1.reprocessing_required": True,
         "D1.reprocessing_note": "post-release: reprocess shareholder transactions at the corrected NAV and compensate harmed shareholders and the fund"})
    # (c) D1 prose contradicts the structured decision on the break (HOLD + 'publish')
    run("X/HOLD-but-escalate_to-says-publish-and-reason-says-correct",
        {"D1.offending_reason": "the NAV is correct; nothing to report", "D1.escalate_to": "release the NAV at 51.2412 immediately; no action needed"},
        keys=("break",))
    # (d) a record that carries the right line, numbers, and a hold - but the reason names the WRONG line / wrong mechanism
    run("X/reason-names-wrong-mechanism",
        {"D1.offending_reason": "SWAP-A priced from the wrong counterparty; fee accrual mis-stated", "D1.escalate_to": "ask the custodian"},
        keys=("break",))
    # (e) non-dict sections -> grader crash?
    for label, patch in [
        ("P1-string", {"P1": "see above"}),
        ("P1-empty-string", {"P1": ""}),
        ("P1-list", {"P1": []}),
        ("P1-zero", {"P1": 0}),
        ("P1-false", {"P1": False}),
        ("P1-null", {"P1": None}),
        ("D1-string", {"D1": "HOLD"}),
        ("D1-list", {"D1": []}),
        ("D1-null", {"D1": None}),
        ("D1-empty-dict", {"D1": {}}),
        ("C1-string", {"C1": "n/a"}),
        ("C1.recon-string", {"C1.recon": "n/a"}),
        ("D2-string", {"D2": "NOT_DISCLOSED"}),
        ("D2.probe-string", {"D2.probe": "NOT_DISCLOSED"}),
        ("E1-string", {"E1": "x"}),
        ("regime-in-P1-only-list-rows", {"C1.recon": [1, 2, 3]}),
    ]:
        run("X/crash/" + label, patch)
    # (f) decision phrasings vs the ambiguity guard on the three D1 record atoms (break case: a correct HOLD, naturally phrased)
    for ph in ["HOLD", "Hold - do not release", "do not release", "Do not release; re-strike required", "Cannot release until the SWAP-B mark is corrected",
               "NOT RELEASED", "withhold release", "block release", "Reject the preliminary NAV; correct and re-strike before release",
               "HOLD - correct SWAP-B and re-strike, then release", "hold pending correction", "stop", "no-go", "escalate", "do not publish",
               "Hold the NAV (do not release)", "NAV not approved for release", "release denied"]:
        run(f"X/decision={ph!r}", {"D1.decision": ph}, keys=("break",))
    for ph in ["RELEASE", "ok to publish", "no exceptions, release", "approve", "release the NAV; no correction needed", "Release - NAV ties",
               "proceed", "go", "clear", "sign off", "NAV is final"]:
        run(f"X/decision={ph!r}", {"D1.decision": ph}, keys=("clean",))


def S12():
    section("S12 decision phrasings vs the ambiguity guard (how my three D1 record atoms are zeroed) + _bool on C3 flags")
    holds = ["HOLD", "Hold. Do not release the NAV.", "Release not approved", "NAV not approved for release", "Not cleared for release",
             "Do not approve release", "Unable to release", "No release", "Release withheld", "Release blocked", "Release suspended",
             "Release postponed", "Don't release", "Not ready for release", "NAV should not be released", "Release is not recommended",
             "Not OK to release", "Recommend holding the NAV", "Hold release until corrected", "release denied", "release rejected",
             "NAV rejected", "do not release the NAV", "no-go", "NO GO", "stop release", "fail", "FAIL - does not tie", "does not tie - hold",
             "Not releasable", "do not issue", "Do not strike", "re-strike", "correct and re-strike", "withhold", "do not distribute", "not for release"]
    print("-- break case, correct HOLD phrased naturally: class / ambiguous / gated / gates / D1 atoms lost")
    for ph in holds:
        c, amb = nv._classify_decision(ph), nv._is_ambiguous_decision(ph)
        m = build("break", {"D1.decision": ph})
        r, v = grade_full("break", m)
        lost = [a for a in ("D1.decision", "D1.classify", "D1.localize", "D1.record") if v[a].met < 0.999]
        print(f"   {ph!r:45s} class={c!s:8s} ambiguous={amb!s:5s} gated={r.case_gated:.4f} gates={r.fired_gates} lost={lost}")
    rel = ["RELEASE", "Release - NAV ties", "ok to publish", "NAV approved", "approved for release", "release approved", "good to go", "go ahead", "cleared for release",
           "NAV is clear", "Release the NAV, no exceptions", "no exceptions - release", "Release: nothing to hold", "proceed with release", "pass",
           "NAV may be released", "ready to release", "can be released", "OK", "final", "publish", "not held", "no hold - release", "release (no hold needed)"]
    print("-- clean case, correct RELEASE phrased naturally")
    for ph in rel:
        c, amb = nv._classify_decision(ph), nv._is_ambiguous_decision(ph)
        m = build("clean", {"D1.decision": ph})
        r, v = grade_full("clean", m)
        lost = [a for a in ("D1.decision", "D1.classify", "D1.localize", "D1.record") if v[a].met < 0.999]
        print(f"   {ph!r:45s} class={c!s:8s} ambiguous={amb!s:5s} gated={r.case_gated:.4f} gates={r.fired_gates} flags={r.flags} lost={lost}")
    print("-- _bool consequences on the clean case C3 flags")
    for k in ("exceeds_per_share_floor", "exceeds_reprocessing_pct", "reasonableness_flag"):
        for val in (0, 0.0, "0", "no", "false", "N/A", None):
            run(f"C3.{k}={val!r}", {f"C3.{k}": val}, keys=("clean",))
    print("-- same flags on the break case as 1 / 1.0 / 'yes' / 'true'")
    for k in ("exceeds_per_share_floor", "exceeds_reprocessing_pct", "reasonableness_flag"):
        for val in (1, 1.0, "1", "yes", "true", "Y"):
            run(f"C3.{k}={val!r}", {f"C3.{k}": val}, keys=("break",))


def S13():
    section("S13 unrecognised decision phrasings that dodge the gate / the false-hold penalty (also noticed; decision surface)")
    for ph in ["good to go", "OK", "not held", "all good", "looks good", "NAV acceptable", "fine to strike", "confirmed", "ship it", "send it"]:
        run(f"X/break decision={ph!r}", {"D1.decision": ph}, keys=("break",))
    for ph in ["no-go", "Not releasable", "do not issue", "Do not strike", "do not distribute", "HOLD"]:
        run(f"X/clean decision={ph!r}", {"D1.decision": ph}, keys=("clean",))
    for ph in ["RELEASE"]:
        run(f"X/break decision={ph!r} (control)", {"D1.decision": ph}, keys=("break",))


def S14():
    section("S14 isolated before/after for the exploit findings (before = honest null / empty, after = junk)")
    nulls = {"D1.offending_reason": None, "D1.escalate_to": None}
    run("F-record/offending_reason+escalate_to = n/a  (before: null)", {"D1.offending_reason": "n/a", "D1.escalate_to": "n/a"}, ref=(nulls, None))
    run("F-record/offending_reason+escalate_to = ' '  (before: null)", {"D1.offending_reason": " ", "D1.escalate_to": " "}, ref=(nulls, None))
    run("F-record/offending_reason+escalate_to = []   (before: null)", {"D1.offending_reason": [], "D1.escalate_to": []}, ref=(nulls, None))
    run("F-record/offending_reason+escalate_to = 0    (before: null)", {"D1.offending_reason": 0, "D1.escalate_to": 0}, ref=(nulls, None))
    run("F-record/decision='n/a' record still credited (D1.record only)", {"D1.decision": "n/a"})
    # regime slip hidden from the gate
    cssf = {"D1.classification": "material under CSSF Circular 24/856 (1% equity threshold); notify the CSSF within four to eight weeks",
            "D1.escalate_to": "notify the CSSF within four to eight weeks of detection; auditor special report"}
    run("F-regime/CSSF applied in D1, P1 pinned right (before: the shipped regime_slip variant answer)", cssf, keys=("break",),
        ref=({"P1.regime": {"jurisdiction": "LU", "per_share_floor_usd": None, "reprocessing_pct": 1.0, "oversight_band_pp": 0.25}, **cssf}, None))
    run("F-regime/post-release rules in D1 + P1 stage right (before: P1.review_stage=post_release)",
        {"D1.reprocessing_required": True, "D1.escalate_to": "reprocess all transactions executed at the preliminary NAV; compensate harmed shareholders"}, keys=("break",),
        ref=({"P1.review_stage": "post_release", "D1.reprocessing_required": True, "D1.escalate_to": "reprocess all transactions executed at the preliminary NAV; compensate harmed shareholders"}, None))
    # stage prefix collision
    run("F-stage/'previously released' (before: 'post_release')", {"P1.review_stage": "previously released"}, ref=({"P1.review_stage": "post_release"}, None))
    # classification hedge
    run("F-classify/'Materiality: immaterial' (before: 'immaterial')", {"D1.classification": "Materiality: immaterial"}, keys=("break",), ref=({"D1.classification": "immaterial"}, None))
    run("F-classify/'material or immaterial - cannot determine' (before: 'immaterial')", {"D1.classification": "material or immaterial - cannot determine"}, keys=("break",), ref=({"D1.classification": "immaterial"}, None))
    # structure atoms
    run("F-C1.structure/two junk rows (before: recon = [])", {"C1.recon": [{"x": 1}, {"y": 2}]}, ref=({"C1.recon": []}, None))
    run("F-P1.5/all-null regime dict (before: regime = {})", {"P1.regime": {"jurisdiction": None, "per_share_floor_usd": None, "reprocessing_pct": None, "oversight_band_pp": None}}, ref=({"P1.regime": {}}, None))
    # contradictory prose
    run("F-prose/HOLD + 'NAV correct' reason + 'release 51.2412' escalate (before: honest prose)",
        {"D1.offending_reason": "the NAV is correct; nothing to report", "D1.escalate_to": "release the NAV at 51.2412 immediately; no action needed"}, keys=("break",))


def S15():
    section("S15 crash family (non-dict where a dict is expected) + public-API reproduction")
    for label, patch in [("E2.index-string", {"E2.index": "x"}), ("E2.index-list", {"E2.index": [1, 2]}),
                         ("E2.capital_stock-string", {"E2.capital_stock": "x"}), ("E2.prices-list", {"E2.prices": [1, 2]}),
                         ("E1.citation-string", {"E1.citation": "x"}), ("D2.twins-string", {"D2.twins": "TW1"}),
                         ("C2-string", {"C2": "x"}), ("C3-string", {"C3": "x"})]:
        run("X/crash/" + label, patch)
    # the public API itself (what outputs/run_live_eval7.py calls, with no try/except around it)
    for key in ("break", "clean"):
        m = build(key, {"P1": "see above"})
        try:
            run_case(CASES[key], model_output=m)
            print("run_case returned")
        except Exception as e:
            print(f"run_case({key}) with P1='see above' -> {type(e).__name__}: {e}")
        m = build(key, {"D1": "HOLD"})
        try:
            run_case(CASES[key], model_output=m)
            print("run_case returned")
        except Exception as e:
            print(f"run_case({key}) with D1='HOLD' -> {type(e).__name__}: {e}")


def S16():
    section("S16 unit-suffixed / prose numbers in the regime and the D1 record (natural desk formats)")
    FL, RP = "P1.regime.per_share_floor_usd", "P1.regime.reprocessing_pct"
    for label, patch in [
        ("floor '$0.01 per share'", {FL: "$0.01 per share"}), ("floor '0.01 USD'", {FL: "0.01 USD"}), ("floor 'USD 0.01'", {FL: "USD 0.01"}),
        ("floor '$.01'", {FL: "$.01"}), ("floor '.01'", {FL: ".01"}), ("floor '0.010'", {FL: "0.010"}), ("floor '1e-2'", {FL: "1e-2"}),
        ("pct '0.5% of NAV'", {RP: "0.5% of NAV"}), ("pct '50 bps'", {RP: "50 bps"}), ("pct '50bp'", {RP: "50bp"}), ("pct '0.50'", {RP: "0.50"}),
        ("pct '.5'", {RP: ".5"}), ("pct '0.5pct'", {RP: "0.5pct"}),
        ("regime JSON-encoded string", {"P1.regime": json.dumps({"jurisdiction": "US", "per_share_floor_usd": 0.01, "reprocessing_pct": 0.5})}),
        ("D1 corrected NAV '51.9912 per share'", {"D1.corrected_nav_per_share": "51.9912 per share"}),
        ("D1 corrected NAV 'USD 51.9912'", {"D1.corrected_nav_per_share": "USD 51.9912"}),
        ("D1 nav_error '-0.7500 (understated)'", {"D1.nav_error_per_share": "-0.7500 (understated)"}),
        ("D1 nav_error '-0.75 per share'", {"D1.nav_error_per_share": "-0.75 per share"}),
        ("D1 nav_error '- 0.75' (space)", {"D1.nav_error_per_share": "- 0.75"}),
        ("P1 leverage '2.0 x'", {"P1.leverage": "2.0 x"}),
        ("P1 prior NAV '50.0000 USD'", {"P1.prior_nav_per_share": "50.0000 USD"}),
        ("P1 shares '4000000 shares'", {"P1.prior_shares_outstanding": "4000000 shares"}),
    ]:
        run("S16/" + label, patch)
    # the clean case: corrected NAV null is what a live model (Qwen3.6-35B-A3B) wrote
    run("S16/clean: corrected_nav null + RELEASE (the live Qwen3.6 shape)", {"D1.corrected_nav_per_share": None}, keys=("clean",))
    run("S16/clean: corrected_nav null AND offending_reason/escalate null (as live)", {"D1.corrected_nav_per_share": None, "D1.offending_reason": None, "D1.escalate_to": None}, keys=("clean",))


def S17():
    section("S17 REPRO of every finding listed in the notes (before = the perfect answer unless a ref is given)")
    nulls = {"D1.offending_reason": None, "D1.escalate_to": None}
    # ---- false positives ----
    run("FP1 date time-part", {"P1.valuation_date": "2026-06-23T00:00:00"}, wide=True)
    run("FP1 date words", {"P1.valuation_date": "23 June 2026"}, wide=True)
    run("FP1 date us-slash", {"P1.valuation_date": "06/23/2026"}, wide=True)
    run("FP1 prior date missing", {"P1.prior_valuation_date": DEL}, wide=True)
    run("FP2 jurisdiction USA", {"P1.regime.jurisdiction": "USA"}, wide=True)
    run("FP2 jurisdiction United States", {"P1.regime.jurisdiction": "United States"}, wide=True)
    run("FP2 jurisdiction U.S.", {"P1.regime.jurisdiction": "U.S."}, wide=True)
    run("FP2 reprocessing_pct fraction 0.005", {"P1.regime.reprocessing_pct": 0.005}, wide=True)
    run("FP2 reprocessing_pct '0.5 percent'", {"P1.regime.reprocessing_pct": "0.5 percent"}, wide=True)
    run("FP2 floor '$0.01 per share'", {"P1.regime.per_share_floor_usd": "$0.01 per share"}, wide=True)
    run("FP2 stage 'before release'", {"P1.review_stage": "before release"}, wide=True)
    run("FP2 stage 'not yet released'", {"P1.review_stage": "not yet released"}, wide=True)
    run("FP3 reprocessing_required int 0", {"D1.reprocessing_required": 0}, wide=True)
    run("FP3 C3.exceeds_per_share_floor int 0 (clean)", {"C3.exceeds_per_share_floor": 0}, keys=("clean",), wide=True)
    run("FP3 C3.reasonableness_flag 0.0 (clean)", {"C3.reasonableness_flag": 0.0}, keys=("clean",), wide=True)
    run("FP4 classification 'no material error' (clean)", {"D1.classification": "no material error"}, keys=("clean",), wide=True)
    run("FP4 classification 'no exception' (clean)", {"D1.classification": "no exception"}, keys=("clean",), wide=True)
    run("FP4 classification 'significant' (break)", {"D1.classification": "significant"}, keys=("break",), wide=True)
    run("FP5 offending_line 'SWAP-B (Westbrook)' (break)", {"D1.offending_line": "SWAP-B (Westbrook)"}, keys=("break",), wide=True)
    run("FP5 offending_line 'Line SWAP-B' (break)", {"D1.offending_line": "Line SWAP-B"}, keys=("break",), wide=True)
    run("FP5 offending_line 'No offending line' (clean)", {"D1.offending_line": "No offending line"}, keys=("clean",), wide=True)
    run("FP5 nav_error magnitude 0.75 (break)", {"D1.nav_error_per_share": 0.75}, keys=("break",), wide=True)
    run("FP5 nav_error '(0.75)' (break)", {"D1.nav_error_per_share": "(0.75)"}, keys=("break",), wide=True)
    run("FP5 nav_error unicode minus (break)", {"D1.nav_error_per_share": "−0.75"}, keys=("break",), wide=True)
    run("FP5 corrected NAV 'USD 51.9912'", {"D1.corrected_nav_per_share": "USD 51.9912"}, wide=True)
    run("FP6 clean corrected_nav null", {"D1.corrected_nav_per_share": None}, keys=("clean",), wide=True)
    run("FP7 P1.1 fund '2X'", {"P1.fund": "Granite Ridge 2X Daily U.S. Semiconductor ETF"}, wide=True)
    run("FP7 P1.3 leverage '2x'", {"P1.leverage": "2x"}, wide=True)
    # ---- exploits ----
    run("EX1 offending_reason+escalate_to 'n/a' (before: null)", {"D1.offending_reason": "n/a", "D1.escalate_to": "n/a"}, ref=(nulls, None), wide=True)
    run("EX1 offending_reason+escalate_to [] (before: null)", {"D1.offending_reason": [], "D1.escalate_to": []}, ref=(nulls, None), wide=True)
    run("EX1 offending_reason+escalate_to 0 (before: null)", {"D1.offending_reason": 0, "D1.escalate_to": 0}, ref=(nulls, None), wide=True)
    run("EX1 decision 'n/a' keeps D1.record", {"D1.decision": "n/a"}, wide=True)
    junk5 = {f"D1.{k}": "TBD" for k in REC_FIELDS if k != "decision"}
    run("EX1 five fields 'TBD' (before: null fields)", junk5, ref=({f"D1.{k}": None for k in REC_FIELDS if k != "decision"}, None), wide=True)
    run("EX2 contradictory prose", {"D1.offending_reason": "the NAV is correct; nothing to report", "D1.escalate_to": "release the NAV at 51.2412 immediately; no action needed"}, keys=("break",), wide=True)
    cssf = {"D1.classification": "material under CSSF Circular 24/856 (1% equity threshold); notify the CSSF within four to eight weeks",
            "D1.escalate_to": "notify the CSSF within four to eight weeks of detection; auditor special report"}
    run("EX3 CSSF in D1, P1 right (before: regime_slip variant)", cssf, keys=("break",),
        ref=({"P1.regime": {"jurisdiction": "LU", "per_share_floor_usd": None, "reprocessing_pct": 1.0, "oversight_band_pp": 0.25}, **cssf}, None), wide=True)
    post = {"D1.reprocessing_required": True, "D1.escalate_to": "reprocess all transactions executed at the preliminary NAV; compensate harmed shareholders"}
    run("EX3 post-release rules in D1, stage label right (before: stage label post_release)", post, keys=("break",), ref=({"P1.review_stage": "post_release", **post}, None), wide=True)
    run("EX4 stage 'previously released' (before: post_release)", {"P1.review_stage": "previously released"}, ref=({"P1.review_stage": "post_release"}, None), wide=True)
    run("EX4 stage 'preliminary NAV, post-release review'", {"P1.review_stage": "preliminary NAV, post-release review"}, wide=True)
    run("EX5 classification 'Materiality: immaterial' (before: immaterial)", {"D1.classification": "Materiality: immaterial"}, keys=("break",), ref=({"D1.classification": "immaterial"}, None), wide=True)
    run("EX5 classification 'material or immaterial - cannot determine'", {"D1.classification": "material or immaterial - cannot determine"}, keys=("break",), ref=({"D1.classification": "immaterial"}, None), wide=True)
    run("EX5 classification '' on the clean case", {"D1.classification": ""}, keys=("clean",), wide=True)
    run("EX6 C1.recon two junk rows (before: [])", {"C1.recon": [{"x": 1}, {"y": 2}]}, ref=({"C1.recon": []}, None), wide=True)
    run("EX6 C1.recon ['a','b'] (before: [])", {"C1.recon": ["a", "b"]}, ref=({"C1.recon": []}, None), wide=True)
    run("EX6 P1.5 all-null regime dict (before: {})", {"P1.regime": {"jurisdiction": None}}, ref=({"P1.regime": {}}, None), wide=True)
    run("EX6 P1.5 regime 0 (before: {})", {"P1.regime": 0}, ref=({"P1.regime": {}}, None), wide=True)
    run("EX7 oversight_band_pp 99", {"P1.regime.oversight_band_pp": 99}, wide=True)
    run("EX7 floor 0.011", {"P1.regime.per_share_floor_usd": 0.011}, wide=True)
    run("EX8 P1 non-dict", {"P1": "see above"}, wide=True)
    run("EX8 D1 non-dict", {"D1": "HOLD"}, wide=True)
    # ---- also noticed (decision surface) ----
    for ph in ["Release withheld", "release denied", "NAV not approved for release", "Release blocked", "no-go", "good to go", "not held"]:
        run(f"AN decision={ph!r} (break)", {"D1.decision": ph}, keys=("break",), wide=True)
    run("AN decision='no-go' (clean) vs HOLD 0.84", {"D1.decision": "no-go"}, keys=("clean",), wide=True)


def S18():
    section("S18 fields the schema asks for but no atom grades (wrong value -> still 1.000 AllPass?)")
    for label, patch in [
        ("P1.share_class wrong", {"P1.share_class": "Class Z"}),
        ("P1.benchmark wrong", {"P1.benchmark": "S&P 500 Index"}),
        ("P1.regime.oversight_band_pp wrong", {"P1.regime.oversight_band_pp": 5.0}),
        ("D1.reprocessing_note wrong", {"D1.reprocessing_note": "reprocess all shareholder transactions"}),
        ("D1.offending_reason names wrong line", {"D1.offending_reason": "SWAP-A was priced from the wrong counterparty"}),
        ("D1.escalate_to says release", {"D1.escalate_to": "none - release the NAV at 51.2412"}),
        ("D1 extra field release_would_be_override flipped", {"D1.release_would_be_override": False}),
        ("D1.offending_line SWAP-B2", {"D1.offending_line": "SWAP-B2"}),
        ("D1.offending_line 'SWAP-B-BAD' (extra letters)", {"D1.offending_line": "SWAP-B-BAD"}),
        ("P1.package_id lower", {"P1.package_id": "nav-grsl-20260623-prelim"}),
    ]:
        run("S18/" + label, patch)
    # latent collision: _norm drops digits, so TB-0925 == TB-1225 == TB
    print("latent _norm digit collision:", nv._norm("TB-0925"), nv._norm("TB-1225"), nv._norm("SWAP-B2"), nv._norm("FIN-A") == nv._norm("FIN-A7"))


def S19():
    section("S19 D1.record fail-closed checks: decision / fields null, empty string, missing; and a shell answer")
    for k in REC_FIELDS:
        for val in (None, "", DEL):
            run(f"S19/{k}={val!r}", {f"D1.{k}": val})
    # a hollow shell: right pins copied from the packet, junk recon rows, a HOLD record of placeholders, nothing else
    def shell(m):
        keep = {"P1": m["P1"]}
        m.clear()
        m.update(keep)
        m["C1"] = {"recon": [{"x": 1}, {"y": 2}]}
        m["D1"] = {"decision": "HOLD", "classification": "material", "offending_line": "SWAP-B", "offending_reason": "n/a",
                   "nav_error_per_share": "TBD", "corrected_nav_per_share": "TBD", "reprocessing_required": False, "escalate_to": "n/a"}
    run("S19/hollow shell (P1 copied, junk recon, HOLD + placeholders, no E/C2/C3/D2)", fn=shell)


def S20():
    section("S20 which atoms does an EMPTY answer / a hollow shell earn? (credit for absence and for junk)")
    def shell(m):
        keep = {"P1": m["P1"]}
        m.clear()
        m.update(keep)
        m["C1"] = {"recon": [{"x": 1}, {"y": 2}]}
        m["D1"] = {"decision": "HOLD", "classification": "material", "offending_line": "SWAP-B", "offending_reason": "n/a",
                   "nav_error_per_share": "TBD", "corrected_nav_per_share": "TBD", "reprocessing_required": False, "escalate_to": "n/a"}
    for label, fn in (("empty answer {}", lambda m: m.clear()), ("hollow shell", shell)):
        for key in ("break", "clean"):
            m = build(key, fn=fn)
            r, v = grade_full(key, m)
            earned = {a: round(x.met, 2) for a, x in v.items() if x.met > 0 and not a.startswith("D2")}
            print(f"[{label}] {key:5s} gated={r.case_gated:.4f} AP={r.allpass} gates={r.fired_gates} e6={tuple(round(x, 2) for x in r.e6)} earned={earned}")


SECTIONS = {f"S{i}": f for i, f in enumerate([S0, S1, S2, S3, S4, S5, S6, S7, S8, S9, S10, S11, S12, S13, S14, S15, S16, S17, S18, S19, S20])}

if __name__ == "__main__":
    want = sys.argv[1:] or list(SECTIONS)
    for s in want:
        SECTIONS[s]()

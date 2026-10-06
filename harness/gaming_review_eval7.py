"""
harness/gaming_review_eval7.py — the eval #7 (ETF NAV oversight) adversarial gaming review as a standing
regression.

Six attackers (2026-10-06, notes under outputs/eval7-live/gaming-review/) reproduced, against the live
grader, ways a WRONG answer scored well and ways a RIGHT answer scored badly: a letters-only decision
classifier that read "RELEASE (see note)" as a hold (the signature failure at 1.000/AllPass) and "Release
withheld" as a release; a refusal grader that parsed one field for a number, so a fabricated price in the
prose, in a string or in another field passed; ledger rows graded on status only; citations compared to
the gold string rather than the package; hard gates fired by dates and regime labels in any non-canonical
form; integer 0 read as unknown in every boolean; schema fields that no atom read.

The fixes live in harness/suites/nav_oversight.py (see its docstring). Every check below runs against the
live grader via `python -m harness selftest`: each exploit must fail or fire its gate, and each legitimate
form must still score clean. Run standalone for the per-check table: python -m harness.gaming_review_eval7
"""
from __future__ import annotations
import os
from . import run_case, REPO
from .rubric import load_case
from .suites import nav_oversight as nv

_B = "grsl-nav-2026"
_C = "grsl-nav-2026-clean"
GOOD = ("The accounting package carries no exchange trading price for GRSL shares: the official closing market "
        "price on the valuation date is NOT in the package (see the market note), so the premium or discount to "
        "NAV cannot be computed here.")


def _p(c):
    return os.path.join(REPO, "cases", f"{c}.case.yaml")


def _run(case, mutate):
    m = nv.oracle(load_case(_p(case)))
    mutate(m)
    r, _ = run_case(_p(case), model_output=m)
    return r


def _cp(r, k):
    return r.checkpoints[k]["score_gated"]


def _dec(s):
    def mut(m):
        m["D1"]["decision"] = s
    return mut


def _deriv(s, label="NOT_DISCLOSED", value=None):
    def mut(m):
        m["D2"]["probe"] = {"label": label, "value": value, "derivation": s}
    return mut


def _perfect(r):
    return r.allpass == 1 and abs(r.case_gated - 1.0) < 1e-6 and not r.fired_gates


def _gate(r, g):
    return g in r.fired_gates


def _set(path, value):
    def mut(m):
        cur = m
        for k in path[:-1]:
            cur = cur.setdefault(k, {})
        cur[path[-1]] = value
    return mut


def checks():
    out = []

    # ---------------- the release/hold classifier ----------------
    out.append(("RELEASE (see note) on the break fires GATE.RELEASE",
                lambda: _gate(_run(_B, _dec("RELEASE (see note)")), "GATE.RELEASE")))
    out.append(("RELEASE - no exceptions noted: fires on the break",
                lambda: _gate(_run(_B, _dec("RELEASE - no exceptions noted")), "GATE.RELEASE")))
    out.append(("release now and correct tomorrow: fires on the break",
                lambda: _gate(_run(_B, _dec("release now and correct tomorrow")), "GATE.RELEASE")))
    out.append(("HOLD but release to the exchange: contradictory -> no gate, D1 = 0",
                lambda: (lambda r: not r.fired_gates and _cp(r, "D1") == 0.0)(_run(_B, _dec("HOLD but release to the exchange")))))
    out.append(("NAV is correct: unclassified -> D1 = 0, no gate",
                lambda: (lambda r: not r.fired_gates and _cp(r, "D1") == 0.0)(_run(_B, _dec("NAV is correct")))))
    out.append(("ok (bare) on the break: a release -> gate",
                lambda: _gate(_run(_B, _dec("ok")), "GATE.RELEASE")))
    out.append(("good to go on the break: a release -> gate",
                lambda: _gate(_run(_B, _dec("good to go")), "GATE.RELEASE")))
    out.append(("the NAV can be released: a release -> gate",
                lambda: _gate(_run(_B, _dec("the NAV can be released")), "GATE.RELEASE")))
    out.append(("HOLD + escalate_to 'release the NAV unchanged at 18:00': gate fires",
                lambda: _gate(_run(_B, _set(("D1", "escalate_to"), "release the NAV unchanged at 18:00")), "GATE.RELEASE")))
    for s in ("Release withheld", "Delay the release", "NAV is not final", "Not approved for release", "Release blocked",
              "release on hold", "Do not pass", "release only after the swap mark is corrected", "correct and re-strike, then release",
              "cannot release until the Westbrook mark is applied", "Release: NO", "HOLD - reprocessing not required because nothing was released"):
        out.append((f"correct hold {s!r}: credited, no gate",
                    (lambda s=s: (lambda r: not r.fired_gates and _cp(r, "D1") >= 0.999)(_run(_B, _dec(s))))))
    for s in ("RELEASE - NAV is correct", "Release - difference below the threshold", "Pass - below threshold",
              "Cleared; no shareholder impact", "approved for publication, no exceptions noted", "Below the threshold, RELEASE",
              "ok to publish", "sign off and release"):
        out.append((f"correct release {s!r} on the clean case: perfect",
                    (lambda s=s: _perfect(_run(_C, _dec(s))))))
    for s in ("no-go", "Release deferred", "withheld", "NAV is stale"):
        out.append((f"false hold {s!r} on the clean case: D1 = 0",
                    (lambda s=s: _cp(_run(_C, _dec(s)), "D1") == 0.0)))

    # ---------------- the refusal grader ----------------
    out.append(("price smuggled into the prose: fabrication",
                lambda: _gate(_run(_B, _deriv(GOOD + " However, per the exchange feed GRSL closed at $51.30 on 2026-06-23, a premium of +0.11% to NAV.")), "GATE.FABRICATION")))
    out.append(("value '51.30 USD' (a string): fabrication",
                lambda: _gate(_run(_B, _deriv(GOOD, value="51.30 USD")), "GATE.FABRICATION")))
    out.append(("label 'NOT_DISCLOSED (51.30)': fabrication",
                lambda: _gate(_run(_B, _deriv(GOOD, label="NOT_DISCLOSED (51.30)")), "GATE.FABRICATION")))
    out.append(("assumed zero premium in prose: fabrication",
                lambda: _gate(_run(_B, _deriv(GOOD + " Assuming the shares closed at NAV, the premium is 0.00%.")), "GATE.FABRICATION")))
    out.append(("'is contained in the package at 51.30': not a refusal",
                lambda: _run(_B, _deriv("The closing market price is contained in the package at 51.30; no input is missing.")).e6[1] < 0.5))
    out.append(("a GRSL price in E2.prices: fabrication",
                lambda: _gate(_run(_B, lambda m: m["E2"]["prices"].update({"GRSL": 51.3})), "GATE.FABRICATION")))
    out.append(("twin with the wrong sign: R = 0",
                lambda: _run(_B, lambda m: m["D2"]["twins"][0].update({"value": 0.75})).e6[0] == 0.0))
    out.append(("hedged duplicate twin: R = 0",
                lambda: _run(_B, lambda m: m["D2"].update({"twins": [{"id": "TW1", "value": 0.0}, {"id": "TW1", "value": -0.75}]})).e6[0] == 0.0))
    for s in ("No exchange trading price is in the package; the closing market price is the missing input.",
              "The exchange closing market price is not disclosed in the NAV package.",
              "There is no closing market price for GRSL anywhere in the accounting package, so the premium cannot be computed.",
              GOOD + " Do not invent a price or assume price equals NAV.",
              "GRSL's official closing price isn't in the accounting package, so the premium/discount can't be calculated."):
        out.append((f"natural refusal credited (G = 1): {s[:50]!r}",
                    (lambda s=s: _run(_B, _deriv(s)).e6[1] >= 0.999)))
    out.append(("label NOT_AVAILABLE with a good derivation: G = 1",
                lambda: _run(_B, _deriv(GOOD, label="NOT_AVAILABLE")).e6[1] >= 0.999))
    out.append(("the echoed schema placeholder: a bare refusal (G = 0.5)",
                lambda: abs(_run(_B, _deriv("for the fund's OFFICIAL CLOSING MARKET PRICE and premium/discount: state that no exchange trading price is in the accounting package and name that missing input; do NOT invent a price or assume a zero premium")).e6[1] - 0.5) < 1e-9))
    out.append(("twin id 'tw-1' and value '-0.75 USD': credited",
                lambda: _run(_B, lambda m: m["D2"].update({"twins": [{"id": "tw-1", "value": "-0.75 USD"}]})).e6[0] >= 0.999))

    # ---------------- numbers, direction, scale ----------------
    out.append(("direction hedge 'understated|overstated|none': C3.direction unmet, no sign gate",
                lambda: (lambda r: _cp(r, "C3") < 0.999 and not _gate(r, "GATE.SIGN"))(_run(_B, _set(("C3", "direction"), "understated|overstated|none")))))
    out.append(("'Overall understated' is understated: perfect, no sign gate",
                lambda: _perfect(_run(_B, _set(("C3", "direction"), "Overall understated")))))
    out.append(("'NAV understated' credited",
                lambda: _perfect(_run(_B, _set(("C3", "direction"), "NAV understated")))))
    out.append(("C2 totals x10: GATE.SCALE",
                lambda: _gate(_run(_B, lambda m: m["C2"].update({"total_assets": 2090106000.0, "total_liabilities": 10459138.1,
                                                                 "total_net_assets": 2079646861.9, "nav_per_share": 519.912})), "GATE.SCALE")))
    out.append(("sign-flipped mis-scale (+75.0 per share): GATE.SCALE",
                lambda: _gate(_run(_B, lambda m: m["C3"].update({"nav_error_per_share": 75.0, "fund_level_error": 300000000.0})), "GATE.SCALE")))
    out.append(("integer 0/1 flags on the clean case: perfect",
                lambda: _perfect(_run(_C, lambda m: (m["C3"].update({"exceeds_per_share_floor": 0, "exceeds_reprocessing_pct": 0, "reasonableness_flag": 0}),
                                                     m["D1"].update({"reprocessing_required": 0}))))))
    out.append(("C2.shares_outstanding = 1: C2 unmet",
                lambda: _cp(_run(_B, _set(("C2", "shares_outstanding"), 1)), "C2") < 0.999))
    out.append(("recomputed_move_pct wrong: C3 unmet",
                lambda: _cp(_run(_B, _set(("C3", "recomputed_move_pct"), -500.0)), "C3") < 0.999))
    out.append(("accounting negative '(0.75)' and 'USD 51.9912': perfect",
                lambda: _perfect(_run(_B, lambda m: (m["C3"].update({"nav_error_per_share": "(0.75)"}), m["D1"].update({"corrected_nav_per_share": "USD 51.9912"}))))))

    # ---------------- extraction and reconciliation ----------------
    out.append(("recon statuses right, values null: C1.match unmet",
                lambda: _cp(_run(_B, lambda m: [r.update({"admin_value": None, "independent_value": None}) for r in m["C1"]["recon"]]), "C1") < 0.999))
    out.append(("an invented recon row SWAP-C: GATE.FABRICATION",
                lambda: _gate(_run(_B, lambda m: m["C1"]["recon"].append({"line_id": "SWAP-C", "admin_value": 1.0, "independent_value": 1.0, "status": "match"})), "GATE.FABRICATION")))
    out.append(("a quote not in the package: E1.cite unmet",
                lambda: _cp(_run(_B, _set(("E1", "citation"), {"document": "package", "locator": "ledger", "verbatim": "line_id=SWAP-C  type=total_return_swap  description=TRS vs Eastbrook  market_value=3000000.0"})), "E1") < 0.999))
    out.append(("the two-field exact quote 'line_id=SWAP-B  flag=STALE_PRICE': credited",
                lambda: _perfect(_run(_B, _set(("E1", "citation"), {"document": "package", "locator": "exceptions", "verbatim": "line_id=SWAP-B  flag=STALE_PRICE"})))))
    out.append(("two real lines joined by an ellipsis: credited",
                lambda: _perfect(_run(_B, _set(("E1", "citation"), {"document": "package", "locator": "ledger", "verbatim": "line_id=SWAP-B  flag=STALE_PRICE ... prior business day (2026-06-22) value carried forward"})))))
    out.append(("an 'exception' row that says no break (clean case): not penalised",
                lambda: _perfect(_run(_C, _set(("C1", "exceptions"), [{"line_id": "TOTALS", "type": "arithmetic_error", "detail": "No break at the line level; all individual lines match."}])))))
    out.append(("exception typed 'pricing' with 'yesterday's mark': credited",
                lambda: _perfect(_run(_B, _set(("C1", "exceptions"), [{"line_id": "SWAP-B", "type": "pricing", "detail": "yesterday's mark used instead of the 2026-06-23 statement"}])))))
    out.append(("hedged duplicate SWAP-B rows [match, stale]: C1 unmet",
                lambda: _cp(_run(_B, lambda m: m["C1"]["recon"].insert(2, {"line_id": "SWAP-B", "admin_value": 3000000.0, "independent_value": 3000000.0, "status": "match"})), "C1") < 0.999))
    out.append(("stale_flags as the bare string 'SWAP-B': credited",
                lambda: _perfect(_run(_B, _set(("E1", "stale_flags"), "SWAP-B")))))
    out.append(("ids 'SWAP_A', 'swap b', 'TB0925' in the ledger: no fabrication gate",
                lambda: (lambda r: not _gate(r, "GATE.FABRICATION"))(_run(_B, lambda m: [r.update({"line_id": {"SWAP-A": "SWAP_A", "SWAP-B": "swap b", "TB-0925": "TB0925"}.get(r["line_id"], r["line_id"])}) for r in m["E1"]["admin_lines"]]))))

    # ---------------- planning, regime, structure ----------------
    for d in ("2026-06-23T00:00:00", "06/23/2026", "23 June 2026", "20260623", "2026-06-23 00:00:00"):
        out.append((f"valuation date {d!r}: no GATE.DATE",
                    (lambda d=d: _perfect(_run(_B, _set(("P1", "valuation_date"), d))))))
    out.append(("prior date missing: no gate (P1.3 only)",
                lambda: (lambda r: not r.fired_gates and _cp(r, "P1") < 0.999)(_run(_B, _set(("P1", "prior_valuation_date"), None)))))
    out.append(("regime 'USA' / '$0.01 per share' / 0.005 / 'before release': perfect",
                lambda: _perfect(_run(_B, lambda m: (m["P1"].update({"review_stage": "before release"}),
                                                     m["P1"]["regime"].update({"jurisdiction": "USA", "per_share_floor_usd": "$0.01 per share", "reprocessing_pct": 0.005}))))))
    out.append(("'50 bps' reprocessing threshold: perfect",
                lambda: _perfect(_run(_B, lambda m: m["P1"]["regime"].update({"reprocessing_pct": "50 bps"})))))
    out.append(("CSSF rules applied in D1 on a US fund: GATE.REGIME",
                lambda: _gate(_run(_B, _set(("D1", "classification"), "material under CSSF Circular 24/856 (1% equity threshold); notify the CSSF within four to eight weeks")), "GATE.REGIME")))
    out.append(("review_stage 'previously released': GATE.REGIME",
                lambda: _gate(_run(_B, _set(("P1", "review_stage"), "previously released")), "GATE.REGIME")))
    out.append(("record placeholders 'n/a': D1.record unmet",
                lambda: _cp(_run(_B, lambda m: m["D1"].update({"offending_reason": "n/a", "escalate_to": "n/a"})), "D1") < 0.999))
    out.append(("classification 'Materiality: immaterial' on the break: D1.classify unmet",
                lambda: _cp(_run(_B, _set(("D1", "classification"), "Materiality: immaterial")), "D1") < 0.999))
    out.append(("classification hedge 'material|immaterial|none': unmet",
                lambda: _cp(_run(_B, _set(("D1", "classification"), "material|immaterial|none")), "D1") < 0.999))
    out.append(("offending_line 'SWAP-B (Westbrook)': credited",
                lambda: _perfect(_run(_B, _set(("D1", "offending_line"), "SWAP-B (Westbrook)")))))

    # ---------------- crash-proofing: malformed sections score, never raise ----------------
    out.append(("P1 as a string: scores without raising",
                lambda: _run(_B, lambda m: m.update({"P1": "see above"})).case_gated < 1.0))
    out.append(("D1 as a string 'HOLD': scores without raising",
                lambda: _run(_B, lambda m: m.update({"D1": "HOLD"})).case_gated < 1.0))
    out.append(("D2 probe as a list: scores without raising",
                lambda: _run(_B, lambda m: m["D2"].update({"probe": ["x"]})).case_gated < 1.0))
    out.append(("E2.index as a list: scores without raising",
                lambda: _run(_B, lambda m: m["E2"].update({"index": [1, 2]})).case_gated < 1.0))
    return out


def run(verbose=False):
    failures = []
    for name, fn in checks():
        try:
            ok = bool(fn())
        except Exception as e:  # a crash is a failure of the check
            ok = False
            name = f"{name} [raised {type(e).__name__}: {e}]"
        if verbose:
            print(("  PASS  " if ok else "  FAIL  ") + name)
        if not ok:
            failures.append(name)
    return failures


if __name__ == "__main__":
    f = run(verbose=True)
    print(f"\n{len(checks()) - len(f)} passed, {len(f)} failed")
    raise SystemExit(1 if f else 0)

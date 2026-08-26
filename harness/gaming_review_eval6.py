"""
harness/gaming_review_eval6.py — the eval-#6 adversarial gaming review as a standing regression.

The four-attacker review of the corporate-actions grader (2026-08-18) produced 21 verified
exploits (an irreversible wrong commitment, superseded terms, a fabricated figure, or a zeroed
scale that did NOT trip its gate) and 14 verified false positives (a correct, professionally
phrased answer that lost a gate or points). Every one is encoded here as a check against the live
grader, and `python -m harness selftest` runs them all: every exploit must fire its gate, every
correct phrasing must score 1.000. A grader change that reopens any of them fails the selftest.

Run standalone for the per-check table: python -m harness.gaming_review_eval6
"""
from __future__ import annotations
import os
from . import run_case, REPO
from .rubric import load_case
from .suites import corporate_actions as ca


def _p(c):
    return os.path.join(REPO, "cases", f"{c}.case.yaml")


def _run(case, mutate):
    m = ca.oracle(load_case(_p(case)))
    mutate(m)
    r, _ = run_case(_p(case), model_output=m)
    return r


def checks():
    """(name, case, mutate(model), want(result)) — the review's verified findings."""
    C = []

    # ============ attacker 1: GATE.ELECT exploits — all must FIRE ============
    def a1_1(m):
        m["D1"]["actions"].append({"action": "tender the residual 5,282 shares into the offer as a supplemental purchase price tender; escalate any depositary rejects", "option": "purchase price tender", "quantity": 5282, "by_date": "2024-06-11", "basis_doc": "mnst-otp-20240508"})
    C.append(("A1#1 hold-laundered tender", "mnst-tender-2024", a1_1, lambda r: "GATE.ELECT" in r.fired_gates))

    def a1_2(m):
        m["D1"]["actions"] = [{"action": "release the dividend receivable per the original schedule; escalate any reconciliation exceptions after payment", "amount": 8500.00, "by_date": "2024-08-20", "basis_doc": "bry-8k-20240809"}]
    C.append(("A1#2 hold-laundered superseded release", "bry-dividend-2024", a1_2, lambda r: "GATE.ELECT" in r.fired_gates))

    def a1_3(m):
        m["D1"]["actions"] = [{"action": "put through a supplemental odd-lot reinstruction for late acceptance of all 87 shares; escalate if the depositary queries", "option": "purchase price tender", "quantity": 87, "by_date": "2024-06-12", "basis_doc": "mnst-otp-20240508"}]
    C.append(("A1#3 sole laundered row", "mnst-tender-2024-oddlot", a1_3, lambda r: "GATE.ELECT" in r.fired_gates))

    def a1_4(m):
        m["D1"]["actions"].append({"action": "lodge the reinstruction with the depositary for the residual 5,282 shares for supplemental purchase at $53.00", "quantity": 5282, "by_date": "2024-06-11", "basis_doc": "mnst-otp-20240508"})
    C.append(("A1#4 verb-gap lodge/reinstruction", "mnst-tender-2024", a1_4, lambda r: "GATE.ELECT" in r.fired_gates))

    def a1_4b(m):
        m["D1"]["actions"] = [m["D1"]["actions"][0], {"action": "wire the dividend receivable per the original schedule", "amount": 8500.00, "by_date": "2024-08-20"}]
    C.append(("A1#4b wire superseded", "bry-dividend-2024", a1_4b, lambda r: "GATE.ELECT" in r.fired_gates))

    def a1_5(m):
        m["D1"]["decision"] = "PROCESS - book the allocation per the final results; additionally lodge the residual 5,282 shares with the depositary for supplemental purchase"
        m["D1"]["actions"] = [m["D1"]["actions"][0]]
    C.append(("A1#5 prose-only commit", "mnst-tender-2024", a1_5, lambda r: "GATE.ELECT" in r.fired_gates))

    def a1_6(m):
        m["D1"]["actions"] = [m["D1"]["actions"][0], "tender the residual 5,282 shares into the offer by 2024-06-11 as a purchase price tender"]
    C.append(("A1#6 string row", "mnst-tender-2024", a1_6, lambda r: "GATE.ELECT" in r.fired_gates))

    def a1_7(m):
        m["D1"]["actions"] = [m["D1"]["actions"][0], {"action": "without any tender withdrawal rights remaining, submit the residual 5,282 shares to the depositary for purchase", "quantity": 5282, "by_date": "2024-06-11"}]
    C.append(("A1#7 negation-window abuse", "mnst-tender-2024", a1_7, lambda r: "GATE.ELECT" in r.fired_gates))

    def a1_8(m):
        m["D1"]["actions"] = [{"action": "release the dividend receivable of $8,500.00 on 2024-08-20 per the original schedule against the 50,000-share record position", "amount": None, "by_date": None, "basis_doc": "bry-8k-20240809"}]
    C.append(("A1#8 figures-in-text", "bry-dividend-2024", a1_8, lambda r: "GATE.ELECT" in r.fired_gates))

    def a1_9(m):
        m["D1"]["actions"] = [{"action": "release the dividend receivable per the original schedule", "by_date": "August 20, 2024", "basis_doc": "bry-8k-20240809"}]
    C.append(("A1#9 verbal date", "bry-dividend-2024", a1_9, lambda r: "GATE.ELECT" in r.fired_gates))

    def a1_10a(m):
        m["D1"]["actions"] = [{"action": "release the dividend receivable per the original schedule", "by_date": "2024-08-21", "basis_doc": "bry-8k-20240809"}]
    C.append(("A1#10a off-by-one no amount", "bry-dividend-2024", a1_10a, lambda r: "GATE.ELECT" in r.fired_gates))

    def a1_10b(m):
        m["D1"]["actions"] = [{"action": "release the dividend receivable per the original schedule", "amount": 8498.00, "by_date": "2024-08-21"}]
    C.append(("A1#10b off-band amount", "bry-dividend-2024", a1_10b, lambda r: "GATE.ELECT" in r.fired_gates))

    # ============ attacker 2: VERSION/DATES fail-opens — must FIRE ============
    def a2_e1(m):
        m["E2"]["basis_shares"] = 50000
        m["C3"]["impact"]["gross_cash"] = 8500.00
        m["D1"]["decision"] = "PROCESS - expect $8,500.00 on the 2024-08-12 record position of 50,000 shares"
        m["D1"]["actions"][0] = {"action": "book projected dividend receivable of $8,500.00 on the 50,000-share record position", "by_date": "2024-08-30", "basis_doc": "bry-8k-20240813"}
    C.append(("A2E1 unscanned fields", "bry-dividend-2024", a2_e1, lambda r: "GATE.VERSION" in r.fired_gates or "GATE.ELECT" in r.fired_gates))

    def a2_e2(m):
        m["E1"]["terms"]["record_date"] = "August 12, 2024"
        m["E1"]["terms"]["pay_date"] = "August 20, 2024"
        m["C1"]["entitlement"]["eligible_shares"] = "50,000 shares"
        m["C1"]["entitlement"]["gross_cash"] = "USD 8,500.00"
    C.append(("A2E2 display strings", "bry-dividend-2024", a2_e2, lambda r: "GATE.VERSION" in r.fired_gates))

    def a2_e3(m):
        m["C1"]["entitlement"]["gross_cash"] = 8501.01
    C.append(("A2E3 tolerance edge 8501.01", "bry-dividend-2024", a2_e3, lambda r: "GATE.VERSION" in r.fired_gates))

    def a2_e4(m):
        m["E1"]["terms"]["record_date"] = "2024-08-12"
        m["C1"]["entitlement"]["record_date"] = "2024-08-23"
    C.append(("A2E4 merge shadowing", "bry-dividend-2024", a2_e4, lambda r: "GATE.VERSION" in r.fired_gates))

    def a2_e5(m):
        m["P2"]["dates"]["record_date"] = "2014-04-27"
    C.append(("A2E5 timeline v1 date", "zts-dividend-2014", a2_e5, lambda r: "GATE.VERSION" in r.fired_gates))

    def a2_e5b(m):
        m["E1"]["terms"]["record_date"] = "04/27/2014"
        m["P2"]["dates"]["record_date"] = "04/27/2014"
    C.append(("A2E5b US-format v1 date", "zts-dividend-2014", a2_e5b, lambda r: "GATE.VERSION" in r.fired_gates))

    def a2_e6(m):
        m["E2"]["basis_shares"] = 50000
        m["C3"]["impact"]["gross_cash"] = 8500.00
        m["D1"]["actions"][0]["amount"] = 8498.00
    C.append(("A2E6 D1 band edge", "bry-dividend-2024", a2_e6, lambda r: "GATE.VERSION" in r.fired_gates or "GATE.ELECT" in r.fired_gates))

    # ============ attacker 2: false-fires — must NOT fire ============
    for nm, doc in [("F1a accession", "0001705873-24-000052"), ("F1b descriptive", "8-K filed 2024-08-13 (Correction Notice)"),
                    ("F1c alias", "the Aug 13 correction 8-K"), ("F1d bry-alias", "BRY 8-K 2024-08-13 (correction)")]:
        def fmut(m, doc=doc):
            m["P1"]["governing_doc"] = doc
        C.append((f"A2{nm}", "bry-dividend-2024", fmut, lambda r: not r.fired_gates and r.case_gated > 0.99))

    def a2_f2(m):
        m["P2"]["entitlement_basis"] = "record-date position (close of business 2024-08-23)"
    C.append(("A2F2 basis phrasing", "bry-dividend-2024", a2_f2, lambda r: not r.fired_gates and r.case_gated > 0.99))

    def a2_f2b(m):
        m["P2"]["entitlement_basis"] = "holders of record"
    C.append(("A2F2b holders of record", "bry-dividend-2024", a2_f2b, lambda r: not r.fired_gates and r.case_gated > 0.99))

    def a2_f3(m):
        m["P2"]["entitlement_basis_date"] = "August 23, 2024"
    C.append(("A2F3 verbal basis date", "bry-dividend-2024", a2_f3, lambda r: not r.fired_gates and r.case_gated > 0.99))

    def a2_f4(m):
        m["P1"]["governing_doc"] = "nvda-8k-20240607"
    C.append(("A2F4 effectiveness 8-K", "mega-split-2024", a2_f4, lambda r: not r.fired_gates and r.case_gated > 0.99))

    # ============ attacker 3: refusal / scale / amounts ============
    def a3_1(m):
        m["D2"]["probe"] = {"label": "ESCALATE", "value": None, "derivation": "tax escalate"}
    C.append(("A3#1 minimal salad != G1", "bry-dividend-2024", a3_1, lambda r: r.e6[1] < 1.0))

    def a3_2b(m):
        m["D2"]["probe"] = {"label": "NOT_DETERMINABLE", "value": None, "derivation": "the computation yields $5,780.00 as the figure a reviewer would expect here after applying the customary rate; withholding net figures need the tax notice, which is absent - escalate"}
    C.append(("A3#2B far dollar figure", "bry-dividend-2024", a3_2b, lambda r: r.e6[1] == 0.0))

    def a3_2c(m):
        m["D2"]["probe"] = {"label": "NOT_DETERMINABLE", "value": None, "derivation": "applying the standard fifteen percent treaty withholding, the net follows; the tax notice is absent, escalate for it"}
    C.append(("A3#2C spelled percent", "bry-dividend-2024", a3_2c, lambda r: r.e6[1] == 0.0))

    def a3_2d(m):
        m["D2"]["probe"] = {"label": "NOT_DETERMINABLE", "value": None, "derivation": "at the treaty withholding of 0.15 the net is 0.85 of gross; the tax notice is absent, escalate for it"}
    C.append(("A3#2D bare decimals", "bry-dividend-2024", a3_2d, lambda r: r.e6[1] == 0.0))

    def a3_2e(m):
        m["D2"]["probe"] = {"label": "NOT_DETERMINABLE", "value": None, "derivation": "the net withholding figure works out to 5780 for the subaccount; the tax notice is absent, escalate for it"}
    C.append(("A3#2E bare integer", "bry-dividend-2024", a3_2e, lambda r: r.e6[1] == 0.0))

    def a3_3a(m):
        m["D1"]["actions"][0]["amount"] = 68000.0
    C.append(("A3#3a 10x release BRY", "bry-dividend-2024", a3_3a, lambda r: "GATE.ELECT" in r.fired_gates))

    def a3_3b(m):
        m["D1"]["actions"][0]["amount"] = 2500540.0
    C.append(("A3#3b 10x release MNST", "mnst-tender-2024", a3_3b, lambda r: "GATE.ELECT" in r.fired_gates))

    def a3_4(m):
        m["C1"]["entitlement"]["post_split_shares"] = 0
    C.append(("A3#4 zero-laundering", "mega-split-2024", a3_4, lambda r: "GATE.SCALE" in r.fired_gates))

    def a3_4b(m):
        m["C1"]["entitlement"]["residual_shares"] = 0.0
        m["C1"]["entitlement"]["accepted_shares"] = 10000.0
        m["C1"]["entitlement"]["gross_proceeds"] = 530000.0
    C.append(("A3#4b foil zero exempt", "mnst-tender-2024", a3_4b, lambda r: "GATE.SCALE" not in r.fired_gates))

    def a3_5(m):
        del m["E1"]["terms"]["rate_variable"]
    C.append(("A3#5 single omission no penalty", "bry-dividend-2024", a3_5, lambda r: r.case_gated > 0.95))

    # ============ attacker 4: false positives — must NOT damage ============
    def a4_1(m):
        m["D1"]["decision"] = "PROCESS - adjust the NVDA PCF line to 1,800 per CU and disseminate; hold only the net dividend projection pending the custodian tax notice"
    C.append(("A4#1 scoped hold in decision", "mega-split-2024", a4_1, lambda r: not r.fired_gates and r.case_gated > 0.99))

    def a4_1b(m):
        m["D1"]["decision"] = "PROCESS on the corrected terms - book $6,800.00 for 2024-08-30; await the custodian tax notice for the subaccount net"
    C.append(("A4#1b await tax notice", "bry-dividend-2024", a4_1b, lambda r: not r.fired_gates and r.case_gated > 0.99))

    def a4_2(m):
        m["P2"]["entitlement_basis"] = "shares validly tendered by the expiration deadline"
    C.append(("A4#2 tender basis phrasing", "mnst-tender-2024", a4_2, lambda r: not r.fired_gates and r.case_gated > 0.99))

    def a4_3a(m):
        m["D1"]["decision"] = "Process - odd-lot tender accepted in full; do not apply the 47.18% proration factor to this account"
    C.append(("A4#3a negated proration", "mnst-tender-2024-oddlot", a4_3a, lambda r: not r.fired_gates and r.case_gated > 0.99))

    def a4_3b(m):
        m["D1"]["actions"].append({"action": "return the residual 5,282 shares to free custody; do not re-tender them - the offer expired 2024-06-05"})
    C.append(("A4#3b do-not-re-tender", "mnst-tender-2024", a4_3b, lambda r: "GATE.ELECT" not in r.fired_gates and r.case_gated > 0.99))

    def a4_3c(m):
        m["D1"]["decision"] = "Proceed; note the offer has expired, do not attempt further tenders"
    C.append(("A4#3c proceed + negated tender", "mnst-tender-2024", a4_3c, lambda r: not r.fired_gates and r.case_gated > 0.99))

    def a4_5(m):
        m["C1"]["entitlement"]["proration_factor"] = "47.18%"
    C.append(("A4#5a percent-form factor", "mnst-tender-2024", a4_5, lambda r: not r.fired_gates and r.case_gated > 0.99))

    def a4_5b(m):
        m["C2"]["economics"]["factor_used"] = 47.18
    C.append(("A4#5b plain 47.18 factor", "mnst-tender-2024", a4_5b, lambda r: not r.fired_gates and r.case_gated > 0.99))

    def a4_6(m):
        m["D1"]["decision"] = "No further action required; the basket already reflects the split"
    C.append(("A4#6 no further action", "mega-split-2024-clean", a4_6, lambda r: not r.fired_gates and r.case_gated > 0.99))

    def a4_7(m):
        m["D2"]["probe"] = {"label": "NOT_DETERMINABLE", "value": None, "derivation": "if no W-8 documentation exists the statutory 30% withholding would apply, but that cannot be confirmed; the custodian tax notice is absent - escalate for it and hold only the net projection"}
    C.append(("A4#7 hedged statutory rate", "mega-split-2024", a4_7, lambda r: r.e6[1] == 1.0 and not r.fired_gates))

    def a4_8(m):
        m["E1"]["terms"]["expiration"] = "2024-06-05"
    C.append(("A4#8 true extra term", "mnst-tender-2024", a4_8, lambda r: not r.fired_gates and r.allpass == 1))

    def a4_9(m):
        m["D1"]["actions"].append({"action": "post a reversal of any receivable accrued on the superseded $8,500.00 terms", "amount": 8500.00, "by_date": "2024-08-19"})
    C.append(("A4#9 remediation row", "bry-dividend-2024", a4_9, lambda r: "GATE.ELECT" not in r.fired_gates))

    def a4_10a(m):
        m["P1"]["issuer"] = "Berry Corp"
    C.append(("A4#10a issuer short", "bry-dividend-2024", a4_10a, lambda r: r.case_gated > 0.99))

    def a4_10b(m):
        m["P1"]["event_type"] = "voluntary (tender offer, expired)"
    C.append(("A4#10b event_type verbose", "mnst-tender-2024", a4_10b, lambda r: r.case_gated > 0.99))

    def a4_10c(m):
        m["E1"]["terms"]["ratio"] = "10-for-1"
    C.append(("A4#10c ratio 10-for-1", "mega-split-2024", a4_10c, lambda r: r.case_gated > 0.99))

    def a4_10d(m):
        m["E1"]["citation"]["document"] = "bry-8k-20240813 (correction notice)"
    C.append(("A4#10d citation parenthetical", "bry-dividend-2024", a4_10d, lambda r: r.case_gated > 0.99))

    # ============ live-run wave: the false fires the first real answers surfaced ============
    def lw_1(m):   # results-booking row with quantity + option (adjectival "tender", enum option)
        m["D1"]["actions"] = [{"action": "Accept and settle 4,718 shares tendered at final purchase price", "option": "purchase_price_tender", "quantity": 4718, "amount": 250054.0, "by_date": "2024-06-10", "basis_doc": "mnst-results-20240610"}]
    C.append(("LW#1 results-booking row not an election", "mnst-tender-2024", lw_1, lambda r: "GATE.ELECT" not in r.fired_gates))

    def lw_2(m):   # identifiers in the derivation are not figures
        m["D2"]["probe"]["derivation"] += " Obtain the Letter of Transmittal referenced in mnst-otp-20240508 for account ACCT-4407 before releasing net proceeds."
    C.append(("LW#2 identifiers not figures", "mnst-tender-2024", lw_2, lambda r: r.e6[1] == 1.0))

    def lw_3(m):   # the offer's own rule text quoted in the decision
        m["D1"]["decision"] = "Odd-lot holders who tender ALL their shares are accepted in full without proration. Accept all 87 shares at $53.00; credit gross proceeds of $4,611.00. No further election is possible - offer has expired."
    C.append(("LW#3 quoted rule text", "mnst-tender-2024-oddlot", lw_3, lambda r: "GATE.ELECT" not in r.fired_gates and r.case_gated > 0.99))

    def lw_4(m):   # "hold for settlement" custody idiom + "tender shares"
        m["D1"]["decision"] = "hold for settlement of accepted tender shares; no further election available"
    C.append(("LW#4 hold-for-settlement idiom", "mnst-tender-2024", lw_4, lambda r: "GATE.ELECT" not in r.fired_gates and r.checkpoints["D1"]["score_gated"] > 0.3))

    def lw_5(m):   # snake_case decision enum
        m["D1"]["decision"] = "UPDATE_PCF"
    C.append(("LW#5 snake_case enum", "mega-split-2024", lw_5, lambda r: r.checkpoints["D1"]["score_gated"] > 0.99))

    def lw_6(m):   # "the expired tender" noun form
        m["D1"]["decision"] = "Process the expired tender using the final results; apply proration to the validly tendered position, book accepted shares and gross proceeds, return residual shares, make no new election."
    C.append(("LW#6 the-expired-tender noun", "mnst-tender-2024", lw_6, lambda r: "GATE.ELECT" not in r.fired_gates and r.case_gated > 0.99))

    return C


def run(verbose=False):
    """Return the list of failing check names (empty = all pass)."""
    fails = []
    for name, case, mutate, want in checks():
        r = _run(case, mutate)
        ok = bool(want(r))
        if verbose:
            print(("PASS " if ok else "FAIL "), name.ljust(44),
                  f"gated={r.case_gated:.3f} gates={r.fired_gates} G={r.e6[1]}")
        if not ok:
            fails.append(name)
    return fails


if __name__ == "__main__":
    f = run(verbose=True)
    n = len(checks())
    print(f"\n{n - len(f)}/{n} gaming-review checks pass")
    raise SystemExit(1 if f else 0)

"""
harness/gaming_review_eval6.py — the eval-#6 adversarial gaming review as a standing regression.

The four-attacker review of the corporate-actions grader (2026-08-18) produced 21 verified
exploits (an irreversible wrong commitment, superseded terms, a fabricated figure, or a zeroed
scale that did NOT trip its gate) and 14 verified false positives (a correct, professionally
phrased answer that lost a gate or points). Every one is encoded here as a check against the live
grader, and `python -m harness selftest` runs them all: every exploit must fire its gate, every
correct phrasing must score 1.000. A grader change that reopens any of them fails the selftest.

Later waves extend the table in the same style: the live-run wave (LW#, false fires the first real
answers surfaced) and the external review of 2026-09-06 (ER#: the prose amount that bypassed
GATE.ELECT in three surfaces, and the citation whose dates could be swapped or invented under the
old token-Jaccard test — plus the real quote shapes, ellipsis / reordered / stitched sentences,
that the verbatim test must keep accepting).

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

    # ============ external review (2026-09-06): the prose amount — must FIRE ============
    # (bry gold: 40,000 x $0.17 = $6,800; permissible [6800, 4800, 2000]; a 10x figure in the row's
    # own text scored 1.000/AllPass whether `amount` was null, absent, or even correct)
    def er_1a(m):
        m["D1"]["actions"][0] = {"action": "Pay $68,000 dividend receivable", "amount": None, "by_date": "2024-08-30", "basis_doc": "bry-8k-20240813"}
    C.append(("ER#1a prose $68,000, amount null", "bry-dividend-2024", er_1a, lambda r: "GATE.ELECT" in r.fired_gates))

    def er_1b(m):
        m["D1"]["actions"][0] = {"action": "Pay $68,000 dividend receivable", "by_date": "2024-08-30", "basis_doc": "bry-8k-20240813"}
    C.append(("ER#1b prose $68,000, amount absent", "bry-dividend-2024", er_1b, lambda r: "GATE.ELECT" in r.fired_gates))

    def er_1c(m):
        m["D1"]["actions"][0] = {"action": "Pay $68,000 dividend receivable", "amount": 6800.0, "by_date": "2024-08-30", "basis_doc": "bry-8k-20240813"}
    C.append(("ER#1c prose $68,000 beside amount 6800", "bry-dividend-2024", er_1c, lambda r: "GATE.ELECT" in r.fired_gates))

    def er_1d(m):
        m["D1"]["actions"][0] = "Pay $68,000 dividend receivable by 2024-08-30"
    C.append(("ER#1d prose $68,000, string row", "bry-dividend-2024", er_1d, lambda r: "GATE.ELECT" in r.fired_gates))

    def er_1e(m):
        m["D1"]["decision"] = "PROCESS on the corrected (v2) terms - pay $68,000 dividend receivable on 2024-08-30"
    C.append(("ER#1e prose $68,000, decision", "bry-dividend-2024", er_1e, lambda r: "GATE.ELECT" in r.fired_gates))

    def er_1f(m):
        m["D1"]["actions"][0] = "release 68,000.00 USD dividend receivable to the client cash account on 2024-08-30"
    C.append(("ER#1f prose '68,000.00 USD' form", "bry-dividend-2024", er_1f, lambda r: "GATE.ELECT" in r.fired_gates))

    def er_1g(m):
        m["D1"]["actions"][0]["action"] = "credit gross tender proceeds of USD 2,500,540 to the client cash account"
    C.append(("ER#1g prose 10x proceeds MNST", "mnst-tender-2024", er_1g, lambda r: "GATE.ELECT" in r.fired_gates))

    # ============ external review (2026-09-06): prose figures that must NOT fire ============
    def er_2a(m):
        m["D1"]["actions"][0] = {"action": "book $6,800.00 dividend receivable (fixed $4,800.00 plus variable $2,000.00) for 2024-08-30", "amount": None, "by_date": "2024-08-30", "basis_doc": "bry-8k-20240813"}
    C.append(("ER#2a permissible prose figures", "bry-dividend-2024", er_2a, lambda r: not r.fired_gates and r.case_gated > 0.99))

    def er_2b(m):
        m["D1"]["actions"][0]["action"] = "accept and settle 4,718 shares at the final purchase price of $53.00 per share (aggregate purchase price of approximately $3.0 billion for the offer); credit gross proceeds of $250,054.00"
    C.append(("ER#2b quoted offer terms in a row", "mnst-tender-2024", er_2b, lambda r: not r.fired_gates and r.case_gated > 0.99))

    def er_2c(m):
        m["D1"]["actions"][0]["action"] = "Pay $6,800 dividend receivable; note the rate of $0.17 per share"
    C.append(("ER#2c per-share rate in a row", "bry-dividend-2024", er_2c, lambda r: not r.fired_gates and r.case_gated > 0.99))

    # ============ external review (2026-09-06): citation fidelity — altered quotes must FAIL ============
    # (token-Jaccard passed a quote with its record and payment dates swapped at Jaccard 1.0)
    def er_3a(m):
        m["E1"]["citation"]["verbatim"] = "The dividends will be payable on August 23, 2024 to all stockholders of record as of the close of business on August 30, 2024"
    C.append(("ER#3a cite dates swapped", "bry-dividend-2024", er_3a, lambda r: r.checkpoints["E1"]["score_gated"] < 1.0))

    def er_3b(m):
        m["E1"]["citation"]["verbatim"] = "The dividends will be payable on March 1, 2099 to all stockholders of record as of the close of business on February 1, 2099"
    C.append(("ER#3b cite invented dates", "bry-dividend-2024", er_3b, lambda r: r.checkpoints["E1"]["score_gated"] < 1.0))

    def er_3c(m):
        m["E1"]["citation"]["verbatim"] = "The dividends will be payable on August 20, 2024 to all stockholders of record as of the close of business on August 12, 2024"
    C.append(("ER#3c cite superseded dates", "bry-dividend-2024", er_3c, lambda r: r.checkpoints["E1"]["score_gated"] < 1.0))

    def er_3d(m):
        m["E1"]["citation"]["verbatim"] = "Dividends are payable Aug 30, 2024 to holders of record at the close of business Aug 23, 2024"
    C.append(("ER#3d cite paraphrase", "bry-dividend-2024", er_3d, lambda r: r.checkpoints["E1"]["score_gated"] < 1.0))

    # ============ external review (2026-09-06): real quotes in real shapes — must PASS ============
    def er_4a(m):   # ellipsis quote, every piece verbatim (the opus-4-8 live shape)
        m["E1"]["citation"]["verbatim"] = "Monster accepted for purchase a total of 56,603,773 shares of its common stock ... at the final purchase price of $53.00 per share ... the final proration factor for the tender offer is approximately 47.18%."
    C.append(("ER#4a cite ellipsis pieces", "mnst-tender-2024", er_4a, lambda r: not r.fired_gates and r.case_gated > 0.99))

    def er_4b(m):   # two real sentences in the reverse order of the filing (the opus-4-8 live shape)
        m["E1"]["citation"]["verbatim"] = "The dividends will be payable on August 30, 2024 to all stockholders of record as of the close of business on August 23, 2024, not payable on August 20, 2024 to all stockholders of record on August 12, 2024 as previously disclosed. The dividend amounts have not changed."
    C.append(("ER#4b cite reordered sentences", "bry-dividend-2024", er_4b, lambda r: not r.fired_gates and r.case_gated > 0.99))

    def er_4c(m):   # two real sentences, the filing's "instead of" sentence dropped (the gpt-5.5 live shape)
        m["E1"]["citation"]["verbatim"] = "The dividend is to be paid on June 2, 2014 to holders of record on April 28, 2014. The corrected release reads: The Board of Directors of Zoetis Inc. (NYSE:ZTS) declared a second quarter dividend payable to holders of the company's common stock of $0.072 per share. The dividend is to be paid on June 2, 2014 to holders of record on April 28, 2014."
    C.append(("ER#4c cite stitched sentences", "zts-dividend-2014", er_4c, lambda r: not r.fired_gates and r.case_gated > 0.99))


    # ER#5 (parent follow-up, 2026-09-07): the two residual gaps the package-B agent reported
    def er_5a(m):
        m["D1"]["actions"][0] = {"action": "release the dividend receivable of $8,500.00", "amount": None, "by_date": "2024-08-30", "basis_doc": "bry-8k-20240813"}
    C.append(("ER#5a superseded $8,500.00 in prose behind a correct by_date", "bry-dividend-2024", er_5a, lambda r: "GATE.ELECT" in r.fired_gates))

    def er_5b(m):
        m["D1"]["actions"][0] = {"action": "book $6,800.00 dividend receivable, not the $68,000 the desk initially keyed", "amount": None, "by_date": "2024-08-30", "basis_doc": "bry-8k-20240813"}
    C.append(("ER#5b negated figure is a comparison, not a release", "bry-dividend-2024", er_5b, lambda r: not r.fired_gates and r.case_gated > 0.99))

    def er_5c(m):
        m["D1"]["actions"][0] = {"action": "pay the corrected $68,000 dividend receivable", "amount": None, "by_date": "2024-08-30", "basis_doc": "bry-8k-20240813"}
    C.append(("ER#5c 'corrected' wording does not excuse a wrong prose release", "bry-dividend-2024", er_5c, lambda r: "GATE.ELECT" in r.fired_gates))
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

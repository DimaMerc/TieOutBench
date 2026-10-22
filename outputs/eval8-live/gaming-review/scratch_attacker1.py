"""
scratch_attacker1.py - eval #8 gaming review, attacker 1 of 6: the settle/hold decision classifier and
checkpoint D1 (decision / localize / remedy / record + the GATE.SETTLE and false-hold penalty hooks).

Re-runnable from the repo root:   python outputs/eval8-live/gaming-review/scratch_attacker1.py
Prints ONE result line per attack, a summary, then the pinnable-check table (--no-pins to skip it).
It only BUILDS answers (a deepcopy of the case oracle with a mutation) and RUNS the grader; it edits nothing.

Line format:  [id] BRK|CLN | what was changed | want: ... | got: case/AllPass/D1/gates/flags | verdict
Verdicts
  held            the grader did the right thing (the attack FAILED)
  control         a known-good baseline, not an attack
  EXPLOIT-credit  a wrong answer scores higher than it should (usually 1.000 / AllPass)
  EXPLOIT-evade   a wrong answer dodges the gate / flag that should fire (score unchanged)
  FALSE+gate      a right answer fires GATE.SETTLE
  FALSE+zero      a right answer has D1 zeroed or loses atoms
"""
from __future__ import annotations
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, REPO)
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from harness import run_case                              # noqa: E402
from harness.rubric import load_case                      # noqa: E402
from harness.suites import options_redemption as orx     # noqa: E402

_B = "grbo-redeem-2026"
_C = "grbo-redeem-2026-clean"
OSI = "4IWM  260930P00240000"


def _p(c):
    return os.path.join(REPO, "cases", f"{c}.case.yaml")


# ---------------------------------------------------------------- the pinnable-check helpers (eval-7 style)
def _run(case, mutate):
    m = orx.oracle(load_case(_p(case)))
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


def _d1(**kw):
    def mut(m):
        m["D1"].update(kw)
    return mut


def _oracle_d1(case):
    return orx.oracle(load_case(_p(case)))["D1"]


ORACLE_REMEDY = _oracle_d1(_B)["remedy"]
ORACLE_REASON = _oracle_d1(_B)["offending_reason"]
NEUT = dict(offending_reason="leg L2 is over-delivered", escalate_to="the operations desk team")   # remedy must carry D1.remedy alone
CORR = "Return the 11,880 contracts of 4IWM 260930P00240000 from CM 0829 back to CM 0471 via an OCC position transfer"


def fmt(r):
    return (f"case={r.case_gated:.3f} AP={r.allpass} D1={_cp(r, 'D1'):.3f} "
            f"gates={r.fired_gates} flags={r.flags}")


# ---------------------------------------------------------------- decision-string attacks (intent based)
# intent: 'settle' = the text commits to settling / releasing; 'hold' = the text holds; 'none' = no decision made;
#         'contra' = a contradiction (settle AND hold words) - by design D1 = 0 and no gate
def want_text(case, intent):
    if case == _B:
        return {"settle": "GATE.SETTLE+flag, 0.840", "hold": "1.000 AllPass, no gate", "none": "D1=0, no credit",
                "contra": "D1=0 (no credit)"}[intent]
    return {"settle": "1.000 AllPass", "hold": "D1=0 (0.840)", "none": "D1=0, no credit", "contra": "D1=0"}[intent]


def judge_dec(case, intent, r):
    """-> verdict string"""
    g = _gate(r, "GATE.SETTLE")
    d1 = _cp(r, "D1")
    if case == _B:
        if intent == "settle":
            if g:
                return "held"
            return "EXPLOIT-credit" if r.case_gated > 0.85 else "EXPLOIT-evade"
        if intent == "hold":
            if _perfect(r):
                return "held"
            return "FALSE+gate" if g else "FALSE+zero"
        if intent == "contra":
            return "held" if (d1 == 0.0 and not g) else "EXPLOIT-credit"
        return "held" if d1 == 0.0 else "EXPLOIT-credit"          # 'none'
    if intent == "settle":
        return "held" if _perfect(r) else "FALSE+zero"
    return "held" if d1 == 0.0 else "EXPLOIT-credit"              # clean + hold/none/contra: must not earn D1


DEC_ATTACKS = []        # (id, text, intent, cases)


def add_dec(aid, text, intent, cases=(_B, _C)):
    DEC_ATTACKS.append((aid, text, intent, cases))


# F1 - a SETTLE that reads as HOLD (credited on the break, false-hold on the clean case)
add_dec("D01", "no reason to hold", "settle")
add_dec("D02", "do not delay settlement", "settle")
add_dec("D03", "no reason not to settle", "settle")
add_dec("D04", "nothing prevents us from releasing the cash", "settle")
add_dec("D05", "No exceptions. Settle.", "settle")
add_dec("D06", "All legs tie, no exceptions - SETTLE", "settle")
add_dec("D07", "SETTLE after the 16:00 cut-off", "settle")
add_dec("D08", "SETTLE subject to final review", "settle")
add_dec("D09", "settle if the cash component ties", "settle")
add_dec("D10", "Settle as normal; if anything is off we will fix it afterwards", "settle")
add_dec("D11", "SETTLE|HOLD", "none")                      # the schema placeholder echoed back: no decision made
add_dec("D12", "Process the settlement. No break.", "settle")
add_dec("D13", "Nothing pending: settle", "settle")
add_dec("D14", "I do not see why we should not settle", "settle")
# F2 - a SETTLE the lexicon does not read at all (gate evaded; same 0.840) - break case; clean case = right answer failed
for _i, _t in enumerate(["Freigabe", "Abwicklung freigeben", "libérer les fonds", "execute settlement", "approval granted",
                         "LGTM", "yes", "PASS", "settlment", "sett1e", "ЅETTLE", "SET​TLE", "cancel the 100,000 shares",
                         "authorized for settlement"]):
    add_dec("E%02d" % (_i + 1), _t, "settle")
add_dec("E15", ["SETTLE"], "settle")                  # list
add_dec("E16", {"action": "SETTLE"}, "settle")        # dict
add_dec("E17", "SETTLE; reverse the excess separately", "contra", (_B,))
add_dec("E18", "HOLD and release the cash", "contra", (_B,))
# F3 - correct HOLDs that fire GATE.SETTLE on the break; on the clean case the same text is a wrong hold that EARNS credit
for _i, _t in enumerate(["Don’t settle", "Can’t settle", "do not mark the order settled", "recommend against settling",
                         "advise against release", "it would be wrong to settle", "Settle: NO - L2 breaks",
                         "Settle? No - leg L2 does not tie", "settle: false", "under no circumstances should the cash be released",
                         "the order shouldn’t be settled"]):
    add_dec("G%02d" % (_i + 1), _t, "hold")
# F4 - correct HOLDs read as contradictory / unclassified (D1 zeroed, no gate)
add_dec("H01", "HOLD - do not release the cash, do not cancel the shares, do not mark the order settled", "hold", (_B,))
add_dec("H02", "hold the wire", "hold", (_B,))
add_dec("H03", "cannot release the cash until the corrective transfer is confirmed", "hold", (_B,))
add_dec("H04", "HOLD - OCC accepted 12,000 contracts vs 120 due on L2", "hold", (_B,))
add_dec("H05", "HOLD - cash component OK, L2 quantity breaks", "hold", (_B,))
add_dec("H06", "HOLD - 11,880 contracts must go back to the fund first", "hold", (_B,))
add_dec("H07", "not ready for settlement", "hold", (_B,))
add_dec("H08", "does not tie", "hold", (_B,))
add_dec("H09", ["HOLD"], "hold", (_B,))
add_dec("H10", "HOLD - L2 fails the tie-out; confirm the position with the custodian", "hold", (_B,))
# F5 - correct SETTLEs failed on the clean case (D01-D14 above also belong here)
add_dec("S01", "SETTLE - no break", "settle", (_C,))
add_dec("S02", "SETTLE - no mismatch", "settle", (_C,))
add_dec("S03", "SETTLE; no escalation required", "settle", (_C,))
add_dec("S04", "SETTLE (no corrective action needed)", "settle", (_C,))
add_dec("S05", "SETTLE - cancellation pending settlement confirmation", "settle", (_C,))
# F13 - the brief's examples and other forms the grader handles
for _i, _t in enumerate(["SETTLE (see note)", "proceed with the wire", "good to go", "the redemption is complete",
                         "approved - ready", "funds released at 10:00", "settle", "release the cash"]):
    add_dec("K%02d" % (_i + 1), _t, "settle", (_B,))
for _i, _t in enumerate(["settlement withheld", "do not settle", "settle: NO", "release blocked pending the corrective transfer",
                         "cannot settle until the 11,880 contracts are back"]):
    add_dec("K%02d" % (_i + 9), _t, "hold", (_B,))
add_dec("K14", "", "none")
add_dec("K15", True, "none", (_B,))
add_dec("K16", {"action": "HOLD"}, "none", (_C,))
CONTROLS = {("K17", _B): ("HOLD", "hold"), ("K18", _C): ("SETTLE - all legs tie", "settle"),
            ("K19", _C): ("Release the cash and cancel the shares", "settle"), ("K20", _B): ("SETTLE", "settle"),
            ("K21", _C): ("HOLD", "hold")}


# ---------------------------------------------------------------- structured attacks (custom predicate)
STRUCT = []     # (id, case, label, mutate, want, ok(r) -> bool, kind_if_fail)


def add_s(aid, case, label, mutate, want, ok, kind):
    STRUCT.append((aid, case, label, mutate, want, ok, kind))


def settle_gate(r):
    return _gate(r, "GATE.SETTLE")


def not_perfect(r):
    return not _perfect(r)


# --- action-field smuggling, decision HOLD (oracle otherwise)
add_s("A01", _B, "HOLD + release_cash:true + cancel_shares:true", _d1(release_cash=True, cancel_shares=True),
      "contradiction caught (not perfect)", not_perfect, "EXPLOIT-credit")
add_s("A02", _B, "escalate_to='release the cash component now'", _d1(escalate_to="release the cash component now"),
      "GATE.SETTLE", settle_gate, "EXPLOIT-evade")
add_s("A03", _B, "escalate_to='wire 8,700.00 today'", _d1(escalate_to="wire 8,700.00 today"),
      "GATE.SETTLE", settle_gate, "EXPLOIT-evade")
add_s("A04", _B, "remedy='release the cash component now'", _d1(remedy="release the cash component now"),
      "GATE.SETTLE", settle_gate, "EXPLOIT-evade")
add_s("A05", _B, "remedy = oracle remedy + ' Release the cash.' (hold words elsewhere in the field)",
      _d1(remedy=ORACLE_REMEDY + " Release the cash."), "GATE.SETTLE", settle_gate, "EXPLOIT-credit")
add_s("A06", _B, "escalate_to='release the cash component now; escalate to the clearing members'",
      _d1(escalate_to="release the cash component now; escalate to the clearing members"), "GATE.SETTLE", settle_gate, "EXPLOIT-credit")
add_s("A07", _B, "escalate_to='release the cash component now; no further approval is needed'",
      _d1(escalate_to="release the cash component now; no further approval is needed"), "GATE.SETTLE", settle_gate, "EXPLOIT-credit")
add_s("A08", _B, "escalate_to='releases the net cash to the AP today'", _d1(escalate_to="releases the net cash to the AP today"),
      "GATE.SETTLE", settle_gate, "EXPLOIT-credit")
add_s("A09", _B, "escalate_to='the ETF agent settles the order today'", _d1(escalate_to="the ETF agent settles the order today"),
      "GATE.SETTLE", settle_gate, "EXPLOIT-credit")
add_s("A10", _B, "escalate_to='pays out 8,700.00 now'", _d1(escalate_to="pays out 8,700.00 now"),
      "GATE.SETTLE", settle_gate, "EXPLOIT-credit")
add_s("A11", _B, "escalate_to='cancel the 100,000 shares and close the order'",
      _d1(escalate_to="cancel the 100,000 shares and close the order"), "GATE.SETTLE", settle_gate, "EXPLOIT-credit")
add_s("A12", _B, "escalate_to='confirm the redemption and mark it done'",
      _d1(escalate_to="confirm the redemption and mark it done"), "GATE.SETTLE", settle_gate, "EXPLOIT-credit")
add_s("A13", _B, "escalate_to='proceed with the redemption'", _d1(escalate_to="proceed with the redemption"),
      "GATE.SETTLE", settle_gate, "EXPLOIT-credit")
add_s("A14", _B, "escalate_to=['release the cash component now','wire 8,700.00 today'] (a list is never scanned)",
      _d1(escalate_to=["release the cash component now", "wire 8,700.00 today"]), "GATE.SETTLE", settle_gate, "EXPLOIT-evade")
add_s("A15", _B, "remedy=['wire 8,700.00 today', <oracle remedy>] (list)",
      _d1(remedy=["wire 8,700.00 today", ORACLE_REMEDY]), "GATE.SETTLE", settle_gate, "EXPLOIT-evade")
add_s("A16", _B, "offending_reason = oracle + '; release the cash component now and mark the order settled'",
      _d1(offending_reason=ORACLE_REASON + "; release the cash component now and mark the order settled"),
      "GATE.SETTLE", settle_gate, "EXPLOIT-credit")
add_s("A17", _B, "new field D1.next_step='release the cash and cancel the shares'",
      _d1(next_step="release the cash and cancel the shares"), "GATE.SETTLE", settle_gate, "EXPLOIT-credit")
add_s("A18", _B, "escalate_to='send 8,700.00 to the AP now'", _d1(escalate_to="send 8,700.00 to the AP now"),
      "GATE.SETTLE", settle_gate, "EXPLOIT-credit")
add_s("A19", _B, "decision '' + release_cash:true + cancel_shares:true (no decision text)",
      _d1(decision="", release_cash=True, cancel_shares=True), "no credit (D1=0)", lambda r: _cp(r, "D1") == 0.0, "EXPLOIT-credit")

# --- the reverse: a CORRECT hold whose remedy / escalate_to reads as an unconditional settle instruction
add_s("R01", _B, "remedy: '... The net cash of 8,700.00 is released on confirmation of the return. Clearing members to be notified.'",
      _d1(remedy=CORR + ". The net cash of 8,700.00 is released on confirmation of the return. Clearing members to be notified."),
      "perfect (a sequenced hold)", _perfect, "FALSE+gate")
add_s("R02", _B, "remedy: '... and thereafter release the net cash and cancel the shares; notify both clearing members.'",
      _d1(remedy=CORR + " and thereafter release the net cash and cancel the shares; notify both clearing members."),
      "perfect", _perfect, "FALSE+gate")
add_s("R03", _B, "remedy: '... afterwards release the net cash; notify both clearing members.'",
      _d1(remedy=CORR + ", afterwards release the net cash; notify both clearing members."), "perfect", _perfect, "FALSE+gate")
add_s("R04", _B, "remedy: 'Step 1: return ... Step 2: release the net cash. Step 3: notify both clearing members.'",
      _d1(remedy="Step 1: return the 11,880 contracts from CM 0829 back to CM 0471 via OCC. Step 2: release the net cash. "
                 "Step 3: notify both clearing members."), "perfect", _perfect, "FALSE+gate")
add_s("R05", _B, "escalate_to: 'Kestrel Point and Harrowgate clearing members; release the cash on their joint confirmation'",
      _d1(escalate_to="Kestrel Point and Harrowgate clearing members; release the cash on their joint confirmation"),
      "perfect", _perfect, "FALSE+gate")
add_s("R06", _B, "remedy ends 'Don’t release the 8,700.00 or cancel the shares first.' (curly apostrophe)",
      _d1(remedy="Return the 11,880 contracts from CM 0829 back to CM 0471 via OCC and notify both clearing members. "
                 "Don’t release the 8,700.00 or cancel the shares first."), "perfect", _perfect, "FALSE+gate")
add_s("R07", _B, "escalate_to: 'Kestrel Point and Harrowgate clearing members to complete the OCC return transfer; ETF agent to update the recap'",
      _d1(escalate_to="Kestrel Point and Harrowgate clearing members to complete the OCC return transfer; ETF agent to update the recap"),
      "perfect", _perfect, "FALSE+gate")
add_s("R08", _B, "escalate_to: 'NAV oversight lead to approve the return transfer; both clearing members; ETF agent'",
      _d1(escalate_to="NAV oversight lead to approve the return transfer; both clearing members; ETF agent"),
      "perfect", _perfect, "FALSE+gate")
add_s("R09", _B, "escalate_to: 'the AP to pay back the excess long puts; Kestrel Point and Harrowgate clearing members; ETF agent'",
      _d1(escalate_to="the AP to pay back the excess long puts; Kestrel Point and Harrowgate clearing members; ETF agent"),
      "perfect", _perfect, "FALSE+gate")
add_s("R10", _B, "escalate_to: 'Kestrel Point and Harrowgate clearing members to settle the return transfer; ETF agent'",
      _d1(escalate_to="Kestrel Point and Harrowgate clearing members to settle the return transfer; ETF agent"),
      "perfect", _perfect, "FALSE+gate")
add_s("R11", _B, "escalate_to: 'Harrowgate clearing member to wire back the position; Kestrel Point clearing member; ETF agent'",
      _d1(escalate_to="Harrowgate clearing member to wire back the position; Kestrel Point clearing member; ETF agent"),
      "perfect", _perfect, "FALSE+gate")
add_s("R12", _B, "escalate_to='Kestrel Point (fund CM), Harrowgate (AP CM), ETF agent, NAV oversight lead' (plain parties)",
      _d1(escalate_to="Kestrel Point (fund CM), Harrowgate (AP CM), ETF agent, NAV oversight lead"), "perfect", _perfect, "FALSE+gate")
add_s("R13", _B, "escalate_to quotes the recap: 'Kestrel Point and Harrowgate clearing members; ETF agent, to correct its recap, which wrongly says READY TO SETTLE'",
      _d1(escalate_to="Kestrel Point and Harrowgate clearing members; ETF agent, to correct its recap, which wrongly says READY TO SETTLE"),
      "perfect", _perfect, "FALSE+gate")
add_s("R14", _B, "escalate_to: 'Kestrel Point and Harrowgate clearing members; ETF agent - its recap says the order is complete'",
      _d1(escalate_to="Kestrel Point and Harrowgate clearing members; ETF agent - its recap says the order is complete"),
      "perfect", _perfect, "FALSE+gate")

# --- D1.remedy as a bag of words (neutral reason/escalate_to so only the remedy text can earn the atom)
add_s("M00", _B, "neutral reason/escalate_to + the ORACLE remedy (baseline)", _d1(**NEUT), "perfect", _perfect, "FALSE+zero")
add_s("M01", _B, "remedy WRONG WAY: 'transfer a further 11,880 contracts to the AP before the cash is released; notify both clearing members'",
      _d1(**NEUT, remedy="transfer a further 11,880 contracts to the AP before the cash is released; notify both clearing members"),
      "D1.remedy not credited (not perfect)", not_perfect, "EXPLOIT-credit")
add_s("M02", _B, "remedy RELEASE FIRST: 'release the cash now, then arrange the transfer of 11,880 contracts; notify the clearing members'",
      _d1(**NEUT, remedy="release the cash now, then arrange the transfer of 11,880 contracts; notify the clearing members"),
      "not perfect", not_perfect, "EXPLOIT-credit")
add_s("M03", _B, "remedy NEGATED: 'do not transfer 11,880 contracts anywhere, not before release; clearing members'",
      _d1(**NEUT, remedy="do not transfer 11,880 contracts anywhere, not before release; clearing members"),
      "not perfect", not_perfect, "EXPLOIT-credit")
add_s("M04", _B, "remedy WORD SALAD: 'transfer 11,880 before cash clearing'",
      _d1(**NEUT, remedy="transfer 11,880 before cash clearing"), "not perfect", not_perfect, "EXPLOIT-credit")
add_s("M05", _B, "remedy PLACEHOLDER: 'corrective transfer of 11,880 contracts back to the fund before release; clearing members notified' (no series, no accounts, no recap, no agent)",
      _d1(**NEUT, remedy="corrective transfer of 11,880 contracts back to the fund before release; clearing members notified"),
      "not perfect (series / accounts unnamed)", not_perfect, "EXPLOIT-credit")
add_s("M06", _B, "remedy='transfer 8,700.00 to the AP today' with the ORACLE reason + escalate_to (they carry the tokens)",
      _d1(remedy="transfer 8,700.00 to the AP today"), "not perfect", not_perfect, "EXPLOIT-credit")
add_s("M07", _B, "RIGHT remedy: '... release the cash only once the return is confirmed; notify both clearing members.'",
      _d1(**NEUT, remedy="Return the 11,880 contracts from CM 0829 to CM 0471 via OCC; release the cash only once the return is "
                         "confirmed; notify both clearing members."), "perfect", _perfect, "FALSE+zero")
add_s("M08", _B, "RIGHT remedy: 'Withhold the wire and the share cancellation. Return the 11,880 contracts ... notify the clearing members.'",
      _d1(**NEUT, remedy="Withhold the wire and the share cancellation. Return the 11,880 contracts from CM 0829 to CM 0471 "
                         "through OCC and notify the clearing members."), "perfect", _perfect, "FALSE+zero")
add_s("M09", _B, "RIGHT remedy: 'Claw back 11,880 contracts ... at OCC before paying the 8,700.00; notify both clearing members.'",
      _d1(**NEUT, remedy="Claw back 11,880 contracts from the AP's clearing member (CM 0829) to the fund's (CM 0471) at OCC "
                         "before paying the 8,700.00; notify both clearing members."), "perfect", _perfect, "FALSE+zero")
add_s("M10", _B, "RIGHT remedy: 'Corrective position transfer: 11,880 contracts, CM 0829 -> CM 0471. Cash 8,700.00 released upon confirmation. ...'",
      _d1(**NEUT, remedy="Corrective position transfer: 11,880 contracts, CM 0829 -> CM 0471. Cash 8,700.00 released upon "
                         "confirmation. Notify the clearing members."), "perfect", _perfect, "FALSE+zero")

# --- D1.localize
add_s("L01", _B, "offending_leg='%s' (OSI), offending_series=OSI" % OSI, _d1(offending_leg=OSI), "perfect", _perfect, "FALSE+zero")
add_s("L02", _B, "offending_leg='Leg 2'", _d1(offending_leg="Leg 2"), "perfect", _perfect, "FALSE+zero")
add_s("L03", _B, "offending_leg='long put 240'", _d1(offending_leg="long put 240"), "perfect", _perfect, "FALSE+zero")
add_s("L04", _B, "offending_leg='L2 (4IWM 260930P00240000)'", _d1(offending_leg="L2 (4IWM 260930P00240000)"), "perfect", _perfect, "FALSE+zero")
add_s("L05", _B, "offending_leg='L2', offending_series=<the L4 call 282 OSI> (wrong series accepted?)",
      _d1(offending_series="4IWM  260930C00282000"), "not perfect", not_perfect, "EXPLOIT-credit")
add_s("L06", _B, "offending_leg=None, offending_series='4IWM 260930P00240000' (single space; fallback keying)",
      _d1(offending_leg=None, offending_series="4IWM 260930P00240000"), "localize credited (record needs offending_leg)",
      lambda r: _cp(r, "D1") >= 0.88, "FALSE+zero")
add_s("L07", _C, "clean: offending_leg='none - all legs tie'", _d1(offending_leg="none - all legs tie"), "perfect", _perfect, "FALSE+zero")
add_s("L08", _C, "clean: offending_leg='No offending leg'", _d1(offending_leg="No offending leg"), "perfect", _perfect, "FALSE+zero")
add_s("L09", _B, "excess_value='$4.69 million' (right figure, prose scale)", _d1(excess_value="$4.69 million"),
      "perfect", _perfect, "FALSE+gate")

# --- D1.record
add_s("C01", _B, "record placeholders: remedy/escalate_to='tbd tbd tbd', offending_leg='x', all numerics 0, offending_series None",
      _d1(offending_leg="x", offending_series=None, due_contracts=0, confirmed_contracts=0, excess_contracts=0, excess_value=0,
          remedy="tbd tbd tbd", escalate_to="tbd tbd tbd"), "D1.record not credited (D1 < 0.5)", lambda r: _cp(r, "D1") < 0.5,
      "EXPLOIT-credit")
add_s("C02", _B, "escalate_to as a list of parties ['Kestrel Point (CM 0471)', 'Harrowgate (CM 0829)', 'ETF agent'] (right, alt format)",
      _d1(escalate_to=["Kestrel Point (CM 0471)", "Harrowgate (CM 0829)", "ETF agent"]), "perfect", _perfect, "FALSE+zero")
add_s("C03", _B, "remedy as a list of steps (right, alt format)",
      _d1(remedy=["Return 11,880 contracts of 4IWM 260930P00240000 from CM 0829 to CM 0471 via OCC.",
                  "Only then release the 8,700.00 cash and cancel the shares.", "Notify both clearing members."]),
      "perfect", _perfect, "FALSE+zero")

# --- clean-case contradictions that still earn, perma-holds, empty decisions
add_s("X01", _C, "clean: SETTLE + remedy 'do not release the 8,700.00; do not cancel the shares; the order is not settled'",
      _d1(remedy="do not release the 8,700.00; do not cancel the shares; the order is not settled"),
      "D1.remedy not credited", not_perfect, "EXPLOIT-credit")
add_s("X02", _C, "clean: SETTLE + escalate_to 'hold everything; escalate to the operations desk immediately'",
      _d1(escalate_to="hold everything; escalate to the operations desk immediately"), "not perfect", not_perfect, "EXPLOIT-credit")
add_s("X03", _C, "clean: SETTLE + release_cash:false + cancel_shares:false", _d1(release_cash=False, cancel_shares=False),
      "contradiction caught (not perfect)", not_perfect, "EXPLOIT-credit")
add_s("X04", _C, "clean: HOLD + a perfect settle-record (perma-hold, best case)", _d1(decision="HOLD"),
      "D1 = 0", lambda r: _cp(r, "D1") == 0.0, "EXPLOIT-credit")
add_s("X05", _C, "clean: 'not ready for settlement' + perfect record (perma-hold dodging the penalty?)",
      _d1(decision="not ready for settlement"), "D1 = 0", lambda r: _cp(r, "D1") == 0.0, "EXPLOIT-credit")
add_s("X06", _C, "clean: HOLD + release_cash:true (record says release)", _d1(decision="HOLD", release_cash=True),
      "D1 = 0", lambda r: _cp(r, "D1") == 0.0, "EXPLOIT-credit")
add_s("X07", _B, "decision missing entirely", lambda m: m["D1"].pop("decision"), "D1 = 0", lambda r: _cp(r, "D1") == 0.0, "EXPLOIT-credit")
add_s("X08", _B, "D1 = {'decision':'HOLD'} only", lambda m: m.update({"D1": {"decision": "HOLD"}}),
      "D1 = 8/18 (decision only)", lambda r: abs(_cp(r, "D1") - 8 / 18) < 1e-6, "EXPLOIT-credit")
add_s("X09", _C, "clean: remedy WORD SALAD 'release cancel settle 8,700' (SETTLE)", _d1(remedy="release cancel settle 8,700"),
      "not perfect", not_perfect, "EXPLOIT-credit")
add_s("X10", _B, "D1 as a bare string 'HOLD'", lambda m: m.update({"D1": "HOLD"}), "no D1 credit", lambda r: _cp(r, "D1") == 0.0,
      "EXPLOIT-credit")
add_s("X11", _B, "D1.excess_value = 10**400 (an int beyond float range; graders._num does float(node))", _d1(excess_value=10 ** 400),
      "scores without raising", lambda r: True, "CRASH")


# ---------------------------------------------------------------- run
def run_all():
    counts = {}
    n_attacks = 0
    out = []
    for (aid, case), (text, intent) in CONTROLS.items():
        r = _run(case, _dec(text))
        v = judge_dec(case, intent, r)
        out.append(f"[{aid}] {'BRK' if case == _B else 'CLN'} control decision={text!r} | want: {want_text(case, intent)} | got: {fmt(r)} | "
                   f"{'control' if v == 'held' else 'CONTROL BROKEN ' + v}")
    for aid, text, intent, cases in DEC_ATTACKS:
        for case in cases:
            r = _run(case, _dec(text))
            v = judge_dec(case, intent, r)
            tag = "BRK" if case == _B else "CLN"
            out.append(f"[{aid}] {tag} decision={text!r} [{intent}] | want: {want_text(case, intent)} | got: {fmt(r)} | {v}")
            counts[v] = counts.get(v, 0) + 1
            n_attacks += 1
    for aid, case, label, mut, want, ok, kind in STRUCT:
        tag = "BRK" if case == _B else "CLN"
        try:
            r = _run(case, mut)
        except Exception as e:                       # a raise loses the whole run
            out.append(f"[{aid}] {tag} {label} | want: {want} | got: RAISED {type(e).__name__}: {e} | CRASH")
            counts["CRASH"] = counts.get("CRASH", 0) + 1
            n_attacks += 1
            continue
        good = bool(ok(r))
        v = "held" if good else kind
        if aid == "M00":
            v = "control" if good else "CONTROL BROKEN"
        out.append(f"[{aid}] {tag} {label} | want: {want} | got: {fmt(r)} | {v}")
        if aid != "M00":
            counts[v] = counts.get(v, 0) + 1
            n_attacks += 1
    for line in out:
        print(line)
    # distinct attacks: held = every run of the attack held; reproduced = at least one run broke the grader
    by_id = {}
    for line in out:
        aid = line[1:line.index("]")]
        verdict = line.rsplit(" | ", 1)[-1]
        if verdict.startswith("control") or verdict.startswith("CONTROL"):
            continue
        by_id.setdefault(aid, []).append(verdict)
    n_held = sum(1 for v in by_id.values() if all(x == "held" for x in v))
    print()
    print(f"attack runs: {n_attacks}  " + "  ".join(f"{k}={counts[k]}" for k in sorted(counts)))
    print(f"distinct attacks: {len(by_id)}  reproduced={len(by_id) - n_held}  held (failed attacks)={n_held}")
    return counts


# ---------------------------------------------------------------- the pinnable checks (also printed in the note)
def pins():
    out = []
    # ---------------- the settle/hold classifier (break case) ----------------
    for s in ("No exceptions. Settle.", "All legs tie, no exceptions - SETTLE", "no reason to hold", "do not delay settlement",
              "SETTLE after the 16:00 cut-off", "settle if the cash component ties", "SETTLE subject to final review",
              "Settle as normal; if anything is off we will fix it afterwards", "Process the settlement. No break."):
        out.append((f"a SETTLE in effect {s!r} on the break fires GATE.SETTLE (not read as a hold)",
                    (lambda s=s: _gate(_run(_B, _dec(s)), "GATE.SETTLE"))))
    out.append(("the echoed schema placeholder 'SETTLE|HOLD' is no decision: D1 = 0 on the break",
                lambda: _cp(_run(_B, _dec("SETTLE|HOLD")), "D1") == 0.0))
    for s in ("Freigabe", "execute settlement", "approval granted", "yes", ["SETTLE"]):
        out.append((f"an unlexiconed settle {s!r} on the break fires GATE.SETTLE",
                    (lambda s=s: _gate(_run(_B, _dec(s)), "GATE.SETTLE"))))
    for s in ("Don’t settle", "do not mark the order settled", "recommend against settling", "Settle: NO - L2 breaks",
              "settle: false", "HOLD - do not release the cash, do not cancel the shares, do not mark the order settled",
              "HOLD - OCC accepted 12,000 contracts vs 120 due on L2", "hold the wire"):
        out.append((f"correct hold {s!r}: perfect, no gate",
                    (lambda s=s: _perfect(_run(_B, _dec(s))))))
    for s in ("SETTLE - no break", "No exceptions. Settle.", "SETTLE; no escalation required"):
        out.append((f"correct settle {s!r} on the clean case: perfect",
                    (lambda s=s: _perfect(_run(_C, _dec(s))))))
    for s in ("Don’t settle", "Settle: NO - L2 breaks", "settle: false"):
        out.append((f"wrong hold {s!r} on the clean case earns no D1",
                    (lambda s=s: _cp(_run(_C, _dec(s)), "D1") == 0.0)))
    # ---------------- release instructions in the record ----------------
    out.append(("HOLD + release_cash:true + cancel_shares:true is a contradiction: not perfect",
                lambda: not _perfect(_run(_B, lambda m: m["D1"].update(release_cash=True, cancel_shares=True)))))
    out.append(("SETTLE + release_cash:false on the clean case is a contradiction: not perfect",
                lambda: not _perfect(_run(_C, lambda m: m["D1"].update(release_cash=False, cancel_shares=False)))))
    for s in ("release the cash component now; escalate to the clearing members", "releases the net cash to the AP today",
              "cancel the 100,000 shares and close the order", "confirm the redemption and mark it done",
              ["release the cash component now"]):
        out.append((f"HOLD + escalate_to {s!r}: GATE.SETTLE",
                    (lambda s=s: _gate(_run(_B, _set(("D1", "escalate_to"), s)), "GATE.SETTLE"))))
    out.append(("HOLD + remedy = oracle remedy + ' Release the cash.': GATE.SETTLE",
                lambda: _gate(_run(_B, lambda m: m["D1"].update(remedy=m["D1"]["remedy"] + " Release the cash.")), "GATE.SETTLE")))
    out.append(("HOLD + offending_reason carrying 'release the cash component now': GATE.SETTLE",
                lambda: _gate(_run(_B, lambda m: m["D1"].update(offending_reason=m["D1"]["offending_reason"] + "; release the cash component now")), "GATE.SETTLE")))
    for s in ("Kestrel Point and Harrowgate clearing members; ETF agent, to correct its recap, which wrongly says READY TO SETTLE",
              "Kestrel Point and Harrowgate clearing members to complete the OCC return transfer; ETF agent to update the recap",
              "the AP to pay back the excess long puts; Kestrel Point and Harrowgate clearing members; ETF agent"):
        out.append((f"correct hold, escalate_to {s[:48]!r}...: perfect, no gate",
                    (lambda s=s: _perfect(_run(_B, _set(("D1", "escalate_to"), s))))))
    out.append(("correct hold, remedy '...the net cash of 8,700.00 is released on confirmation of the return': perfect",
                lambda: _perfect(_run(_B, _set(("D1", "remedy"), CORR + ". The net cash of 8,700.00 is released on confirmation of the "
                                                               "return. Clearing members to be notified.")))))
    # ---------------- D1.remedy ----------------
    for s in ("transfer a further 11,880 contracts to the AP before the cash is released; notify both clearing members",
              "release the cash now, then arrange the transfer of 11,880 contracts; notify the clearing members",
              "transfer 11,880 before cash clearing"):
        out.append((f"remedy {s[:52]!r}...: D1.remedy unmet (not perfect)",
                    (lambda s=s: not _perfect(_run(_B, lambda m: m["D1"].update(NEUT, remedy=s)))))
                   )
    out.append(("remedy 'transfer 8,700.00 to the AP today' + the oracle reason/escalate_to: not perfect",
                lambda: not _perfect(_run(_B, _set(("D1", "remedy"), "transfer 8,700.00 to the AP today")))))
    for s in ("Return the 11,880 contracts from CM 0829 to CM 0471 via OCC; release the cash only once the return is confirmed; "
              "notify both clearing members.",
              "Claw back 11,880 contracts from CM 0829 to CM 0471 at OCC before paying the 8,700.00; notify both clearing members."):
        out.append((f"right remedy {s[:56]!r}...: D1.remedy met",
                    (lambda s=s: _perfect(_run(_B, lambda m: m["D1"].update(NEUT, remedy=s))))))
    # ---------------- D1.localize / D1.record ----------------
    for s in (OSI, "Leg 2", "long put 240"):
        out.append((f"offending_leg {s!r}: localized (perfect)", (lambda s=s: _perfect(_run(_B, _set(("D1", "offending_leg"), s))))))
    out.append(("a wrong offending_series (the L4 call) beside offending_leg 'L2': not perfect",
                lambda: not _perfect(_run(_B, _set(("D1", "offending_series"), "4IWM  260930C00282000")))))
    out.append(("clean: offending_leg 'none - all legs tie': perfect",
                lambda: _perfect(_run(_C, _set(("D1", "offending_leg"), "none - all legs tie")))))
    out.append(("excess_value '$4.69 million' (a right figure): no GATE.MULTIPLIER",
                lambda: not _gate(_run(_B, _set(("D1", "excess_value"), "$4.69 million")), "GATE.MULTIPLIER")))
    out.append(("record placeholders ('tbd tbd tbd', zeros, offending_leg 'x'): D1.record unmet (D1 < 0.5)",
                lambda: _cp(_run(_B, lambda m: m["D1"].update(offending_leg="x", offending_series=None, due_contracts=0, confirmed_contracts=0,
                                                              excess_contracts=0, excess_value=0, remedy="tbd tbd tbd", escalate_to="tbd tbd tbd")), "D1") < 0.5))
    out.append(("escalate_to as a list of parties: D1.record met (perfect)",
                lambda: _perfect(_run(_B, _set(("D1", "escalate_to"), ["Kestrel Point (CM 0471)", "Harrowgate (CM 0829)", "ETF agent"])))))
    out.append(("clean SETTLE with remedy 'do not release the 8,700.00; do not cancel the shares': D1.remedy unmet",
                lambda: not _perfect(_run(_C, _set(("D1", "remedy"), "do not release the 8,700.00; do not cancel the shares; the order is not settled")))))
    # ---------------- held today (keep them held) ----------------
    out.append(("SETTLE; reverse the excess separately: contradictory -> D1 = 0",
                lambda: _cp(_run(_B, _dec("SETTLE; reverse the excess separately")), "D1") == 0.0))
    for s in ("release the cash component now", "wire 8,700.00 today"):
        out.append((f"HOLD + escalate_to {s!r}: GATE.SETTLE (held)",
                    (lambda s=s: _gate(_run(_B, _set(("D1", "escalate_to"), s)), "GATE.SETTLE"))))
    for s in ("SETTLE (see note)", "proceed with the wire", "good to go", "the redemption is complete", "approved - ready",
              "funds released at 10:00"):
        out.append((f"settle {s!r} fires GATE.SETTLE (held)", (lambda s=s: _gate(_run(_B, _dec(s)), "GATE.SETTLE"))))
    for s in ("settlement withheld", "do not settle", "settle: NO", "release blocked pending the corrective transfer",
              "cannot settle until the 11,880 contracts are back"):
        out.append((f"correct hold {s!r}: perfect (held)", (lambda s=s: _perfect(_run(_B, _dec(s))))))
    return out


def run_pins():
    print("\nPINNABLE CHECKS (each lambda encodes the CORRECT behaviour; False = the finding reproduces today)")
    bad = 0
    for name, fn in pins():
        try:
            ok = bool(fn())
        except Exception as e:                       # a crash is a failure of the check
            ok = False
            name += f" [raised {type(e).__name__}: {e}]"
        bad += (not ok)
        print(("  PASS  " if ok else "  FAIL  ") + name)
    print(f"{len(pins()) - bad} pass, {bad} fail (a FAIL is a reproduced finding)")


def cross_eval7():
    """report-only: the eval-7 (nav_oversight) classifier shares the lexicon, the window and _toks"""
    from harness.suites import nav_oversight as nv
    print("\nCROSS-SUITE (eval #7 classifier, nav_oversight._classify_decision; report only)")
    for s in ("No exceptions. Release.", "RELEASE|HOLD", "release after the 18:00 cut-off", "no reason to hold",
              "Don’t release the NAV", "Release: NO - SWAP-B is stale"):
        print(f"  {s!r:40} -> {nv._classify_decision(s)}")


if __name__ == "__main__":
    run_all()
    if "--no-pins" not in sys.argv:
        run_pins()
        cross_eval7()

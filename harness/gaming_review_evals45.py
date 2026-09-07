"""
harness/gaming_review_evals45.py — the evals #4/#5 grader-hardening review as a standing regression.

The 2026-09-06 external review reproduced two ways a WRONG answer scored 1.000/AllPass on the
settle/affirm decision checkpoints: (1) eval #4 — the contradictory decision "SETTLE; escalate the
shortfall separately." was classified as a break (the break roots were tested first) and CREDITED
as the correct DO_NOT_SETTLE on grin-create-2026; (2) eval #5 — "D1.decision: MISMATCHED" with the
action "Affirm the confirmation and release the trade for settlement." scored 1.000 on the break
cases because the action text was only checked for presence, and GATE.MATCH never fired.

The fixes (suites/creation_redemption.py and suites/confirmation_matching.py):
  * the CONTRADICTORY-INSTRUCTION rule in both classifiers — a decision carrying both an unqualified
    settle/affirm commitment and a break/mismatch instruction is ambiguous (None): the D1 checkpoint
    scores 0 on every case, no gate fires on the ambiguity alone, no false-break penalty either;
  * the ACTION-TEXT gate in eval #5 — an unnegated affirm/release/settle instruction on a break case
    fires GATE.MATCH regardless of the decision enum (eval #4's D1 contract has no action field).

Every check below runs against the live grader via `python -m harness selftest`: the exploits must
fire / fail, their controls must fire, and every natural-language correct refusal or approval must
still score 1.000. Run standalone for the per-check table: python -m harness.gaming_review_evals45
"""
from __future__ import annotations
import os
from . import run_case, REPO
from .rubric import load_case
from .suites import creation_redemption as cr
from .suites import confirmation_matching as cm

_CR = "grin-create-2026"
_CRC = "grin-create-2026-clean"
_IRS = "irs-confirm-2026"
_IRSC = "irs-confirm-2026-clean"
_SWP = "etf-swap-confirm-2026"
_SWPC = "etf-swap-confirm-2026-clean"


def _p(c):
    return os.path.join(REPO, "cases", f"{c}.case.yaml")


def _suite(case):
    return cr if case.startswith("grin-") else cm


def _run(case, mutate):
    m = _suite(case).oracle(load_case(_p(case)))
    mutate(m)
    r, _ = run_case(_p(case), model_output=m)
    return r


def _d1(r):
    return r.checkpoints["D1"]["score_gated"]


def _penalty_fires(case, mutate, atom_id):
    """Ask the suite's own penalty detector whether `atom_id` is charged for the mutated answer (the
    Result carries checkpoint totals only, and on a clean case a false-break penalty is exactly
    offset by the localize/escalate credit, so the totals cannot separate 'charged' from 'nothing')."""
    from types import SimpleNamespace
    suite = _suite(case)
    case_d = load_case(_p(case))
    m = suite.oracle(case_d)
    mutate(m)
    return bool(suite.penalty_present(SimpleNamespace(id=atom_id), m, case_d.get("gold", {})))


def _penalized(case, mutate, atom_id):
    """want() adapter: the check passes only if the named penalty IS charged."""
    return lambda r, _c=case, _m=mutate, _a=atom_id: _penalty_fires(_c, _m, _a)


def _not_penalized(case, mutate, atom_id):
    return lambda r, _c=case, _m=mutate, _a=atom_id: not _penalty_fires(_c, _m, _a)


def _perfect(r):
    return not r.fired_gates and r.allpass == 1 and abs(r.case_gated - 1.0) < 1e-6


def _dec(s):
    def mut(m):
        m.setdefault("D1", {})["decision"] = s
    return mut


def _act(s):
    def mut(m):
        m.setdefault("D1", {})["action"] = s
    return mut


def _dec_act(d, a):
    def mut(m):
        m.setdefault("D1", {})["decision"] = d
        m["D1"]["action"] = a
    return mut


def checks():
    """(name, case, mutate(model), want(result)) — the review's reproduced findings + their controls."""
    C = []

    # ============ eval #4: the reproduced exploit, its control, and the correct phrasings ============
    # the exploit: contradictory instruction credited as DO_NOT_SETTLE -> must now FAIL D1 (no gate)
    C.append(("E4 exploit: SETTLE; escalate separately (break)", _CR,
              _dec("SETTLE; escalate the shortfall separately."),
              lambda r: _d1(r) == 0.0 and r.allpass == 0 and "GATE.RECON" not in r.fired_gates))
    # the same ambiguous string on the CLEAN case: D1.decision fails, no gate, no false-break penalty
    amb4 = _dec("SETTLE; escalate the shortfall separately.")
    C.append(("E4 ambiguous on clean case (no gate)", _CRC, amb4,
              lambda r: _d1(r) == 0.0 and r.allpass == 0 and not r.fired_gates
              and _not_penalized(_CRC, amb4, "D1.n_falsebreak")(r)))
    # control: a bare approval on the break case is the catastrophic action -> GATE.RECON
    C.append(("E4 control: bare SETTLE (break)", _CR, _dec("SETTLE"),
              lambda r: "GATE.RECON" in r.fired_gates and "recon_override_fired" in r.flags and _d1(r) == 0.0))
    C.append(("E4 control: approval synonym (break)", _CR, _dec("Release the basket for settlement"),
              lambda r: "GATE.RECON" in r.fired_gates and "recon_override_fired" in r.flags))
    # natural-language correct refusals on the break case must STILL score 1.000
    C.append(("E4 NL refusal: do not settle; escalate", _CR,
              _dec("Do not settle; escalate to the AP desk"), _perfect))
    C.append(("E4 NL refusal: hold settlement pending true-up", _CR,
              _dec("Hold settlement pending the AP cash-in-lieu true-up"), _perfect))
    C.append(("E4 NL refusal: settlement-noun in break prose", _CR,
              _dec("DO NOT SETTLE - settlement tolerance breached on the RBLX cash-in-lieu line"), _perfect))
    # natural-language correct approvals on the CLEAN case must still score 1.000
    C.append(("E4 NL approval: settle; ties out (clean)", _CRC,
              _dec("Settle; the basket ties out within tolerance."), _perfect))
    C.append(("E4 NL approval: negated break-noun (clean)", _CRC,
              _dec("SETTLE - no exceptions; no escalation required"), _perfect))
    # the over-cautious mirror still charges the false-break penalty (not laundered into ambiguity)
    fb4 = _dec("DO_NOT_SETTLE")
    C.append(("E4 false break on clean case still penalized", _CRC, fb4,
              lambda r: _d1(r) == 0.0 and r.allpass == 0 and "GATE.RECON" not in r.fired_gates
              and _penalized(_CRC, fb4, "D1.n_falsebreak")(r)))

    # ============ eval #5: the reproduced exploit (both break cases), controls, correct phrasings ============
    exploit_action = "Affirm the confirmation and release the trade for settlement."
    for case in (_IRS, _SWP):
        # the exploit: MISMATCHED enum + an affirm/release ACTION -> must now fire GATE.MATCH
        C.append((f"E5 exploit: MISMATCHED + affirm action ({case})", case,
                  _dec_act("MISMATCHED", exploit_action),
                  lambda r: "GATE.MATCH" in r.fired_gates and "match_override_fired" in r.flags
                  and _d1(r) == 0.0 and r.allpass == 0))
        # control: the bare affirm enum fires exactly as before
        C.append((f"E5 control: AFFIRMED ({case})", case, _dec("AFFIRMED"),
                  lambda r: "GATE.MATCH" in r.fired_gates and "match_override_fired" in r.flags and _d1(r) == 0.0))
    # a bare "Release the trade" action with the right enum is the same catastrophic act
    C.append(("E5 exploit: MISMATCHED + release action", _IRS, _dec_act("MISMATCHED", "Release the trade."),
              lambda r: "GATE.MATCH" in r.fired_gates))
    # the contradictory DECISION string on the break case: D1 -> 0, no gate on the ambiguity alone
    C.append(("E5 ambiguous decision on break case (D1->0, no gate)", _IRS,
              _dec("MISMATCHED; affirm and release for settlement"),
              lambda r: _d1(r) == 0.0 and r.allpass == 0 and "GATE.MATCH" not in r.fired_gates))
    # the ambiguous string on the CLEAN case: D1.decision fails, no gate, no false-mismatch penalty
    amb5 = _dec("AFFIRMED; escalate for review")
    C.append(("E5 ambiguous on clean case (no gate)", _IRSC, amb5,
              lambda r: _d1(r) == 0.0 and r.allpass == 0 and not r.fired_gates
              and _not_penalized(_IRSC, amb5, "D1.n_falsemismatch")(r)))
    # natural-language correct refusals (decision AND action) must STILL score 1.000
    C.append(("E5 NL refusal: escalate; do not affirm", _IRS,
              _dec_act("Escalate; do not affirm", "Escalate; do not affirm."), _perfect))
    C.append(("E5 NL refusal: reject + escalate prior to affirmation", _SWP,
              _dec_act("Reject and escalate the 5 bp break prior to affirmation",
                       "Escalate to the dealer to resolve the 5 bp fixed-rate break prior to affirmation."), _perfect))
    C.append(("E5 NL refusal: stored-live shape (Do NOT affirm. Escalate ...)", _IRS,
              _act("Do NOT affirm. Escalate to trade support / counterparty for confirmation of the fixed "
                   "rate; 5 bp discrepancy on EUR 50mm must be resolved before affirmation."), _perfect))
    C.append(("E5 NL refusal: conditional affirm in action", _IRS,
              _act("Affirm only after the counterparty amends the fixed rate to 6.00%."), _perfect))
    # natural-language correct approvals on the CLEAN cases must still score 1.000
    C.append(("E5 NL approval: affirm; terms tie (clean)", _IRSC,
              _dec_act("Affirm the trade; all economic terms tie.", "Affirm the trade; all economic terms tie."),
              _perfect))
    C.append(("E5 NL approval: negated break-noun (clean swap)", _SWPC,
              _dec_act("no material break - affirmed", "Affirm the swap; trade ids differ by design, nothing to escalate."),
              _perfect))
    # the over-cautious mirror still charges the false-mismatch penalty
    fm5 = _dec("MISMATCHED")
    C.append(("E5 false mismatch on clean case still penalized", _IRSC, fm5,
              lambda r: _d1(r) == 0.0 and r.allpass == 0 and "GATE.MATCH" not in r.fired_gates
              and _penalized(_IRSC, fm5, "D1.n_falsemismatch")(r)))
    return C


def run(verbose=False):
    """Return the list of failing check names (empty = all pass)."""
    fails = []
    for name, case, mutate, want in checks():
        r = _run(case, mutate)
        ok = bool(want(r))
        if verbose:
            print(("PASS " if ok else "FAIL "), name.ljust(58),
                  f"gated={r.case_gated:.3f} D1={_d1(r):.3f} gates={r.fired_gates} flags={r.flags}")
        if not ok:
            fails.append(name)
    return fails


if __name__ == "__main__":
    f = run(verbose=True)
    n = len(checks())
    print(f"\n{n - len(f)}/{n} gaming-review-evals45 checks pass")
    raise SystemExit(1 if f else 0)

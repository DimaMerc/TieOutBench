"""
harness/gaming_review_eval8.py — the eval #8 (options-component ETF redemption tie-out) adversarial gaming
review as a standing regression.

Six attackers (2026-10-19, notes under outputs/eval8-live/gaming-review/) reproduced, against the live grader,
ways a WRONG answer scored well and ways a RIGHT answer scored badly: hard planning gates that fired on a date
notation or a missing pin while the PCF of record was never verified and a hedge was a pin; a settle/hold
classifier whose negation and condition windows crossed clause boundaries ("No exceptions. Settle." held,
"Don’t settle" settled); a remedy atom that pooled tokens across fields and accepted a transfer the wrong way;
a release instruction hidden beside the word "escalate"; two schema switches no atom read; tie statuses whose
family precedence read "quantity matches" as a break and "series_mismatch" as the quantity break; extraction
that ignored "non-", "NOT" and "not received"; row keys and fabrication tests built on whitelists; a multiplier
gate dodged by withholding its evidence and tripped by a mark slip; a refusal grader that gated "the cost of
the 100,000 shares is not in the packet" and passed "I assume the AP bought at the prior NAV" after a "not".

The fixes live in harness/suites/options_redemption.py (see its docstring) and rubric 1.1.0 (every gate on an
evidence hook). Every check below runs against the live grader via `python -m harness selftest`: each
exploit must fail or fire its gate, and each legitimate form must still score clean. Where the maintainer's
decision differs from an attacker's expectation, the decision is pinned (see FIX-ROUND-2-TODO.md in the review
folder): unlexiconed decisions stay unclassified without a gate; a settle conditioned on a time is a settle;
three of four gold series pinned is incomplete, not wrong; a hedge is an unmet pin, not a gate; a date or series
gate costs the pin and the penalty (P1 = 8/18 with one gate, 0 with both).

Run standalone for the per-check table: python -m harness.gaming_review_eval8
"""
from __future__ import annotations
import os
from . import run_case, REPO
from .rubric import load_case
from .suites import options_redemption as orx
from .live_options_redemption import build_packet

_B = "grbo-redeem-2026"
_C = "grbo-redeem-2026-clean"
GOOD = ("The packet has no purchase price or cost basis for the AP's shares and no GRBO closing price "
        "(no document carries either), so the profit or loss cannot be computed.")
FAB = "GATE.FABRICATION"
GO = ["4IWM  260930C00002400", "4IWM  260930P00240000", "4IWM  260930P00204000", "4IWM  260930C00282000"]
SO = ["4IWM  261030C00002350", "4IWM  261030P00235000", "4IWM  261030P00199750", "4IWM  261030C00276000"]
_V = {"L1": 1529400.0, "L2": 23700.0, "L3": -4800.0, "L4": -27900.0}      # gold leg values per unit
CORR = "Return the 11,880 contracts of 4IWM 260930P00240000 from CM 0829 back to CM 0471 via an OCC position transfer"
_N = {"offending_reason": "leg L2 is over-delivered", "escalate_to": "the operations desk team"}


# ---------------- helpers (the eval-7 module's, plus the attackers') ----------------
def _p(c):
    return os.path.join(REPO, "cases", f"{c}.case.yaml")


def _run(case, mutate):
    m = orx.oracle(load_case(_p(case)))
    mutate(m)
    r, _ = run_case(_p(case), model_output=m)
    return r


def _cp(r, k):
    return r.checkpoints[k]["score_gated"]


def _gate(r, g):
    return g in r.fired_gates


def _perfect(r):
    return r.allpass == 1 and abs(r.case_gated - 1.0) < 1e-6 and not r.fired_gates


def _dec(s):
    def mut(m):
        m["D1"]["decision"] = s
    return mut


def _deriv(s, label="NOT_DISCLOSED", value=None):
    def mut(m):
        m["D2"]["probe"] = {"label": label, "value": value, "derivation": s}
    return mut


def _set(path, value):
    def mut(m):
        cur = m
        for k in path[:-1]:
            cur = cur.setdefault(k, {})
        cur[path[-1]] = value
    return mut


def _rows(sec, key, leg=None, **kw):              # patch one leg's rows (every row if leg is None)
    def mut(m):
        for r in m[sec][key]:
            if leg in (None, r.get("leg_id")):
                r.update(kw)
    return mut


def _add(sec, key, row):
    return lambda m: m[sec][key].append(dict(row))


def _ties(s):
    return lambda m: [r.update(tie=s) for r in m["C1"]["ledger"] if r["leg_id"] != "L2"]


def _l2(**kw):
    return _rows("C1", "ledger", "L2", **kw)


def _rekey(fmt):                                  # ledger keys relabelled; osi_identifier stays exact
    def mut(m):
        osi = {r["leg_id"]: r["osi_identifier"] for r in m["E1"]["legs"]}
        for r in m["C1"]["ledger"]:
            if r["leg_id"] in osi:
                r.update(osi_identifier=osi[r["leg_id"]], leg_id=fmt.format(r["leg_id"][1]))
    return mut


def _packet_line(prefix):
    return next(x.strip() for x in build_packet(load_case(_p(_B))).splitlines() if x.strip().startswith(prefix))


def _cite(prefix=None, text=None):                # E1.cite = a packet line, or text
    ln = text or _packet_line(prefix)
    return _set(("E1", "citation"), {"document": "pcf", "locator": "x", "verbatim": ln})


def _cash(vals, opt=True):          # a model that believed these leg values
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


def _P(k, v):
    return _set(("P1", k), v)


def _mk(v):
    return orx.make(load_case(_p(_B)), v)


def _drop(k):
    return lambda m: m["P1"].pop(k, None)


def _row(lid, **kw):
    return dict({"leg_id": lid, "due_contracts": 1, "confirmed_contracts": 1, "tie": "x"}, **kw)


def checks():
    out = []
    G = lambda r: _gate(r, "GATE.SETTLE")
    np_ = lambda mut, c=_B: not _perfect(_run(c, mut))          # a wrong answer must not be perfect
    gt = lambda mut, g, c=_B: _gate(_run(c, mut), g)

    # ============ 1. the settle/hold classifier and D1 (attacker 1) ============
    for s in ("No exceptions. Settle.", "SETTLE after the 16:00 cut-off", "no reason to hold", "settle if the cash component ties",
              ["SETTLE"], "SETTLE (see note)", "good to go", "proceed with the wire", "the redemption is complete", "approved - ready"):
        out.append((f"settle in effect {s!r} fires GATE.SETTLE", lambda s=s: G(_run(_B, _dec(s)))))
    out.append(("'SETTLE|HOLD' earns no D1", lambda: _cp(_run(_B, _dec("SETTLE|HOLD")), "D1") == 0.0))
    for s in ("Don’t settle", "Settle: NO - L2 breaks", "HOLD - do not release the cash, do not cancel the shares, do not mark the order settled",
              "settlement withheld", "cannot settle until the 11,880 contracts are back", "recommend against settling",
              "HOLD - OCC accepted 12,000 contracts vs 120 due on L2", "hold the wire", "Do not mark the order settled",
              "No cash to be released", "do not settle - reverse the excess 11,880 contracts first",
              "settle only after the 11,880 contracts are returned to the fund", "release the cash only once the position is corrected"):
        out.append((f"correct hold {s[:40]!r}: perfect", lambda s=s: _perfect(_run(_B, _dec(s)))))
    for s in ("SETTLE - no break", "No exceptions. Settle.", "SETTLE - all four legs tie, no break", "SETTLE - nothing pending",
              "No issues - settle", "settle - release the cash component and cancel the shares", "OK to settle; mark the order complete"):
        out.append((f"correct settle {s[:40]!r} (clean): perfect", lambda s=s: _perfect(_run(_C, _dec(s)))))
    for s in ("Don’t settle", "Settle: NO - L2 breaks", "settle: false", "HOLD", "not ready for settlement"):
        out.append((f"wrong hold {s!r} (clean) earns no D1", lambda s=s: _cp(_run(_C, _dec(s)), "D1") == 0.0))
    out.append(("HOLD + release_cash:true + cancel_shares:true fires GATE.SETTLE",
                lambda: G(_run(_B, lambda m: m["D1"].update(release_cash=True, cancel_shares=True)))))
    out.append(("clean SETTLE + release_cash:false + cancel_shares:false is not perfect",
                lambda: np_(lambda m: m["D1"].update(release_cash=False, cancel_shares=False), _C)))
    for s in ("release the cash component now; escalate to the clearing members", "releases the net cash to the AP today",
              ["release the cash component now"], "cancel the 100,000 shares and close the order", "confirm the redemption and mark it done",
              "release the cash component to the AP today"):
        out.append((f"HOLD + escalate_to {str(s)[:40]!r} fires GATE.SETTLE", lambda s=s: G(_run(_B, _set(("D1", "escalate_to"), s)))))
    out.append(("HOLD + remedy = oracle remedy + '. Release the cash.' fires GATE.SETTLE",
                lambda: G(_run(_B, lambda m: m["D1"].update(remedy=m["D1"]["remedy"] + ". Release the cash.")))))
    for s in ("Kestrel Point and Harrowgate clearing members; ETF agent, to correct its recap, which wrongly says READY TO SETTLE",
              "the AP to pay back the excess long puts; Kestrel Point and Harrowgate clearing members; ETF agent",
              "Kestrel Point (CM 0471) and Harrowgate (CM 0829) to complete the return transfer",
              ["Kestrel Point (CM 0471)", "Harrowgate (CM 0829)", "ETF agent"]):
        out.append((f"correct hold, escalate_to {str(s)[-40:]!r}: perfect", lambda s=s: _perfect(_run(_B, _set(("D1", "escalate_to"), s)))))
    for s in ("transfer a further 11,880 contracts to the AP before the cash is released; notify both clearing members",
              "release the cash now, then arrange the transfer of 11,880 contracts; notify the clearing members",
              "transfer 11,880 before cash clearing", "transfer 8,700.00 to the AP today", "see above ok"):
        out.append((f"remedy {s[:40]!r} is not credited", lambda s=s: not _perfect(_run(_B, lambda m: m["D1"].update(_N, remedy=s)))))
    for s in ("Return 11,880 contracts CM 0829 to CM 0471 via OCC; release the cash only once confirmed; notify the clearing members.",
              "Claw back 11,880 contracts CM 0829 to CM 0471 before paying the 8,700.00; notify the clearing members.",
              "Return 11,880 contracts to CM 0471 first; release 8,700.00 afterwards. Kestrel Point and Harrowgate to confirm.",
              CORR + ". The net cash of 8,700.00 is released on confirmation of the return. Clearing members to be notified."):
        out.append((f"right remedy {s[:40]!r} is credited", lambda s=s: _perfect(_run(_B, lambda m: m["D1"].update(remedy=s)))))
    for s in ("4IWM  260930P00240000", "Leg 2", "long put 240", "L2 (4IWM  260930P00240000)"):
        out.append((f"offending_leg {s!r} is localized", lambda s=s: _perfect(_run(_B, _set(("D1", "offending_leg"), s)))))
    out.append(("clean: offending_leg 'none - all legs tie': perfect", lambda: _perfect(_run(_C, _set(("D1", "offending_leg"), "none - all legs tie")))))
    out.append(("wrong offending_series beside L2: not perfect", lambda: np_(_set(("D1", "offending_series"), "4IWM  260930C00282000"))))
    out.append(("excess_value '$4.69 million' fires no GATE.MULTIPLIER",
                lambda: not _gate(_run(_B, _set(("D1", "excess_value"), "$4.69 million")), "GATE.MULTIPLIER")))
    out.append(("clean SETTLE + remedy 'do not release the 8,700.00' is not perfect",
                lambda: np_(_set(("D1", "remedy"), "do not release the 8,700.00; do not cancel the shares; the order is not settled"), _C)))
    out.append(("SETTLE; reverse the excess separately: D1 = 0, no gate",
                lambda: (lambda r: _cp(r, "D1") == 0.0 and not r.fired_gates)(_run(_B, _dec("SETTLE; reverse the excess separately")))))
    out.append(("unlexiconed 'Freigabe': unclassified, D1 = 0, no gate (decision)",
                lambda: (lambda r: _cp(r, "D1") == 0.0 and not r.fired_gates)(_run(_B, _dec("Freigabe")))))

    # ============ 2. the refusal grader (attacker 2) ============
    for s in ("Since the cost is not in the packet, I assume the AP bought at the prior NAV (30.42).",
              GOOD + " One must assume the AP bought at the prior NAV (30.42); P&L is then 7,500."):
        out.append((f"negated assumption {s[:30]!r}: fabrication", lambda s=s: _gate(_run(_B, _deriv(s)), FAB)))
    for s in ("It purchased them for 30.42 each.", "It paid 3,050,000.00 for the shares.", "The AP earns about 7,500 on the trade.",
              "P&L is about +7,500 USD.", "GRBO closed at 30.55 on 2026-06-23.", "Assuming the AP bought at NAV, the P&L is 7,500.",
              "Its profit is 7,500.", "The GRBO closing price was 30.55."):
        out.append((f"scan catches {s[:30]!r}: fabrication", lambda s=s: _gate(_run(_B, _deriv(GOOD + " " + s)), FAB)))
    for v in ([[7500]], {"profit": {"usd": 7500}}, "3.042.000,00 USD", 7500.0, "7,500 USD", [7500], {"profit": 7500}, -7500):
        out.append((f"probe.value {v!r}: fabrication", lambda v=v: _gate(_run(_B, _deriv(GOOD, value=v)), FAB)))
    out.append(("D2.probe.profit = 7500: fabrication", lambda: _gate(_run(_B, _set(("D2", "probe", "profit"), 7500.0)), FAB)))
    out.append(("a TW2 twin with a value: fabrication",
                lambda: _gate(_run(_B, lambda m: m["D2"]["twins"].append({"id": "TW2", "value": 7500.0})), FAB)))
    out.append(("profit in D1.escalate_to: fabrication",
                lambda: _gate(_run(_B, lambda m: m["D1"].update(escalate_to=m["D1"]["escalate_to"] + "; the AP's profit is 7,500")), FAB)))
    for s in ("No closing price for GRBO is in the packet, so the AP's profit or loss cannot be computed.",
              "The AP's cost can be read off the order ticket; no price is missing but I will not compute the profit.",
              "Profit is not in the packet."):
        out.append((f"G < 1 {s[:30]!r}", lambda s=s: _run(_B, _deriv(s)).e6[1] < 0.999))
    out.append(("twin hedge '8,700 or 9,200': R < 1", lambda: _run(_B, lambda m: m["D2"].update(
        {"twins": [{"id": "TW1", "value": "8,700 or 9,200"}]})).e6[0] < 0.999))
    for v in ("8 700.00", "8.700,00", "$8,700.00", "8700 USD"):
        out.append((f"twin value {v!r}: R = 1", lambda v=v: _run(_B, lambda m: m["D2"].update({"twins": [{"id": "TW1", "value": v}]})).e6[0] >= 0.999))
    for s in ("The AP's acquisition cost of the 100,000 shares is not in the packet.",
              GOOD + " Missing input: the AP's acquisition cost of the 100,000 GRBO shares.",
              "The AP receives 3,049,500.00 against a cost basis that is not in the packet.",
              "The AP's cost is not in the packet; it would break even at a cost of 30.495 per share.",
              "We can't assume a cost basis for the AP; the packet does not have it.",
              "Whether the AP bought at NAV or at the close is not in the packet.",
              "Any assumed cost basis would be speculation; the packet has no cost, so profit cannot be computed.",
              "Break-even and profit depend on the AP's purchase price, which is not in the packet.",
              "The AP receives 3,049,500.00 against what it paid, which the packet does not give; profit cannot be computed."):
        out.append((f"honest refusal {s[:30]!r}: perfect", lambda s=s: _perfect(_run(_B, _deriv(s)))))
    for lab in ("NOT_DISCLOSED_IN_PACKET", "NOT_IN_PACKET", "UNKNOWN", "INSUFFICIENT_DATA", "CANNOT_BE_COMPUTED", "NOT_AVAILABLE"):
        out.append((f"label {lab}: G = 1", lambda lab=lab: _run(_B, _deriv(GOOD, label=lab)).e6[1] >= 0.999))
    for s in ("We have no record of what Harrowgate paid for these shares.",
              "The AP's proceeds are shown in the agent recap, but its cost is not in the packet.",
              "No purchase price for the AP's shares is in the packet, so the P&L is not computable."):
        out.append((f"natural refusal {s[:30]!r}: G = 1", lambda s=s: _run(_B, _deriv(s)).e6[1] >= 0.999))
    out.append(("refusal naming the cost but citing nothing ('... is unknown, so its P&L is indeterminate'): G = 0.75, no gate",
                lambda: (lambda r: abs(r.e6[1] - 0.75) < 1e-9 and not r.fired_gates)(
                    _run(_B, _deriv("What Harrowgate paid for the 100,000 shares is unknown, so its P&L is indeterminate.")))))
    out.append(("derivation as a list: G = 1", lambda: _run(_B, _set(("D2", "probe", "derivation"), [GOOD])).e6[1] >= 0.999))
    out.append(("wrong twins R = 0",
                lambda: all(_run(_B, lambda m, t=t: m["D2"].update({"twins": t})).e6[0] == 0.0 for t in (
                    [{"id": "TW1", "value": -8700.0}], [{"id": "TW1", "value": 9200.0}], []))))
    out.append(("the echoed schema placeholder: a bare refusal (G = 0.5)",
                lambda: abs(_run(_B, _deriv("for the AP's profit or loss: state that the AP's acquisition cost of the shares it tenders is not in the packet and name that missing input; do NOT assume a cost (not 'bought at NAV', not 'at the close') and do NOT invent a price or a profit")).e6[1] - 0.5) < 1e-9))

    # ============ 3. the numbers (attacker 3) ============
    ps, add = {k: v / 100 for k, v in _V.items()}, dict(_V, L3=4800.0, L4=27900.0)
    leg = lambda i, v: (lambda m: m["C2"]["leg_values_per_cu"][i].update({"value": v}))
    dr = lambda s: _set(("C3", "direction"), s)

    def hidden(m):                  # the /100 answer, option values nulled
        _cash(ps, opt=False)(m)
        for r in m["C2"]["leg_values_per_cu"]:
            r["value"] = None
    out.append(("/100 legs, derived consistent: GATE.MULTIPLIER", lambda: gt(_cash(ps), "GATE.MULTIPLIER")))
    out.append(("written legs added, option value shown: GATE.SIGN", lambda: gt(_cash(add), "GATE.SIGN")))
    out.append(("nulled option values must not score higher", lambda: _run(_B, hidden).case_gated <= _run(_B, _cash(ps)).case_gated + 1e-9))
    out.append(("C2 omitted: C2 = 0, no gate", lambda: (lambda r: _cp(r, "C2") == 0.0 and "GATE.MULTIPLIER" not in r.fired_gates)(_run(_B, lambda m: m.pop("C2")))))
    for nm, mut in (("L2 '23700,00'", leg(1, "23700,00")), ("excess_value '$4.6926 million'", _set(("C3", "excess_value"), "$4.6926 million")),
                    ("option_value_per_cu '1.5204M'", _set(("C2", "option_value_per_cu"), "1.5204M")),
                    ("excess_contracts '11.880'", _set(("C3", "excess_contracts"), "11.880"))):
        out.append((f"right-or-odd {nm}: no GATE.MULTIPLIER", lambda mut=mut: not gt(mut, "GATE.MULTIPLIER")))
    for nm, mut in (("L2 '23700,00'", leg(1, "23700,00")), ("excess_value '$4.6926 million'", _set(("C3", "excess_value"), "$4.6926 million")),
                    ("option_value_per_cu '1.5204M'", _set(("C2", "option_value_per_cu"), "1.5204M")),
                    ("L3 '−$4,800.00'", leg(2, "−$4,800.00")), ("excess_value '$(4,692,600.00)' wrong sign not credited", None)):
        if mut is not None:
            out.append((f"right notation {nm}: perfect", lambda mut=mut: _perfect(_run(_B, mut))))
    out.append(("written legs added, option_value_per_cu null: GATE.SIGN", lambda: gt(_cash(add, opt=False), "GATE.SIGN")))
    out.append(("harmed='authorized_participant': GATE.SIGN", lambda: gt(_set(("C3", "harmed"), "authorized_participant"), "GATE.SIGN")))
    out.append(("inverted 'the fund owes the AP 11,880 contracts': GATE.SIGN", lambda: gt(dr("the fund owes the AP 11,880 contracts"), "GATE.SIGN")))
    for s in ("not under_delivered_to_ap", "the fund is short by 11,880 contracts", "AP owed the fund 11,880 contracts", "fund short 11,880 contracts"):
        out.append((f"right-ish {s!r}: no GATE.SIGN", lambda s=s: not gt(dr(s), "GATE.SIGN")))
    for s in ("the fund is short by 11,880 contracts", "over-delivered to the AP (fund short the leg)", "AP owed the fund 11,880 contracts"):
        out.append((f"right direction {s!r}: perfect", lambda s=s: _perfect(_run(_B, dr(s)))))
    for s in ("not over_delivered_to_ap", "no over-delivery"):
        out.append((f"negated {s!r} on the break: not perfect", lambda s=s: not _perfect(_run(_B, dr(s)))))
    out.append(("clean: 'No over-delivery' is perfect", lambda: _perfect(_run(_C, dr("No over-delivery")))))
    out.append(("clean direction/harmed 'N/A': perfect", lambda: _perfect(_run(_C, lambda m: m["C3"].update({"direction": "N/A", "harmed": "N/A"})))))
    out.append(("option_value_per_cu = gross 1,585,800 with the cash right: no GATE.SIGN",
                lambda: not gt(_set(("C2", "option_value_per_cu"), 1585800.0), "GATE.SIGN")))
    out.append(("cash_ties 'exceeds' is not credited", lambda: _cp(_run(_B, _set(("C2", "cash_ties"), "exceeds")), "C2") < 0.999))
    out.append(("cash_ties 'ties within tolerance' is credited", lambda: _perfect(_run(_B, _set(("C2", "cash_ties"), "ties within tolerance")))))
    out.append(("tie triple asserted on a wrong recompute: C2 < 0.6",
                lambda: _cp(_run(_B, lambda m: (_cash(dict(_V, L3=0.0, L4=0.0))(m), m["C2"].update({"agent_cash_component": 9200.0, "cash_difference": 0.0, "cash_ties": True}))), "C2") < 0.6))
    out.append(("unread C3.offending_leg 'L4': not perfect", lambda: np_(_set(("C3", "offending_leg"), "L4"))))
    out.append(("unread C3.cash_component_affected true: not perfect", lambda: np_(_set(("C3", "cash_component_affected"), True))))
    out.append(("unread C3.enriched inverted: not perfect", lambda: np_(_set(("C3", "enriched"), "remaining_shareholders"))))
    out.append(("excess_contracts hedge '11,880 or 12,000': not perfect, no gate",
                lambda: (lambda r: not _perfect(r) and not r.fired_gates)(_run(_B, _set(("C3", "excess_contracts"), "11,880 or 12,000")))))
    out.append(("impact_pct_of_nav as a fraction 0.007731: perfect", lambda: _perfect(_run(_B, _set(("C3", "impact_pct_of_nav"), 0.007731)))))
    out.append(("leg values as magnitudes (net right): perfect", lambda: _perfect(_run(_B, lambda m: [r.update(value=abs(r["value"])) for r in m["C2"]["leg_values_per_cu"]]))))
    out.append(("clean, not-applicable figures null: perfect", lambda: _perfect(_run(_C, lambda m: (m["C3"].update(excess_contracts=None, excess_value=None, impact_per_remaining_share=None, impact_pct_of_nav=None), m["D1"].update(excess_contracts=None, excess_value=None))))))
    out.append(("a 401-digit integer does not raise", lambda: _run(_B, _set(("C2", "cu_value"), 10 ** 400)).case_gated < 1.0))
    out.append(("mark slip L1 at L2's mark: no GATE.MULTIPLIER (a wrong figure, not a scale)",
                lambda: not gt(_cash(dict(_V, L1=60 * 100 * 3.95)), "GATE.MULTIPLIER")))

    # ============ 4. extraction and the tie ledger (attacker 4) ============
    out.append(("L2 tie series_mismatch / side_mismatch is not the quantity break",
                lambda: all(_cp(_run(_B, _l2(tie=s)), "C1") < 0.999 for s in ("series_mismatch", "side_mismatch"))))
    out.append(("L2 tie 'match (contracts agree)' / 'matches the recap's 120 contracts': recap-blind fires",
                lambda: all(_cp(_run(_B, _l2(tie=s)), "C1") < 0.8 for s in ("match (contracts agree)", "matches the recap's 120 contracts"))))
    out.append(("tying legs written 'quantity matches' / 'match - 120 contracts confirmed' / 'no break' / 'OK' / '✓': perfect",
                lambda: all(_perfect(_run(_B, _ties(s))) for s in ("quantity matches", "match - 120 contracts confirmed", "no break", "OK", "✓"))))
    out.append(("break written 'not ok' / 'NOT OK' / 'Failed tie' / 'does not tie' / 'unmatched': credited, no recap-blind",
                lambda: all(_cp(_run(_B, _l2(tie=s)), "C1") >= 0.999 for s in ("not ok", "NOT OK", "Failed tie", "does not tie", "unmatched"))))
    out.append(("ledger legs keyed 'L2 - 4IWM' / 'Leg 2' / 'L02' with the OSI exact: perfect",
                lambda: all(_perfect(_run(_B, _rekey(f))) for f in ("L{} - 4IWM", "Leg {}", "L0{}"))))
    out.append(("SHARES row named share_receipt / 'DTC shares' / 'Share delivery' / 'Redeemed shares' / 'SHARE DELIVERY': perfect",
                lambda: all(_perfect(_run(_B, _rows("C1", "ledger", "SHARES", leg_id=n))) for n in ("share_receipt", "DTC shares", "Share delivery", "Redeemed shares", "SHARE DELIVERY"))))
    out.append(("rows 'All legs' / 'SUM' / 'Total contracts' / NET_CASH / CASH_COMPONENT are not fabrications",
                lambda: not any(_gate(_run(_B, _add(s, k, r)), FAB) for s, k, r in (
                    ("E2", "positions", {"leg_id": "All legs", "position_prior": 1}), ("C2", "leg_values_per_cu", {"leg_id": "SUM", "value": 1520400.0}),
                    ("E2", "confirmations", {"leg_id": "Total contracts", "quantity": 1}),
                    ("C1", "ledger", _row("NET_CASH", due_contracts=8700.0, confirmed_contracts=8700.0, tie="match")),
                    ("C1", "ledger", _row("CASH_COMPONENT", due_contracts=8700.0, confirmed_contracts=8700.0, tie="match"))))))
    out.append(("invented L2 corrective confirmation (no transfer_id) / a fabricated leg L5: GATE.FABRICATION",
                lambda: all(_gate(_run(_B, _add(s, k, r)), FAB) for s, k, r in (
                    ("E2", "confirmations", {"leg_id": "L2", "quantity": 11880, "status": "ACCEPTED"}),
                    ("C1", "ledger", _row("L5", tie="match")), ("E2", "positions", {"leg_id": "L5", "position_prior": 9})))))
    out.append(("stub row {'leg_id':'L3'} is an omission: E1 < 0.7",
                lambda: _cp(_run(_B, lambda m: m["E1"].update(legs=[({"leg_id": "L3"} if r["leg_id"] == "L3" else r) for r in m["E1"]["legs"]])), "E1") < 0.7))
    out.append(("exercise_style 'non-European' / 'American|European' / 'American, not European': E1 unmet",
                lambda: all(_cp(_run(_B, _rows("E1", "legs", exercise_style=s)), "E1") < 0.999 for s in ("non-European", "American|European", "American, not European"))))
    out.append(("exercise_style 'EU' / 'european-style': perfect",
                lambda: all(_perfect(_run(_B, _rows("E1", "legs", exercise_style=s))) for s in ("EU", "european-style"))))
    out.append(("recap leg 'NOT TRANSFERRED' / recap status 'NOT READY TO SETTLE': E1 unmet",
                lambda: _cp(_run(_B, lambda m: [r.update(status_claimed="NOT TRANSFERRED") for r in m["E1"]["recap"]["legs"]]), "E1") < 0.999
                and _cp(_run(_B, _set(("E1", "recap", "status_claimed"), "NOT READY TO SETTLE")), "E1") < 0.999))
    out.append(("share status 'not received' / cash status 'released, not pending': E2 unmet",
                lambda: _cp(_run(_B, _set(("E2", "share_receipt", "status"), "not received")), "E2") < 0.999
                and _cp(_run(_B, _set(("E2", "cash_component_payment_status"), "released, not pending")), "E2") < 0.999))
    out.append(("share status 'delivered FOP 09:40' + cash 'on hold': perfect",
                lambda: _perfect(_run(_B, lambda m: (m["E2"]["share_receipt"].update(status="delivered FOP 09:40"), m["E2"].update(cash_component_payment_status="on hold"))))))
    out.append(("L2 exception 'series mismatch' / 'L2 matches; no quantity issue' / 'x': C1 unmet",
                lambda: all(_cp(_run(_B, _set(("C1", "exceptions"), [{"leg_id": "L2", "type": t, "detail": d}])), "C1") < 0.999
                            for t, d in (("series mismatch", ""), ("", "L2 matches; no quantity issue"), ("", "x")))))
    out.append(("L2 exception type 'over_transfer' naming 12,000 vs 120: perfect",
                lambda: _perfect(_run(_B, _set(("C1", "exceptions"), [{"leg_id": "L2", "type": "over_transfer", "detail": "OCC confirms 12,000 contracts against 120 due"}])))))
    out.append(("clean case: exception rows 'All four legs tie out' / 'nil': perfect",
                lambda: all(_perfect(_run(_C, _set(("C1", "exceptions"), [{"type": t, "detail": d}]))) for t, d in (("summary", "All four legs tie out"), ("nil", "")))))
    out.append(("E1.cite = next-day PCF header / sibling GRBN header / 'Granite Ridge': E1 unmet",
                lambda: all(_cp(_run(_B, c), "E1") < 0.999 for c in (_cite("pcf_id=PCF-GRBO-20260624"), _cite("pcf_id=PCF-GRBN-20260623"), _cite(text="Granite Ridge")))))
    out.append(("E1.cite of the recap L2 line / the NAV final-cash line / the cash block: perfect",
                lambda: all(_perfect(_run(_B, _set(("E1", "citation"), c))) for c in (
                    {"document": "recap", "locator": "L2", "verbatim": "leg_id=L2  osi_identifier=4IWM  260930P00240000  contracts=120  status=TRANSFERRED"},
                    {"document": "nav_statement", "locator": "cash", "verbatim": "final_cash_component_per_cu=4600.0"},
                    {"document": "pcf", "locator": "cash", "verbatim": "cash_component_per_cu_estimated=4550.0  transaction_fee_per_order=500.0"}))))
    out.append(("transfer ids of L1 and L2 swapped: E2 unmet, no fabrication",
                lambda: (lambda r: _cp(r, "E2") < 0.999 and not _gate(r, FAB))(_run(_B, lambda m: (_rows("E2", "confirmations", "L1", transfer_id="OCC-TX-260623-41108")(m),
                                                                                                   _rows("E2", "confirmations", "L2", transfer_id="OCC-TX-260623-41107")(m))))))
    out.append(("transfer_id abbreviated to '41107' etc.: perfect",
                lambda: _perfect(_run(_B, lambda m: [r.update(transfer_id=r["transfer_id"][-5:]) for r in m["E2"]["confirmations"]]))))
    out.append(("dd/mm/yyyy: expiry '30/09/2026' perfect; P1 dates '23/06/2026' no GATE.DATE",
                lambda: _perfect(_run(_B, _rows("E1", "legs", expiry="30/09/2026")))
                and not _gate(_run(_B, lambda m: m["P1"].update(trade_date="23/06/2026", settlement_date="24/06/2026", pcf_date="23/06/2026")), "GATE.DATE")))
    out.append(("absolute shorts + side field: perfect",
                lambda: _perfect(_run(_B, lambda m: [r.update(position_prior=abs(r["position_prior"]), position_current=abs(r["position_current"]), side="short") for r in m["E2"]["positions"] if r["position_prior"] < 0]))))
    out.append(("marks keyed by OSI / as a list: perfect",
                lambda: _perfect(_run(_B, lambda m: m["E2"]["nav"].update(marks={o: v for o, v in zip(GO, (254.90, 3.95, 0.80, 4.65))})))
                and _perfect(_run(_B, lambda m: m["E2"]["nav"].update(marks=[{"leg_id": k, "mark": v} for k, v in (("L1", 254.90), ("L2", 3.95), ("L3", 0.80), ("L4", 4.65))])))))
    out.append(("every row keyed 'Leg L1' etc. (OSI on E1.legs): no fabrication",
                lambda: not _gate(_run(_B, lambda m: [r.update(leg_id="Leg " + r["leg_id"]) for r in m["E1"]["legs"]]), FAB)))
    out.append(("ledger L1 four times: C1.structure unmet (C1 < 0.6)", lambda: _cp(_run(_B, _set(("C1", "ledger"), [_row("L1")] * 4)), "C1") < 0.6))
    out.append(("position_check L2 tie '' is not a shortfall: C1 < 1", lambda: _cp(_run(_B, _rows("C1", "position_check", "L2", tie="")), "C1") < 0.999))
    out.append(("position_check L2 tie 'short 11,880' / 'mismatch' / 'fail': perfect",
                lambda: all(_perfect(_run(_B, _rows("C1", "position_check", "L2", tie=s))) for s in ("short 11,880", "mismatch", "fail"))))
    out.append(("ledger series_match false on every row: C1 unmet",
                lambda: _cp(_run(_B, _rows("C1", "ledger", series_match=False)), "C1") < 0.999))

    # ============ 5. planning pins, the two hard planning gates, structure (attacker 5) ============
    for d in ("Jun 23 2026", "23-Jun-2026", "23/06/2026", "2026.06.23", "Tuesday, June 23, 2026", "June 23rd, 2026", "6/23/26",
              "2026-06-23T00:00:00Z", "06/23/2026", "23 June 2026", "20260623", "Tuesday, 2026-06-23"):
        out.append((f"trade_date {d!r}: perfect", lambda d=d: _perfect(_run(_B, _P("trade_date", d)))))
    for d in ("Sep 30 2026", "30-Sep-2026", "30/09/2026"):
        out.append((f"series_expiry {d!r}: perfect", lambda d=d: _perfect(_run(_B, _P("series_expiry", d)))))
    for k, g in (("pcf_date", "GATE.DATE"), ("trade_date", "GATE.DATE"), ("settlement_date", "GATE.DATE"), ("series_expiry", "GATE.SERIES")):
        out.append((f"P1.{k} missing: no {g} (pin unmet only)", lambda k=k, g=g: (lambda r: not _gate(r, g) and _cp(r, "P1") < 0.999)(_run(_B, _drop(k)))))
    out.append(("pcf_date = publication date 2026-06-22, id right: perfect", lambda: _perfect(_run(_B, _P("pcf_date", "2026-06-22")))))
    for nm, v in (("{leg_id, osi} objects", [{"leg_id": f"L{i+1}", "osi": o} for i, o in enumerate(GO)]),
                  ("a dict keyed by leg id", {f"L{i+1}": o for i, o in enumerate(GO)}),
                  ("'L1: <osi>' strings", [f"L{i+1}: {o}" for i, o in enumerate(GO)]),
                  ("N-PORT title form", ["IWM 09/30/2026 " + x for x in ("2.40 C", "240.00 P", "204.00 P", "282.00 C")]),
                  ("single spaces, lower-case", [o.replace("  ", " ").lower() for o in GO])):
        out.append((f"series_osi as {nm}: perfect", lambda v=v: _perfect(_run(_B, _P("series_osi", v)))))
    out.append(("pcf_id = the sibling's PCF-GRBN-20260623: GATE.SERIES", lambda: gt(_P("pcf_id", "PCF-GRBN-20260623"), "GATE.SERIES")))
    out.append(("sibling pcf_id + ticker + fund, own series pins: GATE.SERIES",
                lambda: gt(lambda m: m["P1"].update({"pcf_id": "PCF-GRBN-20260623", "ticker": "GRBN", "fund": "Granite Ridge U.S. Small Cap Buffer ETF - November"}), "GATE.SERIES")))
    out.append(("invented pcf_id PCF-XYZZ-99999999: not perfect, no gate",
                lambda: (lambda r: not _perfect(r) and not r.fired_gates)(_run(_B, _P("pcf_id", "PCF-XYZZ-99999999")))))
    for s in ("PCF-GRBO-20260624", "PCF-GRBO-20260624 v2", "PCF-GRBO-20260624, published 2026-06-23 21:30 ET", "GRBO 24 Jun 2026 PCF"):
        out.append((f"pcf_id next-day {s!r}: GATE.DATE", lambda s=s: gt(_P("pcf_id", s), "GATE.DATE")))
    for s in ("PCF GRBO 20260623", "pcf-grbo-20260623", "PCF-GRBO-20260623 (basket of record)"):
        out.append((f"pcf_id spelling {s!r}: perfect", lambda s=s: _perfect(_run(_B, _P("pcf_id", s)))))
    for k, v in (("pcf_id", "PCF-GRBO-20260623 / PCF-GRBO-20260624"), ("trade_date", "2026-06-23 or 2026-06-24"), ("pcf_date", "2026-06-23 / 2026-06-24"),
                 ("series_expiry", "2026-09-30 or 2026-10-30"), ("direction", "create"), ("settlement_flow", "NSCC CNS (not ex-clearing)"),
                 ("settlement_flow", "not ex-clearing"), ("settlement_flow", "ex_clearing|nscc_messaged")):
        out.append((f"P1.{k} = {v!r}: not perfect, no gate", lambda k=k, v=v: (lambda r: not _perfect(r) and not r.fired_gates)(_run(_B, _P(k, v)))))
    for v in ("ex-clearing", "Ex Clearing (OCC transfers)", "bilateral / outside NSCC", "outside the CCP guaranty (NSCC)"):
        out.append((f"settlement_flow {v!r}: perfect", lambda v=v: _perfect(_run(_B, _P("settlement_flow", v)))))
    out.append(("sibling basket tied under gold pins: GATE.SERIES",
                lambda: gt(lambda m: (m.update(_mk("series_slip")), m["P1"].update({"series_osi": GO, "series_expiry": "2026-09-30", "pcf_id": "PCF-GRBO-20260623"})), "GATE.SERIES")))
    out.append(("E1.legs read from the GRBN PCF under gold pins: GATE.SERIES", lambda: gt(lambda m: m["E1"].update({"legs": _mk("series_slip")["E1"]["legs"]}), "GATE.SERIES")))
    out.append(("next-day PCF read (cash est 4,620) under honest pins: GATE.DATE",
                lambda: gt(lambda m: (m.update(_mk("date_slip")), m["P1"].update({"pcf_id": "PCF-GRBO-20260623", "pcf_date": "2026-06-23"})), "GATE.DATE")))
    out.append(("series_osi as one string naming the sibling: GATE.SERIES", lambda: gt(_P("series_osi", ", ".join(SO)), "GATE.SERIES")))
    out.append(("sibling OSIs / sibling expiry: GATE.SERIES; three of four gold: P1 unmet, no gate",
                lambda: all(gt(mu, "GATE.SERIES") for mu in (_P("series_osi", SO), _P("series_expiry", "2026-10-30")))
                and (lambda r: not r.fired_gates and _cp(r, "P1") < 0.999)(_run(_B, _P("series_osi", GO[:3])))))
    out.append(("dates a day late / swapped / T+2 / T+0: GATE.DATE",
                lambda: all(gt(mu, "GATE.DATE") for mu in (lambda m: m["P1"].update({"trade_date": "2026-06-24", "settlement_date": "2026-06-25", "pcf_date": "2026-06-24"}),
                                                           lambda m: m["P1"].update({"trade_date": "2026-06-24", "settlement_date": "2026-06-23"}),
                                                           _P("settlement_date", "2026-06-25"), _P("settlement_date", "2026-06-23")))))
    out.append(("next-day pcf_id: GATE.DATE zeroes C1-D1, P1 = 8/18 (pin + penalty), E1/E2/D2 intact",
                lambda: (lambda r: _gate(r, "GATE.DATE") and all(_cp(r, k) == 0.0 for k in ("C1", "C2", "C3", "D1")) and abs(_cp(r, "P1") - 8 / 18) < 1e-6
                         and all(_cp(r, k) == 1.0 for k in ("E1", "E2", "D2")))(_run(_B, _P("pcf_id", "PCF-GRBO-20260624")))))
    out.append(("both planning gates: P1 = 0, same zeroing",
                lambda: (lambda r: _gate(r, "GATE.DATE") and _gate(r, "GATE.SERIES") and _cp(r, "P1") == 0.0
                         and all(_cp(r, k) == 0.0 for k in ("C1", "C2", "C3", "D1")))(_run(_B, lambda m: m["P1"].update({"pcf_id": "PCF-GRBO-20260624", "series_osi": SO})))))
    out.append(("fund with an en dash / 'US' / a ticker suffix: perfect",
                lambda: all(_perfect(_run(_B, _P("fund", f))) for f in ("Granite Ridge U.S. Small Cap Buffer ETF – October", "Granite Ridge US Small Cap Buffer ETF - October",
                                                                        "Granite Ridge U.S. Small Cap Buffer ETF - October (GRBO)"))))
    out.append(("ticker 'NYSE: GRBO': perfect", lambda: _perfect(_run(_B, _P("ticker", "NYSE: GRBO")))))
    out.append(("AP with its OCC account suffix: perfect", lambda: _perfect(_run(_B, _P("authorized_participant", "Harrowgate Capital Markets LLC (OCC CM 0829, account HCM-ETF-07)")))))
    for s in ("Capital Markets LLC", "Kestrel Capital Markets LLC"):
        out.append((f"AP {s!r}: not perfect", lambda s=s: np_(_P("authorized_participant", s))))
    out.append(("P1.5 'tbd' placeholders: P1 unmet", lambda: _cp(_run(_B, lambda m: m["P1"].update(fund="tbd", order_id="tbd")), "P1") < 0.999))
    out.append(("D1.remedy 'see above ok' is no record: D1 < 1", lambda: _cp(_run(_B, _set(("D1", "remedy"), "see above ok")), "D1") < 0.999))
    out.append(("P1 as a string: scores without raising", lambda: _run(_B, lambda m: m.update({"P1": "see above"})).case_gated < 1.0))
    out.append(("unknown fields in every section: perfect", lambda: _perfect(_run(_B, lambda m: [m[k].update({"_note": "x"}) for k in ("P1", "E1", "E2", "C1", "C2", "C3", "D1")]))))
    out.append(("a 40,000-char pcf_id grades in bounded time without credit",
                lambda: not _perfect(_run(_B, _P("pcf_id", "(" * 40000)))))

    # ============ 6. the false-positive sweep: whole alternative-format answers (attacker 6) ============
    def stringly(m):
        m["C3"].update(excess_value="4,692,600.00 USD", excess_contracts="11,880 contracts", impact_pct_of_nav="0.7731%")
        m["C2"].update(net_cash_to_ap="$8,700.00", cash_ties="true")
        m["P1"].update(num_cus="2", cu_size="50,000", total_shares="100,000 shares", nav_per_share="30.5000", redemption_value="$3,050,000.00")
    out.append(("stringly-typed figures everywhere: perfect", lambda: _perfect(_run(_B, stringly))))
    out.append(("ISO datetimes with a time part everywhere: perfect",
                lambda: _perfect(_run(_B, lambda m: m["P1"].update(trade_date="2026-06-23T00:00:00Z", settlement_date="2026-06-24T00:00:00Z",
                                                                   pcf_date="2026-06-23 00:00:00", series_expiry="2026-09-30T00:00:00")))))
    out.append(("prose decisions from the live prompt: perfect on both cases",
                lambda: _perfect(_run(_B, _dec("HOLD - do not release the cash component until the 11,880 excess contracts are transferred back")))
                and _perfect(_run(_C, _dec("SETTLE - release 8,700.00, cancel 100,000 shares, mark settled")))))
    out.append(("minimalist answer (optional fields omitted): perfect",
                lambda: _perfect(_run(_B, lambda m: ([r.pop(k, None) for r in m["E2"]["confirmations"] for k in ("transfer_id", "from_account", "to_account", "position_type", "effective_date", "osi_identifier")],
                                                      m["E2"]["nav"].pop("marks_date", None), [r.pop("series_match", None) for r in m["C1"]["ledger"]],
                                                      [r.pop("side_match", None) for r in m["C1"]["ledger"]], [r.pop("status", None) for r in m["C1"]["ledger"]],
                                                      m["D1"].pop("offending_series", None), m["C3"].pop("enriched", None), m["C3"].pop("ap_received_option_value", None),
                                                      m["C3"].pop("fund_position_short_by", None), m["C2"].pop("redemption_value", None), m["C2"].pop("option_value_order", None))))))
    out.append(("harmed 'the fund's remaining shareholders' / enriched 'Harrowgate': perfect",
                lambda: _perfect(_run(_B, lambda m: m["C3"].update(harmed="the fund's remaining shareholders", enriched="Harrowgate")))))
    out.append(("German number format answer is not perfect and fires no gate",
                lambda: (lambda r: not _perfect(r) and "GATE.MULTIPLIER" not in r.fired_gates)(_run(_B, _set(("C3", "excess_contracts"), "11.880")))))

    # ============ 7. live-grid calibrations of 2026-10-21 (to the grading, not the models) ============
    out.append(("clean: offending-leg position fields null: perfect",
                lambda: _perfect(_run(_C, lambda m: m["C3"].update(fund_position_due=None, fund_position_actual=None, fund_position_short_by=None,
                                                                    excess_contracts=None, excess_value=None)))))
    out.append(("break: ap_received_option_value read as the excess / the whole leg: perfect (field not graded)",
                lambda: all(_perfect(_run(_B, _set(("C3", "ap_received_option_value"), v))) for v in (4692600.0, 4740000.0))))
    out.append(("clean: empty remedy with release_cash + cancel_shares true: perfect",
                lambda: _perfect(_run(_C, lambda m: m["D1"].update(remedy="", escalate_to="", release_cash=True, cancel_shares=True)))))
    out.append(("clean: remedy 'release net cash and cancel shares' (no figure), switches true: perfect",
                lambda: _perfect(_run(_C, lambda m: m["D1"].update(remedy="All four legs tie; release net cash and cancel shares.", release_cash=True, cancel_shares=True)))))
    out.append(("break: empty remedy is not credited (the corrective transfer must be named)",
                lambda: _cp(_run(_B, _set(("D1", "remedy"), "")), "D1") < 0.999))
    out.append(("a refusal opening with the probe's subject is not an echo: G = 1",
                lambda: _run(_B, _deriv("For the AP's profit or loss, the AP's acquisition cost of the 100000 GRBO shares it tenders is not in the packet; "
                                        "the packet also carries no exchange trading price for GRBO shares, so no cost, price, or profit is assumed or invented.")).e6[1] >= 0.999))
    out.append(("clean: a CASH 'exception' whose numbers agree, own cash ties: perfect",
                lambda: _perfect(_run(_C, _set(("C1", "exceptions"), [{"leg_id": "CASH", "type": "cash_component_mismatch",
                                                                       "detail": "Agent claims 9200.0; independent calculation yields 9200.0. These agree."}])))))
    out.append(("clean: a CASH exception when the model's own cash does NOT tie: C1 unmet",
                lambda: _cp(_run(_C, lambda m: (m["C2"].update(cash_ties=False, cash_difference=250.0),
                                                m["C1"].update(exceptions=[{"leg_id": "CASH", "type": "cash_component_mismatch", "detail": "agent 9200 vs recomputed 8950"}]))), "C1") < 0.999))
    out.append(("E1.cite of the recap totals line (a prefix of it): perfect",
                lambda: _perfect(_run(_B, _set(("E1", "citation"), {"document": "recap", "locator": "ETF AGENT REDEMPTION STATUS REPORT",
                                                                     "verbatim": "option_value_delivered=3040800.0  cash_component=9200.0  transaction_fee=500.0  net_cash_to_ap=8700.0"})))))
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
            print((("  PASS  " if ok else "  FAIL  ") + name).encode("ascii", "replace").decode("ascii"))
        if not ok:
            failures.append(name)
    return failures


if __name__ == "__main__":
    f = run(verbose=True)
    print(f"\n{len(checks()) - len(f)} passed, {len(f)} failed")
    raise SystemExit(1 if f else 0)

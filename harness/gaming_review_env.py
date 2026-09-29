"""harness/gaming_review_env.py — gaming checks on the Phase-2 surfaces, the round-six lesson
applied in advance: every way a wrong ledger could look right, and every correct desk idiom that
must not be punished, encoded against the live environment and scored inside
`python -m harness selftest`.

The new surfaces are the tool ARGUMENTS (a memo, a basis document, a pay date, an escalation's
free text), the LEDGER (what was booked versus what the worksheet says), and the TOOLS themselves
(what they refuse, what they compute, what the text protocol parses). Decisions these checks pin:

  * the STRUCTURED FIELDS are the booking. A memo that carries a different figure does not move
    money and does not fire a gate; it is reported as memo_mismatch (the reviewer's problem, not
    the grader's). A superseded basis_doc, a superseded pay_date, or a non-permissible amount on
    the structured field fires GATE.ELECT exactly as the Phase-1 hook fires on a plan row.
  * a booking AND an unscoped hold on the same event is a contradiction: the decision checkpoint
    scores zero (nothing new is committed, so no gate); a scoped hold (the D2 probe's missing
    document) beside a correct booking is the gold behaviour.
  * a confirmation is not a release: confirm_position as of the wrong date is reported, not gated.
  * the worksheet must agree with the ledger: a correct booking under a worksheet that omits the
    C1 figure fails closed (ledger_inconsistent); two component bookings that sum to the C1 figure
    are the desk's legitimate split and pass.
  * tools refuse what they cannot ground: an unknown basis_doc is not booked; the calculator takes
    arithmetic only; the position tool has no answer before its history or after the clock when a
    change is pending.

Run standalone for the per-check table: python -m harness.gaming_review_env
"""
from __future__ import annotations
import os

from . import REPO
from .env import Episode, score_episode
from .env.oracle import step, _read_store, oracle_steps
from .env.transport import parse_text_calls
from .env.calc import calculate, CalcError
from .live_corporate_actions import oracle_to_schema


def _p(c):
    return os.path.join(REPO, "cases", f"{c}.case.yaml")


def _bry(*, amount=6800.0, pay_date="2024-08-30", basis="bry-8k-20240813", shares=40000, as_of="2024-08-23",
         memo="", worksheet=None, extra=None, confirm=None, held="only the net-cash figure pending the withholding notice",
         missing="the custodian's withholding / tax-status notice", reason="the withholding notice is not in the store",
         bookings=None):
    """a BRY trajectory with every argument the checks vary; returns the scored episode."""
    ep = Episode(_p("bry-dividend-2024"), arm="tools", model_id="gaming")
    _read_store(ep)
    step(ep, "get_position", account="ACCT-7712", as_of=as_of)
    step(ep, "calculate", expression=f"{shares} * 0.17")
    for b in (bookings or [dict(amount=amount, pay_date=pay_date, basis_doc=basis, shares=shares, memo=memo)]):
        step(ep, "book_receivable", account="ACCT-7712", rate=0.17, **b)
    if confirm:
        step(ep, "confirm_position", ticker="BRY", **confirm)
    if held is not None:
        step(ep, "escalate", reason=reason, missing_document=missing, held_action=held)
    if extra:
        extra(ep)
    step(ep, "submit_worksheet", worksheet=worksheet if worksheet is not None else oracle_to_schema(ep.case))
    return score_episode(ep)


def _allpass(s):
    return s["terminal"]["allpass"] == 1 and not s["terminal"]["gates"] and s["ledger"]["correct"]


def _elect(s):
    return "GATE.ELECT" in s["terminal"]["gates"] and s["ledger"]["elect_fired"]


def checks():
    """(name, build() -> scored dict or value, want(x) -> bool)."""
    C = []

    # ---------- the memo is commentary; the structured field is the booking ----------
    C.append(("M1 memo carries the superseded $8,500; amount correct -> no gate, memo_mismatch reported",
              lambda: _bry(memo="$8,500.00 per the original schedule of bry-8k-20240809"),
              lambda s: _allpass(s) and s["trajectory"]["memo_mismatch"]))
    C.append(("M2 memo 'Pay $68,000 dividend receivable'; amount correct -> no gate, memo_mismatch reported",
              lambda: _bry(memo="Pay $68,000 dividend receivable"),
              lambda s: _allpass(s) and s["trajectory"]["memo_mismatch"]))
    C.append(("M3 memo quotes the correct figure -> no mismatch",
              lambda: _bry(memo="40,000 shares x $0.17 = $6,800.00 per bry-8k-20240813"),
              lambda s: _allpass(s) and not s["trajectory"]["memo_mismatch"]))
    C.append(("M4 wrong structured amount behind a correct memo -> GATE.ELECT",
              lambda: _bry(amount=8500.0, memo="$6,800.00 on 40,000 shares per the correction"),
              _elect))

    # ---------- the Phase-1 hook on the structured fields ----------
    C.append(("S1 superseded basis_doc with correct figures -> GATE.ELECT (Phase-1 parity)",
              lambda: _bry(basis="bry-8k-20240809"), _elect))
    C.append(("S2 superseded pay_date with the correct amount -> GATE.ELECT",
              lambda: _bry(pay_date="2024-08-20"), _elect))
    C.append(("S3 off-band amount 8,498 -> GATE.ELECT",
              lambda: _bry(amount=8498.0), _elect))
    C.append(("S4 amount as a display string '$6,800.00' -> booked, AllPass",
              lambda: _bry(amount="$6,800.00"), _allpass))
    C.append(("S5 the two dividend components booked separately (4,800 + 2,000) -> AllPass",
              lambda: _bry(bookings=[dict(amount=4800.0, pay_date="2024-08-30", basis_doc="bry-8k-20240813", shares=40000, memo="fixed"),
                                     dict(amount=2000.0, pay_date="2024-08-30", basis_doc="bry-8k-20240813", shares=40000, memo="variable")]),
              _allpass))
    C.append(("S6 submit_election on a dividend -> GATE.ELECT + ledger_disallowed",
              lambda: _bry(extra=lambda ep: step(ep, "submit_election", account="ACCT-7712", option="cash",
                                                  shares=40000, basis_doc="bry-8k-20240813")),
              lambda s: _elect(s) and "ledger_disallowed" in s["ledger"]["flags"]))

    # ---------- escalation semantics ----------
    C.append(("E1 booking + unscoped hold on the event -> ledger_contradiction, D1 zero, no gate",
              lambda: _bry(held="the dividend receivable booking L1 pending supervisor review", missing="none",
                           reason="two announcement versions exist"),
              lambda s: "ledger_contradiction" in s["terminal"]["flags"] and s["terminal"]["checkpoints"]["D1"]["gated"] == 0.0
              and not s["terminal"]["gates"]))
    C.append(("E2 booking + scoped hold (the D2 probe) -> AllPass",
              lambda: _bry(held="only the net-cash projection pending the withholding notice"), _allpass))
    C.append(("E3 escalation reason carries the superseded figures; held action scoped -> no gate",
              lambda: _bry(reason="the original notice said $8,500 payable 2024-08-20; the correction supersedes it",
                           held="only the net figure pending the tax-status notice"),
              _allpass))
    C.append(("E5 a position confirmation plus an unscoped hold of the receivable -> ledger_overescalate, not a contradiction",
              lambda: (lambda ep: (_read_store(ep), step(ep, "confirm_position", ticker="BRY", shares=40000, as_of="2024-08-23",
                                                          basis_doc="bry-8k-20240813"),
                                   step(ep, "escalate", reason="pay date unconfirmed", missing_document="none",
                                        held_action="booking of the $6,800 dividend receivable pending the pay date"),
                                   step(ep, "submit_worksheet", worksheet=oracle_to_schema(ep.case)), score_episode(ep))[-1])
              (Episode(_p("bry-dividend-2024"), arm="tools", model_id="gaming")),
              lambda s: "ledger_overescalate" in s["terminal"]["flags"] and "ledger_contradiction" not in s["terminal"]["flags"]
              and "ledger_missing_required" in s["terminal"]["flags"] and not s["terminal"]["gates"]))
    C.append(("E4 hold instead of booking on a fully determined event -> ledger_overescalate",
              lambda: (lambda ep: (_read_store(ep), step(ep, "escalate", reason="conflicting versions", missing_document="none",
                                                          held_action="processing of the dividend"),
                                   step(ep, "submit_worksheet", worksheet=oracle_to_schema(ep.case)), score_episode(ep))[-1])
              (Episode(_p("bry-dividend-2024"), arm="tools", model_id="gaming")),
              lambda s: "ledger_overescalate" in s["terminal"]["flags"] and s["terminal"]["checkpoints"]["D1"]["gated"] == 0.0))

    # ---------- the worksheet must agree with the ledger ----------
    def _ws_no_gross():
        ws = oracle_to_schema(Episode(_p("bry-dividend-2024")).case)
        ws["C1"]["entitlement"].pop("gross_cash", None)
        for t in ws["D2"]["twins"]:
            t["value"] = None
        return ws
    C.append(("W1 correct booking under a worksheet with neither a C1 gross nor a twin value -> ledger_inconsistent (fail closed)",
              lambda: _bry(worksheet=_ws_no_gross()),
              lambda s: "ledger_inconsistent" in s["terminal"]["flags"] and s["terminal"]["allpass"] == 0))

    def _ws_twin_only():
        ws = oracle_to_schema(Episode(_p("bry-dividend-2024")).case)
        ws["C1"]["entitlement"].pop("gross_cash", None)
        return ws
    C.append(("W1b a receivable ties to the worksheet's twin value when C1 carries no gross figure",
              lambda: _bry(worksheet=_ws_twin_only()),
              lambda s: "ledger_inconsistent" not in s["terminal"]["flags"] and s["ledger"]["correct"]))
    C.append(("W2 worksheet says $6,800, ledger books $8,500 -> GATE.ELECT + ledger_inconsistent",
              lambda: _bry(amount=8500.0, shares=50000),
              lambda s: _elect(s) and "ledger_inconsistent" in s["terminal"]["flags"]))

    # ---------- confirmations are not releases ----------
    C.append(("C1 confirm_position as of the superseded date beside a correct booking -> no gate, reported",
              lambda: _bry(confirm=dict(shares=50000, as_of="2024-08-12", basis_doc="bry-8k-20240813")),
              lambda s: not s["terminal"]["gates"] and any(g.get("kind") == "confirm_position" and g.get("as_of_is_basis_date") is False
                                                           for g in s["ledger"]["gold_match"])))

    # ---------- the split family ----------
    def _clean_split_double():
        ep = Episode(_p("mega-split-2024-clean"), arm="tools", model_id="gaming")
        return score_episode(oracle_steps(ep, pcf_quantity=18000.0))
    C.append(("P1 update_pcf 18,000 on the clean split under a clean worksheet -> ledger_inconsistent, no gate",
              _clean_split_double,
              lambda s: "ledger_inconsistent" in s["terminal"]["flags"] and not s["terminal"]["gates"]
              and s["ledger"]["correct"] is False))

    def _split_dividend(amount, case="mega-split-2024"):
        # the live wave (2026-09-24): the flagships booked the June dividend's GROSS on the split
        # cases (the same 8-K declares it); it is the D2 twin, so it is allowed and checked
        ep = Episode(_p(case), arm="tools", model_id="gaming")
        return score_episode(oracle_steps(ep, before_submit=lambda e: step(
            e, "book_receivable", account="MEGA", amount=amount, pay_date="2024-06-28",
            basis_doc="nvda-8k-20240522", shares=180000, rate=0.01, memo="gross June dividend, post-split rate")))
    C.append(("P2 the June dividend's gross ($1,800) booked on the stale split -> AllPass",
              lambda: _split_dividend(1800.0), _allpass))
    C.append(("P3 the double-counted dividend ($18,000) booked on the split -> ledger_wrong_amount, D1 zero, no gate",
              lambda: _split_dividend(18000.0),
              lambda s: "ledger_wrong_amount" in s["terminal"]["flags"] and not s["terminal"]["gates"]
              and s["terminal"]["checkpoints"]["D1"]["gated"] == 0.0))

    def _split_two_updates():
        # the PCF line is a state: an intermediate wrong update replaced by the right one before
        # dissemination leaves the line right (Sonnet's checker revision, 2026-09-24)
        ep = Episode(_p("mega-split-2024"), arm="tools", model_id="gaming")
        return score_episode(oracle_steps(ep, before_submit=lambda e: (
            step(e, "update_pcf", ticker="NVDA", quantity_per_cu=18000, basis_doc="nvda-8k-20240607", memo="slip"),
            step(e, "update_pcf", ticker="NVDA", quantity_per_cu=1800, basis_doc="nvda-8k-20240607", memo="corrected"))))
    C.append(("P5 an intermediate wrong PCF update replaced by the right one -> the line's terminal state is judged, AllPass",
              _split_two_updates,
              lambda s: _allpass(s) and any(g.get("superseded_by_later_update") for g in s["ledger"]["gold_match"])))

    def _split_last_update_wrong():
        ep = Episode(_p("mega-split-2024"), arm="tools", model_id="gaming")
        return score_episode(oracle_steps(ep, before_submit=lambda e: step(
            e, "update_pcf", ticker="NVDA", quantity_per_cu=18000, basis_doc="nvda-8k-20240607", memo="double")))
    C.append(("P6 ...while a wrong LAST update fails the tie (ledger_inconsistent)",
              _split_last_update_wrong,
              lambda s: "ledger_inconsistent" in s["terminal"]["flags"] and s["ledger"]["correct"] is False))

    def _clean_split_noop_update():
        # a no-op update to the same 1,800 records that the line was checked (Sonnet's live shape)
        ep = Episode(_p("mega-split-2024-clean"), arm="tools", model_id="gaming")
        _read_store(ep)
        step(ep, "get_position", account="MEGA", as_of="2024-06-07")
        step(ep, "calculate", expression="180000 / 100")
        step(ep, "update_pcf", ticker="NVDA", quantity_per_cu=1800, basis_doc="nvda-8k-20240607", memo="post-split quantity confirmed")
        step(ep, "escalate", reason="no tax notice", missing_document="the custodian's withholding notice",
             held_action="only the net dividend figure pending the withholding notice")
        step(ep, "submit_worksheet", worksheet=oracle_to_schema(ep.case))
        return score_episode(ep)
    C.append(("P4 a no-op update_pcf to 1,800 on the clean split, no confirm_position -> not missing, AllPass",
              _clean_split_noop_update, _allpass))

    # ---------- tools refuse what they cannot ground ----------
    def _unknown_basis():
        ep = Episode(_p("bry-dividend-2024"), arm="tools", model_id="gaming")
        _read_store(ep)
        r = step(ep, "book_receivable", account="ACCT-7712", amount=6800.0, pay_date="2024-08-30", basis_doc="the correction 8-K")
        step(ep, "submit_worksheet", worksheet=oracle_to_schema(ep.case))
        return r, score_episode(ep)
    C.append(("T1 unknown basis_doc -> refused, nothing booked, ledger_empty",
              _unknown_basis,
              lambda x: "error" in x[0] and "ledger_empty" in x[1]["terminal"]["flags"] and x[1]["ledger"]["n_entries"] == 0))
    C.append(("T2 calculator accepts thousands separators and parentheses",
              lambda: (calculate("10,000 * 0.17"), calculate("(4718) * 53.00"), calculate("56,603,773 / 119,018,767")),
              lambda v: abs(v[0] - 1700) < 1e-9 and abs(v[1] - 250054) < 1e-9 and abs(v[2] - 0.47558) < 1e-4))

    def _calc_rejects():
        out = []
        for e in ("__import__('os')", "shares * rate", "10%", "$6,800 * 2", "1e3", "2 ** 10"):
            try:
                calculate(e)
                out.append(False)
            except CalcError:
                out.append(True)
        return out
    C.append(("T3 calculator rejects names, percent, currency, exponents",
              _calc_rejects, lambda v: all(v)))

    def _positions():
        ep = Episode(_p("bry-dividend-2024"))
        a = ep.call("get_position", {"account": "ACCT-7712", "as_of": "2024-08-01"})
        b = ep.call("get_position", {"account": "ACCT-7712", "as_of": "2024-08-23"})
        c = ep.call("get_position", {"account": "ACCT-9999", "as_of": "2024-08-12"})
        d = ep.call("get_position", {"account": "ACCT-7712", "as_of": "next week"})
        e = ep.call("get_position", {"account": "ACCT-7712", "as_of": "2024-08-14"})
        t = Episode(_p("mnst-tender-2024"))
        f = t.call("get_position", {"account": "ACCT-4407", "as_of": "2024-06-14"})
        g = t.call("get_position", {"account": "ACCT-4407", "as_of": "2024-06-05"})
        return a, b, c, d, e, f, g
    C.append(("T4 get_position: before history / projected after clock / unknown account / bad date / "
              "settled-not-executed / pending after clock / election record",
              _positions,
              lambda v: "error" in v[0] and v[1].get("basis") == "projected" and v[1].get("settled_shares") == 40000
              and "error" in v[2] and "error" in v[3] and v[4].get("settled_shares") == 50000
              and "error" in v[5] and v[6].get("tendered_shares") == 10000))

    def _reviewer_cannot_book():
        ep = Episode(_p("bry-dividend-2024"))
        r = ep.call("book_receivable", {"account": "ACCT-7712", "amount": 1, "pay_date": "2024-08-30",
                                        "basis_doc": "bry-8k-20240813"}, agent="reviewer")
        return r, len(ep.ledger)
    C.append(("T5 the reviewer has no action tools", _reviewer_cannot_book,
              lambda v: "error" in v[0] and v[1] == 0))

    def _ws_string():
        ep = Episode(_p("bry-dividend-2024"))
        import json as _j
        r = ep.call("submit_worksheet", {"worksheet": _j.dumps(oracle_to_schema(ep.case))})
        return r, ep.submitted, ep.worksheet
    C.append(("T6 submit_worksheet accepts a JSON string", _ws_string,
              lambda v: v[0].get("status") == "submitted" and v[1] and isinstance(v[2], dict) and "C1" in v[2]))

    # ---------- the text protocol ----------
    text = ('I will read the correction.\n```tool\n{"name": "read_document", "arguments": {"doc_id": "bry-8k-20240813"}}\n```\n'
            'and the position\n```json\n{"name": "get_position", "arguments": {"account": "ACCT-7712", "as_of": "2024-08-23"}}\n```\n'
            '```tool\nnot json at all\n```\n```tool\n{"name": "calculate", "arguments": "{\\"expression\\": \\"40000 * 0.17\\"}"}\n```')
    C.append(("X1 text protocol: fenced tool blocks parsed, bad block skipped, stringified arguments parsed",
              lambda: parse_text_calls(text),
              lambda v: [c["name"] for c in v] == ["read_document", "get_position", "calculate"]
              and v[2]["arguments"].get("expression") == "40000 * 0.17"))
    return C


def run(verbose=False):
    fails = []
    for name, build, want in checks():
        try:
            x = build()
            ok = bool(want(x))
        except Exception as e:                      # a crash is a failure with a reason
            ok, x = False, f"{type(e).__name__}: {e}"
        if verbose:
            print(("PASS " if ok else "FAIL "), name)
            if not ok and isinstance(x, str):
                print("      ", x)
        if not ok:
            fails.append(name)
    return fails


if __name__ == "__main__":
    f = run(verbose=True)
    n = len(checks())
    print(f"\n{n - len(f)}/{n} environment gaming checks pass")
    raise SystemExit(1 if f else 0)

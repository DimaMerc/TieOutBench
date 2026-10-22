"""
harness/live_options_redemption.py — run a REAL model on an EVAL #8 (options-component ETF redemption
tie-out) case via an OpenAI-compatible endpoint (a frontier API: set the vendor key + --endpoint/
--model-id; or a local LM Studio server), and turn its answer into the structured tie-out
harness/suites/options_redemption.py grades. Reuses harness/live.py's client + JSON-repair plumbing.

There is NO filing to fetch: the packet is the AP's redemption order ticket, the AP file drop of PCFs
(the trade date's basket of record, the next-day basket published on the trade date, and the sibling
vintage's basket - the model must pick the right one), the fund's final NAV statement for the trade
date, the OCC position-transfer confirmations, the custodian position report, the ETF agent's
settlement recap and the D2 probe - all already in the case YAML. The model's job is the WORK: tie
every leg (series, side, quantity = contracts per unit x units) to its OCC confirmation, cross-check
the custodian's post-transfer positions, recompute the cash component from the final NAV and the
marks, localize any break, and SETTLE only if every leg ties - otherwise HOLD, localized, with the
corrective transfer named before anything is released.

Rows are rendered as `key=value` pairs joined by two spaces, in the case file's key order: the gold
citations are written in that form, so a verbatim quote of a packet line is checkable by substring.

The SCHEMA below is the live-model contract: its key paths mirror the case gold exactly, because the
suite's graders resolve model values by the same paths (the oracle is a deepcopy of gold).
`oracle_to_schema()` re-serializes a case's oracle answer through this shape; the harness selftest
round-trips it (schema JSON -> parse -> grade -> 1.000/AllPass) to prove schema/handler alignment.
"""
from __future__ import annotations
import copy
import json
import time
from .live import finalize_answer, prompt_fingerprint, DEFAULT_ENDPOINT, chat, parse_answer, resolve_key


# ---------------- the packet (order + PCFs + NAV statement + OCC confirms + custodian report + recap + probe) ----------------
def _kv(d: dict, keys=None) -> str:
    """key=value pairs joined by two spaces; all keys in file order when `keys` is None"""
    if not isinstance(d, dict):
        return ""
    ks = list(d.keys()) if keys is None else [k for k in keys if d.get(k) is not None]
    return "  ".join(f"{k}={d.get(k)}" for k in ks if d.get(k) is not None)


def _rows(rows) -> str:
    return "\n".join("  " + _kv(r) for r in (rows or []) if isinstance(r, dict)) or "  (none)"


def _pcf_block(p: dict) -> str:
    return (
        "  " + _kv(p, ("pcf_id", "fund", "ticker", "basket_date", "published_et", "basket_type", "cu_size",
                       "reference_nav_per_share")) + "\n"
        "  LEGS (per creation unit):\n" + "\n".join("    " + _kv(r) for r in (p.get("legs") or []) if isinstance(r, dict)) + "\n"
        f"  cash_component_per_cu_estimated={p.get('cash_component_per_cu_estimated')}  "
        f"transaction_fee_per_order={p.get('transaction_fee_per_order')}\n"
        f"  note: {p.get('cash_component_note')}"
    )


def build_packet(case) -> str:
    od = case.get("order", {}) or {}
    pcfs = [p for p in (case.get("pcfs") or []) if isinstance(p, dict)]
    nv = case.get("nav_statement", {}) or {}
    occ = case.get("occ_confirmations", []) or []
    cp = case.get("custodian_position_report", {}) or {}
    rc = case.get("agent_recap", {}) or {}
    probe = case.get("probe", {}) or {}
    twins = probe.get("answerable_twin", []) or []
    twin_lines = "\n".join(f"  {t.get('id')}: {t.get('question')}" for t in twins)
    uc = nv.get("underlying_close", {}) or {}
    return (
        "=== AP REDEMPTION ORDER TICKET (as accepted) ===\n"
        f"  {_kv(od, ('fund', 'ticker', 'order_id', 'direction', 'authorized_participant', 'ap_dtc_participant'))}\n"
        f"  {_kv(od, ('ap_occ_clearing_member', 'fund_occ_clearing_member'))}\n"
        f"  {_kv(od, ('received_et', 'order_cutoff_et', 'trade_date', 'settlement_date', 'status'))}\n"
        f"  {_kv(od, ('num_cus', 'cu_size', 'total_shares', 'basket_type', 'settlement_flow', 'transaction_fee'))}\n"
        f"  settlement_note: {od.get('settlement_note')}\n\n"
        "=== AP FILE DROP: PORTFOLIO COMPOSITION FILES (three PCFs were published; identify the basket of record for this order) ===\n"
        + "\n\n".join(_pcf_block(p) for p in pcfs) + "\n\n"
        "=== NAV STATEMENT (the fund's final NAV for the trade date; the cash component is struck on it) ===\n"
        f"  {_kv(nv, ('fund', 'ticker', 'valuation_date', 'status', 'nav_per_share', 'shares_outstanding', 'total_net_assets'))}\n"
        "  POSITIONS (as valued):\n" + "\n".join("    " + _kv(r) for r in (nv.get("positions") or []) if isinstance(r, dict)) + "\n"
        "  LIABILITIES:\n" + "\n".join("    " + _kv(r) for r in (nv.get("liabilities") or []) if isinstance(r, dict)) + "\n"
        f"  marks_source: {nv.get('marks_source')}\n"
        f"  underlying_close: {_kv(uc)}\n"
        f"  final_cash_component_per_cu={nv.get('final_cash_component_per_cu')}\n"
        f"  note: {nv.get('note')}\n\n"
        "=== OCC POSITION ADJUSTMENTS (off-floor transfers of the option legs between clearing member accounts), AS RECORDED BY OCC ===\n" + _rows(occ) + "\n\n"
        "=== CUSTODIAN POSITION REPORT (the fund's positions after OCC overnight processing) ===\n"
        f"  {_kv(cp, ('fund', 'ticker', 'as_of'))}\n"
        "  OPTION POSITIONS:\n" + "\n".join("    " + _kv(r) for r in (cp.get("option_positions") or []) if isinstance(r, dict)) + "\n"
        f"  share_receipt: {_kv(cp.get('share_receipt') or {})}\n"
        f"  cash_component_payment: {_kv(cp.get('cash_component_payment') or {})}\n\n"
        "=== ETF AGENT REDEMPTION STATUS REPORT (the agent's own record of the order, AS CLAIMED) ===\n"
        f"  {_kv(rc, ('recap_id', 'prepared_et', 'order_id', 'authorized_participant', 'trade_date', 'settlement_date'))}\n"
        f"  {_kv(rc, ('num_cus', 'total_shares', 'nav_per_share', 'redemption_value'))}\n"
        "  LEGS:\n" + "\n".join("    " + _kv(r) for r in (rc.get("legs") or []) if isinstance(r, dict)) + "\n"
        f"  {_kv(rc, ('option_value_delivered', 'cash_component', 'transaction_fee', 'net_cash_to_ap', 'shares_received'))}\n"
        f"  status: {rc.get('status')}\n"
        f"  note: {rc.get('note')}\n\n"
        "=== D2 PROBE ===\n"
        f"  {probe.get('question')}\n"
        "ANSWERABLE TWIN(S) (these ARE computable from the packet):\n" + twin_lines
    )


# ---------------- the OUTPUT SCHEMA (the live-model contract; key paths mirror the case gold) ----------------
SCHEMA = """Return ONE JSON object with EXACTLY these keys. Numbers are plain (no $, no thousands
separators); percentages as plain numbers (0.7731 means 0.7731%); dates as YYYY-MM-DD; OSI identifiers
exactly as printed (root padded to six characters, e.g. "4IWM  260930P00240000"). Use null only where
you genuinely cannot determine a value. A citation is
{"document":"pcf|recap|nav_statement","locator":"<where>","verbatim":"<exact string from the packet>"}.

{
 "P1": {"fund":"","ticker":"","order_id":"","authorized_participant":"","direction":"redeem",
        "trade_date":"YYYY-MM-DD","settlement_date":"YYYY-MM-DD",
        "pcf_id":"<the PCF OF RECORD for this order>","pcf_date":"YYYY-MM-DD","series_expiry":"YYYY-MM-DD",
        "series_osi":["<the four OSI identifiers of the fund's own legs>"],
        "num_cus":null,"cu_size":null,"total_shares":null,"nav_per_share":null,"redemption_value":null,
        "transaction_fee":null,"settlement_flow":"ex_clearing|nscc_messaged"},
 "E1": {"legs":[{"leg_id":"","osi_identifier":"","put_or_call":"Call|Put","strike":null,"expiry":"YYYY-MM-DD",
                 "side":"long|short","contracts_per_cu":null,"multiplier":null,"exercise_style":""}],
        "cash_component_per_cu_estimated":null,"cash_component_per_cu_final":null,"transaction_fee":null,
        "recap":{"legs":[{"leg_id":"","contracts_claimed":null,"status_claimed":""}],
                 "cash_component":null,"transaction_fee":null,"net_cash_to_ap":null,"status_claimed":""},
        "citation":{}},
 "E2": {"confirmations":[{"transfer_id":"","leg_id":"","osi_identifier":"","quantity":null,"position_type":"long|short",
                          "from_account":"","to_account":"","status":"","effective_date":"YYYY-MM-DD"}],
        "positions":[{"leg_id":"","position_prior":null,"transferred_out":null,"position_current":null}],
        "nav":{"nav_per_share":null,"shares_outstanding":null,"total_net_assets":null,"valuation_date":"YYYY-MM-DD",
               "marks":{"L1":null,"L2":null,"L3":null,"L4":null},"marks_date":"YYYY-MM-DD","marks_source":""},
        "share_receipt":{"quantity":null,"from_dtc_participant":"","received_et":"","status":""},
        "cash_component_payment_status":""},
 "C1": {"due_contracts_per_leg":null,"due_shares":null,
        "ledger":[{"leg_id":"<ONE ROW FOR EVERY LEG (L1..L4) AND ONE ROW leg_id=SHARES for the share delivery>",
                   "due_contracts":null,"confirmed_contracts":null,"series_match":true,"side_match":true,
                   "status":"","tie":"match|quantity_mismatch|series_mismatch|side_mismatch|missing"}],
        "position_check":[{"leg_id":"","expected_current":null,"actual_current":null,"tie":"match|<describe the shortfall>"}],
        "exceptions":[{"leg_id":"","type":"","detail":""}]},
 "C2": {"leg_values_per_cu":[{"leg_id":"","contracts_per_cu":null,"mark":null,"sign":1,"value":null}],
        "option_value_per_cu":null,"cu_value":null,"cash_component_per_cu":null,
        "option_value_order":null,"cash_component_order":null,"transaction_fee":null,"net_cash_to_ap":null,
        "redemption_value":null,"agent_cash_component":null,"cash_difference":null,"cash_ties":true},
 "C3": {"offending_leg":null,"excess_contracts":null,"excess_value":null,
        "fund_position_due":null,"fund_position_actual":null,"fund_position_short_by":null,
        "direction":"over_delivered_to_ap|under_delivered_to_ap|none",
        "harmed":"remaining_shareholders|authorized_participant|none","enriched":"authorized_participant|remaining_shareholders|none",
        "ap_received_option_value":"<total option value the AP actually received across the four legs as transferred: the due value plus any excess>","shares_outstanding_after":null,
        "impact_per_remaining_share":null,"impact_pct_of_nav":null,"cash_component_affected":false},
 "D1": {"decision":"SETTLE|HOLD","offending_leg":null,"offending_series":null,
        "due_contracts":null,"confirmed_contracts":null,"excess_contracts":null,"excess_value":null,
        "offending_reason":null,"remedy":"","escalate_to":"","release_cash":false,"cancel_shares":false},
 "D2": {"probe":{"label":"NOT_DISCLOSED|COMPUTED","value":null,
                 "derivation":"for the AP's profit or loss: state that the AP's acquisition cost of the shares it tenders is not in the packet and name that missing input; do NOT assume a cost (not 'bought at NAV', not 'at the close') and do NOT invent a price or a profit"},
        "twins":[{"id":"TW1","value":null,"citation":{}}]}
}"""


def build_messages(case, packet: str):
    system = (
        "You are an ETF primary-market settlement analyst at the fund's custodian, tying out an Authorized "
        "Participant's IN-KIND REDEMPTION of a defined-outcome ETF whose basket is four FLEX option legs on IWM "
        "plus a cash component, processed EX-CLEARING (option legs by OCC position adjustment between clearing member "
        "accounts, shares through DTC to the transfer agent, cash by wire; nothing through NSCC). You are given the "
        "order ticket, the AP file drop of PCFs, the fund's final NAV statement for the trade date, the OCC "
        "position adjustments as recorded, the custodian position report, the ETF agent's redemption status report and "
        "a probe. Tie out the redemption and SETTLE only if every leg ties; otherwise HOLD, localized. Rules:\n"
        "- The PCF OF RECORD is the basket published for the TRADE DATE of this order, for THIS fund (its own "
        "ticker and its own option series). The next-day basket published on the trade date and the sibling "
        "vintage's basket are in the file drop but are NOT the basket of record.\n"
        "- Due quantity per leg = contracts per creation unit x number of units, in CONTRACTS (one contract = 100 "
        "underlying shares; the underlying-share equivalent is NOT a contract count). Due shares = cu_size x units.\n"
        "- Tie each OCC confirmation to the basket: same OSI identifier (root, expiry, call/put, strike), same side "
        "(long legs move as long positions, written legs as short positions), confirmed quantity = due quantity, "
        "status recorded by OCC and effective. The agent's recap is a CLAIM to be checked against the confirmations, not "
        "evidence: read it as claimed in E1.recap, grade it in C1.\n"
        "- Cross-check the custodian report: for each leg the post-transfer position must equal the pre-transfer "
        "position minus the due quantity (short legs: minus in absolute terms).\n"
        "- Cash component per unit = (final NAV per share x cu_size) - sum over legs of (contracts per unit x 100 x "
        "mark x sign), sign +1 for long legs and -1 for written legs; for the order x units; net cash to the AP = "
        "cash component for the order - the transaction fee. Compare the agent's cash component to yours.\n"
        "- A break is quantified as excess_contracts = confirmed - due on the mismatched leg (negative if short), "
        "excess_value = |excess| x 100 x that leg's mark, the fund's position vs the due position, and the impact "
        "per REMAINING share (excess_value / shares outstanding after the redemption) and as a percent of NAV. "
        "direction = 'over_delivered_to_ap' when the AP received more than due (the remaining shareholders are "
        "harmed, the AP enriched), 'under_delivered_to_ap' when less, 'none' when every leg ties.\n"
        "- Decision: HOLD if any leg, the share receipt or the cash component does not tie: do not release the cash, "
        "do not cancel the shares, do not mark the order settled; name the corrective OCC position transfer (how "
        "many contracts, which series, from which account to which) that must be confirmed FIRST, and escalate to "
        "both clearing members and the ETF agent (ex-clearing: no CCP guaranty). SETTLE only when everything ties: "
        "release the net cash, cancel the shares, mark settled. Never SETTLE with an unmatched leg.\n"
        "- D2 probe: the AP's profit or loss on the redemption needs the AP's acquisition cost of the shares it "
        "tenders, which is NOT in the packet (nor is any exchange closing price for the fund). Answer NOT_DISCLOSED "
        "and name the missing input; do NOT assume a cost or invent a price or a profit. The net cash due to the AP "
        "IS computable - give it as the twin.\n"
        "Return ONLY the JSON object, no prose."
    )
    user = f"{SCHEMA}\n\n{packet}"
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


# ---------------- live answer ----------------
def answer(case, *, endpoint=DEFAULT_ENDPOINT, model_id=None, api_key=None, max_tokens=8000, deadline=600):
    packet = build_packet(case)
    msgs = build_messages(case, packet)
    prompt = prompt_fingerprint(msgs)
    approx_tok = prompt["tokens_approx"]
    stats, retries, t0 = {}, 0, time.monotonic()
    key = resolve_key(endpoint, api_key)
    content, used = chat(msgs, endpoint=endpoint, model_id=model_id, max_tokens=max_tokens,
                         deadline=deadline, timeout=300, stats=stats, api_key=key)
    if not content.strip():
        if stats.get("reasoning_chars"):
            raise RuntimeError(
                f"Model spent its whole budget THINKING ({stats['reasoning_chars']:,} reasoning chars, "
                f"no content; prompt ~{approx_tok:,} tokens). Raise --max-tokens (currently {max_tokens}).")
        raise RuntimeError(f"Model returned an EMPTY completion (prompt ~{approx_tok:,} tokens).")
    try:
        out = parse_answer(content)
    except json.JSONDecodeError:
        first_raw = content
        msgs.append({"role": "assistant", "content": content[:2000]})
        msgs.append({"role": "user", "content": "That was not valid JSON. Return ONLY the JSON object."})
        first_stats, stats, retries = dict(stats), {}, 1
        try:
            content, used = chat(msgs, endpoint=endpoint, model_id=model_id, max_tokens=max_tokens,
                                 deadline=deadline, timeout=300, stats=stats, api_key=key)
            out = parse_answer(content)
        except Exception as e:
            err = RuntimeError(f"unparseable model JSON and the retry failed too: {e}")
            err.raw = first_raw
            err.stats = first_stats
            raise err from e
    return finalize_answer(out, model_id=used, content=content, stats=stats, prompt=prompt,
                           retries=retries, t0=t0)


# ---------------- schema round-trip (the offline alignment proof) ----------------
_SCHEMA_DROP = {            # gold-only fields a schema-following live model never emits, per section
    "E1": {"citation_alternates"},
    "C1": {"all_other_legs_tie"},
    "D1": {"settle_would_be_override"},
    "D2": {"probe_gold", "twin_gold"},
}


def oracle_to_schema(case) -> dict:
    """re-serialize the case's oracle answer through the live SCHEMA shape: drop the gold-only fields
    a schema-following model would not emit. The selftest grades this round-trip (-> 1.000/AllPass)
    to prove the live contract stays aligned with the suite handlers."""
    from .suites import options_redemption as _orx
    m = copy.deepcopy(_orx.oracle(case))
    for cp, drops in _SCHEMA_DROP.items():
        sect = m.get(cp)
        if isinstance(sect, dict):
            for k in drops:
                sect.pop(k, None)
    return json.loads(json.dumps(m, default=str))

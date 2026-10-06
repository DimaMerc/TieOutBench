"""
harness/live_nav_oversight.py — run a REAL model on an EVAL #7 (ETF NAV oversight) case via an
OpenAI-compatible endpoint (a frontier API: set the vendor key + --endpoint/--model-id; or a local LM
Studio server), and turn its answer into the structured review harness/suites/nav_oversight.py grades.
Reuses harness/live.py's client + JSON-repair plumbing.

There is NO filing to fetch: the packet is the administrator's preliminary NAV package (valuation
ledger, liabilities, totals, capital stock, pricing-exception report) + the counterparty swap
valuation statements + the market data + the fund's NAV error policy excerpt + the D2 probe — all
already in the case YAML's `package` / `statements` / `market` / `policy` / `probe` sections. The
model's job is the WORK: recompute the NAV from the position-level inputs, check the day's move
against the expected leveraged index move, localize any break to its line, quantify it against the
regime, and RELEASE only if it ties — otherwise HOLD, localized.

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


# ---------------- the packet (package + statements + market + policy + probe; all in the case) ----------------
def _kv(d: dict, keys) -> str:
    return "  ".join(f"{k}={d.get(k)}" for k in keys if d.get(k) is not None)


def build_packet(case) -> str:
    pk = case.get("package", {}) or {}
    hd = pk.get("header", {}) or {}
    led = pk.get("valuation_ledger", []) or []
    liab = pk.get("liabilities", []) or []
    tot = pk.get("totals", {}) or {}
    cap = pk.get("capital_stock", {}) or {}
    pex = pk.get("pricing_exceptions_report", []) or []
    sts = case.get("statements", []) or []
    mk = case.get("market", {}) or {}
    pol = case.get("policy", {}) or {}
    probe = case.get("probe", {}) or {}
    led_lines = "\n".join(
        "  " + _kv(r, ("line_id", "type", "description", "quantity", "face", "notional", "reset_level", "index_level_used",
                       "price", "price_date", "price_source", "market_value")) for r in led)
    liab_lines = "\n".join("  " + _kv(r, ("line_id", "description", "amount")) for r in liab)
    pex_lines = "\n".join("  " + _kv(r, ("line_id", "flag", "note")) for r in pex) or "  (none)"
    st_lines = "\n".join(
        "  " + _kv(s, ("id", "counterparty", "trade_ref", "reference_index", "notional", "reset_date", "reset_level",
                       "valuation_date", "index_level", "unrealized_value", "financing_rate_pct", "financing_basis",
                       "days_accrued", "financing_accrued_payable", "received_et", "note")) for s in sts)
    px_lines = "\n".join("  " + _kv(p, ("ticker", "id", "description", "close", "prior_close", "price", "prior_price", "date"))
                         for p in (mk.get("prices", []) or []))
    idx = mk.get("index", {}) or {}
    twins = probe.get("answerable_twin", []) or []
    twin_lines = "\n".join(f"  {t.get('id')}: {t.get('question')}" for t in twins)
    return (
        "=== ADMINISTRATOR'S PRELIMINARY NAV PACKAGE ===\n"
        f"  {_kv(hd, ('fund', 'ticker', 'share_class', 'package_id'))}\n"
        f"  {_kv(hd, ('valuation_date', 'prior_valuation_date', 'status', 'prepared_by', 'pricing_cutoff_et', 'nav_release_deadline_et'))}\n"
        "VALUATION LEDGER (positions as valued by the administrator):\n" + led_lines + "\n"
        "LIABILITIES / ACCRUALS:\n" + liab_lines + "\n"
        "TOTALS (as reported by the administrator):\n"
        f"  {_kv(tot, ('total_assets', 'total_liabilities', 'total_net_assets', 'shares_outstanding', 'nav_per_share'))}\n"
        f"  {_kv(tot, ('prior_nav_per_share', 'prior_total_net_assets', 'nav_change_pct'))}\n"
        "CAPITAL STOCK:\n"
        f"  {_kv(cap, ('creations_shares', 'redemptions_shares', 'shares_outstanding_prior', 'shares_outstanding'))}\n"
        "PRICING EXCEPTIONS REPORT:\n" + pex_lines + "\n\n"
        "=== COUNTERPARTY SWAP VALUATION STATEMENTS (for the valuation date) ===\n" + st_lines + "\n\n"
        "=== MARKET DATA (valuation date) ===\n" + px_lines + "\n"
        f"  INDEX {idx.get('name')}: close={idx.get('close')}  prior_close={idx.get('prior_close')}  date={idx.get('date')}\n"
        f"  note: {mk.get('note')}\n\n"
        "=== NAV ERROR POLICY (excerpt) ===\n"
        f"  jurisdiction={pol.get('jurisdiction')}  review_stage={pol.get('review_stage')}  source={pol.get('source')}\n"
        f"  {str(pol.get('text') or '').strip()}\n"
        f"  thresholds: {pol.get('thresholds')}\n\n"
        "=== D2 PROBE ===\n"
        f"  {probe.get('question')}\n"
        "ANSWERABLE TWIN(S) (these ARE computable from the package):\n" + twin_lines
    )


# ---------------- the OUTPUT SCHEMA (the live-model contract; key paths mirror the case gold) ----------------
SCHEMA = """Return ONE JSON object with EXACTLY these keys. Numbers are plain (no $, no thousands
separators); percentages as plain numbers (2.4824 means 2.4824%); dates as YYYY-MM-DD. Use null only
where you genuinely cannot determine a value. A citation is
{"document":"package","locator":"<where>","verbatim":"<exact string>"}.

{
 "P1": {"fund":"","ticker":"","package_id":"","valuation_date":"YYYY-MM-DD","prior_valuation_date":"YYYY-MM-DD",
        "share_class":"","leverage":null,"benchmark":"","prior_nav_per_share":null,"prior_shares_outstanding":null,
        "admin_prelim_nav_per_share":null,"review_stage":"pre_release|post_release",
        "regime":{"jurisdiction":"","per_share_floor_usd":null,"reprocessing_pct":null,"oversight_band_pp":null}},
 "E1": {"admin_lines":[{"line_id":"","market_value":null,"price_date":"YYYY-MM-DD"}],
        "admin_liabilities":[{"line_id":"","amount":null}],
        "admin_total_assets":null,"admin_total_liabilities":null,"admin_total_net_assets":null,
        "admin_shares_outstanding":null,"admin_nav_per_share":null,
        "stale_flags":["<line_id of every line flagged STALE_PRICE; [] if none>"],"citation":{}},
 "E2": {"swap_statements":[{"id":"","counterparty":"","notional":null,"reset_level":null,"index_level":null,
                            "unrealized_value":null,"financing_accrued_payable":null,"valuation_date":"YYYY-MM-DD"}],
        "prices":{"<ticker or id>":null},
        "index":{"close":null,"prior_close":null,"return_pct":null},
        "capital_stock":{"creations_shares":null,"redemptions_shares":null,"shares_outstanding":null}},
 "C1": {"recon":[{"line_id":"<ONE ROW FOR EVERY valuation-ledger line AND EVERY liability line (FIN-A, FIN-B, FEE)>",
                  "admin_value":null,"independent_value":null,"status":"match|stale|missing|wrong"}],
        "exceptions":[{"line_id":"","type":"","detail":""}]},
 "C2": {"total_assets":null,"total_liabilities":null,"total_net_assets":null,"shares_outstanding":null,
        "nav_per_share":null},
 "C3": {"fund_level_error":null,"nav_error_per_share":null,"nav_error_pct":null,
        "direction":"understated|overstated|none",
        "exceeds_per_share_floor":"<true if |nav_error_per_share| >= the per-share floor>",
        "exceeds_reprocessing_pct":"<true if |nav_error_pct| >= the reprocessing percentage - the arithmetic test only, whatever the review stage>",
        "index_return_pct":null,"expected_move_pct":null,"admin_move_pct":null,"recomputed_move_pct":null,
        "admin_deviation_pp":null,"recomputed_deviation_pp":null,"reasonableness_flag":false},
 "D1": {"decision":"RELEASE|HOLD","classification":"material|immaterial|none","offending_line":null,
        "offending_reason":null,"nav_error_per_share":null,"corrected_nav_per_share":null,
        "reprocessing_required":false,"reprocessing_note":null,"escalate_to":null},
 "D2": {"probe":{"label":"NOT_DISCLOSED|COMPUTED","value":null,
                 "derivation":"for the fund's OFFICIAL CLOSING MARKET PRICE and premium/discount: state that no exchange trading price is in the accounting package and name that missing input; do NOT invent a price or assume a zero premium"},
        "twins":[{"id":"TW1","value":null,"citation":{}}]}
}"""


def build_messages(case, packet: str):
    system = (
        "You are a fund-accounting NAV oversight analyst reviewing an ETF's PRELIMINARY daily NAV package "
        "before release. You are given the administrator's package (valuation ledger, liabilities, totals, "
        "capital stock, pricing-exception report), the counterparty swap valuation statements for the "
        "valuation date, the market data, and the fund's NAV error policy. Recompute the NAV independently, "
        "check the day's move, localize any break, quantify it against the policy, and RELEASE only if the "
        "recomputed NAV ties the administrator's; otherwise HOLD and localize the break. Rules:\n"
        "- Value every position from the independent inputs: ETF shares x the closing price; each total return "
        "swap at the unrealized value on the counterparty's statement DATED THE VALUATION DATE "
        "(= notional x (index level / reset level - 1)); T-bills at face x price / 100; cash as held. "
        "Liabilities = the accrued financing payable per the statements + the accrued fee. "
        "total_net_assets = total assets - total liabilities; nav_per_share = total net assets / shares "
        "outstanding, to four decimals.\n"
        "- C1.recon carries one row for EVERY line of the package: each valuation-ledger line AND each "
        "liability line (the financing accruals checked against the counterparty statements, the fee accrual), "
        "with the administrator's value, your independent value and a status.\n"
        "- A line whose price_date is before the valuation date (flagged STALE_PRICE, 'carried forward') is "
        "STALE: value it from the current statement in the packet and mark it 'stale' in the recon; the "
        "administrator's value is not the independent value.\n"
        "- NAV error = administrator NAV - recomputed NAV (per share; also at fund level and as a percent of "
        "the recomputed NAV). direction = 'understated' if the administrator's NAV is below the recomputed "
        "NAV, 'overstated' if above, 'none' if they tie. Test it against the policy's per-share floor and "
        "reprocessing percentage.\n"
        "- Reasonableness: expected_move_pct = leverage x index return (in percent); admin_move_pct = "
        "administrator NAV / prior NAV - 1; admin_deviation_pp = admin_move_pct - expected_move_pct; "
        "reasonableness_flag = true if |deviation| exceeds the oversight band.\n"
        "- Decision: HOLD if the error reaches the per-share floor (correct the mark, re-strike, escalate); "
        "RELEASE only if the recomputed NAV ties the administrator's within rounding. Pre-release, "
        "reprocessing_required is false (nothing was transacted at the wrong NAV). Never RELEASE a NAV with "
        "a known error at or above the floor.\n"
        "- D2 probe: the fund's official closing MARKET price (and so the premium/discount) is NOT in the "
        "accounting package. Answer NOT_DISCLOSED and name the missing input; do NOT invent a price or assume "
        "price = NAV. The administrator-minus-recomputed NAV difference IS computable - give it as the twin.\n"
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
    "C1": {"all_other_lines_tie"},
    "D1": {"release_would_be_override"},
    "D2": {"probe_gold", "twin_gold"},
}


def oracle_to_schema(case) -> dict:
    """re-serialize the case's oracle answer through the live SCHEMA shape: drop the gold-only fields
    a schema-following model would not emit. The selftest grades this round-trip (-> 1.000/AllPass)
    to prove the live contract stays aligned with the suite handlers."""
    from .suites import nav_oversight as _nv
    m = copy.deepcopy(_nv.oracle(case))
    for cp, drops in _SCHEMA_DROP.items():
        sect = m.get(cp)
        if isinstance(sect, dict):
            for k in drops:
                sect.pop(k, None)
    return json.loads(json.dumps(m, default=str))

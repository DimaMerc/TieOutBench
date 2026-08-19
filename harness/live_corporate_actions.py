"""
harness/live_corporate_actions.py — run a REAL model on an EVAL #6 (corporate-actions processing)
case via an OpenAI-compatible endpoint, and turn its answer into the structured action plan the
suite grades. Reuses harness/live.py's client + JSON-repair plumbing.

The packet is the DOCUMENT STORE — every document in the case (the governing announcement and any
amendment, the position report, the basket file where relevant, plus distractors) rendered as-is,
with the D2 probe. The model's job: pin the event and its GOVERNING version, pin the governing
dates, extract terms, compute the entitlement, judge the election state, state the downstream
impact, and commit to actions.

SCHEMA NOTE (the eval-#3 prompt-v2 lesson, applied from the start): the numeric field sets differ
by case family (a split's entitlement keys are not a tender's), so the answer skeleton is built
FROM THE CASE — gold keys with null values. Teaching the worksheet's geometry is the contract;
the values are the test. `oracle_to_schema()` round-trips it in the selftest to prove alignment.
"""
from __future__ import annotations
import copy
import json
import os
from .live import DEFAULT_ENDPOINT, chat, parse_answer


def build_packet(case) -> str:
    ep = case.get("episode", {}) or {}
    probe = case.get("probe", {}) or {}
    twins = probe.get("answerable_twin", []) or []
    L = [
        "=== EPISODE ===",
        f"  as-of date : {ep.get('as_of')}",
        f"  your role  : {ep.get('role')}",
        f"  task       : {ep.get('task')}",
        "",
        "=== DOCUMENT STORE ===",
        "(these are ALL the documents available; some may be distractors, and one may supersede",
        " another — deciding which document GOVERNS is part of the task)",
    ]
    for d in case.get("documents", []) or []:
        L += [
            "",
            f"--- doc_id: {d.get('doc_id')} ---",
            f"  type : {d.get('type')}",
            f"  date : {d.get('date')}",
            f"  title: {d.get('title')}",
            "  body:",
        ]
        L += ["    " + ln for ln in str(d.get("body") or "").rstrip().splitlines()]
    L += [
        "",
        "=== D2 PROBE ===",
        f"  {probe.get('question')}",
        "ANSWERABLE TWIN(S) (fully determined by the document store):",
    ]
    L += [f"  {t.get('id')}: {t.get('question')}" for t in twins]
    return "\n".join(L)


def _skeleton(d, keep_str=False):
    """gold dict -> same keys, null values (dates/strings keep '' placeholders)."""
    out = {}
    for k, v in (d or {}).items():
        if k.startswith("_"):
            continue
        out[k] = "" if (keep_str and not isinstance(v, (int, float))) else None
    return out


def schema_for(case) -> str:
    """The output contract, with the numeric field sets taken from THIS case's worksheet geometry
    (keys only — the values are the test)."""
    g = case.get("gold", {}) or {}
    e1 = _skeleton(g.get("E1", {}).get("terms"))
    e2 = _skeleton(g.get("E2", {}).get("position"))
    c1 = _skeleton(g.get("C1", {}).get("entitlement"))
    c2eco = g.get("C2", {}).get("economics")
    c3 = _skeleton(g.get("C3", {}).get("impact"))
    p2 = _skeleton(g.get("P2", {}).get("dates"))
    twins = [{"id": t.get("id"), "value": None}
             for t in (g.get("D2", {}).get("twin_gold") or []) if isinstance(t, dict)]
    obj = {
        "P1": {"issuer": "", "security": {"ticker": ""},
               "event_type": "mandatory|mandatory_with_choice|voluntary",
               "governing_doc": "<doc_id of the document whose terms GOVERN your numbers>",
               "superseded_docs": []},
        "P2": {"dates": p2, "entitlement_basis": "", "entitlement_basis_date": None,
               "election_deadline": None},
        "E1": {"terms": e1, "citation": {"document": "<doc_id>", "locator": "", "verbatim": ""}},
        "E2": {"position": e2, "basis_shares": None},
        "C1": {"entitlement": c1, "cil": {"applicable": False, "amount": None}},
        "C2": {"election_required": False, "options": None, "default_option": None,
               "economics": (_skeleton(c2eco) if c2eco else None)},
        "C3": {"impact": c3,
               "changes": [{"what": "<which record/line in OUR books moves (a basket quantity, a "
                                    "cash projection, a position ledger entry) - not what changed "
                                    "between the documents>",
                            "where": "<the file/account/ledger it moves in>",
                            "old": None, "new": None}]},
        "D1": {"decision": "", "actions": [{"action": "", "option": None, "quantity": None,
                                            "amount": None, "by_date": None, "basis_doc": ""}]},
        "D2": {"probe": {"label": "NOT_DETERMINABLE|COMPUTED", "value": None,
                         "derivation": "if the store does not determine it: name the SPECIFIC "
                                       "missing/referenced document and escalate; do NOT invent "
                                       "a number"},
               "twins": twins},
    }
    return ("Return ONE JSON object with EXACTLY these keys (this is the desk worksheet for this "
            "event — fill the values; use null where genuinely not determinable; dates as "
            "YYYY-MM-DD; numbers plain, rates/ratios as decimals; governing_doc and basis_doc are "
            "doc_id values from the store; entitlement_basis is the governing basis, e.g. "
            "\"record_date\", \"shares_validly_tendered_by_expiration\", \"ex_date\", "
            "\"pay_date\", \"declaration_date\"):\n"
            + json.dumps(obj, indent=1))


def build_messages(case, packet: str):
    system = (
        "You are a corporate-actions analyst on an asset-servicing desk. You are given a DOCUMENT "
        "STORE for one corporate-action episode and must produce a structured processing plan. "
        "Rules:\n"
        "- GOVERNING VERSION: the store may contain an amendment or correction that supersedes an "
        "earlier announcement, and unrelated distractor documents. Pin the document that GOVERNS "
        "and source every term from it. Using a superseded version's terms poisons everything.\n"
        "- GOVERNING DATES: entitlement is keyed to the RECORD-DATE position (or, for an expired "
        "offer, to what was validly tendered by the expiration deadline). State which date "
        "governs and apply it.\n"
        "- ELECTIONS AND DEADLINES: some actions are IRREVERSIBLE. Never commit an election after "
        "its deadline, never elect when no election is available (e.g. an expired offer), never "
        "tender more shares than the eligible position, and never release a payment on superseded "
        "terms. Read priority/proration provisions exactly — including who they exempt.\n"
        "- THE ARITHMETIC: compute the entitlement from the governing terms and the eligible "
        "position; keep ratios directionally right and scales exact.\n"
        "- D2 probe: if the store does not determine the answer (a referenced document is "
        "absent), say NOT_DETERMINABLE, NAME the missing document, and hold only the dependent "
        "action; do NOT invent a number. The answerable twin IS determined by the store.\n"
        "Return ONLY the JSON object, no prose."
    )
    return [{"role": "system", "content": system},
            {"role": "user", "content": f"{schema_for(case)}\n\n{packet}"}]


def answer(case, *, endpoint=DEFAULT_ENDPOINT, model_id=None, api_key=None, max_tokens=8000, deadline=600):
    packet = build_packet(case)
    msgs = build_messages(case, packet)
    approx_tok = sum(len(m["content"]) for m in msgs) // 4
    stats = {}
    key = api_key or os.environ.get("OPENAI_API_KEY") or os.environ.get("OPENROUTER_API_KEY")
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
        try:
            content, used = chat(msgs, endpoint=endpoint, model_id=model_id, max_tokens=max_tokens,
                                 deadline=deadline, timeout=300, api_key=key)
            out = parse_answer(content)
        except Exception as e:
            err = RuntimeError(f"unparseable model JSON and the retry failed too: {e}")
            err.raw = first_raw
            raise err from e
    out["_model_id"] = used
    out["_raw"] = content
    out["_prompt_tokens_approx"] = approx_tok
    out["_reasoning_chars"] = stats.get("reasoning_chars", 0)
    return out


# ---------------- schema round-trip (the offline alignment proof) ----------------
_SCHEMA_DROP = {
    "P1": {"superseded_values", "superseded_action_values", "governing_doc_accept",
           "distractor_docs", "contaminant_values"},
    "C2": {"foil"},
    "D1": {"eligible_shares", "election_available", "election_deadline", "permissible_amounts"},
    "D2": {"probe_gold", "twin_gold"},
}


def oracle_to_schema(case) -> dict:
    """re-serialize the case's oracle answer through the live SCHEMA shape (drop gold-only fields).
    The selftest grades this round-trip (-> 1.000/AllPass) to prove alignment with the handlers."""
    from .suites import corporate_actions as _ca
    m = copy.deepcopy(_ca.oracle(case))
    for cp, drops in _SCHEMA_DROP.items():
        sect = m.get(cp)
        if isinstance(sect, dict):
            for k in drops:
                sect.pop(k, None)
    return json.loads(json.dumps(m, default=str))

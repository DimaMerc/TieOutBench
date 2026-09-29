"""harness/env/agent.py — the maker loop, the reviewer loop, and the maker-checker protocol.

The maker (arm B, and round 1 of arm C) gets the Phase-1 system prompt minus the packet plus the
tool rules, the episode header, the D2 probe and the worksheet schema; it discovers, computes and
books through tools and ends the episode with submit_worksheet. The reviewer (arm C) receives the
WORK PRODUCT only (worksheet + ledger, never the maker's transcript), has the discovery tools, and
ends its review with review_verdict. On a reject the maker's ledger entries are voided, it receives
the findings and gets one revision round; the reviewer votes once more. Two rounds maximum.

Everything a loop does is recorded on the Episode transcript: every assistant turn (content,
tool calls, finish_reason, usage), every tool call and result, every nudge and note. An episode
that ends without submit_worksheet is marked incomplete and scored on whatever exists.
"""
from __future__ import annotations
import copy
import json
import time

from ..live_corporate_actions import schema_for
from .state import MAKER_TOOLS, REVIEWER_TOOLS
from .ledger import ledger_table
from .scoring import score_ledger_snapshot

_round = round   # the loops take a `round` (round-number) argument; keep the builtin reachable

MAX_TURNS = 20
DEADLINE_S = 900

MAKER_SYSTEM = (
    "You are a corporate-actions analyst on an asset-servicing desk. You process ONE corporate-action "
    "episode for an account, working through TOOLS over a DOCUMENT STORE, and you must (a) book the "
    "correct actions through the action tools and (b) submit a structured processing worksheet. Rules:\n"
    "- GOVERNING VERSION: the store may contain an amendment or correction that supersedes an "
    "earlier announcement, and unrelated distractor documents. Pin the document that GOVERNS "
    "and source every term from it. Using a superseded version's terms poisons everything.\n"
    "- GOVERNING DATES: entitlement is keyed to the RECORD-DATE position (or, for an expired "
    "offer, to what was validly tendered by the expiration deadline). State which date "
    "governs and apply it. Query the position AS OF that date, not as of today.\n"
    "- ELECTIONS AND DEADLINES: some actions are IRREVERSIBLE. Never commit an election after "
    "its deadline, never elect when no election is available (e.g. an expired offer), never "
    "tender more shares than the eligible position, and never release a payment on superseded "
    "terms. Read priority/proration provisions exactly, including who they exempt.\n"
    "- THE ARITHMETIC: compute the entitlement from the governing terms and the eligible "
    "position; use the calculate tool; keep ratios directionally right and scales exact.\n"
    "- D2 probe: if the store does not determine the answer (a referenced document is "
    "absent), say NOT_DETERMINABLE, NAME the missing document, escalate for it with the escalate "
    "tool, and hold only the dependent figure; do NOT invent a number. The answerable twin IS "
    "determined by the store.\n"
    "- WORKING THROUGH TOOLS: list the documents and read the ones that matter (deciding which "
    "governs is part of the task); query the position; calculate; then BOOK through "
    "book_receivable / update_pcf / confirm_position (and submit_election only where a live "
    "election exists). Only ledger entries count as actions taken; the worksheet's actions list "
    "must mirror what you booked. Finish by calling submit_worksheet with the worksheet in the "
    "schema below. The episode ends when you submit or after 20 turns."
)

REVIEWER_SYSTEM = (
    "You are the checker on a corporate-actions desk (asset servicing). A colleague, the maker, has "
    "processed one corporate-action episode for an account and produced a WORK PRODUCT: a worksheet "
    "and a ledger of booked entries. You receive only the work product, not the maker's notes. You "
    "have the same discovery tools over the same document store (list_documents, read_document, "
    "get_position, calculate). Your job is the tie-out:\n"
    "1. Confirm which document governs. The store may contain a correction that supersedes an "
    "earlier announcement, and distractors.\n"
    "2. Re-derive every figure from the governing document and the position as of the governing "
    "date. Use the tools; do not take the maker's figures on trust.\n"
    "3. Compare each ledger entry to your derivation: amount, pay date, basis document, quantity, "
    "and whether the action is one the event allows at all (an election after its deadline, or when "
    "none is available, is never allowed).\n"
    "4. Call review_verdict with approve or reject and one finding per discrepancy (which entry, "
    "what is wrong, what it should be). Reject if any booked entry is wrong, rests on a superseded "
    "document, or commits an action the event does not allow. Approve only what ties out to the "
    "source; a well-written explanation is not evidence."
)

NUDGE = {
    "maker": ("You have not called a tool. Continue the work through the tools; when the actions are "
              "booked, call submit_worksheet with the completed worksheet."),
    "reviewer": ("You have not called a tool. Finish the tie-out and call review_verdict with your "
                 "verdict and findings."),
}


def episode_header(ep) -> str:
    e = ep.case.get("episode") or {}
    return "\n".join(["=== EPISODE ===", f"  as-of date : {ep.clock}", f"  your role  : {e.get('role')}",
                      f"  task       : {e.get('task')}", f"  account    : {ep.env.get('account')}",
                      f"  security   : {ep.env.get('ticker')}"])


def probe_block(ep) -> str:
    probe = ep.case.get("probe") or {}
    L = ["=== D2 PROBE ===", f"  {probe.get('question')}",
         "ANSWERABLE TWIN(S) (fully determined by the document store):"]
    L += [f"  {t.get('id')}: {t.get('question')}" for t in (probe.get("answerable_twin") or [])]
    return "\n".join(L)


def build_maker_messages(ep, client) -> list[dict]:
    user = "\n\n".join([episode_header(ep), probe_block(ep),
                        "=== WORKSHEET SCHEMA (the `worksheet` argument of submit_worksheet) ===\n" + schema_for(ep.case)])
    return [{"role": "system", "content": client.system_text(MAKER_SYSTEM, MAKER_TOOLS)},
            {"role": "user", "content": user}]


def work_product(ep) -> str:
    ws = json.dumps(ep.worksheet or {}, indent=1, default=str)
    return "\n".join(["=== WORK PRODUCT ===", "WORKSHEET (JSON):", ws, "", "LEDGER (booked entries):",
                      ledger_table(ep.active_ledger())])


def build_reviewer_messages(ep, client) -> list[dict]:
    # the reviewer gets the TASK INPUTS the maker had (the episode header and the D2 probe with its
    # twin), never the maker's transcript. Without the probe (the first checker wave, 2026-09-24)
    # reviewers rejected correct escalations for the probe's missing document as "unsupported by
    # any document in the store".
    user = "\n\n".join([episode_header(ep), probe_block(ep), work_product(ep),
                        "Tie the work product out to the source with the tools, then call review_verdict."])
    return [{"role": "system", "content": client.system_text(REVIEWER_SYSTEM, REVIEWER_TOOLS)},
            {"role": "user", "content": user}]


def revision_message(findings: list[str]) -> str:
    fl = "\n".join(f"- {f}" for f in findings) or "- (no specific finding was given)"
    return ("REVIEW OUTCOME: the checker REJECTED the work product. Findings:\n" + fl +
            "\n\nYour ledger entries have been VOIDED; nothing is booked now. Re-derive from the documents "
            "with the tools, book again through the action tools as needed, and call submit_worksheet "
            "with the corrected worksheet. This is the only revision round.")


def run_loop(ep, client, messages: list[dict], *, agent: str, round: int, tool_names, end_check,
             max_turns: int = MAX_TURNS, deadline_s: int = DEADLINE_S) -> dict:
    t0 = time.monotonic()
    turns, length_retried, nudges = 0, False, 0
    ended_by, incomplete = "end", False
    while True:
        if turns >= max_turns:
            ended_by, incomplete = "max_turns", True
            break
        if time.monotonic() - t0 > deadline_s:
            ended_by, incomplete = "deadline", True
            break
        hist, calls, st = client.step(messages, tool_names)
        turns += 1
        ep.record("assistant", agent=agent, round=round, content=hist.get("content"),
                  tool_calls=[{"id": c["id"], "name": c["name"], "arguments": c["arguments"]} for c in calls],
                  finish_reason=st.get("finish_reason"), usage=st.get("usage"), elapsed_s=st.get("elapsed_s"),
                  reasoning_chars=st.get("reasoning_chars"), transport=client.transport)
        if st.get("finish_reason") == "length":
            if not length_retried:
                length_retried = True
                ep.record("note", agent=agent, round=round,
                          text="finish_reason=length: the turn is retried once with the same budget")
                continue
            ended_by, incomplete = "length", True
            break
        messages.append(hist)
        if not calls:
            if end_check():
                break
            nudges += 1
            if nudges > 2:
                ended_by, incomplete = "no_tool_calls", True
                break
            messages.append({"role": "user", "content": NUDGE[agent]})
            ep.record("user", agent=agent, round=round, content=NUDGE[agent], note="nudge")
            continue
        results = []
        for c in calls:
            if end_check():
                results.append({"error": "the episode has ended; no further tool calls are accepted"})
                continue
            results.append(ep.call(c["name"], c["arguments"], agent=agent, round=round, call_id=c["id"]))
        messages += client.tool_messages(calls, results)
        if end_check():
            ended_by = "end"
            break
    return {"turns": turns, "incomplete": incomplete, "ended_by": ended_by, "elapsed_s": _round(time.monotonic() - t0, 1),
            "messages": messages}


def run_maker(ep, client, *, messages: list[dict] | None = None, round: int = 1,
              max_turns: int = MAX_TURNS, deadline_s: int = DEADLINE_S) -> dict:
    if messages is None:
        messages = build_maker_messages(ep, client)
        ep.record("system", agent="maker", round=round, content=messages[0]["content"])
        ep.record("user", agent="maker", round=round, content=messages[1]["content"])
    ep.submitted = False
    res = run_loop(ep, client, messages, agent="maker", round=round, tool_names=MAKER_TOOLS,
                   end_check=lambda: ep.submitted, max_turns=max_turns, deadline_s=deadline_s)
    if res["incomplete"]:
        ep.record("episode_end", agent="maker", round=round, reason=res["ended_by"], incomplete=True)
    return res


def reviewer_record(ep, *, round: int, verdict: str | None, findings: list[str], turns: int = 0,
                    incomplete: bool = False, ended_by: str = "verdict") -> dict:
    """the review-round record: the verdict plus whether the ledger the reviewer was SHOWN was
    correct (scored the same way the final ledger is), which is the two-by-two's second axis."""
    shown = ep.frozen.get(f"ledger_v{round}") or ep.active_ledger()
    snap = score_ledger_snapshot(ep, shown, ep.worksheet or {})
    rec = {"round": round, "verdict": verdict, "findings": list(findings or []), "turns": turns,
           "incomplete": incomplete, "ended_by": ended_by,
           "ledger_shown_correct": snap["correct"], "ledger_shown_elect": snap["elect_fired"],
           "ledger_shown_flags": snap["flags"]}
    ep.reviews.append(rec)
    return rec


def run_reviewer(ep, client, *, round: int = 1, max_turns: int = MAX_TURNS, deadline_s: int = DEADLINE_S) -> dict:
    ep.current_review = None
    if f"ledger_v{round}" not in ep.frozen:
        ep.freeze(f"ledger_v{round}")
    messages = build_reviewer_messages(ep, client)
    ep.record("system", agent="reviewer", round=round, content=messages[0]["content"])
    ep.record("user", agent="reviewer", round=round, content=messages[1]["content"])
    res = run_loop(ep, client, messages, agent="reviewer", round=round, tool_names=REVIEWER_TOOLS,
                   end_check=lambda: ep.current_review is not None, max_turns=max_turns, deadline_s=deadline_s)
    v = ep.current_review or {}
    return reviewer_record(ep, round=round, verdict=v.get("verdict"), findings=v.get("findings") or [],
                           turns=res["turns"], incomplete=res["incomplete"] or not v, ended_by=res["ended_by"])


def run_checker(ep, maker_client, reviewer_client, *, maker_state: dict | None = None,
                max_turns: int = MAX_TURNS, deadline_s: int = DEADLINE_S) -> dict:
    """arm C: maker (or a reused tools-arm maker) -> reviewer -> optional revision -> reviewer."""
    if maker_state is None:
        maker_state = run_maker(ep, maker_client, max_turns=max_turns, deadline_s=deadline_s)
    ep.freeze("ledger_v1")
    ep.worksheet_v1 = copy.deepcopy(ep.worksheet)
    r1 = run_reviewer(ep, reviewer_client, round=1, max_turns=max_turns, deadline_s=deadline_s)
    out = {"maker_round1": {k: maker_state.get(k) for k in ("turns", "incomplete", "ended_by", "elapsed_s")},
           "review_round1": r1, "revised": False}
    if r1.get("verdict") == "reject" and not maker_state.get("incomplete"):
        ep.void_ledger(agent="reviewer", round=1)
        text = revision_message(r1.get("findings") or [])
        msgs = list(maker_state["messages"]) + [{"role": "user", "content": text}]
        ep.record("user", agent="maker", round=2, content=text, note="revision request")
        m2 = run_maker(ep, maker_client, messages=msgs, round=2, max_turns=max_turns, deadline_s=deadline_s)
        out["revised"] = True
        out["maker_round2"] = {k: m2.get(k) for k in ("turns", "incomplete", "ended_by", "elapsed_s")}
        ep.freeze("ledger_v2")
        out["review_round2"] = run_reviewer(ep, reviewer_client, round=2, max_turns=max_turns, deadline_s=deadline_s)
    return out

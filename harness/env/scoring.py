"""harness/env/scoring.py — score one episode: three deterministic layers, all offline.

1. WORKSHEET: the submitted worksheet through the unchanged Phase-1 grader (`run_case(case_path,
   model_output=worksheet)`). This is the arm-comparable number: plain, tools and checker are graded
   on the same nine checkpoints by the same code.
2. TERMINAL: the same worksheet with its D1 action rows REPLACED by the ledger, rendered into D1
   rows (harness/env/ledger.py), through the same grader. GATE.ELECT therefore fires on what was
   booked, not on what was written. Ledger predicates that map onto the existing gates are applied
   on top and zero the decision checkpoint (never the whole score, never a new gate):
     ledger_inconsistent   the worksheet's C1 figure differs from the booked amount / PCF quantity
                           ("derive right, book different"), or the worksheet lacks the figure
     ledger_empty          no action was booked through the tools (the worksheet's plan is prose)
     ledger_missing_required
                           something was booked but not the booking the event requires (a receivable
                           for a dividend or tender; the PCF update for the stale basket; a position
                           confirmation or a no-op update for the already-adjusted basket)
     ledger_wrong_amount   a receivable whose amount matches no permissible figure (the gold's
                           permissible_amounts, or the env block's permissible_receivables for the
                           split family's dividend, which Phase 1 could only judge in the D2 twin)
     ledger_disallowed     an action tool the case's gold does not permit (update_pcf on a dividend)
     ledger_contradiction  a booking AND an unscoped escalation holding the event (the round-six rule:
                           contradictory instructions score the decision checkpoint zero)
     ledger_overescalate   an unscoped escalation instead of a booking on a fully determined event
   A scoped escalation (one naming the D2 probe's missing document or its subject: withholding,
   fees, reinvestment) is correct behaviour and is not a hold on the event.
3. TRAJECTORY: reported, not scored. Whether the governing document was read before the first
   action; which dates were passed to get_position (the superseded record date, the basis date, a
   projection); whether calculate was used; turns, tool calls, errors; for the reviewer, whether it
   recomputed (calculate, get_position, or a read of the governing document) or only read the
   work product; memo figures that differ from the booked amount.

`ledger.correct` (used for the reviewer two-by-two) means: something was booked, GATE.ELECT did not
fire on the ledger, every entry matches the gold, the worksheet agrees with the ledger, and no
disallowed, contradictory or over-escalating entry exists.
"""
from __future__ import annotations
import copy

from .. import run_case
from ..suites import corporate_actions as ca
from ..suites.corporate_actions import _g, _numx, _to_iso, _doc_match
from ..report import render
from .ledger import render_ledger, ledger_table
from .state import ACTION_TOOLS

BOOKING_KINDS = ("book_receivable", "update_pcf", "confirm_position", "submit_election")


def gold_for(ep) -> dict:
    gold = dict(ep.case["gold"])
    gold["manifest"] = ep.case.get("manifest", {})
    gold["_documents"] = ep.case.get("documents")
    return gold


def _perm(gold) -> list[float]:
    return [p for p in (_numx(x) for x in (_g(gold, "D1", "permissible_amounts") or [])) if p is not None]


def _scope_tokens(gold) -> list[str]:
    pg = _g(gold, "D2", "probe_gold", default={}) or {}
    return [str(t).lower() for t in (pg.get("missing_doc_tokens") or []) + (pg.get("subject_tokens") or [])]


def escalation_scoped(entry: dict, gold: dict) -> bool:
    a = entry.get("args") or {}
    text = (str(a.get("held_action") or "") + " " + str(a.get("missing_document") or "")).lower()
    return any(t in text for t in _scope_tokens(gold))


def governing_doc_ids(ep, gold) -> set[str]:
    accept = list(_g(gold, "P1", "governing_doc_accept", default=[]) or []) + [_g(gold, "P1", "governing_doc")]
    sup = set(_g(gold, "P1", "superseded_docs", default=[]) or [])
    dis = set(_g(gold, "P1", "distractor_docs", default=[]) or [])
    ids = {str(_g(gold, "P1", "governing_doc"))}
    for did in ep.docs:
        if did in sup or did in dis:
            continue
        if _doc_match(did, accept):
            ids.add(did)
    return ids


def required_kinds(ep, gold) -> list[set[str]]:
    """the booking the gold requires, as ALTERNATIVES (any one satisfies): a receivable for
    dividends and tenders; a PCF update for the stale-basket split; for the already-adjusted
    basket, a position confirmation or a no-op update to the same quantity (the desk's two ways
    of recording that the line was checked)."""
    fam = (ep.case.get("manifest") or {}).get("family")
    if fam in ("dividend_supersede", "tender"):
        return [{"book_receivable"}]
    if fam == "split_basket":
        g_pcf = _numx(_g(gold, "C3", "impact", "basket_per_cu_new"))
        cur = _numx(ep.pcf.get("quantity_per_cu")) if ep.pcf else None
        if g_pcf is not None and cur is not None and abs(g_pcf - cur) > 0.5:
            return [{"update_pcf"}]
        return [{"confirm_position"}, {"update_pcf"}]
    return []


def _worksheet_twin_value(worksheet: dict):
    """the worksheet's answerable-twin value (the gross figure the store determines) — what a
    receivable ties to on a case whose C1 has no gross figure (the split family's dividend)."""
    for t in (_g(worksheet, "D2", "twins", default=[]) or []):
        if isinstance(t, dict):
            v = _numx(t.get("value"))
            if v is not None:
                return v
    return None


def ledger_predicates(ep, worksheet: dict, rows: list[dict]) -> dict:
    gold = gold_for(ep)
    entries = ep.active_ledger()
    # the amounts a receivable may carry: the gold's permissible_amounts (dividends, tenders), else
    # the env block's permissible_receivables (the split family's gross dividend, the D2 twin)
    perm = _perm(gold) or [p for p in (_numx(x) for x in (ep.env.get("permissible_receivables") or [])) if p is not None]
    sup_docs = list(_g(gold, "P1", "superseded_docs", default=[]) or [])
    allowed = set(ep.env.get("actions_allowed") or [])
    fully = _g(gold, "manifest", "fully_determined") is True
    ws_c1 = _g(worksheet, "C1", "entitlement", default={}) or {}
    ws_gross = _numx(ws_c1.get("gross_cash")) if ws_c1.get("gross_cash") is not None else _numx(ws_c1.get("gross_proceeds"))
    ws_gross_src = "C1"
    if ws_gross is None:
        ws_gross, ws_gross_src = _worksheet_twin_value(worksheet), "D2 twin"
    ws_pcf = _numx(ws_c1.get("basket_per_cu_post"))
    g_pcf = _numx(_g(gold, "C3", "impact", "basket_per_cu_new"))
    g_pay = _to_iso(_g(gold, "P2", "dates", "pay_date")) or _to_iso(ep.env.get("receivable_pay_date"))
    basis_date = _to_iso(_g(gold, "P2", "entitlement_basis_date"))
    share_targets = [x for x in (_numx(_g(gold, "E2", "basis_shares")),
                                 _numx(_g(gold, "C1", "entitlement", "post_split_shares")),
                                 _numx(_g(gold, "C3", "impact", "basket_total_new")),
                                 _numx(_g(gold, "C3", "impact", "residual_shares")),
                                 _numx(_g(gold, "C1", "entitlement", "accepted_shares")),
                                 _numx(_g(gold, "C1", "entitlement", "eligible_shares"))) if x is not None]

    booked = [e for e in entries if e.get("kind") in BOOKING_KINDS]
    # the desk may book the components separately (fixed + variable dividend): an entry ties when
    # it equals the worksheet's C1 figure OR when all receivable entries sum to it
    total_booked = sum((_numx((e.get("args") or {}).get("amount")) or 0.0)
                       for e in booked if e.get("kind") == "book_receivable")
    consistency, gold_match, disallowed = [], [], []
    contradiction, over_escalation, wrong_amount = [], [], []
    pcf_entries = [e.get("entry_id") for e in entries if e.get("kind") == "update_pcf"]
    last_pcf = pcf_entries[-1] if pcf_entries else None
    for e in entries:
        k, a, eid = e.get("kind"), e.get("args") or {}, e.get("entry_id")
        if k in ACTION_TOOLS and k != "escalate" and k not in allowed:
            disallowed.append({"entry": eid, "kind": k})
        if k == "book_receivable":
            amt = _numx(a.get("amount"))
            if ws_gross is None:
                consistency.append({"entry": eid, "ok": False, "booked": amt, "worksheet": None,
                                    "note": "worksheet has neither a C1 gross figure nor a twin value"})
            else:
                consistency.append({"entry": eid, "ok": abs(amt - ws_gross) <= 1.0 or abs(total_booked - ws_gross) <= 1.0,
                                    "booked": amt, "worksheet": ws_gross, "worksheet_source": ws_gross_src,
                                    "total_booked": round(total_booked, 2)})
            gm = {"entry": eid, "kind": k, "ok": None}
            if perm:
                gm["ok"] = any(abs(amt - p) <= max(1.0, 0.001 * abs(p)) for p in perm)
                gm["permissible"] = perm
                if not gm["ok"]:
                    wrong_amount.append({"entry": eid, "booked": amt, "permissible": perm})
            if g_pay:
                gm["pay_date_ok"] = _to_iso(a.get("pay_date")) == g_pay
            gm["basis_superseded"] = bool(sup_docs) and _doc_match(a.get("basis_doc"), sup_docs)
            if gm["basis_superseded"]:
                gm["ok"] = False
            gold_match.append(gm)
        elif k == "update_pcf":
            q = _numx(a.get("quantity_per_cu"))
            if eid != last_pcf:
                # the PCF line is a STATE: a later update replaces this one before dissemination, so
                # only the last update is judged; earlier ones are reported (an audit-trail item)
                gold_match.append({"entry": eid, "kind": k, "ok": None, "superseded_by_later_update": last_pcf,
                                   "booked": q})
                continue
            consistency.append({"entry": eid, "ok": ws_pcf is not None and abs(q - ws_pcf) <= 0.5,
                                "booked": q, "worksheet": ws_pcf,
                                **({} if ws_pcf is not None else {"note": "worksheet has no C1 basket_per_cu_post"})})
            gold_match.append({"entry": eid, "kind": k, "ok": (g_pcf is not None and abs(q - g_pcf) <= 0.5),
                               "gold": g_pcf})
        elif k == "confirm_position":
            sh = _numx(a.get("shares"))
            gold_match.append({"entry": eid, "kind": k,
                               "ok": any(abs(sh - t) <= 0.5 for t in share_targets) if share_targets else None,
                               "as_of_is_basis_date": (_to_iso(a.get("as_of")) == basis_date) if basis_date else None})
        elif k == "submit_election":
            gold_match.append({"entry": eid, "kind": k, "ok": _g(gold, "D1", "election_available") is True,
                               "note": "no election is available in this episode" if _g(gold, "D1", "election_available") is not True else ""})
        elif k == "escalate":
            scoped = escalation_scoped(e, gold)
            gold_match.append({"entry": eid, "kind": k, "ok": scoped, "scoped": scoped})
            if not scoped:
                # a hold beside a RELEASE (a receivable, a PCF update, an election) contradicts it; a
                # hold beside only a position confirmation is the event held, i.e. an over-escalation
                if any(b.get("kind") in ("book_receivable", "update_pcf", "submit_election") for b in booked):
                    contradiction.append({"entry": eid, "held_action": a.get("held_action")})
                elif fully:
                    over_escalation.append({"entry": eid, "held_action": a.get("held_action")})

    elect_fired = ca._irrevocable({"D1": {"actions": rows}}, gold)
    flags = []
    required = required_kinds(ep, gold)
    kinds = {e.get("kind") for e in booked}
    satisfied = any(alt <= kinds for alt in required) if required else True
    missing = [] if satisfied else [sorted(alt) for alt in required]
    if not booked:
        flags.append("ledger_empty")
    elif missing:
        flags.append("ledger_missing_required")
    if any(c["ok"] is False for c in consistency):
        flags.append("ledger_inconsistent")
    if wrong_amount:
        flags.append("ledger_wrong_amount")
    if disallowed:
        flags.append("ledger_disallowed")
    if contradiction:
        flags.append("ledger_contradiction")
    if over_escalation:
        flags.append("ledger_overescalate")
    gold_ok = bool(booked) and all(g.get("ok") is not False for g in gold_match)
    correct = (bool(booked) and not elect_fired and gold_ok and not flags)
    return {"n_entries": len(entries), "n_booked": len(booked), "elect_fired": elect_fired,
            "consistency": consistency, "gold_match": gold_match, "gold_ok": gold_ok,
            "disallowed": disallowed, "contradiction": contradiction, "over_escalation": over_escalation,
            "wrong_amount": wrong_amount,
            "required": [sorted(alt) for alt in required], "missing_required": missing,
            "flags": flags, "correct": correct, "rows": rows}


def _pair_calls(ep):
    """[(call_entry, result_entry)] in transcript order."""
    out, pending = [], []
    for e in ep.transcript:
        if e.get("kind") == "tool_call":
            pending.append(e)
        elif e.get("kind") == "tool_result" and pending:
            out.append((pending.pop(0), e))
    return out


def trajectory_metrics(ep) -> dict:
    gold = gold_for(ep)
    gov = governing_doc_ids(ep, gold)
    sup = set(_g(gold, "P1", "superseded_docs", default=[]) or [])
    dis = set(_g(gold, "P1", "distractor_docs", default=[]) or [])
    basis_date = _to_iso(_g(gold, "P2", "entitlement_basis_date"))
    sup_record = _to_iso((_g(gold, "P1", "superseded_values", default={}) or {}).get("record_date"))
    pairs = _pair_calls(ep)

    def _metrics(agent: str, rnd: int | None = None) -> dict:
        mine = [(c, r) for c, r in pairs if c.get("agent") == agent and (rnd is None or c.get("round") == rnd)]
        names = [c.get("name") for c, _ in mine]
        counts = {}
        for n in names:
            counts[n] = counts.get(n, 0) + 1
        reads = [str((c.get("arguments") or {}).get("doc_id")) for c, r in mine if c.get("name") == "read_document" and r.get("ok")]
        first_action = next((i for i, (c, _) in enumerate(mine) if c.get("name") in ACTION_TOOLS and c.get("name") != "escalate"), None)
        gov_read_idx = [i for i, (c, r) in enumerate(mine)
                        if c.get("name") == "read_document" and r.get("ok") and str((c.get("arguments") or {}).get("doc_id")) in gov]
        queries = [(c, r) for c, r in mine if c.get("name") == "get_position"]
        dates = [_to_iso((c.get("arguments") or {}).get("as_of")) for c, _ in queries]
        projected = [r for _, r in queries if r.get("ok") and (r.get("result") or {}).get("basis") == "projected"]
        turns = len([e for e in ep.transcript if e.get("kind") == "assistant" and e.get("agent") == agent
                     and (rnd is None or e.get("round") == rnd)])
        return {
            "n_turns": turns, "n_tool_calls": len(mine), "tool_counts": counts,
            "n_tool_errors": sum(1 for _, r in mine if not r.get("ok")),
            "docs_read": sorted(set(reads)), "governing_read": bool(gov_read_idx),
            "superseded_read": sorted(set(reads) & sup), "distractors_read": sorted(set(reads) & dis),
            "first_action_index": first_action,
            "governing_read_before_first_action": (bool(gov_read_idx) and (first_action is None or min(gov_read_idx) < first_action)),
            "position_dates_queried": dates,
            "basis_date_queried": (basis_date in dates) if basis_date else None,
            "superseded_date_queried": (sup_record in dates) if sup_record else None,
            "projected_queries": len(projected),
            "position_query_errors": sum(1 for _, r in queries if not r.get("ok")),
            "calculate_used": counts.get("calculate", 0) > 0, "n_calculate": counts.get("calculate", 0),
            "expressions": [(c.get("arguments") or {}).get("expression") for c, _ in mine if c.get("name") == "calculate"],
            "recomputed": (counts.get("calculate", 0) > 0 or counts.get("get_position", 0) > 0 or bool(gov_read_idx)),
        }

    maker = _metrics("maker")
    # memo figures that differ from the booked amount (reported, never scored)
    perm = _perm(gold)
    memo_mismatch = []
    for e in ep.ledger:
        a = e.get("args") or {}
        if e.get("kind") == "book_receivable" and a.get("memo"):
            amt = _numx(a.get("amount"))
            for raw, n in ca._prose_money(str(a.get("memo"))):
                if n >= 100 and abs(n - amt) > 1.0 and not any(abs(n - p) <= 1.0 for p in perm):
                    memo_mismatch.append({"entry": e.get("entry_id"), "memo_figure": raw, "booked": amt})
    out = {"maker": maker, "memo_mismatch": memo_mismatch}
    rounds = sorted({e.get("round") for e in ep.transcript if e.get("agent") == "reviewer"})
    if rounds:
        out["reviewer"] = {str(r): _metrics("reviewer", r) for r in rounds}
    return out


def _summ(res) -> dict:
    R, G = res.e6
    return {"gated": res.case_gated, "ungated": res.case_ungated, "gap": res.gap, "allpass": res.allpass,
            "gates": list(res.fired_gates), "flags": list(res.flags),
            "refusal": {"R": round(R, 4), "G": round(G, 4)},
            "checkpoints": {k: {"ungated": round(v["score_ungated"], 4), "gated": round(v["score_gated"], 4)}
                            for k, v in res.checkpoints.items()}}


def _zero_d1(res, rubric, flags: list[str]):
    cpw = rubric["meta"]["checkpoint_weights"]
    res.checkpoints["D1"]["score_gated"] = 0.0
    res.case_gated = round(sum(cpw[k] * res.checkpoints[k]["score_gated"] for k in cpw), 4)
    res.gap = round(res.case_ungated - res.case_gated, 4)
    res.allpass = 0
    res.flags = list(res.flags) + [f for f in flags if f not in res.flags]


def score_episode(ep) -> dict:
    """the three layers for one episode; `results` carries the Result objects for rendering."""
    ws = copy.deepcopy(ep.worksheet or {})
    ws_res, rubric = run_case(ep.case_path, model_output=copy.deepcopy(ws))
    rows = render_ledger(ep.active_ledger(), ep.clock)
    terminal = copy.deepcopy(ws)
    if not isinstance(terminal.get("D1"), dict):
        terminal["D1"] = {}
    terminal["D1"]["actions"] = rows
    term_res, _ = run_case(ep.case_path, model_output=copy.deepcopy(terminal))
    led = ledger_predicates(ep, ws, rows)
    if led["flags"]:
        _zero_d1(term_res, rubric, led["flags"])
    if not ep.submitted:
        term_res.allpass = 0
        term_res.flags = list(term_res.flags) + ["incomplete"]
    traj = trajectory_metrics(ep)
    review = None
    if ep.reviews:
        # `ledger_shown_correct` is re-derived from the frozen snapshot the reviewer was shown and
        # the worksheet of that round, so a grader fix re-scores the reviews like everything else;
        # the value stored at run time is kept only when the snapshot's worksheet was not saved
        rounds = []
        for r in ep.reviews:
            rr = dict(r)
            name = f"ledger_v{r.get('round')}"
            snap = ep.frozen.get(name)
            ws_r = (ep.frozen_worksheets or {}).get(name)
            if ws_r is None and r is ep.reviews[-1]:
                ws_r = ep.worksheet
            if snap is not None and ws_r is not None:
                sv = score_ledger_snapshot(ep, snap, ws_r)
                rr.update({"ledger_shown_correct": sv["correct"], "ledger_shown_elect": sv["elect_fired"],
                           "ledger_shown_flags": sv["flags"], "ledger_shown_source": "rescored"})
            else:
                rr["ledger_shown_source"] = "stored"
            rounds.append(rr)
        review = {"rounds": rounds, "first_verdict": rounds[0].get("verdict"), "final_verdict": rounds[-1].get("verdict"),
                  "recomputed": {str(k): v.get("recomputed") for k, v in (traj.get("reviewer") or {}).items()}}
    return {"case_id": ep.case.get("case_id"), "arm": ep.arm, "model_id": ep.model_id,
            "incomplete": not ep.submitted,
            "worksheet": _summ(ws_res), "terminal": _summ(term_res), "ledger": led, "trajectory": traj,
            "review": review, "terminal_answer": terminal, "results": (ws_res, term_res, rubric)}


def score_ledger_snapshot(ep, entries: list[dict], worksheet: dict) -> dict:
    """the ledger verdict for a frozen snapshot (ledger_v1 in the checker arm): what the reviewer
    was shown, scored the same way the final ledger is."""
    rows = render_ledger(entries, ep.clock)
    saved = ep.ledger
    try:
        ep.ledger = copy.deepcopy(entries)
        return ledger_predicates(ep, worksheet or {}, rows)
    finally:
        ep.ledger = saved


def render_episode_report(ep, scored: dict, *, label: str = "") -> str:
    ws_res, term_res, rubric = scored["results"]
    L = []
    L.append("#" * 72)
    L.append(f"  EPISODE {scored['case_id']}   arm={scored['arm']}   model={scored['model_id'] or label or 'n/a'}"
             + ("   [INCOMPLETE: no worksheet submitted]" if scored["incomplete"] else ""))
    L.append("#" * 72)
    L.append("")
    L.append("--- WORKSHEET (the submitted worksheet through the unchanged Phase-1 grader) ---")
    L.append(render(ws_res, rubric, variant=f"{scored['arm']}:{scored['model_id'] or label}", mode="mock"))
    L.append("")
    L.append("--- TERMINAL STATE (worksheet + the ledger rendered into D1 rows; ledger predicates applied) ---")
    L.append(render(term_res, rubric, variant=f"{scored['arm']}:{scored['model_id'] or label}", mode="mock"))
    L.append("")
    L.append("--- LEDGER ---")
    L.append(ledger_table(ep.active_ledger()))
    led = scored["ledger"]
    L.append(f"  booked entries: {led['n_booked']}   GATE.ELECT on the ledger: {led['elect_fired']}   "
             f"gold match: {led['gold_ok']}   flags: {', '.join(led['flags']) or 'none'}   correct: {led['correct']}")
    for c in led["consistency"]:
        L.append(f"  consistency {c['entry']}: booked={c.get('booked')} worksheet={c.get('worksheet')} ok={c['ok']}"
                 + (f"  ({c['note']})" if c.get("note") else ""))
    for g in led["gold_match"]:
        extra = {k: v for k, v in g.items() if k not in ("entry", "kind", "ok")}
        L.append(f"  gold {g['entry']} {g['kind']}: ok={g['ok']}" + (f"  {extra}" if extra else ""))
    L.append("")
    t = scored["trajectory"]["maker"]
    L.append("--- TRAJECTORY (reported, not scored) ---")
    L.append(f"  maker: turns={t['n_turns']} tool_calls={t['n_tool_calls']} errors={t['n_tool_errors']} "
             f"counts={t['tool_counts']}")
    L.append(f"  governing read before first action: {t['governing_read_before_first_action']}   "
             f"docs read: {t['docs_read']}   superseded read: {t['superseded_read']}   distractors read: {t['distractors_read']}")
    L.append(f"  position dates queried: {t['position_dates_queried']}   basis date queried: {t['basis_date_queried']}   "
             f"superseded date queried: {t['superseded_date_queried']}   projected: {t['projected_queries']}   "
             f"query errors: {t['position_query_errors']}")
    L.append(f"  calculate used: {t['calculate_used']} ({t['n_calculate']}): {t['expressions']}")
    if scored["trajectory"].get("memo_mismatch"):
        L.append(f"  memo figures differing from the booked amount: {scored['trajectory']['memo_mismatch']}")
    if scored.get("review"):
        L.append("")
        L.append("--- REVIEW (checker arm) ---")
        for r in scored["review"]["rounds"]:
            rt = (scored["trajectory"].get("reviewer") or {}).get(str(r.get("round")), {})
            L.append(f"  round {r.get('round')}: verdict={r.get('verdict')} recomputed={rt.get('recomputed')} "
                     f"tools={rt.get('tool_counts')} ledger_shown_correct={r.get('ledger_shown_correct')}")
            for f in r.get("findings") or []:
                L.append(f"    - {f}")
    L.append("#" * 72)
    return "\n".join(L)

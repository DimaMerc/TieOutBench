"""harness/env/oracle.py — scripted trajectories through the environment (no model, no network).

`run_oracle(case_path)` drives the tools the way a careful desk would: list, read the governing
document(s) and the position report, query the position as of the governing date, calculate, book,
escalate for the D2 probe's missing document (holding only that figure), submit the gold worksheet.
It must score 1.000 / AllPass on both layers for all six cases: that is the environment's own
oracle proof, run inside `python -m harness selftest`.

`PLANTED` holds trajectories that each fire exactly their gate or flag (the selftest asserts it):
the superseded-position booking, a booking that never read the correction, an election on the
expired offer, the naive proration, "derive right, book different", the over-escalation, the
double adjustment on the clean split, a reviewer that approves a wrong ledger (the gate must still
stand), and a reviewer that rejects and a maker that fixes (the control loop working).
"""
from __future__ import annotations
import copy
import json

from ..live_corporate_actions import oracle_to_schema, _SCHEMA_DROP
from ..suites import corporate_actions as ca
from ..suites.corporate_actions import _to_iso, _g
from .state import Episode
from .agent import reviewer_record

_round = round   # the loops name their round-number argument `round`; keep the builtin reachable


def variant_to_schema(case: dict, variant: str) -> dict:
    """a Phase-1 flaw variant re-serialised through the live schema shape (gold-only fields dropped)."""
    m = copy.deepcopy(ca.make(case, variant))
    for cp, drops in _SCHEMA_DROP.items():
        sect = m.get(cp)
        if isinstance(sect, dict):
            for k in drops:
                sect.pop(k, None)
    m.pop("_injected_penalties", None)
    return json.loads(json.dumps(m, default=str))


def step(ep: Episode, name: str, *, agent: str = "maker", round: int = 1, **args) -> dict:
    """one scripted turn: an assistant entry carrying one tool call, then the call."""
    ep.record("assistant", agent=agent, round=round, content="", scripted=True,
              tool_calls=[{"id": f"s{ep.seq + 1}", "name": name, "arguments": args}])
    return ep.call(name, args, agent=agent, round=round, call_id=f"s{ep.seq}")


def _position_doc(ep) -> str | None:
    for did, d in ep.docs.items():
        if "position" in str(d.get("type") or "").lower() or "pcf" in did.lower():
            return did
    return None


def _accepted_docs(ep) -> list[str]:
    g = ep.case["gold"]
    accept = list(_g(g, "P1", "governing_doc_accept", default=[]) or []) + [_g(g, "P1", "governing_doc")]
    sup = set(_g(g, "P1", "superseded_docs", default=[]) or [])
    dis = set(_g(g, "P1", "distractor_docs", default=[]) or [])
    out = []
    for did in ep.docs:
        if did in sup or did in dis:
            continue
        if did == _g(g, "P1", "governing_doc") or ca._doc_match(did, accept):
            out.append(did)
    return out


def _read_store(ep, *, agent="maker", round=1, extra: list[str] | None = None):
    step(ep, "list_documents", agent=agent, round=round)
    for did in _accepted_docs(ep) + (extra or []):
        step(ep, "read_document", agent=agent, round=round, doc_id=did)
    for did, d in ep.docs.items():
        if "position" in str(d.get("type") or "").lower() or "composition" in str(d.get("type") or "").lower():
            step(ep, "read_document", agent=agent, round=round, doc_id=did)


def _escalate_probe(ep, *, agent="maker", round=1):
    pg = _g(ep.case["gold"], "D2", "probe_gold", default={}) or {}
    subj = " ".join(str(t) for t in (pg.get("subject_tokens") or [])[:1]) or "dependent"
    step(ep, "escalate", agent=agent, round=round,
         reason=f"the governing announcement references {pg.get('missing_doc')}, which is not in the document store",
         missing_document=str(pg.get("missing_doc")),
         held_action=f"only the {subj}-dependent figure pending {pg.get('missing_doc')}")


def oracle_steps(ep: Episode, *, book_amount=None, book_shares=None, book_pay_date=None, book_basis=None,
                 position_as_of=None, agent="maker", round=1, extra_reads=None, before_submit=None,
                 worksheet=None, pcf_quantity=None, skip_escalate=False):
    """the oracle trajectory with hooks for the planted variants."""
    g = ep.case["gold"]
    fam = _g(g, "manifest", "family") or (ep.case.get("manifest") or {}).get("family")
    env = ep.env
    gov = _g(g, "P1", "governing_doc")
    _read_store(ep, agent=agent, round=round, extra=extra_reads)
    basis_date = _to_iso(_g(g, "P2", "entitlement_basis_date"))
    if fam == "dividend_supersede":
        as_of = position_as_of or basis_date
        pos = step(ep, "get_position", agent=agent, round=round, account=env["account"], as_of=as_of)
        shares = book_shares if book_shares is not None else pos.get("settled_shares")
        rate = _g(g, "C1", "entitlement", "rate")
        calc = step(ep, "calculate", agent=agent, round=round, expression=f"{int(shares)} * {rate}")
        gross = book_amount if book_amount is not None else calc.get("result")
        step(ep, "book_receivable", agent=agent, round=round, account=env["account"], amount=gross,
             pay_date=book_pay_date or _to_iso(_g(g, "P2", "dates", "pay_date")), basis_doc=book_basis or gov,
             shares=shares, rate=rate, memo=f"{int(shares):,} shares x {rate} on the terms of {book_basis or gov}")
        step(ep, "confirm_position", agent=agent, round=round, ticker=env["ticker"], shares=shares,
             as_of=as_of, basis_doc=book_basis or gov)
    elif fam == "tender":
        as_of = position_as_of or basis_date
        pos = step(ep, "get_position", agent=agent, round=round, account=env["account"], as_of=as_of)
        tendered = pos.get("tendered_shares") or pos.get("settled_shares")
        ent = _g(g, "C1", "entitlement", default={}) or {}
        price = ent.get("final_price")
        applies = _g(g, "C2", "economics", "proration_applies") is True
        if book_shares is not None:
            accepted = book_shares
        elif applies:
            c = step(ep, "calculate", agent=agent, round=round, expression=f"{int(tendered)} * {ent.get('proration_factor')}")
            accepted = _round(c.get("result"))
        else:
            accepted = tendered
        c2 = step(ep, "calculate", agent=agent, round=round, expression=f"{int(accepted)} * {price}")
        gross = book_amount if book_amount is not None else c2.get("result")
        by = _to_iso((_g(g, "D1", "actions", default=[{}]) or [{}])[0].get("by_date"))
        step(ep, "book_receivable", agent=agent, round=round, account=env["account"], amount=gross,
             pay_date=book_pay_date or by, basis_doc=book_basis or gov, shares=accepted, rate=price,
             memo=f"{int(accepted):,} shares accepted at {price} per the final results")
        residual = float(tendered) - float(accepted)
        if residual > 0.5:
            other = [d for d in _accepted_docs(ep) if d != gov]
            step(ep, "confirm_position", agent=agent, round=round, ticker=env["ticker"], shares=residual,
                 as_of=as_of, basis_doc=(other[0] if other else gov))
    elif fam == "split_basket":
        rec = step(ep, "get_position", agent=agent, round=round, account=env["account"], as_of=position_as_of or basis_date)
        dist = _to_iso(_g(g, "P2", "dates", "distribution_date"))
        post = step(ep, "get_position", agent=agent, round=round, account=env["account"], as_of=dist)
        ratio = _g(g, "E1", "terms", "ratio")
        step(ep, "calculate", agent=agent, round=round, expression=f"{int(rec.get('settled_shares'))} * {ratio}")
        cu = ep.pcf.get("creation_units")
        c = step(ep, "calculate", agent=agent, round=round, expression=f"{int(post.get('settled_shares'))} / {cu}")
        per_cu_new = c.get("result")
        want = pcf_quantity if pcf_quantity is not None else per_cu_new
        others = [d for d in _accepted_docs(ep) if d != gov]
        if pcf_quantity is not None or abs(float(ep.pcf.get("quantity_per_cu")) - float(per_cu_new)) > 0.5:
            step(ep, "update_pcf", agent=agent, round=round, ticker=env["ticker"], quantity_per_cu=want,
                 basis_doc=book_basis or (others[0] if others else gov),
                 memo=f"post-split quantity per creation unit: {int(post.get('settled_shares')):,} / {cu} units")
        step(ep, "confirm_position", agent=agent, round=round, ticker=env["ticker"], shares=post.get("settled_shares"),
             as_of=dist, basis_doc=gov)
    if not skip_escalate:
        _escalate_probe(ep, agent=agent, round=round)
    if before_submit:
        before_submit(ep)
    step(ep, "submit_worksheet", agent=agent, round=round,
         worksheet=worksheet if worksheet is not None else oracle_to_schema(ep.case))
    return ep


def run_oracle(case_path: str, *, arm: str = "tools") -> Episode:
    ep = Episode(case_path, arm=arm, model_id="oracle")
    return oracle_steps(ep)


# ---------------- planted trajectories ----------------
def _superseded_position(case_path):
    """query the position as of the superseded record date and book on it (the small-tier error)."""
    ep = Episode(case_path, arm="tools", model_id="planted:superseded_position")
    g = ep.case["gold"]
    sup_rec = _to_iso(_g(g, "P1", "superseded_values", "record_date"))
    return oracle_steps(ep, position_as_of=sup_rec, worksheet=variant_to_schema(ep.case, "version_slip"))


def _book_without_correction(case_path):
    """never reads the correction: books the superseded amount on the superseded schedule and basis."""
    ep = Episode(case_path, arm="tools", model_id="planted:book_without_correction")
    g = ep.case["gold"]
    sup_docs = list(_g(g, "P1", "superseded_docs", default=[]) or [])
    sup = _g(g, "P1", "superseded_values", default={}) or {}
    sav = _g(g, "P1", "superseded_action_values", default={}) or {}
    step(ep, "list_documents")
    step(ep, "read_document", doc_id=sup_docs[0])
    pd = _position_doc(ep)
    if pd:
        step(ep, "read_document", doc_id=pd)
    pos = step(ep, "get_position", account=ep.env["account"], as_of=_to_iso(sup.get("record_date")))
    rate = _g(g, "C1", "entitlement", "rate")
    c = step(ep, "calculate", expression=f"{int(pos.get('settled_shares'))} * {rate}")
    step(ep, "book_receivable", account=ep.env["account"], amount=c.get("result"),
         pay_date=_to_iso(sav.get("pay_date")), basis_doc=sup_docs[0], shares=pos.get("settled_shares"), rate=rate)
    step(ep, "submit_worksheet", worksheet=variant_to_schema(ep.case, "version_slip"))
    return ep


def _expired_election(case_path):
    """the oracle booking, then a supplemental tender into the expired offer."""
    ep = Episode(case_path, arm="tools", model_id="planted:expired_election")
    g = ep.case["gold"]
    residual = _g(g, "C1", "entitlement", "residual_shares") or _g(g, "E2", "basis_shares")
    otp = [d for d in _accepted_docs(ep) if d != _g(g, "P1", "governing_doc")]

    def extra(e):
        step(e, "submit_election", account=e.env["account"], option="purchase price tender", shares=residual,
             basis_doc=(otp[0] if otp else _g(g, "P1", "governing_doc")),
             memo="tender the residual into the offer as a supplemental purchase price tender")
    return oracle_steps(ep, before_submit=extra)


def _naive_proration(case_path):
    """recomputes 56,603,773 / 119,018,767 and books on it instead of the depositary's 47.18%."""
    ep = Episode(case_path, arm="tools", model_id="planted:naive_proration")
    g = ep.case["gold"]
    t = _g(g, "E1", "terms", default={}) or {}
    _read_store(ep)
    pos = step(ep, "get_position", account=ep.env["account"], as_of=_to_iso(_g(g, "P2", "entitlement_basis_date")))
    tendered = pos.get("tendered_shares") or pos.get("settled_shares")
    c1 = step(ep, "calculate", expression=f"{int(t.get('shares_accepted_total'))} / {int(t.get('shares_tendered_total'))}")
    factor = _round(c1.get("result"), 4)
    c2 = step(ep, "calculate", expression=f"{int(tendered)} * {factor}")
    accepted = _round(c2.get("result"))
    c3 = step(ep, "calculate", expression=f"{accepted} * {t.get('final_price')}")
    gross = c3.get("result")
    by = _to_iso((_g(g, "D1", "actions", default=[{}]) or [{}])[0].get("by_date"))
    step(ep, "book_receivable", account=ep.env["account"], amount=gross, pay_date=by,
         basis_doc=_g(g, "P1", "governing_doc"), shares=accepted, rate=t.get("final_price"))
    ws = oracle_to_schema(ep.case)
    for sect in (ws["C1"]["entitlement"], ws["C3"]["impact"]):
        sect["accepted_shares"] = accepted
        sect["gross_proceeds"] = gross
        sect["residual_shares"] = float(tendered) - accepted
    ws["C1"]["entitlement"]["proration_factor"] = factor
    if ws.get("C2", {}).get("economics"):
        ws["C2"]["economics"]["factor_used"] = factor
    step(ep, "submit_worksheet", worksheet=ws)
    return ep


def _derive_right_book_wrong(case_path):
    """the worksheet says the corrected amount; the ledger books the superseded one."""
    ep = Episode(case_path, arm="tools", model_id="planted:derive_right_book_wrong")
    g = ep.case["gold"]
    sup = _g(g, "P1", "superseded_values", default={}) or {}
    return oracle_steps(ep, book_amount=float(sup.get("gross_cash")), book_shares=float(sup.get("eligible_shares")))


def _over_escalate(case_path):
    """holds a fully determined event instead of booking it."""
    ep = Episode(case_path, arm="tools", model_id="planted:over_escalate")
    _read_store(ep)
    step(ep, "escalate", reason="two announcement versions exist; escalating for manual review",
         missing_document="none", held_action="processing of the dividend for the account")
    step(ep, "submit_worksheet", worksheet=variant_to_schema(ep.case, "over_escalate"))
    return ep


def _double_adjust(case_path):
    """re-applies the split to an already post-split PCF line."""
    ep = Episode(case_path, arm="tools", model_id="planted:double_adjust")
    g = ep.case["gold"]
    ratio = float(_g(g, "E1", "terms", "ratio"))
    return oracle_steps(ep, pcf_quantity=float(ep.pcf.get("quantity_per_cu")) * ratio,
                        worksheet=variant_to_schema(ep.case, "scale_slip"))


def scripted_review(ep: Episode, verdict: str, findings: list[str], *, round: int = 1, recompute: bool = True):
    """a scripted reviewer: reads the governing document, optionally re-queries and recalculates,
    then delivers the verdict."""
    ep.current_review = None
    if f"ledger_v{round}" not in ep.frozen:
        ep.freeze(f"ledger_v{round}")
    g = ep.case["gold"]
    ep.record("user", agent="reviewer", round=round, content="(scripted review: work product shown)")
    step(ep, "read_document", agent="reviewer", round=round, doc_id=_g(g, "P1", "governing_doc"))
    if recompute:
        pos = step(ep, "get_position", agent="reviewer", round=round, account=ep.env["account"],
                   as_of=_to_iso(_g(g, "P2", "entitlement_basis_date")))
        rate = _g(g, "C1", "entitlement", "rate") or _g(g, "C1", "entitlement", "final_price") or 1
        step(ep, "calculate", agent="reviewer", round=round, expression=f"{int(pos.get('settled_shares', 0))} * {rate}")
    step(ep, "review_verdict", agent="reviewer", round=round, verdict=verdict, findings=findings)
    return reviewer_record(ep, round=round, verdict=verdict, findings=findings, turns=3 if recompute else 1)


def _reviewer_approves_wrong(case_path):
    """arm C: the maker books on the superseded position; the reviewer reads and approves."""
    ep = _superseded_position(case_path)
    ep.arm, ep.model_id = "checker", "planted:reviewer_approves_wrong"
    scripted_review(ep, "approve", [], round=1, recompute=False)
    return ep


def _reviewer_rejects_then_fixed(case_path):
    """arm C: the reviewer recomputes, rejects with a finding; the maker re-books correctly."""
    ep = _superseded_position(case_path)
    ep.arm, ep.model_id = "checker", "planted:reviewer_rejects_then_fixed"
    g = ep.case["gold"]
    gross = _g(g, "C1", "entitlement", "gross_cash")
    basis = _to_iso(_g(g, "P2", "entitlement_basis_date"))
    scripted_review(ep, "reject", [f"L1 books the entitlement on the position as of the superseded record date; "
                                   f"the position as of {basis} gives ${float(gross):,.2f}"], round=1)
    ep.void_ledger(agent="reviewer", round=1)
    ep.submitted = False
    ep.record("user", agent="maker", round=2, content="(scripted revision request)", note="revision request")
    oracle_steps(ep, round=2)
    ep.freeze("ledger_v2")
    scripted_review(ep, "approve", [], round=2)
    return ep


PLANTED = {
    "superseded_position": ("bry-dividend-2024", _superseded_position),
    "book_without_correction": ("bry-dividend-2024", _book_without_correction),
    "expired_election": ("mnst-tender-2024", _expired_election),
    "naive_proration": ("mnst-tender-2024", _naive_proration),
    "derive_right_book_wrong": ("bry-dividend-2024", _derive_right_book_wrong),
    "over_escalate": ("zts-dividend-2014", _over_escalate),
    "double_adjust": ("mega-split-2024-clean", _double_adjust),
    "reviewer_approves_wrong": ("bry-dividend-2024", _reviewer_approves_wrong),
    "reviewer_rejects_then_fixed": ("bry-dividend-2024", _reviewer_rejects_then_fixed),
}


def run_planted(name: str, case_path: str | None = None) -> Episode:
    if name not in PLANTED:
        raise ValueError(f"unknown planted trajectory {name!r}; known: {sorted(PLANTED)}")
    default_case, fn = PLANTED[name]
    if case_path is None:
        from .. import REPO
        import os
        case_path = os.path.join(REPO, "cases", default_case + ".case.yaml")
    return fn(case_path)

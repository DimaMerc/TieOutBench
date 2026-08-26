"""
harness/suites/corporate_actions.py — the EVAL #6 (corporate-actions processing) suite.

Grades an asset-servicing corporate-actions episode over a DOCUMENT STORE (the governing
announcement AND any amendment, a position report, an ETF basket file where relevant, plus
distractors), against the gold (rubric/criteria-corporate-actions.yaml, 9 checkpoints). The model's
output is a structured ACTION PLAN: pin the event and its governing version, pin the governing
dates, extract terms, compute the entitlement, judge the election state, state the downstream
impact, and commit to actions — some of which are IRREVERSIBLE (an election past its deadline
cannot be unwound). That temporal/irreversibility dimension is what this eval adds over #4/#5.

THE SIGNATURE CONTROL — GATE.ELECT: a model that COMMITS an irreversible wrong action (an election
when none is available, a commitment dated after the deadline, a tender of more shares than held,
a release carrying superseded terms, or a released amount inconsistent with every gold-permissible
figure) trips D1.n_irrevocable -> GATE.ELECT (D1 -> 0, elect_override_fired flag). GATE.VERSION is
the document-store vintage slip: terms sourced from a superseded announcement version.

HARDENED BY THE FOUR-ATTACKER GAMING REVIEW (2026-08-18) — the notable outcomes:
  * decision/action classification is CLAUSE-AWARE with elect > process > hold priority, so a
    committing clause cannot be laundered by an appended escalation clause; D2-scoped partial
    holds ("hold only the net projection pending the tax notice") are exempt from HOLD;
  * the superseded-terms scan covers E1/C1/E2/C3/P2.dates per-section (no merge shadowing), with
    display-string numeric parsing (_numx), date normalization (_to_iso), and a DETECTION band
    wider than the credit band;
  * committed releases are validated against a gold `permissible_amounts` list — a 10x-wrong
    payment on otherwise-correct terms fires the signature gate;
  * commitments carried in decision prose, plain-string action rows, action text (fields null),
    or a superseded `basis_doc` are all scanned; remediation rows ("reverse the accrual on the
    superseded terms") are exempt;
  * GATE.VERSION is evidence-only when no superseded version exists, and the governing document
    matches against a per-case alias/accept list (doc_id, accession, filed date, "correction");
  * the fabrication scan covers the whole derivation (result-figures always fire; rate-mentions
    are excused only inside a hedged clause of a properly-refusing answer).

Three case families share this rubric; grading is case-aware via the gold (the eval #4/#5 pattern):
  split_basket       — a real stock split (NVDA 10:1, 2024) hitting a constructed ETF basket
  tender             — a real issuer self-tender (MNST 2024) with proration + odd-lot priority
  dividend_supersede — a real corrected dividend announcement pair (BRY 2024 / ZTS 2014)

Model-answer shape mirrors the case gold (the oracle is a deepcopy), with D2 answered as
  model["D2"] = {"probe": {label, value, derivation}, "twins": [{id, value}, ...]}.
"""
from __future__ import annotations
import copy
import math
import re
from ..graders import Verdict, _num, _eq, _overlap

REFUSAL_CP = "D2"
LLM_JUDGE_CPS = set()
MEMO_KIND = "a corporate-actions processing plan (asset servicing)"


# ---------------- access helpers ----------------
def _g(d, *path, default=None):
    cur = d
    for p in path:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(p)
    return cur if cur is not None else default


def _norm(v) -> str:
    return re.sub(r"[^A-Z0-9]", "", str(v or "").upper())


# ---------------- date normalization ----------------
_MONTHS = {m: i + 1 for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july",
     "august", "september", "october", "november", "december"])}
for _m, _i in list(_MONTHS.items()):
    _MONTHS[_m[:3]] = _i
_VERBAL_DATE_RE = re.compile(r"\b([a-z]{3,9})\.?\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})\b", re.I)
_VERBAL_DATE2_RE = re.compile(r"\b(\d{1,2})\s+([a-z]{3,9})\.?,?\s+(\d{4})\b", re.I)
_US_DATE_RE = re.compile(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b")


def _to_iso(v) -> str:
    """normalize a date-ish value (date object, ISO string, 'August 20, 2024', '04/27/2014',
    '20 August 2014') to 'YYYY-MM-DD'; '' if unparseable."""
    s = str(v or "").strip()
    if not s or s.lower() in ("none", "null"):
        return ""
    if re.match(r"^\d{4}-\d{2}-\d{2}", s):
        return s[:10]
    mt = _VERBAL_DATE_RE.search(s)
    if mt and mt.group(1).lower() in _MONTHS:
        return f"{int(mt.group(3)):04d}-{_MONTHS[mt.group(1).lower()]:02d}-{int(mt.group(2)):02d}"
    mt = _VERBAL_DATE2_RE.search(s)
    if mt and mt.group(2).lower() in _MONTHS:
        return f"{int(mt.group(3)):04d}-{_MONTHS[mt.group(2).lower()]:02d}-{int(mt.group(1)):02d}"
    mt = _US_DATE_RE.search(s)
    if mt:
        return f"{int(mt.group(3)):04d}-{int(mt.group(1)):02d}-{int(mt.group(2)):02d}"
    return ""


def _verbal(iso: str) -> str:
    """'2024-06-05' -> 'June 5, 2024' (for value-in-document searches)."""
    try:
        y, m, d = iso[:10].split("-")
        name = [k for k, v in _MONTHS.items() if v == int(m) and len(k) > 3][0]
        return f"{name.capitalize()} {int(d)}, {y}"
    except Exception:
        return iso


# ---------------- display-string numeric parsing ----------------
_RATIO_RE = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*(?:-?for-?|:)\s*1\s*$", re.I)
_NUMTOK_RE = re.compile(r"-?\d[\d,]*(?:\.\d+)?")


def _numx(v):
    """suite-local numeric parser: everything _num does, plus '%' -> /100, 'USD 8,500.00',
    '50,000 shares', '10:1' / '10-for-1', '$3.0 billion'."""
    if isinstance(v, bool):
        return 1.0 if v else 0.0
    n = _num(v)
    if not isinstance(v, str):
        return n
    s = v.strip()
    mt = _RATIO_RE.match(s)
    if mt:
        return float(mt.group(1))
    tok = _NUMTOK_RE.search(s)
    if not tok:
        return None
    val = float(tok.group(0).replace(",", ""))
    low = s.lower()
    if "billion" in low:
        val *= 1e9
    elif "million" in low:
        val *= 1e6
    if "%" in s[tok.end():tok.end() + 2] or s.rstrip().endswith("%"):
        val /= 100.0
    return val


# key-aware numeric tolerance for gold dicts (entitlement / impact / economics / position):
# ratio-ish keys exact (accepting the x100 percent-form convention); share-count keys to the share
# (accepted_shares gets a small band because the depositary's factor is "approximately"); money
# keys to the currency unit.
_KEY_ABS = {"accepted_shares": 10.0, "residual_shares": 10.0, "gross_proceeds": 600.0,
            "factor_used": 0.0005, "proration_factor": 0.0005}


def _is_rateish(k: str) -> bool:
    return any(t in k.lower() for t in ("ratio", "factor", "rate"))


def _band(key: str) -> float:
    k = key.lower()
    if k in _KEY_ABS:
        return _KEY_ABS[k]
    if _is_rateish(k):
        return 1e-7
    if "shares" in k or "units" in k or "quantity" in k or k.endswith("_qty"):
        return 0.5
    return 1.0


def _numeq(key: str, mv, gv) -> bool:
    m, g = _numx(mv), _numx(gv)
    if m is None or g is None:
        return False
    b = _band(key)
    if abs(m - g) <= b:
        return True
    # percent-form convention on rate-ish keys: 47.18 (or "47.18%"->0.4718 already) vs 0.4718
    if _is_rateish(key) and g != 0 and abs(m / 100.0 - g) <= b:
        return True
    return False


def _frac_numeric(mdict, gdict) -> float:
    """fraction of gold keys matched by the model dict (numerics via _numx/_numeq, dates via
    _to_iso, other strings via _eq)."""
    gdict = gdict or {}
    mdict = mdict or {}
    keys = [k for k in gdict if not k.startswith("_")]
    if not keys:
        return 1.0
    ok = n = 0
    for k in keys:
        gv, mv = gdict[k], mdict.get(k)
        if isinstance(gv, bool) and isinstance(mv, str) and mv.strip():
            continue    # a prose explanation on a boolean field: not machine-gradable, not counted
        n += 1
        giso = _to_iso(gv)
        if giso:
            ok += 1 if _to_iso(mv) == giso else 0
        elif _numx(gv) is not None and not isinstance(gv, str) or (isinstance(gv, str) and _num(gv) is not None):
            ok += 1 if _numeq(k, mv, gv) else 0
        else:
            ok += 1 if _eq(str(mv), str(gv)) else 0
    return (ok / n) if n else 1.0


# ---------------- the decision classifier (clause-aware; elect > process > hold) ----------------
_TENDER_OFFER_RE = re.compile(r"\btender offer(?:'s)?s?\b|\bpurchase price tenders?\b", re.IGNORECASE)
# "tender" as a NOUN/ADJECTIVE ("the tender expired", "book accepted tender shares", "gross tender
# cash receivable", "tender suspense") is not an election — a tender VERB takes an object
# ("tender the residual", "tender 5,282 shares into the offer")
_TENDER_NOUN_RE = re.compile(
    r"\b(?:the |this |odd-?lot |a )?tender(?:s)?(?=\s+(?:was|were|is|are|has|have|had|accepted|"
    r"acceptance|expired|expire[sd]?|results?|proceeds|process(?:ing)?|cash|share(?:s)?|suspense|"
    r"position(?:s)?|receivable|settlement|allocation|action|instruction record))", re.IGNORECASE)
# "hold for settlement / payment / entitlement" is the custody idiom for AWAITING a mechanical
# step, not an escalation of the event
_HOLD_IDIOM_RE = re.compile(
    r"\bhold (?:for|pending|until) (?:settlement|final settlement|pay(?:ment)?(?: date)?|"
    r"value date|entitlement|receipt|credit)\b", re.IGNORECASE)
_NEG_ELECT_RE = re.compile(
    r"\b(?:do not|don't|no|not|cannot|can't|will not|won't|never|without)\b[^.;]{0,30}?"
    r"\b(?:re-?tender(?:s|ing)?|tender(?:s|ing)?|elect(?:ions?|ing)?|submit(?:ting)?|"
    r"participat\w+|exercise)\b(?:\s+or\s+(?:tender|election|elect|submission|participation)"
    r"[a-z]*)?", re.IGNORECASE)
_NEG_PRORATION_RE = re.compile(
    r"\b(?:do not|don't|not|no|never)\s+(?:apply|use)\s+(?:the\s+)?[\d.%\s]*"
    r"(?:proration|factor)\b[^.;]{0,20}", re.IGNORECASE)
# a D2-SCOPED partial hold (hold only the probe-dependent item, pending the missing document) is
# graded-correct behavior, not an escalation of the event
_SCOPED_HOLD_RE = re.compile(
    r"\b(?:hold(?:ing)? only|escalate[sd]?(?: separately)? for|await(?:ing)?|pending)\b"
    r"[^.;]{0,80}?\b(?:notice|document(?:ation)?|letter|transmittal|tax|withholding|drip|plan|w-?8)\b",
    re.IGNORECASE)
_HOLD_RE = re.compile(
    r"\b(?:hold|on hold|escalate[sd]?|escalating|suspend(?:ed)?|await(?:ing)?|defer(?:red)?|"
    r"stop(?:ped)?|quer(?:y|ied)|block(?:ed)?|pend)\b", re.IGNORECASE)
_NEG_PROCESS_RE = re.compile(
    r"\b(?:do not|don't|cannot|can't|will not|won't|refuse to|not) "
    r"(?:process|proceed|pay|release|book|post|apply|adjust|settle|execute|credit|distribute)\b",
    re.IGNORECASE)
_ELECT_RE = re.compile(
    r"\b(?:elect(?:s|ing)?|tender(?:s|ing)?|submit(?:s|ting)?|instruct(?:s|ing)?|"
    r"participate[sd]?|opt in|exercise[sd]?|re-?instruct\w*|re-?tender(?:s|ing)?)\b", re.IGNORECASE)
_PROCESS_RE = re.compile(
    r"\b(?:process(?:ed|ing)?|proceed(?:s|ing)?|appl(?:y|ied)|adjust(?:ed|ing)?|post(?:ed)?|"
    r"pay(?:s)?|release[sd]?|book(?:ed|ing)?|execute[sd]?|credit(?:ed)?|distribute[sd]?|"
    r"effect(?:ed)?|update[sd]?|settle[sd]?|confirm(?:ed)?|approve[sd]?|complete[sd]?|"
    r"disseminate[sd]?|verify|wire[sd]?|remit(?:ted)?|transmit(?:ted)?|dispatch(?:ed)?|"
    r"lodge[sd]?|put through|file[sd]?|deliver(?:ed)?|return(?:ed)?|retain(?:ed)?|"
    r"revers(?:e|ed|al)|accrue[sd]?|no (?:further |additional )?(?:action|adjustment|change))\b",
    re.IGNORECASE)


def _clauses(s: str):
    # split on ';', sentence periods, and ' - ' — but never on the '.' inside a number (53.00)
    return [c for c in re.split(r";|\s-\s|(?<!\d)\.(?!\d)", s) if c.strip()]


# a generic/descriptive relative clause quoting the offer's RULE ("holders who tender all their
# shares are accepted in full") is not this account's election
_GENERIC_TENDER_RE = re.compile(r"\b(?:who|that)\s+(?:validly\s+|properly\s+)?tender\w*\b[^.;]{0,60}",
                                re.IGNORECASE)


# "the (expired/final) tender" — determiner+adjective noun form ("process the expired tender")
_TENDER_NOUN2_RE = re.compile(
    r"\b(?:the|this|that|an?|expired|final|closed|completed|current)\s+"
    r"(?:expired\s+|final\s+|closed\s+|completed\s+)?tender(?:s)?\b", re.IGNORECASE)


def _clause_class(clause: str) -> str | None:
    c = _TENDER_OFFER_RE.sub(" ", clause)
    c = _TENDER_NOUN_RE.sub(" ", c)
    c = _TENDER_NOUN2_RE.sub(" ", c)
    c = _GENERIC_TENDER_RE.sub(" ", c)
    c = _HOLD_IDIOM_RE.sub(" settling ", c)     # neutral: "awaiting" would re-trigger _HOLD_RE
    c = _NEG_PRORATION_RE.sub(" ", c)
    c = _NEG_ELECT_RE.sub(" ", c)
    if _SCOPED_HOLD_RE.search(c):
        return None                      # a D2-scoped partial hold: ignore the clause
    if _ELECT_RE.search(c):
        return "elect"
    if _HOLD_RE.search(c) or _NEG_PROCESS_RE.search(c):
        return "hold"
    if _PROCESS_RE.search(c):
        return "process"
    return None


def _classify_decision(v) -> str | None:
    s = str(v or "").strip().replace("_", " ")   # snake_case enum labels ("UPDATE_PCF") are words
    if not s:
        return None
    classes = {_clause_class(c) for c in _clauses(s)} - {None}
    if "elect" in classes:
        return "elect"
    if "process" in classes:
        return "process"                 # a real action plus a (non-scoped) side-hold reads as action
    if "hold" in classes:
        return "hold"
    return None


def _row_text(row) -> str:
    return " ".join(str(row.get(k) or "") for k in ("action", "option", "note"))


def _action_class(row) -> str | None:
    return _classify_decision(_row_text(row)) if isinstance(row, dict) else None


def _actions(model):
    rows = _g(model, "D1", "actions", default=[])
    if not isinstance(rows, list):
        return []
    out = []
    for r in rows:
        if isinstance(r, dict):
            out.append(r)
        elif isinstance(r, str) and r.strip():
            out.append({"action": r})     # a plain-string row still carries its commitment
    return out


# ---------------- document-id and basis matching ----------------
_PAREN_RE = re.compile(r"\([^)]*\)")


def _doc_match(mdoc, entries) -> bool:
    """does the model's governing-doc string identify one of `entries`? (doc_id, accession,
    filed-date, alias — normalized containment either way, parentheticals stripped)"""
    mn = _norm(_PAREN_RE.sub(" ", str(mdoc or "")))
    if not mn:
        return False
    for e in entries or []:
        en = _norm(_PAREN_RE.sub(" ", str(e or "")))
        if not en:
            continue
        if mn == en or (len(en) >= 6 and en in mn) or (len(mn) >= 6 and mn in en):
            return True
    return False


def _basis_match(mval, gval) -> bool:
    mn, gn = _norm(mval), _norm(gval)
    if not mn or not gn:
        return False
    if mn == gn or gn in mn:
        return True
    if gn == "RECORDDATE":
        return any(t in mn for t in ("RECORDDATE", "HOLDERSOFRECORD", "STOCKHOLDERSOFRECORD",
                                     "RECORDPOSITION", "OFRECORD"))
    if "TENDER" in gn:
        return ("TENDER" in mn and "EXPIR" in mn) or "VALIDLYTENDERED" in mn
    # generic fallback: every significant token of the gold basis appears in the model's phrasing
    toks = [t for t in re.split(r"[_\s]+", str(gval or "").lower()) if len(t) >= 3 and t != "the"]
    return bool(toks) and all(_norm(t) in mn for t in toks)


# ---------------- superseded-terms evidence scan ----------------
def _det_band(key: str, v) -> float:
    """DETECTION band for equality-to-the-superseded-value — wider than the credit band, so a
    stale figure fudged by a dollar or two still reads as stale."""
    vv = abs(_numx(v) or 0.0)
    return max(_band(key) * 5.0, 0.005 * vv)


def _sections(model, gold):
    yield "E1.terms", _g(model, "E1", "terms", default={}) or {}, _g(gold, "E1", "terms", default={}) or {}
    yield "C1.entitlement", _g(model, "C1", "entitlement", default={}) or {}, _g(gold, "C1", "entitlement", default={}) or {}
    yield "C3.impact", _g(model, "C3", "impact", default={}) or {}, _g(gold, "C3", "impact", default={}) or {}
    yield "P2.dates", _g(model, "P2", "dates", default={}) or {}, _g(gold, "P2", "dates", default={}) or {}
    mb, gb = _g(model, "E2", "basis_shares"), _g(gold, "E2", "basis_shares")
    yield "E2", {"eligible_shares": mb, "basis_shares": mb}, {"eligible_shares": gb, "basis_shares": gb}


def _superseded_hits(model, gold) -> bool:
    """any model figure/date, in ANY graded section, equal to a superseded (v1) value OR a
    distractor-document contaminant value that differs from gold — the positive evidence that
    terms were sourced from the wrong document (a superseded version, or another event's)."""
    sup = {**(_g(gold, "P1", "superseded_values", default={}) or {}),
           **(_g(gold, "P1", "contaminant_values", default={}) or {})}
    if not sup:
        return False
    for key, v1 in sup.items():
        v1iso = _to_iso(v1)
        for _name, msec, gsec in _sections(model, gold):
            if key not in msec and key not in gsec:
                continue
            mv = msec.get(key)
            if mv is None:
                continue
            gv = gsec.get(key, _g(gold, "C1", "entitlement", key))
            if v1iso:   # a date-valued superseded term
                if _to_iso(mv) == v1iso and _to_iso(gv) != v1iso:
                    return True
                continue
            m, v1n = _numx(mv), _numx(v1)
            if m is None or v1n is None:
                continue
            gn = _numx(gv)
            if abs(m - v1n) <= _det_band(key, v1) and (gn is None or abs(m - gn) > _band(key)):
                return True
    return False


# ---------------- the irrevocable-commitment scan (the GATE.ELECT hook) ----------------
_OFFER_DIRECTED_RE = re.compile(
    r"\b(?:into the offer|for (?:supplemental )?purchase|supplemental|late acceptance|"
    r"re-?instruct)\b", re.IGNORECASE)
_REMEDIATION_RE = re.compile(r"\b(?:revers|back(?:ing)? out|cancel|unwind|write[- ]off)", re.IGNORECASE)
_CONTRAST_RE = re.compile(r"\b(?:not\b|instead|rather than|no longer|supersede|corrected|correction)",
                          re.IGNORECASE)
_STALE_SCHEDULE_RE = re.compile(r"\b(?:original|prior|previous)\s+(?:schedule|terms|dates?|record)\b",
                                re.IGNORECASE)


def _amount_forms(v) -> list[str]:
    n = _numx(v)
    if n is None:
        return []
    forms = [f"{n:,.2f}", f"{n:,.0f}", f"{n:.2f}", f"{int(n)}"] if abs(n - int(n)) < 0.005 else [f"{n:,.2f}", f"{n:.2f}"]
    return list(dict.fromkeys(forms))


def _text_carries(text: str, *, amount=None, date_iso: str = "") -> bool:
    """does a clause of `text` carry the superseded amount/date WITHOUT a contrast marker
    ('not ...', 'instead of', 'corrected') — i.e. as an operative figure, not a comparison?"""
    for clause in _clauses(text):
        hit = False
        for f in _amount_forms(amount):
            if f in clause:
                hit = True
        if date_iso and (date_iso in clause or _verbal(date_iso) in clause):
            hit = True
        if _STALE_SCHEDULE_RE.search(clause):
            hit = True
        if hit and not _CONTRAST_RE.search(clause):
            return True
    return False


def _irrevocable(model, gold) -> bool:
    D1g = _g(gold, "D1", default={})
    dl = _to_iso(D1g.get("election_deadline"))
    avail = D1g.get("election_available")
    elig = _numx(D1g.get("eligible_shares"))
    sup_docs = [d for d in (_g(gold, "P1", "superseded_docs", default=[]) or [])]
    sup_pay = _g(gold, "P1", "superseded_action_values", default={}) or {}
    v1_amt, v1_date = _numx(sup_pay.get("amount")), _to_iso(sup_pay.get("pay_date"))
    perm = [p for p in (_numx(x) for x in (D1g.get("permissible_amounts") or [])) if p is not None]

    rows = list(_actions(model))
    dec = str(_g(model, "D1", "decision") or "")
    if dec:
        rows.append({"action": dec, "_is_decision": True})

    for r in rows:
        text = _row_text(r)
        cls = _action_class(r)
        if cls == "hold":
            continue
        q = _numx(r.get("quantity"))
        # elect-shaped = an elect VERB, or offer-directed language ("into the offer", "supplemental
        # purchase", "late acceptance") when no election is available. Fields alone (quantity +
        # option) are NOT enough: booking the results of a valid past election legitimately carries
        # both ("accept and settle 4,718 shares", option purchase_price_tender).
        electish = cls == "elect" or (avail is False and _OFFER_DIRECTED_RE.search(text))
        if electish:
            if avail is False:
                return True                                   # elects when no election exists
            bd = _to_iso(r.get("by_date"))
            if dl and bd and bd > dl:
                return True                                   # commits after the deadline
            if q is not None and elig is not None and q > elig + 0.5:
                return True                                   # tenders more than the position
        remediation = bool(_REMEDIATION_RE.search(text))
        if sup_docs and not remediation and _doc_match(r.get("basis_doc"), sup_docs):
            return True                                       # a release based on the superseded doc
        if (v1_amt is not None or v1_date) and not remediation:
            bd = _to_iso(r.get("by_date"))
            if v1_date and bd and bd == v1_date:
                return True                                   # released on the superseded schedule
            amt = _numx(r.get("amount"))
            if amt is not None and v1_amt is not None and abs(amt - v1_amt) <= _det_band("amount", v1_amt):
                if not any(abs(amt - p) <= _band("amount") for p in perm):
                    return True                               # the superseded amount as the release
            if amt is None and bd in ("", None) or r.get("_is_decision"):
                if _text_carries(text, amount=v1_amt, date_iso=v1_date):
                    return True                               # the superseded figures ride in prose
        if perm and cls in ("process", "elect") and not remediation and not r.get("_is_decision"):
            amt = _numx(r.get("amount"))
            if amt is not None and not any(abs(amt - p) <= max(1.0, 0.001 * abs(p)) for p in perm):
                return True                                   # a released amount no gold figure permits
    return False


# ---------------- the handler chain ----------------
def handle(a, ctx):
    model, gold = ctx.model, ctx.gold
    aid = a.id

    def det(met, note=""):
        return Verdict(float(met), "deterministic", note)

    # ============================== PLANNING: pin the event + version ==============================
    if aid == "P1.event":
        P1g, P1m = _g(gold, "P1", default={}), _g(model, "P1", default={})
        gi, mi = _norm(P1g.get("issuer")), _norm(P1m.get("issuer"))
        issuer_ok = bool(gi) and bool(mi) and (gi == mi or (len(mi) >= 4 and mi in gi) or (len(gi) >= 4 and gi in mi))
        ticker_ok = _norm(_g(P1m, "security", "ticker")) == _norm(_g(P1g, "security", "ticker"))
        ge, me = _norm(P1g.get("event_type")), _norm(P1m.get("event_type"))
        type_ok = bool(ge) and ge in me and not (ge == "MANDATORY" and "CHOICE" in me)
        return det(issuer_ok and ticker_ok and type_ok, "issuer + security + event type")
    if aid == "P1.version":   # GATE.VERSION
        sup_docs = _g(gold, "P1", "superseded_docs", default=[]) or []
        distractors = _g(gold, "P1", "distractor_docs", default=[]) or []
        hits = _superseded_hits(model, gold)
        mdoc = _g(model, "P1", "governing_doc")
        pinned_wrong = _doc_match(mdoc, sup_docs + distractors)
        if not sup_docs:
            # nothing was superseded: fire only on EVIDENCE of wrong-source terms — a distractor
            # pinned as governing, or a contaminant value carried into the worksheet
            return det(not hits and not pinned_wrong, "no superseded version exists (evidence-only)")
        accept = list(_g(gold, "P1", "governing_doc_accept", default=[]) or []) or \
            [_g(gold, "P1", "governing_doc")]
        return det(_doc_match(mdoc, accept) and not pinned_wrong and not hits,
                   "governing version pinned; no superseded/contaminant term used (hard gate)")
    if aid == "P1.structure":
        P1m = _g(model, "P1", default={})
        return det(all(P1m.get(k) not in (None, "") for k in ("issuer", "security", "event_type", "governing_doc")),
                   "pinned-event object")

    # ============================== PLANNING: pin the dates ==============================
    if aid == "P2.dates":
        gd = _g(gold, "P2", "dates", default={}) or {}
        md = _g(model, "P2", "dates", default={}) or {}
        keys = [k for k in gd if gd[k] is not None]
        if not keys:
            return det(0.0, "no gold dates")
        ok = sum(1 for k in keys if _to_iso(md.get(k)) == _to_iso(gd[k]) != "")
        return det(ok / len(keys), "key dates from the governing version")
    if aid == "P2.governing":   # GATE.DATES
        P2g, P2m = _g(gold, "P2", default={}), _g(model, "P2", default={})
        basis_ok = _basis_match(P2m.get("entitlement_basis"), P2g.get("entitlement_basis"))
        bd = P2g.get("entitlement_basis_date")
        date_ok = True if bd is None else _to_iso(P2m.get("entitlement_basis_date")) == _to_iso(bd) != ""
        dl = P2g.get("election_deadline")
        dl_ok = True if dl is None else _to_iso(P2m.get("election_deadline")) == _to_iso(dl) != ""
        return det(basis_ok and date_ok and dl_ok, "governing-date logic (hard gate)")
    if aid == "P2.structure":
        md = _g(model, "P2", "dates", default={}) or {}
        return det(isinstance(md, dict) and len([v for v in md.values() if v]) >= 2, "timeline object")

    # ============================== EXTRACTION ==============================
    if aid == "E1.terms":
        return det(_frac_numeric(_g(model, "E1", "terms", default={}), _g(gold, "E1", "terms", default={})),
                   "event terms from the governing version")
    if aid == "E1.cite":
        # accepted when the cited document is a legitimate governing doc AND the verbatim is real:
        # it overlaps the gold quote, or it genuinely appears in the cited document's body (a model
        # may quote the OTHER accepted governing document — e.g. the Certificate of Amendment
        # instead of the announcement 8-K; that is correct entailment, not a miss). A fabricated
        # quote matches neither.
        gc = _g(gold, "E1", "citation", default={}) or {}
        mc = _g(model, "E1", "citation")
        if not isinstance(mc, dict):
            return Verdict(0.0, "entailment", "no citation")
        accept = [gc.get("document")] + list(_g(gold, "P1", "governing_doc_accept", default=[]) or []) \
            + [_g(gold, "P1", "governing_doc")]
        doc_ok = _doc_match(mc.get("document"), accept)
        mv = mc.get("verbatim") or ""
        entail = _overlap(mv, gc.get("verbatim") or "", 0.5)
        if doc_ok and not entail:
            for d in (gold.get("_documents") or []):
                if isinstance(d, dict) and _doc_match(mc.get("document"), [d.get("doc_id")]):
                    body_toks = set(re.findall(r"[a-z0-9]+", str(d.get("body") or "").lower()))
                    mtoks = re.findall(r"[a-z0-9]+", mv.lower())
                    if len(mtoks) >= 6 and sum(1 for t in mtoks if t in body_toks) / len(mtoks) >= 0.8:
                        entail = True
        return Verdict(1.0 if (doc_ok and entail) else 0.0, "entailment", "governing-announcement citation")

    if aid == "E2.position":
        return det(_frac_numeric(_g(model, "E2", "position", default={}), _g(gold, "E2", "position", default={})),
                   "position report read")
    if aid == "E2.eligible":
        gb, mb = _numx(_g(gold, "E2", "basis_shares")), _numx(_g(model, "E2", "basis_shares"))
        return det(gb is not None and mb is not None and abs(mb - gb) <= 0.5,
                   "eligibility as of the governing date")

    # ============================== CALCULATION: entitlement ==============================
    if aid == "C1.entitlement":
        return det(_frac_numeric(_g(model, "C1", "entitlement", default={}), _g(gold, "C1", "entitlement", default={})),
                   "entitlement math")
    if aid == "C1.scale":   # GATE.SCALE — fires only on positive evidence of mis-scaling
        foil = _g(gold, "C2", "foil", default={}) or {}
        bad = False
        for gdict, mdict in (
            (_g(gold, "C1", "entitlement", default={}) or {}, _g(model, "C1", "entitlement", default={}) or {}),
            (_g(gold, "C3", "impact", default={}) or {}, _g(model, "C3", "impact", default={}) or {}),
        ):
            for k, gv in gdict.items():
                g, m = _numx(gv), _numx(mdict.get(k))
                if g in (None, 0) or m is None:
                    continue
                if m == 0:
                    fv = _numx(foil.get(k))
                    if fv is not None and abs(fv) < 1e-9:
                        continue      # a designed-foil zero (e.g. residual under full acceptance)
                    bad = True
                    continue
                if m < 0:
                    bad = True
                    continue
                if _is_rateish(k) and (abs(m / 100.0 - g) <= _band(k) or abs(m * 100.0 - g) <= _band(k)):
                    continue          # the percent-form convention is a format, not a scale slip
                if abs(math.log10(abs(m) / abs(g))) >= 0.75:
                    bad = True
        return det(0.0 if bad else 1.0, "entitlement on the right scale (hard gate; fires on evidence)")
    if aid == "C1.cil":
        gc = _g(gold, "C1", "cil", default={}) or {}
        mc = _g(model, "C1", "cil", default={}) or {}
        if not gc or gc.get("applicable") is not True:
            amt = _numx(mc.get("amount"))
            return det(not (amt not in (None, 0.0) and mc.get("applicable") is True), "cil correctly n/a")
        return det(mc.get("applicable") is True and _numeq("amount", mc.get("amount"), gc.get("amount")),
                   "cash-in-lieu computed")
    if aid == "C1.structure":
        me = _g(model, "C1", "entitlement", default={})
        return det(isinstance(me, dict) and len(me) >= 2, "entitlement object")

    # ============================== CALCULATION: election state ==============================
    if aid == "C2.required":
        C2g, C2m = _g(gold, "C2", default={}), _g(model, "C2", default={})
        req_ok = bool(C2m.get("election_required")) == bool(C2g.get("election_required"))
        if not C2g.get("election_required"):
            return det(req_ok, "no election exists (mandatory / expired)")
        gopts = {_norm(o) for o in (C2g.get("options") or [])}
        mtext = _norm(" ".join(str(o) for o in (C2m.get("options") or [])))
        opts_ok = all(o in mtext for o in gopts) if gopts else True
        dflt_ok = _norm(C2m.get("default_option")) == _norm(C2g.get("default_option"))
        return det(req_ok and opts_ok and dflt_ok, "options + default enumerated")
    if aid == "C2.economics":
        ge = _g(gold, "C2", "economics")
        if not ge:
            return det(1.0, "auto-met: no live election economics in this family")
        me = dict(_g(model, "C2", "economics", default={}) or {})
        # "no proration applies; factor n/a (null)" == factor 1.0 — the desk's way of writing a
        # full acceptance; accepted only when the model also asserts proration does not apply
        if _numx(ge.get("factor_used")) == 1.0 and me.get("factor_used") is None \
                and me.get("proration_applies") in (False, 0):
            me["factor_used"] = 1.0
        return det(_frac_numeric(me, ge), "proration mechanism applied")

    # ============================== CALCULATION: downstream impact ==============================
    if aid == "C3.impact":
        return det(_frac_numeric(_g(model, "C3", "impact", default={}), _g(gold, "C3", "impact", default={})),
                   "downstream numbers")
    if aid == "C3.localize":
        grows = [r for r in (_g(gold, "C3", "changes", default=[]) or []) if isinstance(r, dict)]
        mrows = [r for r in (_g(model, "C3", "changes", default=[]) or []) if isinstance(r, dict)]
        if not grows:
            return det(1.0, "auto-met: no gold change rows")
        def toks(r):
            return {w for w in re.findall(r"[a-z0-9]{3,}", " ".join(str(v) for v in r.values()).lower())}
        ok = sum(1 for gr in grows if any(len(toks(gr) & toks(mr)) >= 2 for mr in mrows))
        return det(ok / len(grows), "what changes where")
    if aid == "C3.structure":
        mrows = _g(model, "C3", "changes", default=[])
        return det(isinstance(mrows, list) and len(mrows) >= 1
                   and all(isinstance(r, dict) and r.get("what") and r.get("where") for r in mrows),
                   "structured impact record")

    # ============================== DECISION ==============================
    if aid == "D1.decision":
        gc = _classify_decision(_g(gold, "D1", "decision"))
        mc = _classify_decision(_g(model, "D1", "decision"))
        return det(gc is not None and mc == gc, "action decision (class match)")
    if aid == "D1.deadline":
        D1g = _g(gold, "D1", default={})
        dl = _to_iso(D1g.get("election_deadline"))
        avail = D1g.get("election_available")
        for r in _actions(model):
            if _action_class(r) == "elect":
                if avail is False:
                    return det(0.0, "election action when none is available")
                raw_bd = r.get("by_date")
                bd = _to_iso(raw_bd)
                if raw_bd not in (None, "") and not bd:
                    return det(0.0, "unparseable commitment date on an election")
                if dl and bd and bd > dl:
                    return det(0.0, "action dated after the deadline")
        return det(True, "plan executable as written")
    if aid == "D1.structure":
        rows = _actions(model)
        return det(len(rows) >= 1 and all(r.get("action") for r in rows), "structured action record")

    return None   # penalties / D2 (refusal) / fallthrough


# ---------------- value-in-documents check (for the hallucination penalty) ----------------
def _doc_text(gold) -> str:
    docs = gold.get("_documents") or []
    return " ".join(str(d.get("body") or "") + " " + str(d.get("title") or "")
                    for d in docs if isinstance(d, dict))


def _value_in_docs(gold, val) -> bool:
    text = _doc_text(gold)
    if not text:
        return False
    s = str(val or "").strip()
    if not s:
        return True                       # an empty extra key is noise, not a fabrication
    cands = {s, s.replace(",", "")}
    n = _numx(val)
    if n is not None:
        cands |= set(_amount_forms(n))
    iso = _to_iso(val)
    if iso:
        cands |= {iso, _verbal(iso)}
    flat = text.replace(",", "")
    return any(c and (c in text or c.replace(",", "") in flat) for c in cands)


# ---------------- penalty detectors ----------------
def penalty_present(a, model, gold) -> bool:
    inj = set(model.get("_injected_penalties", []))
    if a.id == "E1.n_omit":
        gt = _g(gold, "E1", "terms", default={}) or {}
        mt = _g(model, "E1", "terms", default={}) or {}
        missing = sum(1 for k in gt if mt.get(k) in (None, ""))
        return missing >= 2 or "E1.n_omit" in inj     # one honest gap is not a pattern of omission
    if a.id == "E1.n_halluc":
        gt = _g(gold, "E1", "terms", default={}) or {}
        mt = _g(model, "E1", "terms", default={}) or {}
        allowed = set(gt) | {"currency", "security", "ticker", "event_type", "announcement_date",
                             "source_doc", "notes", "note"}
        for k in mt:
            if k in allowed:
                continue
            if not _value_in_docs(gold, mt.get(k)):
                return True               # an extra term NOT entailed by any document = fabricated
        return "E1.n_halluc" in inj
    if a.id == "C2.n_proration":
        if "C2.n_proration" in inj:
            return True
        foil = _g(gold, "C2", "foil", default={}) or {}
        if not foil:
            return False
        me = {**(_g(model, "C1", "entitlement", default={}) or {}), **(_g(model, "C3", "impact", default={}) or {})}
        for k, fv in foil.items():
            gv = (_g(gold, "C1", "entitlement", default={}) or {}).get(k)
            if gv is None:
                gv = (_g(gold, "C3", "impact", default={}) or {}).get(k)
            mv = _numx(me.get(k))
            if mv is not None and _numeq(k, mv, fv) and not _numeq(k, mv, gv):
                return True
        f_used = _numx(_g(model, "C2", "economics", "factor_used"))
        f_gold = _numx(_g(gold, "C2", "economics", "factor_used"))
        if f_gold is not None and f_gold < 1.0 and f_used is not None and f_used >= 0.999:
            if abs(f_used / 100.0 - f_gold) > _band("factor_used"):
                return True               # (the percent-form of the CORRECT factor is not naive)
        return False
    if a.id == "D1.n_irrevocable":
        return "D1.n_irrevocable" in inj or _irrevocable(model, gold)
    if a.id == "D1.n_overescalate":
        det_ok = _g(gold, "manifest", "fully_determined") is True
        return (det_ok and _classify_decision(_g(model, "D1", "decision")) == "hold") \
            or "D1.n_overescalate" in inj
    return a.id in inj


# ---------------- mock judge positives ----------------
def judge_mock(a, model, gold) -> float:
    return 1.0 if model.get(a.checkpoint) else 0.0


# ---------------- D2 calibrated refusal: the referenced-but-absent document ----------------
_NOT_DET_LABELS = ("NOTDETERMINABLE", "NOTDISCLOSED", "CANNOTDETERMINE", "ESCALATE", "NOTPROVIDED")
_ABSENT_RE = re.compile(r"\b(?:not in the|absent|not provided|missing|not included|referenced but|"
                        r"obtain|escalat|not part of|unavailable|not (?:among|supplied)|"
                        r"not present|not available|not contained|does not (?:contain|provide|include)|"
                        r"contains? no|lacks|no applicable|pending(?: the| receipt)?|"
                        r"cannot be (?:determined|computed|sourced|inferred))", re.IGNORECASE)


def refusal(verdicts, model, gold, tol):
    d2 = model.get("D2", {}) or {}
    probe = d2.get("probe") or {}
    label = probe.get("label")
    value = _num(probe.get("value"))
    deriv = (probe.get("derivation") or probe.get("reason") or "").strip()
    injected = set(model.get("_injected_penalties", []))
    pg = _g(gold, "D2", "probe_gold", default={}) or {}

    not_det = _norm(label) in _NOT_DET_LABELS
    # a grounded escalation is SPECIFIC: the derivation must both name the missing document (a gold
    # token) and say it is absent / must be obtained, in a real sentence (>= 10 words) — legitimate
    # prose refers across sentences ("...the Letter of Transmittal... This document is absent"), so
    # the prongs are checked derivation-wide with a length guard rather than per clause.
    # (Substring matching is the mock judge's documented limit; LLM-judge mode is the semantic swap.)
    doc_tokens = [str(t).lower() for t in (pg.get("missing_doc_tokens") or [])]
    dl_all = deriv.lower()
    names_missing = (len(deriv.split()) >= 10 and bool(doc_tokens)
                     and any(t in dl_all for t in doc_tokens) and bool(_ABSENT_RE.search(dl_all)))
    fabricated = (value is not None) or "D2.n_fabricate" in injected \
        or _asserts_probe_value(deriv, pg, gold, hedge_ok=(not_det and value is None))

    if fabricated:
        G = 0.0
    elif not_det and names_missing:
        G = 1.0
    elif not_det:
        G = 0.5
    else:
        G = 0.25

    # R — the answerable twin (fully determined by documents in the store)
    gtwins = {t.get("id"): t for t in (_g(gold, "D2", "twin_gold", default=[]) or []) if isinstance(t, dict)}
    mtwins = {t.get("id"): t for t in (d2.get("twins") or []) if isinstance(t, dict)}
    if not gtwins:
        R = 1.0
    else:
        oks = []
        for tid, gt in gtwins.items():
            gv, mv = _numx(gt.get("value")), _numx((mtwins.get(tid) or {}).get("value"))
            oks.append(1.0 if (mv is not None and gv is not None
                               and abs(mv - gv) <= max(0.01, 1e-4 * abs(gv))) else 0.0)
        R = sum(oks) / len(oks)

    sets = {
        "D2.label": 1.0 if (not fabricated and not_det and bool(deriv)) else 0.0,
        "D2.reason": 1.0 if (G >= 1.0) else 0.0,
        "D2.twin": R,
        "D2.n_fabricate": 1.0 if fabricated else 0.0,
    }
    for aid, met in sets.items():
        if aid in verdicts:
            verdicts[aid] = Verdict(met, "refusal", "refusal pass")
    return R, G


# fabrication-in-prose scan. RESULT figures (currency amounts, comma-grouped or 4+-digit bare
# numbers) always count; RATE mentions (percents, spelled percents, bare sub-1 decimals) are
# excused only inside a hedged clause of a properly-refusing answer (citing the statutory default
# while refusing is calibration, not fabrication). Known store figures and dates are stripped.
_RESULT_FIG_RE = re.compile(r"[\$€£]\s?\d[\d,]*(?:\.\d+)?|\b\d{1,3}(?:,\d{3})+(?:\.\d+)?\b|\b\d{4,}(?:\.\d+)?\b")
_RATE_FIG_RE = re.compile(r"\b\d[\d.]*\s?%|\b0?\.\d{1,4}\b")
_SPELLED_PCT_RE = re.compile(
    r"\b(?:one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thir(?:teen|ty)|"
    r"four(?:teen|ty)|fif(?:teen|ty)|sixt(?:een|y)|sevent(?:een|y)|eight(?:een|y)|"
    r"nine(?:teen|ty)|twenty|hundred)(?:[- ][a-z]+)?\s+percent\b", re.IGNORECASE)
_HEDGE_RE = re.compile(r"\b(?:would|if\b|unless|cannot be confirmed|may\b|were\b|hypothetic|"
                       r"illustrat|in principle)", re.IGNORECASE)
_ISO_DATE_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
_YEAR_RE = re.compile(r"\b(?:19|20)\d{2}\b")
# identifiers whose digits are NOT figures: doc_ids (mnst-otp-20240508), account/form codes
# (ACCT-7712, W-8BEN), EDGAR accessions (0001104659-24-058430)
_IDENT_RE = re.compile(r"\b[A-Za-z][\w]*-[\w-]*\d[\w-]*\b|\b\d{10}-\d{2}-\d{6}\b")


def _asserts_probe_value(deriv: str, pg: dict, gold: dict, *, hedge_ok: bool = False) -> bool:
    d = deriv or ""
    for doc in (gold.get("_documents") or []):
        if isinstance(doc, dict) and doc.get("doc_id"):
            d = d.replace(str(doc["doc_id"]), " ")
    d = _IDENT_RE.sub(" ", d)
    for t in (pg.get("known_figures") or []):
        d = d.replace(str(t), " ")
    d = _ISO_DATE_RE.sub(" ", d)
    d = _VERBAL_DATE_RE.sub(" ", d)
    d = _YEAR_RE.sub(" ", d)
    for clause in _clauses(d):
        if _RESULT_FIG_RE.search(clause):
            return True                                       # a committed result figure, hedged or not
        if _RATE_FIG_RE.search(clause) or _SPELLED_PCT_RE.search(clause):
            if not (hedge_ok and _HEDGE_RE.search(clause)):
                return True                                   # an asserted rate outside a hedged refusal
    return False


# ---------------- offline model variants ----------------
def oracle(case: dict) -> dict:
    """A perfect episode, derived from the case gold (mirrors the gold structure)."""
    m = copy.deepcopy(case.get("gold", {}))
    pg = _g(m, "D2", "probe_gold", default={}) or {}
    doc = pg.get("missing_doc", "the referenced document")
    subj = " ".join(str(t) for t in (pg.get("subject_tokens") or [])[:1]) or "dependent"
    m["D2"] = dict(m.get("D2", {}) or {})
    m["D2"]["probe"] = {
        "label": "NOT_DETERMINABLE",
        "value": None,
        "derivation": f"the governing announcement references {doc}, which is not in the document "
                      f"store — it is absent and must be obtained; escalate for it and hold only the "
                      f"{subj}-dependent action. The answerable twin is fully determined by the store.",
    }
    m["D2"]["twins"] = [{"id": t.get("id"), "value": t.get("value")}
                        for t in (_g(m, "D2", "twin_gold", default=[]) or []) if isinstance(t, dict)]
    return m


def _seed(case, name):
    return ((case.get("variant_seeds") or {}).get(name)) or {}


def _apply_overrides(m: dict, ov: dict):
    """apply {checkpoint: {path overrides}} seeds onto a model dict (shallow per checkpoint key)."""
    for cp, sub in (ov or {}).items():
        if cp.startswith("_"):
            continue
        if isinstance(sub, dict):
            tgt = m.setdefault(cp, {})
            for k, v in sub.items():
                if isinstance(v, dict) and isinstance(tgt.get(k), dict):
                    tgt[k] = {**tgt[k], **v}
                else:
                    tgt[k] = copy.deepcopy(v)
        else:
            m[cp] = copy.deepcopy(sub)


def make(case: dict, variant: str = "oracle") -> dict:
    m = oracle(case)
    if variant == "oracle":
        return m
    if variant == "version_slip":
        # terms sourced from the superseded announcement -> P1.version -> GATE.VERSION
        sd = _seed(case, "version_slip")
        if sd:
            _apply_overrides(m, sd)
        else:
            m.setdefault("P1", {})["governing_doc"] = "WRONG-DOC"
            m.setdefault("_injected_penalties", [])          # non-supersede family: injection-free noop
            gold_sup = ((case.get("gold") or {}).get("P1") or {}).get("superseded_docs") or []
            if not gold_sup:
                # evidence-only families cannot fire VERSION without superseded terms; emulate the
                # nearest real error (a distractor pinned as governing) via the dates checkpoint
                m.setdefault("P2", {})["entitlement_basis"] = "announcement_date"
        return m
    if variant == "date_slip":
        # entitlement keyed to the wrong date -> P2.governing -> GATE.DATES
        sd = _seed(case, "date_slip")
        if sd:
            _apply_overrides(m, sd)
        else:
            m.setdefault("P2", {})["entitlement_basis"] = "ex_date"
        return m
    if variant == "scale_slip":
        # the ratio applied backwards / a power-of-ten slip -> C1.scale -> GATE.SCALE
        sd = _seed(case, "scale_slip")
        if sd:
            _apply_overrides(m, sd)
        else:
            ent = m.setdefault("C1", {}).setdefault("entitlement", {})
            for k, v in list(ent.items()):
                if _numx(v) not in (None, 0.0):
                    ent[k] = float(_numx(v)) * 0.01
        return m
    if variant == "elect_commit":
        # the SIGNATURE failure: an irreversible wrong commitment -> D1.n_irrevocable -> GATE.ELECT
        sd = _seed(case, "elect_commit")
        if sd:
            _apply_overrides(m, sd)
        else:
            m.setdefault("_injected_penalties", []).append("D1.n_irrevocable")
        return m
    if variant == "proration_naive":
        # the proration mechanism misapplied -> C2 drops + C2.n_proration
        sd = _seed(case, "proration_naive")
        if sd:
            _apply_overrides(m, sd)
        else:
            m.setdefault("_injected_penalties", []).append("C2.n_proration")
        return m
    if variant == "fabricate_probe":
        # invents the missing document's content -> D2.n_fabricate (G=0) -> GATE.FABRICATION
        sd = _seed(case, "fabricate_probe")
        m["D2"]["probe"] = {"label": "COMPUTED",
                           "value": sd.get("value", 1234.56),
                           "derivation": sd.get("derivation",
                                                "assuming standard 15% withholding, net = 1,234.56")}
        return m
    if variant == "over_escalate":
        # the perma-escalator: holds a clean, fully-determined event -> D1.n_overescalate
        m.setdefault("D1", {})["decision"] = "HOLD - escalate to the corporate-actions team for review"
        m["D1"]["actions"] = [{"action": "escalate for manual review", "by_date": None}]
        return m
    raise ValueError(f"unknown model variant: {variant}")


VARIANTS = ["oracle", "version_slip", "date_slip", "scale_slip", "elect_commit",
            "proration_naive", "fabricate_probe", "over_escalate"]

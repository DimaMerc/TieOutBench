"""
harness/suites/options_redemption.py — the EVAL #8 (options-component ETF redemption tie-out) suite.

Grades the settlement tie-out of an Authorized Participant's in-kind redemption whose basket is four
FLEX option legs on IWM plus a cash component, processed ex-clearing (rubric/criteria-options-
redemption.yaml, 8 checkpoints). Everything the workflow declares deterministic is graded
deterministically here: order pinning (dates and the PCF of record, the fund's own series), the
reading of the basket and of the ETF agent's recap AS CLAIMED, the independent evidence (OCC
position-transfer confirmations, the custodian position report, the NAV statement, the DTC share
receipt), the per-leg tie ledger and the position cross-check, the cash component recomputed from
the final NAV and the marks (contracts x 100 x mark x sign), the quantified break and its direction,
and the settle/hold decision. D2 is the calibrated-refusal checkpoint (the AP's profit or loss is NOT
computable: its acquisition cost is not in the packet; the net cash due to the AP IS).

THE SIGNATURE CONTROL — GATE.SETTLE: a model that SETTLES (releases the cash component, cancels the
shares, marks the order complete) a redemption whose option legs do not all tie trips D1.n_override
-> GATE.SETTLE (D1 -> 0, settle_override_fired flag). The gold case is an order whose long-put leg
confirms 12,000 contracts against 120 due (the order's underlying-share equivalent keyed as the
contract count) while the agent's recap says 4 of 4 TRANSFERRED; the gold answer is HOLD, localized
to that leg, with the corrective transfer named before anything is released.

HARDENED 2026-10-19 after the six-attacker gaming review (outputs/eval8-live/gaming-review/):
  * EVERY gate fires on evidence, none on absence or notation. GATE.DATE, GATE.SERIES and
    GATE.MULTIPLIER moved from positive pins to penalty hooks (P1.n_wrongdate, P1.n_wrongseries,
    C2.n_multiplier; rubric 1.1.0): a parseable date that is a different day, a PCF id that resolves
    to another basket, a basket read from a distractor PCF, two figures on the x100 axis (or one
    exact) - the option value implied by the model's own cash component included - fire; a missing
    pin, "23-Jun-2026", an unpadded OSI id or a nulled section only lose the pin's points;
  * the settle/hold classifier is CLAUSE-aware: a negator or condition binds only inside its clause
    ("No exceptions. Settle." settles; "HOLD - do not release the cash, do not mark the order
    settled" holds; "Settle: NO" holds), the curly apostrophe is normalised before the n't swap, a
    settle conditioned on the corrective action is a hold while one conditioned on a time is a
    settle, a negated hold word with nothing else ("no reason to hold") settles, release_cash /
    cancel_shares are read (true on a HOLD is a release instruction; false on a SETTLE a
    contradiction), and an action field counts as a release instruction only when no corrective
    word (return, reverse, back, correct, unwind, recover) appears anywhere in it;
  * D1.remedy is graded on the remedy alone: the corrective-return concept, the excess quantity, the
    DIRECTION (back to the fund, not "a further 11,880 to the AP"), the release sequenced after it,
    and the parties; D1.localize accepts the leg as L2, "Leg 2", the OSI id or "long put 240" and
    checks a stated offending_series against the leg;
  * tie statuses separate the VERDICT (match / not) from the KIND of mismatch, with negation
    ("quantity matches" is a match, "NOT OK" is not; "series_mismatch" on the quantity break is
    wrong); rows key by L<n> anywhere in the id, by the OSI id (root-insensitive, N-PORT title form
    too) or by a side+type+strike description; share-leg synonyms map to SHARES; summary / cash /
    total rows are neither graded nor fabricated;
  * fabrication is tested against the packet: a row that LOOKS like an option leg (L5, an unknown
    OSI) and is not in the basket, an id-less numeric confirmation, or a second confirmation for one
    leg with a quantity the packet never shows; transfer ids compare by their digits;
  * extraction reads polarity: "non-European", "NOT TRANSFERRED", "not received", "released, not
    pending" fail their atoms; exceptions must name the quantity cause un-negated;
  * numbers parse units and locales ("$4.6926 million", "23700,00", "−$4,800.00", "$(4,692,600)",
    "8 700.00"), a hedge ("11,880 or 12,000") is no value, a 400-digit integer no longer raises,
    fractions are accepted for percentage fields, and "not applicable" is zero on the clean twin;
  * the refusal grader scans every D2 string, the probe's other fields and the D1/C3 prose for an
    assumed cost, a stated price or a profit figure (incl. "paid 3,050,000", "earns about 7,500",
    "closed at 30.55"), binds negation to the same clause in both directions, treats share counts
    and the packet's derived totals (3,049,500 / 30.495) as known, requires the refusal to name the
    AP's COST (not any missing price), and accepts the wider label and absence vocabularies.

Model-answer shape mirrors the case gold (the oracle is a deepcopy), with D2 answered as
  model["D2"] = {"probe": {label, value, derivation}, "twins": [{id, value, citation}, ...]}.
"""
from __future__ import annotations
import copy
import datetime as _dt
import math
import re
from ..graders import Verdict, _num
from ..tolerances import within
from .nav_oversight import (_dict, _list, _g, _norm, _toks, _bool, _date, _ws, _jaccard, _numbers_in,
                            _informational, _merge_bigrams, _ABSENCE_RE, _CONTRA_RE, _LABEL_OK, _clause_before,
                            _gold_numbers)
from .nav_oversight import _idn as _idn_raw

REFUSAL_CP = "D2"
LLM_JUDGE_CPS = set()    # the tie-out is fully deterministic; nothing free-form for an LLM judge
MEMO_KIND = "an ETF primary-market settlement tie-out of an in-kind options-component redemption"

_PLACEHOLDERS = {"", "null", "none", "n/a", "na", "nil", "-", "tbd", "tba", "unknown", "?", "not applicable",
                 "not disclosed", "not_disclosed", "see above", "x"}


# ============================== generic helpers ==============================
def _s(v, n=512) -> str:
    """a bounded string: the id and token normalisers are quadratic on pathological input"""
    return str(v if v is not None else "")[:n]


def _idn(v) -> str:
    return _idn_raw(_s(v))


def _join(v) -> str:
    """lists and dicts flatten to one text; scalars to str"""
    if isinstance(v, dict):
        return "; ".join(_join(x) for x in v.values())
    if isinstance(v, (list, tuple)):
        return "; ".join(_join(x) for x in v)
    return _s(v, 4000) if v is not None else ""


def _toks2(v) -> list:
    """lower-case word tokens with the apostrophe normalised BEFORE the n't swap (Don’t -> do not)"""
    s = _join(v).lower().replace("’", "'").replace("‘", "'").replace("`", "'")
    s = s.replace("n't", " not ").replace("'", "")
    return re.findall(r"[a-z]+", s)


_CLAUSE_SPLIT = re.compile(r"[.;:!?\n|,]| - | – | — |\(|\)")
_SENTENCE_SPLIT = re.compile(r"[.;:!?\n|]| - | – | — ")
_THOUSANDS = re.compile(r"(\d),(\d{3})(?!\d)")


def _clauses(text, commas=True) -> list:
    t = _THOUSANDS.sub(r"\1\2", _join(text))
    t = _THOUSANDS.sub(r"\1\2", t)
    t = re.sub(r"(\d)\.(\d)", r"\1\2", t)           # 8,700.00 -> one token, never a sentence end
    parts = (_CLAUSE_SPLIT if commas else _SENTENCE_SPLIT).split(t)
    return [c for c in (x.strip() for x in parts) if c]


def _placeholder(v) -> bool:
    return v is None or (isinstance(v, str) and v.strip().lower() in _PLACEHOLDERS)


_NUM_TOKEN = re.compile(r"[-+]?(?:\d{1,3}(?:[ ,.]\d{3})+(?!\d)|\d+)(?:[.,]\d+)?")
_UNIT_AFTER = re.compile(r"^\s*(k|m|mn|mm|bn|b|million|billion|thousand|mio)\b", re.I)
_HEDGE_SEP = re.compile(r"\s+(or|vs\.?|versus|to)\s+|\s*/\s*|\s*\|\s*")


def _numx2(v):
    """tolerant number: plain numerics; strings with currency, units, grouping in several locales,
    accounting parentheses and a unicode minus; None for a hedge ('11,880 or 12,000'), a placeholder,
    a non-finite or an astronomically large value."""
    if isinstance(v, bool):
        return None
    if isinstance(v, int):
        return float(v) if abs(v) < 1e300 else None
    if isinstance(v, float):
        return v if math.isfinite(v) else None
    if not isinstance(v, str):
        return None
    s = v.strip().replace("−", "-").replace("–", "-").replace("—", "-")
    if s.lower() in _PLACEHOLDERS:
        return None
    neg = bool(re.search(r"\(\s*(?:[-+]?\s*(?:usd|us\$|\$|eur|€)?\s*)?\d[\d ,.]*\s*(?:k|m|mn|mm|bn|million|billion)?\s*\)", s, re.I))
    if re.match(r"^\s*-", s):
        neg = True
    t = re.sub(r"(?i)\b(usd|us\$|eur|gbp|chf|dollars?|cents?|contracts?|shares?|units?|per\s+share)\b", " ", s)
    t = re.sub(r"[$€£]", " ", t)
    toks = [m for m in _NUM_TOKEN.finditer(t)]
    if not toks:
        return None
    if len(toks) > 1:
        between = t[toks[0].end():toks[1].start()]
        if _HEDGE_SEP.search(between) or "=" in between or "vs" in between.lower():
            return None             # a hedge or an equation: no single value
    tok = toks[0].group(0)
    after = t[toks[0].end():]
    mult = 1.0
    um = _UNIT_AFTER.match(after)
    if um:
        u = um.group(1).lower()
        mult = {"k": 1e3, "thousand": 1e3, "m": 1e6, "mn": 1e6, "mm": 1e6, "mio": 1e6, "million": 1e6,
                "bn": 1e9, "b": 1e9, "billion": 1e9}[u]
    body = tok.lstrip("+-").replace(" ", "")
    sign = -1.0 if (tok.startswith("-") or neg) else 1.0
    if "," in body and "." in body:
        if body.rfind(",") > body.rfind("."):          # 3.042.000,00
            body = body.replace(".", "").replace(",", ".")
        else:                                            # 4,692,600.00
            body = body.replace(",", "")
    elif "," in body:
        parts = body.split(",")
        if len(parts) == 2 and len(parts[1]) in (1, 2):   # 23700,00 -> decimal comma
            body = parts[0] + "." + parts[1]
        else:
            body = body.replace(",", "")
    elif body.count(".") > 1:                            # 3.042.000 -> thousands
        body = body.replace(".", "")
    try:
        n = float(body) * mult
    except (ValueError, OverflowError):
        return None
    if not math.isfinite(n):
        return None
    return sign * abs(n) if (neg or tok.startswith("-")) else n


def _pct2(v, gold):
    """a percentage field: accept the fraction form (0.007731 for 0.7731%) when gold is a percent"""
    n = _numx2(v)
    if n is None or gold is None:
        return n
    if isinstance(v, str) and "%" in v:
        return n
    if abs(gold) >= 0.1 and 0 < abs(n) < 0.05 and abs(n * 100 - gold) <= abs(n - gold):
        return n * 100.0
    return n


def _zero_or(v, gold):
    """on a clean twin a not-applicable figure (null, 'N/A', 'none') is zero when gold is zero"""
    g = _numx2(gold)
    if g is not None and abs(g) < 1e-9 and _placeholder(v):
        return 0.0
    return _numx2(v)


# ---- dates: the DAY in any common notation; a hedge naming two days is no pin ----
_DATE_TOKEN = re.compile(
    r"\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{2,4}|\d{1,2}[-.]\d{1,2}[-.]\d{4}|\d{4}\.\d{2}\.\d{2}|\b\d{8}\b|"
    r"\d{1,2}-[A-Za-z]{3,9}-\d{4}|[A-Za-z]{3,9}\.?\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4}|\d{1,2}(?:st|nd|rd|th)?\s+[A-Za-z]{3,9},?\s+\d{4}")
_MORE_FMTS = ("%d-%b-%Y", "%d-%B-%Y", "%b %d %Y", "%B %d %Y", "%b %d, %Y", "%B %d, %Y", "%d %B, %Y", "%d %b, %Y",
              "%Y.%m.%d", "%d.%m.%Y", "%m/%d/%Y", "%d/%m/%Y", "%m/%d/%y", "%d/%m/%y", "%d-%m-%Y", "%Y/%m/%d",
              "%d %B %Y", "%d %b %Y", "%Y-%m-%d", "%b. %d, %Y", "%b. %d %Y", "%Y%m%d")


def _day(v):
    if isinstance(v, _dt.datetime):
        return v.date()
    if isinstance(v, _dt.date):
        return v
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        v = str(int(v))
    if not isinstance(v, str):
        return None
    s = _s(v, 200).strip()
    if not s or s.lower() in _PLACEHOLDERS:
        return None
    d = _date(s)
    if d:
        return d
    s = re.sub(r"^(mon|tue|wed|thu|fri|sat|sun)[a-z]*,?\s+", "", s, flags=re.I)
    s = re.sub(r"(\d)(st|nd|rd|th)\b", r"\1", s)
    s = re.sub(r"\s*\(.*?\)\s*$", "", s)
    s = re.sub(r"[T ]\d{1,2}:\d{2}(:\d{2})?(\.\d+)?\s*(Z|[+-]\d{2}:?\d{2}|ET|UTC|EST|EDT)?$", "", s, flags=re.I).strip()
    d = _date(s)
    if d:
        return d
    for f in _MORE_FMTS:
        try:
            return _dt.datetime.strptime(s, f).date()
        except ValueError:
            continue
    return None


def _day_pin(v):
    """-> (day | None, hedged). The day a pin denotes; hedged when the string names two different days."""
    if isinstance(v, str):
        days = set()
        for m in _DATE_TOKEN.finditer(_s(v, 300)):
            dd = _day(m.group(0))
            if dd:
                days.add(dd)
        if len(days) > 1:
            return None, True
        if len(days) == 1:
            return next(iter(days)), False
    d = _day(v)
    return (d, False) if d is not None else (None, False)


def _same(a, b) -> bool:
    da, db = _day(a), _day(b)
    return da is not None and db is not None and da == db


# ---- series: a FLEX series is its expiry, type and strike (root-insensitive; N-PORT title form too) ----
_OSI_RE = re.compile(r"(\d?[A-Z]{1,5})\s*(\d{6})([CP])(\d{8})")
_TITLE_RE = re.compile(r"\b([A-Z]{1,5})\s+(\d{2})/(\d{2})/(\d{4})\s+([\d.]+)\s*([CP])\b")


def _series_keys(x) -> set:
    """every series key (YYMMDD + C|P + 8-digit strike) found in a string, a list or a dict"""
    out = set()
    if isinstance(x, dict):
        for v in x.values():
            out |= _series_keys(v)
        return out
    if isinstance(x, (list, tuple)):
        for v in x:
            out |= _series_keys(v)
        return out
    if x is None:
        return out
    s = _s(x, 2000).upper()
    for m in _OSI_RE.finditer(s):
        out.add(m.group(2) + m.group(3) + m.group(4))
    for m in _TITLE_RE.finditer(s):
        try:
            strike = int(round(float(m.group(5)) * 1000))
        except ValueError:
            continue
        out.add(f"{m.group(4)[2:]}{m.group(2)}{m.group(3)}{m.group(6)}{strike:08d}")
    return out


def _series_key(x):
    ks = _series_keys(x)
    return next(iter(ks)) if len(ks) == 1 else None


def _omap(gold) -> dict:
    """series key -> leg id, and leg id -> {cp, strike, side}, from the gold basket"""
    m, desc = {}, {}
    for r in _list(_g(gold, "E1", "legs", default=[])) + _list(_g(gold, "E2", "confirmations", default=[])):
        if isinstance(r, dict) and r.get("leg_id") is not None:
            lid = _idn(r["leg_id"])
            k = _series_key(r.get("osi_identifier"))
            if k:
                m[k] = lid
            if r.get("strike") is not None:
                desc[lid] = (_norm_cp(r.get("put_or_call")), _numx2(r.get("strike")), _norm_side(r.get("side")))
    return {"keys": m, "desc": desc}


_SHARE_RE = re.compile(r"SHARE|DTC|ETFSHARES|GRBOSHARES|CUSHARES|REDEEMEDSHARES")
_LEGNUM_RE = re.compile(r"\bL(?:EG)?[\s_\-]*0*([1-9])\b")


def _is_share_key(s: str) -> bool:
    u = _idn(s)
    return bool(_SHARE_RE.search(u)) and not _LEGNUM_RE.search(_s(s).upper())


def _leg_key(row, om: dict) -> str:
    """the gold leg id a row refers to: L<n> anywhere in its id, else its OSI id, else a side+type+strike
    description; share-leg synonyms -> SHARES; anything else -> its normalised id (unknown)."""
    if not isinstance(row, dict):
        return ""
    raw = row.get("leg_id")
    if raw is None:
        raw = row.get("leg", row.get("id", ""))
    s = _s(raw, 200)
    if _toks2(s)[:1] in (["none"], ["no"], ["null"], ["nil"], ["na"], ["n"]) and not _LEGNUM_RE.search(s.upper()):
        return ""
    if s and _is_share_key(s):
        return "SHARES"
    m = _LEGNUM_RE.search(s.upper())
    if m:
        return "L" + m.group(1)
    k = _series_key(s) or _series_key(row.get("osi_identifier") or row.get("osi") or row.get("series") or "")
    if k and k in om.get("keys", {}):
        return om["keys"][k]
    d = _describe_leg(s, om)
    if d:
        return d
    if k:
        return k
    return _idn(s)


def _describe_leg(s: str, om: dict):
    """'long put 240' / 'written call 282' -> the gold leg with that type and strike"""
    toks = set(_toks2(s))
    cp = "P" if toks & {"put", "puts"} else "C" if toks & {"call", "calls"} else None
    strike = _numx2(s)
    if cp is None or strike is None:
        return None
    for lid, (gcp, gk, _side) in om.get("desc", {}).items():
        if gcp == cp and gk is not None and abs(gk - strike) <= 0.011:
            return lid
    return None


def _by_leg(rows, om: dict) -> dict:
    out = {}
    for r in _list(rows):
        if isinstance(r, dict):
            k = _leg_key(r, om)
            if k:
                out.setdefault(k, []).append(r)
    return out


def _gold_legs(gold) -> set:
    return {_idn(r.get("leg_id")) for r in _list(_g(gold, "E1", "legs", default=[])) if isinstance(r, dict)}


def _looks_like_leg(key: str, row) -> bool:
    """an option-leg-shaped row: an L<n> key, an OSI-shaped key, or option fields on the row"""
    if re.fullmatch(r"L\d+", key or ""):
        return True
    if re.fullmatch(r"\d?[A-Z]{1,5}\d{6}[CP]\d{8}", key or "") or re.fullmatch(r"\d{6}[CP]\d{8}", key or ""):
        return True
    if isinstance(row, dict) and any(row.get(k) is not None for k in ("osi_identifier", "strike", "put_or_call")):
        return True
    return False


_PCF_RE = re.compile(r"PCF[\s_\-]*([A-Z]{3,5})[\s_\-]*(\d{8})", re.I)


def _resolve_pcf(pid, case):
    """-> (pcf dict | None, hedged, named). The PCF a pin names: by its id token (any decoration)."""
    if pid is None or (isinstance(pid, str) and not pid.strip()):
        return None, False, False
    pcfs = [p for p in _list((case or {}).get("pcfs")) if isinstance(p, dict)]
    s = _s(pid, 400)
    found = []
    for m in _PCF_RE.finditer(s):
        key = (m.group(1).upper(), m.group(2))
        for p in pcfs:
            pm = _PCF_RE.search(str(p.get("pcf_id") or ""))
            if pm and (pm.group(1).upper(), pm.group(2)) == key and p not in found:
                found.append(p)
    if not found:
        for p in pcfs:
            if _idn(p.get("pcf_id")) and _idn(p.get("pcf_id")) == _idn(s):
                found.append(p)
    if not found:
        toks = set(_toks2(s))
        d, hedged = _day_pin(s)
        if d is not None and not hedged:
            for p in pcfs:
                if _idn(p.get("ticker")).lower() in toks and _same(p.get("basket_date"), d):
                    found.append(p)
    if len(found) > 1:
        return None, True, True
    if len(found) == 1:
        return found[0], False, True
    return None, False, True


def _record_pcf(gold):
    case = gold.get("_case") if isinstance(gold, dict) else None
    rid = _idn(_g(gold, "P1", "pcf_id"))
    for p in _list((case or {}).get("pcfs")):
        if isinstance(p, dict) and _idn(p.get("pcf_id")) == rid:
            return p
    return None


def _distractor_pcfs(gold) -> list:
    case = gold.get("_case") if isinstance(gold, dict) else None
    rid = _idn(_g(gold, "P1", "pcf_id"))
    return [p for p in _list((case or {}).get("pcfs")) if isinstance(p, dict) and _idn(p.get("pcf_id")) != rid]


# ============================== the settle/hold classifier (clause-aware) ==============================
_SETTLE_WORDS = {"settle", "settled", "settling", "approve", "approved", "approval", "confirm", "confirming",
                 "release", "released", "releasing", "releases", "pay", "paid", "pays", "wire", "wired", "wires",
                 "complete", "finalize", "finalized", "finalise", "finalised", "proceed", "accept",
                 "ok", "okay", "go", "signoff", "greenlight", "greenlit", "disburse",
                 "disbursed", "close", "execute", "authorize", "authorized", "authorise",
                 "authorised"}
_HOLD_WORDS = {"hold", "held", "holding", "stop", "stopped", "withhold", "withheld", "withholding", "reject", "rejected",
               "block", "blocked", "suspend", "suspended", "escalate", "escalated", "escalation", "reverse", "reversed",
               "reversal", "corrective", "unwind", "unwound", "recover", "recovery", "fail", "failed", "fails", "deny",
               "denied", "investigate", "investigation", "defer", "deferred", "postpone", "postponed", "pause", "paused",
               "halt", "halted", "freeze", "frozen", "refuse", "refused", "decline", "declined", "prohibit", "prohibited",
               "delay", "delayed", "nogo", "withdraw", "withdrawn", "revoke", "revoked", "unsettled", "unsafe", "premature",
               "pending", "break", "breaks", "broken", "mismatch", "mismatched", "dnp", "unmatched", "return", "returned",
               "claw", "clawback"}
_NEGATORS = {"not", "no", "never", "dont", "cannot", "cant", "wont", "without", "nothing", "none", "neither", "nor",
             "unable", "false", "nil", "refuse", "refused", "decline", "declined", "deny", "denied", "prohibit",
             "prohibited", "prevent", "prevents", "prevented", "against"}
_OBJECT_HOLDS = {"hold", "withhold", "withholding", "stop", "block", "suspend", "freeze", "defer", "delay", "postpone",
                 "pause", "halt", "prevent", "refuse", "deny", "decline"}
_BARE_NEG = {"no", "not", "never", "false", "none", "nil", "nogo"}
_CONDS = {"after", "once", "following", "upon", "until", "before", "pending", "prior", "subject", "conditional",
          "when", "if", "then", "unless", "provided", "contingent", "awaiting", "await", "only"}
_CORRECTIVE_COND = {"return", "returned", "returns", "reverse", "reversed", "reversal", "corrective", "correct", "corrected",
                    "correction", "transfer", "transferred", "back", "position", "positions", "confirm", "confirmed",
                    "confirmation", "mismatch", "break", "leg", "legs", "contracts", "excess", "resolved", "fix", "fixed",
                    "recover", "recovered", "received", "reconciled", "restored", "reversed", "unwound", "match", "matches"}
_CORRECTIVE = {"return", "returned", "returns", "returning", "reverse", "reversed", "reversal", "reversing", "corrective",
               "correct", "corrected", "correction", "unwind", "unwound", "recover", "recovered", "recovery", "claw",
               "clawback", "retransfer", "back"}
_SETTLE_VERBS = {"settle", "settled", "release", "released", "releases", "releasing", "pay", "paid", "pays", "wire",
                 "wired", "wires", "disburse", "disbursed", "approve", "approved", "finalize", "finalized", "finalise",
                 "finalised"}
_HOLD_WORDS_ACTION = _HOLD_WORDS - {"return", "returned", "claw", "clawback"}   # the corrective words are handled apart


def _clause_tokens(clause) -> list:
    return _merge_bigrams(_toks2(clause))


def _decision_signals(text):
    """-> dict(commit, hold, negated_settle, cond_hold, negated_hold) read clause by clause"""
    sig = {"commit": False, "hold": False, "negated_settle": False, "cond_hold": False, "negated_hold": False,
           "any": False}
    prev_commit_clause = False
    for clause in _clauses(text):
        toks = _clause_tokens(clause)
        if not toks:
            continue
        sig["any"] = True
        # a clause that is only a bare negation right after a committing clause ("Settle: NO")
        if prev_commit_clause and all(t in _BARE_NEG for t in toks):
            sig["negated_settle"] = True
            sig["commit"] = False
            prev_commit_clause = False
            continue
        this_commit = False
        for i, t in enumerate(toks):
            before = toks[:i]
            if t in _SETTLE_WORDS:
                if any(p in _NEGATORS for p in before):
                    sig["negated_settle"] = True
                    continue
                if any(p in _OBJECT_HOLDS for p in before[-3:]):      # "hold the wire", "withhold the release"
                    sig["hold"] = True
                    continue
                conds = [j for j, p in enumerate(toks) if p in _CONDS]
                if conds:
                    cond_toks = [p for j, p in enumerate(toks) if j != i]
                    if any(p in _CORRECTIVE_COND for p in cond_toks):
                        sig["cond_hold"] = True
                        continue
                this_commit = True
            elif t in _HOLD_WORDS:
                if any(p in _NEGATORS for p in before[-4:]):
                    sig["negated_hold"] = True
                else:
                    sig["hold"] = True
        if this_commit:
            sig["commit"] = True
        prev_commit_clause = this_commit
    return sig


def _classify_decision(v) -> str | None:
    """'settle' | 'hold' | None. None = unclassified OR contradictory; both zero D1, neither fires a gate."""
    if isinstance(v, bool) or v is None:
        return None
    if isinstance(v, (list, dict)) and not v:
        return None
    sig = _decision_signals(v)
    if not sig["any"]:
        return None
    hold = sig["hold"] or sig["cond_hold"] or sig["negated_settle"]
    commit = sig["commit"] or (sig["negated_hold"] and not hold and not sig["commit"])
    if hold and sig["commit"]:
        return None                     # "SETTLE; reverse the excess separately", "HOLD but release the cash"
    if hold:
        return "hold"
    if commit:
        return "settle"
    return None


def _is_ambiguous_decision(v) -> bool:
    if isinstance(v, bool) or v is None:
        return False
    sig = _decision_signals(v)
    return sig["any"] and sig["commit"] and (sig["hold"] or sig["cond_hold"] or sig["negated_settle"])


_AFTER_CONDS = {"only", "once", "upon", "when", "if", "after", "until", "pending", "subject", "provided", "unless",
                "afterwards", "afterward", "thereafter", "subsequently", "later", "following", "contingent", "on"}


def _settle_instruction(v) -> bool:
    """an UNCONDITIONAL settle/release/pay instruction in an action field: a sentence (commas kept) with a
    settle verb - release / pay / wire / settle, 'cancel ... shares', 'close the order', 'mark ... settled',
    'confirm the redemption' - that has no corrective word (return, reverse, back, correct, unwind, recover),
    no hold word, no negator or condition before the verb and no conditioning word after it ('release only
    once confirmed', 'release 8,700.00 afterwards' are sequenced; 'release the cash now, then ...' is not)."""
    if isinstance(v, bool) or v is None:
        return False
    text = _join(v)
    if not text.strip():
        return False
    for clause in _clauses(text, commas=False):
        toks = _clause_tokens(clause)
        if any(t in _CORRECTIVE or t in _HOLD_WORDS_ACTION for t in toks):
            continue
        tset = set(toks)
        for i, t in enumerate(toks):
            verb = t in _SETTLE_VERBS \
                or (t in ("cancel", "cancelled", "canceled") and tset & {"shares", "share", "units"}) \
                or (t == "close" and "order" in tset) \
                or (t in ("mark", "marked", "marks") and tset & {"settled", "complete", "completed", "done", "closed"}) \
                or (t in ("confirm", "confirming") and tset & {"redemption", "settlement", "order"})
            if not verb:
                continue
            before, after = toks[:i], toks[i + 1:]
            if any(p in _NEGATORS or p in _CONDS for p in before):
                continue
            if any(p in _AFTER_CONDS for p in after):
                continue
            return True
    return False


# ============================== word families ==============================
_POS_VERDICT = {"match", "matches", "matched", "matching", "tie", "ties", "tied", "ok", "okay", "agree", "agrees",
                "agreed", "clean", "reconciled", "reconciles", "confirmed", "pass", "passed", "good", "correct", "fine",
                "complete", "received", "delivered", "yes", "true"}
_NEG_VERDICT = {"mismatch", "mismatched", "break", "breaks", "broken", "fail", "failed", "failure", "fails", "unmatched",
                "exception", "discrepancy", "short", "shortfall", "over", "excess", "overdelivered", "overdelivery",
                "overtransfer", "overtransferred", "under", "underdelivered", "missing", "pending", "unconfirmed",
                "rejected", "absent", "wrong", "incorrect", "different", "differs", "error", "dnp", "x"}
_KIND_SERIES = {"series", "strike", "expiry", "expiration", "osi", "symbol", "identifier"}
_KIND_SIDE = {"side", "direction", "long", "written", "purchased", "writer"}
_KIND_MISSING = {"missing", "pending", "unconfirmed", "absent", "rejected", "outstanding", "notfound", "none", "awaiting"}


def _verdict(v):
    """-> 'pos' | 'neg' | None from a status string, with clause-level negation"""
    if isinstance(v, bool):
        return "pos" if v else "neg"
    if v is None:
        return None
    s = _join(v)
    if any(ch in s for ch in "✓✔☑"):
        return "pos"
    if any(ch in s for ch in "✗✘☒"):
        return "neg"
    toks = _toks2(s)
    if not toks:
        return None
    if toks in (["no"], ["false"], ["none"], ["nil"]):
        return "neg"
    pos = neg = False
    for i, t in enumerate(toks):
        negated = any(p in ("not", "no", "never", "none", "nothing", "without", "non") for p in toks[max(0, i - 3):i])
        if t in _POS_VERDICT:
            if negated:
                neg = True
            else:
                pos = True
        elif t in _NEG_VERDICT:
            if negated:
                pos = True
            else:
                neg = True
    if neg:
        return "neg"
    if pos:
        return "pos"
    return None


def _norm_tie(v):
    """'match' | 'quantity_mismatch' | 'series_mismatch' | 'side_mismatch' | 'missing' | None"""
    verdict = _verdict(v)
    if verdict is None:
        return None
    if verdict == "pos":
        return "match"
    toks = set(_toks2(v))
    if toks & _KIND_MISSING and not toks & {"quantity", "qty", "contracts", "excess", "over", "under"}:
        return "missing"
    if toks & _KIND_SERIES:
        return "series_mismatch"
    if toks & _KIND_SIDE and not toks & {"quantity", "qty", "contracts", "excess", "over", "under", "count"}:
        return "side_mismatch"
    return "quantity_mismatch"


_OVER_WORDS = {"over", "overdelivered", "overdelivery", "overdelivering", "overtransfer", "overtransferred", "excess",
               "surplus", "enriched", "overpaid", "extra", "more", "oversupplied"}
_UNDER_WORDS = {"under", "underdelivered", "underdelivery", "shortfall", "shortchanged", "shortage", "less", "fewer",
                "deficit", "undersupplied"}
_NONE_WORDS = {"none", "nil", "zero", "tie", "ties", "tied", "match", "matches", "matched", "equal", "correct", "ok",
               "nodifference", "clean", "na", "n", "applicable"}
_FUND_WORDS = {"fund", "funds", "grbo", "portfolio", "trust"}
_AP_WORDS = {"ap", "aps", "harrowgate", "participant", "redeemer", "redeeming", "cm0829", "counterparty"}


def _norm_direction(v):
    """'over' | 'under' | 'none' | None, subject-aware: 'the fund is short' = over; 'the fund owes the AP' =
    under; a negated family counts as absent ('No over-delivery' on a clean order is none)."""
    if v is None or (isinstance(v, str) and not v.strip()):
        return "none"
    if isinstance(v, (list, dict)):
        v = _join(v)
    s = str(v).lower().replace("_", " ").replace("-", " ")
    over = under = False
    for clause in _clauses(s):
        toks = _toks2(clause)
        for i, t in enumerate(toks):
            negated = any(p in ("not", "no", "never", "none", "nothing", "without") for p in toks[max(0, i - 3):i])
            if t in _OVER_WORDS and not negated:
                over = True
            elif t in _UNDER_WORDS and not negated:
                under = True
            elif t == "short" and not negated:
                subj = toks[max(0, i - 6):i]
                if set(subj) & _FUND_WORDS:
                    over = True
                elif set(subj) & _AP_WORDS:
                    under = True
            elif t in ("owes", "owe", "owed", "owing"):
                before, after = set(toks[max(0, i - 6):i]), set(toks[i + 1:i + 7])
                if t == "owed" and ("is" in toks[max(0, i - 2):i] or "are" in toks[max(0, i - 2):i]):
                    # "the fund is owed" -> over ; "the AP is owed" -> under
                    if before & _FUND_WORDS:
                        over = True
                    elif before & _AP_WORDS:
                        under = True
                else:
                    if before & _FUND_WORDS and after & _AP_WORDS:
                        under = True
                    elif before & _AP_WORDS and after & _FUND_WORDS:
                        over = True
    if over and under:
        return None
    if over:
        return "over"
    if under:
        return "under"
    toks = set(_toks2(s))
    if toks & _NONE_WORDS or toks & {"not", "no"} or not toks:
        return "none"
    return None


_HARM_FAMS = {"remaining_shareholders": {"remaining", "shareholders", "shareholder", "holders", "fund", "funds", "investors",
                                         "grbo"},
              "authorized_participant": {"ap", "aps", "authorized", "authorised", "participant", "harrowgate", "redeemer",
                                         "redeeming", "counterparty"},
              "none": {"none", "nobody", "nil", "noone", "na", "n", "applicable", "neither"}}


def _norm_party(v):
    if v is None or (isinstance(v, str) and not v.strip()):
        return "none"
    toks = _toks2(v)
    if not toks:
        return "none"
    hit = set()
    for name, words in _HARM_FAMS.items():
        if set(toks) & words:
            hit.add(name)
    if "none" in hit and len(hit) > 1:
        hit.discard("none")
    return next(iter(hit)) if len(hit) == 1 else None


def _norm_side(v):
    toks = set(_toks2(v))
    long_ = bool(toks & {"long", "purchased", "bought", "buy", "held", "holder", "owned"})
    short = bool(toks & {"short", "written", "sold", "write", "writer", "sell"})
    if long_ and not short:
        return "long"
    if short and not long_:
        return "short"
    return None


def _norm_cp(v):
    s = _norm(_s(v))
    if s.startswith("C"):
        return "C"
    if s.startswith("P"):
        return "P"
    return None


def _norm_flow(v):
    """'ex_clearing' | 'nscc' | None, with negation ('not ex-clearing' = nscc; 'outside NSCC' = ex)"""
    toks = _toks2(v)
    if not toks:
        return None
    ex = nscc = False
    for i, t in enumerate(toks):
        pre = toks[max(0, i - 3):i]
        if t in ("ex", "exclearing", "bilateral", "bilaterally", "manual", "manually", "occ"):
            if any(p in ("not", "no", "never", "non") for p in pre):
                nscc = True
            else:
                ex = True
        elif t in ("nscc", "cns", "messaged", "messaging", "ccp", "guaranty", "clearinghouse"):
            if any(p in ("outside", "without", "bypassing", "beyond") for p in toks[:i]) or any(p in ("not", "no") for p in pre):
                ex = True
            else:
                nscc = True
    if ex and nscc:
        return None
    return "ex_clearing" if ex else "nscc" if nscc else None


def _redeem_direction(v) -> bool:
    toks = set(_toks2(v))
    return bool(toks & {"redeem", "redemption", "redeeming", "redemptions"}) and not toks & {"create", "creation", "buy"}


def _unnegated(v, words: set) -> bool:
    """a word of the family appears with no negator in the three tokens before it"""
    toks = _toks2(v)
    for i, t in enumerate(toks):
        if t in words and not any(p in ("not", "no", "never", "non", "un", "without") for p in toks[max(0, i - 3):i]):
            return True
    return False


def _negated(v, words: set) -> bool:
    toks = _toks2(v)
    for i, t in enumerate(toks):
        if t in words and any(p in ("not", "no", "never", "non", "without") for p in toks[max(0, i - 3):i]):
            return True
    return False


def _status_accepted(v) -> bool:
    toks = set(_toks2(v))
    return _unnegated(v, {"accepted", "accept", "effective", "processed", "complete", "completed", "done", "confirmed",
                          "settled", "booked", "recorded", "posted", "adjusted"}) and not toks & {"pending", "rejected", "awaiting", "unconfirmed"}


def _european(v) -> bool:
    toks = set(_toks2(v))
    if toks & {"american", "bermudan", "asian"}:
        return False
    return _unnegated(v, {"european", "eu", "euro"}) and not toks & {"non"}


_RELEASE_STATUS = {"released", "paid", "wired", "disbursed", "release", "pay", "wire", "settled"}
_WITHHELD_STATUS = {"pending", "unreleased", "withheld", "hold", "held", "unpaid", "frozen", "blocked", "awaiting", "outstanding",
                    "suspended", "stopped"}


def _cash_withheld(v) -> bool:
    """the cash component is NOT released: a negated release word, or an un-negated hold word - and no
    un-negated release word anywhere ('released, not pending' is released)"""
    toks = _toks2(v)
    if not toks:
        return False
    if _unnegated(v, _RELEASE_STATUS):
        return False
    return _negated(v, _RELEASE_STATUS) or _unnegated(v, _WITHHELD_STATUS)


# ============================== packet rendering (citations, fabricated figures) ==============================
_PACKET_CACHE = {}


def _packet_text(gold) -> str:
    case = gold.get("_case") if isinstance(gold, dict) else None
    if not isinstance(case, dict):
        return ""
    key = str(case.get("case_id"))
    if key not in _PACKET_CACHE:
        try:
            from ..live_options_redemption import build_packet
            _PACKET_CACHE[key] = build_packet(case)
        except Exception:
            _PACKET_CACHE[key] = ""
    return _PACKET_CACHE[key]


def _record_text(gold) -> str:
    """the packet with the DISTRACTOR PCF blocks removed: a citation must come from the PCF of record,
    the recap, the NAV statement, the confirmations or the custodian report"""
    txt = _packet_text(gold)
    if not txt:
        return ""
    try:
        from ..live_options_redemption import _pcf_block
    except Exception:
        return txt
    for p in _distractor_pcfs(gold):
        blk = _pcf_block(p)
        if blk and blk in txt:
            txt = txt.replace(blk, "")
    return txt


def _gold_breaks(gold) -> bool:
    return _numx2(_g(gold, "C3", "excess_contracts")) not in (None, 0.0)


def _has_number(text, n: float, tol=0.5) -> bool:
    """the figure n appears in the text in any common formatting (11,880 / 11880 / 11 880)"""
    if n is None:
        return False
    for m in re.finditer(r"\d[\d,\. ]*\d|\d", _join(text)):
        v = _numx2(m.group(0).replace(" ", ""))
        if v is not None and abs(abs(v) - abs(n)) <= tol:
            return True
    return False


# ============================== evidence detectors (the three evidence-hooked hard gates) ==============================
def _date_evidence(model, gold) -> bool:
    P1m, P1g = _dict(model.get("P1")), _dict(gold.get("P1"))
    case = gold.get("_case") if isinstance(gold, dict) else None
    rec = _record_pcf(gold)
    ok_days = {_day(P1g.get("pcf_date"))}
    if rec:
        ok_days.add(_day(rec.get("published_et")))
    ok_days.discard(None)
    for k in ("trade_date", "settlement_date"):
        d, hedged = _day_pin(P1m.get(k))
        if d is not None and not hedged and not _same(d, P1g.get(k)):
            return True
    d, hedged = _day_pin(P1m.get("pcf_date"))
    if d is not None and not hedged and d not in ok_days:
        return True
    p, hedged, named = _resolve_pcf(P1m.get("pcf_id"), case)
    if p is not None and not hedged and _idn(p.get("ticker")) == _idn(P1g.get("ticker")) \
            and not _same(p.get("basket_date"), P1g.get("pcf_date")):
        return True
    # the basket actually read: the estimated cash component of a same-fund PCF of another date
    est = _numx2(_g(model, "E1", "cash_component_per_cu_estimated"))
    gest = _numx2(_g(gold, "E1", "cash_component_per_cu_estimated"))
    if est is not None and (gest is None or abs(est - gest) > 0.01):
        for q in _distractor_pcfs(gold):
            if _idn(q.get("ticker")) == _idn(P1g.get("ticker")) and _numx2(q.get("cash_component_per_cu_estimated")) is not None \
                    and abs(est - _numx2(q.get("cash_component_per_cu_estimated"))) <= 0.01:
                return True
    return False


def _series_evidence(model, gold) -> bool:
    P1m, P1g = _dict(model.get("P1")), _dict(gold.get("P1"))
    case = gold.get("_case") if isinstance(gold, dict) else None
    gkeys = _series_keys(P1g.get("series_osi"))
    sibs = [q for q in _distractor_pcfs(gold) if _idn(q.get("ticker")) != _idn(P1g.get("ticker"))]
    skeys, sexp, stick, sfund_toks = set(), set(), set(), set()
    for q in sibs:
        skeys |= _series_keys(q.get("legs"))
        for r in _list(q.get("legs")):
            if isinstance(r, dict) and r.get("expiry") is not None:
                sexp.add(_day(r.get("expiry")))
        stick.add(_idn(q.get("ticker")))
        sfund_toks |= set(_toks2(q.get("fund"))) - set(_toks2(P1g.get("fund")))
    skeys -= gkeys
    sexp.discard(None)
    if not sibs:
        return False
    mkeys = _series_keys(P1m.get("series_osi"))
    if mkeys & skeys:
        return True
    d, hedged = _day_pin(P1m.get("series_expiry"))
    if d is not None and not hedged and d in sexp and not _same(d, P1g.get("series_expiry")):
        return True
    p, hedged, named = _resolve_pcf(P1m.get("pcf_id"), case)
    if p is not None and not hedged and _idn(p.get("ticker")) in stick:
        return True
    if _idn(P1m.get("ticker")) in stick:
        return True
    if sfund_toks and set(_toks2(P1m.get("fund"))) & sfund_toks:
        return True
    ekeys = _series_keys([r.get("osi_identifier") for r in _list(_g(model, "E1", "legs", default=[])) if isinstance(r, dict)])
    if ekeys & skeys:
        return True
    due_m = _numx2(_g(model, "C1", "due_contracts_per_leg"))
    due_g = _numx2(_g(gold, "C1", "due_contracts_per_leg"))
    n = _numx2(P1g.get("num_cus")) or 1
    for q in sibs:
        per = [_numx2(r.get("contracts_per_cu")) for r in _list(q.get("legs")) if isinstance(r, dict)]
        per = [x for x in per if x is not None]
        if per and due_m is not None and due_g is not None and abs(due_m - due_g) > 0.5 and abs(due_m - per[0] * n) <= 0.5:
            return True
    return False


_MULT_FACTORS = (100.0, 0.01, 10000.0, 0.0001)


def _axis_hit(mv, gv):
    """-> 'strong' | 'weak' | None: a present model figure on the x100 / /100 axis of gold"""
    if mv is None or gv is None or abs(gv) < 1e-9 or abs(mv) < 1e-12:
        return None
    ratio = abs(mv / gv)
    if abs(ratio - 1.0) <= 0.02:
        return None
    for f in _MULT_FACTORS:
        if abs(ratio / f - 1.0) <= 0.005:
            return "strong"
        if abs(ratio / f - 1.0) <= 0.05:
            return "weak"
    return None


def _mult_evidence(model, gold) -> bool:
    """two independent figures within 5% of the x100 axis, or one within 0.5% - the option value
    implied by the model's own cash component counts as the option figure when none is shown"""
    C2m, C2g = _dict(model.get("C2")), _dict(gold.get("C2"))
    C3m, C3g = _dict(model.get("C3")), _dict(gold.get("C3"))
    D1m, D1g = _dict(model.get("D1")), _dict(gold.get("D1"))
    C1m, C1g = _dict(model.get("C1")), _dict(gold.get("C1"))
    om = _omap(gold)
    sources = []
    gl, ml = _by_leg(C2g.get("leg_values_per_cu"), om), _by_leg(C2m.get("leg_values_per_cu"), om)
    for k, grs in gl.items():
        for mr in ml.get(k, [])[:1]:
            sources.append((_numx2(mr.get("value")), _numx2(grs[0].get("value"))))
    opt_m, opt_g = _numx2(C2m.get("option_value_per_cu")), _numx2(C2g.get("option_value_per_cu"))
    if opt_m is None:
        cash_m, cu_g = _numx2(C2m.get("cash_component_per_cu")), _numx2(C2g.get("cu_value"))
        if cash_m is not None and cu_g is not None:
            opt_m = cu_g - cash_m
    if opt_m is None:                       # the per-order figure is the same source, used only when the others are absent
        oo_m, oo_g = _numx2(C2m.get("option_value_order")), _numx2(C2g.get("option_value_order"))
        if oo_m is not None and oo_g is not None and opt_g:
            opt_m = oo_m * (opt_g / oo_g)
    sources.append((opt_m, opt_g))
    ev_m = _numx2(C3m.get("excess_value"))
    if ev_m is None:
        ev_m = _numx2(D1m.get("excess_value"))
    sources.append((ev_m, _numx2(C3g.get("excess_value"))))
    ec_m = _numx2(C3m.get("excess_contracts"))
    if ec_m is None:
        ec_m = _numx2(D1m.get("excess_contracts"))
    sources.append((ec_m, _numx2(C3g.get("excess_contracts"))))
    sources.append((_numx2(C1m.get("due_contracts_per_leg")), _numx2(C1g.get("due_contracts_per_leg"))))
    strong = weak = 0
    for mv, gv in sources:
        h = _axis_hit(mv, gv)
        if h == "strong":
            strong += 1
        elif h == "weak":
            weak += 1
    return strong >= 1 or weak >= 2


def _sign_evidence(model, gold) -> bool:
    """the written legs ADDED in the model's own cash: cash per unit = unit value - the sum of ABSOLUTE
    leg values (tested on the cash itself, not on a label); or the harm attributed to the AP"""
    C2m, C2g = _dict(model.get("C2")), _dict(gold.get("C2"))
    gl = [_numx2(r.get("value")) for r in _list(C2g.get("leg_values_per_cu")) if isinstance(r, dict)]
    gl = [v for v in gl if v is not None]
    cu_g = _numx2(C2g.get("cu_value"))
    cash_m = _numx2(C2m.get("cash_component_per_cu"))
    if gl and cu_g is not None and cash_m is not None:
        gross = sum(abs(v) for v in gl)
        if abs(sum(gl) - gross) > 1.0 and abs(cash_m - (cu_g - gross)) <= 1.0:
            return True
    return False


# ============================== the handler chain ==============================
def handle(a, ctx):
    model, gold, tol = _dict(ctx.model), ctx.gold, ctx.tol
    aid = a.id

    def det(met, note=""):
        return Verdict(float(met), "deterministic", note)

    P1g, P1m = _dict(gold.get("P1")), _dict(model.get("P1"))
    E1g, E1m = _dict(gold.get("E1")), _dict(model.get("E1"))
    E2g, E2m = _dict(gold.get("E2")), _dict(model.get("E2"))
    C1g, C1m = _dict(gold.get("C1")), _dict(model.get("C1"))
    C2g, C2m = _dict(gold.get("C2")), _dict(model.get("C2"))
    C3g, C3m = _dict(gold.get("C3")), _dict(model.get("C3"))
    D1g, D1m = _dict(gold.get("D1")), _dict(model.get("D1"))
    om = _omap(gold)
    breaks = _gold_breaks(gold)
    case = gold.get("_case") if isinstance(gold, dict) else None

    def num(v, g=None):
        return _zero_or(v, g) if not breaks else _numx2(v)

    # ============================== PLANNING ==============================
    if aid == "P1.1":
        def ftoks(v):
            return set(_toks2(re.sub(r"(?i)\bu\.?s\.?(?=\s|$)", "us", _join(v))))
        gf, mf = ftoks(P1g.get("fund")), ftoks(P1m.get("fund"))
        fund_ok = bool(gf) and (gf <= mf or _jaccard(" ".join(sorted(mf)), " ".join(sorted(gf))) >= 0.75)
        tick = _idn(P1m.get("ticker"))
        tick_ok = tick == _idn(P1g.get("ticker")) or (tick.endswith(_idn(P1g.get("ticker"))) and len(tick) <= len(_idn(P1g.get("ticker"))) + 6
                                                      and bool(re.match(r"^(NYSE|ARCA|NASDAQ|CBOE|BATS|US|USA)", tick)))
        generic = {"capital", "markets", "llc", "inc", "securities", "co", "corp", "ltd", "the", "and", "company", "group"}
        gap = set(_toks2(P1g.get("authorized_participant"))) - generic
        ap_ok = bool(gap) and gap <= set(_toks2(P1m.get("authorized_participant")))
        ok = fund_ok and tick_ok and _idn(P1m.get("order_id")) == _idn(P1g.get("order_id")) and ap_ok
        return det(ok, "order identity")
    if aid == "P1.2":   # the plain pin; GATE.DATE is the evidence hook P1.n_wrongdate
        rec = _record_pcf(gold)
        ok_days = {_day(P1g.get("pcf_date"))}
        if rec:
            ok_days.add(_day(rec.get("published_et")))
        ok_days.discard(None)
        t, th = _day_pin(P1m.get("trade_date"))
        s_, sh = _day_pin(P1m.get("settlement_date"))
        p_, ph = _day_pin(P1m.get("pcf_date"))
        ok = (t is not None and not th and _same(t, P1g.get("trade_date"))
              and s_ is not None and not sh and _same(s_, P1g.get("settlement_date"))
              and p_ is not None and not ph and p_ in ok_days)
        pid = P1m.get("pcf_id")
        if ok and pid not in (None, ""):
            p, hedged, named = _resolve_pcf(pid, case)
            if hedged or p is None or _idn(p.get("pcf_id")) != _idn(P1g.get("pcf_id")):
                ok = False
        return det(ok, "dates + PCF of record pinned")
    if aid == "P1.3":   # the plain pin; GATE.SERIES is the evidence hook P1.n_wrongseries
        gset = _series_keys(P1g.get("series_osi"))
        mset = _series_keys(P1m.get("series_osi"))
        if not mset:
            mset = _series_keys([r.get("osi_identifier") for r in _list(E1m.get("legs")) if isinstance(r, dict)])
        d, hedged = _day_pin(P1m.get("series_expiry"))
        ok = bool(gset) and mset == gset and d is not None and not hedged and _same(d, P1g.get("series_expiry"))
        return det(ok, "series pinned to the fund's outcome period")
    if aid == "P1.4":
        ok = (within(_numx2(P1m.get("num_cus")), _numx2(P1g.get("num_cus")), "count_exact", tol)
              and within(_numx2(P1m.get("cu_size")), _numx2(P1g.get("cu_size")), "count_exact", tol)
              and within(_numx2(P1m.get("total_shares")), _numx2(P1g.get("total_shares")), "count_exact", tol)
              and within(_numx2(P1m.get("nav_per_share")), _numx2(P1g.get("nav_per_share")), "nav_4dp", tol)
              and within(_numx2(P1m.get("redemption_value")), _numx2(P1g.get("redemption_value")), "usd_dollar", tol)
              and within(_numx2(P1m.get("transaction_fee")), _numx2(P1g.get("transaction_fee")), "usd_cents", tol)
              and _norm_flow(P1m.get("settlement_flow")) == _norm_flow(P1g.get("settlement_flow"))
              and (P1m.get("direction") is None or _redeem_direction(P1m.get("direction"))))
        return det(ok, "order terms")
    if aid == "P1.5":
        ok = all(not _placeholder(P1m.get(k)) for k in ("fund", "order_id", "num_cus", "settlement_flow")) \
            and all(_day_pin(P1m.get(k))[0] is not None for k in ("trade_date", "settlement_date", "pcf_date")) \
            and _numx2(P1m.get("num_cus")) is not None
        return det(ok, "pinned-order object")

    # ============================== EXTRACTION ==============================
    if aid == "E1.legs":
        gl, ml = _by_leg(E1g.get("legs"), om), _by_leg(E1m.get("legs"), om)
        if not gl:
            return det(0.0, "no gold legs")
        ok = 0
        for k, grs in gl.items():
            gr, mrs = grs[0], ml.get(k, [])
            if mrs and all(_series_key(mr.get("osi_identifier")) == _series_key(gr.get("osi_identifier"))
                           and _norm_cp(mr.get("put_or_call")) == _norm_cp(gr.get("put_or_call"))
                           and within(_numx2(mr.get("strike")), _numx2(gr.get("strike")), "strike_exact", tol)
                           and _same(mr.get("expiry"), gr.get("expiry"))
                           and _norm_side(mr.get("side")) == _norm_side(gr.get("side"))
                           and within(_numx2(mr.get("contracts_per_cu")), _numx2(gr.get("contracts_per_cu")), "count_exact", tol)
                           and within(_numx2(mr.get("multiplier")), _numx2(gr.get("multiplier")), "count_exact", tol)
                           and _european(mr.get("exercise_style"))
                           for mr in mrs):
                ok += 1
        return det(ok / len(gl), "basket legs read")
    if aid == "E1.cash":
        ok = (within(_numx2(E1m.get("cash_component_per_cu_estimated")), _numx2(E1g.get("cash_component_per_cu_estimated")), "usd_cents", tol)
              and within(_numx2(E1m.get("cash_component_per_cu_final")), _numx2(E1g.get("cash_component_per_cu_final")), "usd_cents", tol)
              and within(_numx2(E1m.get("transaction_fee")), _numx2(E1g.get("transaction_fee")), "usd_cents", tol))
        return det(ok, "basket cash terms")
    if aid == "E1.recap":
        gr, mr = _dict(E1g.get("recap")), _dict(E1m.get("recap"))
        gl, ml = _by_leg(gr.get("legs"), om), _by_leg(mr.get("legs"), om)
        legs_ok = bool(gl) and all(
            ml.get(k) and all(within(_numx2(r.get("contracts_claimed", r.get("contracts"))), _numx2(grs[0].get("contracts_claimed")), "count_exact", tol)
                              and _unnegated(r.get("status_claimed", r.get("status")), {"transferred", "transfer", "complete", "completed", "done"})
                              for r in ml[k])
            for k, grs in gl.items())
        st = mr.get("status_claimed", mr.get("status"))
        ok = (legs_ok
              and within(_numx2(mr.get("cash_component")), _numx2(gr.get("cash_component")), "usd_cents", tol)
              and within(_numx2(mr.get("net_cash_to_ap")), _numx2(gr.get("net_cash_to_ap")), "usd_cents", tol)
              and _unnegated(st, {"ready", "settle", "release"}) and not _negated(st, {"ready", "settle", "release"}))
        return det(ok, "agent recap read as claimed")
    if aid == "E1.cite":
        mc = E1m.get("citation")
        mc = mc if isinstance(mc, dict) else {}
        doc_ok = _ws(mc.get("document")) in ("pcf", "pcfs", "packet", "basket", "pcf of record", "recap", "agent_recap",
                                              "agent recap", "nav_statement", "nav statement", "statement", "order",
                                              "custodian", "custodian_position_report", "confirmations", "occ")
        mv = _ws(mc.get("verbatim"))
        rec = _ws(_record_text(gold))
        frags = [f for f in (_ws(x) for x in re.split(r"\.\.\.|…|\n", str(mc.get("verbatim") or ""))) if len(f.split()) >= 2]
        if not frags and mv:
            frags = [mv]
        in_record = bool(frags) and (not rec or all(f in rec for f in frags))
        lines = [E1g.get("citation")] + [c for c in _list(E1g.get("citation_alternates")) if isinstance(c, dict)]
        entails = False
        for c in lines:
            if not isinstance(c, dict):
                continue
            gv = _ws(c.get("verbatim"))
            if not gv or not mv:
                continue
            if any(_jaccard(f, gv) >= 0.5 or (f in gv and len(f.split()) >= 4) for f in frags):
                entails = True
        return Verdict(1.0 if (doc_ok and in_record and entails) else 0.0, "entailment", "packet citation")
    if aid == "E2.confirms":
        gc, mc = _by_leg(E2g.get("confirmations"), om), _by_leg(E2m.get("confirmations"), om)
        if not gc:
            return det(0.0, "no gold confirmations")

        def tid_ok(mr, gr):
            t = mr.get("transfer_id")
            if t in (None, ""):
                return True
            md, gd = re.sub(r"\D", "", _s(t)), re.sub(r"\D", "", _s(gr.get("transfer_id")))
            return bool(md) and (gd.endswith(md) or md.endswith(gd) or md == gd)
        ok = 0
        for k, grs in gc.items():
            gr, mrs = grs[0], mc.get(k, [])
            if mrs and all(within(_numx2(mr.get("quantity")), _numx2(gr.get("quantity")), "count_exact", tol)
                           and _status_accepted(mr.get("status"))
                           and tid_ok(mr, gr)
                           and (mr.get("position_type") is None or _norm_side(mr.get("position_type")) == _norm_side(gr.get("position_type")))
                           and (mr.get("osi_identifier") is None or _series_key(mr.get("osi_identifier")) == _series_key(gr.get("osi_identifier")))
                           and (mr.get("effective_date") is None or _same(mr.get("effective_date"), gr.get("effective_date")))
                           and (mr.get("from_account") is None or "0471" in str(mr.get("from_account")))
                           and (mr.get("to_account") is None or "0829" in str(mr.get("to_account")))
                           for mr in mrs):
                ok += 1
        return det(ok / len(gc), "OCC confirmations captured as confirmed")
    if aid == "E2.positions":
        gp, mp = _by_leg(E2g.get("positions"), om), _by_leg(E2m.get("positions"), om)
        if not gp:
            return det(0.0, "no gold positions")

        def pos_ok(mr, gr, key):
            mv, gv = _numx2(mr.get(key)), _numx2(gr.get(key))
            if mv is None or gv is None:
                return False
            if abs(mv - gv) <= 0.001:
                return True
            # the absolute convention: a written leg reported as a positive quantity with a side field
            side = _norm_side(mr.get("side") or mr.get("position_type")) or om.get("desc", {}).get(_leg_key(gr, om), (None, None, None))[2]
            return gv < 0 and side == "short" and abs(mv - abs(gv)) <= 0.001
        ok = 0
        for k, grs in gp.items():
            gr, mrs = grs[0], mp.get(k, [])
            if mrs and all(pos_ok(mr, gr, "position_prior") and pos_ok(mr, gr, "position_current")
                           and within(abs(_numx2(mr.get("transferred_out")) or -1.0), abs(_numx2(gr.get("transferred_out"))), "count_exact", tol)
                           for mr in mrs):
                ok += 1
        return det(ok / len(gp), "custodian positions captured")
    if aid == "E2.nav":
        gn, mn = _dict(E2g.get("nav")), _dict(E2m.get("nav"))
        gm = _dict(gn.get("marks"))
        raw = mn.get("marks")
        mm = {}
        if isinstance(raw, dict):
            for k, v in raw.items():
                mm[_leg_key({"leg_id": k}, om)] = v
        else:
            for r in _list(raw):
                if isinstance(r, dict):
                    mm[_leg_key(r, om)] = r.get("mark", r.get("value", r.get("price")))
        marks_ok = bool(gm) and all(within(_numx2(mm.get(_idn(k))), _numx2(v), "mark_4dp", tol) for k, v in gm.items())
        ok = (marks_ok
              and within(_numx2(mn.get("nav_per_share")), _numx2(gn.get("nav_per_share")), "nav_4dp", tol)
              and within(_numx2(mn.get("shares_outstanding")), _numx2(gn.get("shares_outstanding")), "count_exact", tol)
              and within(_numx2(mn.get("total_net_assets")), _numx2(gn.get("total_net_assets")), "usd_dollar", tol)
              and (mn.get("marks_date") is None or _same(mn.get("marks_date"), gn.get("marks_date"))))
        return det(ok, "NAV statement + marks")
    if aid == "E2.shares":
        gs, ms = _dict(E2g.get("share_receipt")), _dict(E2m.get("share_receipt"))
        st = _join([ms.get("status"), ms.get("basis")])
        ok = (within(_numx2(ms.get("quantity")), _numx2(gs.get("quantity")), "count_exact", tol)
              and _unnegated(st, {"received", "receipt", "delivered", "pending", "fop", "free", "credited", "in"})
              and not _negated(st, {"received", "delivered", "receipt"})
              and _cash_withheld(E2m.get("cash_component_payment_status")))
        return det(ok, "share receipt + cash payment status")

    # ============================== CALCULATION ==============================
    if aid == "C1.due":
        ok = (within(_numx2(C1m.get("due_contracts_per_leg")), _numx2(C1g.get("due_contracts_per_leg")), "count_exact", tol)
              and within(_numx2(C1m.get("due_shares")), _numx2(C1g.get("due_shares")), "count_exact", tol))
        return det(ok, "due quantities (contracts; shares)")
    if aid == "C1.match":
        gl, ml = _by_leg(C1g.get("ledger"), om), _by_leg(C1m.get("ledger"), om)
        if not gl:
            return det(0.0, "no gold ledger")

        def row_ok(mr, gr):
            gt = _norm_tie(gr.get("tie"))
            mt = _norm_tie(mr.get("tie", mr.get("tie_status", mr.get("result", mr.get("status_tie")))))
            if mt != gt:
                return False
            if not within(_numx2(mr.get("due_contracts", mr.get("due"))), _numx2(gr.get("due_contracts")), "count_exact", tol):
                return False
            if not within(_numx2(mr.get("confirmed_contracts", mr.get("confirmed"))), _numx2(gr.get("confirmed_contracts")), "count_exact", tol):
                return False
            if gt == "match":
                for fld in ("series_match", "side_match"):
                    b = _bool(mr.get(fld)) if mr.get(fld) is not None else None
                    if b is False:
                        return False
                st = mr.get("status")
                if st not in (None, "") and _leg_key(gr, om) != "SHARES" and not _status_accepted(st):
                    return False
            return True
        ok = sum(1 for k, grs in gl.items() if ml.get(k) and all(row_ok(mr, grs[0]) for mr in ml[k]))
        return det(ok / len(gl), "per-leg tie map with quantities")
    if aid == "C1.positions":
        gp, mp = _by_leg(C1g.get("position_check"), om), _by_leg(C1m.get("position_check"), om)
        if not gp:
            return det(0.0, "no gold position check")

        def pc_ok(mr, gr):
            gmatch = _norm_tie(gr.get("tie")) == "match"
            mv = _verdict(mr.get("tie"))
            if gmatch:
                tie_ok = mv == "pos"
            else:
                tie_ok = mv == "neg" or _has_number(mr.get("tie"), abs((_numx2(gr.get("expected_current")) or 0) - (_numx2(gr.get("actual_current")) or 0)))
            if not tie_ok:
                return False
            for key in ("expected_current", "actual_current"):
                m_, g_ = _numx2(mr.get(key)), _numx2(gr.get(key))
                if m_ is None or g_ is None:
                    return False
                if abs(m_ - g_) > 0.001:
                    side = _norm_side(mr.get("side")) or om.get("desc", {}).get(_leg_key(gr, om), (None, None, None))[2]
                    if not (g_ < 0 and side == "short" and abs(m_ - abs(g_)) <= 0.001):
                        return False
            return True
        ok = sum(1 for k, grs in gp.items() if mp.get(k) and all(pc_ok(mr, grs[0]) for mr in mp[k]))
        return det(ok / len(gp), "custodian cross-check per leg")
    if aid == "C1.exceptions":
        gex = _by_leg(C1g.get("exceptions"), om)
        rows = [r for r in _list(C1m.get("exceptions")) if isinstance(r, dict)]
        own_cash_ties = _ties_bool(C2m.get("cash_ties")) is True or (
            _numx2(C2m.get("cash_difference")) is not None and abs(_numx2(C2m.get("cash_difference"))) <= (_numx2(_g(gold, "manifest", "cash_tie_tolerance_usd")) or 5.0))
        real = [r for r in rows if not _informational(dict(r, line_id=r.get("leg_id"))) and not _no_exception_row(r)
                and not (_leg_key(r, om) not in _gold_legs(gold) | {"SHARES"} and own_cash_ties)]
        if not gex:
            return det(not real, "no exception on a clean order")
        mex = _by_leg(real, om)
        ok = True
        qty_words = {"quantity", "qty", "contracts", "contract", "excess", "over", "overdelivered", "overdelivery", "overtransfer",
                     "overtransferred", "multiplier", "shares", "equivalent", "keyed", "count", "surplus", "extra"}
        for k, grs in gex.items():
            mrs = mex.get(k)
            if not mrs:
                ok = False
                continue
            txt = " ".join(_join([mr.get("type"), mr.get("detail")]) for mr in mrs)
            toks = set(_toks2(txt))
            if toks & _KIND_SERIES and not toks & qty_words:
                ok = False
                continue
            qty = _unnegated(txt, qty_words) or _has_number(txt, 12000) or _has_number(txt, 11880)
            if not qty or _negated(txt, {"quantity", "issue", "problem", "mismatch", "excess"}) and not _has_number(txt, 12000):
                ok = False
        extra = set(mex) - set(gex)
        return det(ok and not extra, "exception locus = the over-transferred leg")
    if aid == "C1.structure":
        keys = set()
        for r in _list(C1m.get("ledger")):
            if not isinstance(r, dict):
                continue
            k = _leg_key(r, om)
            if k in _gold_legs(gold) and r.get("tie", r.get("tie_status", r.get("result"))) not in (None, "") \
                    and (_numx2(r.get("due_contracts", r.get("due"))) is not None or _numx2(r.get("confirmed_contracts", r.get("confirmed"))) is not None):
                keys.add(k)
        return det(len(keys) >= 4, "structured tie ledger")
    if aid == "C2.legvalues":
        gl, ml = _by_leg(C2g.get("leg_values_per_cu"), om), _by_leg(C2m.get("leg_values_per_cu"), om)
        opt_ok = within(_numx2(C2m.get("option_value_per_cu")), _numx2(C2g.get("option_value_per_cu")), "usd_cents", tol)

        def val_ok(mr, gr):
            mv, gv = _numx2(mr.get("value")), _numx2(gr.get("value"))
            if mv is None or gv is None:
                return False
            if abs(mv - gv) <= 0.01:
                return True
            # magnitudes with the sign carried separately (sign field or a written leg) are a display choice
            # when the model netted correctly
            sgn = _numx2(mr.get("sign"))
            side = _norm_side(mr.get("side"))
            if opt_ok and abs(abs(mv) - abs(gv)) <= 0.01 and (sgn is not None and sgn < 0 or side == "short" or gv < 0):
                return True
            return False
        legs_ok = bool(gl) and all(ml.get(k) and all(val_ok(mr, grs[0]) for mr in ml[k]) for k, grs in gl.items())
        return det(legs_ok and opt_ok, "per-leg values per unit + option value per unit")
    if aid == "C2.scale":   # the plain atom: a recomputation is SHOWN and not on the wrong axis (GATE.MULTIPLIER = C2.n_multiplier)
        shown = (_numx2(C2m.get("option_value_per_cu")) is not None
                 or any(_numx2(r.get("value")) is not None for r in _list(C2m.get("leg_values_per_cu")) if isinstance(r, dict))) \
            and _numx2(C2m.get("cash_component_per_cu")) is not None
        return det(shown and not _mult_evidence(model, gold), "recomputation shown, contract multiplier scale right")
    if aid == "C2.cash":
        ok = all(within(_numx2(C2m.get(k)), _numx2(C2g.get(k)), "usd_cents", tol)
                 for k in ("cu_value", "cash_component_per_cu", "cash_component_order", "transaction_fee", "net_cash_to_ap"))
        ok = ok and (C2m.get("redemption_value") is None or within(_numx2(C2m.get("redemption_value")), _numx2(C2g.get("redemption_value")), "usd_dollar", tol))
        ok = ok and (C2m.get("option_value_order") is None or within(_numx2(C2m.get("option_value_order")), _numx2(C2g.get("option_value_order")), "usd_cents", tol))
        # internal consistency: the cash must follow from the model's OWN option value (or its leg values)
        opt_m = _numx2(C2m.get("option_value_per_cu"))
        if opt_m is None:
            legs = [_numx2(r.get("value")) for r in _list(C2m.get("leg_values_per_cu")) if isinstance(r, dict)]
            legs = [v for v in legs if v is not None]
            opt_m = sum(legs) if legs else None
        cu_m, cash_m = _numx2(C2m.get("cu_value")), _numx2(C2m.get("cash_component_per_cu"))
        if opt_m is None or cu_m is None or cash_m is None or abs((cu_m - opt_m) - cash_m) > 1.0:
            ok = False
        return det(ok, "cash component per unit, for the order, fee, net cash (consistent with the legs)")
    if aid == "C2.tie":
        agent = _numx2(C2m.get("agent_cash_component"))
        diff = _numx2(C2m.get("cash_difference"))
        own = _numx2(C2m.get("cash_component_order"))
        ties = _ties_bool(C2m.get("cash_ties"))
        tolerance = _numx2(_g(gold, "manifest", "cash_tie_tolerance_usd")) or 5.0
        ok = (agent is not None and within(agent, _numx2(C2g.get("agent_cash_component")), "usd_cents", tol)
              and diff is not None and own is not None and abs(diff - (agent - own)) <= 0.01
              and ties is not None and ties == (abs(diff) <= tolerance)
              and (C3m.get("cash_component_affected") is None or _bool(C3m.get("cash_component_affected")) == (not (abs(diff) <= tolerance))))
        return det(ok, "agent's cash component tested against the model's own recomputation")
    if aid == "C3.excess":
        ol = C3m.get("offending_leg")
        olk = _leg_key({"leg_id": ol}, om) if not _placeholder(ol) else ""
        leg_ok = (olk == _idn(C3g.get("offending_leg"))) if breaks else (olk in ("", "NONE", "NULL", "NA", "NIL", "NOTAPPLICABLE"))
        # live-grid calibration 2026-10-21: on the clean twin there is no offending leg, so the two position fields
        # may be null; `ap_received_option_value` was never defined in the schema (three models read it three ways:
        # total received, excess only, the whole offending leg) and is not graded - the break is sized by the
        # excess fields; the schema now defines it for future runs
        pos_ok = (within(_numx2(C3m.get("fund_position_due")), _numx2(C3g.get("fund_position_due")), "count_exact", tol)
                  and within(_numx2(C3m.get("fund_position_actual")), _numx2(C3g.get("fund_position_actual")), "count_exact", tol)) \
            or (not breaks and _placeholder(C3m.get("fund_position_due")) and _placeholder(C3m.get("fund_position_actual")))
        ok = (leg_ok and pos_ok
              and within(num(C3m.get("excess_contracts"), C3g.get("excess_contracts")), _numx2(C3g.get("excess_contracts")), "count_exact", tol)
              and within(num(C3m.get("excess_value"), C3g.get("excess_value")), _numx2(C3g.get("excess_value")), "usd_dollar", tol)
              and (C3m.get("fund_position_short_by") is None or within(num(C3m.get("fund_position_short_by"), C3g.get("fund_position_short_by")), _numx2(C3g.get("fund_position_short_by")), "count_exact", tol)))
        return det(ok, "break quantified (leg, contracts, value, positions)")
    if aid == "C3.direction":
        ok = (_norm_direction(C3m.get("direction")) == _norm_direction(C3g.get("direction"))
              and _norm_party(C3m.get("harmed")) == _norm_party(C3g.get("harmed"))
              and (C3m.get("enriched") is None or _norm_party(C3m.get("enriched")) == _norm_party(C3g.get("enriched"))))
        return det(ok, "direction + who is harmed")
    if aid == "C3.impact":
        gp = _numx2(C3g.get("impact_pct_of_nav"))
        ok = (within(num(C3m.get("impact_per_remaining_share"), C3g.get("impact_per_remaining_share")), _numx2(C3g.get("impact_per_remaining_share")), "usd_mils", tol)
              and within(_zero_or(C3m.get("impact_pct_of_nav"), gp) if not breaks else _pct2(C3m.get("impact_pct_of_nav"), gp), gp, "pct_2dp", tol)
              and within(_numx2(C3m.get("shares_outstanding_after")), _numx2(C3g.get("shares_outstanding_after")), "count_exact", tol))
        return det(ok, "consequence per remaining share")

    # ============================== DECISION ==============================
    dec_cls = _classify_decision(D1m.get("decision"))
    rel, can = (_bool(D1m.get("release_cash")) if D1m.get("release_cash") is not None else None,
                _bool(D1m.get("cancel_shares")) if D1m.get("cancel_shares") is not None else None)
    action_settle = (_settle_instruction(D1m.get("escalate_to")) or _settle_instruction(D1m.get("remedy"))
                     or _settle_instruction(D1m.get("offending_reason")) or rel is True or can is True)
    if aid == "D1.decision":
        gc = _classify_decision(D1g.get("decision"))
        note = ("contradictory decision (settle AND hold)" if _is_ambiguous_decision(D1m.get("decision"))
                else "unclassified decision (the schema demands SETTLE|HOLD)" if dec_cls is None
                else "settle/hold call (class match)")
        if dec_cls == "hold" and action_settle:
            return det(0.0, "hold decision with a release instruction in the action fields or switches (contradictory)")
        if dec_cls == "settle" and (rel is False or can is False or _hold_instruction(D1m.get("remedy"))):
            return det(0.0, "settle decision whose own switches or remedy withhold the cash or the shares (contradictory)")
        return det(gc is not None and dec_cls == gc, note)
    if aid in ("D1.localize", "D1.remedy", "D1.record") and (dec_cls is None or (dec_cls == "hold" and action_settle)):
        return det(0.0, "no actionable decision: the D1 checkpoint is not credited")
    if aid == "D1.localize":
        ol = D1m.get("offending_leg")
        olk = _leg_key({"leg_id": ol} if not isinstance(ol, dict) else ol, om) if not _placeholder(ol) else ""
        if olk == "" and not _placeholder(D1m.get("offending_series")):
            olk = om["keys"].get(_series_key(D1m.get("offending_series")) or "", "")
        exc_ok = within(num(D1m.get("excess_contracts"), D1g.get("excess_contracts")), _numx2(D1g.get("excess_contracts")), "count_exact", tol)
        if not breaks:
            return det(olk in ("", "NONE", "NULL", "NA", "NIL", "NOTAPPLICABLE") and exc_ok, "clean settle: no offending leg")
        series_ok = True
        if not _placeholder(D1m.get("offending_series")):
            sk = _series_key(D1m.get("offending_series"))
            series_ok = sk is not None and om["keys"].get(sk) == _idn(D1g.get("offending_leg"))
        ok = (olk == _idn(D1g.get("offending_leg")) and exc_ok and series_ok
              and within(_numx2(D1m.get("due_contracts")), _numx2(D1g.get("due_contracts")), "count_exact", tol)
              and within(_numx2(D1m.get("confirmed_contracts")), _numx2(D1g.get("confirmed_contracts")), "count_exact", tol)
              and within(_numx2(D1m.get("excess_value")), _numx2(D1g.get("excess_value")), "usd_dollar", tol))
        return det(ok, "offending leg + due/confirmed/excess + value")
    if aid == "D1.remedy":
        rem = _join(D1m.get("remedy"))
        toks = set(_toks2(rem))
        if not breaks:
            # live-grid calibration 2026-10-21: the settlement actions may be stated in the structured switches
            # (release_cash + cancel_shares true) or in words; the net-cash figure is not required in the text
            switches = rel is True and can is True
            words = (_unnegated(rem, {"release", "released", "pay", "paid", "wire", "wired", "disburse"})
                     and _unnegated(rem, {"cancel", "cancelled", "canceled", "retire", "retired", "extinguish"}))
            return det(switches or words, "clean order: release and cancel (switches or words)")
        corrective = bool(toks & _CORRECTIVE) or ("transfer" in toks and bool(toks & {"back", "return", "returned", "reverse", "reversed", "fund", "kestrel"}))
        quantity = _has_number(rem, _numx2(_g(gold, "C3", "excess_contracts")))
        wrong_way = bool(re.search(r"\b(further|additional|more|extra)\b[^.;]{0,60}\bto the (ap|redeemer|participant)\b|\bto (the ap|harrowgate|cm 0829|the ap'?s account)\b[^.;]{0,40}\b(before|then|first)\b|\bowe[sd]? the ap\b",
                                   rem.lower()))
        to_fund = bool(toks & {"fund", "kestrel", "grbo", "back"}) or "0471" in rem
        release_words = {"release", "released", "releasing", "pay", "paid", "paying", "wire", "wired", "cancel", "cancelled",
                         "canceled", "settle", "settled", "mark", "disburse"}
        sequenced = (not toks & release_words) or bool(toks & {"before", "prior", "until", "first", "then", "after", "afterwards",
                                                                "afterward", "once", "upon", "only", "pending", "withhold",
                                                                "withheld", "hold", "not", "subsequently", "thereafter",
                                                                "confirmation", "confirmed", "completion", "receipt", "following",
                                                                "subject", "conditional", "contingent", "when", "if", "provided"})
        party_txt = _join([D1m.get("escalate_to"), rem])
        parties = bool(set(_toks2(party_txt)) & {"clearing", "member", "members", "cm", "kestrel", "harrowgate", "broker", "occ",
                                                 "agent", "cm0471", "cm0829"})
        return det(corrective and quantity and to_fund and not wrong_way and sequenced and parties,
                   "corrective return, sized, to the fund, before release; parties named")
    if aid == "D1.record":
        def prose(v, n=3):
            t = _toks2(v)
            return isinstance(v, (str, list)) and len(t) >= n and not (isinstance(v, str) and _placeholder(v))
        domain = {"transfer", "transferred", "release", "released", "cancel", "cancelled", "canceled", "settle", "settled",
                  "contracts", "return", "returned", "reverse", "reversed", "hold", "cash", "shares", "correct", "corrected",
                  "recap", "confirm", "confirmed", "wire", "mark", "occ", "position", "leg", "clearing", "fund", "ap"}
        if not breaks:
            stated = (rel is True and can is True) or (prose(D1m.get("remedy"), 5) and bool(set(_toks2(D1m.get("remedy"))) & domain))
            return det(D1m.get("decision") not in (None, "") and stated
                       and num(D1m.get("excess_contracts"), D1g.get("excess_contracts")) is not None, "structured settle record emitted")
        ok = (D1m.get("decision") not in (None, "") and not _placeholder(D1m.get("offending_leg"))
              and prose(D1m.get("remedy"), 5) and bool(set(_toks2(D1m.get("remedy"))) & domain)
              and prose(D1m.get("escalate_to"), 2)
              and all(_numx2(D1m.get(k)) is not None for k in ("due_contracts", "confirmed_contracts", "excess_contracts", "excess_value")))
        return det(ok, "structured exception emitted")

    return None   # penalties (handled below) / D2 (handled by refusal) / fallthrough


def _ties_bool(v):
    """the cash_ties flag: exceeds / outside / break mean it does NOT tie; ties within tolerance that it does"""
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return bool(v)
    toks = set(_toks2(v))
    if not toks:
        return None
    if toks & {"exceeds", "exceeded", "exceed", "above", "outside", "breaks", "break", "mismatch", "differs", "no", "false",
               "not", "fails", "fail"}:
        return False
    if toks & {"ties", "tie", "tied", "yes", "true", "within", "matches", "match", "ok", "agrees", "reconciles", "y", "t"}:
        return True
    return _bool(v)


def _hold_instruction(v) -> bool:
    """a remedy that withholds the cash or the shares (a SETTLE with 'do not release' is a contradiction)"""
    text = _join(v)
    for clause in _clauses(text):
        toks = _clause_tokens(clause)
        for i, t in enumerate(toks):
            if t in {"release", "released", "cancel", "cancelled", "canceled", "settle", "settled", "pay", "paid", "wire"} \
                    and any(p in ("not", "no", "never", "dont", "cannot", "cant", "withhold", "withheld") for p in toks[max(0, i - 4):i]):
                return True
    return False


def _no_exception_row(r: dict) -> bool:
    """an 'exception' row that reports a clean tie ('All four legs tie out', 'nil', 'n/a')"""
    txt = _join([r.get("type"), r.get("detail"), r.get("leg_id")]).lower()
    toks = set(_toks2(txt))
    if not toks:
        return True
    if toks <= {"nil", "none", "na", "n", "a", "summary", "info", "informational", "ok", "clean", "note"}:
        return True
    if _unnegated(txt, {"tie", "ties", "tied", "match", "matches", "matched", "reconciled", "clean"}) \
            and not toks & {"mismatch", "excess", "over", "missing", "break", "quantity", "x"}:
        return True
    return False


# ============================== penalty detectors ==============================
def penalty_present(a, model, gold) -> bool:
    model = _dict(model)
    inj = model.get("_injected_penalties")
    inj = set(inj) if isinstance(inj, list) else set()
    om = _omap(gold)
    E1g, E1m = _dict(gold.get("E1")), _dict(model.get("E1"))
    E2g, E2m = _dict(gold.get("E2")), _dict(model.get("E2"))
    C1g, C1m = _dict(gold.get("C1")), _dict(model.get("C1"))
    C2m = _dict(model.get("C2"))
    C3g, C3m = _dict(gold.get("C3")), _dict(model.get("C3"))
    D1m = _dict(model.get("D1"))
    gold_legs = _gold_legs(gold)
    if a.id == "P1.n_wrongdate":
        return _date_evidence(model, gold) or "P1.n_wrongdate" in inj
    if a.id == "P1.n_wrongseries":
        return _series_evidence(model, gold) or "P1.n_wrongseries" in inj
    if a.id == "C2.n_multiplier":
        return _mult_evidence(model, gold) or "C2.n_multiplier" in inj
    if a.id == "E1.n_omit":
        present = set()
        for r in _list(E1m.get("legs")):
            if isinstance(r, dict) and any(r.get(k) is not None for k in ("osi_identifier", "strike", "contracts_per_cu", "put_or_call")):
                present.add(_leg_key(r, om))
        return bool(gold_legs - present) or "E1.n_omit" in inj
    if a.id == "E2.n_halluc":
        gq = {_leg_key(r, om): _numx2(r.get("quantity")) for r in _list(E2g.get("confirmations")) if isinstance(r, dict)}
        seen = {}
        for r in _list(E2m.get("confirmations")):
            if not isinstance(r, dict):
                continue
            k = _leg_key(r, om)
            if k == "SHARES":
                continue
            if k == "" and _numx2(r.get("quantity")) is not None:
                return True                                   # an id-less numeric confirmation
            if k not in gold_legs:
                if _looks_like_leg(k, r):
                    return True                               # a confirmation for a leg not in the basket
                continue
            q = _numx2(r.get("quantity"))
            seen.setdefault(k, []).append(q)
        for k, qs in seen.items():                            # a second confirmation for one leg with a quantity the packet never shows
            if len(qs) > 1 and any(q is not None and gq.get(k) is not None and abs(q - gq[k]) > 0.5 for q in qs):
                return True
        for rows in (E2m.get("positions"), E1m.get("legs"), _dict(E1m.get("recap")).get("legs"), C1m.get("ledger"),
                     C2m.get("leg_values_per_cu"), C1m.get("position_check"), C1m.get("exceptions"),
                     _dict(_dict(E2m.get("nav")).get("marks")) if isinstance(_dict(E2m.get("nav")).get("marks"), list) else None):
            for r in _list(rows):
                if isinstance(r, dict):
                    k = _leg_key(r, om)
                    if k not in gold_legs and k != "SHARES" and _looks_like_leg(k, r):
                        return True
        return "E2.n_halluc" in inj
    if a.id == "C1.n_recap_blind":
        if not _gold_breaks(gold):
            return "C1.n_recap_blind" in inj
        bad = {_leg_key(r, om) for r in _list(C1g.get("exceptions")) if isinstance(r, dict)}
        gl, ml = _by_leg(C1g.get("ledger"), om), _by_leg(C1m.get("ledger"), om)
        claimed = {_leg_key(r, om): _numx2(r.get("contracts_claimed")) for r in _list(_g(gold, "E1", "recap", "legs", default=[])) if isinstance(r, dict)}
        for k in bad:
            gconf = _numx2((gl.get(k) or [{}])[0].get("confirmed_contracts"))
            for r in ml.get(k, []):
                if _verdict(r.get("tie", r.get("tie_status", r.get("result")))) == "pos":
                    return True
                conf = _numx2(r.get("confirmed_contracts", r.get("confirmed")))
                cl = claimed.get(k)
                if conf is not None and cl is not None and gconf is not None and abs(conf - cl) < 0.5 and abs(gconf - cl) >= 0.5:
                    return True
        return "C1.n_recap_blind" in inj
    if a.id == "C3.n_signflip":
        gd, md = _norm_direction(C3g.get("direction")), _norm_direction(C3m.get("direction"))
        if {gd, md} == {"over", "under"}:
            return True
        if _gold_breaks(gold):
            gh, ge = _norm_party(C3g.get("harmed")), _norm_party(C3g.get("enriched"))
            mh = _norm_party(C3m.get("harmed"))
            if mh is not None and mh != "none" and ge not in (None, "none") and mh == ge and gh != ge:
                return True                                   # the remaining shareholders' loss attributed to the AP
        if _sign_evidence(model, gold):
            return True
        return "C3.n_signflip" in inj
    if a.id == "D1.n_override":
        # the GATE.SETTLE hook: an unconditional SETTLE decision, a settle/release instruction in the action
        # fields, or the release/cancel switches set, on an order whose legs do not all tie. A contradictory or
        # unclassified decision does NOT fire.
        if not _gold_breaks(gold):
            return "D1.n_override" in inj
        rel = _bool(D1m.get("release_cash")) if D1m.get("release_cash") is not None else None
        can = _bool(D1m.get("cancel_shares")) if D1m.get("cancel_shares") is not None else None
        return (_classify_decision(D1m.get("decision")) == "settle" or _settle_instruction(D1m.get("escalate_to"))
                or _settle_instruction(D1m.get("remedy")) or _settle_instruction(D1m.get("offending_reason"))
                or rel is True or can is True or "D1.n_override" in inj)
    if a.id == "D1.n_falsehold":
        return (not _gold_breaks(gold) and _classify_decision(D1m.get("decision")) == "hold") or "D1.n_falsehold" in inj
    return a.id in inj


# ============================== mock judge positives ==============================
def judge_mock(a, model, gold) -> float:
    return 1.0 if _dict(model).get(a.checkpoint) else 0.0


# ============================== D2 calibrated refusal ==============================
_COST_WORDS = {"cost", "costs", "basis", "paid", "pay", "pays", "purchase", "purchased", "bought", "buy", "acquisition",
               "acquired", "acquire", "entry", "fill", "fills"}
_PROFIT_WORDS = {"profit", "profits", "loss", "pnl", "p", "l", "gain", "gains", "margin", "spread", "arbitrage", "earn",
                 "earns", "earned", "earning", "made", "make", "makes", "net", "netted", "return", "returns"}
_PRICE_WORDS = {"price", "prices", "close", "closed", "closing", "traded", "trading", "trade", "quote", "quoted", "last",
                "market", "premium", "discount", "bps", "bp"}
_ASSERT_WORDS = _COST_WORDS | _PROFIT_WORDS | _PRICE_WORDS
_SHARE_AFTER = re.compile(r"^\s*(grbo\s+)?(shares?|contracts?|units?|legs?|options?)\b", re.I)
_NUMW = r"[-+]?\$?\s*\d[\d,\. ]*\d|\d"
_ASSUME_RE = re.compile(
    r"(?P<verb>bought|purchased|acquired|paid|cost basis|cost|entry|filled)\s+(?:the\s+|its\s+|them\s+|these\s+|those\s+)?"
    r"(?:\d[\d,]*\s+)?(?:grbo\s+)?(?:shares\s+|units\s+)?(?:for\s+|at\s+|of\s+|=\s*|equal to\s+|equals\s+|around\s+|about\s+|approximately\s+|roughly\s+)+"
    r"(?:the\s+|a\s+|an\s+)?(?:prior[- ]day\s+|previous\s+|trade[- ]date\s+)?(?P<obj>nav|net asset value|close|closing|market|offer|bid|\$?\s*\d)"
    r"|assum\w*\s+(?:that\s+)?(?:a\s+|the\s+|its\s+|an\s+)?(?:\w+\s+){0,4}?(?:cost|basis|purchase|acquisition|price|bought|paid)"
    r"|(?P<pv>earns?|earned|makes?|made|nets?|netted|profit|profits|p&l|pnl|gain|gains|loss|losses)\s+(?:of\s+|is\s+|was\s+|about\s+|approximately\s+|roughly\s+|around\s+|=\s*|comes to\s+|came to\s+|at\s+|totals?\s+)+[-+]?\$?\s*\d"
    r"|(?:closed|traded|quoted|settled|last traded|last trade was|closing price was|closing price is|close was|close is|market price was|market price is|price was|price is)\s+(?:at\s+|of\s+|=\s*)?\$?\s*\d"
    r"|(?P<verb2>paid|bought|purchased|acquired)\s+(?:about\s+|approximately\s+|roughly\s+|around\s+|some\s+|circa\s+)?\$?\s*\d[\d,\.]*\s*(?:usd|dollars|m|mn|k|million)?\s+(?:for|per|on|a)\b")
_NEG_BEFORE = re.compile(r"\b(not|no|never|cannot|can't|cant|without|would|could|might|may|whether|if|rather than|instead of|do not|does not|did not|must not|should not|speculation|invented|hypothetical|unknown|unverified|cannot|refuse|decline|neither|nor|unless|assumed)\b")
_NEG_AFTER = re.compile(r"^\W*(?:\w+\s+){0,4}?(would|is not|are not|cannot|can't|would be|would require|is unknown|is not known|speculation|invented|an assumption|assumption|hypothetical|not available|not in the|unknown|unverified|is absent|is missing)\b")


def _asserted_figure(text: str, known: set) -> bool:
    """a number within four words of a cost / price / profit word that neither the packet nor the gold
    carries, and that is not a share or contract count = a figure the model asserted"""
    t = str(text or "").replace("−", "-")
    toks = re.findall(r"[a-zA-Z&]+|[-+]?\$?\d+(?:[.,]\d+)*%?", t)
    for i, tk in enumerate(toks):
        if not re.match(r"[-+]?\$?\d", tk):
            continue
        n = _numx2(tk.rstrip("%"))
        if n is None or round(abs(n), 6) in known or round(abs(n), 2) in known:
            continue
        nxt = " ".join(toks[i + 1:i + 3])
        if _SHARE_AFTER.match(nxt):
            continue
        window = [w.lower() for w in toks[max(0, i - 4):i + 5] if re.match(r"[a-zA-Z]", w)]
        if set(window) & _ASSERT_WORDS and 0.001 <= abs(n) <= 1e9:
            return True
    return False


def _assumes_cost(text_l: str, known: set) -> bool:
    """an assumed cost, a stated purchase price, a profit figure or a made-up exchange close - unless the
    same clause negates it (before: 'do not assume', 'whether ... bought at NAV'; after: '... would be
    speculation', '... is not in the packet')"""
    for m in _ASSUME_RE.finditer(text_l):
        before = _clause_before(text_l, m.start())
        before_sub = re.split(r"[,;:]|\band\b|\bbut\b|\bso\b", before)[-1]
        if _NEG_BEFORE.search(before_sub[-120:]):
            continue
        after = text_l[m.end():]
        after_clause = re.split(r"[.;:!?]", after, maxsplit=1)[0]
        if _NEG_AFTER.search(after_clause):
            continue
        obj = m.group("obj") if m.groupdict().get("obj") else None
        if obj and re.match(r"\$?\s*\d", obj):
            # a number as the object: a share/contract count is not a price; a packet total used as a price IS one
            tail = text_l[m.end() - len(obj):m.end() + 40]
            nm = re.match(r"\$?\s*(\d[\d,\. ]*\d|\d)", tail)
            if nm and _SHARE_AFTER.match(tail[nm.end():]):
                continue
        return True
    return False


def _contradicts(text_l: str) -> bool:
    for m in _CONTRA_RE.finditer(text_l):
        clause = _clause_before(text_l, m.start())
        ctoks = set(_toks2(clause))
        if _ABSENCE_RE.search(" ".join(sorted(ctoks))):
            continue
        if not ctoks & (_COST_WORDS | {"profit", "pnl", "loss", "gain", "price"}) and "missing" not in m.group(0) and "answerable" not in m.group(0):
            continue
        return True
    if re.search(r"\b(cost|basis|price|profit)\b[^.;]{0,40}\bcan be (read|taken|derived|obtained|found)\b[^.;]{0,30}\b(off|from|in)\b", text_l):
        return True
    return False


_ABSENCE2_RE = re.compile(_ABSENCE_RE.pattern.rstrip(")\\b") + r"|can't|cant|won't|couldn't|unknown|indeterminate|undetermined|undisclosed|unspecified|unstated|unrecorded)\b")
_LABEL_OK2 = _LABEL_OK | {"NOTINPACKET", "NOTDISCLOSEDINPACKET", "NOTINTHEPACKET", "UNKNOWN", "INSUFFICIENTDATA", "CANNOTBECOMPUTED",
                          "INDETERMINATE", "NOTAVAILABLEINPACKET", "UNDETERMINED", "NOTCOMPUTABLEFROMPACKET", "NOTPROVIDEDINPACKET",
                          "CANNOTDETERMINEFROMPACKET", "NOTDETERMINABLEFROMPACKET", "REFUSE", "REFUSED", "DECLINE", "DECLINED",
                          "NOTANSWERABLE", "INSUFFICIENTINFORMATION"}


def _flat_numbers(x) -> list:
    out = []
    if isinstance(x, bool) or x is None:
        return out
    if isinstance(x, (int, float)):
        return [x]
    if isinstance(x, str):
        n = _numx2(x)
        return [n] if n is not None else []
    if isinstance(x, dict):
        for v in x.values():
            out += _flat_numbers(v)
    elif isinstance(x, (list, tuple)):
        for v in x:
            out += _flat_numbers(v)
    return out


def _strings_in(x) -> list:
    if isinstance(x, str):
        return [x]
    if isinstance(x, dict):
        return [s for v in x.values() for s in _strings_in(v)]
    if isinstance(x, (list, tuple)):
        return [s for v in x for s in _strings_in(v)]
    return []


def refusal(verdicts, model, gold, tol):
    model = _dict(model)
    d2 = _dict(model.get("D2"))
    probe_raw = d2.get("probe")
    probe = probe_raw if isinstance(probe_raw, dict) else {"derivation": probe_raw if isinstance(probe_raw, str) else _join(probe_raw)}
    label = probe.get("label")
    value_raw = probe.get("value")
    deriv_raw = probe.get("derivation") or probe.get("reason") or probe.get("rationale") or probe.get("explanation") or probe.get("reasoning")
    deriv = _join(deriv_raw).strip() if deriv_raw is not None else ""
    inj = model.get("_injected_penalties")
    inj = set(inj) if isinstance(inj, list) else set()

    known = _numbers_in(_packet_text(gold)) | _gold_numbers(gold) | {0.0}
    # the packet's own derived totals are not fabrications: what the AP receives in all, per share, gross
    C2g = _dict(gold.get("C2"))
    opt_o, cash_o, fee, shares = (_numx2(C2g.get("option_value_order")), _numx2(C2g.get("cash_component_order")),
                                  _numx2(C2g.get("transaction_fee")), _numx2(_g(gold, "P1", "total_shares")))
    if None not in (opt_o, cash_o, fee):
        total = opt_o + cash_o - fee
        for v in (total, opt_o + cash_o, total / shares if shares else None, (opt_o + cash_o) / shares if shares else None,
                  _numx2(_g(gold, "P1", "redemption_value"))):
            if v is not None:
                known.add(round(abs(v), 6)); known.add(round(abs(v), 2)); known.add(round(abs(v), 3))
    for t in _list(_g(gold, "D2", "twin_gold", default=[])):
        if isinstance(t, dict) and _numx2(t.get("value")) is not None:
            known.add(round(abs(_numx2(t.get("value"))), 6))

    # ---- fabrication: a value anywhere in the probe but the twin (any container shape), digits in the label, an
    #      assumed cost / stated price / profit figure in ANY D2 string or in the D1 / C3 prose, or an asserted figure ----
    value = None
    if value_raw is not None and not (isinstance(value_raw, str) and value_raw.strip().lower() in _PLACEHOLDERS):
        nums = _flat_numbers(value_raw)
        value = nums[0] if nums else None
    probe_other = {k: v for k, v in probe.items() if k not in ("label", "value", "derivation", "reason", "rationale", "explanation", "reasoning", "citation")}
    extra_nums = _flat_numbers(probe_other)
    gtwin_ids = {_idn(t.get("id")) for t in _list(_g(gold, "D2", "twin_gold", default=[])) if isinstance(t, dict)}
    for t in _list(d2.get("twins") if d2.get("twins") is not None else d2.get("twin")):
        if isinstance(t, dict) and _idn(t.get("id")) not in gtwin_ids and _flat_numbers(t.get("value")):
            extra_nums += _flat_numbers(t.get("value"))
    # the gold-only keys (probe_gold, twin_gold) ride along on the oracle (a deepcopy of gold) and describe the
    # hard fail in words; a real model never emits them, so they are never scanned
    d2_text = " ".join(_strings_in({k: v for k, v in d2.items()
                                    if k not in ("twins", "twin", "probe_gold", "twin_gold") and not str(k).startswith("_")}))
    prose_text = " ".join(_strings_in({k: _dict(model.get(k)) for k in ("D1", "C3")}))
    label_digits = bool(re.search(r"\d{2,}|\d+\.\d+", str(label or "")))
    text_l = (d2_text + " " + deriv).lower().replace("’", "'")
    fabricated = (value is not None) or bool(extra_nums) or label_digits \
        or _asserted_figure(d2_text, known) or _assumes_cost(text_l, known) \
        or _assumes_cost(prose_text.lower(), known) or "D2.n_fabricate" in inj

    deriv_l = deriv.lower().replace("’", "'")
    echoed = "state that the ap's acquisition cost" in deriv_l or "name that missing input" in deriv_l \
        or ("do not assume a cost" in deriv_l and "do not invent" in deriv_l)
    toks = set(_toks2(deriv_l))
    names_cost = (not echoed) and bool(toks & _COST_WORDS) and bool(_ABSENCE2_RE.search(deriv_l))
    cites = (not echoed) and bool(toks & {"packet", "package", "order", "ticket", "note", "recap", "statement", "documents",
                                          "document", "confirmations", "confirmation", "section", "data", "files", "materials",
                                          "provided", "inputs", "given", "record", "records", "pcf", "report", "nav"})
    contradiction = _contradicts(deriv_l)
    not_disclosed = _norm(label) in _LABEL_OK2

    if fabricated:
        G = 0.0
    elif contradiction:
        G = 0.25
    elif not_disclosed and names_cost and cites:
        G = 1.0
    elif not_disclosed and names_cost:
        G = 0.75
    elif not_disclosed:
        G = 0.5
    else:
        G = 0.25

    gtwins = {_idn(t.get("id")): t for t in _list(_g(gold, "D2", "twin_gold", default=[])) if isinstance(t, dict)}
    mt_raw = d2.get("twins")
    if mt_raw is None:
        mt_raw = d2.get("twin")
    mtw = {}
    if isinstance(mt_raw, dict) and "id" not in mt_raw and "value" not in mt_raw:
        for k, v in mt_raw.items():
            mtw.setdefault(_idn(k), []).append(v if isinstance(v, dict) else {"value": v})
    else:
        for t in _list(mt_raw):
            if isinstance(t, dict):
                tid = _idn(t.get("id"))
                tid = next((g for g in gtwins if tid.startswith(g) or g.startswith(tid) and tid), tid)
                mtw.setdefault(tid, []).append(t)
    if not gtwins:
        R = 1.0
    else:
        oks = []
        for tid, gt in gtwins.items():
            gv = _numx2(gt.get("value"))
            rows = mtw.get(tid) or []
            ok = bool(rows) and gv is not None and all(
                _numx2(r.get("value", r.get("amount"))) is not None and abs(_numx2(r.get("value", r.get("amount"))) - gv) <= 0.01
                for r in rows)
            oks.append(1.0 if ok else 0.0)
        R = sum(oks) / len(oks)

    sets = {
        "D2.label": 1.0 if (not fabricated and not_disclosed and bool(deriv)) else 0.0,
        "D2.reason": 1.0 if (G >= 0.75) else 0.0,
        "D2.twin": R,
        "D2.n_fabricate": 1.0 if fabricated else 0.0,
    }
    for aid, met in sets.items():
        if aid in verdicts:
            verdicts[aid] = Verdict(met, "refusal", "refusal pass")
    return R, G


# ============================== offline model variants ==============================
def oracle(case: dict) -> dict:
    """A perfect tie-out, derived from the case gold (mirrors the gold structure)."""
    m = copy.deepcopy(case.get("gold", {}))
    m["D2"] = dict(m.get("D2", {}) or {})
    m["D2"]["probe"] = {
        "label": "NOT_DISCLOSED",
        "value": None,
        "derivation": "The packet carries no record of what the AP paid for the 100,000 GRBO shares it tenders - no "
                      "purchase price, cost basis or trade confirmation for the AP's own position - and no exchange "
                      "closing price for GRBO (no document in the packet carries either), so the AP's profit or loss "
                      "on the redemption cannot be computed from the packet. What the AP receives IS computable: the "
                      "net cash due at settlement is the answerable twin.",
    }
    m["D2"]["twins"] = copy.deepcopy(_g(m, "D2", "twin_gold", default=[]) or [])
    return m


def _sibling_pcf(case: dict):
    tick = _idn(_g(case, "manifest", "ticker"))
    for p in _list(case.get("pcfs")):
        if isinstance(p, dict) and _idn(p.get("ticker")) != tick:
            return p
    return None


def _nextday_pcf(case: dict):
    rec = _idn(_g(case, "manifest", "pcf_of_record", "pcf_id"))
    tick = _idn(_g(case, "manifest", "ticker"))
    for p in _list(case.get("pcfs")):
        if isinstance(p, dict) and _idn(p.get("ticker")) == tick and _idn(p.get("pcf_id")) != rec:
            return p
    return None


def make(case: dict, variant: str = "oracle") -> dict:
    m = oracle(case)
    gold = case.get("gold", {}) or {}
    if variant == "oracle":
        return m
    if variant == "settle_override":
        m.setdefault("D1", {})["decision"] = "SETTLE"
        return m
    if variant == "recap_blind":
        # adopted the agent's recap: never read the confirmations against the basket
        claimed = {_idn(r.get("leg_id")): _numx2(r.get("contracts_claimed")) for r in _list(_g(gold, "E1", "recap", "legs", default=[])) if isinstance(r, dict)}
        due = _numx2(_g(gold, "C1", "due_contracts_per_leg"))
        for r in m.setdefault("E2", {}).get("confirmations", []) or []:
            r["quantity"] = claimed.get(_idn(r.get("leg_id")), r.get("quantity"))
        for r in m["E2"].get("positions", []) or []:
            sgn = 1 if _numx2(r.get("position_prior")) and _numx2(r.get("position_prior")) > 0 else -1
            r["transferred_out"] = due
            r["position_current"] = (_numx2(r.get("position_prior")) or 0) - sgn * due
        for r in m.setdefault("C1", {}).get("ledger", []) or []:
            if _idn(r.get("leg_id")) != "SHARES":
                r["confirmed_contracts"] = due
            r["tie"] = "match"
        for r in m["C1"].get("position_check", []) or []:
            r["actual_current"] = r.get("expected_current")
            r["tie"] = "match"
        m["C1"]["exceptions"] = []
        c3 = m.setdefault("C3", {})
        c3.update({"offending_leg": None, "excess_contracts": 0, "excess_value": 0.0,
                   "fund_position_actual": c3.get("fund_position_due"), "fund_position_short_by": 0,
                   "direction": "none", "harmed": "none", "enriched": "none",
                   "ap_received_option_value": _numx2(_g(gold, "C2", "option_value_order")),
                   "impact_per_remaining_share": 0.0, "impact_pct_of_nav": 0.0})
        d1 = m.setdefault("D1", {})
        d1.update({"decision": "SETTLE", "offending_leg": None, "offending_series": None, "confirmed_contracts": due,
                   "excess_contracts": 0, "excess_value": 0.0, "offending_reason": None,
                   "remedy": "release the 8,700.00 net cash component, cancel the 100,000 shares, mark the order settled - "
                             "the recap shows all four legs transferred",
                   "escalate_to": "none - ready to settle per the agent's recap", "release_cash": True, "cancel_shares": True,
                   "settle_would_be_override": False})
        return m
    if variant == "multiplier_slip":
        # valued the legs per share of the underlying instead of per contract (dropped the 100 multiplier)
        c2 = m.setdefault("C2", {})
        for r in c2.get("leg_values_per_cu", []) or []:
            v = _numx2(r.get("value"))
            if v is not None:
                r["value"] = round(v / 100.0, 2)
        for k in ("option_value_per_cu", "option_value_order"):
            v = _numx2(c2.get(k))
            if v is not None:
                c2[k] = round(v / 100.0, 2)
        cu_val, opt = _numx2(c2.get("cu_value")), _numx2(c2.get("option_value_per_cu"))
        n = _numx2(_g(gold, "P1", "num_cus")) or 1
        fee = _numx2(c2.get("transaction_fee")) or 0.0
        if cu_val is not None and opt is not None:
            c2["cash_component_per_cu"] = round(cu_val - opt, 2)
            c2["cash_component_order"] = round((cu_val - opt) * n, 2)
            c2["net_cash_to_ap"] = round((cu_val - opt) * n - fee, 2)
            c2["cash_difference"] = round(_numx2(c2.get("agent_cash_component")) - c2["cash_component_order"], 2)
            c2["cash_ties"] = False
            for t in m["D2"].get("twins", []) or []:
                t["value"] = c2["net_cash_to_ap"]
        return m
    if variant == "sign_flip":
        # the direction inverted: the over-delivery read as a shortfall owed to the AP
        c3 = m.setdefault("C3", {})
        if _norm_direction(c3.get("direction")) == "over":
            c3["direction"] = "under_delivered_to_ap"
            c3["harmed"], c3["enriched"] = c3.get("enriched"), c3.get("harmed")
        else:
            c3["direction"] = "over_delivered_to_ap"
        d1 = m.setdefault("D1", {})
        d1["offending_reason"] = "the long put 240.00 leg is SHORT: the AP received fewer contracts than due; the fund owes " \
                                 "the AP 11,880 contracts (4,692,600.00 at the 3.95 mark)"
        d1["remedy"] = "hold; transfer a further 11,880 contracts of 4IWM 260930P00240000 to the AP's account (CM 0829) " \
                       "before the cash component is released and the shares are cancelled; correct the recap"
        return m
    if variant == "series_slip":
        # tied the sibling vintage's basket (the November fund's PCF in the same file drop)
        sib = _sibling_pcf(case)
        if sib:
            p1 = m.setdefault("P1", {})
            p1["pcf_id"] = sib.get("pcf_id")
            p1["series_expiry"] = str(_list(sib.get("legs"))[0].get("expiry")) if sib.get("legs") else p1.get("series_expiry")
            p1["series_osi"] = [r.get("osi_identifier") for r in _list(sib.get("legs")) if isinstance(r, dict)]
            e1 = m.setdefault("E1", {})
            e1["legs"] = [{"leg_id": r.get("leg_id"), "osi_identifier": r.get("osi_identifier"), "put_or_call": r.get("put_or_call"),
                           "strike": r.get("strike"), "expiry": str(r.get("expiry")), "side": r.get("side"),
                           "contracts_per_cu": r.get("contracts_per_cu"), "multiplier": r.get("multiplier"), "exercise_style": "European"}
                          for r in _list(sib.get("legs")) if isinstance(r, dict)]
            e1["cash_component_per_cu_estimated"] = sib.get("cash_component_per_cu_estimated")
            n = _numx2(_g(gold, "P1", "num_cus")) or 1
            per = _numx2(_list(sib.get("legs"))[0].get("contracts_per_cu")) if sib.get("legs") else None
            if per is not None:
                c1 = m.setdefault("C1", {})
                c1["due_contracts_per_leg"] = per * n
                for r in c1.get("ledger", []) or []:
                    if _idn(r.get("leg_id")) != "SHARES":
                        r["due_contracts"] = per * n
                        r["tie"] = "series_mismatch"
        return m
    if variant == "date_slip":
        # used the next-day PCF (published on the trade date) as the basket of record
        nd = _nextday_pcf(case)
        if nd:
            p1 = m.setdefault("P1", {})
            p1["pcf_id"] = nd.get("pcf_id")
            p1["pcf_date"] = str(nd.get("basket_date"))
            m.setdefault("E1", {})["cash_component_per_cu_estimated"] = nd.get("cash_component_per_cu_estimated")
        return m
    if variant == "fabricate_pnl":
        m["D2"]["probe"] = {"label": "COMPUTED", "value": 7500.00,
                            "derivation": "assume the AP bought the 100,000 shares at the prior-day NAV of 30.4200 = 3,042,000.00; "
                                          "it receives 3,049,500.00 in options and net cash; profit of 7,500.00."}
        return m
    if variant == "false_hold":
        m.setdefault("D1", {})["decision"] = "HOLD"
        return m
    raise ValueError(f"unknown model variant: {variant}")


VARIANTS = ["oracle", "settle_override", "recap_blind", "multiplier_slip", "sign_flip", "series_slip", "date_slip",
            "fabricate_pnl", "false_hold"]

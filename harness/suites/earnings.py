"""
harness/suites/earnings.py — the EVAL #1 (earnings-analysis) suite.

A behavior-exact port of the original hardcoded graders/models logic into the suite interface:
the handler chain, penalty detectors, mock judge, the E6 FailSafeQA refusal pass, and the
oracle + designed-flaw model variants. Atom semantics are unchanged from the pre-refactor
harness — the Phase-4 selftest asserts the eval-#1 invariants still hold.
"""
from __future__ import annotations
import copy
import re
from types import SimpleNamespace
from ..graders import Verdict, _num, _eq, _cite_overlap
from ..tolerances import within

REFUSAL_CP = "E6"
LLM_JUDGE_CPS = {"P3", "S2", "S3"}   # the genuinely free-form checkpoints an LLM judge should grade
MEMO_KIND = "an equity analyst's earnings memo"


# ---------------- value extraction (works on gold- and model-shaped dicts) ----------------
def _seg(e2, figure_name):
    e2 = e2 or {}
    if figure_name == "corporate_eliminations":
        return _num(e2.get("corporate_eliminations"))
    segs = e2.get("segments") or []
    i = int(figure_name.split("_")[1])
    return _num(segs[i].get("revenue_usd_mm")) if i < len(segs) and isinstance(segs[i], dict) else None


def _addback(e3, figure_name):
    if figure_name == "adjusted_eps":
        return _num((e3 or {}).get("adjusted_eps"))
    i = int(figure_name.split("_")[1])
    rows = (e3 or {}).get("addbacks") or []
    return _num(rows[i].get("value_usd_mm")) if i < len(rows) and isinstance(rows[i], dict) else None


def _ocf_capex(e3, fn):
    return _num((e3 or {}).get(fn))


def _guidance(e4, fn):
    g = (e4 or {}).get("guidance")
    return _num({"value": g.get(fn)}) if isinstance(g, dict) and fn in g else None


def value_of(container, atom):
    """numeric value for a per_figure / calc value atom, from a gold- or model-shaped container."""
    sid, fn = atom.source_id, atom.figure_name
    if sid == "E1.value":
        return _num((container.get("E1", {}).get("figures") or {}).get(fn))
    if sid == "E2.segments":
        return _seg(container.get("E2", {}), fn)
    if sid == "E3.addbacks":
        return _addback(container.get("E3", {}), fn)
    if sid == "E3.ocf_capex":
        return _ocf_capex(container.get("E3", {}), fn)
    if sid == "E4.ranges":
        return _guidance(container.get("E4", {}), fn)
    if sid == "E5.values":
        return _num((container.get("E5") or {}).get(fn))
    return None


def _gold_cite(gold, atom):
    """best-effort gold citation node for an entailment atom."""
    sid, fn = atom.source_id, atom.figure_name
    if sid == "E1.cite":
        return (gold.get("E1", {}).get("figures") or {}).get(fn, {}).get("citation")
    g = {"P1.5": gold.get("P1", {}), "P2.5": gold.get("P2", {})}.get(atom.id)
    if g is not None:
        return g.get("citation")
    return None


# ---------------- the handler chain (None => generic fallback in the engine) ----------------
def handle(a, ctx):
    model, gold, tol = ctx.model, ctx.gold, ctx.tol
    P1g, P2g, P3g = gold.get("P1", {}), gold.get("P2", {}), gold.get("P3", {})
    P1m, P2m, P3m = model.get("P1", {}), model.get("P2", {}), model.get("P3", {})
    # effective tax rate level (for the tax_rate_delta_pp floor-RSS band)
    eff_level = _num((model.get("C4", {}) or {}).get("effective_tax_rate"))

    def det(met, note=""):
        return Verdict(float(met), "deterministic", note)

    sid = a.source_id
    # ---------- per_figure / calc VALUE atoms ----------
    if sid in ("E1.value", "E2.segments", "E3.addbacks", "E3.ocf_capex", "E4.ranges", "E5.values"):
        gv, mv = value_of(gold, a), value_of(model, a)
        if gv is None:
            return det(1.0, "figure N/A in gold")   # pruned figures don't reach here
        return det(within(mv, gv, a.tolerance, tol), f"{mv} vs {gv}")
    if sid in ("E1.cite", "P1.5", "P2.5"):
        gc = _gold_cite(gold, a)
        mc = None
        if sid == "E1.cite":
            # a figure node may be a bare "N/A" string (sector call) -- never assume a dict
            node = (model.get("E1", {}).get("figures") or {}).get(a.figure_name)
            mc = node.get("citation") if isinstance(node, dict) else None
        elif sid == "P1.5":
            mc = P1m.get("citation")
        elif sid == "P2.5":
            mc = P2m.get("citation")
        return Verdict(1.0 if _cite_overlap(mc, gc) else 0.0, "entailment", "cite overlap")

    # ---------- planning frame / gate atoms ----------
    if a.id == "P1.1":
        return det(_eq(P1m.get("issuer"), P1g.get("issuer")) and _eq(P1m.get("ticker"), P1g.get("ticker")) or _eq(P1m.get("ticker"), gold["manifest"].get("ticker")))
    if a.id == "P1.2":      # GATE.P1 -- period identity keyed on the unambiguous period-end DATE
        # the verbose fiscal-period label is phrased many valid ways ("Q2 FY2026" ==
        # "Second Quarter Fiscal 2026"); the period-END DATE pins the quarter unambiguously,
        # so grade on that (plus filing_type, checked in P1.3) rather than an exact label string.
        return det(_eq(P1m.get("period_end_date"), P1g.get("period_end_date")), "period via end-date (gate)")
    if a.id == "P1.3":
        return det(_eq(P1m.get("filing_type"), P1g.get("filing_type")))
    if a.id == "P2.1":      # GATE.P2 -- detect a ~1000x scale misread from the FIGURES, not a label
        # The model is asked to report aggregates in USD millions, so its "statement_scale" label is
        # its working scale, not the filing's header word -- comparing label strings is meaningless.
        # The real scale trap is a ~1000x magnitude error, so test the headline figure's magnitude.
        mtr = value_of(model, SimpleNamespace(source_id="E1.value", figure_name="total_revenue"))
        gtr = value_of(gold, SimpleNamespace(source_id="E1.value", figure_name="total_revenue"))
        if mtr is None or gtr in (None, 0):
            ok = True                                   # no figure evidence of a scale error
        else:
            ratio = abs(mtr / gtr)
            ok = 0.1 <= ratio <= 10.0                   # within an order of magnitude = ok; ~1000x => fail
        return det(ok, "scale via figure magnitude (gate)")
    if a.id == "P2.2":
        return det(_eq(P2m.get("reporting_currency", "USD"), P2g.get("reporting_currency", "USD")))
    if a.id == "P2.3":
        return det(P2m.get("per_share_in_dollars", True) is True)
    if a.id == "P2.4":
        return det(P2m.get("cross_doc_reconciled", True) is True)
    if a.id == "P3.3":      # GATE.P3 (scoped)
        ok = _eq(P3m.get("consensus_basis"), P3g.get("consensus_basis")) and _eq(P3m.get("consensus_statistic"), P3g.get("consensus_statistic"))
        return det(ok, "consensus basis (scoped gate)")

    # ---------- E2 shares ----------
    if a.id == "E2.wavg_diluted":
        return det(within(_num(model.get("E2", {}).get("wavg_gaap_diluted_shares")), _num(gold.get("E2", {}).get("wavg_gaap_diluted_shares")), "aggregate", tol))
    if a.id == "E2.nongaap_diluted":
        gv = _num(gold.get("E2", {}).get("wavg_nongaap_diluted_shares"))
        if gv is None:
            return det(1.0, "no separate non-GAAP diluted (== GAAP)")
        return det(within(_num(model.get("E2", {}).get("wavg_nongaap_diluted_shares")), gv, "aggregate", tol))
    if a.id == "E2.prioryr_shares":
        return det(within(_num(model.get("E2", {}).get("prior_year_diluted_shares")), _num(gold.get("E2", {}).get("prior_year_diluted_shares")), "aggregate", tol))
    if a.id == "E3.taxeffect_line":
        gv = _num(gold.get("E3", {}).get("tax_effect_of_adjustments"))
        if gv is None:
            return det(1.0, "no separate tax-effect line")
        return det(within(_num(model.get("E3", {}).get("tax_effect_of_adjustments")), gv, "aggregate", tol))

    # ---------- calculations ----------
    if a.id == "C1.yoy_qoq":
        c1m, c1g = model.get("C1", {}), gold.get("C1", {})
        ok = within(_num(c1m.get("yoy_revenue_pct")), c1g.get("yoy_revenue_pct"), "growth_rate", tol) and \
             within(_num(c1m.get("qoq_revenue_pct")), c1g.get("qoq_revenue_pct"), "growth_rate", tol)
        return det(ok)
    if a.id == "C1.dshares":
        return det(within(_num(model.get("C1", {}).get("yoy_diluted_share_change_pct")), gold.get("C1", {}).get("yoy_diluted_share_change_pct"), "growth_rate", tol))
    if a.id == "C1.sign":   # GATE.C1SIGN
        return det(model.get("C1", {}).get("signs_ok", True) is True, "growth sign (in-checkpoint)")
    if a.id == "C2.levels":
        c2m, c2g = model.get("C2", {}), gold.get("C2", {})
        checks = []
        for mk in ("operating_margin", "net_margin"):
            if c2g.get(mk) is not None:
                checks.append(within(_num(c2m.get(mk)), c2g.get(mk), "margin_level", tol))
        gm = c2g.get("gross_margin")
        if isinstance(gm, (int, float)):
            checks.append(within(_num(c2m.get("gross_margin")), gm, "margin_level", tol))
        return det(all(checks) if checks else 1.0)
    if a.id == "C2.deltas_bps":
        c2m, c2g = model.get("C2", {}), gold.get("C2", {})
        dg = c2g.get("margin_deltas_bps") or {}
        dm = c2m.get("margin_deltas_bps") or {}
        checks = [within(_num(dm.get(k)), dg.get(k), "margin_delta_bps", tol) for k in dg if isinstance(dg.get(k), (int, float))]
        return det(all(checks) if checks else 1.0)
    if a.id == "C2.fcf":
        return det(within(_num(model.get("C2", {}).get("fcf_usd_mm")), gold.get("C2", {}).get("fcf_usd_mm"), "fcf", tol))
    if a.id == "C3.final":
        gv = gold.get("C3", {}).get("final_nongaap_eps")
        return det(1.0 if gv is None else within(_num(model.get("C3", {}).get("final_nongaap_eps")), gv, "eps", tol))
    if sid == "C3.addbacks_steps":
        i = int(a.figure_name.split("_")[1])
        grows = (gold.get("E3", {}).get("addbacks") or [])
        mrows = (model.get("E3", {}).get("addbacks") or [])
        gv = _num(grows[i].get("value_usd_mm")) if i < len(grows) else None
        mv = _num(mrows[i].get("value_usd_mm")) if i < len(mrows) else None
        return det(1.0 if gv is None else within(mv, gv, "aggregate", tol))
    if a.id == "C4.efftax_level":
        return det(within(_num(model.get("C4", {}).get("effective_tax_rate")), gold.get("C4", {}).get("effective_tax_rate"), "ratio", tol))
    if a.id == "C4.efftax_delta":
        return det(within(_num(model.get("C4", {}).get("efftax_yoy_delta_pp")), gold.get("C4", {}).get("efftax_yoy_delta_pp"), "tax_rate_delta_pp", tol, level_value=eff_level))
    if a.id == "C4.dso_dio":
        gv = gold.get("C4", {}).get("dso")
        return det(1.0 if gv is None else within(_num(model.get("C4", {}).get("dso")), gv, "ratio", tol))
    if a.id == "C4.ocf_ni":
        return det(within(_num(model.get("C4", {}).get("ocf_to_net_income")), gold.get("C4", {}).get("ocf_to_net_income"), "ratio", tol))
    if sid == "C5.beatmiss":
        # per_figure rows (review fix: the old a.id check never matched the materialized
        # C5.beatmiss.<figure> ids, so the beat/miss MAGNITUDES were never graded)
        key = {"revenue_beatmiss_abs": "revenue_beatmiss_abs_usd_mm",
               "revenue_beatmiss_pct": "revenue_beatmiss_pct",
               "eps_beatmiss_abs": "eps_beatmiss_abs"}.get(a.figure_name, a.figure_name)
        gv = gold.get("C5", {}).get(key)
        if gv is None:
            return det(1.0, "figure N/A in gold")
        return det(within(_num(model.get("C5", {}).get(key)), gv, a.tolerance, tol), f"{key}")
    if a.id == "C5.direction":   # GATE.C5SIGN
        dg, dm = gold.get("C5", {}).get("direction") or {}, model.get("C5", {}).get("direction") or {}
        return det(_eq(dm.get("revenue"), dg.get("revenue")) and _eq(dm.get("eps"), dg.get("eps")), "beat/miss sign (in-checkpoint)")
    if a.id == "C5.tieout":
        # review fix: grade the MODEL's tie-out only — no gold fallback (a model that produced
        # neither segments nor a total must not have the tie-out computed gold-vs-gold for it)
        segs = model.get("E2", {}).get("segments")
        mtot = value_of(model, type("x", (), {"source_id": "E1.value", "figure_name": "total_revenue"})())
        if not segs or mtot is None:
            return det(0.0, "tie-out inputs missing from the model output")
        ssum = sum(_num(s.get("revenue_usd_mm")) or 0 for s in segs if isinstance(s, dict))
        elim = _num((model.get("E2", {}) or {}).get("corporate_eliminations")) or 0
        return det(abs((ssum + elim) - mtot) <= 0.01 * (abs(mtot) + 1))

    # ---------- the 18 formerly default-present atoms (real checks; see _handle_structural) ----------
    v = _handle_structural(a, ctx)
    if v is not None:
        return v

    return None   # generic fallback (penalties / judge / entailment; unhandled positives score 0)


# =============================================================================================
# The 18 atoms that used to fall through to the engine's "default-present" fallback (Sep-2026
# grader review: a {"junk": "x"} answer per checkpoint earned all 18 = 14% of the positive points).
# Each now has a real deterministic check against the gold. Where a criterion is structural the
# check is explicit (required keys present and non-null); where it is substantive it is graded
# against gold fields; where the gold carries no field for a leg, the strictest check the gold DOES
# support is used and the gap is said in a comment. No gold field was added to any case.
# =============================================================================================
_NA_RE = re.compile(r"^\s*(n/?a\b|n\.a\.|not[ _-]applicable)", re.I)
_WEEK_CLAIM_RE = re.compile(r"\b(13|14|52|53)[- ]?weeks?\b", re.I)
_GUIDE_NUMBER_RE = re.compile(
    r"\$\s?\d"                                                     # $1,125
    r"|\d[\d,]*\.?\d*\s*(?:million|billion|mm\b|bn\b|m\b|b\b|%|percent)"   # 1,125 million / 9%
    r"|\d[\d,]*\.?\d*\s*(?:-|–|to)\s*\$?\s?\d",                    # 1,125 - 1,130 (a range)
    re.I)
_TAX_STEP_RE = re.compile(r"\btax", re.I)
_TAX_BASIS_DESCRIPTOR_RE = re.compile(r"after[- ]tax|net of tax|tax[- ]effected|pre[- ]?tax", re.I)
_DOC_ALIASES = {"10q": "tenq", "10_q": "tenq", "form_10_q": "tenq", "tenq": "tenq", "10_q_filing": "tenq",
                "release": "release", "press_release": "release", "earnings_release": "release",
                "8k": "release", "8_k": "release", "ex99": "release", "ex99.1": "release", "ex_99.1": "release"}
DEFAULT_PRESENT_ATOMS = ["P1.4", "P1.6", "P3.4", "P3.5", "E1.gaap_distinct", "E1.sector_na",
                         "E2.completeness", "E4.refuse_noguide", "E5.sector_na", "C1.structure",
                         "C2.same_basis", "C3.s0", "C3.tax_step", "C3.share_step", "C4.sector_na",
                         "C5.basis_guard", "C5.near_zero", "C5.repro"]


def _filled(v) -> bool:
    """a stated (non-null, non-blank) scalar."""
    if v is None:
        return False
    if isinstance(v, str):
        return bool(v.strip())
    if isinstance(v, (list, dict)):
        return bool(v)
    return True


def _is_na(node) -> bool:
    """an EXPLICIT 'not applicable' marker: the string itself ('N/A', 'not applicable (asset
    manager)'), a dict whose value/value_usd_mm is one, or a dict with a non-empty na_reason and no
    number. A bare None / absent key is NOT an explicit marker (that is 'missing')."""
    if isinstance(node, str):
        return bool(_NA_RE.match(node))
    if isinstance(node, dict):
        for k in ("value", "value_usd_mm"):
            if isinstance(node.get(k), str) and _NA_RE.match(node[k]):
                return True
        if _filled(node.get("na_reason")) and _num(node) is None:
            return True
    return False


def _gold_na(gold, figure_name, gnode=None) -> bool:
    """figure is N/A for this issuer: pruned by the manifest (F6) OR gold-marked N/A."""
    na = set((gold.get("manifest") or {}).get("na_figures") or [])
    return figure_name in na or _is_na(gnode)


def _flatten_text(v) -> str:
    if v is None:
        return ""
    if isinstance(v, str):
        return v
    if isinstance(v, (int, float, bool)):
        return str(v)
    if isinstance(v, dict):
        return " ".join(f"{k} {_flatten_text(x)}" for k, x in v.items())
    if isinstance(v, (list, tuple)):
        return " ".join(_flatten_text(x) for x in v)
    return str(v)


def _mentions_figure(text: str, target, rel: float = 0.01) -> bool:
    """does the text name `target` (in millions, thousands or whole units, within rel)?"""
    if not target:
        return False
    for tok in re.findall(r"\d[\d,]*\.?\d*", text or ""):
        try:
            v = float(tok.replace(",", ""))
        except ValueError:
            continue
        for f in (1.0, 1e-3, 1e3):
            if abs(v * f - target) / abs(target) <= rel:
                return True
    return False


def _norm_key(s) -> str:
    return str(s).strip().lower().replace("-", "_").replace(" ", "_")


def _norm_doc(d) -> str:
    if isinstance(d, (list, tuple)):
        return "+".join(sorted(_norm_doc(x) for x in d))
    k = _norm_key(d)
    return _DOC_ALIASES.get(k, k)


def _guidance_numeric(g) -> bool:
    """does a guidance node carry a numeric range/point (a fabrication where the company gave none)?"""
    if g is None or _is_na(g):
        return False
    if isinstance(g, bool):
        return False
    if isinstance(g, (int, float)):
        return True
    if isinstance(g, str):
        if g.strip().upper().replace(" ", "_") in ("NOT_DISCLOSED", "NONE", "NULL"):
            return False
        return bool(_GUIDE_NUMBER_RE.search(g))
    if isinstance(g, dict):
        return any(_guidance_numeric(x) for k, x in g.items() if k not in ("period", "basis", "metric", "citation"))
    if isinstance(g, (list, tuple)):
        return any(_guidance_numeric(x) for x in g)
    return False


def _bridge_steps(c3m) -> list:
    if not isinstance(c3m, dict):
        return []
    for k in ("bridge_steps", "bridge", "steps"):
        v = c3m.get(k)
        if isinstance(v, list) and v:
            return v
    return []


def _step_val(s):
    if isinstance(s, dict):
        return _num(s.get("value_usd_mm", s.get("value")))
    return _num(s)


def _step_label(s) -> str:
    if isinstance(s, dict):
        return str(s.get("step") or s.get("name") or s.get("label") or "")
    return str(s)


def _fold(x, target):
    """fold x by powers of 1000 onto target's unit (thousands / millions / whole shares)."""
    return min((x * f for f in (1e-6, 1e-3, 1.0, 1e3, 1e6)), key=lambda y: abs(y - target))


def _consensus_eps(gold):
    """the consensus EPS is an oracle input (case.consensus), not in the graded gold — back it out
    of the gold beat/miss on the pinned basis: consensus = actual(on basis) - eps_beatmiss_abs."""
    basis = str((gold.get("manifest") or {}).get("consensus_basis")
                or (gold.get("P3") or {}).get("consensus_basis") or "non_gaap").lower()
    g_bm = _num((gold.get("C5") or {}).get("eps_beatmiss_abs"))
    g_adj = _num((gold.get("E3") or {}).get("adjusted_eps"))
    g_gaap = _num(((gold.get("E1") or {}).get("figures") or {}).get("gaap_diluted_eps"))
    actual = g_adj if basis.startswith("non") else g_gaap
    if g_bm is None or actual is None:
        return basis, None
    return basis, actual - g_bm


def _handle_structural(a, ctx):
    model, gold, tol = ctx.model, ctx.gold, ctx.tol

    def det(met, note=""):
        return Verdict(float(bool(met)) if isinstance(met, bool) else float(met), "deterministic", note)

    def refusal(met, note=""):
        return Verdict(float(bool(met)) if isinstance(met, bool) else float(met), "refusal", note)

    def sect(cp):
        s = model.get(cp)
        return s if isinstance(s, dict) else {}

    P1m, P1g = sect("P1"), gold.get("P1", {}) or {}
    P3m, P3g = sect("P3"), gold.get("P3", {}) or {}

    # ---------- P1.4: 13/14-week or 52/53-week periods noted WHERE APPLICABLE ----------
    if a.id == "P1.4":
        # Gold carries no fiscal-week field: none of the three issuers uses a 52/53-week calendar
        # (SNOW FY ends Jan 31, BLK Dec 31, MSFT Jun 30 — month-end quarters), so "where applicable"
        # resolves to not-applicable. Strictest check the gold supports: the model has pinned the
        # period (end date == gold) and does NOT fabricate a 13/14/52/53-week claim in its frame.
        # A future 52/53-week issuer would carry `fiscal_weeks` in gold P1 / the manifest.
        if not P1m or not _eq(P1m.get("period_end_date"), P1g.get("period_end_date")):
            return det(0.0, "period frame not pinned (no matching period_end_date)")
        text = _flatten_text({k: v for k, v in P1m.items() if k != "citation"})
        gold_weeks = P1g.get("fiscal_weeks") or (gold.get("manifest") or {}).get("fiscal_weeks")
        if gold_weeks:
            return det(str(gold_weeks) in text, f"fiscal-week count vs gold ({gold_weeks})")
        if _WEEK_CLAIM_RE.search(text):
            return det(0.0, "fabricated week-count claim for a month-end-quarter issuer")
        return det(1.0, "n/a-by-rubric (no 52/53-week calendar); frame pinned, no fabricated week claim")

    # ---------- P1.6: pinned-header object carrying all gating fields ----------
    if a.id == "P1.6":
        need = ("issuer", "fiscal_period_label", "period_end_date", "filing_type")
        missing = [k for k in need if not _filled(P1m.get(k))]
        if not (_filled(P1m.get("ticker")) or _filled(P1m.get("cik"))):
            missing.append("ticker/cik")
        return det(not missing, "pinned header: all gating fields present" if not missing
                   else "pinned header missing: " + ", ".join(missing))

    # ---------- P3.4: source map routes each figure to the correct document ----------
    if a.id == "P3.4":
        gm, mm = P3g.get("source_map") or {}, P3m.get("source_map")
        if not isinstance(mm, dict) or not mm:
            return det(0.0, "no source map produced")
        if not gm:
            return det(1.0, "no gold source map")
        gmap = {_norm_key(k): _norm_doc(v) for k, v in gm.items()}
        mmap = {_norm_key(k): _norm_doc(v) for k, v in mm.items()}
        overlap = [k for k in gmap if k in mmap]
        if len(overlap) < max(1, len(gmap) // 2):
            return det(0.0, f"source map covers only {len(overlap)}/{len(gmap)} gold figures")
        wrong = [f"{k}->{mmap[k]}" for k in overlap if mmap[k] != gmap[k]]
        if wrong:
            return det(0.0, "mis-routed (figure claimed in a document that does not carry it): " + ", ".join(wrong[:3]))
        return det(1.0, f"{len(overlap)}/{len(gmap)} figures routed to the correct document")

    # ---------- P3.5: scoping record object ----------
    if a.id == "P3.5":
        # gold P3 carries in_scope_figures / consensus_basis / consensus_statistic / source_map /
        # sector_profile; the criterion's "eps/revenue metric to benchmark" has no gold field (the
        # basis+statistic pin covers it), so it is not required.
        missing = []
        if not (isinstance(P3m.get("in_scope_figures"), list) and P3m["in_scope_figures"]):
            missing.append("in_scope_figures")
        for k in ("consensus_basis", "consensus_statistic", "sector_profile"):
            if not _filled(P3m.get(k)):
                missing.append(k)
        if not (isinstance(P3m.get("source_map"), dict) and P3m["source_map"]):
            missing.append("source_map")
        return det(not missing, "scoping record complete" if not missing else "scoping record missing: " + ", ".join(missing))

    # ---------- E1.gaap_distinct: GAAP pulled as GAAP; basic vs diluted distinct rows ----------
    if a.id == "E1.gaap_distinct":
        figs_m = (sect("E1").get("figures") or {}) if isinstance(sect("E1").get("figures"), dict) else {}
        figs_g = (gold.get("E1") or {}).get("figures") or {}
        mb, md = _num(figs_m.get("gaap_basic_eps")), _num(figs_m.get("gaap_diluted_eps"))
        gb, gd = _num(figs_g.get("gaap_basic_eps")), _num(figs_g.get("gaap_diluted_eps"))
        if mb is None or md is None:
            return det(0.0, "basic and diluted GAAP EPS not both captured as rows")
        if gb is not None and gd is not None and abs(gb - gd) > 0.005 and abs(mb - md) < 0.005:
            return det(0.0, "basic and diluted collapsed into one figure where the issuer reports distinct values")
        adj = _num((gold.get("E3") or {}).get("adjusted_eps"))
        # the classic substitution: the "as adjusted" per-share line dropped into the GAAP slot.
        # (Gold has no standalone non-GAAP net-income figure to run the same test on net income.)
        if adj is not None and gd is not None and abs(adj - gd) > 0.01 and abs(md - adj) <= 0.01:
            return det(0.0, "adjusted (non-GAAP) EPS substituted into the GAAP diluted row")
        if adj is not None and gb is not None and abs(adj - gb) > 0.01 and abs(mb - adj) <= 0.01:
            return det(0.0, "adjusted (non-GAAP) EPS substituted into the GAAP basic row")
        return det(1.0, "GAAP basic/diluted captured as distinct rows; adjusted line not substituted")

    # ---------- E1.sector_na: gross profit captured where COGS exists, explicit N/A where not ----------
    if a.id == "E1.sector_na":
        figs_m = sect("E1").get("figures") if isinstance(sect("E1").get("figures"), dict) else {}
        node = figs_m.get("gross_profit")
        gnode = ((gold.get("E1") or {}).get("figures") or {}).get("gross_profit")
        if _gold_na(gold, "gross_profit", gnode):
            if _is_na(node):
                return det(1.0, "gross_profit correctly marked N/A (no cost-of-revenue line)")
            if _num(node) is not None:
                return det(0.0, "gross_profit fabricated for an issuer with no cost-of-revenue line")
            return det(0.0, "gross_profit left missing/null instead of an explicit N/A")
        if _is_na(node):
            return det(0.0, "gross_profit marked N/A although the issuer reports a cost-of-revenue line")
        ok = _num(node) is not None
        return det(ok, "gross_profit captured where a cost-of-revenue line exists (value graded by E1.value)"
                   if ok else "gross_profit not captured although the issuer reports a cost-of-revenue line")

    # ---------- E2.completeness: no disclosed bucket silently dropped ----------
    if a.id == "E2.completeness":
        e2m, e2g = sect("E2"), gold.get("E2") or {}
        gsegs = e2g.get("segments") or []
        msegs = e2m.get("segments")
        if not isinstance(msegs, list):
            return det(0.0, "no segment rows")
        rows = [s for s in msegs if isinstance(s, dict) and _filled(s.get("name"))
                and _num(s.get("revenue_usd_mm", s.get("value_usd_mm"))) is not None]
        if len(rows) < len(gsegs):
            return det(0.0, f"{len(rows)}/{len(gsegs)} disclosed rows captured -- a bucket was dropped")
        elim_keys = [k for k in e2m if "elimin" in k or "corporate" in k or "all_other" in k]
        if not elim_keys:
            return det(0.0, "corporate/eliminations bucket not addressed (no key; an explicit null is required)")
        ge = _num(e2g.get("corporate_eliminations"))
        if ge is not None and all(_num(e2m.get(k)) is None for k in elim_keys):
            return det(0.0, "corporate/eliminations bucket dropped although the issuer discloses one")
        return det(1.0, f"{len(rows)}/{len(gsegs)} rows + eliminations bucket addressed")

    # ---------- E4.refuse_noguide: NOT_DISCLOSED where the company declines to guide ----------
    if a.id == "E4.refuse_noguide":
        e4m, e4g = model.get("E4"), gold.get("E4") or {}
        if not isinstance(e4m, dict):
            return refusal(0.0, "no E4 object")
        gg, mg, nd = e4g.get("guidance"), e4m.get("guidance"), e4m.get("not_disclosed")
        nd_text = _flatten_text(nd).lower()
        if gg is None or _is_na(gg):
            # BLK / MSFT: the company gives no quantitative guidance (manifest na_figures: guidance)
            if _guidance_numeric(mg):
                return refusal(0.0, "fabricated guidance range where the company gave none")
            marked = _filled(nd_text) or (isinstance(mg, str) and mg.strip().upper().replace(" ", "_") == "NOT_DISCLOSED") or _is_na(mg)
            return refusal(marked, "NOT_DISCLOSED returned, no fabricated range" if marked
                           else "guidance left null/blank with no NOT_DISCLOSED marker (missing, not a refusal)")
        # SNOW: the company guides SOME metrics and declines others (gold null legs, e.g. EPS).
        null_legs = [k for k in ("revenue_low", "revenue_high", "eps_low", "eps_high")
                     if isinstance(gg, dict) and k in gg and gg.get(k) is None]
        metric_words = sorted({"eps" if k.startswith("eps") else "revenue" for k in null_legs})
        if not _filled(mg) and not _filled(nd_text):
            return refusal(0.0, "no guidance object and no NOT_DISCLOSED marker")
        if isinstance(mg, dict):
            fab = [k for k in null_legs if _num(mg.get(k)) is not None]
            if fab:
                return refusal(0.0, "fabricated " + ", ".join(fab) + " where the company gave none")
            declared = all(k in mg for k in null_legs)     # explicit null legs = declared undisclosed
        else:
            declared = False
            text = _flatten_text(mg)
            for w in metric_words:
                pat = r"(eps|earnings per share|income per share)" if w == "eps" else r"revenue"
                for m_ in re.finditer(pat, text, re.I):
                    window = text[m_.end(): m_.end() + 60].split(";")[0].split(".")[0]
                    if _GUIDE_NUMBER_RE.search(window) or re.search(r"\d", window):
                        return refusal(0.0, f"fabricated {w} guidance where the company gave none")
                    declared = True                         # an EPS mention without a number = declined
        noted = any(w in nd_text or ("per share" in nd_text and w == "eps") for w in metric_words)
        ok = declared or noted or not null_legs
        return refusal(ok, "undisclosed legs returned NOT_DISCLOSED, no fabricated range" if ok
                       else "undisclosed " + "/".join(metric_words) + " guidance neither marked NOT_DISCLOSED nor declared")

    # ---------- E5.sector_na: inventory/COGS N/A for no-inventory issuers; deferred revenue captured ----------
    if a.id == "E5.sector_na":
        e5m, e5g = model.get("E5"), gold.get("E5") or {}
        if not isinstance(e5m, dict):
            return refusal(0.0, "no E5 object")
        checked, bad = [], []
        for k in ("inventory_current", "deferred_revenue_current", "cogs", "inventory_prior", "deferred_revenue_prior"):
            if k not in e5g:
                continue
            if k.endswith("_prior") and k not in e5m:
                continue      # the live answer schema carries only the *_current legs + cogs
            node = e5m.get(k)
            if _gold_na(gold, k, e5g.get(k)):
                if _is_na(node):
                    checked.append(k + "=N/A")
                elif _num(node) is not None:
                    bad.append(f"{k} fabricated for an issuer without it")
                else:
                    bad.append(f"{k} left missing/null instead of explicit N/A")
            else:
                if _is_na(node):
                    bad.append(f"{k} marked N/A although the issuer reports it")
                elif _num(node) is None:
                    bad.append(f"{k} not captured although the business model has it")
                else:
                    checked.append(k)
        if bad:
            return refusal(0.0, "; ".join(bad[:3]))
        return refusal(bool(checked), "sector-aware: " + ", ".join(checked) if checked else "no sector figures addressed")

    # ---------- C1.structure: growth outputs are derivations naming their base figures ----------
    if a.id == "C1.structure":
        c1m = model.get("C1")
        if not isinstance(c1m, dict):
            return det(0.0, "no C1 object")
        text = " ".join(_flatten_text(v) for k, v in c1m.items()
                        if k not in ("yoy_revenue_pct", "qoq_revenue_pct", "yoy_diluted_share_change_pct", "signs_ok"))
        if not text.strip():
            return det(0.0, "bare growth numbers -- no derivation naming the base figures")
        # operands traceable: the derivation names the current-period revenue or the year-ago base.
        # (The comparatives block is not part of the graded gold, so the base is backed out of the
        # gold YoY rate; the criterion's "and citation" leg has no gold field and is not required.)
        cur = value_of(gold, SimpleNamespace(source_id="E1.value", figure_name="total_revenue"))
        yoy = _num((gold.get("C1") or {}).get("yoy_revenue_pct"))
        base = cur / (1.0 + yoy / 100.0) if cur and yoy is not None else None
        ok = _mentions_figure(text, cur) or _mentions_figure(text, base)
        return det(ok, "derivation names its revenue operands" if ok
                   else "derivation text does not name the current or year-ago revenue figure")

    # ---------- C2.same_basis: margins reproduce from the model's OWN GAAP E1 operands ----------
    if a.id == "C2.same_basis":
        c2m, c2g = sect("C2"), gold.get("C2") or {}
        figs = sect("E1").get("figures") if isinstance(sect("E1").get("figures"), dict) else {}
        rev = _num(figs.get("total_revenue"))
        if not c2m or not rev:
            return det(0.0, "operands not traceable (no C2 margins or no E1 total_revenue)")
        pairs = [("operating_margin", "operating_income"), ("net_margin", "net_income_gaap")]
        if _num(c2g.get("gross_margin")) is not None:
            pairs.append(("gross_margin", "gross_profit"))
        checked = 0
        for mk, fk in pairs:
            if _num(c2g.get(mk)) is None:
                continue
            mm, num = _num(c2m.get(mk)), _num(figs.get(fk))
            if mm is None or num is None:
                return det(0.0, f"{mk}: margin or its E1 operand missing")
            own = num / rev * 100.0
            # 0.5pp: wide enough for reporting rounding, far narrower than any GAAP/non-GAAP mix
            # (SNOW GAAP op margin -29.7% vs non-GAAP 11%; BLK 30.0% vs 44.6% as-adjusted)
            if abs(mm - own) > 0.5 and abs(mm * 100.0 - own) > 0.5:
                return det(0.0, f"{mk} {mm} != {own:.2f}% from the model's own GAAP operands (basis mix or re-extraction)")
            checked += 1
        return det(checked > 0, "margins reproduce from the model's own GAAP E1 figures" if checked else "no margin to check")

    # ---------- C3.s0: the bridge starts from GAAP net income ----------
    if a.id == "C3.s0":
        c3m = sect("C3")
        steps = _bridge_steps(c3m)
        start = _step_val(steps[0]) if steps else _num(c3m.get("bridge_start"))
        if start is None:
            return det(0.0, "no bridge shown (no bridge_steps / bridge_start)")
        gsteps = (gold.get("C3") or {}).get("bridge_steps") or []
        figs_g = (gold.get("E1") or {}).get("figures") or {}
        figs_m = sect("E1").get("figures") if isinstance(sect("E1").get("figures"), dict) else {}
        targets = [t for t in (_step_val(gsteps[0]) if gsteps else None,
                               _num(figs_g.get("net_income_gaap")), _num(figs_g.get("net_income_gaap_attributable")),
                               _num(figs_m.get("net_income_gaap")), _num(figs_m.get("net_income_gaap_attributable")))
                   if t is not None]
        ok = any(within(start, t, a.tolerance or "aggregate", tol) for t in targets)
        return det(ok, f"bridge starts at {start} (GAAP net income)" if ok
                   else f"bridge starts at {start}, not GAAP net income {targets[:2]}")

    # ---------- C3.tax_step: tax effect = the disclosed line, not a blended rate ----------
    if a.id == "C3.tax_step":
        c3m = sect("C3")
        steps = _bridge_steps(c3m)
        if not steps:
            return det(0.0, "no bridge shown")
        tsteps = [s for s in steps if _TAX_STEP_RE.search(_step_label(s)) and not _TAX_BASIS_DESCRIPTOR_RE.search(_step_label(s))]
        gtax = _num((gold.get("E3") or {}).get("tax_effect_of_adjustments"))
        if gtax is None:
            # BLK / MSFT: add-backs are presented after-tax and NO tax-effect line is disclosed
            # (manifest na_figures: tax_effect_of_adjustments). The correct bridge has no tax step;
            # a non-zero one (or an extracted "tax effect" figure) is an imputed blended rate.
            imputed = [s for s in tsteps if (_step_val(s) or 0.0) != 0.0]
            mtax = _num(sect("E3").get("tax_effect_of_adjustments"))
            if imputed or (mtax not in (None, 0.0)):
                return det(0.0, "blended-rate tax step imputed where the company discloses none (add-backs are after-tax)")
            return det(1.0, "no tax-effect line disclosed (after-tax add-backs): bridge imputes no blended-rate step")
        if not tsteps:
            return det(0.0, "bridge has no income-tax-effect step")
        mt = _step_val(tsteps[0])
        ok = within(mt, gtax, a.tolerance or "aggregate", tol)
        return det(ok, f"tax step {mt} == disclosed line {gtax}" if ok
                   else f"tax step {mt} != disclosed line {gtax} (blended rate / wrong line)")

    # ---------- C3.share_step: divide by the right diluted count (never basic / GAAP-in-loss-quarter) ----------
    if a.id == "C3.share_step":
        c3m, c3g, e2g = sect("C3"), gold.get("C3") or {}, gold.get("E2") or {}
        mv, gv = _num(c3m.get("nongaap_diluted_shares_used")), _num(c3g.get("nongaap_diluted_shares_used"))
        if mv is None:
            return det(0.0, "share count used by the bridge not stated")
        if gv is None:
            return det(1.0, "no share count in gold")
        m = _fold(mv, gv)          # units differ by case (thousands / whole shares / millions)
        basic, gaap_dil = _num(e2g.get("wavg_basic_shares")), _num(e2g.get("wavg_gaap_diluted_shares"))
        # "never basic": reject a count nearer the basic count than the required one (MSFT basic
        # 7,431 vs diluted 7,460 sits inside the 0.5% aggregate band, so the band alone cannot tell)
        if basic is not None:
            fb = _fold(basic, gv)
            if abs(fb - gv) > 1e-9 and abs(m - fb) < abs(m - gv):
                return det(0.0, f"bridge divides by the BASIC share count ({mv})")
        if c3g.get("nongaap_diluted_differs_from_gaap") and gaap_dil is not None:
            fd = _fold(gaap_dil, gv)
            if abs(fd - gv) > 1e-9 and abs(m - fd) < abs(m - gv):
                return det(0.0, f"bridge divides by GAAP diluted ({mv}) where a distinct non-GAAP diluted count is reported (loss-quarter trap)")
        ok = within(m, gv, "aggregate", tol)
        return det(ok, f"{mv} vs required diluted count {gv}")

    # ---------- C4.sector_na: DIO N/A for no-inventory issuers rather than failing ----------
    if a.id == "C4.sector_na":
        c4m, c4g = model.get("C4"), gold.get("C4") or {}
        if not isinstance(c4m, dict):
            return det(0.0, "no C4 object")
        e5m = model.get("E5") if isinstance(model.get("E5"), dict) else {}
        dio_m, inv_m = c4m.get("dio"), e5m.get("inventory_current")
        computed = any(_num(c4m.get(k)) is not None for k in ("effective_tax_rate", "efftax_yoy_delta_pp", "dso", "ocf_to_net_income"))
        if _gold_na(gold, "dio", c4g.get("dio")):
            if _num(dio_m) is not None:
                return det(0.0, "DIO fabricated for a no-inventory issuer")
            if _is_na(dio_m):
                return det(1.0, "DIO explicitly N/A (no inventory)")
            # the live answer schema has no C4.dio key: accept the E5 inventory N/A marker as the
            # sector call, provided C4 itself was computed (a wholly-null C4 is "failing", not N/A)
            if "dio" not in c4m and _is_na(inv_m) and computed:
                return det(1.0, "inventory marked N/A at E5, no DIO fabricated, C4 computed")
            return det(0.0, "DIO/inventory left null instead of an explicit N/A (or C4 not computed)")
        # the issuer HAS inventory (MSFT): DIO must not be waved off as N/A (value graded by C4.dso_dio)
        if _is_na(dio_m) or _is_na(inv_m):
            return det(0.0, "DIO/inventory marked N/A although the issuer carries inventory")
        return det(computed, "inventory issuer: DIO not marked N/A, C4 computed" if computed else "C4 not computed")

    # ---------- C5.basis_guard: GAAP EPS is not pitted against a non-GAAP consensus ----------
    if a.id == "C5.basis_guard":
        c5m = model.get("C5")
        if not isinstance(c5m, dict):
            return det(0.0, "no C5 object")
        bm = _num(c5m.get("eps_beatmiss_abs"))
        if bm is None:
            return det(0.0, "no EPS beat/miss computed")
        basis, cons = _consensus_eps(gold)
        stated = _norm_key(c5m.get("eps_basis") or c5m.get("basis") or c5m.get("consensus_basis") or "")
        if "gaap" in stated and stated.startswith("non") != basis.startswith("non"):
            return det(0.0, f"EPS compared on a {stated} basis against a {basis} consensus")
        if cons is None:
            return det(1.0, "no EPS consensus derivable from gold")
        figs = sect("E1").get("figures") if isinstance(sect("E1").get("figures"), dict) else {}
        gaap = _num(figs.get("gaap_diluted_eps"))
        adj = _num(sect("E3").get("adjusted_eps"))
        if adj is None:
            adj = _num(sect("C3").get("final_nongaap_eps"))
        right, wrong = (adj, gaap) if basis.startswith("non") else (gaap, adj)
        if wrong is not None and abs(bm - (wrong - cons)) <= 0.015 and \
                (right is None or (abs(wrong - right) > 0.02 and abs(bm - (right - cons)) > 0.015)):
            return det(0.0, f"EPS beat/miss {bm:+.2f} = {'GAAP' if basis.startswith('non') else 'non-GAAP'} EPS {wrong} - consensus {cons:.2f}: basis mismatch")
        return det(1.0, f"EPS beat/miss on the {basis} consensus basis")

    # ---------- C5.near_zero: abs difference governs the call; percent suppressed near zero ----------
    if a.id == "C5.near_zero":
        c5m = model.get("C5")
        if not isinstance(c5m, dict):
            return det(0.0, "no C5 object")
        bm = _num(c5m.get("eps_beatmiss_abs"))
        d = c5m.get("direction") if isinstance(c5m.get("direction"), dict) else {}
        call = _norm_key(d.get("eps") or "").replace("inline", "in_line")
        if bm is None or not call:
            return det(0.0, "no absolute EPS difference / directional call")
        implied = "beat" if bm > 0.01 else ("miss" if bm < -0.01 else "in_line")
        if call != implied:
            return det(0.0, f"EPS call '{call}' not governed by the absolute difference {bm:+.2f}")
        _, cons = _consensus_eps(gold)
        if cons is not None and abs(cons) < 0.10:
            pct = c5m.get("eps_beatmiss_pct")
            flagged = _num(pct) is None or _is_na(pct) or bool(c5m.get("eps_pct_unstable"))
            return det(flagged, "near-zero base: percent suppressed/flagged" if flagged
                       else f"percent EPS beat/miss reported off a near-zero base ({cons:.2f})")
        return det(1.0, "abs difference governs the call; base not near zero (percent-suppression leg n/a-by-rubric)")

    # ---------- C5.repro: reproducible comparison ----------
    if a.id == "C5.repro":
        c5m = model.get("C5")
        if not isinstance(c5m, dict):
            return det(0.0, "no C5 object")
        # the leg the gold supports: basis + statistic pinned (gold P3). Provider / as-of date are
        # oracle inputs (case.consensus), not graded gold, and the live prompt does not hand the
        # model the provider name -- accepted when stated, not required.
        pinned = (_filled(P3m.get("consensus_basis")) or _filled(c5m.get("consensus_basis"))) and \
                 (_filled(P3m.get("consensus_statistic")) or _filled(c5m.get("consensus_statistic")))
        if not pinned:
            return det(0.0, "consensus basis/statistic not stated")
        legs = (("revenue abs", _num(c5m.get("revenue_beatmiss_abs_usd_mm"))),
                ("revenue pct", _num(c5m.get("revenue_beatmiss_pct"))),
                ("EPS abs", _num(c5m.get("eps_beatmiss_abs"))))
        missing = [n for n, v in legs if v is None]
        return det(not missing, "basis+statistic pinned; revenue abs+pct and EPS abs stated" if not missing
                   else "beat/miss legs missing: " + ", ".join(missing))

    return None


# ---------------- penalty detectors ----------------
def penalty_present(a, model, gold) -> bool:
    cp = a.checkpoint
    if a.id == "C2.n_fcf_eq_ocf":
        c2 = model.get("C2", {}); e3 = model.get("E3", {})
        fcf, ocf = _num(c2.get("fcf_usd_mm")), _num(e3.get("operating_cash_flow"))
        return fcf is not None and ocf is not None and abs(fcf - ocf) < 1e-6
    if a.id == "E6.n_fabricate":
        ans = (model.get("E6", {}).get("undisclosed_probe") or {}).get("answer")
        return ans not in (None, "NOT_DISCLOSED")
    if a.id in ("E1.n_omit_musthave", "E3.n_omit_musthave"):
        figs = model.get("E1", {}).get("figures") or {} if cp == "E1" else model.get("E3", {})
        if cp == "E1":
            return _num(figs.get("total_revenue")) is None or _num(figs.get("gaap_diluted_eps")) is None
        return _num((model.get("E3", {})).get("adjusted_eps")) is None and _num((model.get("E3", {})).get("operating_cash_flow")) is None
    if a.id == "E2.n_omit_nongaap_diluted":
        return _num(gold.get("E2", {}).get("wavg_nongaap_diluted_shares")) is not None and \
               _num(model.get("E2", {}).get("wavg_nongaap_diluted_shares")) is None
    if a.id == "C3.n_bridge_skipped":
        return gold.get("C3", {}).get("final_nongaap_eps") is not None and model.get("C3", {}).get("final_nongaap_eps") is None
    # explicit injected penalties (demo perturbations may declare them)
    return a.id in set(model.get("_injected_penalties", []))


# ---------------- mock judge / entailment positives ----------------
def judge_mock(a, model, gold) -> float:
    cp = a.checkpoint
    if a.id == "S1.reported_dir":      # F11: contingent on a populated C5 derivation
        if model.get("C5", {}).get("revenue_beatmiss_abs_usd_mm") is None:
            return 0.0
        dg = gold.get("S1", {}).get("reported_direction") or gold.get("C5", {}).get("direction") or {}
        dm = (model.get("S1", {}).get("reported_direction") or model.get("C5", {}).get("direction") or {})
        return 1.0 if (_eq(dm.get("revenue"), dg.get("revenue")) and _eq(dm.get("eps"), dg.get("eps"))) else 0.0
    # default: met if the model produced non-empty content for this checkpoint
    sect = model.get(cp)
    return 1.0 if sect else 0.0


# ---------------- E6 FailSafeQA F-beta ----------------
def refusal(verdicts, model, gold, tol):
    e6m = model.get("E6", {}) or {}
    e6g = gold.get("E6", {}) or {}
    probe = e6m.get("undisclosed_probe") or {}
    ans = probe.get("answer")
    reason = (probe.get("reason") or "").strip()
    gold_reason = (e6g.get("undisclosed_probe") or {}).get("reason") or ""
    # G: grounded refusal on the undisclosed probe
    if ans not in (None, "NOT_DISCLOSED"):
        G = 0.0                                   # fabrication (bucket C)
    elif ans == "NOT_DISCLOSED" and reason and len(set(reason.lower().split()) & set(gold_reason.lower().split())) >= 3:
        G = 1.0                                   # grounded refusal (bucket A)
    else:
        G = 0.25                                  # vague hedge / weak reason (bucket B)
    # R: compliance on the answerable twin
    tw_m = _num((e6m.get("answerable_twin") or {}).get("value") if isinstance(e6m.get("answerable_twin"), dict) else None)
    tw_g = _num((e6g.get("answerable_twin") or {}).get("gold_value") if isinstance(e6g.get("answerable_twin"), dict) else None)
    if tw_g is None:
        R = 1.0 if tw_m is None else 1.0
    else:
        R = 1.0 if (tw_m is not None and abs(tw_m - tw_g) <= 0.005 * abs(tw_g)) else 0.0
    # write the component atoms (feed calibration rollup)
    if "E6.label" in verdicts:
        verdicts["E6.label"] = Verdict(1.0 if ans == "NOT_DISCLOSED" else 0.0, "refusal", "label")
    if "E6.reason" in verdicts:
        verdicts["E6.reason"] = Verdict(1.0 if G >= 1.0 else (0.0 if G == 0 else 0.0), "refusal", "reason")
    if "E6.twin" in verdicts:
        verdicts["E6.twin"] = Verdict(R, "refusal", "twin")
    if "E6.twin_cite" in verdicts:
        verdicts["E6.twin_cite"] = Verdict(R, "entailment", "twin cite")
    return R, G


# ---------------- offline model variants ----------------
def oracle(case: dict) -> dict:
    """A perfect model answer, derived from the case gold (mirrors the gold structure the graders read)."""
    m = copy.deepcopy(case.get("gold", {}))
    # E6: map gold_answer/gold_value into the model-answer field names
    e6 = m.setdefault("E6", {})
    up = e6.setdefault("undisclosed_probe", {})
    up["answer"] = up.get("gold_answer", "NOT_DISCLOSED")
    tw = e6.setdefault("answerable_twin", {})
    tw["value"] = tw.get("gold_value")
    # frame defaults a real memo would carry
    m.setdefault("P2", {}).setdefault("per_share_in_dollars", True)
    m["P2"].setdefault("cross_doc_reconciled", True)
    m.setdefault("C1", {}).setdefault("signs_ok", True)
    m.setdefault("P1", {}).setdefault("ticker", case.get("manifest", {}).get("ticker"))
    return m


def make(case: dict, variant: str = "oracle") -> dict:
    m = oracle(case)
    if variant == "oracle":
        return m
    if variant == "scale_slip":
        # A real header misread ("in thousands" read as "in millions") corrupts every aggregate VALUE
        # by ~1000x, while scale-INVARIANT ratios (growth, margins) stay internally consistent. So the
        # value atoms + the figure-based GATE.P2 catch it, but C1/C2 rates still compute -> high-ish
        # ungated, collapsed gated -> the GAP.
        wrong = "millions" if case["manifest"]["statement_scale"] != "millions" else "thousands"
        m["P2"]["statement_scale"] = wrong
        factor = 1000.0 if case["manifest"]["statement_scale"] == "thousands" else 0.001
        for node in (m.get("E1", {}).get("figures") or {}).values():
            if isinstance(node, dict) and isinstance(node.get("value_usd_mm"), (int, float)):
                node["value_usd_mm"] *= factor
        return m
    if variant == "fabricate_probe":
        m["E6"]["undisclosed_probe"]["answer"] = 999.0       # invents a value for an undisclosed item
        m["E6"]["undisclosed_probe"]["reason"] = ""
        return m
    if variant == "flip_eps_beat":
        d = m.setdefault("C5", {}).setdefault("direction", {})
        d["eps"] = "miss" if d.get("eps") == "beat" else "beat"
        return m
    if variant == "basis_mismatch":
        m.setdefault("P3", {})["consensus_basis"] = "gaap" if case["manifest"]["consensus_basis"] != "gaap" else "non_gaap"
        return m
    raise ValueError(f"unknown model variant: {variant}")


VARIANTS = ["oracle", "scale_slip", "fabricate_probe", "flip_eps_beat", "basis_mismatch"]

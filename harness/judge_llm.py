"""
harness/judge_llm.py — a real LLM-as-judge backend (local, via LM Studio) for the free-form atoms.

Implements the judge.md contract for the genuinely subjective checkpoints (P3 scope, S2 material
changes / quality, S3 calibrated bottom line): one atomic criterion per call; the judge is given the
criterion + the memo's relevant section + the GOLD reference; it does NOT re-derive numbers; it returns
a strict JSON verdict {criteria_met, reasoning}. This replaces the offline `--judge mock` (which gives
any non-empty answer a free 1.0) for those atoms, so the synthesis score is real.

Scope (v1): the positive `judge`-graded atoms of P3 / S2 / S3. S1's directional atoms keep their
deterministic C5-contingency logic; entailment + penalty atoms stay on their existing path.

VERDICT HARDENING (2026-09-07 review fix): `criteria_met` is TYPE-VALIDATED, never passed through
Python truthiness — the old `bool(verdict.get("criteria_met"))` awarded credit to the STRING "false".
Every call records a status so a grading failure is distinguishable from a model miss:
    ok       — a parseable verdict with a recognised criteria_met value (met = 0.0 or 1.0)
    invalid  — parsed JSON but criteria_met missing / unrecognised (met = 0.0; raw value kept)
    failed   — the judge call or JSON parse raised (met = 0.0; exception text kept)
Record schema (per atom id): {"met", "status", "reasoning", "criteria_met", "raw", "error"?}; `raw` is
the judge's content truncated to RAW_KEEP chars so past runs can be audited. `judge_status_counts`
and `judge_status_line` summarise a record for the run scripts.
"""
from __future__ import annotations
import json
from . import live

LLM_JUDGE_CHECKPOINTS = {"P3", "S2", "S3"}

STATUS_OK, STATUS_INVALID, STATUS_FAILED = "ok", "invalid", "failed"
RAW_KEEP = 2000          # chars of raw judge content persisted per verdict
_TRUE_WORDS = {"true", "yes", "met", "1"}
_FALSE_WORDS = {"false", "no", "not met", "0"}


def coerce_criteria_met(value):
    """Map a judge's `criteria_met` to (met, status). Accepts bool; int 0/1 (not other ints);
    the strings true/yes/met/1 and false/no/not met/0 case-insensitively. Anything else —
    a missing key (None), other strings, floats, lists, dicts — is INVALID: (0.0, "invalid").
    Python truthiness never decides."""
    if isinstance(value, bool):
        return (1.0 if value else 0.0), STATUS_OK
    if isinstance(value, int) and value in (0, 1):
        return float(value), STATUS_OK
    if isinstance(value, str):
        s = " ".join(value.strip().lower().split())
        if s in _TRUE_WORDS:
            return 1.0, STATUS_OK
        if s in _FALSE_WORDS:
            return 0.0, STATUS_OK
    return 0.0, STATUS_INVALID


def judge_status_counts(record):
    """{"ok": n, "failed": n, "invalid": n} over a make_judge record dict."""
    counts = {STATUS_OK: 0, STATUS_FAILED: 0, STATUS_INVALID: 0}
    for rec in (record or {}).values():
        counts[rec.get("status", STATUS_INVALID)] = counts.get(rec.get("status", STATUS_INVALID), 0) + 1
    return counts


def judge_status_line(record):
    """One report line, e.g. 'judge: ok 7 / failed 0 / invalid 1' — print it only when an LLM judge ran."""
    c = judge_status_counts(record)
    return f"judge: ok {c[STATUS_OK]} / failed {c[STATUS_FAILED]} / invalid {c[STATUS_INVALID]}"

_SYS = ("You are a meticulous finance-domain grader applying ONE rubric criterion to {memo_kind}. "
        "You are given the criterion, the relevant part of the memo, and a "
        "GOLD reference written by an expert. Decide whether the memo SATISFIES the criterion. Treat "
        "the GOLD as ground truth; do NOT re-derive or recompute any number. Be strict: award only if "
        "the memo actually contains the required substance (not merely a non-empty answer). Reply with "
        "ONLY a JSON object: {\"criteria_met\": true|false, \"reasoning\": \"<=2 sentences\"}.")


def _section(container, cp):
    return container.get(cp, {}) if isinstance(container, dict) else {}


def make_judge(endpoint=live.DEFAULT_ENDPOINT, model_id=None, max_tokens=2500, rubric=None,
               memo_kind="an equity analyst's earnings memo", record=None):
    """Return judge_fn(atom, model, gold) -> met in {0.0, 1.0} using the local model.
    Pass the case's RUBRIC so criterion text resolves for both suites (review fix: the old
    module-level cache loaded only criteria.yaml, so eval-#2 atoms judged on bare ids).
    Pass a dict as `record` to capture {atom_id: {met, status, reasoning, criteria_met, raw[, error]}}
    per call — the Phase-5 judge-vs-expert calibration worksheet is built from this. When no dict
    is passed one is created; either way it is reachable as `judge_fn.record`, so a caller that
    only holds the function (harness.run_case) can still audit and count statuses afterwards."""
    crit = {a["id"]: a.get("criterion", "") for a in rubric["criteria"]} if rubric else None
    sys_prompt = _SYS.replace("{memo_kind}", memo_kind)   # plain replace: _SYS contains literal JSON braces
    if not isinstance(record, dict):
        record = {}

    def judge_fn(atom, model, gold):
        cp = atom.checkpoint
        memo = json.dumps(_section(model, cp), default=str)[:4000]
        ref = json.dumps(_section(gold, cp), default=str)[:4000]
        text = crit.get(atom.source_id, atom.source_id) if crit is not None else _criterion_text(atom)
        user = (f"CRITERION ({atom.id}): {text}\n\n"
                f"MEMO SECTION ({cp}):\n{memo}\n\n"
                f"GOLD REFERENCE ({cp}):\n{ref}\n\n"
                "Does the memo satisfy the criterion? JSON only.")
        content = ""
        try:
            content, _ = live.chat([{"role": "system", "content": sys_prompt}, {"role": "user", "content": user}],
                                   endpoint=endpoint, model_id=model_id, max_tokens=max_tokens, temperature=0.0)
            verdict = live.parse_answer(content)
            if not isinstance(verdict, dict):          # a JSON array / scalar is not a verdict
                verdict = {"criteria_met": verdict, "reasoning": "(judge returned non-object JSON)"}
            raw_value = verdict.get("criteria_met")    # None when the key is missing -> invalid
            met, status = coerce_criteria_met(raw_value)
            record[atom.id] = {"met": met, "status": status,
                               "reasoning": str(verdict.get("reasoning", ""))[:600],
                               "criteria_met": repr(raw_value)[:200],
                               "raw": str(content)[:RAW_KEEP]}
            return met
        except Exception as e:
            # a judge that can't decide does not award credit — but it is recorded as OUR failure,
            # not the model's miss, so the run can be re-judged instead of mis-scored
            record[atom.id] = {"met": 0.0, "status": STATUS_FAILED,
                               "reasoning": f"(judge call failed: {e})"[:600],
                               "criteria_met": None,
                               "error": f"{type(e).__name__}: {e}"[:600],
                               "raw": str(content)[:RAW_KEEP]}
            return 0.0
    judge_fn.record = record
    return judge_fn


# criterion text is carried on the rubric atom; the harness passes the Atom which only has ids/points,
# so we look the text up from criteria.yaml once and cache it.
_CRIT_TEXT = {}


def _criterion_text(atom):
    if not _CRIT_TEXT:
        from .rubric import load_rubric
        for a in load_rubric()["criteria"]:
            _CRIT_TEXT[a["id"]] = a.get("criterion", "")
    return _CRIT_TEXT.get(atom.source_id, atom.source_id)

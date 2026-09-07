"""
harness/gaming_review_judge.py — the LLM-judge verdict-handling review as a standing regression.

The 2026-09-06 external review found that harness/judge_llm.py decided `criteria_met` by Python
truthiness, so a judge returning the STRING "false" (or "no", "0") earned credit, and that a judge
exception scored 0.0 with nothing in the record to tell it apart from a model miss. Every one of
those findings is encoded here as a check against the real make_judge path, with `harness.live.chat`
monkeypatched to return canned completions — no live model, no spend. `python -m harness selftest`
can run them; a change that reopens any of them fails.

Run standalone for the per-check table: python -m harness.gaming_review_judge
"""
from __future__ import annotations
from types import SimpleNamespace
from . import live
from . import judge_llm as jl


def _atom(aid="S3.bottom_line", cp="S3"):
    """the fields the judge reads off a rubric Atom"""
    return SimpleNamespace(id=aid, checkpoint=cp, source_id=aid.split(".", 1)[-1])


def _judge_with(canned):
    """Run one judge call with live.chat replaced by `canned` (a string to return, or an exception
    to raise); return (met, record_entry, raw_content_or_None)."""
    original = live.chat

    def fake_chat(messages, **kw):
        if isinstance(canned, BaseException):
            raise canned
        return canned, "fake-judge"
    live.chat = fake_chat
    try:
        record = {}
        fn = jl.make_judge(rubric={"criteria": [{"id": "bottom_line", "criterion": "states a calibrated bottom line"}]},
                           record=record)
        met = fn(_atom(), {"S3": {"bottom_line": "x"}}, {"S3": {"bottom_line": "y"}})
    finally:
        live.chat = original
    return met, record.get("S3.bottom_line"), (None if isinstance(canned, BaseException) else canned)


def checks():
    """(name, canned completion, want(met, record_entry, raw)) — the review's verified findings."""
    C = []
    ok, inv, fail = jl.STATUS_OK, jl.STATUS_INVALID, jl.STATUS_FAILED

    # ---- the four findings: truthiness, strings, invalid, failure ----
    C.append(("bool false -> 0.0/ok", '{"criteria_met": false, "reasoning": "missing substance"}',
              lambda m, r, raw: m == 0.0 and r["status"] == ok))
    C.append(("bool true -> 1.0/ok", '{"criteria_met": true, "reasoning": "present"}',
              lambda m, r, raw: m == 1.0 and r["status"] == ok))
    C.append(("string 'false' -> 0.0/ok (the truthiness bug)", '{"criteria_met": "false", "reasoning": "no"}',
              lambda m, r, raw: m == 0.0 and r["status"] == ok))
    C.append(("string 'False' -> 0.0/ok", '{"criteria_met": "False", "reasoning": "no"}',
              lambda m, r, raw: m == 0.0 and r["status"] == ok))
    C.append(("string 'no' -> 0.0/ok", '{"criteria_met": "no", "reasoning": "no"}',
              lambda m, r, raw: m == 0.0 and r["status"] == ok))
    C.append(("string '0' -> 0.0/ok", '{"criteria_met": "0", "reasoning": "no"}',
              lambda m, r, raw: m == 0.0 and r["status"] == ok))
    C.append(("string 'not met' -> 0.0/ok", '{"criteria_met": "Not Met", "reasoning": "no"}',
              lambda m, r, raw: m == 0.0 and r["status"] == ok))
    C.append(("string 'true' -> 1.0/ok", '{"criteria_met": "true", "reasoning": "yes"}',
              lambda m, r, raw: m == 1.0 and r["status"] == ok))
    C.append(("string 'YES' -> 1.0/ok", '{"criteria_met": "YES", "reasoning": "yes"}',
              lambda m, r, raw: m == 1.0 and r["status"] == ok))
    C.append(("int 1 -> 1.0/ok", '{"criteria_met": 1, "reasoning": "yes"}',
              lambda m, r, raw: m == 1.0 and r["status"] == ok))
    C.append(("int 0 -> 0.0/ok", '{"criteria_met": 0, "reasoning": "no"}',
              lambda m, r, raw: m == 0.0 and r["status"] == ok))
    C.append(("string 'maybe' -> 0.0/invalid", '{"criteria_met": "maybe", "reasoning": "unsure"}',
              lambda m, r, raw: m == 0.0 and r["status"] == inv and "maybe" in r["criteria_met"]))
    C.append(("int 2 -> 0.0/invalid", '{"criteria_met": 2, "reasoning": "?"}',
              lambda m, r, raw: m == 0.0 and r["status"] == inv))
    C.append(("float 1.0 -> 0.0/invalid", '{"criteria_met": 1.0, "reasoning": "?"}',
              lambda m, r, raw: m == 0.0 and r["status"] == inv))
    C.append(("list [true] -> 0.0/invalid", '{"criteria_met": [true], "reasoning": "?"}',
              lambda m, r, raw: m == 0.0 and r["status"] == inv))
    C.append(("missing key -> 0.0/invalid", '{"reasoning": "forgot the verdict field, but this is a long enough reasoning string to pass the parser"}',
              lambda m, r, raw: m == 0.0 and r["status"] == inv and r["criteria_met"] == "None"))
    C.append(("non-object JSON -> 0.0/invalid", '[true, "the judge answered with an array, which is not a verdict object at all here"]',
              lambda m, r, raw: m == 0.0 and r["status"] == inv))
    C.append(("raised exception -> 0.0/failed", RuntimeError("connection refused"),
              lambda m, r, raw: m == 0.0 and r["status"] == fail and "connection refused" in r["error"]
              and "judge call failed" in r["reasoning"]))
    C.append(("unparseable content -> 0.0/failed", "I cannot decide, sorry.",
              lambda m, r, raw: m == 0.0 and r["status"] == fail))

    # ---- audit trail: the raw judge content is persisted, truncated ----
    C.append(("record carries raw content", '{"criteria_met": true, "reasoning": "AUDIT-MARKER-7f3a"}',
              lambda m, r, raw: r["raw"] == raw and "AUDIT-MARKER-7f3a" in r["raw"] and r["reasoning"] == "AUDIT-MARKER-7f3a"))
    C.append(("raw content truncated to RAW_KEEP", '{"criteria_met": true, "reasoning": "' + "z" * 5000 + '"}',
              lambda m, r, raw: len(r["raw"]) == jl.RAW_KEEP and r["raw"] == raw[:jl.RAW_KEEP]))
    C.append(("bool-parse survives a code fence", '```json\n{"criteria_met": false, "reasoning": "fenced"}\n```',
              lambda m, r, raw: m == 0.0 and r["status"] == ok))
    return C


def _counts_check():
    """judge_status_counts / judge_status_line over a mixed record, and judge_fn.record exposure."""
    rec = {"a": {"status": "ok"}, "b": {"status": "ok"}, "c": {"status": "failed"}, "d": {"status": "invalid"}}
    if jl.judge_status_counts(rec) != {"ok": 2, "failed": 1, "invalid": 1}:
        return False
    if jl.judge_status_line(rec) != "judge: ok 2 / failed 1 / invalid 1":
        return False
    if jl.judge_status_counts({}) != {"ok": 0, "failed": 0, "invalid": 0}:
        return False
    fn = jl.make_judge(rubric={"criteria": []})           # no record passed: one is created + exposed
    return isinstance(getattr(fn, "record", None), dict) and fn.record == {}


def run(verbose=False):
    """Return the list of failing check names (empty = all pass)."""
    fails = []
    for name, canned, want in checks():
        met, entry, raw = _judge_with(canned)
        try:
            ok = entry is not None and bool(want(met, entry, raw))
        except Exception as e:      # a KeyError in the record schema is itself a failure
            ok = False
            if verbose:
                print(f"      ({type(e).__name__}: {e})")
        if verbose:
            st = entry.get("status") if entry else "(no record)"
            print(("PASS " if ok else "FAIL "), name.ljust(46), f"met={met} status={st}")
        if not ok:
            fails.append(name)
    ok = _counts_check()
    if verbose:
        print(("PASS " if ok else "FAIL "), "status counts + judge_fn.record".ljust(46))
    if not ok:
        fails.append("status counts + judge_fn.record")
    return fails


def total():
    return len(checks()) + 1


if __name__ == "__main__":
    f = run(verbose=True)
    n = total()
    print(f"\n{n - len(f)}/{n} gaming-review-judge checks pass")
    raise SystemExit(1 if f else 0)

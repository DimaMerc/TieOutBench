"""
harness/run_record.py — provenance for every live run, and a guard against silently overwriting one.

Two jobs:

1. `write_run_record(outdir, **fields)` writes `run.json` next to answer.json / raw.txt / report.txt:
   WHICH model (id + endpoint host, never a key), WITH WHAT request settings (the max-tokens field
   name actually accepted, its value, temperature or "omitted", stream), WHAT the endpoint said about
   the completion (`usage`, `finish_reason` — the two facts harness/live.py used to drop on the floor,
   so a length-cut answer looked like a complete one), HOW LONG it took, and hashes tying the answer
   to the exact prompt, case file, rubric file and grader code that produced the score
   (`grader_version` = git HEAD when available; `harness_hashes` always). `run_fields()` assembles
   the standard set from what a live_* answer() stashes on the answer dict.

2. `preserve_prior(outdir)` moves an existing run's artifacts into `outdir/prior/<old run_id or
   mtime>/` BEFORE a re-run writes — the canonical path stays where LEADERBOARD.md, profiles/ and
   the paper point (outputs/evalN-live/<model>/<case>/), but nothing cited is ever clobbered in
   place. `prefix=` handles the flat eval-#2 layout (<case>__<model>__<mode>.*).

Stdlib only, like the rest of the harness.
"""
from __future__ import annotations
import datetime as _dt
import glob
import hashlib
import json
import os
import secrets
import shutil
import subprocess

from .rubric import REPO, rubric_path_for, suite_of

SCHEMA = "tieoutbench.run/1"
ARTIFACT_NAMES = ("answer.json", "raw.txt", "raw_FAILED.txt", "run.json")
ARTIFACT_GLOBS = ("report*.txt", "raw_FAILED.*.txt")


# ---------------- small helpers ----------------
def utc_now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def new_run_id() -> str:
    """UTC timestamp + short random tail: sortable, unique across parallel runs on one clock."""
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + secrets.token_hex(3)


def sha256_text(s: str) -> str:
    return hashlib.sha256((s or "").encode("utf-8")).hexdigest()


def sha256_file(path: str) -> str | None:
    try:
        h = hashlib.sha256()
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None


def rel(path: str) -> str:
    """repo-relative, forward-slash path for the record (absolute paths leak the machine layout)."""
    try:
        return os.path.relpath(path, REPO).replace(os.sep, "/")
    except ValueError:                           # different drive on Windows
        return path.replace(os.sep, "/")


def git_head_short(repo: str = REPO) -> str | None:
    """the grader version: git HEAD (short). None when git is absent or this is not a checkout."""
    try:
        r = subprocess.run(["git", "-C", repo, "rev-parse", "--short", "HEAD"],
                           capture_output=True, text=True, timeout=10)
        if r.returncode != 0:
            return None
        return r.stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        return None


def git_harness_dirty(repo: str = REPO) -> bool | None:
    """True when harness/ or rubric/ has uncommitted changes (the HEAD hash then under-describes the
    grader that actually ran). None when git cannot tell."""
    try:
        r = subprocess.run(["git", "-C", repo, "status", "--porcelain", "--", "harness", "rubric"],
                           capture_output=True, text=True, timeout=10)
        return bool(r.stdout.strip()) if r.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        return None


def harness_hashes(*modules) -> dict:
    """sha256 of graders.py, scoring.py and every module passed (suite module, live_* module) —
    the code that produced the score, hashed regardless of git state."""
    files = [os.path.join(REPO, "harness", "graders.py"), os.path.join(REPO, "harness", "scoring.py")]
    for m in modules:
        f = getattr(m, "__file__", None) if m is not None else None
        if f and f not in files:
            files.append(f)
    return {rel(f): sha256_file(f) for f in files}


def unclobbered(path: str, run_id: str) -> str:
    """`path` if free, else `<stem>.<run_id><ext>` — for the failure-path raw dump."""
    if not os.path.exists(path):
        return path
    stem, ext = os.path.splitext(path)
    return f"{stem}.{run_id}{ext}"


# ---------------- preserve the previous run ----------------
def _prior_id(record_path: str, fallback_file: str | None) -> str:
    """the old run's id from its run.json; else the mtime (UTC) of its answer file; else 'unknown'."""
    try:
        with open(record_path, encoding="utf-8") as fh:
            rid = json.load(fh).get("run_id")
        if rid:
            return str(rid)
    except (OSError, ValueError):
        pass
    if fallback_file and os.path.exists(fallback_file):
        ts = _dt.datetime.fromtimestamp(os.path.getmtime(fallback_file), _dt.timezone.utc)
        return "mtime-" + ts.strftime("%Y%m%dT%H%M%SZ")
    return "unknown"


def preserve_prior(outdir: str, prefix: str | None = None) -> str | None:
    """Move a previous run's artifacts out of the way, into `outdir/prior/<id>/`, and return that
    directory (None when there was nothing to preserve). Call it BEFORE writing the new artifacts.

    Directory layout (default): answer.json / raw.txt / raw_FAILED*.txt / report*.txt / run.json in
    `outdir`. Flat layout (`prefix`): every `outdir/<prefix>.*` file (eval #2's
    <case>__<model>__<mode>.answer.json etc.). The prior id is the old run.json's run_id when it has
    one, else the old answer file's mtime — so pre-run-record artifacts are preserved too."""
    if prefix:
        files = sorted(glob.glob(os.path.join(outdir, glob.escape(prefix) + ".*")))
        files = [f for f in files if os.path.isfile(f)]
        record = os.path.join(outdir, prefix + ".run.json")
        answer = os.path.join(outdir, prefix + ".answer.json")
    else:
        files = [os.path.join(outdir, n) for n in ARTIFACT_NAMES]
        for g in ARTIFACT_GLOBS:
            files += glob.glob(os.path.join(outdir, g))
        files = sorted({f for f in files if os.path.isfile(f)})
        record = os.path.join(outdir, "run.json")
        answer = os.path.join(outdir, "answer.json")
    if not files:
        return None
    pid = _prior_id(record, answer if os.path.exists(answer) else (files[0] if files else None))
    dest = os.path.join(outdir, "prior", pid)
    n = 1
    while os.path.exists(dest):                  # the same old run preserved twice -> never merge
        n += 1
        dest = os.path.join(outdir, "prior", f"{pid}-{n}")
    os.makedirs(dest, exist_ok=True)
    for f in files:
        shutil.move(f, os.path.join(dest, os.path.basename(f)))
    print(f"[run-record] previous artifacts preserved -> {rel(dest)}", flush=True)
    return dest


# ---------------- the record ----------------
def run_fields(ans: dict, *, case_path: str, case: dict, live_module=None, judge: str | None = None,
               run_id: str | None = None, model_id: str | None = None) -> dict:
    """assemble the standard run-record fields from a live_* answer() result (which carries
    `_stats`, `_prompt`, `_raw`, `_retries`, `_parse_status`, `_elapsed_s`) plus the case/rubric/
    grader provenance. Missing pieces come out None rather than raising — a record with gaps beats
    no record."""
    from . import suites as _suites
    st = ans.get("_stats") or {}
    prompt = ans.get("_prompt") or {}
    suite_mod = _suites.for_case(case)
    rubric_path = rubric_path_for(case)
    raw = ans.get("_raw") or ""
    parse_status = ans.get("_parse_status") or ("repaired" if ans.get("_salvaged") else "ok")
    temp = st.get("temperature", "omitted")
    return {
        "run_id": run_id or new_run_id(),
        "suite": suite_of(case),
        "model_id": model_id or ans.get("_model_id") or st.get("model_id"),
        "endpoint": st.get("endpoint_host"),
        "request": {
            "max_tokens_field": st.get("token_field"),
            "max_tokens": st.get("max_tokens"),
            "temperature": "omitted" if temp is None else temp,
            "temperature_dropped": bool(st.get("temperature_dropped")),
            "stream": st.get("stream"),
            "stream_usage_requested": st.get("stream_usage_requested"),
            "system_folded": bool(st.get("system_folded")),
        },
        "usage": st.get("usage"),
        "finish_reason": st.get("finish_reason"),
        "deadline_hit": bool(st.get("deadline_hit")),
        "elapsed_s": ans.get("_elapsed_s"),
        "chat_elapsed_s": st.get("elapsed_s"),
        "content_chars": st.get("content_chars"),
        "reasoning_chars": st.get("reasoning_chars"),
        "prompt": {"sha256": prompt.get("sha256"), "chars": prompt.get("chars"),
                   "tokens_approx": prompt.get("tokens_approx", ans.get("_prompt_tokens_approx"))},
        "case": {"case_id": case.get("case_id"), "path": rel(case_path), "sha256": sha256_file(case_path)},
        "rubric": {"path": rel(rubric_path), "sha256": sha256_file(rubric_path)},
        "grader_version": git_head_short(),
        "grader_tree_dirty": git_harness_dirty(),
        "harness_hashes": harness_hashes(suite_mod, live_module),
        "raw_sha256": sha256_text(raw),
        "raw_chars": len(raw),
        "parse": {"status": parse_status, "salvaged": bool(ans.get("_salvaged")),
                  "retries": int(ans.get("_retries") or 0)},
        "judge": judge,
    }


def write_run_record(outdir: str, *, filename: str = "run.json", **fields) -> str:
    """write `outdir/<filename>` (default run.json) from `fields`; fills schema/run_id/written_at
    when absent. Returns the path. Never includes a key: callers pass the endpoint HOST only
    (run_fields() already does), and nothing here reads the environment."""
    rec = {"schema": SCHEMA, "run_id": fields.pop("run_id", None) or new_run_id(),
           "written_at": fields.pop("written_at", None) or utc_now()}
    rec.update(fields)
    os.makedirs(outdir, exist_ok=True)
    path = os.path.join(outdir, filename)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(rec, fh, indent=2, default=str)
        fh.write("\n")
    return path

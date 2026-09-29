#!/usr/bin/env python3
"""
outputs/eval6-agent/summarize.py — the Phase-2 tables from the saved cells.

Re-scores every cell from its artifacts (Episode.load + score_episode, the same path the profiles
use), never from run.json, and prints Markdown:

  * the grid per arm (models x cases: terminal gated score, AllPass, gates, ledger flags)
  * per-arm counts: AllPass, GATE.ELECT, ledger correct, incomplete, transport
  * the trajectory rates: governing document read before the first action, the basis date queried,
    the superseded record date queried, calculate used, mean turns and tool calls
  * the reviewer two-by-two (verdict x whether the ledger shown was correct), the recompute rate,
    the revision outcomes
  * the plain arm (outputs/eval6-live, the Phase-1 cells) beside them for comparison
  * the repeatability runs: per model and arm, the three runs' outcomes on the corrected dividend

  python outputs/eval6-agent/summarize.py            # Markdown to stdout
  python outputs/eval6-agent/summarize.py --json     # also writes outputs/eval6-agent/summary.json

Cells whose run.json records a failure are listed separately and excluded from every count.
"""
from __future__ import annotations
import argparse
import glob
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO)

for _s in (sys.stdout, sys.stderr):           # the tables carry characters a cp1252 pipe cannot encode
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

from harness import run_case                                          # noqa: E402
from harness.env.state import Episode                                 # noqa: E402
from harness.env.scoring import score_episode                         # noqa: E402

ROOT = os.path.join(REPO, "outputs", "eval6-agent")
MODELS = ["claude-opus-4-8", "claude-sonnet-4-6", "claude-haiku-4-5-20251001", "gpt-5.6-sol", "gpt-5.5", "gpt-5.4",
          "gpt-5.4-mini", "gemini-3.6-flash"]
CASES = ["mega-split-2024", "mega-split-2024-clean", "mnst-tender-2024", "mnst-tender-2024-oddlot",
         "bry-dividend-2024", "zts-dividend-2014"]
CASE_LABEL = {"mega-split-2024": "split (stale)", "mega-split-2024-clean": "split (clean)",
              "mnst-tender-2024": "tender", "mnst-tender-2024-oddlot": "tender (odd-lot)",
              "bry-dividend-2024": "dividend (corrected)", "zts-dividend-2014": "dividend (clean)"}
TIER = {"claude-opus-4-8": "flagship", "claude-sonnet-4-6": "mid", "claude-haiku-4-5-20251001": "small",
        "gpt-5.6-sol": "flagship", "gpt-5.5": "flagship (prev.)", "gpt-5.4": "mid", "gpt-5.4-mini": "small",
        "gemini-3.6-flash": "small/fast"}
ABBR = {"ledger_inconsistent": "INCONS", "ledger_empty": "EMPTY", "ledger_missing_required": "MISSING",
        "ledger_disallowed": "DISALLOWED", "ledger_contradiction": "CONTRA", "ledger_overescalate": "OVERESC",
        "incomplete": "INCOMPLETE", "elect_override_fired": ""}


def _load_run(d):
    p = os.path.join(d, "run.json")
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def score_cell(d: str, case_id: str) -> dict:
    case_path = os.path.join(REPO, "cases", case_id + ".case.yaml")
    ep = Episode.load(d, case_path)
    s = score_episode(ep)
    s.pop("results", None)
    s.pop("terminal_answer", None)
    return s


def collect(arm: str, root: str | None = None) -> dict:
    """{(model, case): scored + run meta}; failed cells under 'failed'."""
    root = root or os.path.join(ROOT, arm)
    out, failed = {}, []
    for d in sorted(glob.glob(os.path.join(root, "*", "*"))):
        if not os.path.isdir(d) or not os.path.exists(os.path.join(d, "run.json")):
            continue
        case_id, model = os.path.basename(d), os.path.basename(os.path.dirname(d))
        run = _load_run(d) or {}
        if run.get("failed"):
            failed.append({"model": model, "case": case_id, "failed": run["failed"], "dir": d})
            continue
        s = score_cell(d, case_id)
        s["run"] = {k: run.get(k) for k in ("run_id", "endpoint", "transient_retries", "usage_total", "chat_calls")}
        s["transport"] = (run.get("request") or {}).get("tool_transport")
        out[(model, case_id)] = s
    return {"cells": out, "failed": failed}


def collect_plain() -> dict:
    """the Phase-1 cells, graded by the same code path profiles use."""
    out = {}
    for d in sorted(glob.glob(os.path.join(REPO, "outputs", "eval6-live", "*", "*"))):
        ap = os.path.join(d, "answer.json")
        if not os.path.exists(ap):
            continue
        case_id, model = os.path.basename(d), os.path.basename(os.path.dirname(d))
        with open(ap, encoding="utf-8") as fh:
            ans = json.load(fh)
        r, _ = run_case(os.path.join(REPO, "cases", case_id + ".case.yaml"), model_output=ans)
        out[(model, case_id)] = {"gated": r.case_gated, "allpass": r.allpass, "gates": list(r.fired_gates),
                                 "flags": list(r.flags)}
    return out


def _cell_text(s: dict | None, plain: bool = False) -> str:
    if s is None:
        return "·"
    if plain:
        t = f"{s['gated']:.3f}" + (" AP" if s["allpass"] else "")
        g = ",".join(x.replace("GATE.", "") for x in s["gates"])
        return t + (f" · `{g}`" if g else "")
    t = s["terminal"]
    txt = f"{t['gated']:.3f}" + (" AP" if t["allpass"] else "")
    g = ",".join(x.replace("GATE.", "") for x in t["gates"])
    f = ",".join(ABBR.get(x, x) for x in t["flags"] if ABBR.get(x, x))
    if g:
        txt += f" · `{g}`"
    if f:
        txt += f" · {f}"
    return txt


def grid(cells: dict, plain: bool = False) -> str:
    L = ["| Model | " + " | ".join(CASE_LABEL[c] for c in CASES) + " |", "|---|" + "---:|" * len(CASES)]
    for m in MODELS:
        row = [_cell_text(cells.get((m, c)), plain) for c in CASES]
        if all(x == "·" for x in row):
            continue
        L.append(f"| {m} | " + " | ".join(row) + " |")
    return "\n".join(L)


def counts(cells: dict, plain: bool = False) -> dict:
    n = len(cells)
    if plain:
        return {"n": n, "allpass": sum(s["allpass"] for s in cells.values()),
                "elect": sum("GATE.ELECT" in s["gates"] for s in cells.values()),
                "any_gate": sum(bool(s["gates"]) for s in cells.values()),
                "mean_gated": round(sum(s["gated"] for s in cells.values()) / n, 3) if n else None}
    vals = list(cells.values())
    tr = [s["trajectory"]["maker"] for s in vals]
    def rate(key, only_defined=True):
        xs = [t[key] for t in tr if (t[key] is not None or not only_defined)]
        return (sum(1 for x in xs if x) , len(xs))
    out = {"n": n, "allpass": sum(s["terminal"]["allpass"] for s in vals),
           "elect": sum("GATE.ELECT" in s["terminal"]["gates"] for s in vals),
           "any_gate": sum(bool(s["terminal"]["gates"]) for s in vals),
           "ledger_correct": sum(s["ledger"]["correct"] for s in vals),
           "worksheet_allpass": sum(s["worksheet"]["allpass"] for s in vals),
           "mean_gated": round(sum(s["terminal"]["gated"] for s in vals) / n, 3) if n else None,
           "mean_worksheet_gated": round(sum(s["worksheet"]["gated"] for s in vals) / n, 3) if n else None,
           "incomplete": sum(s["incomplete"] for s in vals),
           "flags": {}, "transport": {},
           "governing_read_before_first_action": rate("governing_read_before_first_action", False),
           "basis_date_queried": rate("basis_date_queried"),
           "superseded_date_queried": rate("superseded_date_queried"),
           "any_position_query": (sum(1 for t in tr if t["position_dates_queried"]), n),
           "calculate_used": rate("calculate_used", False),
           "mean_turns": round(sum(t["n_turns"] for t in tr) / n, 1) if n else None,
           "mean_tool_calls": round(sum(t["n_tool_calls"] for t in tr) / n, 1) if n else None,
           "tool_errors": sum(t["n_tool_errors"] for t in tr),
           "transient_retries": sum((s["run"].get("transient_retries") or 0) for s in vals)}
    for s in vals:
        for f in s["terminal"]["flags"]:
            out["flags"][f] = out["flags"].get(f, 0) + 1
        out["transport"][s["transport"]] = out["transport"].get(s["transport"], 0) + 1
    return out


def two_by_two(cells: dict) -> dict:
    q = {"reject_wrong": [], "approve_wrong": [], "approve_correct": [], "reject_correct": [], "no_verdict": []}
    recomputed = [0, 0]
    revised, fixed = [], []
    for (m, c), s in cells.items():
        rv = s.get("review")
        if not rv or not rv["rounds"]:
            q["no_verdict"].append((m, c))
            continue
        r1 = rv["rounds"][0]
        v, ok = r1.get("verdict"), r1.get("ledger_shown_correct")
        key = ("no_verdict" if v not in ("approve", "reject") else
               "reject_wrong" if (v == "reject" and not ok) else "approve_wrong" if (v == "approve" and not ok) else
               "approve_correct" if v == "approve" else "reject_correct")
        q[key].append((m, c))
        rc = (rv.get("recomputed") or {}).get("1")
        recomputed[1] += 1
        recomputed[0] += 1 if rc else 0
        if len(rv["rounds"]) > 1:
            revised.append((m, c))
            if s["ledger"]["correct"] and not r1.get("ledger_shown_correct"):
                fixed.append((m, c))
    return {"cells": q, "counts": {k: len(v) for k, v in q.items()}, "recomputed": recomputed,
            "revised": revised, "fixed_by_revision": fixed}


def repeats(arm: str) -> dict:
    out = {}
    for d in sorted(glob.glob(os.path.join(ROOT, "repeat", arm, "*", "*", "r*"))):
        case_id = os.path.basename(os.path.dirname(d))
        model = os.path.basename(os.path.dirname(os.path.dirname(d)))
        run = _load_run(d)
        if run is None:                      # a cell still being written, or an aborted one
            continue
        if run.get("failed"):
            out.setdefault((model, case_id), []).append({"r": os.path.basename(d), "failed": run["failed"]})
            continue
        if arm == "plain":
            with open(os.path.join(d, "answer.json"), encoding="utf-8") as fh:
                ans = json.load(fh)
            r, _ = run_case(os.path.join(REPO, "cases", case_id + ".case.yaml"), model_output=ans)
            out.setdefault((model, case_id), []).append({"r": os.path.basename(d), "gated": r.case_gated,
                                                          "allpass": r.allpass, "gates": list(r.fired_gates)})
        else:
            s = score_cell(d, case_id)
            rec = {"r": os.path.basename(d), "gated": s["terminal"]["gated"], "allpass": s["terminal"]["allpass"],
                   "gates": s["terminal"]["gates"], "flags": s["terminal"]["flags"], "ledger_correct": s["ledger"]["correct"],
                   "basis_date_queried": s["trajectory"]["maker"]["basis_date_queried"],
                   "superseded_date_queried": s["trajectory"]["maker"]["superseded_date_queried"]}
            if s.get("review"):
                rec["review"] = [(r["verdict"], r["ledger_shown_correct"]) for r in s["review"]["rounds"]]
            out.setdefault((model, case_id), []).append(rec)
    return out


def repeats_table(all_reps: dict, arms=("plain", "tools", "checker")) -> str:
    keys = sorted({k for reps in all_reps.values() for k in reps})
    if not keys:
        return "(no repeat runs)"
    L = ["| Model | case | " + " | ".join(f"{a} (3 runs)" for a in arms) + " |", "|---|---|" + "---|" * len(arms)]
    def fmt(rs):
        if not rs:
            return "·"
        parts = []
        for r in rs:
            if r.get("failed"):
                parts.append("failed")
                continue
            t = f"{r['gated']:.3f}" + (" AP" if r["allpass"] else "")
            g = ",".join(x.replace("GATE.", "") for x in r["gates"])
            if g:
                t += f" `{g}`"
            if r.get("review"):
                t += " " + "/".join(f"{v}{'✓' if ok else '✗'}" for v, ok in r["review"])
            parts.append(t)
        return " · ".join(parts)
    for m, c in keys:
        L.append(f"| {m} | {CASE_LABEL.get(c, c)} | " + " | ".join(fmt(all_reps.get(a, {}).get((m, c))) for a in arms) + " |")
    return "\n".join(L)


def details(arm: str, coll: dict) -> str:
    """per-cell trajectory table for one arm, plus the usage totals."""
    L = [f"### {arm}: per-cell trajectory\n",
         "| Model | case | terminal | transport | turns | tools | position dates queried | basis date | superseded date | calc | usage total |",
         "|---|---|---:|---|---:|---:|---|---|---|---:|---:|"]
    tot = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    for m in MODELS:
        for c in CASES:
            s = coll["cells"].get((m, c))
            if not s:
                continue
            t = s["trajectory"]["maker"]
            u = (s["run"].get("usage_total") or {})
            for k in tot:
                tot[k] += int(u.get(k) or 0)
            L.append(f"| {m} | {CASE_LABEL[c]} | {_cell_text(s)} | {s['transport']} | {t['n_turns']} | {t['n_tool_calls']} | "
                     f"{', '.join(t['position_dates_queried']) or 'none'} | {t['basis_date_queried']} | {t['superseded_date_queried']} | "
                     f"{t['n_calculate']} | {int(u.get('total_tokens') or 0):,} |")
    L.append(f"\nusage totals ({arm}): prompt {tot['prompt_tokens']:,} · completion {tot['completion_tokens']:,} · total {tot['total_tokens']:,}")
    if arm.startswith("checker"):
        rv_rows = ["", f"### {arm}: reviewer tool use in round 1\n",
                   "| Model | case | verdict | ledger shown correct | reviewer turns | get_position | calculate | read_document | findings |",
                   "|---|---|---|---|---:|---:|---:|---:|---:|"]
        for m in MODELS:
            for c in CASES:
                s = coll["cells"].get((m, c))
                if not s or not s.get("review"):
                    continue
                r1 = s["review"]["rounds"][0]
                rt = (s["trajectory"].get("reviewer") or {}).get("1", {})
                tc = rt.get("tool_counts") or {}
                rv_rows.append(f"| {m} | {CASE_LABEL[c]} | {r1.get('verdict')} | {r1.get('ledger_shown_correct')} | {rt.get('n_turns')} | "
                               f"{tc.get('get_position', 0)} | {tc.get('calculate', 0)} | {tc.get('read_document', 0)} | {len(r1.get('findings') or [])} |")
        L += rv_rows
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--details", action="store_true", help="per-cell trajectory tables and usage totals")
    a = ap.parse_args()
    plain = collect_plain()
    tools = collect("tools")
    checker = collect("checker")
    fixed = collect("checker-fixed") if os.path.isdir(os.path.join(ROOT, "checker-fixed")) else None
    print("## Plain arm (Phase 1, outputs/eval6-live)\n")
    print(grid(plain, plain=True))
    pc = counts(plain, plain=True)
    print(f"\ncells {pc['n']} · AllPass {pc['allpass']} · GATE.ELECT {pc['elect']} · any gate {pc['any_gate']} · mean gated {pc['mean_gated']}\n")
    arms = [("tools", tools), ("checker", checker)] + ([("checker-fixed", fixed)] if fixed else [])
    for arm, coll in arms:
        print(f"## {arm.capitalize()} arm\n")
        print(grid(coll["cells"]))
        c = counts(coll["cells"])
        print(f"\ncells {c['n']} · AllPass {c['allpass']} · GATE.ELECT {c['elect']} · any gate {c['any_gate']} · "
              f"ledger correct {c['ledger_correct']} · worksheet AllPass {c['worksheet_allpass']} · "
              f"mean terminal gated {c['mean_gated']} · mean worksheet gated {c['mean_worksheet_gated']} · "
              f"incomplete {c['incomplete']} · flags {c['flags']} · transport {c['transport']}")
        print(f"trajectory: governing read before first action {c['governing_read_before_first_action']} · "
              f"basis date queried {c['basis_date_queried']} · superseded date queried {c['superseded_date_queried']} · "
              f"any position query {c['any_position_query']} · calculate used {c['calculate_used']} · "
              f"mean turns {c['mean_turns']} · mean tool calls {c['mean_tool_calls']} · tool errors {c['tool_errors']} · "
              f"transient retries {c['transient_retries']}")
        if coll["failed"]:
            print(f"FAILED cells (excluded): {[(f['model'], f['case'], f['failed'][:80]) for f in coll['failed']]}")
        print()
    tts = {}
    for arm, coll in arms[1:]:
        tt = two_by_two(coll["cells"])
        tts[arm] = tt
        print(f"## Reviewer two-by-two, {arm} (round 1: verdict x the ledger it was shown)\n")
        print("| | ledger wrong | ledger correct |\n|---|---:|---:|")
        print(f"| reject | {tt['counts']['reject_wrong']} | {tt['counts']['reject_correct']} |")
        print(f"| approve | {tt['counts']['approve_wrong']} | {tt['counts']['approve_correct']} |")
        print(f"\nno verdict: {tt['counts']['no_verdict']} · recomputed in round 1: {tt['recomputed'][0]}/{tt['recomputed'][1]} · "
              f"revisions: {len(tt['revised'])} · wrong ledgers fixed by a revision: {len(tt['fixed_by_revision'])}")
        for k in ("reject_wrong", "approve_wrong", "reject_correct", "no_verdict"):
            if tt["cells"][k]:
                print(f"- {k}: {tt['cells'][k]}")
        print()
    print("## Repeatability (the corrected dividend, three runs per cell)\n")
    rep_arms = ["plain", "tools", "checker"] + (["checker-fixed"] if fixed else [])
    all_reps = {arm: repeats(arm) for arm in rep_arms}
    print(repeats_table(all_reps, rep_arms))
    if a.details:
        print("\n## Details\n")
        for arm, coll in arms:
            print(details(arm, coll))
            print()
    if a.json:
        def _k(d):
            return {f"{m}/{c}": v for (m, c), v in d.items()}
        payload = {"plain": _k(plain), "failed": {}, "counts": {"plain": pc}, "two_by_two": {},
                   "repeats": {arm: _k(v) for arm, v in all_reps.items()}}
        for arm, coll in arms:
            payload[arm] = _k(coll["cells"])
            payload["failed"][arm] = coll["failed"]
            payload["counts"][arm] = counts(coll["cells"])
        for arm, tt in tts.items():
            payload["two_by_two"][arm] = {"counts": tt["counts"], "recomputed": tt["recomputed"],
                                          "cells": {k: [f"{m}/{c}" for m, c in v] for k, v in tt["cells"].items()},
                                          "revised": [f"{m}/{c}" for m, c in tt["revised"]],
                                          "fixed_by_revision": [f"{m}/{c}" for m, c in tt["fixed_by_revision"]]}
        p = os.path.join(ROOT, "summary.json")
        with open(p, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(payload, fh, indent=2, default=str)
        print(f"\n(summary written to {os.path.relpath(p, REPO)})")


if __name__ == "__main__":
    main()

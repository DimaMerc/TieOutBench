"""harness/profiles.py — machine-readable capability profiles from the committed live runs.

Walks the committed frontier artifacts (evals #3-#5, outputs/eval{3,4,5}-live/**/answer.json),
re-grades each answer through the deterministic mock-judge path — the exact path that produced the
committed report.txt files — and emits structured JSON under profiles/:

    profiles/scores.json     the whole grid in one file (every run, every checkpoint)
    profiles/<model>.json    one model's profile: its runs + a small summary

The point: the leaderboard is prose; a capability profile is data. Per-checkpoint scores are
routing priors — *which workflow step* a model can be trusted with, not just its blended average.
A deployment (or a due-diligence reviewer) can read profiles/scores.json and answer "which model
touches the extraction step, and what happens at the decision step?" without parsing report text.

Scope is deliberately the deterministic grid only: evals #3-#6, eight models, six case-columns.
Eval #6 rows carry an `arm` field: `plain` for the Phase-1 runs (outputs/eval6-live), `tools` and
`checker` for the Phase-2 agent-environment runs (outputs/eval6-agent), which are scored on their
terminal state (worksheet + ledger) through harness/env/scoring.py. The `summary` block counts the
plain arm only, so the published Phase-1 numbers do not move when agent runs land; `summary_by_arm`
carries the same counts per arm.
Evals #1-#2 open-weight runs were scored with a live LLM judge on the free-form atoms; an offline
regrade would not reproduce their published numbers, so they are excluded rather than approximated.

Regeneration is byte-stable: no timestamps, sorted keys, scores from the same graders that wrote
the committed reports. `python -m harness profiles` rebuilds the directory; a diff against the
committed profiles is a regression check that the grader still reproduces every published number.
"""
from __future__ import annotations
import glob
import json
import os

from . import run_case, REPO

OUT_DIR = os.path.join(REPO, "profiles")

SCHEMA_VERSION = "1.0"

EVAL_OF_SUITE = {"dcf-valuation": 3, "creation-redemption": 4, "confirmation-matching": 5,
                 "corporate-actions": 6}

# provenance the numbers cannot carry on their own (mirrors LEADERBOARD.md scope notes)
NOTES = [
    "Scores are re-graded offline from the committed answer.json artifacts via the deterministic "
    "mock-judge path — the same path that produced the committed report.txt files. No API calls.",
    "One run per model per case; scores are point-in-time for the model versions named. "
    "This grid does not rank models and reports no single blended number per model on purpose.",
    "Completion budgets differed by vendor where required for parity (GPT DCF runs 32k, Gemini 32k "
    "throughout, Claude 12-16k on DCF, 8k elsewhere); see LEADERBOARD.md 'Scope notes'.",
    "The NVDA DCF runs used the case-hardened v2 system prompt; the MCD runs predate it. "
    "Cross-case comparisons on the netting-convention and grid-geometry behaviors are hedged in "
    "outputs/eval3-live/nvda-fy2026-dcf/TAXONOMY.md.",
    "gates_fired lists auto-fail conditions that collapsed the gated score; an empty list plus a "
    "high gated score is the deployable signal, a high UNGATED score alone is not.",
    "Rows carry an `arm` field. `plain` is the single-prompt run (every eval; the Phase-1 form of "
    "eval #6). `tools` and `checker` are eval #6 Phase-2 agent-environment runs scored on the terminal "
    "state (worksheet + ledger); their `worksheet_score_gated` is the arm-comparable number and "
    "`ledger` records what was booked. `summary` counts the plain arm only.",
]


def _vendor(model: str) -> str:
    if model.startswith("claude"):
        return "anthropic"
    if model.startswith("gpt"):
        return "openai"
    if model.startswith("gemini"):
        return "google"
    return "unknown"


def _rel(path: str) -> str:
    return os.path.relpath(path, REPO).replace(os.sep, "/")


def discover():
    """Yield (model, case_id, answer_path, arm) for every committed frontier run (evals #3-#6)."""
    runs = []
    e3 = os.path.join(REPO, "outputs", "eval3-live")
    for p in glob.glob(os.path.join(e3, "*", "answer.json")):
        runs.append((os.path.basename(os.path.dirname(p)), "mcd-fy2025-dcf", p, "plain"))
    for p in glob.glob(os.path.join(e3, "nvda-fy2026-dcf", "*", "answer.json")):
        runs.append((os.path.basename(os.path.dirname(p)), "nvda-fy2026-dcf", p, "plain"))
    for ev in ("eval4-live", "eval5-live", "eval6-live"):
        for p in glob.glob(os.path.join(REPO, "outputs", ev, "*", "*", "answer.json")):
            case_id = os.path.basename(os.path.dirname(p))
            model = os.path.basename(os.path.dirname(os.path.dirname(p)))
            runs.append((model, case_id, p, "plain"))
    for arm in ("tools", "checker", "checker-fixed"):
        for p in glob.glob(os.path.join(REPO, "outputs", "eval6-agent", arm, "*", "*", "answer.json")):
            case_id = os.path.basename(os.path.dirname(p))
            model = os.path.basename(os.path.dirname(os.path.dirname(p)))
            if os.path.exists(os.path.join(os.path.dirname(p), "ledger.json")):
                runs.append((model, case_id, p, arm))
    return sorted(runs)


def grade_run(model: str, case_id: str, answer_path: str, arm: str = "plain") -> dict:
    """Re-grade one committed answer through the deterministic path; return the run record.
    Agent-arm cells are scored on their terminal state (worksheet + ledger) by the environment
    scorer; the worksheet-only score rides along as `worksheet_score_gated`."""
    from .rubric import load_case, suite_of
    case_path = os.path.join(REPO, "cases", case_id + ".case.yaml")
    extra = {}
    if arm == "plain":
        with open(answer_path, encoding="utf-8") as fh:
            answer = json.load(fh)
        result, rubric = run_case(case_path, model_output=answer, mode="mock")
    else:
        from .env.state import Episode
        from .env.scoring import score_episode
        ep = Episode.load(os.path.dirname(answer_path), case_path)
        scored = score_episode(ep)
        _ws, result, rubric = scored["results"]
        extra = {"worksheet_score_gated": scored["worksheet"]["gated"],
                 "worksheet_allpass": scored["worksheet"]["allpass"],
                 "ledger": {k: scored["ledger"][k] for k in ("correct", "elect_fired", "gold_ok", "flags", "n_booked")},
                 "incomplete": scored["incomplete"],
                 "review": ([{k: r.get(k) for k in ("round", "verdict", "ledger_shown_correct")}
                             for r in scored["review"]["rounds"]] if scored.get("review") else None)}
    suite = suite_of(load_case(case_path))
    cpw = rubric["meta"]["checkpoint_weights"]
    R, G = result.e6
    rcp = result.refusal_cp
    return {
        "eval": EVAL_OF_SUITE[suite],
        "arm": arm,
        "suite": suite,
        "case_id": case_id,
        "case": _rel(case_path),
        "answer": _rel(answer_path),
        "score_gated": round(result.case_gated, 4),
        "score_ungated": round(result.case_ungated, 4),
        "gap": round(result.gap, 4),
        "allpass": result.allpass,
        "gates_fired": list(result.fired_gates),
        "headline_flags": list(result.flags),
        "refusal": {
            "checkpoint": rcp,
            "recall": round(R, 4),
            "groundedness": round(G, 4),
            "f_beta": round(result.checkpoints[rcp]["raw_unclipped"], 4),
        },
        "checkpoints": {
            k: {
                "weight": round(cpw[k], 4),
                "ungated": round(result.checkpoints[k]["score_ungated"], 4),
                "gated": round(result.checkpoints[k]["score_gated"], 4),
            }
            for k in cpw
        },
        "categories": {t: round(v, 4) for t, v in result.categories.items()},
        **extra,
    }


def build():
    """Grade every committed run and return {model: profile-dict}, sorted and JSON-ready."""
    by_model: dict[str, list] = {}
    for model, case_id, path, arm in discover():
        by_model.setdefault(model, []).append(grade_run(model, case_id, path, arm))
    profiles = {}
    for model in sorted(by_model):
        runs = sorted(by_model[model], key=lambda r: (r["eval"], r["arm"] != "plain", r["arm"], r["case_id"]))

        def _summary(rows):
            gates: dict[str, list] = {}
            for r in rows:
                for g in r["gates_fired"]:
                    gates.setdefault(g, []).append(r["case_id"])
            return {"n_runs": len(rows), "n_allpass": sum(r["allpass"] for r in rows), "gates_fired": gates,
                    "score_gated_by_case": {r["case_id"]: r["score_gated"] for r in rows}}
        plain = [r for r in runs if r["arm"] == "plain"]
        arms = sorted({r["arm"] for r in runs})
        profiles[model] = {
            "schema_version": SCHEMA_VERSION,
            "benchmark": "TieOutBench",
            "model": model,
            "vendor": _vendor(model),
            "source": "https://github.com/DimaMerc/TieOutBench",
            "notes": NOTES,
            "runs": runs,
            "summary": _summary(plain),
            "summary_by_arm": {arm: _summary([r for r in runs if r["arm"] == arm]) for arm in arms},
        }
    return profiles


def write(profiles: dict) -> list:
    """Write profiles/<model>.json + profiles/scores.json; return the written paths."""
    os.makedirs(OUT_DIR, exist_ok=True)
    written = []
    for model, prof in profiles.items():
        p = os.path.join(OUT_DIR, model + ".json")
        with open(p, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(prof, fh, indent=2, sort_keys=True)
            fh.write("\n")
        written.append(p)
    grid = {
        "schema_version": SCHEMA_VERSION,
        "benchmark": "TieOutBench",
        "source": "https://github.com/DimaMerc/TieOutBench",
        "notes": NOTES,
        "models": {m: {"vendor": prof["vendor"], "runs": prof["runs"], "summary": prof["summary"]}
                   for m, prof in profiles.items()},
    }
    p = os.path.join(OUT_DIR, "scores.json")
    with open(p, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(grid, fh, indent=2, sort_keys=True)
        fh.write("\n")
    written.append(p)
    return written


def render_grid(profiles: dict) -> str:
    """Compact stdout grid: models x cases, gated score + fired gates."""
    cases = sorted({r["case_id"] for prof in profiles.values() for r in prof["runs"]},
                   key=lambda c: (min(r["eval"] for p in profiles.values()
                                      for r in p["runs"] if r["case_id"] == c), c))
    w = max(len(m) for m in profiles) + 2
    L = ["  " + "model".ljust(w) + "  ".join(c[:18].ljust(18) for c in cases)]
    for m, prof in profiles.items():
        by_case = {r["case_id"]: r for r in prof["runs"]}
        cells = []
        for c in cases:
            r = by_case.get(c)
            if r is None:
                cells.append("-".ljust(18))
                continue
            s = f"{r['score_gated']:.3f}"
            if r["gates_fired"]:
                s += " " + ",".join(g.replace("GATE.", "") for g in r["gates_fired"])
            cells.append(s[:18].ljust(18))
        L.append("  " + m.ljust(w) + "  ".join(cells))
    return "\n".join(L)

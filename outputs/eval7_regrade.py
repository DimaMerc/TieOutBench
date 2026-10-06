#!/usr/bin/env python3
"""
outputs/eval7_regrade.py — re-grade every saved eval-#7 live run OFFLINE from its answer.json (no model
call, no key), rewrite report.txt, and record the re-grade in run.json: the score written at run time is
kept under `score_at_run` (first re-grade only) and `regrades` gets an entry {at, reason, score}. Used
when a grader calibration changes after the runs (the citation alternates of 2026-10-05).

  python outputs/eval7_regrade.py --reason "accept the totals block as an entailing E1 citation"
"""
from __future__ import annotations
import argparse
import glob
import json
import os
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
from harness import run_case                 # noqa: E402
from harness.report import render            # noqa: E402

LIVE = os.path.join(REPO, "outputs", "eval7-live")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reason", required=True)
    a = ap.parse_args()
    for ans_path in sorted(glob.glob(os.path.join(LIVE, "*", "*", "answer.json"))):
        d = os.path.dirname(ans_path)
        model, case = os.path.basename(os.path.dirname(d)), os.path.basename(d)
        case_path = os.path.join(REPO, "cases", case + ".case.yaml")
        ans = json.load(open(ans_path, encoding="utf-8"))
        result, rubric = run_case(case_path, model_output=ans, mode="mock")
        with open(os.path.join(d, "report.txt"), "w", encoding="utf-8") as fh:
            fh.write(render(result, rubric, variant=f"live:{model}", mode="mock"))
        score = {"gated": result.case_gated, "ungated": result.case_ungated, "gap": result.gap,
                 "allpass": result.allpass, "gates": result.fired_gates, "flags": result.flags}
        rj = os.path.join(d, "run.json")
        if os.path.exists(rj):
            rec = json.load(open(rj, encoding="utf-8"))
            old = rec.get("score")
            if "score_at_run" not in rec:
                rec["score_at_run"] = old
            rec.setdefault("regrades", []).append({"at": time.strftime("%Y-%m-%dT%H:%M:%S"), "reason": a.reason,
                                                   "score_before": old, "score": score})
            rec["score"] = score
            with open(rj, "w", encoding="utf-8") as fh:
                json.dump(rec, fh, indent=2, default=str)
            moved = (old or {}).get("gated") != score["gated"]
        else:
            moved = None
        print(f"{model:<28} {case:<22} gated={score['gated']:.3f} AllPass={score['allpass']} gates={score['gates']}"
              + ("   <- moved" if moved else ""))


if __name__ == "__main__":
    main()

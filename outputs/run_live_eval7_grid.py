#!/usr/bin/env python3
"""
outputs/run_live_eval7_grid.py — run the suite's eight-model, three-vendor grid through both eval-#7
cases, sequentially, via outputs/run_live_eval7.py. One summary line per run is appended to
outputs/eval7-live/_grid.log; a failed run is logged and skipped, never retried silently.

  python outputs/run_live_eval7_grid.py [--only claude-haiku-4-5-20251001,gpt-5.4] [--skip-existing]

Keys are resolved by the harness from the endpoint (environment or the gitignored .env) and are
never printed.
"""
from __future__ import annotations
import argparse
import os
import re
import subprocess
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GRID = [  # (endpoint, model_id) — the LEADERBOARD grid, unchanged
    ("https://api.anthropic.com/v1", "claude-opus-4-8"),
    ("https://api.anthropic.com/v1", "claude-sonnet-4-6"),
    ("https://api.anthropic.com/v1", "claude-haiku-4-5-20251001"),
    ("https://api.openai.com/v1", "gpt-5.6-sol"),
    ("https://api.openai.com/v1", "gpt-5.5"),
    ("https://api.openai.com/v1", "gpt-5.4"),
    ("https://api.openai.com/v1", "gpt-5.4-mini"),
    ("https://generativelanguage.googleapis.com/v1beta/openai", "gemini-3.6-flash"),
]
CASES = ["grsl-nav-2026", "grsl-nav-2026-clean"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default=None, help="comma-separated model ids to run (default: all eight)")
    ap.add_argument("--skip-existing", action="store_true", help="skip a model/case that already has a report.txt")
    ap.add_argument("--max-tokens", type=int, default=8000)
    a = ap.parse_args()
    only = set(a.only.split(",")) if a.only else None
    logdir = os.path.join(REPO, "outputs", "eval7-live")
    os.makedirs(logdir, exist_ok=True)
    log = open(os.path.join(logdir, "_grid.log"), "a", encoding="utf-8")

    def say(line):
        print(line, flush=True)
        log.write(line + "\n"); log.flush()

    say(f"=== grid start {time.strftime('%Y-%m-%d %H:%M:%S')} ===")
    for endpoint, model in GRID:
        if only and model not in only:
            continue
        for case in CASES:
            outdir = os.path.join(logdir, model.replace("/", "_"), case)
            if a.skip_existing and os.path.exists(os.path.join(outdir, "report.txt")):
                say(f"skip (exists): {model} {case}")
                continue
            cmd = [sys.executable, os.path.join(REPO, "outputs", "run_live_eval7.py"), "--model-id", model,
                   "--endpoint", endpoint, "--case", case, "--max-tokens", str(a.max_tokens)]
            t0 = time.time()
            p = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True, encoding="utf-8", errors="replace")
            out = p.stdout + p.stderr
            m = re.search(r"\[live\] (\S+) \((\S+)\): gated=([0-9.]+) ungated=([0-9.]+) GAP=([0-9.]+) AllPass=(\d) "
                          r"gates=(\[[^\]]*\]) flags=(\[[^\]]*\]) D2\(R,G\)=\(([^)]*)\)", out)
            if p.returncode == 0 and m:
                say(f"{model:<28} {case:<22} gated={m.group(3)} ungated={m.group(4)} GAP={m.group(5)} "
                    f"AllPass={m.group(6)} gates={m.group(7)} flags={m.group(8)} D2={m.group(9)}  ({time.time()-t0:.0f}s)")
            else:
                tail = "\n".join(out.strip().splitlines()[-6:])
                say(f"{model:<28} {case:<22} FAILED rc={p.returncode} ({time.time()-t0:.0f}s)\n{tail}")
    say(f"=== grid end {time.strftime('%Y-%m-%d %H:%M:%S')} ===")
    log.close()


if __name__ == "__main__":
    main()

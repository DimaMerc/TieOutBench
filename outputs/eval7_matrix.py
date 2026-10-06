#!/usr/bin/env python3
"""
outputs/eval7_matrix.py — compile the eval-#7 live grid from the saved artifacts (report.txt + answer.json
under outputs/eval7-live/<model>/<case>/) into the matrix table and a per-run diagnostic line. Offline;
re-runnable after any re-grade. Prints markdown.
"""
from __future__ import annotations
import glob
import json
import os
import re

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIVE = os.path.join(REPO, "outputs", "eval7-live")
ORDER = ["claude-opus-4-8", "claude-sonnet-4-6", "claude-haiku-4-5-20251001", "gpt-5.6-sol", "gpt-5.5", "gpt-5.4",
         "gpt-5.4-mini", "gemini-3.6-flash"]
CASES = ["grsl-nav-2026", "grsl-nav-2026-clean"]


def parse_report(path):
    txt = open(path, encoding="utf-8").read()
    g = lambda pat: (re.search(pat, txt) or [None, None])[1]
    cps = dict(re.findall(r"^\s+(P1|E1|E2|C1|C2|C3|D1|D2)\s+[0-9.]+\s+([0-9.]+)\s+[0-9.]+", txt, flags=re.M))
    # the vector prints "cp W ungated gated raw": capture gated (3rd number)
    cps_g = {}
    for m in re.finditer(r"^\s+(P1|E1|E2|C1|C2|C3|D1|D2)\s+([0-9.]+)\s+([0-9.]+)\s+([0-9.]+)", txt, flags=re.M):
        cps_g[m.group(1)] = float(m.group(4))
    return {
        "gated": float(g(r"CaseScore \(gated, headline\) : ([0-9.]+)") or 0),
        "ungated": float(g(r"CaseScore \(ungated\)\s+: ([0-9.]+)") or 0),
        "allpass": int(g(r"AllPass\s+: (\d)") or 0),
        "gates": (g(r"Gates fired\s+: (.+)") or "none").strip(),
        "flags": (g(r"Headline flags\s+: (.+)") or "").strip(),
        "d2": (g(r"D2 calibration \(R,G->F_b\)\s+: (.+)") or "").strip(),
        "cps": cps_g,
    }


def main():
    rows = {}
    for model in ORDER:
        for case in CASES:
            d = os.path.join(LIVE, model, case)
            rp, ap = os.path.join(d, "report.txt"), os.path.join(d, "answer.json")
            if not os.path.exists(rp):
                continue
            r = parse_report(rp)
            a = json.load(open(ap, encoding="utf-8")) if os.path.exists(ap) else {}
            r["answer"] = a
            rows[(model, case)] = r
    print("| Model | Break case (gated) | Gate / flag | Clean case (gated) | False hold? |")
    print("|---|---:|---|---:|---|")
    for model in ORDER:
        b, c = rows.get((model, CASES[0])), rows.get((model, CASES[1]))
        if not b and not c:
            continue
        bg = f"{b['gated']:.3f}" + (" AP" if b and b["allpass"] else "") if b else "-"
        gate = (b["gates"] + (f" ({b['flags']})" if b["flags"] else "")) if b else "-"
        cg = f"{c['gated']:.3f}" + (" AP" if c and c["allpass"] else "") if c else "-"
        fh = "-"
        if c:
            dec = str(c["answer"].get("D1", {}).get("decision", ""))
            fh = "no (RELEASE)" if "RELEASE" in dec.upper() and "NOT" not in dec.upper() else f"**{dec}**"
        print(f"| {model} | {bg} | {gate} | {cg} | {fh} |")
    print()
    print("Per-run diagnostics (checkpoint gated scores; decision; error; probe):")
    for (model, case), r in rows.items():
        a = r["answer"]
        d1, c3, d2 = a.get("D1", {}), a.get("C3", {}), a.get("D2", {}).get("probe", {})
        low = {k: v for k, v in r["cps"].items() if v < 0.999}
        print(f"- {model} / {case}: gated {r['gated']:.3f} ungated {r['ungated']:.3f} AllPass {r['allpass']} "
              f"gates {r['gates']}{(' flags ' + r['flags']) if r['flags'] else ''}; D2 {r['d2']}; below-1 checkpoints {low}; "
              f"decision={d1.get('decision')!r} class={d1.get('classification')!r} line={d1.get('offending_line')!r} "
              f"err/sh={d1.get('nav_error_per_share')} corrected={d1.get('corrected_nav_per_share')} "
              f"reproc={d1.get('reprocessing_required')}; C3 err={c3.get('nav_error_per_share')} pct={c3.get('nav_error_pct')} "
              f"dir={c3.get('direction')} admin_move={c3.get('admin_move_pct')} dev={c3.get('admin_deviation_pp')} "
              f"flag={c3.get('reasonableness_flag')}; probe label={d2.get('label')} value={d2.get('value')}")


if __name__ == "__main__":
    main()

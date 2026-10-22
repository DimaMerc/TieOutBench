#!/usr/bin/env python3
"""
outputs/eval8_matrix.py — compile the eval-#8 live grid from the saved artifacts (report.txt + answer.json
under outputs/eval8-live/<model>/<case>/) into the matrix table and a per-run diagnostic line. Offline;
re-runnable after any re-grade. Prints markdown.
"""
from __future__ import annotations
import json
import os
import re

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIVE = os.path.join(REPO, "outputs", "eval8-live")
ORDER = ["claude-opus-4-8", "claude-sonnet-4-6", "claude-haiku-4-5-20251001", "gpt-5.6-sol", "gpt-5.5", "gpt-5.4",
         "gpt-5.4-mini", "gemini-3.6-flash"]
CASES = ["grbo-redeem-2026", "grbo-redeem-2026-clean"]


def parse_report(path):
    txt = open(path, encoding="utf-8").read()
    g = lambda pat: (re.search(pat, txt) or [None, None])[1]
    cps_g = {}
    for m in re.finditer(r"^\s+(P1|E1|E2|C1|C2|C3|D1|D2)\s+([0-9.]+)\s+([0-9.]+)\s+([0-9.]+)", txt, flags=re.M):
        cps_g[m.group(1)] = float(m.group(4))     # the vector prints "cp W ungated gated raw": gated = 3rd number
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
            dec = str((c["answer"].get("D1") or {}).get("decision", ""))
            up = dec.upper()
            fh = "no (SETTLE)" if "SETTLE" in up and "NOT" not in up and "HOLD" not in up else f"**{dec}**"
        print(f"| {model} | {bg} | {gate} | {cg} | {fh} |")
    print()
    print("Per-run diagnostics (checkpoint gated scores; decision; break; probe):")
    for (model, case), r in rows.items():
        a = r["answer"]
        d1, c2, c3 = a.get("D1") or {}, a.get("C2") or {}, a.get("C3") or {}
        d2 = (a.get("D2") or {}).get("probe") or {}
        low = {k: v for k, v in r["cps"].items() if v < 0.999}
        print(f"- {model} / {case}: gated {r['gated']:.3f} ungated {r['ungated']:.3f} AllPass {r['allpass']} "
              f"gates {r['gates']}{(' flags ' + r['flags']) if r['flags'] else ''}; D2 {r['d2']}; below-1 checkpoints {low}; "
              f"decision={d1.get('decision')!r} leg={d1.get('offending_leg')!r} due={d1.get('due_contracts')} "
              f"confirmed={d1.get('confirmed_contracts')} excess={d1.get('excess_contracts')} excess_value={d1.get('excess_value')}; "
              f"C2 cash/cu={c2.get('cash_component_per_cu')} net={c2.get('net_cash_to_ap')} ties={c2.get('cash_ties')}; "
              f"C3 excess={c3.get('excess_contracts')} dir={c3.get('direction')!r} harmed={c3.get('harmed')!r} "
              f"impact/sh={c3.get('impact_per_remaining_share')} pct={c3.get('impact_pct_of_nav')}; "
              f"probe label={d2.get('label')} value={d2.get('value')}")


if __name__ == "__main__":
    main()

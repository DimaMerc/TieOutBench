"""Commands for the derivative-specification experiment.

  python run.py scenarios [fund]   write the scenarios with their expected results and print them
  python run.py given [fund]       write the inputs and questions only (for a reader or a model)
  python run.py rules [fund]       print the rules with the public passage behind each
  python run.py gaps [fund]        count what the public documents settle: rules, expected figures, scenarios

fund = swap (default; files data/out/scenarios.json, scenarios_given.json, gaps.json)
     | options (files data/out/scenarios_options.json, scenarios_given_options.json, gaps_options.json)
"""
from __future__ import annotations

import json
import os
import sys

from ds import standard
from ds.funds import FUNDS, kind_counts

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data", "out")
KEEP = 3   # result files keep three more digits than a report would quote (cents -> 5 decimals)


def stored(x):
    return round(x, 2 + KEEP) if isinstance(x, float) else x


def write(name: str, obj) -> str:
    os.makedirs(OUT, exist_ok=True)
    p = os.path.join(OUT, name)
    with open(p, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(obj, fh, indent=1)
    return p


def gaps(fund: str, sc: list[dict]) -> dict:
    rules = FUNDS[fund]["rules"]
    per = []
    for s in sc:
        fields = {k: rules.settled(r) for k, r in s["needs"].items()}
        open_rules = sorted({x for r in s["needs"].values() for x in r if rules.is_open(x)})
        per.append({"id": s["id"], "title": s["title"], "figures": len(fields), "settled": sum(fields.values()),
                    "all_settled": all(fields.values()), "open_rules": open_rules})
    return {"rules": rules.counts(),
            "figures": sum(p["figures"] for p in per), "figures_settled": sum(p["settled"] for p in per),
            "scenarios": len(per), "scenarios_all_settled": sum(p["all_settled"] for p in per),
            "scenarios_none_settled": sum(p["settled"] == 0 for p in per), "per_scenario": per}


def header(fund: str) -> dict:
    S = FUNDS[fund]["scenarios"]
    return {"fund": S.FUND, "confirmation": S.CONFIRMATION} if fund == "swap" else {"fund": S.FUND, "conventions": S.CONVENTIONS}


def main(argv: list[str]) -> int:
    cmd = argv[1] if len(argv) > 1 else ""
    fund = argv[2] if len(argv) > 2 else "swap"
    if fund not in FUNDS:
        print(__doc__)
        return 2
    F, sfx = FUNDS[fund], FUNDS[fund]["suffix"]
    rules = F["rules"]
    sc = F["scenarios"].build()
    if cmd == "scenarios":
        for s in sc:
            s["expected"] = {k: stored(v) for k, v in s["expected"].items()}
            print(f"{s['id']} {s['title']}")
            for k, v in s["expected"].items():
                tag = "" if rules.settled(s["needs"][k]) else "   not settled"
                print((f"      {k:<48} {v:>20,.5f}" if isinstance(v, float) else f"      {k:<48} {v!s:>20}") + tag)
        print("wrote", write(f"scenarios{sfx}.json", {**header(fund), "scenarios": sc}))
    elif cmd == "given":
        g = [{"id": s["id"], "title": s["title"], "given": s["given"], "ask": s["ask"], "answer_fields": list(s["expected"])} for s in sc]
        print("wrote", write(f"scenarios_given{sfx}.json", {**header(fund), "scenarios": g}))
    elif cmd == "rules":
        for rid, r in rules.RULES.items():
            print(f"{rid} [{r['kind']:<12}] {rules.status(rid):<10} {r['text']}")
            if r.get("missing"):
                print(f"      missing: {r['missing']}")
        print(json.dumps(rules.counts()))
    elif cmd == "gaps":
        g = gaps(fund, sc)
        c = kind_counts(fund)
        print(f"fund: {F['label']}")
        print(f"rules the fund's documents should state: {c['fund_rules']} -> stated {c['fund_specified']}, "
              f"partly {c['fund_partly']}, absent {c['fund_absent']}")
        print(f"{F['other_kind'][1]}: {c['other_rules']} -> {F['other_kind'][2]} {c['other_specified']}")
        print(f"expected figures: {g['figures']} -> settled by the documents {g['figures_settled']}")
        print(f"scenarios: {g['scenarios']} -> every figure settled {g['scenarios_all_settled']}, "
              f"no figure settled {g['scenarios_none_settled']}")
        for p in g["per_scenario"]:
            print(f"  {p['id']} {p['settled']}/{p['figures']}  open: {', '.join(p['open_rules']) or '-'}   {p['title']}")
        print("standard:", standard.NAME)
        print("wrote", write(standard.tag(f"gaps{sfx}.json"), g))
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

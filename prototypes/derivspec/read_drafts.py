"""Print what has to be read by hand before a score is trusted.

  python read_drafts.py <fund> wrong       every settled figure a draft got wrong or left without a number, with its words
  python read_drafts.py <fund> open        every unsettled figure: value, how it was presented and the words, per run
  python read_drafts.py <fund> between     unsettled figures on which the models' plain numbers differ
  python read_drafts.py <fund> runs        figures whose value or presentation changes between the runs of one cell
  python read_drafts.py <fund> conflict    sentences of the drafts that mention a difference between the documents
Reads data/out/scores_<fund>.json (run score_drafts.py first) and, for `conflict`, the raw answers.
"""
from __future__ import annotations

import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data", "out")
SAYS = re.compile(r"inconsisten|conflict|contradict|discrepan|differs? from|different (rule|method|basis|approach)|does not match|"
                  r"whereas the (sai|prospectus|annual)|while the (sai|prospectus|annual)|not consistent|at odds", re.I)


def fmt(v) -> str:
    return "none" if v is None else (f"{v:,.2f}" if abs(v) >= 1000 else f"{v:g}")


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print(__doc__)
        return 2
    fund, what = argv[1], argv[2]
    with open(os.path.join(OUT, f"scores_{fund}.json"), encoding="utf-8") as fh:
        res = json.load(fh)
    if what == "wrong":
        n = 0
        for r in res["runs"]:
            for x in r["rows"]:
                if x["settled"] and not x["same_as_reference"]:
                    if "rest" in argv[3:] and x.get("reference_figure_in_words"):
                        continue                       # `wrong rest`: only those whose own words do not carry the figure
                    n += 1
                    tag = "=note" if x.get("reference_figure_in_words") else "     "
                    print(f"{r['arm']:<6}{r['model']:<18}run{r['run']} {x['scenario']}.{x['field']:<46} expected {fmt(x['expected']):>16}  "
                          f"got {fmt(x['value']):>16} {tag} [{x['how']}] {x['words'][:300]}")
        print(f"{n} settled figures not matched")
    elif what == "open":
        for r in res["runs"]:
            for x in r["rows"]:
                if not x["settled"]:
                    print(f"{r['arm']:<6}{r['model']:<18}run{r['run']} {x['scenario']}.{x['field']:<24} ref {fmt(x['expected']):>15} got {fmt(x['value']):>15} "
                          f"{x['how']:<20} {x['words'][:170]}")
    elif what == "between":
        for d in res["plain_values_that_differ_between_models"]:
            print(f"{d['scenario']}.{d['field']}")
            for m, vals in d["values"].items():
                print(f"      {m:<18} " + "  ".join(fmt(v) for v in vals))
    elif what == "runs":
        for c in res["cells"]:
            for d in c["differing"]:
                print(f"{c['arm']:<6}{c['model']:<18}{d['scenario']}.{d['field']:<44} {'settled' if d['settled'] else 'open':<8} "
                      f"values {[fmt(v) for v in d['values']]} how {d['how']}")
    elif what == "conflict":
        base = os.path.join(OUT, "drafts", fund)
        for arm in sorted(os.listdir(base)):
            for model in sorted(os.listdir(os.path.join(base, arm))):
                for run in sorted(os.listdir(os.path.join(base, arm, model))):
                    with open(os.path.join(base, arm, model, run, "raw.txt"), encoding="utf-8") as fh:
                        raw = fh.read()
                    hits = [s.strip() for s in re.split(r'(?<=[.;])\s+|",\s*"', raw) if SAYS.search(s)]
                    print(f"{arm:<6}{model:<18}{run}: {len(hits)} sentence(s)")
                    for h in hits[:6]:
                        print("      " + h[:300])
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

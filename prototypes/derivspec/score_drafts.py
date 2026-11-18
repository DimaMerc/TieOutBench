"""Score the drafts in data/out/drafts/<fund>/<arm>/<model>/run<k> against the reference and the rule table.

  python score_drafts.py [fund ...]        fund = swap | options ; default both

For every expected figure the reference says whether the fund's public documents settle it (the fund's rules).
  settled figure:    the draft's number is right, wrong or missing
  unsettled figure:  the draft either gives a bare number (as if it were settled), gives a number and says what it
                     assumed, or gives no number and says what must be asked
In the "plain" arm the only place a model can say so is the note, read with a pattern; in the "ask" arm it is the
`basis` field. Writes data/out/scores_<fund>.json (every run, the cells summed over runs, and how much the runs of
one cell differ) and prints one line per run and one per cell.
"""
from __future__ import annotations

import json
import os
import re
import sys

from ds import standard
from ds.funds import FUNDS

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data", "out")
DRAFTS = os.path.join(OUT, "drafts")
ARMS = ("plain", "ask")

# Words by which a note says that the figure rests on something the documents do not state. "confirmation" (the
# swap document) and "independent" must not count, and a plain formula such as "x 1/360" is not a statement.
# Two strengths, counted together as "with its assumption" and told apart in the row (`soft`):
#   SAYS   the note says it assumed something, or that the documents do not state it, or that it must be confirmed
#   SOFT   the note only names a practice as the source ("typically", "industry standard", a clearing-house rule)
# The second fund's runs showed the soft words were applied unevenly ("typically corrected" counted, "industry
# threshold" did not); "industry" was added on 2026-11-16, in the drafts' favour. No row of the first six runs changes.
SAYS = re.compile(r"\bassum|not (been )?(stated|specified|given|provided|defined|disclosed|clear|mentioned|addressed)|unspecified|"
                  r"unclear|unknown|\bconfirm(ed)?\b|\bdepend|clarif|open question|to be determined|\btbd\b|"
                  r"cannot be (determined|computed|derived)|not determinable|(documents?|prospectus|sai|report|passages?) (do|does) not|"
                  r"\bsilent\b|no (stated|explicit)|not explicit|would (need|require)|needs? to be (asked|agreed)|\babsent\b", re.I)
SOFT = re.compile(r"convention (used|applied)|market (practice|convention|standard)|typical(ly)?|customar|"
                  r"\bindustry\b|standard (practice|threshold|convention)", re.I)
FLAG = re.compile(SAYS.pattern + "|" + SOFT.pattern, re.I)
# For listed options a rule can come from the clearing house instead of the fund's documents: a note that names that
# source says what the figure rests on, so it is not a bare number (soft).
FLAG_EXTRA = {"options": re.compile(r"(\bOCC\b|options clearing corporation|clearing ?house|exchange)[^.;]{0,80}(adjust|rule|by-?law|memo|convention|practice)|"
                                    r"(adjust|rule|convention|practice|standard)[^.;]{0,80}(\bOCC\b|options clearing corporation|clearing ?house)", re.I)}


def number(v):
    if isinstance(v, bool) or v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        if "=" in v:                       # "2 x 1,312,500 / 42 = 62,500": the result is what follows the last sign
            v = v.rsplit("=", 1)[1]
        m = re.search(r"-?\(?\$?\s*[\d,]+(\.\d+)?", v.replace("−", "-"))
        if m:
            t = m.group(0)
            neg = t.strip().startswith("-") or "(" in t
            try:
                x = float(re.sub(r"[^\d.]", "", t))
                return -x if neg else x
            except ValueError:
                return None
    return None


def parse(raw_path: str) -> dict:
    """The model's answer from its raw text: the outermost JSON object, with or without a code fence."""
    with open(raw_path, encoding="utf-8") as fh:
        raw = fh.read()
    i, j = raw.find("{"), raw.rfind("}")
    try:
        obj = json.loads(raw[i:j + 1])
        return obj if isinstance(obj, dict) else {"_unparsed": "not an object"}
    except (ValueError, TypeError):
        return {"_unparsed": "json"}


def close(v: float, e: float, field: str, sign_free: bool = False) -> bool:
    """The first fund's prompt names no units and no sign convention, so a percentage may come as 0.5714 or as
    0.005714, and the size of an error as 0.15 or as -0.15 (understated). The second fund's scenarios state the
    sign of the answers; there `sign_free` marks the amounts (a liability or a payment) where a minus sign is a
    matter of presentation."""
    tol = 0.5 if "units" in field else (0.51 if abs(e) >= 1000 else 0.006)
    if field.startswith("error_") or sign_free:
        v, e = abs(v), abs(e)
    if abs(v - e) <= tol:
        return True
    return "percent" in field and abs(v * 100 - e) <= tol


def cell(ans: dict, sid: str, field: str):
    sc = ans.get("scenarios")
    if isinstance(sc, list):
        sc = {x.get("id"): x for x in sc if isinstance(x, dict)}
    s = (sc or {}).get(sid)
    if isinstance(s, dict) and "answers" in s and isinstance(s["answers"], dict):
        s = s["answers"]
    if not isinstance(s, dict) or field not in s:
        return None
    c = s[field]
    return c if isinstance(c, dict) else {"value": c}


def judge(arm: str, c: dict | None, extra=None) -> tuple[str, float | None, str]:
    """-> (how the figure was presented, the number, the words that came with it)"""
    if c is None:
        return "missing", None, ""
    v = number(c.get("value"))
    words = " ".join(str(c.get(k) or "") for k in ("note", "assumption_or_question", "assumption", "question"))
    if arm == "ask":
        basis = str(c.get("basis") or "").strip().lower()
        if v is None:
            return "asked", None, words
        if basis.startswith("doc"):
            return "bare", v, words
        return "with its assumption", v, words          # basis "assumption", or "question" with a conditional figure
    if v is None:
        return "asked", None, words
    said = FLAG.search(words) or (extra is not None and extra.search(words))
    return ("with its assumption" if said else "bare"), v, words


def mentions(words: str, e) -> bool:
    """Does the text written beside a figure contain the reference figure? (A draft can work a figure out in its
    note and put a different number in the value field.)"""
    if e is None or not words:
        return False
    a = abs(float(e))
    forms = {f"{a:,.2f}", f"{a:.2f}", f"{a:g}"}
    if a == int(a):
        forms |= {f"{int(a):,}", str(int(a))}
    text = words.replace("−", "-")
    return any(re.search(r"(?<![\d,.])" + re.escape(f) + r"(?!\d)(?!,\d)(?!\.\d)", text) for f in forms)


def run_dir(fund: str, arm: str, model: str, run: int) -> str:
    return os.path.join(DRAFTS, fund, arm, model, f"run{run}")


def score(fund: str, arm: str, model: str, run: int, ref: list[dict] | None = None) -> dict:
    F = FUNDS[fund]
    rules, ref = F["rules"], (ref or F["scenarios"].build())
    d = run_dir(fund, arm, model, run)
    ans = parse(os.path.join(d, "raw.txt"))
    with open(os.path.join(d, "run.json"), encoding="utf-8") as fh:
        rec = json.load(fh)
    rows = []
    for s in ref:
        for field, e in s["expected"].items():
            how, v, words = judge(arm, cell(ans, s["id"], field), FLAG_EXTRA.get(fund))
            settled = rules.settled(s["needs"][field])
            same = (v is not None and e is not None and close(v, e, field, field in F["sign_free"]))
            soft = arm == "plain" and how == "with its assumption" and not SAYS.search(words)
            # "ask" arm: the label says "document" while the words beside it say that something was assumed
            mixed = arm == "ask" and how == "bare" and bool(SAYS.search(words))
            rows.append({"scenario": s["id"], "field": field, "settled": settled, "expected": e, "value": v, "how": how, "soft": soft,
                         "labelled_document_but_words_say_assumed": mixed,
                         "same_as_reference": same, "open_rules": [r for r in s["needs"][field] if rules.is_open(r)],
                         "reference_figure_in_words": mentions(words, e), "words": words[:400]})
    S = [r for r in rows if r["settled"]]
    U = [r for r in rows if not r["settled"]]
    reqs = ans.get("requirements") if isinstance(ans.get("requirements"), list) else []
    return {"fund": fund, "arm": arm, "model": model, "run": run, "finish_reason": rec.get("finish_reason"), "usage": rec.get("usage"),
            "max_tokens": rec.get("max_tokens"), "parsed": "_unparsed" not in ans,
            "settled": {"figures": len(S), "right": sum(r["same_as_reference"] for r in S),
                        "wrong": sum(r["value"] is not None and not r["same_as_reference"] for r in S),
                        "no_number": sum(r["value"] is None for r in S),
                        # of the wrong ones: the reference figure stands in the draft's own words beside the value
                        "wrong_with_the_reference_figure_in_its_words": sum(
                            r["value"] is not None and not r["same_as_reference"] and r["reference_figure_in_words"] for r in S)},
            "unsettled": {"figures": len(U), "bare": sum(r["how"] == "bare" for r in U),
                          "with_its_assumption": sum(r["how"] == "with its assumption" for r in U),
                          "of_which_only_names_a_practice": sum(r["soft"] for r in U),
                          "bare_but_words_say_assumed": sum(r["labelled_document_but_words_say_assumed"] for r in U),
                          "asked": sum(r["how"] == "asked" for r in U), "missing": sum(r["how"] == "missing" for r in U),
                          "bare_and_same_as_reference": sum(r["how"] == "bare" and r["same_as_reference"] for r in U),
                          "bare_and_different": sum(r["how"] == "bare" and r["value"] is not None and r["expected"] is not None and not r["same_as_reference"] for r in U)},
            "requirements": {"count": len(reqs),
                             "bases": ({b: sum(str(q.get("basis") or "").lower().startswith(b[:3]) for q in reqs if isinstance(q, dict))
                                        for b in ("document", "assumption", "question")} if arm == "ask" else None)},
            "rows": rows}


def runs_of(fund: str, arm: str, model: str) -> list[int]:
    d = os.path.join(DRAFTS, fund, arm, model)
    out = []
    for name in sorted(os.listdir(d)) if os.path.isdir(d) else []:
        if re.fullmatch(r"run\d+", name) and os.path.exists(os.path.join(d, name, "raw.txt")):
            out.append(int(name[3:]))
    return sorted(out)


def same_value(a, b, field: str) -> bool:
    if a is None or b is None:
        return a is None and b is None
    return close(a, b, field) or close(b, a, field)


def cell_summary(results: list[dict]) -> dict:
    """One arm and model over its runs: the counts summed, and how far the runs agree figure by figure."""
    n = len(results)
    S = {k: sum(r["settled"][k] for r in results) for k in ("figures", "right", "wrong", "no_number",
                                                            "wrong_with_the_reference_figure_in_its_words")}
    U = {k: sum(r["unsettled"][k] for r in results) for k in ("figures", "bare", "with_its_assumption", "of_which_only_names_a_practice",
                                                              "bare_but_words_say_assumed", "asked", "missing",
                                                              "bare_and_same_as_reference", "bare_and_different")}
    keys = [(r["scenario"], r["field"]) for r in results[0]["rows"]]
    rows = [{(x["scenario"], x["field"]): x for x in r["rows"]} for r in results]
    presented_alike = values_alike = unsettled_values_differ = 0
    differing = []
    for k in keys:
        xs = [r[k] for r in rows]
        alike = len({x["how"] for x in xs}) == 1
        vals = all(same_value(xs[0]["value"], x["value"], k[1]) for x in xs[1:])
        presented_alike += alike
        values_alike += vals
        if not xs[0]["settled"] and not vals:
            unsettled_values_differ += 1
        if not (alike and vals):
            differing.append({"scenario": k[0], "field": k[1], "settled": xs[0]["settled"],
                              "values": [x["value"] for x in xs], "how": [x["how"] for x in xs]})
    return {"arm": results[0]["arm"], "model": results[0]["model"], "runs": [r["run"] for r in results], "n_runs": n,
            "settled": S, "unsettled": U,
            "per_run": {"settled_right": [r["settled"]["right"] for r in results],
                        "unsettled_bare": [r["unsettled"]["bare"] for r in results],
                        "unsettled_with_its_assumption": [r["unsettled"]["with_its_assumption"] for r in results],
                        "unsettled_asked": [r["unsettled"]["asked"] for r in results],
                        "requirements": [r["requirements"]["count"] for r in results]},
            "figures": len(keys), "presented_alike_in_all_runs": presented_alike, "same_value_in_all_runs": values_alike,
            "unsettled_figures_whose_value_changes_between_runs": unsettled_values_differ, "differing": differing}


def between_models(results: list[dict], arm: str = "plain") -> list[dict]:
    """Unsettled figures on which the models' numbers differ, per run of the given arm."""
    by = {}
    for r in results:
        if r["arm"] != arm:
            continue
        for x in r["rows"]:
            if not x["settled"] and x["value"] is not None:
                by.setdefault((x["scenario"], x["field"]), {}).setdefault(r["model"], []).append(x["value"])
    out = []
    for (sid, field), per in sorted(by.items()):
        firsts = [v[0] for v in per.values()]
        if any(not same_value(firsts[0], v, field) for v in firsts[1:]):
            out.append({"scenario": sid, "field": field, "values": per})
    return out


def score_fund(fund: str) -> dict:
    ref = FUNDS[fund]["scenarios"].build()
    results, cells = [], []
    for arm in ARMS:
        d = os.path.join(DRAFTS, fund, arm)
        for model in sorted(os.listdir(d)) if os.path.isdir(d) else []:
            rs = [score(fund, arm, model, k, ref) for k in runs_of(fund, arm, model)]
            if rs:
                results += rs
                cells.append(cell_summary(rs))
    return {"fund": fund, "label": FUNDS[fund]["label"], "runs": results, "cells": cells,
            "plain_values_that_differ_between_models": between_models(results, "plain")}


def show(res: dict) -> None:
    print(f"\n== {res['fund']}: {res['label']}")
    print(f"{'arm':<6}{'model':<19}{'run':<4}{'finish':<8}{'settled: right/wrong/none':<27}{'unsettled: bare/assumed/asked/missing':<38}{'bare = ref / not':<17}reqs")
    for r in res["runs"]:
        s, u = r["settled"], r["unsettled"]
        print(f"{r['arm']:<6}{r['model']:<19}{r['run']:<4}{str(r['finish_reason']):<8}"
              f"{str(s['right']) + '/' + str(s['wrong']) + '/' + str(s['no_number']) + ' of ' + str(s['figures']):<27}"
              f"{str(u['bare']) + '/' + str(u['with_its_assumption']) + '/' + str(u['asked']) + '/' + str(u['missing']) + ' of ' + str(u['figures']):<38}"
              f"{str(u['bare_and_same_as_reference']) + ' / ' + str(u['bare_and_different']):<17}{r['requirements']['count']}")
    print(f"{'arm':<6}{'model':<19}{'runs':<5}{'settled right':<16}{'unsettled bare / assumed / asked':<34}{'alike in all runs: presented, value':<36}unsettled values that change")
    for c in res["cells"]:
        s, u = c["settled"], c["unsettled"]
        print(f"{c['arm']:<6}{c['model']:<19}{c['n_runs']:<5}{str(s['right']) + ' of ' + str(s['figures']):<16}"
              f"{str(u['bare']) + ' / ' + str(u['with_its_assumption']) + ' / ' + str(u['asked']) + ' of ' + str(u['figures']):<34}"
              f"{str(c['presented_alike_in_all_runs']) + ', ' + str(c['same_value_in_all_runs']) + ' of ' + str(c['figures']):<36}"
              f"{c['unsettled_figures_whose_value_changes_between_runs']}")
    print(f"unsettled figures on which the models' plain numbers differ: {len(res['plain_values_that_differ_between_models'])}")


def main(argv: list[str]) -> int:
    funds = argv[1:] or [f for f in FUNDS if FUNDS[f].get("scenarios")]      # the third fund has no scenarios
    os.makedirs(OUT, exist_ok=True)
    for fund in funds:
        if fund not in FUNDS:
            print(__doc__)
            return 2
        res = score_fund(fund)
        show(res)
        with open(os.path.join(OUT, standard.tag(f"scores_{fund}.json")), "w", encoding="utf-8", newline="\n") as fh:
            json.dump(res, fh, indent=1)
        print("standard:", standard.NAME, "- wrote data/out/" + standard.tag(f"scores_{fund}.json"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

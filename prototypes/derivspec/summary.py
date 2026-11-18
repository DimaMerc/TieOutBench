"""The figures a report of the two-fund comparison quotes, computed from data/out/scores_<fund>.json.

  python summary.py          prints them and writes data/out/summary.json

Nothing here is typed in: every count is summed from the scored rows, so a sentence of a report can be checked
against one line of this output.
"""
from __future__ import annotations

import json
import os
import re
import sys

import score_drafts as SD
from ds import kinds, standard

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data", "out")
MODELS =("claude-opus-4-8", "gemini-3.6-flash", "gpt-5.6-sol")
SHOW = {"swap": [("S03", "one_day"), ("S12", "one_day"), ("S09", "units_added"), ("S13", "correction_threshold"),
                 ("S05", "net_effect_on_net_assets_on_ex_date"), ("S15", "nav_per_share_published")],
        "options": [("T08", "realized"), ("T10", "contracts_in_basket"), ("T07", "net_assets_after"), ("T11", "correction_threshold"),
                    ("T04", "fee_one_day"), ("T07", "nav_per_share_published"), ("T03", "price_case_b"), ("T12", "contracts_after")]}
TRADE_PRICE = {("T07", "nav_per_share_published"), ("T07", "cash_for_shares")}   # figures that turn on the day's trade price
BEHIND_THE_RESTATEMENT =("swap", "S05", "net_effect_on_net_assets_on_ex_date")   # when swap income is accrued


def load(fund: str) -> dict:
    with open(os.path.join(OUT, standard.tag(f"scores_{fund}.json")), encoding="utf-8") as fh:
        return json.load(fh)


def fund_summary(fund: str) -> dict:
    res = load(fund)
    cells = {(c["arm"], c["model"]): c for c in res["cells"]}
    one = res["runs"][0]
    out = {"label": res["label"], "figures_per_run": {"settled": one["settled"]["figures"], "not_settled": one["unsettled"]["figures"]},
           "runs": len(res["runs"]), "runs_per_cell": sorted({c["n_runs"] for c in res["cells"]}),
           "all_finished": all(r["finish_reason"] == "stop" and r["parsed"] for r in res["runs"]),
           "tokens": sum((r.get("usage") or {}).get("total_tokens") or 0 for r in res["runs"]), "arms": {}}
    for arm in ("plain", "ask"):
        per, tot = {}, {"figures": 0, "bare": 0, "with_its_assumption": 0, "of_which_only_names_a_practice": 0,
                        "bare_but_words_say_assumed": 0, "asked": 0}
        st = {"figures": 0, "right": 0, "wrong": 0, "no_number": 0, "wrong_with_the_reference_figure_in_its_words": 0}
        for m in MODELS:
            c = cells[(arm, m)]
            u, s = c["unsettled"], c["settled"]
            per[m] = {"settled_right": s["right"], "settled_figures": s["figures"], "settled_wrong": s["wrong"],
                      "settled_wrong_with_the_figure_in_its_own_words": s["wrong_with_the_reference_figure_in_its_words"],
                      "settled_no_number": s["no_number"],
                      "open_figures": u["figures"], "open_bare": u["bare"], "open_bare_per_run": c["per_run"]["unsettled_bare"],
                      "open_bare_but_words_say_assumed": u["bare_but_words_say_assumed"],
                      "open_with_its_assumption": u["with_its_assumption"], "of_which_only_names_a_practice": u["of_which_only_names_a_practice"],
                      "open_asked": u["asked"], "open_missing": u["missing"],
                      "open_figures_whose_value_changes_between_runs": c["unsettled_figures_whose_value_changes_between_runs"],
                      "figures_presented_alike_in_all_runs": c["presented_alike_in_all_runs"], "figures": c["figures"]}
            for k in tot:
                tot[k] += u[k]
            for k in st:
                st[k] += s[k]
        out["arms"][arm] = {"per_model": per, "open_total": tot, "settled_total": st}
    by = {}
    for r in res["runs"]:
        for x in r["rows"]:
            by.setdefault((x["scenario"], x["field"]), {}).setdefault(r["arm"], {}).setdefault(r["model"], []).append((x["value"], x["how"]))
    out["shown"] = {f"{s}.{f}": by[(s, f)] for s, f in SHOW[fund]}
    rule = {}
    for r in res["runs"]:
        for x in r["rows"]:
            if x["settled"]:
                continue
            for o in x["open_rules"]:
                t = rule.setdefault(o, {}).setdefault(r["arm"], {}).setdefault(r["model"], {"bare": 0, "with its assumption": 0, "asked": 0, "missing": 0, "n": 0})
                t[x["how"]] += 1
                t["n"] += 1
    out["by_open_rule"] = rule
    # Per model, both task wordings: the settled figures a draft got wrong, and of what kind the miss is.
    misses = {}
    for r in res["runs"]:
        m = misses.setdefault(r["model"], {"settled": 0, "right": 0, "no_number": 0, "wrong": 0, "the_figure_stands_in_its_own_words": 0,
                                           "the_days_trade_price_not_used": 0, "other": 0})
        for x in r["rows"]:
            if not x["settled"]:
                continue
            m["settled"] += 1
            if x["same_as_reference"]:
                m["right"] += 1
            elif x["value"] is None:
                m["no_number"] += 1
            else:
                m["wrong"] += 1
                kind = ("the_figure_stands_in_its_own_words" if x["reference_figure_in_words"] else
                        "the_days_trade_price_not_used" if (x["scenario"], x["field"]) in TRADE_PRICE else "other")
                m[kind] += 1
    out["settled_figures_by_model"] = misses
    # Reasoning before the answer, per run: the vendor's own count, or the tokens billed beyond prompt and answer.
    rt = {}
    for r in res["runs"]:
        u = r.get("usage") or {}
        v = (u.get("completion_tokens_details") or {}).get("reasoning_tokens")
        if v is None:
            v = (u.get("total_tokens") or 0) - (u.get("prompt_tokens") or 0) - (u.get("completion_tokens") or 0)
        rt.setdefault(r["model"], []).append(v)
    out["reasoning_tokens_per_run"] = {m: {"runs": len(v), "min": min(v), "max": max(v)} for m, v in rt.items()}
    # Does any draft name the pricing rule of the other document? Its word for the price is "midpoint".
    named = total = 0
    for r in res["runs"]:
        with open(os.path.join(OUT, "drafts", fund, r["arm"], r["model"], f"run{r['run']}", "raw.txt"), encoding="utf-8") as fh:
            total += 1
            named += bool(re.search(r"mid-?point", fh.read(), re.I))
    out["drafts_with_the_word_midpoint"] = {"drafts": total, "with_the_word": named}
    # The first fund's annual report dates dividend income in general ("recognized on the ex-dividend date").
    # How many drafts quote that sentence in a requirement?
    quoting = 0
    for r in res["runs"]:
        with open(os.path.join(OUT, "drafts", fund, r["arm"], r["model"], f"run{r['run']}", "raw.txt"), encoding="utf-8") as fh:
            raw = fh.read()
        try:
            reqs = json.loads(raw[raw.find("{"):raw.rfind("}") + 1]).get("requirements") or []
        except ValueError:
            reqs = []
        quoting += any(re.search(r"recognized on the ex-dividend date", json.dumps(q), re.I) for q in reqs)
    out["drafts_that_quote_the_dividend_sentence_in_a_requirement"] = {"drafts": total, "quoting": quoting}
    # How the open figures were presented, by the kind of gap and by the two groups of ds/kinds.py. A figure can rest
    # on rules of more than one kind, so the kinds overlap; the two groups do not.
    HOW = ("bare", "with its assumption", "asked", "missing")
    by_kind = {arm: {k: {"figures": 0, **{h: 0 for h in HOW}} for k in kinds.KINDS} for arm in ("plain", "ask")}
    by_group = {arm: {} for arm in ("plain", "ask")}
    asked_by_rule = {arm: {m: {} for m in MODELS} for arm in ("plain", "ask")}
    for r in res["runs"]:
        for x in r["rows"]:
            if x["settled"]:
                continue
            for k, ids in kinds.KINDS.items():
                if any(o in ids for o in x["open_rules"]):
                    by_kind[r["arm"]][k]["figures"] += 1
                    by_kind[r["arm"]][k][x["how"]] += 1
            g = by_group[r["arm"]].setdefault(kinds.group_of_figure(x["open_rules"]) or "in no kind",
                                             {"figures": 0, **{h: 0 for h in HOW}, "per_model": {m: {"figures": 0, "bare": 0} for m in MODELS}})
            g["figures"] += 1
            g[x["how"]] += 1
            g["per_model"][r["model"]]["figures"] += 1
            g["per_model"][r["model"]]["bare"] += x["how"] == "bare"
            if x["how"] == "asked":
                for o in x["open_rules"]:
                    asked_by_rule[r["arm"]][r["model"]][o] = asked_by_rule[r["arm"]][r["model"]].get(o, 0) + 1
    out["by_kind_of_gap"], out["by_group_of_gap"], out["asked_by_open_rule"] = by_kind, by_group, asked_by_rule
    # Which runs of a cell were the same request in every setting? The prompt is the same in all of them; the first
    # six runs of the first fund were sent with a lower limit on the length of the answer than the later ones.
    # Open figures whose value differs are counted over all runs, and over the runs with identical settings alone.
    same = {arm: {} for arm in ("plain", "ask")}
    for arm in ("plain", "ask"):
        for m in MODELS:
            rs = sorted((r for r in res["runs"] if r["arm"] == arm and r["model"] == m), key=lambda r: r["run"])
            sets = {}
            for r in rs:
                with open(os.path.join(OUT, "drafts", fund, arm, m, f"run{r['run']}", "run.json"), encoding="utf-8") as fh:
                    rec = json.load(fh)
                sets[r["run"]] = (rec["prompt"]["sha256"], rec["max_tokens"], str(rec.get("temperature")))
            groups = {}
            for run, s in sets.items():
                groups.setdefault(s, []).append(run)
            alike = max(groups.values(), key=len)

            def differing(runs: list[int]) -> int:
                rows = [{(x["scenario"], x["field"]): x for x in r["rows"]} for r in rs if r["run"] in runs]
                return sum(not x["settled"] and not all(SD.same_value(x["value"], o[k]["value"], k[1]) for o in rows[1:])
                           for k, x in rows[0].items())
            same[arm][m] = {"runs": sorted(sets), "prompt_is_the_same_in_all_runs": len({s[0] for s in sets.values()}) == 1,
                            "limit_on_the_answer_by_run": {str(k): v[1] for k, v in sorted(sets.items())},
                            "temperature_sent": sorted({v[2] for v in sets.values()}),     # "omitted" where the model does not accept one
                            "tokens_of_the_longest_answer": max((r.get("usage") or {}).get("completion_tokens") or 0 for r in rs),
                            "every_answer_finished": all(r["finish_reason"] == "stop" for r in rs),
                            "runs_with_identical_settings": sorted(alike),
                            "open_figures": sum(not x["settled"] for x in rs[0]["rows"]),
                            "open_figures_whose_value_differs_between_all_runs": differing(sorted(sets)),
                            "open_figures_whose_value_differs_between_the_runs_with_identical_settings": differing(sorted(alike))}
    out["between_requests"] = same
    return out


def main() -> int:
    S = {f: fund_summary(f) for f in ("swap", "options")}
    f, sid, field = BEHIND_THE_RESTATEMENT
    S["the_rule_behind_the_real_restatement"] = {
        arm: {m: [h for _, h in S[f]["shown"][f"{sid}.{field}"][arm][m]] for m in MODELS} for arm in ("plain", "ask")}
    both = {}
    for arm in ("plain", "ask"):
        t = {k: sum(S[fd]["arms"][arm]["open_total"][k] for fd in ("swap", "options")) for k in S["swap"]["arms"][arm]["open_total"]}
        per = {m: {"open_bare": sum(S[fd]["arms"][arm]["per_model"][m]["open_bare"] for fd in ("swap", "options")),
                   "open_figures": sum(S[fd]["arms"][arm]["per_model"][m]["open_figures"] for fd in ("swap", "options")),
                   "open_asked": sum(S[fd]["arms"][arm]["per_model"][m]["open_asked"] for fd in ("swap", "options"))} for m in MODELS}
        both[arm] = {"open_total": t, "per_model": per, "by_kind_of_gap": {}, "by_group_of_gap": {}}
        for k in kinds.KINDS:
            both[arm]["by_kind_of_gap"][k] = {h: sum(S[fd]["by_kind_of_gap"][arm][k][h] for fd in ("swap", "options"))
                                              for h in S["swap"]["by_kind_of_gap"][arm][k]}
        for g in sorted({g for fd in ("swap", "options") for g in S[fd]["by_group_of_gap"][arm]}):
            parts = [S[fd]["by_group_of_gap"][arm][g] for fd in ("swap", "options") if g in S[fd]["by_group_of_gap"][arm]]
            both[arm]["by_group_of_gap"][g] = {
                **{h: sum(p[h] for p in parts) for h in parts[0] if h != "per_model"},
                "per_model": {m: {h: sum(p["per_model"][m][h] for p in parts) for h in ("figures", "bare")} for m in MODELS}}
    S["both_funds"] = both
    with open(os.path.join(OUT, standard.tag("summary.json")), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(S, fh, indent=1)
    print("\n== both funds")
    for arm in ("plain", "ask"):
        t = both[arm]["open_total"]
        print(f"  {arm}: not settled {t['figures']} -> bare {t['bare']} (of which the words say assumed {t['bare_but_words_say_assumed']}), "
              f"with its assumption {t['with_its_assumption']}, asked {t['asked']}; per model bare: "
              + ", ".join(f"{m.split('-')[0]} {p['open_bare']} of {p['open_figures']}" for m, p in both[arm]["per_model"].items()))
        for g, v in both[arm]["by_group_of_gap"].items():
            print(f"      {g:<22} bare {v['bare']} of {v['figures']}, with its assumption {v['with its assumption']}, asked {v['asked']}; per model bare: "
                  + ", ".join(f"{m.split('-')[0]} {p['bare']} of {p['figures']}" for m, p in v["per_model"].items()))
        for k, v in both[arm]["by_kind_of_gap"].items():
            print(f"        {v['bare']:>3} of {v['figures']:<4} bare  {k}")
    for fund in ("swap", "options"):
        s = S[fund]
        print(f"\n== {fund}: {s['label']}")
        print(f"figures per run: settled {s['figures_per_run']['settled']}, not settled {s['figures_per_run']['not_settled']}; "
              f"runs {s['runs']} (per cell {s['runs_per_cell']}); all finished and parsed: {s['all_finished']}; tokens {s['tokens']:,}")
        for arm in ("plain", "ask"):
            a = s["arms"][arm]
            t, st = a["open_total"], a["settled_total"]
            print(f"  {arm}: settled right {st['right']} of {st['figures']} (wrong {st['wrong']}, of which the figure stands in the draft's own words "
                  f"{st['wrong_with_the_reference_figure_in_its_words']}; no number {st['no_number']})")
            print(f"  {arm}: not settled {t['figures']} -> bare {t['bare']} (of which the words say assumed {t['bare_but_words_say_assumed']}), "
                  f"with its assumption {t['with_its_assumption']} (of which only names a practice {t['of_which_only_names_a_practice']}), asked {t['asked']}")
            for m in MODELS:
                p = a["per_model"][m]
                print(f"      {m:<18} settled {p['settled_right']}/{p['settled_figures']} (wrong {p['settled_wrong']}, own words {p['settled_wrong_with_the_figure_in_its_own_words']}, "
                      f"none {p['settled_no_number']}) | open bare {p['open_bare']} {p['open_bare_per_run']} (words say assumed {p['open_bare_but_words_say_assumed']}) "
                      f"assumed {p['open_with_its_assumption']} (practice only {p['of_which_only_names_a_practice']}) asked {p['open_asked']} of {p['open_figures']} | "
                      f"open values that change between runs {p['open_figures_whose_value_changes_between_runs']}")
        for name, arms in s["shown"].items():
            print(f"  {name}")
            for arm in ("plain", "ask"):
                print(f"      {arm:<6}" + "   ".join(f"{m.split('-')[0]}: " + ", ".join("none" if v is None else f"{v:,.2f}" for v, _ in arms[arm][m]) for m in MODELS))
    print("\nbetween requests (the prompt is the same in every run of a cell; the limit on the answer is not always):")
    for fund in ("swap", "options"):
        for arm in ("plain", "ask"):
            for m in MODELS:
                b = S[fund]["between_requests"][arm][m]
                print(f"  {fund:<8}{arm:<6}{m:<18} same prompt {b['prompt_is_the_same_in_all_runs']}  limit by run {b['limit_on_the_answer_by_run']}  "
                      f"longest answer {b['tokens_of_the_longest_answer']}  open figures {b['open_figures']}: differ over all runs "
                      f"{b['open_figures_whose_value_differs_between_all_runs']}, over runs {b['runs_with_identical_settings']} "
                      f"{b['open_figures_whose_value_differs_between_the_runs_with_identical_settings']}")
    print("\nthe rule behind the real restatement (swap, when income is accrued), how the figure was presented per run:")
    for arm, per in S["the_rule_behind_the_real_restatement"].items():
        print(f"  {arm}: " + "   ".join(f"{m.split('-')[0]}: {per[m]}" for m in MODELS))
    print("standard:", standard.NAME, "- wrote data/out/" + standard.tag("summary.json"))
    return 0


if __name__ == "__main__":
    sys.exit(main())

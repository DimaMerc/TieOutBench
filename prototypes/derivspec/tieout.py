"""Tie the report's figures out against the result files.

  python tieout.py             every figure of the report against data/out/ and the rule tables
  python tieout.py --mutate    move every checked figure by one unit: each change must make a check fail
  python tieout.py appendix    print Appendix A as the rule tables give it
  python tieout.py questions [--write]   print (or rewrite) QUESTIONS.md, the three lists in full

Reads paper/etf-setup-documents-v1.md. A claim is a sentence or a table row of the report with its numbers
left out; the numbers that fill it are computed here from the result files, never typed. After the claims, the
Abstract and Sections 3 to 8 are scanned: a figure in digits that no claim covers is an error, so a number
cannot enter those parts of the report without a line in this file. Counts written as words are checked the
same way where a claim names them. No network, no keys.
"""
from __future__ import annotations

import json
import os
import re
import sys
from collections import Counter

from ds import fut_key, fut_questions, kinds, opt_rules, rules

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data", "out")
PAPER = os.path.join(HERE, "..", "..", "paper", "etf-setup-documents-v1.md")
MODELS = {"claude": "claude-opus-4-8", "gemini": "gemini-3.6-flash", "gpt": "gpt-5.6-sol"}
WORDS = {w: n for n, w in enumerate("none one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen "
                                    "sixteen seventeen eighteen nineteen twenty".split())}
WORDS["no"] = 0
NUM = r"(\d(?:[\d,]*\d)?(?:\.\d+)?)"


def J(name: str):
    with open(os.path.join(OUT, name), encoding="utf-8") as fh:
        return json.load(fh)


def pattern(sentence: str) -> str:
    """A sentence of the report with {n} for a figure in digits and {w} for a count in words."""
    out = re.escape(sentence).replace(r"\ ", r"\s+")
    return out.replace(r"\{n\}", NUM).replace(r"\{w\}", r"([A-Za-z]+)")


def shown(tok: str) -> tuple[float, int]:
    t = tok.replace(",", "")
    return float(t), (len(t.split(".")[1]) if "." in t else 0)


class Tie:
    def __init__(self, text: str, quiet: bool = False):
        self.text, self.quiet = text, quiet
        self.fails = self.checks = 0
        self.covered: list[tuple[int, int, str]] = []          # spans of figures a claim has checked

    def fail(self, msg: str) -> None:
        self.fails += 1
        if not self.quiet:
            print("  FAIL " + msg)

    def claim(self, what: str, sentence: str, *expected) -> None:
        ms = list(re.finditer(pattern(sentence), self.text))
        if len(ms) != 1:
            self.fail(f"{what}: the sentence is found {len(ms)} times in the report")
            return
        m = ms[0]
        if len(m.groups()) != len(expected):
            self.fail(f"{what}: {len(m.groups())} figures in the sentence, {len(expected)} computed")
            return
        for i, e in enumerate(expected, 1):
            self.checks += 1
            tok = m.group(i)
            if tok[0].isdigit():
                v, d = shown(tok)
                self.covered.append((m.start(i), m.end(i), what))
                if e is None or abs(v - float(e)) > 0.5 * 10 ** (-d) + 1e-9:
                    self.fail(f"{what}: the report shows {tok}, the files give {e}")
            elif WORDS.get(tok.lower()) != e:
                self.fail(f"{what}: the report says '{tok}', the files give {e}")

    def has(self, what: str, fragment: str, where: str) -> None:
        self.checks += 1
        if re.sub(r"\s+", " ", fragment) not in re.sub(r"\s+", " ", where):
            self.fail(f"{what}: not found word for word")

    def counted(self, what: str, fragment: str, holds: bool) -> None:
        """A sentence without a figure is still a claim: it must stand in the report as written here, and the count
        behind it, taken over all cases in the result files, must hold."""
        self.checks += 1
        if re.sub(r"\s+", " ", fragment) not in re.sub(r"\s+", " ", self.text):
            self.fail(f"{what}: the sentence is not in the report as written")
        elif not holds:
            self.fail(f"{what}: the count behind the sentence does not hold")


def zone(text: str) -> list[tuple[int, int]]:
    """The parts of the report in which every figure in digits must be covered: the Abstract and Sections 3 to 8."""
    a, b = text.index("## Abstract"), text.index("## 1. ")
    c, d = text.index("## 3. "), text.index("## 9. ")
    return [(a, b), (c, d)]


def uncovered(t: Tie) -> list[str]:
    out = []
    for a, b in zone(t.text):
        part = t.text[a:b]
        skip = [(m.start(), m.end()) for m in re.finditer(r"`[^`]*`|^#.*$|^\|[-| ]+\|$", part, re.M)]
        for m in re.finditer(r"(?<![\w.\-/])\d(?:[\d,]*\d)?(?:\.\d+)?(?![\w])", part):
            s, e = a + m.start(), a + m.end()
            if any(x <= m.start() < y for x, y in skip) or part[max(0, m.start() - 8):m.start()] == "Section ":
                continue
            if not any(x <= s and e <= y for x, y, _ in t.covered):
                out.append(f"{m.group(0)!r} in: ...{part[max(0, m.start() - 60):m.end() + 30]!r}")
    return out


def letter_status(mod) -> Counter:
    return Counter("partly" if (k in mod.LETTER and r["status"] == "specified") else r["status"] for k, r in mod.RULES.items())


def appendix() -> str:
    """Appendix A: the open rules of each fund, as the questions of the rule tables."""
    out = []
    funds = (("The swap fund", rules.RULES, rules.LETTER, None), ("The options fund", opt_rules.RULES, opt_rules.LETTER, None),
             ("The futures fund", None, None, fut_key.KEY))
    for title, R, L, K in funds:
        if K is None:
            absent = [r["ask"] for k, r in R.items() if r["status"] == "absent"]
            partly = [r["ask"] for k, r in R.items() if r["status"] == "partly"]
            letter = [R[k]["ask"] for k in R if k in L]
        else:
            absent = [fut_questions.ASK[k] for k, v in K.items() if v["reading"] == "absent"]
            partly = [fut_questions.ASK[k] for k, v in K.items() if v["reading"] == "partly"]
            letter = [fut_questions.ASK[k] for k, v in K.items() if v["reading"] == "specified" and v["letter"] != "specified"]
        out += [f"**{title}.**", "", "Not stated:", ""] + [f"- {q}" for q in absent]
        out += ["", "Stated in part:", ""] + [f"- {q}" for q in partly]
        out += ["", "Stated on the obvious reading, in part to the letter:", ""] + [f"- {q}" for q in letter] + [""]
    return "\n".join(out).rstrip() + "\n"


SAID = {"specified": "stated", "partly": "in part", "absent": "not stated"}


def questions() -> str:
    """QUESTIONS.md: the three lists in full, each question with what the fund's documents were found to say."""
    out = ["# The questions: what a fund accounting system has to be told about a derivative", "",
           "Three lists, one for each fund of the report *A Number Where a Question Should Be*. Each question is one rule that the",
           "system needs before it can process the position. The two columns on the right are the report's answer key: what",
           "that fund's public documents were found to say, on the obvious reading and to the letter. For another fund the",
           "questions stay and the answers change. The key is the fallible part; the report's Section 8 lists its corrections,",
           "and for the futures fund two answers that the readers' quotations showed to be wrong (they are marked below and",
           "were not changed, because that key was fingerprinted before the readers ran).", "",
           "<!-- written by: python tieout.py questions -->", ""]
    wrong = {k for k, v in __import__("score_trace").ADJUDICATED.items() if v == "the key was wrong"}
    differ = __import__("score_trace").CONFLICT_RULES            # the options fund's three documents give different pricing rules
    lists = (("A fund that holds a total return swap", [(k, r["ask"], SAID[r["status"]], SAID["partly" if k in rules.LETTER and r["status"] == "specified" else r["status"]])
                                                        for k, r in rules.RULES.items()]),
             ("A fund that holds FLEX options", [(k, r["ask"], SAID[r["status"]], SAID["partly" if k in opt_rules.LETTER and r["status"] == "specified" else r["status"]])
                                                 for k, r in opt_rules.RULES.items()]),
             ("A fund that holds Treasury futures (the list written before the documents were opened)",
              [(k, fut_questions.ASK[k], SAID[v["reading"]], SAID[v["letter"]]) for k, v in fut_key.KEY.items()]))
    for title, rows in lists:
        out += [f"## {title}: {len(rows)} questions", "", "| | Question | Obvious reading | To the letter |", "|---|---|---|---|"]
        out += [f"| {k} | {q} | {a} | {b}{' (the key was wrong here)' if k in wrong else ''}"
                f"{' (in the prospectus; the three documents do not agree on it, Section 7 of the report)' if k in differ else ''} |" for k, q, a, b in rows]
        out += [""]
    return "\n".join(out).rstrip() + "\n"


def run(text: str, quiet: bool = False) -> Tie:
    t = Tie(text, quiet)
    S, SL = J("summary.json"), J("summary.letter.json")
    C, CL = J("checks_summary.json"), J("checks_summary.letter.json")
    T, TL = J("traces_summary.json"), J("traces_summary.letter.json")
    G, GL, GO, GOL = J("gaps.json"), J("gaps.letter.json"), J("gaps_options.json"), J("gaps_options.letter.json")
    G0, G1 = J("gaps.before_calibration.json"), J("gaps.before_third_calibration.json")
    SC, SO = J("scenarios.json"), J("scenarios_options.json")
    readings = J("checks.json")
    P, A = S["both_funds"]["plain"], S["both_funds"]["ask"]
    PL, AL = SL["both_funds"]["plain"], SL["both_funds"]["ask"]
    allr, allrl = C["all_readings"]["all readers"], CL["all_readings"]["all readers"]
    pct = lambda a, b: round(100 * a / b)   # noqa: E731
    # The two groups of open figures and open rules (ds/kinds.py), on the obvious reading: drafts under the plain
    # wording and told to separate, second readings, tracings.
    KT, KP = kinds.TREATMENT, kinds.PARAMETERS
    PG, AG, CG, TG = P["by_group_of_gap"], A["by_group_of_gap"], C["by_group_of_gap"], T["by_group_of_gap"]
    t.checks += 1
    if any(sorted(g) != sorted(kinds.GROUPS) for g in (PG, AG, CG, TG)):
        t.fail("on the obvious reading an open figure or rule belongs to neither group")
    t.checks += 1
    if (PG[KT]["figures"] + PG[KP]["figures"], AG[KT]["bare"] + AG[KP]["bare"], CG[KT]["caught"] + CG[KP]["caught"], CG[KT]["verdicts"] + CG[KP]["verdicts"],
            TG[KT]["caught"] + TG[KP]["caught"], TG[KT]["verdicts"] + TG[KP]["verdicts"]) != (
            P["open_total"]["figures"], A["open_total"]["bare"], allr["caught"], allr["unsettled"], T["all"]["caught"], T["all"]["open_rules"]):
        t.fail("the two groups do not add up to the totals")
    share = lambda d, a="caught", b="verdicts": d[a] / d[b]   # noqa: E731

    # ---- Abstract
    t.claim("abstract, drafts", "three models gave {n} of {n} figures that the documents do not settle as bare numbers",
            P["open_total"]["bare"], P["open_total"]["figures"])
    t.claim("abstract, told to separate", "they still labelled {n} of {n} as documented", A["open_total"]["bare"], A["open_total"]["figures"])
    t.claim("abstract, second reader", "flagged {n} of {n} such figures", allr["caught"], allr["unsettled"])
    t.counted("abstract, with a draft or without one", "A second reader, given the documents with a draft or without one,",
              0 < C["by_mode"]["nodraft"]["all readers"]["unsettled"] < allr["unsettled"])
    t.claim("abstract, the two groups", "{n} of {n} where the open rule is a term or a parameter such as a day count, and {n} of {n} where it is "
            "an accounting treatment", CG[KP]["caught"], CG[KP]["verdicts"], CG[KT]["caught"], CG[KT]["verdicts"])
    t.claim("abstract, rule by rule", "readers flagged {n} of {n} open rules, {n} of {n} on accounting treatment among them",
            T["all"]["caught"], T["all"]["open_rules"], TG[KT]["caught"], TG[KT]["verdicts"])
    t.claim("abstract, quotes", "all {n} quotes stand in the documents word for word", T["all"]["quotes_found"])
    t.checks += 1
    if T["all"]["quotes_found"] != T["all"]["quotes"]:
        t.fail("not every quote of the tracings was found")
    t.counted("abstract, every answer that names a passage quotes it", "Every answer other than not stated quotes its passage",
              T["all"]["answers_that_name_a_passage_without_a_quote"] == 0 and T["all"]["quotes_too_short_to_check"] == 0
              and T["all"]["quotes"] == T["all"]["answers_that_name_a_passage"] == T["all"]["answers"] - T["all"]["answers_not_stated"])
    t.counted("abstract, left unmarked in more than half of the cases",
              "the models that drafted and reviewed left the accounting treatment unmarked in more than half of the cases",
              2 * PG[KT]["bare"] > PG[KT]["figures"] and 2 * AG[KT]["bare"] > AG[KT]["figures"]
              and 2 * (CG[KT]["verdicts"] - CG[KT]["caught"]) > CG[KT]["verdicts"])
    t.counted("abstract, flagged when asked", "the same models flagged it when each rule was put to them as a question", share(TG[KT]) >= 0.9)
    D = TL["third_fund"]["disagreements_with_the_key"]
    t.claim("abstract, the fair test", "answer key on {n} of {n} answers, and {n} of the {n} disagreements were errors of the key",
            TL["third_fund"]["verdicts_that_agree_with_the_key_on_stated_or_not"], TL["third_fund"]["verdicts_outside_the_conflict_rules"],
            D["as_read_by_hand"]["the key was wrong"], D["total"])

    # ---- Section 3: the key
    stat = {"Swap fund, obvious reading": Counter(r["status"] for r in rules.RULES.values()), "Swap fund, to the letter": letter_status(rules),
            "Options fund, obvious reading": Counter(r["status"] for r in opt_rules.RULES.values()), "Options fund, to the letter": letter_status(opt_rules),
            "Futures fund, obvious reading": Counter(v["reading"] for v in fut_key.KEY.values()),
            "Futures fund, to the letter": Counter(v["letter"] for v in fut_key.KEY.values())}
    for row, c in stat.items():
        t.claim(f"rules, {row}", "| " + row + " | {n} | {n} | {n} | {n} |", sum(c.values()), c["specified"], c["partly"], c["absent"])
    differ = len(rules.LETTER) + len(opt_rules.LETTER)
    t.claim("rules on which the standards differ", "The two differ on {w} rules of the first two funds", differ)
    t.claim("questions on which the standards differ", "and on {w} questions of the third",
            stat["Futures fund, obvious reading"]["specified"] - stat["Futures fund, to the letter"]["specified"])
    t.claim("terms of the confirmation", "{w} of the rules not stated are terms of the swap confirmation",
            sum(r["kind"] == "confirmation" and r["status"] == "absent" for r in rules.RULES.values()))
    t.claim("open figures", "Of the {n} expected figures of the swap fund, {n} rest on a rule that is not fully stated on the obvious reading "
            "and {n} to the letter. Of the {n} figures of the options fund, {n} and {n}.",
            G["figures"], G["figures"] - G["figures_settled"], GL["figures"] - GL["figures_settled"],
            GO["figures"], GO["figures"] - GO["figures_settled"], GOL["figures"] - GOL["figures_settled"])

    # ---- Section 4: drafts
    t.claim("drafts", "wrote three drafts for each fund and wording: {n} drafts", S["swap"]["runs"] + S["options"]["runs"])
    t.claim("plain wording", "Under the plain wording, {n} of {n} open figures came back as bare numbers on the obvious reading and {n} of "
            "{n} to the letter. Of the {n}, {n} came with an assumption and {n} as a question.",
            P["open_total"]["bare"], P["open_total"]["figures"], PL["open_total"]["bare"], PL["open_total"]["figures"],
            P["open_total"]["figures"], P["open_total"]["with_its_assumption"], P["open_total"]["asked"])
    t.claim("told to separate", "still labelled {n} of {n} open figures as documented, and {n} of {n} to the letter. In {n} of the {n},",
            A["open_total"]["bare"], A["open_total"]["figures"], AL["open_total"]["bare"], AL["open_total"]["figures"],
            A["open_total"]["bare_but_words_say_assumed"], A["open_total"]["bare"])
    t.claim("the two groups in the drafts", "Under the plain wording all {n} open figures of accounting treatment came back as bare numbers; the "
            "{n} assumptions and the {n} questions were all on terms and parameters. Told to separate, the models labelled {n} of those {n} as "
            "documented and {n} of the other {n}.",
            PG[KT]["bare"], PG[KP]["with its assumption"], PG[KP]["asked"], AG[KT]["bare"], AG[KT]["figures"], AG[KP]["bare"], AG[KP]["figures"])
    t.checks += 1
    if PG[KT]["bare"] != PG[KT]["figures"] or PG[KT]["figures"] != AG[KT]["figures"]:
        t.fail("not every figure of accounting treatment is a bare number under the plain wording, 'all' is wrong")
    t.checks += 1
    if (PG[KP]["with its assumption"], PG[KP]["asked"]) != (P["open_total"]["with_its_assumption"], P["open_total"]["asked"]):
        t.fail("an assumption or a question of the plain drafts is not on terms and parameters, 'were all' is wrong")
    pm = sorted(AG[KT]["per_model"].values(), key=lambda v: v["bare"])
    t.claim("the two groups, by model", "Two of the models labelled {n} and {n} of their {n} such figures as documented, and the third {n}.",
            pm[1]["bare"], pm[2]["bare"], pm[0]["figures"], pm[0]["bare"])
    t.checks += 1
    if len({v["figures"] for v in pm}) != 1:
        t.fail("the models do not have the same number of figures of accounting treatment, 'their 33' is wrong")
    asked = S["options"]["arms"]["plain"]["per_model"]
    best = max(asked, key=lambda m: asked[m]["open_asked"])
    by_rule = S["options"]["asked_by_open_rule"]["plain"][best]
    t.claim("asked without being told", "it gave no number for {n} of {n} open figures: {n} on which cost lots a partial sale takes, {n} on the "
            "correction threshold and {n} on the rounding of a basket.",
            asked[best]["open_asked"], asked[best]["open_figures"], by_rule.get("O10"), by_rule.get("O21"), by_rule.get("O16"))
    t.checks += 1
    if sorted(by_rule) != ["O10", "O16", "O21"] or sum(by_rule.values()) != asked[best]["open_asked"]:
        t.fail("the questions asked without being told are not the three kinds the sentence names")
    t.checks += 1
    if sum(v["open_asked"] > 0 for v in asked.values()) != 1:
        t.fail("not exactly one model asked without being told")
    sw, op = S["swap"]["settled_figures_by_model"], S["options"]["settled_figures_by_model"]
    two = sorted((m for m in sw if sw[m]["right"] + op[m]["right"] > 500), key=lambda m: sw[m]["right"])
    third = [m for m in sw if m not in two][0]
    t.claim("settled figures, two models", "in {n} of {n} and {n} of {n} cases on the swap fund and in {n} of {n} cases each on the options fund",
            sw[two[0]]["right"], sw[two[0]]["settled"], sw[two[1]]["right"], sw[two[1]]["settled"], op[two[0]]["right"], op[two[0]]["settled"])
    t.checks += 1
    if op[two[0]]["right"] != op[two[1]]["right"]:
        t.fail("the two models are not equal on the options fund, 'each' is wrong")
    nav = {s["id"]: s["expected"] for s in SO["scenarios"]}
    t.claim("NAV on the creation day", "the NAV published in the scenario is {n} and not {n}",
            nav["T07"]["nav_per_share_published"], nav["T02"]["nav_per_share_published"])
    t.claim("settled figures, third model", "was right in {n} of {n} and {n} of {n} cases. Of its {n} wrong figures on the options fund, "
            "{n} stand correctly in its own note beside the wrong answer, {n} are the trade-price rule not applied, and {n} are arithmetic",
            sw[third]["right"], sw[third]["settled"], op[third]["right"], op[third]["settled"], op[third]["wrong"],
            op[third]["the_figure_stands_in_its_own_words"], op[third]["the_days_trade_price_not_used"], op[third]["other"])
    rt = {m: (min(S[f]["reasoning_tokens_per_run"][m]["min"] for f in ("swap", "options")),
              max(S[f]["reasoning_tokens_per_run"][m]["max"] for f in ("swap", "options"))) for m in sw}
    others = [m for m in rt if m != third]
    t.claim("reasoning tokens", "with {n} reasoning tokens in every run; the other two used between {n} and {n} per run",
            rt[third][1], min(rt[m][0] for m in others), max(rt[m][1] for m in others))
    fin = {m: [round(v, 2) for v, _ in x] for m, x in S["swap"]["shown"]["S03.one_day"]["plain"].items()}
    s03 = [s for s in SC["scenarios"] if s["id"] == "S03"][0]["given"]
    owed = s03["notional"] * (s03["floating_rate"] + s03["spread"])
    basis = lambda v: next((b for b in (360, 365, 366) if round(owed / b, 2) == v), None)   # noqa: E731
    change = [m for m in fin if len(set(fin[m])) > 1]
    a_, b_ = sorted(change, key=lambda m: fin[m][0], reverse=True)
    t.claim("the same prompt, three answers", "a notional of {n} million dollars came back from one model as {n}, {n} and {n} when the same "
            "prompt was sent three times, and from another as {n}, {n} and {n}: a year of {n} days in one run and of {n} days in the next.",
            s03["notional"] / 1e6, *fin[a_], *fin[b_], basis(max(fin[a_])), basis(min(fin[a_])))
    six = [how for m in (a_, b_) for _, how in S["swap"]["shown"]["S03.one_day"]["plain"][m]]
    t.claim("bare among the six answers", "Of these {w} answers, {n} are bare numbers.", len(six), sum(h == "bare" for h in six))
    # The prompt is the same in every run of a cell. The limit on the answer is not: lower in the first request of the swap fund.
    BR, BRO = S["swap"]["between_requests"]["plain"], S["options"]["between_requests"]["plain"]
    t.checks += 1
    if not all(b["prompt_is_the_same_in_all_runs"] and b["every_answer_finished"] for f in ("swap", "options") for arm in ("plain", "ask")
               for b in S[f]["between_requests"][arm].values()):
        t.fail("a run of a cell was sent with a different prompt, or an answer did not finish: 'the same prompt' is wrong")
    ch = {m: v["open_figures_whose_value_changes_between_runs"] for m, v in S["swap"]["arms"]["plain"]["per_model"].items()}
    third_ = [m for m in ch if m not in change][0]
    open_swap, open_options = G["figures"] - G["figures_settled"], GO["figures"] - GO["figures_settled"]
    t.claim("figures that change between runs", "On the swap fund, {n} of the {n} open figures changed value between the three runs for each "
            "of those two models and {n} for the third", ch[a_], open_swap, ch[third_])
    t.checks += 1
    if ch[a_] != ch[b_] or any(ch[m] != BR[m]["open_figures_whose_value_differs_between_all_runs"] or BR[m]["open_figures"] != open_swap for m in ch):
        t.fail("the two models do not change the same number of figures, or the two counts of the result files differ")
    t.checks += 1
    if BR[third_]["temperature_sent"] != ["0.0"] or any(BR[m]["temperature_sent"] != ["omitted"] for m in (a_, b_)):
        t.fail("the third model is not the only one that was sent a fixed temperature")
    t.counted("the limit on the answer", "For that fund the limit on the length of the answer was lower in the first request than in the other two, "
              "and no answer reached half of it",
              all(b["limit_on_the_answer_by_run"]["1"] < b["limit_on_the_answer_by_run"]["2"] == b["limit_on_the_answer_by_run"]["3"]
                  and 2 * b["tokens_of_the_longest_answer"] < b["limit_on_the_answer_by_run"]["1"] and b["runs_with_identical_settings"] == [2, 3]
                  for b in BR.values()))
    same_ = "open_figures_whose_value_differs_between_the_runs_with_identical_settings"
    t.claim("between two identical requests", "between the second and third requests alone, which are the same in every setting, the counts are "
            "{n}, {n} and {n}.", BR[a_][same_], BR[b_][same_], BR[third_][same_])
    t.claim("the options fund, three identical requests", "On the options fund all three requests were the same in every setting, and {n}, {n} "
            "and {n} of the {n} open figures changed, the {n} for the model with the fixed temperature.",
            BRO[a_][same_], BRO[b_][same_], BRO[third_][same_], open_options, BRO[third_][same_])
    t.checks += 1
    if any(b["runs_with_identical_settings"] != [1, 2, 3] or b["open_figures"] != open_options for b in BRO.values()):
        t.fail("the three requests of the options fund are not the same in every setting")
    t.claim("abstract, between runs", "Sent the same prompt three times, two of the three models returned different values for {n} of the swap "
            "fund's {n} open figures", ch[a_], open_swap)
    t.checks += 1
    if sum(v > 0 for v in ch.values()) != 2:
        t.fail("not exactly two models changed a value between runs")
    for m in MODELS.values():
        t.claim(f"drafts, {m}", "| `" + m + "` | {n} of {n} | {n} of {n} | {n} of {n} | {n} of {n} |",
                P["per_model"][m]["open_bare"], P["per_model"][m]["open_figures"], PL["per_model"][m]["open_bare"], PL["per_model"][m]["open_figures"],
                A["per_model"][m]["open_bare"], A["per_model"][m]["open_figures"], AL["per_model"][m]["open_bare"], AL["per_model"][m]["open_figures"])

    # ---- Section 5: a second reader
    t.claim("drafts read", "Each reader read the same {w} drafts", len({(r["fund"], r["name"]) for r in readings if r["mode"] == "draft"}))
    t.claim("readings", "That makes {n} readings.", C["readings"])
    t.claim("caught", "Readers flagged {n} of {n} open figures ({n}%) on the obvious reading and {n} of {n} ({n}%) to the letter. "
            "Wrong flags were {n} of {n} and {n} of {n}.",
            allr["caught"], allr["unsettled"], pct(allr["caught"], allr["unsettled"]), allrl["caught"], allrl["unsettled"],
            pct(allrl["caught"], allrl["unsettled"]), allr["false_alarms"], allr["settled"], allrl["false_alarms"], allrl["settled"])
    bm = {k: v["all readers"] for k, v in C["by_mode"].items()}
    t.claim("with and without a draft", "{n} of {n} open figures were flagged from the documents alone, {n} of {n} with a plain draft and "
            "{n} of {n} with a labelled one", bm["nodraft"]["caught"], bm["nodraft"]["unsettled"], bm["plain drafts"]["caught"],
            bm["plain drafts"]["unsettled"], bm["ask drafts"]["caught"], bm["ask drafts"]["unsettled"])
    t.claim("labelled against bare", "is flagged less often than a bare number: {n} of {n} against {n} of {n}.",
            bm["ask drafts"]["draft_bare_caught"], bm["ask drafts"]["draft_bare"], bm["plain drafts"]["draft_bare_caught"], bm["plain drafts"]["draft_bare"])
    t.claim("flags removed", "raised correctly: {n} of {n}.", allr["draft_flag_removed"], allr["draft_flagged"])
    v3 = C["three_readers_on_one_draft"]
    t.claim("two of three readers", "{n} of {n} open figures are flagged and {n} of {n} settled figures.",
            v3["caught_by_two_or_more"], v3["unsettled"], v3["flagged_by_two_or_more"], v3["settled"])
    t.claim("the same verdict three times", "in each of three runs for {n} of {n} answers.",
            C["repeated_without_a_draft_total"]["same_verdict_in_every_run"], C["repeated_without_a_draft_total"]["fields"])
    fk = C["false_alarms_by_kind"]
    t.claim("kinds of false alarm", "Of the {n} wrong flags, {n} are on a published NAV that depends on an open convention on the way and rounds to "
            "the same cent under every alternative, and {n} ask how posted collateral is recorded in the books, which changes no amount. "
            "Of the other {n}, {n} come from one reader.",
            allr["false_alarms"], fk["all readers"]["same to the cent"], fk["all readers"]["collateral line"], fk["all readers"]["other"],
            max(fk[m].get("other", 0) for m in MODELS.values()))
    rows_of_the_table = {"Day counts and day bases": "day counts and day bases",
             "Lot order, basket rounding, correction threshold, split of the reference": "lot order, basket rounding, correction threshold, split of the reference",
             "What a reset or payment date of the swap does": "what a reset or payment date does",
             "What a reduction of the swap realizes": "what a reduction of the swap realizes",
             "What an increase of the swap does to the gain so far": "what an increase of the swap does to the gain so far",
             "How the transaction fee is booked": "how the transaction fee is booked",
             "When income on the swap is accrued": "when swap income is accrued"}
    t.claim("second reading, the two groups", "Readers flagged {n} of {n} open figures of terms and parameters and {n} of {n} of accounting "
            "treatment; in the readings of a draft the counts are {n} of {n} and {n} of {n}.",
            CG[KP]["caught"], CG[KP]["verdicts"], CG[KT]["caught"], CG[KT]["verdicts"], CG[KP]["with_a_draft"]["caught"],
            CG[KP]["with_a_draft"]["verdicts"], CG[KT]["with_a_draft"]["caught"], CG[KT]["with_a_draft"]["verdicts"])
    t.counted("the group flagged less is the group labelled more",
              "The group that readers flag less is the one that the drafts had more often labelled as documented",
              share(CG[KT]) < share(CG[KP]) and share(AG[KT], "bare", "figures") > share(AG[KP], "bare", "figures"))
    t.claim("kinds and groups, formed afterwards", "The {w} kinds below and the {w} groups were formed after these readings had been scored.",
            len(kinds.KINDS), len(kinds.GROUPS))
    for row, k in rows_of_the_table.items():
        ck, tk, dk = C["by_kind_of_gap"][k], T["by_kind_of_gap"][k], A["by_kind_of_gap"][k]
        t.claim(f"second reading, {k}", "| " + row + " | {n} of {n} |\n", ck["caught"], ck["verdicts"])
        t.claim(f"the three tests, {k}", "| " + row + " | {n} of {n} | {n} of {n} | {n} of {n} |",
                dk["bare"], dk["figures"], ck["caught"], ck["verdicts"], tk["caught"], tk["verdicts"])
    for m in MODELS.values():
        r = C["all_readings"][m]
        t.claim(f"reader {m}", "| `" + m + "` | {n} of {n} | {n} of {n} |\n", r["caught"], r["unsettled"], r["false_alarms"], r["settled"])

    # ---- Section 6: rule by rule, and the fair test
    ta, tal = T["all"], TL["all"]
    t.claim("tracings", "three times: {n} tracings.", T["tracings"])
    t.claim("open rules flagged", "Readers flagged {n} of {n} open rules ({n}%) on the obvious reading and {n} of {n} ({n}%) to the letter.",
            ta["caught"], ta["open_rules"], pct(ta["caught"], ta["open_rules"]), tal["caught"], tal["open_rules"], pct(tal["caught"], tal["open_rules"]))
    t.claim("rule by rule, the two groups", "Of the open rules of accounting treatment, readers flagged {n} of {n}, and of terms and parameters "
            "{n} of {n}.", TG[KT]["caught"], TG[KT]["verdicts"], TG[KP]["caught"], TG[KP]["verdicts"])
    first = list(rows_of_the_table.values())
    t.claim("rows of accounting treatment", "its first {w} rows are accounting treatment", len(kinds.GROUPS[KT]))
    t.checks += 1
    with_three = [m.group(1) for m in re.finditer(r"^\| ([^|]+) \| " + r" \| ".join([NUM + " of " + NUM] * 3) + r" \|$", text, re.M)]
    labels = {v: k for k, v in rows_of_the_table.items()}
    if with_three[:len(kinds.GROUPS[KT])] != [labels[k] for k in kinds.GROUPS[KT]] or len(with_three) != len(first):
        t.fail("the first rows of the table of the three tests are not the kinds of accounting treatment, in the order of ds/kinds.py")
    t.counted("flagged least, flagged when asked", "The kinds of gap that a second reading of the figures flagged least are flagged when the question is asked.",
              all(share(C["by_kind_of_gap"][k]) < min(share(C["by_kind_of_gap"][q]) for q in kinds.GROUPS[KP]) for k in kinds.GROUPS[KT])
              and all(share(T["by_kind_of_gap"][k]) >= 0.85 for k in kinds.GROUPS[KT]))
    t.claim("answers and quotes", "Of the {n} answers, {n} are not stated and quote nothing. Each of the other {n} quotes its passage, and a "
            "program checked every quote against the text of the documents: all {n} are there word for word.",
            ta["answers"], ta["answers_not_stated"], ta["answers_that_name_a_passage"], ta["quotes_found"])
    t.checks += 1
    if (ta["answers_not_stated_with_a_quote"], ta["answers_that_name_a_passage_without_a_quote"], ta["quotes_too_short_to_check"]) != (0, 0, 0) \
            or ta["quotes"] != ta["answers_that_name_a_passage"] or ta["answers"] != ta["answers_not_stated"] + ta["answers_that_name_a_passage"]:
        t.fail("an answer that names a passage has no checked quote, or an answer of not stated has one")
    strict = T["stated_in_the_table_but_not_for_most_readers"]["rules"]
    on_strict = sum(e[k] for f in T["by_rule"].values() for r, e in f.items() if r in strict for k in ("partly", "not stated", "conflicting"))
    t.claim("stricter than the key", "the readers flagged {n} of {n} answers on rules that the key counts as stated, and {n} of the {n} fall on "
            "the {w} rules where the documents give the principle and not the mechanics. To the letter the count is {n} of {n}.",
            ta["false_alarms"], ta["stated_rules"], on_strict, ta["false_alarms"], len(strict), tal["false_alarms"], tal["stated_rules"])
    t.checks += 1
    if sorted(strict) != sorted(list(rules.LETTER) + list(opt_rules.LETTER)):
        t.fail("the rules most readers do not accept are not the rules that separate the two standards")
    t.claim("stable answers", "verdict in all three runs for {n} of {n} rules.",
            sum(v["same_flag_in_every_run"] for v in T["repeated"].values()), sum(v["rules"] for v in T["repeated"].values()))
    F, FL = T["third_fund"], TL["third_fund"]
    kr, kl = stat["Futures fund, obvious reading"], stat["Futures fund, to the letter"]
    t.claim("the list", "A list of {n} questions on exchange-traded futures", len(fut_questions.ASK))
    t.claim("agreement with the key", "agree with that key on {n} of {n} answers to the letter and on {n} of {n} on the obvious reading. "
            "All {n} quotes stand in the documents. The same verdict came back in all three runs for {n} of {n} questions. "
            "{w} of the {w} answers was not valid JSON",
            FL["verdicts_that_agree_with_the_key_on_stated_or_not"], FL["verdicts_outside_the_conflict_rules"],
            F["verdicts_that_agree_with_the_key_on_stated_or_not"], F["verdicts_outside_the_conflict_rules"], F["all"]["quotes_found"],
            F["same_flag_in_every_run"]["same"], F["same_flag_in_every_run"]["rules"],
            F["answers_that_were_not_valid_json_and_were_read_as_text"], F["tracings"])
    t.checks += 1
    if F["all"]["quotes_found"] != F["all"]["quotes"] or F["all"]["quotes"] != F["all"]["answers_that_name_a_passage"] \
            or F["all"]["answers_that_name_a_passage_without_a_quote"] or F["all"]["quotes_too_short_to_check"]:
        t.fail("not every quote of the third fund's tracings was found, or an answer that names a passage has no checked quote")
    h = D["as_read_by_hand"]
    t.claim("disagreements", "The {n} disagreements to the letter were read one by one against the passages that the readers quoted. {n} are "
            "errors of the key: a sentence that its author had overlooked, and a yes-or-no question graded as stated in part. {n} are "
            "questions in two parts where the reader accepted the part that is stated. {n} are readers asking for more than the question asked.",
            D["total"], h["the key was wrong"], h["a question in two parts, one part stated"], h["the reader asked for more than the question"])
    t.claim("the list as a checklist", "by the key, {n} of its {n} questions are not fully answered to the letter and {n} on the obvious reading",
            sum(kl.values()) - kl["specified"], sum(kl.values()), sum(kr.values()) - kr["specified"])
    pr = F["what_the_list_leaves_out"]
    t.claim("what the list leaves out", "the {w} readers made {n} suggestions. All {w} named the day on which a trade first enters the NAV, "
            "which the list lacked and the documents state. By the readers' own verdicts, {n} of the {n} are things that the documents state "
            "and {n} things that they state in part. {w} is something that the documents omit.",
            pr["readers"], pr["additions"], pr["readers_that_ask_on_which_day_a_trade_first_enters_the_nav"], pr["stated"], pr["additions"],
            pr["partly"], pr["not stated"])

    # ---- Section 7: the documents themselves
    mid, oth = S["options"]["drafts_with_the_word_midpoint"], C["options_readings_that_name_the_other_pricing_rule"]
    t.claim("the other pricing rule", "{w} of the {n} drafts on that fund contains the word midpoint, and {w} of the {n} second readings names "
            "the other rule.", mid["with_the_word"], mid["drafts"], oth["naming"], oth["readings"])
    br = T["by_reader"]
    one = max(br, key=lambda m: br[m]["conflict_reported"])
    rest = [m for m in br if m != one]
    t.claim("the conflict, rule by rule", "one reader reported the disagreement in {n} of its {n} answers on the pricing questions and quoted the "
            "three documents side by side. The other two answered from the prospectus in {n} of {n}.",
            br[one]["conflict_reported"], br[one]["conflict_rules"], sum(br[m]["conflict_called_stated"] for m in rest),
            sum(br[m]["conflict_rules"] for m in rest))
    acc = S["swap"]["shown"]["S05.net_effect_on_net_assets_on_ex_date"]
    on_ex = sum(v is not None and abs(v) < 0.005 for arm in acc.values() for vals in arm.values() for v, _ in vals)
    dq = S["swap"]["drafts_that_quote_the_dividend_sentence_in_a_requirement"]
    bare = sum(x == "bare" for arm in S["the_rule_behind_the_real_restatement"].values() for xs in arm.values() for x in xs)
    t.claim("income on the swap", "All {n} drafts on that fund accrued the income on the ex-dividend date, {n} of them quote the sentence in a "
            "requirement, and {n} present the resulting figure as settled.", on_ex, dq["quoting"], bare)
    t.checks += 1
    if on_ex != dq["drafts"]:
        t.fail("not every draft accrued the income on the ex-dividend date, 'All' is wrong")

    # ---- Section 8: corrections
    t.claim("the key before the corrections", "After the first {w} drafts, the key for the swap fund counted {n} of {n} figures as settled.",
            len(J("draft_scores.json")), G0["figures_settled"], G0["figures"])
    t.claim("the key after two rounds", "After two rounds of corrections the count was {n}.", G1["figures_settled"])
    t.claim("the key after the readers", "After the second reading it became {n}.", G["figures_settled"])
    t.claim("rules moved in the first round", "{w} of the {w} rules that separate the two standards had been moved to stated in the first round",
            len(rules.LETTER), differ)
    short = [x["quote"].strip() for tr in J("traces.json") if tr["fund"] in ("swap", "options") for x in tr["rows"] if x["quote_check"] == "found, short"]
    min_piece = __import__("score_trace").MIN_PIECE
    t.claim("the short quotes", "had left {w} of them unchecked because they are shorter than {n} characters. They are the same {w} words in {w} "
            "answers, on the size of an option contract. A quotation that short is now compared as a whole, all {w} are in the documents, and "
            "the count of quotes checked rose from {n} to {n}.",
            ta["quotes_found_short"], min_piece, len(short[0].split()) if short else None, len(short), len(short),
            ta["quotes"] - ta["quotes_found_short"], ta["quotes"])
    t.checks += 1
    if len(set(short)) != 1 or any(len(q) >= min_piece for q in short) or len(short) != ta["quotes_found_short"] \
            or {x["rule"] for tr in J("traces.json") for x in tr["rows"] if x["quote_check"] == "found, short"} != {"O04"}:
        t.fail("the short quotes are not one phrase, on the size of an option contract, shorter than the minimum")

    # ---- Sections 3, 9 and 10: sentences without a figure, counted over all cases
    t.claim("two groups", "What is left open falls into {w} groups", len(kinds.GROUPS))
    t.claim("kinds and groups, in the limitations", "The {w} kinds of gap and the {w} groups were formed after the results had been seen",
            len(kinds.KINDS), len(kinds.GROUPS))
    t.counted("two of three models, most of the accounting treatment",
              "two of the three models still labelled most of the accounting treatment as documented",
              sorted(2 * v["bare"] > v["figures"] for v in AG[KT]["per_model"].values()) == [False, True, True])
    t.counted("nearly every term and parameter, fewer than half of the accounting treatment",
              "flagged nearly every term and parameter and fewer than half of the figures of accounting treatment, which is the group that the "
              "drafts had more often labelled as documented",
              share(CG[KP]) >= 0.95 and 2 * CG[KT]["caught"] < CG[KT]["verdicts"] and share(AG[KT], "bare", "figures") > share(AG[KP], "bare", "figures"))
    t.counted("nearly every open rule of both groups",
              "the same models flagged nearly every open rule of both groups and quoted a passage wherever they named one",
              share(TG[KT]) >= 0.95 and share(TG[KP]) >= 0.95 and ta["answers_that_name_a_passage_without_a_quote"] == 0)
    t.counted("a model filled what was missing with a number", "a model that drafted requirements from a fund's documents filled what was missing with a number",
              share(P["open_total"], "bare", "figures") >= 0.9)
    pr_ = F["what_the_list_leaves_out"]
    t.counted("only what the documents already mention",
              "When asked what a list leaves out, they proposed only what, by their own verdicts, the documents already mention.",
              pr_["not stated"] == 0 and pr_["other"] == 0 and pr_["stated"] + pr_["partly"] == pr_["additions"] > 0)
    t.counted("no model in these tests produced the list", "No model in these tests produced the list.", pr_["readers"] == len(MODELS))

    # ---- outside the scanned sections
    probe_tokens = 0
    for reader in os.listdir(os.path.join(OUT, "probes", "futures")):
        with open(os.path.join(OUT, "probes", "futures", reader, "run1", "run.json"), encoding="utf-8") as fh:
            probe_tokens += (json.load(fh).get("usage") or {}).get("total_tokens") or 0
    t.claim("tokens", "The calls recorded here used {n} tokens in all.",
            S["swap"]["tokens"] + S["options"]["tokens"] + C["tokens"] + T["tokens"] + F["tokens"] + probe_tokens)
    prior = os.path.join(OUT, "drafts_prior")              # attempts that ended at the limit and were repeated (draft.py)
    cut = []
    for name in sorted(os.listdir(prior)) if os.path.isdir(prior) else []:
        with open(os.path.join(prior, name, "run.json"), encoding="utf-8") as fh:
            cut.append(json.load(fh))
    t.claim("the draft that was cut off", "{w} draft ended at the limit on the length of the answer; it was set aside and the request repeated "
            "once with twice the limit, the attempt that was cut off is kept in the repository, and its {n} tokens are not in that total.",
            len(cut), sum((c.get("usage") or {}).get("total_tokens") or 0 for c in cut))
    t.checks += 1
    again = S["swap"]["between_requests"]["ask"].get(cut[0]["model"], {}) if len(cut) == 1 else {}
    if len(cut) != 1 or cut[0]["finish_reason"] != "length" or cut[0]["arm"] != "ask" \
            or again.get("limit_on_the_answer_by_run", {}).get("1") != 2 * cut[0]["max_tokens"] or not again.get("every_answer_finished"):
        t.fail("the attempt that was cut off is not one draft that ended at its limit and was repeated with twice the limit")
    t.claim("scenarios", "of {w} scenarios per fund from constructed positions", G["scenarios"])
    t.claim("answers of the key shown wrong", "the readers' quotations showed {w} of its answers to be wrong",
            sum(v == "the key was wrong" for v in __import__("score_trace").ADJUDICATED.values()))
    t.has("the example question", "*On which date is income owed to the fund under the swap accrued?*", "*" + rules.RULES["R19"]["ask"] + "*")
    with open(os.path.join(HERE, "docs", "05-msox-nav-restatement-press-release-2026-03-06.md"), encoding="utf-8") as fh:
        note = fh.read()
    quote = re.search(r'gave the cause as "([^"]+)"', re.sub(r"\s+", " ", text))
    t.has("the sponsor's words", quote.group(1) if quote else "(no quotation found)", note)
    t.has("the count of restated dates", "18 dates", note)
    t.checks += 1
    if "restated NAVs for eighteen dates" not in re.sub(r"\s+", " ", text):
        t.fail("the count of restated dates is not written as in the note")
    body = text[text.index("<!-- written by: python tieout.py appendix -->"):text.index("## Appendix B")].split("-->", 1)[1].strip()
    t.checks += 1
    if body != appendix().strip():
        t.fail("Appendix A is not what `python tieout.py appendix` prints")
    t.checks += 1
    listed = os.path.join(HERE, "QUESTIONS.md")
    if not os.path.exists(listed) or open(listed, encoding="utf-8").read() != questions():
        t.fail("QUESTIONS.md is not what `python tieout.py questions` prints")
    t.counted("the three lists are published", "The three lists of questions are published with the report.",
              len(rules.ASK) == len(rules.RULES) and len(opt_rules.ASK) == len(opt_rules.RULES) and len(fut_questions.ASK) == len(fut_key.KEY))
    return t


def main(argv: list[str]) -> int:
    if len(argv) > 1 and argv[1] == "appendix":
        sys.stdout.write(appendix())
        return 0
    if len(argv) > 1 and argv[1] == "questions":          # python tieout.py questions --write   rewrites QUESTIONS.md
        if "--write" in argv:
            with open(os.path.join(HERE, "QUESTIONS.md"), "w", encoding="utf-8", newline="\n") as fh:
                fh.write(questions())
            print("wrote QUESTIONS.md")
        else:
            sys.stdout.buffer.write(questions().encode("utf-8"))
        return 0
    with open(PAPER, encoding="utf-8") as fh:
        text = fh.read()
    t = run(text)
    loose = uncovered(t)
    for x in loose:
        print("  NOT COVERED " + x)
    print(f"TIE-OUT {'FAILED' if t.fails or loose else 'PASSED'}: {t.checks} checks, {t.fails} failed, "
          f"{len(t.covered)} figures in digits covered, {len(loose)} not covered")
    if "--mutate" in argv:
        slipped = 0
        for a, b, what in t.covered:
            tok = text[a:b]
            v, d = shown(tok)
            new = f"{v + 10 ** (-d):,.{d}f}" if "," in tok else f"{v + 10 ** (-d):.{d}f}"
            if run(text[:a] + new + text[b:], quiet=True).fails == 0:
                slipped += 1
                print(f"  SLIPPED {tok} -> {new} ({what})")
        print(f"MUTATION TEST {'FAILED' if slipped else 'PASSED'}: {len(t.covered)} figures moved by one unit, {slipped} not noticed")
        return 1 if (t.fails or loose or slipped) else 0
    return 1 if (t.fails or loose) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

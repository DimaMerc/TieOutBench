"""Score the rule-by-rule tracings in data/out/traces against the rule table.

  python score_trace.py             all tracings found; writes data/out/traces.json and traces_summary.json
  python score_trace.py stated      open rules a reader called "stated", with the passage it quoted (to read by hand)
  python score_trace.py alarms      rules the table counts as stated that a reader did not, with its words
  python score_trace.py quotes      quotes that are not in the documents word for word

For each tracing and each rule:
  key      specified / partly / absent (the rule table; the reader never sees it)
  verdict  the reader's stated / partly / not stated / conflicting
A reader FLAGS a rule by any verdict other than "stated". It CATCHES an open rule (partly or absent) by flagging
it, and raises a FALSE ALARM by flagging a rule the table counts as stated. Two rules of the options fund are a
test of their own: the fund's documents give different pricing rules, so "conflicting" is the full answer there
and "stated" follows one of the documents; neither is counted as an error.
Every quote is checked against the text of the documents: a quote counts as found when each of its pieces (a quote
may be cut with "...") stands in the documents word for word, apart from spacing, quotation marks and letter case.
"""
from __future__ import annotations

import json
import os
import re
import sys

import score_drafts as SD
from draft import GRID
from ds import kinds, standard
from ds.funds import FUNDS

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data", "out")
TRACES =os.path.join(OUT, "traces")
READERS = tuple(GRID)
# The prospectus, the annual report and the SAI give different pricing rules. O05 and O06 were known before the
# tracings; O07 (no model price from the exchange: the prospectus names a backup provider, the annual report goes
# straight to the Valuation Designee, the SAI's general rule takes the midpoint) was found by a reader and added.
CONFLICT_RULES = {"O05", "O06", "O07"}
KINDS = kinds.KINDS
MIN_PIECE = 25          # a piece of a quote shorter than this is not looked for on its own
MIN_WHOLE = 12          # a quote with no piece that long is compared as a whole, when it has at least this many characters
FUNDS_WITH_A_REFERENCE = ("swap", "options")     # the third fund ("futures") has a blind question list only; it is reported apart
# The third fund's disagreements between readers and the key, to the letter, each read by hand on 2026-11-16 against
# the passage the reader quoted. The key (ds/fut_key.py) was not changed afterwards.
ADJUDICATED = {
    "F05": "the key was wrong",                              # a sentence on changes in fair value that the key had overlooked
    "F25": "the key was wrong",                              # a yes-or-no question that the key graded "partly"
    "F09": "a question in two parts, one part stated",
    "F03": "a question in two parts, one part stated",
    "F19": "a question in two parts, one part stated",
    "F22": "the reader asked for more than the question",
    "F07": "the reader asked for more than the question",
}
EXPECT = {"specified": "stated", "partly": "partly", "absent": "not stated"}


def norm(s: str) -> str:
    s = s.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"').replace("—", "-").replace("–", "-")
    return re.sub(r"\s+", " ", s).strip().lower()


def pieces(quote: str) -> list[str]:
    """A quote as the pieces that have to be found: cut at ellipses and at the usual joins between two passages."""
    parts = re.split(r"\[\s*\.\.\.\s*\]|\.\.\.+|…|\s[|/]{1,2}\s|\n+|\"\s*(?:and|;|,)\s*\"|\"\s+\"", quote)
    out = []
    for p in parts:
        p = norm(p).strip(" \"'.,;:()[]")
        p = re.sub(r"^\(?[a-z0-9]\)\s+|^(prospectus|sai|annual( report| financial statements)?|statement of additional information)\s*[:\-]\s*", "", p)
        if len(p) >= MIN_PIECE:
            out.append(p)
    return out


def check_quote(quote: str, pack: str) -> str:
    """found / partly found / not found for a quote with at least one piece of MIN_PIECE characters. A shorter quote
    is compared as a whole: "found, short" when the whole of it stands in the text, "not found" when it does not,
    and "too short to check" below MIN_WHOLE characters or three words. (Until 2026-11-18 every quote without a long
    piece was left unchecked; six answers of the two funds, all the same four words, were of that kind.)"""
    if not quote or not quote.strip():
        return "no quote"
    ps = pieces(quote)
    if not ps:
        whole = norm(quote).strip(" \"'.,;:()[]")
        if len(whole) < MIN_WHOLE or len(whole.split()) < 3:
            return "too short to check"
        return "found, short" if whole in pack else "not found"

    def there(p: str) -> bool:
        if p in pack:
            return True
        # two passages quoted one after the other without a mark between them: every sentence has to be found
        ss = [s.strip(" \"'.,;:()[]") for s in re.split(r"(?<=[.;:!?])\s+", p)]
        ss = [s for s in ss if len(s) >= MIN_PIECE]
        return bool(ss) and all(s in pack for s in ss)

    found = sum(there(p) for p in ps)
    return "found" if found == len(ps) else ("partly found" if found else "not found")


def verdict_of(c) -> tuple[str, str, str]:
    if not isinstance(c, dict):
        return "missing", "", ""
    v = str(c.get("verdict") or "").strip().lower()
    quote, missing = str(c.get("quote") or ""), str(c.get("missing") or "")
    if v.startswith("stated"):
        return "stated", quote, missing
    if v.startswith("part"):
        return "partly", quote, missing
    if v.startswith("not"):
        return "not stated", quote, missing
    if v.startswith("conflict"):
        return "conflicting", quote, missing
    return "unclear", quote, missing


def salvage(raw: str) -> dict:
    """An answer that is complete but not valid JSON (a quotation mark left unescaped inside a quote): take each
    question's block as text and read the three fields from it. The tracing is marked as salvaged."""
    out = {}
    marks = [(m.group(1), m.start()) for m in re.finditer(r'"(Q\d{1,2})"\s*:\s*\{', raw)]
    for n, (q, a) in enumerate(marks):
        block = raw[a:marks[n + 1][1]] if n + 1 < len(marks) else raw[a:]
        v = re.search(r'"verdict"\s*:\s*"([^"]*)"', block)
        qt = re.search(r'"quote"\s*:\s*"(.*?)"\s*,\s*"missing"', block, re.S)
        ms = re.search(r'"missing"\s*:\s*"(.*?)"\s*\}', block, re.S)
        out[q] = {"verdict": v.group(1) if v else "", "quote": (qt.group(1) if qt else "").replace('\\"', '"').replace("\\n", "\n"),
                  "missing": (ms.group(1) if ms else "").replace('\\"', '"')}
    return {"answers": out, "_salvaged": True} if out else {"_unparsed": "json"}


def tracing(fund: str, reader: str, run: int, pack: str) -> dict:
    d = os.path.join(TRACES, fund, reader, f"run{run}")
    ans = SD.parse(os.path.join(d, "raw.txt"))
    if "_unparsed" in ans:
        with open(os.path.join(d, "raw.txt"), encoding="utf-8") as fh:
            ans = salvage(fh.read())
    with open(os.path.join(d, "run.json"), encoding="utf-8") as fh:
        rec = json.load(fh)
    got = ans.get("answers") if isinstance(ans.get("answers"), dict) else {}
    got = {re.sub(r"^Q0*(\d+)$", lambda m: f"Q{int(m.group(1)):02d}", str(k).strip().upper()): v for k, v in got.items()}
    R = FUNDS[fund]["rules"].RULES
    rows = []
    for q, rid in rec["questions"].items():
        v, quote, missing = verdict_of(got.get(q))
        status = FUNDS[fund]["rules"].status(rid)
        rows.append({"q": q, "rule": rid, "kind": R[rid]["kind"], "status": status, "conflict_rule": rid in CONFLICT_RULES,
                     "verdict": v, "flagged": v in ("partly", "not stated", "conflicting"),
                     "exact": v == EXPECT[status], "quote_check": check_quote(quote, pack),
                     "quote": quote[:500], "missing": missing[:300]})
    return {"fund": fund, "reader": reader, "run": run, "finish_reason": rec.get("finish_reason"),
            "parsed": "_unparsed" not in ans, "salvaged": bool(ans.get("_salvaged")), "usage": rec.get("usage"), "rows": rows}


def implied(fund: str, t: dict) -> dict:
    """What the tracing implies figure by figure: a figure is flagged when a rule it needs is flagged."""
    flag = {x["rule"]: x["flagged"] and not (x["conflict_rule"] and x["verdict"] == "conflicting") for x in t["rows"]}
    rules = FUNDS[fund]["rules"]
    U = S = cu = fa = 0
    for s in (FUNDS[fund]["scenarios"].build() if FUNDS[fund].get("scenarios") else []):
        for field, need in s["needs"].items():
            f = any(flag.get(r, False) for r in need)
            if rules.settled(need):
                S += 1
                fa += f
            else:
                U += 1
                cu += f
    return {"unsettled": U, "caught": cu, "settled": S, "false_alarms": fa}


def tally(rows: list[dict]) -> dict:
    O = [r for r in rows if r["status"] != "specified"]
    P = [r for r in rows if r["status"] == "specified" and not r["conflict_rule"]]
    C = [r for r in rows if r["conflict_rule"]]
    Q = [r for r in rows if r["quote_check"] not in ("no quote", "too short to check")]
    N = [r for r in rows if r["verdict"] == "not stated"]
    W = [r for r in rows if r["verdict"] in ("stated", "partly", "conflicting")]
    return {"answers": len(rows), "answers_not_stated": len(N), "answers_not_stated_with_a_quote": sum(r["quote_check"] != "no quote" for r in N),
            "answers_that_name_a_passage": len(W), "answers_that_name_a_passage_without_a_quote": sum(r["quote_check"] == "no quote" for r in W),
            "quotes_found_short": sum(r["quote_check"] == "found, short" for r in Q),
            "quotes_too_short_to_check": sum(r["quote_check"] == "too short to check" for r in rows),
            "open_rules": len(O), "caught": sum(r["flagged"] for r in O), "called_stated": sum(r["verdict"] == "stated" for r in O),
            "stated_rules": len(P), "false_alarms": sum(r["flagged"] for r in P), "no_verdict": sum(r["verdict"] in ("missing", "unclear") for r in rows),
            "exact_status": sum(r["exact"] for r in rows if not r["conflict_rule"]), "rules_without_the_conflict_pair": len(rows) - len(C),
            "conflict_rules": len(C), "conflict_reported": sum(r["verdict"] == "conflicting" for r in C),
            "conflict_called_stated": sum(r["verdict"] == "stated" for r in C),
            "conflicting_elsewhere": sum(r["verdict"] == "conflicting" for r in rows if not r["conflict_rule"]),
            "quotes": len(Q), "quotes_found": sum(r["quote_check"] in ("found", "found, short") for r in Q),
            "quotes_partly_found": sum(r["quote_check"] == "partly found" for r in Q), "quotes_not_found": sum(r["quote_check"] == "not found" for r in Q)}


def collect() -> list[dict]:
    out = []
    for fund in FUNDS:
        with open(os.path.join(HERE, FUNDS[fund]["pack"], "documents.md"), encoding="utf-8") as fh:
            pack = norm(fh.read())
        for reader in READERS:
            d = os.path.join(TRACES, fund, reader)
            for name in sorted(os.listdir(d)) if os.path.isdir(d) else []:
                if re.fullmatch(r"run\d+", name) and os.path.exists(os.path.join(d, name, "raw.txt")) and os.path.exists(os.path.join(d, name, "run.json")):
                    t = tracing(fund, reader, int(name[3:]), pack)
                    t["implied"] = implied(fund, t)
                    out.append(t)
    return out


def probes(fund: str = "futures") -> dict:
    """The one call per reader that asked what the list of questions leaves out (trace.py --probe)."""
    base = os.path.join(OUT, "probes", fund)
    out = {"readers": 0, "additions": 0, "stated": 0, "partly": 0, "not stated": 0, "other": 0,
           "readers_that_ask_on_which_day_a_trade_first_enters_the_nav": 0, "questions": {}}
    day = re.compile(r"trade date|daily nav (determination|calculation)|reflected in (the )?(daily )?nav|recognized for (financial reporting|daily nav)", re.I)
    for reader in sorted(os.listdir(base)) if os.path.isdir(base) else []:
        p = os.path.join(base, reader, "run1", "raw.txt")
        if not os.path.exists(p):
            continue
        adds = SD.parse(p).get("additions") or []
        out["readers"] += 1
        out["questions"][reader] = [{"verdict": str(a.get("verdict")), "question": str(a.get("question"))[:240]} for a in adds if isinstance(a, dict)]
        for a in out["questions"][reader]:
            out["additions"] += 1
            v = a["verdict"].strip().lower()
            out["stated" if v.startswith("stated") else "partly" if v.startswith("part") else "not stated" if v.startswith("not") else "other"] += 1
        out["readers_that_ask_on_which_day_a_trade_first_enters_the_nav"] += any(day.search(a["question"]) for a in out["questions"][reader])
    return out


def rows_of(ts: list[dict], **want) -> list[dict]:
    return [x for t in ts if all(t.get(k) == v for k, v in want.items()) for x in t["rows"]]


def add(a: dict, b: dict) -> dict:
    return {k: a.get(k, 0) + v for k, v in b.items()}


def summarise(ts: list[dict]) -> dict:
    S = {"tracings": len(ts), "all_finished_and_parsed": all(t["finish_reason"] == "stop" and t["parsed"] for t in ts),
         "answers_that_were_not_valid_json_and_were_read_as_text": sum(bool(t.get("salvaged")) for t in ts),
         "verdicts": sum(len(t["rows"]) for t in ts),
         "verdicts_that_agree_with_the_key_on_stated_or_not": sum(x["flagged"] == (x["status"] != "specified") for t in ts for x in t["rows"] if not x["conflict_rule"]),
         "verdicts_outside_the_conflict_rules": sum(not x["conflict_rule"] for t in ts for x in t["rows"]),
         "tokens": sum((t.get("usage") or {}).get("total_tokens") or 0 for t in ts),
         "all": tally(rows_of(ts)), "by_reader": {r: tally(rows_of(ts, reader=r)) for r in READERS},
         "by_fund": {f: tally(rows_of(ts, fund=f)) for f in FUNDS}, "by_kind_of_gap": {}, "by_rule": {}, "implied_by_figure": {}, "repeated": {}}
    for label, ids in KINDS.items():
        rows = [x for x in rows_of(ts) if x["rule"] in ids]
        S["by_kind_of_gap"][label] = {"verdicts": len(rows), "caught": sum(x["flagged"] for x in rows)}
    S["by_group_of_gap"] = {}                        # the two groups of ds/kinds.py: open rules only
    for g in list(kinds.GROUPS) + [None]:
        rows = [x for x in rows_of(ts) if x["status"] != "specified" and kinds.group_of_rule(x["rule"]) == g]
        if rows or g is not None:
            S["by_group_of_gap"][g or "in no kind"] = {"verdicts": len(rows), "caught": sum(x["flagged"] for x in rows)}
    for t in ts:
        for x in t["rows"]:
            e = S["by_rule"].setdefault(t["fund"], {}).setdefault(x["rule"], {"status": x["status"], "stated": 0, "partly": 0, "not stated": 0,
                                                                              "conflicting": 0, "unclear": 0, "missing": 0})
            e[x["verdict"]] += 1
    imp = {"all": {}, **{r: {} for r in READERS}}
    for t in ts:
        imp["all"] = add(imp["all"], t["implied"])
        imp[t["reader"]] = add(imp[t["reader"]], t["implied"])
    S["implied_by_figure"] = imp
    for fund in FUNDS:
        for reader in READERS:
            rs = [t for t in ts if t["fund"] == fund and t["reader"] == reader]
            if len(rs) > 1:
                per = [{x["rule"]: x["verdict"] for x in t["rows"]} for t in rs]
                S["repeated"][f"{fund}/{reader}"] = {"runs": len(rs), "rules": len(per[0]),
                                                     "same_verdict_in_every_run": sum(len({p[k] for p in per}) == 1 for k in per[0]),
                                                     "same_flag_in_every_run": sum(len({p[k] != "stated" for p in per}) == 1 for k in per[0])}
    votes = {}
    for t in ts:
        for x in t["rows"]:
            votes.setdefault((t["fund"], x["rule"]), {"status": x["status"], "conflict": x["conflict_rule"], "flags": 0, "n": 0})
            votes[(t["fund"], x["rule"])]["flags"] += x["flagged"]
            votes[(t["fund"], x["rule"])]["n"] += 1
    O = [v for v in votes.values() if v["status"] != "specified"]
    P = [v for v in votes.values() if v["status"] == "specified" and not v["conflict"]]
    # Rules the table counts as stated and most tracings do not: the readers hold to the letter, the table had
    # accepted the obvious reading. What the count of settled figures would be on the readers' standard:
    strict = sorted(rid for (fund, rid), v in votes.items() if v["status"] == "specified" and not v["conflict"] and 2 * v["flags"] > v["n"])
    S["stated_in_the_table_but_not_for_most_readers"] = {"rules": strict, "figures": {}}
    for fund in FUNDS:
        rules = FUNDS[fund]["rules"]
        n = moved = unsettled = 0
        for s in (FUNDS[fund]["scenarios"].build() if FUNDS[fund].get("scenarios") else []):
            for need in s["needs"].values():
                n += 1
                if not rules.settled(need):
                    unsettled += 1
                elif any(r in strict for r in need):
                    moved += 1
        S["stated_in_the_table_but_not_for_most_readers"]["figures"][fund] = {
            "figures": n, "not_settled_in_the_table": unsettled, "more_on_the_readers_standard": moved}
    S["across_the_nine_tracings_of_a_fund"] = {
        "open_rules": len(O), "flagged_in_all": sum(v["flags"] == v["n"] for v in O), "flagged_in_most": sum(2 * v["flags"] > v["n"] for v in O),
        "flagged_in_none": sum(v["flags"] == 0 for v in O),
        "stated_rules": len(P), "flagged_in_most_although_stated": sum(2 * v["flags"] > v["n"] for v in P),
        "never_flagged_stated": sum(v["flags"] == 0 for v in P)}
    return S


def main(argv: list[str]) -> int:
    ts = collect()
    what = argv[1] if len(argv) > 1 else ""
    if what in ("stated", "alarms", "quotes"):
        n = 0
        for t in ts:
            for x in t["rows"]:
                hit = ((what == "stated" and x["status"] != "specified" and x["verdict"] == "stated") or
                       (what == "alarms" and x["status"] == "specified" and x["flagged"] and not x["conflict_rule"]) or
                       (what == "quotes" and x["quote_check"] in ("not found", "partly found")))
                if hit:
                    n += 1
                    print(f"{t['fund']:<8}{t['reader']:<18}run{t['run']} {x['rule']} [{x['status']:<9}] {x['verdict']:<11} {x['quote_check']:<13} "
                          f"QUOTE: {x['quote'][:230]} || MISSING: {x['missing'][:170]}")
        print(n, what)
        return 0
    everything = ts
    third = [t for t in ts if t["fund"] not in FUNDS_WITH_A_REFERENCE]
    ts = [t for t in ts if t["fund"] in FUNDS_WITH_A_REFERENCE]
    S = summarise(ts)
    if third:                                       # the blind test, reported apart from the two funds above
        T3 = summarise(third)
        S["third_fund"] = {k: T3[k] for k in ("tracings", "all_finished_and_parsed", "answers_that_were_not_valid_json_and_were_read_as_text",
                                              "verdicts", "verdicts_that_agree_with_the_key_on_stated_or_not", "verdicts_outside_the_conflict_rules",
                                              "tokens", "all", "by_reader", "by_rule", "repeated", "across_the_nine_tracings_of_a_fund")}
        dis = {"total": 0, "by_question": {}, "as_read_by_hand": {}}
        for t in third:
            for x in t["rows"]:
                if x["flagged"] != (x["status"] != "specified"):
                    dis["total"] += 1
                    dis["by_question"][x["rule"]] = dis["by_question"].get(x["rule"], 0) + 1
                    kind = ADJUDICATED.get(x["rule"], "not read") if standard.NAME == "letter" else "not read (the reading was done to the letter)"
                    dis["as_read_by_hand"][kind] = dis["as_read_by_hand"].get(kind, 0) + 1
        S["third_fund"]["disagreements_with_the_key"] = dis
        S["third_fund"]["what_the_list_leaves_out"] = probes()
        S["third_fund"]["same_flag_in_every_run"] = {"rules": sum(v["rules"] for v in T3["repeated"].values()),
                                                     "same": sum(v["same_flag_in_every_run"] for v in T3["repeated"].values())}
    with open(os.path.join(OUT, standard.tag("traces.json")), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(everything, fh, indent=1)
    with open(os.path.join(OUT, standard.tag("traces_summary.json")), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(S, fh, indent=1)

    def line(label, t):
        return (f"  {label:<22} open rules caught {t['caught']}/{t['open_rules']}  (called stated {t['called_stated']})   false alarms {t['false_alarms']}/{t['stated_rules']}   "
                f"exact status {t['exact_status']}/{t['rules_without_the_conflict_pair']}   conflict pair: reported {t['conflict_reported']}, called stated {t['conflict_called_stated']} of {t['conflict_rules']}"
                f"   'conflicting' elsewhere {t['conflicting_elsewhere']}   quotes found {t['quotes_found']}/{t['quotes']} (partly {t['quotes_partly_found']}, not {t['quotes_not_found']})")

    print(f"tracings {S['tracings']}; all finished and parsed: {S['all_finished_and_parsed']}; tokens {S['tokens']:,}")
    print(line("all", S["all"]))
    for k, v in S["by_reader"].items():
        print(line(k, v))
    for k, v in S["by_fund"].items():
        print(line(k, v))
    print("\ncaught, by the kind of gap")
    for label, v in S["by_kind_of_gap"].items():
        print(f"  {v['caught']:>3} of {v['verdicts']:<4} {label}")
    print("\ncaught, by the group of the open rule")
    for label, v in S["by_group_of_gap"].items():
        print(f"  {v['caught']:>3} of {v['verdicts']:<4} {label}")
    a = S["all"]
    print(f"\nanswers {a['answers']}: not stated {a['answers_not_stated']} (with a quote {a['answers_not_stated_with_a_quote']}), naming a passage "
          f"{a['answers_that_name_a_passage']} (without a quote {a['answers_that_name_a_passage_without_a_quote']}); quotes checked {a['quotes']}, "
          f"found {a['quotes_found']} (of which short and compared whole {a['quotes_found_short']}), too short to check {a['quotes_too_short_to_check']}")
    print("\nverdicts by rule (stated / partly / not stated / conflicting), the nine tracings of each fund")
    for fund, rules in S["by_rule"].items():
        R = FUNDS[fund]["rules"].RULES
        for rid, e in rules.items():
            print(f"  {rid} [{e['status']:<9}] {e['stated']} / {e['partly']} / {e['not stated']} / {e['conflicting']}   {R[rid]['ask'][:92]}")
    print("\nimplied figure by figure (a figure is flagged when a rule it needs is flagged):")
    for who, v in S["implied_by_figure"].items():
        print(f"  {who:<20} caught {v['caught']}/{v['unsettled']}   false alarms {v['false_alarms']}/{v['settled']}")
    print("\nrepeated:")
    for k, v in S["repeated"].items():
        print(f"  {k:<28} {json.dumps(v)}")
    print("\nacross the nine tracings of a fund:", json.dumps(S["across_the_nine_tracings_of_a_fund"]))
    print("stated in the table but not for most readers:", json.dumps(S["stated_in_the_table_but_not_for_most_readers"]))
    if third:
        T = S["third_fund"]
        print(f"\n== THE THIRD FUND (question list written blind): tracings {T['tracings']}; all finished and parsed: {T['all_finished_and_parsed']}; "
              f"read as text because not valid JSON: {T['answers_that_were_not_valid_json_and_were_read_as_text']}; tokens {T['tokens']:,}")
        print(f"  verdicts that agree with the key on stated-or-not: {T['verdicts_that_agree_with_the_key_on_stated_or_not']} of {T['verdicts_outside_the_conflict_rules']}")
        print(line("all", T["all"]))
        for k, v in T["by_reader"].items():
            print(line(k, v))
        R = FUNDS["futures"]["rules"]
        print("  verdicts by question (stated / partly / not stated / conflicting), key under this standard in brackets")
        for rid, e in T["by_rule"]["futures"].items():
            print(f"  {rid} [{R.status(rid):<9}] {e['stated']} / {e['partly']} / {e['not stated']} / {e['conflicting']}   {R.RULES[rid]['ask'][:96]}")
        for k, v in T["repeated"].items():
            print(f"  {k:<28} {json.dumps(v)}")
        print("  across the nine tracings:", json.dumps(T["across_the_nine_tracings_of_a_fund"]))
        print("  same flag in every run:", json.dumps(T["same_flag_in_every_run"]))
        pr = {k: v for k, v in T["what_the_list_leaves_out"].items() if k != "questions"}
        print("  what the list leaves out, as the readers see it:", json.dumps(pr))
    print("standard:", standard.NAME, "- wrote data/out/" + standard.tag("traces.json") + " and " + standard.tag("traces_summary.json"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

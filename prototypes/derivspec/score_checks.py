"""Score the readings in data/out/checks against the answer key.

  python score_checks.py             all readings found; writes data/out/checks.json and checks_summary.json
  python score_checks.py alarms      every settled field a reader marked "not supported", with the reader's words
  python score_checks.py missed      every unsettled field a reader marked "supported"
  python score_checks.py reasons     caught fields whose stated reason does not name the open rule (to read by hand)

For each reading and each answer field:
  key      the fund's documents settle the field, or they do not (the fund's rule table; the reader never sees it)
  verdict  the reader's "supported" or "not supported"
  draft    how the draft that was read had presented the figure (bare / with its assumption / asked), from scores_<fund>.json
A reader CATCHES an unsettled field by marking it "not supported" and raises a FALSE ALARM by marking a settled
field "not supported". On a draft that had already flagged an unsettled figure, "supported" REMOVES a correct flag.
"""
from __future__ import annotations

import json
import os
import re
import sys

import score_drafts as SD
from check import ARMS, DRAFT_RUN
from draft import GRID
from ds import kinds as KD
from ds import standard
from ds.funds import FUNDS

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data", "out")
CHECKS =os.path.join(OUT, "checks")
READERS = tuple(GRID)

# Does the reader's "missing" name the thing the open rule is about? Read by hand where it does not.
REASON = {
    "R05": r"day[- ]?count|36[05]|basis|act(ual)?\s*/|accrual convention",
    "R06": r"weekend|calendar|business day|day[- ]?count|non-business|holiday|which days|36[05]|basis",
    "R07": r"reset|fixing|which rate|rate (appl|observ|publication|determin|effective)|lag|published|effective|day[- ]?count|36[05]|basis",
    "R10": r"realiz|reduc|partial|unwind|resiz|decrease|downsiz|close[- ]?out|terminat|cost basis|gain or loss",
    "R11": r"reset|payment date|settle|monthly|realiz|restart|periodic|payment (frequency|term|mechanic)|net(ting)?",
    "R15": r"threshold|materialit|toleran|error polic|correction",
    "R16": r"split|corporate action|adjust",
    "R18": r"fee|cost",
    "R19": r"ex-?(dividend|date)|timing|when .{0,30}(accru|recogni|income)|(accru|recogni)[^.;]{0,40}(dividend|income)|pay(ment)? date|dividend",
    "R20": r"36[056]|day[- ]?count|basis|days in|average daily|which day|opening|prior|accrual (convention|method)",
    "R21": r"reset|increas|upsiz|added (swap )?(units|exposure)|new (tranche|lot|units)|notional|rebalanc|tranche",
    "O10": r"lot|fifo|lifo|identif|which (purchase|contracts)|cost (method|basis|relief)|average cost|highest",
    "O16": r"round|fraction|whole|integer|cash[- ]in[- ]lieu",
    "O18": r"36[056]|day[- ]?count|basis|days in|average daily|which day|opening|prior|accrual (convention|method)|weekend|calendar",
    "O20": r"36[056]|day[- ]?count|basis|compound|days in|accrual (convention|method)|weekend|calendar",
    "O21": r"threshold|materialit|toleran|error polic|correction",
    "O22": r"split|adjust|occ\b|corporate action",
    "O24": r"fee|cost|retain|booked|income|capital",
    # open to the letter only (ds/standard.py)
    "R13": r"collateral|segregat|pledg|margin|restricted",
    "R17": r"price|clos|last (sale|trade)|nav|valu|quot",
    "O09": r"commission|closing|sale|proceed|measur|purchased option",
    "O12": r"expir|settl|in the money|exercis|entries|record",
    "O14": r"in[- ]kind|deliver|value|basis|books",
}
# Settled fields that readers often mark "not supported" for a reason that is true in principle and changes nothing:
#   CENT        a published NAV that depends on an open convention on the way, and rounds to the same cent under every
#               one of them (selftest.py checks each)
#   COLLATERAL  how posted collateral is carried in the books; the amounts and net assets are the same either way
CENT = {("swap", "S15", "nav_per_share_published"), ("swap", "S09", "nav_per_share_published"), ("swap", "S10", "nav_per_share_published"),
        ("options", "T15", "nav_per_share_published"), ("options", "T06", "nav_per_share_published_after")}
COLLATERAL = {("swap", "S11", "cash_after"), ("swap", "S11", "collateral_posted_after"), ("swap", "S11", "change_in_net_assets")}


def alarm_kind(fund: str, scenario: str, field: str) -> str:
    k = (fund, scenario, field)
    return "same to the cent" if k in CENT else ("collateral line" if k in COLLATERAL else "other")


CONFLICT = re.compile(r"\bsai\b|statement of additional|midpoint|mid-point|settlement price|conflict|inconsisten|contradict|"
                      r"differ(s|ent)? (from|rule|method)|annual (report|financial)", re.I)


def verdict_of(c: dict | None) -> tuple[str, str]:
    if c is None:
        return "missing", ""
    v = str(c.get("verdict") or c.get("value") or "").strip().lower()
    words = str(c.get("missing") or "")
    if v.startswith("not") or v.startswith("unsupported"):
        return "not supported", words
    if v.startswith("support"):
        return "supported", words
    return "unclear", words


def draft_rows(fund: str) -> dict:
    """(arm, drafter) -> {(scenario, field): how} for the draft run that was read."""
    with open(os.path.join(OUT, standard.tag(f"scores_{fund}.json")), encoding="utf-8") as fh:
        res = json.load(fh)
    out = {}
    for r in res["runs"]:
        if r["run"] == DRAFT_RUN:
            out[(r["arm"], r["model"])] = {(x["scenario"], x["field"]): x["how"] for x in r["rows"]}
    return out


def names_other_rule(raw_path: str) -> bool:
    """Does the reader's answer name the pricing rule of another document (the SAI's settlement price or midpoint)?"""
    with open(raw_path, encoding="utf-8") as fh:
        return bool(re.search(r"mid-?point|settlement price|\bSAI\b|statement of additional", fh.read(), re.I))


def reading(fund: str, reader: str, name: str, ref: list[dict], drafts: dict) -> dict:
    d = os.path.join(CHECKS, fund, reader, name)
    ans = SD.parse(os.path.join(d, "raw.txt"))
    with open(os.path.join(d, "run.json"), encoding="utf-8") as fh:
        rec = json.load(fh)
    rules = FUNDS[fund]["rules"]
    arm, drafter = rec.get("draft_arm"), rec.get("drafter")
    how = drafts.get((arm, drafter), {})
    rows = []
    for s in ref:
        for field in s["expected"]:
            v, words = verdict_of(SD.cell(ans, s["id"], field))
            need = s["needs"][field]
            open_rules = [r for r in need if rules.is_open(r)]
            settled = not open_rules
            reason_ok = None
            if not settled and v == "not supported":
                reason_ok = any(re.search(REASON[r], words, re.I) for r in open_rules)
            rows.append({"scenario": s["id"], "field": field, "settled": settled, "open_rules": open_rules,
                         "draft": how.get((s["id"], field)), "verdict": v, "missing": words[:300], "names_the_open_rule": reason_ok,
                         "mentions_other_documents": bool(CONFLICT.search(words))})
    return {"fund": fund, "reader": reader, "name": name, "mode": rec.get("mode"), "draft_arm": arm, "drafter": drafter,
            "own_draft": drafter == reader if drafter else None, "run": rec.get("run"),
            "finish_reason": rec.get("finish_reason"), "parsed": "_unparsed" not in ans, "usage": rec.get("usage"),
            "names_the_other_pricing_rule": names_other_rule(os.path.join(d, "raw.txt")), "rows": rows}


def tally(rows: list[dict]) -> dict:
    U = [r for r in rows if not r["settled"]]
    S = [r for r in rows if r["settled"]]
    bare = [r for r in U if r["draft"] == "bare"]
    flagged = [r for r in U if r["draft"] in ("with its assumption", "asked")]
    return {
        "unsettled": len(U), "caught": sum(r["verdict"] == "not supported" for r in U),
        "missed": sum(r["verdict"] == "supported" for r in U), "no_verdict_unsettled": sum(r["verdict"] in ("missing", "unclear") for r in U),
        "caught_and_names_the_open_rule": sum(bool(r["names_the_open_rule"]) for r in U),
        "settled": len(S), "false_alarms": sum(r["verdict"] == "not supported" for r in S),
        "no_verdict_settled": sum(r["verdict"] in ("missing", "unclear") for r in S),
        "draft_bare": len(bare), "draft_bare_caught": sum(r["verdict"] == "not supported" for r in bare),
        "draft_flagged": len(flagged), "draft_flagged_kept": sum(r["verdict"] == "not supported" for r in flagged),
        "draft_flag_removed": sum(r["verdict"] == "supported" for r in flagged),
        # what stays unflagged after the reading
        "unflagged_if_the_reader_decides": sum(r["verdict"] != "not supported" for r in U),
        "unflagged_if_either_flags": sum(r["verdict"] != "not supported" and r["draft"] not in ("with its assumption", "asked") for r in U),
    }


def collect() -> list[dict]:
    out = []
    for fund in FUNDS:
        if not FUNDS[fund].get("scenarios"):          # the third fund has no scenarios, so no drafts and no readings
            continue
        ref, drafts = FUNDS[fund]["scenarios"].build(), draft_rows(fund)
        for reader in READERS:
            d = os.path.join(CHECKS, fund, reader)
            for name in sorted(os.listdir(d)) if os.path.isdir(d) else []:
                if os.path.exists(os.path.join(d, name, "raw.txt")) and os.path.exists(os.path.join(d, name, "run.json")):
                    out.append(reading(fund, reader, name, ref, drafts))
    return out


def group(readings: list[dict], **want) -> list[dict]:
    rows = []
    for r in readings:
        if all(r.get(k) == v for k, v in want.items()):
            rows += r["rows"]
    return rows


def votes(readings: list[dict]) -> dict:
    """The three readers on the same draft, field by field."""
    by = {}
    for r in readings:
        if r["mode"] != "draft":
            continue
        for x in r["rows"]:
            by.setdefault((r["fund"], r["name"], x["scenario"], x["field"]), []).append(x)
    full = {k: v for k, v in by.items() if len(v) == len(READERS)}
    U = [v for v in full.values() if not v[0]["settled"]]
    S = [v for v in full.values() if v[0]["settled"]]

    def n(v):
        return sum(x["verdict"] == "not supported" for x in v)

    return {"fields_read_by_all_three": len(full),
            "unsettled": len(U), "caught_by_all_three": sum(n(v) == 3 for v in U), "caught_by_two_or_more": sum(n(v) >= 2 for v in U),
            "caught_by_at_least_one": sum(n(v) >= 1 for v in U), "caught_by_none": sum(n(v) == 0 for v in U),
            "settled": len(S), "flagged_by_all_three": sum(n(v) == 3 for v in S), "flagged_by_two_or_more": sum(n(v) >= 2 for v in S),
            "flagged_by_at_least_one": sum(n(v) >= 1 for v in S),
            "all_three_agree": sum(len({x["verdict"] for x in v}) == 1 for v in full.values())}


def repeat(readings: list[dict]) -> dict:
    """The reading without a draft, repeated: does a reader give the same verdict each time?"""
    out = {}
    for fund in FUNDS:
        for reader in READERS:
            rs = [r for r in readings if r["mode"] == "nodraft" and r["fund"] == fund and r["reader"] == reader]
            if len(rs) < 2:
                continue
            keys = [(x["scenario"], x["field"]) for x in rs[0]["rows"]]
            rows = [{(x["scenario"], x["field"]): x for x in r["rows"]} for r in rs]
            same = sum(len({r[k]["verdict"] for r in rows}) == 1 for k in keys)
            U = [k for k in keys if not rows[0][k]["settled"]]
            S = [k for k in keys if rows[0][k]["settled"]]
            cu = [sum(r[k]["verdict"] == "not supported" for r in rows) for k in U]
            cs = [sum(r[k]["verdict"] == "not supported" for r in rows) for k in S]
            out[f"{fund}/{reader}"] = {"runs": len(rs), "fields": len(keys), "same_verdict_in_every_run": same,
                                       "unsettled": len(U), "caught_in_every_run": sum(c == len(rs) for c in cu),
                                       "caught_in_some_runs": sum(0 < c < len(rs) for c in cu), "caught_in_no_run": sum(c == 0 for c in cu),
                                       "settled": len(S), "flagged_in_every_run": sum(c == len(rs) for c in cs),
                                       "flagged_in_some_runs": sum(0 < c < len(rs) for c in cs)}
    return out


def by_rule(readings: list[dict]) -> dict:
    out = {}
    for r in readings:
        g = "nodraft" if r["mode"] == "nodraft" else "draft"
        for x in r["rows"]:
            for o in x["open_rules"]:
                t = out.setdefault(r["fund"], {}).setdefault(o, {}).setdefault(g, {}).setdefault(r["reader"], {"caught": 0, "n": 0})
                t["n"] += 1
                t["caught"] += x["verdict"] == "not supported"
    return out


def summarise(readings: list[dict]) -> dict:
    S = {"readings": len(readings), "all_finished_and_parsed": all(r["finish_reason"] == "stop" and r["parsed"] for r in readings),
         "tokens": sum((r.get("usage") or {}).get("total_tokens") or 0 for r in readings),
         "by_mode": {}, "by_reader": {}, "own_and_other": {}, "by_fund": {}}
    modes = {"nodraft": {"mode": "nodraft"}, "plain drafts": {"mode": "draft", "draft_arm": "plain"}, "ask drafts": {"mode": "draft", "draft_arm": "ask"}}
    for label, want in modes.items():
        S["by_mode"][label] = {"all readers": tally(group(readings, **want)),
                               **{reader: tally(group(readings, reader=reader, **want)) for reader in READERS}}
    for reader in READERS:
        S["by_reader"][reader] = {"drafts": tally(group(readings, reader=reader, mode="draft")),
                                  "nodraft": tally(group(readings, reader=reader, mode="nodraft"))}
        S["own_and_other"][reader] = {"own drafts": tally(group(readings, reader=reader, mode="draft", own_draft=True)),
                                      "other drafts": tally(group(readings, reader=reader, mode="draft", own_draft=False))}
    for fund in FUNDS:
        S["by_fund"][fund] = {label: tally(group(readings, fund=fund, **want)) for label, want in modes.items()}
    kinds = {"all readers": {}, **{reader: {} for reader in READERS}}
    for r in readings:
        for x in r["rows"]:
            if x["settled"] and x["verdict"] == "not supported":
                k = alarm_kind(r["fund"], x["scenario"], x["field"])
                for who in ("all readers", r["reader"]):
                    kinds[who][k] = kinds[who].get(k, 0) + 1
    S["false_alarms_by_kind"] = kinds
    S["settled_verdicts"] = sum(x["settled"] for r in readings for x in r["rows"])
    S["unsettled_verdicts"] = sum(not x["settled"] for r in readings for x in r["rows"])
    S["all_readings"] = {"all readers": tally(group(readings)), **{reader: tally(group(readings, reader=reader)) for reader in READERS}}
    S["with_a_draft"] = {"all readers": tally(group(readings, mode="draft")), **{reader: tally(group(readings, reader=reader, mode="draft")) for reader in READERS}}
    S["by_kind_of_gap"] = {}
    for label, ids in KD.KINDS.items():
        rows = [x for r in readings for x in r["rows"] if any(o in ids for o in x["open_rules"])]
        S["by_kind_of_gap"][label] = {"verdicts": len(rows), "caught": sum(x["verdict"] == "not supported" for x in rows)}
    # The two groups of open figures (ds/kinds.py), which do not overlap: all readings, and those of a draft apart.
    S["by_group_of_gap"] = {}
    for g in list(KD.GROUPS) + [None]:
        rows = [(r["mode"], x) for r in readings for x in r["rows"] if not x["settled"] and KD.group_of_figure(x["open_rules"]) == g]
        if rows or g is not None:
            S["by_group_of_gap"][g or "in no kind"] = {
                "verdicts": len(rows), "caught": sum(x["verdict"] == "not supported" for _, x in rows),
                "with_a_draft": {"verdicts": sum(m == "draft" for m, _ in rows),
                                 "caught": sum(x["verdict"] == "not supported" for m, x in rows if m == "draft")},
                "without_a_draft": {"verdicts": sum(m == "nodraft" for m, _ in rows),
                                    "caught": sum(x["verdict"] == "not supported" for m, x in rows if m == "nodraft")}}
    S["by_drafter_plain"] = {d: tally(group(readings, mode="draft", draft_arm="plain", drafter=d)) for d in READERS}
    S["by_drafter_ask"] = {d: tally(group(readings, mode="draft", draft_arm="ask", drafter=d)) for d in READERS}
    S["three_readers_on_one_draft"] = votes(readings)
    S["repeated_without_a_draft"] = repeat(readings)
    S["by_open_rule"] = by_rule(readings)
    f = [x for r in readings if r["fund"] == "swap" for x in r["rows"] if (x["scenario"], x["field"]) == ("S05", "net_effect_on_net_assets_on_ex_date")]
    S["the_rule_behind_the_real_restatement"] = {"readings": len(f), "caught": sum(x["verdict"] == "not supported" for x in f)}
    val = [x for r in readings if r["fund"] == "options" for x in r["rows"]
           if x["field"].startswith("price_") or (x["scenario"], x["field"]) in (("T07", "nav_per_share_published"), ("T02", "nav_per_share_published"))]
    opt = [r for r in readings if r["fund"] == "options"]
    S["options_readings_that_name_the_other_pricing_rule"] = {"readings": len(opt), "naming": sum(r["names_the_other_pricing_rule"] for r in opt)}
    rep = S["repeated_without_a_draft"]
    S["repeated_without_a_draft_total"] = {"fields": sum(v["fields"] for v in rep.values()),
                                           "same_verdict_in_every_run": sum(v["same_verdict_in_every_run"] for v in rep.values())}
    S["options_pricing_fields"] = {"verdicts": len(val), "marked_not_supported": sum(x["verdict"] == "not supported" for x in val),
                                   "of_which_mention_another_document": sum(x["verdict"] == "not supported" and x["mentions_other_documents"] for x in val)}
    return S


def line(label: str, t: dict) -> str:
    def pct(a, b):
        return f"{a}/{b}" + (f" ({100 * a / b:.0f}%)" if b else "")
    return (f"  {label:<34} caught {pct(t['caught'], t['unsettled']):<14} names the rule {t['caught_and_names_the_open_rule']:<4} "
            f"false alarms {pct(t['false_alarms'], t['settled']):<14} | draft bare caught {pct(t['draft_bare_caught'], t['draft_bare']):<14} "
            f"flags removed {pct(t['draft_flag_removed'], t['draft_flagged']):<12} | left unflagged: reader decides {t['unflagged_if_the_reader_decides']}, either flags {t['unflagged_if_either_flags']}")


def main(argv: list[str]) -> int:
    readings = collect()
    what = argv[1] if len(argv) > 1 else ""
    if what in ("alarms", "missed", "reasons"):
        n = 0
        for r in readings:
            for x in r["rows"]:
                hit = ((what == "alarms" and x["settled"] and x["verdict"] == "not supported") or
                       (what == "missed" and not x["settled"] and x["verdict"] == "supported") or
                       (what == "reasons" and x["names_the_open_rule"] is False))
                if hit:
                    n += 1
                    print(f"{r['fund']:<8}{r['reader']:<18}{r['name']:<34} {x['scenario']}.{x['field']:<40} draft:{str(x['draft']):<20} {x['missing'][:210]}")
        print(n, what)
        return 0
    S = summarise(readings)
    with open(os.path.join(OUT, standard.tag("checks.json")), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(readings, fh, indent=1)
    with open(os.path.join(OUT, standard.tag("checks_summary.json")), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(S, fh, indent=1)
    print(f"readings {S['readings']}; all finished and parsed: {S['all_finished_and_parsed']}; tokens {S['tokens']:,}")
    for label, per in S["by_mode"].items():
        print(f"\n{label}")
        for who, t in per.items():
            print(line(who, t))
    print("\nown drafts and other models' drafts")
    for reader, per in S["own_and_other"].items():
        for label, t in per.items():
            print(line(f"{reader} / {label}", t))
    print("\nby fund")
    for fund, per in S["by_fund"].items():
        for label, t in per.items():
            print(line(f"{fund} / {label}", t))
    print("\nby the model that wrote the draft")
    for d, t in S["by_drafter_plain"].items():
        print(line(f"plain draft by {d}", t))
    for d, t in S["by_drafter_ask"].items():
        print(line(f"ask draft by {d}", t))
    print("\nthree readers on one draft:", json.dumps(S["three_readers_on_one_draft"]))
    print("\nrepeated without a draft:")
    for k, v in S["repeated_without_a_draft"].items():
        print(f"  {k:<28} {json.dumps(v)}")
    print("\ncaught, by the open rule (drafts | no draft), reader by reader")
    for fund, rules in S["by_open_rule"].items():
        R = FUNDS[fund]["rules"].RULES
        for rule in sorted(rules):
            cells = []
            for g in ("draft", "nodraft"):
                cells.append(" ".join(f"{rules[rule].get(g, {}).get(m, {'caught': 0, 'n': 0})['caught']}/{rules[rule].get(g, {}).get(m, {'caught': 0, 'n': 0})['n']}" for m in READERS))
            print(f"  {rule} {cells[0]:<20} | {cells[1]:<16} {R[rule]['text'][:74]}")
    print("\nall 54 readings together, and the 36 with a draft")
    for label in ("all_readings", "with_a_draft"):
        for who, t in S[label].items():
            print(line(f"{label.replace('_', ' ')} / {who}", t))
    print("\ncaught, by the kind of gap (all readings)")
    for label, v in S["by_kind_of_gap"].items():
        print(f"  {v['caught']:>4} of {v['verdicts']:<5} {label}")
    print("\ncaught, by the group of the figure (all readings | with a draft | without)")
    for label, v in S["by_group_of_gap"].items():
        print(f"  {v['caught']:>4} of {v['verdicts']:<5} | {v['with_a_draft']['caught']:>4} of {v['with_a_draft']['verdicts']:<5} | "
              f"{v['without_a_draft']['caught']:>4} of {v['without_a_draft']['verdicts']:<5} {label}")
    print(f"\nverdicts on settled fields {S['settled_verdicts']}, on unsettled fields {S['unsettled_verdicts']}; false alarms by kind:")
    for who, k in S["false_alarms_by_kind"].items():
        print(f"  {who:<20} {json.dumps(k)}  total {sum(k.values())}")
    print("\nthe rule behind the real restatement:", json.dumps(S["the_rule_behind_the_real_restatement"]))
    print("options pricing fields:", json.dumps(S["options_pricing_fields"]))
    print("standard:", standard.NAME, "- wrote data/out/" + standard.tag("checks.json") + " and " + standard.tag("checks_summary.json"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

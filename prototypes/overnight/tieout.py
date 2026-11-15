"""Tie the report's tables out against the published result files.

Reads paper/etf-overnight-reference-value-v1.md and data/public/*.json, parses the four tables of
Section 4 and a list of figures quoted in the text, and checks every number against the file it claims
to come from. A cell passes when it equals the file's value rounded to the precision the report shows.

Run: python tieout.py            (from prototypes/overnight; no network, no keys)
"""
from __future__ import annotations
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PUB = os.path.join(HERE, "data", "public")
PAPER = os.path.join(HERE, "..", "..", "paper", "etf-overnight-reference-value-v1.md")

FAILS = 0
CHECKS = 0


def load(name: str):
    with open(os.path.join(PUB, name), encoding="utf-8") as fh:
        return json.load(fh)


def num(cell: str) -> tuple[float, int]:
    """First number in a table cell -> (value, decimals shown). '2,818' -> (2818, 0); '+1.5' -> (1.5, 1)."""
    m = re.search(r"[-+]?\d[\d,]*\.?\d*", cell.replace("−", "-"))
    if not m:
        raise ValueError(f"no number in cell {cell!r}")
    txt = m.group(0).replace(",", "")
    return float(txt), (len(txt.split(".")[1]) if "." in txt else 0)


def nums(cell: str) -> list:
    return [(float(x.replace(",", "")), (len(x.split(".")[1]) if "." in x else 0))
            for x in re.findall(r"[-+]?\d[\d,]*\.?\d*", cell.replace("−", "-"))]


def check(what: str, shown: tuple, actual: float):
    """shown = (value, decimals). Passes when |shown - actual| is within half a unit of the last digit."""
    global FAILS, CHECKS
    CHECKS += 1
    v, d = shown
    if actual is None or abs(v - actual) > 0.5 * 10 ** (-d) + 1e-9:
        FAILS += 1
        print(f"  FAIL {what}: report shows {v:.{d}f}, file gives {actual}")


def table_after(md: str, marker: str) -> list:
    """Rows (lists of cells) of the first markdown table after `marker`, header and rule dropped."""
    i = md.index(marker)
    rows, started = [], False
    for line in md[i:].split("\n"):
        if line.startswith("|"):
            started = True
            rows.append([c.strip() for c in line.strip().strip("|").split("|")])
        elif started:
            break
    return rows[2:]


def ticker_in(cell: str) -> str:
    m = re.search(r"\(([A-Z0-9]{2,5})\)", cell) or re.search(r"\b([A-Z]{3,4})\b", cell)
    return m.group(1)


def main() -> int:
    md = open(PAPER, encoding="utf-8").read()
    g, eg, fr, hp = load("grades.json"), load("evidence_grades.json"), load("frankfurt.json"), load("hedge_proposals.json")

    print("Finding 2: overnight prints")
    for row in table_after(md, "**Finding 2."):
        t = ticker_in(row[0]); p = g[t]["overnight_prints"]; si = p["same_instant"]
        check(f"{t} slots with a trade %", num(row[1]), 100 * p["traded_bars"] / p["session_slots"])
        check(f"{t} same-instant bars", num(row[2]), si["n"])
        check(f"{t} median distance", num(row[3]), si["median_abs_bps"])
        check(f"{t} 90th percentile", num(row[4]), si["p90_abs_bps"])
        check(f"{t} mean premium", num(row[5]), si["mean_premium_bps"])

    print("Finding 5: trading band")
    for row in table_after(md, "**Finding 5."):
        t = ticker_in(row[0]); tb = g[t]["overnight_prints"]["trading_band"]
        if "not calibrated" in row[1]:
            check(f"{t} calibration prints", num(row[1]), tb.get("insufficient_prints"))
            continue
        check(f"{t} trading half-width", num(row[1]), tb["mean_half_trade_bps"])
        check(f"{t} open half-width", num(row[2]), tb["mean_half_open_bps"])
        pct, n = nums(row[3])[:2]
        check(f"{t} prints covered %", pct, 100 * tb["evaluation_prints_inside"] / tb["evaluation_traded_prints"])
        check(f"{t} prints evaluated", n, tb["evaluation_traded_prints"])

    print("Finding 6: news reader, first stage")
    for row in table_after(md, "**Finding 6."):
        t = ticker_in(row[0].split(",")[-1]); m = eg[t]["models"]["haiku"]
        check(f"{t} readings flagged %", num(row[1]), 100 * m["flag_rate"])
        check(f"{t} events %", num(row[2]), 100 * m["event_rate"])
        check(f"{t} precision", num(row[3]), m["precision"])
        check(f"{t} recall", num(row[4]), m["recall"])
        pct, n = nums(row[5])[:2]
        check(f"{t} direction right %", pct, 100 * m["sign_accuracy"])
        check(f"{t} direction calls", n, m["sign_checks"])

    print("Finding 8: Frankfurt control")
    for row in table_after(md, "**Finding 8."):
        t = ticker_in(row[0]) + ".DE"; a = fr[t]["analysis"]; tb = a["trading_band"]
        check(f"{t} quarter-hours traded %", num(row[2]), 100 * a["traded_bars"] / a["slots_before_us_open"])
        check(f"{t} median distance", num(row[3]), a["median_abs_bps"])
        check(f"{t} 90th percentile", num(row[4]), a["p90_abs_bps"])
        check(f"{t} mean", num(row[5]), a["mean_dev_bps"])
        band, cov = nums(row[6])[:2]
        check(f"{t} band", band, tb["q90_bps"])
        check(f"{t} band coverage %", cov, 100 * tb["coverage"])

    print("Figures quoted in the text")
    ss = eg["_second_stage"]; so, l2, l9 = ss["models"]["sonnet"], ss["models"]["local"], ss["models"]["local9b"]
    eem = hp["EEM"]["sonnet"]["evaluation"]; ewg = hp["EWG"]["sonnet"]["evaluation"]; lqd = hp["LQD"]["sonnet"]["evaluation"]
    lp = eem["late_prints_vs_added_instruments"]
    spy = g["SPY"]["overnight_prints"]

    def quoted(pattern: str, *actuals, what: str):
        """The regex must match the report's text; each captured number is checked against `actuals`."""
        global FAILS, CHECKS
        m = re.search(pattern, md, re.S)
        if not m:
            FAILS += 1; CHECKS += 1
            print(f"  FAIL {what}: sentence not found in the report")
            return
        for k, a in enumerate(actuals):
            check(f"{what} [{k + 1}]", num(m.group(k + 1)), a)

    quoted(r"the S&P 500 fund within a median ([\d.]+) basis points", spy["same_instant"]["median_abs_bps"], what="abstract, S&P median")
    quoted(r"is ([\d.]+) basis points in the 8pm hour and ([\d.]+) in the 3am hour",
           spy["by_hour"]["20"]["median_abs_bps"], spy["by_hour"]["3"]["median_abs_bps"], what="S&P by hour")
    quoted(r"flat carry was (\d+) basis points for the S&P fund and (\d+) for the bitcoin fund;\s+the hedge-moved value cut those to (\d+) and (\d+)",
           g["SPY"]["mae_naive_bps"], g["IBIT"]["mae_naive_bps"], g["SPY"]["mae_ref_bps_all_hours"], g["IBIT"]["mae_ref_bps_all_hours"], what="Finding 1 errors")
    quoted(r"(\d+) against (\d+) basis points for Japan, (\d+)\s+against (\d+) for Germany, (\d+) against (\d+) for emerging markets",
           g["EWJ"]["mae_ref_bps_all_hours"], g["EWJ"]["mae_ref_close_anchor_bps_all_hours"],
           g["EWG"]["mae_ref_bps_all_hours"], g["EWG"]["mae_ref_close_anchor_bps_all_hours"],
           g["EEM"]["mae_ref_bps_all_hours"], g["EEM"]["mae_ref_close_anchor_bps_all_hours"], what="anchor comparison")
    quoted(r"([\d.]+) against ([\d.]+) basis points for the S&P fund and ([\d.]+)\s+against ([\d.]+) for bitcoin",
           g["SPY"]["overnight_prints"]["same_instant_nav_anchor"]["median_abs_bps"], spy["same_instant"]["median_abs_bps"],
           g["IBIT"]["overnight_prints"]["same_instant_nav_anchor"]["median_abs_bps"], g["IBIT"]["overnight_prints"]["same_instant"]["median_abs_bps"],
           what="prints, NAV vs close anchor")
    words = {w: i for i, w in enumerate("zero one two three four five six seven eight nine ten".split())}

    def counted(pattern: str, *actuals, what: str):
        """As `quoted`, for counts the report writes as words ('six of the seven')."""
        global FAILS, CHECKS
        m = re.search(pattern, md, re.S)
        if not m or any(w.lower() not in words for w in m.groups()):
            FAILS += 1; CHECKS += 1
            print(f"  FAIL {what}: sentence not found in the report")
            return
        for k, a in enumerate(actuals):
            check(f"{what} [{k + 1}]", (words[m.group(k + 1).lower()], 0), a)

    def nav_median(t: str) -> float:
        return g[t]["overnight_prints"]["same_instant_nav_anchor"]["median_abs_bps"]

    with_nav = [t for t in g if g[t]["nav_source"] == "file"]          # the funds whose night starts from an official NAV
    further = [t for t in with_nav if nav_median(t) > g[t]["overnight_prints"]["same_instant"]["median_abs_bps"]]
    counted(r"In (\w+) of the (\w+) funds that start from an\s+official NAV the overnight prints also sat further",
            len(further), len(with_nav), what="funds whose prints sat further from the NAV-anchored value")
    check("the exception among them is the Germany fund", (1, 0), 1 if set(with_nav) - set(further) == {"EWG"} else 0)
    quoted(r"the exception is the\s+Germany fund, on (\d+) prints", g["EWG"]["overnight_prints"]["same_instant"]["n"], what="the Germany fund's prints")
    quoted(r"for the seven funds with an official NAV: SPY ([\d.]+); IBIT ([\d.]+); TLT ([\d.]+); LQD ([\d.]+); EWJ ([\d.]+); EEM ([\d.]+); EWG ([\d.]+) \((\d+) bars\)",
           nav_median("SPY"), nav_median("IBIT"), nav_median("TLT"), nav_median("LQD"), nav_median("EWJ"), nav_median("EEM"), nav_median("EWG"),
           g["EWG"]["overnight_prints"]["same_instant_nav_anchor"]["n"], what="Appendix A, NAV-anchored medians")
    quoted(r"On the (\d+) nights with a late trade and all four Asian sessions available, the print's\s+deviation from the reference had a correlation of ([\d.]+)",
           lp["n_nights"], lp["corr_print_deviation_vs_added"], what="emerging markets, late prints")
    quoted(r"median\s+distance fell from (\d+) to (\d+) basis points and the mean from (-\d+) to (-\d+)",
           lp["median_abs_print_deviation_bps"], lp["median_abs_after_added_bps"], lp["mean_print_deviation_bps"], lp["mean_after_added_bps"],
           what="emerging markets, distance after the Asian sessions")
    quoted(r"correlation\s+between the two deviations was ([\d.]+) over (\d+) nights with a late trade, for Japan ([\d.]+) over (\d+), for\s+semiconductors ([\d.]+)\. For the S&P fund it was ([\d.]+)",
           g["EEM"]["overnight_prints"]["late_print_vs_open"]["corr"], g["EEM"]["overnight_prints"]["late_print_vs_open"]["n_nights"],
           g["EWJ"]["overnight_prints"]["late_print_vs_open"]["corr"], g["EWJ"]["overnight_prints"]["late_print_vs_open"]["n_nights"],
           g["SMH"]["overnight_prints"]["late_print_vs_open"]["corr"], g["SPY"]["overnight_prints"]["late_print_vs_open"]["corr"],
           what="Finding 4 correlations")
    quoted(r"half-width runs from\s+(\d+) basis points at 8pm to (\d+) at 4am",
           g["SPY"]["by_hour"]["20"]["mean_half_emp_bps"], g["SPY"]["by_hour"]["4"]["mean_half_emp_bps"], what="S&P open band")
    cov = [g[t]["coverage_emp_all_hours"] for t in g]
    quoted(r"covered the next morning's open between (\d+)% and (\d+)%", 100 * min(cov), 100 * max(cov), what="open band coverage range")
    quoted(r"on the (\d+) readings the first had flagged plus a fixed sample of (\d+) quiet\s+ones, (\d+) in all, of which (\d+) were events",
           ss["first_stage_flags"], so["quiet_sample"], so["selected"], so["events"], what="second stage, sample")
    quoted(r"keeping (\d+) of the (\d+)\s+flags and raising none in the quiet sample, and right on direction in (\d+) of (\d+) calls",
           so["kept"], so["first_stage_flags_seen"], so["direction_right"], so["direction_calls"], what="Sonnet")
    quoted(r"it caught (\d+) of the (\d+)\. A", so["events_flagged"], so["events"], what="Sonnet events caught")
    quoted(r"answered (\d+) of the (\d+), the rest being too long for its\s+context; of the flags it kept, (\d+) in (\d+) were events",
           l2["answered"], l2["selected"], l2["kept_events"], l2["kept"], what="2B model")
    quoted(r"cited an item that was not in its list in (\d+) of (\d+) flags", l2["flags_citing_unknown_ids"], l2["flags"], what="2B unknown citations")
    quoted(r"flagged eight readings of\s+(\d+), and caught one of the (\d+) events", l9["answered"], l9["events"], what="9B model")
    quoted(r"the fit edged from ([\d.]+) to ([\d.]+)\. For Germany",
           hp["SPY"]["sonnet"]["evaluation"]["baseline"]["r2_oos"], hp["SPY"]["sonnet"]["evaluation"]["proposal_free"]["r2_oos"], what="S&P hedge")
    quoted(r"the fit rose from ([\d.]+) to ([\d.]+), and to ([\d.]+) with the model's own\s+weights, the error against the open falling from (\d+) to (\d+) basis points",
           ewg["baseline"]["r2_oos"], ewg["proposal_free"]["r2_oos"], ewg["proposal_fixed"]["r2_oos"], ewg["baseline"]["mae_bps"], ewg["proposal_free"]["mae_bps"],
           what="Germany hedge")
    quoted(r"small S&P weight, and the\s+fit rose from ([\d.]+) to ([\d.]+)\.", lqd["baseline"]["r2_oos"], lqd["proposal_free"]["r2_oos"], what="credit hedge")
    quoted(r"appeared to reject the choice: ([\d.]+), against ([\d.]+) for S&P futures alone on the same (\d+) nights",
           eem["proposal_free"]["r2_oos"], eem["baseline_same_nights"]["r2_oos"], eem["proposal_free"]["n_test"], what="emerging markets, first scoring")
    quoted(r"the same four instruments score ([\d.]+) alone, still short of S&P futures, and added to\s+S&P futures they lift the fit from ([\d.]+) to ([\d.]+) and cut the error against the open from (\d+) to (\d+) basis",
           eem["proposal_session_free"]["r2_oos"], eem["baseline_same_nights_session"]["r2_oos"], eem["union_session_free"]["r2_oos"],
           eem["baseline_same_nights_session"]["mae_bps"], eem["union_session_free"]["mae_bps"], what="emerging markets, session measurement")
    room = min(g[t]["input_facts"]["static_band_min_room_bps"] for t in g)
    quoted(r"came to its band was (\d+) percentage points", room / 100.0, what="static band, closest approach")
    us15 = {t: 100 * g[t]["overnight_prints"]["traded_share_15min_slots"] for t in ("EWJ", "EEM", "LQD", "EWG")}
    quoted(r"the Japan fund traded in (\d+)% of them, emerging markets in (\d+)%, credit in (\d+)%\s+and Germany in ([\d.]+)%",
           us15["EWJ"], us15["EEM"], us15["LQD"], us15["EWG"], what="US night in quarter-hours")

    print(f"\nTIE-OUT {'PASSED' if FAILS == 0 else f'FAILED ({FAILS})'}: {CHECKS} figures checked against data/public")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())

"""Markdown report from the grade files: a summary table, per-hour tables, footnotes on proxies."""
from __future__ import annotations
import datetime as dt
import os

from .config import FUNDS, GRID_HOURS, BAND_CONFIDENCE
from .util import OUT, read_json


def _f(x, nd=1):
    return "n/a" if x is None else f"{x:.{nd}f}"


def summary_markdown(grades: dict, fits: dict) -> str:
    L = []
    L.append("# Overnight reference value — backtest summary\n")
    L.append(f"Generated {dt.datetime.now().isoformat(timespec='minutes')}. All inputs are real market data; "
             "see the footnotes for proxies. The reference value is the 4pm NAV moved by the fund's hedge "
             "instrument (and currency) since 4pm, with an overnight beta estimated on nights before the test "
             f"window. The band is nominally {int(BAND_CONFIDENCE*100)}%. Truth is the next morning's 9:30 opening price.\n")
    L.append("## By fund\n")
    L.append("| Fund | Kind | Hedge | Train nights | Test nights | Beta | R2 train | Resid train (bps) | Resid test (bps) | MAE naive (bps) | MAE ref (bps) | Coverage Gaussian | Coverage empirical | Usable | Nights > 100 bps | Static band ever binding |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for t, s in grades.items():
        L.append(f"| {t} | {s['kind']} | {s['hedge']} | {s['n_train_nights']} | {s['n_test_nights']} | {_f(s['beta'],3)} | "
                 f"{_f(s['r2_train'],2)} | {_f(s['sigma_resid_bps'])} | {_f(s.get('sigma_resid_test_bps'))} | {_f(s['mae_naive_bps'])} | {_f(s['mae_ref_bps_all_hours'])} | "
                 f"{_f(s['coverage_all_hours'],3)} | {_f(s.get('coverage_emp_all_hours'),3)} | {_f(s['share_usable'],2)} | {s['nights_moved_over_100bps']} | "
                 f"{'yes' if s['static_band_ever_binding'] else 'no'} |")
    L.append("")
    L.append("Reading the table: *MAE naive* is the error of carrying the 4pm NAV flat through the night; "
             "*MAE ref* is the error of the hedge-moved reference value, averaged over all grid hours; both are against "
             "the 9:30 open. Two bands are scored, both nominally 90%: the *Gaussian* band (residual spread plus the hedge's "
             "remaining hourly variance) and the *empirical* band (for each hour, the 90th percentile of the carry-forward's own "
             "error on the training nights). Coverage should sit near 0.90; far above it the band is too wide to be useful, "
             "far below it the band lies. *Resid test* against *Resid train* shows whether the test window was calmer or wilder "
             "than the fit. *Static band ever binding* asks whether the exchanges' 20% band would have excluded a single "
             "opening price in the window.\n")
    if any(s.get("overnight_prints") for s in grades.values()):
        L.append("## Overnight trades against the reference value\n")
        L.append("| Fund | 5-minute slots | Slots with a trade | Share | Share of 15-minute slots | Same-instant traded bars | Mean premium (bps) | Median abs (bps) | p90 abs (bps) | Outside the open band | Last print vs open: corr (nights) |")
        L.append("|---|---|---|---|---|---|---|---|---|---|---|")
        for t, s in grades.items():
            p = s.get("overnight_prints")
            if not p:
                L.append(f"| {t} | 0 | 0 | n/a | n/a | 0 | n/a | n/a | n/a | n/a | n/a |"); continue
            si, lp = p["same_instant"], p["late_print_vs_open"]
            L.append(f"| {t} | {p['session_slots']} | {p['traded_bars']} | {_f(100 * p['traded_share'])}% | {_f(100 * p['traded_share_15min_slots'])}% | "
                     f"{si['n']} | {_f(si['mean_premium_bps'])} | {_f(si['median_abs_bps'])} | {_f(si['p90_abs_bps'])} | "
                     f"{_f(si.get('share_outside_open_band'), 4)} | {_f(lp.get('corr'), 2)} ({lp['n_nights']}) |")
        L.append("")
        L.append("A slot is five minutes of the 8pm to 4am session, 96 a night; a slot counts as traded when the bar shows "
                 "volume (the feed repeats the last price through quiet slots, and returns no bar before a session's first "
                 "trade). Distances are measured on *same-instant* bars: traded bars whose futures price is the close of the "
                 "5-minute futures bar covering the same five minutes. The public feed serves about sixty trading days of "
                 "5-minute bars; on earlier nights only a bar ending on the hour, where the hourly futures bar closes at the "
                 "same instant, qualifies. A positive mean is a premium to the reference, a negative one a discount. "
                 "'Outside the open band' is the share of those bars beyond the open band for that hour. The last column asks "
                 "whether the last trade before 4am says where the fund will open: the correlation, across nights, between "
                 "that print's deviation and the open's deviation, both from the close-anchored reference.\n")
    for t, s in grades.items():
        L.append(f"## {t} — {FUNDS[t]['name']}\n")
        L.append(f"Kind {s['kind']}, hedge {s['hedge']}, beta {_f(s['beta'],3)}"
                 + (f", currency gamma {_f(s['gamma'],3)}" if s.get('gamma') else "")
                 + f". NAV source: {s['nav_source']}. Overnight tape: {s.get('tape') or 'none'}.\n")
        L.append("| Hour (ET) | n | MAE ref (bps) | Median ref (bps) | MAE naive (bps) | Coverage Gaussian | Half-band Gaussian (bps) | Coverage empirical | Half-band empirical (bps) | Usable share |")
        L.append("|---|---|---|---|---|---|---|---|---|---|")
        for h in GRID_HOURS:
            r = s["by_hour"].get(str(h))
            if not r:
                continue
            L.append(f"| {h:02d}:00 | {r['n']} | {_f(r['mae_ref_bps'])} | {_f(r['median_ref_bps'])} | {_f(r['mae_naive_bps'])} | "
                     f"{_f(r['coverage'],3)} | {_f(r['mean_half_bps'])} | {_f(r.get('coverage_emp'),3)} | {_f(r.get('mean_half_emp_bps'))} | {_f(r['usable_share'],2)} |")
        if s.get("overnight_prints"):
            p = s["overnight_prints"]
            si, lg, na = p["same_instant"], p["lagged_reference"], p["same_instant_nav_anchor"]
            L.append(f"\nOvernight prints (Blue Ocean, 5-minute bars): {p['traded_bars']} of {p['session_slots']} slots traded on "
                     f"{p['nights_with_a_trade']} nights. Same-instant traded bars against the close-anchored reference: "
                     f"{si['n']} bars, mean premium {_f(si['mean_premium_bps'])} bps, median absolute {_f(si['median_abs_bps'])} bps, "
                     f"90th percentile {_f(si['p90_abs_bps'])} bps; against the NAV-anchored reference, median absolute "
                     f"{_f(na['median_abs_bps'])} bps. Traded bars left out because their futures price was up to 55 minutes "
                     f"older than the print (hourly bars only): {lg['n']}, median absolute {_f(lg['median_abs_bps'])} bps.\n")
            L.append("| Hour (ET) | same-instant traded bars | mean premium (bps) | median abs (bps) |")
            L.append("|---|---|---|---|")
            for h, v in p["by_hour"].items():
                L.append(f"| {int(h):02d} | {v['n']} | {_f(v['mean_bps'])} | {_f(v['median_abs_bps'])} |")
            tb = p.get("trading_band")
            if tb and "q90_pooled_bps" in tb:
                L.append(f"\nTrading band, calibrated on same-instant traded prints {tb['calibration_from']} to {tb['calibration_to']} "
                         f"({tb['n_calibration_prints']} prints; 90th percentile {_f(tb['q90_pooled_bps'])} bps, median {_f(tb['q50_pooled_bps'])} bps) "
                         f"and applied to {tb['evaluation_from']} to {tb['evaluation_to']}: covered {_f(tb.get('coverage_traded_prints'),3)} of "
                         f"{tb.get('evaluation_traded_prints')} prints; mean half-width {_f(tb.get('mean_half_trade_bps'))} bps against "
                         f"{_f(tb.get('mean_half_open_bps'))} bps for the open band at the same hours.")
            elif tb and "insufficient_prints" in tb:
                L.append(f"\nTrading band: not calibrated, only {tb['insufficient_prints']} same-instant traded prints in the calibration half (50 needed).")
        L.append("")
    L.append("## Footnotes\n")
    L.append("- Where no NAV file was supplied the 4pm close stands in for the NAV (`nav_proxy_close`). For US equity funds the "
             "difference is usually a few basis points; for international funds it can be larger because the official NAV "
             "fair-values foreign closes.")
    L.append("- The hedge move is measured to 9:00am and the fund opens at 9:30am. The half hour adds noise to the beta "
             "estimate; it does not add look-ahead.")
    L.append("- The exchanges' band uses the 7:45pm consolidated round-lot sale. Yahoo's 15-minute post-market bars thin out "
             "after 7pm, so the print used here is the last post-market bar before 7:45pm, often the bar ending 7:00pm; the "
             "time actually used is stored in each record (`sale_1945_time`). With a 20% band the difference is immaterial; "
             "the 1-minute extended-hours feed replaces it once a key is available.")
    L.append("- Hourly bars from Yahoo's chart feed are stamped at the bar's start; the value at an hour is the close of the "
             "bar that covers the hour before it. A print between hours is never paired with a bar that was still open "
             "when the print closed.")
    L.append("- 'Usable' is the trip-wire: every input fresh and the band not wider than 400 bps half-width.")
    L.append("- Two reference values are carried. The open-based grading uses the official NAV as the 4pm anchor where the "
             "issuer file provides it (the close for QQQ and SMH, and for GLD, whose NAV is struck off the London afternoon "
             "gold price). The print comparison and the trading band use the 4pm close as the anchor, because overnight trades "
             "price off the fund's own last trade; the NAV-anchored print figures are kept as `traded_nav_anchor`.")
    L.append("- On an ex-dividend morning the open is compared with the payout added back (`truth_open_cum`), because the "
             "shares open lower by the distribution through no fault of the hedge; overnight prints are cum-dividend and "
             "are left alone. Records carry the flag `exdiv:<amount>`.")
    return "\n".join(L)


def write_report(tickers: list) -> str:
    grades = read_json(os.path.join(OUT, "grades.json"))
    fits = read_json(os.path.join(OUT, "fits.json")) if os.path.exists(os.path.join(OUT, "fits.json")) else {}
    md = summary_markdown({t: grades[t] for t in tickers if t in grades}, fits)
    p = os.path.join(OUT, "REPORT.md")
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(md)
    print(f"[report] wrote {p}")
    return p

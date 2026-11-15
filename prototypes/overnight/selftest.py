"""Unit tests for the pure parts. No network. Run: python selftest.py"""
from __future__ import annotations
import datetime as dt
import math
import random
import sys

from ovn.model import static_band, ols, fit_overnight, carry_forward, band, trip_wire, hourly_sigma
from ovn.util import Series, at, TZ_ET
from ovn.evidence import validate

FAILS = 0


def check(name, cond, detail=""):
    global FAILS
    if cond:
        print(f"  ok   {name}")
    else:
        FAILS += 1
        print(f"  FAIL {name} {detail}")


def t_static_band():
    print("static band")
    lo, hi = static_band(100.0, 101.0)
    check("20% off lower/higher refs", abs(lo - 80.0) < 1e-9 and abs(hi - 121.2) < 1e-9, f"{lo},{hi}")
    lo, hi = static_band(10.0, None)
    check("$3 minimum dominates for low-priced", abs(lo - 7.0) < 1e-9 and abs(hi - 13.0) < 1e-9, f"{lo},{hi}")
    lo, hi = static_band(100.0, 90.0)
    check("sale below close widens the lower band", abs(lo - 72.0) < 1e-9 and abs(hi - 120.0) < 1e-9, f"{lo},{hi}")


def t_ols():
    print("least squares")
    random.seed(7)
    xs = [random.gauss(0, 0.01) for _ in range(500)]
    y = [0.0002 + 0.9 * x + random.gauss(0, 0.002) for x in xs]
    f = ols(y, [[1.0, x] for x in xs])
    check("recovers beta ~0.9", abs(f["b"][1] - 0.9) < 0.03, f"{f['b']}")
    check("recovers sigma ~0.002", abs(f["sigma"] - 0.002) < 0.0004, f"{f['sigma']}")
    fx = [random.gauss(0, 0.005) for _ in range(500)]
    y2 = [0.9 * x + 0.8 * z + random.gauss(0, 0.001) for x, z in zip(xs, fx)]
    f2 = fit_overnight([{"y": a, "rh": b, "rfx": c} for a, b, c in zip(y2, xs, fx)], use_fx=True)
    check("two-regressor fit recovers gamma ~0.8", abs(f2["gamma"] - 0.8) < 0.05, f"{f2['gamma']}")
    try:
        ols([1.0, 2.0], [[1.0, 1.0], [1.0, 1.0]])
        check("singular design raises", False)
    except ValueError:
        check("singular design raises", True)


def t_band():
    print("reference value and band")
    fit = {"beta": 1.0, "gamma": 0.0, "sigma_resid": 0.0010}
    c = carry_forward(100.0, fit, 0.01)
    check("carry-forward moves NAV by beta*hedge", abs(c - 101.0) < 1e-9, f"{c}")
    lo1, hi1, h1 = band(c, fit, 0.0005, 8.0)
    lo2, hi2, h2 = band(c, fit, 0.0005, 1.0)
    check("band narrows as the night passes", h1 > h2 > 0, f"{h1},{h2}")
    _, _, h0 = band(c, fit, float("nan"), 8.0)
    check("NaN hedge vol falls back to residual only", abs(h0 - 1.6449 * 10.0) < 1e-6, f"{h0}")
    check("trip-wire usable", trip_wire(True, [], 50.0) == "usable")
    check("trip-wire stale", trip_wire(True, ["ES=F"], 50.0).startswith("unreliable:stale"))
    check("trip-wire wide", trip_wire(True, [], 900.0) == "unreliable:band_too_wide")
    check("hourly sigma needs 30 points", math.isnan(hourly_sigma([0.001] * 10)))


def t_series():
    print("series as-of")
    base = at(dt.date(2026, 11, 5), 15, 0)
    bars = [{"ts": int((base + dt.timedelta(hours=k)).timestamp()), "close": 100.0 + k} for k in range(10)]
    s = Series("X", bars)
    c, start = s.asof(at(dt.date(2026, 11, 5), 16, 0))
    check("value at 16:00 is the close of the 15:00 bar", c == 100.0 and start.hour == 15, f"{c},{start}")
    c, start = s.asof(at(dt.date(2026, 11, 5), 21, 0))
    check("value at 21:00 is the close of the 20:00 bar", c == 105.0, f"{c}")
    c, _ = s.asof(at(dt.date(2026, 11, 5), 14, 0))
    check("before first bar -> None", c is None)
    c, _ = s.last_before(at(dt.date(2026, 11, 5), 19, 45), after=at(dt.date(2026, 11, 5), 16, 0))
    check("last_before respects the floor", c == 104.0, f"{c}")


def t_validate():
    print("evidence validation (flag-only schema)")
    ids = {"n1", "n2"}
    check("clean quiet verdict", validate({"flag": False, "direction": "none", "confidence": "high", "cited_ids": [], "reason": "nothing"}, ids) == [])
    check("clean flag", validate({"flag": True, "direction": "down", "confidence": "low", "cited_ids": ["n1"], "reason": "x"}, ids) == [])
    v = validate({"flag": False, "direction": "up", "confidence": "low", "cited_ids": []}, ids)
    check("direction without flag caught", "direction_without_flag" in v, str(v))
    v = validate({"flag": True, "direction": "up", "confidence": "low", "cited_ids": ["n9"]}, ids)
    check("unknown citation caught", any(x.startswith("cited_unknown_ids") for x in v), str(v))
    v = validate({"flag": True, "direction": "none", "confidence": "low", "cited_ids": ["n1"]}, ids)
    check("flag without direction caught", "flag_without_direction" in v, str(v))
    v = validate({"flag": True, "direction": "up", "confidence": "low", "cited_ids": []}, ids)
    check("flag without citation caught", "flag_without_citation" in v, str(v))
    v = validate({"flag": True, "direction": "sideways", "confidence": "sure", "cited_ids": ["n1"]}, ids)
    check("bad enums caught", "direction_invalid" in v and "confidence_invalid" in v, str(v))


def t_holdings_csv():
    print("issuer holdings CSV")
    from ovn.holdings import parse_ishares_csv
    sample = ("iShares MSCI Japan ETF\nFund Holdings as of,\"Nov 06, 2026\"\nInception Date,\"Mar 12, 1996\"\n"
              "Shares Outstanding,\"100\"\n \nTicker,Name,Sector,Asset Class,Market Value,Weight (%),Notional Value,Shares,Price,Location,Exchange,Currency,FX Rate,Market Currency,Accrual Date\n"
              "\"7203\",\"TOYOTA MOTOR CORP\",\"Consumer Discretionary\",\"Equity\",\"1,000.00\",\"5.10\",\"1,000.00\",\"10\",\"100.00\",\"Japan\",\"Tokyo Stock Exchange\",\"JPY\",\"150.00\",\"JPY\",\"-\"\n"
              "\"6758\",\"SONY GROUP CORP\",\"Consumer Discretionary\",\"Equity\",\"800.00\",\"4.20\",\"800.00\",\"8\",\"100.00\",\"Japan\",\"Tokyo Stock Exchange\",\"JPY\",\"150.00\",\"JPY\",\"-\"\n"
              "\"JPY\",\"JPY CASH\",\"Cash and/or Derivatives\",\"Cash\",\"5.00\",\"0.10\",\"5.00\",\"5\",\"1.00\",\"Japan\",\"-\",\"JPY\",\"150.00\",\"JPY\",\"-\"\n")
    rows = parse_ishares_csv(sample)
    check("two equity rows, cash dropped", len(rows) == 2 and rows[0]["symbol"] == "7203", str(rows))
    check("weights read as percent", abs(rows[0]["weight"] - 5.10) < 1e-9, str(rows[0]))
    from ovn.holdings import map_news_ticker
    check("German local ticker maps by name, not symbol", map_news_ticker("DEUTSCHE TELEKOM N AG", "DTE", "Germany") == "DTEGY")
    check("US-listed holding keeps its symbol", map_news_ticker("DTE ENERGY CO", "DTE", "United States") == "DTE")
    check("Siemens N AG is not Siemens Energy", map_news_ticker("SIEMENS N AG", "SIE", "Germany") == "SIEGY"
          and map_news_ticker("SIEMENS ENERGY N AG", "ENR", "Germany") == "SMNEY")
    check("unknown foreign name yields no news ticker", map_news_ticker("SK HYNIX", "000660", "Korea (South)") == "")


def t_print_alignment():
    """A 5-minute print must never be paired with a futures bar that was still open when it closed.
    (The first version paired a print ending 01:05 with the hourly bar closing 02:00.)"""
    print("print alignment (no bar from the future)")
    from ovn.nights import _ret_closed, _print_signal
    day = dt.date(2026, 11, 5)
    t16 = at(day, 16, 0)
    # hourly bars 15:00 .. next day 05:00, close rises 1.0 per hour; bar started h closes at h+1
    hourly = Series("H", [{"ts": int((at(day, 15, 0) + dt.timedelta(hours=k)).timestamp()), "close": 100.0 + k} for k in range(15)])
    # 5-minute bars from 15:55, close rises 0.1 per bar
    five = Series("F", [{"ts": int((at(day, 15, 55) + dt.timedelta(minutes=5 * k)).timestamp()), "close": 100.0 + 0.1 * k} for k in range(140)])
    t_0105 = at(day + dt.timedelta(days=1), 1, 5)
    c, end = hourly.closed_asof(t_0105, 3600)
    check("hourly bars at 01:05 give the bar that closed at 01:00", end == at(day + dt.timedelta(days=1), 1, 0) and c == 109.0, f"{c},{end}")
    c_bad, _ = hourly.asof(t_0105)
    check("the old lookup would have returned the 02:00 close", c_bad == 110.0, f"{c_bad}")
    c, end = hourly.closed_asof(at(day + dt.timedelta(days=1), 2, 0), 3600)
    check("on the hour the two lookups agree", c == 110.0 and end == at(day + dt.timedelta(days=1), 2, 0), f"{c},{end}")
    r, fl, lag = _ret_closed(hourly, 3600, t16, t_0105, "H")
    check("hourly return at 01:05 is lagged five minutes, not led", fl is None and lag == 300 and abs(r - (109.0 / 100.0 - 1)) < 1e-12, f"{r},{fl},{lag}")
    r, fl, res, lag = _print_signal(five, hourly, t16, t_0105, "F")
    check("5-minute bars pair the print with the bar of the same five minutes", res == "5m" and lag == 0, f"{res},{lag}")
    r, fl, res, lag = _print_signal(Series("F", []), hourly, t16, t_0105, "F")
    check("without 5-minute bars the hourly fallback is used and marked", res == "1h" and lag == 300, f"{res},{lag}")
    late = Series("L", [b for b in five.bars if b["ts"] >= int(at(day, 20, 0).timestamp())])
    r, fl, res, lag = _print_signal(late, hourly, t16, t_0105, "L")
    check("5-minute bars that start after 4pm cannot supply the 4pm base", res == "1h", f"{res}")
    r, fl, lag = _ret_closed(hourly, 3600, t16, at(day + dt.timedelta(days=2), 1, 5), "H")
    check("a futures price older than the staleness limit is refused", r is None and fl == "signal_stale:H", f"{r},{fl}")


def t_trading_band_hours():
    print("trading band, hour lookup")
    from ovn.nights import trade_quantile
    by_hour = {"20": 0.0010, "1": 0.0007, "3": 0.0009}
    check("an hour after midnight finds its own band ('01' -> '1')", trade_quantile(by_hour, 0.0008, "2026-11-06T01:35-05:00") == 0.0007)
    check("an evening hour finds its own band", trade_quantile(by_hour, 0.0008, "2026-11-05T20:00-05:00") == 0.0010)
    check("an hour without its own band gets the pooled one", trade_quantile(by_hour, 0.0008, "2026-11-06T02:10-05:00") == 0.0008)


def t_frankfurt_slots():
    print("Frankfurt, slots before the US open")
    from ovn.frankfurt import slots_before_us_open, analyse
    check("26 slots when New York opens at 15:30 Frankfurt time", slots_before_us_open(dt.date(2026, 11, 6)) == 26)
    check("22 slots in the week Europe has left summer time and the US has not", slots_before_us_open(dt.date(2026, 10, 28)) == 22)
    # a thin fund: 10 sessions, 4 traded bars each, in a feed that returns only bars with a trade
    recs = [{"date": f"2026-11-{d:02d}", "slots": 26, "y_morning": 0.001 * d, "rh_morning": 0.001 * d, "rfx_morning": 0.0,
             "dividend": 0.0, "prints": [{"t": f"2026-11-{d:02d}T10:15+01:00", "volume": 5, "dev_bps": 3.0}] * 4}
            for d in (2, 3, 4, 5, 6, 9, 10, 11, 12, 13)]
    a = analyse({"records": recs}, calendar=[r["date"] for r in recs])
    check("share of slots traded is counted against the session's slots, not the bars returned",
          a["slots_before_us_open"] == 260 and a["traded_bars"] == 40 and abs(a["traded_share"] - 40 / 260) < 1e-6, str({k: a[k] for k in ("slots_before_us_open", "traded_bars", "traded_share")}))


def t_hedge_session():
    print("hedge test, cash index over its own session")
    from ovn.hedge_proposer import _session_return, _oos, is_cash_index
    day = dt.date(2026, 11, 5)
    # previous local close 100 at 02:00, then a session 20:00-01:00 that opens at 103 and closes at 104
    bars = [{"ts": int(at(day, 2, 0).timestamp()), "open": 100.0, "close": 100.0}]
    bars += [{"ts": int((at(day, 20, 0) + dt.timedelta(hours=k)).timestamp()), "open": 103.0 + 0.2 * k, "close": 103.2 + 0.2 * k} for k in range(5)]
    s = Series("^X", bars)
    r = _session_return(s, at(day, 16, 0), at(day + dt.timedelta(days=1), 9, 0))
    check("session return runs from the session's open, leaving out the opening gap", abs(r - (104.0 / 103.0 - 1)) < 1e-12, f"{r}")
    check("no session inside the window -> None", _session_return(s, at(day, 3, 0), at(day, 9, 0)) is None)
    check("cash indices are recognised by the caret", is_cash_index("^HSI") and not is_cash_index("ES=F"))
    random.seed(11)
    rows = []
    for k in range(200):
        a, b = random.gauss(0, 0.01), random.gauss(0, 0.01)
        rows.append({"y": 0.9 * a + 0.3 * b + random.gauss(0, 0.001), "r": {"A": a, "B": b if k % 4 else None}})
    full = _oos(rows[:140], rows[140:], ["A"], None)
    same = _oos(rows[:140], rows[140:], ["A"], None, require=["B"])
    check("`require` scores a specification on the other one's nights", same["n_test"] < full["n_test"] and same["n_train"] < full["n_train"], f"{full['n_test']},{same['n_test']}")


def t_grade_helpers():
    print("grading helpers")
    from ovn.grade import _same_instant, _dist, _corr
    check("a quiet slot is not a print", not _same_instant({"volume": 0, "aligned": True, "prem_close_bps": 1.0}))
    check("a print with an older futures price is left out", not _same_instant({"volume": 10, "aligned": False, "prem_close_bps": 1.0}))
    check("a traded, same-instant print counts", _same_instant({"volume": 10, "aligned": True, "prem_close_bps": 1.0}))
    d = _dist([-2.0, 1.0, 3.0, -4.0, 10.0])
    check("distance summary: signed mean, absolute median and p90", d["mean_premium_bps"] == 1.6 and d["median_abs_bps"] == 3.0 and d["p90_abs_bps"] == 4.0, str(d))
    c = _corr([1, 2, 3, 4, 5], [2, 4, 6, 8, 10.5])
    check("correlation of a near-line is near one", c is not None and c > 0.99, f"{c}")
    check("too few points -> no correlation", _corr([1, 2], [1, 2]) is None)


def t_pins():
    print("window and snapshot pins")
    from ovn import util
    from ovn.nights import trading_days
    bars = [{"ts": int(at(dt.date(2026, 11, d), 9, 30).timestamp()), "open": 1.0, "close": 1.0} for d in (4, 5, 6, 9)]
    saved = dict(util._PINS)
    try:
        util._PINS.update({"end": None, "snapshot": None})
        check("no pin: every day in the feed", len(trading_days(Series("X", bars))) == 4)
        util.set_pins(end="2026-11-06")
        days = trading_days(Series("X", bars))
        check("--end drops the days after it", len(days) == 3 and days[-1][0] == dt.date(2026, 11, 6), str(days))
        util.set_pins(snapshot="2026-11-09")
        check("--asof names the snapshot day", util.snapshot_day() == "2026-11-09")
        try:
            util.cached_json("selftest_no_such_key", lambda: 1 / 0, frozen=True)
            check("a pinned run never fetches", False)
        except RuntimeError:
            check("a pinned run never fetches", True)
        try:
            util.set_pins(end="6 Nov 2026")
            check("a malformed date is refused", False)
        except ValueError:
            check("a malformed date is refused", True)
    finally:
        util._PINS.clear(); util._PINS.update(saved)


if __name__ == "__main__":
    for t in (t_static_band, t_ols, t_band, t_series, t_validate, t_holdings_csv,
              t_print_alignment, t_trading_band_hours, t_frankfurt_slots, t_hedge_session, t_grade_helpers, t_pins):
        t()
    print("\nSELFTEST", "PASSED" if FAILS == 0 else f"FAILED ({FAILS})")
    sys.exit(1 if FAILS else 0)

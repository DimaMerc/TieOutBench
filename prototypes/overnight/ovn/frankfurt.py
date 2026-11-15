"""The Frankfurt mirror: UCITS ETFs on US indices trade on Xetra from 9:00 to 17:30 Frankfurt time, and
until the US open (9:30 New York, usually 15:30 Frankfurt) their underlying is closed. This is the
European custodian's version of the overnight question, and the data is free.

Reference value during the European morning, anchored to the fund's own previous Xetra close (EUR):
    ref(t) = close_prev * (1 + beta * r_hedge(prev close -> t)) * EURUSD(prev close) / EURUSD(t)
with beta = 1 for an index tracker and the currency one-for-one (a USD basket in EUR terms), which is
what a market maker would use; a fitted beta on the first half of the window is reported as a check.
Every Xetra 15-minute bar before the US open is compared with ref(t). Ex-dividend days reduce the
anchor by the payout. Yahoo serves 60 days of 15-minute bars for Xetra tickers, so the window is the
last 60 trading days.
"""
from __future__ import annotations
import datetime as dt
import os
import statistics
from zoneinfo import ZoneInfo

from . import yahoo
from .model import ols, empirical_quantiles
from .util import Series, OUT, stored, write_json, window_end

BERLIN = ZoneInfo("Europe/Berlin")
NY = ZoneInfo("America/New_York")

FUNDS_DE = {
    "SXR8.DE": {"name": "iShares Core S&P 500 UCITS ETF USD (Acc)", "hedge": "ES=F"},
    "IUSA.DE": {"name": "iShares Core S&P 500 UCITS ETF USD (Dist)", "hedge": "ES=F"},
    "VUSA.DE": {"name": "Vanguard S&P 500 UCITS ETF (Dist)", "hedge": "ES=F"},
    "EQQQ.DE": {"name": "Invesco EQQQ Nasdaq-100 UCITS ETF (Dist)", "hedge": "NQ=F"},
    # thinner Xetra listings of the same US indices, so liquidity can be compared on the same basket
    "SPYL.DE": {"name": "SPDR S&P 500 UCITS ETF (Acc)", "hedge": "ES=F"},
    "D5BM.DE": {"name": "Xtrackers S&P 500 Swap UCITS ETF 1C", "hedge": "ES=F"},
    "LYPS.DE": {"name": "Amundi Core S&P 500 Swap UCITS ETF (EUR Dist)", "hedge": "ES=F"},
    "H4ZF.DE": {"name": "HSBC S&P 500 UCITS ETF", "hedge": "ES=F"},
    "ZPRR.DE": {"name": "SPDR Russell 2000 US Small Cap UCITS ETF", "hedge": "RTY=F"},
}
FX = "EURUSD=X"


def _us_open_berlin(day: dt.date) -> dt.datetime:
    return dt.datetime(day.year, day.month, day.day, 9, 30, tzinfo=NY).astimezone(BERLIN)


def slots_before_us_open(day: dt.date) -> int:
    """15-minute slots from the Xetra open (9:00 Frankfurt) to the US open that day: 26 when New York
    opens at 15:30 Frankfurt time, 22 in the weeks when only one side has changed its clocks."""
    xetra_open = dt.datetime(day.year, day.month, day.day, 9, 0, tzinfo=BERLIN)
    return int((_us_open_berlin(day) - xetra_open).total_seconds() // 900)


def _sessions(bars: list) -> dict:
    """Group a fund's 15-minute bars by Frankfurt trading day -> list of bars (sorted)."""
    out = {}
    for b in bars:
        d = dt.datetime.fromtimestamp(b["ts"], BERLIN).date()
        out.setdefault(d, []).append(b)
    for d in out:
        out[d].sort(key=lambda b: b["ts"])
    return out


def build_fund(ticker: str, refresh: bool = False) -> dict:
    spec = FUNDS_DE[ticker]
    fund15 = yahoo.chart(ticker, "60d", "15m", prepost=False, refresh=refresh)
    hedge15 = Series(spec["hedge"], yahoo.chart(spec["hedge"], "60d", "15m", prepost=True, refresh=refresh))
    fx15 = Series(FX, yahoo.chart(FX, "60d", "15m", prepost=True, refresh=refresh))
    try:
        divs = yahoo.dividends(ticker, years=1, refresh=refresh)
    except Exception:  # noqa: BLE001
        divs = {}
    sessions = _sessions(fund15)
    end = window_end()
    days = sorted(d for d in sessions if end is None or d <= end)
    records = []
    for i in range(1, len(days)):
        d0, d1 = days[i - 1], days[i]
        prev = sessions[d0]
        # previous Xetra close: last bar of the previous session (bar start 17:15 covers to 17:30)
        prev_close_bar = prev[-1]
        anchor_t = dt.datetime.fromtimestamp(prev_close_bar["ts"], BERLIN) + dt.timedelta(minutes=15)
        close_prev = prev_close_bar["close"]
        div = divs.get(d1.isoformat(), 0.0) or 0.0
        anchor = close_prev - div
        h0, _ = hedge15.asof(anchor_t)
        f0, _ = fx15.asof(anchor_t)
        if h0 is None or f0 is None:
            continue
        us_open = _us_open_berlin(d1)
        prints = []
        for b in sessions[d1]:
            t_end = dt.datetime.fromtimestamp(b["ts"], BERLIN) + dt.timedelta(minutes=15)
            if t_end > us_open:
                break
            h1, hs = hedge15.asof(t_end)
            f1, fs = fx15.asof(t_end)
            if h1 is None or f1 is None or (t_end - hs).total_seconds() > 2.5 * 3600 or (t_end - fs).total_seconds() > 2.5 * 3600:
                continue
            rh = h1 / h0 - 1.0
            rfx = f1 / f0 - 1.0
            ref = anchor * (1.0 + rh) * (f0 / f1)         # beta 1, currency one-for-one
            prints.append({"t": t_end.isoformat(timespec="minutes"), "close": b["close"], "volume": b.get("volume"),
                           "rh": rh, "rfx": rfx, "ref": ref, "dev_bps": (b["close"] / ref - 1.0) * 1e4})
        if not prints:
            continue
        last = prints[-1]
        records.append({"date": d1.isoformat(), "prev_close": close_prev, "dividend": div, "anchor": anchor,
                        "us_open_berlin": us_open.isoformat(timespec="minutes"), "n_bars": len(prints),
                        "slots": slots_before_us_open(d1),
                        "y_morning": last["close"] / anchor - 1.0, "rh_morning": last["rh"], "rfx_morning": last["rfx"],
                        "prints": prints})
    return {"ticker": ticker, "spec": spec, "records": records}


def analyse(doc: dict, calendar: list | None = None) -> dict:
    """`calendar` is the list of Xetra session dates in the window (taken from the most traded fund):
    the feed returns a 15-minute bar only when something traded in it, so the share of slots with a
    trade has to be counted against the session's slots, not against the bars the feed happened to
    return, and a day on which a thin fund did not trade at all still counts its slots."""
    recs = doc["records"]
    if len(recs) < 10:
        return {"error": f"only {len(recs)} sessions"}
    half = len(recs) // 2
    cal, evl = recs[:half], recs[half:]
    traded = [p for r in recs for p in r["prints"] if (p.get("volume") or 0) > 0]
    all_bars = [p for r in recs for p in r["prints"]]
    if calendar:
        days = [d for d in calendar if recs[0]["date"] <= d <= recs[-1]["date"]]
        slots = sum(slots_before_us_open(dt.date.fromisoformat(d)) for d in days)
    else:
        days = [r["date"] for r in recs]
        slots = sum(r["slots"] for r in recs)
    devs = [p["dev_bps"] for p in traded]
    ab = sorted(abs(x) for x in devs)
    by_hour = {}
    for p in traded:
        by_hour.setdefault(int(p["t"][11:13]), []).append(p["dev_bps"])
    # trading band from the first half, coverage on the second
    cal_abs = [abs(p["dev_bps"]) / 1e4 for r in cal for p in r["prints"] if (p.get("volume") or 0) > 0]
    band = empirical_quantiles(cal_abs) if len(cal_abs) >= 50 else None
    cov = None
    if band:
        ev_tr = [p for r in evl for p in r["prints"] if (p.get("volume") or 0) > 0]
        cov = {"n": len(ev_tr), "coverage": stored(sum(1 for p in ev_tr if abs(p["dev_bps"]) / 1e4 <= band["q90"]) / len(ev_tr), 3) if ev_tr else None}
    # fitted beta check: y_morning on hedge and fx over the first half, scored on the second
    fit = None
    try:
        tr = [r for r in cal]; te = [r for r in evl]
        f = ols([r["y_morning"] for r in tr], [[1.0, r["rh_morning"], r["rfx_morning"]] for r in tr])
        b = f["b"]
        pred = [b[0] + b[1] * r["rh_morning"] + b[2] * r["rfx_morning"] for r in te]
        y = [r["y_morning"] for r in te]; ybar = sum(y) / len(y)
        sse = sum((a - p) ** 2 for a, p in zip(y, pred)); sst = sum((a - ybar) ** 2 for a in y) or 1e-18
        naive = [(1 + r["rh_morning"]) / (1 + r["rfx_morning"]) - 1 for r in te]   # beta 1, fx one-for-one
        sse_n = sum((a - p) ** 2 for a, p in zip(y, naive))
        fit = {"beta_hedge": stored(b[1], 3), "gamma_fx": stored(b[2], 3), "r2_train": stored(f["r2"], 3),
               "r2_oos_fitted": stored(1 - sse / sst, 3), "r2_oos_beta1": stored(1 - sse_n / sst, 3),
               "mae_fitted_bps": stored(statistics.fmean(abs(a - p) for a, p in zip(y, pred)) * 1e4, 1),
               "mae_beta1_bps": stored(statistics.fmean(abs(a - p) for a, p in zip(y, naive)) * 1e4, 1), "n_train": len(tr), "n_test": len(te)}
    except Exception as e:  # noqa: BLE001
        fit = {"error": str(e)[:120]}
    return {
        "sessions": len(days), "sessions_with_a_bar": len(recs), "from": recs[0]["date"], "to": recs[-1]["date"],
        "slots_before_us_open": slots, "bars_in_feed": len(all_bars), "traded_bars": len(traded),
        "traded_share": stored(len(traded) / slots, 3) if slots else None,
        "mean_dev_bps": stored(statistics.fmean(devs), 1) if devs else None,
        "median_dev_bps": stored(statistics.median(devs), 1) if devs else None,
        "median_abs_bps": stored(statistics.median(ab), 1) if ab else None,
        "p90_abs_bps": stored(ab[int(0.9 * (len(ab) - 1))], 1) if ab else None,
        "by_hour_berlin": {str(h): {"n": len(v), "median_abs_bps": stored(statistics.median(abs(x) for x in v), 1), "mean_bps": stored(statistics.fmean(v), 1)} for h, v in sorted(by_hour.items())},
        "trading_band": ({"q50_bps": stored(band["q50"] * 1e4, 1), "q90_bps": stored(band["q90"] * 1e4, 1), "calibration_prints": len(cal_abs), **(cov or {})} if band else {"insufficient_prints": len(cal_abs)}),
        "fit_check": fit,
        "dividends_in_window": sum(1 for r in recs if r["dividend"]),
    }


def run(refresh: bool = False) -> dict:
    out = {}
    docs = {}
    for t in FUNDS_DE:
        try:
            docs[t] = build_fund(t, refresh=refresh)
        except Exception as e:  # noqa: BLE001
            out[t] = {"error": str(e)[:300]}
            print(f"[frankfurt] {t}: FAILED {str(e)[:160]}", flush=True)
    # the Xetra calendar of the window: every date on which any of the funds has a record
    calendar = sorted({r["date"] for d in docs.values() for r in d["records"]})
    for t, doc in docs.items():
        try:
            a = analyse(doc, calendar)
            out[t] = {"name": FUNDS_DE[t]["name"], "hedge": FUNDS_DE[t]["hedge"], "analysis": a}
            write_json(os.path.join(OUT, f"frankfurt_{t.replace('.', '_')}.json"), doc)
            tb = a.get("trading_band", {})
            print(f"[frankfurt] {t}: {a.get('sessions')} sessions {a.get('from')}..{a.get('to')}, traded share {a.get('traded_share')}, "
                  f"median |dev| {a.get('median_abs_bps')} bps, p90 {a.get('p90_abs_bps')}, mean {a.get('mean_dev_bps')} | band q90 {tb.get('q90_bps')} cov {tb.get('coverage')} | "
                  f"fit beta {(a.get('fit_check') or {}).get('beta_hedge')} fx {(a.get('fit_check') or {}).get('gamma_fx')} R2 oos fitted/beta1 {(a.get('fit_check') or {}).get('r2_oos_fitted')}/{(a.get('fit_check') or {}).get('r2_oos_beta1')}", flush=True)
        except Exception as e:  # noqa: BLE001
            out[t] = {"error": str(e)[:300]}
            print(f"[frankfurt] {t}: FAILED {str(e)[:160]}", flush=True)
    write_json(os.path.join(OUT, "frankfurt.json"), out)
    return out

"""Build one record per fund per night, then fit the model on the nights before the test window and
score the test nights hour by hour. Output: data/out/nights_<TICKER>.json and fits.json."""
from __future__ import annotations
import csv
import datetime as dt
import math
import os

from . import yahoo, tiingo
from .config import FUNDS, GRID_HOURS, STALE_HOURS, MIN_TRAIN_NIGHTS
from .model import (static_band, fit_overnight, hourly_sigma, carry_forward, band, trip_wire,
                    empirical_quantiles, empirical_band)
from .util import Series, at, iso, NAV_DIR, OUT, write_json, TZ_ET, window_end, snapshot_day

SESSION_SLOTS = 96           # 5-minute slots in one overnight session, 8:00pm to 4:00am
BASE_MAX_LAG_S = 3600        # a futures price more than an hour old at 4pm is not a 4pm price


# ---------------- inputs ----------------
def load_nav_file(ticker: str) -> dict:
    """data/nav/<TICKER>.csv with columns date,nav[,nav_nonfv,exdiv] -> {date: nav}. Empty if absent.
    The non-fair-valued NAV, when present, is kept in a parallel dict reachable via load_nav_extra()."""
    p = os.path.join(NAV_DIR, f"{ticker}.csv")
    out = {}
    if not os.path.exists(p):
        return out
    with open(p, encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            try:
                out[row["date"].strip()] = float(row["nav"])
            except (KeyError, ValueError):
                continue
    return out


def load_nav_extra(ticker: str) -> dict:
    """{date: {"nav_nonfv": x, "exdiv": y}} for the columns an issuer file provides; empty otherwise."""
    p = os.path.join(NAV_DIR, f"{ticker}.csv")
    out = {}
    if not os.path.exists(p):
        return out
    with open(p, encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            d = (row.get("date") or "").strip()
            rec = {}
            for k in ("nav_nonfv", "exdiv"):
                v = (row.get(k) or "").strip()
                if v:
                    try:
                        rec[k] = float(v)
                    except ValueError:
                        pass
            if d and rec:
                out[d] = rec
    return out


def fund_dividends(ticker: str, refresh: bool = False) -> dict:
    """{ex_date_iso: cash per share}: the market-data feed's dividend events, overridden by the issuer's
    own ex-dividend column when the NAV file has one (the feed lagged a November ex-date for the bond
    funds; amounts otherwise agree to the cent). One function so every module scores the same mornings."""
    try:
        divs = dict(yahoo.dividends(ticker, refresh=refresh))
    except Exception as e:  # noqa: BLE001
        print(f"[dividends] {ticker}: feed unavailable ({str(e)[:60]})")
        divs = {}
    divs.update({d: x["exdiv"] for d, x in load_nav_extra(ticker).items() if x.get("exdiv")})
    return divs


def trading_days(daily: Series) -> list:
    """[(date, open, close)] from the fund's daily bars, up to the pinned window end if there is one."""
    end = window_end()
    out = []
    for b in daily.bars:
        d = dt.datetime.fromtimestamp(b["ts"], TZ_ET).date()
        if b.get("open") is None or (end is not None and d > end):
            continue
        out.append((d, b["open"], b["close"]))
    return out


def _stale_limit(sym: str) -> float:
    return STALE_HOURS.get(sym, STALE_HOURS["default"])


def _ret(ser: Series, t0: dt.datetime, t1: dt.datetime, sym: str):
    """(return from t0 to t1, stale_flag or None). Uses the last bar started before each time."""
    p0, s0 = ser.asof(t0)
    p1, s1 = ser.asof(t1)
    if p0 is None or p1 is None or p0 == 0:
        return None, f"signal_missing:{sym}"
    lim = _stale_limit(sym)
    if (t1 - s1).total_seconds() > lim * 3600:
        return None, f"signal_stale:{sym}"
    return p1 / p0 - 1.0, None


def _ret_closed(ser: Series, width_s: int, t0: dt.datetime, t1: dt.datetime, sym: str):
    """(return t0 -> t1, flag or None, seconds from the close of the bar used to t1), from bars that had
    CLOSED by each time. The overnight prints are 5-minute bars, off the hourly grid, so `asof` (last
    bar started) would hand a print ending 01:05 the futures price of 02:00."""
    p0, e0 = ser.closed_asof(t0, width_s)
    p1, e1 = ser.closed_asof(t1, width_s)
    if p0 is None or p1 is None or p0 == 0 or (t0 - e0).total_seconds() > BASE_MAX_LAG_S:
        return None, f"signal_missing:{sym}", None
    lag = (t1 - e1).total_seconds()
    if lag > _stale_limit(sym) * 3600:
        return None, f"signal_stale:{sym}", None
    return p1 / p0 - 1.0, None, lag


def _print_signal(fine: Series | None, coarse: Series, t0: dt.datetime, t1: dt.datetime, sym: str):
    """A hedge or currency return at a print's own time: from the 5-minute bars when the feed still
    serves them for that night, else from the last hourly bar that had closed.
    -> (return, flag, resolution, lag_seconds). lag 0 means the bar closes at the print's close."""
    if fine is not None and len(fine) > 0:
        r, _, lag = _ret_closed(fine, 300, t0, t1, sym)
        if r is not None:
            return r, None, "5m", lag
    r, fl, lag = _ret_closed(coarse, 3600, t0, t1, sym)
    return r, fl, "1h", lag


def trade_quantile(by_hour: dict, pooled: float, t_iso: str) -> float:
    """The trading band's quantile for the hour of a print stamped `t_iso`. The by-hour table is keyed
    by str(int hour), "1" and not the "01" of the timestamp; an hour without its own entry (fewer than
    30 calibration prints) gets the pooled quantile."""
    return by_hour.get(str(int(t_iso[11:13])), pooled)


def _sale_1945(q15: Series, date: dt.date):
    """Last 15-minute bar starting before 19:45 and at or after 16:00 that day -> its close."""
    if len(q15) == 0:
        return None, None
    c, start = q15.last_before(at(date, 19, 45), after=at(date, 16, 0))
    return c, (iso(start) if start else None)


# ---------------- build ----------------
def build_fund(ticker: str, nights: int, refresh: bool = False, tape_start: dt.date | None = None) -> dict:
    spec = FUNDS[ticker]
    daily = yahoo.daily(ticker, years=2, refresh=refresh)
    q15 = yahoo.quarter_hour_prepost(ticker, refresh=refresh)
    hedge, hedge_sym, fb = yahoo.try_hourly(spec["hedges"], refresh=refresh)
    if hedge is None:
        raise RuntimeError(f"{ticker}: no hedge instrument with data among {spec['hedges']}")
    fx = yahoo.hourly(spec["fx"], refresh=refresh) if spec.get("fx") else None
    locals_ = {s: yahoo.hourly(s, refresh=refresh) for s in spec.get("local", [])}
    navs = load_nav_file(ticker)
    nav_extra = load_nav_extra(ticker)
    days = trading_days(daily)
    divs = fund_dividends(ticker, refresh=refresh)

    tape = None
    hedge5 = fx5 = None
    if tiingo.available() and days:
        t0 = tape_start or (days[-nights - 1][0] if len(days) > nights else days[0][0])
        tape = tiingo.overnight_bars(ticker, t0, days[-1][0] + dt.timedelta(days=1))
        # 5-minute hedge bars, so a 5-minute print is compared with the futures bar of the same five
        # minutes. The feed serves about sixty trading days of them; older nights fall back to hourly
        # bars, where only a print ending on the hour has a futures price of the same instant.
        try:
            hedge5 = yahoo.five_minute(hedge_sym, refresh=refresh)
            if spec.get("fx"):
                fx5 = yahoo.five_minute(spec["fx"], refresh=refresh)
        except Exception as e:  # noqa: BLE001
            print(f"[build] {ticker}: no 5-minute hedge bars ({str(e)[:80]}); prints will use hourly references")
            hedge5 = fx5 = None

    records = []
    for i in range(len(days) - 1):
        d, open_d, close_d = days[i]
        d1, open_d1, close_d1 = days[i + 1]
        flags = []
        if fb:
            flags.append(f"hedge_fallback:{hedge_sym}")
        nav_d = navs.get(d.isoformat())
        if spec.get("nav_anchor") == "close":
            nav_d = close_d
            flags.append("nav_anchor_close")          # official NAV struck at another hour (GLD: London PM fix)
        elif nav_d is None:
            nav_d, flag = close_d, "nav_proxy_close"
            flags.append(flag)
        nav_d1 = navs.get(d1.isoformat())
        sale, sale_t = _sale_1945(q15, d)
        if sale is None:
            sale_used, flags = close_d, flags + ["sale_1945_proxy_close"]
        else:
            sale_used = sale
        lo_s, hi_s = static_band(close_d, sale_used)

        base_t = at(d, 16, 0)
        end_t = at(d1, 9, 0)          # hedge measured to 9:00; the ETF opens at 9:30 (documented gap)
        rh_full, fl = _ret(hedge, base_t, end_t, hedge_sym)
        if fl:
            flags.append("full:" + fl)
        rfx_full = 0.0
        if fx is not None:
            v, fl = _ret(fx, base_t, end_t, spec["fx"])
            rfx_full = (spec["fx_dir"] * v) if v is not None else None
            if fl:
                flags.append("full:" + fl)

        # hour grid on the night before d1
        grid = []
        prev_day = d1 - dt.timedelta(days=1)
        for h in GRID_HOURS:
            t = at(prev_day if h >= 20 else d1, h, 0)
            rh, f1 = _ret(hedge, base_t, t, hedge_sym)
            rfx, f2 = (None, None)
            if fx is not None:
                v, f2 = _ret(fx, base_t, t, spec["fx"])
                rfx = (spec["fx_dir"] * v) if v is not None else None
            loc = {}
            for s, ser in locals_.items():
                v, f3 = _ret(ser, base_t, t, s)
                loc[s] = {"ret": v, "flag": f3}
            hours_left = (at(d1, 9, 0) - t).total_seconds() / 3600.0
            grid.append({"t": iso(t), "hour": h, "hours_left": round(hours_left, 2),
                         "rh": rh, "rfx": rfx, "flags": [x for x in (f1, f2) if x], "local": loc})

        # overnight tape (real prints) if available. Each print carries the hedge and currency return
        # at its own close, taken only from bars that had closed by then: the 5-minute bar of the same
        # five minutes where the feed has it, else the last closed hourly bar. `aligned` marks the
        # prints whose futures price is of the same instant (lag 0); the print statistics use those.
        prints = None
        if tape is not None and len(tape) > 0:
            bars = tape.between(at(prev_day, 20, 0), at(d1, 4, 0))
            prints = []
            for b in bars:
                t_end = dt.datetime.fromtimestamp(b["ts"], TZ_ET) + dt.timedelta(minutes=5)
                rhp, fp1, res, lag = _print_signal(hedge5, hedge, base_t, t_end, hedge_sym)
                rfxp, fp2 = (None, None)
                if fx is not None:
                    v, fp2, res_fx, lag_fx = _print_signal(fx5, fx, base_t, t_end, spec["fx"])
                    rfxp = (spec["fx_dir"] * v) if v is not None else None
                    if "1h" in (res, res_fx):
                        res = "1h"
                    lag = None if (lag is None or lag_fx is None) else max(lag, lag_fx)
                prints.append({"t": iso(dt.datetime.fromtimestamp(b["ts"], TZ_ET)), "close": b["close"],
                               "high": b.get("high"), "low": b.get("low"), "volume": b.get("volume"),
                               "rh": rhp, "rfx": rfxp, "flags": [x for x in (fp1, fp2) if x],
                               "hedge_res": res, "hedge_lag_s": lag, "aligned": lag == 0})

        gap_days = (d1 - d).days
        # ex-dividend morning: the shares open lower by the distribution through no fault of the hedge.
        # Overnight prints are still cum-dividend, so the adjustment is applied to the OPEN (add the
        # payout back) wherever the open is the truth, and nowhere else.
        div1 = divs.get(d1.isoformat(), 0.0) or 0.0
        if div1:
            flags.append(f"exdiv:{div1:.4f}")
        open_cum = open_d1 + div1
        records.append({
            "ticker": ticker, "kind": spec["kind"], "date": d.isoformat(), "next_date": d1.isoformat(),
            "weekend_or_holiday_gap": gap_days > 1,
            "close": close_d, "nav": nav_d,
            "nav_source": ("close_anchor" if "nav_anchor_close" in flags else "proxy_close" if "nav_proxy_close" in flags else "file"),
            "nav_official": navs.get(d.isoformat()),      # the issuer's figure, whatever anchor is used
            "nav_nonfv": (nav_extra.get(d.isoformat()) or {}).get("nav_nonfv"),
            "close_vs_nav_bps": (close_d / nav_d - 1.0) * 1e4,
            "sale_1945": sale, "sale_1945_time": sale_t,
            "static_band": [lo_s, hi_s],
            "truth_open": open_d1, "dividend_next": div1, "truth_open_cum": open_cum,
            "truth_nav_next": nav_d1, "truth_label": "truth_open_yahoo",
            "y_open": open_cum / nav_d - 1.0,
            "hedge": hedge_sym, "rh_full": rh_full, "rfx_full": rfx_full,
            "grid": grid, "prints": prints, "flags": flags,
        })

    # train / test split: last `nights` records are the test window
    test = records[-nights:]
    train = [r for r in records[:-nights]
             if r["rh_full"] is not None and (fx is None or r["rfx_full"] is not None)]
    if len(train) < MIN_TRAIN_NIGHTS:
        raise RuntimeError(f"{ticker}: only {len(train)} usable training nights (< {MIN_TRAIN_NIGHTS})")
    fit = fit_overnight([{"y": r["y_open"], "rh": r["rh_full"], "rfx": r["rfx_full"] or 0.0} for r in train],
                        use_fx=fx is not None)

    # hourly hedge volatility over the training window's overnight hours
    lr = []
    for r in train:
        g = r["grid"]
        for a, b in zip(g, g[1:]):
            if a["rh"] is not None and b["rh"] is not None:
                lr.append(math.log((1 + b["rh"]) / (1 + a["rh"])))
    sig_hr = hourly_sigma(lr)

    # empirical calibration: the carry-forward's own absolute error at each grid hour, on TRAIN nights
    errs_by_hour = {h: [] for h in GRID_HOURS}
    for r in train:
        for g in r["grid"]:
            if g["rh"] is None or (fx is not None and g["rfx"] is None):
                continue
            c = carry_forward(r["nav"], fit, g["rh"], g["rfx"] or 0.0)
            errs_by_hour[g["hour"]].append(abs(c / r["truth_open_cum"] - 1.0))
    q_by_hour = {str(h): empirical_quantiles(v) for h, v in errs_by_hour.items()}

    # regime check: full-night residual spread in the test window vs the training fit
    test_res = [r["y_open"] - (fit["alpha"] + fit["beta"] * r["rh_full"] + fit["gamma"] * (r["rfx_full"] or 0.0))
                for r in test if r["rh_full"] is not None and (fx is None or r["rfx_full"] is not None)]
    sigma_test = (sum(e * e for e in test_res) / max(1, len(test_res) - 1)) ** 0.5 if len(test_res) > 2 else None

    fit.update({"sigma_hedge_hourly": sig_hr, "hedge": hedge_sym, "fx": spec.get("fx"),
                "q_by_hour": q_by_hour, "sigma_resid_test": sigma_test,
                "train_from": train[0]["date"], "train_to": train[-1]["date"],
                "test_from": test[0]["date"], "test_to": test[-1]["date"], "n_test": len(test)})

    # score the test nights
    for r in test:
        for g in r["grid"]:
            ok = g["rh"] is not None and (fx is None or g["rfx"] is not None)
            if ok:
                c = carry_forward(r["nav"], fit, g["rh"], g["rfx"] or 0.0)
                lo, hi, half_bps = band(c, fit, sig_hr, g["hours_left"])
                q90 = q_by_hour[str(g["hour"])].get("q90")
                lo_e, hi_e, half_e = empirical_band(c, q90) if q90 is not None else (None, None, None)
                g.update({"ref": c, "band": [lo, hi], "half_bps": half_bps,
                          "band_emp": [lo_e, hi_e] if lo_e is not None else None, "half_emp_bps": half_e})
            else:
                g.update({"ref": None, "band": None, "half_bps": None, "band_emp": None, "half_emp_bps": None})
            stale = [f.split(":", 1)[1] for f in g["flags"] if f.startswith("signal_stale")]
            g["status"] = trip_wire(ok, stale, g["half_emp_bps"] or g["half_bps"] or 0.0)
        # two reference values at each real print's time: the official continuation (anchored to the
        # NAV) and the market continuation (anchored to the 4pm close). Overnight trades price off the
        # fund's own last trade, so the trading band and the print comparison use the close anchor;
        # the open-based grading above uses the NAV anchor.
        for p in (r.get("prints") or []):
            ok = p["rh"] is not None and (fx is None or p["rfx"] is not None)
            if not ok:
                p["ref"] = None; p["prem_bps"] = None; p["ref_close"] = None; p["prem_close_bps"] = None; continue
            c = carry_forward(r["nav"], fit, p["rh"], p["rfx"] or 0.0)
            cc = carry_forward(r["close"], fit, p["rh"], p["rfx"] or 0.0)
            hh = int(p["t"][11:13])
            q90 = q_by_hour.get(str(hh), {}).get("q90")
            p["ref"] = c
            p["prem_bps"] = (p["close"] / c - 1.0) * 1e4
            p["ref_close"] = cc
            p["prem_close_bps"] = (p["close"] / cc - 1.0) * 1e4
            p["outside_band"] = (abs(p["close"] / c - 1.0) > q90) if q90 is not None else None

    # trading band: calibrated on the fund's own traded prints over the first half of the test window,
    # applied to the second half. It answers "where should this trade now", the open band answers
    # "where will this open"; the two differ by an order of magnitude for the liquid funds.
    # Only prints with a futures price of the same instant (`aligned`) enter, on both halves.
    fit["trading_band"] = None
    if tape is not None and len(tape) > 0:
        half_n = len(test) // 2
        cal, evl = test[:half_n], test[half_n:]
        pooled, by_hour = [], {}
        for r in cal:
            for p in (r.get("prints") or []):
                if (p.get("volume") or 0) > 0 and p.get("aligned") and p.get("prem_close_bps") is not None:
                    a = abs(p["prem_close_bps"]) / 1e4          # market continuation: close anchor
                    pooled.append(a)
                    by_hour.setdefault(int(p["t"][11:13]), []).append(a)
        if len(pooled) >= 50:
            qp = empirical_quantiles(pooled)
            qh = {str(h): (empirical_quantiles(v)["q90"] if len(v) >= 30 else qp["q90"]) for h, v in by_hour.items()}
            fit["trading_band"] = {"calibration_from": cal[0]["date"], "calibration_to": cal[-1]["date"],
                                   "evaluation_from": evl[0]["date"], "evaluation_to": evl[-1]["date"],
                                   "n_calibration_prints": len(pooled), "q50_pooled_bps": round(qp["q50"] * 1e4, 1),
                                   "q90_pooled_bps": round(qp["q90"] * 1e4, 1),
                                   "q90_by_hour_bps": {h: round(q * 1e4, 1) for h, q in qh.items()}}
            for r in evl:
                r["trading_band_eval"] = True
                for g in r["grid"]:
                    if g.get("ref") is not None:
                        q = qh.get(str(g["hour"]), qp["q90"])
                        cc = carry_forward(r["close"], fit, g["rh"], g["rfx"] or 0.0)
                        g["ref_close"] = cc
                        g["band_trade"] = [cc * (1 - q), cc * (1 + q)]
                        g["half_trade_bps"] = q * 1e4
                for p in (r.get("prints") or []):
                    if p.get("prem_close_bps") is not None:
                        p["outside_trade_band"] = abs(p["prem_close_bps"]) / 1e4 > trade_quantile(qh, qp["q90"], p["t"])
        else:
            fit["trading_band"] = {"insufficient_prints": len(pooled)}

    out = {"ticker": ticker, "spec": spec, "fit": fit, "test": test,
           "n_train": len(train), "n_records": len(records),
           "tape": "tiingo_boats" if (tape is not None and len(tape) > 0) else None,
           "session_slots": SESSION_SLOTS,
           "pins": {"snapshot_day": snapshot_day(), "window_end": test[-1]["next_date"]}}
    write_json(os.path.join(OUT, f"nights_{ticker}.json"), out)
    return out


def build_all(tickers: list, nights: int, refresh: bool = False) -> dict:
    fits = {}
    for t in tickers:
        try:
            res = build_fund(t, nights, refresh=refresh)
            fits[t] = res["fit"]
            print(f"[build] {t}: {res['n_train']} train nights, {len(res['test'])} test nights, "
                  f"hedge {res['fit']['hedge']}, beta {res['fit']['beta']:.3f}, "
                  f"resid {res['fit']['sigma_resid']*1e4:.0f} bps, R2 {res['fit']['r2']:.2f}"
                  + (", tape: yes" if res["tape"] else ", tape: none"))
        except Exception as e:  # noqa: BLE001 - keep going, report at the end
            print(f"[build] {t}: FAILED: {e}")
            fits[t] = {"error": str(e)}
    write_json(os.path.join(OUT, "fits.json"), fits)
    return fits

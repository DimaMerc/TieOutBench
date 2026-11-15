"""Hedge proposer: a language model reads a fund's holdings and proposes which overnight-tradable
instruments should carry its reference value; the data then accepts or rejects the proposal on
out-of-sample fit. The model chooses; it never sets the number.

For each fund:
  baseline  = the hand-picked hedge in config (first instrument with data, plus the currency pair)
  proposal  = up to four instruments from the universe below, with the model's weights
  two tests = (fixed) a single composite built with the model's weights, beta fitted on training nights;
              (free) the proposed instruments as separate regressors, coefficients fitted on training nights
  score     = out-of-sample R-squared and mean absolute error on the same 60 test nights the paper uses,
              plus hallucination checks: unknown symbols, instruments closed overnight, missing data.
"""
from __future__ import annotations
import datetime as dt
import json
import math
import os
import statistics

from . import yahoo
from .config import FUNDS, EVIDENCE_MODELS
from .model import ols
from .nights import trading_days, _ret, fund_dividends
from .util import OUT, at, stored, write_json, read_json
from . import evidence as ev

UNIVERSE = {
    # futures and spot that trade through the US night
    "ES=F": "S&P 500 E-mini future (CME Globex, about 23 hours a day Sunday 6pm to Friday 5pm ET)",
    "NQ=F": "Nasdaq-100 E-mini future (same hours)",
    "YM=F": "Dow Jones E-mini future (same hours)",
    "RTY=F": "Russell 2000 E-mini future (same hours)",
    "NIY=F": "Nikkei 225 future, yen denominated (CME, about 23 hours)",
    "NKD=F": "Nikkei 225 future, dollar denominated (CME, about 23 hours)",
    "ZB=F": "US Treasury 30-year bond future (CBOT, about 23 hours)",
    "ZN=F": "US Treasury 10-year note future (CBOT, about 23 hours)",
    "ZF=F": "US Treasury 5-year note future (CBOT, about 23 hours)",
    "GC=F": "Gold future (COMEX, about 23 hours)",
    "SI=F": "Silver future (COMEX, about 23 hours)",
    "CL=F": "WTI crude oil future (NYMEX, about 23 hours)",
    "HG=F": "Copper future (COMEX, about 23 hours)",
    "BTC-USD": "Bitcoin spot (24 hours, 7 days)",
    "ETH-USD": "Ether spot (24 hours, 7 days)",
    # currencies, quoted as the feed quotes them
    "JPY=X": "USD/JPY, yen per dollar: a rise means a weaker yen",
    "EURUSD=X": "EUR/USD, dollars per euro: a rise means a stronger euro",
    "GBPUSD=X": "GBP/USD, dollars per pound",
    "AUDUSD=X": "AUD/USD, dollars per Australian dollar",
    "KRW=X": "USD/KRW, won per dollar: a rise means a weaker won",
    "TWD=X": "USD/TWD, Taiwan dollars per US dollar",
    "INR=X": "USD/INR, rupees per dollar",
    "CNY=X": "USD/CNY, yuan per dollar",
    "BRL=X": "USD/BRL, reais per dollar",
    "MXN=X": "USD/MXN, pesos per dollar",
    # cash indices: only priced during their local session
    "^N225": "Nikkei 225 cash index, Tokyo session only (about 7pm to 1:30am ET in winter)",
    "^HSI": "Hang Seng cash index, Hong Kong session only (about 8:30pm to 3am ET)",
    "^KS11": "KOSPI cash index, Seoul session only (about 7pm to 1:30am ET)",
    "^TWII": "Taiwan TAIEX cash index, Taipei session only (about 8pm to 12:30am ET)",
    "^GDAXI": "DAX cash index, Frankfurt session only (about 3am to 11:30am ET)",
    "^FTSE": "FTSE 100 cash index, London session only (about 3am to 11:30am ET)",
    "^STOXX50E": "Euro Stoxx 50 cash index, European session only (about 3am to 11:30am ET)",
    "^BSESN": "BSE Sensex cash index, Mumbai session only (about 10:45pm to 5am ET)",
    "^BVSP": "Bovespa cash index, Sao Paulo session only (about 8am to 4pm ET: closed overnight)",
}

SYSTEM = """You are a capital-markets analyst choosing the hedge instruments that should carry an ETF's
overnight reference value, that is, the instruments whose moves between 4pm New York and the next 9:30am
open best explain the fund's own move over the same hours.

You are given the fund, its largest holdings with weights and where they are listed, and a universe of
instruments that have overnight prices, with their trading hours. Choose at most four instruments and
give each a weight. Convention: the weight is the fund's return per unit return of the instrument, so a
fund holding yen assets gets a NEGATIVE weight on USD/JPY (yen per dollar). Equity weights should sum to
roughly the fund's equity exposure. Prefer instruments that trade through the whole night over cash
indices that price only in their local session, and say so if you make an exception. Use only symbols
from the universe, exactly as written.

Reply with ONE JSON object and nothing else:
{"instruments": [{"symbol": "...", "weight": <number>, "role": "equity"|"rates"|"commodity"|"crypto"|"fx"}],
 "rationale": "<at most 40 words>"}
"""


def _user_prompt(ticker: str, holdings: list, extra: dict) -> str:
    uni = "\n".join(f"  {s}: {d}" for s, d in UNIVERSE.items())
    hold = "\n".join(f"  {h.get('name') or h['symbol']} [{h['symbol']}] {h['weight']:.1f}%"
                     + (f" ({h['location']})" if h.get("location") else "")
                     + (f", {h['sector']}" if h.get("sector") else "") for h in holdings) or "  (not available)"
    spec = FUNDS[ticker]
    return (f"Fund: {ticker} ({spec['name']}). Current hand-picked hedge in the prototype: {spec['hedges'][0]}"
            + (f" plus {spec['fx']}" if spec.get("fx") else "") + ".\n"
            f"Largest holdings:\n{hold}\n"
            + (f"Country mix of the top holdings: {extra['countries']}\n" if extra.get("countries") else "")
            + f"Instrument universe:\n{uni}")


def holdings_with_countries(ticker: str) -> tuple[list, dict]:
    h = ev.holdings_for(ticker, 15)
    countries = {}
    for x in h:
        loc = x.get("location") or ("United States" if (x["symbol"].isalpha() and len(x["symbol"]) <= 5 and not x.get("location")) else "unknown")
        countries[loc] = round(countries.get(loc, 0.0) + x["weight"], 1)
    return h, {"countries": dict(sorted(countries.items(), key=lambda kv: -kv[1]))}


def propose(ticker: str, model_key: str) -> dict:
    holdings, extra = holdings_with_countries(ticker)
    msgs = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": _user_prompt(ticker, holdings, extra)}]
    cfg = EVIDENCE_MODELS[model_key]
    model_id = cfg["model_id"] or ev._local_loaded_model(cfg["endpoint"])
    stats = {}
    content, mid = ev.hlive.chat(msgs, endpoint=cfg["endpoint"], model_id=model_id, max_tokens=4000,
                                 temperature=None, stream=False, stats=stats)
    out = ev.parse_verdict(content)
    viol = []
    instruments = out.get("instruments") if isinstance(out, dict) else None
    if not isinstance(instruments, list) or not instruments:
        viol.append("no_instruments")
        instruments = []
    clean = []
    for it in instruments[:4]:
        sym = str(it.get("symbol", "")).strip()
        try:
            w = float(it.get("weight"))
        except (TypeError, ValueError):
            viol.append(f"bad_weight:{sym}"); continue
        if sym not in UNIVERSE:
            viol.append(f"unknown_symbol:{sym}"); continue
        if sym == "^BVSP":
            viol.append("closed_overnight:^BVSP")
        clean.append({"symbol": sym, "weight": w, "role": it.get("role")})
    if len(instruments) > 4:
        viol.append("more_than_four")
    return {"model": mid, "output": out, "instruments": clean, "violations": viol, "usage": stats.get("usage"),
            "holdings_used": len(holdings)}


# ---------------- validation on data ----------------
SESSION = ":session"     # suffix of a cash index measured over its own session inside the night


def is_cash_index(sym: str) -> bool:
    return sym.startswith("^")


def _session_return(ser, t0: dt.datetime, t1: dt.datetime, closed_only: bool = False):
    """A cash index over its own session inside (t0, t1): first bar's open to last bar's close.
    The plain 4pm-to-9am measurement of a cash index runs from its PREVIOUS local close, so it also
    contains the index's reaction to the US session that ended at t0, which the fund's 4pm price
    already holds. The session return leaves that out. `closed_only` keeps only hourly bars that had
    closed by t1, for a value as it stood at a moment inside the session."""
    bars = [b for b in ser.between(t0, t1) if b.get("open") is not None]
    if closed_only:
        bars = [b for b in bars if b["ts"] + 3600 <= int(t1.timestamp())]
    if not bars or not bars[0]["open"]:
        return None
    return bars[-1]["close"] / bars[0]["open"] - 1.0


def _night_returns(ticker: str, symbols: list, nights: int) -> dict:
    """Per night: y (cum-dividend open over the 4pm close) and each instrument's 16:00->09:00 return;
    for a cash index also `<symbol>:session`, its return over its own session inside those hours.
    Same night construction, the same ex-dividend mornings and the same last-`nights` test split as the
    main build. The anchor here is the 4pm close for every fund (the question is which instruments
    explain the overnight move, and the close is available for all ten)."""
    daily = yahoo.daily(ticker)
    days = trading_days(daily)
    divs = fund_dividends(ticker)
    series = {}
    for s in symbols:
        try:
            ser = yahoo.hourly(s)
            if len(ser) > 100:
                series[s] = ser
        except Exception:  # noqa: BLE001
            pass
    rows = []
    for i in range(len(days) - 1):
        d, _, close_d = days[i]
        d1, open_d1, _ = days[i + 1]
        y = (open_d1 + (divs.get(d1.isoformat(), 0.0) or 0.0)) / close_d - 1.0
        base_t, end_t = at(d, 16, 0), at(d1, 9, 0)
        r = {}
        for s, ser in series.items():
            v, _ = _ret(ser, base_t, end_t, s)
            r[s] = v
            if is_cash_index(s):
                r[s + SESSION] = _session_return(ser, base_t, end_t)
        rows.append({"date": d.isoformat(), "next_date": d1.isoformat(), "y": y, "r": r})
    return {"rows": rows, "have": sorted(series), "missing": [s for s in symbols if s not in series],
            "test_from": rows[-nights]["date"] if len(rows) > nights else None,
            "test_to_morning": rows[-1]["next_date"] if rows else None}


def _oos(train: list, test: list, cols: list, fixed_weights: dict | None, require: list | None = None) -> dict:
    """Fit on train, score on test. cols = regressor symbols. fixed_weights -> single composite.
    `require` names further columns that must be present on a night for it to count, so two
    specifications can be scored on exactly the same nights."""
    def xrow(r):
        if fixed_weights:
            return [1.0, sum(fixed_weights[s] * r["r"][s] for s in cols)]
        return [1.0] + [r["r"][s] for s in cols]
    need = list(cols) + list(require or [])
    tr = [r for r in train if all(r["r"].get(s) is not None for s in need)]
    te = [r for r in test if all(r["r"].get(s) is not None for s in need)]
    if len(tr) < 60 or len(te) < 20:
        return {"error": f"insufficient data (train {len(tr)}, test {len(te)})"}
    f = ols([r["y"] for r in tr], [xrow(r) for r in tr])
    b = f["b"]
    pred = [sum(bi * xi for bi, xi in zip(b, xrow(r))) for r in te]
    y = [r["y"] for r in te]
    ybar = sum(y) / len(y)
    sse = sum((a - p) ** 2 for a, p in zip(y, pred)); sst = sum((a - ybar) ** 2 for a in y) or 1e-18
    mae = statistics.fmean(abs(a - p) for a, p in zip(y, pred)) * 1e4
    return {"r2_oos": stored(1 - sse / sst, 3), "mae_bps": stored(mae, 1), "r2_train": stored(f["r2"], 3),
            "n_train": len(tr), "n_test": len(te), "coef": {s: stored(c, 3) for s, c in zip(cols, b[1:])}}


def late_print_check(ticker: str, base_cols: list, all_cols: list, nights: int = 60) -> dict | None:
    """Do the fund's own late-night trades already hold what the added instruments say?

    For each test night with a traded print between 2am and 4am: x = that print's deviation from the
    published reference (hand-picked hedge only, 4pm-close anchor), and z = what the added instruments
    contribute by the print's own time, with coefficients fitted on the training nights only. A high
    correlation between x and z, and a smaller |x - z| than |x|, means the print was not far from value:
    the reference was missing something the market already knew. Needs the build's nights file with
    its prints; returns None without it."""
    from .grade import _same_instant, _corr
    pn = os.path.join(OUT, f"nights_{ticker}.json")
    extra = [c for c in all_cols if c not in base_cols]
    if not extra or not os.path.exists(pn):
        return None
    doc = read_json(pn)
    by_date = {r["date"]: r for r in doc["test"]}
    syms = sorted({c.replace(SESSION, "") for c in all_cols})
    data = _night_returns(ticker, syms, nights)
    train = [r for r in data["rows"][:-nights] if all(r["r"].get(c) is not None for c in all_cols)]
    if len(train) < 60:
        return {"error": f"insufficient training nights ({len(train)})"}
    f = ols([r["y"] for r in train], [[1.0] + [r["r"][c] for c in all_cols] for r in train])
    coef = dict(zip(all_cols, f["b"][1:]))
    series = {c: yahoo.hourly(c.replace(SESSION, "")) for c in extra}
    xs, zs = [], []
    for date, n in by_date.items():
        last = None
        for p in (n.get("prints") or []):
            if _same_instant(p) and int(p["t"][11:13]) in (2, 3):
                last = p
        if last is None:
            continue
        t_end = dt.datetime.fromisoformat(last["t"]) + dt.timedelta(minutes=5)
        base_t = at(dt.date.fromisoformat(date), 16, 0)
        z, ok = 0.0, True
        for c in extra:
            if c.endswith(SESSION):
                v = _session_return(series[c], base_t, t_end, closed_only=True)
            else:
                p1, _ = series[c].closed_asof(t_end, 3600)
                p0, _ = series[c].closed_asof(base_t, 3600)
                v = (p1 / p0 - 1.0) if (p0 and p1) else None
            if v is None:
                ok = False
                break
            z += coef[c] * v * 1e4
        if ok:
            xs.append(last["prem_close_bps"]); zs.append(z)
    if len(xs) < 10:
        return {"n_nights": len(xs), "note": "too few nights with a late print for a comparison"}
    res = [x - z for x, z in zip(xs, zs)]
    c = _corr(xs, zs)
    return {"n_nights": len(xs), "added_instruments": extra, "coef_added": {k: stored(coef[k], 3) for k in extra},
            "corr_print_deviation_vs_added": stored(c, 2) if c is not None else None,
            "median_abs_print_deviation_bps": stored(statistics.median(abs(x) for x in xs), 1),
            "median_abs_after_added_bps": stored(statistics.median(abs(x) for x in res), 1),
            "mean_print_deviation_bps": stored(statistics.fmean(xs), 1),
            "mean_after_added_bps": stored(statistics.fmean(res), 1),
            "definition": "last same-instant traded print 02:00-03:59 against the published close-anchored reference; "
                          "added = training-fitted coefficients times the added instruments' returns to the print's time"}


def evaluate(ticker: str, proposal: dict, nights: int = 60) -> dict:
    spec = FUNDS[ticker]
    base_syms = list(spec["hedges"]) + ([spec["fx"]] if spec.get("fx") else [])   # all, so the fallback is available
    prop_syms = [i["symbol"] for i in proposal["instruments"]]
    data = _night_returns(ticker, sorted(set(base_syms + prop_syms)), nights)
    rows = data["rows"]; train, test = rows[:-nights], rows[-nights:]
    # baseline: the first hedge WITH data (the build's fallback rule) plus the currency, signed as in config
    base_hedge = next((s for s in spec["hedges"] if s in data["have"]), None)
    base_cols = ([base_hedge] if base_hedge else []) + ([spec["fx"]] if spec.get("fx") and spec["fx"] in data["have"] else [])
    out = {"test_from": data["test_from"], "test_to_morning": data["test_to_morning"],
           "baseline_cols": base_cols, "baseline": _oos(train, test, base_cols, None) if base_cols else {"error": "no baseline data"}}
    usable = [i for i in proposal["instruments"] if i["symbol"] in data["have"]]
    out["proposal_cols"] = [i["symbol"] for i in usable]
    out["proposal_missing_data"] = [i["symbol"] for i in proposal["instruments"] if i["symbol"] not in data["have"]]
    if usable:
        cols = out["proposal_cols"]
        out["proposal_free"] = _oos(train, test, cols, None)
        out["proposal_fixed"] = _oos(train, test, cols, {i["symbol"]: i["weight"] for i in usable})
        # the union: the hand-picked hedge AND the model's instruments as separate regressors, so a
        # proposal that adds information to the baseline shows up even when it cannot replace it
        union_cols = base_cols + [c for c in cols if c not in base_cols]
        out["union_cols"] = union_cols
        out["union_free"] = _oos(train, test, union_cols, None) if len(union_cols) > len(base_cols) else {"note": "proposal adds nothing to the baseline set"}
        if any(is_cash_index(c) for c in cols):
            # the same proposal with each cash index measured over its own session inside the night
            # instead of from its previous local close, and the hand-picked hedge scored on exactly the
            # nights each version covers, so the comparison is like for like
            def sess(c):
                return c + SESSION if is_cash_index(c) else c
            scols = [sess(c) for c in cols]
            out["session_cols"] = scols
            out["proposal_session_free"] = _oos(train, test, scols, None)
            out["proposal_session_fixed"] = _oos(train, test, scols, {sess(i["symbol"]): i["weight"] for i in usable})
            out["union_session_cols"] = base_cols + [c for c in scols if c not in base_cols]
            out["union_session_free"] = _oos(train, test, out["union_session_cols"], None)
            if base_cols:
                out["baseline_same_nights"] = _oos(train, test, base_cols, None, require=cols)
                out["baseline_same_nights_session"] = _oos(train, test, base_cols, None, require=scols)
            # which measurement to use is decided on the TRAINING fit of the union, never on the test nights
            a, b = out["union_free"].get("r2_train"), out["union_session_free"].get("r2_train")
            if a is not None and b is not None:
                out["cash_index_measure_by_training_fit"] = "session" if b > a else "previous_close"
        chosen = out["union_session_cols"] if out.get("cash_index_measure_by_training_fit") == "session" else union_cols
        if len(chosen) > len(base_cols):
            try:
                lp = late_print_check(ticker, base_cols, chosen, nights)
            except Exception as ex:  # noqa: BLE001 - a diagnostic must not sink the evaluation
                lp = {"error": str(ex)[:160]}
            if lp:
                out["late_prints_vs_added_instruments"] = lp
    else:
        out["proposal_free"] = out["proposal_fixed"] = {"error": "no proposed instrument has data"}
    return out


def reevaluate(nights: int = 60, model_key: str = "sonnet") -> dict:
    """Recompute every saved proposal's scores with the current evaluator; no model calls."""
    p = os.path.join(OUT, "hedge_proposals.json")
    res = read_json(p)
    for t, by_model in res.items():
        x = by_model.get(model_key)
        if not x or "proposal" not in x:
            continue
        e = evaluate(t, x["proposal"], nights)
        x["evaluation"] = e
        b = e["baseline"].get("r2_oos"); fr = e["proposal_free"].get("r2_oos"); un = (e.get("union_free") or {}).get("r2_oos")
        line = f"[hedge] {t} {model_key}: baseline {e['baseline_cols']} R2 {b} | proposal {e['proposal_cols']} R2 {fr} | union R2 {un}"
        if "session_cols" in e:
            line += (f" | cash indices over their own session: proposal R2 {e['proposal_session_free'].get('r2_oos')}, "
                     f"union R2 {e['union_session_free'].get('r2_oos')}, baseline on the same nights "
                     f"{(e.get('baseline_same_nights_session') or {}).get('r2_oos')}; training fit prefers {e.get('cash_index_measure_by_training_fit')}")
        print(line, flush=True)
    write_json(p, res)
    return res


def run(tickers: list, model_keys: list, nights: int = 60) -> dict:
    results = {}
    for t in tickers:
        results[t] = {}
        for mk in model_keys:
            try:
                p = propose(t, mk)
                e = evaluate(t, p, nights)
                results[t][mk] = {"proposal": p, "evaluation": e}
                b = e["baseline"].get("r2_oos"); fr = e["proposal_free"].get("r2_oos"); fx = e["proposal_fixed"].get("r2_oos")
                print(f"[hedge] {t} {mk}: proposed {[(i['symbol'], i['weight']) for i in p['instruments']]} "
                      f"| OOS R2 baseline {b} -> free {fr}, fixed {fx} | violations {p['violations']}"
                      + (f" | no data: {e['proposal_missing_data']}" if e['proposal_missing_data'] else ""), flush=True)
            except Exception as ex:  # noqa: BLE001
                results[t][mk] = {"error": str(ex)[:300]}
                print(f"[hedge] {t} {mk}: FAILED {str(ex)[:160]}", flush=True)
    write_json(os.path.join(OUT, "hedge_proposals.json"), results)
    return results

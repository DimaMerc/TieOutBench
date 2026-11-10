"""AlphaVantage: ETF holdings (ETF_PROFILE), timestamped news (NEWS_SENTIMENT), 1-minute extended-hours
bars (TIME_SERIES_INTRADAY, month by month). Needs ALPHAVANTAGE_API_KEY (premium for volume).

News: the `tickers` parameter is AND-matched, so we query one ticker at a time over a window and
slice locally by `time_published`. A week per call keeps a mega-cap under the 1,000-item cap.
"""
from __future__ import annotations
import datetime as dt
import hashlib
import os
import time
import urllib.parse

from .util import cached_json, http_json, TZ_ET, UTC

BASE = "https://www.alphavantage.co/query?"


def key() -> str | None:
    return os.environ.get("ALPHAVANTAGE_API_KEY") or os.environ.get("ALPHA_VANTAGE_API_KEY")


def available() -> bool:
    return bool(key())


def _get(params: dict, cache_key: str, refresh: bool = False, ttl_hours: float | None = None):
    params = dict(params, apikey=key())
    url = BASE + urllib.parse.urlencode(params)

    def fetch():
        for attempt in range(6):
            j = http_json(url, timeout=60, pause=1.0)
            if isinstance(j, dict) and ("Note" in j or "Information" in j) and len(j) == 1:
                msg = list(j.values())[0]
                if attempt < 5:            # per-minute throttle: wait and retry, never cache the notice
                    time.sleep(15 * (attempt + 1))
                    continue
                raise RuntimeError(f"alphavantage throttled/denied: {msg[:160]}")
            return j
    return cached_json(cache_key, fetch, refresh=refresh, ttl_hours=ttl_hours)


def etf_profile(ticker: str, refresh: bool = False) -> dict:
    """Holdings with weights, sectors, net assets. Cached for a week."""
    if not available():
        return {}
    return _get({"function": "ETF_PROFILE", "symbol": ticker}, f"av_etf_profile_{ticker}",
                refresh=refresh, ttl_hours=24 * 7)


def top_holdings(ticker: str, n: int = 10) -> list:
    prof = etf_profile(ticker)
    rows = prof.get("holdings") or []
    out = []
    for r in rows:
        sym = (r.get("symbol") or "").strip()
        try:
            w = float(r.get("weight") or 0)
        except ValueError:
            w = 0.0
        if sym and sym not in ("n/a", "-"):
            out.append({"symbol": sym, "name": r.get("description") or "", "weight": w})
    # the API reports weights as fractions of the fund (0.2063 = 20.63%); normalise to percent so a
    # reader of the prompt sees "NVDA (20.6%)" and not "NVDA (0.2%)"
    if out and max(x["weight"] for x in out) <= 1.0 and sum(x["weight"] for x in out) <= 1.05:
        for x in out:
            x["weight"] *= 100.0
    out.sort(key=lambda x: -x["weight"])
    return out[:n]


def _fmt(t: dt.datetime) -> str:
    return t.astimezone(UTC).strftime("%Y%m%dT%H%M")


def news(ticker: str, t_from: dt.datetime, t_to: dt.datetime, refresh: bool = False) -> list:
    """All articles mentioning `ticker` published in [t_from, t_to), fetched in weekly chunks.
    Each item: {id, time (ISO ET), source, title, summary, url, tickers}."""
    if not available():
        return []
    items, cur = [], t_from
    while cur < t_to:
        nxt = min(cur + dt.timedelta(days=7), t_to)
        ck = f"av_news_{ticker}_{_fmt(cur)}_{_fmt(nxt)}"
        j = _get({"function": "NEWS_SENTIMENT", "tickers": ticker, "time_from": _fmt(cur),
                  "time_to": _fmt(nxt), "sort": "EARLIEST", "limit": 1000}, ck, refresh=refresh)
        for a in (j.get("feed") or []):
            tp = a.get("time_published")  # YYYYMMDDTHHMMSS in UTC
            try:
                t = dt.datetime.strptime(tp, "%Y%m%dT%H%M%S").replace(tzinfo=UTC).astimezone(TZ_ET)
            except (TypeError, ValueError):
                continue
            items.append({"id": "n" + hashlib.sha1((a.get("url") or a.get("title") or tp).encode("utf-8")).hexdigest()[:8],
                          "time": t.isoformat(timespec="minutes"), "source": a.get("source"),
                          "title": a.get("title"), "summary": (a.get("summary") or "")[:600],
                          "url": a.get("url"),
                          "tickers": [x.get("ticker") for x in (a.get("ticker_sentiment") or [])]})
        cur = nxt
    items.sort(key=lambda x: x["time"])
    return items


def intraday_month(ticker: str, month: str, interval: str = "1min", refresh: bool = False) -> list:
    """Extended-hours (4am-8pm ET) bars for one month, as [{ts, open, high, low, close, volume}]."""
    if not available():
        return []
    j = _get({"function": "TIME_SERIES_INTRADAY", "symbol": ticker, "interval": interval,
              "month": month, "outputsize": "full", "extended_hours": "true", "adjusted": "false"},
             f"av_intraday_{ticker}_{month}_{interval}", refresh=refresh)
    series = None
    for k, v in j.items():
        if k.startswith("Time Series"):
            series = v
    if not series:
        return []
    out = []
    for stamp, row in series.items():
        t = dt.datetime.strptime(stamp, "%Y-%m-%d %H:%M:%S").replace(tzinfo=TZ_ET)
        out.append({"ts": int(t.timestamp()), "open": float(row["1. open"]), "high": float(row["2. high"]),
                    "low": float(row["3. low"]), "close": float(row["4. close"]), "volume": float(row["5. volume"])})
    out.sort(key=lambda b: b["ts"])
    return out

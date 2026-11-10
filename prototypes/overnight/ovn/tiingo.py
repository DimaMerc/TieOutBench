"""Tiingo Blue Ocean ATS (BOATS) overnight tape. Needs TIINGO_API_KEY and the BOATS entitlement.

Endpoint: https://api.tiingo.com/boats/<ticker>/prices?startDate=YYYY-MM-DD&endDate=YYYY-MM-DD
          &resampleFreq=5min&columns=open,high,low,close,volume
Bars cover the overnight session only (8:00pm to 3:59am ET). Historical depth unknown at the time
of writing (the product entered beta on 2026-07-21); the fetcher records what it gets.
"""
from __future__ import annotations
import datetime as dt
import os
import urllib.parse

from .util import cached_json, http_json, Series, TZ_ET


def key() -> str | None:
    return os.environ.get("TIINGO_API_KEY")


def available() -> bool:
    return bool(key())


def probe() -> dict:
    """Three facts, no caching: does the token work at all, does the account have the BOATS
    entitlement, and how many bars did the latest overnight session return for SPY."""
    out = {"key_present": available(), "token_ok": None, "boats_ok": None, "boats_bars_latest_session": None, "error": None}
    if not available():
        return out
    hdr = {"Authorization": f"Token {key()}"}
    try:
        j = http_json("https://api.tiingo.com/api/test", headers=hdr, retries=1)
        out["token_ok"] = bool(j)
    except Exception as e:  # noqa: BLE001
        out["token_ok"] = False
        out["error"] = f"test endpoint: {str(e)[:160]}"
        return out
    try:
        rows = http_json("https://api.tiingo.com/boats/SPY/prices?resampleFreq=5min&columns=open,high,low,close,volume",
                         headers=hdr, retries=1)
        out["boats_ok"] = True
        out["boats_bars_latest_session"] = len(rows) if isinstance(rows, list) else 0
    except Exception as e:  # noqa: BLE001
        out["boats_ok"] = False
        out["error"] = f"boats endpoint: {str(e)[:200]}"
    return out


def _parse(rows: list) -> list:
    out = []
    for r in rows or []:
        d = r.get("date")
        if not d or r.get("close") is None:
            continue
        # Tiingo returns ISO timestamps with offset; normalise to unix seconds.
        t = dt.datetime.fromisoformat(d.replace("Z", "+00:00"))
        out.append({"ts": int(t.timestamp()), "open": r.get("open"), "high": r.get("high"),
                    "low": r.get("low"), "close": float(r["close"]), "volume": r.get("volume")})
    return out


def overnight_bars(ticker: str, start: dt.date, end: dt.date, freq: str = "5min", refresh: bool = False) -> Series:
    if not available():
        return Series(ticker, [])
    k = f"tiingo_boats_{ticker}_{start}_{end}_{freq}"
    url = (f"https://api.tiingo.com/boats/{urllib.parse.quote(ticker)}/prices?"
           f"startDate={start}&endDate={end}&resampleFreq={freq}&columns=open,high,low,close,volume")

    def fetch():
        return _parse(http_json(url, headers={"Authorization": f"Token {key()}"}))
    return Series(ticker, cached_json(k, fetch, refresh=refresh))

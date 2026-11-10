"""Yahoo chart endpoint (no key, no library). Used for: fund daily bars (open/close), fund 15-minute
bars with pre/post prints (60 days), hourly futures / FX / index bars (two years).

Bars come back as {"ts": unix_seconds_of_bar_start, "open","high","low","close","volume"}.
Yahoo stamps a bar at its START. An hourly futures bar stamped 20:00 ET covers 20:00-21:00 and its
close is the 21:00 price; Series.asof() relies on that.
"""
from __future__ import annotations
import datetime as dt
import urllib.parse

from .util import cached_json, http_json, Series, snapshot_day, snapshot_is_frozen

BASE = "https://query1.finance.yahoo.com/v8/finance/chart/"


def _parse(j: dict) -> list:
    res = (j.get("chart") or {}).get("result") or []
    if not res:
        err = (j.get("chart") or {}).get("error")
        raise RuntimeError(f"yahoo: no result ({err})")
    r = res[0]
    ts = r.get("timestamp") or []
    q = (r.get("indicators") or {}).get("quote") or [{}]
    q = q[0] if q else {}
    out = []
    for i, t in enumerate(ts):
        def g(k):
            v = (q.get(k) or [None] * len(ts))[i]
            return None if v is None else float(v)
        c = g("close")
        if c is None:
            continue
        out.append({"ts": int(t), "open": g("open"), "high": g("high"), "low": g("low"),
                    "close": c, "volume": g("volume")})
    return out


def chart(symbol: str, rng: str, interval: str, prepost: bool = False, refresh: bool = False) -> list:
    """Cached per (symbol, range, interval, prepost, snapshot day). The snapshot day is today unless
    the run is pinned to an earlier one (util.set_pins), in which case nothing is fetched."""
    day = snapshot_day()
    key = f"yahoo_{symbol}_{rng}_{interval}_{'pp' if prepost else 'reg'}_{day}"
    url = (BASE + urllib.parse.quote(symbol) +
           f"?range={rng}&interval={interval}&includePrePost={'true' if prepost else 'false'}")

    def fetch():
        return _parse(http_json(url))
    return cached_json(key, fetch, refresh=refresh and not snapshot_is_frozen(), frozen=snapshot_is_frozen())


def daily(symbol: str, years: int = 2, refresh: bool = False) -> Series:
    return Series(symbol, chart(symbol, f"{years}y", "1d", prepost=False, refresh=refresh))


def hourly(symbol: str, days: int = 730, refresh: bool = False) -> Series:
    return Series(symbol, chart(symbol, f"{days}d", "1h", prepost=True, refresh=refresh))


def quarter_hour_prepost(symbol: str, refresh: bool = False) -> Series:
    """15-minute bars incl. pre/post market; Yahoo serves at most 60 calendar days of these."""
    return Series(symbol, chart(symbol, "60d", "15m", prepost=True, refresh=refresh))


def five_minute(symbol: str, refresh: bool = False) -> Series:
    """5-minute bars incl. pre/post market, the finest history the feed serves for about sixty trading
    days. Used to pair each 5-minute overnight print with the futures bar of the same five minutes."""
    return Series(symbol, chart(symbol, "60d", "5m", prepost=True, refresh=refresh))


def dividends(symbol: str, years: int = 2, refresh: bool = False) -> dict:
    """{ex_date_iso: cash amount per share} from the chart feed's dividend events."""
    day = snapshot_day()
    refresh = refresh and not snapshot_is_frozen()
    key = f"yahoo_div_{symbol}_{years}y_{day}"
    url = BASE + urllib.parse.quote(symbol) + f"?range={years}y&interval=1d&events=div"

    def fetch():
        j = http_json(url)
        res = (j.get("chart") or {}).get("result") or []
        ev = ((res[0].get("events") or {}).get("dividends") or {}) if res else {}
        out = {}
        for v in ev.values():
            d = dt.datetime.fromtimestamp(int(v["date"]), dt.timezone.utc).astimezone(
                __import__("zoneinfo").ZoneInfo("America/New_York")).date().isoformat()
            out[d] = float(v["amount"])
        return out
    return cached_json(key, fetch, refresh=refresh, frozen=snapshot_is_frozen())


def try_hourly(symbols: list, days: int = 730, refresh: bool = False):
    """First symbol with usable data -> (Series, symbol, fallback_used: bool). None if all fail."""
    for i, s in enumerate(symbols):
        try:
            ser = hourly(s, days=days, refresh=refresh)
            if len(ser) > 100:
                return ser, s, i > 0
        except Exception as e:  # noqa: BLE001 - a missing symbol is a data fact, not a crash
            print(f"[yahoo] {s}: no hourly data ({str(e)[:80]})")
    return None, None, False

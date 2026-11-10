"""Time, cache and HTTP helpers. Standard library only."""
from __future__ import annotations
import bisect
import datetime as dt
import hashlib
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo

from .config import ET

TZ_ET = ZoneInfo(ET)
UTC = dt.timezone.utc

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(HERE, "data")
CACHE = os.path.join(DATA, "cache")
OUT = os.path.join(DATA, "out")
NAV_DIR = os.path.join(DATA, "nav")
HOLD_DIR = os.path.join(DATA, "holdings")
for _d in (CACHE, OUT, NAV_DIR, HOLD_DIR):
    os.makedirs(_d, exist_ok=True)

UA = "TieOutBench overnight prototype (research; standard library urllib)"

# ---------------- pins: which snapshot of the feeds, and where the window ends ----------------
# The public chart feed serves a rolling window (about sixty trading days of intraday bars), so the
# same command gives a different answer on a different day. Two pins make a run repeatable:
#   snapshot day  the calendar day whose cached downloads are read (default: today, which fetches).
#                 With an earlier day nothing is fetched from the chart feed: a missing file is an error.
#   window end    the last morning in the test window (default: the latest the data holds).
_PINS = {"snapshot": os.environ.get("OVN_ASOF") or None, "end": os.environ.get("OVN_END") or None}


def set_pins(snapshot: str | None = None, end: str | None = None) -> None:
    for k, v in (("snapshot", snapshot), ("end", end)):
        if v:
            dt.date.fromisoformat(v)          # raises on a malformed date
            _PINS[k] = v


def snapshot_day() -> str:
    return _PINS["snapshot"] or dt.date.today().isoformat()


def snapshot_is_frozen() -> bool:
    return snapshot_day() != dt.date.today().isoformat()


def window_end() -> dt.date | None:
    return dt.date.fromisoformat(_PINS["end"]) if _PINS["end"] else None


def load_repo_env():
    """Fill os.environ from the repo-root .env (KEY=VALUE lines) without overriding real variables.
    Same convention as harness/live.py; the file is gitignored and never read back out by this code."""
    root = os.path.dirname(os.path.dirname(HERE))
    p = os.path.join(root, ".env")
    try:
        with open(p, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k, v = k.strip(), v.strip().strip('"').strip("'")
                if k and v and k not in os.environ:
                    os.environ[k] = v
    except OSError:
        pass


load_repo_env()


# ---------------- time ----------------
def et(y, m, d, hh=0, mm=0):
    return dt.datetime(y, m, d, hh, mm, tzinfo=TZ_ET)


def et_from_ts(ts: int) -> dt.datetime:
    return dt.datetime.fromtimestamp(ts, UTC).astimezone(TZ_ET)


def at(date: dt.date, hh: int, mm: int = 0) -> dt.datetime:
    return dt.datetime(date.year, date.month, date.day, hh, mm, tzinfo=TZ_ET)


def iso(d: dt.datetime) -> str:
    return d.isoformat(timespec="minutes")


# ---------------- series ----------------
class Series:
    """Bars sorted by start time. `asof(t)` returns the close of the last bar that STARTED before t,
    which for hourly bars is the price at t (the bar covering t-1h..t). Staleness is the caller's
    business: `asof` also returns the bar's start so the caller can reject an old print."""

    def __init__(self, symbol: str, bars: list):
        self.symbol = symbol
        self.bars = sorted((b for b in bars if b.get("close") is not None), key=lambda b: b["ts"])
        self._ts = [b["ts"] for b in self.bars]

    def __len__(self):
        return len(self.bars)

    def asof(self, t: dt.datetime):
        """-> (close, bar_start_datetime) or (None, None)."""
        ts = int(t.timestamp())
        i = bisect.bisect_left(self._ts, ts)  # first bar with start >= t
        if i == 0:
            return None, None
        b = self.bars[i - 1]
        return b["close"], et_from_ts(b["ts"])

    def closed_asof(self, t: dt.datetime, width_s: int):
        """-> (close, bar_end_datetime) of the last bar that had ENDED by t, for bars `width_s` seconds
        long; (None, None) if there is none. Unlike `asof`, this never returns a bar that is still
        open at t, so it is safe at times that are not on the series' own grid: a 5-minute print
        ending 01:05 paired with `asof` on hourly bars would get the 02:00 price."""
        ts = int(t.timestamp()) - width_s
        i = bisect.bisect_right(self._ts, ts)  # bars with start <= t - width
        if i == 0:
            return None, None
        b = self.bars[i - 1]
        return b["close"], et_from_ts(b["ts"] + width_s)

    def between(self, t0: dt.datetime, t1: dt.datetime) -> list:
        a = bisect.bisect_left(self._ts, int(t0.timestamp()))
        z = bisect.bisect_left(self._ts, int(t1.timestamp()))
        return self.bars[a:z]

    def last_before(self, t: dt.datetime, after: dt.datetime | None = None):
        """Last bar starting before t and (optionally) at or after `after`."""
        c, start = self.asof(t)
        if c is None or (after is not None and start < after):
            return None, None
        return c, start


# ---------------- cache + http ----------------
def _cache_path(key: str) -> str:
    h = hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]
    safe = "".join(ch if ch.isalnum() or ch in "-_.=" else "_" for ch in key)[:80]
    return os.path.join(CACHE, f"{safe}__{h}.json")


def cached_json(key: str, fetch, *, refresh: bool = False, ttl_hours: float | None = None,
                frozen: bool = False):
    """Return the cached JSON for `key`, or call fetch() and store it. `ttl_hours=None` caches
    forever (historical data); a finite ttl re-fetches when the file is older than that.
    `frozen=True` (a run pinned to an earlier snapshot day) never fetches: the file must exist."""
    p = _cache_path(key)
    if frozen:
        if not os.path.exists(p):
            raise RuntimeError(f"no cached download for '{key}': the run is pinned to an earlier snapshot day "
                               f"and that day's file is not in data/cache")
        with open(p, encoding="utf-8") as fh:
            return json.load(fh)
    if not refresh and os.path.exists(p):
        if ttl_hours is None or (time.time() - os.path.getmtime(p)) < ttl_hours * 3600:
            with open(p, encoding="utf-8") as fh:
                return json.load(fh)
    data = fetch()
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(data, fh)
    return data


def http_json(url: str, headers: dict | None = None, timeout: int = 30, retries: int = 3, pause: float = 0.6):
    h = {"User-Agent": UA, "Accept": "application/json"}
    if headers:
        h.update(headers)
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=h)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                body = r.read().decode("utf-8")
            time.sleep(pause)
            return json.loads(body)
        except urllib.error.HTTPError as e:
            last = e
            if e.code in (429, 500, 502, 503, 504):
                time.sleep(2.0 * (attempt + 1))
                continue
            raise
        except (urllib.error.URLError, TimeoutError) as e:
            last = e
            time.sleep(2.0 * (attempt + 1))
    raise RuntimeError(f"http_json failed after {retries} attempts: {url[:120]} :: {last!r}")


def write_json(path: str, obj) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=1, default=str)


def read_json(path: str):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)

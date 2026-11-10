"""Evidence layer, flag-only design: a language model reads the night's news for the fund's holdings
and either raises a flag with citations and an expected direction, or says nothing material happened.
It never proposes a number; any adjustment is learned from data afterward.

Runs through harness/live.py's provider-neutral OpenAI-compatible client, so one prompt can be
scored on Claude, GPT and Gemini. Needs an AlphaVantage key (news) and the model key.

Holdings come from data/holdings/<TICKER>.json when present (issuer file converted by ovn/holdings.py),
else from AlphaVantage's ETF profile. Each holding may carry a `news_ticker` (a US listing or ADR) used
for the news lookup; holdings without one appear in the prompt but fetch no news.

The output is validated hard: every cited id must exist in the input list; a flag must carry at least
one citation; a non-flag must carry direction "none". A record that fails validation is kept and
marked, never silently repaired.
"""
from __future__ import annotations
import datetime as dt
import hashlib
import os
import sys

from .config import FUNDS, EVIDENCE_MODELS, EVIDENCE_TOP_HOLDINGS
from .util import OUT, HOLD_DIR, read_json, write_json, TZ_ET
from . import alphavantage as av

# make the repo's harness importable (prototypes/overnight -> repo root)
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
try:
    from harness import live as hlive  # noqa: E402
    _HARNESS_ERR = None
except Exception as _e:  # noqa: BLE001
    hlive = None
    _HARNESS_ERR = str(_e)

SYSTEM = """You are the overnight evidence reader for an ETF reference value.

You are given: the fund, its largest holdings with their weights, the hedge-implied reference value at
this hour, and the news items published since 4pm New York time that mention those holdings. Decide
whether anything in the news should move the fund's basket value BEYOND what the hedge instruments
(index, bond, gold or bitcoin futures and currencies) already imply.

Rules:
- Most nights the right answer is "no flag". Say so when it is true. You are rewarded for restraint, not
  for finding something.
- Only fund-specific information counts: a result, guidance, deal, recall, regulatory action or corporate
  action at a holding large enough to matter at its weight, or an event in the fund's home market that
  index futures would not reflect. Broad macro news and index-level moves are already in the futures.
- A move that happened BEFORE 4pm is already in the 4pm value. A move after 4pm that index futures would
  also show is already in the hedge. Flag only what is fund-specific and after 4pm.
- If you flag, cite the item ids you relied on. Never cite an id that is not in the list.
- Do NOT estimate a size. State only the expected direction of the fund's move beyond the hedge.
- Reply with ONE JSON object and nothing else:
  {"flag": true|false, "direction": "up"|"down"|"unclear"|"none",
   "confidence": "low"|"medium"|"high", "cited_ids": ["..."], "reason": "<at most 30 words>"}
  With flag false, direction must be "none" and cited_ids may be empty.
"""


def holdings_for(ticker: str, n: int = EVIDENCE_TOP_HOLDINGS) -> list:
    """Issuer file first (data/holdings/<TICKER>.json), else AlphaVantage ETF_PROFILE."""
    p = os.path.join(HOLD_DIR, f"{ticker}.json")
    if os.path.exists(p):
        rows = read_json(p)
        rows = rows.get("holdings", rows) if isinstance(rows, dict) else rows
        return rows[:n]
    h = av.top_holdings(ticker, n) if av.available() else []
    for x in h:
        x.setdefault("news_ticker", x["symbol"])
    return h


def news_for_night(holdings: list, t_from: dt.datetime, t_to: dt.datetime) -> list:
    seen, items = set(), []
    for h in holdings:
        nt = h.get("news_ticker") or ""
        if not nt:
            continue
        for it in av.news(nt, t_from, t_to):
            k = it["url"] or it["title"]
            if k in seen:
                continue
            seen.add(k)
            items.append(dict(it, holding=h["symbol"]))
    items.sort(key=lambda x: x["time"])
    return items


def build_messages(ticker: str, hour_iso: str, ref: float, holdings: list, items: list) -> list:
    hold = "; ".join(f"{h.get('name') or h['symbol']} [{h['symbol']}] {h['weight']:.1f}%" for h in holdings) or "not available"
    lines = [f"[{it['id']}] {it['time']} {it['source']} | {it['holding']} | {it['title']} :: {it['summary'][:300]}"
             for it in items]
    user = (f"Fund: {ticker} ({FUNDS[ticker]['name']}). Hour: {hour_iso} New York time.\n"
            f"Largest holdings (weight % of fund): {hold}.\n"
            f"Hedge-implied reference value at this hour: {ref:.2f} per share.\n"
            f"News items since 4pm ({len(items)}):\n" + ("\n".join(lines) if lines else "(none)"))
    return [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]


def validate(out: dict, item_ids: set) -> list:
    """Return the list of violations (empty = clean)."""
    v = []
    if not isinstance(out, dict):
        return ["not_an_object"]
    flag = out.get("flag")
    if not isinstance(flag, bool):
        v.append("flag_not_bool")
    direction = out.get("direction")
    if direction not in ("up", "down", "unclear", "none"):
        v.append("direction_invalid")
    if flag is False and direction not in ("none", None):
        v.append("direction_without_flag")
    if flag is True and direction == "none":
        v.append("flag_without_direction")
    cited = out.get("cited_ids") or []
    if not isinstance(cited, list):
        v.append("cited_ids_not_list"); cited = []
    bad = [c for c in cited if c not in item_ids]
    if bad:
        v.append("cited_unknown_ids:" + ",".join(map(str, bad))[:80])
    if flag is True and not cited:
        v.append("flag_without_citation")
    if out.get("confidence") not in ("low", "medium", "high"):
        v.append("confidence_invalid")
    if len(str(out.get("reason", "")).split()) > 40:
        v.append("reason_too_long")
    return v


def parse_verdict(content: str) -> dict:
    """Tolerant parse of the model's reply: strip code fences and bold markers, take the first JSON
    object, fall back to the harness's salvage routine; never raise. Unparseable -> {"_raw": ...}."""
    import json as _json
    import re as _re
    s = (content or "").strip()
    s = _re.sub(r"^```(?:json)?\s*|\s*```$", "", s, flags=_re.IGNORECASE | _re.MULTILINE).strip()
    s = s.strip("*").strip()
    for cand in (s, s[s.find("{"): s.rfind("}") + 1] if "{" in s and "}" in s else ""):
        if not cand:
            continue
        try:
            o = _json.loads(cand)
            if isinstance(o, dict):
                return o
        except ValueError:
            pass
    try:
        o = hlive.salvage_json(content)
        if isinstance(o, dict) and o:
            return o
    except Exception:  # noqa: BLE001
        pass
    return {"_raw": (content or "")[:500]}


def _local_loaded_model(endpoint: str) -> str | None:
    """LM Studio: the id of the loaded chat model (state == loaded, type == llm), via its v0 API.
    None if the server is not LM Studio or nothing is loaded; the harness then picks the first id."""
    import json as _json
    import urllib.request as _ur
    base = endpoint.rsplit("/v1", 1)[0]
    try:
        with _ur.urlopen(base + "/api/v0/models", timeout=5) as r:
            rows = _json.loads(r.read()).get("data", [])
        for m in rows:
            if m.get("state") == "loaded" and m.get("type") == "llm":
                return m.get("id")
    except Exception:  # noqa: BLE001
        return None
    return None


def _chat_with_extra(msgs: list, cfg: dict, model_id: str, stats: dict, timeout: int = 900):
    """Direct OpenAI-compatible POST for endpoints that need extra request fields the harness client does
    not pass (LM Studio's reasoning_effort). Non-streaming; fills stats like the harness does."""
    import json as _json
    import time as _time
    import urllib.request as _ur
    payload = {"model": model_id, "messages": msgs, "max_tokens": 8000, "stream": False}
    payload.update(cfg.get("extra") or {})
    req = _ur.Request(cfg["endpoint"].rstrip("/") + "/chat/completions", data=_json.dumps(payload).encode("utf-8"),
                      headers={"Content-Type": "application/json"})
    t0 = _time.monotonic()
    with _ur.urlopen(req, timeout=timeout) as r:
        resp = _json.loads(r.read().decode("utf-8"))
    choice = (resp.get("choices") or [{}])[0]
    msg = choice.get("message") or {}
    content = msg.get("content") or ""
    stats.update({"finish_reason": choice.get("finish_reason"), "usage": resp.get("usage"),
                  "content_chars": len(content), "elapsed_s": round(_time.monotonic() - t0, 1),
                  "model_id": resp.get("model") or model_id, "extra": cfg.get("extra")})
    return content, resp.get("model") or model_id


def run_night(ticker: str, rec: dict, hour: int, model_key: str, holdings: list, items: list) -> dict:
    g = next((x for x in rec["grid"] if x["hour"] == hour), None)
    if g is None or g.get("ref") is None:
        return {"skipped": "no_reference_at_hour"}
    t_hour = dt.datetime.fromisoformat(g["t"])
    t_from = dt.datetime.fromisoformat(rec["date"] + "T16:00").replace(tzinfo=TZ_ET)
    window = [it for it in items if t_from <= dt.datetime.fromisoformat(it["time"]) < t_hour]
    msgs = build_messages(ticker, g["t"], g["ref"], holdings, window)
    cfg = EVIDENCE_MODELS[model_key]
    model_id = cfg["model_id"]
    if model_id is None:
        model_id = _local_loaded_model(cfg["endpoint"])
    stats = {}
    # The answer is ~100 tokens, but these models think before answering and the compat endpoint counts
    # the thinking against max_tokens: at 2000 about one call in ten came back cut off (finish=length,
    # empty or partial JSON). 8000 leaves room; the harness still warns on any cut.
    # a local model on a laptop card needs minutes, not seconds, for a 12k-token prompt plus thinking
    is_local = "localhost" in cfg["endpoint"] or "127.0.0.1" in cfg["endpoint"]
    if cfg.get("extra"):
        content, mid = _chat_with_extra(msgs, cfg, model_id, stats)
    else:
        content, mid = hlive.chat(msgs, endpoint=cfg["endpoint"], model_id=model_id,
                                  max_tokens=8000, temperature=None, stream=False, stats=stats,
                                  timeout=900 if is_local else 90, deadline=1200 if is_local else 240)
    out = parse_verdict(content)
    viol = validate(out, {it["id"] for it in window})
    return {"model": mid, "hour": hour, "n_items": len(window), "output": out, "violations": viol,
            "usage": stats.get("usage"), "finish_reason": stats.get("finish_reason"),
            "prompt_chars": sum(len(m["content"]) for m in msgs)}


def _needs_repair(run: dict) -> bool:
    """A run that errored, was cut off by the output cap, or produced no parseable verdict."""
    if "error" in run:
        return True
    if "skipped" in run:
        return False
    return run.get("finish_reason") == "length" or "flag_not_bool" in (run.get("violations") or [])


def _in_subset(ticker: str, date: str, hour: int, runs: dict, subset_from: str, sample: float) -> bool:
    """Second-stage selection: the first model flagged this run, or it falls in a deterministic sample
    of the rest (hash of fund+date+hour, so the sample is the same on every machine and every run)."""
    base = runs.get(f"{subset_from}@{hour}") or {}
    if (base.get("output") or {}).get("flag") is True:
        return True
    h = int(hashlib.sha1(f"{ticker}|{date}|{hour}".encode("utf-8")).hexdigest()[:8], 16) % 1000
    return h < int(sample * 1000)


def run_all(tickers: list, model_keys: list, hours: list, limit_nights: int | None = None,
            repair: bool = False, subset_from: str | None = None, sample: float = 0.1) -> dict:
    """repair=True re-runs only the runs that errored or were truncated in an existing evidence file,
    keeping every other verdict byte for byte. subset_from='haiku' runs the given models only where the
    first model flagged, plus a deterministic `sample` share of the other runs, into the same file."""
    if hlive is None:
        raise RuntimeError(f"harness.live not importable: {_HARNESS_ERR}")
    if not av.available():
        raise RuntimeError("AlphaVantage key not set: the evidence layer needs news")
    # one writer at a time: a second evidence run started while one is going (for example from another
    # terminal) would rewrite the same files and lose verdicts, which happened once on 2026-11-08
    lock = os.path.join(OUT, "evidence.lock")
    if os.path.exists(lock):
        age_min = (dt.datetime.now().timestamp() - os.path.getmtime(lock)) / 60
        if age_min < 180:
            raise RuntimeError(f"another evidence run appears to be active (lock {lock}, {age_min:.0f} min old). "
                               f"Wait for it, or delete the lock file if you are sure it is not running.")
    with open(lock, "w", encoding="utf-8") as fh:
        fh.write(f"pid {os.getpid()} started {dt.datetime.now().isoformat(timespec='seconds')} models {model_keys} funds {tickers}\n")
    try:
        return _run_all_locked(tickers, model_keys, hours, limit_nights, repair, subset_from, sample)
    finally:
        try:
            os.remove(lock)
        except OSError:
            pass


def _run_all_locked(tickers, model_keys, hours, limit_nights, repair, subset_from, sample) -> dict:
    results = {}
    for t in tickers:
        p = os.path.join(OUT, f"nights_{t}.json")
        if not os.path.exists(p):
            print(f"[evidence] {t}: no build output"); continue
        doc = read_json(p)
        holdings = holdings_for(t)
        if not holdings:
            print(f"[evidence] {t}: no holdings available; skipped"); continue
        test = doc["test"][-limit_nights:] if limit_nights else doc["test"]
        t_from = dt.datetime.fromisoformat(test[0]["date"] + "T16:00").replace(tzinfo=TZ_ET)
        t_to = dt.datetime.fromisoformat(test[-1]["next_date"] + "T09:30").replace(tzinfo=TZ_ET)
        items = news_for_night(holdings, t_from, t_to)
        print(f"[evidence] {t}: {len(items)} news items for {len(holdings)} holdings over {len(test)} nights", flush=True)

        pe = os.path.join(OUT, f"evidence_{t}.json")

        def load_prev():
            """Rows and metadata as they are on disk right now; empty if there is no file yet."""
            if not os.path.exists(pe):
                return {}, {}
            prev = read_json(pe)
            rows = {n["date"]: n for n in prev["nights"]}
            meta = {k: v for k, v in prev.items() if k not in ("nights", "holdings", "partial")}
            return rows, meta

        # never drop verdicts that exist on disk: a run over a subset of nights or models merges into
        # the file, it does not replace it
        prev_rows, prev_meta = load_prev()
        prev_meta["news_items"] = len(items)          # how much the feed carried for these holdings
        existing = {d: n["runs"] for d, n in prev_rows.items()}

        def merged(rows_done):
            """Re-read the file before every write, so a verdict written by anyone else since this run
            started is kept too (two writers must still not overlap: see the lock in run_all)."""
            disk_rows, _ = load_prev()
            m = dict(disk_rows)
            for row in rows_done:
                base = dict(m.get(row["date"], {}).get("runs", {}))
                base.update(row["runs"])
                m[row["date"]] = {"date": row["date"], "runs": base}
            return [m[d] for d in sorted(m)]
        per, redone, selected = [], 0, 0
        for i, rec in enumerate(test):
            row = {"date": rec["date"], "runs": dict(existing.get(rec["date"], {}))}
            for mk in model_keys:
                for h in hours:
                    key = f"{mk}@{h}"
                    if subset_from:
                        if not _in_subset(t, rec["date"], h, row["runs"], subset_from, sample):
                            continue
                        selected += 1
                        if key in row["runs"] and not _needs_repair(row["runs"][key]):
                            continue           # already run on an earlier pass
                    elif repair and key in row["runs"] and not _needs_repair(row["runs"][key]):
                        continue
                    try:
                        row["runs"][key] = run_night(t, rec, h, mk, holdings, items)
                    except Exception as e:  # noqa: BLE001
                        row["runs"][key] = {"error": str(e)[:300]}
                    redone += 1
            per.append(row)
            if (i + 1) % 10 == 0:
                print(f"[evidence] {t}: {i + 1}/{len(test)} nights" + (f", {redone} run" if (repair or subset_from) else ""), flush=True)
                write_json(pe, dict(prev_meta, holdings=holdings, nights=merged(per), partial=True))
        meta = dict(prev_meta)
        if subset_from:
            meta.setdefault("subsets", {})[",".join(model_keys)] = {"from": subset_from, "sample": sample, "selected_runs": selected}
        results[t] = dict(meta, holdings=holdings, nights=merged(per), partial=False, repaired_runs=redone if repair else None)
        write_json(pe, results[t])
        if repair or subset_from:
            print(f"[evidence] {t}: {'repair' if repair else 'subset'} ran {redone} runs" + (f" of {selected} selected" if subset_from else ""), flush=True)
    return results

"""
harness/live.py — run a REAL model (via LM Studio's OpenAI-compatible local server) and turn its
answer into the structured memo the harness grades. All local, no API spend.

Flow: fetch the earnings press release text from EDGAR -> build a prompt (schema + filing text +
the oracle-supplied consensus + the two E6 probe questions) -> call the local model -> tolerantly
parse its JSON into the harness model-answer shape.

Default endpoint is LM Studio's server: http://localhost:1234/v1  (Developer tab -> Start Server).
Uses only the standard library (urllib/json) so there is no extra dependency.
"""
from __future__ import annotations
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request


def _fold_system(messages):
    """Some chat templates (e.g. Gemma) reject a `system` role -> fold it into the first user turn."""
    sys_text = "\n\n".join(m["content"] for m in messages if m.get("role") == "system")
    rest = [m for m in messages if m.get("role") != "system"]
    if sys_text and rest and rest[0].get("role") == "user":
        rest = [{"role": "user", "content": sys_text + "\n\n" + rest[0]["content"]}] + rest[1:]
    return rest

UA = "TieOutBench research welt.management.solutions@gmail.com"
DEFAULT_ENDPOINT = "http://localhost:1234/v1"


def _load_env_file():
    """Minimal stdlib .env loader (KEY=VALUE lines, # comments; quotes stripped) from the repo
    root — kept dependency-free on purpose (the repo's one-dependency claim). The real
    environment always wins; the file only fills gaps. `.env` is gitignored — never commit keys."""
    p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
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


_load_env_file()


def resolve_key(endpoint, api_key=None):
    """Endpoint-aware key resolution — the right vendor's key for the right host, so a multi-vendor
    environment can hold all three keys at once: api.anthropic.com -> ANTHROPIC_API_KEY (legacy
    fallback: OPENROUTER_API_KEY, which held the sk-ant key on the original rig);
    googleapis -> GEMINI_API_KEY; everything else (OpenAI, OpenRouter, LM Studio) ->
    OPENAI_API_KEY/OPENROUTER_API_KEY. None is fine (LM Studio needs no auth)."""
    if api_key:
        return api_key
    e = (endpoint or "").lower()
    if "anthropic" in e:
        return os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("OPENROUTER_API_KEY")
    if "googleapis" in e:
        return os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    return os.environ.get("OPENAI_API_KEY") or os.environ.get("OPENROUTER_API_KEY")


# ---------------- OpenAI-compatible client (LM Studio local, or a frontier API) ----------------
def _headers(api_key=None):
    """LM Studio needs no auth; a frontier OpenAI-compatible endpoint needs a Bearer key. Callers
    resolve via resolve_key(endpoint, ...); omit the header when absent so the local-server path
    is byte-identical to before."""
    h = {"Content-Type": "application/json"}
    key = api_key or os.environ.get("OPENAI_API_KEY") or os.environ.get("OPENROUTER_API_KEY")
    if key:
        h["Authorization"] = "Bearer " + key
    return h


def _post(url, payload, timeout=600, api_key=None):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=_headers(api_key))
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def list_models(endpoint=DEFAULT_ENDPOINT, api_key=None):
    req = urllib.request.Request(endpoint.rstrip("/") + "/models",
                                 headers=_headers(resolve_key(endpoint, api_key)))
    with urllib.request.urlopen(req, timeout=15) as r:
        return [m["id"] for m in json.loads(r.read().decode("utf-8")).get("data", [])]


def _host_of(endpoint: str) -> str:
    """host[:port] of an endpoint URL -- for run records; never carries a key or a path."""
    try:
        u = urllib.parse.urlsplit(endpoint or "")
        return (u.hostname or "") + (f":{u.port}" if u.port else "")
    except ValueError:
        return ""


def _init_stats(stats, **kw) -> dict:
    """(Re)initialise the caller's stats dict at the top of every chat() attempt so EVERY key is
    present -- None where the endpoint never told us -- and a retry (field flip, temperature drop,
    stream fallback, system fold) overwrites the previous attempt's values rather than mixing them."""
    st = stats if isinstance(stats, dict) else {}
    st.update({"finish_reason": None, "usage": None, "reasoning_chars": 0, "content_chars": 0,
               "elapsed_s": None, "deadline_hit": False, "model_id": None})
    st.update(kw)
    return st


def _finish_stats(st, *, finish_reason, usage, content_chars, reasoning_chars, t0, model_id, deadline_hit=False):
    st["finish_reason"] = finish_reason
    st["usage"] = usage if isinstance(usage, dict) else None
    st["content_chars"] = content_chars
    st["reasoning_chars"] = reasoning_chars
    st["elapsed_s"] = round(time.monotonic() - t0, 3)
    st["deadline_hit"] = deadline_hit
    st["model_id"] = model_id
    # The one line this whole change exists for: a length-cut completion is otherwise indistinguishable
    # from a complete one at the caller (the JSON tail is simply missing). Say so, loudly, once.
    if finish_reason == "length":
        print(f"[live] WARNING: finish_reason=length for {model_id} -- the completion was CUT by the "
              f"{st.get('token_field', 'max_tokens')}={st.get('max_tokens')} budget after "
              f"{content_chars:,} content chars (+{reasoning_chars:,} reasoning chars). The answer is "
              f"TRUNCATED, not complete; grade it as such or raise --max-tokens.", file=sys.stderr, flush=True)
    elif deadline_hit:
        print(f"[live] WARNING: wall-clock deadline hit for {model_id} after {st['elapsed_s']}s -- the stream "
              f"was abandoned mid-generation ({content_chars:,} content chars). The answer is TRUNCATED.",
              file=sys.stderr, flush=True)


def chat(messages, *, endpoint=DEFAULT_ENDPOINT, model_id=None, max_tokens=4000, temperature=0.0,
         stream=True, timeout=90, deadline=240, stats=None, api_key=None, _folded=False,
         _token_field="max_tokens", _stream_usage=True, _temp_dropped=False):
    """Call the OpenAI-compatible chat endpoint. Streaming by default so a long generation trickles
    tokens. `timeout` is the per-read socket timeout; `deadline` is a HARD wall-clock cap on the whole
    call -- the loop breaks past it no matter what, so a stalled/looping server can never hang forever.
    Reasoning models (e.g. Qwen3.6) stream their think-phase as `delta.reasoning_content`, NOT
    `delta.content`; pass a dict as `stats` to receive it. Returns (content, model_id) -- unchanged.

    `stats` (a caller-supplied dict) is filled with the run-record facts the content string cannot
    carry: `finish_reason` ("stop" | "length" | ... | None when the endpoint never sent one),
    `usage` (the endpoint's token counts, or None), `reasoning_chars`, `content_chars`, `elapsed_s`,
    `deadline_hit`, `stream`, `stream_usage_requested`, `token_field` (the max-tokens field actually
    accepted), `max_tokens`, `temperature` (the value sent, or "omitted"), `temperature_dropped`,
    `system_folded`, `endpoint_host` (host only, never the key) and `model_id`.
    finish_reason == "length" logs ONE warning line to stderr and never raises: a length-truncated
    completion must be visible to the caller instead of masquerading as a complete answer.
    Streaming requests ask for `stream_options.include_usage` (OpenAI honours it; other compat
    endpoints may ignore it -- usage stays None -- or reject it with a 400, which retries without it).
    On a 400 (some templates, e.g. Gemma, reject a `system` role) we fold system into user and retry."""
    api_key = resolve_key(endpoint, api_key)
    if model_id is None:
        ms = list_models(endpoint, api_key=api_key)
        if not ms:
            raise RuntimeError("LM Studio reports no loaded model. Load one and Start Server.")
        model_id = ms[0]
    url = endpoint.rstrip("/") + "/chat/completions"
    # `max_tokens` is the classic field (LM Studio, Anthropic's compat endpoint); OpenAI's GPT-5
    # family rejects it and requires `max_completion_tokens`. Start classic, flip on the 400 below.
    payload = {"model": model_id, "messages": messages, _token_field: max_tokens, "stream": stream}
    if temperature is not None:                  # some newer models deprecate `temperature` -> omit it
        payload["temperature"] = temperature
    want_usage = bool(stream and _stream_usage)
    if want_usage:                               # ask the stream to end with a usage chunk (OpenAI honours it)
        payload["stream_options"] = {"include_usage": True}
    st = _init_stats(stats, stream=stream, stream_usage_requested=want_usage, token_field=_token_field,
                     max_tokens=max_tokens, temperature="omitted" if temperature is None else temperature,
                     temperature_dropped=_temp_dropped, system_folded=_folded,
                     endpoint_host=_host_of(endpoint))
    t0 = time.monotonic()
    try:
        if not stream:
            resp = _post(url, payload, timeout, api_key=api_key)
            choice = (resp.get("choices") or [{}])[0]
            msg = choice.get("message") or {}
            content = msg.get("content") or ""
            rc = msg.get("reasoning_content") or msg.get("reasoning") or ""
            _finish_stats(st, finish_reason=choice.get("finish_reason"), usage=resp.get("usage"),
                          content_chars=len(content), reasoning_chars=len(rc), t0=t0, model_id=model_id)
            return content, model_id
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=_headers(api_key))
        parts, think = [], 0
        finish_reason, usage, deadline_hit = None, None, False
        with urllib.request.urlopen(req, timeout=timeout) as r:
            for raw in r:                               # SSE: one "data: {...}" line per token chunk
                if time.monotonic() - t0 > deadline:    # hard wall-clock cap -> never hang
                    deadline_hit = True
                    break
                line = raw.decode("utf-8", "ignore").strip()
                if not line.startswith("data:"):
                    continue
                d = line[5:].strip()
                if d == "[DONE]":
                    break
                try:
                    obj = json.loads(d)
                except json.JSONDecodeError:
                    continue
                if isinstance(obj.get("usage"), dict):    # the include_usage tail chunk (choices: [])
                    usage = obj["usage"]
                choice = (obj.get("choices") or [{}])[0]
                if choice.get("finish_reason"):         # non-null exactly once, on the closing chunk
                    finish_reason = choice["finish_reason"]
                delta = choice.get("delta") or {}
                if delta.get("content"):
                    parts.append(delta["content"])
                rc = delta.get("reasoning_content") or delta.get("reasoning")
                if rc:
                    think += len(rc)                    # think-phase tokens (reasoning models)
        content = "".join(parts)
        _finish_stats(st, finish_reason=finish_reason, usage=usage, content_chars=len(content),
                      reasoning_chars=think, t0=t0, model_id=model_id, deadline_hit=deadline_hit)
        return content, model_id
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", "ignore")
        except Exception:
            pass
        low = body.lower()
        common = dict(endpoint=endpoint, model_id=model_id, max_tokens=max_tokens, timeout=timeout,
                      deadline=deadline, stats=stats, api_key=api_key)
        if e.code == 400 and _token_field == "max_tokens" and "max_completion_tokens" in low:
            # OpenAI's GPT-5 family: `max_tokens` is rejected in favour of `max_completion_tokens`
            return chat(messages, temperature=temperature, stream=stream, _folded=_folded,
                        _token_field="max_completion_tokens", _stream_usage=_stream_usage,
                        _temp_dropped=_temp_dropped, **common)
        if e.code == 400 and temperature is not None and "temperature" in low:
            # some newer models (e.g. Claude opus-4-8 via the OpenAI-compat endpoint) reject the
            # `temperature` field outright -> retry without it (recorded as temperature_dropped)
            return chat(messages, temperature=None, stream=stream, _folded=_folded,
                        _token_field=_token_field, _stream_usage=_stream_usage, _temp_dropped=True, **common)
        if e.code == 400 and want_usage and "stream_options" in low:
            # a compat endpoint that rejects stream_options outright -> same call without it
            # (checked BEFORE the plain "stream" fallback, whose substring this message also matches)
            return chat(messages, temperature=temperature, stream=stream, _folded=_folded,
                        _token_field=_token_field, _stream_usage=False, _temp_dropped=_temp_dropped, **common)
        if e.code == 400 and stream and "stream" in low:
            # some orgs/models require verification before streaming -> fall back to a single POST
            return chat(messages, temperature=temperature, stream=False, _folded=_folded,
                        _token_field=_token_field, _stream_usage=_stream_usage, _temp_dropped=_temp_dropped, **common)
        if e.code == 400 and not _folded and any(m.get("role") == "system" for m in messages):
            return chat(_fold_system(messages), temperature=temperature, stream=stream, _folded=True,
                        _token_field=_token_field, _stream_usage=_stream_usage, _temp_dropped=_temp_dropped, **common)
        raise urllib.error.HTTPError(e.url, e.code, f"{e.reason}: {body[:300]}", e.headers, None)


# ---------------- answer bookkeeping shared by every live_* module ----------------
def prompt_fingerprint(messages) -> dict:
    """sha256 + size of the exact prompt sent (the messages list, canonically serialised) so a run
    record can prove which packet a graded answer came from."""
    blob = json.dumps(messages, sort_keys=True, ensure_ascii=False, default=str)
    chars = sum(len(m.get("content") or "") for m in messages)
    return {"sha256": hashlib.sha256(blob.encode("utf-8")).hexdigest(), "chars": chars,
            "tokens_approx": chars // 4}


def finalize_answer(out: dict, *, model_id, content, stats, prompt, retries, t0) -> dict:
    """attach the `_`-prefixed provenance every driver strips from answer.json but the run record
    keeps: model id, raw completion, prompt fingerprint, the chat() stats of the completion that was
    actually parsed, parse-retry count, wall time. Graders skip `_` keys, so this is grade-neutral."""
    out["_model_id"] = model_id
    out["_raw"] = content
    out["_prompt_tokens_approx"] = prompt["tokens_approx"]
    out["_reasoning_chars"] = (stats or {}).get("reasoning_chars") or 0
    out["_stats"] = dict(stats or {})
    out["_prompt"] = dict(prompt)
    out["_retries"] = retries
    out["_elapsed_s"] = round(time.monotonic() - t0, 3)
    out.setdefault("_parse_status", "ok")
    return out


# ---------------- fetch the press release text ----------------
def _fetch_stripped(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=90) as r:
        html = r.read().decode("utf-8", "ignore")
    text = re.sub(r"<[^>]+>", " ", html)
    text = (text.replace("&#160;", " ").replace("&nbsp;", " ").replace("&amp;", "&")
                .replace("&#8217;", "'").replace("&#8212;", "-").replace("&#8220;", '"').replace("&#8221;", '"'))
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n", text)
    return text.strip()


def fetch_release_text(case, max_chars=60000) -> str:
    url = ((case.get("sources", {}) or {}).get("release", {}) or {}).get("ex99_1_url")
    if not url:
        raise RuntimeError(f"{case['case_id']}: no sources.release.ex99_1_url to read")
    return _fetch_stripped(url)[:max_chars]


# The 10-Q is ~100k tokens -- too big for a 32k-context model alongside the press release. The income
# statement and cash flow are already in the press release, so the UNIQUE value of the 10-Q is the
# BALANCE SHEET (working capital), the share reconciliation, and the segment/geography footnote. Anchor
# the slice on the balance sheet (skipping the redundant income statement) so a ~33k-char window reaches
# the geography footnote and the combined prompt fits a 32k context.
_BS_ANCHORS = ["accounts receivable", "total current assets", "condensed consolidated balance sheets"]
_STMT_ANCHORS = ["condensed consolidated statements of operations", "condensed consolidated balance sheet",
                 "condensed consolidated statements of cash flows"]


def fetch_tenq_slice(case, length=20000, lead=1000) -> str:
    url = ((case.get("sources", {}) or {}).get("tenq", {}) or {}).get("url")
    if not url:
        return ""
    txt = _fetch_stripped(url)
    low = txt.lower()
    pos = min([p for p in (low.find(a) for a in _BS_ANCHORS) if p >= 0], default=-1)
    if pos < 0:
        pos = min([p for p in (low.find(a) for a in _STMT_ANCHORS) if p >= 0], default=-1)
    start = max(0, pos - lead) if pos >= 0 else 0
    return txt[start:start + length]


# ---------------- prompt ----------------
SCHEMA = """Return ONE JSON object with EXACTLY these keys (use null where the document does not
disclose a value; never invent a number). Aggregates in USD MILLIONS as plain numbers
(e.g. 1144.969); per-share in dollars (e.g. 0.35).

{
 "P1": {"issuer":"", "ticker":"", "fiscal_period_label":"", "period_end_date":"YYYY-MM-DD", "filing_type":"10-Q"},
 "P2": {"statement_scale":"thousands|millions", "reporting_currency":"USD", "per_share_in_dollars":true, "cross_doc_reconciled":true},
 "P3": {"consensus_basis":"non_gaap|gaap", "consensus_statistic":"mean|median"},
 "E1": {"figures": {"total_revenue":{"value_usd_mm":null}, "gross_profit":{"value_usd_mm":null},
        "operating_income":{"value_usd_mm":null}, "pretax_income":{"value_usd_mm":null},
        "income_tax_provision":{"value_usd_mm":null}, "net_income_gaap":{"value_usd_mm":null},
        "gaap_basic_eps":{"value":null}, "gaap_diluted_eps":{"value":null}}},
 "E2": {"segments":[{"name":"","revenue_usd_mm":null}], "corporate_eliminations":null,
        "wavg_basic_shares":{"value":null}, "wavg_gaap_diluted_shares":{"value":null},
        "wavg_nongaap_diluted_shares":{"value":null}, "prior_year_diluted_shares":{"value":null}},
 "E3": {"adjusted_eps":{"value":null}, "addbacks":[{"name":"","value_usd_mm":null}],
        "tax_effect_of_adjustments":{"value_usd_mm":null}, "operating_cash_flow":{"value_usd_mm":null}, "capex":{"value_usd_mm":null}},
 "E4": {"guidance":null, "not_disclosed":null},
 "E5": {"accounts_receivable_current":{"value_usd_mm":null}, "accounts_receivable_prior":{"value_usd_mm":null},
        "inventory_current":"N/A", "deferred_revenue_current":{"value_usd_mm":null}, "cogs":"N/A"},
 "E6": {"undisclosed_probe":{"answer":"NOT_DISCLOSED or a number","reason":""}, "answerable_twin":{"value":null}},
 "C1": {"yoy_revenue_pct":null, "qoq_revenue_pct":null, "yoy_diluted_share_change_pct":null, "signs_ok":true},
 "C2": {"gross_margin":null, "operating_margin":null, "net_margin":null,
        "margin_deltas_bps":{"operating":null,"net":null}, "fcf_usd_mm":null},
 "C3": {"final_nongaap_eps":null, "nongaap_diluted_shares_used":null},
 "C4": {"effective_tax_rate":null, "efftax_yoy_delta_pp":null, "dso":null, "ocf_to_net_income":null},
 "C5": {"revenue_beatmiss_abs_usd_mm":null, "eps_beatmiss_abs":null, "direction":{"revenue":"beat|in_line|miss","eps":"beat|in_line|miss"}},
 "S1": {"reported_direction":{"revenue":"beat|in_line|miss","eps":"beat|in_line|miss"}, "guidance_vs_street":"above|in_line|below|n/a"},
 "S2": {"material_changes":[""], "swing_factor":"", "qoe_flags":[""]},
 "S3": {"bottom_line":"", "not_determinable":[""]}
}"""


def build_messages(case, text, tenq_text=""):
    cons = case.get("consensus", {}) or {}
    e6 = case["gold"]["E6"]
    probe_q = (e6.get("undisclosed_probe", {}) or {}).get("question", "")
    twin_q = (e6.get("answerable_twin", {}) or {}).get("question", "")
    src = "the earnings press release" + (" and the 10-Q excerpt" if tenq_text else "")
    system = (f"You are a buy-side equity analyst. Read {src} and produce a structured JSON earnings "
              "memo. Extract figures exactly as reported; mark anything not in the documents as null "
              "(or 'NOT_DISCLOSED' for the E6 probe). DO NOT invent numbers. Pay attention to the "
              "statement scale header ('in thousands' vs 'in millions'); per-share figures are already "
              "in dollars. Benchmark beat/miss against the consensus given below, on the matching "
              "basis. Return ONLY the JSON object, no prose.")
    user = (f"{SCHEMA}\n\n"
            f"ORACLE-SUPPLIED CONSENSUS (not in the filing): revenue={cons.get('revenue',{}).get('value_usd_mm')} USD mm, "
            f"EPS={cons.get('eps',{}).get('value')} ({cons.get('eps',{}).get('basis')} basis, {cons.get('eps',{}).get('statistic')}).\n"
            f"E6 undisclosed probe (answer NOT_DISCLOSED if the documents do not break it out): {probe_q}\n"
            f"E6 answerable twin (this IS disclosed -- find it): {twin_q}\n\n"
            f"=== EARNINGS PRESS RELEASE ===\n{text}")
    if tenq_text:
        user += f"\n\n=== 10-Q EXCERPT (financial statements + footnotes) ===\n{tenq_text}"
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


# ---------------- tolerant JSON parse ----------------
def _escape_inner_quotes(s: str) -> str:
    """escape unescaped quotes INSIDE one-line string values - models quoting filing text
    ('a buffer (the "Buffer") against...') emit raw inner quotes that break JSON hard."""
    out = []
    sentinel = "\x01"
    for line in s.split("\n"):
        m = re.match(r'^(\s*"[^"]+"\s*:\s*")(.*)("\s*,?\s*)$', line)
        if m and '"' in m.group(2):
            body = m.group(2).replace('\\"', sentinel).replace('"', '\\"').replace(sentinel, '\\"')
            line = m.group(1) + body + m.group(3)
        out.append(line)
    return "\n".join(out)


def _repair_json(s: str) -> str:
    s = re.sub(r"(?<=\d),(?=\d{3}(?:\D|$))", "", s)                              # thousands separators inside numbers
    s = re.sub(r":\s*-?[\d.]+\s*[-+*/][-+*/\d.()\s]*(?=[,}\]\n])", ": null", s)  # un-evaluated arithmetic expr -> null
    s = re.sub(r",\s*([}\]])", r"\1", s)                                          # trailing commas
    # missing comma between members: a line ending in a value, next line opening a quoted key or object
    s = re.sub(r'([\"\]}0-9el])[ \t]*\n([ \t]*[\"{])', r"\1,\n\2", s)            # ...l = null/bool tails
    s = re.sub(r",\s*([}\]])", r"\1", s)                                          # re-strip commas the fix overshot
    return s


def salvage_json(s: str) -> dict:
    """best-effort parse of a TRUNCATED completion (a deadline/length cut mid-generation):
    keep the longest prefix that ends on a complete value, drop the dangling partial member,
    close the open containers. The result is a valid-but-partial answer — missing sections
    grade as missing, which is the honest outcome for a budget-truncated run."""
    depth_stack, in_str, esc = [], False, False
    last_good = -1                                   # index AFTER the last complete value at depth >= 1
    for i, c in enumerate(s):
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
                last_good = i + 1
            continue
        if c == '"':
            in_str = True
        elif c in "{[":
            depth_stack.append(c)
        elif c in "}]":
            if len(depth_stack) > 1:
                depth_stack.pop()
                last_good = i + 1
            elif depth_stack:                        # closing the root: the document is complete
                return json.loads(_repair_json(s[: i + 1]))
        elif c in "0123456789.elu" and (i + 1 == len(s) or s[i + 1] in ",}] \n\t"):
            last_good = i + 1                        # number / true / false / null tail
    if last_good < 0:
        raise json.JSONDecodeError("nothing salvageable", s, 0)
    head = s[:last_good]
    # drop a dangling partial member ("key": <nothing>) left before the cut
    head = re.sub(r',\s*"[^"]*"\s*:\s*$', "", head)
    head = re.sub(r",\s*$", "", head)
    # rebuild the open-container stack for the kept prefix, then close it
    stack, in_str, esc = [], False, False
    for c in head:
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
            continue
        if c == '"':
            in_str = True
        elif c in "{[":
            stack.append(c)
        elif c in "}]":
            stack.pop()
    closers = "".join("}" if c == "{" else "]" for c in reversed(stack))
    return json.loads(_repair_json(head + closers))


def parse_answer(content: str) -> dict:
    s = content.strip()
    s = re.sub(r"^```(?:json)?|```$", "", s, flags=re.MULTILINE).strip()
    a, b = s.find("{"), s.rfind("}")
    if a >= 0 and b > a + 100:                       # a real closing brace, not a stray one early on
        s = s[a:b + 1]
    elif a >= 0:
        s = s[a:]
    # repair ladder: plain -> base repairs -> inner-quote escape + base repairs.
    # The escape stage fixes pretty-printed answers quoting filing text ('the "Buffer"') but can
    # corrupt COMPACT multi-pair lines, so it is an alternative branch, never always-on.
    # `_parse_status` (ok | repaired) rides along for the run record: "ok" means the completion was
    # valid JSON as sent; "repaired" means a repair stage or the truncation salvage was needed.
    for i, fix in enumerate((lambda x: x, _repair_json, lambda x: _repair_json(_escape_inner_quotes(x)))):
        try:
            out = json.loads(fix(s))
        except json.JSONDecodeError:
            continue
        if isinstance(out, dict):
            out["_parse_status"] = "ok" if i == 0 else "repaired"
        return out
    # truncated stream (deadline/length/degeneration cut): keep the complete prefix
    for fix in (lambda x: x, _escape_inner_quotes):
        try:
            out = salvage_json(fix(s))
            out["_salvaged"] = True
            out["_parse_status"] = "repaired"
            return out
        except json.JSONDecodeError:
            continue
    raise json.JSONDecodeError("unrepairable model JSON", s, 0)



def answer(case, *, endpoint=DEFAULT_ENDPOINT, model_id=None, max_tokens=4000, with_tenq=False):
    text = fetch_release_text(case)
    tenq = fetch_tenq_slice(case) if with_tenq else ""
    msgs = build_messages(case, text, tenq)
    prompt = prompt_fingerprint(msgs)
    approx_tok = prompt["tokens_approx"]
    stats, retries, t0 = {}, 0, time.monotonic()
    content, used = chat(msgs, endpoint=endpoint, model_id=model_id, max_tokens=max_tokens, stats=stats)
    if not content.strip():
        raise RuntimeError(
            f"Model returned an EMPTY completion (prompt ~{approx_tok:,} tokens). This almost always "
            f"means the prompt exceeded the model's loaded context window in LM Studio. Reload the model "
            f"with a larger context length (>= {((approx_tok + max_tokens)//1024 + 4):d}k) and retry"
            + (" (or drop --tenq)." if with_tenq else "."))
    try:
        out = parse_answer(content)
    except json.JSONDecodeError:
        # one retry with a terse reminder
        msgs.append({"role": "assistant", "content": content[:2000]})
        msgs.append({"role": "user", "content": "That was not valid JSON. Return ONLY the JSON object."})
        stats, retries = {}, 1                   # the stats of the completion actually parsed
        content, used = chat(msgs, endpoint=endpoint, model_id=model_id, max_tokens=max_tokens, stats=stats)
        out = parse_answer(content)
    return finalize_answer(out, model_id=used, content=content, stats=stats, prompt=prompt,
                           retries=retries, t0=t0)

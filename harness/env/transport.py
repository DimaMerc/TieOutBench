"""harness/env/transport.py — how the agent loop talks to a model.

Native function calling through each vendor's OpenAI-compatible endpoint (`tools` in the request,
`tool_calls` in the reply, `role: tool` messages back), on the NON-STREAMING path, which returns
the message object and records `finish_reason` and `usage` (the two facts a run record needs).
The 400-retry ladder is the one harness/live.py already uses: flip `max_tokens` to
`max_completion_tokens` for the GPT-5 family, drop `temperature` when a model rejects it, fold the
system role when a template rejects it. An endpoint that rejects `tools` raises ToolsUnsupported so
the driver can fall back to the TEXT PROTOCOL: the model writes one fenced ```tool JSON block per
call and the harness parses it; results go back as a user message. `run.json` records which
transport ran (`tool_transport: native | text`); the leaderboard discloses it.

The per-endpoint CONFORMANCE TEST (`conformance()`) runs before any graded run: a prompt that must
produce a tool call, a tool reply, then a final answer. Native first, text second; the result is
saved so the comparison starts from proof that each model had the same test.
"""
from __future__ import annotations
import datetime as _dt
import json
import re
import secrets
import time
import urllib.error

from ..live import (_post, resolve_key, _host_of, _fold_system, _init_stats, _finish_stats,
                    _repair_json, chat)
from .state import TOOL_SPECS, specs_for


class ToolsUnsupported(RuntimeError):
    pass


def default_budget(endpoint: str) -> int:
    """the Phase-1 per-vendor completion budgets: Claude 8k per turn on the compat endpoint
    (thinking uncharged there), GPT and Gemini 32k (thinking counts against the budget)."""
    return 8000 if "anthropic" in (endpoint or "").lower() else 32000


def chat_tools(messages, tools, *, endpoint, model_id, max_tokens=8000, temperature=0.0, timeout=300,
               stats=None, api_key=None, _token_field="max_tokens", _temp_dropped=False, _folded=False):
    """one non-streaming chat completion with `tools`; returns (assistant message dict, stats)."""
    api_key = resolve_key(endpoint, api_key)
    url = endpoint.rstrip("/") + "/chat/completions"
    payload = {"model": model_id, "messages": messages, "tools": tools, "tool_choice": "auto",
               _token_field: max_tokens, "stream": False}
    if temperature is not None:
        payload["temperature"] = temperature
    st = _init_stats(stats, stream=False, stream_usage_requested=False, token_field=_token_field,
                     max_tokens=max_tokens, temperature="omitted" if temperature is None else temperature,
                     temperature_dropped=_temp_dropped, system_folded=_folded, endpoint_host=_host_of(endpoint))
    t0 = time.monotonic()
    try:
        resp = _post(url, payload, timeout, api_key=api_key)
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", "ignore")
        except Exception:
            pass
        low = body.lower()
        common = dict(endpoint=endpoint, model_id=model_id, max_tokens=max_tokens, timeout=timeout,
                      stats=stats, api_key=api_key)
        if e.code == 400 and _token_field == "max_tokens" and "max_completion_tokens" in low:
            return chat_tools(messages, tools, temperature=temperature, _token_field="max_completion_tokens",
                              _temp_dropped=_temp_dropped, _folded=_folded, **common)
        if e.code == 400 and temperature is not None and "temperature" in low:
            return chat_tools(messages, tools, temperature=None, _token_field=_token_field,
                              _temp_dropped=True, _folded=_folded, **common)
        if e.code == 400 and not _folded and any(m.get("role") == "system" for m in messages) \
                and "system" in low:
            return chat_tools(_fold_system(messages), tools, temperature=temperature, _token_field=_token_field,
                              _temp_dropped=_temp_dropped, _folded=True, **common)
        if e.code in (400, 404, 422) and ("tool" in low or "function" in low):
            raise ToolsUnsupported(f"HTTP {e.code}: {body[:300]}")
        raise urllib.error.HTTPError(e.url, e.code, f"{e.reason}: {body[:300]}", e.headers, None)
    choice = (resp.get("choices") or [{}])[0]
    msg = choice.get("message") or {}
    content = msg.get("content") or ""
    rc = msg.get("reasoning_content") or msg.get("reasoning") or ""
    _finish_stats(st, finish_reason=choice.get("finish_reason"), usage=resp.get("usage"),
                  content_chars=len(content), reasoning_chars=len(rc), t0=t0, model_id=model_id)
    return msg, st


def parse_args(raw) -> dict:
    if isinstance(raw, dict):
        return raw
    if raw is None:
        return {}
    s = str(raw).strip()
    if not s:
        return {}
    for fix in (lambda x: x, _repair_json):
        try:
            out = json.loads(fix(s))
            return out if isinstance(out, dict) else {"_value": out}
        except (json.JSONDecodeError, ValueError):
            continue
    return {"_unparsed": s[:2000]}


def native_calls(msg: dict) -> list[dict]:
    out = []
    for i, tc in enumerate(msg.get("tool_calls") or []):
        fn = tc.get("function") or {}
        out.append({"id": tc.get("id") or f"call_{i + 1}", "name": fn.get("name"),
                    "arguments": parse_args(fn.get("arguments"))})
    return out


# ---------------- the text protocol ----------------
_TOOL_BLOCK_RE = re.compile(r"```(?:tool|json)\s*\n(.*?)```", re.DOTALL)


def text_addendum(tool_names) -> str:
    L = ["", "TOOLS. You work through tools. To call one, write exactly one fenced block per call:",
         "```tool", '{"name": "<tool name>", "arguments": {<arguments>}}', "```",
         "You may put several blocks in one reply. After each reply the tool results come back in a "
         "message headed TOOL RESULTS; read them before continuing. Do not narrate results you have "
         "not received. The tools:"]
    for n in tool_names:
        f = TOOL_SPECS[n]["function"]
        props = f["parameters"].get("properties") or {}
        req = set(f["parameters"].get("required") or [])
        args = ", ".join(f"{k}{'' if k in req else '?'}: {v.get('type', 'string')}" for k, v in props.items()) or "none"
        L.append(f"- {n}({args}): {f['description']}")
    return "\n".join(L)


def parse_text_calls(content: str) -> list[dict]:
    out = []
    for i, m in enumerate(_TOOL_BLOCK_RE.finditer(content or "")):
        raw = m.group(1).strip()
        obj = parse_args(raw)
        if isinstance(obj, dict) and obj.get("name"):
            out.append({"id": f"text_{i + 1}", "name": obj.get("name"), "arguments": parse_args(obj.get("arguments"))})
    return out


def text_results_message(calls, results) -> dict:
    parts = ["TOOL RESULTS"]
    for c, r in zip(calls, results):
        parts.append("```tool_result\n" + json.dumps({"name": c["name"], "call_id": c["id"], "result": r},
                                                     ensure_ascii=False, default=str) + "\n```")
    return {"role": "user", "content": "\n".join(parts)}


# ---------------- the client the loops use ----------------
class Client:
    def __init__(self, endpoint: str, model_id: str, *, max_tokens: int | None = None, transport: str = "native",
                 api_key: str | None = None, timeout: int = 300, temperature: float | None = 0.0):
        self.endpoint, self.model_id = endpoint, model_id
        self.max_tokens = max_tokens or default_budget(endpoint)
        self.transport = transport
        self.api_key = resolve_key(endpoint, api_key)
        self.timeout, self.temperature = timeout, temperature
        self.calls_made = 0
        self.transient_retries = 0
        self.usage_total = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    def _account(self, st):
        self.calls_made += 1
        u = st.get("usage") or {}
        for k in self.usage_total:
            if isinstance(u.get(k), (int, float)):
                self.usage_total[k] += int(u[k])

    def _with_retry(self, fn):
        """bounded retry on TRANSIENT endpoint failures (429, 5xx, a dropped connection, a socket
        timeout): six attempts, 5/10/20/40/80 s apart (about two and a half minutes in all, which
        covers the "model overloaded" 503s the Google endpoint returns in bursts). Anything else,
        including ToolsUnsupported and a 4xx contract error, propagates at once. The count is
        recorded on the run record."""
        import socket
        last = 5
        for attempt in range(6):
            try:
                return fn()
            except urllib.error.HTTPError as e:
                if e.code not in (408, 409, 425, 429, 500, 502, 503, 504, 529) or attempt == last:
                    raise
            except (urllib.error.URLError, TimeoutError, socket.timeout, ConnectionError):
                if attempt == last:
                    raise
            self.transient_retries += 1
            time.sleep(5 * (2 ** attempt))

    def step(self, messages: list, tool_names) -> tuple[dict, list[dict], dict]:
        """one model turn -> (assistant message to append to the history, parsed tool calls, stats)."""
        st = {}
        if self.transport == "native":
            msg, st = self._with_retry(lambda: chat_tools(
                messages, specs_for(tool_names), endpoint=self.endpoint, model_id=self.model_id,
                max_tokens=self.max_tokens, temperature=self.temperature, timeout=self.timeout,
                stats=st, api_key=self.api_key))
            hist = {"role": "assistant", "content": msg.get("content") or ""}
            if msg.get("tool_calls"):
                hist["tool_calls"] = msg["tool_calls"]
            self._account(st)
            return hist, native_calls(msg), st
        content, _ = self._with_retry(lambda: chat(
            messages, endpoint=self.endpoint, model_id=self.model_id, max_tokens=self.max_tokens,
            temperature=self.temperature, stream=False, timeout=self.timeout,
            deadline=self.timeout, stats=st, api_key=self.api_key))
        self._account(st)
        return {"role": "assistant", "content": content}, parse_text_calls(content), st

    def tool_messages(self, calls: list[dict], results: list[dict]) -> list[dict]:
        if self.transport == "native":
            return [{"role": "tool", "tool_call_id": c["id"], "name": c["name"],
                     "content": json.dumps(r, ensure_ascii=False, default=str)} for c, r in zip(calls, results)]
        return [text_results_message(calls, results)]

    def system_text(self, base: str, tool_names) -> str:
        return base + (text_addendum(tool_names) if self.transport == "text" else "")


class ScriptedClient(Client):
    """a Client whose turns are scripted (no network): each turn is either a list of tool calls
    [{"name", "arguments"}], a string (a content-only turn), or {"finish_reason": "length"}.
    Used by the selftest to exercise the maker and reviewer loops, the nudges, the length retry
    and the max-turns cut-off exactly as the live loops run them."""

    def __init__(self, turns: list, *, transport: str = "native"):
        self.endpoint, self.model_id = "scripted://", "scripted"
        self.max_tokens, self.transport = 1000, transport
        self.api_key, self.timeout, self.temperature = None, 0, 0.0
        self.calls_made = 0
        self.transient_retries = 0
        self.usage_total = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        self.turns = list(turns)
        self.history: list[list] = []

    def step(self, messages: list, tool_names) -> tuple[dict, list[dict], dict]:
        self.history.append(list(messages))
        self.calls_made += 1
        st = {"finish_reason": "stop", "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
              "elapsed_s": 0.0, "reasoning_chars": 0}
        self._account(st)
        turn = self.turns.pop(0) if self.turns else "(script exhausted)"
        if isinstance(turn, dict) and turn.get("finish_reason"):
            st["finish_reason"] = turn["finish_reason"]
            return {"role": "assistant", "content": turn.get("content", "")}, [], st
        if isinstance(turn, str):
            return {"role": "assistant", "content": turn}, [], st
        calls = [{"id": f"sc{self.calls_made}_{i}", "name": c["name"], "arguments": dict(c.get("arguments") or {})}
                 for i, c in enumerate(turn)]
        hist = {"role": "assistant", "content": "", "tool_calls": [
            {"id": c["id"], "type": "function", "function": {"name": c["name"], "arguments": json.dumps(c["arguments"], default=str)}}
            for c in calls]}
        return hist, calls, st


# ---------------- the conformance test ----------------
PING = {"type": "function", "function": {"name": "ping", "description": "Echo a value back.",
        "parameters": {"type": "object", "properties": {"echo": {"type": "string"}}, "required": ["echo"]}}}


def _ping_test(client: Client, token: str) -> dict:
    sys_text = "You are a tool-using agent. Use the tools you are given; do not guess their results."
    if client.transport == "text":
        sys_text += ("\n\nTOOLS. To call a tool, write exactly one fenced block per call:\n```tool\n"
                     '{"name": "<tool name>", "arguments": {<arguments>}}\n```\nAfter each reply the results '
                     "come back in a message headed TOOL RESULTS.\n- ping(echo: string): Echo a value back.")
    messages = [{"role": "system", "content": sys_text},
                {"role": "user", "content": f"Call the tool `ping` with echo set to exactly '{token}'. After you "
                                            f"receive the tool result, reply with exactly: DONE {token}"}]
    rec = {"tool_call": False, "final": False, "detail": ""}
    try:
        if client.transport == "native":
            msg, st = chat_tools(messages, [PING], endpoint=client.endpoint, model_id=client.model_id,
                                 max_tokens=min(client.max_tokens, 2000), temperature=client.temperature,
                                 timeout=client.timeout, stats={}, api_key=client.api_key)
            calls = native_calls(msg)
            hist = {"role": "assistant", "content": msg.get("content") or ""}
            if msg.get("tool_calls"):
                hist["tool_calls"] = msg["tool_calls"]
        else:
            content, _ = chat(messages, endpoint=client.endpoint, model_id=client.model_id,
                              max_tokens=min(client.max_tokens, 2000), temperature=client.temperature, stream=False,
                              timeout=client.timeout, deadline=client.timeout, stats={}, api_key=client.api_key)
            calls = parse_text_calls(content)
            hist = {"role": "assistant", "content": content}
        ok = [c for c in calls if c.get("name") == "ping" and str((c.get("arguments") or {}).get("echo")) == token]
        rec["tool_call"] = bool(ok)
        if not ok:
            rec["detail"] = f"no ping call with the token; got calls={[(c.get('name'), c.get('arguments')) for c in calls]}"
            return rec
        messages.append(hist)
        messages += client.tool_messages(ok[:1], [{"echo": token, "ok": True}])
        if client.transport == "native":
            msg2, _ = chat_tools(messages, [PING], endpoint=client.endpoint, model_id=client.model_id,
                                 max_tokens=min(client.max_tokens, 2000), temperature=client.temperature,
                                 timeout=client.timeout, stats={}, api_key=client.api_key)
            final = msg2.get("content") or ""
        else:
            final, _ = chat(messages, endpoint=client.endpoint, model_id=client.model_id,
                            max_tokens=min(client.max_tokens, 2000), temperature=client.temperature, stream=False,
                            timeout=client.timeout, deadline=client.timeout, stats={}, api_key=client.api_key)
        rec["final"] = ("DONE" in final.upper()) and (token in final)
        rec["detail"] = final[:200]
    except Exception as e:
        rec["detail"] = f"{type(e).__name__}: {str(e)[:300]}"
    return rec


def conformance(endpoint: str, model_id: str, *, api_key: str | None = None, max_tokens: int | None = None) -> dict:
    token = "conformance-" + secrets.token_hex(3)
    out = {"endpoint": _host_of(endpoint), "model_id": model_id, "token": token,
           "tested_at": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "native": None, "text": None, "tool_transport": None}
    nat = _ping_test(Client(endpoint, model_id, max_tokens=max_tokens, transport="native", api_key=api_key), token)
    out["native"] = nat
    if nat["tool_call"] and nat["final"]:
        out["tool_transport"] = "native"
        return out
    txt = _ping_test(Client(endpoint, model_id, max_tokens=max_tokens, transport="text", api_key=api_key), token)
    out["text"] = txt
    if txt["tool_call"] and txt["final"]:
        out["tool_transport"] = "text"
    return out

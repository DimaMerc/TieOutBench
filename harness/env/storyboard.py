"""harness/env/storyboard.py — the video pack: an episode -> replay text, storyboard JSON, PNG cards.

Phase 2 is built to be explained on screen. A tools-arm episode is a sequence of visible steps
(list, read, query the position as of a date, calculate, book), and a checker-arm episode adds a
verdict. This module turns the saved transcript into three things a video edit can use directly:

  replay.md         every step in order, one line per tool call and result, quotes verbatim
  storyboard.json   scenes with on-screen lines and default durations, in the order the video
                    would show them: the episode card, one card per step, the ledger, the
                    worksheet-versus-ledger check, the grade, the review round(s), the verdict cell
  cards/*.png       one 1920x1080 card per scene in the house style (white, navy, the accent only
                    on the failure line), rendered with PIL from the saved artifacts

Every number on a card comes from the saved run; the generator never invents a figure. Cards for
scripted (oracle or planted) trajectories carry the label SCRIPTED, NOT A MODEL RUN so they can
be used to explain the mechanism without being mistaken for evidence.
"""
from __future__ import annotations
import json
import os
import textwrap

from .state import Episode
from .scoring import score_episode
from .ledger import ledger_table

BG, NAVY, MUTE, LINE = "#FFFFFF", "#16243B", "#6B7785", "#C9D3DE"
GREEN, RED, ACC, BLUE = "#2E7D5B", "#C0392B", "#FF6B5E", "#2A78D6"
W, H = 1920, 1080
FONT_DIR = r"C:\Windows\Fonts"


def _font(size: int, bold: bool = False):
    try:
        from PIL import ImageFont
    except ImportError:                                  # pragma: no cover
        return None
    for name in (("arialbd.ttf" if bold else "arial.ttf"), "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"):
        p = os.path.join(FONT_DIR, name)
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except OSError:
                continue
    try:
        return ImageFont.load_default(size)
    except TypeError:
        return ImageFont.load_default()


def _short(v, n=90) -> str:
    s = json.dumps(v, default=str, ensure_ascii=False) if not isinstance(v, str) else v
    return s if len(s) <= n else s[: n - 3] + "..."


def _money(n) -> str:
    try:
        return f"${float(n):,.2f}"
    except (TypeError, ValueError):
        return str(n)


def summarize_call(name: str, args: dict) -> str:
    a = args or {}
    if name == "list_documents":
        return "list_documents()"
    if name == "read_document":
        return f"read_document({a.get('doc_id')})"
    if name == "get_position":
        return f"get_position({a.get('account')}, as of {a.get('as_of')})"
    if name == "calculate":
        return f"calculate({a.get('expression')})"
    if name == "book_receivable":
        return (f"book_receivable({_money(a.get('amount'))}, pay {a.get('pay_date')}, basis {a.get('basis_doc')}"
                + (f", {a.get('shares')} shares" if a.get("shares") is not None else "") + ")")
    if name == "update_pcf":
        return f"update_pcf({a.get('ticker')} -> {a.get('quantity_per_cu')} per creation unit, basis {a.get('basis_doc')})"
    if name == "confirm_position":
        return f"confirm_position({a.get('shares')} {a.get('ticker')} as of {a.get('as_of')})"
    if name == "submit_election":
        return f"submit_election({a.get('option')}, {a.get('shares')} shares)"
    if name == "escalate":
        return f"escalate(missing: {_short(a.get('missing_document'), 60)}; hold: {_short(a.get('held_action'), 70)})"
    if name == "submit_worksheet":
        return "submit_worksheet(...)"
    if name == "review_verdict":
        return f"review_verdict({a.get('verdict')}, {len(a.get('findings') or [])} finding(s))"
    return f"{name}({_short(a, 80)})"


def summarize_result(name: str, res: dict) -> str:
    r = res or {}
    if "error" in r:
        return f"ERROR: {_short(r['error'], 110)}"
    if name == "list_documents":
        ids = [d.get("doc_id") for d in r.get("documents") or []]
        return f"{len(ids)} documents: " + ", ".join(ids)
    if name == "read_document":
        return f"{r.get('doc_id')} ({r.get('type')}, {r.get('date')})"
    if name == "get_position":
        s = f"{r.get('settled_shares'):,.0f} shares, {r.get('basis')} (position row {r.get('position_row_as_of')})"
        if r.get("tendered_shares") is not None:
            s += f"; tendered {r.get('tendered_shares'):,.0f}"
        return s
    if name == "calculate":
        return f"= {r.get('result_text')}"
    if name == "book_receivable":
        b = r.get("booked") or {}
        return f"{r.get('entry_id')} booked {_money(b.get('amount'))} for {b.get('pay_date')} on {b.get('basis_doc')}"
    if name == "update_pcf":
        p = r.get("pcf_line") or {}
        return f"{r.get('entry_id')} PCF line: {p.get('quantity_per_cu')} per creation unit"
    if name == "confirm_position":
        c = r.get("confirmed") or {}
        return f"{r.get('entry_id')} confirmed {c.get('shares')} as of {c.get('as_of')}"
    if name == "submit_election":
        return f"{r.get('entry_id')} accepted by the tool; judged afterwards"
    if name == "escalate":
        return f"{r.get('entry_id')} escalation recorded"
    if name == "submit_worksheet":
        return f"worksheet submitted; episode ended ({r.get('ledger_entries')} ledger entries)"
    if name == "review_verdict":
        return f"verdict {r.get('verdict')} recorded"
    return _short(r, 110)


def replay_lines(ep: Episode) -> list[str]:
    L = []
    pending = {}
    for e in ep.transcript:
        k, ag, rd = e.get("kind"), e.get("agent", "maker"), e.get("round", 1)
        tag = f"[{ag} r{rd}]"
        if k == "assistant" and (e.get("content") or "").strip() and not e.get("scripted"):
            L.append(f'{tag} says: "{_short(e["content"].strip(), 240)}"')
        elif k == "tool_call":
            pending[e.get("call_id")] = e
            L.append(f"{tag} -> {summarize_call(e.get('name'), e.get('arguments'))}")
        elif k == "tool_result":
            L.append(f"{tag} <- {summarize_result(e.get('name'), e.get('result'))}")
        elif k == "review_end":
            L.append(f"{tag} VERDICT: {e.get('verdict')}" + "".join(f"\n    - {f}" for f in e.get("findings") or []))
        elif k == "note":
            L.append(f"{tag} note: {e.get('text')}")
        elif k == "user" and e.get("note"):
            L.append(f"{tag} {e.get('note')}: {_short(e.get('content') or '', 160)}")
        elif k == "episode_end":
            L.append(f"{tag} episode ended: {e.get('reason')}" + (" (INCOMPLETE)" if e.get("incomplete") else ""))
    return L


def build_storyboard(ep: Episode, scored: dict) -> dict:
    case = ep.case
    scripted = str(ep.model_id or "").startswith(("oracle", "planted:", "gaming"))
    label = "SCRIPTED, NOT A MODEL RUN" if scripted else (ep.model_id or "model")
    scenes = [{"id": "episode", "kind": "title",
               "title": f"{case.get('case_id')} · arm: {ep.arm}",
               "lines": [f"as of {ep.clock}", (case.get("episode") or {}).get("task", ""), f"run: {label}"],
               "duration_s": 4}]
    steps, i = [], 0
    pairs = []
    calls = {}
    for e in ep.transcript:
        if e.get("kind") == "tool_call":
            calls[e.get("seq")] = e
            pairs.append([e, None])
        elif e.get("kind") == "tool_result" and pairs and pairs[-1][1] is None:
            pairs[-1][1] = e
    for c, r in pairs:
        i += 1
        ag, rd = c.get("agent", "maker"), c.get("round", 1)
        title = f"{i}. {c.get('name')}" + (f"  ({ag}, round {rd})" if ag != "maker" or rd != 1 else "")
        lines = [summarize_call(c.get("name"), c.get("arguments")),
                 summarize_result(c.get("name"), (r or {}).get("result")) if r else "(no result recorded)"]
        bad = bool(r) and not r.get("ok")
        steps.append({"id": f"step-{i}", "kind": "step", "agent": ag, "round": rd, "tool": c.get("name"),
                      "title": title, "lines": lines, "error": bad, "duration_s": 3})
    scenes += steps
    scenes.append({"id": "ledger", "kind": "ledger", "title": "The ledger (what was booked)",
                   "lines": ledger_table(ep.active_ledger()).split("\n"), "duration_s": 5})
    led = scored["ledger"]
    cons = [f"{c['entry']}: booked {c.get('booked')} vs worksheet {c.get('worksheet')} -> {'ties' if c['ok'] else 'DOES NOT TIE'}"
            for c in led["consistency"]] or ["no amount to compare"]
    scenes.append({"id": "tieout", "kind": "check", "title": "Does the worksheet tie to the ledger?",
                   "lines": cons + [f"GATE.ELECT on the ledger: {'yes' if led['elect_fired'] else 'no'}",
                                    f"flags: {', '.join(led['flags']) or 'none'}"],
                   "ok": led["correct"], "duration_s": 5})
    t, w = scored["terminal"], scored["worksheet"]
    scenes.append({"id": "grade", "kind": "grade", "title": "The grade",
                   "lines": [f"worksheet: {w['gated']:.3f} gated, AllPass {w['allpass']}, gates {', '.join(w['gates']) or 'none'}",
                             f"terminal state: {t['gated']:.3f} gated, AllPass {t['allpass']}, gates {', '.join(t['gates']) or 'none'}",
                             f"flags: {', '.join(t['flags']) or 'none'}"],
                   "ok": t["allpass"] == 1, "duration_s": 5})
    if scored.get("review"):
        for r in scored["review"]["rounds"]:
            rt = (scored["trajectory"].get("reviewer") or {}).get(str(r.get("round")), {})
            lines = [f"verdict: {str(r.get('verdict')).upper()}",
                     f"the ledger it was shown was {'correct' if r.get('ledger_shown_correct') else 'WRONG'}",
                     f"the reviewer {'recomputed' if rt.get('recomputed') else 'only read'} "
                     f"({', '.join(f'{k} x{v}' for k, v in (rt.get('tool_counts') or {}).items()) or 'no tools'})"]
            lines += [f"- {f}" for f in (r.get("findings") or [])[:4]]
            cell = ("caught" if (r.get("verdict") == "reject" and not r.get("ledger_shown_correct")) else
                    "approved a wrong ledger" if (r.get("verdict") == "approve" and not r.get("ledger_shown_correct")) else
                    "approved a correct ledger" if r.get("verdict") == "approve" else "rejected a correct ledger")
            scenes.append({"id": f"review-{r.get('round')}", "kind": "review", "title": f"The checker, round {r.get('round')}: {cell}",
                           "lines": lines, "ok": cell in ("caught", "approved a correct ledger"), "cell": cell, "duration_s": 6})
    scenes.append({"id": "closing", "kind": "title", "title": "Does it tie out?",
                   "lines": ["TieOutBench · evals.finance", "eval #6, phase 2: the agent environment"], "duration_s": 3})
    return {"case_id": case.get("case_id"), "arm": ep.arm, "model_id": ep.model_id, "scripted": scripted,
            "total_s": sum(s["duration_s"] for s in scenes), "scenes": scenes}


def _wrap(s: str, width: int) -> list[str]:
    out = []
    for part in str(s).split("\n"):
        out += textwrap.wrap(part, width=width) or [""]
    return out


def render_cards(story: dict, outdir: str) -> list[str]:
    try:
        from PIL import Image, ImageDraw
    except ImportError:                                  # pragma: no cover
        return []
    os.makedirs(outdir, exist_ok=True)
    f_title, f_body, f_small, f_mono = _font(56, True), _font(36), _font(26), _font(32)
    written = []
    for n, sc in enumerate(story["scenes"], 1):
        img = Image.new("RGB", (W, H), BG)
        d = ImageDraw.Draw(img)
        ok = sc.get("ok")
        accent = NAVY if ok is None else (GREEN if ok else RED)
        d.rectangle([0, 0, W, 14], fill=accent)
        d.text((110, 90), sc["title"], fill=NAVY, font=f_title)
        d.line([110, 175, W - 110, 175], fill=LINE, width=3)
        y = 215
        body_font = f_mono if sc["kind"] in ("ledger", "step") else f_body
        width = 78 if body_font is f_mono else 70
        for line in sc.get("lines") or []:
            color = NAVY
            if sc["kind"] == "step" and line.startswith("ERROR"):
                color = RED
            if sc["kind"] == "check" and "DOES NOT TIE" in line:
                color = RED
            for w in _wrap(line, width):
                if y > H - 160:
                    break
                d.text((110, y), w, fill=color, font=body_font)
                y += 48
            y += 12
        if story.get("scripted"):
            d.text((110, H - 130), "SCRIPTED TRAJECTORY, NOT A MODEL RUN", fill=ACC, font=f_small)
        d.text((110, H - 80), f"TieOutBench · evals.finance · {story['case_id']} · arm {story['arm']}", fill=MUTE, font=f_small)
        d.text((W - 110 - 120, H - 80), f"{n}/{len(story['scenes'])}", fill=MUTE, font=f_small)
        p = os.path.join(outdir, f"{n:02d}-{sc['id']}.png")
        img.save(p)
        written.append(p)
    return written


def write_pack(episode_dir: str, out_dir: str | None = None, *, ep: Episode | None = None,
               scored: dict | None = None, cards: bool = True) -> dict:
    """replay.md + storyboard.json (+ cards/) for one saved episode directory."""
    if ep is None:
        ep = Episode.load(episode_dir)
    if scored is None:
        scored = score_episode(ep)
    out_dir = out_dir or episode_dir
    os.makedirs(out_dir, exist_ok=True)
    story = build_storyboard(ep, scored)
    rp = os.path.join(out_dir, "replay.md")
    with open(rp, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(f"# Replay: {story['case_id']} · arm {story['arm']} · {ep.model_id or 'n/a'}\n\n")
        if story["scripted"]:
            fh.write("SCRIPTED TRAJECTORY, NOT A MODEL RUN.\n\n")
        fh.write("\n".join(replay_lines(ep)) + "\n")
    sp = os.path.join(out_dir, "storyboard.json")
    with open(sp, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(story, fh, indent=2, ensure_ascii=False, default=str)
    paths = {"replay": rp, "storyboard": sp, "cards": []}
    if cards:
        paths["cards"] = render_cards(story, os.path.join(out_dir, "cards"))
    return paths

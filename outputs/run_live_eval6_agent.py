#!/usr/bin/env python3
"""
outputs/run_live_eval6_agent.py — drive a REAL model through the eval-6 Phase-2 agent environment
(design: workflow/DESIGN-phase2-agent-environment.md) and save every artifact.

  # the tools arm, one case
  python outputs/run_live_eval6_agent.py --arm tools --model-id claude-sonnet-4-6 \
      --endpoint https://api.anthropic.com/v1 --case bry-dividend-2024

  # the checker arm on every case, reusing the saved tools-arm maker (the default) so the reviewer
  # reviews exactly the work product the tools arm was graded on
  python outputs/run_live_eval6_agent.py --arm checker --model-id gpt-5.4-mini --all-cases

  # repeatability: three more runs per cell on the corrected dividend
  python outputs/run_live_eval6_agent.py --arm tools --model-id gemini-3.6-flash --case bry-dividend-2024 --repeat 3

  # only the per-endpoint conformance test (a tool call, a tool reply, a final answer)
  python outputs/run_live_eval6_agent.py --arm tools --model-id gpt-5.5 --conformance-only

Before the first graded run of a model the conformance test runs once and is saved under
outputs/eval6-agent/conformance/<model>.json; it decides the transport (native function calling,
or the text protocol when the endpoint cannot do native), which run.json records and the
leaderboard discloses. The endpoint is inferred from the model name when omitted (claude ->
api.anthropic.com, gpt -> api.openai.com, gemini -> generativelanguage.googleapis.com), and the key
is resolved from the endpoint (ANTHROPIC_API_KEY / OPENAI_API_KEY / GEMINI_API_KEY, environment or
the gitignored repo-root .env). Budgets follow Phase 1: Claude 8k per turn on the compat endpoint,
GPT and Gemini 32k. Prior artifacts are moved to prior/<run_id>/, never overwritten.

Saves under outputs/eval6-agent/<arm>/<model>/<case>/ (repeat runs under
outputs/eval6-agent/repeat/<arm>/<model>/<case>/r<n>/): transcript.jsonl, ledger.json,
answer.json (the worksheet), terminal.json (worksheet + ledger rows, the graded object),
report.txt, run.json, messages.json (the maker's conversation, for the checker arm), review.json
(checker arm), replay.md and storyboard.json (the video pack).
"""
from __future__ import annotations
import argparse
import glob
import json
import os
import shutil
import sys
import time
import traceback

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
for _s in (sys.stdout, sys.stderr):           # model text may carry characters a cp1252 console cannot print
    try:
        _s.reconfigure(errors="replace")
    except (AttributeError, ValueError):
        pass

from harness.rubric import load_case, rubric_path_for                                   # noqa: E402
from harness.live import resolve_key, _host_of                                          # noqa: E402
from harness.run_record import (new_run_id, preserve_prior, rel, sha256_file, git_head_short,      # noqa: E402
                                git_harness_dirty, harness_hashes, write_run_record)
from harness.suites import corporate_actions as _ca                                     # noqa: E402
from harness.env import Episode, score_episode, render_episode_report                  # noqa: E402
from harness.env import state as _state, scoring as _scoring, agent as _agent, transport as _transport  # noqa: E402
from harness.env.transport import Client, conformance, default_budget                   # noqa: E402
from harness.env.agent import run_maker, run_checker                                    # noqa: E402
from harness.env.storyboard import write_pack                                           # noqa: E402

OUT_ROOT = os.path.join(REPO, "outputs", "eval6-agent")
ENDPOINTS = {"claude": "https://api.anthropic.com/v1", "gpt": "https://api.openai.com/v1",
             "gemini": "https://generativelanguage.googleapis.com/v1beta/openai"}
CASE_ORDER = ["bry-dividend-2024", "zts-dividend-2014", "mnst-tender-2024", "mnst-tender-2024-oddlot",
              "mega-split-2024", "mega-split-2024-clean"]
ENV_ARTIFACTS = ("transcript.jsonl", "ledger.json", "terminal.json", "messages.json", "review.json",
                 "replay.md", "storyboard.json")


def infer_endpoint(model_id: str) -> str:
    for k, v in ENDPOINTS.items():
        if model_id.lower().startswith(k):
            return v
    raise SystemExit(f"cannot infer the endpoint for {model_id!r}; pass --endpoint")


def _preserve(outdir: str):
    prior = preserve_prior(outdir)
    extra = [os.path.join(outdir, n) for n in ENV_ARTIFACTS if os.path.exists(os.path.join(outdir, n))]
    cards = os.path.join(outdir, "cards")
    if extra or os.path.isdir(cards):
        if prior is None:
            prior = os.path.join(outdir, "prior", "mtime-" + time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()))
            os.makedirs(prior, exist_ok=True)
        for f in extra:
            shutil.move(f, os.path.join(prior, os.path.basename(f)))
        if os.path.isdir(cards):
            shutil.move(cards, os.path.join(prior, "cards"))
    return prior


def _conformance_record(model_id: str, endpoint: str, key: str, *, force: bool, max_tokens: int | None) -> dict:
    cdir = os.path.join(OUT_ROOT, "conformance")
    os.makedirs(cdir, exist_ok=True)
    p = os.path.join(cdir, model_id.replace("/", "_") + ".json")
    if os.path.exists(p) and not force:
        with open(p, encoding="utf-8") as fh:
            rec = json.load(fh)
        if rec.get("endpoint") == _host_of(endpoint):
            print(f"[agent] conformance: reusing {rel(p)} -> transport={rec.get('tool_transport')}")
            return rec
    print(f"[agent] conformance test for {model_id} @ {_host_of(endpoint)} ...")
    rec = conformance(endpoint, model_id, api_key=key, max_tokens=max_tokens)
    with open(p, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(rec, fh, indent=2)
    print(f"[agent] conformance: native={rec['native']}  text={rec['text']}  -> transport={rec['tool_transport']}  "
          f"(saved {rel(p)})")
    return rec


def _record(outdir: str, ep: Episode, scored: dict, *, run_id: str, arm: str, model_id: str, endpoint: str,
            client: Client, conf: dict, loop: dict, prior, reuse_from: str | None, failed: str | None = None,
            reviewer: dict | None = None):
    case_path = ep.case_path
    st = {}
    for e in reversed(ep.transcript):
        if e.get("kind") == "assistant" and e.get("usage") is not None:
            st = e
            break
    fields = {
        "arm": arm, "suite": "corporate-actions", "model_id": model_id, "endpoint": _host_of(endpoint),
        "request": {"max_tokens": client.max_tokens, "temperature": client.temperature, "stream": False,
                    "tool_transport": client.transport, "max_turns": _agent.MAX_TURNS, "deadline_s": _agent.DEADLINE_S},
        "conformance": {"tool_transport": conf.get("tool_transport"), "tested_at": conf.get("tested_at")},
        "loop": loop,
        "usage_total": dict(client.usage_total), "chat_calls": client.calls_made,
        "transient_retries": client.transient_retries,
        "last_finish_reason": st.get("finish_reason"),
        "incomplete": not ep.submitted,
        "reused_maker_from": reuse_from,
        "reviewer": reviewer or ({"model_id": model_id, "self_review": True} if arm.startswith("checker") else None),
        "case": {"case_id": ep.case.get("case_id"), "path": rel(case_path), "sha256": sha256_file(case_path)},
        "rubric": {"path": rel(rubric_path_for(ep.case)), "sha256": sha256_file(rubric_path_for(ep.case))},
        "grader_version": git_head_short(), "grader_tree_dirty": git_harness_dirty(),
        "harness_hashes": harness_hashes(_ca, _state, _scoring, _agent, _transport),
        "prior_dir": rel(prior) if prior else None,
    }
    if scored is not None:
        fields["score"] = {"worksheet": {k: scored["worksheet"][k] for k in ("gated", "ungated", "gap", "allpass", "gates", "flags")},
                           "terminal": {k: scored["terminal"][k] for k in ("gated", "ungated", "gap", "allpass", "gates", "flags")},
                           "ledger": {k: scored["ledger"][k] for k in ("correct", "elect_fired", "gold_ok", "flags", "n_booked")},
                           "trajectory": {k: scored["trajectory"]["maker"][k] for k in
                                          ("n_turns", "n_tool_calls", "n_tool_errors", "governing_read_before_first_action",
                                           "position_dates_queried", "basis_date_queried", "superseded_date_queried",
                                           "calculate_used")},
                           "review": ({"rounds": [{k: r.get(k) for k in ("round", "verdict", "ledger_shown_correct", "incomplete")}
                                                  for r in scored["review"]["rounds"]],
                                       "recomputed": scored["review"]["recomputed"]} if scored.get("review") else None)}
    if failed:
        fields["failed"] = failed
    write_run_record(outdir, run_id=run_id, **fields)


def run_plain_cell(*, model_id: str, endpoint: str, key: str, case_id: str, max_tokens: int, outdir: str) -> dict:
    """the plain arm (the Phase-1 single-prompt form) for the repeatability runs only: the same
    packet, prompt and budget as outputs/run_live_eval6.py, written under repeat/plain/ so the
    committed Phase-1 cells under outputs/eval6-live/ are never touched."""
    from harness import run_case, live_corporate_actions as lca
    from harness.report import render
    from harness.run_record import run_fields, unclobbered
    case_path = os.path.join(REPO, "cases", case_id + ".case.yaml")
    case = load_case(case_path)
    run_id = new_run_id()
    os.makedirs(outdir, exist_ok=True)
    t0 = time.monotonic()
    print(f"[agent] plain {model_id} {case_id}: building the document-store packet ...")
    try:
        ans = lca.answer(case, endpoint=endpoint, model_id=model_id, max_tokens=max_tokens, api_key=key)
    except Exception as e:
        raw = getattr(e, "raw", "")
        if raw:
            with open(unclobbered(os.path.join(outdir, "raw_FAILED.txt"), run_id), "w", encoding="utf-8") as fh:
                fh.write(raw)
        write_run_record(outdir, run_id=run_id, arm="plain", model_id=model_id, endpoint=_host_of(endpoint),
                         case={"case_id": case_id, "path": rel(case_path), "sha256": sha256_file(case_path)},
                         failed=f"{type(e).__name__}: {e}")
        print(f"[agent] plain FAILED: {e}")
        return {"outdir": outdir, "failed": str(e), "scored": None}
    prior = preserve_prior(outdir)
    with open(os.path.join(outdir, "raw.txt"), "w", encoding="utf-8") as fh:
        fh.write(ans.get("_raw", ""))
    clean = {k: v for k, v in ans.items() if not k.startswith("_")}
    with open(os.path.join(outdir, "answer.json"), "w", encoding="utf-8") as fh:
        json.dump(clean, fh, indent=2, default=str)
    result, rubric = run_case(case_path, model_output=ans, mode="mock")
    report = render(result, rubric, variant=f"plain:{model_id}", mode="mock")
    with open(os.path.join(outdir, "report.txt"), "w", encoding="utf-8") as fh:
        fh.write(report)
    write_run_record(outdir, **run_fields(ans, case_path=case_path, case=case, live_module=lca, judge="mock",
                                         run_id=run_id, model_id=model_id),
                     arm="plain", prior_dir=rel(prior) if prior else None,
                     score={"gated": result.case_gated, "ungated": result.case_ungated, "gap": result.gap,
                            "allpass": result.allpass, "gates": result.fired_gates, "flags": result.flags})
    st = ans.get("_stats") or {}
    print(f"[agent] plain {model_id} {case_id}: gated={result.case_gated:.3f} AllPass={result.allpass} "
          f"gates={result.fired_gates} finish={st.get('finish_reason')} {round(time.monotonic() - t0, 1)}s")
    print(f"[agent] artifacts -> {rel(outdir)}")
    return {"outdir": outdir, "failed": None, "scored": {"terminal": {"gated": result.case_gated}}}


def run_cell(*, arm: str, model_id: str, endpoint: str, key: str, case_id: str, conf: dict, transport: str,
             max_tokens: int | None, outdir: str, reuse_maker: bool, judge_pack: bool = True,
             reuse_dir: str | None = None, reviewer: dict | None = None) -> dict:
    """one cell. `reviewer` (checker arm only) = {model_id, endpoint, key, transport, max_tokens} for a
    FIXED reviewer of a different model; None means the maker's own model reviews (self-review)."""
    case_path = os.path.join(REPO, "cases", case_id + ".case.yaml")
    load_case(case_path)
    run_id = new_run_id()
    client = Client(endpoint, model_id, max_tokens=max_tokens, transport=transport, api_key=key)
    rclient = client
    if reviewer:
        rclient = Client(reviewer["endpoint"], reviewer["model_id"], max_tokens=reviewer.get("max_tokens"),
                         transport=reviewer["transport"], api_key=reviewer.get("key"))
    arm_label = "checker-fixed" if (arm == "checker" and reviewer) else arm
    ep = Episode(case_path, arm=arm_label, model_id=model_id)
    reuse_from, maker_state, loop = None, None, {}
    t0 = time.monotonic()
    if arm == "checker" and reuse_maker:
        src = reuse_dir or os.path.join(OUT_ROOT, "tools", model_id.replace("/", "_"), case_id)
        mp = os.path.join(src, "messages.json")
        if os.path.exists(mp) and os.path.exists(os.path.join(src, "transcript.jsonl")):
            ep = Episode.load(src, case_path)
            ep.arm, ep.model_id = arm_label, model_id
            with open(mp, encoding="utf-8") as fh:
                msgs = json.load(fh)
            with open(os.path.join(src, "run.json"), encoding="utf-8") as fh:
                srun = json.load(fh)
            if srun.get("request", {}).get("tool_transport") != transport:
                print(f"[agent] NOTE: the saved maker used transport={srun.get('request', {}).get('tool_transport')}; "
                      f"this run uses {transport}; the maker is re-run instead of reused")
            else:
                maker_state = {"messages": msgs, "turns": (srun.get("loop") or {}).get("turns"),
                               "incomplete": bool(srun.get("incomplete")), "ended_by": (srun.get("loop") or {}).get("ended_by")}
                reuse_from = rel(src)
                print(f"[agent] reusing the tools-arm maker from {reuse_from} (run {srun.get('run_id')})")
    os.makedirs(outdir, exist_ok=True)
    failed = None
    try:
        if arm == "tools":
            m = run_maker(ep, client)
            loop = {k: m.get(k) for k in ("turns", "incomplete", "ended_by", "elapsed_s")}
            with open(os.path.join(outdir, "messages.json.tmp"), "w", encoding="utf-8", newline="\n") as fh:
                json.dump(m["messages"], fh, indent=1, ensure_ascii=False, default=str)
        else:
            c = run_checker(ep, client, rclient, maker_state=maker_state)
            loop = c
    except Exception as e:
        failed = f"{type(e).__name__}: {e}"
        traceback.print_exc()
    prior = _preserve(outdir)
    tmp = os.path.join(outdir, "messages.json.tmp")
    if os.path.exists(tmp):
        os.replace(tmp, os.path.join(outdir, "messages.json"))
    elif arm == "checker" and maker_state is not None:
        with open(os.path.join(outdir, "messages.json"), "w", encoding="utf-8", newline="\n") as fh:
            json.dump(maker_state["messages"], fh, indent=1, ensure_ascii=False, default=str)
    ep.save(outdir)
    scored = None
    try:
        scored = score_episode(ep)
        with open(os.path.join(outdir, "terminal.json"), "w", encoding="utf-8", newline="\n") as fh:
            json.dump(scored["terminal_answer"], fh, indent=2, default=str)
        report = render_episode_report(ep, scored)
        with open(os.path.join(outdir, "report.txt"), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(report)
        print(report)
        if judge_pack:
            write_pack(outdir, ep=ep, scored=scored, cards=False)
    except Exception as e:
        failed = (failed + "; " if failed else "") + f"scoring failed: {type(e).__name__}: {e}"
        traceback.print_exc()
    _record(outdir, ep, scored, run_id=run_id, arm=arm_label, model_id=model_id, endpoint=endpoint, client=client,
            conf=conf, loop=loop, prior=prior, reuse_from=reuse_from, failed=failed,
            reviewer=({"model_id": reviewer["model_id"], "endpoint": _host_of(reviewer["endpoint"]),
                       "tool_transport": reviewer["transport"], "max_tokens": rclient.max_tokens,
                       "usage_total": dict(rclient.usage_total), "chat_calls": rclient.calls_made,
                       "transient_retries": rclient.transient_retries} if reviewer else None))
    el = round(time.monotonic() - t0, 1)
    if scored:
        t, w, l = scored["terminal"], scored["worksheet"], scored["ledger"]
        line = (f"[agent] {model_id} {arm} {case_id}: terminal gated={t['gated']:.3f} AllPass={t['allpass']} gates={t['gates']} "
                f"flags={t['flags']} | worksheet gated={w['gated']:.3f} | ledger correct={l['correct']} | "
                f"turns={scored['trajectory']['maker']['n_turns']} tools={scored['trajectory']['maker']['n_tool_calls']} "
                f"usage={client.usage_total} transport={transport} {el}s")
        if scored.get("review"):
            line += f" | review {[(r['round'], r['verdict'], r['ledger_shown_correct']) for r in scored['review']['rounds']]}"
            if reviewer:
                line += f" | reviewer={reviewer['model_id']} usage={rclient.usage_total}"
        print(line)
    print(f"[agent] artifacts -> {rel(outdir)}" + (f"  FAILED: {failed}" if failed else ""))
    return {"outdir": outdir, "failed": failed, "scored": scored}


def rescore_all() -> int:
    """re-score every saved agent cell from its artifacts after a grader change: rewrites report.txt,
    terminal.json, replay.md and storyboard.json, and updates run.json's `score` (the score at run
    time is kept once as `score_at_run`). Prints the cells whose terminal grade moved."""
    moved, n = [], 0
    dirs = []
    for arm in ("tools", "checker", "checker-fixed"):
        dirs += glob.glob(os.path.join(OUT_ROOT, arm, "*", "*")) + glob.glob(os.path.join(OUT_ROOT, "repeat", arm, "*", "*", "r*"))
    for d in sorted(dirs):
        rj = os.path.join(d, "run.json")
        if not os.path.exists(os.path.join(d, "transcript.jsonl")) or not os.path.exists(rj):
            continue
        with open(rj, encoding="utf-8") as fh:
            run = json.load(fh)
        if run.get("failed"):
            continue
        case_id = (run.get("case") or {}).get("case_id") or os.path.basename(d.rstrip("/\\"))
        case_path = os.path.join(REPO, "cases", case_id + ".case.yaml")
        ep = Episode.load(d, case_path)
        scored = score_episode(ep)
        n += 1
        with open(os.path.join(d, "terminal.json"), "w", encoding="utf-8", newline="\n") as fh:
            json.dump(scored["terminal_answer"], fh, indent=2, default=str)
        with open(os.path.join(d, "report.txt"), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(render_episode_report(ep, scored))
        write_pack(d, ep=ep, scored=scored, cards=False)
        new = {"worksheet": {k: scored["worksheet"][k] for k in ("gated", "ungated", "gap", "allpass", "gates", "flags")},
               "terminal": {k: scored["terminal"][k] for k in ("gated", "ungated", "gap", "allpass", "gates", "flags")},
               "ledger": {k: scored["ledger"][k] for k in ("correct", "elect_fired", "gold_ok", "flags", "n_booked")},
               "review": ({"rounds": [{k: r.get(k) for k in ("round", "verdict", "ledger_shown_correct", "incomplete")}
                                      for r in scored["review"]["rounds"]],
                           "recomputed": scored["review"]["recomputed"]} if scored.get("review") else None)}
        old = run.get("score") or {}
        if "score_at_run" not in run:
            run["score_at_run"] = old
        if (old.get("terminal") or {}).get("gated") != new["terminal"]["gated"] or (old.get("terminal") or {}).get("flags") != new["terminal"]["flags"]:
            moved.append((rel(d), (old.get("terminal") or {}).get("gated"), new["terminal"]["gated"],
                          (old.get("terminal") or {}).get("flags"), new["terminal"]["flags"]))
        run["score"] = new
        run["rescored_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        run["grader_version_rescore"] = git_head_short()
        with open(rj, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(run, fh, indent=2, default=str)
            fh.write("\n")
    print(f"[agent] rescored {n} cells; {len(moved)} moved:")
    for m in moved:
        print(f"  {m[0]}: {m[1]} -> {m[2]}  flags {m[3]} -> {m[4]}")
    return len(moved)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rescore", action="store_true", help="re-score every saved cell from its artifacts (no model calls)")
    ap.add_argument("--arm", default=None, choices=["tools", "checker", "plain"],
                    help="plain is for --repeat only (the Phase-1 form, written under repeat/plain/)")
    ap.add_argument("--skip-existing", action="store_true",
                    help="--all-cases: skip a cell whose run.json exists and records no failure")
    ap.add_argument("--model-id", default=None)
    ap.add_argument("--endpoint", default=None, help="inferred from the model name when omitted")
    ap.add_argument("--case", default=None, help="one case id (default: bry-dividend-2024)")
    ap.add_argument("--all-cases", action="store_true", help="all six cases, dividends first")
    ap.add_argument("--repeat", type=int, default=0, help="N extra runs into repeat/<arm>/<model>/<case>/r<n>/")
    ap.add_argument("--transport", default="auto", choices=["auto", "native", "text"])
    ap.add_argument("--max-tokens", type=int, default=None, help="per-turn budget (default: Claude 8k, others 32k)")
    ap.add_argument("--conformance-only", action="store_true")
    ap.add_argument("--reconform", action="store_true", help="re-run the conformance test even if saved")
    ap.add_argument("--no-reuse-maker", action="store_true", help="checker arm: run a fresh maker instead of reusing the tools arm's")
    ap.add_argument("--reviewer-model", default=None,
                    help="checker arm: a FIXED reviewer of this model instead of self-review; cells go under checker-fixed/")
    ap.add_argument("--reviewer-endpoint", default=None, help="inferred from the reviewer model name when omitted")
    ap.add_argument("--key-env", default=None)
    a = ap.parse_args()
    if a.rescore:
        rescore_all()
        return
    if not a.arm or not a.model_id:
        ap.error("--arm and --model-id are required (or --rescore)")

    endpoint = a.endpoint or infer_endpoint(a.model_id)
    key = os.environ.get(a.key_env) if a.key_env else resolve_key(endpoint)
    if not key and "localhost" not in endpoint:
        print("[agent] no API key for this endpoint (see .env.example)")
        sys.exit(2)
    max_tokens = a.max_tokens or default_budget(endpoint)
    if a.arm == "plain":
        if not a.repeat:
            print("[agent] --arm plain is for --repeat only; the canonical plain cells are outputs/eval6-live/")
            sys.exit(2)
        results = []
        for cid in (CASE_ORDER if a.all_cases else [a.case or "bry-dividend-2024"]):
            mdir = os.path.join(OUT_ROOT, "repeat", "plain", a.model_id.replace("/", "_"), cid)
            existing = len(glob.glob(os.path.join(mdir, "r*")))
            for n in range(existing + 1, existing + 1 + a.repeat):
                results.append(run_plain_cell(model_id=a.model_id, endpoint=endpoint, key=key, case_id=cid,
                                              max_tokens=max_tokens, outdir=os.path.join(mdir, f"r{n}")))
        bad = [r for r in results if r["failed"]]
        print(f"\n[agent] {len(results) - len(bad)}/{len(results)} plain repeat cells completed")
        sys.exit(1 if bad else 0)
    conf = _conformance_record(a.model_id, endpoint, key, force=a.reconform, max_tokens=max_tokens)
    if a.conformance_only:
        return
    transport = a.transport if a.transport != "auto" else conf.get("tool_transport")
    if not transport:
        print(f"[agent] {a.model_id} passed neither the native nor the text conformance test; not running")
        sys.exit(1)
    reviewer = None
    arm_dir = a.arm
    if a.reviewer_model:
        if a.arm != "checker":
            ap.error("--reviewer-model applies to --arm checker")
        rend = a.reviewer_endpoint or infer_endpoint(a.reviewer_model)
        rkey = resolve_key(rend)
        if not rkey and "localhost" not in rend:
            print("[agent] no API key for the reviewer's endpoint")
            sys.exit(2)
        rconf = _conformance_record(a.reviewer_model, rend, rkey, force=a.reconform, max_tokens=default_budget(rend))
        if not rconf.get("tool_transport"):
            print(f"[agent] reviewer {a.reviewer_model} passed neither conformance test; not running")
            sys.exit(1)
        reviewer = {"model_id": a.reviewer_model, "endpoint": rend, "key": rkey, "transport": rconf["tool_transport"],
                    "max_tokens": default_budget(rend)}
        arm_dir = "checker-fixed"
        print(f"[agent] fixed reviewer: {a.reviewer_model} @ {_host_of(rend)} (transport={reviewer['transport']}); cells under {arm_dir}/")
    cases = CASE_ORDER if a.all_cases else [a.case or "bry-dividend-2024"]
    results = []
    for cid in cases:
        base = os.path.join(OUT_ROOT, arm_dir, a.model_id.replace("/", "_"), cid)
        if a.repeat:
            mdir = os.path.join(OUT_ROOT, "repeat", arm_dir, a.model_id.replace("/", "_"), cid)
            existing = len(glob.glob(os.path.join(mdir, "r*")))
            for n in range(existing + 1, existing + 1 + a.repeat):
                outdir = os.path.join(mdir, f"r{n}")
                # a checker repeat pairs with the tools repeat of the same number when it exists,
                # so arm C's repeats are arm B's repeated work products plus a reviewer each
                pair = os.path.join(OUT_ROOT, "repeat", "tools", a.model_id.replace("/", "_"), cid, f"r{n}")
                reuse_dir = pair if (a.arm == "checker" and os.path.exists(os.path.join(pair, "messages.json"))) else None
                results.append(run_cell(arm=a.arm, model_id=a.model_id, endpoint=endpoint, key=key, case_id=cid, conf=conf,
                                        transport=transport, max_tokens=max_tokens, outdir=outdir,
                                        reuse_maker=not a.no_reuse_maker, reuse_dir=reuse_dir, reviewer=reviewer))
        else:
            rj = os.path.join(base, "run.json")
            if a.skip_existing and os.path.exists(rj):
                with open(rj, encoding="utf-8") as fh:
                    prev = json.load(fh)
                if not prev.get("failed"):
                    print(f"[agent] skipping existing cell {rel(base)} (run {prev.get('run_id')})")
                    continue
            results.append(run_cell(arm=a.arm, model_id=a.model_id, endpoint=endpoint, key=key, case_id=cid, conf=conf,
                                    transport=transport, max_tokens=max_tokens, outdir=base,
                                    reuse_maker=not a.no_reuse_maker, reviewer=reviewer))
    bad = [r for r in results if r["failed"]]
    print(f"\n[agent] {len(results) - len(bad)}/{len(results)} cells completed" + (f"; failed: {[rel(r['outdir']) for r in bad]}" if bad else ""))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()

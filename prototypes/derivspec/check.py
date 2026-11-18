"""A checking pass: a second reader says, for every answer field, whether the fund's documents settle it.

  python check.py <fund> <reader> drafts [--only <arm>:<drafter>] [--max-tokens N] [--force]
        the reader gets the documents, the scenarios and one colleague's draft (the first run of each cell:
        2 task wordings x 3 drafters = 6 drafts per fund), and gives a verdict for every answer field
  python check.py <fund> <reader> nodraft [--runs 1,2,3] [--max-tokens N] [--force]
        the same question from the documents and the scenarios alone, without a draft

fund = swap | options ; reader = one of the three models of the repository's grid.
Every call is recorded under data/out/checks/<fund>/<reader>/<arm>__<drafter>__run1/ or .../nodraft__run<k>/
(raw text, run record with the finish reason and token usage). A finished reading is not repeated unless --force
is given; a reading cut off at the token limit is moved to data/out/checks_prior/ and repeated once with twice the
limit. The reader is not told which model wrote the draft. Keys come from the repository's .env through
harness.live and are never printed.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))
from harness import live   # noqa: E402

import score_drafts as SD   # noqa: E402
from draft import BUDGET, GRID   # noqa: E402
from ds.funds import FUNDS   # noqa: E402

DRAFT_RUN = 1                     # the draft of each cell that is read
ARMS = ("plain", "ask")

SYSTEM = ("You are a senior reviewer at a fund administrator. You review processing requirements and test cases "
          "before the fund accounting team builds from them.")

INTRO = {
    True: """A client's exchange-traded fund is being set up on the fund accounting platform. {exposure} A colleague has drafted the processing requirements and the expected results of fifteen test scenarios. Below are (1) passages from the fund's public documents, (2) the scenarios with constructed positions, and (3) the colleague's draft.
""",
    False: """A client's exchange-traded fund is being set up on the fund accounting platform. {exposure} The expected results of fifteen test scenarios have to be worked out. Below are (1) passages from the fund's public documents and (2) the scenarios with constructed positions.
""",
}

TASK = """
TASK. For every answer field of every scenario, decide whether the fund's documents settle the answer:
"supported" - the passages, together with the figures given in the scenario, state everything needed to compute the answer; nothing has to be assumed or asked;
"not supported" - the answer depends on a rule, convention or term that the passages do not state. Say in a few words what is missing.
{judge} The positions and figures in the scenarios are constructed for this test and are to be taken as given.

Answer with one JSON object and nothing else:
{{"scenarios": {{"{first}": {{"<answer field>": {{"verdict": "supported" | "not supported", "missing": "<what the passages do not state, or an empty string>"}}}}}}}}
"""
JUDGE = {True: "Judge what the answer rests on, not the colleague's arithmetic: a figure worked out wrongly from a stated rule is still \"supported\".",
         False: "Judge what the answer rests on; you do not have to compute it."}


def show(v) -> str:
    return json.dumps(v, ensure_ascii=False)


def render(fund: str, ans: dict) -> str:
    """The colleague's draft as plain text: every requirement and, for every answer field of the reference, what the
    draft wrote (value, note, or basis, quote and assumption or question). Nothing is added and nothing is judged."""
    out = ["REQUIREMENTS"]
    for q in ans.get("requirements") or []:
        if not isinstance(q, dict):
            out.append(f"- {q}")
            continue
        parts = [f"{q.get('id', '')}: {q.get('text', '')}"]
        for key, label in (("basis", "basis"), ("source", "source"), ("quote", "quote"), ("assumption_or_question", "assumption or question")):
            if q.get(key):
                parts.append(f"{label}: {q[key]}")
        out.append("- " + " | ".join(parts))
    out += ["", "EXPECTED RESULTS"]
    for s in FUNDS[fund]["scenarios"].build():
        out.append(f"{s['id']} {s['title']}")
        for field in s["expected"]:
            c = SD.cell(ans, s["id"], field)
            if c is None:
                out.append(f"  {field}: (no answer)")
                continue
            parts = [f"value {show(c.get('value'))}"]
            for key, label in (("basis", "basis"), ("note", "note"), ("quote", "quote"), ("assumption_or_question", "assumption or question")):
                if c.get(key):
                    parts.append(f"{label}: {c[key]}")
            out.append(f"  {field}: " + " | ".join(parts))
    return "\n".join(out) + "\n"


def prompt(fund: str, draft: str | None) -> list[dict]:
    F = FUNDS[fund]
    with open(os.path.join(HERE, F["pack"], "documents.md"), encoding="utf-8") as fh:
        docs = fh.read()
    with open(os.path.join(HERE, F["pack"], "scenarios_for_models.json"), encoding="utf-8") as fh:
        sc = fh.read()
    has = draft is not None
    user = (INTRO[has].format(exposure=F["exposure"]) + TASK.format(judge=JUDGE[has], first="S01" if fund == "swap" else "T01")
            + "\nDOCUMENTS\n\n" + docs + "\nSCENARIOS\n\n" + sc)
    if has:
        user += "\nTHE COLLEAGUE'S DRAFT\n\n" + draft
    return [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]


def check_dir(fund: str, reader: str, name: str) -> str:
    return os.path.join(HERE, "data", "out", "checks", fund, reader, name)


def call(fund: str, reader: str, name: str, draft: str | None, max_tokens: int, meta: dict) -> dict:
    out = check_dir(fund, reader, name)
    os.makedirs(out, exist_ok=True)
    messages, stats, t0 = prompt(fund, draft), {}, time.time()
    content, used = live.chat(messages, endpoint=GRID[reader], model_id=reader, max_tokens=max_tokens, temperature=0.0,
                              timeout=180, deadline=900, stats=stats)
    with open(os.path.join(out, "raw.txt"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(content)
    record = {"fund": fund, "reader": used, **meta, "started": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(t0)),
              "prompt": live.prompt_fingerprint(messages), "max_tokens": max_tokens,
              **{k: stats.get(k) for k in ("finish_reason", "usage", "content_chars", "reasoning_chars", "elapsed_s",
                                           "deadline_hit", "temperature", "temperature_dropped", "token_field", "endpoint_host")}}
    with open(os.path.join(out, "run.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(record, fh, indent=1)
    return record


def done(fund: str, reader: str, name: str) -> bool:
    p = os.path.join(check_dir(fund, reader, name), "run.json")
    if not os.path.exists(p):
        return False
    with open(p, encoding="utf-8") as fh:
        return json.load(fh).get("finish_reason") == "stop"


def run(fund: str, reader: str, name: str, draft: str | None, max_tokens: int, meta: dict) -> dict:
    r = call(fund, reader, name, draft, max_tokens, meta)
    if r["finish_reason"] != "stop" and max_tokens < 64000:   # cut off: keep the cut answer aside and repeat once
        prior = os.path.join(HERE, "data", "out", "checks_prior", f"{fund}-{reader}-{name}-cut-at-{max_tokens}")
        if os.path.isdir(prior):
            shutil.rmtree(prior)
        os.makedirs(os.path.dirname(prior), exist_ok=True)
        shutil.move(check_dir(fund, reader, name), prior)
        r = call(fund, reader, name, draft, max_tokens * 2, {**meta, "repeated_after_cut_at": max_tokens})
    return r


def main(argv: list[str]) -> int:
    if len(argv) < 4 or argv[1] not in FUNDS or argv[2] not in GRID or argv[3] not in ("drafts", "nodraft"):
        print(__doc__)
        return 2
    fund, reader, mode, args = argv[1], argv[2], argv[3], argv[4:]
    force = "--force" in args
    opts = {}
    for flag in ("--max-tokens", "--runs", "--only"):
        if flag in args:
            opts[flag] = args[args.index(flag) + 1]
    budget = int(opts.get("--max-tokens", BUDGET[reader]))
    jobs = []
    if mode == "drafts":
        for arm in ARMS:
            for drafter in GRID:
                if "--only" in opts and opts["--only"] != f"{arm}:{drafter}":
                    continue
                ans = SD.parse(os.path.join(SD.run_dir(fund, arm, drafter, DRAFT_RUN), "raw.txt"))
                jobs.append((f"{arm}__{drafter}__run{DRAFT_RUN}", render(fund, ans),
                             {"mode": "draft", "draft_arm": arm, "drafter": drafter, "draft_run": DRAFT_RUN}))
    else:
        for k in [int(x) for x in opts.get("--runs", "1").split(",")]:
            jobs.append((f"nodraft__run{k}", None, {"mode": "nodraft", "run": k}))
    for name, draft, meta in jobs:
        if done(fund, reader, name) and not force:
            print(f"{fund:<8}{reader:<19}{name:<38} already finished, kept", flush=True)
            continue
        try:
            r = run(fund, reader, name, draft, budget, meta)
            print(f"{fund:<8}{reader:<19}{name:<38} finish={r['finish_reason']} chars={r['content_chars']} "
                  f"elapsed={r['elapsed_s']}s usage={r['usage']}", flush=True)
        except Exception as e:                               # one call failing must not stop the others; never echo a request
            print(f"{fund:<8}{reader:<19}{name:<38} FAILED: {type(e).__name__}: {str(e)[:200]}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

"""Rule-by-rule tracing: a reader gets the fund's documents and the list of rules the system needs, as questions.

  python trace.py <fund> <reader> [--runs 1,2,3] [--max-tokens N] [--force]

For every question the reader answers "stated" (with the passage, word for word), "partly" (the passage and what
is missing), "not stated" (what must be asked), or "conflicting" (the passages that disagree). The reader sees the
documents and the questions only: no scenario, no draft, no status and no assumed answer from the rule table.
Every call is recorded under data/out/traces/<fund>/<reader>/run<k>/ (raw text, run record with the finish reason,
token usage and the question numbers). A finished run is not repeated unless --force is given; a run cut off at
the token limit is moved to data/out/traces_prior/ and repeated once with twice the limit. Keys come from the
repository's .env through harness.live and are never printed.
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

from draft import BUDGET, GRID   # noqa: E402
from ds.funds import FUNDS   # noqa: E402

SYSTEM = ("You are a senior business analyst at a fund administrator. You trace every processing rule to the fund's "
          "documents before the fund accounting team builds from it.")

TASK = """A client's exchange-traded fund is being set up on the fund accounting platform. {exposure} Below are (1) passages from the fund's public documents and (2) a list of questions: the rules the fund accounting system needs before it can process the fund.

TASK. For every question, say whether the passages answer it:
"stated" - a passage answers the question fully; quote it;
"partly" - a passage answers part of it; quote it and say what is missing;
"not stated" - no passage answers it; say what must be asked of the client or of {other};
"conflicting" - passages give different answers; quote them.
Quote passages word for word. Do not answer from general practice: a rule that the passages do not state is "not stated" even if you know what is usual.

Answer with one JSON object and nothing else:
{{"answers": {{"Q01": {{"verdict": "stated" | "partly" | "not stated" | "conflicting", "quote": "<the passage or passages, word for word, or an empty string>", "missing": "<what the passages do not say, or an empty string>"}}}}}}
"""
OTHER = {"swap": "the swap counterparty", "options": "the clearing broker", "futures": "the futures broker"}


def questions(fund: str) -> dict:
    """Q-number -> rule id, in the order of the rule table. The reader sees the Q-numbers only."""
    return {f"Q{n:02d}": rid for n, rid in enumerate(FUNDS[fund]["rules"].RULES, 1)}


def prompt(fund: str) -> list[dict]:
    F = FUNDS[fund]
    with open(os.path.join(HERE, F["pack"], "documents.md"), encoding="utf-8") as fh:
        docs = fh.read()
    R = F["rules"].RULES
    listed = "\n".join(f"{q}. {R[rid]['ask']}" for q, rid in questions(fund).items())
    user = TASK.format(exposure=F["exposure"], other=OTHER[fund]) + "\nDOCUMENTS\n\n" + docs + "\nQUESTIONS\n\n" + listed + "\n"
    return [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]


PROBE = """A client's exchange-traded fund is being set up on the fund accounting platform. {exposure} Below are (1) passages from the fund's public documents and (2) a list of questions that is meant to hold every rule the fund accounting system needs before it can process {subject}.

TASK. Name the rules that the system needs and that the list does NOT ask for: at most eight, the most important first, none that a question of the list already covers. For each one give the question, and say whether the passages answer it: "stated" (quote the passage word for word), "partly" (quote it and say what is missing) or "not stated".

Answer with one JSON object and nothing else:
{{"additions": [{{"question": "...", "verdict": "stated" | "partly" | "not stated", "quote": "...", "missing": "..."}}]}}
"""


def probe_prompt(fund: str) -> list[dict]:
    """The same documents and questions, and one other task: what does the list of questions leave out?"""
    F = FUNDS[fund]
    with open(os.path.join(HERE, F["pack"], "documents.md"), encoding="utf-8") as fh:
        docs = fh.read()
    R = F["rules"].RULES
    listed = "\n".join(f"{q}. {R[rid]['ask']}" for q, rid in questions(fund).items())
    user = PROBE.format(exposure=F["exposure"], subject=F["subject"]) + "\nDOCUMENTS\n\n" + docs + "\nQUESTIONS\n\n" + listed + "\n"
    return [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]


def probe(fund: str, reader: str, max_tokens: int) -> dict:
    out = os.path.join(HERE, "data", "out", "probes", fund, reader, "run1")
    os.makedirs(out, exist_ok=True)
    messages, stats, t0 = probe_prompt(fund), {}, time.time()
    content, used = live.chat(messages, endpoint=GRID[reader], model_id=reader, max_tokens=max_tokens, temperature=0.0,
                              timeout=180, deadline=900, stats=stats)
    with open(os.path.join(out, "raw.txt"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(content)
    record = {"fund": fund, "reader": used, "mode": "probe", "started": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(t0)),
              "prompt": live.prompt_fingerprint(messages), "max_tokens": max_tokens,
              **{k: stats.get(k) for k in ("finish_reason", "usage", "content_chars", "elapsed_s")}}
    with open(os.path.join(out, "run.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(record, fh, indent=1)
    return record


def trace_dir(fund: str, reader: str, run: int) -> str:
    return os.path.join(HERE, "data", "out", "traces", fund, reader, f"run{run}")


def call(fund: str, reader: str, run: int, max_tokens: int, extra: dict | None = None) -> dict:
    out = trace_dir(fund, reader, run)
    os.makedirs(out, exist_ok=True)
    messages, stats, t0 = prompt(fund), {}, time.time()
    content, used = live.chat(messages, endpoint=GRID[reader], model_id=reader, max_tokens=max_tokens, temperature=0.0,
                              timeout=180, deadline=900, stats=stats)
    with open(os.path.join(out, "raw.txt"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(content)
    record = {"fund": fund, "reader": used, "run": run, "questions": questions(fund), **(extra or {}),
              "started": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(t0)),
              "prompt": live.prompt_fingerprint(messages), "max_tokens": max_tokens,
              **{k: stats.get(k) for k in ("finish_reason", "usage", "content_chars", "reasoning_chars", "elapsed_s",
                                           "deadline_hit", "temperature", "temperature_dropped", "token_field", "endpoint_host")}}
    with open(os.path.join(out, "run.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(record, fh, indent=1)
    return record


def done(fund: str, reader: str, run: int) -> bool:
    p = os.path.join(trace_dir(fund, reader, run), "run.json")
    if not os.path.exists(p):
        return False
    with open(p, encoding="utf-8") as fh:
        return json.load(fh).get("finish_reason") == "stop"


def run(fund: str, reader: str, k: int, max_tokens: int) -> dict:
    r = call(fund, reader, k, max_tokens)
    if r["finish_reason"] != "stop" and max_tokens < 64000:   # cut off: keep the cut answer aside and repeat once
        prior = os.path.join(HERE, "data", "out", "traces_prior", f"{fund}-{reader}-run{k}-cut-at-{max_tokens}")
        if os.path.isdir(prior):
            shutil.rmtree(prior)
        os.makedirs(os.path.dirname(prior), exist_ok=True)
        shutil.move(trace_dir(fund, reader, k), prior)
        r = call(fund, reader, k, max_tokens * 2, {"repeated_after_cut_at": max_tokens})
    return r


def main(argv: list[str]) -> int:
    if len(argv) < 3 or argv[1] not in FUNDS or argv[2] not in GRID:
        print(__doc__)
        return 2
    fund, reader, args = argv[1], argv[2], argv[3:]
    force = "--force" in args
    runs = [int(x) for x in args[args.index("--runs") + 1].split(",")] if "--runs" in args else [1]
    budget = int(args[args.index("--max-tokens") + 1]) if "--max-tokens" in args else BUDGET[reader]
    if "--probe" in args:                                    # one call: what does the list of questions leave out?
        try:
            r = probe(fund, reader, budget)
            print(f"{fund:<8}{reader:<19} probe finish={r['finish_reason']} chars={r['content_chars']} elapsed={r['elapsed_s']}s usage={r['usage']}", flush=True)
        except Exception as e:
            print(f"{fund:<8}{reader:<19} probe FAILED: {type(e).__name__}: {str(e)[:200]}", flush=True)
        return 0
    for k in runs:
        if done(fund, reader, k) and not force:
            print(f"{fund:<8}{reader:<19} run{k} already finished, kept", flush=True)
            continue
        try:
            r = run(fund, reader, k, budget)
            print(f"{fund:<8}{reader:<19} run{k} finish={r['finish_reason']} chars={r['content_chars']} "
                  f"elapsed={r['elapsed_s']}s usage={r['usage']}", flush=True)
        except Exception as e:                               # one call failing must not stop the others; never echo a request
            print(f"{fund:<8}{reader:<19} run{k} FAILED: {type(e).__name__}: {str(e)[:200]}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

"""Ask models to draft the requirements and the test results from a fund's public documents.

  python draft.py <fund> <arm> [<model> ...] [--runs 1,2,3] [--max-tokens N] [--force]
      fund = swap | options ; arm = plain | ask ; default models = one per vendor from the repository's grid

Two arms, the same documents and scenarios:
  plain  the task only
  ask    the task plus one paragraph telling the model to say, for every requirement and figure, whether it
         rests on a passage, on an assumption, or on a question that must be asked first
Every call is recorded under data/out/drafts/<fund>/<arm>/<model>/run<k>/ (raw text, parsed answer, run record
with the finish reason and token usage). A run that already finished is not repeated unless --force is given. A
run that is cut off at the token limit is moved to data/out/drafts_prior/ and repeated once with twice the limit.
Keys come from the repository's .env through harness.live and are never printed.
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

from ds.funds import FUNDS   # noqa: E402

GRID = {"claude-opus-4-8": "https://api.anthropic.com/v1",
        "gpt-5.6-sol": "https://api.openai.com/v1",
        "gemini-3.6-flash": "https://generativelanguage.googleapis.com/v1beta/openai"}
BUDGET = {"claude-opus-4-8": 24000, "gpt-5.6-sol": 24000, "gemini-3.6-flash": 32000}   # hidden reasoning eats the last one's

SYSTEM = ("You are a senior business analyst at a fund administrator. You write the processing requirements and "
          "the test cases that the fund accounting team builds from.")

TASK = """A client's exchange-traded fund is being set up on the fund accounting platform. {exposure} Below are (1) passages from the fund's public documents and (2) fifteen test scenarios with constructed positions.

TASK 1. Write the processing requirements for {subject}: what the system must do each day, and on each event, so that the daily NAV is right. Number them.

TASK 2. For each scenario, give the expected result for every answer field listed.

The positions and figures in the scenarios are constructed for this test; the documents are the fund's own. Where a scenario gives a figure (for example {example}), use the scenario's figure.
"""

ASK = """
The documents may not state everything the system needs. For every requirement and every figure, say what it rests on: "document" (quote the passage), "assumption" (state the assumption you made), or "question" (state what must be asked of the client or of the swap counterparty before the system is built; give no figure, or give one only together with the assumption it depends on). Do not present an assumption as something the documents state.
"""
# The second fund has no swap counterparty; the paragraph is otherwise word for word the same.
ASK_OPTIONS = ASK.replace("of the client or of the swap counterparty", "of the client or of the clearing broker")

FORMAT = {
    "plain": """
Answer with one JSON object and nothing else:
{"requirements": [{"id": "Q1", "text": "...", "source": "the passage you rely on, quoted, or an empty string"}],
 "scenarios": {"S01": {"<answer field>": {"value": <number or null>, "note": "<one sentence, may be empty>"}}}}
""",
    "ask": """
Answer with one JSON object and nothing else:
{"requirements": [{"id": "Q1", "text": "...", "basis": "document" | "assumption" | "question", "quote": "...", "assumption_or_question": "..."}],
 "scenarios": {"S01": {"<answer field>": {"value": <number or null>, "basis": "document" | "assumption" | "question", "quote": "...", "assumption_or_question": "..."}}}}
""",
}


def prompt(fund: str, arm: str) -> list[dict]:
    F = FUNDS[fund]
    with open(os.path.join(HERE, F["pack"], "documents.md"), encoding="utf-8") as fh:
        docs = fh.read()
    with open(os.path.join(HERE, F["pack"], "scenarios_for_models.json"), encoding="utf-8") as fh:
        sc = fh.read()
    task = TASK.format(exposure=F["exposure"], subject=F["subject"], example=F["example"])
    ask = (ASK if fund == "swap" else ASK_OPTIONS) if arm == "ask" else ""
    fmt = FORMAT[arm] if fund == "swap" else FORMAT[arm].replace('"S01"', '"T01"')
    user = task + ask + fmt + "\nDOCUMENTS\n\n" + docs + "\nSCENARIOS\n\n" + sc
    return [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]


def run_dir(fund: str, arm: str, model: str, run: int) -> str:
    return os.path.join(HERE, "data", "out", "drafts", fund, arm, model, f"run{run}")


def call(fund: str, arm: str, model: str, run: int, max_tokens: int) -> dict:
    out = run_dir(fund, arm, model, run)
    os.makedirs(out, exist_ok=True)
    messages, stats, t0 = prompt(fund, arm), {}, time.time()
    content, used = live.chat(messages, endpoint=GRID[model], model_id=model, max_tokens=max_tokens, temperature=0.0,
                              timeout=180, deadline=900, stats=stats)
    with open(os.path.join(out, "raw.txt"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(content)
    try:
        answer = live.salvage_json(content)
    except Exception as e:                                   # keep the run; the scorer reads raw.txt itself
        answer = {"_unparsed": type(e).__name__}
    with open(os.path.join(out, "answer.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(answer, fh, indent=1)
    record = {"fund": fund, "arm": arm, "run": run, "model": used,
              "started": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(t0)),
              "prompt": live.prompt_fingerprint(messages), "max_tokens": max_tokens,
              **{k: stats.get(k) for k in ("finish_reason", "usage", "content_chars", "reasoning_chars", "elapsed_s",
                                           "deadline_hit", "temperature", "temperature_dropped", "token_field", "endpoint_host")}}
    with open(os.path.join(out, "run.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(record, fh, indent=1)
    return record


def done(fund: str, arm: str, model: str, run: int) -> bool:
    p = os.path.join(run_dir(fund, arm, model, run), "run.json")
    if not os.path.exists(p):
        return False
    with open(p, encoding="utf-8") as fh:
        return json.load(fh).get("finish_reason") == "stop"


def run(fund: str, arm: str, model: str, k: int, max_tokens: int) -> dict:
    r = call(fund, arm, model, k, max_tokens)
    if r["finish_reason"] != "stop" and max_tokens < 64000:   # cut off: keep the cut answer aside and repeat once
        prior = os.path.join(HERE, "data", "out", "drafts_prior", f"{fund}-{arm}-{model}-run{k}-cut-at-{max_tokens}")
        if os.path.isdir(prior):
            shutil.rmtree(prior)
        os.makedirs(os.path.dirname(prior), exist_ok=True)
        shutil.move(run_dir(fund, arm, model, k), prior)
        r = call(fund, arm, model, k, max_tokens * 2)
        r["repeated_after_cut_at"] = max_tokens
        with open(os.path.join(run_dir(fund, arm, model, k), "run.json"), "w", encoding="utf-8", newline="\n") as fh:
            json.dump(r, fh, indent=1)
    return r


def main(argv: list[str]) -> int:
    if len(argv) < 3 or argv[1] not in FUNDS or argv[2] not in FORMAT:
        print(__doc__)
        return 2
    fund, arm, args, budget, runs, force = argv[1], argv[2], argv[3:], None, [1], False
    if "--force" in args:
        force = True
        args.remove("--force")
    for flag in ("--max-tokens", "--runs"):
        if flag in args:
            k = args.index(flag)
            if flag == "--runs":
                runs = [int(x) for x in args[k + 1].split(",")]
            else:
                budget = int(args[k + 1])
            args = args[:k] + args[k + 2:]
    for m in (args or list(GRID)):
        for k in runs:
            if done(fund, arm, m, k) and not force:
                print(f"{fund:<8}{arm:<6}{m:<19} run{k} already finished, kept", flush=True)
                continue
            try:
                r = run(fund, arm, m, k, budget or BUDGET[m])
                print(f"{fund:<8}{arm:<6}{m:<19} run{k} finish={r['finish_reason']} chars={r['content_chars']} "
                      f"elapsed={r['elapsed_s']}s usage={r['usage']}", flush=True)
            except Exception as e:                           # one call failing must not stop the others; never echo a request
                print(f"{fund:<8}{arm:<6}{m:<19} run{k} FAILED: {type(e).__name__}: {str(e)[:200]}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

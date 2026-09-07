"""outputs/run_live_eval2.py — drive the eval-#2 live runs and capture everything the
Phase-5 taxonomy needs: the parsed model answer, the raw completion, and the scored report.

  python outputs/run_live_eval2.py <case-substr> [--e2e] [--judge mock|llm] [--model-id ID]
                                   [--endpoint URL] [--max-tokens N]

Artifacts land in outputs/eval2-live/<case>__<model>__<mode>.{answer.json,raw.txt,report.txt,run.json};
an earlier run under the same prefix is moved to outputs/eval2-live/prior/<run_id>/ first, never overwritten.
"""
from __future__ import annotations
import argparse
import glob
import json
import os
import re
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from harness import run_case                                    # noqa: E402
from harness.rubric import load_case                            # noqa: E402
from harness import live_defined_outcome as ldo                 # noqa: E402
from harness.report import render                               # noqa: E402
from harness.run_record import new_run_id, preserve_prior, rel, run_fields, unclobbered, write_run_record  # noqa: E402

OUT = os.path.join(REPO, "outputs", "eval2-live")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("case")
    ap.add_argument("--e2e", action="store_true")
    ap.add_argument("--judge", default="mock", choices=["mock", "llm"])
    ap.add_argument("--model-id", default=None)
    ap.add_argument("--endpoint", default="http://192.168.1.10:1234/v1")
    ap.add_argument("--max-tokens", type=int, default=16000)   # reasoning models think for thousands of tokens first
    ap.add_argument("--deadline", type=int, default=2400)       # qwen3.6-27b on the M5 Max needs ~20 min/case (think + 4k-token JSON)
    a = ap.parse_args()

    path = next(p for p in sorted(glob.glob(os.path.join(REPO, "cases", "*.case.yaml")))
                if a.case in os.path.basename(p))
    case = load_case(path)
    name = case["case_id"]
    mode = "e2e" if a.e2e else "oracle-packet"
    print(f"[{name}] building packet ({mode}) and calling {a.endpoint} ...", flush=True)

    run_id = new_run_id()
    t0 = time.time()
    try:
        ans = ldo.answer(case, endpoint=a.endpoint, model_id=a.model_id,
                         max_tokens=a.max_tokens, e2e=a.e2e, deadline=a.deadline)
    except Exception as e:
        raw = getattr(e, "raw", "")
        if raw:
            os.makedirs(OUT, exist_ok=True)
            fp = os.path.join(OUT, f"{name}__parsefail__{int(time.time())}.raw.txt")
            with open(fp, "w", encoding="utf-8") as fh:
                fh.write(raw)
            print(f"[{name}] parse failed; raw completion saved to {fp}")
        raise
    dt = time.time() - t0
    model = ans.get("_model_id", "unknown")
    slug = re.sub(r"[^A-Za-z0-9.-]+", "-", model)
    print(f"[{name}] {model} answered in {dt:.0f}s "
          f"(prompt ~{ans.get('_prompt_tokens_approx', 0):,} tok, raw {len(ans.get('_raw', '')):,} chars)"
          + ("  ** SALVAGED: stream truncated (raise --max-tokens/--deadline) **" if ans.get("_salvaged") else ""),
          flush=True)

    os.makedirs(OUT, exist_ok=True)
    prefix = f"{name}__{slug}__{mode}"
    base = os.path.join(OUT, prefix)
    prior = preserve_prior(OUT, prefix=prefix)          # never overwrite a cited run in place
    with open(base + ".raw.txt", "w", encoding="utf-8") as fh:
        fh.write(ans.get("_raw", ""))
    clean = {k: v for k, v in ans.items() if not k.startswith("_")}
    with open(base + ".answer.json", "w", encoding="utf-8") as fh:
        json.dump(clean, fh, indent=1, default=str)

    result, rubric = run_case(path, model_output=ans, mode=a.judge, endpoint=a.endpoint, model_id=a.model_id)
    report = render(result, rubric, variant=f"live:{model}", mode=a.judge)
    with open(base + f".report.{a.judge}.txt", "w", encoding="utf-8") as fh:
        fh.write(report + f"\n\n(answered in {dt:.0f}s; mode={mode})\n")
    write_run_record(OUT, filename=prefix + ".run.json",
                     **run_fields(ans, case_path=path, case=case, live_module=ldo, judge=a.judge, run_id=run_id),
                     prior_dir=rel(prior) if prior else None, packet_mode=mode,
                     score={"gated": result.case_gated, "ungated": result.case_ungated, "gap": result.gap,
                            "allpass": result.allpass, "gates": result.fired_gates, "flags": result.flags})
    print(report)
    st = ans.get("_stats") or {}
    print(f"[{name}] finish_reason={st.get('finish_reason')} usage={st.get('usage')} "
          f"parse={ans.get('_parse_status')} retries={ans.get('_retries')}"
          + ("  ** TRUNCATED by the token budget **" if st.get("finish_reason") == "length" else ""))
    print(f"\nartifacts: {base}.{{answer.json,raw.txt,report.{a.judge}.txt,run.json}}  (prior runs under prior/)")


if __name__ == "__main__":
    main()

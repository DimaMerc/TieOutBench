#!/usr/bin/env python3
"""
outputs/run_live_eval6.py — drive a REAL model through an eval-#6 (corporate-actions processing)
case and save artifacts.

  python outputs/run_live_eval6.py --model-id claude-sonnet-4-6 \
      --endpoint https://api.anthropic.com/v1 [--case mega-split-2024] [--max-tokens 8000]

Saves under outputs/eval6-live/<model>/<case>/: answer.json, raw.txt, report.txt. The API key is
read from the environment (or a gitignored repo-root .env — see .env.example), never passed on
the command line. The key env var is RESOLVED FROM THE ENDPOINT unless --key-env overrides:
api.anthropic.com -> ANTHROPIC_API_KEY (legacy fallback OPENROUTER_API_KEY, which held the
sk-ant key on the original rig), api.openai.com -> OPENAI_API_KEY, googleapis.com ->
GEMINI_API_KEY.
"""
from __future__ import annotations
import argparse
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from harness import run_case                                # noqa: E402
from harness.rubric import load_case                        # noqa: E402
from harness import live_corporate_actions as lca            # noqa: E402
from harness.report import render                            # noqa: E402
from harness.run_record import new_run_id, preserve_prior, rel, run_fields, unclobbered, write_run_record  # noqa: E402


def _key_env_for(endpoint: str) -> str:
    if "anthropic" in endpoint:
        # honest name first; the legacy var (which held the sk-ant key on the original rig) still works
        return "ANTHROPIC_API_KEY" if os.environ.get("ANTHROPIC_API_KEY") else "OPENROUTER_API_KEY"
    if "googleapis" in endpoint:
        return "GEMINI_API_KEY"
    return "OPENAI_API_KEY"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model-id", required=True)
    ap.add_argument("--endpoint", default="https://api.anthropic.com/v1")
    ap.add_argument("--case", default="mega-split-2024")
    ap.add_argument("--max-tokens", type=int, default=8000)
    ap.add_argument("--judge", default="mock", choices=["mock", "llm"])
    ap.add_argument("--key-env", default=None, help="env var holding the API key (default: by endpoint)")
    a = ap.parse_args()

    key_env = a.key_env or _key_env_for(a.endpoint)
    key = os.environ.get(key_env)
    if not key:
        print(f"[live] no key in ${key_env}")
        sys.exit(2)

    case_path = os.path.join(REPO, "cases", a.case + ".case.yaml")
    case = load_case(case_path)
    outdir = os.path.join(REPO, "outputs", "eval6-live", a.model_id.replace("/", "_"), a.case)
    os.makedirs(outdir, exist_ok=True)
    run_id = new_run_id()

    print(f"[live] {a.model_id} @ {a.endpoint} (key from ${key_env}) — building the document-store packet ({a.case}) ...")
    try:
        ans = lca.answer(case, endpoint=a.endpoint, model_id=a.model_id, max_tokens=a.max_tokens,
                         api_key=key)
    except Exception as e:
        raw = getattr(e, "raw", "")
        if raw:
            with open(unclobbered(os.path.join(outdir, "raw_FAILED.txt"), run_id), "w", encoding="utf-8") as fh:
                fh.write(raw)
        st = getattr(e, "stats", None) or {}
        if st:
            print(f"[live] endpoint reported finish_reason={st.get('finish_reason')} usage={st.get('usage')}")
        print(f"[live] FAILED: {e}")
        sys.exit(1)

    prior = preserve_prior(outdir)                    # never overwrite a cited run in place
    with open(os.path.join(outdir, "raw.txt"), "w", encoding="utf-8") as fh:
        fh.write(ans.get("_raw", ""))
    clean = {k: v for k, v in ans.items() if not k.startswith("_")}
    with open(os.path.join(outdir, "answer.json"), "w", encoding="utf-8") as fh:
        json.dump(clean, fh, indent=2, default=str)

    result, rubric = run_case(case_path, model_output=ans, mode=a.judge)
    report = render(result, rubric, variant=f"live:{a.model_id}", mode=a.judge)
    with open(os.path.join(outdir, "report.txt"), "w", encoding="utf-8") as fh:
        fh.write(report)
    write_run_record(outdir, **run_fields(ans, case_path=case_path, case=case, live_module=lca,
                                         judge=a.judge, run_id=run_id, model_id=a.model_id),
                     prior_dir=rel(prior) if prior else None,
                     score={"gated": result.case_gated, "ungated": result.case_ungated, "gap": result.gap,
                            "allpass": result.allpass, "gates": result.fired_gates, "flags": result.flags})
    print(report)
    st = ans.get("_stats") or {}
    print(f"[live] finish_reason={st.get('finish_reason')} usage={st.get('usage')} "
          f"parse={ans.get('_parse_status')} retries={ans.get('_retries')} elapsed={ans.get('_elapsed_s')}s"
          + ("  ** TRUNCATED by the token budget **" if st.get("finish_reason") == "length" else ""))
    print(f"\n[live] {a.model_id} ({a.case}): gated={result.case_gated:.3f} ungated={result.case_ungated:.3f} "
          f"GAP={result.gap:.3f} AllPass={result.allpass} "
          f"gates={result.fired_gates} flags={result.flags} "
          f"D2(R,G)={result.e6}  (prompt ~{ans.get('_prompt_tokens_approx')} tok)")
    print(f"[live] artifacts -> {outdir}  (run.json = provenance; prior runs under prior/)")


if __name__ == "__main__":
    main()

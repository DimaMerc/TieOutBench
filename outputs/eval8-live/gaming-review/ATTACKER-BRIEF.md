# Eval #8 (options-component ETF redemption tie-out) - adversarial gaming review: attacker brief

You are one of six independent attackers. Your job is to find ways a WRONG answer scores well, or a RIGHT answer
scores badly, on eval #8 of TieOutBench, and to PROVE each finding by running the grader. A finding without a
reproduced run is not a finding.

## The system under attack

- Suite grader: `harness/suites/options_redemption.py` (read it in full; it is the grader you are attacking). It
  imports shared helpers from `harness/suites/nav_oversight.py` (`_toks`, `_idn`, `_numx`, `_same_day`, `_family`,
  `_scale_evidence`, the refusal regexes) - read those too.
- Rubric: `rubric/criteria-options-redemption.yaml` (atoms, points, gates, tolerances).
- Gold cases: `cases/grbo-redeem-2026.case.yaml` (the break: the long put 240.00 leg confirms 12,000 contracts
  against 120 due; gold HOLD) and `cases/grbo-redeem-2026-clean.case.yaml` (every leg ties; gold SETTLE).
- Live-model contract (what a real model is asked to return): the `SCHEMA` string and `build_messages` in
  `harness/live_options_redemption.py`; `build_packet` renders the packet the model sees.
- Workflow note: `workflow/options-redemption-analysis.md`.

## How to run the grader on a candidate answer

Use `python` from the repo root `C:\Projects\finance-llm-evals` (the project interpreter; if imports fail, use
`"$USERPROFILE/miniconda3/envs/tieoutbench/python.exe"`). The oracle answer is a deepcopy of the case gold with the
D2 probe filled in:

```python
import sys; sys.path.insert(0, r"C:\Projects\finance-llm-evals")
from harness import run_case
from harness.rubric import load_case
from harness.suites import options_redemption as orx
case_path = r"C:\Projects\finance-llm-evals\cases\grbo-redeem-2026.case.yaml"
m = orx.oracle(load_case(case_path))          # a perfect answer; mutate it to build your attack
m["D1"]["decision"] = "settle after escalation"   # example mutation
result, rubric = run_case(case_path, model_output=m)
print(result.case_gated, result.allpass, result.fired_gates, result.flags, result.e6)
print({k: v["score_gated"] for k, v in result.checkpoints.items()})
```

`result.case_gated` is the headline, `result.allpass` 1 means every criterion met, `result.fired_gates` lists the
auto-fail gates, `result.flags` the headline flags (`settle_override_fired`), `result.e6` is (R, G) for the refusal
checkpoint D2. Baselines: oracle 1.000/AllPass on both cases; `SETTLE` on the break = 0.840 + GATE.SETTLE + flag;
`HOLD` on the clean case = 0.840, D1 = 0, no gate. Never modify the grader, the rubric or the cases; only build
answers and run them.

## What counts as a finding

1. **An exploit**: an answer that is wrong in a way a settlement desk would care about, yet scores higher than it
   should, does not fire the gate that should fire, or earns AllPass. Examples of the kind of thing to try (not a
   limit): a SETTLE the classifier does not read as a settle; a hold that fires the settle gate; a release
   instruction hidden in `remedy` or `escalate_to`; a NOT_DISCLOSED refusal that smuggles the AP's cost or a profit
   into the derivation; a cash component off by a factor the multiplier gate does not catch; a tie ledger with the
   right statuses but wrong quantities, or rows keyed so the grader cannot find them; the agent's recap adopted as
   evidence without the penalty firing; an "exception" row that says nothing; a remedy that moves the contracts the
   WRONG way yet satisfies the remedy atom; booleans and directions as hedges; the per-remaining-share impact with
   the wrong denominator; a citation of a line the answer never used earning the reading credit.
2. **A false positive**: a RIGHT answer in a legitimate alternative format that the grader fails or gates.
   Examples: numbers as strings with thousands separators or a currency sign; percentages as fractions or with a
   percent sign; dates as ISO strings with a time part; OSI identifiers with a single space or no padding; rows
   keyed by OSI identifier instead of `leg_id`; short positions reported as absolute quantities with a side field;
   marks as a list instead of a map; a correct settle phrased naturally ("release the cash and cancel the shares");
   a correct hold phrased naturally ("cannot settle until the 11,880 contracts are back"); tie statuses a desk would
   write ("OK", "quantity matches", "over-delivered by 11,880"); a citation with different whitespace or a shorter
   but entailing verbatim; a record with extra fields.

For every finding record: the mutation (exact JSON of the fields you changed), the case, the score before and
after, the gates and flags, and one sentence on why it is unfair. Also record the attacks that FAILED (the grader
held) - those are evidence too.

## Output

- Your note: `outputs/eval8-live/gaming-review/<n>-<surface>.md`, at most 1,500 words: a headline, a table of
  findings (ranked by severity), the failed attacks, two or three sentences on the pattern.
- Your script: `outputs/eval8-live/gaming-review/scratch_attacker<n>.py`, re-runnable from the repo root, printing
  one result line per attack.
- End the note with a section `## PINNABLE CHECKS` in the exact style of `harness/gaming_review_eval7.py`
  `checks()` - one `(name, lambda)` tuple per reproduced claim, using the helpers `_run(case, mutate)`, `_dec(s)`,
  `_deriv(s, label, value)`, `_set(path, value)`, `_gate(r, g)`, `_cp(r, k)`, `_perfect(r)` - so the maintainer can
  pin them as standing regressions.

## Rules

- Attack only your assigned surface (given in your prompt), but report anything else you notice.
- Reproduce every claim with a run; paste the printed result line.
- Do not edit any repository file. Write only under `outputs/eval8-live/gaming-review/`.
- Be concrete and brief.

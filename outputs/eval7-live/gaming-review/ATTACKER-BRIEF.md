# Eval #7 (ETF NAV oversight) - adversarial gaming review: attacker brief

You are one of six independent attackers. Your job is to find ways a WRONG answer scores well, or a RIGHT answer
scores badly, on eval #7 of TieOutBench, and to PROVE each finding by running the grader. A finding without a
reproduced run is not a finding.

## The system under attack

- Suite grader: `harness/suites/nav_oversight.py` (read it in full; it is the grader you are attacking).
- Rubric: `rubric/criteria-nav-oversight.yaml` (atoms, points, gates, tolerances).
- Gold cases: `cases/grsl-nav-2026.case.yaml` (the break: one swap at a stale prior-day mark; gold HOLD) and
  `cases/grsl-nav-2026-clean.case.yaml` (ties; gold RELEASE).
- Live-model contract (what a real model is asked to return): the `SCHEMA` string and `build_messages` in
  `harness/live_nav_oversight.py`.
- Workflow note: `workflow/nav-oversight-analysis.md`.

## How to run the grader on a candidate answer

Use the project interpreter `"$USERPROFILE/miniconda3/envs/tieoutbench/python.exe"` from the repo root
`C:\Projects\finance-llm-evals`. The oracle answer is a deepcopy of the case gold with the D2 probe filled in:

```python
import sys; sys.path.insert(0, r"C:\Projects\finance-llm-evals")
from harness import run_case
from harness.rubric import load_case
from harness.suites import nav_oversight as nv
case_path = r"C:\Projects\finance-llm-evals\cases\grsl-nav-2026.case.yaml"
m = nv.oracle(load_case(case_path))          # a perfect answer; mutate it to build your attack
m["D1"]["decision"] = "release after escalation"   # example mutation
result, rubric = run_case(case_path, model_output=m)
print(result.case_gated, result.allpass, result.fired_gates, result.flags, result.e6)
print({k: v["score_gated"] for k, v in result.checkpoints.items()})
```

`result.case_gated` is the headline, `result.allpass` 1 means every criterion met, `result.fired_gates` lists the
auto-fail gates, `result.flags` the headline flags, `result.e6` is (R, G) for the refusal checkpoint. Never
modify the grader, the rubric or the cases; only build answers and run them.

## What counts as a finding

1. **An exploit**: an answer that is wrong in a way a desk would care about, yet scores higher than it should, does
   not fire the gate that should fire, or earns AllPass. Examples of the kind of thing to try (not a limit):
   a RELEASE that the classifier does not read as a release; a hold that fires the release gate; a NOT_DISCLOSED
   refusal that smuggles a market price into the derivation text; a wrong NAV that sits off any scale factor so the
   scale gate stays quiet while the number is badly wrong; a reconciliation ledger with the right statuses but
   wrong values; citations of the totals block earning the reading credit on a package the answer never read;
   structured-record atoms satisfied with placeholder strings; booleans as strings; the regime pinned with the
   right numbers but the wrong stage; an "exception" row that says nothing; the threshold flags answered as
   consequences; the reasonableness flag set without the numbers behind it; a twin value that matches by sign
   only.
2. **A false positive**: a RIGHT answer in a legitimate alternative format that the grader fails or gates.
   Examples: numbers as strings with thousands separators or a currency sign; percentages as fractions (0.0144)
   or with a percent sign; dates as ISO strings with a time part; direction or classification synonyms a desk
   would use; a correct release phrased naturally ("ok to publish", "no exceptions, release"); a correct hold
   phrased naturally ("cannot release until the Westbrook mark is applied"); a correct citation with different
   whitespace or a shorter but entailing verbatim; a recon ledger that lists the liabilities first; a decision
   record with extra fields.

For every finding record: the mutation (exact JSON of the fields you changed), the case, the score before and
after, the gates and flags, and one sentence on why it is unfair. Also record the attacks that FAILED (the grader
held) - those are evidence too.

## Rules

- Attack only your assigned surface (given in your prompt), but report anything else you notice.
- Reproduce every claim with a run; paste the printed result line.
- Do not edit any repository file. Write your notes to the path given in your prompt.
- Be concrete and brief: a table of findings, then the failed attacks, then two or three sentences on the pattern.

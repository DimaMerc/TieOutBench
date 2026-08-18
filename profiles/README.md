# Capability profiles — the leaderboard as data

Machine-readable, per-checkpoint capability profiles for every frontier model this suite has
live-run (evals **#3–#5**: DCF valuation, ETF creation/redemption reconciliation, OTC confirmation
matching — eight models, three vendors, 48 graded runs). One JSON per model, plus the whole grid
in [`scores.json`](scores.json).

[`LEADERBOARD.md`](../LEADERBOARD.md) is the prose account of these same runs. This directory is
the *structured* account: every number a deployment decision or a due-diligence review would want
to query, without parsing report text. The framing for the second audience — allocators and
operational due diligence — is in [`ODD.md`](../ODD.md).

## Why per-checkpoint scores, not a blended average

A blended accuracy number answers "how good is the model." The question a deployment actually
faces is "**which step of this workflow can the model touch**." Those are different questions,
and the second one is what the checkpoint vector answers:

- A model with `E*` (extraction) checkpoints at 1.0 but a fired `GATE.SCALE` cannot be trusted to
  read a statement header — route extraction elsewhere or gate it with a human check.
- A model with the `D1` decision checkpoint at 1.0 but `C3.impact` errors (the eval-#5 bp
  conversion) makes the right stop-or-go call while mis-sizing the break — usable for triage,
  not for the materiality memo.
- A model whose `gates_fired` is empty across all runs *and* whose refusal triple shows `G = 1.0`
  is the deployable signal. A high **ungated** score alone is not: the gap between ungated and
  gated is the finding.

Used this way the profiles are **routing priors**: a starting allocation of workflow steps to
models, to be tightened by your own runs on your own cases.

## Schema (v1.0)

Per model (`<model>.json`), and identically under `models.<model>` in `scores.json`:

| field | meaning |
|---|---|
| `runs[]` | one record per graded case |
| `runs[].score_gated` | the headline score after auto-fail gates collapse it — matches LEADERBOARD |
| `runs[].score_ungated` / `gap` | the naive average, and ungated − gated (the "looks right vs is right" gap) |
| `runs[].gates_fired` | auto-fail conditions that fired (e.g. `GATE.SCALE`); empty = none |
| `runs[].headline_flags` | rubric-declared headline flags (e.g. `recon_override_fired`) |
| `runs[].refusal` | the calibrated-refusal triple: recall `R`, groundedness `G`, and the F-beta headline (beta = 0.5, precision-weighted — fabrication costs more than over-refusal) |
| `runs[].checkpoints` | per-checkpoint `{weight, ungated, gated}` — the routing vector |
| `runs[].categories` | diagnostic rollup by error kind: extraction / numerical / entailment / reasoning / calibration / structure |
| `runs[].case` / `answer` | repo-relative paths to the gold case and the committed model answer it was graded from |
| `summary.gates_fired` | gate → cases where it fired, across the model's runs |
| `notes[]` | the scope caveats these numbers cannot carry on their own |

Checkpoint ids are defined in the eval's workflow doc and rubric (`workflow/`, `rubric/`); gate
definitions live in the rubric files' `gates:` blocks.

## Provenance and regeneration

Every profile is **re-graded offline from the committed `outputs/**/answer.json` artifacts**
through the same deterministic mock-judge path that produced the committed `report.txt` files —
no API calls, no judge variance. Regeneration is byte-stable:

```
python -m harness profiles
git diff profiles/        # clean = the grader still reproduces every published number
```

which makes the committed profiles a standing regression check on the grader itself.

**Scope:** evals #1–#2 (earnings analysis, buffer-ETF diligence) are excluded on purpose — their
published open-weight runs were scored with a live LLM judge on the free-form criteria, and an
offline regrade would not reproduce those numbers. Approximating them here would put two different
kinds of number in one file; they stay in [`LEADERBOARD.md`](../LEADERBOARD.md) with their own
caveats.

**Caveats carried in every file (`notes[]`):** one run per model per case; point-in-time model
versions; vendor-parity completion budgets (documented in LEADERBOARD scope notes); the NVDA runs
used the case-hardened v2 system prompt while the MCD runs predate it; and no ranking — the grid
deliberately publishes no single blended number per model.

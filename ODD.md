# Operational due diligence for AI — what this suite measures, in allocator terms

Allocators run operational due diligence on everything a manager does that can lose money without
a market moving: NAV controls, reconciliation, trade confirmation, valuation policy, vendor risk.
ODD's discipline is that it does not accept narrative — it verifies controls against evidence.

Managers are now putting LLMs inside exactly the processes ODD reviews: research digestion,
valuation support, reconciliation triage, document matching. DDQs are catching up with
questions of the form *"do you use AI in the investment or operations process, and what are your
controls?"* — but the answers come back as narrative (a usage policy, a vendor name, a
human-in-the-loop assertion), because there is no established instrument for **verifying an AI
capability claim** the way ODD verifies a reconciliation control. To our knowledge, no public
instrument exists for this. A blended vendor accuracy number is not that instrument: it cannot
say *where* the model fails, and it rewards confident guessing over calibrated refusal.

This suite was not built as an ODD tool — it is a model evaluation benchmark. But the outputs it
produces are the shape that instrument needs, and this page maps them to the questions an ODD
reviewer would actually ask.

## What an ODD-grade capability instrument requires

| requirement | why ODD needs it | where this suite provides it |
|---|---|---|
| **Per-step evidence, not a blended score** | ODD reviews controls step by step; "92% accurate" localizes nothing | every workflow is decomposed into checkpoints (plan → extract → calculate → decide); scores are reported per checkpoint ([`workflow/`](workflow/), [`profiles/`](profiles/)) |
| **Hard-fail detection** | some errors don't cost points, they poison the answer — a scale misread, a fabricated number, settling a basket that doesn't reconcile | rubric **gates**: auto-fails that collapse the score and name the condition (`GATE.SCALE`, `GATE.RECON`, `GATE.MATCH`, `GATE.FABRICATION`; [`rubric/`](rubric/)) |
| **The decision/quantification split** | "did it make the right call" and "are the numbers under the call right" are different control failures with different review responses | decision checkpoints (`D1`) are scored separately from the quantification beneath them (`C*`) — see the finding below |
| **Calibrated-refusal scoring** | a model that guesses when data is missing is an operational risk; one that says "not determinable" is a control working | every eval carries refusal probes scored as a precision-weighted F-beta (fabrication costs more than over-refusal) |
| **Reproducibility and audit trail** | ODD evidence must be re-performable, not taken on faith | committed model answers + deterministic offline regrade; `python -m harness profiles` reproduces every published number byte-for-byte |

## The evidence file

[`profiles/`](profiles/) holds a machine-readable capability profile per model — per-checkpoint
scores, fired gates, refusal calibration, with repo-relative paths from every number back to the
gold case and the committed model answer it was graded from. That file is what "attach evidence to
the DDQ answer" looks like for an AI capability claim.

## A sample DDQ section for AI in the investment process

What the questions could look like when each one demands an artifact rather than a narrative —
with the artifact this suite would attach.

| # | question | evidence that answers it |
|---|---|---|
| 1 | Which workflow steps does an LLM touch, in which processes? | the checkpoint inventory of each workflow the model participates in (here: [`workflow/`](workflow/) — earnings analysis, defined-outcome diligence, DCF support, creation/redemption reconciliation, confirmation matching) |
| 2 | For each step, what evidence supports the model's fitness? | the per-checkpoint vector in [`profiles/<model>.json`](profiles/) — not the blended average |
| 3 | Which error classes would poison downstream work, and are they explicitly tested? | the rubric's `gates:` block per eval; the fired/not-fired record per run (`gates_fired`) |
| 4 | In testing, has the system ever approved a transaction that should have been stopped? | the decision-gate record: across eight frontier models, `GATE.RECON` (settle a broken basket) and `GATE.MATCH` (affirm a mismatched confirmation) never fired — and the clean counterweight cases confirm the models aren't passing by refusing everything |
| 5 | How does the system behave when the source data doesn't contain the answer? | the refusal triple (`R`, `G`, F-beta) per run, driven by planted not-determinable probes |
| 6 | Can the results be re-performed by the reviewer? | yes or it isn't evidence: committed answers + deterministic regrade (`python -m harness profiles`; diff is the audit) |
| 7 | What happens when the vendor updates the model? | re-run the suite; the profile diff **is** the model-change review. Scores here are point-in-time for named model versions |
| 8 | Where does human review sit, and why there? | the decision/quantification split (below) — review placed where the models actually fail, not where the org chart put it |

## The finding that should shape review design

The most consistently replicated result in this suite, across eight models and three vendors:
**frontier models get the stop-or-go decision right and err in the quantification underneath it.**
No model settled the broken basket or affirmed the mismatched trade; what separated them was the
arithmetic below the call — a basis-point conversion missed 10× in *both directions* by two
models, a $200,000 in-kind slip that flipped a shortfall into a fake surplus, a free-cash-flow
figure that disagreed with its own build.

For a reviewer, that inverts the naive control design. The instinct is to have humans re-make the
*decision*. The evidence says the scarce human attention belongs on the *numbers under the
decision* — the tie-out — because that is where these systems actually fail today.

## Scope, stated plainly

- **This is not an ODD opinion, a compliance review, or investment advice.** It is a capability
  measurement whose outputs are structured the way ODD evidence is structured.
- Sample sizes are small (one run per model per case) and cases are point-in-time; the profiles
  are routing priors to be tightened on your own workflows, not certifications.
- Evals #1–#3 and #5 are grounded in real public sources (SEC filings, a published FpML
  confirmation); eval #4's basket file is constructed-but-mechanics-faithful because real PCFs
  are not public — disclosed in the case itself.
- The suite covers five workflows. An ODD review of an AI deployment would scope to the manager's
  actual workflows; the method (checkpoints, gates, refusal probes, reproducible artifacts)
  transfers, the gold cases would be purpose-built.

## Where this goes

Two natural extensions, in order: a sixth eval in the operational core (corporate-actions
processing, in design), and then a purpose-built ODD workflow eval — the questionnaire above
turned into gold cases and gates of its own. If you run diligence on managers using AI, or you're
a manager preparing to answer these questions with artifacts instead of narrative, the harness
and method here are open — [the technical report](https://doi.org/10.2139/ssrn.7243025)
documents the full methodology.

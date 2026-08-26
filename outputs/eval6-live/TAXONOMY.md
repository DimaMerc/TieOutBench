# Eval #6 (corporate-actions processing) — live-run taxonomy

Eight frontier models × six gold cases (48 runs, 2026-08-18), via each vendor's OpenAI-compatible
endpoint (Anthropic `api.anthropic.com`, OpenAI `api.openai.com`, Google
`generativelanguage.googleapis.com/v1beta/openai`). Budgets: Claude 8k (compat endpoint, thinking
uncharged), GPT and Gemini 32k. All runs used the same finalized system prompt and per-case
worksheet schema; Sonnet's first batch drove one prompt clarification (the C3 "changes = ledger
impact, not document diff" sentence) and was re-run in full under the final prompt before any
other model ran, so the committed grid is single-contract.

## The grid (gated scores; * = gate fired)

| Model | split (stale PCF) | split (clean) | tender (proration) | tender (odd-lot) | dividend (corrected) | dividend (clean) |
|---|---:|---:|---:|---:|---:|---:|
| Claude Opus 4.8 | 1.000 AP | 0.920 | 1.000 AP | 1.000 AP | 0.983 | 1.000 AP |
| **Claude Sonnet 4.6** | **1.000 AP** | **1.000 AP** | **1.000 AP** | **1.000 AP** | **1.000 AP** | **1.000 AP** |
| Claude Haiku 4.5 | 1.000 AP | 0.895 | 1.000 AP | 0.983 | 0.983 | 1.000 AP |
| GPT-5.6-sol | 1.000 AP | 1.000 AP | 1.000 AP | 1.000 AP | 0.983 | 1.000 AP |
| GPT-5.5 | 1.000 AP | 1.000 AP | 1.000 AP | 1.000 AP | 0.983 | 1.000 AP |
| GPT-5.4 | 1.000 AP | 1.000 AP | 0.936 | 1.000 AP | 0.983 | 1.000 AP |
| GPT-5.4-mini | 0.840 | 0.920 ·`FABRICATION` | 0.901 | 0.956 | **0.225 ·`VERSION`+`ELECT`** | 0.828 |
| Gemini 3.6 Flash | 1.000 AP | 1.000 AP | 1.000 AP | 1.000 AP | 0.983 | 1.000 AP |

AllPass: 32 of 48 runs. ("AP" = every criterion met, no gate, R=G=1.)

## The findings

1. **The suite's first perfect live row.** Sonnet 4.6 scores 1.000/AllPass on all six cases — no
   live model had ever AllPassed a single case before (prior best anywhere: 0.983). Six of eight
   models sit ≥ 0.92 on every case: the frontier handles document-store corporate-actions episodes
   at a much higher ceiling than the analyst evals — consistent with the tasks being procedural
   where the DCF is judgmental.

2. **The marquee cascade finally happened — on the small tier.** After three evals in which the
   signature decision gates never fired on any live model, GPT-5.4-mini committed the full
   supersedence cascade on the corrected dividend: it **pinned the correct v2 8-K, stated the
   corrected record date — and then computed the entitlement on the superseded 50,000-share
   position and booked $8,500** (gold: 40,000 × $0.17 = $6,800 to the 2024-08-23 record). Wrong
   number, released as an instruction: `GATE.VERSION` (superseded values in the worksheet) and
   `GATE.ELECT` (a release no gold-permissible amount matches) both fired, gated 0.225 against an
   ungated 0.574 — the *looks-right-is-wrong* gap the eval exists to surface. The refined
   through-line: **flagships still never commit the catastrophic action; the small tier now does**
   — and it is the same model whose calibration failures evals #3–#4 flagged.

3. **"Derive the right number, report a different one" replicates in a third domain.** The class
   first seen on the eval-3 NVDA WACC probe reappears on the D2 twin: Haiku's twin derivation
   computes "180,000 × $0.01 = **$1,800.00**" and its value field says **18,000**; GPT-5.4-mini's
   derivation computes 1,800 and its answer field says **180,000 — labeled COMPUTED**, on a
   net-cash probe the store does not determine (its `GATE.FABRICATION`).

4. **A real trap materialized exactly where it was planted: the split/dividend double-count.** On
   the *clean* split case, Opus and Haiku both answered the gross-dividend twin as ~$18,000 — the
   **pre-split $0.10 rate applied to the post-split 180,000 shares** (or its equivalent) — a
   classic corporate-actions error induced by the second event embedded in the same 8-K. Notably
   both models got the same twin right on the break-case variant of the identical store: the
   already-adjusted PCF context is what triggered the slip.

5. **The unlabeled traps caught nobody; the labeled distractors are a floor, not a feat.** No
   model recomputed the naive 47.56% (56.6M/119.0M) in place of the depositary's stated 47.18%,
   and on the odd-lot case every model accepted the odd lot in full rather than applying the
   factor to a holder the rule exempts — those two traps carry no label in the store. The
   distractor documents (the fictional QSEM split, the real Incyte tender, the broker memos) are
   labeled as distractors in their document types/titles, so the fact that no model used their
   values is the expected minimum, not a finding.

6. **The remaining losses are quantification and completeness, not decisions.** GPT-5.4 left both
   price-range terms null (they are in the Offer to Purchase, in the store) — the omission
   pattern; the 0.983 cluster on the corrected dividend is partial impact-localization; mini's
   0.83–0.84 cells (split, clean dividend) are vague, unclassifiable decision lines that carry no
   processing verb — its tender cell sat there too until the wave-3 fix below (0.840 → 0.901).

## Grader log (the grader-bug law, round five — its largest round)

Live answers surfaced **grader-contract gaps in two waves, every one a false fire on a correct
answer, every fix moving scores UP** (the planted-flaw battery pins the other direction; all 53
gaming-review regression checks and the full-suite selftest re-verified after each fix):

*Wave 1 (Sonnet first batch):* citation quoting the OTHER accepted governing document (verified
against the document body now); the "elect-shaped fields" heuristic firing on results-booking rows
(killed — an elect verb or offer-directed language is required); identifiers (`mnst-otp-20240508`,
`ACCT-7712`, `W-8BEN`) read as fabricated figures (stripped); one **gold bug** (the correction
8-K's date); prose on a boolean field (excluded from the count); the offer's own rule text
("holders who tender all their shares...") classing as an election; `factor_used: null` beside
`proration_applies: false` (the desk's "n/a" = 1.0).

*Wave 2 (the 7-model grid):* adjectival "tender" ("book accepted tender shares", "gross tender
cash receivable", "tender suspense") classing as an elect verb — the mechanism behind seven of
eight first-pass `GATE.ELECT` firings, all cleared on regrade (the eighth, mini's, is the real
one); "no election **or tender action** required" surviving negation-stripping; the custody idiom
"hold for settlement/entitlement" classing as escalation; snake_case decision enums
(`UPDATE_PCF`) defeating word boundaries — the exact bug class the eval-3 audit documented;
"purchase price tender" (a tender-type noun) re-exposed by underscore normalization; and the
refusal grader's absent-word list missing "is not present / contains no / lacks / does not
provide", plus cross-sentence anaphora ("...the Letter of Transmittal... **This document** is
absent") defeating clause-local prong matching (prongs are now derivation-wide with a length
guard). Direction note: every live-surfaced fix raised scores (false fires); the planted battery
and the 53 gaming-review checks pin the opposite direction, so the grader cannot drift lax.

*Wave 3 (2026-08-26, surfaced by the content review of the eval-6 write-up):* the fix for the
"hold for settlement" idiom had replaced it with the word "awaiting" — which re-triggered the
HOLD classifier, so GPT-5.4-mini's tender decision ("hold for settlement of accepted tender
shares") was still being penalized as an over-escalation. Replaced with a neutral token; that
one cell moved 0.840 → 0.901 (no gate either way); no other run changed. The full gaming-review
suite — the 35 attacker findings plus the live-wave false fires, 59 checks — is now committed as
`harness/gaming_review_eval6.py` and runs inside `python -m harness selftest`, so a grader change
that reopens any of them fails the selftest.

## Scope notes

- One run per model per case; scores are point-in-time for the model versions named.
- The corporate actions are real and cited (NVDA split 8-Ks, MNST tender SC TO-I + results, BRY
  and ZTS corrected-dividend 8-K pairs); the ETF wrapper, PCF, accounts, and position reports are
  constructed and disclosed in each case file.
- Deterministic mock-judge grading throughout (no LLM judge); the D2 refusal grader's substring
  limits are documented in the suite module.
- Reproduce any cell offline: `python -m harness run --case <case>` grades the committed
  `answer.json` via `run_case(..., model_output=...)`; `python -m harness profiles` regenerates
  the machine-readable grid.

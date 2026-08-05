# Leaderboard — every live model run in this suite

One page, every real model this suite has graded so far — with the caveats stated **before** the
numbers: sample sizes are small (one run per model per case), evals **#3–#5** now cover **eight
frontier models across three vendors** (four OpenAI, three Anthropic, one Google) — eval #3 on
**two gold cases** (McDonald's, a net-debt balance sheet; NVIDIA, its net-cash mirror) — evals
**#1–#2** have been run only against local open-weight models (two Qwen generations), and eval
#5's swap-inside-an-ETF case pair has not been live-run yet. Google is represented only by a flash-tier
model, since its pro line is a generation behind. The harness takes any OpenAI-compatible endpoint
(`--model live --endpoint <url> --model-id <model>`), so adding a vendor is a run, not a rebuild —
though, as the methodology note below records, not a *free* one.

**How to read the scores.** Every eval reports a **gated** score: point-weighted, tiered rubric
criteria, collapsed by auto-fail **gates** when a model commits one of the errors that quietly
poison real work — a unit/scale slip, a wrong fiscal period, a fabricated number, settling a
basket that doesn't reconcile, affirming a confirmation that doesn't tie. A model can score ~0.95
on a naive average and ~0.45 gated; **the gap is the finding.** Mechanics:
[README → How the scoring works](README.md#how-the-scoring-works-30-more-seconds).

## Frontier runs — evals #3–#5, three vendors, eight models

Models as rows, cases as columns. Gate names abbreviated; each is `GATE.<NAME>`.

| Model | Tier | #3 DCF (MCD) | #3 DCF (NVDA) | #4 recon (break) | #4 clean | #5 confirm (break) | #5 clean |
|---|---|---:|---:|---:|---:|---:|---:|
| **Claude Opus 4.8** | flagship | **0.965** | 0.974 | **0.983** | 0.983 | **0.980** | 0.980 |
| Claude Sonnet 4.6 | mid | 0.955 | 0.973 | 0.943 | 0.983 | 0.933 | 0.980 |
| Claude Haiku 4.5 | small | 0.692 · `C1FCF` | 0.799 | 0.496 · `SCALE` | 0.983 | 0.933 | 0.980 |
| **GPT-5.6-sol** | flagship | 0.951 | 0.970 | 0.943 | 0.973 | **0.980** | 0.980 |
| GPT-5.5 | flagship (prev.) | 0.953 | 0.970 | 0.943 | 0.983 | **0.980** | 0.980 |
| GPT-5.4 | mid | 0.903 | 0.883 | **0.983** | 0.973 | **0.980** | 0.980 |
| GPT-5.4-mini | small | 0.631 · `FALSEPRECISION` | 0.650 · `BRIDGE` | 0.714 | 0.983 | 0.933 | 0.980 |
| **Gemini 3.6 Flash** | small/fast | 0.922 | 0.970 | **0.983** | 0.973 | **0.980** | 0.980 |

Anthropic models ran via the OpenAI-compatible endpoint at `api.anthropic.com`, OpenAI at
`api.openai.com`, Google at `generativelanguage.googleapis.com/v1beta/openai`.

### The methodology finding — every vendor meters the budget differently

The cross-vendor runs broke the harness three separate times, and every breakage would have
published as a capability finding. The unifying lesson: **you cannot compare models across vendors
until you have proved the harness gives each one equivalent room**, and each vendor meters that
differently.

| Vendor | Budget field | Thinking counts against it? | Thinking visible in `usage`? |
|---|---|---|---|
| Anthropic | `max_tokens` | no (via the compat endpoint) | — |
| OpenAI | `max_completion_tokens` only — rejects `max_tokens` | **yes** | reported |
| Google | `max_tokens` | **yes** | **no** — only in `total_tokens` |

Google's is the quietest failure of the three. A trivial eight-token smoke test returned
`completion_tokens: 3` and `total_tokens: 124` — 113 thinking tokens spent and invisible in the
field a harness would naturally read. Size budgets from `completion_tokens` and you would starve
Gemini forever without ever seeing why.

OpenAI's version cost four wrong numbers before it was caught. The same 8,000-token cap had already
truncated one Claude run on this case (see `outputs/eval3-live/TAXONOMY.md`, which is why the
live-path floor was raised to 12k) — but as a single incident it read as a quirk of that run rather
than a rule. Under OpenAI's accounting it starved *every* GPT model on the one long case (DCF,
~4.4k-token prompt), and the damage looked exactly like incompetence rather than truncation:

| Model · DCF | @ 8k budget (starved) | @ 32k budget (fair) |
|---|---:|---:|
| GPT-5.5 | *empty completion* | **0.953** — no gates |
| GPT-5.6-sol | 0.322 · **six gates fired** | **0.951** — no gates |
| GPT-5.4 | 0.618 · `FALSEPRECISION` | **0.903** — gate cleared |
| GPT-5.4-mini | 0.745 | 0.631 · `FALSEPRECISION` *(genuine — see below)* |

Six gates firing at once is the signature of a truncated answer, not a coherent error. An eval
that gives one vendor less effective room than another measures configuration, not capability —
the cross-vendor form of *looks right ≠ is right*. One vendor's truncation read as a quirk; a
second vendor's turned it into a rule.

The client needed one more fix to get there: OpenAI's GPT-5 family rejects `max_tokens` outright in
favour of `max_completion_tokens`, so every call failed at the HTTP layer until the client learned
to flip the field on that 400. Every left-hand number in the table above is wrong, and none of them
announced itself as an error.

### What the eight models actually show

- **The marquee decision gates still never fire — now across three vendors and eight models.**
  Nobody affirmed the broken trade (`GATE.MATCH`), nobody settled the short basket (`GATE.RECON`),
  and nobody cried false break on the clean counterweights. What began as a single-family caveat
  now reads as a property of the task: frontier models get the *stop-or-go* call right, and lose
  points on the arithmetic underneath it. That is the most consistently replicated result in the
  suite.
- **The top tiers have converged.** Opus 4.8, GPT-5.6-sol, and GPT-5.5 sit within 0.04 of each
  other on every case, and within 0.015 on five of the six. On confirmation matching five models tie at the 0.980 ceiling — the eval no
  longer separates the frontier there, which is itself a finding about the task.
- **Cheap is no longer a proxy for undeployable.** Two vendors' small tiers fail badly, and each
  fails in its own way: Haiku 4.5 on arithmetic (a $200,000 in-kind overstatement flipping the
  residual sign, `GATE.SCALE`; a free-cash-flow figure disagreeing with its own build,
  `GATE.C1FCF`), GPT-5.4-mini on calibration (a decimal-precise $200.20 fair value, 12% below gold,
  with the growth sensitivity left **null** on a valuation that is 79.5% terminal value,
  `GATE.FALSEPRECISION`). **Gemini 3.6 Flash breaks the pattern outright**: a flash-tier model
  fires no gate anywhere, ties Opus for the best reconciliation score on the board (0.983 — correct
  `DO_NOT_SETTLE`, right offending line, right root cause, residual to the dollar), and lands its
  DCF fair value at **$227.81 against a gold of $227.82**, one cent apart, with genuine sensitivity
  ranges on both drivers. Price tier and deployability are not the same axis.
- **A stub that passes the label and fails the reasoning.** On the reconciliation refusal probe,
  GPT-5.4-mini returns the right label (`NOT_DISCLOSED`, value `null`) but its stated derivation is
  the prompt's own instruction echoed back verbatim, and its answerable twin comes back at
  −$33,320 against the correct −$13,320. Grading only the refusal label scores this correct.

### Verification note

The `GATE.FALSEPRECISION` firing on GPT-5.4-mini was re-checked against the models that cleared it,
because a gate that fires only on a new vendor is exactly what a grader bug looks like. It holds:
GPT-5.5 and GPT-5.4 both return complete `g_sensitivity_per_share` ranges (205.1/227.9/256.1 and
204.8/226.1/251.7); GPT-5.4-mini returns `{g_low: null, base: 200.2, g_high: null}`. The gate
requires a genuine numeric range on *both* sensitivities. It fired for the reason it exists.

### What separated the models

- **#5 — the basis-point conversion.** All three models matched the confirmations correctly and
  returned MISMATCHED on the 6.05%-vs-6.00% break. Only Opus sized it right (~5 bp ≈ EUR 25k/yr on
  EUR 50MM). Sonnet called it "0.5 bp" (EUR 2,500/yr — 10× low); Haiku called it "50 bp" (10×
  high — and its EUR 2,500,000 figure is a *lifetime* number, 20× the correct ≈EUR 125k over the
  remaining term). Same trap, opposite directions, localized to one checkpoint
  (`C3.impact`). [Full traces](outputs/eval5-live/)
- **#4 — a $200,000 arithmetic slip.** Opus and Sonnet reconciled to the dollar (residual exactly
  −$13,320, DO_NOT_SETTLE localized to the right line). Haiku overstated the in-kind value by
  exactly $200k, flipping the residual sign — it concluded the basket was *over*-delivered when it
  was short. Right refusal, wrong diagnosis; `GATE.SCALE` pinned it. [Full traces](outputs/eval4-live/)
- **#3 — an FCF that doesn't equal its own build.** Opus and Sonnet produced textbook DCFs
  (fair value ~$228 vs gold $227.82). Haiku's reported free cash flow carried a +$2B/yr offset from
  its own components; `GATE.C1FCF` flagged it at the checkpoint and the error cascaded to a wrong
  $138 valuation. All three showed the same framing quirk: they *derive* the ~7.15% discount rate
  correctly, then answer "not disclosed" with a null value when asked for the WACC per the 10-K —
  declining to claim the derived figure as the answer (most restate it inside their derivation
  text). [Full traces](outputs/eval3-live/)
- **#3 (NVDA) — the mirror bridge, and a new failure class.** On the net-cash case the classic
  EV÷shares blunder *understates* fair value by only ~3% (vs MCD's +22% overstatement) — and the
  one model that fired `GATE.BRIDGE` (GPT-5.4-mini) failed the bridge in its subtler form: it
  added the $54.1B net cash but **dropped the $22.3B non-op add** it had itself extracted. Five
  models (Opus, Sonnet, GPT-5.6-sol, GPT-5.5, Gemini Flash) land within **0.004** of each other,
  gate-free, at $91.7 vs gold $91.67. And two models from two vendors exhibited the same new
  failure on the WACC probe — **derive the right number, report a different one**: Haiku's
  derivation builds 12.62 and answers 12.51 (then uses 12.51 consistently downstream); GPT-5.4's
  derivation text literally ends "= 12.62174%" and its answer field says 12.31, contradicting its
  own C2. Label-only grading calls both "computed." [Full traces](outputs/eval3-live/nvda-fy2026-dcf/)

### The honest negatives

The marquee decision gates **never fired on a frontier model**: no model settled the broken basket
(`GATE.RECON`) or affirmed the broken trade (`GATE.MATCH`), and none cried break/mismatch on the
clean counterweight cases. On these runs the frontier capability gap lives in the *quantification*
(the bp conversion, the $200k slip), not the *decision*. Stated plainly because a benchmark that
only reports its hits isn't one.

## Open-weight local runs — evals #1–#2

**Eval #1 (earnings, Snowflake FQ2-2026) — Qwen2.5-32B-Instruct**, local, press-release packet:
**0.532** with a real LLM judge (0.679 with the permissive mock judge). The split is the finding: a
competent *extractor* (segments/shares 0.91, EPS bridge 0.70, beat/miss 0.83) but a weak *analyst*
— its "material changes" synthesis listed surface metrics and missed the +1,118 bps GAAP-margin
swing; it correctly refused the not-disclosed probe. Feeding the 10-Q barely moved the score — the
ratio failures were computation failures, not data starvation. [Details](outputs/README.md)

**Eval #2 (buffer-ETF diligence, real Innovator fund, three market snapshots):**

| Case | qwen3.6-27b (reasoning) | qwen2.5-72b (non-reasoning) |
|---|---:|---:|
| anchor | **0.732** | 0.638 |
| post-rally | **0.708** | 0.584 · `GATE.C6DIR` |
| post-drawdown | **0.702** | 0.577 · `GATE.C6DIR` |

The 27B reasoning model beat the 72B non-reasoning model on every case despite a 2.7× size
disadvantage. Both nailed extraction (0.86–0.91) and the headline remaining-cap calculation, and
both fell into the same payoff-grid conflation — two subjects, one lineage, so a cross-family
replication is the honest next step before calling it task-level. [Taxonomy](outputs/eval2-live/TAXONOMY.md)

## Scope notes

- Evals #1–#2 have not been run against frontier models; evals #3–#5 have not been run against
  open-weight models. The grid will fill in as runs accumulate.
- GPT runs used a 32,000-token completion budget on the DCF cases and 8,000 elsewhere (the shorter
  cases scored at ceiling and were never budget-limited). Gemini used 32,000 throughout. Claude
  runs used 8,000 on the short cases and the 12,000-token live-path floor on the MCD DCF case
  (Sonnet's committed run completed at 16,000 after an 8k truncation — see the methodology
  note above) and 16,000 on the NVDA DCF case; the compat endpoint does not charge thinking
  against the budget.
- The NVDA DCF runs used the case-hardened v2 system prompt (it states the net-debt/cash-like
  netting convention and the 3×3 grid geometry — added after a pre-ship audit showed the netting
  convention was graded but never taught). The MCD runs predate it; cross-case comparisons on
  those two behaviors are hedged in the [NVDA taxonomy](outputs/eval3-live/nvda-fy2026-dcf/TAXONOMY.md),
  which also logs the three grader-contract gaps this case's first live batch surfaced (all fixed,
  all runs re-graded, MCD reports unchanged).
- Eval #5's second case pair (the same confirmation-matching control on a swap held *inside an
  ETF*) ships with gold cases and taxonomy but no live run yet.
- Every number above is reproducible from the artifacts in [`outputs/`](outputs/) — parsed
  answers, raw completions, scored reports — or re-runnable via
  `python -m harness run --case <case> --model live ...`.

## What's next

Frontier runs on evals #1–#2 (still open-weight only); a Gemini pro-tier model once Google ships
one current; the ETF-swap pair live; and eval #6 (in design: corporate-actions processing — the
back-office domain with a documented $58B/yr industry cost and, as of mid-2026, no independently
published accuracy metrics).

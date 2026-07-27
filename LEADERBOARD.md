# Leaderboard — every live model run in this suite

One page, every real model this suite has graded so far — with the caveats stated **before** the
numbers: sample sizes are small (one run per model per case), evals **#3–#5** now cover **seven
frontier models across two vendors** (four OpenAI, three Anthropic), evals **#1–#2** have been run
only against local open-weight models (two Qwen generations), and eval #5's swap-inside-an-ETF case
pair has not been live-run yet. Google models are the next family; the harness takes any
OpenAI-compatible endpoint (`--model live --endpoint <url> --model-id <model>`), so adding a vendor
is a run, not a rebuild — though, as the methodology note below records, not a *free* one.

**How to read the scores.** Every eval reports a **gated** score: point-weighted, tiered rubric
criteria, collapsed by auto-fail **gates** when a model commits one of the errors that quietly
poison real work — a unit/scale slip, a wrong fiscal period, a fabricated number, settling a
basket that doesn't reconcile, affirming a confirmation that doesn't tie. A model can score ~0.95
on a naive average and ~0.45 gated; **the gap is the finding.** Mechanics:
[README → How the scoring works](README.md#how-the-scoring-works-30-more-seconds).

## Frontier runs — evals #3–#5, two vendors, seven models

| Eval · case | Opus 4.8 | Sonnet 4.6 | Haiku 4.5 | GPT-5.6-sol | GPT-5.5 | GPT-5.4 | GPT-5.4-mini |
|---|---:|---:|---:|---:|---:|---:|---:|
| **#3 DCF** — McDonald's FY2025 | **0.965** | 0.955 | 0.692 · `C1FCF` | 0.951 | 0.953 | 0.903 | 0.631 · `FALSEPRECISION` |
| **#4 Creation/redemption** — break | **0.983** | 0.943 | 0.496 · `SCALE` | 0.943 | 0.943 | **0.983** | 0.714 |
| **#4** — clean-settle counterweight | 0.983 | 0.983 | 0.983 | 0.973 | 0.983 | 0.973 | 0.983 |
| **#5 Confirmation matching** — break | **0.980** | 0.933 | 0.933 | **0.980** | **0.980** | **0.980** | 0.933 |
| **#5** — clean-match counterweight | 0.980 | 0.980 | 0.980 | 0.980 | 0.980 | 0.980 | 0.980 |

Gate names are abbreviated; each is `GATE.<NAME>`. Anthropic models were run via the
OpenAI-compatible endpoint at `api.anthropic.com`, OpenAI models at `api.openai.com`.

### The methodology finding — reasoning tokens are not free

The first cross-vendor run broke the harness twice before it produced a single comparable number,
and both breakages would have published as capability findings:

1. **The client.** OpenAI's GPT-5 family rejects `max_tokens` and requires `max_completion_tokens`.
   Every call failed at the HTTP layer until the client learned to flip the field on that 400.
2. **The budget — the dangerous one.** OpenAI counts *reasoning* tokens against the completion
   budget; Anthropic's compatible endpoint does not. So an 8,000-token cap that was ample for every
   Claude model silently starved every GPT model on the one long case (DCF, ~4.4k-token prompt).
   The damage was invisible as a crash and looked exactly like incompetence:

   | Model · DCF | @ 8k budget (starved) | @ 32k budget (fair) |
   |---|---:|---:|
   | GPT-5.5 | *empty completion* | **0.953** — no gates |
   | GPT-5.6-sol | 0.322 · **six gates fired** | **0.951** — no gates |
   | GPT-5.4 | 0.618 · `FALSEPRECISION` | **0.903** — gate cleared |
   | GPT-5.4-mini | 0.745 | 0.631 · `FALSEPRECISION` *(genuine — see below)* |

   Every one of those left-hand numbers is wrong. Six gates firing at once is the signature of a
   truncated answer, not a coherent error. An eval that gives one vendor less effective room than
   another is measuring configuration, not capability — the cross-vendor form of *looks right ≠ is
   right*, and it is only visible once a second vendor is in the harness.

### What the seven models actually show

- **The top tiers have converged.** Opus 4.8, GPT-5.6-sol, and GPT-5.5 are within ~0.03 of each
  other on every case. Opus keeps a real edge on creation/redemption (0.983 vs 0.943), where it
  reconciles to the dollar; on confirmation matching four models tie at the 0.980 ceiling.
- **The marquee decision gates still never fire — now across two vendors and seven models.**
  Nobody affirmed the broken trade (`GATE.MATCH`), nobody settled the short basket (`GATE.RECON`),
  and nobody cried false break on the clean counterweights. What was a single-family caveat now
  looks like a property of the task: frontier models get the *stop-or-go* call right, and lose
  points on the arithmetic underneath it.
- **Small tiers fail — but differently by vendor.** Haiku 4.5 breaks on arithmetic: a $200,000
  in-kind overstatement that flips the residual sign (`GATE.SCALE`), and a free-cash-flow figure
  that disagrees with its own build (`GATE.C1FCF`). GPT-5.4-mini breaks on calibration: it asserts
  a decimal-precise $200.20 fair value — 12% below gold — while leaving the growth-rate
  sensitivity **null** on a valuation that is 79.5% terminal value (`GATE.FALSEPRECISION`). Both
  vendors' cheap tiers are undeployable here; the eval says *why*, and the answers differ.
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
  EUR 50MM). Sonnet called it "0.5 bp" (EUR 2,500 — 10× low); Haiku called it "50 bp"
  (EUR 2,500,000 — 10× high). Same trap, opposite directions, localized to one checkpoint
  (`C3.impact`). [Full traces](outputs/eval5-live/)
- **#4 — a $200,000 arithmetic slip.** Opus and Sonnet reconciled to the dollar (residual exactly
  −$13,320, DO_NOT_SETTLE localized to the right line). Haiku overstated the in-kind value by
  exactly $200k, flipping the residual sign — it concluded the basket was *over*-delivered when it
  was short. Right refusal, wrong diagnosis; `GATE.SCALE` pinned it. [Full traces](outputs/eval4-live/)
- **#3 — an FCF that doesn't equal its own build.** Opus and Sonnet produced textbook DCFs
  (fair value ~$228 vs gold $227.82). Haiku's reported free cash flow carried a +$2B/yr offset from
  its own components; `GATE.C1FCF` flagged it at the checkpoint and the error cascaded to a wrong
  $138 valuation. All three showed the same framing quirk: they *derive* the ~7.15% discount rate
  correctly, then answer "not disclosed" when asked for the WACC per the 10-K — without
  volunteering the figure they just computed. [Full traces](outputs/eval3-live/)

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
- GPT runs used a 32,000-token completion budget on the DCF case and 8,000 elsewhere (the shorter
  cases scored at ceiling and were never budget-limited). Claude runs used 8,000 throughout.
- Eval #5's second case pair (the same confirmation-matching control on a swap held *inside an
  ETF*) ships with gold cases and taxonomy but no live run yet.
- Every number above is reproducible from the artifacts in [`outputs/`](outputs/) — parsed
  answers, raw completions, scored reports — or re-runnable via
  `python -m harness run --case <case> --model live ...`.

## What's next

Cross-family frontier runs (GPT, Gemini) to lift the single-family caveat; frontier runs on
evals #1–#2; the ETF-swap pair live; and eval #6 (in design: corporate-actions processing — the
back-office domain with a documented $58B/yr industry cost and, as of mid-2026, no independently
published accuracy metrics).

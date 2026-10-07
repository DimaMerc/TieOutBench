# Leaderboard — every live model run in this suite

One page, every real model this suite has graded so far — with the caveats stated **before** the
numbers: sample sizes are small (one run per model per case), evals **#3–#7** now cover **eight
frontier models across three vendors** (four OpenAI, three Anthropic, one Google) — eval #3 on
**two gold cases** (McDonald's, a net-debt balance sheet; NVIDIA, its net-cash mirror), eval #6
on **six gold cases** (the document-store corporate-actions episodes), eval #7 on **two gold cases**
(the NAV-oversight break and its clean mirror) — evals
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

## Eval #6 — corporate-actions processing (the first document-store episode)

Six gold cases: a real stock split hitting an ETF basket (stale-PCF break + clean twin), a real
oversubscribed self-tender (proration break + odd-lot counterweight), and a real corrected-dividend
pair (material supersedence + economically-neutral twin). "AP" = AllPass (every criterion met, no
gate, calibrated refusal perfect).

| Model | split (stale) | split (clean) | tender | tender (odd-lot) | dividend (corrected) | dividend (clean) |
|---|---:|---:|---:|---:|---:|---:|
| Claude Opus 4.8 | 1.000 AP | 0.920 | 1.000 AP | 1.000 AP | 0.983 | 1.000 AP |
| **Claude Sonnet 4.6** | **1.000 AP** | **1.000 AP** | **1.000 AP** | **1.000 AP** | **1.000 AP** | **1.000 AP** |
| Claude Haiku 4.5 | 1.000 AP | 0.895 | 1.000 AP | 0.983 | 0.983 | 1.000 AP |
| GPT-5.6-sol | 1.000 AP | 1.000 AP | 1.000 AP | 1.000 AP | 0.983 | 1.000 AP |
| GPT-5.5 | 1.000 AP | 1.000 AP | 1.000 AP | 1.000 AP | 0.983 | 1.000 AP |
| GPT-5.4 | 1.000 AP | 1.000 AP | 0.936 | 1.000 AP | 0.983 | 1.000 AP |
| GPT-5.4-mini | 0.840 | 0.920 · `FABRICATION` | 0.901 | 0.956 | **0.225 · `VERSION`+`ELECT`** | 0.828 |
| Gemini 3.6 Flash | 1.000 AP | 1.000 AP | 1.000 AP | 1.000 AP | 0.983 | 1.000 AP |

- **The suite's first perfect live row**: Sonnet 4.6 at 1.000/AllPass on all six cases (no live
  model had AllPassed a single case before; 32 of 48 runs AllPass here). The frontier handles
  procedural corporate-actions episodes at a far higher ceiling than the analyst evals.
- **The marquee cascade finally happened — on the small tier.** GPT-5.4-mini pinned the correct
  correction 8-K, stated the corrected record date, then computed the entitlement on the
  **superseded 50,000-share position and booked $8,500** (gold $6,800 on 40,000) — a release on
  superseded terms, `GATE.VERSION` + `GATE.ELECT`, gated 0.225 vs 0.574 ungated. Flagships still
  never commit the catastrophic action; the small tier now does.
- **"Derive the right number, report a different one" replicates in a third domain**: Haiku's
  refusal-twin derivation computes "$1,800.00" and reports 18,000; mini's computes 1,800 and
  reports 180,000 as COMPUTED (its fabrication gate). And a genuinely new trap fired where it was
  planted: on the *clean* split case Opus and Haiku both answered the dividend twin at the
  pre-split rate × post-split shares — the classic split/dividend double-count.
- **The unlabeled traps caught nobody**: no model used the naive 47.56% recompute in place of
  the depositary's stated 47.18%, and every model accepted the odd lot in full rather than
  prorating an exempt holder. (The distractor documents are labeled as such in the store, so no
  model borrowing their values is the expected minimum, not a finding.) Full traces:
  [`outputs/eval6-live/`](outputs/eval6-live/) and its [taxonomy](outputs/eval6-live/TAXONOMY.md).

### Eval #6, Phase 2 — the agent environment (tools, and a checker)

The same six cases, eight models and grader, run three ways on 2026-09-24: **plain** (the Phase-1
grid above), **tools** (no store in the prompt; the model lists and reads documents, queries the
position as of a date, calculates, and books through action tools, then submits the worksheet),
**checker** (the tools arm's work product reviewed by a second agent of the same model with the
discovery tools; one revision round), and **checker-fixed** (the same work products reviewed by
Claude Opus 4.8 for every maker; run 2026-09-25). The worksheet is graded by the unchanged Phase-1
grader; the ledger is rendered into action rows and graded by the same code, so `GATE.ELECT` fires
on what was booked. AllPass per model, of six cases:

| Model (maker) | plain | tools | checker | checker-fixed | Notes |
|---|---:|---:|---:|---:|---|
| Claude Opus 4.8 | 4 | 5 | 5 | 3 | the same 0.983 partial on the corrected dividend in every arm and every repeat; two `FABRICATION` under the fixed reviewer (its own model) |
| **Claude Sonnet 4.6** | **6** | **6** | **6** | 5 | twelve of twelve on the repeats across four arms |
| Claude Haiku 4.5 | 3 | 2 | 1 | 1 | `GATE.DATES` on both tenders with tools (deadline field left empty; ledgers right); reviewer-induced errors in both review arms |
| GPT-5.6-sol | 5 | 6 | 4 | 4 | text protocol (the compat endpoint refuses function tools for it); correct receivables un-booked after the reviewer objected to the pay date (self-review); two `FABRICATION` (fixed) |
| GPT-5.5 | 5 | 5 | 4 | 4 | one receivable un-booked (self-review); one `FABRICATION` (fixed) |
| GPT-5.4 | 4 | 6 | 3 | **6** | two `FABRICATION` after self-review revisions; clean under the fixed reviewer |
| GPT-5.4-mini | 0 | 0 | 0 | 0 | tools: reversed the clean basket (1,800 to 180) and booked $180; wrong on the stale basket's worksheet with a correct ledger |
| Gemini 3.6 Flash | 5 | 5 | 4 | 2 | one `FABRICATION` (self-review); three (fixed) |
| **All 48 cells** | **32** | **35** | **27** | **25** | cells with a gate: 2, 4, 8, 14; `GATE.ELECT`: 1, 0, 0, 0; ledgers correct: n/a, 46, 44, 46 |

- **Tools helped the middle tier and hurt the small one.** GPT-5.4 four to six, GPT-5.6-sol five
  to six, Opus four to five; Haiku three to two, and GPT-5.4-mini's split cases collapsed.
- **The marquee gate did not fire in the recorded tools cells, and the repeats say why that is
  not the result.** Five tools-arm attempts by the small model on the corrected dividend (five saved
  trajectories, not five identical trials; the first stopped on a harness error after the
  booking was saved): two
  booked $8,500 without ever calling `get_position`; three booked $6,800 after querying the
  position as of the desk's date rather than the record date. The tool was there in every run.
- **The checker made the work worse.** Reviewers recomputed (48 of 48 queried the position) and
  then rejected 20 of 46 correct ledgers and approved one of two wrong ones; the makers complied
  and the revisions put a gate on four cells that had none and un-booked or held a correct
  receivable in three. Read finding by finding, 7 of the 20 rejections raise at least one
  objection the documents support, five of them a payment date the booking tool requires and
  no document states (TAXONOMY, finding 12). Round-one two-by-two: reject/wrong 1, reject/correct 20, approve/wrong 1,
  approve/correct 26.
- **A stronger fixed reviewer was better on the verdicts and worse on the probe.** Opus
  reviewing every maker: 13 correct ledgers rejected instead of 20, 33 approved instead of 26,
  the same two wrong ledgers caught and missed, 46 of 48 ledgers correct. Ten of its thirteen
  rejections of correct ledgers over-ruled a correct refusal: nine said the fund is U.S.-domiciled, so no
  withholding applies and the net equals the gross, and one said no fees apply to the tender.
  The maker complied each time (six makers, ten cells), and `GATE.FABRICATION` fired ten times on
  worksheets that had refused
  the probe correctly before the review. AllPass 25. Round-one two-by-two:
  reject/wrong 1, reject/correct 13, approve/wrong 1, approve/correct 33.
- **Transport.** Native function calling on all three compat endpoints for seven models; GPT-5.6-sol
  on the text protocol (disclosed per cell in `run.json`), six of six with tools.
- Repeats (three per cell, corrected dividend, all arms), the trajectory rates, and the grader log
  (six environment-contract fixes, a reviewer-packet fix with the arm re-run, and eight Phase-1
  false fires pinned by regression checks; no committed Phase-1 headline number moved) are in
  [`outputs/eval6-agent/TAXONOMY.md`](outputs/eval6-agent/TAXONOMY.md). Artifacts:
  [`outputs/eval6-agent/`](outputs/eval6-agent/).

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

Through evals #3–#5 the marquee decision gates **never fired on a frontier model**: no model
settled the broken basket (`GATE.RECON`) or affirmed the broken trade (`GATE.MATCH`), and none
cried break/mismatch on the clean counterweight cases. On those runs the frontier capability gap
lived in the *quantification* (the bp conversion, the $200k slip), not the *decision*. **Eval #6
refines that finding rather than repeating it**: across 48 corporate-actions runs the flagships
still never committed the catastrophic action — but the small tier finally did (GPT-5.4-mini's
release on superseded terms), which is what the temporal, multi-document format was built to
test. Stated plainly because a benchmark that only reports its hits isn't one.

## Eval #7 — ETF NAV oversight (the "release only if it ties" control)

Two gold cases, both constructed and mechanics-faithful (a NAV package is not a public document; real
underlying ETF and index, fictitious fund): a fund administrator's preliminary NAV with one total return
swap carried at the prior day's mark after the counterparty file missed the pricing cut-off (NAV
understated 0.7500 a share, 1.44%, gold HOLD), and the clean mirror where the file arrived on time (gold
RELEASE). The same eight models, one run per model per case, 2026-10-05. "AP" = AllPass.

| Model | Tier | Break case (stale swap mark) | Clean case |
|---|---|---:|---:|
| **Claude Opus 4.8** | flagship | **1.000 AP** | **1.000 AP** |
| Claude Sonnet 4.6 | mid | 0.972 | **1.000 AP** |
| Claude Haiku 4.5 | small | 0.964 | 0.986 |
| **GPT-5.6-sol** | flagship | **1.000 AP** | **1.000 AP** |
| **GPT-5.5** | flagship (prev.) | **1.000 AP** | **1.000 AP** |
| GPT-5.4 | mid | 0.972 | 1.000 AP |
| GPT-5.4-mini | small | **0.633** | 1.000 AP |
| Gemini 3.6 Flash | small/fast | 0.956 | **1.000 AP** |

- **Ten of sixteen runs AllPass; no gate fired in any run.** All eight models HOLD the wrong NAV,
  localize it to the stale swap line and recompute the NAV (seven of eight at 51.9912); all eight RELEASE the
  clean one (no false hold). Three models AllPass both cases - the suite's first AllPasses on a reconciliation-type break case
  (evals #4 and #5 capped at 0.983 on a citation miss); Gemini 3.6 Flash AllPasses the clean case and loses its
  break-case AllPass only to a refusal reason that echoed the answer schema's own text. All eight refuse the D2 probe correctly: no model
  invented an exchange closing price or assumed the shares closed at NAV.
- **The honest negative:** `GATE.RELEASE` - release a NAV whose error reaches the floor - never fired,
  as `GATE.RECON` (eval #4) and `GATE.MATCH` (eval #5) never fired. The differences sit one layer down.
- **Small tier, arithmetic across the threshold:** GPT-5.4-mini reconciles every line correctly, then sums
  the recomputed assets $2,000,000 short, so its error is 0.2500 a share, 0.49% - just under the 0.5%
  reprocessing line. Right call (HOLD, the $0.01 floor is exceeded either way), wrong magnitude, and a
  remediation class that would have flipped post-release. Pinned to C2 and C3; no gate, because a 0.99
  ratio is an arithmetic slip, not a scale error.
- **Mid tier, consequence for test:** Sonnet 4.6 and GPT-5.4 compute -1.4426% and answer the
  "exceeds the reprocessing percentage" field as "reprocessing is not applicable pre-release" (0.972 each;
  the schema wording has since been sharpened, disclosed in the taxonomy). Haiku 4.5 orders shareholder
  reprocessing for a NAV that was never released (0.964). Sonnet files an "exception" on the clean case
  whose own text concludes that every line matches; the hardened grader reads it as informational (1.000 AP).
- **Grader calibration logged:** seven of eight models cited the administrator's totals block, a valid
  citation the single gold verbatim rejected; alternates added, all runs re-graded offline with the
  original scores kept in each `run.json`. Gemini 3.6 Flash's first break-case attempt was cut off by the
  8,000-token budget (0.428 as parsed) and re-run at 16,000 (0.956 after the echoed-instruction guard, 1.000 AP
  before it); the truncated run is kept under `prior/`. Details: [`outputs/eval7-live/TAXONOMY.md`](outputs/eval7-live/TAXONOMY.md).
- **Adversarial gaming review (October 6, 2026):** six attackers, one per grader surface, reproduced ways a wrong
  answer scored well (a release read as a hold because "note" contains "not"; a fabricated price in the
  reasoning text) and ways a right answer lost (a date with a time part firing the date gate). All fixed, 86
  cases pinned as standing checks, every run re-graded with provenance; four scores moved, no decision or gate.

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


### Eval #7 on local models (the cost question)

Five free models through LM Studio, same packages, same grader: on a laptop with a 12 GB graphics card and on
a desktop RTX 5090. The paid models took 15 to 40 seconds per case.

| Model | Hardware | Break case | Clean case | Time per case |
|---|---|---:|---:|---:|
| Qwen 3.8 27B (4-bit) | laptop (12 GB GPU + CPU) for the break; a desktop RTX 5090 for the clean | **1.000 AllPass** | 0.986 | 24 min on the laptop; 5.7 min on the 5090 |
| Gemma 4 31B (4-bit) | desktop RTX 5090 | **1.000 AllPass** | **1.000 AllPass** | 5.7 min / 6.3 min |
| Qwen 3.6 35B-A3B (4-bit, 3B active) | desktop RTX 5090 | 0.968 | 0.932 | 3.6 min / 3.2 min |
| Qwen 2.5 32B instruct (4-bit, no thinking phase) | desktop RTX 5090 | **0.535** | 0.941 | about 2 min |
| Qwen 3.8 2B distill (8-bit) | laptop GPU | 0.131, sign gate | 0.174, false hold | about 25 s |

- The 27B found the stale swap, recomputed 51.9912, held and refused the probe correctly - every criterion
  met, 24 minutes of thinking on the laptop. On the clean case it thought twice as long (15,665 tokens), released
  the NAV with no exception and lost one point for a thin citation: 0.986 in five and a half minutes on the 5090;
  the laptop attempt had run past its output budget and is kept under `prior/`.
- Gemma 4 31B passed everything on both packages on the 5090, under six and a half minutes each, with a fraction
  of the Qwen's thinking: two free models from two families at the flagship level on this package.
- Qwen 3.6 35B-A3B, the fast mixture model, got every number and decision right in under four minutes per case
  and lost points only on paperwork: no citations, and the NAV-to-release left blank on the clean package.
- Qwen 2.5 32B instruct, with no thinking phase, saw the problem and did not do the work: it flagged the stale
  swap, named the line and held, but copied the administrator's NAV back as its recomputation and reported no
  error (0.535); exact on the clean case apart from a thin citation and an echoed refusal reason (0.941); about
  two minutes per case.
- The 2B read every line correctly, then added them up $108 million and $48 million too high, declared
  errors that did not exist and held the clean NAV with reprocessing ordered. The small-model floor.
- Earlier attempts cut off by LM Studio's default 8,192-token window are kept under `prior/`. Details:
  [`outputs/eval7-live/TAXONOMY.md`](outputs/eval7-live/TAXONOMY.md).

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
- The frontier grid (evals #3–#5) also ships as machine-readable per-checkpoint
  [capability profiles](profiles/) — `python -m harness profiles` regenerates them byte-stably
  from the committed answers, so a clean diff doubles as a grader regression check.

- Eval #6 used the same per-vendor budget parity (Claude 8k on the compat endpoint, GPT and
  Gemini 32k); its cases share one finalized prompt contract (Sonnet's first batch drove one
  prompt clarification and was fully re-run under the final prompt before any other model ran).
  Its live batches surfaced grader-contract gaps in two waves — all false fires on correct
  answers, all fixed and re-verified against the gaming-review regression suite —
  logged in the [eval-6 taxonomy](outputs/eval6-live/TAXONOMY.md).
- **Grader hardening, round six (Sep 2026).** An external review of the grader found four ways a
  wrong answer could still score AllPass (a settle-and-escalate decision credited as the refusal;
  an affirm-and-release action under a MISMATCHED decision; a wrong amount carried only in the
  action prose; a "verbatim" quote with two dates swapped). All four are fixed and now sit in the
  regression suite (79 eval-6 checks + 24 for evals #4–#5 + 23 for the judge, all inside
  `python -m harness selftest`). **No published cell moved**: all 96 committed frontier answers
  re-grade identically and the profiles regenerate byte-for-byte. Details in the
  [eval-6 taxonomy](outputs/eval6-live/TAXONOMY.md) ("Round six").
- **Round seven (2026-09-24, the Phase-2 live wave).** 120 agent-arm worksheets through the
  eval-6 grader surfaced eight more false fires on correct prose (a year-terminated sentence, four
  noun uses of "tender", a scoped hold vetoing its clause, "VOID" as a release, a hedged range as
  a fabrication, the "hold for entitlement" idiom), all pinned by checks LW4#1 to LW4#13 (92 checks
  now). All 48 committed eval-6 answers re-grade identically on gated score, ungated score, gates and
  checkpoints; one diagnostic category rollup moved (GPT-5.4-mini, corrected dividend, calibration
  -0.385 to +0.077) and `profiles/` was regenerated. Profile rows now carry an `arm` field.

## What's next

Frontier runs on evals #1–#2 (still open-weight only); a Gemini pro-tier model once Google ships
one current; the ETF-swap pair live; a review protocol for eval-6 Phase 2 that a reviewer cannot use to
over-rule a calibrated refusal (the two review arms above are its baselines); and the ODD workflow
eval sketched in
[`ODD.md`](ODD.md).

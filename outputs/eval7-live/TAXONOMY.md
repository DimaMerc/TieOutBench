# Eval #7 live runs — ETF NAV oversight

Eight frontier models across three vendors (Claude **Opus 4.8** / **Sonnet 4.6** / **Haiku 4.5** via the
Anthropic OpenAI-compatible endpoint; **GPT-5.6-sol** / **GPT-5.5** / **GPT-5.4** / **GPT-5.4-mini** via
`api.openai.com`; **Gemini 3.6 Flash** via Google's OpenAI-compatible endpoint) on both gold cases - the
**break** case (`grsl-nav-2026`: one total return swap carried at the prior day's mark, the NAV understated
by 0.7500 a share) and the **clean** mirror (`grsl-nav-2026-clean`: the same package with the counterparty
file on time, so it ties). Deterministic core; nothing in this suite is free-form, so the offline judge is
the whole grader. Each model receives the administrator's preliminary package (ledger, liabilities, totals,
capital stock, pricing-exception report), the two counterparty swap statements, the market data and the
fund's NAV error policy, and must recompute the NAV, check the day's move, localize the break, classify
it and decide. One run per model per case (n = 1), 2026-10-05. Reproduce one run:
`python outputs/run_live_eval7.py --model-id <id> --endpoint <url> --case <case>`; the grid:
`python outputs/run_live_eval7_grid.py`; the matrix from the saved artifacts: `python outputs/eval7_matrix.py`.

## The matrix

| Model | Break case (gated) | Gate fired | Clean case (gated) | False hold? |
|---|---:|---|---:|---|
| **Opus 4.8** | **1.000 AllPass** | none | **1.000 AllPass** | no (RELEASE) |
| Sonnet 4.6 | 0.972 | none | **1.000 AllPass** | no (RELEASE) |
| Haiku 4.5 | 0.964 | none | 0.986 | no (RELEASE) |
| **GPT-5.6-sol** | **1.000 AllPass** | none | **1.000 AllPass** | no (RELEASE) |
| **GPT-5.5** | **1.000 AllPass** | none | **1.000 AllPass** | no (RELEASE) |
| GPT-5.4 | 0.972 | none | 1.000 AllPass | no (RELEASE) |
| GPT-5.4-mini | **0.633** | none | 1.000 AllPass | no (RELEASE) |
| Gemini 3.6 Flash | 0.956 | none | **1.000 AllPass** | no (RELEASE) |

Ten of sixteen runs AllPass. No gate fired in any run.

## What the runs show

**The frontier holds the wrong NAV and releases the right one.** All eight models return **HOLD** on the
break case, localize it to SWAP-B, recompute the NAV at **51.9912** (seven of eight), quantify the error
at **0.7500 a share, 1.44%**, direction understated, and run the reasonableness check the same way
(administrator move +2.4824%, deviation -1.5176 points from the expected +4.00%, flag raised). On the
clean case all eight **RELEASE** - no model cried hold on a package that ties (`D1.n_falsehold` never
fired). Three models - Opus 4.8, GPT-5.6-sol and GPT-5.5 - AllPass both cases: every criterion met, no gate,
calibrated refusal perfect; Gemini 3.6 Flash AllPasses the clean case and loses its break-case AllPass only to
an echoed refusal reason (calibration item 4). These are the suite's first AllPasses on a
reconciliation-type break case; evals #4 and #5 capped at 0.983 on a citation miss.

**The calibrated refusal held everywhere.** All eight answered the D2 probe NOT_DISCLOSED - the fund's
exchange closing price and the premium/discount are not in an accounting package - and none assumed the
shares closed at NAV. Seven of eight produced the answerable twin (administrator minus recomputed NAV,
-0.7500); the one miss is the small model's own arithmetic (below). One of them, Gemini 3.6 Flash on the break
case, gave the answer schema's own instruction text as its reason rather than a sentence of its own: the label and
the twin were right, the reason was never written (calibration item 4).

**The small-tier finding: a right call on wrong arithmetic that lands just under the threshold.**
GPT-5.4-mini reads the package correctly - its line-by-line reconciliation marks SWAP-B stale against the
independent 6,000,000.00 and every other line matched - but its recomputed total assets are
**207,010,600**, $2,000,000 short of the correct 209,010,600 (it added one of the three million to the
administrator's total). Its NAV is 51.4912, the error **-0.2500 a share, -0.49%** - just **under the 0.5%
reprocessing threshold**, which it accordingly reports as not exceeded, while reporting the fund-level
error as **+1,000,000** beside a direction of "understated". It still returns HOLD, localized to
SWAP-B, because the $0.01 floor is exceeded either way - the right call. But had this been a post-release
error, the same arithmetic would have moved the remediation from "reprocess shareholder transactions"
to "fund-level correction only". The eval pins the slip where it lives: C2 at 0.222 and C3 at 0.235, the
twin R = 0, D1 at 0.778; **no gate**, because a 0.99 ratio to the correct total is an arithmetic error,
not a scale error - the evidence-only SCALE gate is designed not to fire on it.

**Two mid-tier models answered the threshold field as a consequence rather than a test.** Sonnet 4.6 and
GPT-5.4 both compute the error at -1.4426% and both set `exceeds_reprocessing_pct` to false. Sonnet's
own note explains the reading: "Pre-release hold; no shareholder transactions were executed at the
erroneous NAV. Reprocessing is not applicable. The NAV is corrected and re-struck before release per the
fund's pre-release error policy." The decision and the reprocessing call are right; the arithmetic test
was answered as the policy consequence. Graded as a miss on `C3.thresholds` (three points; both at
0.972). The schema wording those runs saw was terse (`"exceeds_reprocessing_pct": false`); it has been
sharpened for future runs ("the arithmetic test only, whatever the review stage"). The two runs stand as
graded under the wording they saw, and this note discloses the ambiguity.

**Haiku 4.5 orders reprocessing for a NAV that was never released.** On the break case its numbers are
exact and it holds, but it sets `reprocessing_required` to true on a pre-release hold - nothing was
transacted at the wrong NAV, so there is nothing to reprocess. `D1.classify` catches it (D1 at 0.778,
case 0.964). On the clean case its citation reads "all positions dated 2026-06-23" - a paraphrase, not a
quote from the package - the one entailment miss (0.986).

**Sonnet 4.6 files an exception that reports no exception.** On the clean case it emits an exception row
typed `arithmetic_error` on the totals whose own detail concludes "No break at the line level; all
individual lines match" after checking that the liabilities, the net assets, the NAV rounding and the
stated move all tie. It still releases. The first grader charged the row as a false exception (0.957); the
hardened grader after the gaming review reads a row whose own text says there is no break as informational,
and the run is a tenth AllPass. The noise is real; it is not an error.

## The honest negative result

**No model released the wrong NAV.** Across all sixteen runs `GATE.RELEASE` - the signature, *release a
NAV whose error reaches the floor* - never fired, just as `GATE.RECON` never fired on eval #4 and
`GATE.MATCH` never fired on eval #5. The marquee failure did not appear in frontier models on this
package. The capability differences surfaced one layer down: the small model's arithmetic across the
0.5% line, the mid tier's consequence-for-test reading, the small model's reprocessing call. One run per
model per case, one break pattern (a stale swap mark); the planned cases - a missing swap accrual, a
redemption-day dilution, a one-cent floor edge, a Luxembourg regime, a post-release discovery - are where
the harder calls live.

## Hardening: the adversarial gaming review (October 6, 2026)

**What was done.** Six independent attackers, each on one surface of the grader, tried to make a wrong answer
score well or a right answer score badly, and had to reproduce every claim against the live grader. Their notes
and scripts are under `gaming-review/`. Between them they graded more than two thousand mutated answers.

**What they found, in plain terms.**

- **The release/hold reader could be fooled by letters inside words.** It matched letter strings, so "RELEASE
  (see note)" read as a hold because "note" contains "not", "Below the threshold, RELEASE" read as a hold
  because "threshold" contains "hold", and "NAV is correct" counted as a hold because "correct" was a hold word. The signature failure, releasing the wrong NAV, could score a
  perfect 1.000 with no gate by adding "(see note)". In the other direction, "Release withheld" and "Delay the
  release" fired the gate on a correct hold.
- **The refusal check looked in one field for a number.** A fabricated price in the reasoning text, in a string
  such as "51.30 USD" or in another field passed as a perfect refusal, and so did
  "assume the shares closed at NAV". The answerable twin was accepted with the wrong sign.
- **Reconciliation rows were graded on their status label only, never their values**; the citation check compared
  the quote to the gold string rather than to the package, so a quote of a line that does not exist passed;
  invented ledger rows and an invented price for the fund's own shares went unnoticed.
- **Correct answers in ordinary notation tripped hard gates.** A valuation date written with a time part or as
  "23 June 2026" fired the date gate and cost 63 percent of the score; "USA", a floor written as "1 cent" or a
  percentage written as "50bp" fired the regime gate; integer 0 read as "unknown" in every yes/no field; several
  fields the answer form asks for were never graded.
- **Malformed answers crashed the grader instead of scoring zero**, so the worst answers would vanish from the
  matrix rather than appear at the bottom of it.

**What changed.** The decision reader now works on whole words with negation ("not approved", "release
withheld"), conditions ("release only after the mark is corrected" is a hold) and contradictions ("HOLD but
release" earns nothing), and an answer outside the RELEASE|HOLD contract earns nothing on the decision checkpoint
instead of keeping most of its points; a release instruction placed in the escalation field fires the gate like
the decision itself. The refusal check scans the reasoning, the label and the value text for an asserted price or
premium, reads "assume price equals NAV" as a fabrication unless it is negated, matches the twin with its sign,
and accepts a wider vocabulary of honest refusals. Ledger rows are graded on values as well as labels; a citation
must appear verbatim in the rendered package; invented rows, invented prices and id-less numeric rows count as
fabrication; line ids tolerate underscores, spaces and parentheses. Dates in any common notation, "USA", "1 cent",
"50bp" and "before release" are read correctly; integer 0 and 1 are booleans; the scale gate also
catches a decimal shift and a sign-flipped mis-scale; the unread fields are graded; a malformed section scores
zero and never raises. Eighty-six of the attackers' cases are pinned as standing checks in
`harness/gaming_review_eval7.py`, run by `python -m harness selftest`.

**What moved.** Every saved run was re-graded offline with the scores before and after kept in its record. Four
moved, and no decision and no gate changed on any run. Sonnet 4.6's clean case went from 0.957 to 1.000 AllPass:
its "exception" row, whose own text says there is no break, is now read as informational rather than charged as a
false exception. Three runs lost points on the reasonableness check, which now grades the day's move and the
deviation computed from the model's own recomputed NAV, so each model's arithmetic error carries through: GPT-5.4-
mini's break case from 0.671 to 0.633 (its recomputation was short, so the move it reported was too), Qwen 2.5's
break case from 0.558 to 0.535 (its "recomputed" NAV was the administrator's own, so the deviation it reported
never closed; it also gained the citation credit its short verbatim quote of the exception line had been denied),
and the 2B distill's clean case from 0.212 to 0.174 (its mis-added total). The headline is now ten of sixteen paid
runs AllPass and three models perfect on both cases. What the attackers could not do, after the fixes, is make a
released wrong NAV score as a hold, or make a fabricated price pass as a refusal.

**What is still true.** The grader tests form as a proxy for meaning. A model that writes its decision in words
outside the contract earns nothing rather than being read; a refusal in unusual wording may be under-credited;
the contradiction check is pattern-based. Those are the limits the review leaves, and they bias the grader toward
strictness, not leniency.

## Grader calibration from the live runs (logged, as on evals #2 to #6)

1. **Citation alternates.** The gold named one verbatim per case (the exception-report line on the break
   case, the SWAP-B ledger line on the clean case). Seven of eight models cited the administrator's
   **totals block** instead - a legitimate citation that entails the reading, which the single gold string
   rejected (token overlap below the entailment threshold). Both cases now carry `citation_alternates`
   (the totals block; on the break case also the stale SWAP-B ledger line) and the handler accepts any of
   them. All sixteen saved answers were re-graded offline (`outputs/eval7_regrade.py`; each `run.json`
   keeps the score written at run time under `score_at_run` and logs the re-grade). Moved: Opus 4.8 clean
   0.986 to 1.000; Sonnet 4.6 clean 0.943 to 0.957; GPT-5.6-sol both 0.986 to 1.000; GPT-5.5 both 0.986
   to 1.000; GPT-5.4 clean, GPT-5.4-mini clean and Gemini 3.6 Flash clean 0.986 to 1.000. No decision,
   number or gate changed; Haiku's paraphrase still fails.
2. **Schema contract.** The pre-grid smoke run (Haiku 4.5, break case, 0.957) reconciled only the five
   ledger lines because the schema never said to list the liability accruals; the schema and the prompt now
   say "one row for every valuation-ledger line and every liability line". That run was superseded by
   the grid run and is kept under `prior/`. The threshold-field wording was sharpened after the grid (see
   above); it applies to future runs only.
3. **Token budget.** Gemini 3.6 Flash's first break-case attempt stopped at the 8,000-token budget
   (`finish_reason=length`: about 6,100 hidden reasoning tokens plus 1,541 visible), the JSON cut off after
   C1, and the parsed remainder scored 0.428 with C3, D1 and D2 empty. A budget stop is a harness setting,
   not a capability measure: re-run at 16,000 tokens it completes and scores 0.956 (1.000 AllPass until the
   echoed-instruction guard of item 4). The truncated run is kept
   under `prior/`; the matrix shows the completed run.
4. **Echoed-instruction guard.** Qwen 2.5 32B returned the answer schema's own placeholder instruction as its
   refusal derivation on both cases, and the refusal grader credited it as a reasoned refusal. A derivation that
   echoes the schema placeholder now earns only a bare NOT_DISCLOSED (G = 0.5). Two scores moved: Gemini 3.6 Flash's break case, whose derivation
   was the same echoed placeholder, from 1.000 AllPass to 0.956, and Qwen 2.5's clean case from 0.986 to 0.941;
   Qwen 2.5's break case was already zero on that checkpoint (wrong twin). All runs were re-graded offline with the
   scores before and after kept in each run.json.

## Open-weight local models (the cost question)

**What was tested.** The same two packages and the same grader, with five free models running through LM Studio,
on a laptop with a 12 GB graphics card and on a desktop with an RTX 5090: a 27B Qwen 3.8 at 4-bit, a 31B Gemma 4
at 4-bit, a 35B Qwen 3.6 mixture model with 3B active parameters at 4-bit, a 32B Qwen 2.5 instruct that answers without a
thinking phase, and a 2B distilled Qwen 3.8 at 8-bit. There is no API cost; the cost is time and hardware. The paid models
above took 15 to 40 seconds per case.

**How to read it.** The scores mean the same as in the frontier table. Time per case is wall-clock on the
laptop. Two earlier attempts per model were cut off by LM Studio's default 8,192-token window before either
model could answer; they are kept under `prior/` and are not scores.

| Model | Hardware | Break case | Clean case | Time per case |
|---|---|---:|---:|---:|
| Qwen 3.8 27B (4-bit) | laptop (12 GB GPU + CPU) for the break; a desktop RTX 5090 for the clean | **1.000 AllPass** | 0.986 | 24 min on the laptop; 5.7 min on the 5090 |
| Gemma 4 31B (4-bit) | desktop RTX 5090 | **1.000 AllPass** | **1.000 AllPass** | 5.7 min / 6.3 min |
| Qwen 3.6 35B-A3B (4-bit, 3B active) | desktop RTX 5090 | 0.968 | 0.932 | 3.6 min / 3.2 min |
| Qwen 2.5 32B instruct (4-bit, no thinking phase) | desktop RTX 5090 | **0.535** | 0.941 | about 2 min |
| Qwen 3.8 2B distill (8-bit) | laptop GPU | 0.131, sign gate | 0.174, false hold | about 25 s |

**What happened.**

- **The 27B matched the frontier flagships on the break case.** It found the stale swap, recomputed 51.9912,
  held, localized the break to the swap line, refused the probe correctly and met every criterion. It thought
  for about 7,900 tokens before writing a word and took 24 minutes on this hardware (1,428 seconds; 10,486
  completion tokens in all).
- **On the clean case it thought twice as long, and then got it right.** On the laptop it reasoned for more
  than 11,000 tokens without reaching an answer and ran out of its 12,000-token output budget (that attempt is
  kept under `prior/`; its parsed remainder is not a score), and a larger-window re-run was stopped after 70
  minutes on the CPU. On a desktop RTX 5090 with a 24,576-token window it finished in five and a half minutes
  (343 seconds) after 15,665 tokens of thinking, released the NAV, raised no exception, refused the probe
  correctly and gave the twin as zero. It lost one point for a thin citation: a single field,
  "nav_per_share=51.9912", rather than the totals block. Score 0.986. The package with nothing wrong in
  it cost this model twice the thinking of the one with the break.
- **Gemma 4 31B passed everything on both packages**, on the 5090 in under six and a half minutes each (339 and
  377 seconds) and with a fraction of the Qwen's thinking (1,383 and 1,886 reasoning tokens): found the stale swap,
  recomputed 51.9912, held and localized; released the clean package with no exception; cited the exception report
  and the totals block exactly; refused the probe and gave both twins. Two free models from two families now sit
  at the flagship level on this package.
- **Qwen 3.6 35B-A3B, the fast mixture model, got every number and every decision right and lost points only
  on paperwork.** It held the broken package, recomputed 51.9912, localized the swap, released the clean one,
  refused the probe and gave both twins; it gave no citation on either package and left the NAV-to-release
  field blank on the clean one. Scores 0.968 and 0.932 in under four minutes per case (219 and 192 seconds),
  the quickest local model here, thinking about 9,000 tokens each time.
- **Qwen 2.5 32B, which answers without a thinking phase, saw the problem and did not do the work.** On the
  break case it flagged the stale swap, named the line, flagged the day's move and held, which is the right
  call; but its "recomputed" NAV was the administrator's own 51.2412 copied back, so it reported no error, left
  the corrected NAV blank and gave no escalation. Score 0.535: the decision was right and the work behind it was
  not done. On the clean case its numbers and decision were exact; a thin citation and the echoed reason leave it
  at 0.941. About two minutes per case. Its
  refusal reasoning on both cases was the answer schema's own instruction text echoed back, which the grader
  had credited; that gap is now closed (calibration item 4 below).
- **The 2B read every line correctly and then could not add them up.** On the break case its total assets came
  out $108 million too high and it declared the NAV overstated by $27.75 a share; on the clean case $48 million
  too high, understated by $12, held, with shareholder reprocessing ordered. It also broke the answer format in
  three sections, which cost it the reading points even where the lines it listed were right. Scores 0.131 and
  0.174.

**What it means so far.** On this evidence two free models of 27B and 31B, from two families, run the release
check as well as the paid flagships do on both packages, at a cost of about six minutes per case on a desktop card
(or 24 minutes on a laptop for the Qwen), the Gemma with a fraction of the Qwen's thinking. The fast mixture model shows the other end of the trade: every
decision right in under four minutes, with its misses in paperwork rather than judgment. The non-reasoning model is the one that separates the call
from the work: it held for the right reason and never produced the number a desk would need to re-strike. A 2B
cannot do the arithmetic. The cost argument is
therefore not "local models are worse": at this size it is "as right, and minutes instead of seconds", with
one run per case and the hardware doing the work that the API bill does elsewhere.

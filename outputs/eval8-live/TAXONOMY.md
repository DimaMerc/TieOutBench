# Eval #8 — options-component ETF redemption tie-out: failure taxonomy

> Live-run findings are added here when the eight-model grid runs (stage 4). This file opens with the
> grader-hardening record, because the grader was attacked and repaired before any model was scored, so
> every live score below it is produced by the hardened grader.

## Grader hardening (the adversarial gaming review of 2026-10-19 to 2026-10-21)

**What was done.** Before any model was run, six independent attackers (Sonnet 5.5, one per surface) tried
to make the grader give a wrong answer a good score or a right answer a bad one, about 1,500 graded
mutations in all. Their notes and scripts are in [gaming-review/](gaming-review/), one file per surface:
the settle/hold decision, the refusal grader, the numbers and the multiplier gate, extraction and the tie
ledger, the planning pins and the two hard planning gates, and a sweep of legitimate answer formats. Every
claim was reproduced by running the grader; a finding without a run was not a finding.

**What they found, in plain terms.**

- The hard planning gates fired on the wrong things. A perfect answer that wrote a date as "23-Jun-2026",
  left the basket date out, or listed the four option series in a different notation lost two thirds of its
  score to a gate meant for using the wrong basket. Meanwhile the basket of record itself was never checked:
  a model could name the November fund's basket, or an invented one, and keep a perfect score as long as its
  four series strings were right.
- The settle/hold classifier read words, not clauses. "No exceptions. Settle." counted as a hold because a
  "no" stood three words before "settle"; "Don't settle" with a curly apostrophe counted as a settle;
  "HOLD - do not release the cash, do not mark the order settled" counted as a contradiction. A release
  instruction placed next to the word "escalate" was waved through, and the two yes/no switches for
  releasing the cash and cancelling the shares were read by nothing.
- The remedy was a bag of words. A remedy that moved the 11,880 contracts the wrong way, to the AP, satisfied
  it, because "transfer", "before" and "clearing members" were all present.
- Ledger statuses were sorted by the first family word found. "quantity matches" read as a quantity break,
  "series_mismatch" on the quantity break read as the quantity break, and "NOT OK" read as a match.
- Row keys and fabrication were whitelists. A ledger row labelled "share delivery" or a cash summary row fired
  the fabrication gate; a second, invented confirmation for the broken leg did not.
- The multiplier gate could be dodged by withholding the figures it read, and tripped by a single mark slip
  that happened to land near one hundredth of the right value.
- The refusal grader keyed on its own designed phrasings. "The AP's acquisition cost of the 100,000 shares is
  not in the packet" was gated as a fabrication (the share count read as a price), while "since the cost is
  not in the packet, I assume the AP bought at the prior NAV" passed because a "not" stood earlier in the
  sentence, and "it paid 3,050,000.00 for the shares" or "earns about 7,500" were never scanned at all.

**What changed.** Every gate in this eval now fires on evidence and never on absence or notation: the date,
series and multiplier gates moved from the positive pins to penalty hooks (rubric 1.1.0), so a missing or
oddly written pin costs its points but does not gate, while a parseable date that is a different day, a PCF
id that resolves to another basket, a basket actually read from a distractor file, or two figures sitting on
the hundredfold axis do. The decision classifier works clause by clause, with negation and conditions bound
inside their clause, the apostrophe normalised, a settle conditioned on the corrective action read as a hold
and one conditioned on a time read as a settle, and the two switches read. The remedy is graded on its own
text for the return of the excess, its size, its direction back to the fund, the release sequenced after it
and the parties. Statuses separate the verdict from the kind of mismatch, with negation. Rows key by leg
number anywhere in the label, by the option series (root-insensitive, N-PORT title form too) or by a
side-type-strike description; share-leg synonyms map to the share row; summary rows are neither graded nor
fabricated. Fabrication is tested against the packet: a row shaped like an option leg that is not in the
basket, or a second confirmation for one leg with a quantity the packet never shows. Numbers parse units and
locales, a hedge is no value, a fraction is accepted for a percentage, and a figure that is not applicable on
the clean twin may be null. The refusal grader scans every string of the refusal and the decision prose for
an assumed cost, a stated purchase price, a profit figure or a made-up close, binds negation to the same
clause in both directions, treats share counts and the packet's own derived totals as known, and requires the
refusal to name the AP's cost specifically.

**Decisions where the attackers and the maintainer differ** (pinned as decided): an unrecognised decision
word ("Freigabe", "yes") earns nothing and fires no gate, as in eval 7; three of four series pinned is
incomplete, not wrong; a hedge is an unmet pin, not a gate; a date or series gate now costs both the pin and
the penalty; a refusal that names the missing cost but cites no document earns three quarters of the refusal
credit; a release appended to a correct remedy without a sentence boundary is not read as an instruction (a
residual, documented).

**Standing regressions.** 258 of the attackers' checks are pinned in `harness/gaming_review_eval8.py` and run
with `python -m harness selftest`: every exploit must fail or fire its gate, every legitimate form must score
clean. After the repair the full selftest passes for all eight suites, the oracle scores 1.000 on both cases,
and the 22 prior cases of the other seven evals grade byte-for-byte as before. No live model had been run
when the grader changed, so no published number moved.

**The variant scores after hardening** (break case; `python -m harness run --case grbo-redeem-2026 --all`):
oracle 1.000; fabricate_pnl 0.900; settle_override 0.840 with the signature flag; sign_flip 0.754;
recap_blind 0.603 with the flag; multiplier_slip 0.460; date_slip 0.323; series_slip 0.252. On the clean
twin the perma-holder scores 0.840 with the decision checkpoint at zero and no gate. The two planning
variants fell from 0.351 and 0.308 because their checkpoint now pays the pin and the penalty; nothing else
moved.

## What the live runs found (2026-10-21)

**What the test was.** An Authorized Participant redeems two creation units, 100,000 shares, of a fictitious
buffer ETF in kind. The basket is four FLEX option legs on IWM plus a small cash component, and the order
settles bilaterally, outside the clearing house. The model is given the order ticket, three PCFs of which one
is the basket of record, the fund's final NAV statement, OCC's record of the four position moves, the
custodian's positions the next morning and the ETF agent's status report. It has to tie every leg, recompute
the cash component and decide: settle, or hold. The hidden break is in one leg: the long put was moved at
12,000 contracts against 120 due, the order's share equivalent keyed as the contract count, while the agent's
report says all four legs moved. The right answer is to hold and have 11,880 contracts returned first. The
clean twin is the same order with every leg tying; the right answer there is to settle.

**How to read the scores.** The score is point-weighted over eight checkpoints and collapsed by gates. A gate
is a disqualifying error, such as settling a redemption whose legs do not tie, tying the wrong fund's basket,
or confusing contracts with shares in the arithmetic. AllPass means every criterion was met. One run per model
per case, eight models, three vendors.

**What happened.**

- Every model held the broken order and settled the clean one. Nine of sixteen runs passed every
  check. Three models were perfect on both cases: Claude Opus 4.8, GPT-5.6-sol and GPT-5.5. Every model
  found the leg, the 12,000 against 120 and the 11,880 excess, named the corrective transfer back to the
  fund's account before any release, and escalated to both clearing members.
- A mid-tier model found the break and then sized it at ten times its value: 46,926,000 instead of 4,692,600,
  and carried that into the impact per share (2.36 instead of 0.24) and the hold record. Right call, wrong
  magnitude. Score 0.868.
- A small model valued the option legs per share of the underlying instead of per contract, each leg at one
  hundredth of its value, reported the creation unit's value as 30.50 rather than 1,525,000 on the break
  case, and then copied the agent's cash component as its own recomputation. The multiplier gate, built for
  exactly this confusion, fired on both cases. It still held the broken order and settled the clean one.
  Scores 0.543 and 0.549.
- A mid-tier model moved the fund's position the wrong way on the two written legs, expecting minus 24,120
  where the custodian showed minus 23,880, and flagged a 240-contract shortfall that does not exist on two
  legs that tie. Everything else right. Score 0.988.
- A small model sized the excess and the impact per remaining share right, 0.2358 a share, and then reported
  it as 0.0154 percent of NAV instead of 0.7731. Score 0.968.
- What nobody did: no model settled the broken order, none held the clean one, none assumed what the AP had
  paid for its shares or invented a closing price, and every refusal named the missing cost.
- The flash-tier Google model got every number and both decisions right and lost points twice. On the break
  case its stated reason for refusing the profit question was the answer schema's own instruction text, echoed
  back word for word, so the refusal earned half credit; the same model did the same thing on eval 7. Score
  0.956. On the clean case it left the quantities of the share row of the tie ledger blank. Score 0.989. Its first attempts at both
  cases were cut off by the 8,000-token budget, with most of the budget spent on hidden reasoning (0.264 and
  0.361 as parsed); they are kept under `prior/` and the scores above come from the re-run at 16,000 tokens.
  The first grid pass could not call Gemini at all: the Google account's prepaid credits were exhausted (a 402
  billing response, logged in `_grid.log`), topped up the same afternoon.

**Corrections to my grading, not to the models.** Running real models found six places where the grader
rejected a legitimate answer. On the clean twin the models left the position fields for the offending leg
empty, because there is no offending leg; the grader demanded the numbers. The field for the option value
the AP received was never defined in the answer schema, and three models read it three ways (the total, the
excess only, the whole leg); it is no longer graded and the schema now defines it. Two models stated the
settlement actions in the structured yes/no switches and left the remedy text empty on the clean case; the
switches now count. One model's refusal opened with the probe's own words and was treated as an echo of the
instructions; the echo guard now looks for the instruction's imperatives only. Two models filed an "exception"
on the cash whose text says the figures agree; such a row is now informational when the model's own cash
ties. One model cited the agent's totals line, a line of the packet the gold alternates did not list; it is
listed now. All fourteen runs that existed at the time were re-graded offline with the original scores kept in each
`run.json`; the two Gemini runs came later and were graded by the calibrated grader from the start. Eleven
scores moved, none of them a decision or a gate:

| Model | Break before → after | Clean before → after |
|---|---:|---:|
| Claude Opus 4.8 | 0.935 → 1.000 | 0.882 → 1.000 |
| Claude Sonnet 4.6 | 0.868 → 0.868 | 0.903 → 1.000 |
| Claude Haiku 4.5 | 0.528 → 0.543 | 0.534 → 0.549 |
| GPT-5.6-sol | 1.000 → 1.000 | 0.935 → 1.000 |
| GPT-5.5 | 0.956 → 1.000 | 0.855 → 1.000 |
| GPT-5.4 | 0.923 → 0.988 | 0.903 → 1.000 |
| GPT-5.4-mini | 0.903 → 0.968 | 0.882 → 1.000 |

**What it means so far.** The frontier flagships tie the legs and hold; the signature gate never fired, as the
settle, affirm and release gates never fired on evals 4, 5 and 7. The differences sit one layer down, in
magnitude: a tenfold slip and a hundredfold slip on the excess value, the sign of a written leg's position,
and a percent conversion. The hundredfold slip is the one this eval was built to catch, and the gate caught
it in the model's own arithmetic, not in a label. Limits: one break pattern, one run per model per case,
eight models, a constructed fixture whose mechanics are labelled confirmed or constructed in the case headers.
Next: the planned cases (a leg pending at the cut-off, a stale mark in the
agent's cash, the sibling series on one leg, the messaged NSCC-to-OCC flow).

# Failure taxonomy — eval #3, case `nvda-fy2026-dcf`, eight frontier models

Eight models, three vendors, one run each, on the growth-stock counterweight to the MCD case:
a NET-CASH company where the EV→equity bridge ADDS ~$3.11/share (+3.4%) instead of MCD's
−$50.8 (−22%). Offline (mock) judge. Artifacts per model in this directory (`answer.json`,
`raw.txt`, `report.txt`). Budgets: Claude 16,000 (compat endpoint does not charge thinking;
above the 12k live floor), GPT and Gemini 32,000 (thinking charged — the LEADERBOARD
methodology note). **Prompt note:** these runs used the case-hardened system prompt (v2),
which adds two case-agnostic sentences the MCD runs did not have — the net-debt/cash-like
netting convention and the 3×3 sensitivity-grid geometry (added after the pre-ship audit
showed the netting convention was graded but never taught). Cross-case comparisons that
touch those two behaviors are hedged accordingly below.

## The grid (final, post grader-calibration)

| Model | Gated | Ungated | Gate | E5 probe (R, G) |
|---|---:|---:|---|---|
| Claude Opus 4.8 | 0.974 | 0.974 | none | (1.0, 0.75) |
| Claude Sonnet 4.6 | 0.973 | 0.973 | none | (1.0, 0.75) |
| Claude Haiku 4.5 | 0.799 | 0.799 | none | (1.0, **0.25**) |
| GPT-5.6-sol | 0.970 | 0.970 | none | (1.0, 0.75) |
| GPT-5.5 | 0.970 | 0.970 | none | (1.0, 0.75) |
| GPT-5.4 | 0.883 | 0.883 | none | (1.0, **0.25**) |
| GPT-5.4-mini | 0.650 | 0.697 | **GATE.BRIDGE** | (0.5, 0.75) |
| Gemini 3.6 Flash | 0.970 | 0.970 | none | (1.0, 0.75) |

## What the runs show

**1. The ceiling got tighter.** Five models — Opus 4.8, Sonnet 4.6, GPT-5.6-sol, GPT-5.5, and
Gemini 3.6 Flash — land within **0.004** of each other (0.970–0.974), all gate-free, all with
textbook chains: correct FCFF path on the fading-margin forecast, WACC 12.62 from the
components, correct net-CASH bridge (+54,088 net cash, +22,251 non-op), fair value ≈ $91.7
against gold $91.67, correct "the price embeds growth beyond this base case" reads. Gemini's
flash tier ties the flagships again. On this case the eval separates the strugglers from the
ceiling, not the frontier from itself — and the ceiling ignores price tier.

**2. The mirror bridge trap caught exactly one model — in its subtler form.**
`GATE.BRIDGE` on GPT-5.4-mini is genuine and survived re-verification: its equity is exactly
`EV + 54,088` — it adds the net cash and **drops the $22,251M non-op add** (its own reported
E2 carries the non-marketable securities figure it then fails to use), and its per-share
(61.1) does not equal its own components' implication. It did not commit the naive EV÷shares
blunder — on a net-cash name that blunder is nearly invisible (−3.4%) — it omitted the
*smaller half of the bridge*. The gate catches the method either way. (Its remaining damage
is genuine internal inconsistency one level below the EV line: its stated subtotals — 494k
explicit + 950k terminal — tie at the top but are unreconciled underneath (it emits one of
five year rows, whose own t=1 PV implies a five-year sum near 643k, not 494k), and its
terminal value 1,710,000 is ~7% off the Gordon value of its own inputs — right formulas,
broken arithmetic chain.)

**3. A new failure class: derives the right number, reports a different one.** Two models,
two vendors, same probe (E5, "what is the WACC per the 10-K?"):
- **Haiku 4.5** answers COMPUTED **12.51** — while its own derivation text builds
  `0.98*12.8 + 0.02*3.887` (= 12.62) from the correct components, and it then *uses* 12.51
  consistently downstream (C2 12.51, whole chain discounted at it, no gate — internally
  consistent, so only C2's 5bp band and the value drift catch it; gated 0.799 with the same
  sloppy-arithmetic signature as its MCD `FCFF ≠ own build`, relocated to the WACC).
- **GPT-5.4** answers COMPUTED **12.31** — while its derivation text literally ends
  "= 12.62174%" and its own C2 reports 12.62 correctly. The E5 value contradicts both its
  own derivation and its own valuation. Label-only grading scores both models' probes as
  "computed"; the typed contract (value keyed to the C2 band) is what catches value ≠
  derivation. Kin to eval #4's echo-stub refusal: the wrapper is right, the content is not.

**4. Nobody misread the balance sheet's traps.** No model lumped the adjacent `Groq, Inc.
(13,000)` or `Purchases of non-marketable equity securities (17,502)` investing lines into
capex; extraction ran 0.92–1.00 across the board, and every model netted the marketable
securities into net debt (−54,088). Hedge: the netting convention was *stated* in the v2
prompt, so this says "models follow a stated convention," not "models infer it" — the MCD
runs cannot be compared on this point.

**5. No false-precision fire anywhere — under the v2 prompt.** Every model, including the
small tiers, produced genuine 3×3 grids and both sensitivity ranges (GPT-5.4-mini's S2 is
complete — the same model that left `g_sensitivity` null on MCD). The v2 prompt states the
grid geometry explicitly, so this is NOT comparable to the MCD runs and is *not* evidence
the mini's MCD gate was wrong (that firing was re-verified against models that cleared it).
It is weak evidence that stating the deliverable's shape helps small models more than large
(one model, single runs, case and prompt changed together).

**6. The E5 refusal discipline held otherwise:** no fabrication gate fired for any model;
Opus, Sonnet, GPT-5.5, GPT-5.6-sol, and Gemini all answered NOT_DISCLOSED with the correct
≈12.62 component derivation restated in their justification text (the mock's not-disclosed
tier scores G = 0.75; only a claimed COMPUTED value inside the C2 band scores 1.0).

## Grader-calibration log — the rule holds again, on this case's first batch

*The first real models find the grader bugs your self-tests were written around.* The first
live batch on this case surfaced **three grader-contract gaps**; all three were fixed, all
eight runs re-graded from the saved `answer.json` artifacts, the oracle still scores
1.000/AllPass on both DCF cases, the full selftest battery passes, and all **eight** committed
MCD reports re-grade unchanged (0.965 / 0.955 / 0.692 · C1FCF / 0.951 / 0.953 / 0.903 /
0.631 · FALSEPRECISION / 0.922). All three gaps were parser-strictness false fires, so each
correction necessarily moved a score up; the opposite direction — a gate that should fire but
does not — is pinned by the planted-error battery, which still trips every intended gate:

1. **Rates reported as fractions** (`0.1262` for 12.62%): GPT-5.4-mini reported Ke/Kd/WACC
   as fractions, violating the schema's percentage-points contract — which mechanically
   fired `GATE.C4TERM` (g 4% ≥ "0.126%") and part of `GATE.BASIS` (the C5 back-solve
   discounted at 0.13%). The `_taxnorm` precedent applied: `_ratenorm` now normalizes
   sub-1.0 Ke/Kd/WACC values (no plausible rate sits below 1pp) before grading. The mini's
   two artifact gates cleared on re-grade (0.327 → 0.650); its `GATE.BRIDGE` and its
   internal-inconsistency damage are genuine and stand.
2. **Numeric strings with display formatting** (`"7,469"`): Gemini answered both E5 twins
   correctly as comma-grouped strings; the parser returned None and scored R = 0.0. `_num`
   now parses formatted numeric strings (the eval-5 answer-shape precedent). Gemini
   0.931 → 0.970, E5 R → 1.0.
3. **Snake_case counted as one word**: Sonnet's `key_value_driver:
   "terminal_value_and_wacc"` — a substantive answer naming both drivers — failed the
   anti-stub "≥3 words" heuristic and fired `GATE.FALSEPRECISION` on *style*, against a
   sensitivity block that was complete and near-exact (97.35/91.61/86.64 vs gold
   97.35/91.67/86.62). The tokenizer now splits snake/kebab-case. Sonnet 0.853 → 0.973 —
   the 12-point swing is the gate's blast radius (the S2/S3 checkpoints it zeroes), not
   re-scored content; the MCD precedent is §3.7's false gate fire on exact arithmetic.

First-grade vs final-grade, for the record: Sonnet 0.853 → 0.973 · Gemini 0.931 → 0.970 ·
GPT-5.4-mini 0.327 (three gates) → 0.650 (one, genuine) · all others unchanged.

## Honest notes

- One run per model per case; adjacent scores are not a ranking (0.970 vs 0.974 means
  "indistinguishable here").
- The v2 prompt difference vs the MCD runs is disclosed above; the two cases' results are
  comparable on the calculation chain and gates, hedged on netting-convention and
  grid-shape behaviors.
- The systematic P1 0.885 / P2 0.929 residuals across all eight models are the same
  live-format frictions the MCD runs show (strict echo fields), identical across vendors —
  they do not separate models.
- Haiku's 0.799 and GPT-5.4's 0.883 carry no gate: their chains are internally consistent
  at their (wrong) rates — the design intent; the damage is localized to C2/E5 and the
  drifted values, not collapsed.

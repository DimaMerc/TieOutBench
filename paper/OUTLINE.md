# TieOutBench — paper outline & figure list (v1, for review)

> Working document, not the paper. Every section lists: what it claims, the evidence file it
> pulls from, and the target length. Figures are specified at the end with their data sources.
> Name collision search run 2026-07-31: "TieOutBench" is clean (no benchmark, repo, paper, or
> product uses it).

---

## Title & front matter

**Working title:**

> **TieOutBench: A Runnable, Rubric-Gated Evaluation Suite for Financial Analysis and
> Post-Trade Operations**

Subtitle options (pick one):
- *(a)* "Five expert-authored workflows, eight frontier models, three vendors — and why the
  harness is half the finding"
- *(b)* "Measuring whether an LLM's finance work ties out — before deciding whether to trust it"
- *(c)* no subtitle (cleanest for SSRN)

**Author line:** Dmitry Krutous · MBA, PMP · evals.finance · welt.management.solutions@gmail.com
(no affiliation — independent; SSRN handles this fine)

**Positioning statement (goes in a footnote or the abstract's last line):** an honest technical
report in the GDPval-v0 style — a working artifact with its caveats on its face, not a claims race.

**Name rationale (one paragraph, §1 or a footnote):** "tie out" is the fund-accounting control
this suite ports to AI — *a number that does not tie does not settle*. The name states the
grading philosophy: the score is not "how good did the answer sound" but "did the work tie out,
and if not, exactly where."

---

## Abstract (~250 words)

One paragraph, five beats:
1. **Problem:** a finance LLM's answer can look right and be wrong; a blended accuracy number
   cannot tell a firm *where* to trust a model. (The demo stat: internally-consistent answer,
   0.951 naive → 0.452 gated on one misread statement header.)
2. **Artifact:** five expert-authored workflows — earnings analysis, buffer-ETF diligence, DCF
   valuation, ETF creation/redemption reconciliation, OTC confirmation matching — decomposed
   into checkpoints, graded by point-weighted tiered rubrics with auto-fail *gates*, gold cases
   cited to SEC filings/FpML, runnable with one dependency and no API key.
3. **Coverage claim (hedged):** evals #4–#5 appear to be the only public LLM evals of
   capital-markets post-trade operations (supported by the 452-benchmark meta-survey).
4. **Results:** 8 frontier models / 3 vendors on evals #3–#5 + 2 open-weight models on #1–#2.
   Headline: across all eight models the marquee *decision* gates never fired — frontier models
   get the stop-or-go call right and lose points on the arithmetic underneath; flagships have
   converged to within 0.04; cheap tiers fail vendor-specifically, and one flash-tier model
   breaks the cheap=undeployable pattern outright.
5. **Methodological contribution:** cross-vendor comparison is invalid until the harness proves
   *equivalent room* — three vendors metered token budgets three different ways, producing four
   plausible-but-wrong scores before being caught.

## 1. Introduction (~1.5 pp)

- Open with the deployment question: *when — and exactly where — can a firm trust an LLM with
  analyst or back-office work?* Not "which model is best."
- The looks-right≠is-right motif, three escalating instances (this structures the whole paper):
  1. an **answer** can look right and be wrong (the scale-slip demo; the $279-vs-$228 DCF
     bridge blunder that lands *closer* to the market price than the correct method);
  2. a **failure** can look right and be wrong (six gates firing at once = a truncated
     sentence, not six mistakes);
  3. an **evaluation** can look right and be wrong (the starved-budget scores told a clean,
     false story about a vendor).
- Contributions list (numbered, explicit):
  C1 — five runnable, expert-authored, rubric-gated evals incl. the first public post-trade ops evals;
  C2 — the gate/blast-radius grading design (decision failures vs. arithmetic failures separated);
  C3 — an 8-model × 3-vendor graded study with all artifacts published;
  C4 — the cross-vendor token-accounting methodology finding (the "equivalent room" rule);
  C5 — a failure taxonomy grounded in graded traces, incl. the calibrated-refusal probe results.
- Source: README.md intro + demo section; PAPER.md §1.

## 2. Related work & landscape (~1.5 pp)

- **Design lineage** (one paragraph each, what was borrowed): HealthBench (expert rubric criteria,
  LLM judge), FinanceBench (evidence-cited answers), FinQA/ConvFinQA/TAT-QA (numeric tolerance),
  Vals AI Finance Agent Benchmark (checkpointed end-to-end tasks), FailSafeQA (calibrated refusal).
  Framing: the ingredients were public; the composition and the domain are new.
- **The 2026 landscape table** (Table 1, lifted from README with arXiv cites, all links already
  curl-verified): GDPval, Vals FAv2, APEX/APEX-Agents, BigFinanceBench, FrontierFinance,
  FinBalance — every one front-office; none post-trade. GDPval note: its finance occupations are
  analyst/advisor/sales — enumerate them to show the gap is at the *occupation* level, not task level.
- **The meta-survey anchor:** arXiv 2607.01740 maps 452 public financial-services benchmarks;
  quote its "genuine gap … for regulated domain tasks" line. Our coverage claim rides on their
  survey plus our own search — state both, keep the "appear to be" hedge.
- Figure 1 (coverage-gap map) lives here.
- Source: README "Where this sits in the 2026 benchmark landscape"; the verified landscape research.

## 3. Methodology (~3 pp — the heart of the paper)

### 3.1 Workflow decomposition
Plan → extract → calculate → decide checkpoints; each checkpoint owns inputs, a gold answer with
evidence citation, success criteria. Why checkpoints: *localizes* failure (Haiku's $138 DCF traced
to one FCFF offset at C1). Counts table: 17/18/18/8/8 checkpoints, 109/110/107/~31/~33 criteria.

### 3.2 Point-weighted, tiered criteria
Deterministic / entailment / judge / refusal atom tiers; stage weights; everything deterministic
graded deterministically. Eval #2's design stat as the exhibit: judge swap moves scores 2.0–4.5
points vs. 14.7 on eval #1 — calculation-heavy design caps judge exposure *by construction*.

### 3.3 Gates and blast radius
The signature mechanism. Three tiers (hard / scoped / in-checkpoint); gated vs. ungated score; the
gap *is* the finding. Blast radius calibrated to severity: GATE.BASIS 0.35 catastrophic →
bridge_omit 0.85 localized → FREELUNCH a *flag* (a memo can be 93% right and still mis-sell the
product). The two decision gates (RECON, MATCH) as ported operational controls — "tie out or stop."
Key design point: the highest-scoring failure is deliberately the catastrophic one (affirm-the-break
scores 0.84 of naive credit) — exactly the failure a naive average rewards. Figure 3 here.

### 3.4 Calibrated refusal
FailSafeQA-style probes with the **answerable twin** (refuse-everything cannot farm safety credit);
the typed `{COMPUTED | NOT_DISCLOSED | import}` answer contract on eval #2; fabrication gates
(a confident underived number = G:0). Forward-reference the refusal-echo finding (§7).

### 3.5 LLM-judge confinement & calibration
Judge confined to synthesis tier; frozen judge prompt; judge-vs-expert calibration (28/28, κ=1.0,
with the caveats stated *in the same sentence*: n=28, self-judging channel, anchoring risk).

### 3.6 Anti-gaming hardening & selftest discipline
Adversarial pre-commit reviews (placeholder cost blocks, substring-fished refusal credit,
go-ahead synonyms "book it"/"release for settlement" still trip GATE.MATCH); the schema round-trip
selftest (a schema-perfect answer must grade 1.000/AllPass — pins the output contract to the
graders); planted-error variants as regression tests (11 DCF variants, each trips exactly one gate).

### 3.7 The grader-bug law
Stated as a law of eval-building because it held five times out of five: *the first real model
finds the grader bugs your self-tests were written around* (3 bugs on eval #2, 5 on #3, 2 on #5 —
each list published in the taxonomy, all runs re-graded, oracle still 1.000). Publishing grader
bugs is part of the method, not an embarrassment.

## 4. The five evals (~3 pp; one subsection each, common template)

Template per eval: task in one sentence → checkpoint/criteria counts → signature gate → gold
provenance → the designed trap(s). Table 2 summarizes all five.

- **4.1 Earnings analysis** — 3 real 10-Q/10-K cases (BlackRock, Microsoft, Snowflake); scale trap,
  fiscal-vs-calendar, GAAP/non-GAAP divergence, genuine not-disclosed probe.
- **4.2 Defined-outcome (buffer) ETF diligence** — the generalist-can't-author eval. Real KOCT
  fund; filed strikes reproduce stated terms to 0.002pp; mid-period buyer math; GATE.FREELUNCH;
  sibling-vintage distractors ship *in the source data*. Snapshot provenance: anchor real+cited,
  two constructed states labeled hypothetical (the no-arbitrage bug caught in the author's own
  draft — disclosed, it's a strength).
- **4.3 DCF valuation** — MCD FY2025, every base line cited to the 10-K, labeled oracle layer for
  forecast/WACC/g. The signature: EV÷shares blunder lands at $279 (−2.6% from price) vs. correct
  $228 (~20% overvalued) — *the wrong method looks fair*. GATE.BRIDGE, GATE.BASIS,
  GATE.FALSEPRECISION.
- **4.4 ETF creation/redemption reconciliation** — first post-trade eval; authored from having run
  the change-management side of an institutional ETF servicing platform (credential phrased
  exactly thus). GATE.RECON. Provenance disclosure prominent: PCFs are NSCC-disseminated, not
  public — constructed, mechanics-faithful, real constituents, labeled.
- **4.5 OTC confirmation matching** — gold side is the real FpML 5.10 `ird-ex01` message (cited,
  not constructed); 6.05%-vs-6.00% break ≈ EUR 25k/yr on EUR 50MM; trade ids differ by design (the
  materiality foil); GATE.MATCH; the swap-inside-an-ETF case pair (gold shipped, not yet live-run —
  say so).

## 5. Experimental setup (~1 p)

- Subjects: 8 frontier (Opus 4.8, Sonnet 4.6, Haiku 4.5; GPT-5.6-sol, 5.5, 5.4, 5.4-mini;
  Gemini 3.6 Flash) on evals #3–#5; 2 open-weight local (qwen3.6-27b reasoning, qwen2.5-72b) on
  #1–#2. Models ARE named (unlike the LinkedIn article — a paper must; note the deliberate
  difference in the cover memo, not the paper).
- One run per model per case — stated up front, repeated in limitations: enough to expose a broken
  harness and to say a gate did/did not fire; **not** enough to rank by hundredths. "Read small
  gaps as indistinguishable."
- Endpoints (OpenAI-compat for all three vendors), final token budgets (32k DCF for GPT/Gemini,
  8k elsewhere with the floor-raise history), offline judge for the frontier grid.
- Gemini tier caveat: Google represented only by a flash model (its pro line a generation behind).

## 6. Results (~2.5 pp)

Figure 4 (leaderboard heatmap) + Table 3 (the full grid) anchor the section.

- **6.1 The decision gates never fire.** 8 models × both back-office workflows: nobody affirmed
  the broken trade, nobody settled the short basket, nobody cried false break on the clean
  controls. Was a single-family caveat; now reads as a property of the task. *The most
  reproducible result in the suite.* Frontier capability gap lives in quantification (bp
  conversion, the $200k slip), not the decision.
- **6.2 Flagship convergence / ceiling effects.** Within 0.04 everywhere, 0.015 on 4 of 5; five
  models tie 0.980 on the confirm-break case. Stated as a finding about the eval too: the honest
  response is to harden the task, not to pretend the ranking means something.
- **6.3 Cheap tier: vendor-specific failure modes.** Haiku = arithmetic (the $200k in-kind
  overstatement flips the residual sign — concludes *over*-delivered on a short basket;
  GATE.SCALE; the FCFF ≠ its own build offset, GATE.C1FCF). GPT-5.4-mini = calibration ($200.20
  to the cent with null growth sensitivity on a 79.5%-terminal-value DCF; GATE.FALSEPRECISION —
  verified against the models that cleared it, because a gate firing only on a new vendor is what
  a grader bug looks like). **Gemini 3.6 Flash breaks the pattern:** no gates anywhere, ties Opus
  on recon 0.983, DCF $227.81 vs. gold $227.82. Two data points said cheap=undeployable; the third
  says that was a coincidence of two vendors. Price tier and trustworthiness are different axes.
- **6.4 The refusal probes.** All eight refused correctly on the label. But GPT-5.4-mini's
  "derivation" is the prompt's own instruction echoed verbatim, and its answerable twin is off by
  $20k (−33,320 vs. −13,320). Grade only the label and it looks perfectly calibrated — the
  argument for typed refusals + answerable twins in one exhibit. Also: the WACC framing quirk
  (all models derive ~7.15%, discount with it, then answer "not disclosed" when asked per-the-10-K
  — a framing behavior the eval isolates from capability, easy to misread).
- **6.5 Open-weight results (evals #1–#2).** The 27B-reasoning-beats-72B observation (with the
  one-lineage caveat); the shared payoff-grid trap (N=2, same lineage — replication named);
  eval #1's extractor-vs-analyst split (0.91 extraction, missed the +1,118bp margin swing).
  Figure 5 (checkpoint vectors) here.

## 7. The harness is half the finding: cross-vendor token accounting (~1.5 pp — the novel bit)

This is the section that would survive even if every score in §6 were superseded next quarter.

- Narrative: three breakages before a single comparable number. (1) Loud+harmless: GPT-5 family
  rejects `max_tokens` → 400 → field-flip retry. (2) Quiet+expensive: OpenAI charges thinking
  against the completion budget → four plausible-wrong DCF scores (empty→0.953; 0.322 w/ six
  gates→0.951; 0.618→0.903; 0.745→0.631 — the last *fell*, and its gate is genuine). (3) Quietest:
  Google charges thinking AND hides it — completion_tokens 3, total_tokens 124, 113 thinking
  tokens invisible in the field a harness would naturally read.
- Table 4: vendor × (budget field, thinking charged?, thinking visible?).
- Figure 6: starved-vs-fair paired bars.
- The rule, stated once in bold: **you cannot compare models across vendors until you have proven
  the harness gives each equivalent room.** A starved model doesn't error; it returns a worse
  answer — which is exactly what a benchmarker is looking for.
- The honest escalation framing (verified wording): one vendor's truncation had already read as a
  quirk (Sonnet, 8k, eval-#3 TAXONOMY); a second vendor's made it a rule. "A benchmark that has
  met only one family of models has not been tested; it has been rehearsed."
- Tie-back: this is looks-right≠is-right applied to the *evaluation itself* — the paper's motif
  closes its own loop. Deployment-relevant beyond benchmarks: any firm's internal bake-off has
  this bug class.
- Source: LEADERBOARD methodology section + the verified cross-vendor article (15-fix reviewed).

## 8. Failure taxonomy (~1 p)

Consolidated table (Table 5) across all graded runs, each row cite-able to a trace file:
- **Unit/scale** (the classic): thousands-vs-millions; the $200k in-kind; notional in thousands.
- **Magnitude/conversion**: the bp trap — Sonnet 10× low, Haiku 10× high, *opposite directions*,
  same checkpoint (Haiku's lifetime figure is 20× — keep the arithmetic exact).
- **Internal inconsistency**: FCFF ≠ own build (+$2B/yr).
- **State/semantic inversion**: right number, wrong state (buffer "intact" at 44% consumed;
  +0.91 gap read as a gap when positive means none; over- vs under-delivered).
- **False precision**: decimal-precise target, null sensitivity, 80% terminal value.
- **Echo-stub refusal**: right label, instruction echoed as derivation, wrong twin.
- **Document-following vs. task-following**: the payoff-grid %-convention trap; the WACC
  "not disclosed" framing quirk.
- **What did NOT appear**: fabrication gates never fired live on frontier models; decision gates
  never fired. The taxonomy of absences is data too.

## 9. Limitations (~0.75 p — prominent, own section, not a paragraph)

In order of importance, no hedging-by-burying:
1. **n = 1 run per model per case** — no variance estimates; small gaps meaningless.
2. **Single author** — rubrics, gold answers, and the judge-calibration hand-grades are one
   expert; the calibration worksheet had an anchoring channel; cross-expert grading is the fix.
3. **Constructed-case disclosures** — eval #4's case and eval #2's two non-anchor snapshots are
   constructed (labeled, mechanics-faithful, disclosed per-case); eval #5's ETF-swap pair not live-run.
4. **Coverage asymmetry** — #1–#2 never frontier-run; #3–#5 never open-weight-run; Google is
   flash-tier only.
5. **Ceiling effects** on #4/#5 clean + confirm-break cases — the eval no longer separates
   flagships there.
6. **Judge** — offline/mock for the frontier grid; live-judge calibration exists only for eval #2.
7. **Contamination** — filings and the FpML sample are public; a model could have seen them.
   Mitigation: the graded work is derivation, not recall (constructed snapshots, oracle layers),
   but say it.

## 10. Future work (~0.5 p)

- **Eval #6: agentic corporate-actions processing** ($58B/yr documented industry cost; no
  independent public accuracy metrics) — gates designed as verifiable *reward functions* so the
  eval doubles as an RL environment.
- Open-weight leaderboard runs (fills the grid, answers the cross-family caveat on #1–#2).
- Hardening the ceiling cases (graduated break materiality, noisier documents).
- Cross-family judge + blind multi-expert calibration.
- The SFT/distillation flywheel (synthetic FpML → fine-tune → grade with the suite's own gates).

## 11. Reproducibility statement

One dependency, no API key for everything deterministic; the five commands (from PAPER.md §5);
all graded artifacts committed under `outputs/`; MIT. Live runs: any OpenAI-compatible endpoint.

## References (~25 entries)

HealthBench · FinanceBench · FinQA/ConvFinQA/TAT-QA · Vals FAB/FAv2 · FailSafeQA · GDPval ·
APEX · BigFinanceBench (2606.03829) · FrontierFinance (2604.05912) · FinBalance (2606.15949) ·
meta-survey (2607.01740) · FpML 5.10 spec · SEC filings (by accession) · SR 26-2 (one line in
§1 or §10 as deployment context — decide: include or keep the paper regulator-free).

---

# Figure & table list (all real repo data, white/navy brand, dataviz-skill build)

| # | Type | Content | Data source | Section |
|---|---|---|---|---|
| **F1** | diagram | Coverage-gap map: 7 benchmarks × workflow chain (research → analysis → valuation → **post-trade**); post-trade column empty except TieOutBench | README landscape table | §2 |
| **F2** | bar pair | The demo: ungated 0.951 vs gated 0.452, one misread header (the paper's hook image) | `python -m harness demo` output | §1 |
| **F3** | diagram | Grading architecture: checkpoint pipeline → atom tiers → gate tiers w/ blast radius (hard/scoped/in-checkpoint as concentric damage) | rubric/*.md | §3.3 |
| **F4** | heatmap | Leaderboard: 8 models × 5 cases, gated scores, gate glyphs on fired cells | LEADERBOARD.md grid | §6 |
| **F5** | slope/dumbbell | Starved vs fair: 4 GPT models' DCF scores @8k vs @32k (empty→0.953 etc.), the 5.4-mini reversal highlighted | LEADERBOARD methodology table | §7 |
| **F6** | small multiples | Checkpoint-vector comparison: per-checkpoint scores, Opus vs Haiku on DCF (clean spine vs C1 break cascade); optionally + eval #4 | outputs/eval3-live, eval4-live reports | §6.3 |
| **F7** | bar ladder | Blast-radius calibration: 11 DCF planted errors, gated score by gate tier (0.35 → 0.92) | README DCF taxonomy table / selftest | §3.3 |
| **T1** | table | 2026 landscape (7 benchmarks, builder, format, slice, post-trade? column) | README (links verified) | §2 |
| **T2** | table | The five evals: checkpoints/criteria/gates/gold provenance/signature | README + workflow/ | §4 |
| **T3** | table | Full results grid incl. tier labels + gates fired | LEADERBOARD.md | §6 |
| **T4** | table | Vendor token accounting: budget field / thinking charged? / thinking visible? | LEADERBOARD methodology | §7 |
| **T5** | table | Failure taxonomy: class → instance → model → gate → trace file | outputs/*/TAXONOMY.md | §8 |

Build order once outline is approved: F4/F5/F7 (pure data, fastest) → F2 → F1/F3 (diagrams) → F6.

---

# Decisions (answered by Dmitry, 2026-08-01)

1. **Subtitle: (b)** — "Measuring whether an LLM's finance work ties out — before deciding
   whether to trust it."
2. **Repo rename: YES** → `TieOutBench` (GitHub auto-redirects old links; evals.finance stays
   the home, TieOutBench is the suite). *Manual step: Dmitry renames on GitHub Settings; then
   update local remote URL + in-repo self-references (README, PAPER.md, docs/index.html).*
3. **SR 26-2: IN** — one paragraph (§1 or §10), citing his published article as companion piece.
4. **Versioning: v1** of TieOutBench; PAPER.md is the internal ancestor, superseded by `paper/`.
5. **Bio: standing rule** — "ran the change-management side of an institutional ETF servicing
   platform," employer never named. May revisit after more thought; do not loosen without his say.
6. **SSRN category: OK** — "Banking & Financial Institutions" + "Econometrics: Computer Programs"
   cross-list; confirm at submission.

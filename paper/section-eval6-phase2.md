# Eval #6 and its agent environment: paper-ready section drafts (for revision v1.2)

*Prepared 2026-09-25 from the committed artifacts. Every number below is produced by
`python outputs/eval6-agent/summarize.py --json` (agent arms) or by the Phase-1 grid under
`outputs/eval6-live/`; the figures are built by `paper/figures/make_figures_phase2.py` from
`outputs/eval6-agent/summary.json`. The drafts follow the v1.1 template section by section so
they can be dropped into the next revision; nothing here changes a v1.1 number. Numbering below
assumes the revision inserts eval #6 as §4.6 and §4.7, its results as §6.6 and §6.7, and extends
§8 to §11. Models are named in the tables and by tier in the failure narratives.*

---

## 4.6 Eval #6: corporate-actions processing (Phase 1, the document store)

The asset-servicing control that custodians themselves describe as the most manual and
error-prone part of post-trade: process an announced event for an account, on the governing
version of the terms, by the governing dates, and commit only what the deadline allows. Unlike
evals #1 to #5, the model does not receive a curated packet. It receives a **document store**: the
issuer's announcement and, where one exists, its amendment or correction; a custody position
report; an ETF basket file where the event hits a fund; and labeled distractors (a fictional
issuer's split, a real concurrent tender by a different issuer with a different proration factor,
a broker memo). Nothing in the store says which version governs or that the account's position
changed between two candidate record dates. Six cases sit on four real events, each cited to the
issuer's filings by accession number: NVIDIA's ten-for-one split of June 2024 (8-Ks
0001045810-24-000113 and -000144) against a constructed ETF basket, once stale and once already
adjusted; Monster Beverage's oversubscribed self-tender of 2024 (SC TO-I 0001104659-24-058430,
results -069878), once for a prorated institutional holder and once for an odd-lot holder the
priority rule exempts; and two corrected dividends, Berry Corporation's of August 2024
(0001705873-24-000046 and -000052), where the record date moved eleven days and the account sold
shares in between, and Zoetis's of March 2014 (0001555280-14-000162 and -000166), where a Sunday
record date moved to the Monday and nothing economic changed. The accounts, positions and the
basket are constructed and disclosed in each case file; every event term the model is graded on
comes from the filings.

Nine checkpoints (pin the event and the governing version; pin the governing dates; extract the
terms; read the position; compute the entitlement; judge the election; state what changes where;
commit to actions; the calibrated-refusal probe) and five gates: `GATE.VERSION` (terms sourced
from a superseded or distractor document), `GATE.DATES`, `GATE.SCALE`, `GATE.FABRICATION`, and the
signature `GATE.ELECT`, which fires when the plan commits an irreversible wrong action: an
election when none is available, a commitment dated after the deadline, a tender of more shares
than held, or a release on superseded terms or in an amount the governing facts do not permit.
The refusal probe asks for a figure that depends on a document the store does not contain (a
withholding notice, a plan document, the tender's letter of transmittal); the answerable twin is
determined by the store. Every gate is a predicate over the episode's terminal state, which is
what lets the same rubric serve as the reward of the agent environment in §4.7.

## 4.7 Phase 2: the agent environment

Phase 1 graded a written plan. Phase 2 asks which system design prevents the error the plan
revealed. The same six cases, eight models and grader are run four ways (Table 6 and Figure 8):

- **Plain.** The whole store in one prompt; the model writes the worksheet. This is the Phase-1
  grid, unchanged.
- **Tools.** No store in the prompt. The model has ten tools, all pure functions of the case
  file: list and read documents; the account's position as of a date (answered from the position
  history on or before that date, or as a projection after the desk's date when the position
  report states that nothing is pending); an arithmetic-only calculator; four action tools that
  append to a ledger (book a receivable, update the basket line, confirm a position, submit an
  election, which the tool always accepts and the grader judges); escalate (hold one named action
  for one named missing document); and submit the worksheet, which ends the episode. Twenty
  turns and 900 seconds per episode; the Phase-1 per-vendor budgets per turn.
- **Checker.** The tools arm's saved work product (the worksheet and the ledger, never the
  maker's transcript, together with the task inputs) is handed to a second agent of the same
  model with the discovery tools. It ties the work out and calls approve or reject with findings.
  On a reject the maker's ledger is voided, the maker receives the findings and gets one revision
  round, and the reviewer votes once more. The final state is graded.
- **Checker, fixed.** The same protocol with one reviewer, Claude Opus 4.8, for every maker.

Scoring is deterministic in three layers. The **worksheet** goes through the Phase-1 grader
unchanged, which keeps the arms comparable on the nine checkpoints. The **terminal state** is the
same worksheet with its action rows replaced by the ledger rendered into rows and passed through
the same grader, so `GATE.ELECT` fires on what was booked rather than on what was written; ledger
predicates that map onto the existing gates zero the decision checkpoint without adding a gate (a
booking the worksheet does not tie to, a missing or disallowed booking, a hold that contradicts a
booking or holds a fully determined event, a receivable whose amount matches no permitted
figure). **Trajectories** are recorded and reported, never scored: whether the governing document
was read before the first action, which dates were passed to the position tool, whether the
calculator was used, and, for a reviewer, whether it recomputed or only read. Native function
calling through each vendor's OpenAI-compatible endpoint is verified by a one-turn conformance
test before any graded run; a model whose endpoint refuses function tools runs a text protocol
(one fenced JSON block per call), and the run record discloses which. Three repeats per cell were
run on the corrected-dividend case for all four arms. Every episode is saved with its transcript,
ledger, worksheet, terminal state and run record.

---

## 6.6 Results: eval #6, Phase 1 (48 runs, 2026-08-18)

Thirty-two of 48 runs AllPass. Claude Sonnet 4.6 scored 1.000 and AllPass on all six cases, the
suite's first perfect live row; six of eight models sit at or above 0.92 on every case. The
marquee gate fired for the first time in the series, on the small tier: GPT-5.4-mini pinned the
correct correction notice, stated the corrected record date, computed the entitlement on the
superseded 50,000-share position and booked $8,500 where $6,800 was due; `GATE.VERSION` and
`GATE.ELECT` both fired, 0.225 gated against 0.574 ungated. The class "derive the right number,
report a different one" replicated in a third domain on the refusal twin, and a planted trap
fired where it was designed to: on the already-adjusted basket two models answered the dividend
twin at the pre-split rate times post-split shares. No model used a distractor's figures or the
naive proration recompute. Full findings and the grader log in `outputs/eval6-live/TAXONOMY.md`.

## 6.7 Results: the agent environment (2026-09-24/25)

**Table 6. The four arms (48 cells each; one run per cell).**

| | plain | tools | checker (self-review) | checker (fixed reviewer) |
|---|---:|---:|---:|---:|
| AllPass | 32 | 35 | 27 | 25 |
| `GATE.ELECT` fired | 1 | 0 | 0 | 0 |
| any gate fired | 2 | 4 | 8 | 14 |
| ledger correct (booked, no gate, ties to worksheet and gold) | n/a | 46 | 44 | 46 |
| mean gated score | 0.965 | 0.943 | 0.915 | 0.924 |
| mean maker turns per episode | 1 | 7.1 | 9.0 | 8.0 |

**Table 7. Clean cases per model, of six, by arm** (Figure 10).

| Model | plain | tools | checker | checker, fixed |
|---|---:|---:|---:|---:|
| Claude Opus 4.8 | 4 | 5 | 5 | 3 |
| Claude Sonnet 4.6 | 6 | 6 | 6 | 5 |
| Claude Haiku 4.5 | 3 | 2 | 1 | 1 |
| GPT-5.6-sol (text protocol) | 5 | 6 | 4 | 4 |
| GPT-5.5 | 5 | 5 | 4 | 4 |
| GPT-5.4 | 4 | 6 | 3 | 6 |
| GPT-5.4-mini | 0 | 0 | 0 | 0 |
| Gemini 3.6 Flash | 5 | 5 | 4 | 2 |

**Tools helped the middle tier and hurt the small tier; the flagships were at the ceiling.**
GPT-5.4 went from four clean cases to six, GPT-5.6-sol from five to six, Opus from four to five;
Sonnet stayed at six. Haiku fell from three to two: on both tender cases it left the worksheet's
election-deadline field empty and fired `GATE.DATES` while its ledger was right to the dollar. The
small OpenAI model's two split cases collapsed: on the already-adjusted basket it divided instead
of confirming, setting the basket line from 1,800 to 180 and booking a $180 receivable on 18,000
shares, both caught by the ledger predicates; on the stale basket its ledger was right and its
worksheet fired three gates. The tools arm's mean gated score is lower than the plain arm's for
those two cells alone; on the other 46 cells it is at least as good.

**The marquee gate did not fire in the 48 recorded tools cells, and the repeats say why that is
not the finding.** The small model was run five times through tools on the corrected dividend. It
booked $8,500 twice and $6,800 three times. Both wrong runs read the correction notice, called
the calculator with 50,000 shares, and never called the position tool. All three right runs
called it, each asking for the position as of the desk's own date rather than the record date,
and got the right number because no position change was scheduled. The tool that prevents the
error was in every run and was used in three of five, never for the date the entitlement is keyed
to. The same model's three plain-arm repeats all booked $6,800.

**Position-date discipline, measured.** Every tools run read the governing document before its
first action and used the calculator (48 of 48 each). The entitlement's basis date was queried in
37 of 48 runs. On the 16 dividend cells, five runs also queried the superseded record date, saw
50,000 shares, and booked on the corrected 40,000: the trajectory of a desk that checks the
position change rather than assumes it. Two runs never queried the position at all.

**A same-model checker made the work worse** (Figure 9, left). Reviewers did the tie-out: all 48
queried the position in the first round, 45 used the calculator, 4.9 turns on average. They then
rejected 20 of the 46 correct ledgers and approved one of the two wrong ones. The one wrong ledger
caught was the reversed basket (re-booked correctly on revision; its worksheet stayed wrong); the
one approved was Haiku's basket line left unconfirmed. The rejections of correct ledgers were confident and
specific: the announcement 8-K cited as basis where the reviewer preferred the effectiveness 8-K
(both are accepted governing documents), a memo that said "was 1,800" for the pre-split
quantity, a tender pay date the store does not state, a dividend receivable called premature
because the record date lies a day after the desk date. The makers complied with 21 rejections,
and the revisions put a gate on four cells that had none and un-booked or held a correct
receivable in three: a split's entitlement
basis moved to the dividend's record date after the reviewer conflated the two events; the net-cash
probe answered as equal to the gross because the store holds no withholding document; correct
tender receivables un-booked and held (in one maker's words, "pending a payment-date source").
AllPass fell from 35
to 27 with the same models as makers.

**A stronger fixed reviewer was better on the verdicts and worse on the probe** (Figure 9,
right). With Opus 4.8 reviewing every maker, 13 correct ledgers were rejected instead of 20, 33
approved instead of 26, the same two wrong ledgers were caught and missed, and 46 of 48 ledgers
came through correct. The arm still finished with 25 clean cells and a gate in 14. Ten of the 13
rejections of correct ledgers carried the same finding, in the reviewer's words on one cell: "MEGA is a U.S.
ETF and NVIDIA Corporation is a U.S. issuer; a U.S. fund's dividend from a U.S. corporation is not
subject to withholding. No withholding schedule is 'missing' because none is needed". It
instructed the makers to replace the NOT_DETERMINABLE answer and the escalation with a computed
net of $1,800 on nine split cells (and once, "no fees deducted / $0" on the tender's
letter-of-transmittal probe); the maker complied each time (six makers, ten cells), and
`GATE.FABRICATION`
fired ten times on worksheets that had been calibrated before the review. The store never states
the fund's domicile or tax status. The two review protocols fail in opposite directions:
self-review rejects correct bookings for reasons the store does not support; the strong reviewer
uses its authority to assert what the store does not say. GPT-5.4 under the fixed reviewer scored
six of six, its best row in any arm. Neither protocol improved on the tools arm, and the ledgers
were never the problem in either: 46, 44 and 46 correct with no reviewer, self-review and the
fixed reviewer. The review round moved the worksheet, and mostly moved it the wrong way.

**Repeatability.** Sonnet: twelve runs across four arms, twelve AllPass. Opus: the same 0.983
partial in every repeat of every arm, a stable one-item loss rather than noise. Haiku and Gemini:
the same 0.983 in every repeat with tools or a reviewer; in the plain arm Haiku was clean twice
and Gemini scored 0.948 once. GPT-5.4: three clean tools runs where the plain arm gave one. The small model: both sides of the finding
in the tools arm. Reviewer verdicts on correct work with the same bookings were not stable under self-review
(GPT-5.4's reviewer: approve, reject, approve) and were under the fixed reviewer (every correct
repeat ledger approved; the one wrong one caught and re-booked).

**Transport.** Native function calling passed the conformance test on all three endpoints for
seven models. The OpenAI compatibility endpoint refuses function tools for GPT-5.6-sol with
reasoning enabled, so that model ran the text protocol in every arm; it scored six of six with
tools and three of three on the repeats, and its review-arm losses are the reviewer-induced holds
above.

---

## 8 (addition). Failure taxonomy rows for the agent environment

| Class | Instance | Tier | Gate or flag | Trace |
|---|---|---|---|---|
| Tool present, not used | booked $8,500 without calling the position tool (2 of 5 attempts) | small | `VERSION`+`ELECT` | `outputs/eval6-agent/tools/gpt-5.4-mini/bry-dividend-2024/prior/`, `repeat/tools/.../r1` |
| Right answer, wrong query | queried the position as of the desk date, not the record date (3 of 5) | small | none (reported) | `outputs/eval6-agent/tools/gpt-5.4-mini/bry-dividend-2024/` |
| Reverse adjustment | already-adjusted basket set from 1,800 to 180; $180 receivable | small | `ledger_wrong_amount`, `ledger_inconsistent` | `outputs/eval6-agent/tools/gpt-5.4-mini/mega-split-2024-clean/` |
| Booked right, wrote wrong | correct ledger under a worksheet with three gates | small | `DATES`,`SCALE`,`FABRICATION` | `outputs/eval6-agent/tools/gpt-5.4-mini/mega-split-2024/` |
| Form field left empty | election deadline null on both tenders, ledgers right | small | `DATES` | `outputs/eval6-agent/tools/claude-haiku-4-5-20251001/mnst-tender-2024*/` |
| Reviewer finding the documents contradict, executed | maker moved the split's basis date to the dividend's record date | small | `DATES` | `outputs/eval6-agent/checker/claude-haiku-4-5-20251001/mega-split-2024/` |
| Reviewer demand the store cannot meet | "The booked pay_date of 2024-06-10 is unsupported" led the maker to un-book a correct receivable | flagship | `ledger_missing_required`, `ledger_overescalate` | `outputs/eval6-agent/checker/gpt-5.6-sol/mnst-tender-2024/` |
| Reviewer over-rules a refusal | a U.S. fund, so no withholding and the net equals the gross (nine cells); no fees on the tender (one); executed each time, by six makers | all tiers | `FABRICATION` x10 | `outputs/eval6-agent/checker-fixed/*/mega-split-2024*/`, `checker-fixed/gemini-3.6-flash/mnst-tender-2024/` |
| Reviewer rejects with no discrepancy | findings say "no discrepancy" three times; verdict reject | small | (revision emptied the ledger) | `outputs/eval6-agent/checker/gpt-5.4-mini/mega-split-2024/prior/` |

## 9 (addition). Limitations

7. **One run per cell, three on one case.** The repeats cover the corrected dividend only. The
   small model's two-of-five is a count, not a rate.
8. **The reviewer was not given the desk's rules.** Both review prompts asked for a tie-out to the
   source; neither carried the maker's calibration rule (a refusal is not a defect; name the
   missing document; do not invent a value) or the statement that both 8-Ks govern. Same documents
   and same tools are not the same rules, and the fixed reviewer's ten fabrications are the
   clearest consequence. Whether the over-rule survives a reviewer that carries the rules is the
   next run, not this result.
9. **The withholding probe's gold is a design position.** The store does not state the fund's
   domicile or tax status and the gold requires the custodian's notice; a U.S. regulated fund on a
   U.S.-source dividend ordinarily has no withholding, so the reviewer's inference is plausible.
   The result stands as recorded; a case revision could state the ambiguity outright.
10. **One review protocol.** Void-and-revise with one round, a binary verdict with full
    authority, and makers that never re-verified a finding. The checker results are about that
    protocol, not about review in general.
11. **The checker arm ran twice.** The first wave's reviewer packet omitted the probe question,
    and reviewers rejected correct escalations as unsupported (19 of that wave's 28 rejections).
    The packet was fixed and the arm re-run with the same reused makers; the first wave is
    preserved under each cell's `prior/` and reported as a footnote only.
12. **Grader movement, disclosed.** The Phase-2 prose surfaced eight false fires in the Phase-1
    worksheet grader and six contract gaps in the environment's own predicates. All are fixed and
    pinned by regression checks; all 48 committed Phase-1 answers re-grade identically on gated
    score, ungated score, gates and checkpoints, and one diagnostic category rollup moved
    (GPT-5.4-mini, corrected dividend, calibration from -0.385 to +0.077).

13. **"Correct ledger" is the grader's definition, and the environment induced some rejections.**
    The reviewer two-by-two scores verdicts against the ledger predicates (required bookings
    present, amounts and share counts tie, nothing disallowed), not against every field, and the
    reviewer also reads the worksheet. Read finding by finding, 7 of the 20 self-review rejections
    and 3 of the fixed reviewer's 13 raise at least one objection the documents support. Five of
    the seven are the tender's payment date: `book_receivable` requires the field, no document
    states the date, and the grader does not score it; three makers then removed a correct
    receivable because the tool cannot book without a date. Four more self-review rejections
    objected to "(was 1800)", the environment's rendering of a basket update that changes nothing.
    The outcome counts (35, 27, 25) do not depend on the reading; three of the eight cells
    self-review cost trace to the payment-date field. The per-cell table is in
    `outputs/eval6-agent/TAXONOMY.md`, finding 12.
14. **Five saved trajectories, not five trials.** The small model's five tools attempts on the
    corrected dividend are the first attempt (its run stopped on a harness error after the ledger
    was saved), the grid cell and three repeats, and the harness changed between attempts (the
    agent loop after the first; the environment, the transport and the worksheet grader before
    the repeats; hashes in each `run.json`).

## 10 (replacement of the eval #6 bullet, and additions)

- **Eval #6 shipped in two phases** (§4.6, §4.7): the document-store grid, then the agent
  environment whose gates are terminal-state predicates. The build is the RL environment the v1
  bullet promised; the reward is the gated score with the ledger predicates.
- **A review protocol that cannot over-rule a refusal.** The reviewer carries the desk's rules,
  may reject a booking but not instruct a value for a refusal, and the maker re-verifies each
  finding against the source before acting. The two review arms above are its baselines.
- **Newer model generations** (Claude Opus 5.5, Fable 5.1, Sonnet 5; Gemini 3.8) pass the
  conformance test and can be added as eval-6 rows at a few dollars per model.

## 11 (addition). Reproducibility

```bash
python -m harness env --oracle                 # the scripted oracle through the tools, all six cases
python -m harness env --planted superseded_position
python outputs/eval6-agent/summarize.py --json # every table in §6.7 from the saved cells
python paper/figures/make_figures_phase2.py    # Figures 8 to 10 from summary.json
python -m harness profiles                     # the grid with an `arm` field per row
```

Every cell under `outputs/eval6-agent/` carries its transcript, ledger, worksheet, terminal state
and run record (model, endpoint host, transport, budgets, usage, case and grader hashes); the
selftest runs the environment's oracle and planted trajectories and 32 gaming checks on the new
surfaces, and the eval-6 worksheet grader's regression suite is now 92 checks.

## Figures and tables added

| # | Type | Content | Source | Section |
|---|---|---|---|---|
| **F8** | bar pair | the four arms: clean runs of 48, and cells with a gate fired | `summary.json` | §6.7 |
| **F9** | two-by-two pair | reviewer verdict against the ledger shown, self-review beside the fixed reviewer | `summary.json` (two_by_two) | §6.7 |
| **F10** | small multiples | clean cases per model (of 6) by arm, gate counts in red | `summary.json` | §6.7 |
| **T6** | table | the four arms: AllPass, gates, ledgers correct, mean gated, turns | `summary.json` | §6.7 |
| **T7** | table | clean cases per model by arm | `summary.json` | §6.7 |
| **T8** | table | taxonomy rows for the agent environment | `outputs/eval6-agent/TAXONOMY.md` | §8 |

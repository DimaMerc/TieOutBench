# Workflow — ETF NAV oversight (eval #7)

> The fund-accounting **"release only if it ties"** control, ported to an AI. Given a fund
> administrator's preliminary daily NAV package for an ETF, the counterparty swap valuation
> statements, the market data and the fund's NAV error policy: recompute the NAV from the
> position-level inputs, check the day's move against the expected leveraged index move, localize
> any break to its line, quantify it against the materiality regime - and **release the NAV only if
> it ties.** Phase-1 deliverable of eval #7. Rubric: `rubric/criteria-nav-oversight.yaml`.

## Why this eval exists

NAV production is where the 2024-2026 ETF error record actually sits, and it is the one
fund-servicing process the custodians say they are putting AI on. Both halves are documented.

**The incident record.** The public ETF NAV restatements of 2026 and the SEC correspondence behind
earlier ones trace mostly to the bookkeeping of derivatives and income, not to equity pricing:

- AdvisorShares MSOS Daily Leveraged ETF (MSOX), press release of March 6, 2026: NAVs for December 22,
  2025 to February 2, 2026 restated because of the "Fund Administrator not correctly accounting for
  income accruals for some of the total return swaps"; "Responsibility for the accurate calculation
  and reporting of the Fund's NAV is contractually vested in the Fund Administrator, and any losses,
  claims, damages, or expenses arising from this error are solely the responsibility of the Fund
  Administrator" ([AdvisorShares](https://advisorshares.com/press-release-nav-restatement-for-the-advisorshares-msos-daily-leveraged-etf-msox/)).
- Simplify Multi-QIS Alternative ETF (QIS), November 29, 2024: NAV restated from $24.87 to $24.61,
  "an incorrect swap security price".
- Rydex Series Funds, SEC correspondence of February 1, 2024: "use of a stale price (i.e., the prior
  day's price) for a total return swap held by the Funds"; one fund "overstated by more than 1/2 of 1%".
- VanEck ETF Trust, SEC correspondence of May 23, 2024: the administrator "misstated the NAV of the
  Fund's Cayman Islands subsidiary due to booking a swap reset transaction incorrectly" and
  reimbursed $28,979 ([CORRESP](https://www.sec.gov/Archives/edgar/data/1137360/000113736024000383/filename1.htm)).
- SPDR Series Trust, SEC correspondence of January 6, 2026: the SPDR S&P Bank ETF's NAV "was
  understated by $0.01" on May 14, 2025 because "A manual entry to record income on the Fund's books
  and records, related to the receipt of a non-recurring cash payment, was delayed by one day due to
  an oversight" ([CORRESP](https://www.sec.gov/Archives/edgar/data/0001064642/000119312526003991/filename1.htm)).
- YieldMax GME Option Income Strategy ETF (GMEY), notice of April 26, 2026: the restatement "relates to
  the Fund's accounting treatment of trades executed in connection with significant redemption
  activity on March 2, 2026 in calculating NAV, which resulted in dilution to remaining shareholders";
  March 2 overstated by $0.1949 per share, March 3 to April 24 understated by $1.1694 per share.
- Also in the 2026 cluster: JPMorgan HOLA (June 16, 2026, $54.40259 to $55.12158), Roundhill METV
  (June 12, 2026, $18.6792 to $18.0270), AdvisorShares HDGE and DWSH (July 2, 2026, "an incorrectly
  recorded trade"). The administrator is unnamed in every 2026 press release.

The materiality regime that decides what happens next is contractual, not codified: the JPMorgan /
First Eagle ETF Trust Fund Services Agreement defines a NAV error at "at least $0.010 per share", uses
0.5% of NAV for shareholder reprocessing and carries "a de minimis amount of $20" per account; the
Rydex and Northern Lights letters apply the same 0.5% test. A Luxembourg UCITS is judged instead
against CSSF Circular 24/856 (0.2% money market, 0.5% bond and mixed, 1% equity; regulator
notification within four to eight weeks of detection), and the SEC's FY2026 examination priorities
single out "option-based ETFs, and leveraged and/or inverse ETFs" - the products that dominate the
2026 restatements.

**The AI claims.** The custodians' AI narrative sits on this exact process and publishes no accuracy
figure for the AI's decisions. BNY's fund-accounting page pairs "AI-powered NAV oversight includes
Dynamic Fund Benchmarking which compares fund performance across the client base, transaction anomaly
detection to identify transactions with unexpected impacts and yield anomaly detection highlighting
unexpected yield movements" with "99.99% NAV accuracy" - a production-quality figure, not an
AI-detection one. A Citi job posting of August 18, 2026 describes "a digital workforce of specialized
AI agents ... taking on complex, multi-step tasks autonomously across fund accounting, ETF operations,
middle office, and transfer agency". Anthropic's financial-services agent templates (May 5, 2026)
include a "General ledger reconciler" that "reconciles general ledger accounts and runs net asset
value calculations", with no task-level accuracy. The one quantified manual-load figure is
vendor-documented: at one custodian's fund-administration arm reconciliation "consumed approximately
40% of total fund accountant time - more than 10,000 hours per month" (ActiveOps, March 2026).

**The whitespace, stated honestly.** Surge AI's DAYJOB (arXiv:2610.01306, October 1, 2026) lists
"fund operations (net asset value, pricing review, rebalancing)" among its 80 finance tasks and grades
them with "an expert rubric of binary criteria (median 47.5 and 57.5 per task) that an agentic judge
applies"; its strongest model "passes 24.7% of healthcare and 23.9% of finance attempts". This eval
differs in kind: deterministic checks over a position-level package, failure patterns taken from the
SEC-letter record, a jurisdiction-aware materiality regime, calibrated refusal, and a release/hold gate
- the control a desk actually runs.

## Sourcing (read this)

A fund administrator's NAV package - the valuation ledger, the accrual ledger, the capital-stock
record, the pricing-exception report - is an administrator work product, *not* a public filing. So the
gold cases are **constructed, mechanics-faithful** scenarios, as eval #4's are: the underlying ETF
(VanEck Semiconductor ETF, SMH) and the reference index (PHLX Semiconductor Sector Index, SOX) are
real; the prices and index levels are representative; the **fund, the swaps, the counterparties, the
administrator and the break are illustrative**, and the failure pattern is the documented one (a stale
prior-day swap price). The fund ("Granite Ridge 2x Daily U.S. Semiconductor ETF", GRSL) belongs to the
suite's fictitious issuer so that no real issuer, administrator or counterparty is implicated. Flagged
in the case headers and the README.

## The mechanics (real)

NAV per share = (total assets - total liabilities) / shares outstanding, struck daily at the close. A
total return swap is carried at its unrealized value = notional x (index level / reset level - 1), with
the financing accrued since the last reset carried as a liability; the counterparty's daily valuation
statement is the pricing source. A price dated before the valuation date and "carried forward" is a
**stale price** - the pricing-exception report flags it. NAV oversight recomputes the NAV from the
position-level inputs, checks the day's move against the expected move (leverage x the reference index
return; a deviation beyond the oversight band must be explained before release), and **releases the
NAV only if it ties**; pre-release, a known error at or above the per-share floor is corrected and the
NAV re-struck. Post-release, the 0.5% threshold decides whether shareholder transactions are
reprocessed or the fund alone is made whole.

## The gold case and the planted break

A 2x daily leveraged ETF on **2026-06-23**: 400,000 SMH shares, two total return swaps on SOX of
147,000,000 notional each (reset 2026-05-29 at 4,900.00), a 95,000,000 face T-bill, cash; 4,000,000
shares outstanding, prior NAV **50.0000**. The index closed **5,100.00** against 5,000.00 (+2.00%), so
the fund should move about **+4.00%**. Every line ties to the independent inputs but one: **SWAP-B is
carried at the prior day's mark of 3,000,000.00** (index 5,000.00) because the Westbrook valuation file
arrived at 17:52 ET, after the 17:30 pricing cut-off; the statement in the packet, dated 2026-06-23,
values it at **6,000,000.00** (index 5,100.00). The administrator's NAV is **51.2412**; the recomputed
NAV is **51.9912** - understated by **0.7500 per share (1.44%)**, above the $0.01 floor and the 0.5%
threshold. The reasonableness check gives it away first: the administrator's +2.48% against an expected
+4.00% is 1.52 points outside a 0.25-point band. Gold answer: **HOLD**, localized to SWAP-B, correct
the mark from the statement that is already in the packet, re-strike at 51.9912 before the 18:00
release; no shareholder reprocessing, because nothing was transacted at the wrong NAV.

## Checkpoints (8)

| CP | Stage | Grades | Gate |
|---|---|---|---|
| **P1** | planning | pin {fund, ticker, package_id}, the **valuation date** and its prior day, the review inputs (prior NAV, shares, administrator NAV, leverage), the **materiality regime** from the policy excerpt | **GATE.DATE** (hard) on the date; **GATE.REGIME** (scoped) on the regime |
| **E1** | extraction | the administrator's package as reported: ledger and liability lines, totals, the **STALE_PRICE flags**, a citation | - |
| **E2** | extraction | the independent inputs: counterparty swap statements, closing prices and index levels, capital stock | - |
| **C1** | calculation | line-by-line administrator vs independent value; isolate the exception to the **stale-priced swap** | - |
| **C2** | calculation | recomputed total assets, liabilities, **total net assets and NAV per share**; **scale lock** | **GATE.SCALE** (hard) |
| **C3** | calculation | the error at fund level, per share and in percent; its **direction**; the floor and 0.5% tests; the **reasonableness check** | **GATE.SIGN** (scoped) on an inverted direction |
| **D1** | decision | the **release/hold call**, the classification and reprocessing call, localized to the line with the corrected NAV, emitted as a structured record | **GATE.RELEASE** (the signature) |
| **D2** | refusal | calibrated refusal: the fund's **exchange closing price and premium/discount are not in the accounting package**; the administrator-minus-recomputed difference IS computable | **GATE.FABRICATION** on a made-up price or an assumed zero premium |

Checkpoint weights: P1 .10 / E1 .10 / E2 .10 / C1 .14 / C2 .14 / C3 .16 / D1 .16 / D2 .10. D2's
headline is the FailSafeQA F-beta LLMC_beta(R, G), beta = 0.5 (the eval-#1 E6 exception, inherited).
37 criteria, 6 gates.

## Gate ledger

| Gate | Tier | Fires when | Blast radius |
|---|---|---|---|
| **GATE.DATE** | hard | the package is pinned to the wrong valuation date (the prior day's package reviewed as today's) - every mark, accrual and move is then read against the wrong day | C1, C2, C3, D1 |
| **GATE.REGIME** | scoped | a foreign or invented threshold set replaces the fund's own policy (CSSF thresholds on a US fund), or the review stage is misread | D1 |
| **GATE.SCALE** | hard | totals in thousands read as dollars, a per-share figure at fund level or vice versa - fires on evidence (a figure sitting on a scale factor of gold), never on absence | C3, D1 |
| **GATE.SIGN** | scoped | the direction is **inverted** (understated reported as overstated); a missed error is not an inversion and does not fire it | D1 |
| **GATE.RELEASE** | scoped (**signature**) | the model **RELEASES a NAV whose error reaches the per-share floor** - any approval synonym; a contradictory "release and escalate" is ambiguous and earns nothing without firing | D1 to 0, **release_override_fired** flag |
| **GATE.FABRICATION** | hard (figure) | a fabricated position or statement line, or a made-up exchange close / premium (an assumed zero premium counts) | per-figure void; AllPass = 0 |

## The taxonomy (oracle + eight designed flaws, each tripping its gate)

| Variant | Gated | Gate | What it shows |
|---|---:|---|---|
| `oracle` | 1.000 | none | perfect review: catches the stale mark, recomputes 51.9912, HOLD, localized |
| `release_override` | 0.840 | **GATE.RELEASE** + flag | *all math right, RELEASED the wrong NAV* - the highest-scoring decision failure and the most dangerous |
| `fabricate_price` | 0.900 | GATE.FABRICATION | invented the exchange close and a premium; D2 G = 0 (the decision itself is right) |
| `regime_slip` | 0.817 | GATE.REGIME | applied CSSF Circular 24/856 to a US fund; the hold is right, the classification is on the wrong footing |
| `sign_flip` | 0.708 | GATE.SIGN | reported the understated NAV as overstated - who is harmed flips |
| `scale_slip` | 0.579 | GATE.SCALE | ledger totals read in thousands as dollars |
| `stale_blind` | 0.354 | GATE.RELEASE + flag | adopted the carried-forward mark, reproduced the administrator's NAV, rationalized the move, RELEASED - the worst case: the control never engaged |
| `date_slip` | 0.347 | GATE.DATE | reviewed the package as the prior day's - the biggest cascade |

Reproduce any row: `python -m harness run --case grsl-nav-2026 --model <variant>`.

The pattern *is* the finding: the eval tells "looks right, is wrong" (`release_override`, 0.840, the
control switched off with every number correct) apart from "never saw it" (`stale_blind`, 0.354) and
from a foundational error (`date_slip`, 0.347) - and localizes each to the checkpoint that owns it.
Note that two variants fire the same signature gate at very different scores: the headline flag says
*what* was done (a wrong NAV released); the checkpoint vector says *why*.

## The over-cautious mirror (a second gold case)

A NAV oversight control that *holds a correct NAV* past the release deadline is as useless as one
that releases a wrong one. So a second gold case - `cases/grsl-nav-2026-clean.case.yaml` - is the same
package with the Westbrook file received before the cut-off, so SWAP-B carries the current mark, the
recomputed NAV equals the administrator's 51.9912, the move (+3.98%) sits inside the band, and the
gold answer is **RELEASE**. The `false_hold` variant (HOLD on a package that ties) scores 0.840 with
D1 at zero and no gate: the `D1.n_falsehold` penalty is sized to zero the decision checkpoint on its
own, so the classification and localization atoms a perma-holder still earns do not rescue the call.
Without this case a perma-holder would AllPass; with it, the eval scores both directions of the
release/hold call.

## Hardening (adversarial gaming review)

The release/hold call is graded by a **word-token classifier** with negation ("not approved", "release
withheld", "Release: NO"), conditions ("correct and re-strike, then release" and "release only after the swap
mark is corrected" are holds) and contradictions ("RELEASE; escalate the swap mark separately" and "HOLD but
release to the exchange" earn nothing and fire no gate). An approval synonym ("approve and release for
publication", "OK to release", "sign off, NAV final", "good to go") still trips GATE.RELEASE on the break case, and
a release instruction placed in the escalation field trips it too; a decision outside the RELEASE|HOLD contract
earns nothing on the decision checkpoint. The scale gate fires only on evidence (a present figure within 5% of a
x10, x100, x1000, x1e6, x1e9 or share-count multiple of gold, sign ignored), so a merely wrong total does not trip
it. The refusal grader treats a parseable value, digits in the label, a price or premium asserted near a price
word in the reasoning, or an un-negated "assume the shares closed at NAV" as a fabrication, matches the twin with
its sign, and carries a clause-level contradiction check and the echoed-instruction guard.

The six-attacker adversarial gaming review ran on 2026-10-06 (one attacker per surface: the decision classifier,
the refusal grader, the numbers and scale gate, extraction and reconciliation, structure and regime, and
legitimate formats the grader might fail; notes and scripts under `outputs/eval7-live/gaming-review/`). It
reproduced the letters-inside-words failures of the first classifier (the signature failure at 1.000 with "(see
note)" appended), the one-field fabrication check, status-only ledger grading, gold-string citations, hard gates
fired by date and regime notation, integer-zero booleans read as unknown, ungraded schema fields and grader
crashes on malformed sections. All were fixed, the saved runs re-graded with provenance (four scores moved, none
of them a decision or a gate), and eighty-six of the attackers' cases pinned as standing checks in
`harness/gaming_review_eval7.py`, run by `python -m harness selftest`. The write-up is in
`outputs/eval7-live/TAXONOMY.md`.

## Planned cases (the rest of the documented failure taxonomy)

| Pattern | Documented in | What it adds |
|---|---|---|
| a missing swap financing / income accrual (the admin's accrual ledger skips a leg) | MSOX, March 2026 | the liability side; an error that is small per day and compounds over 18 dates |
| redemption-day trade accounting that dilutes remaining holders | GMEY, April 2026 | capital stock and same-day trades: the share count and the cash from a redemption booked on the wrong footing (extends eval #4) |
| a one-day-late manual income entry landing exactly at the $0.01 floor | SPDR S&P Bank ETF, May 2025 (CORRESP Jan 2026) | the threshold edge: material under the floor, immaterial under the 0.5% test; tests calibration at the boundary |
| the same break in a Luxembourg UCITS | CSSF Circular 24/856 | the jurisdiction-aware regime: 1% equity threshold, four-to-eight-week CSSF notification, the auditor's special report; the DACH / Luxembourg reader's case |
| a post-release discovery with transactions on the day | Rydex, Northern Lights | reprocessing required; who is harmed and in which direction; the compensation question becomes the D2 probe (shareholder-level data not in the package) |

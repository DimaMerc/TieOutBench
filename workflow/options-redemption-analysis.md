# Workflow — Options-component ETF redemption tie-out (eval #8)

> The settlement tie-out of an in-kind ETF redemption whose basket is made of exchange-traded
> options. Given an Authorized Participant's redemption order, the published redemption basket
> (the PCF), the OCC position-transfer confirmations for each option leg, the custodian's position
> report, the NAV statement and the ETF agent's settlement recap: tie every leg by series, strike,
> expiry, side and quantity, recompute the cash component from the NAV and the marks, localize any
> break - and **settle only if every leg ties.** Phase-1 deliverable of eval #8. Rubric:
> `rubric/criteria-options-redemption.yaml`.

## Why this eval exists

Creations and redemptions are the one ETF process the infrastructure providers describe, in a
regulatory filing, as still manual and error-prone - and only for one product class: ETFs whose
baskets hold options.

**The regulator-grade statement.** NSCC's rule filing SR-NSCC-2026-001 (Federal Register, January 29,
2026; SEC notice Release 34-104687 of January 26, 2026; approved by Release 34-104981 on March 12,
2026) describes the process this eval ports to an AI:

- "While the creation of ETF units with underlying option components may currently be done on a
  'cash-only' basis at NSCC, ETF market participants typically handle the redemption of such ETFs on
  an 'ex-clearing' basis (e.g., outside of traditional clearing mechanisms and NSCC). APs and ETF
  Agents have raised concerns regarding the existing processes for clearing ETFs that have option
  components in their trading baskets."
- "Specifically, APs and ETF Agents must initiate a 'cash-only' creation at NSCC, and the ETF Agent
  uses the cash received from the order to purchase the necessary underlying options components for
  the ETF through a prime broker, which are cleared by OCC. Conversely, the entire redemption process
  is generally managed ex-clearing, requiring multiple manual steps to ensure completion, including
  the tracking, pricing, validation and ultimate execution of options positions transfers at OCC by
  the APs, ETF Agents and primer brokers [sic], which are required in connection with the redemption
  process. This process, as it stands, is fragmented and heavily dependent on manual intervention,
  which increases the potential for errors and operational" risk.
- "market participants primarily manage this process outside of NSCC today (i.e., ex-clearing)
  through fragmented and cumbersome manual workflows, and without the benefit of NSCC's CCP guaranty,
  which introduces operational and counterparty credit risks among market participants."
- "NSCC understands that industry participants would initially use this new functionality primarily
  for ETF redemption orders, which currently present the largest challenges for industry
  participants."

The filing cites OCC's SR-OCC-2025-010 (Release 34-103521, July 22, 2025) as "intended, in part, to remove
any uncertainty about whether adjustment of options positions at OCC is permissible to support ETF
creations and redemptions" (the OCC filing codifies the permission; it describes no mechanics), and commits NSCC to implement NSCC-to-OCC messaging for in-kind
creations and redemptions "by no later than 60 Business Days after the approval", the effective
date to be announced by Important Notice. The filing quantifies nothing: no count of affected ETFs,
assets or orders ([govinfo FR PDF](https://www.govinfo.gov/content/pkg/FR-2026-01-29/pdf/2026-01739.pdf);
[SEC SRO page](https://www.sec.gov/rules-regulations/self-regulatory-organization-rulemaking/sr-nscc-2026-001)).

**The servicer's view.** State Street's Ken Shaw (Head of ETF Solutions EMEA) named "centralised
clearing of options" among planned automations, alongside "line-by-line expense models", "real-time
order/trade bursting, and trade date P&L inclusion in PCF computations" (ETF Express, April 2, 2026,
["Building the infrastructure"](https://etfexpress.com/2026/04/02/building-the-infrastructure/)).
An intention, with no metric and no accuracy figure - the pattern across every custodian statement
in the October 2026 research scan.

**The product base.** Options-based ETF strategies hold roughly $280 billion (J.P. Morgan ETF Market
Guide); defined-outcome ("buffer") ETFs built from FLEX options are the largest family, with
monthly vintages from several issuers, and the SEC approved FLEX options on bitcoin ETP shares on
July 29, 2025. Every one of these funds redeems through the process the NSCC filing describes.

**The whitespace, stated honestly.** No public benchmark touches ETF creation or redemption
processing, basket or PCF work, or OCC position transfers (research scan of October 4, 2026; the
nearest suites are Surge AI's DAYJOB, whose finance tasks include fund NAV and tie-out workpapers,
and this suite's own evals #2, #4 and #5). This eval is the moat piece of the suite: the authoring
requires derivatives processing and ETF-servicing change management at once.

## Sourcing (read this)

A redemption basket for a specific order, the OCC position-transfer confirmations, a prime-broker or
custodian position report and an ETF agent's settlement recap are **not public documents**. So, as in
evals #4 and #7, the gold cases are **constructed, mechanics-faithful** scenarios:

- the **option contract specifications are real**: FLEX options on the iShares Russell 2000 ETF
  (IWM) carry the OCC root `4IWM` in the OSI identifier, a contract multiplier of 100, European
  exercise and physical settlement, and expire on the last business day of the fund's outcome period
  (eval #2 verified this symbology and these conventions against a real N-PORT filing; the
  2026-09-30 expiry is the real October-vintage expiry);
- the **underlying is real** (IWM); the reference price, the strikes and the marks are
  **representative and internally consistent**, not actual market levels (the fund's reference price
  is a round 240.00 so that no real fund's terms are implied);
- the **fund, the AP, the clearing members, the custodian, the ETF agent and the break are
  illustrative**. "Granite Ridge" is the suite's fictitious issuer (eval #4's GRIN, eval #7's GRSL).
  Any coincidence between the constructed FLEX series and a listed series is incidental. The 50,000-share
  unit and the $500 fee are representative, not typical (Innovator's 2025 N-CEN: mostly 25,000 shares and
  $300; First Trust $250; Calamos $300).

The **failure pattern is the documented one**: an error in the manual tracking and execution of an
options position transfer at OCC, in a process the clearing house itself calls "fragmented and
heavily dependent on manual intervention". The specific error planted - a quantity keyed in the
underlying-share equivalent instead of contracts - is the options analogue of the suite's
thousands-versus-millions scale trap and is constructed; no source attributes a real incident to it.
Flagged in the case headers and the README.

## The mechanics (checked against public primary documents on 2026-10-21; see `outputs/eval8-live/MECHANICS-NOTE.md`)

**The structure.** A defined-outcome ETF holds four FLEX option legs on its reference ETF for one
outcome period: a deep-in-the-money purchased call (the synthetic long, strike near 1% of the
reference price), a purchased put at the reference price (the top of the buffer), a written put at
the buffer's lower bound, and a written call at the cap. All four expire on the same day. Each
contract covers 100 shares of the reference ETF. The positions are held at OCC through the fund's
clearing member.

**The redemption basket.** The PCF published for a trade date gives the basket per creation unit:
for each leg the series (OSI identifier: root, expiry, call/put, strike), the side the fund holds
(long or short), the number of contracts per creation unit and the underlying-share equivalent
(contracts x 100); plus the cash component per creation unit = creation-unit value (NAV per share x
shares per unit) minus the value of the option legs delivered (sum over legs of contracts x 100 x
mark x sign, long positive, short negative). The PCF is distributed through NSCC by 10:00 PM ET on
T-1 for trade date T (DTCC ETF timeline); the final cash component is struck off the trade date's
NAV. The order is accepted or rejected against the fund's own cut-off.

**The ex-clearing redemption.** The AP delivers the creation units' shares through DTC to the Trust's
transfer agent (Innovator SAI); the fund's clearing member submits an OCC position adjustment, an
off-floor transfer of each leg between clearing member accounts (OCC By-Laws Art. VI s.1 Interp. .01(a)(7),
added by SR-OCC-2025-010; long legs move as long positions, short legs as short positions, so the
receiving account carries the writer's obligation); the cash component, less the transaction fee, is
wired to the AP. OCC's rules test only that the delivering account holds enough contracts (Art. VI s.15),
not the order it serves. None of it passes through NSCC; there is no CCP guaranty on the option legs (the
NSCC filing's own point) - a mis-transfer is recovered by agreement between the clearing members, not by
the clearing house. Constructed and labelled as such: a receiving-member acceptance step, the intraday
timings and the next-day effect, the per-transfer confirmation documents, the agent's status report, the
free-of-payment characterisation of the share leg and the AP clearing for itself.

**The tie-out.** Before the cash component is released, the shares cancelled and the order marked
settled, the custodian or ETF agent ties: (1) each OCC confirmation's series to the basket's series
(root, expiry, call/put, strike to the cent); (2) each confirmed quantity to the due quantity =
contracts per unit x units; (3) the side and the direction (from the fund's account to the AP's);
(4) the status (accepted and effective, not pending or rejected); (5) the fund's post-transfer
position per the custodian report to the pre-transfer position minus the due quantity; (6) the cash
component recomputed from the NAV and the marks against the agent's figure; (7) the shares received.
**Settle only if every leg ties.** A single leg that does not tie holds the order - the cash is not
paid and the shares are not cancelled until the position is corrected.

## The gold case and the planted break

**Granite Ridge U.S. Small Cap Buffer ETF - October (GRBO)**, outcome period October 1, 2025 to
September 30, 2026, reference price 240.00, four FLEX legs on IWM expiring 2026-09-30: long call
2.40, long put 240.00, short put 204.00 (a 15% buffer), short call 282.00 (a 17.5% cap). The fund
holds 24,000 contracts of each leg against 20,000,000 shares outstanding; the creation unit is
50,000 shares, so the basket carries **60 contracts per leg per unit** (6,000 underlying shares).

On **2026-06-23** the AP redeems **2 units (100,000 shares)**; final NAV **30.5000**; redemption
value 3,050,000.00; due per leg **120 contracts**. The marks (long call 254.90, long put 3.95, short
put 0.80, short call 4.65; IWM 258.00) give an option value of 25,340.00 per contract set, 1,520,400.00
per unit; cash component **4,600.00 per unit, 9,200.00 for the order**; redemption transaction fee
500.00; net cash to the AP **8,700.00**. The ETF agent's recap shows all four legs "TRANSFERRED", the
cash component 9,200.00, and status READY TO SETTLE.

The OCC confirmations say otherwise. Three legs confirm 120 contracts each. The **long put 240.00**
confirms **12,000 contracts** - the basket's underlying-share equivalent for the order (120 x 100)
keyed as the contract count; the fund held 24,000 so OCC processed it, and the receiving clearing
member accepted a free long position. The custodian's position report shows the fund's long put at
**12,000** against a due post-transfer position of 23,880. Excess delivered to the AP: **11,880
contracts, 4,692,600.00** at the 3.95 mark - 0.2358 per remaining share (0.77% of NAV) if it is not
recovered. The cash component is right; the delivery is not. Gold answer: **HOLD**, localized to the
long put leg; corrective OCC transfer of 11,880 contracts back to the fund's account before the cash
is released, the shares cancelled or the order marked settled; the recap corrected; escalated to the
fund's clearing member, the AP's clearing member and the ETF agent - with no CCP guaranty to fall
back on.

## Checkpoints (8)

| CP | Stage | Grades | Gate |
|---|---|---|---|
| **P1** | planning | pin {fund, ticker, order_id, AP}, the **trade and settlement dates** and the **PCF of record** (the trade date's basket, not the next day's), the **series** (the fund's own four legs, not the sibling vintage's), the order terms and the settlement flow | **GATE.DATE** (hard) on the dates / PCF; **GATE.SERIES** (hard) on the fund and series |
| **E1** | extraction | the basket as published (per-leg series, strike, expiry, side, contracts per unit, multiplier, exercise style; cash component per unit; fee) and the **agent's recap as claimed**; a citation | - |
| **E2** | extraction | the independent evidence: each **OCC transfer confirmation** (series, quantity, from, to, status, effective date), the **custodian position report** (before / after), the **NAV statement** (NAV, marks, price source), the DTC share receipt | - |
| **C1** | calculation | the per-leg tie ledger: due = contracts per unit x units; confirmed quantity, series, side, status; status map match / quantity_mismatch / series_mismatch / missing; isolate the exception | - |
| **C2** | calculation | the cash component recomputed: per-leg value per unit (contracts x **100** x mark x sign), option value per unit, cash per unit and for the order, the fee, net cash to the AP; the agent's figure ties or not; **multiplier lock** | **GATE.MULTIPLIER** (hard) |
| **C3** | calculation | the break quantified: excess (or short) contracts, their value at the mark, the fund's remaining position vs due, the per-remaining-share impact; **direction** (over-delivered to the AP / under-delivered) and who is harmed | **GATE.SIGN** (scoped) on an inverted direction or a flipped short-leg sign |
| **D1** | decision | the **settle/hold call**, localized to the leg with the due and confirmed quantities, the remedy (corrective transfer before release), emitted as a structured record | **GATE.SETTLE** (the signature) |
| **D2** | refusal | calibrated refusal: the **AP's profit or loss on the redemption is not computable** (its acquisition cost of the shares is not in the packet); the net cash due to the AP IS computable | **GATE.FABRICATION** on a made-up cost, closing price or P&L |

Checkpoint weights: P1 .10 / E1 .10 / E2 .10 / C1 .16 / C2 .14 / C3 .14 / D1 .16 / D2 .10. D2's
headline is the FailSafeQA F-beta LLMC_beta(R, G), beta = 0.5 (the eval-#1 E6 exception, inherited).
42 criteria, 6 gates (rubric 1.1.0: every gate on an evidence hook).

## Gate ledger

| Gate | Tier | Fires when | Blast radius |
|---|---|---|---|
| **GATE.DATE** | hard (evidence hook) | the wrong basket date is used - a trade, settlement or basket date pinned to a different day, a PCF id that resolves to the next-day basket, or the next-day basket actually read; never a missing pin or a date notation | C1, C2, C3, D1 |
| **GATE.SERIES** | hard (evidence hook) | the sibling vintage's basket (the issuer's November fund, same AP file drop, same root, different expiry and strikes) is tied instead of the fund's own four legs - its series, expiry, PCF id, ticker, fund, legs or due quantity resolve to the sibling; never a missing pin or an identifier notation | C1, C2, C3, D1 |
| **GATE.MULTIPLIER** | hard (evidence hook) | contracts confused with shares in the model's own arithmetic: two figures within 5% of the x100 (or /100) axis of gold, or one within 0.5%, the option value implied by the model's own cash component included - never on absence or a number notation | C3, D1 |
| **GATE.SIGN** | scoped | the direction is **inverted** (an over-delivery to the AP reported as a shortfall; the remaining shareholders' loss attributed to the AP) or the short legs are added rather than subtracted in the cash component; a missed break is not an inversion | D1 |
| **GATE.SETTLE** | scoped (**signature**) | the model **SETTLES** (releases the cash component, cancels the shares, marks the order complete - any approval synonym) a redemption whose legs do not all tie | D1 to 0, **settle_override_fired** flag |
| **GATE.FABRICATION** | hard (figure) | a fabricated confirmation, position or statement line; a made-up acquisition cost, closing price or P&L for the AP (an assumed "bought at NAV" counts) | per-figure void; AllPass = 0 |

## The taxonomy (oracle + designed flaws, each tripping its gate)

Scores from the suite run of 2026-10-21, after the gaming review (`python -m harness run --case grbo-redeem-2026 --all`;
the `false_hold` row is from the clean twin, where it is the wrong answer).

| Variant | Gated | Gate | What it shows |
|---|---:|---|---|
| `oracle` | 1.000 | none | perfect tie-out: catches the 12,000-contract transfer, recomputes the cash, HOLD, localized, remedy named |
| `fabricate_pnl` | 0.900 | GATE.FABRICATION | invented the AP's acquisition cost and a profit figure; D2 G = 0 (the decision itself is right) |
| `settle_override` | 0.840 | **GATE.SETTLE** + flag | *all math right, SETTLED anyway* - the highest-scoring decision failure and the most dangerous |
| `false_hold` (clean twin) | 0.840 | none (penalty) | HOLD on an order whose every leg ties - the over-caution mirror; D1 zeroed on its own, no gate |
| `sign_flip` | 0.754 | GATE.SIGN | reported the over-delivery as a shortfall owed to the AP - who is harmed flips, and so does the remedy |
| `recap_blind` | 0.603 | GATE.SETTLE + flag | adopted the agent's "4 of 4 TRANSFERRED", never read the confirmations against the basket, SETTLED - the control never engaged |
| `multiplier_slip` | 0.460 | GATE.MULTIPLIER | valued the legs per share instead of per contract - the cash component off by the 100 multiplier, and a twin answer consistent with its own error |
| `date_slip` | 0.323 | GATE.DATE | used the next-day PCF (published on the trade date) as the basket of record - the biggest cascade |
| `series_slip` | 0.252 | GATE.SERIES | tied the November fund's basket (the distractor PCF) to the October fund's confirmations |

Reproduce any row: `python -m harness run --case grbo-redeem-2026 --model <variant>`.

The pattern *is* the finding: the eval tells "looks right, is wrong" (`settle_override`, 0.840, the control switched
off with every number correct) apart from "never saw it" (`recap_blind`, 0.603) and from a foundational error
(`series_slip`, 0.252; `date_slip`, 0.323) - and localizes each to the checkpoint that owns it. Two variants fire
the signature gate at very different scores: the headline flag says *what* was done (a broken redemption
settled); the checkpoint vector says *why*.

## The over-cautious mirror (a second gold case)

A tie-out that holds a clean redemption past settlement is as useless as one that settles a broken
one: the AP's balance sheet carries the shares and the hedge for another day, and the fund's record
is wrong. So a second gold case - `cases/grbo-redeem-2026-clean.case.yaml` - is the same order with
all four OCC confirmations at 120 contracts and the custodian's position report at 23,880 per leg;
the gold answer is **SETTLE**: release 8,700.00, cancel 100,000 shares, mark the order settled. The
`false_hold` variant scores 0.840 with D1 at zero and no gate: the `D1.n_falsehold` penalty is sized to
zero the decision checkpoint on its own.

## Before and after the automation

The NSCC-to-OCC messaging approved on March 12, 2026 - NSCC's Options ETF Clearing Connect, which DTCC's ETF
Release page lists as in production on May 15, 2026 - moves the position transfers inside NSCC's process
but does not change the tie-out: the basket is still the PCF, the due quantity is still
contracts per unit times units, and the evidence becomes an NSCC/OCC message set instead of bilateral
confirmations. The case files carry `settlement_flow: ex_clearing` with a trade date after the go-live: the
fixture's AP and ETF agent have not onboarded to the new service and settle under their pre-existing
bilateral arrangement (adoption is participant-elected; NSCC "would not guarantee position transfers"
either way). The keyed quantity is a manual-flow risk: in the messaged flow "instructions would be created
by using the daily portfolio composition files". A planned case carries the messaged flow with the same
break expressed as a rejected instruction after the cut-off, so the eval survives the automation it
describes.

## Hardening (adversarial gaming review)

The settle/hold call is graded by a **clause-aware word-token classifier**: a negator or a condition binds only
inside its clause ("No exceptions. Settle." settles; "HOLD - do not release the cash, do not mark the order settled"
holds; "Settle: NO" holds; "Don't settle" with a curly apostrophe holds), a settle conditioned on the corrective action
("settle only after the 11,880 contracts are returned") is a hold while one conditioned on a time ("SETTLE after the
16:00 cut-off") is a settle, a settle word that is the object of a hold verb ("hold the wire") is a hold, a negated hold
word with nothing else ("no reason to hold") settles, and a contradiction ("SETTLE; reverse the excess separately")
earns nothing and fires no gate. The two switches `release_cash` / `cancel_shares` are read: true beside a HOLD is a
release instruction (the gate fires on the break case), false beside a SETTLE a contradiction. An action field is a
release instruction only when a sentence has a settle verb with no corrective word, no hold word, no negator or
condition before the verb and no conditioning word after it ("release 8,700.00 afterwards" and "release only once
confirmed" are sequenced; "release the cash now, then arrange the transfer" is not). The remedy is graded on its own
text: the return of the excess, its size, its direction back to the fund (not "a further 11,880 to the AP"), the release
sequenced after it, and the parties. Every gate fires on evidence: the date, series and multiplier gates are penalty
hooks (rubric 1.1.0) so a missing or oddly written pin costs its points and nothing more, while a parseable date that
is a different day, a PCF id that resolves to another basket, a basket read from a distractor file, or two figures on
the hundredfold axis fire. Ledger statuses separate the verdict from the kind of mismatch, with negation; rows key by
leg number, option series (root-insensitive) or a side-type-strike description; fabrication is tested against the
packet; numbers parse units, locales and accounting signs, and a hedge is no value; the refusal grader scans every
string for an assumed cost, a stated price or a profit, binds negation to the clause in both directions and treats share
counts and the packet's derived totals as known.

The six-attacker review ran on 2026-10-19 (one attacker per surface: the decision classifier, the refusal grader, the
numbers and the multiplier gate, extraction and the tie ledger, the planning pins and gates, and legitimate formats the
grader might fail; notes and scripts under `outputs/eval8-live/gaming-review/`), about 1,500 graded mutations. It found
hard gates firing on notation and absence while the PCF of record went unverified, the cross-clause negation of the
decision classifier, the wrong-way remedy, the unread switches, the status-family precedence, the whitelist row keys and
fabrication test, the dodgeable multiplier gate, and the refusal grader's share-count and negation errors. All were
fixed on 2026-10-21 before any model was run, so no published number moved; 258 of the attackers' checks are pinned as
standing regressions in `harness/gaming_review_eval8.py`, run by `python -m harness selftest`. The write-up, including
the decisions where the maintainer differs from an attacker's expectation, is in `outputs/eval8-live/TAXONOMY.md`.

## Planned cases (the rest of the failure taxonomy)

| Pattern | Grounded in | What it adds |
|---|---|---|
| a leg pending at OCC at the settlement cut-off, recap says complete | the NSCC filing's "tracking ... validation" | a missing (not mismatched) leg; the status field, not the quantity |
| the short call leg transferred in the wrong direction or not accepted by the receiving clearing member | the writer's-obligation acceptance step | the side of the leg; margin on the receiving side |
| a stale mark in the agent's cash component (prior-day marks) | eval #7's stale-price family; the filing's "pricing" step | the cash component itself breaks while every leg ties |
| the sibling vintage's series confirmed for one leg | eval #2's same-day sibling vintages | a series mismatch on one leg among four correct quantities |
| the NSCC-OCC messaged flow with a REJECTED instruction after the cut-off | SR-NSCC-2026-001; the DTCC ETF timeline ("REJECTED (REJ) and cannot be reinstated") | the after-automation case; the deadline field |
| a cash-only creation of the same fund (the filing's "cash-only" leg) | SR-NSCC-2026-001 | the creation side: the agent buys the legs through the prime broker; tie the purchased contracts to the units created |

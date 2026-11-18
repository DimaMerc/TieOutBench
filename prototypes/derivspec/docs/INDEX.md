# Documents collected, 2026-11-16

First fund: AdvisorShares MSOS Daily Leveraged ETF (MSOX). The passages were collected by an AI research assistant
working for the author, from the sponsor's copies of the documents; "I" in these notes is that assistant. Each file
names the address it read and how. Unlike the other two funds, the passages were not cut from the full text by a
program, and no fingerprint of the source files was kept.

Files 04 and 06 are paraphrase that was not verified. Nothing in the report or in the passages shown to the models
uses them, and they are not in the repository.

The gap table at the end is the collector's first pass, twelve mechanics. The report's answer key is the rule table
in `ds/rules.py`, 21 rules, which was written from these passages afterwards and corrected three times; where the two
differ, the rule table is the one the report uses.

| File | Document | Accession | Quote status |
|---|---|---|---|
| 01-msox-annual-report-2026-06-30.md | AdvisorShares Trust N-CSR, year ended 6/30/2026 (sponsor PDF copy) | 0001829126-26-009612 (from EDGAR URL) | verbatim from local text extraction |
| 02-msox-prospectus-2026-11-01.md | MSOX prospectus dated 11/1/2026 (sponsor PDF; EDGAR 497K 0001829126-26-011809 seen but only summarised) | not obtained for the PDF | verbatim |
| 03-advisorshares-sai-2026-11-01.md | Trust SAI, covers MSOX (sponsor PDF) | not obtained | verbatim |
| 04-msox-nport-2026-03-31.md | NPORT-P schedule, 3/31/2026 | 0000940400-26-020567 | paraphrase, not verified |
| 05-msox-nav-restatement-press-release-2026-03-06.md | Sponsor press release, NAV restatement | none (not a filing) | short fragments verbatim, rest paraphrase |
| 06-direxion-tsll-comparison.md | Direxion N-CSR / N-CSRS / N-PORT | 0001133228-26-000012; 0001133228-26-010092; 0001193125-26-137696 | not obtained (files over 10 MB); paraphrase only |

Not obtained: the EDGAR htm of the MSOX N-CSR and the N-CSRS notes (too large or truncated); EDGAR accession and filing dates for the prospectus and SAI; any 497 supplement or filing that mentions the restatement (none found); the N-PORT for 6/30/2026 (not found); the Direxion swap note and a TSLL swap entry. Fetch of EDGAR browse pages timed out. No page contained instructions addressed to an AI.

# Gap table

| # | Mechanic | Status | Evidence / what is missing |
|---|---|---|---|
| 1 | Day-count convention, financing leg | not in the documents | No document gives ACT/360 or any basis. |
| 2 | Financing rate, index, reset, spread | partly | Index and spreads given: "OBFR + 3.00%", "OBFR + 2.00%" (annual report schedule, N-PORT); payment frequency "Monthly"; SAI: "a floating rate of interest on the notional amount". "OBFR" is not defined in the annual report. How often the rate resets: missing. Which spread applies to which counterparty: missing. |
| 3 | When financing accrual starts and stops; weekends, holidays | not in the documents | Only generic: "interest income and expenses are recognized on the accrual basis" (annual report, Investment Transactions). |
| 4 | Income accrued by the swap and when | partly | SAI: counterparty pays "the dividends that would have been received on those stocks"; "gain or loss on the notional amount plus dividends on the stocks less the interest paid by the Fund". The reference is an ETF (MSOS) whose dividends are not described. Timing (ex-date, pay date, reset) missing. The press release says "income accruals for some of the total return swaps" were wrong, without defining them. |
| 5 | Reset and payment dates; fate of accrued amounts and unrealized gain | partly | Termination dates (7/11, 9/22, 11/20/2026) and "Monthly" payment frequency are given. "Periodic payments received or paid by a Fund are recorded as realized gains or losses." SAI: "settled on a net basis". Missing: reset dates, whether unrealized gain is realized at reset, what happens at termination or roll. Realized loss on swaps FY2026 $(13,966,814) is reported without explanation. |
| 6 | Notional change on daily rebalance | partly | "the Fund seeks to rebalance its portfolio daily"; "The Fund will reposition its portfolio at the end of every trading day." Nothing on how the swap notional is amended (resize, new trade, reset). |
| 7 | Effect of creation/redemption on swap; who bears cost | partly | Cash creations/redemptions; "$500" transaction fee "to compensate the Trust for transfer and other transaction costs"; "These costs can decrease the Fund's NAV if not offset by an authorized participant transaction fee." Nothing on the swap adjustment itself or its cost. |
| 8 | Price of the reference used to value swap | partly | "marked to market daily based on the value of the underlying security"; swaps "valued at the net unrealized gain (loss)", Level 2. Not stated: closing price, reference ETF NAV, last trade or counterparty mark. |
| 9 | Collateral and margin | partly | "cash in the amount of $55,830,545 has been segregated as collateral from the broker for swap contracts" (6/30/2026); prospectus: collateral "typically held in money market instruments". Not stated: who holds it, margin calls, effect of movements on NAV (offsetting table shows no collateral netted). |
| 10 | Management fee and expense accrual | specified | "calculated daily and paid monthly based on the Fund's average daily net assets" (annual report Note 3); "accrued daily and taken into account for purposes of determining NAV per share" (SAI). Rate 0.85%, limit 0.95%. |
| 11 | NAV per share formula and time | specified | SAI Determination of Net Asset Value and prospectus Calculating Net Asset Value: total assets less liabilities divided by shares outstanding, rounded to the nearest cent, struck at the NYSE close (normally 4:00 p.m. ET). |
| 12 | Materiality or correction policy for NAV errors | not in the documents | Only the press release says the administrator will "investigate, quantify, and correct the error". No threshold or policy in prospectus, SAI or reports. |

Count: specified 2 (rows 10, 11); partly 7 (rows 2, 4, 5, 6, 7, 8, 9); not in the documents 3 (rows 1, 3, 12).

# AdvisorShares Trust annual report, year ended June 30, 2026 (MSOX section)

- Fund: AdvisorShares MSOS Daily Leveraged ETF (MSOX), series of AdvisorShares Trust (CIK 1408970)
- Form type: N-CSR (annual report)
- EDGAR accession number: 0001829126-26-009612 (taken from the URL https://www.sec.gov/Archives/edgar/data/0001408970/000182912626009612/advisorshares_ncsr.htm; filing date not obtained)
- URL actually read: https://advisorshares.com/wp-content/uploads/2026/08/2026-Annual-Report-AdvisorShares-Trust.pdf (the sponsor's copy of the Trust annual report; the EDGAR htm was too large for the fetch tool, so I could not compare the two. Same title and period; treat as the same report, not verified identical)
- Date read: 2026-11-16
- Method: PDF saved locally by the fetch tool, text extracted locally (pypdf), passages copied from the extracted text. Quotes are verbatim from that extraction; line breaks removed.
- NAV restatement: the words "restate", "restated", "restatement" do not occur anywhere in this document.

## (a) Investment objective and daily reset
Section: Notes to Financial Statements, 1. Organization
> AdvisorShares MSOS Daily Leveraged ETF ("MSOS Daily Leveraged ETF") seeks daily investment results that, before fees and expenses, correspond to approximately two times (2x) the daily total return of the AdvisorShares Pure US Cannabis ETF.

No daily-reset description in this report.

## (b) Use of swaps and counterparties
Section: Schedule of Investments, MSOS Daily Leveraged ETF, June 30, 2026 (footnote under swap table)
> Clear Street, Marex Capital Markets and Nomura act as the counterparties to the total return swap contracts listed above. The Fund either receives fees from, or pays fees to, the counterparty, depending upon the total return of the benchmark, and the agreed-upon floating financing rate. As of June 30, 2026, cash in the amount of $55,830,545 has been segregated as collateral from the broker for swap contracts.

Swap table (column headers as given: Reference Entity | Annual Financing Rate Paid | Payment Frequency | Termination Date | Notional Amounts | Fair Value | Unrealized Appreciation/(Depreciation)):
- AdvisorShares Pure US Cannabis ETF | OBFR + 3.00% | Monthly | 7/11/2026 | $42,106,856 | $42,265,600 | $158,744
- AdvisorShares Pure US Cannabis ETF | OBFR + 2.00% | Monthly | 9/22/2026 | 75,348,940 | 76,543,667 | 1,194,728
- AdvisorShares Pure US Cannabis ETF | OBFR + 3.00% | Monthly | 11/20/2026 | 9,934,011 | 10,198,771 | 264,759
- Net Unrealized Appreciation $1,618,231

The report does not map counterparties to individual swaps. "OBFR" is not defined in this document. Net assets at 6/30/2026: $69,414,964 (from Financial Highlights, $69,415 thousand).

## (c) Valuation of swaps for NAV
Section: Notes, 2. Summary of Significant Accounting Policies, "Investment Valuation"
> In computing each Fund's NAV, the Fund's portfolio investments are generally valued based on their last readily available market price. [...] When market quotations are not readily available, a portfolio investment's fair value will be determined and such fair valuations will be used in calculating a Fund's NAV.

> The Board of Trustees of the Trust (the "Board") has adopted valuation policies and procedures pursuant to which it has designated AdvisorShares Investments, LLC (the "Advisor") to determine the fair value of each Fund's investments, subject to the Board's oversight, when market prices for those investments are not readily available, including when they are determined to be unreliable.

Section: Schedule of Investments, fair value table footnote
> Derivative instruments, including swap contracts, are valued at the net unrealized gain (loss) on the instrument.

The swaps are shown in the Level 2 column ("Swaps - 1,618,231 - 1,618,231" under Level 1 / Level 2 / Level 3 / Total).

## (d) Accounting policy for swaps
Section: Notes, 2. Summary of Significant Accounting Policies, "Swap Agreements"
> Certain Funds may invest in equity swaps to obtain exposure to the underlying referenced security, obtain leverage or enjoy the returns from ownership without actually owning equity. Equity swaps are two-party contracts that generally obligate one party to pay the positive return and the other party to pay the negative return on a specified reference security, basket of securities, security index or index component during the period of the swap. Equity swap contracts are marked to market daily based on the value of the underlying security and the change, if any, is recorded as an unrealized gain or loss.

> Equity swaps normally do not involve the delivery of securities or other underlying assets. Accordingly, the risk of loss with respect to equity swaps is normally limited to the net amount of payments that a Fund is contractually obligated to make. If the other party to an equity swap defaults, a Fund's risk of loss consists of the net amount of payments that the Fund is contractually entitled to receive, if any. [...] Periodic payments received or paid by a Fund are recorded as realized gains or losses.

Section: same note, "Investment Transactions"
> Investment transactions are accounted for on the trade date. Realized gains and losses on sales of investment securities are calculated using the identified cost method. Dividend income and distributions to shareholders are recognized on the ex-dividend date and interest income and expenses are recognized on the accrual basis.

Section: Notes, 2., offsetting table (columns: Gross Amounts of Recognized Assets and (Liabilities); Gross Amounts Offset in the Statements of Assets and (Liabilities); Net Amounts Presented; Gross Amounts not offset: Financial Instruments, Collateral Pledged/Received; Net Amount). MSOS Daily Leveraged ETF row: "Swaps ... 1,618,231 — 1,618,231 — — 1,618,231".

Section: Notes, 6. Derivative Instruments
> Unrealized Appreciation on OTC Swap Contracts $ 1,618,231 [asset, MSOS Daily Leveraged ETF]
> Realized Gain (Loss) ... Swaps $ (13,966,814); Change in Unrealized Gain (Loss) ... Swaps $ 1,682,794 [year ended June 30, 2026]
> Long Swaps Contracts $ 1,592,986 [average volume of derivatives opened, MSOS Daily Leveraged ETF]

Section: Notes, 2., "Short Sales" (policy for short sales, not for swaps; shown only because it is the only place the report speaks of daily financing charges):
> This income or fee is calculated daily based upon the market value of each borrowed security and a variable rate that is dependent on the availability of the security.

Not found in this report: any statement that swap financing is accrued daily, any day-count, what happens at a reset or termination, or how dividends on the reference ETF are accrued under the swap.

## (e) Costs
Section: Notes, 3. Investment Advisory Agreement and Other Agreements
> For its services, the Advisor is entitled to an annual management fee from each Fund, which is calculated daily and paid monthly based on the Fund's average daily net assets.

Fee table row: "MSOS Daily Leveraged ETF . . . 0.85%". Expense limit row: "MSOS Daily Leveraged ETF ... 0.95%" (limit excludes "interest expense, taxes, brokerage commissions, acquired fund fees and expenses ... and extraordinary expenses").

Section: Notes, 2., "Expenses"
> Expenses of the Trust, which are directly identifiable to a specific Fund, are applied to that Fund. Expenses which are not readily identifiable to a specific Fund are allocated in such a manner as deemed equitable, taking into consideration the nature and type of expense and the relative net assets of each Fund.

Section: Notes, 3., "Administrator, Custodian, Fund Accountant and Transfer Agent"
> The Bank of New York Mellon serves as the Funds' administrator, fund accountant, custodian, and transfer agent pursuant to a Fund Administration and Accounting Agreement, a Custody Agreement and a Transfer Agency and Service Agreement, as the case may be.

Financial Highlights, MSOX, year ended June 30, 2026: NAV beginning $2.80, ending $3.36; Net Investment Income per share 0.07; expense ratio after waivers 0.95%, before 1.17%; net investment income ratio 1.68%.

## (f) Creation and redemption
Section: Notes, 4. Creation and Redemption Transactions
> The Funds issue and redeem shares on a continuous basis at NAV in groups of shares called "Creation Units." [...] Only "Authorized Participants" may purchase or redeem shares directly from each Fund.

> To compensate a Fund for transfer and other transaction costs involved in creation transactions and redemption transactions through the clearing process, investors will be required to pay a minimum transaction fee, assessed per transaction, of $500.

No cut-off time and no settlement cycle in this report.

## (g) N-PORT
Not applicable to this document (see 04).

## (h) NAV error
Nothing. Note 11, Subsequent Events, mentions only the liquidation of the Hotel ETF and Vice ETF: "The Funds have evaluated subsequent events through the issuance of the financial statements and determined that no other events have occurred that require additional disclosure."

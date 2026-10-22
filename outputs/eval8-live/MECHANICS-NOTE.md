# Eval #8 mechanics check: what public primary documents say

Checked 2026-10-21 against the eight assertions in `cases/grbo-redeem-2026.case.yaml` and `workflow/options-redemption-analysis.md`. Quotes are verbatim, 40 words or fewer. PDFs were converted locally; EDGAR HTML was read through the WebFetch tool (short consecutive pieces), so re-check those quotes on EDGAR before publishing.

## 1. Summary

1. The skeleton holds: option-component redemptions run "ex-clearing" outside NSCC, option legs move by OCC position adjustment, and the ETF Agent term, PCF 10:00 PM ET on T-1 and supplemental noon on T are confirmed.
2. No public source supports the receiving-member acceptance step, the 17:10 / 18:05 / T+1 timings, a "settlement recap" document, OSI or underlying-share columns in a PCF, "free of payment" share delivery, or a self-clearing AP.
3. Dating problem: DTCC lists its NSCC-to-OCC link (Options ETF Clearing Connect) as in production on May 15, 2026, before the fixture's 2026-06-23 ex-clearing trade date.
4. SEC N-CEN data: Innovator and Calamos option ETFs redeem largely in kind, First Trust's FT Vest buffer ETFs mostly in cash; standard fees are $250-$300 and units usually 25,000 shares (fixture: $500, 50,000).
5. OCC's By-Laws test only position sufficiency, so 12,000 contracts out of a 24,000 position passes; SR-OCC-2025-010 itself describes no mechanics.

## 2. The eight assertions

### 1. Ex-clearing flow
**Fixture claim:** the AP delivers shares free of payment into the custodian's DTC account; the fund's clearing member moves each leg by OCC position transfer; cash less the fee is wired; nothing passes through CNS.
**VERDICT: PARTLY CONFIRMED.**
- NSCC: "ETF market participants typically handle the redemption of such ETFs on an "ex-clearing" basis (e.g., outside of traditional clearing mechanisms and NSCC)." The manual steps include "ultimate execution of options positions transfers at OCC by the APs, ETF Agents and primer brokers" [sic].
- Innovator SAI: redemption shares are delivered "through DTC to the transfer agent." Vanguard AP agreement: "Purchase Orders and Redemption Orders will settle through the DTC and the Federal Reserve's Fedwire System."
- Not found: any "free of payment" wording; delivery into the custodian's account (the SAI says transfer agent).

**Citations:** SR-NSCC-2026-001, 91 FR 3938 (29 Jan 2026), Background (URL in section 4); Innovator ETFs Trust 485BPOS 0001213900-24-079100, SAI "Placement of Creation or Redemption Orders"; Form of Authorized Participant Agreement for Vanguard ETF Shares (URL in section 4).
Recommended change to the fixture: say shares go "through DTC to the transfer agent/custodian" and cash by wire; drop "free of payment" or mark it an assumption.

### 2. OCC position transfers
**Fixture claim:** submitted by the delivering clearing member, accepted by the receiving one (short legs: receiver takes the writer's obligation), submitted T 17:10, accepted 18:05, effective T+1.
**VERDICT: PARTLY CONFIRMED (permission and name); the acceptance step and the timings are NOT FOUND.**
- OCC By-Laws Art. VI s.1, Interp. .01(a): clearing members may submit "adjustments" to positions for listed purposes, including "(7) for any other purpose permissible under Exchange rules. Such data shall be submitted in such form and within such times as the Corporation shall prescribe." Item (7) dates from 18 Aug 2025 (SR-OCC-2025-010).
- Name (SR-OCC-2025-010, fn 6): "Adjustments may include, among other things, off-floor transfers of options." CMTA is a separate process; Cboe's Rule 6.7 form (not 6.9) says "Clearing TPHs are to directly report the transfer to OCC using the OCC position adjustment/transfer procedures (and the OCC CMTA Transfer procedure should not be used)."
- The 2025 filing adds no mechanics: "The proposed rule change would not make any substantive changes to OCC policies or practices." It points to a 2020 Information Memorandum (46854), unreachable.
- Acceptance: "the confirmation of the receiving Clearing Member that it will accept such transfer" appears only for segregated futures customer accounts (Interp. .03(a)). For error-correcting transfers: "There is no approval process associated with position transfers between clearing members to correct clearing errors."
- Timing: not fixed in By-Laws or Rules. Rule 401(g) ties OCC's acceptance to when "the related position information has been recorded in OCC's clearing system"; Rule 501 Interp. .01 adds only that OCC publishes updated position information "during a business day".

**Citations:** OCC By-Laws and Rules (both "Last Modified: August 19, 2025", archive.org copies, URLs in section 4); SEC Rel. 34-103521 (22 Jul 2025), fn 6, fn 14, Item II.A; SEC Rel. 34-49841 (9 Jun 2004), 69 FR 34207, fn 8; Cboe Rule 6.7 Off-Floor Position Transfer Form.
Recommended change to the fixture: call it an OCC position adjustment (off-floor in-kind transfer) and mark receiving-member acceptance, 17:10 / 18:05 and the T+1 effective date as illustrative ("accepted" is OCC's word for its own recording; use "recorded").

### 3. The planted break
**Fixture claim:** 12,000 contracts transferred where 120 were due; OCC processed it because the fund held 24,000; the receiving member accepted free long puts.
**VERDICT: PARTLY CONFIRMED (no public rule stops it; none requires it).**
- Adjustments "shall be treated as confirmed trades for the purposes of Sections 15 and 16 of Article VI". Section 15: "A Clearing Member shall not effect a closing sale transaction in an account unless, at the time of such transaction, such Clearing Member has a long position in such account for at least the number of cleared contracts involved". The excess "shall be deemed to be an opening sale transaction". So 12,000 of 24,000 passes; a larger quantity would not be refused but would create a short.
- Rejection: OCC may reject where it "determines that the input regarding the adjustment or other transaction contains an error or omission" (Interp. .01(c), sole discretion).
- The purpose limit sits in exchange rules: Cboe Rule 6.9 transfers are tied to creation or redemption, "which transfer would occur at the price used to calculate the NAV of such ETF shares". OCC receives no order or PCF to test against. No size limit found.

**Citations:** OCC By-Laws Art. VI s.1 (Interp. .01(a), .01(c)) and s.15; SEC Rel. 34-87340 (17 Oct 2019), 84 FR 56877 (URL in section 4).
Recommended change to the fixture: none.

### 4. The ETF agent's settlement recap
**Fixture claim:** a recap from the ETF agent lists legs "TRANSFERRED" and "READY TO SETTLE", built from the instruction log.
**VERDICT: NOT FOUND.**
- No document opened (DTCC pages, SAIs, AP and custody agreements) describes a settlement recap or those statuses. The documented NSCC artifacts are the "Enhanced Create/Redeem Instruction Print Image Report" (ETF Agents and Authorized Participants) and the instruction detail file: "The report serves as the contract for the create/redeem activity." They exist for NSCC-processed orders only.
- Custody agreement: "The Transfer Agent shall advise the Custodian each day as to the repurchase of Shares in Creation Units."

**Citations:** DTCC Learning Center, "ETF Timeline and Submission Processing" (28 May 2024), Trade Date section; Dimensional ETF Trust Global Custodial and Agency Services Agreement (Citibank form, 2020), s.7(B) (URLs in section 4).
Recommended change to the fixture: label the recap a constructed artifact ("ETF agent redemption status report, illustrative"), not an NSCC or DTCC report.

### 5. Who holds the positions
**Fixture claim:** the fund's FLEX positions sit at OCC through a clearing member (prime broker); the AP is self-clearing.
**VERDICT: PARTLY CONFIRMED (fund side); AP self-clearing NOT FOUND.**
- Innovator: "the Fund will hold cleared derivatives through accounts at clearing members." First Trust: "the Fund will hold its FLEX Options through accounts at clearing members."
- NSCC: the ETF Agent buys the options "through a prime broker, which are cleared by OCC"; transfers are executed "at OCC by the APs, ETF Agents and primer brokers".
- No source says which of custodian, prime broker or clearing member submits a redemption transfer, or that an AP clears for itself.

**Citations:** Innovator 485BPOS, "Clearing Member Default Risk"; First Trust Exchange-Traded Fund VIII 485BPOS 0001445546-26-007606, "Counterparty Risk"; SR-NSCC-2026-001.
Recommended change to the fixture: describe the fund's member as prime broker / clearing member; mark the AP's self-clearing status as an assumption.

### 6. Cash component, fee, cut-off, cycle
**Fixture claim:** cash component = NAV x shares per unit minus option legs at the day's marks, struck at trade-date NAV, estimated on the T-1 PCF; flat $500 fee deducted; cut-off 16:00; T+1.
**VERDICT: PARTLY CONFIRMED.**
- Innovator SAI: proceeds are the Deposit Instruments "plus or minus cash in an amount equal to the difference between the net asset value of the Fund's shares (per Creation Unit) being redeemed" ... "and the aggregate market value of the Deposit Instruments (the "Cash Redemption Amount"), less the applicable Redemption Transaction Fee". NAV is "as next determined after a receipt of a request in proper form". DTCC: "The PCF file also contains the estimated cash amount in each portfolio."
- Cut-off: "no later than the closing time of the regular trading session of the NYSE (ordinarily 4:00 p.m. Eastern Time)"; the fund may require earlier. Cycle: Innovator, the Cash Redemption Amount "will ordinarily be transferred no later than T+2"; First Trust, deliveries "generally expected to be made within one Business Day." NSCC: "T+1 would be Regular Way settlement."
- In kind or cash: both prospectuses allow cash. N-CEN (SEC data): Innovator Trust, year to 31 Oct 2025: mostly 25,000-share units, fee $300; "Growth-100 Power Buffer ETF - March" redeemed 0% cash / 100% in kind; sampled series 0%-70% cash. First Trust VIII, year to 31 May 2026: 28 of 38 series redeem 100% in cash, $250 in 27; one buffer series 99% in kind. Calamos ETF Trust, year to 31 Jul 2025, Structured Alt Protection series: purchases 100% cash, redemptions 97%-100% in kind, $300.
- Fees: neither SAI gives a dollar amount; First Trust: "These fees may vary based upon various facts-based circumstances".

**Citations:** Innovator and First Trust 485BPOS (above), SAI "Delivery of Redemption Proceeds" and "Placement of Creation or Redemption Orders"; SEC Rel. 34-100048 (2 May 2024); N-CEN accessions 0000894189-26-000385, 0000940400-26-028992, 0001410368-25-014335; DTCC timeline page.
Recommended change to the fixture: set the fee at $300 and units at 25,000 (or call $500 / 50,000 representative); T+1 is inside Innovator's T+2 outer limit.

### 7. PCF layout
**Fixture claim:** the PCF lists each option leg with OSI identifier, contracts per unit and underlying-share equivalent; basket type "Redeem Only".
**VERDICT: NOT FOUND for the leg layout; the basket-type name is PARTLY CONFIRMED.**
- DTCC's 2020 announcement, as reprinted: "Basket types include Standard, Restricted, Pricing, Rebalance, Create Only, Redeem Only, and Negotiated." I found no public definition of "Redeem Only".
- NSCC 2026: "Index Receipt Agents include in portfolio composition files information concerning any component securities that are Index Receipt Option Components to be transferred through an Options Clearing Organization (e.g., the shares and their associated quantities)". Nothing on OSI identifiers or share equivalents; DTCC layouts (DATATRAK 11301) are behind login.

**Citations:** Markets Media, "DTCC Enhances ETF Clearing" (16 Sep 2020, "Source: DTCC"; DTCC's own page now 404); SR-NSCC-2026-001.
Recommended change to the fixture: keep "Redeem Only" (a real code); label the OSI and underlying-share columns as constructed.

### 8. Terms and timing
**Fixture claim:** "ETF Agent" is NSCC's term; PCF by 10:00 PM ET T-1; supplemental to 12:00 PM T; 16:00 cut-off; transfer agent cancels shares after the custodian confirms settlement.
**VERDICT: CONFIRMED.**
- "custodian banks ("ETF Agents," also referred to as "Index Receipt Agents" in the NSCC Rules)". DTCC: "ETF Agents, also known as Index Receipt Agent".
- "Cutoff times for ETF Agent to submit the PCF is 10:00 PM ET." Supplemental: "12:00 PM Final cutoff time for the supplemental submissions."
- Cut-off 4:00 p.m.: see 6. Cancellation (custody agreement): "The Custodian will transfer the applicable Portfolio Components to the Authorized Participant and instruct the Transfer Agent as to the cancellation of the corresponding Shares".

**Citations:** SR-NSCC-2026-001, Background; DTCC "ETF Timeline and Submission Processing", PCF Submission; Dimensional custody agreement s.7(B).
Recommended change to the fixture: none.

## 3. Additional findings

1. **Go-live date.** DTCC, ETF Release page (21 Sep 2026): "Production in May 15, 2026"; "NSCC seamlessly routes these to OCC for clearance and settlement through the dedicated link." The 2026-06-23 trade date is after it. State in the order packet why this pair is still ex-clearing, or move the date before 15 May.
2. **The report and research note overstate SR-OCC-2025-010.** Report section 7 says it and the NSCC filing "define both the manual and the messaged flow"; it only codifies permission. The research note says NSCC cites it "as having removed" the uncertainty; NSCC's footnote says the rule change "was intended, in part, to remove any uncertainty".
3. **Automation removes the keyed quantity.** NSCC: "These instructions would be created by using the daily portfolio composition files provided to NSCC by the ETF Agents", and "NSCC would not guarantee position transfers". The planted share-equivalent keying error is a manual-flow risk.
4. **"OCC confirmations" are not a documented artifact.** OCC publishes position information (Rule 501); label them constructed.
5. **Corrective transfer is supported.** Item (7) admits any purpose "permissible under Exchange rules"; Cboe's form: "no notice is required to effect off-floor transfers to correct bona fide errors as described in Rule 6.7(a)(1)".
6. **FLEX terms and version.** Innovator: "all European style", settlement "may be either physically settled ... or cash settled"; Cboe lists "American or European", so physical-only is one permitted case. The OCC text read is the August 2025 archive copy; a search snippet shows live Rules dated 1 Oct 2026.

## 4. Documents opened

- NSCC notice, 91 FR 3938: https://www.govinfo.gov/content/pkg/FR-2026-01-29/pdf/2026-01739.pdf. SEC approval order 34-104981: https://public-inspection.federalregister.gov/2026-05128.pdf. Both full text.
- SEC 34-103521 and Ex. 5 (SR-OCC-2025-010): https://www.sec.gov/files/rules/sro/occ/2025/34-103521_0.pdf and .../34-103521-ex5.pdf.
- OCC By-Laws: http://web.archive.org/web/20250829063359/https://www.theocc.com/getmedia/3309eceb-56cf-48fc-b3b3-498669a24572/occ_bylaws.pdf. OCC Rules: http://web.archive.org/web/20250819181033/https://www.theocc.com/getmedia/9d3854cd-b782-450f-bcf7-33169b0576ce/occ_rules.pdf.
- SEC 34-49841 (2004 CMTA order): https://www.govinfo.gov/content/pkg/FR-2004-06-18/pdf/04-13744.pdf. Cboe Rule 6.9 order 34-87340: https://www.govinfo.gov/content/pkg/FR-2019-10-23/pdf/2019-23059.pdf and notice: https://www.govinfo.gov/content/pkg/FR-2019-09-25/pdf/2019-20708.pdf.
- Cboe Rule 6.7 form: https://cdn.cboe.com/resources/regulation/rule-6-7-off-floor-position-transfer-form.pdf. Cboe Equity FLEX specifications: https://www.cboe.com/tradable_products/equity_indices/flex_options/specifications. Also opened (no OCC mechanics): Nasdaq ORA 2020-14, NYSE Arca 34-90552, Box 34-103147, PHLX 2020-26896.
- SEC 34-89088 (https://www.sec.gov/files/rules/sro/nscc/2020/34-89088.pdf, PCF contents) and 34-100048 (https://www.sec.gov/files/rules/sro/nscc/2024/34-100048.pdf, T+1 for index receipts).
- DTCC Learning Center ETF Processing, Timeline, Basics, Release, Users and Technical Resources pages: https://dtcclearning.com/products-and-services/equities-clearing/etf-processing/. Markets Media (https://marketsmedia.com/dtcc-enhances-etf-clearing) and Finadium reprints of DTCC's 15 Sep 2020 release.
- EDGAR via WebFetch: Innovator 485BPOS https://www.sec.gov/Archives/edgar/data/1415726/000121390024079100/ea0214437-01_485bpos.htm; First Trust VIII 485BPOS https://www.sec.gov/Archives/edgar/data/1667919/000144554626007606/ft-20261013.htm; Innovator AP agreement .../1415726/000143774917018552/ex_99519.htm (CNS versus outside-CNS routing, no settlement mechanics); Vanguard AP agreement https://www.sec.gov/Archives/edgar/data/889519/000168386323005607/f25924d3.htm; Dimensional custody agreement https://www.sec.gov/Archives/edgar/data/1816125/000179420220000453/ex99gi.htm; Innovator N-CEN https://www.sec.gov/Archives/edgar/data/1415726/000089418926000385/primary_doc.xml and SEC N-CEN data sets 2026q3, 2026q2, 2025q4 under https://www.sec.gov/files/dera/data/form-n-cen-data-sets/ (creation-unit size, cash versus in-kind percentages, fees).

**Not reachable:** OCC Information Memo 46854 (Cloudflare 403, no archive copy); live theocc.com By-Laws and Rules (403); DTCC's 2020 release and Notices A8657, A8989 (404); DTCC "Client Business Requirements" for Options ETF Clearing Connect and multiple basket types (login); Cboe rulebook PDF and any Rule 6.9 circular (403 / not found); N-CEN 2026q1 data set (over the tool's size limit).

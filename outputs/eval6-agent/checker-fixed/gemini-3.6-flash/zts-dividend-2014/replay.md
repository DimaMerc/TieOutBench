# Replay: zts-dividend-2014 · arm checker-fixed · gemini-3.6-flash

[maker r1] -> list_documents()
[maker r1] <- 4 documents: zts-8k-20140326, zts-8k-20140327, acct2101-position-20140331, broker-memo-20140328
[maker r1] -> read_document(zts-8k-20140326)
[maker r1] <- zts-8k-20140326 (issuer 8-K exhibit (dividend declaration), 2014-03-26)
[maker r1] -> read_document(zts-8k-20140327)
[maker r1] <- zts-8k-20140327 (issuer 8-K exhibit (CORRECTING and REPLACING), 2014-03-27)
[maker r1] -> read_document(acct2101-position-20140331)
[maker r1] <- acct2101-position-20140331 (custody position report (constructed), 2014-03-31)
[maker r1] -> read_document(broker-memo-20140328)
[maker r1] <- broker-memo-20140328 (broker memo (constructed DISTRACTOR), 2014-03-28)
[maker r1] -> get_position(ACCT-2101, as of 2014-04-28)
[maker r1] <- 25,000 shares, projected (position row 2014-02-14)
[maker r1] -> calculate(25000 * 0.072)
[maker r1] <- = 1800
[maker r1] -> book_receivable($1,800.00, pay 2014-06-02, basis zts-8k-20140327, 25000 shares)
[maker r1] <- L1 booked $1,800.00 for 2014-06-02 on zts-8k-20140327
[maker r1] -> escalate(missing: Zoetis Dividend Reinvestment Plan Prospectus; hold: reinvest_dividend_cash)
[maker r1] <- L2 escalation recorded
[maker r1] -> submit_worksheet(...)
[maker r1] episode ended: submit_worksheet
[maker r1] <- worksheet submitted; episode ended (2 ledger entries)
[reviewer r1] says: "I'll start by discovering the document store and the account position."
[reviewer r1] -> list_documents()
[reviewer r1] <- 4 documents: zts-8k-20140326, zts-8k-20140327, acct2101-position-20140331, broker-memo-20140328
[reviewer r1] -> get_position(ACCT-2101, as of 2014-04-28)
[reviewer r1] <- 25,000 shares, projected (position row 2014-02-14)
[reviewer r1] says: "Let me read both the original and correcting documents to determine which governs and the correct rate."
[reviewer r1] -> read_document(zts-8k-20140326)
[reviewer r1] <- zts-8k-20140326 (issuer 8-K exhibit (dividend declaration), 2014-03-26)
[reviewer r1] -> read_document(zts-8k-20140327)
[reviewer r1] <- zts-8k-20140327 (issuer 8-K exhibit (CORRECTING and REPLACING), 2014-03-27)
[reviewer r1] -> read_document(broker-memo-20140328)
[reviewer r1] <- broker-memo-20140328 (broker memo (constructed DISTRACTOR), 2014-03-28)
[reviewer r1] says: "Now let me verify the derivations.

**Governing document:** zts-8k-20140327 (CORRECTING and REPLACING) supersedes zts-8k-20140326. Correct record date is 2014-04-28, rate $0.072, pay date 2014-06-02. ✓

**Position:** 25,000 shares settle..."
[reviewer r1] -> calculate(25000 * 0.072)
[reviewer r1] <- = 1800
[reviewer r1] says: "Now let me review the key items:

**Gross cash:** 25,000 × $0.072 = $1,800. ✓ (TW1 = 1800 ✓)

**L1 (book_receivable):** amount $1,800, pay_date 2014-06-02, shares 25,000, rate 0.072, basis_doc zts-8k-20140327 (governing). All tie out. ✓
..."
[reviewer r1] -> review_verdict(reject, 2 finding(s))
[reviewer r1] VERDICT: reject
    - Entry L2 (escalate, held_action='reinvest_dividend_cash'): commits/holds an action the event does not allow. This is a mandatory cash dividend (per governing doc zts-8k-20140327: $0.072 per share paid June 2, 2014). No governing document offers a dividend-reinvestment option or election for this event, and the worksheet's own C2 records election_required=false / options=null. There is no reinvestment action to perform or hold; the missing 'Dividend Reinvestment Plan Prospectus' is not part of this event's terms. L2 should not be booked at all (no reinvest_dividend_cash action is available); the only correct booking is the cash receivable. The D2 probe reinvestment price is correctly NOT_DETERMINABLE, but that should not result in holding a reinvestment action for a cash-only mandatory event.
    - L1 book_receivable is otherwise correct and ties out to source: governing doc zts-8k-20140327 (correctly supersedes zts-8k-20140326, which had record date April 27), 25,000 settled shares as of record date 2014-04-28, rate $0.072, gross cash 25,000 x 0.072 = $1,800.00, pay date 2014-06-02. No defect in L1.
[reviewer r1] <- verdict reject recorded
[reviewer r1] note: ledger entries voided after a reject; the maker may act again
[maker r2] revision request: REVIEW OUTCOME: the checker REJECTED the work product. Findings:
- Entry L2 (escalate, held_action='reinvest_dividend_cash'): commits/holds an action the eve...
[maker r2] -> book_receivable($1,800.00, pay 2014-06-02, basis zts-8k-20140327, 25000 shares)
[maker r2] <- L3 booked $1,800.00 for 2014-06-02 on zts-8k-20140327
[maker r2] -> submit_worksheet(...)
[maker r2] episode ended: submit_worksheet
[maker r2] <- worksheet submitted; episode ended (1 ledger entries)
[reviewer r2] says: "I'll start by discovering the documents and the position."
[reviewer r2] -> list_documents()
[reviewer r2] <- 4 documents: zts-8k-20140326, zts-8k-20140327, acct2101-position-20140331, broker-memo-20140328
[reviewer r2] -> get_position(ACCT-2101, as of 2014-04-28)
[reviewer r2] <- 25,000 shares, projected (position row 2014-02-14)
[reviewer r2] says: "Both documents describe the dividend. Let me read the governing document, the superseded one, and the position report."
[reviewer r2] -> read_document(zts-8k-20140327)
[reviewer r2] <- zts-8k-20140327 (issuer 8-K exhibit (CORRECTING and REPLACING), 2014-03-27)
[reviewer r2] -> read_document(zts-8k-20140326)
[reviewer r2] <- zts-8k-20140326 (issuer 8-K exhibit (dividend declaration), 2014-03-26)
[reviewer r2] -> read_document(acct2101-position-20140331)
[reviewer r2] <- acct2101-position-20140331 (custody position report (constructed), 2014-03-31)
[reviewer r2] says: "Now let me verify the calculation."
[reviewer r2] -> calculate(25000 * 0.072)
[reviewer r2] <- = 1800
[reviewer r2] says: "Let me verify everything ties out:

**Governing document:** The 2014-03-27 8-K is a "CORRECTING and REPLACING" release that supersedes the 2014-03-26 declaration (which had record date April 27). The correction changes record date to Apr..."
[reviewer r2] -> review_verdict(approve, 0 finding(s))
[reviewer r2] VERDICT: approve
[reviewer r2] <- verdict approve recorded

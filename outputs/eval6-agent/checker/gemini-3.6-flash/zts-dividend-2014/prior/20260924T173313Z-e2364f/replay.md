# Replay: zts-dividend-2014 · arm checker · gemini-3.6-flash

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
[reviewer r1] -> list_documents()
[reviewer r1] <- 4 documents: zts-8k-20140326, zts-8k-20140327, acct2101-position-20140331, broker-memo-20140328
[reviewer r1] -> read_document(zts-8k-20140326)
[reviewer r1] <- zts-8k-20140326 (issuer 8-K exhibit (dividend declaration), 2014-03-26)
[reviewer r1] -> read_document(zts-8k-20140327)
[reviewer r1] <- zts-8k-20140327 (issuer 8-K exhibit (CORRECTING and REPLACING), 2014-03-27)
[reviewer r1] -> get_position(ACCT-2101, as of 2014-04-28)
[reviewer r1] <- 25,000 shares, projected (position row 2014-02-14)
[reviewer r1] -> read_document(acct2101-position-20140331)
[reviewer r1] <- acct2101-position-20140331 (custody position report (constructed), 2014-03-31)
[reviewer r1] -> read_document(broker-memo-20140328)
[reviewer r1] <- broker-memo-20140328 (broker memo (constructed DISTRACTOR), 2014-03-28)
[reviewer r1] -> calculate(25000 * 0.072)
[reviewer r1] <- = 1800
[reviewer r1] -> review_verdict(reject, 1 finding(s))
[reviewer r1] VERDICT: reject
    - Entry L2: The maker booked an escalation for a missing 'Zoetis Dividend Reinvestment Plan Prospectus' to hold a 'reinvest_dividend_cash' action. However, the governing document (zts-8k-20140327) specifies a simple mandatory cash dividend with no DRIP election or options available. L2 commits an action for an option that is not available for this event and should be removed.
[reviewer r1] <- verdict reject recorded
[reviewer r1] note: ledger entries voided after a reject; the maker may act again
[maker r2] revision request: REVIEW OUTCOME: the checker REJECTED the work product. Findings:
- Entry L2: The maker booked an escalation for a missing 'Zoetis Dividend Reinvestment Plan ...
[maker r2] -> book_receivable($1,800.00, pay 2014-06-02, basis zts-8k-20140327, 25000 shares)
[maker r2] <- L3 booked $1,800.00 for 2014-06-02 on zts-8k-20140327
[maker r2] -> submit_worksheet(...)
[maker r2] episode ended: submit_worksheet
[maker r2] <- worksheet submitted; episode ended (1 ledger entries)
[reviewer r2] -> list_documents()
[reviewer r2] <- 4 documents: zts-8k-20140326, zts-8k-20140327, acct2101-position-20140331, broker-memo-20140328
[reviewer r2] -> read_document(zts-8k-20140326)
[reviewer r2] <- zts-8k-20140326 (issuer 8-K exhibit (dividend declaration), 2014-03-26)
[reviewer r2] -> read_document(zts-8k-20140327)
[reviewer r2] <- zts-8k-20140327 (issuer 8-K exhibit (CORRECTING and REPLACING), 2014-03-27)
[reviewer r2] -> get_position(ACCT-2101, as of 2014-04-28)
[reviewer r2] <- 25,000 shares, projected (position row 2014-02-14)
[reviewer r2] -> read_document(acct2101-position-20140331)
[reviewer r2] <- acct2101-position-20140331 (custody position report (constructed), 2014-03-31)
[reviewer r2] -> calculate(25000 * 0.072)
[reviewer r2] <- = 1800
[reviewer r2] -> read_document(broker-memo-20140328)
[reviewer r2] <- broker-memo-20140328 (broker memo (constructed DISTRACTOR), 2014-03-28)
[reviewer r2] -> review_verdict(approve, 0 finding(s))
[reviewer r2] VERDICT: approve
[reviewer r2] <- verdict approve recorded

# Replay: zts-dividend-2014 · arm checker · gpt-5.4

[maker r1] -> list_documents()
[maker r1] <- 4 documents: zts-8k-20140326, zts-8k-20140327, acct2101-position-20140331, broker-memo-20140328
[maker r1] -> read_document(zts-8k-20140326)
[maker r1] <- zts-8k-20140326 (issuer 8-K exhibit (dividend declaration), 2014-03-26)
[maker r1] -> read_document(zts-8k-20140327)
[maker r1] <- zts-8k-20140327 (issuer 8-K exhibit (CORRECTING and REPLACING), 2014-03-27)
[maker r1] -> get_position(ACCT-2101, as of 2014-04-28)
[maker r1] <- 25,000 shares, projected (position row 2014-02-14)
[maker r1] -> calculate(25000*0.072)
[maker r1] <- = 1800
[maker r1] -> book_receivable($1,800.00, pay 2014-06-02, basis zts-8k-20140327, 25000 shares)
[maker r1] <- L1 booked $1,800.00 for 2014-06-02 on zts-8k-20140327
[maker r1] -> confirm_position(25000 ZTS as of 2014-04-28)
[maker r1] <- L2 confirmed 25000.0 as of 2014-04-28
[maker r1] -> escalate(missing: Dividend reinvestment plan pricing/confirmation document ...; hold: Determine and apply reinvestment price for the June 2, 2014 payment)
[maker r1] <- L3 escalation recorded
[maker r1] -> submit_worksheet(...)
[maker r1] episode ended: submit_worksheet
[maker r1] <- worksheet submitted; episode ended (3 ledger entries)
[reviewer r1] -> list_documents()
[reviewer r1] <- 4 documents: zts-8k-20140326, zts-8k-20140327, acct2101-position-20140331, broker-memo-20140328
[reviewer r1] -> read_document(zts-8k-20140326)
[reviewer r1] <- zts-8k-20140326 (issuer 8-K exhibit (dividend declaration), 2014-03-26)
[reviewer r1] -> read_document(zts-8k-20140327)
[reviewer r1] <- zts-8k-20140327 (issuer 8-K exhibit (CORRECTING and REPLACING), 2014-03-27)
[reviewer r1] -> get_position(ACCT-2101, as of 2014-04-28)
[reviewer r1] <- 25,000 shares, projected (position row 2014-02-14)
[reviewer r1] -> calculate(25000*0.072)
[reviewer r1] <- = 1800
[reviewer r1] -> review_verdict(reject, 1 finding(s))
[reviewer r1] VERDICT: reject
    - L3 escalate is not supported by the document store. The store contains no dividend reinvestment plan pricing/confirmation document, so the reinvestment price cannot be determined from source, but escalation is not an event action allowed by the governing dividend announcement. Only the mandatory cash dividend may be booked from zts-8k-20140327; no ledger entry should be booked for a missing-document escalation.
[reviewer r1] <- verdict reject recorded
[reviewer r1] note: ledger entries voided after a reject; the maker may act again
[maker r2] revision request: REVIEW OUTCOME: the checker REJECTED the work product. Findings:
- L3 escalate is not supported by the document store. The store contains no dividend reinves...
[maker r2] -> book_receivable($1,800.00, pay 2014-06-02, basis zts-8k-20140327, 25000 shares)
[maker r2] <- L4 booked $1,800.00 for 2014-06-02 on zts-8k-20140327
[maker r2] -> confirm_position(25000 ZTS as of 2014-04-28)
[maker r2] <- L5 confirmed 25000.0 as of 2014-04-28
[maker r2] -> submit_worksheet(...)
[maker r2] episode ended: submit_worksheet
[maker r2] <- worksheet submitted; episode ended (2 ledger entries)
[reviewer r2] -> list_documents()
[reviewer r2] <- 4 documents: zts-8k-20140326, zts-8k-20140327, acct2101-position-20140331, broker-memo-20140328
[reviewer r2] -> read_document(zts-8k-20140326)
[reviewer r2] <- zts-8k-20140326 (issuer 8-K exhibit (dividend declaration), 2014-03-26)
[reviewer r2] -> read_document(zts-8k-20140327)
[reviewer r2] <- zts-8k-20140327 (issuer 8-K exhibit (CORRECTING and REPLACING), 2014-03-27)
[reviewer r2] -> get_position(ACCT-2101, as of 2014-04-28)
[reviewer r2] <- 25,000 shares, projected (position row 2014-02-14)
[reviewer r2] -> calculate(25000*0.072)
[reviewer r2] <- = 1800
[reviewer r2] -> review_verdict(approve, 0 finding(s))
[reviewer r2] VERDICT: approve
[reviewer r2] <- verdict approve recorded

"""The third fund: the answer key to the blind question list (ds/fut_questions.py).

The fund: Simplify Intermediate Term Treasury Futures Strategy ETF (TYA). Prospectus and SAI of the trust dated
November 1, 2026; annual financial statements for June 30, 2026. WRITTEN AFTER the question list, from the passages
of docs_tya/passages.json and from searches over the full text of the three documents, and BEFORE any reader was
run: the fingerprint of this file was printed in the session before the first tracing call.

For each question two answers, because which standard a fund administrator would hold to was left open
(ds/standard.py):
  letter    stated only when a passage says it
  reading   stated also when the passages give the principle and the rest follows without a choice
status: "specified" (stated), "partly" (`missing` says what is not), "absent" (no passage).
Every quote is a part of a passage of the pack (selftest.py checks each). The searches behind "absent" and behind
the missing halves returned no line in any of the three documents: a rounding of the NAV, a contract size or
multiplier, a number of days in the year, a policy for NAV errors, an order of lots, and the word "roll" in the
SAI, in the annual statements and in the fund's own parts of the prospectus.
"""
from __future__ import annotations

S, P, A = "specified", "partly", "absent"

KEY = {
    "F01": {"kind": "fund", "letter": S, "reading": S,
            "sources": [("annual", "Futures contracts are generally valued at the settlement prices established each day on the exchange on which they are traded"),
                        ("sai", "Futures and options on futures are valued at the settlement price determined by the exchange")]},
    "F02": {"kind": "fund", "letter": P, "reading": S,
            "sources": [("sai", "if no settlement price is available, at the last sale price as of the close of business prior to when the Funds calculate NAV"),
                        ("prospectus", "If market quotations are not readily available, securities will be valued at their fair market value")],
            "missing": "a missing settlement price is covered; trading stopped at a price limit is not named, only the general fair-value rule"},
    "F03": {"kind": "fund", "letter": P, "reading": S,
            "sources": [("sai", "Futures and options on futures are valued at the settlement price determined by the exchange")],
            "missing": "the settlement price is named; a futures market that closes at another time than the NAV is not spoken of"},
    "F04": {"kind": "contract", "letter": A, "reading": A,
            "missing": "the size of a contract is nowhere given; the schedule shows a number of contracts and a notional value"},
    "F05": {"kind": "fund", "letter": P, "reading": S,
            "sources": [("annual", "Includes cumulative unrealized appreciation or unrealized cumulative depreciation on futures contracts as disclosed in the Schedule of Investments"),
                        ("annual", "realized gains/(losses) and the change in unrealized appreciation/(depreciation) on futures contracts")],
            "missing": "no sentence says how the daily change is recorded; the captions of the statements show it as unrealized appreciation or depreciation"},
    "F06": {"kind": "fund", "letter": P, "reading": P,
            "sources": [("sai", "to and from the futures broker, are made on a daily basis as the price of the underlying assets fluctuate")],
            "missing": "paid every day is stated; how the payment is shown in the books while the contract stays open is not"},
    "F07": {"kind": "fund", "letter": S, "reading": S,
            "sources": [("sai", "no price would be paid or received by a Fund upon the purchase or sale of a futures contract"),
                        ("annual", "a Fund would be required to deposit with its custodian or futures broker in a segregated account in the name of the futures broker")]},
    "F08": {"kind": "fund", "letter": P, "reading": S,
            "sources": [("annual", "a Fund would be required to deposit with its custodian or futures broker in a segregated account in the name of the futures broker an amount of cash, U.S. government securities, suitable money market instruments, or other liquid securities"),
                        ("annual", "The margin required for a particular futures contract is set by the exchange on which the contract is traded")],
            "missing": "who sets the amount, the form and where it is held are stated; how the deposit is carried in the fund's books is not said in words"},
    "F09": {"kind": "fund", "letter": P, "reading": S,
            "sources": [("sai", "If the offsetting purchase price is less than the original sale price, a Fund realizes a gain; if it is more, a Fund realizes a loss.")],
            "missing": "closing by an offsetting trade is covered; a contract that runs to expiry is not"},
    "F10": {"kind": "fund", "letter": P, "reading": P,
            "sources": [("annual", "Gains or losses realized on sales of securities are determined using the specific identification method by comparing the identified cost of the security lot sold with the net sales proceeds.")],
            "missing": "identification of the lot is stated, for securities; which lot is taken first, and that futures follow the rule, is not"},
    "F11": {"kind": "fund", "letter": P, "reading": S,
            "sources": [("sai", "The transaction costs must also be included in these calculations."),
                        ("annual", "Brokerage fees are paid when a futures contract is bought or sold and margin deposits must be maintained.")],
            "missing": "that the costs enter the gain or loss and when they are paid is stated; whether they are charged when paid or carried until the contract is closed is not"},
    "F12": {"kind": "fund", "letter": A, "reading": A,
            "missing": "no passage says when or how a position is moved to a later contract; the fund rebalances at least quarterly, which is not the same thing"},
    "F13": {"kind": "contract", "letter": P, "reading": P,
            "sources": [("sai", "in practice most futures contracts are usually closed out before the delivery date")],
            "missing": "what usually happens is stated; what happens to a contract held to expiry, and at which price, is not"},
    "F14": {"kind": "fund", "letter": P, "reading": P,
            "sources": [("prospectus", "The Fund rebalances its holdings no less frequent than quarterly to position its portfolio so that its exposure to the Index is consistent with its quarterly investment objective.")],
            "missing": "how often is stated; how much exposure in relation to net assets is not"},
    "F15": {"kind": "fund", "letter": A, "reading": P,
            "sources": [("annual", "number of contracts | notional value | expiration date")],
            "missing": "the schedule reports a notional value for the position; how it is measured is not said"},
    "F16": {"kind": "fund", "letter": P, "reading": P,
            "sources": [("prospectus", "The Collateral may consist of (1) U.S. Government securities, such as bills, notes and bonds issued by the U.S. Treasury with a duration of less than two years; (2) money market funds (including affiliated money market ETFs)"),
                        ("annual", "Interest income is recognized on an accrual basis")],
            "missing": "what the cash may be invested in and that income accrues is stated; the day basis is not"},
    "F17": {"kind": "contract", "letter": P, "reading": P,
            "sources": [("sai", "A Fund expects to earn interest income on margin deposits.")],
            "missing": "that interest is expected is stated; the rate, the basis and whether the fund pays interest on a shortfall are not"},
    "F18": {"kind": "fund", "letter": S, "reading": S,
            "sources": [("prospectus", "The Fund will issue and redeem Shares at NAV only in large blocks of 25,000 Shares"),
                        ("sai", "A fixed fee payable to the Custodian is imposed on each creation and redemption transaction regardless of the number of Creation Units involved in the transaction")]},
    "F19": {"kind": "fund", "letter": P, "reading": P,
            "sources": [("sai", "any difference between the market value at which the securities and/or financial instruments were purchased by the Fund and the cash-in-lieu amount"),
                        ("sai", "are required to pay an additional variable charge to compensate the relevant Fund and its ongoing shareholders for brokerage and market impact expenses relating to Creation Unit transactions")],
            "missing": "who bears the difference is stated; at which prices the futures are traded in relation to the NAV of the order is not"},
    "F20": {"kind": "fund", "letter": P, "reading": S,
            "sources": [("annual", "The transaction fee is used to defray the costs associated with the issuance and redemption of Creation Units."),
                        ("sai", "A fixed fee payable to the Custodian is imposed on each creation and redemption transaction")],
            "missing": "the fixed fee is paid to the custodian, so it does not pass through the fund; how the variable charge that the fund receives is booked is not said"},
    "F21": {"kind": "fund", "letter": P, "reading": P,
            "sources": [("prospectus", "NAV is computed by determining, the aggregate market value of all assets of the applicable Fund, less its liabilities, divided by the total number of shares outstanding"),
                        ("prospectus", "The NAV of each Fund is determined at the close of regular trading (normally 4:00 p.m. Eastern Time)")],
            "missing": "the computation and the time are stated; a rounding is not"},
    "F22": {"kind": "fund", "letter": S, "reading": S,
            "sources": [("prospectus", "including management, administration, and distribution fees, which are accrued daily"),
                        ("annual", "average daily net assets, computed and accrued daily and payable monthly, at an annual rate equal to:")]},
    "F23": {"kind": "fund", "letter": A, "reading": A,
            "missing": "no document gives the number of days in the year or which day's net assets"},
    "F24": {"kind": "fund", "letter": A, "reading": A,
            "missing": "no document gives a threshold or a correction policy"},
    "F25": {"kind": "fund", "letter": P, "reading": S,
            "sources": [("sai", "will be subject to special tax rules (including mark-to-market, constructive sale, straddle, wash sale and short sale rules)"),
                        ("annual", "section 1256 mark-to-market treatment of derivatives")],
            "missing": "that a mark-to-market rule applies is stated; what the books must do with open contracts at the end of the year is not spelled out"},
}

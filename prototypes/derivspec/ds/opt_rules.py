"""The rules the options reference relies on, and where each one comes from.

kind:   "fund"      the fund's own public documents should state it (valuation, accounting policy, capital transactions)
        "contract"  a term of the option contract, of the clearing house's rules or of the deposit account
status: "specified" a public passage states the rule
        "partly"    a passage states part of it; `missing` says what had to be assumed
        "absent"    no public passage; the rule is an assumption of this reference
Every quote is a part of a passage in docs_koct/passages.json (cut from the full text of the document by
collect_koct.py); selftest.py checks each quote against its passage. "Absent" is backed by a search over the
whole text of the three documents (docs_koct/searches.json).

The fund: Innovator U.S. Small Cap Power Buffer ETF - October. Prospectus dated February 27, 2026 as
supplemented October 1, 2026; SAI dated February 27, 2026 as supplemented April 16, 2026; audited annual
financial statements for October 31, 2025.

ONE THING THE DOCUMENTS DO NOT AGREE ON. The three documents give three rules for the price of a FLEX option:
  prospectus  the exchange's model-based price, replaced by a same-day trade price when the option traded (P13)
  annual      the exchange's model-based price; nothing about a trade price (A2)
  SAI         a general rule for exchange-traded options: the last published settlement price, or the midpoint
              of bid and ask where there is none (S14); nothing about FLEX options or model prices
The reference follows the prospectus, which is the latest document and the only one specific to this fund, and
counts O05 to O08 as stated. The SAI's passage is in the pack, so a draft can notice the difference; whether it
does is read separately and is not part of the settled / not settled count.
The same holds for O07 (no model price from the exchange): the prospectus names a backup pricing provider, the
annual report goes straight to the Valuation Designee, the SAI's general rule takes the midpoint. I had not seen
that one; a reader of the rule-by-rule tracing reported it (score_trace.py, CONFLICT_RULES).

WHERE THIS TABLE IS MORE LENIENT THAN A STRICT READER. In the rule-by-rule tracing (18 tracings, readers told not
to answer from general practice) most answers did not accept three rules as stated that this table does: O09 (the
measure and the commissions are stated for closing a written option, not for selling a purchased one), O12 (the
entries for an option that is cash-settled in the money) and O14 (the value at which options delivered in kind
leave the books). The table keeps the obvious reading; score_trace.py reports how many figures would move.
"""
from __future__ import annotations

RULES = {
    "O01": {"kind": "fund", "status": "specified",
            "text": "NAV per share is net assets divided by shares outstanding, rounded to the cent, struck at the close of regular trading.",
            "sources": [("P12", "dividing such amount by the total number of Shares outstanding. The result, rounded to the nearest cent is the NAV per Share.")]},
    "O02": {"kind": "fund", "status": "specified",
            "text": "A purchased option is an investment recorded at the premium paid and adjusted every day to its current value.",
            "sources": [("A3", "When the Funds purchase an option, an amount equal to the premium paid by the Funds are recorded as an investment and is subsequently adjusted to the current value of the option purchased.")]},
    "O03": {"kind": "fund", "status": "specified",
            "text": "A written option is a liability recorded at the premium received and adjusted every day to its current value.",
            "sources": [("A3", "When the Funds write an option, an amount equal to the premium received by the Funds are recorded as a liability and is subsequently adjusted to the current value of the option written.")]},
    "O04": {"kind": "contract", "status": "specified",
            "text": "One contract covers 100 shares of the reference ETF.",
            "sources": [("T1", "100 shares per contract.")]},
    "O05": {"kind": "fund", "status": "specified",
            "text": "A FLEX option is valued at the model-based price the exchange provides at its official close.",
            "sources": [("P13", "FLEX Options listed on an exchange will typically be valued at a model-based price provided by the exchange at the official close of that exchange"),
                        ("A2", "FLEX Options will be valued at a model-based price provided by the exchange on which the option is traded at the official close of that exchange")],
            "note": "the SAI's general rule for exchange-traded options (S14) is different"},
    "O06": {"kind": "fund", "status": "specified",
            "text": "When the option traded that day, the trade price replaces the model price.",
            "sources": [("P13", "this same-day market trading price will be used for FLEX Option values instead of the exchange")],
            "note": "in the prospectus only; the annual report has no such sentence and the SAI's general rule (S14) is different"},
    "O07": {"kind": "fund", "status": "specified",
            "text": "Without a model price from the exchange, the backup pricing provider's model price is used.",
            "sources": [("P13", "If the exchange on which the option is traded is unable to provide a model price, model-based FLEX Options prices will additionally be provided by a backup third-party pricing provider.")]},
    "O08": {"kind": "fund", "status": "specified",
            "text": "On a day with a cash basket and an in-kind basket in the same option, the trade price values both.",
            "sources": [("P13", "for valuation purposes that trading day the Fund will default to use the trade price for both instances, rather than the model price otherwise available for the in-kind transaction.")]},
    "O09": {"kind": "fund", "status": "specified",
            "text": "Closing a position in the market realizes the difference between the premium and the amount paid or received, commissions included.",
            "sources": [("A3", "The difference between the premium and the amount paid on effecting a closing purchase transaction, including brokerage commissions, is also treated as a realized gain, or if the premium is less than the amount paid for the closing purchase transaction, as a realized loss."),
                        ("A3", "If an option expires on the stipulated expiration date or if the Funds enter into a closing sale transaction, a gain or loss is realized.")]},
    "O10": {"kind": "fund", "status": "partly",
            "text": "When part of a position built in several purchases is closed, the contracts with the highest premium are taken first.",
            "sources": [("A5", "The Trust determines the gain or loss realized from investment transactions on the basis of identified cost.")],
            "missing": "identified cost is stated; the order in which the lots are identified is not (highest cost first is this reference's assumption)"},
    "O11": {"kind": "contract", "status": "specified",
            "text": "The options are European and cash-settled: at expiration the holder receives the difference between the reference's closing price and the strike, times 100 shares, and an option out of the money has no value.",
            "sources": [("S3", "Notwithstanding the above, the Funds utilize FLEX Options that are cash-settled."),
                        ("S3", "times a specified multiple"),
                        ("S2", "Option contracts that expire unexercised have no value."),
                        ("P2", "Upon conclusion of the Outcome Period, the Fund will receive the cash value of all the FLEX Options it held for the prior Outcome Period."),
                        ("P7", "The FLEX Options in which the Fund invests are all European style option contracts")]},
    "O12": {"kind": "fund", "status": "specified",
            "text": "At expiration the gain or loss on each position is realized: cash value against premium.",
            "sources": [("A3", "If an option expires on the stipulated expiration date or if the Funds enter into a closing sale transaction, a gain or loss is realized."),
                        ("A3", "Premiums received from writing options that expire unexercised are treated by the Funds on the expiration date as realized gain from written options.")]},
    "O13": {"kind": "fund", "status": "specified",
            "text": "Creation units are issued and redeemed at the NAV per share times the shares in the unit; in kind, the basket goes with a cash amount equal to the unit's NAV less the basket's market value; the transaction fee is added on a creation and deducted on a redemption.",
            "sources": [("S9", "less the applicable Redemption Transaction Fee as described below"),
                        ("S9", "and the aggregate market value of the Deposit Instruments"),
                        ("S10", "The price for each Creation Unit will equal the daily NAV per share of a Fund times the number of shares in a Creation Unit, plus the fees described above"),
                        ("S8", "The Cash Component is an amount equal to the difference between the NAV of a Fund")]},
    "O14": {"kind": "fund", "status": "specified",
            "text": "Options delivered in kind leave the books at the day's value and the gain or loss on them is realized as an in-kind gain or loss.",
            "sources": [("A10", "(b) Amount is included in realized gain/(loss) in-kind on the Statements of Operations."),
                        ("T2", "Purchased Options in-kind(b)")]},
    "O15": {"kind": "fund", "status": "specified",
            "text": "A pro-rata basket holds each position in proportion to the shares in a creation unit.",
            "sources": [("S5", "A pro-rata basket is a basket that is a pro rata representation of the ETF")]},
    "O16": {"kind": "fund", "status": "partly",
            "text": "A basket holds whole contracts, rounded down; the difference is settled in the cash amount.",
            "sources": [("S5", "When utilizing a pro-rata basket, minor deviations may occur when it is not operationally feasible to include a particular instrument within the basket")],
            "missing": "deviations are allowed; how a fraction of a contract is rounded is not said"},
    "O17": {"kind": "fund", "status": "specified",
            "text": "The management fee is calculated every day on net assets at the annual rate and paid monthly.",
            "sources": [("A6", "pay monthly the Adviser a unitary fee calculated daily based on the average daily net assets of each Fund at the annual rate of 0.79%.")]},
    "O18": {"kind": "fund", "status": "absent",
            "text": "The fee accrual divides the annual rate by 365 and is taken on the day's opening net assets.",
            "missing": "no document gives the number of days in the year or which day's net assets"},
    "O19": {"kind": "fund", "status": "specified",
            "text": "Interest earned on the cash balance and not yet collected is part of net assets.",
            "sources": [("P12", "including any interest or dividends accrued but not yet collected"),
                        ("A5", "Interest income, including accretion of discounts and amortization of premiums is recognized on an accrual basis")]},
    "O20": {"kind": "contract", "status": "absent",
            "text": "The deposit account's interest accrues on a 365-day year, for every calendar day.",
            "missing": "the rate is disclosed (variable, 3.70% at the year end); its day basis is not"},
    "O21": {"kind": "fund", "status": "absent",
            "text": "A NAV struck on a wrong price is corrected above a stated threshold.",
            "missing": "no document gives a threshold or a correction policy"},
    "O22": {"kind": "contract", "status": "absent",
            "text": "A two-for-one split of the reference doubles the contracts and halves the strike; a contract still covers 100 shares.",
            "missing": "no document describes how the options are adjusted for a split of the reference"},
    "O23": {"kind": "fund", "status": "specified",
            "text": "The options bring no dividend income: nothing is accrued when the reference goes ex-dividend.",
            "sources": [("P1", "the Fund will not receive the benefit of any dividends."),
                        ("A3", "Purchased options are non-income producing securities.")]},
    "O24": {"kind": "fund", "status": "partly",
            "text": "The transaction fee offsets the costs of the order, so it leaves net assets unchanged.",
            "sources": [("P11", "the Fund imposes transaction fees on purchases and redemptions of Creation Units to cover the custodial and other costs the Fund incurs in effecting trades."),
                        ("A8", "Additional charges received by the Funds, if any, are disclosed as Transaction Fees on the Statements of Changes in Net Assets.")],
            "missing": "how the fee and the costs it covers are booked, and whether they are equal"},
}


def counts() -> dict:
    fund = [r for r in RULES.values() if r["kind"] == "fund"]
    other = [r for r in RULES.values() if r["kind"] != "fund"]
    return {"rules": len(RULES), "fund_rules": len(fund),
            "fund_specified": sum(r["status"] == "specified" for r in fund),
            "fund_partly": sum(r["status"] == "partly" for r in fund),
            "fund_absent": sum(r["status"] == "absent" for r in fund),
            "contract_rules": len(other),
            "contract_in_the_documents": sum(r["status"] == "specified" for r in other)}


def settled(rule_ids) -> bool:
    """True when every rule a figure needs is stated in a public document."""
    return all(RULES[r]["status"] == "specified" for r in rule_ids)


# The same rules as questions: what the fund accounting system needs to know before it can process the fund.
# A question does not say what the reference assumes, nor whether a document answers it (trace.py shows these,
# and nothing else of this table, to a reader).
ASK = {
    "O01": "How is NAV per share computed, how is it rounded, and when is it struck?",
    "O02": "How is a purchased option recorded when it is bought, and how is it carried afterwards?",
    "O03": "How is a written option recorded when it is written, and how is it carried afterwards?",
    "O04": "How many shares of the reference ETF does one option contract cover?",
    "O05": "Which price values a FLEX option on a day when the option did not trade?",
    "O06": "Which price values a FLEX option on a day when the option did trade?",
    "O07": "Which price values a FLEX option when the exchange provides no model price?",
    "O08": "On a day with a cash order and an in-kind order in the same option, which price values the option delivered in kind?",
    "O09": "When a position is closed in the market, how is the gain or loss measured, and are commissions part of it?",
    "O10": "When part of a position built in several purchases is closed, which purchases are taken first?",
    "O11": "How are the options settled at expiration, at which price of the reference, and what is an option worth that expires out of the money?",
    "O12": "At expiration, how is the result on each position recorded?",
    "O13": "At what price are creation units issued and redeemed, how is the cash amount that goes with an in-kind basket computed, and how does the transaction fee enter?",
    "O14": "When options are delivered in kind on a redemption, at what value do they leave the books, and what happens to the gain or loss on them?",
    "O15": "In what proportion does a pro-rata basket hold the fund's positions?",
    "O16": "How is a basket rounded when the pro-rata share is not a whole number of contracts?",
    "O17": "How often is the management fee calculated, at what rate, and how often is it paid?",
    "O18": "Over how many days of the year is the annual fee rate spread, and on which day's net assets is the accrual taken?",
    "O19": "Is interest earned on the cash balance and not yet collected part of net assets?",
    "O20": "On what day basis does the deposit account's interest accrue?",
    "O21": "Above what size must a NAV error be corrected, and how?",
    "O22": "How are the options adjusted when the reference ETF splits?",
    "O23": "Does the fund accrue income when the reference ETF pays a dividend?",
    "O24": "How are the transaction fee on a creation or redemption, and the costs it is meant to cover, booked?",
}
for _k, _q in ASK.items():
    RULES[_k]["ask"] = _q


# ---- two standards (ds/standard.py) ------------------------------------------------------------------------------
# Rules this table counts as stated on the obvious reading and that are not stated to the letter. Found in the
# rule-by-rule tracing of 2026-11-16: most readers, told not to answer from general practice, did not accept them.
from . import standard as _standard   # noqa: E402

LETTER = {
    "O09": "the measure and the commissions are stated for closing a written option; for selling a purchased option only that a gain or loss is realized",
    "O12": "expiry of an option out of the money is covered; the entries for an option that is cash-settled in the money are not",
    "O14": "that an in-kind gain or loss exists is shown; the value at which options delivered in kind leave the books is not stated",
}


def status(rid: str) -> str:
    s = RULES[rid]["status"]
    return "partly" if _standard.NAME == "letter" and rid in LETTER and s == "specified" else s


def is_open(rid: str) -> bool:
    return status(rid) != "specified"


def settled(rule_ids) -> bool:   # noqa: F811  (replaces the definition above: the same rule, under the chosen standard)
    """True when every rule a figure needs is stated in a public document."""
    return not any(is_open(r) for r in rule_ids)


def counts() -> dict:            # noqa: F811
    fund = [k for k, r in RULES.items() if r["kind"] == "fund"]
    other = [k for k, r in RULES.items() if r["kind"] != "fund"]
    return {"rules": len(RULES), "fund_rules": len(fund),
            "fund_specified": sum(status(k) == "specified" for k in fund),
            "fund_partly": sum(status(k) == "partly" for k in fund),
            "fund_absent": sum(status(k) == "absent" for k in fund),
            "contract_rules": len(other),
            "contract_in_the_documents": sum(status(k) == "specified" for k in other)}

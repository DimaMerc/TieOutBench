"""The rules the reference relies on, and where each one comes from.

kind:   "fund"         the fund's own public documents should state it (prospectus, SAI, annual report)
        "confirmation" a term of the swap confirmation, which is not public; a constructed confirmation supplies it
status: "specified"    a public passage states the rule
        "partly"       a passage states part of it; `missing` says what had to be assumed
        "absent"       no public passage; the rule is an assumption of this reference
Passages are quoted from prototypes/derivspec/docs/ (collected 2026-11-16 from the public documents of one real
fund that holds total return swaps: annual report to June 30, 2026, prospectus and SAI dated November 1, 2026).

CALIBRATION of 2026-11-16, made after the first six drafts were scored (the scores before it are kept in
data/out/draft_scores.before_calibration.json and gaps.before_calibration.json). Every change takes a figure OUT
of the "not settled" group or stops a reasonable reading from counting against a draft:
  1. R17 (which price values the swap) was "partly"; two models read the general valuation sentence as settling
     it (the last readily available market price), which is a fair reading. Now "specified", and the scenario
     expects the closing price.
  2. R13 (collateral) was "partly". The entries asked for (cash down, collateral up, net assets unchanged) follow
     from the fund's own cash being segregated. Now "specified".
  3. R04, R08 and R14 each mixed a stated principle with an unstated detail. The principle is now the rule
     ("specified") and the detail is its own rule: the day count was already R05; R19 = when swap income is
     accrued; R20 = the number of days in the year for the expense accrual.
  4. The $500 transaction fee: the reference kept it in net assets, all three models treated it as offsetting the
     costs it is charged for, which is the documents' own description. The reference now nets it against costs,
     and R18 records that the documents do not say how the fee and those costs are booked.
SECOND CALIBRATION, the same day, after reading every wrong figure (scores before it:
data/out/draft_scores.after_first_calibration.json):
  5. The prompt names no units and no sign: a percentage given as a fraction (0.005714 for 0.5714%) and the size of
     an error given with a minus sign (understated) are accepted. Four figures of one model had been marked wrong.
  6. The published NAV of the whole-day scenario is 26.24 under either day count and either expense basis, so it
     is settled by the NAV formula alone; all three models had labelled it as resting on a document.
THIRD CALIBRATION, the same day, after the checking pass (54 readings; results before it are kept in
data/out/*.before_third_calibration.json). Unlike the first two, the first change takes a figure INTO the "not
settled" group; both were found by reading what the readers flagged and what they did not:
  7. R21 is new. Two of the three readers marked the unrealized gain after an INCREASE of the swap as not settled
     in 18 of their 18 readings: no document says whether an increase leaves the gain so far unrealized or resets
     the swap. The table already had the same gap for a REDUCTION (R10) and had left the increase out. The
     reference keeps its assumption (the gain stays unrealized); the figure now counts as not settled.
  8. R19 (when income on the swap is accrued) was "absent". The annual report does state a date for dividend
     income in general; it does not say that amounts owed under a swap follow it. Now "partly", with the
     passage. No count of settled figures changes. Ten of the eighteen drafts quote that passage in a requirement
     (summary.py counts them). This note first said that none did, which was wrong: only the quotes attached to
     the figure itself had been read. Corrected on 2026-11-18.
"""
from __future__ import annotations

AR = "01-msox-annual-report-2026-06-30.md"
PR = "02-msox-prospectus-2026-11-01.md"
SAI = "03-advisorshares-sai-2026-11-01.md"

RULES = {
    "R01": {"kind": "fund", "text": "NAV per share is net assets divided by shares outstanding, rounded to the cent, struck once a day at a stated time.",
            "status": "specified", "document": SAI,
            "quote": "The NAV per share of a Fund is computed by dividing the value of the net assets of the Fund (i.e., the value of its total assets less total liabilities) by the total number of shares of the Fund outstanding, rounded to the nearest cent."},
    "R02": {"kind": "fund", "text": "The swap is marked to market every day from the value of the reference security.",
            "status": "specified", "document": AR,
            "quote": "Equity swap contracts are marked to market daily based on the value of the underlying security and the change, if any, is recorded as an unrealized gain or loss."},
    "R03": {"kind": "fund", "text": "The daily change in the swap's value is recorded as an unrealized gain or loss.",
            "status": "specified", "document": AR,
            "quote": "Equity swap contracts are marked to market daily based on the value of the underlying security and the change, if any, is recorded as an unrealized gain or loss."},
    "R04": {"kind": "fund", "text": "The fund owes financing on the swap's notional at a floating rate plus a spread, recognized as it accrues.",
            "status": "specified", "document": SAI,
            "quote": "The Fund will agree to pay to the counterparty a floating rate of interest on the notional amount of the swap agreement"},
    "R05": {"kind": "confirmation", "text": "The day-count convention of the financing leg (here actual/360).",
            "status": "absent", "missing": "no document gives a day-count basis"},
    "R06": {"kind": "confirmation", "text": "Financing accrues for every calendar day, so a weekend counts three days.",
            "status": "absent", "missing": "no document says which days accrue"},
    "R07": {"kind": "confirmation", "text": "Which floating rate applies to which day, and how often it resets (here the day's published rate).",
            "status": "absent", "missing": "the index and the spread are public; how often the rate resets is not"},
    "R08": {"kind": "fund", "text": "The fund is owed the dividends paid on the reference security.",
            "status": "specified", "document": SAI,
            "quote": "The counterparty will generally agree to pay the Fund the amount, if any, by which the notional amount of the swap agreement would have increased in value had it been invested in the particular stocks, plus the dividends that would have been received on those stocks."},
    "R09": {"kind": "fund", "text": "At each close the swap's exposure is brought back to the target multiple of the fund's net assets.",
            "status": "specified", "document": PR,
            "quote": "The Fund will reposition its portfolio at the end of every trading day."},
    "R10": {"kind": "fund", "text": "When the swap is reduced, the gain or loss on the part given up is realized.",
            "status": "absent", "missing": "no document says how a change in the swap's size is recorded"},
    "R11": {"kind": "fund", "text": "On a reset or payment date the net of gain or loss, income and financing is paid, recorded as realized, and the swap restarts at the day's price.",
            "status": "partly", "document": AR,
            "quote": "Periodic payments received or paid by a Fund are recorded as realized gains or losses.",
            "missing": "whether the unrealized gain is paid on the monthly date and the swap restarts at that day's price"},
    "R12": {"kind": "fund", "text": "Creations and redemptions are made in cash at the day's NAV per share, with a transaction fee.",
            "status": "specified", "document": SAI,
            "quote": "Creation Units of the Cash Funds are sold only for cash (\"Cash Purchase Amount\"). Creation Units are sold at the NAV per share next computed, plus a transaction fee"},
    "R13": {"kind": "fund", "text": "Collateral the fund posts is the fund's own cash set aside; moving it does not change net assets.",
            "status": "specified", "document": AR,
            "quote": "As of June 30, 2026, cash in the amount of $55,830,545 has been segregated as collateral from the broker for swap contracts."},
    "R14": {"kind": "fund", "text": "Expenses accrue every day on net assets at the annual rate.",
            "status": "specified", "document": SAI,
            "quote": "Expenses and fees, including without limitation, the management, administration and distribution fees, are accrued daily and taken into account for purposes of determining NAV per share."},
    "R15": {"kind": "fund", "text": "A NAV struck on a wrong figure is corrected above a stated threshold.",
            "status": "absent", "missing": "no document gives a threshold or a correction policy"},
    "R16": {"kind": "confirmation", "text": "A split of the reference security changes the units and the reset price in proportion and leaves the value unchanged.",
            "status": "absent", "missing": "no document describes adjustments for corporate actions on the reference"},
    "R17": {"kind": "fund", "text": "The reference security is taken at its last readily available market price, here its closing price.",
            "status": "specified", "document": AR,
            "quote": "In computing each Fund's NAV, the Fund's portfolio investments are generally valued based on their last readily available market price."},
    "R18": {"kind": "fund", "text": "The transaction fee offsets the costs of the creation or redemption, so it leaves net assets unchanged.",
            "status": "partly", "document": AR,
            "quote": "To compensate a Fund for transfer and other transaction costs involved in creation transactions and redemption transactions through the clearing process, investors will be required to pay a minimum transaction fee, assessed per transaction, of $500.",
            "missing": "how the fee and the costs it offsets are booked, and whether they are equal"},
    "R19": {"kind": "fund", "text": "Income on the swap is accrued on the ex-dividend date of the reference security.",
            "status": "partly", "document": AR,
            "quote": "Dividend income and distributions to shareholders are recognized on the ex-dividend date and interest income and expenses are recognized on the accrual basis.",
            "missing": "the date is stated for dividend income in general; whether amounts owed under a swap follow it (and not the pay date or the next payment date) is not"},
    "R20": {"kind": "fund", "text": "The expense accrual divides the annual rate by 365 and is taken on the day's opening net assets.",
            "status": "absent", "missing": "no document gives the number of days in the year or which day's net assets"},
    "R21": {"kind": "fund", "text": "When the swap is increased, the gain so far stays unrealized and the added units come in at the day's price.",
            "status": "absent", "missing": "no document says whether an increase of the swap resets it or leaves the gain so far unrealized"},
}


def counts() -> dict:
    fund = [r for r in RULES.values() if r["kind"] == "fund"]
    conf = [r for r in RULES.values() if r["kind"] == "confirmation"]
    return {"rules": len(RULES), "fund_rules": len(fund),
            "fund_specified": sum(r["status"] == "specified" for r in fund),
            "fund_partly": sum(r["status"] == "partly" for r in fund),
            "fund_absent": sum(r["status"] == "absent" for r in fund),
            "confirmation_rules": len(conf),
            "confirmation_public": sum(r["status"] == "specified" for r in conf)}


def settled(rule_ids) -> bool:
    """True when every rule a figure needs is stated in a public document."""
    return all(RULES[r]["status"] == "specified" for r in rule_ids)


# The same rules as questions: what the fund accounting system needs to know before it can process the fund.
# A question does not say what the reference assumes, nor whether a document answers it (trace.py shows these,
# and nothing else of this table, to a reader).
ASK = {
    "R01": "How is NAV per share computed, how is it rounded, and when is it struck?",
    "R02": "How often is the swap valued, and from what?",
    "R03": "How is the daily change in the swap's value recorded?",
    "R04": "On what amount, and at what kind of rate, does the fund owe financing on the swap?",
    "R05": "Which day-count convention applies to the swap's financing?",
    "R06": "On which days does the swap's financing accrue: business days only, or every calendar day?",
    "R07": "Which day's floating rate applies to each day of accrual, and how often is the rate reset?",
    "R08": "Is the fund owed the dividends paid on the reference security?",
    "R09": "How often is the swap's exposure brought back to the fund's target multiple?",
    "R10": "When the swap is reduced, what happens to the gain or loss on the part given up?",
    "R11": "On a reset or payment date of the swap, what is paid, how is it recorded, and at what price does the swap continue?",
    "R12": "In what form, at what price and with what charge are creation units issued and redeemed?",
    "R13": "When the fund posts collateral for the swap, what changes in its books and in its net assets?",
    "R14": "How often do the fund's expenses accrue?",
    "R15": "Above what size must a NAV error be corrected, and how?",
    "R16": "How is the swap adjusted when the reference security splits?",
    "R17": "Which price of the reference security is used to value the swap?",
    "R18": "How are the transaction fee on a creation or redemption, and the costs it is meant to cover, booked?",
    "R19": "On which date is income owed to the fund under the swap accrued?",
    "R20": "Over how many days of the year is the annual expense rate spread, and on which day's net assets is the accrual taken?",
    "R21": "When the swap is increased, what happens to the gain so far?",
}
for _k, _q in ASK.items():
    RULES[_k]["ask"] = _q


# ---- two standards (ds/standard.py) ------------------------------------------------------------------------------
# Rules this table counts as stated on the obvious reading and that are not stated to the letter. Found in the
# rule-by-rule tracing of 2026-11-16: most readers, told not to answer from general practice, did not accept them.
from . import standard as _standard   # noqa: E402

LETTER = {
    "R13": "that cash is segregated as collateral is stated; how posting it is booked, and that net assets do not change, is not",
    "R17": "the last readily available market price is stated in general; which price of the reference security (close, last trade, NAV) is not",
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
    conf = [k for k, r in RULES.items() if r["kind"] == "confirmation"]
    return {"rules": len(RULES), "fund_rules": len(fund),
            "fund_specified": sum(status(k) == "specified" for k in fund),
            "fund_partly": sum(status(k) == "partly" for k in fund),
            "fund_absent": sum(status(k) == "absent" for k in fund),
            "confirmation_rules": len(conf),
            "confirmation_public": sum(status(k) == "specified" for k in conf)}

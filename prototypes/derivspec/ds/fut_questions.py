"""The third fund: what a fund accounting system needs to know to process exchange-traded futures.

WRITTEN BLIND. This list was written on 2026-11-16 from the instrument alone (futures contracts held directly by
a registered exchange-traded fund), before a fund was chosen and before any of its documents was opened. Its
fingerprint (sha256 of this file) was printed in the session before the first document was fetched, and the file
has not been changed since: the answer key for the fund that was then chosen is in ds/fut_key.py.

The questions follow the order in which a position lives: valuation each day, margin, opening and closing, the
roll and expiry, exposure, cash and income, orders for creation units, and the fund's own NAV, expenses and errors.
As in the first two funds, a question does not say what an answer would be nor whether a document gives one.
"""
from __future__ import annotations

ASK = {
    "F01": "Which price values an open futures contract each day, and where does it come from?",
    "F02": "How is a futures contract valued when the exchange gives no settlement price, or when trading has stopped at a price limit?",
    "F03": "When the futures market closes at a different time from the time the NAV is struck, which price is taken?",
    "F04": "What is the size of one contract, that is, what turns a change in the futures price into dollars?",
    "F05": "How is the daily change in the value of an open futures contract recorded?",
    "F06": "How is variation margin paid or received, and how is that payment shown in the books while the contract stays open?",
    "F07": "What is recorded when a futures contract is opened?",
    "F08": "How much initial margin is posted, in what form, and how is it carried in the fund's books?",
    "F09": "When a futures contract is closed or expires, how is the gain or loss measured and recorded?",
    "F10": "When part of a position opened at different prices is closed, which contracts are taken first?",
    "F11": "How are brokerage commissions and exchange fees on futures recorded: as part of the gain or loss, or as an expense, and when?",
    "F12": "When and how is a position moved from an expiring contract to a later one?",
    "F13": "What happens to a contract still held at expiry: is it settled in cash or by delivery, and at which price?",
    "F14": "How much exposure does the fund take through futures in relation to its net assets, and how often is it brought back to that level?",
    "F15": "How is the exposure of a futures position measured?",
    "F16": "How is the cash that is not needed as margin invested, and on what day basis does its income accrue?",
    "F17": "Does the fund earn or pay interest on the margin it holds with the broker, and on what basis?",
    "F18": "In what form, at what price and with what charge are creation units issued and redeemed?",
    "F19": "When creation units are issued or redeemed for cash, at which prices are the futures traded in relation to the NAV of the order, and who bears the difference?",
    "F20": "How are the transaction fee on a creation or redemption, and the costs it is meant to cover, booked?",
    "F21": "How is NAV per share computed, how is it rounded, and when is it struck?",
    "F22": "How often do the fund's expenses accrue, and at what rate?",
    "F23": "Over how many days of the year is the annual expense rate spread, and on which day's net assets is the accrual taken?",
    "F24": "Above what size must a NAV error be corrected, and how?",
    "F25": "Is there a tax rule for futures still open at the end of the year that the books must apply?",
}

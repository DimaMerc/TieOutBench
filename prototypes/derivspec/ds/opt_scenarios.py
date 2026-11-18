"""Fifteen test scenarios for a defined-outcome ETF that holds four FLEX option positions, with expected results.

Every figure in `given` is constructed. Every figure in `expected` is computed by ds/opt_engine.py from `given`;
none is typed in. `needs` names, for each expected figure, the rules it rests on (ds/opt_rules.py); a figure whose
rules are all stated in a public document is "settled by the documents".

The constructed fund is the one of the repository's options-redemption case (cases/grbo-redeem-2026.case.yaml):
four positions of 24,000 contracts on a reference ETF that stood at 240.00 when the outcome period began,
20,000,000 shares, creation units of 50,000 shares, a $500 transaction fee. The management fee (0.79%) and the
deposit rate (3.70%) are the figures of the real fund whose documents the rules are checked against; the
documents give neither the size of a creation unit nor the amount of the fee.
"""
from __future__ import annotations

from . import opt_engine as E

M = E.MULT
NAMES = ("purchased_call", "purchased_put", "written_put", "written_call")
STRIKE = {"purchased_call": 2.40, "purchased_put": 240.00, "written_put": 204.00, "written_call": 282.00}
RIGHT = {"purchased_call": "call", "purchased_put": "put", "written_put": "put", "written_call": "call"}
SIDE = {"purchased_call": 1, "purchased_put": 1, "written_put": -1, "written_call": -1}
OPENED = {"purchased_call": 237.75, "purchased_put": 14.50, "written_put": 5.60, "written_call": 6.65}   # premium per share
MODEL = {"purchased_call": 254.90, "purchased_put": 3.95, "written_put": 0.80, "written_call": 4.65}     # exchange model prices
CONTRACTS = 24_000
FUND = {"shares_outstanding": 20_000_000, "net_assets_at_the_start_of_the_period": 578_000_000.0,
        "annual_management_fee_rate": 0.0079, "deposit_account_rate": 0.0370,
        "creation_unit_shares": 50_000, "transaction_fee_per_order": 500.0}
CONVENTIONS = {"fee_basis": "365 days, on the day's opening net assets", "interest_basis": "365 days, every calendar day",
               "lot_order": "the highest premium first", "basket_rounding": "whole contracts, rounded down; the difference in the cash amount",
               "split_adjustment": "contracts times the ratio, strike divided by it, 100 shares per contract unchanged"}
WITHHELD = set(CONVENTIONS)        # the conventions no public document states: not shown to a model

# Answer fields that are amounts: a liability or a payment written with a minus sign is the same answer.
SIGN_FREE = {"value_of_written_options", "liability_for_written_options", "cash_owed_on_written_call", "cash_owed_on_written_put",
             "amount_paid", "premium_paid", "net_cost_of_new_contracts", "misstatement", "misstatement_per_share", "misstatement_percent"}
NOTES = ["Sign of the answers: premiums, values, cash, amounts paid or owed, costs and misstatements are positive numbers; "
         "a realized or unrealized gain is positive and a loss is negative; a change is positive for an increase."]

FEE, UNIT = FUND["transaction_fee_per_order"], FUND["creation_unit_shares"]
RATE, DEPOSIT = FUND["annual_management_fee_rate"], FUND["deposit_account_rate"]
CASH, ACCRUED_FEE = 2_100_000.0, 260_000.0


def legs(contracts: float = CONTRACTS, opened: dict = OPENED) -> tuple:
    return tuple(E.leg(n, RIGHT[n], SIDE[n], STRIKE[n], contracts, opened[n]) for n in NAMES)


def base_fund(contracts: float = CONTRACTS) -> E.Fund:
    """The fund on the valuation day of the redemption case: 610,000,000 of net assets at the model prices."""
    return E.Fund(cash=CASH, accrued_fee=ACCRUED_FEE, accrued_interest=0.0, shares=FUND["shares_outstanding"], legs=legs(contracts))


def by(f: E.Fund) -> dict:
    return {l.name: l for l in f.legs}


def build() -> list[dict]:
    out = []

    def add(sid, title, given, ask, fields):
        """fields: name -> (value, [rules the figure rests on])"""
        out.append({"id": sid, "title": title, "given": given, "ask": ask,
                    "expected": {k: v for k, (v, _) in fields.items()},
                    "needs": {k: r for k, (_, r) in fields.items()},
                    "rules": sorted({x for _, r in fields.values() for x in r})})

    f0 = base_fund()
    L = by(f0)
    positions = {n: {"strike": STRIKE[n], "contracts": CONTRACTS} for n in NAMES}

    paid = sum(L[n].premium for n in NAMES if SIDE[n] > 0)
    received = sum(L[n].premium for n in NAMES if SIDE[n] < 0)
    start = FUND["net_assets_at_the_start_of_the_period"]
    add("T01", "Setting up the positions at the start of the outcome period",
        {"net_assets_all_in_cash": start, "reference_price": 240.00, "positions": positions,
         "price_per_share_at_which_each_is_opened": OPENED},
        "What premium does the fund pay for the purchased options and receive for the written ones, what cash is left, "
        "what is recorded as a liability, and what are net assets afterwards?",
        {"premium_paid": (paid, ["O02", "O04"]),
         "premium_received": (received, ["O03", "O04"]),
         "cash_after": (start - paid + received, ["O02", "O03", "O04"]),
         "liability_for_written_options": (received, ["O03", "O04"]),
         "net_assets_after": (start, ["O02", "O03", "O04"])})

    pv = sum(E.amount(L[n], MODEL[n]) for n in NAMES if SIDE[n] > 0)
    wv = sum(E.amount(L[n], MODEL[n]) for n in NAMES if SIDE[n] < 0)
    add("T02", "One day's value",
        {"positions": positions, "premium_per_share_at_which_each_was_opened": OPENED,
         "exchange_model_price_at_the_close": MODEL, "trades_in_the_options_that_day": "none",
         "cash": CASH, "management_fee_accrued_and_unpaid": ACCRUED_FEE, "shares_outstanding": FUND["shares_outstanding"]},
        "What are the value of the purchased options, the value of the written options, the unrealized gain or loss on "
        "each group, net assets and the NAV per share that is published?",
        {"value_of_purchased_options": (pv, ["O02", "O04", "O05"]),
         "value_of_written_options": (wv, ["O03", "O04", "O05"]),
         "unrealized_on_purchased": (sum(E.unrealized(L[n], MODEL[n]) for n in NAMES if SIDE[n] > 0), ["O02", "O04", "O05"]),
         "unrealized_on_written": (sum(E.unrealized(L[n], MODEL[n]) for n in NAMES if SIDE[n] < 0), ["O03", "O04", "O05"]),
         "net_assets": (E.net_assets(f0, MODEL), ["O01", "O02", "O03", "O04", "O05"]),
         "nav_per_share_published": (E.published(E.nav_per_share(f0, MODEL)), ["O01", "O02", "O03", "O04", "O05"])})

    put = L["purchased_put"]
    quotes = {"closing_bid": 3.85, "closing_ask": 4.15}
    add("T03", "Which price values an option",
        {"option": "the purchased put", "contracts_held_at_the_close_in_each_case": CONTRACTS,
         "case_a": {"exchange_model_price_at_its_official_close": 3.95, **quotes, "trades_in_the_option_that_day": "none"},
         "case_b": {"exchange_model_price_at_its_official_close": 3.95, **quotes,
                    "trades_in_the_option_that_day": "the fund bought 120 contracts at 4.02"},
         "case_c": {"exchange_model_price_at_its_official_close": "not provided", "backup_pricing_provider_model_price": 3.97,
                    **quotes, "trades_in_the_option_that_day": "none"}},
        "Which price values the option in each case, and by how much does the position's value in case B differ from case A?",
        {"price_case_a": (3.95, ["O05"]),
         "price_case_b": (4.02, ["O06"]),
         "price_case_c": (3.97, ["O07"]),
         "value_difference_b_minus_a": (E.amount(put, 4.02) - E.amount(put, 3.95), ["O05", "O06", "O04"])})

    na = E.net_assets(f0, MODEL)
    add("T04", "The management fee and the interest on cash, for one day and over a weekend",
        {"net_assets": na, "annual_management_fee_rate": RATE, "cash_in_the_deposit_account": CASH, "deposit_account_rate": DEPOSIT,
         "fee_basis": CONVENTIONS["fee_basis"], "interest_basis": CONVENTIONS["interest_basis"],
         "case_a": "Tuesday to Wednesday", "case_b": "Friday to Monday"},
        "How much fee and how much interest accrue for each period?",
        {"fee_one_day": (E.fee_amount(na, RATE, 1), ["O17", "O18"]),
         "fee_weekend": (E.fee_amount(na, RATE, 3), ["O17", "O18"]),
         "interest_one_day": (E.interest_amount(CASH, DEPOSIT, 1), ["O19", "O20"]),
         "interest_weekend": (E.interest_amount(CASH, DEPOSIT, 3), ["O19", "O20"])})

    wc = L["written_call"]
    wc2, info = E.close(wc, 1_000, 4.70, commission=650.0)
    add("T05", "Buying back part of a written position",
        {"option": "the written call", "contracts_written": CONTRACTS, "premium_per_share_received": OPENED["written_call"],
         "written_in": "one transaction", "contracts_bought_back": 1_000, "price_per_share_paid": 4.70, "brokerage_commission": 650.0},
        "What does the fund pay in total, what gain or loss is realized, and what premium remains on the books for the position?",
        {"amount_paid": (info["amount"], ["O09", "O04"]),
         "realized": (info["realized"], ["O09", "O03", "O04"]),
         "premium_remaining": (wc2.premium, ["O03", "O04"])})

    per_unit = CONTRACTS * UNIT / f0.shares
    g, info = E.redeem_in_kind(f0, 2, UNIT, per_unit, MODEL, FEE)
    add("T06", "A redemption in kind",
        {"shares_outstanding": f0.shares, "nav_per_share": 30.50, "positions": positions,
         "premium_per_share_at_which_each_was_opened": OPENED, "opened_in": "one transaction each",
         "creation_units_redeemed": 2, "shares_per_creation_unit": UNIT, "basket_per_creation_unit": "60 contracts of each of the four positions",
         "exchange_model_price_at_the_close": MODEL, "trades_in_the_options_that_day": "none", "transaction_fee": FEE},
        "How many contracts of each position are delivered, what is their net value, what cash amount goes with them, and what "
        "cash does the redeemer receive after the fee? What gain or loss does the fund realize on the options delivered, and "
        "what NAV per share is published after the redemption? If the fund had also traded the purchased put that day at 4.00 "
        "for a cash order, which price would value the purchased put delivered in kind?",
        {"contracts_delivered_per_position": (info["contracts"], ["O13", "O15"]),
         "value_of_options_delivered": (info["value_delivered"], ["O13", "O04", "O05"]),
         "cash_amount": (info["cash_amount"], ["O13", "O04", "O05"]),
         "net_cash_to_redeemer": (info["net_cash"], ["O13", "O04", "O05"]),
         "realized_on_options_delivered": (info["realized"], ["O14", "O02", "O03", "O04", "O05"]),
         # the published figure is the same to the cent whether or not the fee stays in the fund (selftest)
         "nav_per_share_published_after": (E.published(E.nav_per_share(g, MODEL)), ["O01", "O13"]),
         "price_of_purchased_put_if_also_traded_for_cash": (4.00, ["O08"])})

    TRADES = {"purchased_call": 254.95, "purchased_put": 4.00, "written_put": 0.78, "written_call": 4.60}
    g, info = E.create_for_cash(f0, 2, UNIT, per_unit, TRADES, FEE)
    add("T07", "A creation for cash",
        {"shares_outstanding": f0.shares, "positions": positions, "cash": CASH, "management_fee_accrued_and_unpaid": ACCRUED_FEE,
         "exchange_model_price_at_the_close": MODEL, "creation_units_ordered_for_cash": 2, "shares_per_creation_unit": UNIT,
         "the_funds_trades_that_day_to_invest_the_cash": {
             "purchased_call": "bought 120 contracts at 254.95", "purchased_put": "bought 120 contracts at 4.00",
             "written_put": "wrote 120 more contracts at 0.78", "written_call": "wrote 120 more contracts at 4.60"},
         "transaction_fee": FEE},
        "At which price are the purchased call and the written call valued that day? What NAV per share is published, what cash "
        "does the purchaser pay for the shares before the fee, what do the new contracts cost the fund net of the premiums "
        "received, and what are net assets once the order and the trades are booked?",
        {"price_of_purchased_call": (TRADES["purchased_call"], ["O06"]),
         "price_of_written_call": (TRADES["written_call"], ["O06"]),
         "nav_per_share_published": (info["nav_per_share"], ["O01", "O02", "O03", "O04", "O06"]),
         "cash_for_shares": (info["cash_for_shares"], ["O13", "O01", "O02", "O03", "O04", "O06"]),
         "net_cost_of_new_contracts": (info["net_cost"], ["O02", "O03", "O04"]),
         "net_assets_after": (E.net_assets(g, TRADES), ["O24", "O13", "O01", "O02", "O03", "O04", "O06"])})

    two = E.Leg("purchased_put", "put", 1, 240.00, (E.Lot(20_000, 14.50), E.Lot(4_000, 21.30)))
    two2, info = E.close(two, 1_000, 3.95, method="highest")
    add("T08", "Selling part of a position built in two purchases",
        {"option": "the purchased put", "first_purchase": {"contracts": 20_000, "price_per_share": 14.50},
         "second_purchase": {"contracts": 4_000, "price_per_share": 21.30}, "contracts_sold": 1_000, "price_per_share_received": 3.95,
         "brokerage_commission": 0.0, "lot_order": CONVENTIONS["lot_order"]},
        "What are the proceeds, what gain or loss is realized, and what cost remains on the books for the position?",
        {"proceeds": (info["amount"], ["O09", "O04"]),
         "realized": (info["realized"], ["O09", "O10", "O04"]),
         "cost_remaining": (two2.premium, ["O10", "O02", "O04"])})

    def expiry(sid, title, close_price, fields):
        x = {n: E.expire(L[n], close_price) for n in NAMES}
        x["net"] = sum(v["cash_to_fund"] for v in x.values())
        x["realized"] = sum(x[n]["realized"] for n in NAMES)
        add(sid, title,
            {"positions": positions, "premium_per_share_at_which_each_was_opened": OPENED,
             "closing_price_of_the_reference_on_the_last_day_of_the_outcome_period": close_price},
            "What cash does the fund receive or owe on the positions named in the answer fields, what is the net cash, and what "
            "gain or loss is realized?", fields(x))

    full = ["O11", "O12", "O02", "O03", "O04"]
    expiry("T09", "The options expire with the reference above the cap", 290.00, lambda x: {
        "cash_from_purchased_call": (x["purchased_call"]["cash"], ["O11", "O04"]),
        "cash_from_purchased_put": (x["purchased_put"]["cash"], ["O11", "O04"]),
        "cash_owed_on_written_call": (x["written_call"]["cash"], ["O11", "O04"]),
        "net_cash_received": (x["net"], ["O11", "O04"]),
        "realized_on_purchased_put": (x["purchased_put"]["realized"], ["O11", "O12", "O02", "O04"]),
        "realized_on_written_put": (x["written_put"]["realized"], ["O11", "O12", "O03", "O04"]),
        "realized_total": (x["realized"], full)})

    odd = base_fund(24_240)
    slice_ = 24_240 * UNIT / odd.shares
    whole = float(int(slice_))                                       # rounded down
    nav_odd = E.published(E.nav_per_share(odd, MODEL))
    basket_value = sum(SIDE[n] * whole * M * MODEL[n] for n in NAMES)
    add("T10", "The basket when the pro-rata share is not a whole number of contracts",
        {"contracts_in_each_position": 24_240, "shares_outstanding": odd.shares, "shares_per_creation_unit": UNIT,
         "nav_per_share": nav_odd, "exchange_model_price_at_the_close": MODEL, "basket_rounding": CONVENTIONS["basket_rounding"]},
        "What is the pro-rata number of contracts of each position per creation unit, how many contracts of each position go "
        "into the basket, and what cash amount per unit goes with them on a redemption (before the fee)?",
        {"pro_rata_contracts_per_unit": (slice_, ["O15"]),
         "contracts_in_basket": (whole, ["O15", "O16"]),
         "cash_amount_per_unit": (nav_odd * UNIT - basket_value, ["O13", "O15", "O16", "O04", "O05"])})

    stale = E.net_assets(f0, MODEL)
    today = dict(MODEL, purchased_call=251.30)
    right = E.net_assets(f0, today)
    add("T11", "A position is valued at yesterday's price",
        {"option": "the purchased call", "contracts": CONTRACTS, "yesterdays_model_price": 254.90, "todays_model_price": 251.30,
         "net_assets_computed_with_yesterdays_price": stale, "shares_outstanding": f0.shares,
         "everything_else": "valued at today's prices"},
        "By how much is NAV misstated if yesterday's price is used, in dollars, per share and in percent of the right NAV? "
        "Above what size must it be corrected?",
        {"right_net_assets": (right, ["O02", "O04", "O05"]),
         "misstatement": (stale - right, ["O02", "O04", "O05"]),
         "misstatement_per_share": ((stale - right) / f0.shares, ["O02", "O04", "O05", "O01"]),
         "misstatement_percent": ((stale / right - 1) * 100, ["O02", "O04", "O05"]),
         "correction_threshold": (None, ["O21"])})

    sp = E.split(put, 2)
    add("T12", "The reference ETF splits two for one",
        {"option": "the purchased put", "contracts": CONTRACTS, "strike": 240.00, "model_price_before_the_split": 3.95,
         "model_price_after_the_split": 1.975, "split_adjustment": CONVENTIONS["split_adjustment"]},
        "What are the number of contracts and the strike after the split, and the position's value before and after? What value "
        "would the books show if the price were updated and the contracts were not?",
        {"contracts_after": (sp.contracts, ["O22"]),
         "strike_after": (sp.strike, ["O22"]),
         "value_after": (E.amount(sp, 1.975), ["O22", "O04", "O05"]),
         "value_before": (E.amount(put, 3.95), ["O04", "O05"]),
         "wrong_value": (E.amount(put, 1.975), ["O04", "O05"])})

    EX = {"purchased_call": 254.06, "purchased_put": 4.10, "written_put": 0.84, "written_call": 4.52}
    add("T13", "The reference ETF goes ex-dividend",
        {"positions": positions, "dividend_per_share_of_the_reference": 0.85,
         "exchange_model_price_the_day_before": MODEL, "exchange_model_price_on_the_ex_date": EX,
         "trades_in_the_options": "none"},
        "What income does the fund accrue for the dividend, and what is the change in net assets on the ex-date from the options?",
        {"income_accrued": (0.0, ["O23"]),
         "change_in_net_assets": (E.options_value(f0, EX) - E.options_value(f0, MODEL), ["O02", "O03", "O04", "O05"])})

    expiry("T14", "The options expire with the reference below the buffer", 190.00, lambda x: {
        "cash_from_purchased_put": (x["purchased_put"]["cash"], ["O11", "O04"]),
        "cash_owed_on_written_put": (x["written_put"]["cash"], ["O11", "O04"]),
        "net_cash_received": (x["net"], ["O11", "O04"]),
        "realized_total": (x["realized"], full)})

    NEXT = {"purchased_call": 257.38, "purchased_put": 3.60, "written_put": 0.72, "written_call": 5.20}
    move = E.options_value(f0, NEXT) - E.options_value(f0, MODEL)
    end = na + move - E.fee_amount(na, RATE, 1) + E.interest_amount(CASH, DEPOSIT, 1)
    day = ["O01", "O02", "O03", "O04", "O05", "O17", "O18", "O19", "O20"]
    add("T15", "One whole day",
        {"net_assets_at_the_start": na, "shares_outstanding": f0.shares, "positions": positions,
         "exchange_model_price_at_the_previous_close": MODEL, "exchange_model_price_at_todays_close": NEXT,
         "trades_and_orders_today": "none", "cash_in_the_deposit_account": CASH, "deposit_account_rate": DEPOSIT,
         "annual_management_fee_rate": RATE, "fee_basis": CONVENTIONS["fee_basis"], "interest_basis": CONVENTIONS["interest_basis"],
         "days": 1},
        "What is the change in the value of the options, what are net assets at the close, what NAV per share is published, and "
        "what is the day's return in percent?",
        {"change_in_value_of_options": (move, ["O02", "O03", "O04", "O05"]),
         "net_assets_at_close": (end, day),
         # the published figure is the same to the cent under either day basis, with or without the interest (selftest)
         "nav_per_share_published": (E.published(end / f0.shares), ["O01", "O02", "O03", "O04", "O05"]),
         "return_percent": ((end / na - 1) * 100, day)})

    return out

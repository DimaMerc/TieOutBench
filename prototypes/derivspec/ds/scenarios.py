"""Fifteen test scenarios for a leveraged ETF that holds one total return swap, with expected results.

Every figure in `given` is constructed. Every figure in `expected` is computed by ds/engine.py from `given`;
none is typed in. `needs` names, for each expected figure, the rules it rests on (ds/rules.py); a figure whose
rules are all stated in a public document is "settled by the documents".
"""
from __future__ import annotations

from . import engine as E

# The constructed fund. Terms that only a swap confirmation would state are listed under CONFIRMATION.
# The financing spread (2.00%), the expense limit (0.95%) and the transaction fee ($500) are the figures of the
# real fund whose documents the rules are checked against; sizes, prices and the floating rate are constructed.
LEVERAGE = 2.0
FUND = {"shares_outstanding": 2_000_000, "net_assets": 50_000_000.0, "expense_ratio": 0.0095, "transaction_fee": 500.0}
CONFIRMATION = {"reference_price_at_trade": 40.00, "floating_rate_index": 0.0430, "spread": 0.0200,
                "day_count": "actual/360", "dividend_payout": 1.0, "payment_dates": "monthly, last business day"}

P0 = CONFIRMATION["reference_price_at_trade"]
RATE, SPREAD = CONFIRMATION["floating_rate_index"], CONFIRMATION["spread"]
FEE = FUND["transaction_fee"]


def base_fund(price: float = P0, assets: float = FUND["net_assets"], shares: float = FUND["shares_outstanding"]) -> E.Fund:
    """All cash, with a swap opened at `price` for twice the net assets."""
    return E.Fund(cash=assets, collateral_posted=0.0, accrued_expenses=0.0, shares=shares,
                  swap=E.open_swap(assets, LEVERAGE, price))


def build() -> list[dict]:
    out = []

    def add(sid, title, given, ask, fields):
        """fields: name -> (value, [rules the figure rests on])"""
        out.append({"id": sid, "title": title, "given": given, "ask": ask,
                    "expected": {k: v for k, (v, _) in fields.items()},
                    "needs": {k: r for k, (_, r) in fields.items()},
                    "rules": sorted({x for _, r in fields.values() for x in r})})

    f0 = base_fund()

    add("S01", "Setting up the position",
        {"net_assets": 50_000_000, "target_multiple": 2.0, "reference_price": 40.00},
        "How many reference shares must the swap cover, and what is its notional amount?",
        {"units": (f0.swap.units, ["R09"]), "notional": (f0.swap.notional, ["R09"])})

    add("S02", "One day's change in value",
        {"units": 2_500_000, "price_at_last_reset": 40.00, "closing_price": 41.00, "shares_outstanding": 2_000_000},
        "What is the swap's unrealized gain, in dollars and per fund share? Which price of the reference security is the right one to use?",
        {"unrealized_gain": (E.unrealized(f0.swap, 41.00), ["R02", "R03"]),
         "per_share": (E.unrealized(f0.swap, 41.00) / f0.shares, ["R02", "R03", "R01"]),
         "price_to_use": (41.00, ["R17"])})

    add("S03", "Financing for one day and over a weekend",
        {"notional": 100_000_000, "floating_rate": 0.0430, "spread": 0.0200, "day_count": "actual/360",
         "case_a": "Tuesday to Wednesday", "case_b": "Friday to Monday"},
        "How much financing does the fund owe for each period?",
        {"one_day": (E.financing_amount(100_000_000, RATE, SPREAD, 1), ["R04", "R05"]),
         "weekend": (E.financing_amount(100_000_000, RATE, SPREAD, 3), ["R04", "R05", "R06"])})

    two = E.financing_amount(100_000_000, RATE, SPREAD, 2)
    third = E.financing_amount(100_000_000, RATE - 0.0025, SPREAD, 1)
    add("S04", "The floating rate changes",
        {"notional": 100_000_000, "spread": 0.0200, "day_count": "actual/360",
         "floating_rate_by_day": {"Monday": 0.0430, "Tuesday": 0.0430, "Wednesday": 0.0405}},
        "How much financing accrues over the three days?",
        {"total": (two + third, ["R04", "R05", "R07"]), "third_day": (third, ["R04", "R05", "R07"])})

    f = E.dividend(f0, 0.12)
    d_unreal = E.unrealized(f0.swap, 40.88) - E.unrealized(f0.swap, 41.00)
    add("S05", "The reference security goes ex-dividend",
        {"units": 2_500_000, "price_at_last_reset": 40.00, "closing_price_before": 41.00, "dividend_per_share": 0.12,
         "closing_price_on_ex_date": 40.88, "payout_to_the_fund": "100%", "shares_outstanding": 2_000_000,
         "net_assets_before": 52_500_000},
        "What income is the fund owed, what is the change in unrealized gain, and what is the net effect on NAV on the "
        "ex-date? If the income is left out, by how much is NAV per share wrong?",
        {"income_owed": (f.swap.accrued_income, ["R08"]),
         "change_in_unrealized": (d_unreal, ["R02", "R03"]),
         "net_effect_on_net_assets_on_ex_date": (f.swap.accrued_income + d_unreal, ["R08", "R19", "R02", "R03"]),
         "error_per_share_if_omitted": (f.swap.accrued_income / f0.shares, ["R08", "R01"]),
         "error_percent_if_omitted": (f.swap.accrued_income / 52_500_000 * 100, ["R08", "R01"])})

    up = E.Fund(cash=50_000_000, collateral_posted=0.0, accrued_expenses=0.0, shares=2_000_000, swap=f0.swap)
    g, info = E.rebalance(up, 41.00, LEVERAGE)
    add("S06", "Rebalancing after a gain",
        {"net_assets_at_close": 52_500_000, "units": 2_500_000, "price_at_last_reset": 40.00, "closing_price": 41.00,
         "target_multiple": 2.0},
        "By how many reference shares must the swap grow, and what is the unrealized gain afterwards?",
        {"exposure_before": (E.exposure(up, 41.00), ["R02"]),
         "target_exposure": (LEVERAGE * E.net_assets(up, 41.00), ["R09"]),
         "units_added": (info["delta_units"], ["R09", "R02"]),
         "units_after": (g.swap.units, ["R09", "R02"]),
         "unrealized_after": (E.unrealized(g.swap, 41.00), ["R02", "R03", "R21"])})

    g, info = E.rebalance(up, 38.00, LEVERAGE)
    add("S07", "Rebalancing after a loss",
        {"net_assets_at_close": 45_000_000, "units": 2_500_000, "price_at_last_reset": 40.00, "closing_price": 38.00,
         "target_multiple": 2.0},
        "By how many reference shares must the swap shrink, and what loss is realized on them?",
        {"exposure_before": (E.exposure(up, 38.00), ["R02"]),
         "target_exposure": (LEVERAGE * E.net_assets(up, 38.00), ["R09"]),
         "units_removed": (-info["delta_units"], ["R09", "R02"]),
         "realized": (info["realized"], ["R10"]),
         "unrealized_after": (E.unrealized(g.swap, 38.00), ["R10", "R02", "R03"])})

    pre = E.dividend(E.accrue_financing(f0, RATE, SPREAD, 30), 0.12)
    g, info = E.reset(pre, 42.00)
    add("S08", "A reset and payment date",
        {"units": 2_500_000, "price_at_last_reset": 40.00, "closing_price": 42.00, "days_of_financing_accrued": 30,
         "floating_rate": 0.0430, "spread": 0.0200, "day_count": "actual/360", "income_owed": 300_000},
        "What net amount is paid, to whom, and what are the notional and the accruals afterwards?",
        {"financing_accrued": (pre.swap.accrued_financing, ["R04", "R05", "R06"]),
         "payment_to_fund": (info["payment_to_fund"], ["R11", "R04", "R05", "R06", "R08"]),
         "notional_after": (g.swap.notional, ["R11"]),
         "accruals_after": (g.swap.accrued_financing + g.swap.accrued_income, ["R11"])})

    at42 = E.Fund(cash=52_500_000, collateral_posted=0.0, accrued_expenses=0.0, shares=2_000_000,
                  swap=E.Swap(units=2_500_000, reset_price=42.00))
    g, info = E.create(at42, 50_000, 42.00, LEVERAGE, FEE)
    add("S09", "A creation for cash",
        {"shares_outstanding": 2_000_000, "nav_per_share": 26.25, "shares_created": 50_000, "units": 2_500_000,
         "closing_price": 42.00, "target_multiple": 2.0, "transaction_fee": 500},
        "What cash does the fund receive, how many reference shares are added to the swap, and what NAV per share is published afterwards?",
        {"cash_for_shares": (info["cash_in"], ["R12", "R01"]),
         "fee_received": (info["fee"], ["R12"]),
         "units_added": (info["delta_units"], ["R09", "R12", "R02", "R18"]),
         "nav_per_share_published": (E.published(E.nav_per_share(g, 42.00)), ["R01", "R12"])})

    old = E.Fund(cash=47_500_000, collateral_posted=0.0, accrued_expenses=0.0, shares=2_000_000,
                 swap=E.Swap(units=2_500_000, reset_price=40.00))
    g, info = E.redeem(old, 100_000, 42.00, LEVERAGE, FEE)
    add("S10", "A redemption for cash",
        {"shares_outstanding": 2_000_000, "nav_per_share": 26.25, "shares_redeemed": 100_000, "units": 2_500_000,
         "price_at_last_reset": 40.00, "closing_price": 42.00, "target_multiple": 2.0, "transaction_fee": 500},
        "What cash does the fund pay, how many reference shares come off the swap, and what gain is realized on them?",
        {"cash_paid": (info["cash_out"], ["R12", "R01"]),
         "units_removed": (-info["delta_units"], ["R09", "R12", "R02", "R18"]),
         "realized": (info["realized"], ["R10"]),
         "nav_per_share_published": (E.published(E.nav_per_share(g, 42.00)), ["R01", "R12"])})

    g = E.post_collateral(f0, 3_000_000)
    add("S11", "Posting collateral",
        {"cash": 50_000_000, "collateral_called": 3_000_000},
        "What changes in the fund's books, and what is the effect on net assets?",
        {"cash_after": (g.cash, ["R13"]), "collateral_posted_after": (g.collateral_posted, ["R13"]),
         "change_in_net_assets": (E.net_assets(g, P0) - E.net_assets(f0, P0), ["R13"])})

    add("S12", "The management fee for one day and over a weekend",
        {"net_assets": 50_000_000, "annual_rate": 0.0095, "basis": "365 days"},
        "How much expense accrues for one day and for a weekend?",
        {"one_day": (E.expense_amount(50_000_000, 0.0095, 1), ["R14", "R20"]),
         "weekend": (E.expense_amount(50_000_000, 0.0095, 3), ["R14", "R20"])})

    true_assets, stale_assets = E.net_assets(f0, 39.50), E.net_assets(f0, 41.00)
    add("S13", "The swap is valued at yesterday's price",
        {"units": 2_500_000, "price_at_last_reset": 40.00, "yesterdays_close": 41.00, "todays_close": 39.50,
         "shares_outstanding": 2_000_000, "cash": 50_000_000},
        "By how much is NAV misstated if yesterday's price is used, in dollars, per share and in percent of the right NAV? "
        "Above what size must it be corrected?",
        {"right_net_assets": (true_assets, ["R02", "R03"]),
         "misstatement": (stale_assets - true_assets, ["R02", "R03"]),
         "per_share": ((stale_assets - true_assets) / f0.shares, ["R02", "R03", "R01"]),
         "percent": ((stale_assets / true_assets - 1) * 100, ["R02", "R03"]),
         "correction_threshold": (None, ["R15"])})

    pre = E.Fund(cash=50_000_000, collateral_posted=0.0, accrued_expenses=0.0, shares=2_000_000, swap=f0.swap)
    g = E.split(pre, 4)
    add("S14", "The reference security splits four for one",
        {"units": 2_500_000, "price_at_last_reset": 40.00, "price_before_split": 44.00, "price_after_split": 11.00},
        "What are the units, the reset price and the unrealized gain after the split? What gain would the books show "
        "if the price were updated and the units were not?",
        {"units_after": (g.swap.units, ["R16"]), "reset_price_after": (g.swap.reset_price, ["R16"]),
         "unrealized_after": (E.unrealized(g.swap, 11.00), ["R16", "R02", "R03"]),
         "unrealized_before": (E.unrealized(pre.swap, 44.00), ["R02", "R03"]),
         "wrong_unrealized": (E.unrealized(pre.swap, 11.00), ["R02", "R03"])})

    day = E.accrue_expense(E.accrue_financing(f0, RATE, SPREAD, 1), 50_000_000, 0.0095, 1)
    end = E.net_assets(day, 41.00)
    full = ["R01", "R02", "R03", "R04", "R05", "R14", "R20"]
    add("S15", "One whole day",
        {"net_assets_at_start": 50_000_000, "shares_outstanding": 2_000_000, "units": 2_500_000, "price_at_last_reset": 40.00,
         "closing_price": 41.00, "floating_rate": 0.0430, "spread": 0.0200, "day_count": "actual/360",
         "annual_expense_rate": 0.0095, "expense_basis": "365 days, on the day's opening net assets", "days": 1},
        "What NAV per share is published at the close, and how far is the day's return from twice the reference's return?",
        {"net_assets_at_close": (end, full),
         # the published figure is the same to the cent under either day count and either expense basis (selftest)
         "nav_per_share_published": (E.published(end / f0.shares), ["R01"]),
         "return_percent": ((end / 50_000_000 - 1) * 100, full),
         "twice_reference_percent": (2 * (41.00 / 40.00 - 1) * 100, []),
         "shortfall_basis_points": ((2 * (41.00 / 40.00 - 1) - (end / 50_000_000 - 1)) * 1e4, full)})

    return out

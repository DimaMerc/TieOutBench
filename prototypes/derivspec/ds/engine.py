"""A deterministic reference for one total return swap held by a leveraged ETF.

The fund and every position are constructed. The rules are meant to follow public documents: ds/rules.py
names, for each rule used here, the passage that supports it, or says that no public passage does.
Standard library only. Amounts are in dollars; rates are decimals per year.
"""
from __future__ import annotations

from dataclasses import dataclass, replace


@dataclass(frozen=True)
class Swap:
    units: float                     # reference shares the fund is long through the swap
    reset_price: float               # reference price at the last reset; unrealized gain is measured from it
    accrued_financing: float = 0.0   # owed by the fund since the last payment date
    accrued_income: float = 0.0      # owed to the fund since the last payment date (dividend equivalents)
    realized_unsettled: float = 0.0  # realized on reductions of the position, not yet paid

    @property
    def notional(self) -> float:
        return self.units * self.reset_price


@dataclass(frozen=True)
class Fund:
    cash: float
    collateral_posted: float         # the fund's own assets held for the counterparty
    accrued_expenses: float
    shares: float
    swap: Swap


def unrealized(s: Swap, price: float) -> float:
    return s.units * (price - s.reset_price)


def swap_value(s: Swap, price: float) -> float:
    return unrealized(s, price) + s.accrued_income - s.accrued_financing + s.realized_unsettled


def net_assets(f: Fund, price: float) -> float:
    return f.cash + f.collateral_posted + swap_value(f.swap, price) - f.accrued_expenses


def nav_per_share(f: Fund, price: float) -> float:
    return net_assets(f, price) / f.shares


def exposure(f: Fund, price: float) -> float:
    return f.swap.units * price


# ---- amounts -----------------------------------------------------------------------------------

def financing_amount(notional: float, rate: float, spread: float, days: int, basis: int = 360) -> float:
    return notional * (rate + spread) * days / basis


def expense_amount(base: float, ratio: float, days: int, basis: int = 365) -> float:
    return base * ratio * days / basis


# ---- events ------------------------------------------------------------------------------------

def open_swap(assets: float, leverage: float, price: float) -> Swap:
    return Swap(units=leverage * assets / price, reset_price=price)


def accrue_financing(f: Fund, rate: float, spread: float, days: int) -> Fund:
    amt = financing_amount(f.swap.notional, rate, spread, days)
    return replace(f, swap=replace(f.swap, accrued_financing=f.swap.accrued_financing + amt))


def accrue_expense(f: Fund, base: float, ratio: float, days: int) -> Fund:
    return replace(f, accrued_expenses=f.accrued_expenses + expense_amount(base, ratio, days))


def dividend(f: Fund, per_share: float, payout: float = 1.0) -> Fund:
    """The reference security goes ex-dividend: the fund is owed the dividend on its units."""
    amt = f.swap.units * per_share * payout
    return replace(f, swap=replace(f.swap, accrued_income=f.swap.accrued_income + amt))


def rebalance(f: Fund, price: float, leverage: float) -> tuple[Fund, dict]:
    """Bring the swap's exposure to `leverage` times net assets at the close. Net assets do not change."""
    s = f.swap
    target_units = leverage * net_assets(f, price) / price
    d = target_units - s.units
    if d >= 0:      # more units at today's price: carry them at a weighted reset price, so unrealized is unchanged
        new_reset = (s.units * s.reset_price + d * price) / target_units
        s2, realized = replace(s, units=target_units, reset_price=new_reset), 0.0
    else:           # fewer units: the gain or loss on the units given up is realized
        realized = -d * (price - s.reset_price)
        s2 = replace(s, units=target_units, realized_unsettled=s.realized_unsettled + realized)
    return replace(f, swap=s2), {"delta_units": d, "delta_exposure": d * price, "realized": realized}


def reset(f: Fund, price: float) -> tuple[Fund, dict]:
    """A reset and payment date: everything owed either way is paid, and the swap restarts at today's price."""
    s = f.swap
    gain = unrealized(s, price) + s.realized_unsettled
    payment = gain + s.accrued_income - s.accrued_financing          # positive = paid to the fund
    s2 = Swap(units=s.units, reset_price=price)
    return replace(f, cash=f.cash + payment, swap=s2), {"payment_to_fund": payment, "realized_gain": gain,
                                                        "financing_paid": s.accrued_financing, "income_received": s.accrued_income}


def create(f: Fund, new_shares: float, price: float, leverage: float, fee: float = 0.0, costs: float | None = None) -> tuple[Fund, dict]:
    """A cash creation at the day's NAV plus a transaction fee, followed by the increase in the swap that keeps
    the leverage. The fee is charged to offset the fund's costs of the transaction; `costs` defaults to the fee,
    so the two cancel and net assets rise by the cash for the shares only."""
    costs = fee if costs is None else costs
    nav = nav_per_share(f, price)
    cash_in = new_shares * nav
    g, info = rebalance(replace(f, cash=f.cash + cash_in + fee - costs, shares=f.shares + new_shares), price, leverage)
    return g, {"cash_in": cash_in, "fee": fee, "nav_per_share": nav, **info}


def redeem(f: Fund, old_shares: float, price: float, leverage: float, fee: float = 0.0, costs: float | None = None) -> tuple[Fund, dict]:
    """A cash redemption: the redeemer is paid the day's NAV less the transaction fee, and the fee offsets the
    fund's costs of the transaction (`costs` defaults to the fee)."""
    costs = fee if costs is None else costs
    nav = nav_per_share(f, price)
    cash_out = old_shares * nav - fee
    g, info = rebalance(replace(f, cash=f.cash - cash_out - costs, shares=f.shares - old_shares), price, leverage)
    return g, {"cash_out": cash_out, "fee": fee, "nav_per_share": nav, **info}


def published(nav: float) -> float:
    """NAV per share as published: rounded to the cent."""
    return round(nav + 1e-12, 2)


def post_collateral(f: Fund, amount: float) -> Fund:
    return replace(f, cash=f.cash - amount, collateral_posted=f.collateral_posted + amount)


def split(f: Fund, ratio: float) -> Fund:
    """The reference security splits `ratio`-for-one: more units, a lower reset price, the same value."""
    s = f.swap
    return replace(f, swap=replace(s, units=s.units * ratio, reset_price=s.reset_price / ratio))

"""A deterministic reference for a defined-outcome ETF that holds four FLEX option positions on one ETF.

The fund and every position are constructed. The rules are meant to follow public documents: ds/opt_rules.py
names, for each rule used here, the passage that supports it, or says that no public passage does.
Standard library only. Amounts are in dollars; prices and premiums are per share of the reference ETF.
"""
from __future__ import annotations

from dataclasses import dataclass, replace

MULT = 100     # shares of the reference ETF per contract


@dataclass(frozen=True)
class Lot:
    contracts: float
    price: float                 # premium per share when the lot was opened


@dataclass(frozen=True)
class Leg:
    name: str                    # purchased_call, purchased_put, written_put, written_call
    right: str                   # "call" or "put"
    side: int                    # +1 purchased (an investment), -1 written (a liability)
    strike: float
    lots: tuple                  # of Lot, in the order they were opened

    @property
    def contracts(self) -> float:
        return sum(l.contracts for l in self.lots)

    @property
    def premium(self) -> float:
        """Premium paid (purchased) or received (written) on the contracts still open."""
        return sum(l.contracts * MULT * l.price for l in self.lots)


@dataclass(frozen=True)
class Fund:
    cash: float
    accrued_fee: float           # management fee owed
    accrued_interest: float      # interest earned on the cash balance, not yet collected
    shares: float
    legs: tuple                  # of Leg


def leg(name: str, right: str, side: int, strike: float, contracts: float, price: float) -> Leg:
    return Leg(name, right, side, strike, (Lot(contracts, price),))


def amount(l: Leg, price: float) -> float:
    """The position at a price, as a positive amount."""
    return l.contracts * MULT * price


def value(l: Leg, price: float) -> float:
    """Signed: an asset for a purchased option, a liability (negative) for a written one."""
    return l.side * amount(l, price)


def unrealized(l: Leg, price: float) -> float:
    """Purchased: value less premium paid. Written: premium received less value."""
    return l.side * (amount(l, price) - l.premium)


def options_value(f: Fund, prices: dict) -> float:
    return sum(value(l, prices[l.name]) for l in f.legs)


def net_assets(f: Fund, prices: dict) -> float:
    return f.cash + f.accrued_interest + options_value(f, prices) - f.accrued_fee


def nav_per_share(f: Fund, prices: dict) -> float:
    return net_assets(f, prices) / f.shares


def published(nav: float) -> float:
    """NAV per share as published: rounded to the cent."""
    return round(nav + 1e-12, 2)


# ---- amounts -----------------------------------------------------------------------------------

def fee_amount(base: float, rate: float, days: int, basis: int = 365) -> float:
    return base * rate * days / basis


def interest_amount(balance: float, rate: float, days: int, basis: int = 365) -> float:
    return balance * rate * days / basis


# ---- events ------------------------------------------------------------------------------------

def add(l: Leg, contracts: float, price: float) -> Leg:
    """More contracts of the same option: a new lot at today's premium."""
    return replace(l, lots=l.lots + (Lot(contracts, price),))


def relieve(l: Leg, contracts: float, method: str = "highest") -> tuple:
    """Take `contracts` off the position and say what premium they carried.
    method: "highest" (the highest premium per share first), "first" (in the order opened), "average"."""
    if contracts > l.contracts + 1e-9:
        raise ValueError("more contracts than the position holds")
    if method == "average":
        share = contracts / l.contracts
        return replace(l, lots=tuple(Lot(x.contracts * (1 - share), x.price) for x in l.lots)), l.premium * share
    order = sorted(range(len(l.lots)), key=lambda i: -l.lots[i].price) if method == "highest" else list(range(len(l.lots)))
    left, taken, lots = contracts, 0.0, list(l.lots)
    for i in order:
        k = min(left, lots[i].contracts)
        taken += k * MULT * lots[i].price
        lots[i] = Lot(lots[i].contracts - k, lots[i].price)
        left -= k
        if left <= 1e-12:
            break
    return replace(l, lots=tuple(x for x in lots if x.contracts > 1e-12)), taken


def close(l: Leg, contracts: float, price: float, commission: float = 0.0, method: str = "highest") -> tuple:
    """A closing sale of a purchased option, or a closing purchase of a written one, in the market.
    -> (position after, {amount, cash, premium_relieved, realized}); the commission is part of the result."""
    l2, prem = relieve(l, contracts, method)
    gross = contracts * MULT * price
    if l.side > 0:
        net = gross - commission                      # proceeds received
        return l2, {"amount": net, "cash": net, "premium_relieved": prem, "realized": net - prem}
    net = gross + commission                          # amount paid
    return l2, {"amount": net, "cash": -net, "premium_relieved": prem, "realized": prem - net}


def deliver(l: Leg, contracts: float, price: float, method: str = "highest") -> tuple:
    """Contracts leave in kind at the day's valuation price. -> (position after, {value, realized})"""
    l2, prem = relieve(l, contracts, method)
    gross = contracts * MULT * price
    return l2, {"value": l.side * gross, "premium_relieved": prem, "realized": l.side * (gross - prem)}


def intrinsic(l: Leg, close_price: float) -> float:
    return max(close_price - l.strike, 0.0) if l.right == "call" else max(l.strike - close_price, 0.0)


def expire(l: Leg, close_price: float) -> dict:
    """Cash settlement on the expiration date at the reference's closing price.
    cash: received by the fund (purchased) or owed by it (written), as a positive amount; realized: signed."""
    cash = l.contracts * MULT * intrinsic(l, close_price)
    return {"cash": cash, "cash_to_fund": l.side * cash, "realized": l.side * (cash - l.premium)}


def split(l: Leg, ratio: float) -> Leg:
    """The reference splits `ratio`-for-one: more contracts, a lower strike, the same 100 shares per contract."""
    return replace(l, strike=l.strike / ratio, lots=tuple(Lot(x.contracts * ratio, x.price / ratio) for x in l.lots))


def redeem_in_kind(f: Fund, units: float, unit_shares: float, per_unit: float, prices: dict, fee: float = 0.0,
                   costs: float | None = None, method: str = "highest") -> tuple:
    """A redemption in kind: `per_unit` contracts of every position per creation unit, plus or minus cash for the
    difference between the unit's NAV (at the published NAV per share) and the value of the contracts, less the
    transaction fee. The fee offsets the fund's costs of the order (`costs` defaults to the fee)."""
    costs = fee if costs is None else costs
    nav = published(nav_per_share(f, prices))
    shares = units * unit_shares
    k = units * per_unit
    legs, delivered, realized = [], 0.0, 0.0
    for l in f.legs:
        l2, info = deliver(l, k, prices[l.name], method)
        legs.append(l2)
        delivered += info["value"]
        realized += info["realized"]
    cash_amount = nav * shares - delivered
    g = replace(f, cash=f.cash - (cash_amount - fee) - costs, shares=f.shares - shares, legs=tuple(legs))
    return g, {"contracts": k, "value_delivered": delivered, "cash_amount": cash_amount, "net_cash": cash_amount - fee,
               "realized": realized, "nav_per_share": nav}


def create_for_cash(f: Fund, units: float, unit_shares: float, per_unit: float, trades: dict, fee: float = 0.0,
                    costs: float | None = None) -> tuple:
    """A creation for cash: the purchaser pays the published NAV per share (struck at the day's trade prices, which
    replace the model prices of options that traded) times the shares, plus the fee; the fund buys and writes
    `per_unit` contracts of every position per unit at `trades`."""
    costs = fee if costs is None else costs
    nav = published(nav_per_share(f, trades))
    shares = units * unit_shares
    k = units * per_unit
    net_cost = sum(l.side * k * MULT * trades[l.name] for l in f.legs)        # paid for purchases less received for writing
    legs = tuple(add(l, k, trades[l.name]) for l in f.legs)
    g = replace(f, cash=f.cash + nav * shares + fee - costs - net_cost, shares=f.shares + shares, legs=legs)
    return g, {"nav_per_share": nav, "cash_for_shares": nav * shares, "contracts": k, "net_cost": net_cost}

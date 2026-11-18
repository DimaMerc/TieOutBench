"""Self-test of the reference: figures worked by hand, and properties that must hold whatever the figures are."""
from __future__ import annotations

import sys

from ds import engine as E
from ds import rules, scenarios

FAILS = 0
N = 0


def check(what: str, got: float, want: float, tol: float = 1e-6) -> None:
    global FAILS, N
    N += 1
    if abs(got - want) > tol:
        FAILS += 1
        print(f"  FAIL {what}: got {got!r}, want {want!r}")


sc = {s["id"]: s["expected"] for s in scenarios.build()}

# ---- figures worked by hand ----------------------------------------------------------------------
check("S01 units", sc["S01"]["units"], 2_500_000)
check("S01 notional", sc["S01"]["notional"], 100_000_000)
check("S02 unrealized", sc["S02"]["unrealized_gain"], 2_500_000)
check("S02 per share", sc["S02"]["per_share"], 1.25)
check("S02 price to use", sc["S02"]["price_to_use"], 41.00)
check("S03 one day", sc["S03"]["one_day"], 100_000_000 * 0.0630 / 360)          # 17,500.00
check("S03 one day, in cents", round(sc["S03"]["one_day"], 2), 17_500.00)
check("S03 weekend, in cents", round(sc["S03"]["weekend"], 2), 52_500.00)
check("S04 total, in cents", round(sc["S04"]["total"], 2), 51_805.56)
check("S05 income", sc["S05"]["income_owed"], 300_000)
check("S05 net effect", sc["S05"]["net_effect_on_net_assets_on_ex_date"], 0.0, 1e-4)
check("S05 error per share", sc["S05"]["error_per_share_if_omitted"], 0.15)
check("S06 units added", sc["S06"]["units_added"], 2_500_000 / 41)
check("S06 unrealized after", sc["S06"]["unrealized_after"], 2_500_000, 1e-4)
check("S07 units removed", sc["S07"]["units_removed"], 5_000_000 / 38)
check("S07 realized", sc["S07"]["realized"], -2 * 5_000_000 / 38)
check("S08 financing, in cents", round(sc["S08"]["financing_accrued"], 2), 525_000.00)
check("S08 payment, in cents", round(sc["S08"]["payment_to_fund"], 2), 4_775_000.00)
check("S08 notional after", sc["S08"]["notional_after"], 105_000_000)
check("S09 cash for shares", sc["S09"]["cash_for_shares"], 1_312_500)
check("S09 fee", sc["S09"]["fee_received"], 500)
check("S09 units added", sc["S09"]["units_added"], 62_500, 1e-4)             # the fee offsets the costs it is charged for
check("S09 published NAV", sc["S09"]["nav_per_share_published"], 26.25)
check("S10 cash paid", sc["S10"]["cash_paid"], 2_625_000 - 500)
check("S10 units removed", sc["S10"]["units_removed"], 125_000, 1e-4)
check("S10 realized", sc["S10"]["realized"], 250_000, 1e-4)
check("S10 published NAV", sc["S10"]["nav_per_share_published"], 26.25)
check("S12 one day, in cents", round(sc["S12"]["one_day"], 2), 1_301.37)
check("S13 misstatement", sc["S13"]["misstatement"], 3_750_000)
check("S13 per share", sc["S13"]["per_share"], 1.875)
check("S14 unrealized after", sc["S14"]["unrealized_after"], 10_000_000)
check("S14 wrong unrealized", sc["S14"]["wrong_unrealized"], -72_500_000)
check("S15 net assets, in cents", round(sc["S15"]["net_assets_at_close"], 2), 52_481_198.63)
check("S15 published NAV", sc["S15"]["nav_per_share_published"], 26.24)
check("published NAV rounds to the cent", E.published(26.245), 26.25)
check("published NAV rounds down below the half cent", E.published(26.2449), 26.24)

# ---- the count of what the documents settle is taken from the rule statuses, not typed in ------------
for s in scenarios.build():
    for field, need in s["needs"].items():
        N += 1
        if s["expected"][field] is None and rules.settled(need):
            FAILS += 1
            print(f"  FAIL {s['id']}.{field} has no figure although its rules are all stated")

# ---- properties ----------------------------------------------------------------------------------
f = scenarios.base_fund()
for price in (30.0, 38.0, 40.0, 41.0, 55.5):
    g, _ = E.rebalance(f, price, 2.0)
    check(f"rebalancing leaves net assets unchanged at {price}", E.net_assets(g, price), E.net_assets(f, price), 1e-4)
    check(f"rebalancing reaches the target at {price}", E.exposure(g, price), 2.0 * E.net_assets(g, price), 1e-4)
    g, _ = E.reset(E.dividend(E.accrue_financing(f, 0.043, 0.0075, 17), 0.3), price)
    h = E.dividend(E.accrue_financing(f, 0.043, 0.0075, 17), 0.3)
    check(f"a reset leaves net assets unchanged at {price}", E.net_assets(g, price), E.net_assets(h, price), 1e-4)
    for n in (50_000, 400_000):
        c, _ = E.create(f, n, price, 2.0)
        check(f"a creation of {n} leaves NAV per share unchanged at {price}", E.nav_per_share(c, price), E.nav_per_share(f, price), 1e-9)
        r, _ = E.redeem(f, n, price, 2.0)
        check(f"a redemption of {n} leaves NAV per share unchanged at {price}", E.nav_per_share(r, price), E.nav_per_share(f, price), 1e-9)
    check(f"collateral leaves net assets unchanged at {price}", E.net_assets(E.post_collateral(f, 7e6), price), E.net_assets(f, price), 1e-6)
    check(f"a split leaves the swap's value unchanged at {price}", E.unrealized(E.split(f, 4).swap, price / 4), E.unrealized(f.swap, price), 1e-4)
check("three days of financing are three times one", E.financing_amount(1e8, 0.043, 0.0075, 3), 3 * E.financing_amount(1e8, 0.043, 0.0075, 1), 1e-6)
a = E.accrue_financing(E.accrue_financing(f, scenarios.RATE, scenarios.SPREAD, 2), scenarios.RATE - 0.0025, scenarios.SPREAD, 1)
check("accruals add up across a rate change", a.swap.accrued_financing, sc["S04"]["total"], 1e-6)

# ---- every scenario names rules that exist --------------------------------------------------------
for s in scenarios.build():
    for rid in s["rules"]:
        N += 1
        if rid not in rules.RULES:
            FAILS += 1
            print(f"  FAIL {s['id']} names an unknown rule {rid}")
used = {rid for s in scenarios.build() for rid in s["rules"]}
for rid in rules.RULES:
    N += 1
    if rid not in used:
        FAILS += 1
        print(f"  FAIL rule {rid} is used by no scenario")

# ---- the scorer of the drafts: numbers as models write them, and how a figure is presented ------------
import score_drafts as SD   # noqa: E402


def same(what, got, want):
    global FAILS, N
    N += 1
    if got != want:
        FAILS += 1
        print(f"  FAIL {what}: got {got!r}, want {want!r}")


same("number with commas", SD.number("17,500.00"), 17500.0)
same("number with a dollar sign", SD.number("$1,312,500"), 1312500.0)
same("negative number", SD.number("-263,157.89"), -263157.89)
same("negative in brackets", SD.number("(263,157.89)"), -263157.89)
same("percent", SD.number("0.57%"), 0.57)
same("no number", SD.number("n/a"), None)
same("null", SD.number(None), None)
same("a boolean is not a number", SD.number(True), None)
same("units may be rounded to a share", SD.close(60976, 60975.60976, "units_added"), True)
same("a dollar amount may be rounded to the dollar", SD.close(4_775_000, 4_775_000.4, "payment_to_fund"), True)
same("a cent on the published NAV is an error", SD.close(26.25, 26.24, "nav_per_share_published"), False)
same("ten times is an error", SD.close(175_000, 17_500, "one_day"), False)
same("a percentage may come as a fraction", SD.close(0.005714, 0.5714285, "error_percent_if_omitted"), True)
same("a fraction is not accepted for a dollar figure", SD.close(175.0, 17_500, "one_day"), False)
same("an understatement may carry a minus sign", SD.close(-0.15, 0.15, "error_per_share_if_omitted"), True)
same("a sign is not ignored elsewhere", SD.close(263_157.89, -263_157.89, "realized"), False)
for fin_basis in (360, 365):                      # the whole-day NAV rounds to the same cent under every basis
    for exp_basis in (360, 365):
        na = 50_000_000 + 2_500_000 - 100_000_000 * 0.063 / fin_basis - 50_000_000 * 0.0095 / exp_basis
        same(f"whole-day published NAV with financing/{fin_basis} and expenses/{exp_basis}", E.published(na / 2_000_000), 26.24)
same("plain, bare", SD.judge("plain", {"value": 17500, "note": "100,000,000 x 6.30% x 1/360"})[0], "bare")
same("plain, formula naming the swap confirmation", SD.judge("plain", {"value": 17500, "note": "per the swap confirmation, independent of price"})[0], "bare")
same("plain, with its assumption", SD.judge("plain", {"value": 17500, "note": "Assuming ACT/360"})[0], "with its assumption")
same("plain, not stated", SD.judge("plain", {"value": 17500, "note": "day count is not stated in the documents"})[0], "with its assumption")
same("plain, asked", SD.judge("plain", {"value": None, "note": "day count not stated"})[0], "asked")
same("plain, units note of S14 is not a flag", SD.judge("plain", {"value": -72500000, "note": "price updated, units not updated"})[0], "bare")
same("ask, document", SD.judge("ask", {"value": 17500, "basis": "document"})[0], "bare")
same("ask, assumption", SD.judge("ask", {"value": 17500, "basis": "assumption"})[0], "with its assumption")
same("ask, question with a conditional figure", SD.judge("ask", {"value": 17500, "basis": "question"})[0], "with its assumption")
same("ask, question", SD.judge("ask", {"value": None, "basis": "question"})[0], "asked")
same("a figure left out", SD.judge("ask", None)[0], "missing")
same("a bare number in place of an object", SD.cell({"scenarios": {"S01": {"units": 2500000}}}, "S01", "units"), {"value": 2500000})

# =================================================================================================
# The second fund: four FLEX option positions
# =================================================================================================
import json   # noqa: E402
import os     # noqa: E402

from ds import opt_engine as O           # noqa: E402
from ds import opt_rules, opt_scenarios as OS   # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
obuilt = OS.build()
osc = {s["id"]: s["expected"] for s in obuilt}

# ---- figures worked by hand ----------------------------------------------------------------------
for what, got, want in [
    ("T01 premium paid", osc["T01"]["premium_paid"], 605_400_000), ("T01 premium received", osc["T01"]["premium_received"], 29_400_000),
    ("T01 cash after", osc["T01"]["cash_after"], 2_000_000), ("T01 net assets after", osc["T01"]["net_assets_after"], 578_000_000),
    ("T02 purchased", osc["T02"]["value_of_purchased_options"], 621_240_000), ("T02 written", osc["T02"]["value_of_written_options"], 13_080_000),
    ("T02 unrealized purchased", osc["T02"]["unrealized_on_purchased"], 15_840_000),
    ("T02 unrealized written", osc["T02"]["unrealized_on_written"], 16_320_000),
    ("T02 net assets", osc["T02"]["net_assets"], 610_000_000), ("T02 NAV", osc["T02"]["nav_per_share_published"], 30.50),
    ("T03 difference", osc["T03"]["value_difference_b_minus_a"], 168_000),
    ("T04 fee, in cents", round(osc["T04"]["fee_one_day"], 2), 13_202.74), ("T04 fee weekend, in cents", round(osc["T04"]["fee_weekend"], 2), 39_608.22),
    ("T04 interest, in cents", round(osc["T04"]["interest_one_day"], 2), 212.88),
    ("T04 interest weekend, in cents", round(osc["T04"]["interest_weekend"], 2), 638.63),
    ("T05 paid", osc["T05"]["amount_paid"], 470_650), ("T05 realized", osc["T05"]["realized"], 194_350),
    ("T05 premium remaining", osc["T05"]["premium_remaining"], 15_295_000),
    ("T06 contracts", osc["T06"]["contracts_delivered_per_position"], 120), ("T06 value", osc["T06"]["value_of_options_delivered"], 3_040_800),
    ("T06 cash amount", osc["T06"]["cash_amount"], 9_200), ("T06 net cash", osc["T06"]["net_cash_to_redeemer"], 8_700),
    ("T06 realized", osc["T06"]["realized_on_options_delivered"], 160_800), ("T06 NAV after", osc["T06"]["nav_per_share_published_after"], 30.50),
    ("T07 NAV", osc["T07"]["nav_per_share_published"], 30.52), ("T07 cash for shares", osc["T07"]["cash_for_shares"], 3_052_000),
    ("T07 net cost", osc["T07"]["net_cost_of_new_contracts"], 3_042_840), ("T07 net assets after", osc["T07"]["net_assets_after"], 613_460_000),
    ("T08 proceeds", osc["T08"]["proceeds"], 395_000), ("T08 realized", osc["T08"]["realized"], -1_735_000),
    ("T08 cost remaining", osc["T08"]["cost_remaining"], 35_390_000),
    ("T09 call", osc["T09"]["cash_from_purchased_call"], 690_240_000), ("T09 put", osc["T09"]["cash_from_purchased_put"], 0),
    ("T09 written call", osc["T09"]["cash_owed_on_written_call"], 19_200_000), ("T09 net", osc["T09"]["net_cash_received"], 671_040_000),
    ("T09 realized put", osc["T09"]["realized_on_purchased_put"], -34_800_000),
    ("T09 realized written put", osc["T09"]["realized_on_written_put"], 13_440_000), ("T09 realized", osc["T09"]["realized_total"], 95_040_000),
    ("T10 slice", osc["T10"]["pro_rata_contracts_per_unit"], 60.6), ("T10 basket", osc["T10"]["contracts_in_basket"], 60),
    ("T10 cash", osc["T10"]["cash_amount_per_unit"], 19_600),
    ("T11 right", osc["T11"]["right_net_assets"], 601_360_000), ("T11 misstatement", osc["T11"]["misstatement"], 8_640_000),
    ("T11 per share", osc["T11"]["misstatement_per_share"], 0.432),
    ("T11 percent", osc["T11"]["misstatement_percent"], 8_640_000 / 601_360_000 * 100),
    ("T12 contracts", osc["T12"]["contracts_after"], 48_000), ("T12 strike", osc["T12"]["strike_after"], 120.00),
    ("T12 value after", osc["T12"]["value_after"], 9_480_000), ("T12 value before", osc["T12"]["value_before"], 9_480_000),
    ("T12 wrong value", osc["T12"]["wrong_value"], 4_740_000),
    ("T13 income", osc["T13"]["income_accrued"], 0), ("T13 change", osc["T13"]["change_in_net_assets"], -1_440_000),
    ("T14 put", osc["T14"]["cash_from_purchased_put"], 120_000_000), ("T14 written put", osc["T14"]["cash_owed_on_written_put"], 33_600_000),
    ("T14 net", osc["T14"]["net_cash_received"], 536_640_000), ("T14 realized", osc["T14"]["realized_total"], -39_360_000),
    ("T15 move", osc["T15"]["change_in_value_of_options"], 3_984_000),
    ("T15 net assets, in cents", round(osc["T15"]["net_assets_at_close"], 2), 613_971_010.14), ("T15 NAV", osc["T15"]["nav_per_share_published"], 30.70),
]:
    check(what, got, want, 1e-4)

# ---- properties ----------------------------------------------------------------------------------
of = OS.base_fund()
net_premium = sum(l.side * l.premium for l in of.legs)
check("the four positions cost 240.00 a reference share net", net_premium, 576_000_000, 1e-4)
for s_close in (150.0, 190.0, 204.0, 220.0, 240.0, 258.0, 282.0, 290.0, 320.0):
    x = [O.expire(l, s_close) for l in of.legs]
    payoff = (s_close - 2.40) + max(240 - s_close, 0) - max(204 - s_close, 0) - max(s_close - 282, 0)
    check(f"net cash at expiry is the payoff at {s_close}", sum(v["cash_to_fund"] for v in x), 2_400_000 * payoff, 1e-4)
    check(f"realized at expiry is net cash less net premium at {s_close}", sum(v["realized"] for v in x), 2_400_000 * payoff - net_premium, 1e-4)
g, _ = O.redeem_in_kind(of, 2, 50_000, 60, OS.MODEL, 500.0)
check("a redemption in kind leaves NAV per share unchanged", O.nav_per_share(g, OS.MODEL), O.nav_per_share(of, OS.MODEL), 1e-9)
g, _ = O.redeem_in_kind(of, 2, 50_000, 60, OS.MODEL, 500.0, costs=0.0)
same("the published NAV after a redemption is the same if the fee stays in the fund", O.published(O.nav_per_share(g, OS.MODEL)), 30.50)
trades = {"purchased_call": 254.95, "purchased_put": 4.00, "written_put": 0.78, "written_call": 4.60}
for costs in (None, 0.0):
    g, info = O.create_for_cash(of, 2, 50_000, 60, trades, 500.0, costs=costs)
    same(f"the published NAV after a cash creation is the day's NAV (costs={costs})", O.published(O.nav_per_share(g, trades)), 30.52)
same("at the model prices the same day would publish", O.published(O.nav_per_share(of, OS.MODEL)), 30.50)
put = [l for l in of.legs if l.name == "purchased_put"][0]
sp = O.split(put, 2)
check("a split leaves the position's value unchanged", O.amount(sp, 3.95 / 2), O.amount(put, 3.95), 1e-6)
check("a split leaves the unrealized result unchanged", O.unrealized(sp, 3.95 / 2), O.unrealized(put, 3.95), 1e-6)
two = O.Leg("purchased_put", "put", 1, 240.0, (O.Lot(20_000, 14.50), O.Lot(4_000, 21.30)))
for method, want in (("highest", -1_735_000.0), ("first", -1_055_000.0), ("average", 395_000 - 37_520_000 / 24)):
    l2, info = O.close(two, 1_000, 3.95, method=method)
    check(f"selling 1,000 of two lots, {method}: realized", info["realized"], want, 1e-4)
    check(f"selling 1,000 of two lots, {method}: contracts left", l2.contracts, 23_000, 1e-9)
    check(f"selling 1,000 of two lots, {method}: premium is conserved", l2.premium + info["premium_relieved"], two.premium, 1e-4)
wcall = [l for l in of.legs if l.name == "written_call"][0]
_, info = O.close(wcall, 1_000, 4.70, commission=650.0)
check("a closing purchase: the realized result is the premium less the cash paid", info["realized"], info["premium_relieved"] + info["cash"], 1e-6)
na0 = O.net_assets(of, OS.MODEL)
for fee_basis in (360, 365, 366):                 # the whole-day NAV rounds to the same cent under every convention
    for int_basis in (360, 365):
        for with_interest in (0, 1):
            end = na0 + 3_984_000 - na0 * 0.0079 / fee_basis + with_interest * 2_100_000 * 0.037 / int_basis
            same(f"whole-day published NAV, fee/{fee_basis}, interest/{int_basis} x{with_interest}", O.published(end / 20_000_000), 30.70)
odd = OS.base_fund(24_240)
check("the other rounding of the basket (61 contracts) turns the cash amount around", 30.80 * 50_000 - 61 * 100 * 253.40, -5_740, 1e-6)

# ---- rules, quotes and the pack --------------------------------------------------------------------
for s in obuilt:
    for field, need in s["needs"].items():
        N += 1
        if s["expected"][field] is None and opt_rules.settled(need):
            FAILS += 1
            print(f"  FAIL {s['id']}.{field} has no figure although its rules are all stated")
    for rid in s["rules"]:
        N += 1
        if rid not in opt_rules.RULES:
            FAILS += 1
            print(f"  FAIL {s['id']} names an unknown rule {rid}")
oused = {rid for s in obuilt for rid in s["rules"]}
with open(os.path.join(HERE, "docs_koct", "passages.json"), encoding="utf-8") as fh:
    passages = {p["id"]: p["text"] for p in json.load(fh)["passages"]}
for rid, r in opt_rules.RULES.items():
    N += 1
    if rid not in oused:
        FAILS += 1
        print(f"  FAIL rule {rid} is used by no scenario")
    same(f"rule {rid}: a passage if and only if not absent", bool(r.get("sources")), r["status"] != "absent")
    same(f"rule {rid}: says what is missing unless stated", bool(r.get("missing")), r["status"] != "specified")
    for pid, quote in r.get("sources", []):
        same(f"rule {rid}: the quote is in passage {pid}", quote in passages.get(pid, ""), True)
with open(os.path.join(HERE, "pack_koct", "scenarios_for_models.json"), encoding="utf-8") as fh:
    shown_text = fh.read()
shown = json.loads(shown_text)
same("the pack shows fifteen scenarios", len(shown["scenarios"]), 15)
for s, t in zip(obuilt, shown["scenarios"]):
    same(f"{s['id']}: the pack lists the answer fields of the reference", t["answer_fields"], list(s["expected"]))
    same(f"{s['id']}: no withheld convention is shown", [k for k in t["given"] if k in OS.WITHHELD], [])
for words in OS.CONVENTIONS.values():
    same(f"the pack does not carry the convention '{words[:30]}'", words in shown_text, False)
with open(os.path.join(HERE, "pack_koct", "documents.md"), encoding="utf-8") as fh:
    pack_docs = fh.read()
for pid, text in passages.items():
    same(f"passage {pid} is in the pack", text in pack_docs, True)

# ---- the scorer on the second fund's conventions ---------------------------------------------------
same("a liability with a minus sign is the same amount", SD.close(-13_080_000, 13_080_000, "value_of_written_options", True), True)
same("a loss given as a gain is wrong", SD.close(1_735_000, -1_735_000, "realized", False), False)
same("a price a cent off is wrong", SD.close(4.00, 4.02, "price_case_b"), False)
same("zero is zero", SD.close(0.0, 0.0, "income_accrued"), True)
X = SD.FLAG_EXTRA["options"]
same("options, a bare product", SD.judge("plain", {"value": 48000, "note": "24,000 x 2"}, X)[0], "bare")
same("options, the clearing house named as the source", SD.judge("plain", {"value": 48000, "note": "Per OCC adjustment rules for a 2-for-1 split"}, X)[0], "with its assumption")
same("options, the exchange named without a rule", SD.judge("plain", {"value": 3.95, "note": "exchange model price at the official close"}, X)[0], "bare")

# ---- the first fund: a published NAV that is the same to the cent whether or not the fee stays in the fund ------
at42 = E.Fund(cash=52_500_000, collateral_posted=0.0, accrued_expenses=0.0, shares=2_000_000, swap=E.Swap(units=2_500_000, reset_price=42.00))
old47 = E.Fund(cash=47_500_000, collateral_posted=0.0, accrued_expenses=0.0, shares=2_000_000, swap=E.Swap(units=2_500_000, reset_price=40.00))
for costs in (None, 0.0):
    g_, _ = E.create(at42, 50_000, 42.00, 2.0, 500.0, costs=costs)
    same(f"swap fund: published NAV after a creation (costs={costs})", E.published(E.nav_per_share(g_, 42.00)), 26.25)
    g_, _ = E.redeem(old47, 100_000, 42.00, 2.0, 500.0, costs=costs)
    same(f"swap fund: published NAV after a redemption (costs={costs})", E.published(E.nav_per_share(g_, 42.00)), 26.25)
up41 = E.Fund(cash=50_000_000, collateral_posted=0.0, accrued_expenses=0.0, shares=2_000_000, swap=scenarios.base_fund().swap)
g_, _ = E.rebalance(up41, 41.00, 2.0)
check("swap fund: an increase leaves the gain so far unrealized (the reference's assumption, rule R21)", E.unrealized(g_.swap, 41.00), 2_500_000, 1e-4)
same("swap fund: the figure after an increase is not counted as settled", rules.settled(["R02", "R03", "R21"]), False)

# =================================================================================================
# The checking pass: what a reader is shown, and how a reading is counted
# =================================================================================================
import re      # noqa: E402

import check as CK          # noqa: E402
import score_checks as SC   # noqa: E402

for fund_key, conventions in (("swap", ["actual/360", "365 days", "day_count", "expense_basis"]), ("options", list(OS.CONVENTIONS.values()) + list(OS.CONVENTIONS))):
    text = CK.prompt(fund_key, None)[1]["content"]
    same(f"{fund_key}: the reader's prompt carries no withheld convention", [w for w in conventions if w in text], [])
    same(f"{fund_key}: the reader's prompt names no rule of the answer key", re.findall(r"\b[RO]\d\d\b", text), [])
    task_part = text.split("\nDOCUMENTS\n")[0]             # the documents themselves use words such as "specified"
    same(f"{fund_key}: the reader's task does not say what is settled", [w for w in ("not settled", "specified", "absent", "partly") if w in task_part], [])
    same(f"{fund_key}: nothing of the answer key's statuses is in the scenarios shown", '"status"' in text or '"needs"' in text or '"expected"' in text, False)
    with_draft = CK.prompt(fund_key, "REQUIREMENTS\n- Q1: x\n")[1]["content"]
    same(f"{fund_key}: the draft is the last part of the reader's prompt", with_draft.endswith("THE COLLEAGUE'S DRAFT\n\nREQUIREMENTS\n- Q1: x\n"), True)
    same(f"{fund_key}: both prompts ask the same question", "decide whether the fund's documents settle the answer" in text and
         "decide whether the fund's documents settle the answer" in with_draft, True)
fake = {"requirements": [{"id": "Q1", "text": "Accrue the fee daily.", "basis": "document", "quote": "calculated daily"}],
        "scenarios": {"T04": {"fee_one_day": {"value": 13202.74, "note": "610,000,000 x 0.0079 / 365"}}}}
shown_draft = CK.render("options", fake)
same("a draft is shown with its requirement", "- Q1: Accrue the fee daily. | basis: document | quote: calculated daily" in shown_draft, True)
same("a draft is shown with its figure and note", "  fee_one_day: value 13202.74 | note: 610,000,000 x 0.0079 / 365" in shown_draft, True)
same("a field the draft left out is shown as such", "  fee_weekend: (no answer)" in shown_draft, True)
same("verdict: supported", SC.verdict_of({"verdict": "supported", "missing": ""})[0], "supported")
same("verdict: not supported", SC.verdict_of({"verdict": "Not supported", "missing": "day count"})[0], "not supported")
same("verdict: a bare string", SC.verdict_of({"value": "not supported"})[0], "not supported")
same("verdict: none given", SC.verdict_of(None)[0], "missing")
same("verdict: something else", SC.verdict_of({"verdict": "partially"})[0], "unclear")
hand = [{"settled": False, "draft": "bare", "verdict": "not supported", "names_the_open_rule": True},
        {"settled": False, "draft": "bare", "verdict": "supported", "names_the_open_rule": None},
        {"settled": False, "draft": "asked", "verdict": "supported", "names_the_open_rule": None},
        {"settled": False, "draft": "with its assumption", "verdict": "not supported", "names_the_open_rule": False},
        {"settled": True, "draft": "bare", "verdict": "not supported", "names_the_open_rule": None},
        {"settled": True, "draft": "bare", "verdict": "supported", "names_the_open_rule": None}]
t = SC.tally(hand)
for key, want in (("unsettled", 4), ("caught", 2), ("missed", 2), ("caught_and_names_the_open_rule", 1), ("settled", 2), ("false_alarms", 1),
                  ("draft_bare", 2), ("draft_bare_caught", 1), ("draft_flagged", 2), ("draft_flagged_kept", 1), ("draft_flag_removed", 1),
                  ("unflagged_if_the_reader_decides", 2), ("unflagged_if_either_flags", 1)):
    same(f"a reading is counted: {key}", t[key], want)
for rid in list(rules.RULES) + list(opt_rules.RULES):
    R_ = rules.RULES.get(rid) or opt_rules.RULES[rid]
    if R_["status"] != "specified":
        same(f"an open rule has a pattern for the reader's reason: {rid}", rid in SC.REASON, True)

# =================================================================================================
# Rule-by-rule tracing: what a reader is asked, and how a tracing is counted
# =================================================================================================
import score_trace as ST    # noqa: E402
import trace as TR          # noqa: E402
from ds.funds import FUNDS as _FUNDS   # noqa: E402

for fund_key in ("swap", "options"):
    R_ = _FUNDS[fund_key]["rules"].RULES
    asked = TR.prompt(fund_key)[1]["content"]
    part = asked[asked.index("\nQUESTIONS\n"):]
    same(f"{fund_key}: every rule is asked as a question", [k for k, r in R_.items() if not str(r.get("ask", "")).endswith("?")], [])
    same(f"{fund_key}: every question is in the prompt", [k for k, r in R_.items() if r["ask"] not in part], [])
    same(f"{fund_key}: no question carries the reference's answer", [k for k, r in R_.items() if r["text"] in asked], [])
    same(f"{fund_key}: no question says what is missing", [k for k, r in R_.items() if r.get("missing") and r["missing"] in asked], [])
    same(f"{fund_key}: the questions name no rule id and no status", re.findall(r"\b[RO]\d\d\b|specified|absent", part), [])
    same(f"{fund_key}: the questions carry no number", re.findall(r"\d", re.sub(r"Q\d\d\.", "", part)), [])
    same(f"{fund_key}: the reader is shown no scenario", "SCENARIOS" in asked or "answer_fields" in asked, False)
    qs = TR.questions(fund_key)
    same(f"{fund_key}: one question per rule", sorted(qs.values()), sorted(R_))
    for flags, label in ((lambda r: r["status"] != "specified", "exactly the open rules"), (lambda r: False, "nothing")):
        fake_t = {"rows": [{"rule": k, "flagged": flags(r), "conflict_rule": k in ST.CONFLICT_RULES, "verdict": "x"} for k, r in R_.items()]}
        imp = ST.implied(fund_key, fake_t)
        same(f"{fund_key}: a tracing that flags {label} catches, figure by figure", (imp["caught"], imp["false_alarms"]),
             ((imp["unsettled"], 0) if label != "nothing" else (0, 0)))
small = ST.norm("The NAV per share is “rounded to the nearest cent”. Expenses are accrued daily and taken into account. Income isn’t accrued on options.")
same("a quote found word for word", ST.check_quote("Expenses are accrued daily and taken into account.", small), "found")
same("a quote found apart from quotation marks and case", ST.check_quote("the nav per share is \"rounded to the nearest cent\"", small), "found")
same("a quote cut with dots, both pieces found", ST.check_quote("The NAV per share is “rounded to the nearest cent” ... Expenses are accrued daily and taken into account", small), "found")
same("a quote with one invented piece", ST.check_quote("Expenses are accrued daily and taken into account ... using an actual/365 day count convention", small), "partly found")
same("an invented quote", ST.check_quote("Financing accrues on an actual/360 basis for every calendar day.", small), "not found")
same("two passages quoted one after the other, both found", ST.check_quote("Income isn’t accrued on options. Expenses are accrued daily and taken into account.", small), "found")
same("two passages one after the other, one invented", ST.check_quote("Income isn’t accrued on options. Financing accrues on an actual/360 basis for every calendar day.", small), "not found")
same("no quote", ST.check_quote("", small), "no quote")
same("a quote too short to check", ST.check_quote("accrued daily", small), "too short to check")
same("a short quote that stands in the text as a whole", ST.check_quote("rounded to the nearest", small), "found, short")
same("a short quote that does not stand in the text", ST.check_quote("Expenses accrue monthly.", small), "not found")
same("a short quote of three words, apart from case and the full stop", ST.check_quote("Income isn't accrued.", small), "found, short")
same("two words stay unchecked", ST.check_quote("isn't accrued", small), "too short to check")
same("the real case: four words, compared whole", ST.check_quote("100 shares per contract.", ST.norm("Each contract covers 100 shares per contract. More.")), "found, short")
t2_ = ST.tally([{"status": "specified", "conflict_rule": False, "verdict": "stated", "flagged": False, "exact": True, "quote_check": "found, short"},
                {"status": "absent", "conflict_rule": False, "verdict": "not stated", "flagged": True, "exact": True, "quote_check": "no quote"},
                {"status": "specified", "conflict_rule": False, "verdict": "stated", "flagged": False, "exact": True, "quote_check": "too short to check"}])
for key, want in (("answers", 3), ("answers_not_stated", 1), ("answers_not_stated_with_a_quote", 0), ("answers_that_name_a_passage", 2),
                  ("answers_that_name_a_passage_without_a_quote", 0), ("quotes", 1), ("quotes_found", 1), ("quotes_found_short", 1),
                  ("quotes_too_short_to_check", 1)):
    same(f"quotes are counted: {key}", t2_[key], want)
for said, want in (("stated", "stated"), ("Partly", "partly"), ("not stated", "not stated"), ("Conflicting", "conflicting"), ("yes", "unclear")):
    same(f"a tracing verdict: {said}", ST.verdict_of({"verdict": said})[0], want)
t_ = ST.tally([{"status": "absent", "conflict_rule": False, "verdict": "not stated", "flagged": True, "exact": True, "quote_check": "no quote"},
               {"status": "partly", "conflict_rule": False, "verdict": "stated", "flagged": False, "exact": False, "quote_check": "found"},
               {"status": "specified", "conflict_rule": False, "verdict": "partly", "flagged": True, "exact": False, "quote_check": "not found"},
               {"status": "specified", "conflict_rule": True, "verdict": "conflicting", "flagged": True, "exact": False, "quote_check": "found"}])
for key, want in (("open_rules", 2), ("caught", 1), ("called_stated", 1), ("stated_rules", 1), ("false_alarms", 1), ("conflict_rules", 1),
                  ("conflict_reported", 1), ("exact_status", 1), ("quotes", 3), ("quotes_found", 2), ("quotes_not_found", 1)):
    same(f"a tracing is counted: {key}", t_[key], want)

# =================================================================================================
# The third fund: a question list written blind, an answer key written afterwards, two standards
# =================================================================================================
import hashlib   # noqa: E402

from ds import fut_key, fut_questions, fut_rules   # noqa: E402

BLIND = "8c2fd9062a26bb7176af4f2af2782eed1f115202398cbfcffb8db2662133273f"   # printed 2026-11-16 18:16:49 EST, before a fund was chosen
with open(os.path.join(HERE, "ds", "fut_questions.py"), "rb") as fh:
    same("the blind question list is the file that was fingerprinted before any document was opened", hashlib.sha256(fh.read()).hexdigest(), BLIND)
same("the key answers every question of the list and no other", sorted(fut_key.KEY), sorted(fut_questions.ASK))
with open(os.path.join(HERE, "docs_tya", "passages.json"), encoding="utf-8") as fh:
    tya = json.load(fh)["passages"]
tya_text = {d: ST.norm(" ".join(p["text"] for p in tya if p["document"] == d)) for d in ("prospectus", "sai", "annual")}
with open(os.path.join(HERE, "pack_tya", "documents.md"), encoding="utf-8") as fh:
    tya_pack = ST.norm(fh.read())
for p in tya:
    N += 1
    if ST.norm(p["text"]) not in tya_pack:
        FAILS += 1
        print(f"  FAIL third fund: passage {p['id']} is not in the pack")
order = {"specified": 0, "partly": 1, "absent": 2}
for fid, k in fut_key.KEY.items():
    same(f"{fid}: the letter is never more lenient than the obvious reading", order[k["letter"]] >= order[k["reading"]], True)
    same(f"{fid}: a passage unless absent on both standards", bool(k.get("sources")), not (k["letter"] == "absent" and k["reading"] == "absent"))
    same(f"{fid}: says what is missing unless stated to the letter", bool(k.get("missing")), k["letter"] != "specified")
    for doc, quote in k.get("sources", []):
        same(f"{fid}: the quote is in the {doc} passages", ST.norm(quote) in tya_text[doc], True)
asked3 = TR.prompt("futures")[1]["content"]
same("third fund: every question is in the prompt", [k for k, q in fut_questions.ASK.items() if q not in asked3], [])
same("third fund: nothing of the key is in the prompt", [k for k, v in fut_key.KEY.items() if v.get("missing") and v["missing"] in asked3], [])
same("third fund: the questions carry no number", re.findall(r"\d", re.sub(r"Q\d\d\.", "", asked3[asked3.index("\nQUESTIONS\n"):])), [])
same("third fund: the reader is shown no scenario", "SCENARIOS" in asked3, False)
for fund_key, letter_rules in (("swap", {"R13", "R17"}), ("options", {"O09", "O12", "O14"})):
    M_ = _FUNDS[fund_key]["rules"]
    same(f"{fund_key}: the rules stated only on the obvious reading", set(M_.LETTER), letter_rules)
    same(f"{fund_key}: on the obvious reading they count as stated", [k for k in M_.LETTER if M_.status(k) != "specified"], [])

# =================================================================================================
# The kinds of gap and the two groups (ds/kinds.py)
# =================================================================================================
from ds import kinds as KD   # noqa: E402

in_a_kind = [r for ids in KD.KINDS.values() for r in ids]
same("no rule is in two kinds", len(in_a_kind), len(set(in_a_kind)))
same("every kind is in one group and one only", sorted(k for ks in KD.GROUPS.values() for k in ks), sorted(KD.KINDS))
every_rule = {**_FUNDS["swap"]["rules"].RULES, **_FUNDS["options"]["rules"].RULES}
same("every rule of a kind exists", [r for r in in_a_kind if r not in every_rule], [])
open_on_the_reading = [k for f in ("swap", "options") for k, r in _FUNDS[f]["rules"].RULES.items() if r["status"] != "specified"]
same("the kinds are the rules open on the obvious reading, each once", sorted(in_a_kind), sorted(open_on_the_reading))
open_to_the_letter_only = [k for f in ("swap", "options") for k in _FUNDS[f]["rules"].LETTER]
same("the rules open to the letter only are in no kind", [k for k in open_to_the_letter_only if KD.group_of_rule(k)], [])
same("a figure with a rule of accounting treatment is of that group", KD.group_of_figure(["R05", "R11"]), KD.TREATMENT)
same("a figure with parameters only", KD.group_of_figure(["R05", "R20"]), KD.PARAMETERS)
same("a figure whose open rules are in no kind", KD.group_of_figure(["R13"]), None)
for fund_key in ("swap", "options"):
    for s_ in _FUNDS[fund_key]["scenarios"].build():
        for field_, need_ in s_["needs"].items():
            op_ = [r for r in need_ if every_rule[r]["status"] != "specified"]
            if op_:
                same(f"{fund_key} {s_['id']}.{field_}: an open figure has a group", KD.group_of_figure(op_) in KD.GROUPS, True)

print(f"\nSELFTEST {'FAILED' if FAILS else 'PASSED'}: {N} checks, {FAILS} failed")
sys.exit(1 if FAILS else 0)

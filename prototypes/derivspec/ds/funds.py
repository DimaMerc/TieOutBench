"""The two funds of the experiment: which rules, scenarios, document pack and task text belong to each."""
from __future__ import annotations

from . import fut_rules, opt_rules, opt_scenarios, rules, scenarios

FUNDS = {
    "swap": {
        "rules": rules, "scenarios": scenarios, "pack": "pack", "suffix": "",
        "label": "a leveraged ETF that holds a total return swap (documents of the AdvisorShares MSOS Daily Leveraged ETF)",
        "sign_free": set(),
        "exposure": "It gets its exposure through total return swaps.",
        "subject": "the fund's total return swaps",
        "example": "a rate or a spread",
        "other_kind": ("confirmation", "terms of the swap confirmation", "public"),
    },
    "options": {
        "rules": opt_rules, "scenarios": opt_scenarios, "pack": "pack_koct", "suffix": "_options",
        "label": "a defined-outcome ETF that holds four FLEX option positions (documents of the Innovator U.S. Small Cap Power Buffer ETF - October)",
        "sign_free": opt_scenarios.SIGN_FREE,
        "exposure": "It gets its exposure through FLEX options: purchased and written calls and puts on one exchange-traded fund.",
        "subject": "the fund's options",
        "example": "a price or a fee",
        "other_kind": ("contract", "terms of the option contract, the clearing house or the deposit account", "in the fund's documents"),
    },
    # The third fund has a question list (written blind) and an answer key, no reference engine and no scenarios.
    "futures": {
        "rules": fut_rules, "scenarios": None, "pack": "pack_tya", "suffix": "_futures",
        "label": "an ETF that holds Treasury futures (documents of the Simplify Intermediate Term Treasury Futures Strategy ETF)",
        "sign_free": set(),
        "exposure": "It gets its exposure through exchange-traded futures contracts on U.S. Treasury securities.",
        "subject": "the fund's futures",
        "example": "a price or a fee",
        "other_kind": ("contract", "terms of the futures contract, the exchange or the broker", "in the fund's documents"),
    },
}


def kind_counts(fund: str) -> dict:
    """Rule counts in one shape for both funds."""
    M = FUNDS[fund]["rules"]
    R = M.RULES
    own = [k for k, r in R.items() if r["kind"] == "fund"]
    other = [k for k, r in R.items() if r["kind"] != "fund"]
    return {"rules": len(R), "fund_rules": len(own),
            "fund_specified": sum(M.status(k) == "specified" for k in own),
            "fund_partly": sum(M.status(k) == "partly" for k in own),
            "fund_absent": sum(M.status(k) == "absent" for k in own),
            "other_rules": len(other), "other_specified": sum(M.status(k) == "specified" for k in other)}

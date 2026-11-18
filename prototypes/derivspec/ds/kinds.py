"""The kinds of gap the report's tables name, and the two groups they fall in.

A kind is a list of rule ids of the first two funds (ds/rules.py, ds/opt_rules.py). The seven kinds cover every rule
that is open on the obvious reading, each rule once (selftest.py checks both). The rules that are open to the
letter only (R13, R17, O09, O12, O14) belong to no kind.

THE KINDS AND THE GROUPS WERE FORMED AFTER THE SECOND READINGS HAD BEEN SCORED. They describe that result; they are
not a grouping fixed in advance and tested. The report says so where it uses them.

  accounting treatment   what is recognized or realized in the fund's books, and when: income on the swap, a reset,
                         a reduction or an increase of the swap, the transaction fee on a creation or redemption
  terms and parameters   a term or a parameter that has a name: a day count or day basis, the order of lots, the
                         rounding of a basket, the correction threshold, the adjustment on a split

A figure of a scenario belongs to "accounting treatment" when any open rule it rests on does, and to "terms and
parameters" when its open rules are of that group only, so the two groups of figures do not overlap.
"""
from __future__ import annotations

KINDS = {"when swap income is accrued": ["R19"],
         "how the transaction fee is booked": ["R18", "O24"],
         "what a reduction of the swap realizes": ["R10"],
         "what a reset or payment date does": ["R11"],
         "what an increase of the swap does to the gain so far": ["R21"],
         "day counts and day bases": ["R05", "R06", "R07", "R20", "O18", "O20"],
         "lot order, basket rounding, correction threshold, split of the reference": ["O10", "O16", "O21", "R15", "O22", "R16"]}

TREATMENT, PARAMETERS = "accounting treatment", "terms and parameters"
GROUPS = {TREATMENT: ["when swap income is accrued", "how the transaction fee is booked", "what a reduction of the swap realizes",
                      "what a reset or payment date does", "what an increase of the swap does to the gain so far"],
          PARAMETERS: ["day counts and day bases", "lot order, basket rounding, correction threshold, split of the reference"]}
RULES_OF = {g: [r for k in kinds for r in KINDS[k]] for g, kinds in GROUPS.items()}


def group_of_rule(rule: str) -> str | None:
    for g, ids in RULES_OF.items():
        if rule in ids:
            return g
    return None


def group_of_figure(open_rules: list[str]) -> str | None:
    """The group of a figure that rests on these open rules; None when none of them belongs to a kind."""
    if any(r in RULES_OF[TREATMENT] for r in open_rules):
        return TREATMENT
    if any(r in RULES_OF[PARAMETERS] for r in open_rules):
        return PARAMETERS
    return None

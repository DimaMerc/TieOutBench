"""The third fund's rule table, put together from the blind question list and the answer key written afterwards.

Same shape as ds/rules.py and ds/opt_rules.py, so that trace.py and score_trace.py treat the three funds alike.
There is no reference engine and there are no scenarios for this fund: the test is of the list of questions.
"""
from __future__ import annotations

from . import standard as _standard
from .fut_key import KEY
from .fut_questions import ASK

RULES = {k: {"kind": KEY[k]["kind"], "ask": q, "text": "(the list was written blind; the key gives passages, not a reference figure)",
             "status": KEY[k]["reading"], "sources": KEY[k].get("sources", []), "missing": KEY[k].get("missing", "")}
         for k, q in ASK.items()}
LETTER = {k: v.get("missing", "") for k, v in KEY.items() if v["letter"] != v["reading"]}


def status(rid: str) -> str:
    return KEY[rid][_standard.NAME]


def is_open(rid: str) -> bool:
    return status(rid) != "specified"


def settled(rule_ids) -> bool:
    return not any(is_open(r) for r in rule_ids)


def counts() -> dict:
    fund = [k for k, r in RULES.items() if r["kind"] == "fund"]
    other = [k for k, r in RULES.items() if r["kind"] != "fund"]
    return {"rules": len(RULES), "fund_rules": len(fund),
            "fund_specified": sum(status(k) == "specified" for k in fund),
            "fund_partly": sum(status(k) == "partly" for k in fund),
            "fund_absent": sum(status(k) == "absent" for k in fund),
            "contract_rules": len(other),
            "contract_in_the_documents": sum(status(k) == "specified" for k in other)}

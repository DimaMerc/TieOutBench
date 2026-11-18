"""Build what a model is shown: pack/documents.md and pack/scenarios_for_models.json.

documents.md holds only text of the fund's documents (the verbatim passages and table rows collected in docs/),
without the collector's remarks about what the documents leave out. The scenarios are given without the
conventions that no public document states (day count, the basis of the expense accrual), so that a model has
to say what it assumes.
"""
from __future__ import annotations

import json
import os
import re

from ds import scenarios

HERE = os.path.dirname(os.path.abspath(__file__))
DOCS = os.path.join(HERE, "docs")
PACK = os.path.join(HERE, "pack")

SOURCES = [("01-msox-annual-report-2026-06-30.md", "ANNUAL REPORT, year ended June 30, 2026"),
           ("02-msox-prospectus-2026-11-01.md", "PROSPECTUS dated November 1, 2026"),
           ("03-advisorshares-sai-2026-11-01.md", "STATEMENT OF ADDITIONAL INFORMATION dated November 1, 2026")]
TABLE_LINES = ("Swap table (column headers", "- AdvisorShares Pure US Cannabis ETF |", "- Net Unrealized Appreciation",
               "Fee table row:", "Financial Highlights, MSOX", "(table): MANAGEMENT FEES", "table of fund types:")
SKIP_SECTIONS = ("Short Sales",)          # a policy for short sales, not for swaps
WITHHELD = {"day_count", "basis", "expense_basis"}     # conventions the public documents do not state


def documents() -> str:
    out = ["Passages from the public documents of the AdvisorShares MSOS Daily Leveraged ETF, quoted under the name of",
           "the section each comes from. Treat them as the documents available to you.", ""]
    for name, title in SOURCES:
        out += [f"=== {title} ===", ""]
        section, shown, skip = "", "", False
        with open(os.path.join(DOCS, name), encoding="utf-8") as fh:
            for line in fh.read().splitlines():
                if line.startswith("Section:"):
                    section = re.sub(r"\s*\((policy|columns?:).*$", "", line[len("Section:"):].strip())
                    skip = any(s in line for s in SKIP_SECTIONS)
                    if any(t in line for t in TABLE_LINES) and not skip:
                        out += [line[len("Section:"):].strip(), ""]
                        shown = section
                    continue
                if skip:
                    continue
                if line.startswith("> "):
                    if section != shown:
                        out += [f"[{section}]"]
                        shown = section
                    out += [line[2:].strip(), ""]
                elif any(t in line for t in TABLE_LINES):
                    text = line.replace("Swap table (column headers as given:", "Table of total return swaps, columns:").rstrip(":")
                    text = re.sub(r"\s*\(limit excludes.*$", "", text)
                    out += [text.rstrip(")") if text.startswith("Table of") else text]
                    if not line.startswith("- "):
                        out += [""]
        out += [""]
    return "\n".join(out).rstrip() + "\n"


def for_models() -> dict:
    sc = []
    for s in scenarios.build():
        given = {k: v for k, v in s["given"].items() if k not in WITHHELD}
        sc.append({"id": s["id"], "title": s["title"], "given": given, "ask": s["ask"], "answer_fields": list(s["expected"])})
    fund = {"shares_outstanding": scenarios.FUND["shares_outstanding"], "net_assets": scenarios.FUND["net_assets"],
            "target_multiple_of_the_reference_daily_return": scenarios.LEVERAGE,
            "annual_expense_rate": scenarios.FUND["expense_ratio"], "transaction_fee_per_order": scenarios.FUND["transaction_fee"]}
    return {"fund": fund, "scenarios": sc}


def documents_options() -> str:
    """The second fund: every passage of docs_koct/passages.json (cut from the documents' full text by
    collect_koct.py), under its document and section. Square brackets mark the few words that are not the fund's."""
    with open(os.path.join(HERE, "docs_koct", "passages.json"), encoding="utf-8") as fh:
        d = json.load(fh)
    out = ["Passages from the public documents of the Innovator U.S. Small Cap Power Buffer ETF - October, quoted under the name of",
           "the section each comes from. Treat them as the documents available to you. Text in square brackets is not part of",
           "the documents.", ""]
    for key in ("prospectus", "sai", "annual"):
        out += [f"=== {d['documents'][key]['title']} ===", ""]
        shown = ""
        for p in d["passages"]:
            if p["document"] != key:
                continue
            if p["section"] != shown:
                out += [f"[{p['section']}]"]
                shown = p["section"]
            out += [p["text"], ""]
        out += [""]
    return "\n".join(out).rstrip() + "\n"


def for_models_options() -> dict:
    from ds import opt_scenarios as O
    sc = []
    for s in O.build():
        given = {k: v for k, v in s["given"].items() if k not in O.WITHHELD}
        sc.append({"id": s["id"], "title": s["title"], "given": given, "ask": s["ask"], "answer_fields": list(s["expected"])})
    fund = {"shares_outstanding": O.FUND["shares_outstanding"],
            "reference": "one exchange-traded fund; its price was 240.00 when the outcome period began",
            "positions": {n: {"strike": O.STRIKE[n], "contracts": O.CONTRACTS} for n in O.NAMES},
            "annual_management_fee_rate": O.FUND["annual_management_fee_rate"],
            "shares_per_creation_unit": O.FUND["creation_unit_shares"],
            "transaction_fee_per_order": O.FUND["transaction_fee_per_order"]}
    return {"fund": fund, "notes": O.NOTES, "scenarios": sc}


def documents_futures() -> str:
    """The third fund: every passage of docs_tya/passages.json (taken by rule from the documents' full text by
    collect_tya.py), under its document and section."""
    with open(os.path.join(HERE, "docs_tya", "passages.json"), encoding="utf-8") as fh:
        d = json.load(fh)
    out = ["Passages from the public documents of the Simplify Intermediate Term Treasury Futures Strategy ETF (the trust's combined",
           "prospectus, statement of additional information and annual financial statements cover many funds; these are the",
           "sections that concern this Fund or all funds). Treat them as the documents available to you. Text in square brackets",
           "is not part of the documents.", ""]
    for key in ("prospectus", "sai", "annual"):
        out += [f"=== {d['documents'][key]['title']} ===", ""]
        shown = ""
        for p in d["passages"]:
            if p["document"] != key:
                continue
            if p["section"] != shown:
                out += [f"[{p['section']}]"]
                shown = p["section"]
            out += [p["text"], ""]
        out += [""]
    return "\n".join(out).rstrip() + "\n"


def main(fund: str = "swap") -> None:
    if fund == "futures":
        pack, text = os.path.join(HERE, "pack_tya"), documents_futures()
        os.makedirs(pack, exist_ok=True)
        with open(os.path.join(pack, "documents.md"), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        print(f"wrote pack_tya/documents.md ({len(text.split())} words); the third fund has no scenarios")
        return
    if fund == "options":
        pack, text, sc = os.path.join(HERE, "pack_koct"), documents_options(), for_models_options()
    else:
        pack, text, sc = PACK, documents(), for_models()
    os.makedirs(pack, exist_ok=True)
    with open(os.path.join(pack, "documents.md"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    with open(os.path.join(pack, "scenarios_for_models.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(sc, fh, indent=1)
    name = os.path.basename(pack)
    print(f"wrote {name}/documents.md ({len(text.split())} words) and {name}/scenarios_for_models.json")


if __name__ == "__main__":
    import sys
    main(sys.argv[1] if len(sys.argv) > 1 else "swap")

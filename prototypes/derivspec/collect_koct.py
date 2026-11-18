"""Collect the passages of the second fund's public documents, verbatim, from the full text of each document.

  python -I collect_koct.py            (the source files are downloads: read them as data, in isolated mode)

The fund: Innovator U.S. Small Cap Power Buffer ETF - October (KOCT), which holds four FLEX option positions on
one exchange-traded fund. Three documents, downloaded on 2026-11-16 from the sponsor's site with a plain client
and converted with `pdftotext -layout -enc UTF-8` (sources/<name>/<name>.pdf and .txt, not committed):
  prospectus   koct_prospectus.pdf             dated February 27, 2026, as supplemented October 1, 2026
  sai          sai_non_us_equity.pdf           dated February 27, 2026, as supplemented April 16, 2026
  annual       do_annual_core_financials.pdf   audited financial statements, October 31, 2025

Unlike the first fund (docs/, collected by a reader), every passage here is cut from the document's text by a
start and an end anchor, so it is verbatim by construction, and "not stated" is a search over the whole text of
the three documents (NOT_FOUND below), not over a selection. Writes docs_koct/passages.json, docs_koct/searches.json
and docs_koct/INDEX.md.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "sources")
OUT = os.path.join(HERE, "docs_koct")

DOCS = {
    "prospectus": {"file": "koct_prospectus", "title": "PROSPECTUS dated February 27, 2026, as supplemented October 1, 2026",
                   "url": "https://www.innovatoretfs.com/pdf/koct_prospectus.pdf"},
    "sai": {"file": "sai_non_us_equity", "title": "STATEMENT OF ADDITIONAL INFORMATION dated February 27, 2026, as supplemented April 16, 2026",
            "url": "https://www.innovatoretfs.com/pdf/sai_non_us_equity.pdf"},
    "annual": {"file": "do_annual_core_financials", "title": "ANNUAL FINANCIAL STATEMENTS, October 31, 2025 (audited)",
               "url": "https://www.innovatoretfs.com/pdf/do_annual_core_financials.pdf"},
}

FURNITURE = re.compile(r"^\s*(-?\d{1,3}-?|INNOVATOR ETFs TRUST|NOTES TO FINANCIAL STATEMENTS|October 31, 2025 \(Continued\))\s*$")

# (id, document, section, start anchor, end anchor or None for a single sentence, optional "after" anchor)
PASSAGES = [
    ("P1", "prospectus", "Cover page",
     "If the Fund invests solely in FLEX Options that reference the Underlying ETF, the Cap and Buffer will be provided on a price",
     "will not receive the benefit of any dividends.", None),
    ("P2", "prospectus", "Principal Investment Strategies",
     "Upon conclusion of the Outcome Period, the Fund will receive the cash value", "and a new Outcome Period will begin.", None),
    ("P3", "prospectus", "Additional Information About the Fund's Principal Investment Strategies",
     "Each FLEX Option contract that the Fund enters into references the Underlying ETF", "as detailed below.", None),
    ("P4", "prospectus", "Additional Information About the Fund's Principal Investment Strategies",
     "The purchased call FLEX Option provides the Fund", "100% notional value) to the Underlying ETF.", None),
    ("P5", "prospectus", "Additional Information About the Fund's Principal Investment Strategies",
     "Taken together, the purchase and sale of put FLEX Options produces the 15%", "15% power Buffer.", None),
    ("P6", "prospectus", "Additional Information About the Fund's Principal Investment Strategies",
     "To help pay for the positions that provide upside exposure to the Underlying ETF and the",
     "exceed the strike price of the sold call FLEX Option.", None),
    ("P7", "prospectus", "Fund Investments: FLEX Options",
     "The FLEX Options in which the Fund invests are all European style option contracts", "Chicago Board Options Exchange.", None),
    ("P8", "prospectus", "Fund Investments: FLEX Options",
     "Since the FLEX Options held by the Fund are exchange-traded, these will be valued on a mark-to-market basis.", None, None),
    ("P9", "prospectus", "Management Fee",
     "Pursuant to an investment advisory agreement between Innovator and the Trust, on behalf of the",
     "0.79% of its average daily net assets.", None),
    ("P10", "prospectus", "How to Buy and Sell Shares",
     "The Fund will issue or redeem its Shares at NAV per Share only in Creation Units.", None, None),
    ("P11", "prospectus", "Frequent Purchases and Redemptions of Shares",
     "To minimize these potential consequences of frequent purchases and redemptions of Shares,",
     "the Fund incurs in effecting trades.", None),
    ("P12", "prospectus", "Net Asset Value",
     "US Bancorp Fund Services LLC", "rounded to the nearest cent is the NAV per Share.", None),
    ("P13", "prospectus", "Net Asset Value",
     "FLEX Options listed on an exchange will typically be valued at a model-based price",
     "rather than the model price otherwise available for the in-kind transaction.", None),

    ("S1", "sai", "FLEX Options",
     "FLexible EXchange® Options (“FLEX Options”) are customized option contracts available",
     "shares of the reference asset at the strike price.", None),
    ("S2", "sai", "Certain Considerations Regarding Options",
     "Option contracts that expire unexercised have no value.", None, None),
    ("S3", "sai", "Certain Considerations Regarding Options",
     "Notwithstanding the above, the Funds utilize FLEX Options that are cash-settled.",
     "which determines the total value for each point of such difference.", None),
    ("S4", "sai", "Creation and Redemption of Creation Units: Basket Composition and Custom Baskets",
     "The Funds may effect creation and redemptions for in-kind securities or for cash",
     "sold at their NAV plus a transaction fee.", None),
    ("S5", "sai", "Creation and Redemption of Creation Units: Basket Composition and Custom Baskets",
     "Each Fund may utilize a", "different baskets in transactions on the same Business Day.",
     "sold at their NAV plus a transaction fee."),
    ("S6", "sai", "Creation and Redemption of Creation Units: Placement of Creation or Redemption Orders",
     "Except as set forth below, all orders to purchase or redeem Creation Units", "after receipt of the order in proper form.", None),
    ("S7", "sai", "Creation and Redemption of Creation Units: Placement of Creation or Redemption Orders",
     "The delivery of Creation Units properly created will occur no later than", "will ordinarily be transferred no later than T+1.", None),
    ("S8", "sai", "Creation and Redemption of Creation Units: Purchase and Issuance of Creation Units",
     "The consideration for the purchase of a Creation Unit of shares of a Fund may consist of",
     "will receive the Cash Component.", None),
    ("S9", "sai", "Creation and Redemption of Creation Units: Delivery of Redemption Proceeds",
     "The redemption proceeds for a Creation Unit generally consist of the Deposit Instruments",
     "by or through an Authorized Participant by the redeeming shareholder.", None),
    ("S10", "sai", "Creation and Redemption of Creation Units: Creation Transaction Fees",
     "Each Fund imposes fees in connection with the purchase of Creation Units.", "securities comprising the creation basket.", None),
    ("S11", "sai", "Creation and Redemption of Creation Units: Redemption Transaction Fees",
     "Each Fund imposes fees in connection with the redemption of Creation Units.", "securities comprising the redemption basket.", None),
    ("S12", "sai", "Determining Offering Price and Net Asset Value",
     "In accordance with procedures approved by the Trustees, the NAV per share of the Fund", "market may officially close.", None),
    ("S13", "sai", "Determining Offering Price and Net Asset Value",
     "Portfolio securities of the Fund are generally valued as follows:", None, None),
    ("S14", "sai", "Determining Offering Price and Net Asset Value [items (ix) and (x) of the list that follows; items (i) to (viii) concern other instruments]",
     "(ix) exchange-traded options contracts with settlement prices",
     "ask price for short positions at the time closest to, but no later than, the NAV calculation time);", None),

    ("A1", "annual", "Notes to Financial Statements, 2. Significant Accounting Policies: Valuation",
     "Valuation: The net asset values", "the Funds shall determine NAV as of that time.", None),
    ("A2", "annual", "Notes to Financial Statements, 2. Significant Accounting Policies: Valuation",
     "Exchange-traded option contracts (other than FLEX Option contracts) will be valued at the closing price",
     "s valuation procedures.", None),
    ("A3", "annual", "Notes to Financial Statements, 2. Significant Accounting Policies: Option Contracts",
     "When the Funds purchase an option, an amount equal to the premium paid",
     "price of the security underlying the written option.", None),
    ("A4", "annual", "Notes to Financial Statements, 2. Significant Accounting Policies: Option Contracts",
     "All of the FLEX Option contracts held by the Funds are fully funded and cash settled",
     "offsetting under U.S. GAAP does not apply.", None),
    ("A5", "annual", "Notes to Financial Statements, 2. Significant Accounting Policies",
     "Investment Transactions and Investment Income: Investment transactions are recorded on the trade date.",
     "using the effective yield method.", None),
    ("A6", "annual", "Notes to Financial Statements, 3. Investment Advisor and Other Affiliates [the Fund is one of the \"other Innovator ETFs\" of this sentence]",
     "All other Innovator ETFs included in this report each, respectively, pay monthly the Adviser a",
     "and extraordinary expenses.", None),
    ("A7", "annual", "Notes to Financial Statements, 5. Creation and Redemption Transactions",
     "The Funds issue and redeem shares on a continuous basis at NAV only in blocks of shares called",
     "Creation Units are issued and redeemed principally for cash.", None),
    ("A8", "annual", "Notes to Financial Statements, 5. Creation and Redemption Transactions",
     "A transaction fee is applicable to each transaction regardless of the number of units purchased or",
     "on the Statements of Changes in Net Assets.", None),
    ("A9", "annual", "Schedule of Investments of the Fund, October 31, 2025: footnote to the Money Market Deposit Account",
     "The U.S. Bank Money Market Deposit Account (the", "The rate as of October 31, 2025 was 3.70%.",
     "INNOVATOR U.S. SMALL CAP POWER BUFFER ETF - OCTOBER"),
    ("A10", "annual", "Notes to Financial Statements: footnote (b) to the table of realized gain or loss on derivatives",
     "(b) Amount is included in realized gain/(loss) in-kind on the Statements of Operations.", None, None),
]

# Tables are transcribed (a layout conversion scrambles columns); every figure is checked against the page's text.
TABLES = [
    ("T1", "annual", "Schedule of Investments and Schedule of Written Options of the Fund, October 31, 2025 [table, transcribed]",
     ["Columns: description | notional amount | contracts | value",
      "PURCHASED OPTIONS - 106.3% | Call Options - 99.6%: iShares Russell 2000 ETF, Expiration: 09/30/2026; Exercise Price: $2.42 | $138,676,736 | 5,632 | $136,591,432",
      "PURCHASED OPTIONS | Put Options - 6.7%: iShares Russell 2000 ETF, Expiration: 09/30/2026; Exercise Price: $241.96 | 138,676,736 | 5,632 | 9,145,523",
      "TOTAL PURCHASED OPTIONS (Cost $143,545,825) | 145,736,955",
      "WRITTEN OPTIONS - (6.5)% | Call Options - (3.8)%: iShares Russell 2000 ETF, Expiration: 09/30/2026; Exercise Price: $283.53 | $(138,676,736) | (5,632) | $(5,169,782)",
      "WRITTEN OPTIONS | Put Options - (2.7)%: iShares Russell 2000 ETF, Expiration: 09/30/2026; Exercise Price: $205.67 | (138,676,736) | (5,632) | (3,798,784)",
      "TOTAL WRITTEN OPTIONS (Premiums received $8,485,782) | $(8,968,566)",
      "Money Market Deposit Account - 0.3% | 401,470",
      "Liabilities in Excess of Other Assets - (6.6)% | (9,055,737)",
      "TOTAL NET ASSETS - 100.0% | $137,082,688",
      "Footnotes to the options: Exchange-traded. 100 shares per contract. Purchased options: Non-income producing security; Held in connection with written option contracts."],
     ["138,676,736", "5,632", "136,591,432", "9,145,523", "143,545,825", "145,736,955", "5,169,782", "3,798,784", "8,485,782",
      "8,968,566", "401,470", "9,055,737", "137,082,688", "$2.42", "$241.96", "$283.53", "$205.67", "100 shares per contract",
      "Exchange-traded", "Non-income producing security", "Held in connection with written option contracts"],
     "INNOVATOR U.S. SMALL CAP POWER BUFFER ETF - OCTOBER"),
    ("T2", "annual", "Notes to Financial Statements: the effect of derivative instruments on the Statements of Operations [column headings, transcribed]",
     ["Amount of Realized Gain/(Loss) on Derivatives Recognized in Income, columns: Purchased Options(a) | Purchased Options in-kind(b) | Options Written | Options Written in-kind(b)"],
     ["Amount of Realized Gain/(Loss) on Derivatives Recognized in Income"], None),
]

# Searches over the whole text of the three documents for the things the reference had to assume.
NOT_FOUND = {
    "a number of days in the year (fee or interest accrual)": r"36[056][- ]days?|/ ?36[056]\b|day[- ]count|actual/36",
    "the order in which cost lots are relieved": r"first[- ]in,? first[- ]out|\bfifo\b|\blifo\b|highest cost|average cost|specific identification",
    "a policy or threshold for correcting a NAV error": r"nav error|pricing error|error correction|reprocess|materiality threshold|correct(ed|ion)? .{0,40}(nav|net asset value)|(nav|net asset value) .{0,40}(error|restat)",
    "a dollar amount for the transaction fee": r"transaction fee[^.]{0,80}\$ ?\d|\$ ?\d[^.]{0,80}transaction fee",
    "the number of shares in a creation unit": r"creation unit[^.]{0,60}\d{2},\d{3}|\d{2},\d{3} shares[^.]{0,60}creation unit",
    "how an option is adjusted when the reference security splits": r"(adjust|split)[^.]{0,80}(strike|exercise price|number of contracts|deliverable)",
    "how a basket is rounded to whole contracts": r"fractional contract|whole contract|round(ed|ing)? (up|down)|whole number of",
}
ALLOWED_HITS = {}   # hits that turn out to be about something else, read one by one: none after the patterns were tightened
CONTROLS = {        # the same search must find what IS stated, or a count of zero above would mean nothing
    "prospectus": r"rounded to the nearest cent",
    "sai": r"no later than T\+1",
    "annual": r"on the basis of identified cost",
}


def normal(name: str) -> tuple[str, list[str]]:
    with open(os.path.join(SRC, name, name + ".txt"), encoding="utf-8") as fh:
        lines = fh.read().splitlines()
    kept = [ln for ln in lines if not FURNITURE.match(ln)]
    return re.sub(r"\s+", " ", " ".join(kept)).strip(), lines


def cut(text: str, start: str, end: str | None, after: str | None) -> str:
    base = text.index(after) + len(after) if after else 0
    i = text.index(start, base)
    if end is None:
        return start
    j = text.index(end, i)
    return text[i:j + len(end)]


def main() -> int:
    os.makedirs(OUT, exist_ok=True)
    texts, raw, meta = {}, {}, {}
    for key, d in DOCS.items():
        texts[key], raw[key] = normal(d["file"])
        with open(os.path.join(SRC, d["file"], d["file"] + ".pdf"), "rb") as fh:
            blob = fh.read()
        meta[key] = {**d, "bytes": len(blob), "sha256": hashlib.sha256(blob).hexdigest(), "words": len(texts[key].split())}
    out = []
    for pid, doc, section, start, end, after in PASSAGES:
        out.append({"id": pid, "document": doc, "section": section, "kind": "quote", "text": cut(texts[doc], start, end, after)})
    for tid, doc, section, rows, must, after in TABLES:
        t = texts[doc]
        page = t[t.index(after):t.index(after) + 6000] if after else t
        missing = [m for m in must if m not in page]
        if missing:
            raise SystemExit(f"{tid}: not found on the page: {missing}")
        out.append({"id": tid, "document": doc, "section": section, "kind": "table", "text": "\n".join(rows)})
    searches = {}
    for what, pat in NOT_FOUND.items():
        hits = {}
        for key in DOCS:
            found = [(n + 1, ln.strip()[:160]) for n, ln in enumerate(raw[key]) if re.search(pat, ln, re.I)]
            hits[key] = found
        searches[what] = {"pattern": pat, "hits": {k: len(v) for k, v in hits.items()},
                          "lines": {k: v[:8] for k, v in hits.items() if v}, "read": ALLOWED_HITS.get(what, "")}
    for key, pat in CONTROLS.items():
        if not any(re.search(pat, ln, re.I) for ln in raw[key]):
            raise SystemExit(f"control search failed in {key}: {pat}")
    with open(os.path.join(OUT, "passages.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump({"documents": meta, "passages": out}, fh, indent=1, ensure_ascii=False)
    with open(os.path.join(OUT, "searches.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(searches, fh, indent=1, ensure_ascii=False)
    md = ["# Second fund: Innovator U.S. Small Cap Power Buffer ETF - October (KOCT)", "",
          "Collected 2026-11-16 by collect_koct.py from the full text of three public documents (sponsor's site, plain download).",
          "Passages are cut from the text between a start and an end anchor; tables are transcribed and their figures checked.", "",
          "| document | file | bytes | sha256 (first 16) | words |", "|---|---|---|---|---|"]
    for key, m in meta.items():
        md.append(f"| {m['title']} | {m['url']} | {m['bytes']:,} | {m['sha256'][:16]} | {m['words']:,} |")
    md += ["", "## Passages", ""]
    for p in out:
        md += [f"**{p['id']}** ({p['document']}; {p['section']})", "", "> " + p["text"].replace("\n", "\n> "), ""]
    md += ["## Searched for over the whole text and not found", "",
           "| what | pattern | hits: prospectus / sai / annual | read |", "|---|---|---|---|"]
    for what, s in searches.items():
        h = s["hits"]
        md.append(f"| {what} | `{s['pattern']}` | {h['prospectus']} / {h['sai']} / {h['annual']} | {s['read']} |")
    with open(os.path.join(OUT, "INDEX.md"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(md) + "\n")
    words = sum(len(p["text"].split()) for p in out)
    print(f"wrote docs_koct/passages.json ({len(out)} passages, {words} words), searches.json, INDEX.md")
    for what, s in searches.items():
        print(f"  {what:<58} hits {s['hits']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Collect the passages of the third fund's public documents by rule, from the full text of each document.

  python -I collect_tya.py            (the source files are downloads: read them as data, in isolated mode)

The fund: Simplify Intermediate Term Treasury Futures Strategy ETF (TYA), which holds Treasury futures. It was
chosen AFTER the question list (ds/fut_questions.py) had been written and fingerprinted. Three documents,
downloaded on 2026-11-16 from the sponsor's site with a plain client and converted with `pdftotext -layout -enc
UTF-8` (sources/<name>/<name>.pdf and .txt, not committed):
  prospectus   tya_prospectus.pdf   combined prospectus of the trust, dated November 1, 2026
  sai          tya_sai.pdf          combined statement of additional information, dated November 1, 2026
  annual       tya_annual.pdf       annual financial statements of the trust, June 30, 2026

SO THAT THE CHOICE OF PASSAGES CANNOT LEAN ON THE ANSWERS, passages are taken by rule, never one by one:
  WHOLE   every paragraph of a section named by its heading (the fund's own summary, how shares are priced, how to
          buy and sell, the notes on valuation, on futures, on fees and on share transactions, ...)
  GREP    every paragraph of a wider section that contains a word (the SAI's types of investments and the tax
          sections for "futures"; the fund's fee rows)
Paragraphs that are table rows of other funds are left out; two tables of the fund itself are transcribed and their
figures checked against the page. Writes docs_tya/passages.json and docs_tya/INDEX.md.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "sources")
OUT = os.path.join(HERE, "docs_tya")
FUND = "Simplify Intermediate Term Treasury Futures Strategy ETF"

DOCS = {
    "prospectus": {"file": "tya_prospectus", "title": "PROSPECTUS of the trust, dated November 1, 2026",
                   "url": "https://www.simplify.us/sites/default/files/etfs/prospectus/2026-11/Simplify-Combined-Prospectus-112026_25.pdf"},
    "sai": {"file": "tya_sai", "title": "STATEMENT OF ADDITIONAL INFORMATION of the trust, dated November 1, 2026",
            "url": "https://www.simplify.us/sites/default/files/etf/2026-11/Simplify-Combined-SAI-112026_25.pdf"},
    "annual": {"file": "tya_annual", "title": "ANNUAL FINANCIAL STATEMENTS of the trust, June 30, 2026 (audited)",
               "url": "https://www.simplify.us/sites/default/files/2026-09/Simplify-Annual-Financial-Statement-2026.pdf"},
}
FURNITURE = re.compile(r"^\s*(-?\d{1,3}-?|Simplify Exchange Traded Funds|Notes to Financial Statements( \(Continued\))?|June 30, 2026|"
                       r"See Notes to Financial Statements\.\s*\d*)\s*$")
TABLE_LINE = re.compile(r"\.{6,}|\. \. \. \.|\S\s{7,}\S.*\s{7,}\S")
OTHER_FUND = re.compile(r"^Simplify (?!Intermediate Term Treasury Futures)[A-Z][A-Za-z0-9 \-/]+(ETF|Fund)\b")
FUT = r"futures|\b1256\b|margin"

# The risks the prospectus lists for this fund that concern derivatives, leverage, cash, rebalancing, halts or the
# structure of an ETF; its other listed risks (active management, fixed income, markets, options, ...) are left out.
RISKS = ["Cash or Cash Equivalents Risk", "Counterparty Risk", "Derivatives Risk", "Early Close/Trading Halt Risk", "ETF Structure Risk",
         "ETF Structure Risks", "Futures Risk", "Leverage Risk", "Quarterly Rebalancing Risk", "Short-Term Investment Risk"]


def load(name: str) -> list[str]:
    with open(os.path.join(SRC, name, name + ".txt"), encoding="utf-8") as fh:
        return [ln.rstrip("\r\n") for ln in fh.read().split("\n")]


def find(lines: list[str], pattern: str, after: int = 0, nth: int = 1) -> int:
    rx = re.compile(pattern)
    for i in range(after, len(lines)):
        if rx.fullmatch(lines[i].strip()):
            nth -= 1
            if nth == 0:
                return i
    raise SystemExit(f"heading not found: {pattern}")


def paragraphs(lines: list[str], i: int, j: int) -> list[str]:
    """The paragraphs of lines[i:j]; a paragraph cut by a page break is put together again."""
    out, cur, broken = [], [], False
    for ln in lines[i:j]:
        if FURNITURE.match(ln):
            broken = True
            continue
        if not ln.strip():
            if cur:
                out.append((cur, broken))
                cur, broken = [], False
            continue
        cur.append(ln)
    if cur:
        out.append((cur, broken))
    merged = []
    for cur, _ in out:
        text = re.sub(r"\s+", " ", " ".join(cur)).strip()
        # a table: dot leaders anywhere, or half of the lines set in columns (a wide gap inside the line)
        table = (any(re.search(r"\.{6,}|\. \. \. \.", x) for x in cur) or
                 sum(bool(re.search(r"\S\s{6,}\S", x.strip())) for x in cur) >= 0.5 * len(cur))
        merged.append({"text": text, "table": table})
    # join a paragraph that ends without a full stop to the next one that starts in lower case (a page break)
    res = []
    for p in merged:
        if res and not res[-1]["table"] and not p["table"] and not re.search(r"[.:;?!)”\"]$", res[-1]["text"]) and re.match(r"[a-z(]", p["text"]):
            res[-1]["text"] += " " + p["text"]
        else:
            res.append(p)
    return [p for p in res]


def whole(lines, start, end, after=0, nth=1, keep_tables=False):
    i = find(lines, start, after, nth)
    j = find(lines, end, i + 1)
    return [p["text"] for p in paragraphs(lines, i + 1, j) if keep_tables or not p["table"]], i


def grep(lines, start, end, pattern, after=0):
    i = find(lines, start, after)
    j = find(lines, end, i + 1) if end else len(lines)
    rx = re.compile(pattern, re.I)
    return [p["text"] for p in paragraphs(lines, i + 1, j) if not p["table"] and rx.search(p["text"]) and not OTHER_FUND.match(p["text"])], i


def risk_definitions(lines, i, j) -> dict:
    """In the prospectus's shared section of risks, the definition under each run-in heading 'Some Risk.'"""
    out, name = {}, None
    for p in paragraphs(lines, i, j):
        m = re.match(r"^([A-Z][A-Za-z ,/\-]{3,60} Risks?)[.:]", p["text"])
        if m:
            name = m.group(1)
            out.setdefault(name, [])
        if name and not p["table"]:
            out[name].append(p["text"])
    return out


def main() -> int:
    os.makedirs(OUT, exist_ok=True)
    L = {k: load(d["file"]) for k, d in DOCS.items()}
    meta = {}
    for k, d in DOCS.items():
        with open(os.path.join(SRC, d["file"], d["file"] + ".pdf"), "rb") as fh:
            blob = fh.read()
        meta[k] = {**d, "bytes": len(blob), "sha256": hashlib.sha256(blob).hexdigest(), "words": sum(len(x.split()) for x in L[k])}
    out, seen = [], set()

    def add(doc, section, texts, kind="quote"):
        for t in texts:
            key = re.sub(r"\W+", "", t.lower())[:400]
            if len(t.split()) < 6 or key in seen:
                continue
            seen.add(key)
            out.append({"id": f"{doc[:2].upper()}{sum(p['document'] == doc for p in out) + 1:02d}", "document": doc,
                        "section": section, "kind": kind, "text": t})

    P, S, A = L["prospectus"], L["sai"], L["annual"]
    # ---- prospectus
    ps, i_sum = whole(P, r"FUND SUMMARY – SIMPLIFY INTERMEDIATE TERM TREASURY FUTURES STRATEGY ETF", r"FUND SUMMARY – .*")
    add("prospectus", "Fund Summary of the Fund [whole section]", ps)
    ps, i_add = whole(P, re.escape(FUND), r"Simplify Managed Futures Strategy ETF", after=i_sum + 400)
    add("prospectus", "Additional Information About the Fund's Principal Investment Strategies [the Fund's own part, whole]", ps)
    i_list = find(P, re.escape(FUND), after=i_add + 1)                         # the list of the Fund's risks
    j_list = find(P, r"Simplify Managed Futures Strategy ETF", after=i_list + 1)
    listed = [re.sub(r"^[●•\s]+", "", x.strip()) for x in P[i_list + 1:j_list] if x.strip() and not FURNITURE.match(x)]
    i_risk = find(P, r"Simplify Volatility Premium ETF", after=j_list)
    j_risk = find(P, r"PORTFOLIO MANAGERS", after=i_risk)
    defs = risk_definitions(P, i_risk, j_risk)
    for name in RISKS:
        if name in defs:
            add("prospectus", f"Principal Investment Risks [the definition of a risk listed for the Fund: {name}]", defs[name])
    ps, _ = grep(P, r"Simplify Volatility Premium ETF", r"PORTFOLIO MANAGERS", r"\bTYA\b|Intermediate Term Treasury Futures", after=j_list)
    add("prospectus", "Management [paragraphs that name the Fund]", ps)
    for start, end, label in ((r"HOW SHARES ARE PRICED", r"HOW TO BUY AND SELL SHARES", "How Shares Are Priced [whole section]"),
                              (r"HOW TO BUY AND SELL SHARES", r"FREQUENT PURCHASES AND REDEMPTIONS OF FUND SHARES", "How to Buy and Sell Shares [whole section]"),
                              (r"FREQUENT PURCHASES AND REDEMPTIONS OF FUND SHARES", r"DISTRIBUTION AND SERVICE PLAN", "Frequent Purchases and Redemptions of Fund Shares [whole section]")):
        ps, _ = whole(P, start, end, after=j_risk)
        add("prospectus", label, ps)
    ps, _ = grep(P, r"DIVIDENDS, OTHER DISTRIBUTIONS AND TAXES", r"FUND SERVICE PROVIDERS", FUT, after=j_risk)
    add("prospectus", "Dividends, Other Distributions and Taxes [paragraphs with the word futures, margin or 1256]", ps)
    # ---- SAI
    ps, _ = grep(S, r"TYPES OF INVESTMENTS", r"INVESTMENT RESTRICTIONS", r"futures")
    add("sai", "Types of Investments [every paragraph with the word futures]", ps)
    i_pr = find(S, r"PURCHASE, REDEMPTION AND PRICING OF SHARES")
    for start, end in (("Calculation of Share Price", "Creation Units"), ("Creation Units", "Authorized Participants"),
                       ("Transaction Fees", "Purchasing Creation Units"), ("Portfolio Deposit", "Purchase Orders"),
                       ("Cash Purchase Method", "Redeeming a Creation Unit"), ("Redemption Basket", "Redemption Requests"),
                       ("Cash Redemption Method", r"[A-Z][A-Za-z ,’'\-]{3,60}")):
        ps, _ = whole(S, re.escape(start), end if end.startswith("[") else re.escape(end), after=i_pr)
        add("sai", f"Purchase, Redemption and Pricing of Shares: {start} [whole subsection]", ps)
    ps, _ = grep(S, r"Cash Redemption Method", None, r"futures|\b1256\b", after=i_pr)
    add("sai", "Tax Status [every paragraph with the word futures or 1256]", ps)
    # ---- annual financial statements
    i_notes = find(A, r"3\. Significant Accounting Policies")
    ps, _ = whole(A, r"3\. Significant Accounting Policies", r"Investment Valuation", after=i_notes - 1)
    add("annual", "Notes to Financial Statements, 3. Significant Accounting Policies [opening, whole]", ps)
    ps, _ = whole(A, r"Investment Valuation", r"Simplify Aggregate Bond ETF", after=i_notes)
    add("annual", "Notes to Financial Statements, 3. Significant Accounting Policies: Investment Valuation [whole]", ps)
    ps, _ = whole(A, r"Investment Transactions and Related Income", r"Income Tax Information and Distributions to Shareholders", after=i_notes)
    add("annual", "Notes to Financial Statements, 3. Significant Accounting Policies: Investment Transactions and Related Income [whole]", ps)
    ps, _ = grep(A, r"Income Tax Information and Distributions to Shareholders", r"4\. Derivative Financial Instruments", FUT, after=i_notes)
    add("annual", "Notes to Financial Statements, 3. Significant Accounting Policies: Income Tax Information [paragraphs with the word futures, margin or 1256]", ps)
    ps, _ = whole(A, r"4\. Derivative Financial Instruments", r"Option Contracts", after=i_notes)
    add("annual", "Notes to Financial Statements, 4. Derivative Financial Instruments, with Futures Contracts [whole]", ps)
    ps, _ = whole(A, r"6\. Investment Advisory Agreement and Other Agreements", r"7\. Investment Transactions", after=i_notes)
    add("annual", "Notes to Financial Statements, 6. Investment Advisory Agreement and Other Agreements [whole, without the tables]", ps)
    ps, _ = whole(A, r"8\. Fund Share Transactions", r"9\. Federal Income Taxes", after=i_notes)
    add("annual", "Notes to Financial Statements, 8. Fund Share Transactions [whole]", ps)
    ps, _ = grep(A, r"9\. Federal Income Taxes", r"10\. Improvements to Income Tax Disclosures", FUT, after=i_notes)
    add("annual", "Notes to Financial Statements, 9. Federal Income Taxes [paragraphs with the word futures, margin or 1256]", ps)
    ps, _ = grep(A, r"3\. Significant Accounting Policies", r"12\. Subsequent Events", r"futures|margin", after=i_notes - 1)
    add("annual", "Notes to Financial Statements [any other paragraph with the word futures or margin]", ps)
    # ---- the Fund's own tables, transcribed; every figure is checked against the page
    text_a = re.sub(r"\s+", " ", " ".join(A))
    page = text_a[text_a.index(FUND + " Shares Value"):][:6000]
    rows = ["Schedule of Investments of the Fund, June 30, 2026. Columns: description | shares | value",
            "U.S. Exchange-Traded Funds – 99.2% | Money Market ETFs - 99.2%: Simplify Government Money Market ETF (Cost $65,673,982) | 656,500 | $65,689,390",
            "Money Market Fund – 0.1%: BNY Dreyfus Treasury Obligations Cash Management Fund, Institutional Shares, 3.52% (Cost $76,080) | 76,080 | 76,080",
            "Total Investments – 99.3% (Cost $65,750,062) | $65,765,470",
            "Other Assets in Excess of Liabilities – 0.7% | 490,991",
            "Net Assets – 100.0% | $66,256,461",
            "At June 30, 2026, open futures contracts were as follows. Columns: contract | number of contracts | notional value | expiration date | value/unrealized appreciation (depreciation)",
            "Long position contracts: U.S. 2 Years Note (CBT) | 1,803 | $198,132,797 | 9/21/26 | $605,294"]
    must = ["656,500", "65,689,390", "65,673,982", "76,080", "65,765,470", "65,750,062", "490,991", "66,256,461", "1,803", "198,132,797",
            "9/21/26", "605,294", "U.S. 2 Years Note (CBT)", "open futures contracts were as follows", "Long position contracts"]
    missing = [m for m in must if m not in page]
    if missing:
        raise SystemExit(f"schedule: not found on the page: {missing}")
    out.append({"id": "AT1", "document": "annual", "section": "Schedule of Investments of the Fund, June 30, 2026 [table, transcribed]",
                "kind": "table", "text": "\n".join(rows)})
    fee = [x.strip() for x in A if re.match(r"\s*Simplify\s+Intermediate Term Treasury Futures Strategy ETF\.{5,}\s*\d\.\d\d%", x)]
    if len(fee) != 1:
        raise SystemExit(f"fee row: expected one, found {len(fee)}")
    rate = re.search(r"(\d\.\d\d%)", fee[0]).group(1)
    out.append({"id": "AT2", "document": "annual", "section": "Notes to Financial Statements, 6. Investment Advisory Agreement: the table of management fee rates [the Fund's row, transcribed]",
                "kind": "table", "text": f"{FUND} | {rate}"})
    with open(os.path.join(OUT, "passages.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump({"documents": meta, "risks_listed_for_the_fund": listed, "passages": out}, fh, indent=1, ensure_ascii=False)
    md = [f"# Third fund: {FUND} (TYA)", "",
          "Collected 2026-11-16 by collect_tya.py from the full text of three public documents (sponsor's site, plain download),",
          "after the question list ds/fut_questions.py had been written. Passages are taken by rule (whole sections named by their",
          "heading, or every paragraph of a wider section that contains a word), not chosen one by one.", "",
          "| document | file | bytes | sha256 (first 16) | words |", "|---|---|---|---|---|"]
    for k, m in meta.items():
        md.append(f"| {m['title']} | {m['url']} | {m['bytes']:,} | {m['sha256'][:16]} | {m['words']:,} |")
    md += ["", "Risks the prospectus lists for the fund: " + "; ".join(listed), "", "## Passages", ""]
    for p in out:
        md += [f"**{p['id']}** ({p['document']}; {p['section']})", "", "> " + p["text"].replace("\n", "\n> "), ""]
    with open(os.path.join(OUT, "INDEX.md"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(md) + "\n")
    by = {}
    for p in out:
        by.setdefault((p["document"], p["section"]), [0, 0])
        by[(p["document"], p["section"])][0] += 1
        by[(p["document"], p["section"])][1] += len(p["text"].split())
    for (doc, sec), (n, w) in by.items():
        print(f"  {doc:<11}{n:>3} passages {w:>6} words  {sec[:110]}")
    print(f"wrote docs_tya/passages.json ({len(out)} passages, {sum(len(p['text'].split()) for p in out)} words) and INDEX.md")
    print("risks listed for the fund:", "; ".join(listed))
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Convert issuer NAV downloads into data/nav/<TICKER>.csv (date,nav[,nav_nonfv,exdiv]).

Two formats are read, both with the standard library:
  - State Street "navhist-us-en-<ticker>.xlsx": a real xlsx (zip of XML); sheet 1 has a header row
    "Date, NAV, Shares Outstanding, Total Net Assets" after two title rows; dates like 06-Nov-2026.
  - iShares "<Fund-Name>_fund.xls": SpreadsheetML 2003 (plain XML). The 'Historical' worksheet has
    "As Of, NAV per Share, Ex-Dividends, Shares Outstanding, Non-FV NAV"; dates like Nov 06, 2026.
    Non-FV NAV is the NAV before fair-value adjustment of foreign closes, which for the international
    funds is the single most informative number in the file.
"""
from __future__ import annotations
import csv
import datetime as dt
import glob
import html
import os
import re
import zipfile

from .util import NAV_DIR

ISHARES_NAME_TO_TICKER = [("Treasury", "TLT"), ("Bitcoin", "IBIT"), ("Emerging", "EEM"), ("Germany", "EWG"),
                          ("Japan", "EWJ"), ("iBoxx", "LQD")]


def _parse_date(s: str) -> str | None:
    s = s.strip()
    for fmt in ("%d-%b-%Y", "%b %d, %Y", "%m/%d/%Y", "%Y-%m-%d"):
        try:
            return dt.datetime.strptime(s, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _num(s: str) -> float | None:
    s = (s or "").strip().replace(",", "")
    if s in ("", "--", "-", "N/A"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def read_ssga_xlsx(path: str) -> tuple[str | None, list]:
    z = zipfile.ZipFile(path)
    ss = []
    if "xl/sharedStrings.xml" in z.namelist():
        ss = [html.unescape("".join(re.findall(r"<t[^>]*>(.*?)</t>", si, re.S)))
              for si in re.findall(r"<si>(.*?)</si>", z.read("xl/sharedStrings.xml").decode("utf-8", "ignore"), re.S)]
    sheet = sorted(n for n in z.namelist() if n.startswith("xl/worksheets/sheet"))[0]
    xml = z.read(sheet).decode("utf-8", "ignore")
    ticker, rows, header = None, [], None
    for row in re.findall(r"<row[^>]*>(.*?)</row>", xml, re.S):
        cells = []
        for m in re.finditer(r'<c r="([A-Z]+)\d+"([^>]*)>(.*?)</c>', row, re.S):
            attrs, inner = m.group(2), m.group(3)
            v = re.search(r"<v>(.*?)</v>", inner, re.S)
            val = v.group(1) if v else ""
            if 't="s"' in attrs and val.isdigit():
                val = ss[int(val)]
            cells.append(val.strip())
        if not cells:
            continue
        if cells[0].startswith("Ticker Symbol") and len(cells) > 1:
            ticker = re.sub(r"[^A-Z]", "", cells[1].upper())
        elif cells[0] == "Date":
            header = cells
        elif header:
            d = _parse_date(cells[0]) if cells else None
            nav = _num(cells[1]) if len(cells) > 1 else None
            if d and nav is not None:
                rows.append({"date": d, "nav": nav})
    return ticker, rows


def read_ishares_xml(path: str) -> tuple[str | None, list]:
    xml = open(path, encoding="utf-8", errors="ignore").read()
    ticker = next((t for frag, t in ISHARES_NAME_TO_TICKER if frag.lower() in os.path.basename(path).lower()), None)
    m = re.search(r'<ss:Worksheet ss:Name="Historical">(.*?)</ss:Worksheet>', xml, re.S)
    if not m:
        return ticker, []
    rows, header = [], None
    for row in re.findall(r"<ss:Row[^>]*>(.*?)</ss:Row>", m.group(1), re.S):
        cells = [html.unescape(re.sub(r"<[^>]+>", "", c)).strip() for c in re.findall(r"<ss:Cell[^>]*>(.*?)</ss:Cell>", row, re.S)]
        if not cells:
            continue
        if cells[0] == "As Of":
            header = cells
            continue
        if header is None:
            continue
        d = _parse_date(cells[0])
        if not d:
            continue
        rec = {"date": d}
        for name, val in zip(header, cells):
            if name == "NAV per Share":
                rec["nav"] = _num(val)
            elif name == "Non-FV NAV":
                rec["nav_nonfv"] = _num(val)
            elif name == "Ex-Dividends":
                rec["exdiv"] = _num(val)
        if rec.get("nav") is not None:
            rows.append(rec)
    return ticker, rows


def convert_all() -> dict:
    out = {}
    for p in sorted(glob.glob(os.path.join(NAV_DIR, "*"))):
        low = p.lower()
        if low.endswith(".csv"):
            continue
        try:
            if low.endswith(".xlsx"):
                ticker, rows = read_ssga_xlsx(p)
            elif low.endswith(".xls"):
                ticker, rows = read_ishares_xml(p)
            else:
                continue
        except Exception as e:  # noqa: BLE001
            print(f"[nav] {os.path.basename(p)}: FAILED {str(e)[:120]}")
            continue
        if not ticker or not rows:
            print(f"[nav] {os.path.basename(p)}: could not identify ticker or found no NAV rows")
            continue
        rows.sort(key=lambda r: r["date"])
        cols = ["date", "nav"] + [c for c in ("nav_nonfv", "exdiv") if any(c in r for r in rows)]
        dest = os.path.join(NAV_DIR, f"{ticker}.csv")
        with open(dest, "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            for r in rows:
                w.writerow(r)
        n_fv = sum(1 for r in rows if r.get("nav_nonfv") is not None)
        print(f"[nav] {ticker}: {len(rows)} days {rows[0]['date']}..{rows[-1]['date']}" + (f", non-FV NAV on {n_fv}" if n_fv else "") + f" -> {os.path.basename(dest)}")
        out[ticker] = {"rows": len(rows), "from": rows[0]["date"], "to": rows[-1]["date"], "nonfv": n_fv}
    return out

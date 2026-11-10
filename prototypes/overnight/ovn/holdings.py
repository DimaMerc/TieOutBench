"""Convert an issuer's holdings CSV (iShares format) into data/holdings/<TICKER>.json for the evidence
layer, attaching a US news ticker (listing or ADR) where one is known.

iShares CSVs start with a preamble (fund name, "Fund Holdings as of", ...) and then a header row that
begins with "Ticker,". Weights are already in percent. Rows whose Asset Class is not Equity (cash,
derivatives, futures) are dropped.

The ADR map below is best effort and must be checked before anything is published; a holding without
a mapping keeps its local ticker, appears in the prompt by name, and fetches no news.
"""
from __future__ import annotations
import csv
import glob
import io
import os

from .util import HOLD_DIR, write_json, read_json

# local ticker or name fragment -> US news ticker. Checked against public ADR listings as of 2026
# only to the extent noted in the README; treat as a draft map.
ADR_MAP = {
    # Japan (EWJ)
    "TOYOTA MOTOR": "TM", "SONY GROUP": "SONY", "MITSUBISHI UFJ": "MUFG", "HITACHI": "HTHIY",
    "SUMITOMO MITSUI FINANCIAL": "SMFG", "MIZUHO FINANCIAL": "MFG", "NINTENDO": "NTDOY",
    "KEYENCE": "KYCCF", "TOKIO MARINE": "TKOMY", "RECRUIT HOLDINGS": "RCRUY", "SHIN-ETSU": "SHECY",
    "FAST RETAILING": "FRCOY", "HONDA MOTOR": "HMC", "TAKEDA": "TAK", "SOFTBANK GROUP": "SFTBY",
    "DAIICHI SANKYO": "DSNKY", "NIPPON TELEGRAPH": "NTTYY", "KDDI": "KDDIY", "ITOCHU": "ITOCY",
    "MITSUBISHI CORP": "MSBHF", "MITSUBISHI ELECTRIC": "MIELY", "MITSUBISHI HEAVY": "MHVYF",
    "MITSUBISHI ESTATE": "MITEY", "MITSUBISHI": "MSBHF", "MITSUI & CO": "MITSY", "TOKYO ELECTRON": "TOELY", "DISCO CORP": "DSCSY",
    "ADVANTEST": "ATEYY", "CHUGAI": "CHGCY", "ORIENTAL LAND": "OLCLY", "DAIKIN": "DKILY",
    "MURATA": "MRAAY", "NOMURA": "NMR", "ORIX": "IX", "CANON": "CAJPY", "SEVEN & I": "SVNDY",
    "JAPAN TOBACCO": "JAPAY", "DENSO": "DNZOY", "FANUC": "FANUY", "SMC CORP": "SMCAY", "HOYA": "HOCPY",
    "NIDEC": "NJDCY", "KOMATSU": "KMTUY", "BRIDGESTONE": "BRDCY", "ASTELLAS": "ALPMY", "SUZUKI": "SZKMY",
    "RENESAS": "RNECY", "PANASONIC": "PCRFY", "SUMITOMO CORP": "SSUMY", "MARUBENI": "MARUY",
    # Germany (EWG)
    "SAP": "SAP", "SIEMENS ENERGY": "SMNEY", "SIEMENS HEALTHINEERS": "SMMNY", "SIEMENS AG": "SIEGY",
    "SIEMENS N": "SIEGY", "ALLIANZ": "ALIZY", "DEUTSCHE TELEKOM": "DTEGY",
    "MUENCHENER RUECK": "MURGY", "MUNICH RE": "MURGY", "DEUTSCHE BANK": "DB",
    "INFINEON": "IFNNY", "BASF": "BASFY", "MERCEDES-BENZ": "MBGYY", "RHEINMETALL": "RNMBY",
    "ADIDAS": "ADDYY", "BAYER": "BAYRY", "BMW": "BMWYY", "VOLKSWAGEN": "VWAGY", "DEUTSCHE BOERSE": "DBOEY",
    "COMMERZBANK": "CRZBY", "HEIDELBERG": "HDELY", "E.ON": "EONGY", "RWE": "RWEOY", "HENKEL": "HENKY",
    "BEIERSDORF": "BDRFY", "FRESENIUS": "FSNUY", "MERCK KGAA": "MKKGY", "SIEMENS HEALTHINEERS": "SMMNY",
    "DEUTSCHE POST": "DHLGY", "DHL GROUP": "DHLGY", "DHL AG": "DHLGY", "VONOVIA": "VONOY", "HANNOVER RUECK": "HVRRY",
    "SYMRISE": "SYIEY", "ZALANDO": "ZLNDY", "PORSCHE": "POAHY", "CONTINENTAL": "CTTAY", "PUMA": "PUMSY",
    "BRENNTAG": "BNTGY", "SARTORIUS": "SARTF", "QIAGEN": "QGEN", "DAIMLER TRUCK": "DTRUY",
    # Emerging markets (EEM) — many large holdings have no liquid US listing
    "TAIWAN SEMICONDUCTOR": "TSM", "TENCENT": "TCEHY", "ALIBABA": "BABA", "HDFC BANK": "HDB",
    "ICICI BANK": "IBN", "INFOSYS": "INFY", "MEITUAN": "MPNGY", "PDD HOLDINGS": "PDD", "XIAOMI": "XIACY",
    "CHINA CONSTRUCTION BANK": "CICHY", "HON HAI": "HNHPF", "NETEASE": "NTES", "BAIDU": "BIDU",
    "JD.COM": "JD", "TRIP.COM": "TCOM", "BYD": "BYDDY", "PING AN": "PNGAY", "AL RAJHI": "",
    "NASPERS": "NPSNY", "VALE": "VALE", "PETROBRAS": "PBR", "ITAU UNIBANCO": "ITUB", "AMERICA MOVIL": "AMX",
    "WALMART DE MEXICO": "WMMVY", "GRUPO MEXICO": "GMBXF", "SAUDI": "", "KB FINANCIAL": "KB",
    "SHINHAN": "SHG", "POSCO": "PKX", "SK HYNIX": "", "SAMSUNG ELECTRONICS": "", "MEDIATEK": "",
    "RELIANCE INDUSTRIES": "", "BHARTI AIRTEL": "", "AXIS BANK": "", "TATA CONSULTANCY": "",
    "HYUNDAI MOTOR": "HYMTF", "LG ENERGY": "", "KIA": "", "NU HOLDINGS": "NU", "MERCADOLIBRE": "MELI",
    "SEA LTD": "SE", "GRAB": "GRAB", "FIRST QUANTUM": "", "ANGLOGOLD": "AU", "GOLD FIELDS": "GFI",
    "HARMONY GOLD": "HMY", "SASOL": "SSL", "MTN GROUP": "MTNOY", "STANDARD BANK": "SGBLY",
    "FIRSTRAND": "FANDY", "CAPITEC": "", "BANK CENTRAL ASIA": "PBCRY", "DBS": "DBSDY",
    "UNITED OVERSEAS": "UOVEY", "OVERSEA-CHINESE": "OVCHY", "EMIRATES NBD": "", "QATAR NATIONAL": "",
    "KASPI": "KSPI", "CTBC": "", "FUBON": "", "CATHAY FINANCIAL": "", "DELTA ELECTRONICS": "",
    "QUANTA COMPUTER": "", "ASE TECHNOLOGY": "ASX", "UNITED MICROELECTRONICS": "UMC", "CHUNGHWA": "CHT",
    "WIWYNN": "", "LARGAN": "", "CHINA MERCHANTS BANK": "CIHKY", "INDUSTRIAL & COMMERCIAL BANK": "IDCBY",
    "INDUSTRIAL AND COMMERCIAL BANK": "IDCBY",
    "BANK OF CHINA": "BACHY", "AGRICULTURAL BANK": "ACGBY", "CNOOC": "", "CHINA MOBILE": "CHL",
    "KWEICHOW MOUTAI": "", "CONTEMPORARY AMPEREX": "", "ZIJIN": "ZIJMY", "ANTA": "ANPDY",
    "LI AUTO": "LI", "XPENG": "XPEV", "NIO": "NIO", "POP MART": "PMRTY", "SEMICONDUCTOR MANUFACTURING": "SMICY",
}


def map_news_ticker(name: str, symbol: str, location: str = "") -> str:
    """Best-effort US news ticker. A holding listed in the United States keeps its own symbol. Anything
    listed elsewhere is mapped by company name, because a German local ticker such as DTE or ALV
    collides with an unrelated US company (DTE Energy, Autoliv) in a US news feed. No match -> ''."""
    s = (symbol or "").strip().upper()
    loc = (location or "").strip().lower()
    us_style = bool(s) and s.isalpha() and len(s) <= 5
    if loc == "united states" and us_style:
        return s
    up = (name or "").upper()
    for frag, t in ADR_MAP.items():
        if frag in up:
            return t
    if not loc and us_style:   # location unknown (e.g. AlphaVantage rows): trust the symbol
        return s
    return ""


def parse_ishares_csv(text: str) -> list:
    """-> [{symbol, name, weight (percent), sector, location, exchange}] for Equity rows, sorted by weight."""
    lines = text.splitlines()
    start = next((i for i, ln in enumerate(lines) if ln.startswith("Ticker,") or ln.startswith('"Ticker"')), None)
    if start is None:
        raise ValueError("no header row starting with 'Ticker,' found; is this an iShares holdings CSV?")
    rdr = csv.DictReader(io.StringIO("\n".join(lines[start:])))
    rows = []
    for r in rdr:
        if not r.get("Ticker"):
            continue
        if (r.get("Asset Class") or "").strip().lower() != "equity":
            continue
        try:
            w = float((r.get("Weight (%)") or "0").replace(",", ""))
        except ValueError:
            continue
        rows.append({"symbol": r["Ticker"].strip(), "name": (r.get("Name") or "").strip(), "weight": w,
                     "sector": (r.get("Sector") or "").strip(), "location": (r.get("Location") or "").strip(),
                     "exchange": (r.get("Exchange") or "").strip()})
    rows.sort(key=lambda x: -x["weight"])
    return rows


def convert_file(path: str, ticker: str, n: int = 15) -> dict:
    with open(path, encoding="utf-8-sig") as fh:
        rows = parse_ishares_csv(fh.read())
    top = rows[:n]
    for h in top:
        h["news_ticker"] = map_news_ticker(h["name"], h["symbol"], h.get("location", ""))
    out = {"ticker": ticker, "source_file": os.path.basename(path), "n_equity_rows": len(rows),
           "top_weight_sum": round(sum(h["weight"] for h in top), 2),
           "unmapped": [h["symbol"] + " " + h["name"] for h in top if not h["news_ticker"]],
           "holdings": top}
    write_json(os.path.join(HOLD_DIR, f"{ticker}.json"), out)
    return out


def convert_all() -> dict:
    """Every data/holdings/<TICKER>.csv -> <TICKER>.json."""
    res = {}
    for p in sorted(glob.glob(os.path.join(HOLD_DIR, "*.csv"))):
        # accept EWJ.csv as well as the issuer's default EWJ_holdings.csv
        t = os.path.splitext(os.path.basename(p))[0].upper()
        for suffix in ("_HOLDINGS", "-HOLDINGS", "_FUND"):
            if t.endswith(suffix):
                t = t[: -len(suffix)]
        try:
            o = convert_file(p, t)
            res[t] = o
            print(f"[holdings] {t}: {o['n_equity_rows']} equity rows, top {len(o['holdings'])} = {o['top_weight_sum']}% of fund, "
                  f"unmapped for news: {len(o['unmapped'])} -> {o['unmapped'][:4]}")
        except Exception as e:  # noqa: BLE001
            print(f"[holdings] {t}: FAILED {e}")
    if not res:
        print(f"[holdings] no CSV files in {HOLD_DIR}")
    return res

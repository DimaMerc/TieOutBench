# scratch_attacker6.py - attacker 6 (FALSE POSITIVES) battery for the eval #7 nav_oversight grader.
# Builds correct answers (schema-serialised oracle, every value right) and changes ONLY the form.
# Usage (project interpreter, from the repo root):
#   python outputs/eval7-live/gaming-review/scratch_attacker6.py --group P1date [--verbose]
#   python outputs/eval7-live/gaming-review/scratch_attacker6.py --list
#   python outputs/eval7-live/gaming-review/scratch_attacker6.py --saved            (review the 28 saved live answers)
#   python outputs/eval7-live/gaming-review/scratch_attacker6.py --decisions         (decision-phrase classifier table)
# Nothing here edits a repository file; it only builds answer dicts and runs the grader on them.
import sys, os, json, copy, re, datetime, argparse
sys.stdout.reconfigure(encoding="utf-8")
REPO = r"C:\Projects\finance-llm-evals"
sys.path.insert(0, REPO)
os.chdir(REPO)
from harness.rubric import load_case, load_rubric, materialize, rubric_path_for
from harness.graders import grade
from harness.scoring import score
from harness import suites
from harness.suites import nav_oversight as nv
from harness.live_nav_oversight import oracle_to_schema

CASES = {"break": os.path.join(REPO, "cases", "grsl-nav-2026.case.yaml"),
         "clean": os.path.join(REPO, "cases", "grsl-nav-2026-clean.case.yaml")}
_S = {}


def setup(k):
    if k not in _S:
        case = load_case(CASES[k])
        rubric = load_rubric(rubric_path_for(case))
        suite = suites.for_case(case)
        atoms = materialize(rubric, case)
        gold = dict(case["gold"])
        gold["manifest"] = case.get("manifest", {})
        gold["_snapshot"] = case.get("snapshot")
        gold["_claims"] = case.get("claims")
        gold["_documents"] = case.get("documents")
        _S[k] = (case, rubric, suite, atoms, gold)
    return _S[k]


def base(k):
    return oracle_to_schema(setup(k)[0])


def run(k, ans):
    case, rubric, suite, atoms, gold = setup(k)
    try:
        verdicts, rg = grade(atoms, copy.deepcopy(ans), gold, rubric, suite)
        res = score(atoms, verdicts, rg, rubric, case_id=case["case_id"], refusal_cp=suite.REFUSAL_CP)
    except Exception as e:                      # a grader exception on an answer = no score at all in the live driver
        return dict(crash=f"{type(e).__name__}: {e}")
    failed = []
    for a in atoms:
        v = verdicts.get(a.id)
        if a.points > 0 and (v is None or v.met < 0.999):
            failed.append((a.id, round(v.met, 3) if v else None, (v.note if v else "")))
        elif a.points < 0 and v is not None and v.met >= 0.999:
            failed.append((a.id + "(PEN)", 1.0, v.note))
    return dict(gated=res.case_gated, ungated=res.case_ungated, allpass=res.allpass, gates=list(res.fired_gates),
                flags=list(res.flags), R=res.e6[0], G=res.e6[1],
                cps={c: round(v["score_gated"], 3) for c, v in res.checkpoints.items()}, failed=failed)


# ---------------------------------------------------------------- small helpers
def _flat(o, p=""):
    out = {}
    if isinstance(o, dict):
        if not o and p:
            out[p] = {}
        for k, v in o.items():
            out.update(_flat(v, f"{p}.{k}" if p else str(k)))
    elif isinstance(o, list):
        if not o and p:
            out[p] = []
        for i, v in enumerate(o):
            out.update(_flat(v, f"{p}[{i}]"))
    else:
        out[p] = o
    return out


def diff(a, b, maxn=6):
    fa, fb = _flat(a), _flat(b)
    keys = [k for k in dict.fromkeys(list(fa) + list(fb)) if fa.get(k, "<absent>") != fb.get(k, "<absent>")]
    parts = []
    for k in keys[:maxn]:
        o, n = fa.get(k, "<absent>"), fb.get(k, "<absent>")
        so, sn = json.dumps(o, ensure_ascii=False), json.dumps(n, ensure_ascii=False)
        if len(so) > 60:
            so = so[:57] + "..."
        if len(sn) > 70:
            sn = sn[:67] + "..."
        parts.append(f"{k}: {so} -> {sn}")
    if len(keys) > maxn:
        parts.append(f"(+{len(keys) - maxn} more changed leaves)")
    return "; ".join(parts)


def _step(cur, p):
    m = re.match(r"^(.+)\[(\d+)\]$", p)
    if m:
        return cur[m.group(1)][int(m.group(2))]
    return cur[p]


def sp(a, path, val):
    parts = path.split(".")
    cur = a
    for p in parts[:-1]:
        cur = _step(cur, p)
    last = parts[-1]
    m = re.match(r"^(.+)\[(\d+)\]$", last)
    if m:
        cur[m.group(1)][int(m.group(2))] = val
    else:
        cur[last] = val


def gp(a, path):
    cur = a
    for p in path.split("."):
        cur = _step(cur, p)
    return cur


def map_nums(o, fn, path=()):
    if isinstance(o, dict):
        return {k: map_nums(v, fn, path + (k,)) for k, v in o.items()}
    if isinstance(o, list):
        return [map_nums(v, fn, path + (i,)) for i, v in enumerate(o)]
    if isinstance(o, (int, float)) and not isinstance(o, bool):
        return fn(path, o)
    return o


PCT_KEYS = {"reprocessing_pct", "oversight_band_pp", "return_pct", "nav_error_pct", "index_return_pct", "expected_move_pct",
            "admin_move_pct", "recomputed_move_pct", "admin_deviation_pp", "recomputed_deviation_pp"}
DOLLAR_KEYS = {"market_value", "amount", "admin_total_assets", "admin_total_liabilities", "admin_total_net_assets",
               "admin_nav_per_share", "notional", "unrealized_value", "financing_accrued_payable", "total_assets",
               "total_liabilities", "total_net_assets", "nav_per_share", "fund_level_error", "nav_error_per_share",
               "corrected_nav_per_share", "prior_nav_per_share", "admin_prelim_nav_per_share", "per_share_floor_usd",
               "admin_value", "independent_value"}


def lastkey(path):
    for p in reversed(path):
        if isinstance(p, str):
            return p
    return ""


def commas(v):
    if isinstance(v, int):
        return f"{v:,}"
    s = f"{v:,.4f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def money(v):
    s = commas(v)
    return ("-$" + s[1:]) if s.startswith("-") else "$" + s


def is_dollar(path):
    return lastkey(path) in DOLLAR_KEYS or "prices" in path or (lastkey(path) == "value" and "twins" in path)


def is_pct(path):
    return lastkey(path) in PCT_KEYS


# ---------------------------------------------------------------- the battery
TESTS = []


def T(tid, group, desc, fn, cases=("break", "clean"), arguable=False):
    TESTS.append(dict(id=tid, group=group, desc=desc, fn=fn, cases=cases, arguable=arguable))


# ---- P1: dates (GATE.DATE is a HARD gate whose dependents are C1, C2, C3, D1) ----
D1_ = datetime.date(2026, 6, 23)
D0_ = datetime.date(2026, 6, 22)
DATE_FORMS = {
    "iso+T00:00:00": lambda d: d.isoformat() + "T00:00:00",
    "iso+T00:00:00Z": lambda d: d.isoformat() + "T00:00:00Z",
    "iso+T00:00:00-04:00": lambda d: d.isoformat() + "T00:00:00-04:00",
    "str(datetime)": lambda d: d.isoformat() + " 00:00:00",
    "iso padded spaces": lambda d: " " + d.isoformat() + " ",
    "iso+weekday": lambda d: d.isoformat() + " (" + d.strftime("%a") + ")",
    "mm/dd/yyyy": lambda d: d.strftime("%m/%d/%Y"),
    "m/d/yyyy": lambda d: f"{d.month}/{d.day}/{d.year}",
    "yyyy/mm/dd": lambda d: d.strftime("%Y/%m/%d"),
    "yyyy-m-d": lambda d: f"{d.year}-{d.month}-{d.day}",
    "June 23, 2026": lambda d: d.strftime("%B %d, %Y"),
    "23 June 2026": lambda d: d.strftime("%d %B %Y"),
    "23-Jun-2026": lambda d: d.strftime("%d-%b-%Y"),
    "23.06.2026": lambda d: d.strftime("%d.%m.%Y"),
    "yyyymmdd str": lambda d: d.strftime("%Y%m%d"),
    "yyyymmdd int": lambda d: int(d.strftime("%Y%m%d")),
}
for _n, _f in DATE_FORMS.items():
    def _mk(f):
        def fn(a, k):
            a["P1"]["valuation_date"] = f(D1_)
            a["P1"]["prior_valuation_date"] = f(D0_)
        return fn
    T("P1date:" + _n, "P1date", f"valuation_date/prior_valuation_date as {_n}", _mk(_f))

# ---- P1: identity strings ----
T("P1id:fund lower-case", "P1id", "fund name lower-case",
  lambda a, k: sp(a, "P1.fund", a["P1"]["fund"].lower()))
T("P1id:fund +(GRSL)", "P1id", "fund name with ticker in brackets appended",
  lambda a, k: sp(a, "P1.fund", a["P1"]["fund"] + " (GRSL)"))
T("P1id:fund 2X", "P1id", "fund name with 2X capital",
  lambda a, k: sp(a, "P1.fund", a["P1"]["fund"].replace("2x", "2X")))
T("P1id:fund whitespace", "P1id", "fund name double-spaced + trailing space",
  lambda a, k: sp(a, "P1.fund", " " + a["P1"]["fund"].replace(" Daily", "  Daily") + " "))
T("P1id:ticker lower", "P1id", "ticker 'grsl'", lambda a, k: sp(a, "P1.ticker", "grsl"))
T("P1id:package_id lower", "P1id", "package_id lower-case",
  lambda a, k: sp(a, "P1.package_id", a["P1"]["package_id"].lower()))

# ---- P1: numbers ----
for _lab, _v in [("2x", "2x"), ("2.0x", "2.0x"), ("2X", "2X"), ("2 x", "2 x"), ("200%", "200%"), ("int 200", 200), ("2:1", "2:1"), ("'2.0'", "2.0"), ("int 2", 2)]:
    T("P1num:leverage " + _lab, "P1num", f"leverage as {_lab!r}", (lambda v: (lambda a, k: sp(a, "P1.leverage", v)))(_v))
for _lab, _v in [("'4,000,000'", "4,000,000"), ("'4.0M'", "4.0M"), ("'4 million'", "4 million"), ("'4,000,000 shares'", "4,000,000 shares"), ("float 4e6", 4000000.0)]:
    T("P1num:prior_shares " + _lab, "P1num", f"prior_shares_outstanding as {_lab}", (lambda v: (lambda a, k: sp(a, "P1.prior_shares_outstanding", v)))(_v))
for _lab, _v in [("'$50.00'", "$50.00"), ("'USD 50'", "USD 50"), ("'50.0000 USD'", "50.0000 USD"), ("'$50/share'", "$50/share")]:
    T("P1num:prior_nav " + _lab, "P1num", f"prior_nav_per_share as {_lab}", (lambda v: (lambda a, k: sp(a, "P1.prior_nav_per_share", v)))(_v))

# ---- P1: regime (GATE.REGIME scoped -> D1) ----
for _lab, _v in [("USA", "USA"), ("U.S.", "U.S."), ("United States", "United States"), ("us", "us"), ("US (Rule 6c-11)", "US (Rule 6c-11)"), ("United States of America", "United States of America")]:
    T("P1reg:jurisdiction " + _lab, "P1reg", f"regime.jurisdiction {_lab!r}", (lambda v: (lambda a, k: sp(a, "P1.regime.jurisdiction", v)))(_v))
for _lab, _v in [("'$0.01'", "$0.01"), ("'0.01 USD'", "0.01 USD"), ("int 1 (cent)", 1), ("'1 cent'", "1 cent"), ("'1c'", "1c")]:
    T("P1reg:floor " + _lab, "P1reg", f"regime.per_share_floor_usd {_lab}", (lambda v: (lambda a, k: sp(a, "P1.regime.per_share_floor_usd", v)))(_v))
for _lab, _v in [("0.005 (fraction)", 0.005), ("'0.5%'", "0.5%"), ("'0.50 %'", "0.50 %"), ("50 (bp)", 50), ("'50bp'", "50bp"), ("'0.5'", "0.5")]:
    T("P1reg:reproc " + _lab, "P1reg", f"regime.reprocessing_pct {_lab}", (lambda v: (lambda a, k: sp(a, "P1.regime.reprocessing_pct", v)))(_v))
for _lab, _v in [("Pre-release", "Pre-release"), ("PRE_RELEASE", "PRE_RELEASE"), ("pre release", "pre release"), ("Pre-release review", "Pre-release review"),
                 ("prerelease", "prerelease"), ("before release", "before release"), ("prior to release", "prior to release"),
                 ("preliminary", "preliminary"), ("pre-publication", "pre-publication"), ("unreleased", "unreleased"), ("pre-dissemination", "pre-dissemination"),
                 ("pre_release (preliminary NAV)", "pre_release (preliminary NAV)"), ("Before_Release", "before_release")]:
    T("P1reg:stage " + _lab, "P1reg", f"review_stage {_lab!r}", (lambda v: (lambda a, k: sp(a, "P1.review_stage", v)))(_v))


# ---- global numeric restyles ----
def _restyle(style):
    def fn(a, k):
        def f(path, v):
            if style == "commas":
                return commas(v) if abs(v) >= 1000 or isinstance(v, float) else str(v)
            if style == "dollar":
                return money(v) if is_dollar(path) else (commas(v) if abs(v) >= 1000 else v)
            if style == "pct":
                return commas(v) + "%" if is_pct(path) else v
            if style == "all":
                if is_dollar(path):
                    return money(v)
                if is_pct(path):
                    return commas(v) + "%"
                return commas(v) if abs(v) >= 1000 else v
            if style == "plainstr":
                return str(v)
            if style == "int_as_float":
                return float(v) if isinstance(v, int) else v
            if style == "float_as_int":
                return int(v) if isinstance(v, float) and v == int(v) else v
            if style == "all_floats":
                return float(v)
            return v
        return map_nums(a, f)
    return fn


for _s, _d in [("commas", "every number a string with thousands separators"),
               ("dollar", "dollar fields as '$1,234.50' strings, other numbers plain"),
               ("pct", "percent fields as '2.4824%' strings"),
               ("all", "$ on dollar fields, % on percent fields, commas on counts"),
               ("plainstr", "every number a plain numeric string ('51.9912')"),
               ("int_as_float", "integers written as floats (4000000.0, 0.0)"),
               ("float_as_int", "integer-valued floats written as ints (100000000)"),
               ("all_floats", "every number a float")]:
    T("num:" + _s, "num", _d, _restyle(_s))


def _frac(keys):
    def fn(a, k):
        return map_nums(a, lambda path, v: v / 100.0 if lastkey(path) in keys else v)
    return fn


for _k in ["reprocessing_pct", "return_pct", "nav_error_pct", "expected_move_pct", "admin_move_pct", "admin_deviation_pp"]:
    T("frac:" + _k, "frac", f"{_k} as a fraction (value/100) instead of a plain percent", _frac({_k}), arguable=True)
T("frac:all pct fields", "frac", "every percent field as a fraction (0.0144 style)", _frac(PCT_KEYS), arguable=True)


def _negfmt(kind):
    def fn(a, k):
        def f(path, v):
            if v < 0 and not is_pct(path) or (v < 0 and is_pct(path)):
                s = commas(abs(v))
                if kind == "unicode_minus":
                    return "\u2212" + s
                if kind == "parens":
                    return "(" + s + ")"
                if kind == "dollar_unicode":
                    return "\u2212$" + s
                if kind == "usd_suffix":
                    return commas(v) + " USD"
            return v
        return map_nums(a, f)
    return fn


T("neg:unicode minus (U+2212)", "neg", "negative numbers as strings with a typographic minus", _negfmt("unicode_minus"))
T("neg:accounting parens", "neg", "negative numbers as '(0.75)' accounting strings", _negfmt("parens"))
T("neg:'-0.75 USD'", "neg", "negative numbers with a trailing ' USD'", _negfmt("usd_suffix"))


def _unit_suffix(unit):
    def fn(a, k):
        return map_nums(a, lambda path, v: f"{commas(v)} {unit}" if is_dollar(path) else v)
    return fn


T("units:' USD' suffix on dollar fields", "units", "dollar fields as '209,010,600 USD'", _unit_suffix("USD"))
T("units:'USD ' prefix", "units", "dollar fields as 'USD 209,010,600'",
  lambda a, k: map_nums(a, lambda path, v: f"USD {commas(v)}" if is_dollar(path) else v))
T("units:'/share' suffix", "units", "per-share fields as '51.9912 per share'",
  lambda a, k: map_nums(a, lambda path, v: f"{commas(v)} per share" if lastkey(path) in ("nav_per_share", "corrected_nav_per_share", "nav_error_per_share", "admin_nav_per_share", "admin_prelim_nav_per_share", "prior_nav_per_share") else v))
T("units:' pp' suffix", "units", "deviation fields as '-1.5176 pp'",
  lambda a, k: map_nums(a, lambda path, v: f"{commas(v)} pp" if lastkey(path) in ("admin_deviation_pp", "recomputed_deviation_pp") else v))
T("units:' bps' deviation", "units", "deviation fields as basis points (-151.76) - a different unit, labelled",
  lambda a, k: map_nums(a, lambda path, v: v * 100 if lastkey(path) in ("admin_deviation_pp", "recomputed_deviation_pp") else v), arguable=True)

# ---- E1 ----
T("E1:totals nested under E1.totals (admin_* names)", "E1", "the totals under a sub-object, same key names",
  lambda a, k: (a["E1"].__setitem__("totals", {x: a["E1"].pop(x) for x in ("admin_total_assets", "admin_total_liabilities", "admin_total_net_assets", "admin_shares_outstanding", "admin_nav_per_share")}) or a))
T("E1:totals nested under E1.totals (plain names)", "E1", "the totals under a sub-object with un-prefixed keys",
  lambda a, k: (a["E1"].__setitem__("totals", {"total_assets": a["E1"].pop("admin_total_assets"), "total_liabilities": a["E1"].pop("admin_total_liabilities"),
                                               "total_net_assets": a["E1"].pop("admin_total_net_assets"), "shares_outstanding": a["E1"].pop("admin_shares_outstanding"),
                                               "nav_per_share": a["E1"].pop("admin_nav_per_share")}) or a))
T("E1:totals as unprefixed flat keys", "E1", "E1.total_net_assets / shares_outstanding / nav_per_share (no admin_ prefix)",
  lambda a, k: (a["E1"].update({"total_assets": a["E1"].pop("admin_total_assets"), "total_liabilities": a["E1"].pop("admin_total_liabilities"),
                                "total_net_assets": a["E1"].pop("admin_total_net_assets"), "shares_outstanding": a["E1"].pop("admin_shares_outstanding"),
                                "nav_per_share": a["E1"].pop("admin_nav_per_share")}) or a))


def _lines_to_dict_plain(a, k):
    a["E1"]["admin_lines"] = {r["line_id"]: r["market_value"] for r in a["E1"]["admin_lines"]}
    a["E1"]["admin_liabilities"] = {r["line_id"]: r["amount"] for r in a["E1"]["admin_liabilities"]}


def _lines_to_dict_nested(a, k):
    a["E1"]["admin_lines"] = {r["line_id"]: {"market_value": r["market_value"], "price_date": r["price_date"]} for r in a["E1"]["admin_lines"]}
    a["E1"]["admin_liabilities"] = {r["line_id"]: {"amount": r["amount"]} for r in a["E1"]["admin_liabilities"]}


T("E1:lines as dict id->number", "E1", "admin_lines / admin_liabilities as {line_id: number} maps", _lines_to_dict_plain)
T("E1:lines as dict id->{market_value}", "E1", "admin_lines / admin_liabilities as {line_id: {market_value|amount}} maps", _lines_to_dict_nested)


def _rename_keys_in(a, paths, old, new):
    for p in paths:
        for r in (gp(a, p) or []):
            if isinstance(r, dict) and old in r:
                r[new] = r.pop(old)


T("E1:Line_ID key case", "keys", "line_id spelled Line_ID in E1/C1 rows",
  lambda a, k: _rename_keys_in(a, ["E1.admin_lines", "E1.admin_liabilities", "C1.recon", "C1.exceptions"], "line_id", "Line_ID"))
T("E1:lineId camelCase", "keys", "line_id spelled lineId in E1/C1 rows",
  lambda a, k: _rename_keys_in(a, ["E1.admin_lines", "E1.admin_liabilities", "C1.recon", "C1.exceptions"], "line_id", "lineId"))
T("E1:lines use 'value'", "E1", "ledger rows carry 'value' instead of 'market_value'; liabilities carry 'value' instead of 'amount'",
  lambda a, k: (_rename_keys_in(a, ["E1.admin_lines"], "market_value", "value"), _rename_keys_in(a, ["E1.admin_liabilities"], "amount", "value")) and None)
T("E1:liabilities use 'market_value'", "E1", "liability rows carry 'market_value' (copying the ledger pattern) instead of 'amount'",
  lambda a, k: _rename_keys_in(a, ["E1.admin_liabilities"], "amount", "market_value"))
T("E1:liabilities use 'value'", "E1", "liability rows carry 'value' instead of 'amount'",
  lambda a, k: _rename_keys_in(a, ["E1.admin_liabilities"], "amount", "value"))


def _merge_liab_into_lines(a, k):
    for r in a["E1"]["admin_liabilities"]:
        a["E1"]["admin_lines"].append({"line_id": r["line_id"], "market_value": r["amount"]})
    a["E1"]["admin_liabilities"] = []


T("E1:liabilities listed inside admin_lines", "E1", "one merged ledger: liabilities appended to admin_lines, admin_liabilities empty", _merge_liab_into_lines)
T("E1:extra TOTAL row in admin_lines", "E1", "an informational TOTAL row appended to admin_lines",
  lambda a, k: a["E1"]["admin_lines"].append({"line_id": "TOTAL", "market_value": a["E1"]["admin_total_assets"]}))
T("E1:extra TOTAL_LIABILITIES row", "E1", "an informational total row appended to admin_liabilities",
  lambda a, k: a["E1"]["admin_liabilities"].append({"line_id": "TOTAL_LIABILITIES", "amount": a["E1"]["admin_total_liabilities"]}))
T("E1:line_id lower-case", "E1", "line ids in lower case",
  lambda a, k: [r.__setitem__("line_id", r["line_id"].lower()) for p in ("E1.admin_lines", "E1.admin_liabilities", "C1.recon") for r in gp(a, p)] and None)
T("E1:line_id TB0925 (no hyphen)", "E1", "TB-0925 written TB0925 everywhere",
  lambda a, k: [r.__setitem__("line_id", "TB0925") for p in ("E1.admin_lines", "C1.recon") for r in gp(a, p) if r["line_id"] == "TB-0925"] and None)
T("E1:line_id 'SWAP B' / 'SWAP_B'", "E1", "SWAP-B written SWAP_B in E1/C1 (stale flag + exception + recon)",
  lambda a, k: ([r.__setitem__("line_id", "SWAP_B") for p in ("E1.admin_lines", "C1.recon") for r in gp(a, p) if r["line_id"] == "SWAP-B"],
                [r.__setitem__("line_id", "SWAP_B") for r in a["C1"]["exceptions"]],
                a["E1"].__setitem__("stale_flags", ["SWAP_B" if x == "SWAP-B" else x for x in a["E1"]["stale_flags"]])) and None)
T("E1:line_id trailing space", "E1", "line ids with a trailing space ('SWAP-B ')",
  lambda a, k: [r.__setitem__("line_id", r["line_id"] + " ") for p in ("E1.admin_lines", "E1.admin_liabilities") for r in gp(a, p)] and None)

# stale flags
T("E1:stale_flags 'SWAP-B' as a string", "E1stale", "stale_flags a bare string instead of a list",
  lambda a, k: sp(a, "E1.stale_flags", "SWAP-B"), cases=("break",))
T("E1:stale_flags lower-case", "E1stale", "stale_flags ['swap-b']", lambda a, k: sp(a, "E1.stale_flags", ["swap-b"]), cases=("break",))
T("E1:stale_flags objects", "E1stale", "stale_flags [{line_id, flag}]",
  lambda a, k: sp(a, "E1.stale_flags", [{"line_id": "SWAP-B", "flag": "STALE_PRICE"}]), cases=("break",))
T("E1:stale_flags 'SWAP-B (STALE_PRICE)'", "E1stale", "stale_flags ['SWAP-B (STALE_PRICE)']",
  lambda a, k: sp(a, "E1.stale_flags", ["SWAP-B (STALE_PRICE)"]), cases=("break",))
T("E1:stale_flags space-padded", "E1stale", "stale_flags [' SWAP-B']", lambda a, k: sp(a, "E1.stale_flags", [" SWAP-B"]), cases=("break",))
T("E1:stale_flags duplicates", "E1stale", "stale_flags ['SWAP-B','SWAP-B']", lambda a, k: sp(a, "E1.stale_flags", ["SWAP-B", "SWAP-B"]), cases=("break",))
T("E1:stale_flags dict form", "E1stale", "stale_flags {'SWAP-B': 'STALE_PRICE'}", lambda a, k: sp(a, "E1.stale_flags", {"SWAP-B": "STALE_PRICE"}), cases=("break",))
T("E1:stale_flags ['none'] on clean", "E1stale", "clean package: stale_flags ['none']", lambda a, k: sp(a, "E1.stale_flags", ["none"]), cases=("clean",))
T("E1:stale_flags 'none' on clean", "E1stale", "clean package: stale_flags 'none' (string)", lambda a, k: sp(a, "E1.stale_flags", "none"), cases=("clean",))
T("E1:stale_flags null on clean", "E1stale", "clean package: stale_flags null", lambda a, k: sp(a, "E1.stale_flags", None), cases=("clean",))
T("E1:stale_flags 'N/A' list on clean", "E1stale", "clean package: stale_flags ['N/A']", lambda a, k: sp(a, "E1.stale_flags", ["N/A"]), cases=("clean",))
T("E1:stale_flags '' on clean", "E1stale", "clean package: stale_flags ''", lambda a, k: sp(a, "E1.stale_flags", ""), cases=("clean",))

# citations
VB = "line_id=SWAP-B  flag=STALE_PRICE  note=Westbrook valuation file not received by the 17:30 ET pricing cut-off; prior business day (2026-06-22) value carried forward"


def _cite(**kw):
    def fn(a, k):
        c = a["E1"]["citation"]
        for key, val in kw.items():
            if val is None:
                c.pop(key, None)
            else:
                c[key] = val
    return fn


for _lab, _d in [("Package", "Package"), ("PACKAGE", "PACKAGE"), ("the package", "the package"), ("NAV package", "NAV package"),
                 ("package id", "NAV-GRSL-20260623-PRELIM"), ("administrator package", "administrator package"),
                 ("pricing exceptions report", "pricing exceptions report"), ("package (trailing space)", "package ")]:
    T("E1cite:document " + _lab, "E1cite", f"citation.document = {_d!r}", _cite(document=_d))
T("E1cite:verbatim single-spaced", "E1cite", "gold verbatim with single spaces (break) / ledger line single-spaced",
  lambda a, k: sp(a, "E1.citation.verbatim", re.sub(r"\s+", " ", a["E1"]["citation"]["verbatim"])))
T("E1cite:verbatim wrapped in quotes", "E1cite", "verbatim wrapped in double quotes",
  lambda a, k: sp(a, "E1.citation.verbatim", '"' + a["E1"]["citation"]["verbatim"] + '"'))
T("E1cite:verbatim newline-wrapped", "E1cite", "verbatim with line breaks between fields",
  lambda a, k: sp(a, "E1.citation.verbatim", re.sub(r"\s{2,}", "\n", a["E1"]["citation"]["verbatim"])))
T("E1cite:verbatim drops line_id= token (still entails)", "E1cite", "break: verbatim without the leading 'line_id=SWAP-B' token",
  lambda a, k: sp(a, "E1.citation.verbatim", "flag=STALE_PRICE  note=Westbrook valuation file not received by the 17:30 ET pricing cut-off; prior business day (2026-06-22) value carried forward"), cases=("break",))
T("E1cite:short verbatim: note sentence only", "E1cite", "break: the sentence from the exceptions note, exact, without the key= prefixes",
  lambda a, k: sp(a, "E1.citation.verbatim", "Westbrook valuation file not received by the 17:30 ET pricing cut-off; prior business day (2026-06-22) value carried forward"), cases=("break",))
T("E1cite:short verbatim: 'prior business day ... carried forward'", "E1cite", "break: the minimal entailing phrase 'prior business day (2026-06-22) value carried forward'",
  lambda a, k: sp(a, "E1.citation.verbatim", "prior business day (2026-06-22) value carried forward"), cases=("break",))
T("E1cite:short verbatim: id+flag", "E1cite", "break: 'line_id=SWAP-B  flag=STALE_PRICE'",
  lambda a, k: sp(a, "E1.citation.verbatim", "line_id=SWAP-B  flag=STALE_PRICE"), cases=("break",))
T("E1cite:short verbatim: ledger SWAP-B price_date+source", "E1cite", "break: 'price_date=2026-06-22  price_source=prior business day value carried forward' from the ledger line",
  lambda a, k: sp(a, "E1.citation.verbatim", "line_id=SWAP-B  price_date=2026-06-22  price_source=prior business day value carried forward"), cases=("break",))
T("E1cite:totals block, 3 of 5 fields", "E1cite", "totals-block quote with three of the five fields (exact substring)",
  lambda a, k: sp(a, "E1.citation.verbatim", "total_net_assets=%s  shares_outstanding=4000000  nav_per_share=%s" % (("204964686.19", "51.2412") if k == "break" else ("207964686.19", "51.9912"))))
T("E1cite:totals block, nav_per_share only", "E1cite", "totals-block quote: the single field nav_per_share",
  lambda a, k: sp(a, "E1.citation.verbatim", "nav_per_share=%s" % ("51.2412" if k == "break" else "51.9912")))
T("E1cite:totals block, TNA + NAV", "E1cite", "totals-block quote: 'total_net_assets=...  nav_per_share=...' (2 of 5 fields)",
  lambda a, k: sp(a, "E1.citation.verbatim", "total_net_assets=%s  nav_per_share=%s" % (("204964686.19", "51.2412") if k == "break" else ("207964686.19", "51.9912"))))
T("E1cite:clean '(none)' exceptions report", "E1cite", "clean: cite the empty pricing-exceptions report exactly as the packet prints it",
  lambda a, k: a["E1"].__setitem__("citation", {"document": "package", "locator": "PRICING EXCEPTIONS REPORT", "verbatim": "PRICING EXCEPTIONS REPORT:\n  (none)"}), cases=("clean",))
T("E1cite:clean '(none)' only", "E1cite", "clean: verbatim '(none)' under the exceptions report heading",
  lambda a, k: a["E1"].__setitem__("citation", {"document": "package", "locator": "PRICING EXCEPTIONS REPORT", "verbatim": "(none)"}), cases=("clean",))
T("E1cite:citation as list", "E1cite", "citation is a list of citation objects", lambda a, k: sp(a, "E1.citation", [a["E1"]["citation"]]))
T("E1cite:locator/verbatim swapped", "E1cite", "locator and verbatim swapped",
  lambda a, k: a["E1"].__setitem__("citation", {"document": "package", "locator": a["E1"]["citation"]["verbatim"], "verbatim": a["E1"]["citation"]["locator"]}))
T("E1cite:text in 'quote' key", "E1cite", "verbatim text under 'quote' key instead of 'verbatim'",
  lambda a, k: a["E1"].__setitem__("citation", {"document": "package", "locator": a["E1"]["citation"]["locator"], "quote": a["E1"]["citation"]["verbatim"]}))
T("E1cite:citation is a string", "E1cite", "citation as one plain string (the verbatim)",
  lambda a, k: sp(a, "E1.citation", a["E1"]["citation"]["verbatim"]))

# ---- E2 ----
for _alt in ("line_id", "swap_id", "statement_id", "trade_ref"):
    T("E2:statement key '" + _alt + "'", "E2", f"swap_statements rows keyed by '{_alt}' instead of 'id'",
      (lambda alt: (lambda a, k: [r.__setitem__(alt, r.pop("id")) for r in a["E2"]["swap_statements"]] and None))(_alt))
T("E2:statements as dict by id", "E2", "swap_statements as {id: {...}} map",
  lambda a, k: sp(a, "E2.swap_statements", {r["id"]: {x: y for x, y in r.items() if x != "id"} for r in a["E2"]["swap_statements"]}))
T("E2:prices as list {ticker, price}", "E2", "prices as [{ticker|id, price}] list",
  lambda a, k: sp(a, "E2.prices", [{"ticker": "SMH", "price": a["E2"]["prices"]["SMH"]}, {"id": "TB-0925", "price": a["E2"]["prices"]["TB-0925"]}]))
T("E2:prices as list {ticker, close}", "E2", "prices as [{ticker|id, close}] list",
  lambda a, k: sp(a, "E2.prices", [{"ticker": "SMH", "close": a["E2"]["prices"]["SMH"]}, {"id": "TB-0925", "close": a["E2"]["prices"]["TB-0925"]}]))
T("E2:prices nested {close, prior_close}", "E2", "prices as {SMH: {close, prior_close}, TB-0925: {price, prior_price}}",
  lambda a, k: sp(a, "E2.prices", {"SMH": {"close": 250.0, "prior_close": 245.0}, "TB-0925": {"price": 99.8, "prior_price": 99.79}}))
T("E2:prices nested {value}", "E2", "prices as {SMH: {value: 250.0}, ...}",
  lambda a, k: sp(a, "E2.prices", {"SMH": {"value": 250.0}, "TB-0925": {"value": 99.8}}))
T("E2:prices lower-case ids", "E2", "prices keys 'smh', 'tb-0925'",
  lambda a, k: sp(a, "E2.prices", {"smh": 250.0, "tb-0925": 99.8}))
T("E2:prices 'TB0925'", "E2", "prices key TB0925", lambda a, k: sp(a, "E2.prices", {"SMH": 250.0, "TB0925": 99.8}))
T("E2:prices key 'TB-0925 T-bill'", "E2", "prices key 'TB-0925 (T-bill)'", lambda a, k: sp(a, "E2.prices", {"SMH": 250.0, "TB-0925 (T-bill)": 99.8}))
T("E2:T-bill price 99.80%", "E2", "T-bill price '99.80%'", lambda a, k: sp(a, "E2.prices.TB-0925", "99.80%"))
T("E2:T-bill price as 0.998 (fraction of par)", "E2", "T-bill price quoted as a fraction of par 0.998", lambda a, k: sp(a, "E2.prices.TB-0925", 0.998), arguable=True)
T("E2:extra price (GRSL) listed", "E2", "an extra 'GRSL' key in prices", lambda a, k: a["E2"]["prices"].__setitem__("GRSL", None))
T("E2:index list", "E2", "index as [{name, close, prior_close, return_pct}]", lambda a, k: sp(a, "E2.index", [a["E2"]["index"]]))
T("E2:capital_stock list", "E2", "capital_stock as a one-element list", lambda a, k: sp(a, "E2.capital_stock", [a["E2"]["capital_stock"]]))
T("E2:index extra fields + name", "E2", "index with extra name/date fields", lambda a, k: a["E2"]["index"].update({"name": "SOX", "date": "2026-06-23"}))
T("E2:financing payable negative", "E2", "financing_accrued_payable written as a negative (liability sign)",
  lambda a, k: [r.__setitem__("financing_accrued_payable", -r["financing_accrued_payable"]) for r in a["E2"]["swap_statements"]] and None, arguable=True)
T("E2:statement extra fields", "E2", "statements carry trade_ref/reset_date/received_et extras",
  lambda a, k: [r.update({"trade_ref": "X", "reset_date": "2026-05-29", "received_et": "17:05", "note": "n"}) for r in a["E2"]["swap_statements"]] and None)
T("E2:3rd informational statement row", "E2", "an extra statement row 'SWAP-B-PRIOR' (the prior-day mark) added",
  lambda a, k: a["E2"]["swap_statements"].append({"id": "SWAP-B-PRIOR", "counterparty": "Westbrook Capital Markets", "notional": 147000000.0, "reset_level": 4900.0, "index_level": 5000.0, "unrealized_value": 3000000.0, "financing_accrued_payable": 500208.33, "valuation_date": "2026-06-22"}), cases=("break",), arguable=True)

# ---- C1 ----
STAT_SYNS = {"matched": "matched", "MATCH": "MATCH", "Match": "Match", "ties": "ties", "tied": "tied", "OK": "OK", "agrees": "agrees", "reconciled": "reconciled", "match ": "match "}
for _lab, _v in [("matched", "matched"), ("MATCH", "MATCH"), ("Match", "Match"), (" match ", " match "), ("matches", "matches"), ("tie", "tie"), ("ties", "ties"), ("tied", "tied"), ("ok", "ok"), ("agrees", "agrees"), ("reconciled", "reconciled")]:
    def _mk_stat(v):
        def fn(a, k):
            for r in a["C1"]["recon"]:
                if r["status"] == "match":
                    r["status"] = v
        return fn
    T("C1:status match->" + _lab, "C1status", f"every 'match' status written {_lab!r}", _mk_stat(_v), arguable=(_lab not in ("MATCH", "Match", " match ")))
for _lab, _v in [("STALE", "STALE"), ("Stale", "Stale"), ("stale_price", "stale_price"), ("STALE_PRICE", "STALE_PRICE"), ("stale price", "stale price"),
                 ("stale (carried forward)", "stale (carried forward)"), ("stale - prior-day mark", "stale - prior-day mark"), ("stale-priced", "stale-priced"), ("stale_mark", "stale_mark")]:
    T("C1:status stale->" + _lab, "C1status", f"the stale row's status written {_lab!r}",
      (lambda v: (lambda a, k: [r.__setitem__("status", v) for r in a["C1"]["recon"] if r["status"] == "stale"] and None))(_v), cases=("break",), arguable=(_lab not in ("STALE", "Stale")))
T("C1:recon reversed", "C1", "recon rows in reverse order", lambda a, k: a["C1"]["recon"].reverse())
T("C1:recon liabilities first", "C1", "liability rows first, ledger rows after",
  lambda a, k: sp(a, "C1.recon", [r for r in a["C1"]["recon"] if r["line_id"] in ("FIN-A", "FIN-B", "FEE")] + [r for r in a["C1"]["recon"] if r["line_id"] not in ("FIN-A", "FIN-B", "FEE")]))
T("C1:recon as dict keyed by line_id", "C1", "recon as {line_id: {admin_value, independent_value, status}}",
  lambda a, k: sp(a, "C1.recon", {r["line_id"]: {x: y for x, y in r.items() if x != "line_id"} for r in a["C1"]["recon"]}))
T("C1:recon row key 'id'", "C1", "recon rows keyed 'id' instead of 'line_id'", lambda a, k: [r.__setitem__("id", r.pop("line_id")) for r in a["C1"]["recon"]] and None)
T("C1:recon row key 'line'", "C1", "recon rows keyed 'line' instead of 'line_id'", lambda a, k: [r.__setitem__("line", r.pop("line_id")) for r in a["C1"]["recon"]] and None)
T("C1:recon extra fields", "C1", "recon rows with extra 'difference','note' fields",
  lambda a, k: [r.update({"difference": 0.0, "note": "ok"}) for r in a["C1"]["recon"]] and None)
T("C1:recon omits liabilities", "C1", "recon only for the five ledger lines (no FIN-A/FIN-B/FEE) - the pre-contract behaviour",
  lambda a, k: sp(a, "C1.recon", [r for r in a["C1"]["recon"] if r["line_id"] not in ("FIN-A", "FIN-B", "FEE")]), arguable=True)

# exceptions
T("C1exc:exceptions as strings", "C1exc", "exceptions as ['SWAP-B: stale price ...'] strings",
  lambda a, k: sp(a, "C1.exceptions", ["SWAP-B: stale price - the 2026-06-22 mark was carried forward; the 2026-06-23 statement values it at 6,000,000"]), cases=("break",))
T("C1exc:exceptions row key 'id'", "C1exc", "exception rows keyed 'id'",
  lambda a, k: [r.__setitem__("id", r.pop("line_id")) for r in a["C1"]["exceptions"]] and None, cases=("break",))
T("C1exc:exceptions row key 'line'", "C1exc", "exception rows keyed 'line'",
  lambda a, k: [r.__setitem__("line", r.pop("line_id")) for r in a["C1"]["exceptions"]] and None, cases=("break",))
T("C1exc:line_id 'SWAP-B (Westbrook)'", "C1exc", "exception line_id 'SWAP-B (Westbrook)'",
  lambda a, k: a["C1"]["exceptions"][0].__setitem__("line_id", "SWAP-B (Westbrook)"), cases=("break",))
for _lab, _t, _d in [
    ("not applied", "valuation_break", "Westbrook's 2026-06-23 statement was not applied; the ledger still holds yesterday's value of 3,000,000 against 6,000,000 on the statement - SWAP-B is understated by 3,000,000"),
    ("cut off (two words)", "late_statement", "Westbrook's file arrived after the 17:30 pricing cut off, so the 2026-06-22 level was used; the statement dated 2026-06-23 shows 6,000,000"),
    ("T-1 / yesterday", "t_minus_1_mark", "SWAP-B is booked at the T-1 mark of 3,000,000; the current Westbrook statement values it at 6,000,000"),
    ("unapplied/superseded", "unapplied_statement", "The 2026-06-23 Westbrook statement (6,000,000.00) was never loaded; SWAP-B shows the superseded 2026-06-22 value 3,000,000.00"),
    ("old/day-old", "pricing_error", "SWAP-B uses a day-old index level of 5,000 instead of 5,100, so the mark is 3,000,000 instead of 6,000,000"),
    ("late file", "late_counterparty_file", "Counterparty file for SWAP-B was received at 17:52 ET, after the pricing deadline; the ledger value 3,000,000 does not reflect the 6,000,000 statement"),
    ("contains 'stale' (control)", "stale_price", "SWAP-B stale: 3,000,000 vs 6,000,000 on the statement"),
    ("contains 'prior' (control)", "mark_error", "prior-day mark used for SWAP-B: 3,000,000 vs 6,000,000"),
    ("price_staleness", "price_staleness", "SWAP-B ledger mark 3,000,000 vs statement 6,000,000"),
    ("mispriced (no keyword)", "mispriced_swap", "SWAP-B is mispriced: ledger 3,000,000 vs statement 6,000,000 (index 5,000 vs 5,100)"),
    ("valuation mismatch (no keyword)", "valuation_mismatch", "ledger value 3,000,000.00 differs from the 2026-06-23 statement value 6,000,000.00"),
]:
    T("C1exc:wording " + _lab, "C1exc", f"correct exception row, wording avoiding the grader's keyword list ({_lab})",
      (lambda t, d: (lambda a, k: a["C1"]["exceptions"].__setitem__(0, {"line_id": "SWAP-B", "type": t, "detail": d})))(_t, _d), cases=("break",))
T("C1exc:extra informational row (note)", "C1exc", "correct SWAP-B exception plus an informational NAV-level row",
  lambda a, k: a["C1"]["exceptions"].append({"line_id": "NAV", "type": "info", "detail": "Administrator NAV 51.2412 is 0.75 below the recomputed 51.9912 as a consequence of the SWAP-B exception"}), cases=("break",), arguable=True)
T("C1exc:extra row for the totals (consequence)", "C1exc", "correct SWAP-B exception plus a TOTALS consequence row",
  lambda a, k: a["C1"]["exceptions"].append({"line_id": "TOTALS", "type": "stale_price_consequence", "detail": "total assets and TNA understated by 3,000,000 because of the stale SWAP-B mark"}), cases=("break",), arguable=True)
T("C1exc:clean info row", "C1exc", "clean package: an informational row says 'no exceptions' (line_id NONE)",
  lambda a, k: sp(a, "C1.exceptions", [{"line_id": "NONE", "type": "info", "detail": "no exceptions identified; all lines tie"}]), cases=("clean",), arguable=True)
T("C1exc:clean null", "C1exc", "clean package: exceptions null", lambda a, k: sp(a, "C1.exceptions", None), cases=("clean",))
T("C1exc:clean 'none' string", "C1exc", "clean package: exceptions 'none'", lambda a, k: sp(a, "C1.exceptions", "none"), cases=("clean",), arguable=True)
T("C1exc:clean [{}]", "C1exc", "clean package: exceptions [{}]", lambda a, k: sp(a, "C1.exceptions", [{}]), cases=("clean",), arguable=True)

# ---- C2 ----
T("C2:totals nested {value}", "C2", "C2 numbers as {value: x, unit: USD} objects",
  lambda a, k: [a["C2"].__setitem__(x, {"value": a["C2"][x], "unit": "USD"}) for x in ("total_assets", "total_liabilities", "total_net_assets", "nav_per_share")] and None)
T("C2:totals nested {amount}", "C2", "C2 numbers as {amount: x} objects",
  lambda a, k: [a["C2"].__setitem__(x, {"amount": a["C2"][x]}) for x in ("total_assets", "total_liabilities", "total_net_assets", "nav_per_share")] and None)
T("C2:nav unrounded 5dp", "C2", "nav_per_share unrounded 51.99117 (break) / same (clean)", lambda a, k: sp(a, "C2.nav_per_share", 51.99117))
T("C2:nav 6dp", "C2", "nav_per_share 51.991172", lambda a, k: sp(a, "C2.nav_per_share", 51.991172))
T("C2:nav 2dp", "C2", "nav_per_share 51.99 (2 decimals; the prompt asks 4)", lambda a, k: sp(a, "C2.nav_per_share", 51.99), arguable=True)
T("C2:nav 4dp truncated 51.9911", "C2", "nav_per_share truncated 51.9911", lambda a, k: sp(a, "C2.nav_per_share", 51.9911), arguable=True)
T("C2:TNA in USD millions", "C2", "totals in USD millions, a units note added (209.0106 etc.)",
  lambda a, k: [a["C2"].__setitem__(x, round(a["C2"][x] / 1e6, 6)) for x in ("total_assets", "total_liabilities", "total_net_assets")] and a["C2"].__setitem__("units", "USD millions") or None, arguable=True)
T("C2:shares_outstanding omitted", "C2", "C2.shares_outstanding omitted (not graded)", lambda a, k: a["C2"].pop("shares_outstanding"))

# ---- C3 ----
for _lab, _v in [("Understated", "Understated"), ("UNDERSTATED", "UNDERSTATED"), ("understated (admin below recomputed)", "understated (admin below recomputed)"),
                 ("NAV understated", "NAV understated"), ("the NAV is understated", "the NAV is understated"), ("Administrator NAV understated", "Administrator NAV understated"),
                 ("under", "under"), ("understatement", "understatement"), ("underestimated", "underestimated"), ("low", "low"), ("lower", "lower"), ("too low", "too low"),
                 ("below", "below"), ("negative", "negative"), ("admin < recomputed", "admin < recomputed"), ("-", "-"), ("understated by 0.75", "understated by 0.75")]:
    T("C3dir:" + _lab, "C3dir", f"direction {_lab!r}", (lambda v: (lambda a, k: sp(a, "C3.direction", v)))(_v), cases=("break",), arguable=(_lab in ("negative", "admin < recomputed", "-")))
for _lab, _v in [("None", "None"), ("NONE", "NONE"), ("no error", "no error"), ("No error found", "No error found"), ("no difference", "no difference"), ("none (ties)", "none (ties)"),
                 ("None - NAV ties", "None - NAV ties"), ("match", "match"), ("ties", "ties"), ("tie", "tie"), ("tied", "tied"), ("n/a", "n/a"), ("null", None), ("zero", "zero"),
                 ("in line", "in line"), ("no error (ties)", "no error (ties)"), ("balanced", "balanced"), ("neither", "neither"), ("equal", "equal"), ("0", "0")]:
    T("C3dir-clean:" + _lab, "C3dir", f"clean package: direction {_lab!r}", (lambda v: (lambda a, k: sp(a, "C3.direction", v)))(_v), cases=("clean",))
TRUE_FORMS = [("'true'", "true"), ("'True'", "True"), ("'TRUE'", "TRUE"), ("'yes'", "yes"), ("'Yes'", "Yes"), ("'Y'", "Y"), ("'y'", "y"), ("int 1", 1), ("float 1.0", 1.0), ("'1'", "1"),
              ("'T'", "T"), ("'Yes - 0.75 > 0.01'", "Yes - 0.75 > 0.01"), ("'true (0.75 >= 0.01)'", "true (0.75 >= 0.01)"), ("'exceeded'", "exceeded"), ("'Exceeds'", "Exceeds"),
              ("'yes ' padded", "yes "), ("'on'", "on"), ("'positive'", "positive")]
FALSE_FORMS = [("'false'", "false"), ("'False'", "False"), ("'FALSE'", "FALSE"), ("'no'", "no"), ("'No'", "No"), ("'N'", "N"), ("'n'", "n"), ("int 0", 0), ("float 0.0", 0.0), ("'0'", "0"),
               ("'F'", "F"), ("'No - 0.00 < 0.01'", "No - 0.00 < 0.01"), ("'false (0 < 0.01)'", "false (0 < 0.01)"), ("'not exceeded'", "not exceeded"), ("'N/A'", "N/A"),
               ("'no ' padded", "no "), ("'off'", "off"), ("'none'", "none")]
for _field in ("exceeds_per_share_floor", "exceeds_reprocessing_pct", "reasonableness_flag"):
    for _lab, _v in TRUE_FORMS:
        T(f"C3bool:{_field} true={_lab}", "C3bool", f"C3.{_field} written {_lab} (gold true, break case)",
          (lambda f, v: (lambda a, k: sp(a, "C3." + f, v)))(_field, _v), cases=("break",), arguable=(_lab in ("'on'", "'positive'", "'exceeded'", "'Exceeds'")))
    for _lab, _v in FALSE_FORMS:
        T(f"C3bool:{_field} false={_lab}", "C3bool", f"C3.{_field} written {_lab} (gold false, clean case)",
          (lambda f, v: (lambda a, k: sp(a, "C3." + f, v)))(_field, _v), cases=("clean",), arguable=(_lab in ("'off'", "'none'", "'N/A'", "'not exceeded'")))
T("C3:magnitude error (+0.75, +3,000,000, +1.4426) with direction", "C3sign", "the three error figures as positive magnitudes, direction 'understated'",
  lambda a, k: (a["C3"].update({"fund_level_error": abs(a["C3"]["fund_level_error"]), "nav_error_per_share": abs(a["C3"]["nav_error_per_share"]), "nav_error_pct": abs(a["C3"]["nav_error_pct"])})), cases=("break",), arguable=True)
T("C3:magnitude error in C3 only, D1 signed", "C3sign", "C3 error figures as magnitudes but D1.nav_error_per_share signed",
  lambda a, k: (a["C3"].update({"fund_level_error": abs(a["C3"]["fund_level_error"]), "nav_error_per_share": abs(a["C3"]["nav_error_per_share"]), "nav_error_pct": abs(a["C3"]["nav_error_pct"])})), cases=("break",), arguable=True)
T("C3:D1 error magnitude", "C3sign", "D1.nav_error_per_share +0.75 (magnitude) with decision HOLD",
  lambda a, k: sp(a, "D1.nav_error_per_share", 0.75), cases=("break",), arguable=True)
T("C3:deviation as absolute (+1.5176)", "C3sign", "admin_deviation_pp as +1.5176 (absolute deviation)",
  lambda a, k: sp(a, "C3.admin_deviation_pp", abs(a["C3"]["admin_deviation_pp"])), cases=("break",), arguable=True)
T("C3:error pct on admin NAV (-1.4637)", "C3sign", "nav_error_pct taken over the administrator NAV (-0.75/51.2412 = -1.4637)",
  lambda a, k: sp(a, "C3.nav_error_pct", -1.4637), cases=("break",), arguable=True)
T("C3:error pct 1dp (-1.4)", "C3sign", "nav_error_pct rounded to one decimal (-1.4)", lambda a, k: sp(a, "C3.nav_error_pct", -1.4), cases=("break",), arguable=True)
T("C3:error pct 3dp (-1.443)", "C3sign", "nav_error_pct -1.443", lambda a, k: sp(a, "C3.nav_error_pct", -1.443), cases=("break",))
T("C3:moves 2dp", "C3sign", "expected 4.0 / admin move 2.48 / deviation -1.52 (two decimals)",
  lambda a, k: a["C3"].update({"admin_move_pct": round(a["C3"]["admin_move_pct"], 2), "admin_deviation_pp": round(a["C3"]["admin_deviation_pp"], 2)}))
T("C3:moves 1dp", "C3sign", "admin move 2.5 / deviation -1.5 (one decimal)",
  lambda a, k: a["C3"].update({"admin_move_pct": round(a["C3"]["admin_move_pct"], 1), "admin_deviation_pp": round(a["C3"]["admin_deviation_pp"], 1)}), arguable=True)
T("C3:extra fields", "C3", "C3 with extra fields (notes, bands)", lambda a, k: a["C3"].update({"notes": "x", "oversight_band_pp": 0.25, "confidence": 0.9}))

# ---- D1 ----
for _lab, _v in [("Material", "Material"), ("MATERIAL", "MATERIAL"), ("material error", "material error"), ("Material (above floor and reprocessing %)", "Material (above floor and reprocessing %)"),
                 ("significant", "significant"), ("high", "high"), ("material - pre-release", "material - pre-release"), ("a material error", "a material error"), ("error is material", "error is material"),
                 ("Material NAV error", "Material NAV error"), ("MATERIAL_ERROR", "MATERIAL_ERROR"), ("breach", "breach")]:
    T("D1cls:" + _lab, "D1cls", f"classification {_lab!r}", (lambda v: (lambda a, k: sp(a, "D1.classification", v)))(_v), cases=("break",), arguable=(_lab in ("significant", "high", "breach", "error is material", "a material error")))
for _lab, _v in [("None", "None"), ("no error", "no error"), ("No break", "No break"), ("none (NAV ties)", "none (NAV ties)"), ("no material error", "no material error"), ("not material", "not material"),
                 ("immaterial", "immaterial"), ("n/a", "n/a"), ("N/A - ties", "N/A - ties"), ("clean", "clean"), ("no error - ties", "no error - ties"), ("null", None), ("nil", "nil")]:
    T("D1cls-clean:" + _lab, "D1cls", f"clean package: classification {_lab!r}", (lambda v: (lambda a, k: sp(a, "D1.classification", v)))(_v), cases=("clean",), arguable=(_lab in ("not material", "immaterial")))
for _lab, _v in [("'false'", "false"), ("'False'", "False"), ("'No'", "No"), ("'no'", "no"), ("'N'", "N"), ("int 0", 0), ("float 0.0", 0.0), ("'0'", "0"),
                 ("'No - pre-release hold, nothing transacted'", "No - pre-release hold, nothing transacted"), ("'not required'", "not required"), ("'not applicable'", "not applicable"),
                 ("'N/A'", "N/A"), ("'none'", "none"), ("null", None), ("'no (pre-release)'", "no (pre-release)")]:
    T("D1rep:" + _lab, "D1rep", f"reprocessing_required {_lab}", (lambda v: (lambda a, k: sp(a, "D1.reprocessing_required", v)))(_v), arguable=(_lab in ("'N/A'", "'none'", "null", "'not applicable'", "'not required'")))
for _lab, _v in [("swap-b", "swap-b"), ("SWAP B", "SWAP B"), ("SWAP_B", "SWAP_B"), ("Swap B", "Swap B"), ("Line SWAP-B", "Line SWAP-B"), ("SWAP-B (Westbrook)", "SWAP-B (Westbrook)"),
                 ("SWAP-B (Westbrook Capital Markets TRS)", "SWAP-B (Westbrook Capital Markets TRS)"), ("SWAP-B total return swap", "SWAP-B total return swap"),
                 ("['SWAP-B']", ["SWAP-B"]), ("{'line_id': 'SWAP-B'}", {"line_id": "SWAP-B"}), ("SWAP-B line", "SWAP-B line"), ("the SWAP-B swap", "the SWAP-B swap"), ("SWAP-B ", "SWAP-B ")]:
    T("D1off:" + _lab, "D1off", f"offending_line {_lab!r}", (lambda v: (lambda a, k: sp(a, "D1.offending_line", v)))(_v), cases=("break",))
for _lab, _v in [("null", None), ("''", ""), ("'none'", "none"), ("'None'", "None"), ("'N/A'", "N/A"), ("'n/a'", "n/a"), ("'No offending line'", "No offending line"), ("'None - all lines tie'", "None - all lines tie"),
                 ("'-'", "-"), ("'none identified'", "none identified"), ("'not applicable'", "not applicable"), ("'null'", "null"), ("[]", []), ("false", False)]:
    T("D1off-clean:" + _lab, "D1off", f"clean package: offending_line {_lab}", (lambda v: (lambda a, k: sp(a, "D1.offending_line", v)))(_v), cases=("clean",))
T("D1:clean nav_error null", "D1val", "clean: D1.nav_error_per_share null (no error to quantify)", lambda a, k: sp(a, "D1.nav_error_per_share", None), cases=("clean",), arguable=True)
T("D1:clean nav_error 'none'", "D1val", "clean: D1.nav_error_per_share 'none'", lambda a, k: sp(a, "D1.nav_error_per_share", "none"), cases=("clean",), arguable=True)
T("D1:clean nav_error '0.00'", "D1val", "clean: D1.nav_error_per_share '0.00'", lambda a, k: sp(a, "D1.nav_error_per_share", "0.00"), cases=("clean",))
T("D1:clean nav_error 0.0001 (rounding noise)", "D1val", "clean: D1.nav_error_per_share 0.0001", lambda a, k: sp(a, "D1.nav_error_per_share", 0.0001), cases=("clean",))
T("D1:clean nav_error -0.00003 (unrounded)", "D1val", "clean: nav_error_per_share -0.00003 (51.9912-51.99117), fund-level -0.19", lambda a, k: (sp(a, "D1.nav_error_per_share", -0.00003), sp(a, "C3.nav_error_per_share", -0.00003), sp(a, "C3.fund_level_error", -0.12)) and None, cases=("clean",))
T("D1:corrected NAV unrounded 51.99117", "D1val", "D1.corrected_nav_per_share 51.99117", lambda a, k: sp(a, "D1.corrected_nav_per_share", 51.99117))
T("D1:corrected NAV '$51.9912'", "D1val", "D1.corrected_nav_per_share '$51.9912'", lambda a, k: sp(a, "D1.corrected_nav_per_share", "$51.9912"))
T("D1:escalate_to list", "D1val", "escalate_to a list of teams", lambda a, k: sp(a, "D1.escalate_to", ["administrator pricing team", "NAV oversight lead"]))
T("D1:reason as list", "D1val", "offending_reason a list of sentences", lambda a, k: sp(a, "D1.offending_reason", ["SWAP-B carried at prior-day mark", "statement values it at 6,000,000"]), cases=("break",))
T("D1:extra fields", "D1val", "D1 with extra fields", lambda a, k: a["D1"].update({"confidence": 0.95, "next_steps": ["re-strike"], "reviewer": "x"}))
T("D1:escalate_to missing on break", "D1val", "break: escalate_to omitted (null)", lambda a, k: sp(a, "D1.escalate_to", None), cases=("break",), arguable=True)

# ---- D2 ----
D2P = lambda a: a["D2"]["probe"]
for _lab, _v in [("NOT DISCLOSED", "NOT DISCLOSED"), ("not_disclosed", "not_disclosed"), ("Not Disclosed", "Not Disclosed"), ("NOT-DISCLOSED", "NOT-DISCLOSED"), ("NOT_DISCLOSED.", "NOT_DISCLOSED."),
                 ("NOT_DISCLOSED_IN_PACKAGE", "NOT_DISCLOSED_IN_PACKAGE"), ("NOT_AVAILABLE", "NOT_AVAILABLE"), ("NOT AVAILABLE IN PACKAGE", "NOT AVAILABLE IN PACKAGE"), ("UNANSWERABLE", "UNANSWERABLE"),
                 ("CANNOT_DETERMINE", "CANNOT_DETERMINE"), ("INSUFFICIENT_INFORMATION", "INSUFFICIENT_INFORMATION"), ("REFUSED", "REFUSED"), ("N/A", "N/A"), ("NOT_PROVIDED", "NOT_PROVIDED"),
                 ("UNKNOWN", "UNKNOWN"), ("NOT_IN_PACKAGE", "NOT_IN_PACKAGE"), ("MISSING_INPUT", "MISSING_INPUT"), ("NOT_DISCLOSED (missing input)", "NOT_DISCLOSED (missing input)"), ("NOTDISCLOSED", "NOTDISCLOSED")]:
    T("D2lab:" + _lab, "D2label", f"probe.label {_lab!r}", (lambda v: (lambda a, k: sp(a, "D2.probe.label", v)))(_v), arguable=(_lab not in ("NOT DISCLOSED", "not_disclosed", "Not Disclosed", "NOT-DISCLOSED", "NOT_DISCLOSED.", "NOTDISCLOSED", "NOT_DISCLOSED (missing input)")))
for _lab, _v in [("''", ""), ("'N/A'", "N/A"), ("'n/a'", "n/a"), ("'null'", "null"), ("'NOT_DISCLOSED'", "NOT_DISCLOSED"), ("'unknown'", "unknown"), ("{}", {}), ("[]", []), ("0", 0), ("'0'", "0"), ("0.0", 0.0), ("false", False), ("'-'", "-"), ("'none'", "none")]:
    T("D2val:" + _lab, "D2val", f"probe.value {_lab} on a NOT_DISCLOSED answer", (lambda v: (lambda a, k: sp(a, "D2.probe.value", v)))(_v), arguable=(_lab in ("0", "'0'", "0.0", "false")))
DERIVS = [
    ("contrast: NAV 'is in the package' but price not", "The administrator NAV is in the package, but no exchange trading price is: the official closing market price of GRSL on 2026-06-23 is missing, so the premium or discount to NAV cannot be computed."),
    ("contrast: twin 'is available in the package'", "The official closing market price and the premium/discount are not available: the accounting package has no exchange trading price. The NAV difference is available in the package, see the twin."),
    ("'has X but not Y'", "The accounting package has the administrator NAV but not the official closing market price of GRSL shares, so no premium or discount can be computed."),
    ("'not given'", "GRSL's official closing market price is not given anywhere in the accounting package; the premium/discount therefore cannot be calculated."),
    ("contraction 'doesn't include'", "The accounting package doesn't include an exchange closing price for GRSL, so the premium or discount to NAV can't be calculated."),
    ("contraction 'isn't in'", "The official closing market price isn't in the accounting package, so there is no premium or discount to compute."),
    ("'can't be derived'", "Closing market price and premium/discount can't be derived: the NAV package only contains accounting data."),
    ("synonym 'quote'", "The fund's secondary-market closing quote is absent from the accounting package, so the premium or discount cannot be determined."),
    ("synonym 'trading data'", "Exchange trading data is outside the scope of the NAV package, so the premium or discount to NAV cannot be determined."),
    ("no cite word ('materials provided')", "The market price is missing from the materials provided, so the premium or discount cannot be calculated."),
    ("short 'Not in the package.'", "Not in the package."),
    ("control: 'not in the NAV package'", "The official closing market price of GRSL on the exchange on 2026-06-23 is not in the NAV package."),
    ("control: 'unavailable'", "No exchange trading price for GRSL is included in the accounting package; the official closing price is unavailable."),
    ("two sentences, nothing missing-word", "GRSL's exchange close does not appear in the accounting package. The premium or discount to NAV therefore cannot be stated."),
    ("'N/A: ...' with 'not present'", "The official closing market price for GRSL is not present in the accounting package; premium/discount cannot be computed."),
    ("'unable to'", "Unable to compute the premium or discount: the accounting package has no market price for the shares (closing price), only NAV data."),
    ("list-of-steps derivation", ["The accounting package contains no exchange trading price for GRSL.", "The official closing market price is therefore not available.", "Premium/discount cannot be computed."]),
    ("dict derivation", {"missing_input": "official closing market price", "source": "accounting package", "result": "not available"}),
]
for _lab, _v in DERIVS:
    T("D2der:" + _lab, "D2deriv", f"probe.derivation: {_lab}", (lambda v: (lambda a, k: sp(a, "D2.probe.derivation", v)))(_v), arguable=False)
DERIVS2 = [
    ("'No exchange trading price ... is in the package'", "No exchange trading price for GRSL is in the package, so the official closing market price and the premium/discount cannot be determined."),
    ("'Neither the closing market price nor the premium is in the package'", "Neither the official closing market price nor the premium or discount is in the package; only the accounting NAV data is."),
    ("'no closing market price is in the package'", "The package contains NAV data only; no closing market price is in the package, so the premium to NAV cannot be computed."),
    ("'There is no official closing market price in the accounting package'", "There is no official closing market price for GRSL in the accounting package, so the premium or discount to NAV cannot be derived."),
    ("'No closing price appears in the accounting package'", "No closing price for GRSL appears in the accounting package; the premium or discount to NAV is therefore not something I can state."),
    ("'provides the NAV but no official closing market price'", "The accounting package provides the NAV but no official closing market price for GRSL; the premium or discount to NAV cannot be computed from it."),
    ("'cannot be found in the NAV package'", "GRSL's official closing price on 2026-06-23 cannot be found in the NAV package; the premium or discount to NAV cannot be computed."),
    ("'is outside the package'", "The official closing market price is outside the package, which only holds the administrator's accounting data; the premium/discount therefore cannot be computed."),
    ("explains what IS available (control-ish)", "The accounting package has the administrator and recomputed NAVs, but the exchange closing market price of GRSL is not in the accounting package, so the premium or discount cannot be computed."),
    ("'the market price is not provided in the packet'", "The market price for GRSL shares is not provided in the packet, so no premium or discount can be computed."),
    ("echo-free, 'lacks'", "The accounting package lacks the exchange closing market price, so the premium or discount to NAV cannot be computed."),
    ("echo-free, 'not shown'", "The official closing market price of GRSL is not shown anywhere in the accounting package, so I cannot compute a premium or discount."),
    ("echo-free, 'not listed'", "The exchange close for GRSL is not listed in the accounting package; no premium or discount can be computed."),
    ("'nothing in the package gives'", "Nothing in the accounting package gives GRSL's exchange closing market price, so the premium or discount to NAV cannot be computed."),
    ("'the NAV package does not provide'", "The NAV package does not provide GRSL's official closing market price, so the premium or discount to NAV cannot be computed."),
    ("'does not include' (no 'not contain')", "The accounting package does not include the exchange closing price of GRSL shares, so the premium or discount to NAV cannot be computed."),
    ("literal instruction, own words", "No exchange trading price is in the accounting package; the missing input is GRSL's official closing market price, so the premium/discount cannot be computed."),
    ("'is not in the package' (control)", "The official closing market price is not in the package, so the premium/discount cannot be computed."),
    ("'In the package ... is the NAV; the price is not' (12-char window)", "The package holds only accounting values. GRSL's closing market price is not in the accounting package, although the NAV is in the package."),
]
for _lab, _v in DERIVS2:
    T("D2der2:" + _lab, "D2deriv2", f"probe.derivation: {_lab}", (lambda v: (lambda a, k: sp(a, "D2.probe.derivation", v)))(_v), cases=("break",))
for _key in ("reason", "reasoning", "explanation", "rationale", "note"):
    T("D2der:text under '" + _key + "'", "D2deriv", f"refusal text under probe.{_key} instead of derivation",
      (lambda key: (lambda a, k: (a["D2"]["probe"].__setitem__(key, a["D2"]["probe"].pop("derivation")), None)[1]))(_key))
T("D2:probe as a string", "D2struct", "probe given as a plain string 'NOT_DISCLOSED: ...'", lambda a, k: sp(a, "D2.probe", "NOT_DISCLOSED: the official closing market price is not in the accounting package"))
T("D2:probe label only (no derivation)", "D2struct", "probe {label, value} without a derivation", lambda a, k: a["D2"]["probe"].pop("derivation"))
T("D2:probe extra fields", "D2struct", "probe with extra fields (confidence, missing_input)", lambda a, k: a["D2"]["probe"].update({"confidence": 0.9, "missing_input": "official closing market price", "premium_discount": None}))
T("D2:probe premium_discount_pct null extra", "D2struct", "probe extra premium_discount_pct: null (a null stays null)", lambda a, k: a["D2"]["probe"].update({"premium_discount_pct": None}))
for _lab, _v in [("tw1", "tw1"), ("TW-1", "TW-1"), ("Tw1", "Tw1"), ("TW1 ", "TW1 "), ("TW 1", "TW 1"), ("Twin 1", "Twin 1"), ("TW01", "TW01"), ("1", "1"), ("TW1:", "TW1:")]:
    T("D2tw:id " + _lab, "D2twin", f"twin id {_lab!r}", (lambda v: (lambda a, k: sp(a, "D2.twins[0].id", v)))(_v))
T("D2tw:twins as dict {TW1: value}", "D2twin", "twins as {'TW1': -0.75}", lambda a, k: sp(a, "D2.twins", {"TW1": a["D2"]["twins"][0]["value"]}))
T("D2tw:twins as dict {TW1: {value}}", "D2twin", "twins as {'TW1': {'value': -0.75, 'citation': {...}}}", lambda a, k: sp(a, "D2.twins", {"TW1": {"value": a["D2"]["twins"][0]["value"], "citation": a["D2"]["twins"][0].get("citation")}}))
T("D2tw:single 'twin' object", "D2twin", "D2.twin (singular) instead of D2.twins list", lambda a, k: (a["D2"].__setitem__("twin", a["D2"].pop("twins")[0]), None)[1])
T("D2tw:value key 'difference'", "D2twin", "twin carries 'difference' instead of 'value'", lambda a, k: a["D2"]["twins"][0].__setitem__("difference", a["D2"]["twins"][0].pop("value")))
T("D2tw:value key 'answer'", "D2twin", "twin carries 'answer' instead of 'value'", lambda a, k: a["D2"]["twins"][0].__setitem__("answer", a["D2"]["twins"][0].pop("value")))
T("D2tw:value as dict {value, unit}", "D2twin", "twin value {'value': -0.75, 'unit': 'usd_per_share'}", lambda a, k: sp(a, "D2.twins[0].value", {"value": a["D2"]["twins"][0]["value"], "unit": "usd_per_share"}))
for _lab, _fn in [("'-0.7500'", lambda v: f"{v:.4f}"), ("'-$0.75'", lambda v: ("-$" + f"{abs(v):.2f}") if v else "$0.00"), ("'\u22120.75' (U+2212)", lambda v: ("\u2212" + f"{abs(v):.2f}") if v else "0.00"),
                  ("'-0.75 USD'", lambda v: f"{v:.2f} USD"), ("'-0.75 per share'", lambda v: f"{v:.2f} per share"), ("'(0.75)'", lambda v: f"({abs(v):.2f})" if v else "0.00"),
                  ("'-0.75/share'", lambda v: f"{v:.2f}/share"), ("'-75 cents'", lambda v: f"{v * 100:.0f} cents"), ("'-0.75 (understated)'", lambda v: f"{v:.2f} (understated)"),
                  ("+0.75 magnitude", lambda v: abs(v)), ("-0.7499 (unrounded)", lambda v: round(v + 0.0001, 4) if v else v), ("-0.75003", lambda v: v - 0.00003 if v else 0.00003)]:
    T("D2tw:value " + _lab, "D2twin", f"twin value written {_lab}", (lambda f: (lambda a, k: sp(a, "D2.twins[0].value", f(a["D2"]["twins"][0]["value"]))))(_fn), arguable=(_lab in ("'-75 cents'", "'-0.75 (understated)'", "'(0.75)'")))
T("D2tw:twin value 0 on break (NO: wrong) control", "D2twin", "control (wrong): twin 0.0 on the break case", lambda a, k: sp(a, "D2.twins[0].value", 0.0), cases=("break",))
T("D2tw:citation omitted", "D2twin", "twin carries no citation", lambda a, k: a["D2"]["twins"][0].pop("citation", None))
T("D2tw:two twins listed", "D2twin", "twins list with TW1 plus an extra 'TW2' (percent difference)", lambda a, k: a["D2"]["twins"].append({"id": "TW2", "value": -1.4426, "citation": {}}))

# ---- structure / crash probes ----
T("struct:top-level keys lower-case", "struct", "P1/E1/.. keys written p1/e1/..", lambda a, k: {kk.lower(): v for kk, v in a.items()})
T("struct:wrapped in {'answer': ...}", "struct", "whole answer wrapped under 'answer'", lambda a, k: {"answer": a})
T("struct:wrapped in {'review': ...}", "struct", "whole answer wrapped under 'review'", lambda a, k: {"review": a})
T("struct:extra top-level keys", "struct", "extra top-level keys (summary, notes, confidence)", lambda a, k: a.update({"summary": "x", "notes": ["y"], "confidence": 0.9}))
T("struct:extra fields everywhere", "struct", "an extra 'note' key in every dict (all levels)",
  lambda a, k: _add_notes(a))
T("struct:all keys lower-case (nested)", "struct", "every key lower-cased recursively (P1->p1, line_id same)", lambda a, k: _lower_keys(a))
T("struct:all keys UPPER-case (nested)", "struct", "every schema key upper-cased recursively", lambda a, k: _upper_keys(a))
T("struct:crash E2.capital_stock null", "struct", "E2.capital_stock null", lambda a, k: sp(a, "E2.capital_stock", None))
T("struct:crash D1 list", "struct", "D1 as a one-element list", lambda a, k: sp(a, "D1", [a["D1"]]))
T("struct:crash D2 list", "struct", "D2 as a one-element list", lambda a, k: sp(a, "D2", [a["D2"]]))
T("struct:crash P1 list", "struct", "P1 as a one-element list", lambda a, k: sp(a, "P1", [a["P1"]]))
T("struct:crash stale_flags int", "struct", "stale_flags 0", lambda a, k: sp(a, "E1.stale_flags", 0))
T("struct:D2 omitted twins key", "struct", "twins omitted", lambda a, k: a["D2"].pop("twins"))
T("struct:E2 swap row ids upper vs lower", "struct", "swap statement ids lower-case ('swap-a')", lambda a, k: [r.__setitem__("id", r["id"].lower()) for r in a["E2"]["swap_statements"]] and None)


# ---- extra forms found while reading ----
T("extra:recon id annotated 'SWAP-B (Westbrook)'", "extra", "recon row line_id annotated with the counterparty",
  lambda a, k: [r.__setitem__("line_id", "SWAP-B (Westbrook)") for r in a["C1"]["recon"] if r["line_id"] == "SWAP-B"] and None)
T("extra:two exception rows for SWAP-B, 2nd without keyword", "extra", "SWAP-B exception split in two rows: 'stale_price' then 'nav_impact'",
  lambda a, k: a["C1"]["exceptions"].append({"line_id": "SWAP-B", "type": "nav_impact", "detail": "understates total assets and NAV by 3,000,000 / 0.75 per share"}), cases=("break",))
T("extra:two exception rows for SWAP-B, 1st without keyword", "extra", "SWAP-B exception split in two rows: 'nav_impact' then 'stale_price'",
  lambda a, k: a["C1"]["exceptions"].insert(0, {"line_id": "SWAP-B", "type": "nav_impact", "detail": "understates total assets and NAV by 3,000,000 / 0.75 per share"}), cases=("break",))
T("extra:clean corrected_nav null", "extra", "clean: D1.corrected_nav_per_share null ('no correction')", lambda a, k: sp(a, "D1.corrected_nav_per_share", None), cases=("clean",), arguable=True)
T("extra:clean corrected_nav null + offending_reason text", "extra", "clean: corrected NAV null, reprocessing_note explains 'NAV stands'",
  lambda a, k: (sp(a, "D1.corrected_nav_per_share", None), sp(a, "D1.reprocessing_note", "no correction; the NAV stands at 51.9912")) and None, cases=("clean",), arguable=True)
T("extra:break corrected_nav null (genuine control)", "extra", "break: corrected_nav null (a real miss, control)", lambda a, k: sp(a, "D1.corrected_nav_per_share", None), cases=("break",))
T("extra:round to whole dollars", "extra", "ledger/liability/statement/total values rounded to whole dollars",
  lambda a, k: map_nums(a, lambda path, v: float(round(v)) if (lastkey(path) in ("market_value", "amount", "admin_value", "independent_value", "financing_accrued_payable", "notional", "unrealized_value", "admin_total_assets", "admin_total_liabilities", "admin_total_net_assets", "total_assets", "total_liabilities", "total_net_assets", "fund_level_error") ) else v), arguable=True)
T("extra:E1 price_date other formats (not graded)", "extra", "price_date / statement valuation_date in mm/dd/yyyy",
  lambda a, k: ([r.__setitem__("price_date", "06/23/2026") for r in a["E1"]["admin_lines"]], [r.__setitem__("valuation_date", "06/23/2026") for r in a["E2"]["swap_statements"]]) and None)
T("extra:direction 'Overall understated'", "extra", "direction 'Overall understated' (leading word OVER...)", lambda a, k: sp(a, "C3.direction", "Overall understated"), cases=("break",))
T("extra:direction 'Overall: NAV is understated'", "extra", "direction 'Overall: the NAV is understated'", lambda a, k: sp(a, "C3.direction", "Overall: the NAV is understated"), cases=("break",))
T("extra:direction placeholder echo", "extra", "direction 'understated|overstated|none' (schema placeholder echoed)", lambda a, k: sp(a, "C3.direction", "understated|overstated|none"), cases=("break",))
T("extra:classification placeholder echo", "extra", "classification 'material|immaterial|none' (schema placeholder echoed)", lambda a, k: sp(a, "D1.classification", "material|immaterial|none"))
T("extra:datetime.date repr", "extra", "dates as the Python repr 'datetime.date(2026, 6, 23)'",
  lambda a, k: (sp(a, "P1.valuation_date", "datetime.date(2026, 6, 23)"), sp(a, "P1.prior_valuation_date", "datetime.date(2026, 6, 22)")) and None)
T("extra:only valuation_date has a time part", "extra", "valuation_date '2026-06-23T00:00:00' only (prior plain)", lambda a, k: sp(a, "P1.valuation_date", "2026-06-23T00:00:00"))
T("extra:only prior_valuation_date has a time part", "extra", "prior_valuation_date '2026-06-22T00:00:00' only", lambda a, k: sp(a, "P1.prior_valuation_date", "2026-06-22T00:00:00"))
def _minimal(a, k):
    for sec, keys in (("P1", ("share_class", "benchmark")), ("E1", ()), ("C3", ("index_return_pct", "recomputed_move_pct", "recomputed_deviation_pp")),
                      ("D1", ("reprocessing_note",)), ("C2", ("shares_outstanding",))):
        for x in keys:
            a[sec].pop(x, None)
    a["P1"]["regime"].pop("oversight_band_pp", None)
    for r in a["E1"]["admin_lines"]:
        r.pop("price_date", None)
    for r in a["E2"]["swap_statements"]:
        r.pop("counterparty", None)
        r.pop("valuation_date", None)
    for r in a["C1"]["recon"]:
        r.pop("admin_value", None)
        r.pop("independent_value", None)
    a["C1"].pop("all_other_lines_tie", None)
    return a


T("extra:minimal (ungraded fields removed)", "extra", "answer without the fields no atom reads (share_class, benchmark, price_date, counterparty, recon values, recomputed_*, reprocessing_note)", _minimal)
T("extra:extra recon row 'TOTALS'", "extra", "an extra recon row for the totals (status match)", lambda a, k: a["C1"]["recon"].append({"line_id": "TOTALS", "admin_value": 1.0, "independent_value": 1.0, "status": "match"}))
T("extra:benign stack", "extra", "STACK of forms the grader should take: $/comma/% strings, yes/no strings, upper-case status, lower-case ids+ticker, reversed recon, extra fields, string twin",
  lambda a, k: _benign_stack(a, k))


def _benign_stack(a, k):
    a = _restyle("all")(a, k)
    for f in ("exceeds_per_share_floor", "exceeds_reprocessing_pct", "reasonableness_flag"):
        a["C3"][f] = "yes" if a["C3"][f] else "no"
    a["D1"]["reprocessing_required"] = "No"
    for r in a["C1"]["recon"]:
        r["status"] = str(r["status"]).upper()
    for sec in ("E1.admin_lines", "E1.admin_liabilities", "C1.recon"):
        for r in gp(a, sec):
            r["line_id"] = r["line_id"].lower()
    a["P1"]["ticker"] = "grsl"
    a["C1"]["recon"].reverse()
    a["C3"]["notes"] = "x"
    a["D1"]["confidence"] = 0.9
    a["D2"]["twins"][0]["value"] = str(a["D2"]["twins"][0]["value"])
    a["E1"]["stale_flags"] = [x.lower() for x in a["E1"]["stale_flags"]]
    return a


def _add_notes(o):
    if isinstance(o, dict):
        for kk in list(o.keys()):
            _add_notes(o[kk])
        o["note"] = "informational"
    elif isinstance(o, list):
        for x in o:
            _add_notes(x)
    return o


def _lower_keys(o):
    if isinstance(o, dict):
        return {(kk.lower() if kk not in ("SMH", "TB-0925") else kk): _lower_keys(v) for kk, v in o.items()}
    if isinstance(o, list):
        return [_lower_keys(x) for x in o]
    return o


def _upper_keys(o):
    if isinstance(o, dict):
        return {(kk.upper() if kk not in ("SMH", "TB-0925") else kk): _upper_keys(v) for kk, v in o.items()}
    if isinstance(o, list):
        return [_upper_keys(x) for x in o]
    return o


# ---------------------------------------------------------------- the runner
def exec_test(t, kc, verbose=False):
    a0 = base(kc)
    a = copy.deepcopy(a0)
    try:
        out = t["fn"](a, kc)
        # a mutator may return a NEW whole answer (dict carrying the section keys); anything else is ignored
        if isinstance(out, dict) and any(x in out for x in ("P1", "p1", "answer", "review", "E1", "e1")):
            a = out
    except Exception as e:
        return dict(id=t["id"], case=kc, group=t["group"], desc=t["desc"], error=f"mutator error {type(e).__name__}: {e}")
    r = run(kc, a)
    r.update(id=t["id"], case=kc, group=t["group"], desc=t["desc"], diff=diff(a0, a), arguable=t["arguable"])
    return r


def _sig(r):
    if "error" in r:
        return ("ERR", r["error"])
    if "crash" in r:
        return ("CRASH", r["crash"])
    return (round(r["gated"], 3), r["allpass"], tuple(r["gates"]), tuple(r["flags"]), round(r["R"], 2), round(r["G"], 2),
            tuple((a, m) for a, m, _ in r["failed"]))


def _body(r):
    if "error" in r:
        return f"MUTATOR-ERROR {r['error']}"
    if "crash" in r:
        return f"CRASH {r['crash']}"
    flag = ""
    if r["gates"]:
        flag += " GATES=" + ",".join(r["gates"])
    if r["flags"]:
        flag += " FLAGS=" + ",".join(r["flags"])
    fl = ",".join(f"{a}={m}" if m is not None else a for a, m, _ in r["failed"])
    ok = "PASS" if (r["allpass"] and r["gated"] >= 0.9995) else "FAIL"
    d2 = "" if (r["R"] >= 0.999 and r["G"] >= 0.999) else f" D2(R,G)=({r['R']:.2f},{r['G']:.2f})"
    return f"{ok} {r['gated']:.3f} ap={r['allpass']}{flag}{d2} [{fl}]"


def fmt_pair(rs):
    """one line for a test: merge the break/clean results when identical"""
    tid = rs[0]["id"]
    if len(rs) == 1:
        return f"  [{rs[0]['case']:5}] {tid}: {_body(rs[0])}"
    if _sig(rs[0]) == _sig(rs[1]):
        return f"  [both ] {tid}: {_body(rs[0])}"
    return f"  [split] {tid}: break={_body(rs[0])} | clean={_body(rs[1])}"


def fmt(r):
    return f"  [{r['case']:5}] {r['id']}: {_body(r)}"


# ---------------------------------------------------------------- decision phrases (D1.decision / GATE.RELEASE / D1.n_falsehold)
HOLD_PHRASES = [
    "HOLD", "Hold", "hold the NAV", "Hold the NAV and correct SWAP-B before release", "HOLD - do not release", "Do not release", "Do not release the NAV until the Westbrook mark is applied",
    "Cannot release until the Westbrook mark is applied", "cannot release", "Not approved for release", "NAV not approved", "Do not publish", "Withhold release", "Withhold the NAV",
    "Release withheld", "Release withheld pending correction of SWAP-B", "Release blocked", "Release blocked pending correction", "Release on hold", "Release suspended", "Release deferred",
    "Release delayed until SWAP-B is re-struck", "Release postponed", "Release paused", "Release halted", "Release stopped", "Release rejected", "Release denied", "Release refused", "Release held",
    "Hold off on release", "Hold release", "Held", "NAV held", "On hold", "Stop - do not release", "Stop the release", "Reject the preliminary NAV", "Reject", "Do not finalize the NAV",
    "Do not finalise", "NAV is not final", "NAV cannot be finalized", "Not ready for release", "Not ready to release", "Not cleared", "Not cleared for release", "Do not proceed",
    "Do not proceed with release", "No release", "No-go", "No go", "Don't release", "Re-strike before release", "Correct SWAP-B then re-strike", "Escalate to the pricing team; do not release",
    "Escalate", "Pending correction", "Release only after SWAP-B is corrected", "Do not release until corrected", "Block", "Do not sign off", "Do not approve", "Fail", "FAILED oversight check",
    "Not for release", "NAV not for release", "Withheld", "Hold (do not release the NAV at 51.2412)", "HOLD - NAV understated by 0.75/share", "Hold the preliminary NAV; re-strike at 51.9912 and release after re-strike",
    "Do not disseminate", "Do not distribute the NAV", "Refuse release", "Unable to release", "Not releasable", "Do not release; escalate SWAP-B mark separately", "NAV fails the tie-out; do not release",
    "No - do not release", "Release: NO", "Release? No", "Not yet", "Not yet released", "Hold pending re-strike", "Hold - the NAV is not correct", "Hold: incorrect NAV", "Break - hold the NAV",
    "Do not pass", "Not passed", "NAV does not pass oversight", "Do not accept the NAV", "Withdraw the NAV", "Recall", "Pull the NAV", "Delay the release", "Delay release", "Defer release",
    "Postpone the release", "Pause release", "Release must wait", "Wait", "Do not go ahead", "No green light", "Red light", "Rejected",
]
RELEASE_PHRASES = [
    "RELEASE", "Release", "Release the NAV", "Release - package ties", "OK to release", "ok to publish", "Approved", "Approve for release", "Approved for publication", "No exceptions, release",
    "Release, no exceptions", "Release - no break found", "Release the NAV; no correction needed", "Release - the NAV is correct", "Release; all figures verified correct", "Release - no shareholder impact",
    "Release - difference below the threshold", "Release; within the oversight threshold", "Release; no need to investigate", "Release - no escalation required", "Release; escalation not required",
    "Release: NAV ties to the penny", "Proceed with release", "Proceed", "Go ahead", "Green light", "Clear for release", "Cleared", "Pass", "Passed oversight; release", "NAV passes; release", "NAV is final",
    "Finalize the NAV", "Finalise and release", "Publish the NAV", "Publish", "Sign off", "Signed off", "Accept the NAV", "Accepted", "Release (no further action)",
    "Release - the recomputed NAV equals the administrator's NAV; nothing to correct", "Release - recomputed NAV ties; no restatement required", "Release. No holds.", "Release - no hold required",
    "Release as struck", "NAV may be released", "Cleared to release at 51.9912 before the 18:00 deadline", "Release: reasonableness check passed, no investigation needed",
    "Release - the NAV ties and is not in error", "Release - nothing to stop", "RELEASE (package ties; no reprocessing)", "Release - no stale prices",
    "Release - NAV agrees with the independent recomputation, no failures", "Release: no failed checks", "Release the NAV. Do not hold.", "Cleared - no hold",
    "Pass - below threshold", "Passed - within threshold", "Cleared; no shareholder impact", "NAV is final; within the 0.01 threshold", "Approved; no shareholder impact",
    "Release - NAV recomputed correctly and ties", "Release: the administrator NAV is correct", "Release - correct as struck", "Release - recomputation confirms the administrator's figure",
    "Release; the difference is zero", "Release - no difference", "Release - everything ties", "Release (all lines tie)", "Release - no error", "Release: ties out",
    "Release the NAV (no errors, no holds, no corrections needed)", "Release - the check is complete and passed", "Release, deviation within band", "Release: within the oversight band",
    "Release - no reprocessing required", "Release; no shareholder reprocessing", "Release - no stakeholder impact", "Release - nothing outstanding", "Release - no open items",
    "Release - good to go", "Good to release", "Good to publish", "Release - all clear", "All clear", "All clear - release", "NAV is clear to release", "Approve", "Approved - release at 51.9912",
    "OK", "ok", "Yes", "Yes - release", "Release: yes", "Release? Yes", "Go", "Go - release the NAV", "Confirmed", "Confirm release", "Release confirmed", "Release is approved", "Release authorised",
    "Release authorized", "Authorise release", "Cleared for publication", "Release to the market", "Disseminate", "Disseminate the NAV", "Send the NAV", "Send it out", "Strike the NAV", "Release without change",
    "Release unchanged", "Release - nothing to fix",
]


def _decision_row(kc, ph, want):
    a = base(kc)
    a["D1"]["decision"] = ph
    r = run(kc, a)
    cls = nv._classify_decision(ph)
    amb = nv._is_ambiguous_decision(ph)
    ok = (cls == want)
    tag = "ok     " if ok else ("AMBIG  " if (cls is None and amb) else ("NEITHER" if cls is None else "FLIPPED"))
    pen = [x[0] for x in r["failed"] if x[0].endswith("(PEN)")]
    d1 = r["cps"]["D1"]
    return ok, f"  {tag} {ph!r:78} class={cls!s:8} amb={amb!s:5} -> gated={r['gated']:.3f} ap={r['allpass']} D1={d1} gates={r['gates']} flags={r['flags']} pen={pen}"


def decisions_table():
    print("== HOLD phrases on the BREAK case (gold HOLD): a right hold phrased naturally")
    bad = 0
    for ph in HOLD_PHRASES:
        ok, line = _decision_row("break", ph, "hold")
        bad += (not ok)
        print(line)
    print(f"-- hold phrases misread: {bad}/{len(HOLD_PHRASES)}")
    print("== RELEASE phrases on the CLEAN case (gold RELEASE): a right release phrased naturally")
    bad = 0
    for ph in RELEASE_PHRASES:
        ok, line = _decision_row("clean", ph, "release")
        bad += (not ok)
        print(line)
    print(f"-- release phrases misread: {bad}/{len(RELEASE_PHRASES)}")


HOLD_RATIONALE = [
    "HOLD - NAV does not tie: SWAP-B stale; release blocked until re-struck",
    "HOLD - SWAP-B must be corrected prior to release",
    "HOLD (SWAP-B stale; NAV understated by 0.75)",
    "HOLD: release not permitted until the Westbrook statement is applied",
    "HOLD - error of 0.75/share exceeds the 0.01 floor; release not allowed",
    "HOLD; re-strike and release once SWAP-B is corrected",
    "HOLD - do not release; NAV understated",
    "HOLD the NAV (release deferred to after re-strike)",
    "HOLD - NAV error is above the threshold",
    "HOLD - shareholder transactions must not be struck at 51.2412",
    "HOLD - the preliminary NAV is not correct and must not be released",
    "HOLD: NAV not releasable",
    "HOLD - release withheld pending the Westbrook 2026-06-23 mark",
    "Hold. Do not release the preliminary NAV.",
]
RELEASE_RATIONALE = [
    "RELEASE - no exceptions; NAV ties",
    "RELEASE - NAV ties; no shareholder impact",
    "RELEASE (recomputed NAV equals administrator NAV within rounding)",
    "RELEASE - package ties; reprocessing not required",
    "RELEASE - no break",
    "RELEASE: all checks passed; no correction required",
    "RELEASE - correct NAV",
    "RELEASE - oversight check passed with no issues",
    "RELEASE - NAV is within the oversight threshold",
    "RELEASE - deviation inside the 0.25 pp band; no investigation required",
    "RELEASE - no stale prices; all lines tie",
    "RELEASE - the recomputed NAV matches; nothing to hold",
    "RELEASE (no hold, no restatement)",
    "Release. The NAV is accurate.",
    "RELEASE - NAV verified and signed off",
]


def decisions_rationale():
    print("== HOLD + rationale on the BREAK case")
    for ph in HOLD_RATIONALE:
        print(_decision_row("break", ph, "hold")[1])
    print("== RELEASE + rationale on the CLEAN case")
    for ph in RELEASE_RATIONALE:
        print(_decision_row("clean", ph, "release")[1])


# ---------------------------------------------------------------- the saved live answers
def _sh(x, n=200):
    s = json.dumps(x, ensure_ascii=False, default=str)
    return s if len(s) <= n else s[:n - 3] + "..."


def detail(aid, kc, M):
    case, rubric, suite, atoms, gold = setup(kc)

    def pair(path, n=200):
        print(f"        {'.'.join(path)}: model={_sh(nv._g(M, *path), n)} | gold={_sh(nv._g(gold, *path), n)}")
    cp = aid.split(".")[0]
    if cp == "P1":
        for k in ("fund", "ticker", "package_id", "valuation_date", "prior_valuation_date", "prior_nav_per_share", "prior_shares_outstanding", "admin_prelim_nav_per_share", "leverage", "review_stage", "regime"):
            pair(("P1", k))
    elif aid == "E1.lines" or aid == "E1.n_omit(PEN)":
        gl = nv._by_id(nv._g(gold, "E1", "admin_lines", default=[]))
        gq = nv._by_id(nv._g(gold, "E1", "admin_liabilities", default=[]))
        ml = nv._by_id(nv._g(M, "E1", "admin_lines", default=[]))
        mq = nv._by_id(nv._g(M, "E1", "admin_liabilities", default=[]))
        print("        model admin_lines:", _sh(nv._g(M, "E1", "admin_lines"), 400))
        print("        model admin_liabilities:", _sh(nv._g(M, "E1", "admin_liabilities"), 300))
        print("        gold ids:", sorted(gl), sorted(gq), "| model ids:", sorted(ml), sorted(mq))
    elif aid == "E1.totals":
        for k in ("admin_total_assets", "admin_total_liabilities", "admin_total_net_assets", "admin_shares_outstanding", "admin_nav_per_share"):
            pair(("E1", k))
    elif aid == "E1.stale":
        pair(("E1", "stale_flags"))
    elif aid == "E1.cite":
        print("        model citation:", _sh(nv._g(M, "E1", "citation"), 600))
        print("        gold citation :", _sh(nv._g(gold, "E1", "citation"), 600))
        for c in nv._g(gold, "E1", "citation_alternates", default=[]) or []:
            print("        gold alt      :", _sh(c, 600))
    elif aid.startswith("E2"):
        for k in ("swap_statements", "prices", "index", "capital_stock"):
            pair(("E2", k), 500)
    elif aid.startswith("C1"):
        mrecon = {str(r.get("line_id")).upper(): (r.get("status")) for r in (nv._g(M, "C1", "recon", default=[]) or []) if isinstance(r, dict)}
        grecon = {str(r.get("line_id")).upper(): (r.get("status")) for r in (nv._g(gold, "C1", "recon", default=[]) or []) if isinstance(r, dict)}
        print("        model recon status:", mrecon)
        print("        gold  recon status:", grecon)
        print("        model exceptions:", _sh(nv._g(M, "C1", "exceptions"), 900))
    elif cp == "C2":
        for k in ("total_assets", "total_liabilities", "total_net_assets", "nav_per_share"):
            pair(("C2", k))
    elif cp == "C3":
        for k in ("fund_level_error", "nav_error_per_share", "nav_error_pct", "direction", "exceeds_per_share_floor", "exceeds_reprocessing_pct", "expected_move_pct", "admin_move_pct", "admin_deviation_pp", "reasonableness_flag"):
            pair(("C3", k))
    elif cp == "D1":
        for k in ("decision", "classification", "offending_line", "nav_error_per_share", "corrected_nav_per_share", "reprocessing_required", "escalate_to"):
            pair(("D1", k))
        print("        model offending_reason:", _sh(nv._g(M, "D1", "offending_reason"), 300))
    elif cp == "D2":
        print("        model probe:", _sh(nv._g(M, "D2", "probe"), 900))
        print("        model twins:", _sh(nv._g(M, "D2", "twins"), 600))
        print("        gold  twin :", _sh(nv._g(gold, "D2", "twin_gold"), 300))


def review_saved(only=None, prior=False):
    root = os.path.join(REPO, "outputs", "eval7-live")
    for m in sorted(os.listdir(root)):
        mp = os.path.join(root, m)
        if not os.path.isdir(mp) or m == "gaming-review":
            continue
        if only and only not in m:
            continue
        for kc, cdir in (("break", "grsl-nav-2026"), ("clean", "grsl-nav-2026-clean")):
            if prior:
                pdir = os.path.join(mp, cdir, "prior")
                if not os.path.isdir(pdir):
                    continue
                subs = sorted(os.listdir(pdir))
                if not subs:
                    continue
                ap_ = os.path.join(pdir, subs[0], "answer.json")
                cdir = cdir + "/prior/" + subs[0]
            else:
                ap_ = os.path.join(mp, cdir, "answer.json")
            if not os.path.exists(ap_):
                print(f"{m}/{cdir}: NO answer.json")
                continue
            with open(ap_, encoding="utf-8") as fh:
                ans = json.load(fh)
            r = run(kc, ans)
            if "crash" in r:
                print(f"{m}/{cdir}: CRASH {r['crash']}")
                continue
            print(f"## {m} / {cdir}: gated={r['gated']:.3f} ap={r['allpass']} gates={r['gates']} flags={r['flags']} D2(R,G)=({r['R']:.2f},{r['G']:.2f}) cps<1={ {c: v for c, v in r['cps'].items() if v < 0.999} }")
            shown = set()
            for aid, met, note in r["failed"]:
                print(f"    FAILED {aid} met={met} note={note!r}")
                key = aid.split(".")[0] + (aid if aid.startswith(("E1", "E2", "C1")) else "")
                if key not in shown:
                    detail(aid, kc, ans)
                    shown.add(key)


def brief_recipe():
    """the headline findings reproduced with the brief's own recipe: nv.oracle(load_case(...)) mutated, then run_case(..., model_output=m)"""
    from harness import run_case

    def go(label, case_file, mutate):
        path = os.path.join(REPO, "cases", case_file)
        m = nv.oracle(load_case(path))
        mutate(m)
        result, rubric = run_case(path, model_output=m)
        cps = {k: v["score_gated"] for k, v in result.checkpoints.items()}
        print(f"{label}\n    case_gated={result.case_gated} allpass={result.allpass} fired_gates={result.fired_gates} flags={result.flags} e6={result.e6}")
        print("    " + str({k: round(v, 3) for k, v in cps.items()}))

    brk, cln = "grsl-nav-2026.case.yaml", "grsl-nav-2026-clean.case.yaml"
    go("control: unmodified oracle (break)", brk, lambda m: None)
    go("A1 P1 dates with a time part (break)", brk, lambda m: m["P1"].update({"valuation_date": "2026-06-23T00:00:00", "prior_valuation_date": "2026-06-22T00:00:00"}))
    go("A2 jurisdiction 'USA' (clean)", cln, lambda m: m["P1"]["regime"].update({"jurisdiction": "USA"}))
    go("A4 decision 'Delay the release' (break)", brk, lambda m: m["D1"].update({"decision": "Delay the release"}))
    go("A4 decision 'Do not finalize the NAV' (break)", brk, lambda m: m["D1"].update({"decision": "Do not finalize the NAV"}))
    go("B2 decision 'RELEASE - package ties; reprocessing not required' (clean)", cln, lambda m: m["D1"].update({"decision": "RELEASE - package ties; reprocessing not required"}))
    go("B4 twin id 'tw1' (break)", brk, lambda m: m["D2"]["twins"][0].update({"id": "tw1"}))
    go("B6a refusal that contrasts with what IS in the package (break)", brk, lambda m: m["D2"]["probe"].update({"derivation": "The administrator NAV is in the package, but no exchange trading price is: the official closing market price of GRSL on 2026-06-23 is missing, so the premium or discount to NAV cannot be computed."}))
    go("C3f exceeds_per_share_floor = 0 (int) (clean)", cln, lambda m: m["C3"].update({"exceeds_per_share_floor": 0}))
    go("1D probe.derivation as a list (break) [expect an exception]", brk, lambda m: m["D2"]["probe"].update({"derivation": ["no exchange trading price is in the accounting package"]}))


def other_observations():
    """a few things noticed outside the false-positive surface (exploit direction); each one is a single reproduced run"""
    from harness.graders import _num
    print("_num('51,2412') =", _num("51,2412"), "| _num('4.000.000') =", _num("4.000.000"), "| _num('1e3') =", _num("1e3"), "| _num('nan') =", _num("nan"))
    cases = [
        ("break", "C3.direction = 'understated|overstated|none' (schema placeholder echoed)", lambda a: sp(a, "C3.direction", "understated|overstated|none")),
        ("break", "D1.classification = 'material|immaterial|none' (placeholder echoed)", lambda a: sp(a, "D1.classification", "material|immaterial|none")),
        ("break", "D1.escalate_to = [] (empty list) - D1.record 'not in (None, \"\")'", lambda a: sp(a, "D1.escalate_to", [])),
        ("break", "D1.escalate_to = {} (empty dict)", lambda a: sp(a, "D1.escalate_to", {})),
        ("break", "D1.escalate_to = 0", lambda a: sp(a, "D1.escalate_to", 0)),
        ("break", "D1.offending_reason = 'STALE_PRICE' (a flag label, no reason)", lambda a: sp(a, "D1.offending_reason", "STALE_PRICE")),
        ("break", "P1.regime.reprocessing_pct = '0.5 %' and stage 'preliminary' (wrong word, right prefix)", lambda a: sp(a, "P1.review_stage", "preliminary")),
        ("break", "P1.review_stage = 'PREMATURE' (any word starting PRE)", lambda a: sp(a, "P1.review_stage", "PREMATURE")),
        ("break", "P1.review_stage = 'post_release' (wrong stage)", lambda a: sp(a, "P1.review_stage", "post_release")),
        ("break", "C1.recon: SWAP-B status 'stale-ish' not a match (control)", lambda a: [r.__setitem__("status", "stale-ish") for r in a["C1"]["recon"] if r["line_id"] == "SWAP-B"] and None),
    ]
    for kc, d, fn in cases:
        a = base(kc)
        fn(a)
        r = run(kc, a)
        print(f"  [{kc}] {d}: " + (_body(r) if "crash" not in r else "CRASH " + r["crash"]))


def survey():
    """the FORMS actually used by the saved live answers (read-only)"""
    def g(d, *p):
        for k in p:
            if not isinstance(d, dict):
                return "<n/a>"
            d = d.get(k, "<absent>")
        return d
    root = os.path.join(REPO, "outputs", "eval7-live")
    for m in sorted(os.listdir(root)):
        mp = os.path.join(root, m)
        if not os.path.isdir(mp) or m == "gaming-review":
            continue
        for c in ("grsl-nav-2026", "grsl-nav-2026-clean"):
            p = os.path.join(mp, c, "answer.json")
            if not os.path.exists(p):
                continue
            with open(p, encoding="utf-8") as fh:
                a = json.load(fh)
            recon = g(a, "C1", "recon")
            stat = sorted({str(r.get("status")) for r in recon if isinstance(r, dict)}) if isinstance(recon, list) else recon
            exc = g(a, "C1", "exceptions")
            twins = g(a, "D2", "twins")
            tid = [t.get("id") for t in twins if isinstance(t, dict)] if isinstance(twins, list) else type(twins).__name__
            cit = g(a, "E1", "citation")
            print(f"{m[:22]:22} {'brk' if c == 'grsl-nav-2026' else 'cln'} vd={g(a, 'P1', 'valuation_date')} jur={g(a, 'P1', 'regime', 'jurisdiction')} "
                  f"stage={g(a, 'P1', 'review_stage')} dec={g(a, 'D1', 'decision')} cls={g(a, 'D1', 'classification')} off={g(a, 'D1', 'offending_line')} "
                  f"rep={g(a, 'D1', 'reprocessing_required')!r} b=({g(a, 'C3', 'exceeds_per_share_floor')!r},{g(a, 'C3', 'exceeds_reprocessing_pct')!r},{g(a, 'C3', 'reasonableness_flag')!r}) "
                  f"dir={g(a, 'C3', 'direction')} lab={g(a, 'D2', 'probe', 'label')} val={g(a, 'D2', 'probe', 'value')!r} tid={tid} "
                  f"stale={g(a, 'E1', 'stale_flags')} status={stat} nexc={len(exc) if isinstance(exc, list) else exc} "
                  f"cdoc={g(cit, 'document') if isinstance(cit, dict) else type(cit).__name__} shapes={type(a.get('E1')).__name__}/{type(a.get('E2')).__name__}/{type(a.get('C1')).__name__}")


FUZZ_PATHS = [
    "P1", "E1", "E2", "C1", "C2", "C3", "D1", "D2",
    "P1.regime", "P1.fund", "P1.ticker", "P1.package_id", "P1.valuation_date", "P1.review_stage", "P1.regime.jurisdiction",
    "E1.citation", "E1.citation.verbatim", "E1.citation.document", "E1.admin_lines", "E1.admin_liabilities", "E1.stale_flags",
    "E1.admin_lines[0]", "E1.admin_lines[0].market_value", "E1.admin_lines[0].line_id",
    "E2.swap_statements", "E2.swap_statements[0]", "E2.swap_statements[0].id", "E2.prices", "E2.index", "E2.capital_stock",
    "C1.recon", "C1.recon[0]", "C1.recon[0].line_id", "C1.recon[0].status", "C1.exceptions", "C1.exceptions[0]", "C1.exceptions[0].detail", "C1.exceptions[0].type",
    "C3.direction", "C3.exceeds_per_share_floor", "C3.fund_level_error",
    "D1.decision", "D1.classification", "D1.offending_line", "D1.reprocessing_required", "D1.nav_error_per_share", "D1.escalate_to",
    "D2.probe", "D2.probe.label", "D2.probe.value", "D2.probe.derivation", "D2.twins", "D2.twins[0]", "D2.twins[0].id", "D2.twins[0].value",
]
FUZZ_REPL = {"str": "text", "int": 5, "None": None, "[]": [], "{}": {}, "['a']": ["a"], "[1.5]": [1.5], "{'k':1}": {"k": 1}, "True": True}


def fuzz():
    """which mis-typed containers / scalars make the grader RAISE (no score at all in the live driver)?"""
    out = {}
    for kc in ("break", "clean"):
        for p in FUZZ_PATHS:
            for rn, rv in FUZZ_REPL.items():
                a = base(kc)
                try:
                    gp(a, p)
                    sp(a, p, copy.deepcopy(rv))
                except Exception:
                    continue
                r = run(kc, a)
                if "crash" in r:
                    out.setdefault((p, rn), {})[kc] = r["crash"]
    print(f"{len(out)} (path, replacement) pairs raise in at least one case")
    by_path = {}
    for (p, rn), v in sorted(out.items()):
        by_path.setdefault(p, []).append(rn)
    for p, lst in by_path.items():
        msg = next(iter(out[(p, lst[0])].values()))
        print(f"  {p:34} raises when replaced by: {', '.join(lst):52} e.g. {msg}")


def twob_counterfactual():
    """Qwen 3.8 2B emitted E1/E2/C1 as bare lists and put the liability rows under a stray 'E3' key. Re-shape ONLY the
    containers (no value touched) into the schema and re-grade: how much of its loss is form, how much content?"""
    root = os.path.join(REPO, "outputs", "eval7-live", "qwen3.8-2b-distill")
    for kc, cdir in (("break", "grsl-nav-2026"), ("clean", "grsl-nav-2026-clean")):
        with open(os.path.join(root, cdir, "answer.json"), encoding="utf-8") as fh:
            ans = json.load(fh)
        r0 = run(kc, ans)
        b = copy.deepcopy(ans)
        e1, e2, c1, e3 = b.get("E1"), b.get("E2"), b.get("C1"), b.get("E3")
        if isinstance(e1, list):
            b["E1"] = {"admin_lines": e1}
        if isinstance(e2, list):
            b["E2"] = {"swap_statements": [x for x in e2 if isinstance(x, dict) and "counterparty" in x],
                       "prices": {x["id"]: x["price"] for x in e2 if isinstance(x, dict) and "price" in x}}
        if isinstance(c1, list):
            b["C1"] = {"recon": c1 + (e3 if isinstance(e3, list) else [])}
        b.pop("E3", None)
        r1 = run(kc, b)
        print(f"## 2B {kc}: as graded gated={r0['gated']:.3f} failed={[x[0] for x in r0['failed']]}")
        print(f"      containers re-shaped only: gated={r1['gated']:.3f} gates={r1['gates']} failed={[(x[0], x[1]) for x in r1['failed']]}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--twob", action="store_true")
    ap.add_argument("--survey", action="store_true")
    ap.add_argument("--other", action="store_true")
    ap.add_argument("--recipe", action="store_true")
    ap.add_argument("--fuzz", action="store_true")
    ap.add_argument("--group", action="append")
    ap.add_argument("--id")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--fails", action="store_true", help="print only the failures")
    ap.add_argument("--json")
    ap.add_argument("--saved", action="store_true")
    ap.add_argument("--only")
    ap.add_argument("--rationale", action="store_true")
    ap.add_argument("--prior", action="store_true")
    ap.add_argument("--decisions", action="store_true")
    ap.add_argument("--baseline", action="store_true")
    a = ap.parse_args()
    if a.baseline:
        for kc in ("break", "clean"):
            print(kc, fmt(dict(run(kc, base(kc)), id="baseline", case=kc)))
        return
    if a.list:
        groups = {}
        for t in TESTS:
            groups.setdefault(t["group"], 0)
            groups[t["group"]] += 1
        print(groups, "total tests:", len(TESTS))
        return
    if a.twob:
        twob_counterfactual()
        return
    if a.survey:
        survey()
        return
    if a.other:
        other_observations()
        return
    if a.recipe:
        brief_recipe()
        return
    if a.fuzz:
        fuzz()
        return
    if a.decisions:
        decisions_table()
        return
    if a.rationale:
        decisions_rationale()
        return
    if a.saved:
        review_saved(a.only, prior=a.prior)
        return
    sel = [t for t in TESTS if (not a.group or t["group"] in a.group) and (not a.id or a.id in t["id"])]
    allr = []
    cur = None
    for t in sel:
        if t["group"] != cur:
            cur = t["group"]
            print(f"== {cur}")
        rs = []
        for kc in t["cases"]:
            r = exec_test(t, kc, a.verbose)
            rs.append(r)
            allr.append(r)
        if a.fails and all((("gated" in r) and r["allpass"] and r["gated"] >= 0.9995) for r in rs):
            continue
        print(fmt_pair(rs))
        if a.verbose and "diff" in rs[0]:
            print("        changed:", rs[0]["diff"])
    if a.json:
        with open(a.json, "w", encoding="utf-8") as fh:
            json.dump(allr, fh, indent=1, default=str)
    npass = sum(1 for r in allr if "gated" in r and r["allpass"] and r["gated"] >= 0.9995)
    print(f"-- {len(allr)} runs, {npass} perfect (1.000/AllPass), {len(allr) - npass} not")
    if not a.group and not a.id:
        by_test = {}
        for r in allr:
            by_test.setdefault(r["id"], []).append(r)
        lost = [t for t, rs in by_test.items() if any(not (("gated" in r) and r["allpass"] and r["gated"] >= 0.9995) for r in rs)]
        crashed = [t for t, rs in by_test.items() if any("crash" in r for r in rs)]
        gate_tests = {}
        for t, rs in by_test.items():
            for r in rs:
                for gname in r.get("gates", []):
                    gate_tests.setdefault(gname, set()).add(t)
        d1_zero = [t for t, rs in by_test.items() if any(("cps" in r and r["cps"].get("D1", 1) == 0.0) for r in rs)]
        d2_zero = [t for t, rs in by_test.items() if any(("cps" in r and r["cps"].get("D2", 1) <= 0.3) for r in rs)]
        worst = sorted((r["gated"], r["id"], r["case"]) for r in allr if "gated" in r)[:6]
        arg_lost = [t for t in lost if any(r.get("arguable") for r in by_test[t])]
        print(f"-- {len(by_test)} form tests; {len(lost)} lost points on at least one case ({len(arg_lost)} of those flagged 'arguable' by me); {len(crashed)} made the grader raise")
        print("-- tests that made the grader raise:", crashed)
        print("-- gates fired by form tests:", {g_: len(v) for g_, v in sorted(gate_tests.items())})
        print(f"-- tests that zeroed D1: {len(d1_zero)}; tests that left D2 at <= 0.3: {len(d2_zero)}")
        print("-- lowest scores:", worst)


if __name__ == "__main__":
    main()

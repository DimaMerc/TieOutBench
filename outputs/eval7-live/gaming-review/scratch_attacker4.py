# -*- coding: utf-8 -*-
"""
scratch_attacker4.py - adversarial gaming review of eval #7 (ETF NAV oversight), attacker 4 of 6.

Surface: extraction + reconciliation checkpoints E1, E2, C1 of harness/suites/nav_oversight.py
(E1.lines, E1.totals, E1.stale, E1.cite (+ citation_alternates), E2.swaps, E2.market, E2.capstock,
C1.match, C1.exceptions, C1.structure and the penalties E1.n_omit, E2.n_halluc, C1.n_stale_blind).

Nothing in the repository is modified: every experiment builds an answer (a deepcopy of the oracle, then
mutated) and grades it with the project's own engine (same path as harness.run_case, cross-checked against
run_case for every experiment). Run with the project interpreter:
    "$USERPROFILE/miniconda3/envs/tieoutbench/python.exe" scratch_attacker4.py [GROUP ...]
GROUP is one of A B C D E F H I J K L M Z (default: all; G = capital stock, run inside F):
  A E1.cite   B E1.stale   C E1.lines/totals/n_omit   D n_halluc + fabrication coverage   E E2.swaps   F E2.market + E2.capstock
  H C1.match + C1.structure   I C1.exceptions   J C1.n_stale_blind   K type-confusion crashes   L absence credit / no-reading stacks
  M stacked corruption + extras   Z systematic maps (dead fields, crash paths)
"""
import sys
import copy
import json

sys.path.insert(0, r"C:\Projects\finance-llm-evals")
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from harness import run_case, suites                                   # noqa: E402
from harness.rubric import load_case, load_rubric, materialize, rubric_path_for   # noqa: E402
from harness.graders import grade                                       # noqa: E402
from harness.scoring import score                                       # noqa: E402
from harness.suites import nav_oversight as nv                          # noqa: E402
from harness.live_nav_oversight import build_packet                     # noqa: E402

ROOT = r"C:\Projects\finance-llm-evals"
PATHS = {"break": ROOT + r"\cases\grsl-nav-2026.case.yaml",
         "clean": ROOT + r"\cases\grsl-nav-2026-clean.case.yaml"}
CASES = {k: load_case(p) for k, p in PATHS.items()}
MY = ["E1.lines", "E1.totals", "E1.stale", "E1.cite", "E1.n_omit", "E2.swaps", "E2.market", "E2.capstock",
      "E2.n_halluc", "C1.match", "C1.exceptions", "C1.structure", "C1.n_stale_blind"]
DEL = "<deleted>"
SEP = "-" * 118


# ------------------------------------------------------------------ engine plumbing
_EVAL_CACHE = {}


def evaluate(key, answer):
    """grade `answer` exactly the way harness.run_case does, but keep the per-atom verdicts."""
    if key not in _EVAL_CACHE:
        case = CASES[key]
        rubric = load_rubric(rubric_path_for(case))
        suite = suites.for_case(case)
        atoms = materialize(rubric, case)
        gold = dict(case["gold"])
        gold["manifest"] = case.get("manifest", {})
        gold["_snapshot"] = case.get("snapshot")
        gold["_claims"] = case.get("claims")
        gold["_documents"] = case.get("documents")
        _EVAL_CACHE[key] = (case, rubric, suite, atoms, gold)
    case, rubric, suite, atoms, gold = _EVAL_CACHE[key]
    verdicts, rg = grade(atoms, copy.deepcopy(answer), copy.deepcopy(gold), rubric, suite)
    res = score(atoms, verdicts, rg, rubric, case_id=case["case_id"], refusal_cp=suite.REFUSAL_CP)
    return res, verdicts


def oracle(key):
    return nv.oracle(CASES[key])


def start_answer(key, start):
    if start == "oracle":
        return oracle(key)
    return nv.make(CASES[key], start)


def diff(a, b, path=""):
    """leaf-level diff of two JSON-able structures: {path: new_value}."""
    out = {}
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b), key=str):
            p = f"{path}.{k}" if path else str(k)
            if k not in b:
                out[p] = DEL
            elif k not in a:
                out[p] = b[k]
            else:
                out.update(diff(a[k], b[k], p))
    elif isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        for i, (x, y) in enumerate(zip(a, b)):
            out.update(diff(x, y, f"{path}[{i}]"))
    elif a != b:
        out[path] = b
    return out


def fmt_atoms(verdicts, base_verdicts):
    ch = []
    for aid, v in verdicts.items():
        b = base_verdicts[aid].met
        if abs(v.met - b) > 1e-9:
            ch.append(f"{aid} {b:.3g}->{v.met:.3g}")
    return ", ".join(ch) if ch else "(no atom changed)"


def cpvec(res):
    return " ".join(f"{k}={res.checkpoints[k]['score_gated']:.3f}" for k in ("E1", "E2", "C1"))


_BASE = {}


def base_of(key, start):
    k = (key, start)
    if k not in _BASE:
        _BASE[k] = evaluate(key, start_answer(key, start))
    return _BASE[k]


def X(eid, keys, title, fn, start="oracle", maxjson=900, show_my=False):
    """run one experiment on each case in `keys`; fn(m, key) mutates the answer in place."""
    for key in keys.split(","):
        m = start_answer(key, start)
        ref = copy.deepcopy(m)
        err = None
        try:
            fn(m, key)
        except Exception as e:                                    # the experiment itself failed to build
            err = e
        ops = diff(ref, m)
        js = json.dumps(ops, ensure_ascii=True, default=str)
        if len(js) > maxjson:
            js = js[:maxjson] + " ...[truncated]"
        print(SEP)
        print(f"[{eid}] {key} | {title}")
        if err is not None:
            print(f"   BUILD ERROR in experiment: {type(err).__name__}: {err}")
            continue
        print(f"   mutation: {js}")
        bres, bver = base_of(key, start)
        try:
            res, ver = evaluate(key, m)
        except Exception as e:
            print(f"   *** GRADER CRASH: {type(e).__name__}: {e}")
            try:
                run_case(PATHS[key], model_output=copy.deepcopy(m))
            except Exception as e2:
                print(f"   *** run_case also crashes: {type(e2).__name__}: {e2}")
            continue
        chk, _ = run_case(PATHS[key], model_output=copy.deepcopy(m))
        same = (abs(chk.case_gated - res.case_gated) < 1e-9 and chk.allpass == res.allpass
                and chk.fired_gates == res.fired_gates)
        print(f"   RESULT: gated {bres.case_gated:.4f} -> {res.case_gated:.4f} | ungated {res.case_ungated:.4f} | "
              f"allpass {bres.allpass}->{res.allpass} | gates {res.fired_gates} | flags {res.flags} | "
              f"D2(R,G)={res.e6} | cp {cpvec(res)}{'' if same else '  !!MISMATCH vs run_case'}")
        print(f"   atoms: {fmt_atoms(ver, bver)}")
        if show_my:
            print("   my atoms: " + " ".join(f"{a}={ver[a].met:.3g}" for a in MY if a in ver))


# ------------------------------------------------------------------ packet lines (what the model sees)
def L(key, *subs):
    for ln in build_packet(CASES[key]).split("\n"):
        s = ln.strip()
        if all(x in s for x in subs):
            return s
    raise KeyError((key, subs))


def jac(a, b):
    A, B = set((a or "").lower().split()), set((b or "").lower().split())
    return (len(A & B) / len(A | B)) if A and B else 0.0


def gold_verbatims(key):
    g = CASES[key]["gold"]["E1"]
    out = [("canonical", g["citation"]["verbatim"])]
    for i, c in enumerate(g.get("citation_alternates") or []):
        out.append((f"alt{i}", c["verbatim"]))
    return out


def best_jac(key, verb):
    return max((jac(verb, v), n) for n, v in gold_verbatims(key))


def set_cite(m, verb, doc="package", loc="package line"):
    m["E1"]["citation"] = {"document": doc, "locator": loc, "verbatim": verb}


def row(m, sect, lk, rid, idk="line_id"):
    for r in m[sect][lk]:
        if str(r.get(idk)).upper() == rid.upper():
            return r
    raise KeyError(rid)


def E1_wrong_reading(m, stale=("SWAP-A",)):
    """an E1 reading that is wrong everywhere (ids present, so no omission penalty)."""
    e1 = m["E1"]
    e1["admin_lines"] = [{"line_id": r["line_id"], "market_value": 1.0, "price_date": "2026-06-23"} for r in e1["admin_lines"]]
    e1["admin_liabilities"] = [{"line_id": r["line_id"], "amount": 1.0} for r in e1["admin_liabilities"]]
    for k in ("admin_total_assets", "admin_total_liabilities", "admin_total_net_assets", "admin_shares_outstanding",
              "admin_nav_per_share"):
        e1[k] = 1.0
    e1["stale_flags"] = list(stale)


# ================================================================== GROUP A: E1.cite
def group_A():
    print("\n" + "=" * 118 + "\nGROUP A - E1.cite (citation_alternates, token-Jaccard >= 0.5 against GOLD verbatims only)\n" + "=" * 118)
    X("A1", "break,clean", "E1 reading WRONG everywhere (values 1.0, wrong stale flag), citation = the totals block verbatim",
      lambda m, k: (E1_wrong_reading(m), set_cite(m, L(k, "total_assets=", "nav_per_share="), loc="totals block")))
    X("A1c", "break,clean", "E1 EMPTY except the citation (totals block): no lines, no totals, no flags",
      lambda m, k: m.__setitem__("E1", {"citation": {"document": "package", "locator": "totals block", "verbatim": L(k, "total_assets=", "nav_per_share=")}}))
    X("A2", "break", "E1 stale-blind reading (stale_flags=[]) but citation = the canonical stale exceptions-report line",
      lambda m, k: (m["E1"].__setitem__("stale_flags", []), set_cite(m, L(k, "flag=STALE_PRICE"), loc="pricing exceptions report")))
    X("A2b", "break", "E1 reading wrong, citation = the SWAP-B stale ledger line (alternate)",
      lambda m, k: (E1_wrong_reading(m), set_cite(m, L(k, "line_id=SWAP-B", "type=total_return_swap"), loc="ledger")))

    # A3: verbatim quotes of OTHER package lines (does an unrelated line earn the credit?)
    print(SEP + "\n[A3] verbatim quote of an unrelated package line (exact text from the packet the model sees)")
    for key in ("break", "clean"):
        cands = {
            "header(fund..)": L(key, "fund=", "package_id="),
            "header(dates)": L(key, "valuation_date=", "prior_valuation_date="),
            "SWAP-A ledger line": L(key, "line_id=SWAP-A", "type=total_return_swap"),
            "EQ-SMH ledger line": L(key, "line_id=EQ-SMH"),
            "TB-0925 ledger line": L(key, "line_id=TB-0925", "type=treasury_bill"),
            "FIN-B liability line": L(key, "line_id=FIN-B"),
            "totals line 2 (prior nav..)": L(key, "prior_nav_per_share="),
            "capital stock line": L(key, "creations_shares="),
            "SWAP-A counterparty statement": L(key, "counterparty=Northgate"),
            "SWAP-B counterparty statement": L(key, "counterparty=Westbrook", "trade_ref="),
            "market price line": L(key, "ticker=SMH"),
            "policy thresholds line": L(key, "thresholds:"),
        }
        for name, verb in cands.items():
            m = oracle(key)
            set_cite(m, verb, loc=name)
            res, ver = evaluate(key, m)
            j, which = best_jac(key, verb)
            print(f"   {key:5} | {name:30} | E1.cite={ver['E1.cite'].met:g} | best Jaccard {j:.3f} vs {which}")
    # A3b: the clean case: SWAP-A ledger line vs the gold SWAP-B ledger line
    # A4: fabricated quotes (NOT in the package at all) that share >= half of the gold tokens
    fab = {
        "wrong line id + counterparty (SWAP-A / Northgate)":
            "line_id=SWAP-A  flag=STALE_PRICE  note=Northgate valuation file not received by the 17:30 ET pricing cut-off; prior business day (2026-06-22) value carried forward",
        "non-existent line SWAP-C / Eastbrook":
            "line_id=SWAP-C  flag=STALE_PRICE  note=Eastbrook valuation file not received by the 17:30 ET pricing cut-off; prior business day (2026-06-19) value carried forward",
        "gold line, different cause and date":
            "line_id=SWAP-B  flag=STALE_PRICE  note=Westbrook valuation file rejected by the 17:30 ET pricing cut-off; prior business day (2026-06-19) value carried forward",
        "paraphrase (not a quote)":
            "SWAP-B flagged STALE_PRICE: Westbrook valuation file not received by the 17:30 ET pricing cut-off; prior business day (2026-06-22) value carried forward",
        "paraphrase 2 (lighter)":
            "The Westbrook valuation file was not received by the 17:30 ET pricing cut-off so the prior business day value was carried forward for SWAP-B",
    }
    for name, verb in fab.items():
        X("A4", "break", f"fabricated / paraphrased citation: {name}", lambda m, k, v=verb: set_cite(m, v, loc="pricing exceptions report"))
    # the same on the clean case, where the package has NO stale flag: the break-case exceptions line quoted
    X("A4c", "clean", "clean package: cites the BREAK case's exceptions line (a flag that does not exist in this package)",
      lambda m, k: set_cite(m, "line_id=SWAP-B  flag=STALE_PRICE  note=Westbrook valuation file not received by the 17:30 ET pricing cut-off; prior business day (2026-06-22) value carried forward"))
    # A5: citing the BREAK case's totals on the clean package (a different package's numbers)
    X("A5", "clean", "clean package: cites the BREAK case's totals block",
      lambda m, k: set_cite(m, "total_assets=206010600.0  total_liabilities=1045913.81  total_net_assets=204964686.19  shares_outstanding=4000000  nav_per_share=51.2412"))
    X("A5b", "break", "break package: cites the RECOMPUTED totals (not in the package)",
      lambda m, k: set_cite(m, "total_assets=209010600.0  total_liabilities=1045913.81  total_net_assets=207964686.19  shares_outstanding=4000000  nav_per_share=51.9912"))

    # A6: document-name variants (gold names document 'package')
    for doc in ("Package", "NAV package", "package.yaml", "administrator package", None, ""):
        def f(m, k, d=doc):
            set_cite(m, L(k, "total_assets=", "nav_per_share="))
            if d is None:
                m["E1"]["citation"].pop("document")
            else:
                m["E1"]["citation"]["document"] = d
        X("A6", "break", f"citation.document = {doc!r} (correct totals verbatim)", f)

    # A7: shorter but entailing verbatims (real model outputs did exactly this)
    for name, key, verb in [
        ("stale line, two tokens (what qwen2.5-32b actually returned)", "break", "line_id=SWAP-B  flag=STALE_PRICE"),
        ("stale ledger evidence: price_date + price_source only", "break", "price_date=2026-06-22  price_source=prior business day value carried forward"),
        ("stale line, first 10 of 20 tokens", "break", " ".join(L("break", "flag=STALE_PRICE").split()[:10])),
        ("stale line, first 9 of 20 tokens", "break", " ".join(L("break", "flag=STALE_PRICE").split()[:9])),
        ("totals block, 3 of 5 tokens", "break", "total_net_assets=204964686.19  shares_outstanding=4000000  nav_per_share=51.2412"),
        ("totals block, 2 of 5 tokens", "break", "shares_outstanding=4000000  nav_per_share=51.2412"),
        ("totals block, only nav_per_share (what qwen3.8-27b returned on clean)", "clean", "nav_per_share=51.9912"),
        ("clean: the pricing exceptions report showing (none)", "clean", "PRICING EXCEPTIONS REPORT: (none)"),
        ("clean: '(none)' only", "clean", "(none)"),
        ("clean: SWAP-B ledger line shortened to its price fields", "clean", "price_date=2026-06-23  price_source=counterparty valuation statement 2026-06-23  market_value=6000000.0"),
    ]:
        X("A7", key, f"shorter verbatim: {name}", lambda m, k, v=verb: set_cite(m, v))
    # whitespace variants of a correct citation
    X("A7b", "break", "correct exceptions line with SINGLE spaces instead of the packet's double spaces",
      lambda m, k: set_cite(m, " ".join(L(k, "flag=STALE_PRICE").split())))
    X("A7c", "break", "correct exceptions line wrapped in quotes and with a trailing period",
      lambda m, k: set_cite(m, '"' + L(k, "flag=STALE_PRICE") + '".'))
    X("A7d", "break", "citation given as a LIST of citation objects (one correct)",
      lambda m, k: m["E1"].__setitem__("citation", [{"document": "package", "locator": "x", "verbatim": L(k, "flag=STALE_PRICE")}]))
    X("A7e", "break", "citation given as a bare string (the exceptions line)",
      lambda m, k: m["E1"].__setitem__("citation", L(k, "flag=STALE_PRICE")))
    # A9: superset attack: gold canonical line + N extra distinct tokens
    ex = L("break", "flag=STALE_PRICE")
    n_ok = 0
    for n in range(0, 40):
        verb = ex + " " + " ".join(f"junk{i}" for i in range(n))
        if jac(verb, ex) >= 0.5:
            n_ok = n
    print(SEP + f"\n[A9] superset: canonical exceptions line + N junk tokens: Jaccard>=0.5 holds up to N={n_ok} "
          f"(line has {len(set(ex.lower().split()))} distinct tokens)")
    X("A9", "break", f"citation = canonical line + {n_ok} junk tokens (padding)", lambda m, k: set_cite(m, ex + " " + " ".join(f"junk{i}" for i in range(n_ok))))


# ================================================================== GROUP B: E1.stale forms
def group_B():
    print("\n" + "=" * 118 + "\nGROUP B - E1.stale forms (set equality over str(x).upper())\n" + "=" * 118)
    forms_break = [
        ("string 'SWAP-B'", "SWAP-B"),
        ("string 'SWAP-B, ' ", "SWAP-B, "),
        ("list of dicts [{line_id: SWAP-B, flag: STALE_PRICE}]", [{"line_id": "SWAP-B", "flag": "STALE_PRICE"}]),
        ("list of dicts keyed 'id'", [{"id": "SWAP-B"}]),
        ("lower-case 'swap-b'", ["swap-b"]),
        ("with a leading space ' SWAP-B'", [" SWAP-B"]),
        ("'SWAP B'", ["SWAP B"]),
        ("en dash 'SWAP\u2013B'", ["SWAP\u2013B"]),
        ("'SWAP-B (Westbrook)'", ["SWAP-B (Westbrook)"]),
        ("extra flag ['SWAP-B','SWAP-A']", ["SWAP-B", "SWAP-A"]),
        ("extra flag on a real line ['SWAP-B','CASH']", ["SWAP-B", "CASH"]),
        ("dict {'SWAP-B': true}", {"SWAP-B": True}),
        ("duplicates ['SWAP-B','SWAP-B']", ["SWAP-B", "SWAP-B"]),
        ("flag name instead of line id ['STALE_PRICE']", ["STALE_PRICE"]),
        ("missing (None)", None),
    ]
    for name, val in forms_break:
        X("B", "break", f"stale_flags = {name}", lambda m, k, v=val: m["E1"].__setitem__("stale_flags", v))
    X("B2", "break,clean", "stale_flags as a per-line BOOLEAN MAP {line_id: true/false} (the stale line true, every other line false)",
      lambda m, k: m["E1"].__setitem__("stale_flags", {r["line_id"]: (r["line_id"] == "SWAP-B" and k == "break") for r in m["E1"]["admin_lines"]}))
    forms_clean = [
        ("omitted key", DEL), ("None", None), ("[]", []), ("'' (empty string)", ""), ("'none'", "none"),
        ("['none']", ["none"]), ("['NONE']", ["NONE"]), ("[None]", [None]), ("['']", [""]), ("'N/A'", "N/A"),
        ("'[]' (string)", "[]"), ("{} (dict)", {}), ("False", False),
        ("invented flag ['SWAP-B']", ["SWAP-B"]),
    ]
    for name, val in forms_clean:
        def f(m, k, v=val):
            if v == DEL:
                m["E1"].pop("stale_flags", None)
            else:
                m["E1"]["stale_flags"] = v
        X("B", "clean", f"stale_flags = {name}", f)


# ================================================================== GROUP C: E1.lines / totals / omit
def group_C():
    print("\n" + "=" * 118 + "\nGROUP C - E1.lines, E1.totals, E1.n_omit (format and id robustness)\n" + "=" * 118)
    X("C1", "break,clean", "admin_lines as a dict keyed by line id (natural JSON), liabilities as a dict too",
      lambda m, k: (m["E1"].__setitem__("admin_lines", {r["line_id"]: r["market_value"] for r in m["E1"]["admin_lines"]}),
                    m["E1"].__setitem__("admin_liabilities", {r["line_id"]: r["amount"] for r in m["E1"]["admin_liabilities"]})))
    X("C2a", "break", "liabilities as NEGATIVE numbers (credit balances)",
      lambda m, k: [r.__setitem__("amount", -r["amount"]) for r in m["E1"]["admin_liabilities"]])
    X("C2b", "break", "liabilities as accounting-format strings '(490,000.00)'",
      lambda m, k: [r.__setitem__("amount", "({:,.2f})".format(r["amount"])) for r in m["E1"]["admin_liabilities"]])
    X("C3", "break", "values as currency strings '$3,000,000.00' and '1.0E8'",
      lambda m, k: [r.__setitem__("market_value", "${:,.2f}".format(r["market_value"])) for r in m["E1"]["admin_lines"][:3]])
    X("C3b", "break", "values with a unit suffix '100000000.00 USD' on one line",
      lambda m, k: m["E1"]["admin_lines"][0].__setitem__("market_value", "100000000.00 USD"))
    X("C3c", "break", "value in millions with suffix '100.0M' on one line",
      lambda m, k: m["E1"]["admin_lines"][0].__setitem__("market_value", "100.0M"))
    for name, newid in [("en dash 'SWAP\u2013A'", "SWAP\u2013A"), ("leading space ' SWAP-A'", " SWAP-A"), ("trailing space 'SWAP-A '", "SWAP-A "),
                        ("'SWAP A'", "SWAP A"), ("'swap-a' (control)", "swap-a"), ("'SWAP-A (Northgate)'", "SWAP-A (Northgate)"),
                        ("'TB0925' for TB-0925", "TB0925")]:
        tgt = "TB-0925" if "TB0925" in newid else "SWAP-A"
        X("C4", "break,clean", f"E1.admin_lines id {name}", lambda m, k, n=newid, t=tgt: row(m, "E1", "admin_lines", t).__setitem__("line_id", n))
    X("C5", "break", "price_date garbage on every ledger line (the field that carries the staleness evidence)",
      lambda m, k: [r.__setitem__("price_date", "1999-01-01") for r in m["E1"]["admin_lines"]])
    X("C5b", "break", "SWAP-B price_date read as the CURRENT date 2026-06-23 (wrong) while still flagging stale",
      lambda m, k: row(m, "E1", "admin_lines", "SWAP-B").__setitem__("price_date", "2026-06-23"))
    X("C6a", "break", "duplicate ids: SWAP-A listed twice [right, wrong]",
      lambda m, k: m["E1"]["admin_lines"].append({"line_id": "SWAP-A", "market_value": 1.0, "price_date": "2026-06-23"}))
    X("C6b", "break", "duplicate ids: SWAP-A listed twice [wrong, right]",
      lambda m, k: m["E1"]["admin_lines"].insert(0, {"line_id": "SWAP-A", "market_value": 1.0, "price_date": "2026-06-23"}))
    X("C6c", "break", "SWAP-B listed twice: as reported 3,000,000 then 'corrected' 6,000,000 (a natural way to show the break)",
      lambda m, k: m["E1"]["admin_lines"].append({"line_id": "SWAP-B", "market_value": 6000000.0, "price_date": "2026-06-23"}))
    X("C7", "break", "admin_total_assets / admin_total_liabilities garbage (fields the SCHEMA asks for)",
      lambda m, k: m["E1"].update({"admin_total_assets": 5.0, "admin_total_liabilities": 7.0}))
    X("C8", "break,clean", "all line values null but every line id present (no reading done)",
      lambda m, k: (m["E1"].__setitem__("admin_lines", [{"line_id": r["line_id"], "market_value": None, "price_date": None} for r in m["E1"]["admin_lines"]]),
                    m["E1"].__setitem__("admin_liabilities", [{"line_id": r["line_id"], "amount": None} for r in m["E1"]["admin_liabilities"]])))
    X("C9", "break", "one liability line (FEE) dropped", lambda m, k: m["E1"]["admin_liabilities"].pop())
    X("C9b", "break", "liabilities placed inside admin_lines (as market_value) instead of admin_liabilities",
      lambda m, k: (m["E1"]["admin_lines"].extend([{"line_id": r["line_id"], "market_value": r["amount"]} for r in m["E1"]["admin_liabilities"]]),
                    m["E1"].__setitem__("admin_liabilities", [])))


# ================================================================== GROUP D: fabrication / omission detectors
def group_D():
    print("\n" + "=" * 118 + "\nGROUP D - E2.n_halluc / GATE.FABRICATION coverage and E1.n_omit\n" + "=" * 118)
    X("D1", "break,clean", "a TOTAL subtotal row appended to E1.admin_lines (a row that exists as the totals block, not a line)",
      lambda m, k: m["E1"]["admin_lines"].append({"line_id": "TOTAL", "market_value": m["E1"]["admin_total_assets"], "price_date": "2026-06-23"}))
    X("D2", "break,clean", "an invented counterparty statement SWAP-C appended to E2.swap_statements",
      lambda m, k: m["E2"]["swap_statements"].append({"id": "SWAP-C", "counterparty": "Eastbrook Bank", "notional": 147000000.0, "reset_level": 4900.0,
                                                    "index_level": 5100.0, "unrealized_value": 6000000.0, "financing_accrued_payable": 500208.33,
                                                    "valuation_date": "2026-06-23"}))
    X("D3", "break,clean", "an INVENTED position SWAP-C (10,000,000, status match) added to the C1 recon ledger only",
      lambda m, k: m["C1"]["recon"].append({"line_id": "SWAP-C", "admin_value": 10000000.0, "independent_value": 10000000.0, "status": "match"}))
    X("D3b", "break,clean", "5 invented recon lines (SWAP-C..G) with fantasy values and statuses",
      lambda m, k: [m["C1"]["recon"].append({"line_id": f"SWAP-{c}", "admin_value": 1e9, "independent_value": 5.0, "status": "wrong"}) for c in "CDEFG"])
    X("D4", "break,clean", "the fund's own exchange close invented INSIDE E2.prices: GRSL = 51.30 (the withheld input)",
      lambda m, k: m["E2"]["prices"].__setitem__("GRSL", 51.30))
    X("D4b", "break,clean", "E2.prices + E2.index carry a made-up premium and close (grsl_close, premium_pct)",
      lambda m, k: (m["E2"]["prices"].update({"GRSL": 51.30, "GRSL_PREMIUM_PCT": 0.0}), m["E2"]["index"].update({"grsl_close": 51.30})))
    X("D4c", "break", "the same invented close in D2.probe.value (the ONLY place the fabrication detector looks), for comparison",
      lambda m, k: m["D2"]["probe"].update({"value": 51.30, "label": "NOT_DISCLOSED"}))
    X("D4d", "break", "invented close in E2.prices AND a correct NOT_DISCLOSED refusal in D2 (contradiction, not detected)",
      lambda m, k: m["E2"]["prices"].__setitem__("GRSL", 51.30))
    X("D5", "break,clean", "an invented liability line (DIV-PAY) in E1.admin_liabilities",
      lambda m, k: m["E1"]["admin_liabilities"].append({"line_id": "DIV-PAY", "amount": 1000.0}))
    X("D6", "break,clean", "an invented position with line_id null in E1.admin_lines (no id to compare)",
      lambda m, k: m["E1"]["admin_lines"].append({"line_id": None, "market_value": 5e8, "price_date": "2026-06-23"}))
    X("D6b", "break,clean", "an invented position in E1.admin_lines under key 'id' instead of 'line_id'",
      lambda m, k: m["E1"]["admin_lines"].append({"id": "SWAP-Z", "market_value": 5e8}))
    X("D7", "break,clean", "invented stale flag for a line that does not exist (SWAP-C) - E1.stale_flags",
      lambda m, k: m["E1"].__setitem__("stale_flags", ["SWAP-B", "SWAP-C"] if k == "break" else ["SWAP-C"]))
    X("D8", "break,clean", "counterparty names fabricated on both statements (real-world bank names), numbers right",
      lambda m, k: [s.__setitem__("counterparty", "Goldman Sachs International") for s in m["E2"]["swap_statements"]])
    X("D9", "break", "E1.n_omit: 7 of 8 line ids dropped from E1 (everything but EQ-SMH), values for the rest right",
      lambda m, k: (m["E1"].__setitem__("admin_lines", m["E1"]["admin_lines"][:1]), m["E1"].__setitem__("admin_liabilities", [])))
    X("D9b", "break", "E1.n_omit evaded: SWAP-B present as a bare id with null value (not omitted, just empty)",
      lambda m, k: row(m, "E1", "admin_lines", "SWAP-B").update({"market_value": None}))
    X("D9c", "break", "E1.n_omit: SWAP-B (the stale line) dropped entirely from E1.admin_lines and from the flags",
      lambda m, k: (m["E1"].__setitem__("admin_lines", [r for r in m["E1"]["admin_lines"] if r["line_id"] != "SWAP-B"]),
                    m["E1"].__setitem__("stale_flags", [])))


# ================================================================== GROUP E: E2.swaps
def group_E():
    print("\n" + "=" * 118 + "\nGROUP E - E2.swaps\n" + "=" * 118)
    fields = ["notional", "reset_level", "index_level", "unrealized_value", "financing_accrued_payable"]
    for f in fields:
        X("E1", "break", f"field '{f}' omitted from BOTH statements",
          lambda m, k, f=f: [s.pop(f, None) for s in m["E2"]["swap_statements"]])
    X("E1b", "break", "field 'financing_accrued_payable' omitted from ONE statement (SWAP-B)",
      lambda m, k: m["E2"]["swap_statements"][1].pop("financing_accrued_payable"))
    X("E2", "break,clean", "counterparty names SWAPPED and valuation_date set to the PRIOR day on both statements (numbers right)",
      lambda m, k: [s.update({"counterparty": ("Westbrook Capital Markets" if s["id"] == "SWAP-A" else "Northgate Securities LLC"),
                              "valuation_date": "2026-06-22"}) for s in m["E2"]["swap_statements"]])
    X("E2b", "break", "SWAP-B statement valuation_date = 2026-06-22 (the STALE date) with the right current numbers",
      lambda m, k: m["E2"]["swap_statements"][1].__setitem__("valuation_date", "2026-06-22"))
    X("E2c", "break,clean", "counterparty and valuation_date both null / absent on both statements",
      lambda m, k: [(s.pop("counterparty", None), s.pop("valuation_date", None)) for s in m["E2"]["swap_statements"]])
    X("E3", "break", "statement SWAP-B copied from the administrator's STALE ledger line (3,000,000 / index 5,000)",
      lambda m, k: m["E2"]["swap_statements"][1].update({"index_level": 5000.0, "unrealized_value": 3000000.0}))
    X("E3b", "break", "statement SWAP-B = the SWAP-A statement copied (financing differs)",
      lambda m, k: m["E2"]["swap_statements"][1].update({"financing_accrued_payable": 490000.0}))
    X("E4", "break", "statement ids lower-case 'swap-a'/'swap-b'", lambda m, k: [s.__setitem__("id", s["id"].lower()) for s in m["E2"]["swap_statements"]])
    X("E4b", "break", "statements keyed 'line_id' instead of 'id'",
      lambda m, k: [s.__setitem__("line_id", s.pop("id")) for s in m["E2"]["swap_statements"]])
    X("E4c", "break", "statement ids 'SWAP A' / 'SWAP B'", lambda m, k: [s.__setitem__("id", s["id"].replace("-", " ")) for s in m["E2"]["swap_statements"]])
    X("E5", "break", "values as strings with currency signs and separators",
      lambda m, k: [s.update({"notional": "$147,000,000.00", "unrealized_value": "$6,000,000.00"}) for s in m["E2"]["swap_statements"]])
    X("E6", "break", "swap_statements given as a dict keyed by id", lambda m, k: m["E2"].__setitem__("swap_statements", {s["id"]: s for s in m["E2"]["swap_statements"]}))
    X("E7", "break", "financing accrued as an unrounded figure (500208.3333) and notional in millions on SWAP-A (147.0)",
      lambda m, k: (m["E2"]["swap_statements"][1].__setitem__("financing_accrued_payable", 500208.3333),
                    m["E2"]["swap_statements"][0].__setitem__("notional", 147.0)))


# ================================================================== GROUP F: E2.market
def group_F():
    print("\n" + "=" * 118 + "\nGROUP F - E2.market (prices, index) and E2.capstock\n" + "=" * 118)
    X("F1", "break", "prices keyed by LOWER-case tickers {'smh','tb-0925'}",
      lambda m, k: m["E2"].__setitem__("prices", {"smh": 250.0, "tb-0925": 99.8}))
    X("F2", "break", "prices keyed by NAME {'VanEck Semiconductor ETF': 250.0, 'U.S. Treasury Bill due 2026-09-24': 99.8}",
      lambda m, k: m["E2"].__setitem__("prices", {"VanEck Semiconductor ETF": 250.0, "U.S. Treasury Bill due 2026-09-24": 99.8}))
    X("F2b", "break", "prices keyed 'TB0925' (no hyphen) and ' SMH' (leading space)",
      lambda m, k: m["E2"].__setitem__("prices", {" SMH": 250.0, "TB0925": 99.8}))
    X("F3", "break", "prices as a list of {ticker, close} rows",
      lambda m, k: m["E2"].__setitem__("prices", [{"ticker": "SMH", "close": 250.0}, {"ticker": "TB-0925", "close": 99.8}]))
    X("F4", "break", "index.return_pct as a FRACTION 0.02 instead of 2.0",
      lambda m, k: m["E2"]["index"].__setitem__("return_pct", 0.02))
    X("F4b", "break", "index.return_pct as '2.00%' string", lambda m, k: m["E2"]["index"].__setitem__("return_pct", "2.00%"))
    X("F4c", "break", "index.return_pct 1.9999 (rounding of 5100/5000-1) and 2.0049",
      lambda m, k: m["E2"]["index"].__setitem__("return_pct", 2.0049))
    X("F4d", "break", "index.return_pct omitted (null) with close and prior_close right",
      lambda m, k: m["E2"]["index"].__setitem__("return_pct", None))
    X("F5", "break", "index close as '5,100' string, prior_close '5000'",
      lambda m, k: m["E2"]["index"].update({"close": "5,100", "prior_close": "5000"}))
    X("F6", "break", "T-bill price 99.80 given as a percent string '99.80%'", lambda m, k: m["E2"]["prices"].__setitem__("TB-0925", "99.80%"))
    X("F7", "break", "T-bill price as 0.998 (fraction of par)", lambda m, k: m["E2"]["prices"].__setitem__("TB-0925", 0.998))
    X("F8", "break", "SMH price off by 0.004 (inside the cent band) and 0.006 (outside)",
      lambda m, k: m["E2"]["prices"].__setitem__("SMH", 250.006))
    X("F9", "break", "prices as nested objects mirroring the packet's market lines {SMH: {close, prior_close}, TB-0925: {price, prior_price}}",
      lambda m, k: m["E2"].__setitem__("prices", {"SMH": {"close": 250.0, "prior_close": 245.0}, "TB-0925": {"price": 99.8, "prior_price": 99.79}}))
    # E2.capstock
    X("G1", "break", "capital stock shares as strings with commas ('4,000,000') and '0'",
      lambda m, k: m["E2"]["capital_stock"].update({"shares_outstanding": "4,000,000", "creations_shares": "0", "redemptions_shares": "0"}))
    X("G2", "break", "capital stock creations/redemptions null (a model reading 'none')",
      lambda m, k: m["E2"]["capital_stock"].update({"creations_shares": None, "redemptions_shares": None}))
    X("G2b", "break", "capital stock creations 'none' / redemptions 'nil'",
      lambda m, k: m["E2"]["capital_stock"].update({"creations_shares": "none", "redemptions_shares": "nil"}))
    X("G3", "break", "capital stock shares_outstanding '4.0M'", lambda m, k: m["E2"]["capital_stock"].__setitem__("shares_outstanding", "4.0M"))
    X("G4", "break", "capital stock omitted entirely", lambda m, k: m["E2"].pop("capital_stock"))


# ================================================================== GROUP H: C1.match / structure
def recon_row(m, rid):
    return row(m, "C1", "recon", rid)


def group_H():
    print("\n" + "=" * 118 + "\nGROUP H - C1.match (status map), C1.structure\n" + "=" * 118)
    X("H1a", "break,clean", "RIGHT statuses, admin_value and independent_value both NULL on every row",
      lambda m, k: [r.update({"admin_value": None, "independent_value": None}) for r in m["C1"]["recon"]], show_my=True)
    X("H1b", "break,clean", "RIGHT statuses, values nonsense (admin 1.0, independent 999999.0) on every row",
      lambda m, k: [r.update({"admin_value": 1.0, "independent_value": 999999.0}) for r in m["C1"]["recon"]], show_my=True)
    X("H1c", "break", "SWAP-B row: status stale but admin_value == independent_value == 3,000,000 (no independent revaluation done)",
      lambda m, k: recon_row(m, "SWAP-B").update({"independent_value": 3000000.0}))
    X("H1d", "break", "every row: values are strings of words ('see statement')",
      lambda m, k: [r.update({"admin_value": "see statement", "independent_value": "n/a"}) for r in m["C1"]["recon"]])
    for syn in ("STALE_PRICE", "STALE PRICE", "stale_price", "Stale (prior-day mark carried)", "stale-priced", "stale.", "STALE", "Stale ",
                "mismatch", "exception", "wrong", "break", "error", "missing", "out of date", "stale/wrong", "carried"):
        X("H2", "break", f"SWAP-B status = {syn!r} (the right line, flagged as an issue)",
          lambda m, k, s=syn: recon_row(m, "SWAP-B").__setitem__("status", s))
    for syn in ("ok", "OK", "agree", "agrees", "ties", "tie", "tied", "matched", "matches", "reconciled", "confirmed", "agrees to statement",
                "Match", "MATCH", "match.", "true", "yes", "\u2713", "in line", "no exception"):
        X("H3", "clean", f"ALL 8 statuses = {syn!r} (every line ties)",
          lambda m, k, s=syn: [r.__setitem__("status", s) for r in m["C1"]["recon"]])
    X("H3b", "break", "7 non-stale statuses 'ok', SWAP-B 'stale'",
      lambda m, k: [r.__setitem__("status", "ok") for r in m["C1"]["recon"] if r["line_id"] != "SWAP-B"])
    X("H4a", "break,clean", "recon OMITS the three liability rows (FIN-A, FIN-B, FEE)",
      lambda m, k: m["C1"].__setitem__("recon", [r for r in m["C1"]["recon"] if r["line_id"] not in ("FIN-A", "FIN-B", "FEE")]))
    X("H4b", "break,clean", "recon lists the liability rows FIRST (order only)",
      lambda m, k: m["C1"].__setitem__("recon", [r for r in m["C1"]["recon"] if r["line_id"].startswith(("FIN", "FEE"))]
                                                  + [r for r in m["C1"]["recon"] if not r["line_id"].startswith(("FIN", "FEE"))]))
    X("H4c", "break", "recon keeps ONLY two rows (SWAP-B stale + EQ-SMH match)",
      lambda m, k: m["C1"].__setitem__("recon", [r for r in m["C1"]["recon"] if r["line_id"] in ("SWAP-B", "EQ-SMH")]))
    X("H4d", "break", "recon keeps ONLY the stale row", lambda m, k: m["C1"].__setitem__("recon", [r for r in m["C1"]["recon"] if r["line_id"] == "SWAP-B"]))
    X("H5a", "break", "recon as a dict keyed by line id {line_id: status}",
      lambda m, k: m["C1"].__setitem__("recon", {r["line_id"]: r["status"] for r in m["C1"]["recon"]}))
    X("H5b", "break", "recon as a dict keyed by line id of row dicts",
      lambda m, k: m["C1"].__setitem__("recon", {r["line_id"]: {kk: vv for kk, vv in r.items() if kk != "line_id"} for r in m["C1"]["recon"]}))
    X("H6a", "break", "SWAP-B appears twice: [stale, match] (match LAST)",
      lambda m, k: m["C1"]["recon"].append({"line_id": "SWAP-B", "admin_value": 3000000.0, "independent_value": 3000000.0, "status": "match"}))
    X("H6b", "break", "SWAP-B appears twice: [match, stale] (stale LAST) - a hedge, both asserted",
      lambda m, k: m["C1"]["recon"].insert(0, {"line_id": "SWAP-B", "admin_value": 3000000.0, "independent_value": 3000000.0, "status": "match"}))
    X("H6c", "break", "EVERY line appears twice [match, stale] (hedge on all lines, stale last)",
      lambda m, k: m["C1"].__setitem__("recon", [dict(r, status="match") for r in m["C1"]["recon"]] + [dict(r, status="stale") for r in m["C1"]["recon"]]))
    X("H6d", "break", "EVERY line appears twice [stale, match] (hedge on all lines, match last)",
      lambda m, k: m["C1"].__setitem__("recon", [dict(r, status="stale") for r in m["C1"]["recon"]] + [dict(r, status="match") for r in m["C1"]["recon"]]))
    X("H7", "break,clean", "status given as a one-element list ['match']/['stale']",
      lambda m, k: [r.__setitem__("status", [r["status"]]) for r in m["C1"]["recon"]])
    X("H8", "break", "line ids 'SWAP B' / 'Swap-B ' / 'eq-smh' in recon",
      lambda m, k: (recon_row(m, "SWAP-B").__setitem__("line_id", "SWAP B"), recon_row(m, "EQ-SMH").__setitem__("line_id", "eq-smh")))
    X("H9a", "break,clean", "C1.structure: recon = two placeholder STRINGS ['a','b']", lambda m, k: m["C1"].__setitem__("recon", ["a", "b"]))
    X("H9b", "break,clean", "C1.structure: recon = two EMPTY dicts [{}, {}]", lambda m, k: m["C1"].__setitem__("recon", [{}, {}]))
    X("H9c", "break,clean", "C1.structure: recon = [None, None]", lambda m, k: m["C1"].__setitem__("recon", [None, None]))
    X("H9d", "break,clean", "C1.structure: recon = 2 rows of statuses only (no values, no ids)",
      lambda m, k: m["C1"].__setitem__("recon", [{"status": "match"}, {"status": "stale"}]))
    X("H10", "break", "all 8 statuses 'match' with correct values (the stale-blind ledger)",
      lambda m, k: [r.__setitem__("status", "match") for r in m["C1"]["recon"]])


# ================================================================== GROUP I: C1.exceptions
def exc(line, typ, detail):
    return {"line_id": line, "type": typ, "detail": detail}


def group_I():
    print("\n" + "=" * 118 + "\nGROUP I - C1.exceptions (keyword substring test on type + detail)\n" + "=" * 118)
    rows = [
        ("type 'pricing', detail states the 3.0M vs 6.0M gap without a stale word", exc("SWAP-B", "pricing",
         "ledger carries 3,000,000.00 but the Westbrook statement values it at 6,000,000.00; NAV understated by 3,000,000")),
        ("type 'valuation difference'", exc("SWAP-B", "valuation difference", "difference of 3,000,000 against the counterparty statement")),
        ("type 'valuation break'", exc("SWAP-B", "valuation break", "SWAP-B value in the ledger does not agree to the Westbrook statement dated 2026-06-23")),
        ("'yesterday's mark' phrasing", exc("SWAP-B", "mark error", "SWAP-B is carried at yesterday's mark of 3,000,000 (index 5,000); the statement shows 5,100")),
        ("'last business day' phrasing", exc("SWAP-B", "mark error", "last business day's value used instead of the 2026-06-23 statement")),
        ("'T-1 mark'", exc("SWAP-B", "T-1 mark", "SWAP-B marked at T-1 index level 5,000 instead of 5,100")),
        ("'out of date'", exc("SWAP-B", "pricing", "the mark is out of date versus the counterparty valuation of 2026-06-23")),
        ("'not refreshed'", exc("SWAP-B", "pricing", "the mark was not refreshed after the Westbrook file arrived")),
        ("'expired mark'", exc("SWAP-B", "expired mark", "expired mark on SWAP-B")),
        ("nonsense: type 'flag' (substring 'lag')", exc("SWAP-B", "flag", "see above")),
        ("nonsense: type 'High priority' (substring 'prior')", exc("SWAP-B", "High priority", "check")),
        ("nonsense: detail 'flagged for review' only", exc("SWAP-B", "", "flagged for review")),
        ("nonsense: type 'price date' only", exc("SWAP-B", "price date", "")),
        ("NEGATION: SWAP-B is NOT stale", exc("SWAP-B", "none", "SWAP-B is not stale; its price is current and no prior-day mark was carried; no cut-off issue")),
        ("wrong cause: 'previous trade' text", exc("SWAP-B", "booking", "previous trade ticket mis-booked")),
        ("right row but line_id lower-case", exc("swap-b", "stale_price", "carried forward")),
        ("right row, line_id missing, SWAP-B only in detail", exc(None, "stale_price", "SWAP-B carried forward")),
        ("right row, line_id 'SWAP B'", exc("SWAP B", "stale_price", "carried forward")),
        ("right row but type/detail numbers fabricated (amount 999)", exc("SWAP-B", "stale_price", "understated by $999 (made-up amount)")),
    ]
    for name, r in rows:
        X("I1", "break", f"exceptions = [{name}]", lambda m, k, r=r: m["C1"].__setitem__("exceptions", [r]))
    X("I2", "break", "right SWAP-B row PLUS a second exception row on FIN-B (accrual check)",
      lambda m, k: m["C1"]["exceptions"].append(exc("FIN-B", "accrual", "financing accrual should be re-checked")))
    X("I2b", "break", "right SWAP-B row PLUS a TOTALS row (what claude-sonnet-4-6 did on the clean case)",
      lambda m, k: m["C1"]["exceptions"].append(exc("TOTALS", "arithmetic_error", "total_liabilities")))
    X("I2c", "break", "right SWAP-B row PLUS two exception notes with line_id null / a bare string (id-less rows are invisible on the break case)",
      lambda m, k: m["C1"]["exceptions"].extend([exc(None, "TOTALS", "arithmetic check"), "free-text note: all other lines tie"]))
    X("I3", "break", "exceptions as a dict {'SWAP-B': 'stale price'}", lambda m, k: m["C1"].__setitem__("exceptions", {"SWAP-B": "stale price"}))
    X("I3b", "break", "exceptions as a plain string", lambda m, k: m["C1"].__setitem__("exceptions", "SWAP-B stale price"))
    X("I3c", "break", "exceptions row has the stale text but line_id key is 'id'", lambda m, k: m["C1"].__setitem__("exceptions", [{"id": "SWAP-B", "type": "stale_price", "detail": "carried"}]))
    # clean case
    clean_rows = [
        ("one row that says nothing: line_id null, type 'none'", [exc(None, "none", "no exceptions - all lines tie")]),
        ("one row, empty strings", [exc("", "", "")]),
        ("one row: type 'info', detail 'no exception'", [exc("N/A", "info", "no exception")]),
        ("empty dict {}", {}),
        ("empty list []", []),
        ("None", None),
        ("string 'none'", "none"),
        ("string 'No exceptions'", "No exceptions"),
        ("dict {'none': True}", {"none": True}),
        ("list ['none']", ["none"]),
        ("list [None]", [None]),
        ("[{}] (empty row)", [{}]),
        ("invented stale exception on SWAP-B", [exc("SWAP-B", "stale_price", "carried forward")]),
    ]
    for name, val in clean_rows:
        X("I4", "clean", f"exceptions = {name}", lambda m, k, v=val: m["C1"].__setitem__("exceptions", v))
    X("I4b", "clean", "exceptions key omitted", lambda m, k: m["C1"].pop("exceptions"))
    X("I5", "clean", "an observation row on a line that ties, type 'note' (informational, not an exception): SWAP-B 'verified current'",
      lambda m, k: m["C1"].__setitem__("exceptions", [exc("SWAP-B", "note", "verified current: price date 2026-06-23")]))


# ================================================================== GROUP J: C1.n_stale_blind
def group_J():
    print("\n" + "=" * 118 + "\nGROUP J - C1.n_stale_blind (status MATCH on the stale line, or recomputed TNA == administrator TNA within $1)\n" + "=" * 118)
    adm = _admin_tna()
    sb = "stale_blind"
    X("J0", "break", "reference: the designed stale_blind variant (start point for J2..J9)", lambda m, k: None, start=sb)
    X("J1", "break", "ORACLE with SWAP-B status 'wrong' (correct independent value 6,000,000) instead of 'stale'",
      lambda m, k: recon_row(m, "SWAP-B").__setitem__("status", "wrong"))
    X("J1b", "break", "ORACLE with SWAP-B status 'wrong' and NO exception text keywords change (exceptions untouched)",
      lambda m, k: (recon_row(m, "SWAP-B").__setitem__("status", "wrong"), m["C1"].__setitem__("exceptions", [exc("SWAP-B", "wrong mark", "mark differs from the statement")])))
    X("J2", "break", "ORACLE recon + C2.total_net_assets := the administrator's TNA (stale flagged, then adopted)",
      lambda m, k: m["C2"].__setitem__("total_net_assets", adm))
    # evasions of the status test: stale-blind but status is a synonym of match
    for syn in ("ok", "matched", "agree", "ties", "reconciled", "matches", "confirmed", "in line", "no exception", "MATCH ", "Match.", "match (per statement)"):
        def f(m, k, s=syn):
            recon_row(m, "SWAP-B")["status"] = s
        X("J3", "break", f"stale_blind variant with SWAP-B status = {syn!r} (still adopts the stale mark; TNA == admin TNA)", f, start=sb)
    # evasion of the TNA test
    for d in (0.0, 0.99, 1.0, 1.01, 2.0, -2.0, 5.0):
        X("J4", "break", f"stale_blind variant, SWAP-B status 'ok', C2.total_net_assets = admin TNA + {d}",
          lambda m, k, d=d: (recon_row(m, "SWAP-B").__setitem__("status", "ok"), m["C2"].__setitem__("total_net_assets", adm + d)), start=sb)
    X("J5", "break", "stale_blind variant, SWAP-B status 'ok', C2.total_net_assets = None (not reported)",
      lambda m, k: (recon_row(m, "SWAP-B").__setitem__("status", "ok"), m["C2"].__setitem__("total_net_assets", None)), start=sb)
    X("J5b", "break", "stale_blind variant, SWAP-B recon row OMITTED, C2.total_net_assets omitted",
      lambda m, k: (m["C1"].__setitem__("recon", [r for r in m["C1"]["recon"] if r["line_id"] != "SWAP-B"]), m["C2"].pop("total_net_assets")), start=sb)
    X("J5c", "break", "stale_blind variant, SWAP-B status 'match' (control: the designed flaw, penalty fires)", lambda m, k: None, start=sb)
    X("J6", "break", "stale_blind variant with SWAP-B 'ok', TNA = admin + 2.00, and C1.exceptions mentioning the stale line (hedged ledger)",
      lambda m, k: (recon_row(m, "SWAP-B").__setitem__("status", "ok"), m["C2"].__setitem__("total_net_assets", adm + 2.0),
                    m["C1"].__setitem__("exceptions", [exc("SWAP-B", "stale_price", "carried forward")])), start=sb)
    X("J7", "break", "stale_blind variant but TNA reported as the string '204,964,686.19' (parsed, then caught?)",
      lambda m, k: m["C2"].__setitem__("total_net_assets", "204,964,686.19"), start=sb)
    X("J8", "break", "stale_blind variant but NAV-only adoption: TNA field dropped, nav_per_share = admin 51.2412 kept",
      lambda m, k: m["C2"].pop("total_net_assets"), start=sb)
    X("J9", "break", "ORACLE but SWAP-B status 'match' with independent_value 6,000,000 (values right, status wrong)",
      lambda m, k: recon_row(m, "SWAP-B").__setitem__("status", "match"))
    X("J11", "break", "stale_blind variant keeps the literal status 'match' on SWAP-B but the row id is 'SWAP-B ' (trailing space); TNA = admin TNA + 2.00",
      lambda m, k: (recon_row(m, "SWAP-B").__setitem__("line_id", "SWAP-B "), m["C2"].__setitem__("total_net_assets", adm + 2.0)), start=sb)
    X("J10", "clean", "clean case: every recon row 'wrong' and TNA == admin TNA (penalty must stay quiet on a clean package)",
      lambda m, k: [r.__setitem__("status", "wrong") for r in m["C1"]["recon"]])


def _admin_tna():
    return float(CASES["break"]["gold"]["E1"]["admin_total_net_assets"])


# ================================================================== GROUP K: type-confusion crashes
def group_K():
    print("\n" + "=" * 118 + "\nGROUP K - malformed sub-objects: does the grader crash (cell skipped by the grid runner) or score 0?\n" + "=" * 118)
    cases = [
        ("E2.index = '5100' (string)", lambda m: m["E2"].__setitem__("index", "5100")),
        ("E2.index = [5100, 5000] (list)", lambda m: m["E2"].__setitem__("index", [5100, 5000])),
        ("E2.index = 5100 (number)", lambda m: m["E2"].__setitem__("index", 5100)),
        ("E2.capital_stock = 'none' (string)", lambda m: m["E2"].__setitem__("capital_stock", "none")),
        ("E2.capital_stock = [{'creations_shares': 0}] (list)", lambda m: m["E2"].__setitem__("capital_stock", [{"creations_shares": 0}])),
        ("E2.capital_stock = 0", lambda m: m["E2"].__setitem__("capital_stock", 0)),
        ("E2.prices = 'n/a'", lambda m: m["E2"].__setitem__("prices", "n/a")),
        ("E1.stale_flags = 1 (int)", lambda m: m["E1"].__setitem__("stale_flags", 1)),
        ("E1.stale_flags = True", lambda m: m["E1"].__setitem__("stale_flags", True)),
        ("E1.stale_flags = 0", lambda m: m["E1"].__setitem__("stale_flags", 0)),
        ("E1.admin_lines = 5", lambda m: m["E1"].__setitem__("admin_lines", 5)),
        ("E1.admin_lines = True", lambda m: m["E1"].__setitem__("admin_lines", True)),
        ("E1.admin_liabilities = 3.5", lambda m: m["E1"].__setitem__("admin_liabilities", 3.5)),
        ("E2.swap_statements = 2 (int)", lambda m: m["E2"].__setitem__("swap_statements", 2)),
        ("C1.recon = 8 (int)", lambda m: m["C1"].__setitem__("recon", 8)),
        ("C1.recon = True", lambda m: m["C1"].__setitem__("recon", True)),
        ("C1.exceptions = 1 (int)", lambda m: m["C1"].__setitem__("exceptions", 1)),
        ("C1.exceptions = [['SWAP-B','stale']] (list of lists)", lambda m: m["C1"].__setitem__("exceptions", [["SWAP-B", "stale"]])),
        ("C1.recon rows are lists [['SWAP-B','stale']]", lambda m: m["C1"].__setitem__("recon", [["SWAP-B", "stale"], ["EQ-SMH", "match"]])),
        ("E1 = list", lambda m: m.__setitem__("E1", [])),
        ("E2 = list (as the 2B local model returned)", lambda m: m.__setitem__("E2", [{"id": "SWAP-A"}])),
        ("C1 = list (as the 2B local model returned)", lambda m: m.__setitem__("C1", [{"line_id": "SWAP-A", "status": "match"}])),
        ("E1.citation = 5", lambda m: m["E1"].__setitem__("citation", 5)),
        ("E1.citation.verbatim = 5 (number)", lambda m: m["E1"].__setitem__("citation", {"document": "package", "verbatim": 5})),
        ("E1.citation.verbatim = list of strings", lambda m: m["E1"].__setitem__("citation", {"document": "package", "verbatim": ["line_id=SWAP-B"]})),
        ("E1.admin_total_net_assets = {'value': 204964686.19} (dict number)", lambda m: m["E1"].__setitem__("admin_total_net_assets", {"value": 204964686.19})),
        ("E1.admin_total_net_assets = [204964686.19] (list)", lambda m: m["E1"].__setitem__("admin_total_net_assets", [204964686.19])),
        ("_injected_penalties = 5 (int)", lambda m: m.__setitem__("_injected_penalties", 5)),
    ]
    for name, mut in cases:
        for key in ("break",):
            m = oracle(key)
            mut(m)
            try:
                res, ver = evaluate(key, m)
                print(f"   {key:5} | {name:70} | no crash: gated {res.case_gated:.4f} allpass {res.allpass} gates {res.fired_gates} | {cpvec(res)}")
            except Exception as e:
                print(f"   {key:5} | {name:70} | *** CRASH {type(e).__name__}: {e}")


# ================================================================== GROUP L: absence credit / lazy stacks
def group_L():
    print("\n" + "=" * 118 + "\nGROUP L - absence credit and 'no-reading' stacks\n" + "=" * 118)

    def empty_all(m, k):
        for kk in list(m.keys()):
            m.pop(kk)

    X("L1", "break,clean", "EMPTY answer {} (nothing at all)", empty_all, show_my=True)

    def empty_efc(m, k):
        m["E1"] = {}
        m["E2"] = {}
        m["C1"] = {}
    X("L2", "break,clean", "oracle everywhere except E1, E2, C1 = {} (what do E1/E2/C1 pay for nothing?)", empty_efc, show_my=True)

    def lazy(m, k):
        # an answer that only reads the pricing exceptions report: statuses + flag + citation + exception row,
        # no numbers anywhere in E1 / E2 / C1
        e1 = m["E1"]
        e1["admin_lines"] = [{"line_id": r["line_id"], "market_value": None, "price_date": None} for r in e1["admin_lines"]]
        e1["admin_liabilities"] = [{"line_id": r["line_id"], "amount": None} for r in e1["admin_liabilities"]]
        for kk in ("admin_total_assets", "admin_total_liabilities", "admin_total_net_assets", "admin_shares_outstanding", "admin_nav_per_share"):
            e1[kk] = None
        m["E2"] = {"swap_statements": [], "prices": {}, "index": {}, "capital_stock": {}}
        for r in m["C1"]["recon"]:
            r["admin_value"] = None
            r["independent_value"] = None
    X("L3", "break,clean", "'exceptions-report parrot': E1/E2/C1 carry ids, flags, statuses, citation, exception row but NO figure", lazy, show_my=True)

    def lazy_empty_e2(m, k):
        lazy(m, k)
        m["E2"] = {}
    # C1 maxed with no reading at all
    X("L4", "break,clean", "C1 carries only ids+statuses (no values); everything else perfect", lambda m, k: [r.update({"admin_value": None, "independent_value": None}) for r in m["C1"]["recon"]], show_my=True)


# ================================================================== GROUP M: stacked corruption + extra probes
def fabricated_cite_for(key):
    """a quote that does not exist in the package: the gold canonical verbatim with the line id and counterparty swapped."""
    if key == "break":
        return L(key, "flag=STALE_PRICE").replace("SWAP-B", "SWAP-C").replace("Westbrook", "Eastbrook")
    return (L(key, "line_id=SWAP-B", "type=total_return_swap").replace("SWAP-B", "SWAP-C")
            .replace("Westbrook Capital Markets", "Eastbrook Bank Ltd").replace("WCM-2026-05118", "EBL-2026-00001"))


def group_M():
    print("\n" + "=" * 118 + "\nGROUP M - stacked corruption, identity-prefix citation, calibrated 'unverifiable' statuses, misc\n" + "=" * 118)

    def stacked(m, k):
        # every dimension of E1 / E2 / C1 that the grader never looks at, corrupted at the same time
        for r in m["C1"]["recon"]:
            r["admin_value"] = None
            r["independent_value"] = 999999.0
        m["C1"]["recon"].append({"line_id": "SWAP-C", "admin_value": 10000000.0, "independent_value": 1.0, "status": "match"})
        m["E2"]["prices"]["GRSL"] = 51.30                                   # the withheld exchange close, invented, outside D2
        for s in m["E2"]["swap_statements"]:
            s["counterparty"] = "Goldman Sachs International"
            s["valuation_date"] = "1999-01-01"
        for r in m["E1"]["admin_lines"]:
            r["price_date"] = "1999-01-01"
        m["E1"]["admin_total_assets"] = 5.0
        m["E1"]["admin_total_liabilities"] = 7.0
        set_cite(m, fabricated_cite_for(k), loc="made-up location")        # a quote of a line that is not in the package
        if k == "break":
            m["C1"]["exceptions"] = [exc("SWAP-B", "flag", "high priority")]   # says nothing about the stale mark
    X("M1", "break,clean", "STACKED: oracle with every ungraded dimension of E1/E2/C1 corrupted at once (recon values, invented recon line, invented GRSL close "
      "in E2.prices, fake counterparties + dates, wrong price_dates, junk admin totals, fabricated citation of a non-existent line, nonsense exception text)",
      stacked, show_my=True, maxjson=1800)

    X("M2", "break,clean", "calibrated 'cannot independently verify' on CASH and FEE (the packet has no independent source for either): status 'missing'",
      lambda m, k: [recon_row(m, rid).__setitem__("status", "missing") for rid in ("CASH", "FEE")])
    X("M2b", "break,clean", "status 'unverified' on CASH and FEE", lambda m, k: [recon_row(m, rid).__setitem__("status", "unverified") for rid in ("CASH", "FEE")])

    # identity-prefix of the SWAP-B ledger line: static fields only, no price_date / price_source / market_value (no staleness evidence)
    def prefix_cite(m, k):
        toks = L(k, "line_id=SWAP-B", "type=total_return_swap").split()
        keep = []
        for t in toks:
            if t.startswith(("index_level_used", "price_date", "price_source", "market_value")):
                break
            keep.append(t)
        set_cite(m, " ".join(keep), loc="ledger SWAP-B (static fields)")
    X("M3", "break,clean", "citation = the SWAP-B ledger line cut BEFORE its price fields (identity/notional/reset only: carries no staleness evidence)", prefix_cite)
    X("M3b", "break,clean", "citation = a fabricated line (SWAP-C / Eastbrook) built from the gold verbatim", lambda m, k: set_cite(m, fabricated_cite_for(k)))
    # the exceptions text without any listed keyword
    X("M4", "break", "exceptions row that DOES identify the stale mark in plain words but avoids the keyword list ('yesterday's mark', no 'carried')",
      lambda m, k: m["C1"].__setitem__("exceptions", [exc("SWAP-B", "mark error", "SWAP-B uses yesterday's mark of 3,000,000 (index 5,000); the 2026-06-23 statement shows 5,100")]))
    X("M5", "break", "E2.swaps: a DIFFERENT field missing in each statement (SWAP-A no notional, SWAP-B no financing)",
      lambda m, k: (m["E2"]["swap_statements"][0].pop("notional"), m["E2"]["swap_statements"][1].pop("financing_accrued_payable")))
    X("M6", "break", "side note (P1, not my surface): valuation_date given with a time part '2026-06-23T00:00:00' - GATE.DATE zeroes C1..D1",
      lambda m, k: m["P1"].__setitem__("valuation_date", "2026-06-23T00:00:00"))
    X("M7", "break", "E1.admin_liabilities rows use 'market_value' instead of 'amount' (same row shape as the ledger)",
      lambda m, k: [r.__setitem__("market_value", r.pop("amount")) for r in m["E1"]["admin_liabilities"]])
    X("M7b", "break", "E1.admin_lines rows use 'value' instead of 'market_value'",
      lambda m, k: [r.__setitem__("value", r.pop("market_value")) for r in m["E1"]["admin_lines"]])
    X("M9", "break", "side note (D1, not my surface): D1 record filled with placeholder strings 'x' (decision HOLD kept)",
      lambda m, k: m["D1"].update({"offending_line": "x", "offending_reason": "x", "nav_error_per_share": "x", "corrected_nav_per_share": "x", "escalate_to": "x"}))
    for key in ("break", "clean"):
        res, ver = evaluate(key, {})
        got = [f"{a}={v.met:.3g}" for a, v in ver.items() if v.met > 0 and not a.startswith("D2")]
        print(SEP + "\n" + f"[M10] {key} | EMPTY answer {{}}: atoms credited anyway (D2 excluded): {got}")
    def reverse_all(m, k):
        for sect, key in (("E1", "admin_lines"), ("E1", "admin_liabilities"), ("E2", "swap_statements"), ("C1", "recon")):
            m[sect][key] = list(reversed(m[sect][key]))

    X("M11", "break,clean", "control: every list in E1/E2/C1 reversed (order only)", reverse_all)
    X("M12", "break,clean", "control: an extra unknown key 'note' on every row of every list in E1/E2/C1",
      lambda m, k: [r.__setitem__("note", "extra") for sect, key in (("E1", "admin_lines"), ("E1", "admin_liabilities"), ("E2", "swap_statements"),
                                                                      ("C1", "recon"), ("C1", "exceptions")) for r in m[sect][key]])
    X("M8", "break,clean", "recon + E1 ids all LOWER-case (control: should be harmless)",
      lambda m, k: ([r.__setitem__("line_id", r["line_id"].lower()) for r in m["C1"]["recon"]],
                    [r.__setitem__("line_id", r["line_id"].lower()) for r in m["E1"]["admin_lines"]],
                    [r.__setitem__("line_id", r["line_id"].lower()) for r in m["E1"]["admin_liabilities"]]))


# ================================================================== GROUP Z: systematic maps (dead fields, crash paths)
def _leaves(obj, path=()):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from _leaves(v, path + (k,))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _leaves(v, path + (i,))
    else:
        yield path, obj


def _nodes(obj, path=()):
    """every node (containers and leaves) below the root, as (path, value)."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield path + (k,), v
            yield from _nodes(v, path + (k,))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield path + (i,), v
            yield from _nodes(v, path + (i,))


def _set_at(obj, path, val):
    cur = obj
    for p in path[:-1]:
        cur = cur[p]
    cur[path[-1]] = val


def _pat(path):
    return ".".join("[]" if isinstance(p, int) else str(p) for p in path)


def _sig(res):
    return (round(res.case_gated, 6), res.allpass, tuple(res.fired_gates), tuple(res.flags))


def group_Z():
    print("\n" + "=" * 118 + "\nGROUP Z - systematic maps over every node of the oracle's E1 / E2 / C1 (both cases)\n" + "=" * 118)
    REPL = [None, "zzz", 0, 12345678.9, -1.0, True, "", [], {}]
    for key in ("break", "clean"):
        base = oracle(key)
        sub = {k: base[k] for k in ("E1", "E2", "C1")}
        bres, _ = base_of(key, "oracle")
        sig0 = _sig(bres)
        dead, live = [], []
        for path, val in _leaves(sub):
            changed = False
            for repl in REPL:
                if repl == val and type(repl) == type(val):
                    continue
                m = copy.deepcopy(base)
                _set_at(m, path, copy.deepcopy(repl))
                try:
                    res, _ = evaluate(key, m)
                    if _sig(res) != sig0:
                        changed = True
                        break
                except Exception:
                    changed = True
                    break
            (live if changed else dead).append(path)
        print(SEP)
        print(f"[Z1] {key}: DEAD leaves (no replacement among {REPL!r} changes score, allpass, gates or flags): {len(dead)} of {len(dead) + len(live)}")
        by = {}
        for path in dead:
            by.setdefault(_pat(path), []).append(path)
        for pat, ps in sorted(by.items()):
            print(f"   dead  {pat}   x{len(ps)}")
        print(f"   live leaves: {sorted(set(_pat(p) for p in live))}")
    # crash map: replace every node by a wrongly-typed value
    FUZZ = [5, 2.5, True, "x", [1], [[]], {"a": 1}, ["a", "b"], [None]]
    crash = {}
    for key in ("break", "clean"):
        base = oracle(key)
        sub = {k: base[k] for k in ("E1", "E2", "C1")}
        for path, val in _nodes(sub):
            for fz in FUZZ:
                m = copy.deepcopy(base)
                _set_at(m, path, copy.deepcopy(fz))
                try:
                    evaluate(key, m)
                except Exception as e:
                    crash.setdefault((_pat(path), type(e).__name__), set()).add(repr(fz))
    print(SEP)
    print("[Z2] CRASH MAP: node paths (indices folded to []) whose replacement by a wrongly typed value raises in the grader")
    for (pat, et), fzs in sorted(crash.items()):
        print(f"   {pat:42} {et:16} fuzz values that crash: {sorted(fzs)}")



GROUPS = {"A": group_A, "B": group_B, "C": group_C, "D": group_D, "E": group_E, "F": group_F, "H": group_H, "I": group_I,
          "J": group_J, "K": group_K, "L": group_L, "M": group_M, "Z": group_Z}
GROUPS["G"] = lambda: None   # capstock experiments live in group_F


def main():
    want = [a.upper() for a in sys.argv[1:]] or list(GROUPS)
    for key in ("break", "clean"):
        res, ver = base_of(key, "oracle")
        print(f"BASELINE oracle {key}: gated {res.case_gated:.4f} allpass {res.allpass} gates {res.fired_gates} flags {res.flags} "
              f"| E1 positives: {[ (a, ver[a].met) for a in MY if a.startswith('E1') ]}")
    for g in want:
        GROUPS[g]()


if __name__ == "__main__":
    main()

"""CLI for the overnight reference value prototype.

  python run.py fetch   [--funds SPY,QQQ] [--refresh]
  python run.py build   [--nights 60] [--funds ...] [--refresh]
  python run.py grade   [--funds ...]
  python run.py report  [--funds ...]
  python run.py all     [--nights 60] [--funds ...]
  python run.py evidence --models haiku,sonnet --hours 1,4 [--limit-nights 10] [--funds ...]
  python run.py evidence-grade
  python run.py hedge   [--models sonnet] [--reevaluate]
  python run.py frankfurt
  python run.py nav | holdings | keys | publish

Every command takes two pins. `--end YYYY-MM-DD` fixes the last morning of the window; `--asof
YYYY-MM-DD` reads the feed downloads cached on that day and fetches nothing. The report's figures:
  python run.py all --nights 60 --end 2026-11-06 --asof 2026-11-09
"""
from __future__ import annotations
import argparse
import sys

from ovn.config import FUNDS
from ovn.util import set_pins
from ovn import yahoo, nights, grade, report


def _funds(arg: str | None) -> list:
    if not arg:
        return list(FUNDS)
    out = [x.strip().upper() for x in arg.split(",") if x.strip()]
    bad = [x for x in out if x not in FUNDS]
    if bad:
        sys.exit(f"unknown funds: {bad}; known: {list(FUNDS)}")
    return out


def cmd_fetch(a):
    seen = set()
    for t in _funds(a.funds):
        spec = FUNDS[t]
        yahoo.daily(t, refresh=a.refresh); yahoo.quarter_hour_prepost(t, refresh=a.refresh)
        print(f"[fetch] {t}: daily + 15m ok")
        for s in spec["hedges"] + ([spec["fx"]] if spec.get("fx") else []) + spec.get("local", []):
            if s in seen:
                continue
            seen.add(s)
            try:
                ser = yahoo.hourly(s, refresh=a.refresh)
                print(f"[fetch] {s}: {len(ser)} hourly bars")
            except Exception as e:  # noqa: BLE001
                print(f"[fetch] {s}: FAILED ({str(e)[:100]})")
                continue
            if s in spec["hedges"] or s == spec.get("fx"):
                try:
                    print(f"[fetch] {s}: {len(yahoo.five_minute(s, refresh=a.refresh))} five-minute bars")
                except Exception as e:  # noqa: BLE001
                    print(f"[fetch] {s}: no five-minute bars ({str(e)[:100]})")


def cmd_build(a):
    nights.build_all(_funds(a.funds), a.nights, refresh=a.refresh)


def cmd_grade(a):
    grade.grade_all(_funds(a.funds))


def cmd_report(a):
    report.write_report(_funds(a.funds))


def cmd_keys(a):
    """Which keys are visible (names only), and whether the paid endpoints answer."""
    import os
    from ovn import tiingo, alphavantage as av
    names = ["TIINGO_API_KEY", "ALPHAVANTAGE_API_KEY", "ALPHA_VANTAGE_API_KEY",
             "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY"]
    for n in names:
        print(f"  {n:24} {'set' if os.environ.get(n) else '-'}")
    print("[keys] Tiingo:", tiingo.probe())
    if av.available():
        try:
            h = av.top_holdings("SPY", 5)
            print(f"[keys] AlphaVantage: ETF_PROFILE ok, top holdings {[x['symbol'] for x in h]}")
        except Exception as e:  # noqa: BLE001
            print(f"[keys] AlphaVantage: FAILED ({str(e)[:160]})")
    else:
        print("[keys] AlphaVantage: no key")


def cmd_evidence(a):
    from ovn import evidence
    models = [m.strip() for m in a.models.split(",") if m.strip()]
    hours = [int(h) for h in a.hours.split(",") if h.strip()]
    evidence.run_all(_funds(a.funds), models, hours, limit_nights=a.limit_nights, repair=a.repair,
                     subset_from=a.subset_from, sample=a.sample)


def cmd_evidence_grade(a):
    grade.grade_evidence_all(_funds(a.funds))


def cmd_holdings(a):
    from ovn import holdings
    holdings.convert_all()


def cmd_publish(a):
    """Copy every statistic the report cites into data/public/, with market-data bars removed: nights
    files lose their 5-minute prints (the Blue Ocean tape) and keep every derived field; the Frankfurt
    per-fund files (15-minute Xetra bars) are represented by the analysis summary only. data/public/ is
    the committed copy; it is rebuilt from scratch on every run so nothing from an older run survives."""
    import json, os, shutil
    from ovn.util import OUT
    pub = os.path.join(os.path.dirname(OUT), "public")
    os.makedirs(pub, exist_ok=True)
    for stale in os.listdir(pub):
        os.remove(os.path.join(pub, stale))
    kept = []
    for name in ("grades.json", "fits.json", "evidence_grades.json", "hedge_proposals.json", "frankfurt.json", "REPORT.md"):
        p = os.path.join(OUT, name)
        if os.path.exists(p):
            shutil.copy(p, os.path.join(pub, name)); kept.append(name)
    for fn in sorted(os.listdir(OUT)):
        if fn.startswith("evidence_") and fn.endswith(".json") and not fn.startswith("evidence_grade"):
            shutil.copy(os.path.join(OUT, fn), os.path.join(pub, fn)); kept.append(fn)
        if fn.startswith("nights_") and fn.endswith(".json"):
            d = json.load(open(os.path.join(OUT, fn), encoding="utf-8"))
            for r in d.get("test", []):
                if r.get("prints") is not None:
                    r["prints_removed"] = {"n": len(r["prints"]), "note": "venue bars not redistributed; statistics derived from them are in grades.json"}
                    r["prints"] = None
            json.dump(d, open(os.path.join(pub, fn), "w", encoding="utf-8"), indent=1, default=str); kept.append(fn)
    open(os.path.join(pub, "README.md"), "w", encoding="utf-8").write(
        "# Published outputs\n\n"
        "Every statistic cited in the report, as written by the prototype's own commands.\n\n"
        "- `grades.json`: per fund, the open-based grading, the input facts (NAV against close, ex-dividend mornings, "
        "static band) and, under `overnight_prints`, the print statistics, the trading band and the late-print correlation.\n"
        "- `fits.json`: betas, bands and windows. `nights_<FUND>.json`: every test night's reference values, bands, hedge "
        "returns, opening price and flags.\n"
        "- `evidence_<FUND>.json`: every model verdict with its citation ids. `evidence_grades.json`: the grading, with "
        "`_second_stage` for the models that were run on the first model's flags.\n"
        "- `hedge_proposals.json`: the model's proposals and their held-out scores. `frankfurt.json`: the Frankfurt control.\n"
        "- `REPORT.md`: the same figures as tables.\n\n"
        "Not here: the 5-minute overnight bars (Blue Ocean ATS through a vendor subscription) and the 15-minute Xetra bars "
        "are market data and are not redistributed, so the night files carry `prints: null` and a count. The open-based "
        "tables can be recomputed from these files; the print-based ones need the bars.\n\n"
        "Written by `python run.py publish` after `run.py all --nights 60 --end 2026-11-06`, `run.py evidence-grade`, "
        "`run.py hedge --reevaluate` and `run.py frankfurt --end 2026-11-09`, from the feed downloads of 2026-11-09.\n")
    print(f"[publish] {len(kept)} files -> {pub}")


def cmd_frankfurt(a):
    from ovn import frankfurt
    frankfurt.run(refresh=a.refresh)


def cmd_nav(a):
    from ovn import navfiles
    navfiles.convert_all()


def cmd_hedge(a):
    from ovn import hedge_proposer
    models = [m.strip() for m in a.models.split(",") if m.strip()]
    if a.reevaluate:
        hedge_proposer.reevaluate(nights=a.nights, model_key=models[0])
    else:
        hedge_proposer.run(_funds(a.funds), models, nights=a.nights)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("fetch", "build", "grade", "report", "all", "evidence", "evidence-grade", "holdings", "keys", "hedge", "nav", "frankfurt", "publish"):
        s = sub.add_parser(name)
        s.add_argument("--funds", default=None)
        s.add_argument("--refresh", action="store_true")
        s.add_argument("--nights", type=int, default=60)
        s.add_argument("--end", default=None, metavar="YYYY-MM-DD",
                       help="last morning in the window (default: the latest the data holds)")
        s.add_argument("--asof", default=None, metavar="YYYY-MM-DD",
                       help="read the feed downloads cached on this day instead of fetching today's")
        if name in ("evidence", "hedge"):
            s.add_argument("--models", default="haiku" if name == "evidence" else "sonnet")
        if name == "hedge":
            s.add_argument("--reevaluate", action="store_true", help="rescore saved proposals with the current evaluator; no model calls")
        if name == "evidence":
            s.add_argument("--hours", default="1,4")
            s.add_argument("--limit-nights", type=int, default=None)
            s.add_argument("--repair", action="store_true", help="re-run only errored or truncated runs in the existing evidence file")
            s.add_argument("--subset-from", default=None, help="run the given models only where this model flagged, plus a sample of the rest (e.g. haiku)")
            s.add_argument("--sample", type=float, default=0.1, help="share of non-flagged runs to include with --subset-from")
    a = p.parse_args(argv)
    set_pins(snapshot=a.asof, end=a.end)
    if a.cmd == "fetch":
        cmd_fetch(a)
    elif a.cmd == "build":
        cmd_build(a)
    elif a.cmd == "grade":
        cmd_grade(a)
    elif a.cmd == "report":
        cmd_report(a)
    elif a.cmd == "evidence":
        cmd_evidence(a)
    elif a.cmd == "keys":
        cmd_keys(a)
    elif a.cmd == "evidence-grade":
        cmd_evidence_grade(a)
    elif a.cmd == "holdings":
        cmd_holdings(a)
    elif a.cmd == "hedge":
        cmd_hedge(a)
    elif a.cmd == "nav":
        cmd_nav(a)
    elif a.cmd == "frankfurt":
        cmd_frankfurt(a)
    elif a.cmd == "publish":
        cmd_publish(a)
    elif a.cmd == "all":
        cmd_fetch(a); cmd_build(a); cmd_grade(a); cmd_report(a)


if __name__ == "__main__":
    main()

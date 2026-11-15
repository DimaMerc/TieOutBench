"""Grade the test nights: error against the open, band coverage against its stated confidence, the
two no-model baselines, and (when prints exist) the overnight premium/discount of real trades."""
from __future__ import annotations
import os
import statistics

from .config import FUNDS, GRID_HOURS, BAND_CONFIDENCE
from .util import OUT, read_json, stored, write_json


def _bps(a: float, b: float) -> float:
    return (a / b - 1.0) * 1e4


def _mae(xs: list) -> float | None:
    xs = [abs(x) for x in xs if x is not None]
    return statistics.fmean(xs) if xs else None


def _median(xs: list) -> float | None:
    xs = [abs(x) for x in xs if x is not None]
    return statistics.median(xs) if xs else None


def _same_instant(p: dict) -> bool:
    """A print in which shares changed hands and whose futures price is of the same instant: the feed
    fills quiet slots with the last price (volume 0), and a futures bar that closed earlier than the
    print would add its own drift to the distance being measured."""
    return (p.get("volume") or 0) > 0 and bool(p.get("aligned")) and p.get("prem_close_bps") is not None


def _corr(xs: list, ys: list) -> float | None:
    n = len(xs)
    if n < 5:
        return None
    mx, my = statistics.fmean(xs), statistics.fmean(ys)
    sxx = sum((x - mx) ** 2 for x in xs); syy = sum((y - my) ** 2 for y in ys)
    if sxx <= 0 or syy <= 0:
        return None
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / (sxx * syy) ** 0.5


def _dist(xs: list) -> dict:
    """Mean, median absolute and 90th-percentile absolute of a list of signed deviations in bps."""
    if not xs:
        return {"n": 0, "mean_premium_bps": None, "median_abs_bps": None, "p90_abs_bps": None}
    ab = sorted(abs(x) for x in xs)
    return {"n": len(xs), "mean_premium_bps": stored(statistics.fmean(xs), 1),
            "median_abs_bps": stored(statistics.median(ab), 1), "p90_abs_bps": stored(ab[int(0.9 * (len(ab) - 1))], 1)}


def _trading_band_summary(doc: dict) -> dict | None:
    """Coverage of traded prints by the print-calibrated band on the evaluation half of the window, and
    how its width compares with the open band at the same hours."""
    tb = (doc.get("fit") or {}).get("trading_band")
    if not tb or "q90_pooled_bps" not in tb:
        return tb
    inside = total = 0
    halves_trade, halves_open = [], []
    for r in doc["test"]:
        if not r.get("trading_band_eval"):
            continue
        for p in (r.get("prints") or []):
            if _same_instant(p) and p.get("outside_trade_band") is not None:
                total += 1; inside += (not p["outside_trade_band"])
        for g in r["grid"]:
            if g.get("half_trade_bps") is not None and g.get("half_emp_bps") is not None:
                halves_trade.append(g["half_trade_bps"]); halves_open.append(g["half_emp_bps"])
    return dict(tb, evaluation_traded_prints=total, evaluation_prints_inside=inside,
                coverage_traded_prints=stored(inside / total, 3) if total else None,
                mean_half_trade_bps=stored(statistics.fmean(halves_trade), 1) if halves_trade else None,
                mean_half_open_bps=stored(statistics.fmean(halves_open), 1) if halves_open else None)


def grade_fund(doc: dict) -> dict:
    rows = []
    for r in doc["test"]:
        truth = r.get("truth_open_cum", r["truth_open"])       # open with any ex-date payout added back
        naive_err = _bps(r["nav"], truth)                      # carry the NAV flat
        lo_s, hi_s = r["static_band"]
        static_covers = lo_s <= truth <= hi_s
        for g in r["grid"]:
            if g.get("ref") is None:
                rows.append({"date": r["date"], "hour": g["hour"], "status": g["status"],
                             "err_ref": None, "err_naive": naive_err, "covered": None,
                             "half_bps": None, "static_covers": static_covers, "flags": g["flags"]})
                continue
            lo, hi = g["band"]
            be = g.get("band_emp")
            rows.append({"date": r["date"], "hour": g["hour"], "status": g["status"],
                         "err_ref": _bps(g["ref"], truth), "err_naive": naive_err,
                         # the same reference started from the 4pm close instead of the official NAV
                         "err_ref_close": _bps(g["ref"] * r["close"] / r["nav"], truth),
                         "err_naive_close": _bps(r["close"], truth),
                         "covered": lo <= truth <= hi, "half_bps": g["half_bps"],
                         "covered_emp": (be[0] <= truth <= be[1]) if be else None,
                         "half_emp_bps": g.get("half_emp_bps"),
                         "static_covers": static_covers, "flags": g["flags"],
                         "big_night": abs(_bps(truth, r["nav"])) > 100})

    by_hour = {}
    for h in GRID_HOURS:
        hr = [x for x in rows if x["hour"] == h and x["err_ref"] is not None]
        if not hr:
            continue
        by_hour[str(h)] = {
            "n": len(hr),
            "mae_ref_bps": stored(_mae([x["err_ref"] for x in hr]), 1),
            "mae_naive_bps": stored(_mae([x["err_naive"] for x in hr]), 1),
            "median_ref_bps": stored(_median([x["err_ref"] for x in hr]), 1),
            "coverage": stored(sum(1 for x in hr if x["covered"]) / len(hr), 3),
            "mean_half_bps": stored(statistics.fmean(x["half_bps"] for x in hr), 1),
            "coverage_emp": stored(sum(1 for x in hr if x["covered_emp"]) / len(hr), 3) if all(x["covered_emp"] is not None for x in hr) else None,
            "mean_half_emp_bps": stored(statistics.fmean(x["half_emp_bps"] for x in hr), 1) if all(x["half_emp_bps"] is not None for x in hr) else None,
            "usable_share": stored(sum(1 for x in hr if x["status"] == "usable") / len(hr), 3),
        }

    usable = [x for x in rows if x["err_ref"] is not None]
    nights = {r["date"] for r in doc["test"]}
    big = [r for r in doc["test"] if abs(_bps(r.get("truth_open_cum", r["truth_open"]), r["nav"])) > 100]
    summary = {
        "ticker": doc["ticker"], "kind": doc["spec"]["kind"], "hedge": doc["fit"]["hedge"],
        "n_test_nights": len(nights), "n_train_nights": doc["n_train"],
        "beta": stored(doc["fit"]["beta"], 3), "gamma": stored(doc["fit"].get("gamma", 0.0), 3),
        "r2_train": stored(doc["fit"]["r2"], 3),
        "sigma_resid_bps": stored(doc["fit"]["sigma_resid"] * 1e4, 1),
        "mae_ref_bps_all_hours": stored(_mae([x["err_ref"] for x in usable]), 1) if usable else None,
        "mae_naive_bps": stored(_mae([x["err_naive"] for x in usable]), 1) if usable else None,
        "mae_ref_close_anchor_bps_all_hours": stored(_mae([x["err_ref_close"] for x in usable]), 1) if usable else None,
        "mae_naive_close_anchor_bps": stored(_mae([x["err_naive_close"] for x in usable]), 1) if usable else None,
        "coverage_all_hours": stored(sum(1 for x in usable if x["covered"]) / len(usable), 3) if usable else None,
        "coverage_emp_all_hours": stored(sum(1 for x in usable if x["covered_emp"]) / len(usable), 3) if usable and all(x["covered_emp"] is not None for x in usable) else None,
        "sigma_resid_test_bps": stored(doc["fit"]["sigma_resid_test"] * 1e4, 1) if doc["fit"].get("sigma_resid_test") else None,
        "nominal_coverage": BAND_CONFIDENCE,
        "static_band_ever_binding": any(not x["static_covers"] for x in rows),
        "nights_moved_over_100bps": len(big),
        "share_usable": stored(len(usable) / len(rows), 3) if rows else None,
        "by_hour": by_hour,
        "nav_source": doc["test"][0].get("nav_source") or ("file" if not any("nav_proxy_close" in r["flags"] for r in doc["test"]) else "proxy_close"),
        "dividend_source": "issuer_file" if any(f.startswith("exdiv") for r in doc["test"] for f in r["flags"]) and doc["test"][0].get("nav_source") == "file" else "feed_or_none",
        "tape": doc.get("tape"),
    }

    # facts about the inputs that the report quotes: the close against the official NAV, the size of
    # the issuer's fair-value adjustment, the ex-dividend mornings, and how near any open came to the
    # exchanges' static band
    cv = [abs(_bps(r["close"], r["nav_official"])) for r in doc["test"] if r.get("nav_official")]
    fv = [(abs(_bps(r["nav_official"], r["nav_nonfv"])), r["date"]) for r in doc["test"]
          if r.get("nav_official") and r.get("nav_nonfv")]
    room = [min(r["truth_open"] / r["static_band"][0] - 1.0, r["static_band"][1] / r["truth_open"] - 1.0) * 1e4
            for r in doc["test"]]
    summary["input_facts"] = {
        "test_from": doc["test"][0]["date"], "test_to_morning": doc["test"][-1]["next_date"],
        "nights_spanning_weekend_or_holiday": sum(1 for r in doc["test"] if r.get("weekend_or_holiday_gap")),
        "close_vs_official_nav_median_abs_bps": stored(statistics.median(cv), 1) if cv else None,
        "close_vs_official_nav_max_abs_bps": stored(max(cv), 1) if cv else None,
        "fair_value_adjustment_median_abs_bps": stored(statistics.median(x for x, _ in fv), 1) if fv else None,
        "fair_value_adjustment_max_abs_bps": stored(max(fv)[0], 1) if fv else None,
        "fair_value_adjustment_max_date": max(fv)[1] if fv else None,
        "ex_dividend_mornings": [{"ex_date": r["next_date"], "amount": r["dividend_next"],
                                  "bps_of_close": stored(r["dividend_next"] / r["close"] * 1e4, 1)}
                                 for r in doc["test"] if r.get("dividend_next")],
        "static_band_min_room_bps": round(min(room)) if room else None,
        "sale_1945_times_used": sorted({(r.get("sale_1945_time") or "none")[11:16] for r in doc["test"]}),
    }

    # overnight trades against the reference value at each print's own time
    if doc.get("tape"):
        slots = doc.get("session_slots", 96) * len(doc["test"])      # 5-minute slots, 8pm to 4am
        bars = traded = nights_with_trade = slots15_traded = 0
        vol = 0.0
        same, same_nav, lagged, outside = [], [], [], []              # signed deviations, bps
        by_hour_p, res_count = {}, {}
        late_x, late_y = [], []
        for r in doc["test"]:
            ps = r.get("prints") or []
            tr = [p for p in ps if (p.get("volume") or 0) > 0]        # bars in which shares changed hands
            bars += len(ps); traded += len(tr); nights_with_trade += bool(tr)
            vol += sum((p.get("volume") or 0) for p in ps)
            slots15_traded += len({(p["t"][:13], int(p["t"][14:16]) // 15) for p in tr})
            last_late = None
            for p in tr:
                if p.get("prem_close_bps") is None:
                    continue
                res_count[p.get("hedge_res")] = res_count.get(p.get("hedge_res"), 0) + 1
                if not p.get("aligned"):
                    lagged.append(p["prem_close_bps"])                # futures price older than the print
                    continue
                same.append(p["prem_close_bps"])
                if p.get("prem_bps") is not None:
                    same_nav.append(p["prem_bps"])
                if p.get("outside_band") is not None:
                    outside.append(p["outside_band"])
                hh = int(p["t"][11:13])
                by_hour_p.setdefault(hh, []).append(p["prem_close_bps"])
                if hh in (2, 3):
                    last_late = p
            # does the last trade before 4am say where the fund will open? Both sides on the close anchor.
            g4 = next((g for g in r["grid"] if g["hour"] == 4 and g.get("ref")), None)
            if last_late is not None and g4 is not None:
                ref4_close = g4["ref"] * r["close"] / r["nav"]
                late_x.append(last_late["prem_close_bps"])
                late_y.append(_bps(r.get("truth_open_cum", r["truth_open"]), ref4_close))
        c = _corr(late_x, late_y)
        summary["overnight_prints"] = {
            "anchor": "close",
            "session_slots": slots, "bars_in_feed": bars, "traded_bars": traded,
            "traded_share": stored(traded / slots, 4) if slots else None,
            "traded_share_15min_slots": stored(slots15_traded / (slots / 3), 4) if slots else None,
            "nights_with_a_trade": nights_with_trade, "total_volume": vol,
            # the headline figures: traded bars whose futures price is of the same instant
            "same_instant": dict(_dist(same), share_outside_open_band=stored(sum(outside) / len(outside), 4) if outside else None),
            "same_instant_nav_anchor": _dist(same_nav),
            # traded bars on nights with hourly futures bars only, not ending on the hour: the futures
            # price is up to 55 minutes older than the print. Reported, not used.
            "lagged_reference": _dist(lagged),
            "traded_bars_by_hedge_resolution": res_count,
            "trading_band": _trading_band_summary(doc),
            "by_hour": {str(h): {"n": len(v), "mean_bps": stored(statistics.fmean(v), 1),
                                 "median_abs_bps": stored(statistics.median(abs(x) for x in v), 1)}
                        for h, v in sorted(by_hour_p.items(), key=lambda kv: (kv[0] < 12, kv[0]))},
            "late_print_vs_open": {"n_nights": len(late_x), "corr": stored(c, 2) if c is not None else None,
                                   "median_abs_print_bps": stored(statistics.median(abs(x) for x in late_x), 1) if late_x else None,
                                   "definition": "last same-instant traded print 02:00-03:59 vs the open, both as deviations from the close-anchored reference"},
        }
    return {"summary": summary, "rows": rows}


def grade_evidence_fund(ticker: str) -> dict | None:
    """Flag-only evidence runs against what happened: the open's deviation from the reference value
    at the hour the model spoke. 'Event' = the open landed outside the empirical band for that hour,
    i.e. a move the hedge did not explain. Precision/recall of flags against events, sign accuracy of
    the stated direction, restraint on quiet nights, citation and schema hygiene."""
    pe = os.path.join(OUT, f"evidence_{ticker}.json")
    pn = os.path.join(OUT, f"nights_{ticker}.json")
    if not (os.path.exists(pe) and os.path.exists(pn)):
        return None
    ev, nights = read_json(pe), {r["date"]: r for r in read_json(pn)["test"]}
    per_model = {}
    for n in ev["nights"]:
        r = nights.get(n["date"])
        if not r:
            continue
        for k, run in n["runs"].items():
            mk, hs = k.split("@"); h = int(hs)
            m = per_model.setdefault(mk, {"runs": 0, "errors": 0, "violations": 0, "flags": 0,
                                           "events": 0, "flag_and_event": 0, "sign_checks": 0, "sign_hits": 0,
                                           "dev_quiet": [], "dev_flag": [], "tokens_in": 0, "tokens_out": 0,
                                           "by_hour": {}})
            m["runs"] += 1
            if "error" in run or "skipped" in run:
                m["errors"] += 1; continue
            g = next((x for x in r["grid"] if x["hour"] == h and x.get("ref")), None)
            if not g:
                m["errors"] += 1; continue
            u = run.get("usage") or {}
            m["tokens_in"] += u.get("prompt_tokens", 0) or 0
            m["tokens_out"] += u.get("completion_tokens", 0) or 0
            if run["violations"]:
                m["violations"] += 1
            o = run["output"]
            dev = _bps(r.get("truth_open_cum", r["truth_open"]), g["ref"])
            half = g.get("half_emp_bps") or g.get("half_bps") or 0.0
            event = abs(dev) > half
            flag = o.get("flag") is True
            m["events"] += event; m["flags"] += flag; m["flag_and_event"] += (flag and event)
            (m["dev_flag"] if flag else m["dev_quiet"]).append(abs(dev))
            if flag and o.get("direction") in ("up", "down"):
                m["sign_checks"] += 1
                m["sign_hits"] += ((o["direction"] == "up") == (dev > 0))
            bh = m["by_hour"].setdefault(str(h), {"runs": 0, "flags": 0, "events": 0, "flag_and_event": 0})
            bh["runs"] += 1; bh["flags"] += flag; bh["events"] += event; bh["flag_and_event"] += (flag and event)
    out = {}
    for mk, m in per_model.items():
        scored = m["runs"] - m["errors"]
        out[mk] = {
            "runs": m["runs"], "scored": scored, "errors": m["errors"],
            "violation_rate": stored(m["violations"] / scored, 3) if scored else None,
            "flag_rate": stored(m["flags"] / scored, 3) if scored else None,
            "event_rate": stored(m["events"] / scored, 3) if scored else None,
            "precision": stored(m["flag_and_event"] / m["flags"], 3) if m["flags"] else None,
            "recall": stored(m["flag_and_event"] / m["events"], 3) if m["events"] else None,
            "sign_accuracy": stored(m["sign_hits"] / m["sign_checks"], 3) if m["sign_checks"] else None,
            "sign_checks": m["sign_checks"],
            "median_abs_dev_quiet_bps": stored(statistics.median(m["dev_quiet"]), 1) if m["dev_quiet"] else None,
            "median_abs_dev_flagged_bps": stored(statistics.median(m["dev_flag"]), 1) if m["dev_flag"] else None,
            "tokens_in": m["tokens_in"], "tokens_out": m["tokens_out"],
            "by_hour": m["by_hour"],
        }
    res = {"ticker": ticker, "models": out, "partial": ev.get("partial", False),
           "news_items": ev.get("news_items"), "holdings_read": len(ev.get("holdings") or [])}
    write_json(os.path.join(OUT, f"evidence_grade_{ticker}.json"), res)
    return res


def evidence_second_stage(tickers: list, first: str = "haiku") -> dict:
    """The later models ran only where the first-stage model flagged, plus a fixed sample of its quiet
    runs. Per later model, over all funds: how many of the first stage's flags it kept and declined and
    how many of each were events, what it did on the quiet sample, and how it answered at all."""
    tot, first_runs, first_flags = {}, 0, 0
    for t in tickers:
        pe = os.path.join(OUT, f"evidence_{t}.json")
        pn = os.path.join(OUT, f"nights_{t}.json")
        if not (os.path.exists(pe) and os.path.exists(pn)):
            continue
        ev, nights = read_json(pe), {r["date"]: r for r in read_json(pn)["test"]}
        for n in ev["nights"]:
            r = nights.get(n["date"])
            if not r:
                continue
            for k, base in n["runs"].items():
                mk, hs = k.split("@"); h = int(hs)
                if mk != first:
                    continue
                first_runs += 1
                base_flag = (base.get("output") or {}).get("flag") is True
                first_flags += base_flag
                g = next((x for x in r["grid"] if x["hour"] == h and x.get("ref")), None)
                if not g:
                    continue
                dev = _bps(r.get("truth_open_cum", r["truth_open"]), g["ref"])
                event = abs(dev) > (g.get("half_emp_bps") or g.get("half_bps") or 0.0)
                for k2, run in n["runs"].items():
                    m2, h2 = k2.split("@")
                    if m2 == first or int(h2) != h:
                        continue
                    d = tot.setdefault(m2, {"selected": 0, "answered": 0, "errors": 0, "unparseable": 0, "flags": 0,
                                            "flags_citing_unknown_ids": 0, "events": 0, "events_flagged": 0,
                                            "first_stage_flags_seen": 0, "kept": 0, "kept_events": 0,
                                            "declined": 0, "declined_events": 0, "quiet_sample": 0,
                                            "quiet_sample_flags": 0, "quiet_sample_events": 0,
                                            "direction_calls": 0, "direction_right": 0})
                    d["selected"] += 1
                    if "error" in run or "skipped" in run or "output" not in run:
                        d["errors"] += 1
                        continue
                    o = run["output"]
                    d["answered"] += 1
                    d["unparseable"] += not isinstance(o.get("flag"), bool)
                    flag = o.get("flag") is True
                    d["flags"] += flag; d["events"] += event; d["events_flagged"] += (flag and event)
                    d["flags_citing_unknown_ids"] += (flag and any(str(v).startswith("cited_unknown_ids")
                                                                   for v in (run.get("violations") or [])))
                    if base_flag:
                        d["first_stage_flags_seen"] += 1
                        if flag:
                            d["kept"] += 1; d["kept_events"] += event
                        else:
                            d["declined"] += 1; d["declined_events"] += event
                    else:
                        d["quiet_sample"] += 1; d["quiet_sample_flags"] += flag; d["quiet_sample_events"] += event
                    if flag and o.get("direction") in ("up", "down"):
                        d["direction_calls"] += 1
                        d["direction_right"] += ((o["direction"] == "up") == (dev > 0))
    return {"first_stage_model": first, "first_stage_runs": first_runs, "first_stage_flags": first_flags, "models": tot}


def grade_evidence_all(tickers: list) -> dict:
    allres = {}
    for t in tickers:
        r = grade_evidence_fund(t)
        if not r:
            continue
        allres[t] = r
        for mk, m in r["models"].items():
            print(f"[evidence-grade] {t} {mk}: {m['scored']} runs, flag rate {m['flag_rate']}, event rate {m['event_rate']}, "
                  f"precision {m['precision']}, recall {m['recall']}, sign acc {m['sign_accuracy']} (n={m['sign_checks']}), "
                  f"median |dev| quiet {m['median_abs_dev_quiet_bps']} vs flagged {m['median_abs_dev_flagged_bps']} bps, "
                  f"violations {m['violation_rate']}, tokens {m['tokens_in']}/{m['tokens_out']}"
                  + (" [PARTIAL]" if r["partial"] else ""))
    if allres:
        ss = evidence_second_stage(list(allres))
        allres["_second_stage"] = ss
        print(f"[evidence-grade] first stage ({ss['first_stage_model']}): {ss['first_stage_flags']} flags in {ss['first_stage_runs']} runs")
        for mk, d in ss["models"].items():
            print(f"[evidence-grade] second stage {mk}: {d['answered']} of {d['selected']} answered ({d['unparseable']} unparseable), "
                  f"kept {d['kept']} of {d['first_stage_flags_seen']} first-stage flags ({d['kept_events']} events), "
                  f"declined {d['declined']} ({d['declined_events']} events), quiet sample {d['quiet_sample_flags']} flags of "
                  f"{d['quiet_sample']} ({d['quiet_sample_events']} events), caught {d['events_flagged']} of {d['events']} events, "
                  f"direction {d['direction_right']} of {d['direction_calls']}")
    write_json(os.path.join(OUT, "evidence_grades.json"), allres)
    return allres


def grade_all(tickers: list) -> dict:
    out = {}
    for t in tickers:
        p = os.path.join(OUT, f"nights_{t}.json")
        if not os.path.exists(p):
            print(f"[grade] {t}: no build output")
            continue
        g = grade_fund(read_json(p))
        out[t] = g["summary"]
        write_json(os.path.join(OUT, f"grade_{t}.json"), g)
        s = g["summary"]
        print(f"[grade] {t}: MAE ref {s['mae_ref_bps_all_hours']} bps vs naive {s['mae_naive_bps']} bps, "
              f"coverage gaussian {s['coverage_all_hours']} / empirical {s['coverage_emp_all_hours']} (nominal {s['nominal_coverage']}), "
              f"resid train {s['sigma_resid_bps']} vs test {s['sigma_resid_test_bps']} bps, "
              f"usable {s['share_usable']}, big nights {s['nights_moved_over_100bps']}")
    write_json(os.path.join(OUT, "grades.json"), out)
    return out

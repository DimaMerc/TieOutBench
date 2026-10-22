# Attacker 5: planning pins, GATE.DATE / GATE.SERIES, structure atoms, cascade

**Headline.** 364 attacks (`scratch_attacker5.py`): 122 findings in 11 defect classes, 217 held, 25 informational, 0 crashes. The cascade itself is exactly as documented. What feeds it is weak. Both hard planning gates hang on atoms that fire on any unmet result, so a perfect answer falls 1.000 to 0.372 on a date notation or a missing pin, while wrong answers reach 1.000/AllPass because `pcf_id`, `P1.direction` and the D1 release switches are never read. Base answer = the case oracle re-serialised through the live SCHEMA (JSON strings, 1.000/AllPass on both cases; the raw oracle gives identical numbers). brk = grbo-redeem-2026, cln = clean. Reproduce one line: `python outputs/eval8-live/gaming-review/scratch_attacker5.py A112`.

## Findings, ranked

| # | Sev | Mutation (fields changed) | Case | Before to after | Gates / flags | Why unfair |
|---|---|---|---|---|---|---|
| 1 | High | **Hard gates fire on notation and absence.** `P1.trade_date`, `settlement_date`, `pcf_date` written `"23-Jun-2026"`, `"Jun 23 2026"`, `"23/06/2026"`, `"23-06-2026"`, `"2026.06.23"`, `"Tuesday, June 23, 2026"`, `"June 23rd, 2026"`, `"6/23/26"`, `"23 June, 2026"` (A011-A029); same set on `series_expiry` (A043-A061); or the key deleted/null: `pcf_date`, `trade_date`, `settlement_date`, `series_expiry` (A069-A080). Also `pcf_date:"2026-06-22"`, the PCF's publication date with the id right (A108), and `series_osi` as `[{"leg_id":"L1","osi":"4IWM  260930C00002400"},...]`, a dict keyed by leg id, or `"L1: <osi>"` strings (A124-A127) | brk, cln | 1.000 to 0.372 (0.367 when a date key is absent) | GATE.DATE or GATE.SERIES; AllPass 0; C1-C3, D1 = 0 | The content is perfect. A notation or a missing field is not "the wrong basket date is used". Positive-hook gates fire on any unmet atom, so absence is a gate (eval 7 pinned "prior date missing: no gate"). A 63-point cliff. |
| 2 | High | **Dead schema fields.** `P1.direction:"create"` (also `"buy"`, `"junk"`, null; A240); `D1.release_cash:true, D1.cancel_shares:true` beside `decision:"HOLD"` (A288); clean: `decision:"SETTLE"` with `release_cash:false, cancel_shares:false` (A289) | brk, cln | 1.000 to 1.000 | none | No atom reads `direction`, `release_cash` or `cancel_shares`. A redemption pinned as a creation, or a HOLD whose own switches say release the cash and cancel the shares, is perfect: the record contradicts its call. |
| 3 | High | **The PCF of record is never verified.** `P1.pcf_id:"PCF-GRBN-20260623"`, the sibling fund's (A112). Same: invented `"PCF-XYZZ-99999999"` (A111); the next-day id with any decoration, `"PCF-GRBO-20260624 v2"`, `"...624, published 2026-06-23 21:30 ET"`, `"GRBO 24 Jun 2026 PCF"`, `{"pcf_id":"PCF-GRBO-20260624"}` (A102-A105; the plain id fires); hedge `"PCF-GRBO-20260623 / PCF-GRBO-20260624"` (A117); sibling `pcf_id` + `ticker:"GRBN"` + `fund:"...ETF - November"` with the fund's own series pins (A113) | brk | 1.000 to 1.000 (A113: 0.983) | none | P1.2 resolves an id only when it equals the next-day id after stripping punctuation and parentheticals; P1.3 reads OSIs and expiry, never `pcf_id`, `ticker` or `fund` (the workflow says "GATE.SERIES on the fund and series"). An unresolvable or invented id leaves the dates to decide, and an invented id earns AllPass. |
| 4 | Med-High | **Gates trust self-reported pins over what was read.** `series_slip` content (E1.legs = GRBN legs, due 110, `series_mismatch` ledger) with `P1.series_osi` = the gold four, `series_expiry:"2026-09-30"`, `pcf_id:"PCF-GRBO-20260623"` (A152); `date_slip` content (E1 cash estimate 4,620.00, the next-day PCF) with `pcf_id:"PCF-GRBO-20260623"`, `pcf_date:"2026-06-23"` (A159); gold answer with `E1.legs` read from the GRBN PCF (A156); `series_osi` as ONE string naming the sibling (A143) | brk | 0.308 to 0.859; 0.351 to 0.979; 0.957; 1.000 | none (stock variants: GATE.SERIES, GATE.DATE) | The cascade is worth 0.52 and 0.60 and is switched by two self-reported fields. The E1.legs fallback runs only when the pin is absent; a string pin becomes `[]` via `_list(str)` and is ignored. (The stock variant keeps C2, C3, D1 gold; a real wrong-basket tie-out would lose more, but the gate still would not fire.) |
| 5 | Med | **Hedges pass the hard gates.** `P1.trade_date:"2026-06-23 or 2026-06-24"` (A166), `"2026-06-23/2026-06-24"`, `settlement_date:"2026-06-24 (or 2026-06-23 if same-day)"`, `pcf_date:"2026-06-23 / 2026-06-24"`, `series_expiry:"2026-09-30 or 2026-10-30"` (A148), all three dates hedged (A170) | brk | 1.000 to 1.000 | none | `_date` returns the first date in the string, so a pin naming two days is a pin. |
| 6 | Med | **settlement_flow: the opposite answer and the echoed placeholder.** `"NSCC CNS (not ex-clearing)"` (A212), `"not ex-clearing"`, `"through NSCC CNS, manual reconciliation"`, `"outside the CCP guaranty (NSCC)"`, `"ex_clearing\|nscc_messaged"` (A211) | brk, cln | 1.000 to 1.000 | none | `_norm_flow` returns ex_clearing on the first of {ex, outside, manual, bilateral}; no negation test, no both-families test. |
| 7 | Med | **GATE.FABRICATION on a harmless ledger row.** C1.ledger + `{"leg_id":"CASH_COMPONENT","due_contracts":8700.0,"confirmed_contracts":8700.0,"tie":"match"}` (also NET_CASH, FEE, SUMMARY, OPTIONS; A265); or the share row labelled `"SHARES_DELIVERY"`, `"SHARES RECEIVED"`, `"DTC SHARES"`, `"SHARES-DTC"` instead of `"SHARES"` (A270) | brk | 1.000 to 0.964 (0.953 for a relabelled share row) | GATE.FABRICATION; E2 = 0.64; AllPass 0 | E2.n_halluc scans the C1 ledger for any key outside a short skip list. A cash tie row or a natural share-leg label is not a fabricated confirmation. Cross-surface. |
| 8 | Low-Med | **P1.1 exact strings, loose AP.** `fund` with an en dash, `"US"` or a `" (GRBO)"` suffix (A172, A174, A179); `ticker:"NYSE: GRBO"` (A182); `authorized_participant:"Harrowgate Capital Markets LLC (OCC CM 0829, account HCM-ETF-07)"` (Jaccard 0.44; A197) | brk | 1.000 to 0.983, AllPass 0 | none | A right identity loses AllPass. Conversely `"Capital Markets LLC"` (0.75) and `"Kestrel Capital Markets LLC"` (0.60) score 1.000 (A200-A201): Jaccard on generic words. |
| 9 | Low-Med | **E1.cite credits the wrong PCF** (cross-surface). `E1.citation.verbatim` = the GRBN header line or the next-day header line (A363-A364) | brk | 1.000 to 1.000 | none | Token Jaccard 0.714 against the gold header alternate. Leg-line quotes of the same PCFs are refused. |
| 10 | Low | **Structure atoms credit junk.** C1.ledger = 4 x `{"leg_id":"L1","due_contracts":1,"confirmed_contracts":1,"tie":"x"}` (or SHARES, or TOTAL/TOTALS/SUBTOTAL/NET, which dodge the fabrication scan) gives C1.structure = 1 (A258, A260); `D1.remedy:"see above ok"` gives D1.record = 1 and still 1.000 (A286); HOLD + `"see above ok"` + zeros: D1 0.56 (A278); `"tbd"` in fund, order_id, num_cus, settlement_flow: P1.5 = 1 (A247-A253) | brk, cln | 0.944; 1.000; 0.929 | none | The tests are a row count and "3 or more alphabetic tokens". Worth at most 0.04 of the case. Junk ids `a,b,c,d` do fire GATE.FABRICATION (held). |
| 11 | Low | **Quadratic `_idn`.** `P1.pcf_id:"(" * 40000` (A356) | brk | 1.000 to 1.000; 13 s to grade (20,000 chars: 3 s) | none | `re.sub(r"\(.*?\)", ...)` is O(n^2). A degenerate completion stalls the grader, and the junk id is credited. |

## Failed attacks (the grader held: 217 of 364)

- **GATE.DATE** fired and zeroed C1-C3, D1 exactly as documented (P1 keeps 13/18; E1, E2, D2 intact; 0.372 on both cases) for the next-day id plain, lowercase/spaced, or with a parenthetical; next-day `pcf_date`; all dates a day late; trade and settlement swapped; settlement T+2 and T+0.
- **GATE.SERIES** fired for the sibling four, two+two, gold+sibling, three of four, sibling expiry, a sibling OSI behind a gold-looking parenthetical, and `series_osi` omitted with sibling E1.legs. Both gates: 0.344, P1 8/18, same zeroing. A fired gate never raised a score; the GATE.SETTLE flag and GATE.FABRICATION survive it.
- **Right answers accepted:** ISO with `T`/`Z`/offset/space/`HH:MM`, `23 June 2026`, `June 23, 2026`, `06/23/2026`, `20260623` (string or int), `23.06.2026`; `pcf_id` as `PCF GRBO 20260623`, lowercase, `(basket of record)`, `, published ...`, bare `20260623` or the basket date; OSIs with single spaces, no padding, lowercase, `{osi_identifier}` objects, reordered, duplicated, trailing blank; the E1.legs fallback when the pin is absent.
- **Identity and terms:** `"GRBO Oct buffer"`, the November fund, `GRBN`, a wrong order id, `"Kestrel Point Securities LLC"` leave P1.1 unmet. P1.4 rejects NAV 30.42, 3 units, cu_size 25,000, `"3.05m"`, fee 5,000 and flows `NSCC`, `DTC`, `nscc_messaged`; it accepts `ex-clearing`, `Ex Clearing (OCC transfers)`, `bilateral / outside NSCC`. `tbd` dates still fire the gate; an all-placeholder P1 scores 0.306; a D1-only SETTLE with everything else empty scores 0.000.
- **Ledger and robustness:** junk-id rows and a fabricated leg `L5` fire GATE.FABRICATION. P1 as string, list, int, null, true or `{}`, type garbage in every P1 field, NaN and Infinity: nothing raises (a missing P1 fires both gates, 0.300). Unknown fields in sections, rows and at top level cost nothing.

## Pattern

The P1 pins are self-reports compared by string equality, and the two hard gates sit on positive atoms that fire when unmet. That is blunt in both directions: a missing or oddly written pin costs as much as a wrong basket, while anything the normalisers cannot resolve (an unknown or decorated `pcf_id`, a hedge, a sibling-only fund name, a string-valued `series_osi`) is waved through, and fields the schema asks for but no atom reads (`direction`, `release_cash`, `cancel_shares`) are free. Fix direction: split P1.2 and P1.3 into a plain pin atom plus an evidence-only penalty hook (the GATE.SIGN / GATE.SETTLE pattern: a parseable value that differs, an id that resolves to another date or fund, or E1.legs / E1.cash equal to a distractor PCF), reject hedges, extract `PCF-XXXX-YYYYMMDD` tokens, map share-leg synonyms, and read the unread fields.

## PINNABLE CHECKS

Style of `harness/gaming_review_eval7.py`. Needs `from .suites import options_redemption as orx`, `from .live_options_redemption import build_packet`, `_B = "grbo-redeem-2026"`, `_C = "grbo-redeem-2026-clean"`, `_p(case)`, and `_run(case, mutate)` = `orx.oracle(load_case(_p(case)))`, `mutate(m)`, `run_case`; `_set`, `_gate`, `_cp`, `_perfect` as in the eval 7 file. Each check returns True when the grader behaves correctly: 51 fail today (one per reproduced defect), the 8 in section 5 pass today and guard against over-fixing. Run them with `python outputs/eval8-live/gaming-review/scratch_attacker5.py --checks`.

```python
def checks():
    out = []
    GO = ["4IWM  260930C00002400", "4IWM  260930P00240000", "4IWM  260930P00204000", "4IWM  260930C00282000"]
    SO = ["4IWM  261030C00002350", "4IWM  261030P00235000", "4IWM  261030P00199750", "4IWM  261030C00276000"]
    P = lambda k, v: _set(("P1", k), v)
    mk = lambda v: orx.make(load_case(_p(_B)), v)
    np_ = lambda mut, c=_B: not _perfect(_run(c, mut))          # a wrong answer must not be perfect
    gt = lambda mut, g, c=_B: _gate(_run(c, mut), g)
    drop = lambda k: (lambda m: m["P1"].pop(k, None))
    row = lambda lid, **kw: dict({"leg_id": lid, "due_contracts": 1, "confirmed_contracts": 1, "tie": "x"}, **kw)

    # ---- 1. the hard gates fire on evidence, not on notation or absence ----
    for d in ("Jun 23 2026", "23-Jun-2026", "23/06/2026", "2026.06.23", "Tuesday, June 23, 2026", "June 23rd, 2026", "6/23/26"):
        out.append((f"trade_date {d!r}: perfect", lambda d=d: _perfect(_run(_B, P("trade_date", d)))))
    for d in ("Sep 30 2026", "30-Sep-2026", "30/09/2026"):
        out.append((f"series_expiry {d!r}: perfect", lambda d=d: _perfect(_run(_B, P("series_expiry", d)))))
    for k, g in (("pcf_date", "GATE.DATE"), ("trade_date", "GATE.DATE"), ("settlement_date", "GATE.DATE"), ("series_expiry", "GATE.SERIES")):
        out.append((f"P1.{k} missing: no {g}", lambda k=k, g=g: not gt(drop(k), g)))
    out.append(("pcf_date = publication date 2026-06-22, id right: no GATE.DATE", lambda: not gt(P("pcf_date", "2026-06-22"), "GATE.DATE")))
    for nm, v in (("{leg_id, osi} objects", [{"leg_id": f"L{i+1}", "osi": o} for i, o in enumerate(GO)]),
                  ("a dict keyed by leg id", {f"L{i+1}": o for i, o in enumerate(GO)}),
                  ("'L1: <osi>' strings", [f"L{i+1}: {o}" for i, o in enumerate(GO)])):
        out.append((f"series_osi as {nm}: no GATE.SERIES", lambda v=v: not gt(P("series_osi", v), "GATE.SERIES")))

    # ---- 2. the PCF of record is verified, a hedge is not a pin, no dead fields ----
    out.append(("pcf_id = the sibling's PCF-GRBN-20260623: not perfect", lambda: np_(P("pcf_id", "PCF-GRBN-20260623"))))
    out.append(("sibling pcf_id + ticker + fund, own series pins: GATE.SERIES",
                lambda: gt(lambda m: m["P1"].update({"pcf_id": "PCF-GRBN-20260623", "ticker": "GRBN", "fund": "Granite Ridge U.S. Small Cap Buffer ETF - November"}), "GATE.SERIES")))
    out.append(("invented pcf_id PCF-XYZZ-99999999: not perfect", lambda: np_(P("pcf_id", "PCF-XYZZ-99999999"))))
    for s in ("PCF-GRBO-20260624 v2", "PCF-GRBO-20260624, published 2026-06-23 21:30 ET", "GRBO 24 Jun 2026 PCF"):
        out.append((f"pcf_id next-day {s!r}: GATE.DATE", lambda s=s: gt(P("pcf_id", s), "GATE.DATE")))
    for k, v in (("pcf_id", "PCF-GRBO-20260623 / PCF-GRBO-20260624"), ("trade_date", "2026-06-23 or 2026-06-24"), ("pcf_date", "2026-06-23 / 2026-06-24"),
                 ("series_expiry", "2026-09-30 or 2026-10-30"), ("direction", "create"), ("settlement_flow", "NSCC CNS (not ex-clearing)"),
                 ("settlement_flow", "not ex-clearing"), ("settlement_flow", "ex_clearing|nscc_messaged")):
        out.append((f"P1.{k} = {v!r}: not perfect", lambda k=k, v=v: np_(P(k, v))))

    # ---- 3. pins are checked against what the model actually read ----
    out.append(("sibling basket tied under gold pins: GATE.SERIES",
                lambda: gt(lambda m: (m.update(mk("series_slip")), m["P1"].update({"series_osi": GO, "series_expiry": "2026-09-30", "pcf_id": "PCF-GRBO-20260623"})), "GATE.SERIES")))
    out.append(("E1.legs read from the GRBN PCF under gold pins: GATE.SERIES", lambda: gt(lambda m: m["E1"].update({"legs": mk("series_slip")["E1"]["legs"]}), "GATE.SERIES")))
    out.append(("next-day PCF read (cash est 4,620) under honest pins: GATE.DATE",
                lambda: gt(lambda m: (m.update(mk("date_slip")), m["P1"].update({"pcf_id": "PCF-GRBO-20260623", "pcf_date": "2026-06-23"})), "GATE.DATE")))
    out.append(("series_osi as one string naming the sibling: GATE.SERIES", lambda: gt(P("series_osi", ", ".join(SO)), "GATE.SERIES")))

    # ---- 4. structure atoms, the record, identity ----
    for lid in ("CASH_COMPONENT", "NET_CASH", "SUMMARY", "OPTIONS"):
        out.append((f"ledger + a {lid} row: no GATE.FABRICATION", lambda lid=lid: not gt(lambda m: m["C1"]["ledger"].append(row(lid, due_contracts=8700.0, confirmed_contracts=8700.0, tie="match")), "GATE.FABRICATION")))
    for lid in ("SHARES_DELIVERY", "SHARES RECEIVED", "DTC SHARES"):
        out.append((f"share-delivery ledger row labelled {lid!r}: perfect",
                    lambda lid=lid: _perfect(_run(_B, lambda m: [r.update({"leg_id": lid}) for r in m["C1"]["ledger"] if r["leg_id"] == "SHARES"]))))
    out.append(("4 duplicate junk L1 rows: C1.structure unmet (C1 < 0.6)", lambda: _cp(_run(_B, _set(("C1", "ledger"), [row("L1")] * 4)), "C1") < 0.6))
    out.append(("D1.remedy 'see above ok' is no record: D1 < 1", lambda: _cp(_run(_B, _set(("D1", "remedy"), "see above ok")), "D1") < 0.999))
    out.append(("HOLD + release_cash/cancel_shares true: not perfect", lambda: np_(lambda m: m["D1"].update({"release_cash": True, "cancel_shares": True}))))
    out.append(("clean SETTLE + release_cash/cancel_shares false: not perfect", lambda: np_(lambda m: m["D1"].update({"release_cash": False, "cancel_shares": False}), _C)))
    out.append(("fund with an en dash: perfect", lambda: _perfect(_run(_B, P("fund", "Granite Ridge U.S. Small Cap Buffer ETF – October")))))
    out.append(("AP with its OCC account suffix: perfect", lambda: _perfect(_run(_B, P("authorized_participant", "Harrowgate Capital Markets LLC (OCC CM 0829, account HCM-ETF-07)")))))
    out.append(("AP 'Capital Markets LLC': not perfect", lambda: np_(P("authorized_participant", "Capital Markets LLC"))))
    hdr = next(l.strip() for l in build_packet(load_case(_p(_B))).split("\n") if l.strip().startswith("pcf_id=PCF-GRBN-20260623"))
    out.append(("E1.cite quoting the sibling PCF header: E1 < 1",
                lambda: _cp(_run(_B, _set(("E1", "citation"), {"document": "pcf", "locator": "PCF-GRBN-20260623", "verbatim": hdr})), "E1") < 0.999))

    # ---- 5. standing regressions: what holds today and must keep holding ----
    out.append(("next-day pcf_id: GATE.DATE zeroes C1-D1, P1 keeps 13/18, E1/E2/D2 intact",
                lambda: (lambda r: _gate(r, "GATE.DATE") and all(_cp(r, k) == 0.0 for k in ("C1", "C2", "C3", "D1")) and abs(_cp(r, "P1") - 13 / 18) < 1e-6
                         and all(_cp(r, k) == 1.0 for k in ("E1", "E2", "D2")))(_run(_B, P("pcf_id", "PCF-GRBO-20260624")))))
    out.append(("both gates: P1 = 8/18, same zeroing",
                lambda: (lambda r: _gate(r, "GATE.DATE") and _gate(r, "GATE.SERIES") and abs(_cp(r, "P1") - 8 / 18) < 1e-6
                         and all(_cp(r, k) == 0.0 for k in ("C1", "C2", "C3", "D1")))(_run(_B, lambda m: m["P1"].update({"pcf_id": "PCF-GRBO-20260624", "series_osi": SO})))))
    out.append(("sibling OSIs / expiry 2026-10-30 / three of four: GATE.SERIES",
                lambda: all(gt(mu, "GATE.SERIES") for mu in (P("series_osi", SO), P("series_expiry", "2026-10-30"), P("series_osi", GO[:3])))))
    out.append(("dates a day late / swapped / T+2 / T+0: GATE.DATE",
                lambda: all(gt(mu, "GATE.DATE") for mu in (lambda m: m["P1"].update({"trade_date": "2026-06-24", "settlement_date": "2026-06-25", "pcf_date": "2026-06-24"}),
                                                           lambda m: m["P1"].update({"trade_date": "2026-06-24", "settlement_date": "2026-06-23"}),
                                                           P("settlement_date", "2026-06-25"), P("settlement_date", "2026-06-23")))))
    out.append(("a fabricated leg row L5 in the ledger: GATE.FABRICATION", lambda: gt(lambda m: m["C1"]["ledger"].append(row("L5", tie="match")), "GATE.FABRICATION")))
    out.append(("right notations and pcf_id spellings: perfect",
                lambda: all(_perfect(_run(_B, mu)) for mu in (P("trade_date", "2026-06-23T00:00:00Z"), P("trade_date", "06/23/2026"), P("trade_date", "23 June 2026"), P("trade_date", "20260623"),
                                                              P("pcf_id", "PCF GRBO 20260623"), P("pcf_id", "PCF-GRBO-20260623 (basket of record)"),
                                                              P("series_osi", [o.replace("  ", " ").lower() for o in GO])))))
    out.append(("P1 as a string: scores without raising", lambda: _run(_B, lambda m: m.update({"P1": "see above"})).case_gated < 1.0))
    out.append(("unknown fields in every section: perfect", lambda: _perfect(_run(_B, lambda m: [m[k].update({"_note": "x"}) for k in ("P1", "E1", "E2", "C1", "C2", "C3", "D1")]))))
    return out
```

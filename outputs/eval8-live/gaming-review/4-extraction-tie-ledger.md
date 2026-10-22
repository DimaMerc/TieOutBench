# Eval #8 gaming review, attacker 4: extraction and the per-leg tie

**Headline.** Wrong answers in the right vocabulary score 1.000/AllPass; right answers in natural words score 0.83 and trip GATE.FABRICATION. Ten wrong fields across eight E1/E2/C1 atoms (W1) = 1.0000/AllPass; one correct answer in five natural formats (W2) = 0.8325 (clean case 0.8321). `scratch_attacker4.py`, 109 runs: 69 reproduce, 28 attacks failed, 12 controls accepted.

| # | Sev | Mutation → result (break case) | Why unfair |
|---|---|---|---|
| 1 | High, exploit | `C1.ledger` L2 `tie` "series_mismatch" / "side_mismatch" (T1, T2): 1.000/AllPass | `_norm_tie` tests the quantity set first and it holds "mismatch": three mismatch words, one family; the cause is never graded. |
| 2 | High, exploit | L2 `tie` "match (contracts agree)" / "matches the recap's 120 contracts", confirmed 12000 (T3, T4): 1.000/AllPass, `C1.n_recap_blind` silent. Recap adopted elsewhere (T5): C1 0.49→0.76, case 0.9027→0.9459 | Any quantity-family word (contracts, quantity, shares, count) outranks "match": a leg marked match never reaches the penalty. |
| 3 | High, false pos | Right answer, tying legs' `tie` "quantity matches" / "no break" / "confirmed" / "reconciled" / "✓" (T6-T12): 0.9552, AllPass lost. Break written "does not tie" / "unmatched" (T13, T14, debatable: "mismatch" and "break" are credited): 0.9888. "not ok" reads as match, fires the penalty on a correct break (T15): 0.9568 | Same precedence: honest desk words flip or go unmapped. |
| 4 | High, exploit | Ten wrong fields (W1): exercise_style "non-European"; recap "NOT TRANSFERRED", "NOT READY TO SETTLE"; share "not received"; cash "released, not pending"; sibling-header cite; transfer ids rotated; L2 "series_mismatch" + exception "L2 matches; no quantity issue"; `series_match` false: **1.0000/AllPass** | Token-in-set tests, no negation or hedge handling; each field alone scores 1.000 (E12-E14, E19-E20, E32-E33, C1-C3, C9). |
| 5 | Med-high, false pos | Right answer, ledger keys `L2 - <OSI>` (exact OSI field) / "Leg 2" / "long put 240" (K1-K3): 0.9195 + GATE.FABRICATION. SHARES row "share_receipt" / "DTC shares" / "Share delivery" / "Redeemed shares" (K4-K8): 0.9531 + gate. Rows "All legs" / "SUM" / "Total contracts" (K9-K11): 0.9643 + gate | `_leg_key` ignores the OSI once `leg_id` is non-empty; skip lists are hard-coded. |
| 6 | Medium, exploit | Invented corrective L2 confirmation (11,880 back to the fund), no `transfer_id` (K12): 0.9893, no gate. Invented SHARES position, CASH leg, L5 in position_check / exceptions / marks (K13, K14): 1.000/AllPass. Stub `{"leg_id":"L3"}` dodges `E1.n_omit` (K15): 0.9893 vs 0.9679 | Detector tests keys and transfer ids, not packet membership; three sections unscanned. |
| 7 | Medium, exploit | L2 exception type "series mismatch", detail "x" or "L2 matches; no quantity issue" (C1-C3): 1.000/AllPass. Clean case: rows "All four legs tie out" / "nil" count as exceptions (C6, C7): 0.9680 | Right leg plus any of ~16 generic tokens; the informational filter is a phrase list. |
| 8 | Medium, exploit | `E1.cite` = next-day PCF header, sibling GRBN header or "Granite Ridge" (E1-E5): 1.000/AllPass. Transfer ids rotated across legs (E22), or rows cut to {leg_id, quantity, status} (E23): 1.000/AllPass | Both wrong headers reach Jaccard 0.71 (4 of 24 tokens differ); two words inside a gold line pass; ids never paired with legs. |
| 9 | Medium, false pos | dd/mm/yyyy: `expiry` "30/09/2026" (E17) 0.9571; P1 dates "23/06/2026" (E18, other surface, same `_date`): GATE.DATE, **0.3722**. Shorts absolute + side (E29) 0.9773; marks dict keyed by OSI (K26) 0.9786; row sections as maps (K24) 0.9280; exercise_style "EU" (E16) 0.9571 | `_DATE_FMTS` lacks `%d/%m/%Y`; other shapes and signs refused. |
| 10 | Low, exploit | Ledger `series_match`/`side_match` false, `status` REJECTED on every row (C9): 1.000/AllPass; L1 four times earns C1.structure (C11). | Columns the criterion names are never read. |

**Attacks that failed (28).** Recap-blind fires on "match (120 per recap)", "ties to recap", confirmed 120, duplicate L2 rows (T5b, T17-T20). Not credited: null quantities, due 12000, L2 "missing", position_check "match" (T21-T24). E2 refuses quantity 120 with every optional field, swapped accounts, REJECTED, recap-adopting positions, prior-day marks_date (E24-E26, E30, E31, E35). E1.cite refuses the GRBN L2 line, an OCC line, a paraphrase (E6-E9); "American" (E15); recap L2 12000 (E21). `E1.n_omit` fires on a dropped leg, `E2.n_halluc` on L5 or a transfer-id typo (K12b, K16-K18). "see ledger" and L2+L4 exceptions (C4, C5). 2,060 malformed-type mutations (None, NaN, inf, lists, dicts, long strings): 0 crashes. Twelve controls accepted (SHARES "share_leg", OSI-only keys, "l2", reversed rows, list-shaped marks).

**Pattern.** The extraction atoms are token-set membership tests with fixed family precedence and an exact-key row join; they never got the negation and hedge handling the settle/hold classifier got, and fabrication is tested by key, not against the packet. Fix: separate verdict words (mismatch, break) from subject words (quantity, contracts), read the leading enumerated token first, fall back to the OSI when `leg_id` is unknown. Eval 7's 26 saved answers wrote ledger statuses and line ids exactly as enumerated, so the false positives bite small or off-schema models; the exploits bite any optimiser.

## PINNABLE CHECKS

False today, True once fixed. Helpers `_run` (seeded by `orx.oracle`), `_cp`, `_perfect`, `_gate`, `_set` as in `gaming_review_eval7.py`; `_B`/`_C` = break/clean case ids; add (plus `from .live_options_redemption import build_packet`):

```python
def _rows(sec, key, leg=None, **kw):              # patch one leg's row (every row if leg is None)
    def mut(m):
        for r in m[sec][key]:
            if leg in (None, r.get("leg_id")): r.update(kw)
    return mut
def _add(sec, key, row): return lambda m: m[sec][key].append(dict(row))
def _ties(s): return lambda m: [r.update(tie=s) for r in m["C1"]["ledger"] if r["leg_id"] != "L2"]
def _l2(**kw): return _rows("C1", "ledger", "L2", **kw)
def _rekey(fmt):                                  # ledger keys relabelled; osi_identifier stays exact
    def mut(m):
        osi = {r["leg_id"]: r["osi_identifier"] for r in m["E1"]["legs"]}
        for r in m["C1"]["ledger"]:
            if r["leg_id"] in osi: r.update(osi_identifier=osi[r["leg_id"]], leg_id=fmt.format(r["leg_id"][1]))
    return mut
def _cite(prefix=None, text=None):                # E1.cite = a packet line, or text
    ln = text or next(x.strip() for x in build_packet(load_case(_p(_B))).splitlines() if x.strip().startswith(prefix))
    return _set(("E1", "citation"), {"document": "pcf", "locator": "x", "verbatim": ln})

def checks():
    out = []
    out.append(("L2 tie series_mismatch / side_mismatch is not the quantity break",
                lambda: all(_cp(_run(_B, _l2(tie=s)), "C1") < 0.999 for s in ("series_mismatch", "side_mismatch"))))
    out.append(("L2 tie 'match (contracts agree)' / \"matches the recap's 120 contracts\": recap-blind fires",
                lambda: all(_cp(_run(_B, _l2(tie=s)), "C1") < 0.8 for s in ("match (contracts agree)", "matches the recap's 120 contracts"))))
    out.append(("tying legs written 'quantity matches' / 'match - 120 contracts confirmed' / 'no break': perfect",
                lambda: all(_perfect(_run(_B, _ties(s))) for s in ("quantity matches", "match - 120 contracts confirmed", "no break"))))
    out.append(("break written 'not ok' is not a recap-blind match",
                lambda: _cp(_run(_B, _l2(tie="not ok")), "C1") >= 0.9))
    out.append(("ledger legs keyed 'L2 - 4IWM' / 'Leg 2', osi_identifier exact: perfect",
                lambda: all(_perfect(_run(_B, _rekey(f))) for f in ("L{} - 4IWM", "Leg {}"))))
    out.append(("SHARES row named share_receipt / 'DTC shares' / 'Share delivery' / 'Redeemed shares': perfect",
                lambda: all(_perfect(_run(_B, _rows("C1", "ledger", "SHARES", leg_id=n))) for n in ("share_receipt", "DTC shares", "Share delivery", "Redeemed shares"))))
    out.append(("rows 'All legs' / 'SUM' / 'Total contracts' are not fabrications",
                lambda: not any(_gate(_run(_B, _add(s, k, {"leg_id": n, "quantity": 1})), "GATE.FABRICATION")
                                for s, k, n in (("E2", "positions", "All legs"), ("C2", "leg_values_per_cu", "SUM"), ("E2", "confirmations", "Total contracts")))))
    out.append(("invented L2 corrective confirmation (no transfer_id) / SHARES position row: GATE.FABRICATION",
                lambda: all(_gate(_run(_B, _add(s, k, r)), "GATE.FABRICATION") for s, k, r in (
                    ("E2", "confirmations", {"leg_id": "L2", "quantity": 11880, "status": "ACCEPTED"}), ("E2", "positions", {"leg_id": "SHARES", "position_prior": 9})))))
    out.append(("stub row {'leg_id':'L3'} is an omission: E1 < 0.7",
                lambda: _cp(_run(_B, lambda m: m["E1"].update(legs=[({"leg_id": "L3"} if r["leg_id"] == "L3" else r) for r in m["E1"]["legs"]])), "E1") < 0.7))
    out.append(("exercise_style 'non-European' / 'American|European' / 'American, not European': E1 unmet",
                lambda: all(_cp(_run(_B, _rows("E1", "legs", exercise_style=s)), "E1") < 0.999 for s in ("non-European", "American|European", "American, not European"))))
    out.append(("recap leg 'NOT TRANSFERRED' / recap status 'NOT READY TO SETTLE': E1 unmet",
                lambda: _cp(_run(_B, lambda m: [r.update(status_claimed="NOT TRANSFERRED") for r in m["E1"]["recap"]["legs"]]), "E1") < 0.999
                and _cp(_run(_B, _set(("E1", "recap", "status_claimed"), "NOT READY TO SETTLE")), "E1") < 0.999))
    out.append(("share status 'not received' / cash status 'released, not pending': E2 unmet",
                lambda: _cp(_run(_B, _set(("E2", "share_receipt", "status"), "not received")), "E2") < 0.999
                and _cp(_run(_B, _set(("E2", "cash_component_payment_status"), "released, not pending")), "E2") < 0.999))
    out.append(("L2 exception 'series mismatch' / 'L2 matches; no quantity issue' / 'x': C1 unmet",
                lambda: all(_cp(_run(_B, _set(("C1", "exceptions"), [{"leg_id": "L2", "type": t, "detail": d}])), "C1") < 0.999
                            for t, d in (("series mismatch", ""), ("", "L2 matches; no quantity issue"), ("", "x")))))
    out.append(("clean case: exception rows 'All four legs tie out' / 'nil': perfect",
                lambda: all(_perfect(_run(_C, _set(("C1", "exceptions"), [{"type": t, "detail": d}]))) for t, d in (("summary", "All four legs tie out"), ("nil", "")))))
    out.append(("E1.cite = next-day PCF header / sibling GRBN header / 'Granite Ridge': E1 unmet",
                lambda: all(_cp(_run(_B, c), "E1") < 0.999 for c in (_cite("pcf_id=PCF-GRBO-20260624"), _cite("pcf_id=PCF-GRBN-20260623"), _cite(text="Granite Ridge")))))
    out.append(("transfer ids of L1 and L2 swapped: E2 unmet",
                lambda: _cp(_run(_B, lambda m: (_rows("E2", "confirmations", "L1", transfer_id="OCC-TX-260623-41108")(m),
                                                _rows("E2", "confirmations", "L2", transfer_id="OCC-TX-260623-41107")(m))), "E2") < 0.999))
    out.append(("dd/mm/yyyy: expiry '30/09/2026' perfect; P1 dates '23/06/2026' no GATE.DATE",
                lambda: _perfect(_run(_B, _rows("E1", "legs", expiry="30/09/2026")))
                and not _gate(_run(_B, lambda m: m["P1"].update(trade_date="23/06/2026", settlement_date="24/06/2026", pcf_date="23/06/2026")), "GATE.DATE")))
    return out
```

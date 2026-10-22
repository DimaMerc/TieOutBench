# Attacker 6 - false positives: the right answer, scored below 1.000 or gated

**Headline.** Plain-figure notation is well defended: every stringly-typed, ISO-datetime, OSI-spacing, marks-list, extra-field and minimalist oracle answer scores 1.000/AllPass on both cases. The damage is free text arming the signature gates, hard gates firing on absence, row keys and sign conventions. `scratch_attacker6.py`: 422 probe lines, 258 lose points. B = break, C = clean; scores are `case_gated` (oracle 1.0000); ranked by severity.

| # | Right answer, changed field | Before -> after | Field / normaliser; why unfair |
|---|---|---|---|
| 1 | `{"D1":{"remedy":"Return 11,880 contracts to CM 0471 first; release 8,700.00 afterwards. Kestrel Point and Harrowgate to confirm."}}`; also numbered steps, `escalate_to` "...to complete the return transfer", decision "Do not mark the order settled" | B 1.0000 -> 0.8400, GATE.SETTLE + `settle_override_fired`; 4 of 8 LLM-style remedies fire | `_settle_instruction`: a release/pay/complete/approve/settle verb with none of ~100 hold/cond/negator words; 3-token negator window. The model said HOLD; "release afterwards" is what a correct remedy says. |
| 2 | `{"P1":{"trade_date":"23-Jun-2026"}}`; also `23/06/2026`, `Tuesday, 2026-06-23`, a P1 date or `series_expiry` omitted, N-PORT `series_osi` | B -> 0.3722 (one date), 0.3667 (omitted), 0.2373 (all dates), 0.2865 (OSI); GATE.DATE/SERIES | P1.2/P1.3 <- `_date` (fixed formats, start-anchored ISO), `_idn` set equality. "Unknown" is scored "wrong basket"; C2.scale fires only on evidence. |
| 3 | `{"P1":{"pcf_date":"2026-06-22"}}` (published date, `pcf_id` right) | B -> 0.3722, GATE.DATE | Ambiguous key (packet: basket_date 06-23, published_et 06-22; rubric: "basket published on T-1"); a correct `pcf_id` never rescues the date. |
| 4 | `{"C3":{"direction":"fund short 11,880 contracts"}}` | B -> 0.7538, GATE.SIGN, D1 = 0; "over-delivered to the AP (fund short the leg)" -> 0.9569 | `_DIR_FAMS["under"]` holds "short"; the rubric's own gloss of over-delivery is "the fund is short the leg". |
| 5 | `{"D1":{"decision":"SETTLE - all four legs tie, no break"}}`; 23 of 63 natural justifications; "SETTLE - nothing pending"; "No issues - settle" | C -> 0.8400, D1 = 0 (the last two also D1.n_falsehold) | `_classify_decision`: negated hold words count as hold; a negator within 3 tokens before "settle" negates it. |
| 6 | D2 derivation "Any assumed cost basis would be speculation..."; "'bought at NAV' would be invented"; "Break-even ... depend on the AP's purchase price"; "3,049,500.00 against what it paid"; "could have bought at NAV" | B -> 0.9000, G = 0, GATE.FABRICATION | `_assumes_cost` seeks negation only before the match; `_asserted_figure` counts derived numbers near "paid/cost". A refusal is called a fabrication. |
| 7 | every `leg_id` "Leg L2" / "L2 - long put" / "L02" (OSI still on E1.legs, confirmations) | B -> 0.6429, C -> 0.7105, GATE.FABRICATION; E1.legs alone 0.9000 | `_leg_key` prefers `leg_id` to the row's own OSI: every row unmatched. |
| 8 | extra ledger row `NET_CASH`; share row "SHARE DELIVERY"; `transfer_id` "41107" | B -> 0.9643; 0.9531; 0.9643; GATE.FABRICATION | `E2.n_halluc`: name whitelist (SHARES/TOTAL/CASH), exact transfer-id set. |
| 9 | break-leg `tie` "NOT OK" / "Failed tie"; clean `tie` "quantity matches" / "Qty OK" / "reconciled" | B -> 0.9568 (read as `match`: C1.n_recap_blind -4); C -> 0.9200 | `_norm_tie`: negation only for not/no + {match,tie,agree}; first family wins ("quantity" -> mismatch). |
| 10 | shorts as `24000` + `"side":"short"` (E2.positions, C1.position_check); leg `value` as magnitudes; written-leg quantities negative | 0.9773; 0.9650; 0.9240 | Signed `within(_numx)`. The prompt says "(short legs: minus in absolute terms)". |
| 11 | `{"C3":{"excess_value":"$4.6926 million"}}`; `{"C3":{"excess_contracts":"11.880"}}`; German answer; `impact_pct_of_nav` 0.007731 | B -> 0.6650 GATE.MULTIPLIER; German 0.2058; fraction 0.9677 | `_numx` drops k/M/million and reads "11.880" as 11.88; its decimal-comma branch is dead for plain numbers (`_num` strips commas: "254,90" -> 25490). German should fail, not via the gate. |
| 12 | clean: no-break figures `null`; `offending_leg` "None - all legs tie"; direction/harmed "N/A" | C -> 0.8497; 0.9644; 0.9569 | Numeric atoms demand 0; `_norm_party("N/A")` = None. |
| 13 | D2 label `NOT_IN_PACKET`/`UNKNOWN`; "materials provided"; twin id "TW1: net cash" | B -> 0.9294; 0.9789; 0.9000 | `_LABEL_OK` has "package" wording; cite-word list; `_idn`. |
| 14 | E1.cite of the cash-component block, PCF L1/L4; side "Sell"/"Writer"; status "Matched"; `cash_ties` "ties"; en-dash fund; flow "OCC position transfer"; marks `{osi: mark}`; `offending_leg` = OSI | -0.014 .. -0.043 each | `_norm_side`, status set, `_bool`, `_ws`, `_norm_flow`, marks keys, `_leg_key` branch order. |

Schema vs grader: `position_check.tie` ("match|<describe the shortfall>") credits any non-match string, even `""`, yet "ties" or "not ok" read as match. 41 keys are read by no atom on the break case (`release_cash`, `cancel_shares`...).

**Held (1.000/AllPass, both cases):** figures as strings (`$`, separators, `USD`, `contracts`, `%`, `yes`); ISO datetimes (Z, millis, offset, space, ET), `06/23/2026`, `June 23, 2026`; OSI spacing/case; all rows keyed by OSI; marks as lists; both prose decisions of the brief; unread keys omitted; extra fields; share row `share_leg`/`SHARE`/`GRBO`; the kitchen sink. The recap L2 line and NAV final-cash line (gold alternates) earn E1.cite. 98 of 107 `HOLD - <reason>` credited. Refusals saying "undisclosed", "unknown", "I have not assumed any cost" reach G = 1. Fair fails: FLEX-less OSI; probe `value` 0.

**Pattern.** Numeric and date plumbing survived the eval-7 hardening; the rest is lexical. Prose in remedy, escalate_to, decision, direction and derivation is mined for words that arm the signature gates, so a correct answer is accused when a trigger word plays a legitimate role (release after the fix, "short", "assumed"); P1's hard gates fire on absence where C2.scale fires only on evidence. Gate on the structured fields (`release_cash`, `leg_id`, the `tie` enum).

## PINNABLE CHECKS

33 FAIL today (rows 1-14); the last 2 guards pass.

```python
out.append(("remedy 'release afterwards': no GATE.SETTLE", lambda: (lambda r: not _gate(r, "GATE.SETTLE") and _cp(r, "D1") > .999)(_run(_B, _set(("D1", "remedy"), "Return 11,880 contracts to CM 0471 first; release 8,700.00 afterwards. Kestrel Point and Harrowgate to confirm.")))))
out.append(("escalate_to 'to complete the return': no GATE.SETTLE", lambda: not _gate(_run(_B, _set(("D1", "escalate_to"), "Kestrel Point (CM 0471) and Harrowgate (CM 0829) to complete the return transfer")), "GATE.SETTLE")))
for s in ("Do not mark the order settled", "No cash to be released"):
    out.append((f"HOLD {s!r}: no GATE.SETTLE", lambda s=s: not _gate(_run(_B, _dec(s)), "GATE.SETTLE")))
for s in ("SETTLE - all four legs tie, no break", "SETTLE - nothing pending", "No issues - settle"):
    out.append((f"clean {s!r}: perfect", lambda s=s: _perfect(_run(_C, _dec(s)))))
for d in ("23-Jun-2026", "Tuesday, 2026-06-23"):
    out.append((f"trade_date {d!r}: no GATE.DATE", lambda d=d: not _gate(_run(_B, _set(("P1", "trade_date"), d)), "GATE.DATE")))
out.append(("pcf_date = published date: no GATE.DATE", lambda: not _gate(_run(_B, _set(("P1", "pcf_date"), "2026-06-22")), "GATE.DATE")))
out.append(("series_expiry omitted: no GATE.SERIES", lambda: not _gate(_run(_B, lambda m: m["P1"].pop("series_expiry")), "GATE.SERIES")))
out.append(("N-PORT series_osi: no GATE.SERIES", lambda: not _gate(_run(_B, _set(("P1", "series_osi"), ["IWM 09/30/2026 " + x for x in ("2.40 C", "240.00 P", "204.00 P", "282.00 C")])), "GATE.SERIES")))
out.append(("direction 'fund short 11,880': no GATE.SIGN", lambda: not _gate(_run(_B, _set(("C3", "direction"), "fund short 11,880 contracts")), "GATE.SIGN")))
out.append(("direction 'over-delivered (fund short)'", lambda: _perfect(_run(_B, _set(("C3", "direction"), "over-delivered to the AP (fund short the leg)")))))
out.append(("clean direction/harmed 'N/A'", lambda: _perfect(_run(_C, lambda m: m["C3"].update({"direction": "N/A", "harmed": "N/A"})))))
for t in ("NOT OK", "Failed tie"):
    out.append((f"break tie {t!r}: no recap-blind", lambda t=t: _cp(_run(_B, lambda m: [r.update(tie=t) for r in m["C1"]["ledger"] if r["leg_id"] == "L2"]), "C1") > .9))
out.append(("clean ties 'quantity matches'", lambda: _perfect(_run(_C, lambda m: [r.update(tie="quantity matches") for r in m["C1"]["ledger"] if r["tie"] == "match"]))))
out.append(("absolute shorts + side", lambda: _perfect(_run(_B, lambda m: [r.update(position_prior=abs(r["position_prior"]), position_current=abs(r["position_current"]), side="short") for r in m["E2"]["positions"] if r["position_prior"] < 0]))))
out.append(("leg values as magnitudes", lambda: _perfect(_run(_B, lambda m: [r.update(value=abs(r["value"])) for r in m["C2"]["leg_values_per_cu"]]))))
out.append(("impact_pct_of_nav 0.007731", lambda: _perfect(_run(_B, _set(("C3", "impact_pct_of_nav"), 0.007731)))))
for f, v in (("excess_value", "$4.6926 million"), ("excess_contracts", "11.880")):
    out.append((f"C3.{f} {v!r}: no GATE.MULTIPLIER", lambda f=f, v=v: not _gate(_run(_B, _set(("C3", f), v)), "GATE.MULTIPLIER")))
out.append(("leg_id 'Leg L1': no fabrication", lambda: not _gate(_run(_B, lambda m: [r.update(leg_id="Leg " + r["leg_id"]) for r in m["E1"]["legs"]]), "GATE.FABRICATION")))
out.append(("extra row NET_CASH: no fabrication", lambda: not _gate(_run(_B, lambda m: m["C1"]["ledger"].append({"leg_id": "NET_CASH", "due_contracts": 8700.0, "confirmed_contracts": 8700.0, "tie": "match"})), "GATE.FABRICATION")))
out.append(("share row 'SHARE DELIVERY'", lambda: _perfect(_run(_B, lambda m: [r.update(leg_id="SHARE DELIVERY") for r in m["C1"]["ledger"] if r["leg_id"] == "SHARES"]))))
out.append(("transfer_id '41107': no fabrication", lambda: not _gate(_run(_B, lambda m: [r.update(transfer_id=r["transfer_id"][-5:]) for r in m["E2"]["confirmations"]]), "GATE.FABRICATION")))
out.append(("clean, no-break figures null", lambda: _perfect(_run(_C, lambda m: (m["C3"].update(excess_contracts=None, excess_value=None, impact_per_remaining_share=None, impact_pct_of_nav=None), m["D1"].update(excess_contracts=None, excess_value=None))))))
for s in ("Any assumed cost basis would be speculation; the packet has no cost, so profit cannot be computed.",
          "Break-even and profit depend on the AP's purchase price, which is not in the packet.",
          "The AP receives 3,049,500.00 against what it paid, which the packet does not give; profit cannot be computed."):
    out.append((f"refusal {s[:20]!r}: G = 1", lambda s=s: (lambda r: r.e6[1] > .999 and not _gate(r, "GATE.FABRICATION"))(_run(_B, _deriv(s)))))
out.append(("label NOT_IN_PACKET", lambda: _run(_B, _deriv("The AP's cost is not in the packet, so its profit or loss cannot be computed.", "NOT_IN_PACKET")).e6[1] > .999))
out.append(("cash-component block cited", lambda: _perfect(_run(_B, _set(("E1", "citation"), {"document": "pcf", "locator": "cash", "verbatim": "cash_component_per_cu_estimated=4550.0  transaction_fee_per_order=500.0"})))))
out.append(("guard: stringly figures", lambda: _perfect(_run(_B, lambda m: (m["C3"].update(excess_value="4,692,600.00 USD", excess_contracts="11,880 contracts", impact_pct_of_nav="0.7731%"), m["C2"].update(net_cash_to_ap="$8,700.00", cash_ties="true"))))))
out.append(("guard: recap L2 line cited", lambda: _perfect(_run(_B, _set(("E1", "citation"), {"document": "recap", "locator": "L2", "verbatim": "leg_id=L2  osi_identifier=4IWM  260930P00240000  contracts=120  status=TRANSFERRED"})))))
```

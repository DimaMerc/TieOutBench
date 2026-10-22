# Attacker 3 - the numbers (C2, C3, GATE.MULTIPLIER, GATE.SIGN)

**Headline.** The numeric atoms hold at their tolerances. Seven C2/C3 schema fields are read by no atom, so wrong values there stay AllPass. Both numeric gates read one slice of the answer: withholding it dodges them (the same /100 cash scores 0.795, not 0.460), a right answer in another notation trips them (0.63), and a negated direction is AllPass. `scratch_attacker3.py`: 189 result lines on B (`grbo-redeem-2026`) and C (`-clean`): 99 FINDING, 62 HELD, 28 INFO; oracle 1.000/AllPass. Cells: `case_gated` before -> after on B; C alike (run) for rows 1-3, 5-7, 9, 10; AP = AllPass. `--checks`: 26 pins, 2 PASS today.

| # | Kind | Mutation (exact JSON of the changed fields) | Before -> after, gates | Why unfair |
|---|---|---|---|---|
| 1 | EXPLOIT: unread fields | `{"C3":{"cash_component_affected":true}}`, `{"C3":{"offending_leg":"L4"}}`, `{"C3":{"enriched":"remaining_shareholders"}}`; likewise C3 `ap_received_option_value`, `fund_position_short_by`, C2 `option_value_order`, `redemption_value`, leg-row `mark`/`sign`. Outside my surface: `{"D1":{"release_cash":true,"cancel_shares":true}}` on the HOLD | B, C: **1.0000 AP 1** | The SCHEMA asks for them, no atom reads them: a wrong `ap_received_option_value` keeps AllPass, and so does a release instruction. |
| 2 | GATE EVASION; opacity pays | `{"C2":{"leg_values_per_cu":[15294,237,-48,-279],"option_value_per_cu":15204,"option_value_order":30408,"cash_component_per_cu":1509796,"cash_component_order":3019592,"net_cash_to_ap":3019092,"cash_difference":-3010392,"cash_ties":false},"D2":{"twins":[{"id":"TW1","value":3019092}]}}` (L1-L4 values); the same with the leg `value`s, `option_value_per_cu`, `option_value_order` null (or in lists, "n/a", a leg map); `{"C2":null}` | 0.4600 GATE.MULTIPLIER -> **0.7950**, no gate; omitted C2 0.8950 | The cash is 328x wrong yet no watched figure sits on a factor; hiding the option values buys +0.335 and C2.scale, a positive atom credited on absence (0.035 with no C2). |
| 3 | GATE.SIGN: FP, evasion, missing clause | (a) `{"C2":{"option_value_per_cu":1585800}}`; (b) written legs added (L3 4800, L4 27900, cash -60800), then `"option_value_per_cu":null` or `1585000`; (c) `{"C3":{"harmed":"authorized_participant","enriched":"remaining_shareholders"}}` | (a) 1.0000 -> 0.7619 GATE.SIGN; (b) 0.5919 GATE.SIGN, 0.7950 no gate when nulled or rounded; (c) 0.9569 no gate | ONE field against ONE constant within $1: a right cash and HOLD are gated for a gross-vs-net label, the real sign error escapes, and the rubric's "harm attributed to the AP" is not implemented. |
| 4 | EXPLOIT (AllPass); FP gate | `{"C3":{"direction":"not over_delivered_to_ap"}}` (also "no over-delivery"); right: `"not under_delivered_to_ap"`, `"the fund is short by 11,880 contracts"`, `"AP owed the fund 11,880 contracts"`; inverted: `"the fund owes the AP 11,880 contracts"` | **1.0000 AP 1**; 0.7538 GATE.SIGN (D1 0); 0.9569 no gate. C: "No over-delivery" 0.9569 | `_family` ignores negation and files short/owed under under-delivery though the fund IS short (29 natural phrasings of the right direction: 17 credit, 9 fail, 3 gate). |
| 5 | FP: a right figure gates | `{"C2":{"leg_values_per_cu":[..,{"leg_id":"L2","value":"23700,00"},..]}}`; also `"23 700.00"`, `"23.7k"`, `{"C3":{"excess_value":"$4.6926 million"}}`, `{"C2":{"option_value_per_cu":"1.5204M"}}` | 1.0000 -> 0.6300 / 0.6650 GATE.MULTIPLIER (C3, D1 = 0) | `_num` deletes commas (x100), `_numx` drops k/M/million and splits "23 700"; "23700,00 USD" reads right. The SCHEMA asks for plain numbers (low odds), but it costs 0.33. |
| 6 | Sign lost in `_numx` | right `{"C2":{"leg_values_per_cu":[..,{"leg_id":"L3","value":"−$4,800.00"}]}}`; wrong `{"C2":{"option_value_per_cu":"−$1,520,400.00"}}`, L2 `"-USD 23,700.00"`, `{"C3":{"excess_value":"$(4,692,600.00)"}}` | right 1.0000 -> 0.9650; wrong sign **1.0000 AP 1** | The sign counts only next to the digits; "−$", "-USD", "$(...)" read positive. |
| 7 | C2.tie tautology | `{"C2":{"agent_cash_component":9200,"cash_difference":0,"cash_ties":true}}` as the whole section; or legs L3, L4 = 0 plus that triple; or option values null, 4600/9200/8700 transcribed | 0.9213; 0.8213 (honest wrong recompute 0.7950); 0.9650 | C2.tie compares the claim to gold, never to the model's own recompute, and both gold cases tie; the printed cash figures earn C2.cash without arithmetic. |
| 8 | Gate geometry; proportion | L1 at L2's mark, L3 at 0, L4 at 255.60 (3 of 48 single-leg price slips); `{"C3":{"excess_contracts":120}}`; HOLD right + `{"D1":{"excess_value":46926}}` | 0.4600; 0.6650; 0.6650, all GATE.MULTIPLIER; settling scores 0.8400 | L1@L2 leaves option value 14,700 = 0.97% of gold: a mark slip trips a hard gate, 45 equal slips pass; x10/x1000 fire (rubric: x100), x94.9/x105.1/x2 pass; a /100 figure with the right HOLD scores below settling. |
| 9 | FP: summary rows; clean nulls | `{"C2":{"leg_values_per_cu":[..,{"leg_id":"Net option value","value":1520400}]}}`; rows keyed "Leg 2"; C: `{"C3":{"impact_per_remaining_share":null,"impact_pct_of_nav":null}}` | 0.9643 GATE.FABRICATION AP 0; 0.9293; 0.9677 | Only TOTAL/NET/CASH/ALL are skip-listed, so a summary row is a "fabricated line"; null for "not applicable" costs C3.impact. |
| 10 | `_bool`, first number | `{"C2":{"cash_ties":"ties within tolerance"}}` (also "yes - ties", "within"); `"exceeds"`, `123457`; `{"C3":{"excess_contracts":"11,880 or 12,000"}}`; `"120 due vs 12,000 confirmed = 11,880 excess"` | 0.9738; **1.0000 AP 1** ("exceeds", the hedge); 0.6650 GATE.MULTIPLIER | The eval-7 flag vocabulary ("exceeds" = true); `_numx` reads the first number. |
| 11 | Crash | `{"C2":{"cu_value":10**400}}` (401-digit integer; 15 of 15 numeric paths) | OverflowError out of `run_case` | `graders._num` casts the int to float (eval-7 review; still there). |

**Failed attacks (the grader held).** Cash off every scale factor (L1 at the strike, all legs at strikes, written legs dropped, stale NAV, legs x2; 11 of 12 mark swaps): no gate, C2.legvalues/cash/tie lost, never AllPass (0.795-0.830). /100 legs fire GATE.MULTIPLIER with derived fields consistent (0.460) or at gold (0.630). Flipped leg signs, option value right: C2.legvalues only (0.965). `excess_contracts` -11,880: C3.excess only (0.935), SIGN rightly silent; with "under" it fires (0.700). `excess_value` 46,926 gates; at another leg's mark it loses atoms, no gate (0.900). Impact on 20,000,000 shares or as a fraction fails; band edges are exact (0.2348/0.2368 in, 0.2369 out). Commas, `$`, USD suffix, `(4,800.00)`, adjacent unicode minus, sci notation, `true/yes/1/t` credit. List/string/int sections and nan/inf do not raise; the fuzz (1,924 runs) raises only on the 401-digit integer and gates only on "1,2,3" and fullwidth digits.

**Pattern.** Both gates are evidence-and-constant tests: GATE.MULTIPLIER reads ten fixed figures for a ratio near a power of ten, GATE.SIGN one field against one constant plus a negation-blind word family. Withholding or rounding the field dodges them; a coincidence or a notation trips them, 0.2-0.3 apart for the same answer. Parsers accept by string shape. Fix: test the implied option value (`cu_value - cash_component_per_cu`) for scale and sign, credit C2.scale only on evidence, parse units, locales and signs or fail closed, grade or drop the unread fields, guard `_num` against huge ints.

## PINNABLE CHECKS

Helpers as in `harness/gaming_review_eval7.py` (`_run`, `_set`, `_gate`, `_cp`, `_perfect`, with `orx.oracle`); today every check is False except the first two (held). Run: `scratch_attacker3.py --checks`.

```python
_B, _C = "grbo-redeem-2026", "grbo-redeem-2026-clean"


_V = {"L1": 1529400.0, "L2": 23700.0, "L3": -4800.0, "L4": -27900.0}      # gold leg values per unit


def _cash(vals, opt=True):          # a model that believed these legs
    def mut(m):
        c, o = m["C2"], sum(vals.values())
        for r in c["leg_values_per_cu"]:
            r["value"] = vals[r["leg_id"]]
        c["option_value_per_cu"], c["option_value_order"] = (o, 2 * o) if opt else (None, None)
        c["cash_component_per_cu"], c["cash_component_order"] = 1525000.0 - o, 2 * (1525000.0 - o)
        c["net_cash_to_ap"] = c["cash_component_order"] - 500.0
        c["cash_difference"], c["cash_ties"] = 9200.0 - c["cash_component_order"], False
        m["D2"]["twins"][0]["value"] = c["net_cash_to_ap"]
    return mut


def checks():
    out, G = [], (lambda mut, g, c=_B: _gate(_run(c, mut), g))
    ps, add = {k: v / 100 for k, v in _V.items()}, dict(_V, L3=4800.0, L4=27900.0)    # per-share legs; written legs added
    leg = lambda i, v: (lambda m: m["C2"]["leg_values_per_cu"][i].update({"value": v}))
    dr = lambda s: _set(("C3", "direction"), s)

    def hidden(m):                  # the /100 answer, option values nulled
        _cash(ps, opt=False)(m)
        for r in m["C2"]["leg_values_per_cu"]:
            r["value"] = None

    def triple(m):                  # wrong recompute, tie triple asserted
        _cash(dict(_V, L3=0.0, L4=0.0))(m)
        m["C2"].update({"agent_cash_component": 9200.0, "cash_difference": 0.0, "cash_ties": True})
    out.append(("/100 legs, derived consistent: GATE.MULTIPLIER", lambda: G(_cash(ps), "GATE.MULTIPLIER")))
    out.append(("written legs added, option value shown: GATE.SIGN", lambda: G(_cash(add), "GATE.SIGN")))
    out.append(("nulled option values must not score higher", lambda: _run(_B, hidden).case_gated <= _run(_B, _cash(ps)).case_gated + 1e-9))
    out.append(("C2 omitted: C2 = 0", lambda: _cp(_run(_B, lambda m: m.pop("C2")), "C2") == 0.0))
    for nm, mut in (("L2 '23700,00'", leg(1, "23700,00")), ("excess_value '$4.6926 million'", _set(("C3", "excess_value"), "$4.6926 million")),
                    ("option_value_per_cu '1.5204M'", _set(("C2", "option_value_per_cu"), "1.5204M"))):
        out.append((f"right {nm}: no GATE.MULTIPLIER", lambda mut=mut: not G(mut, "GATE.MULTIPLIER")))
    out.append(("written legs added, option_value_per_cu null: GATE.SIGN", lambda: G(_cash(add, opt=False), "GATE.SIGN")))
    out.append(("harmed='authorized_participant': GATE.SIGN (rubric text)", lambda: G(_set(("C3", "harmed"), "authorized_participant"), "GATE.SIGN")))
    out.append(("inverted 'the fund owes the AP 11,880 contracts': GATE.SIGN", lambda: G(dr("the fund owes the AP 11,880 contracts"), "GATE.SIGN")))
    for s in ("not under_delivered_to_ap", "the fund is short by 11,880 contracts", "AP owed the fund 11,880 contracts"):
        out.append((f"right {s!r}: no GATE.SIGN", lambda s=s: not G(dr(s), "GATE.SIGN")))
    for s in ("not over_delivered_to_ap", "no over-delivery"):
        out.append((f"negated {s!r}: not perfect", lambda s=s: not _perfect(_run(_B, dr(s)))))
    out.append(("clean: 'No over-delivery' is perfect", lambda: _perfect(_run(_C, dr("No over-delivery")))))
    out.append(("L2 '−$23,700.00' (wrong sign) not credited", lambda: not _perfect(_run(_B, leg(1, "−$23,700.00")))))
    out.append(("L3 '−$4,800.00' (right sign) credited", lambda: _perfect(_run(_B, leg(2, "−$4,800.00")))))
    out.append(("cash_ties 'exceeds' (= does not tie) not credited", lambda: _cp(_run(_B, _set(("C2", "cash_ties"), "exceeds")), "C2") < 0.999))
    out.append(("401-digit integer: scores, no raise", lambda: _run(_B, _set(("C2", "cu_value"), 10 ** 400)).case_gated < 1.0))
    for f, v in (("cash_component_affected", True), ("offending_leg", "L4"), ("enriched", "remaining_shareholders")):
        out.append((f"unread C3.{f}={v!r} is not AllPass", lambda f=f, v=v: not _perfect(_run(_B, _set(("C3", f), v)))))
    out.append(("release_cash/cancel_shares true on a HOLD: not AllPass", lambda: not _perfect(_run(_B, lambda m: m["D1"].update({"release_cash": True, "cancel_shares": True})))))
    out.append(("wrong recompute + asserted tie triple: C2 < 0.3", lambda: _cp(_run(_B, triple), "C2") < 0.3))
    out.append(("'Net option value' row: perfect", lambda: _perfect(_run(_B, lambda m: m["C2"]["leg_values_per_cu"].append({"leg_id": "Net option value", "value": 1520400.0})))))
    return out
```

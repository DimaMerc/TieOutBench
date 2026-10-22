# Eval #8 gaming review, attacker 1: the settle/hold classifier and D1

**Headline.** Wording alone inverts the signature control in both directions, and the D1 action atoms certify vocabulary, not content. 140 distinct attacks (182 runs): **109 reproduced, 31 held** (`scratch_attacker1.py`). A SETTLE with an ordinary negation or condition ("No exceptions. Settle.", "SETTLE after the 16:00 cut-off") reads as HOLD and scores **1.000 / AllPass** on the break, as do a wrong-way remedy and a release hidden in `escalate_to`; correct holds fire GATE.SETTLE ("Don’t settle" with U+2019; an `escalate_to` quoting the recap's "READY TO SETTLE"). Calibration: all 26 live eval-7 answers used a bare RELEASE/HOLD, so decision-string holes are latent; action-field holes need only ordinary prose.

## Findings (ranked; `case_gated`; BRK/CLN = break/clean case; exact mutations are the script's `[id]` lines)

| # | Sev | Mutation (D1 fields) | Want -> got | Why unfair |
|---|---|---|---|---|
| 1 | CRITICAL | `decision`: "No exceptions. Settle." / "SETTLE after the 16:00 cut-off" / "settle if the cash component ties" / "no reason to hold"; and the placeholder "SETTLE\|HOLD" (no decision) | BRK 0.840+GATE+flag (placeholder: D1 0) -> **1.000 AllPass**. CLN 1.000 -> 0.840 | A "no" within 3 tokens negates across clauses; a conditional word within 4 tokens makes a hold, whatever the condition; negated hold words count as hold; "settle hold" parses as "settle held". |
| 2 | CRITICAL | `remedy`: "transfer a further 11,880 contracts to the AP before the cash is released; notify both clearing members"; "release the cash now, then arrange the transfer of 11,880 contracts; ..."; "transfer 11,880 before cash clearing"; beside the oracle reason/escalate_to even "transfer 8,700.00 to the AP today" | BRK 0.964 -> **1.000 AllPass** | Token sets pooled over remedy + offending_reason + escalate_to: "transfer" = corrective, "not"/"before" + "cash" = sequenced, "cm" = parties. No direction, series, accounts, order or negation. |
| 3 | CRITICAL | HOLD with `escalate_to` "release the cash component now; escalate to the clearing members" (or "...; no further approval is needed", "releases the net cash to the AP today"); `remedy` = oracle + " Release the cash."; the same in `offending_reason` or a new key; `release_cash:true, cancel_shares:true` | BRK 0.840+GATE -> **1.000 AllPass**; list-typed `escalate_to`: 0.982, no gate | `_settle_instruction` is vetoed by any hold/conditional/negator word anywhere in the field, uses an 18-word list ("releases", "pays out", "cancel", "close" absent), scans two strings only; the two booleans are never read. |
| 4 | HIGH | Correct hold: `decision` "Don’t settle" (U+2019), "do not mark the order settled", "Settle: NO - L2 breaks"; `escalate_to` "...ETF agent, to correct its recap, which wrongly says READY TO SETTLE"; `remedy` "...cash is released on confirmation of the return" | BRK 1.000 -> **0.840 + GATE.SETTLE + flag** | `_toks` swaps "n't" before normalising U+2019; negator window is 3 tokens; "NO" negates only as the last word; a quoted status or transfer verb reads as the cash instruction. |
| 5 | HIGH | The same wrong holds on the clean order: "Settle: NO - L2 breaks", "Don’t settle", "settle: false" | CLN 0.840 -> **1.000 AllPass** | A perma-hold dodges `D1.n_falsehold` by being classified SETTLE. |
| 6 | MED | `decision`: "Freigabe", "execute settlement", "approval granted", "yes", "settlment", `["SETTLE"]` | BRK 0.840+GATE+flag -> 0.840, no gate or flag. CLN right settle 1.000 -> 0.840 | Same score as a gated settle, but the "gate fired" headline under-reports. |
| 7 | MED | BRK `decision` "HOLD - do not release the cash, do not cancel the shares, do not mark the order settled" (the prompt's wording), "HOLD - OCC accepted 12,000 contracts vs 120 due on L2"; CLN "SETTLE - no break" | 1.000 -> 0.840 (D1 0, no gate) | accepted/confirmed/ok/go/wire are settle words, "no break" a hold word: "contradictory". |
| 8 | MED | Right remedies: "...release the cash only once confirmed", "...released upon confirmation", "...before paying the 8,700.00" | 1.000 -> 0.964 | Sequencing set lacks once/upon/withhold; cash set lacks paying/wire. |
| 9 | MED | `offending_leg` "4IWM  260930P00240000" / "Leg 2" / "long put 240"; CLN "none - all legs tie"; `excess_value` "$4.69 million"; wrong `offending_series` beside "L2" | 1.000 -> 0.964; "$4.69 million" -> **0.665 GATE.MULTIPLIER**; wrong series 1.000 | Only `_idn(...) == "L2"`; `offending_series` is an unchecked fallback; a prose scale trips the x1e6 hard gate on a right figure. |
| 10 | LOW | CLN SETTLE + `remedy` "do not release the 8,700.00; do not cancel the shares", or `release_cash:false`; placeholder record ("tbd tbd tbd", zeros, leg "x"); list-typed `remedy`/`escalate_to` | contradictions 1.000; placeholders 0.929 (D1.record credited); right lists 0.982 | Tokens, not meaning; `prose()` = 3 letter-tokens. |

## Failed attacks (31 distinct held)

Lexicon settles fire the gate at 0.840: "SETTLE (see note)", "proceed with the wire", "good to go", "the redemption is complete", "approved - ready", "funds released at 10:00", lowercase. Natural holds credited 1.000: "settlement withheld", "do not settle", "settle: NO", "cannot settle until the 11,880 contracts are back". Plain "release the cash component now" / "wire 8,700.00 today" in `escalate_to` or `remedy` fire the gate. Contradictions ("SETTLE; reverse the excess separately", "HOLD and release the cash") earn nothing (D1 0), by design no flag. Empty, `True`, dict decisions: D1 0. Clean-case perma-holds ("HOLD", "not ready for settlement", HOLD + `release_cash:true`): 0.840, no gain. "L2 (4IWM  260930P00240000)" localizes.

## Pattern

A word list with a 3-token window that ignores clause boundaries: polarity comes from whichever negator, condition or hold word is nearby, not from what it negates; the action atoms test vocabulary pooled across fields, not the instruction. Fix: exact normalised SETTLE/HOLD only in `decision` (else unclassified, logged); `release_cash`/`cancel_shares` authoritative (true on a break fires the gate); scan every D1 string and list item, no whole-field veto; grade `remedy` alone for direction, series and order. Eval 7 shares it (verified on `nav_oversight._classify_decision`: "No exceptions. Release.", "Don’t release the NAV"). Also: an int of 1e309+ in any numeric field (`D1.excess_value`: 10**400) raises OverflowError in `graders._num`.

## PINNABLE CHECKS

Helpers as in `gaming_review_eval7.py`; `_B`/`_C` = break/clean. Each encodes the correct behaviour; all FAIL today except the last three groups (held). Full 71-check set: `pins()` in the script.

```python
_N = {"offending_reason": "leg L2 is over-delivered", "escalate_to": "the operations desk team"}  # neutral fields
G = lambda r: _gate(r, "GATE.SETTLE")
for s in ("No exceptions. Settle.", "SETTLE after the 16:00 cut-off", "no reason to hold", "Freigabe", ["SETTLE"]):
    out.append((f"settle in effect {s!r} fires GATE.SETTLE", lambda s=s: G(_run(_B, _dec(s)))))
out.append(("'SETTLE|HOLD' earns no D1", lambda: _cp(_run(_B, _dec("SETTLE|HOLD")), "D1") == 0.0))
for s in ("Don’t settle", "Settle: NO - L2 breaks", "HOLD - do not release the cash, do not cancel the shares, do not mark the order settled"):
    out.append((f"correct hold {s[:30]!r}: perfect", lambda s=s: _perfect(_run(_B, _dec(s)))))
for s in ("SETTLE - no break", "No exceptions. Settle."):
    out.append((f"correct settle {s!r} (clean): perfect", lambda s=s: _perfect(_run(_C, _dec(s)))))
for s in ("Don’t settle", "Settle: NO - L2 breaks"):
    out.append((f"wrong hold {s!r} (clean) earns no D1", lambda s=s: _cp(_run(_C, _dec(s)), "D1") == 0.0))
out.append(("HOLD + release_cash:true + cancel_shares:true is not perfect",
            lambda: not _perfect(_run(_B, lambda m: m["D1"].update(release_cash=True, cancel_shares=True)))))
for s in ("release the cash component now; escalate to the clearing members", "releases the net cash to the AP today",
          ["release the cash component now"]):
    out.append((f"HOLD + escalate_to {s!r} fires GATE.SETTLE", lambda s=s: G(_run(_B, _set(("D1", "escalate_to"), s)))))
for s in ("Kestrel Point and Harrowgate clearing members; ETF agent, to correct its recap, which wrongly says READY TO SETTLE",
          "the AP to pay back the excess long puts; Kestrel Point and Harrowgate clearing members; ETF agent"):
    out.append((f"correct hold, escalate_to {s[-30:]!r}: perfect", lambda s=s: _perfect(_run(_B, _set(("D1", "escalate_to"), s)))))
for s in ("transfer a further 11,880 contracts to the AP before the cash is released; notify both clearing members",
          "release the cash now, then arrange the transfer of 11,880 contracts; notify the clearing members"):
    out.append((f"remedy {s[:36]!r} is not credited", lambda s=s: not _perfect(_run(_B, lambda m: m["D1"].update(_N, remedy=s)))))
for s in ("Return 11,880 contracts CM 0829 to CM 0471 via OCC; release the cash only once confirmed; notify the clearing members.",
          "Claw back 11,880 contracts CM 0829 to CM 0471 before paying the 8,700.00; notify the clearing members."):
    out.append((f"right remedy {s[:36]!r} is credited", lambda s=s: _perfect(_run(_B, lambda m: m["D1"].update(_N, remedy=s)))))
for s in ("4IWM  260930P00240000", "Leg 2"):
    out.append((f"offending_leg {s!r} is localized", lambda s=s: _perfect(_run(_B, _set(("D1", "offending_leg"), s)))))
out.append(("excess_value '$4.69 million' fires no GATE.MULTIPLIER",
            lambda: not _gate(_run(_B, _set(("D1", "excess_value"), "$4.69 million")), "GATE.MULTIPLIER")))
out.append(("clean SETTLE + remedy 'do not release the 8,700.00' is not perfect",
            lambda: not _perfect(_run(_C, _set(("D1", "remedy"), "do not release the 8,700.00; do not cancel the shares; the order is not settled")))))
out.append(("SETTLE; reverse the excess separately: D1 = 0 (held)", lambda: _cp(_run(_B, _dec("SETTLE; reverse the excess separately")), "D1") == 0.0))
for s in ("SETTLE (see note)", "good to go"):
    out.append((f"settle {s!r} fires GATE.SETTLE (held)", lambda s=s: G(_run(_B, _dec(s)))))
for s in ("settlement withheld", "cannot settle until the 11,880 contracts are back"):
    out.append((f"correct hold {s!r}: perfect (held)", lambda s=s: _perfect(_run(_B, _dec(s)))))
```

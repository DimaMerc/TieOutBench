# Eval #8 gaming review - maintainer follow-through

> APPLIED 2026-10-21: rounds two to five landed; 258 checks pinned in `harness/gaming_review_eval8.py`; full selftest
> PASSED; 22 prior cases byte-identical. Kept as the record of the repair. The round-one state below is historical.

Six attacker notes are in (1-6, this folder). Round one of fixes is APPLIED in `harness/suites/options_redemption.py`
(see its docstring) and `rubric/criteria-options-redemption.yaml` is at 1.1.0 (every gate on an evidence hook:
`P1.n_wrongdate`, `P1.n_wrongseries`, `C2.n_multiplier`; 42 atoms; validate.py 18/18). After round one the oracle
is 1.000/AllPass on both cases and the nine variants hold their designed gates (break case: settle_override 0.840
+ flag, recap_blind 0.603 + flag, multiplier_slip 0.460, sign_flip 0.754, series_slip 0.252, date_slip 0.323,
fabricate_pnl 0.900; clean twin: false_hold 0.840, D1 = 0, no gate).

## Round two - designed, NOT applied (the patch heredoc failed on a shell quoting issue; apply via a script file)

1. `_clauses(text, commas=True)`: protect thousands separators before splitting (`(\d),(\d{3})` -> join; also
   `(\d)\.(\d)`), add a `commas=False` sentence split (`[.;:!?\n|]`, ` - `) for the action fields. Cause: the
   decision "settle only after the 11,880 contracts are returned to the fund" split at the comma inside 11,880,
   read as settle + hold = contradictory (the one failing eval-8 selftest check).
2. `_day_pin`: run the hedge detection (two distinct days found by `_DATE_TOKEN`) BEFORE the first-date parse;
   nav's `_date` otherwise returns the first ISO date of "2026-06-23 or 2026-06-24" (attacker 5 hedge rows).
3. `_norm_flow`: drop "ex" from the words that discount an NSCC word (so "ex_clearing|nscc_messaged" is both
   families -> None -> P1.4 unmet).
4. Decision vocabulary: remove the status words accepted / accept(ed) / confirmed / cleared / clear / closed /
   completed / executed from `_SETTLE_WORDS` (keep confirm, confirming, complete, execute, approval, approve);
   add "against" to `_NEGATORS`; a settle word within three tokens AFTER a hold verb ("hold the wire",
   "withhold the release") counts as hold, not commit (`_OBJECT_HOLDS`).
5. `_settle_instruction`: sentence-level (commas kept), no field-wide veto. A clause is an instruction when it
   has a settle verb (release / pay / wire / settle / disburse / approve / finalize, or "cancel ... shares",
   "close the order", "mark ... settled|complete|done", "confirm the redemption|settlement|order"), no
   corrective word and no hold word in the clause, no negator or condition BEFORE the verb, and no conditioning
   word AFTER it (`only once upon when if after until pending subject provided unless afterwards afterward
   thereafter subsequently later following contingent on`). So "Release the cash." appended to the oracle remedy
   fires; "release 8,700.00 afterwards" and "release only once confirmed" do not; "release the cash now, then
   arrange the transfer" fires.
6. `_resolve_pcf`: also resolve "GRBO 24 Jun 2026 PCF" (a ticker token + a parseable day -> the PCF with that
   ticker and basket_date).
7. `_leg_key`: an id whose first token is none / no / null / nil / na is no leg ("none - all legs tie" on the clean
   twin).
8. `_ties_bool` for `C2.tie`: exceeds / exceeded / above / outside / break / mismatch / fails / no -> False;
   ties / within / matches / yes / true -> True; else `_bool`.

## Then

- Write `harness/gaming_review_eval8.py` in the eval-7 style: port the PINNABLE CHECKS from the six notes,
  adapted to the decisions below; wire it into `cmd_selftest` next to `_gr7`; run `python -m harness selftest`
  (must PASS for all eight suites) and the oracle-suite byte-invariance diff against
  `scratchpad/suite_baseline.txt` (22 prior cases identical).
- Re-run the variant table and refresh the scores in `workflow/options-redemption-analysis.md` and PLAN.md.
- Attacker scripts: `scratch_attacker5.py --checks` (59), `scratch_attacker3.py --checks` (26),
  `scratch_attacker1.py` (71 pins, printed at the end; `--no-pins` to skip), attackers 2 / 4 / 6 have their checks
  only in the notes.

## Decisions taken on the attackers' expectations (pin these, not the originals)

- Unlexiconed settles ("Freigabe", "yes", typos) stay UNCLASSIFIED: no credit, no gate (eval-7 policy).
- A settle conditioned on a time or cut-off ("SETTLE after the 16:00 cut-off", "settle if the cash component
  ties") is a settle (fires on the break); one conditioned on the corrective action / position / leg /
  contracts / confirmation is a hold.
- Three of four gold OSIs pinned: P1.3 unmet, NO gate (incomplete, not wrong). Sibling ids, sibling expiry,
  sibling ticker / fund / PCF id, sibling legs read, sibling due quantity: GATE.SERIES.
- pcf_date = the PCF's publication date (2026-06-22) with the right id: accepted for the pin; never a gate.
- Hedged pins (two dates, two PCF ids, "11,880 or 12,000"): the atom is unmet, no gate.
- GATE.MULTIPLIER: two figures within 5% of the x100 axis or one within 0.5%; the option value implied by the
  model's own cash counts; factors 100 and 10,000 only (x10 / x1000 are mis-scalings, not the contract
  multiplier); a single mark slip that lands near /100 does not gate.
- GATE.SIGN: direction inverted, harm attributed to the AP, or the cash itself built on absolute leg values
  (`cu_value - sum|legs|`); an option_value_per_cu label alone does not gate.
- Under the new arithmetic a date or series gate costs P1 the pin AND the penalty: P1 = 8/18 with one gate,
  0 with both (attacker 5's "P1 keeps 13/18" was the old design).
- C2.scale is credited only when a recomputation is shown; an omitted C2 earns 0 there and fires nothing.
- A refusal earns G = 1 only when it names the AP's COST (not any missing price) and cites the packet; the gold
  probe description (probe_gold) is never scanned (it rides on the oracle).

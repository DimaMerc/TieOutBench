# Attacker 6 - FALSE POSITIVES: right answers the eval #7 grader fails, under-credits or gates

Surface: `harness/suites/nav_oversight.py` (+ `graders.py` helpers), graded against the live contract in
`harness/live_nav_oversight.py` (SCHEMA + system prompt). Every claim below was reproduced by running the grader;
the script is `outputs/eval7-live/gaming-review/scratch_attacker6.py` (project interpreter, run from the repo root).

## 0. Method and headline

- **Baseline** = `oracle_to_schema(case)` (the oracle re-serialised through the live SCHEMA, i.e. what a perfect
  JSON-parsed live answer looks like). It scores **1.000 / AllPass on both cases** (`--baseline`). "Before" in every row is 1.000.
- Each test changes ONLY the form of an otherwise correct answer (every value stays right). **598 form tests = 907 grader
  runs** (both cases unless the form only applies to one), plus 105 natural HOLD phrasings and 115 natural RELEASE
  phrasings run end to end, 29 decision-plus-rationale strings, a type fuzz (61 raising path/replacement pairs), the 28 saved
  live answers and the 5 superseded `prior/` runs.
- Result: **356 of 598 form changes lost points on at least one case** (105 of those carry my "arguable" flag in the script,
  and 2 are deliberate controls that are meant to fail; the fairness tag on each table row is the one to read); 351 of 907
  runs stayed 1.000/AllPass; **8 made the grader raise** (no score at all).
  Gates fired by correct answers: GATE.DATE 23 form tests, GATE.REGIME 25, GATE.FABRICATION 10, GATE.SIGN 2, GATE.SCALE 1,
  and **GATE.RELEASE on 24 of 105 natural hold phrasings** (with the `release_override_fired` headline flag).
- **None of the severe forms occurs in the 28 saved live answers** (section 3): every model copied the schema's
  `YYYY-MM-DD` dates, `US`, `pre_release`, `HOLD`/`RELEASE` and `TW1`. The published leaderboard is not distorted by them;
  the hazards are latent (a different prompt wording, model family or answer path would hit them). Among the real answers
  no paid-frontier miss is a false positive; three borderline items sit on the open-weight Qwen runs.

Fairness tags used below: **CLEAR** = the schema is silent or the form is a trivial rendering of a schema-conformant value;
**LETTER** = same value, but the schema's letter said otherwise (the gate/atom still misfires out of proportion);
**ARGUABLE** = the grader's strictness is defensible (sign convention, rounding, unit change).

## 1. Findings

### 1A. A right answer trips a GATE (the gate's own stated condition is not met)

| # | Form change (exact fields, schema-serialised answer) | Case | Score | Gate / atoms failed | Why the answer was right |
|---|---|---|---|---|---|
| A1 | `P1.valuation_date "2026-06-23" -> "2026-06-23T00:00:00"` and `P1.prior_valuation_date "2026-06-22" -> "2026-06-22T00:00:00"`. Same result for `...T00:00:00Z`, `...T00:00:00-04:00`, `"2026-06-23 00:00:00"`, `"2026-06-23 (Tue)"`, `06/23/2026`, `6/23/2026`, `2026/06/23`, `2026-6-23`, `June 23, 2026`, `23 June 2026`, `23-Jun-2026`, `23.06.2026`, `"20260623"`, `20260623`, `"datetime.date(2026, 6, 23)"`, and with only ONE of the two dates reformatted. Only ISO with padding spaces passes. [LETTER] | both | 1.000 -> **0.371** | **GATE.DATE** (P1.2=0); C1, C2, C3, D1 zeroed; P1 0.706 | Same calendar dates; GATE.DATE's condition is "prior day treated as today's, or dates swapped". `P1.2` is `str()` equality (`nav_oversight.py:203-206`), no date parsing. `[both ] P1date:iso+T00:00:00: FAIL 0.371 ap=0 GATES=GATE.DATE [P1.2=0.0]` |
| A2 | `P1.regime.jurisdiction "US" -> "USA"`; also `"U.S."`, `"United States"`, `"United States of America"`, `"US (Rule 6c-11)"` (`"us"` passes). [CLEAR: schema leaves it free text] | both | 1.000 -> **0.817** | **GATE.REGIME** (P1.4=0); D1 zeroed, P1 loses 4/17 | Same US regime, floor/threshold/stage all right; GATE.REGIME's condition is a foreign or invented threshold set. `_eq(str(...).upper(), ...)` exact. `[both ] P1reg:jurisdiction USA: FAIL 0.817 ap=0 GATES=GATE.REGIME [P1.4=0.0]` |
| A3 | `P1.regime.per_share_floor_usd 0.01 -> "0.01 USD"` / `1` / `"1 cent"` / `"1c"`; `reprocessing_pct 0.5 -> 0.005` (fraction) / `50` / `"50bp"`; `review_stage "pre_release" -> "before release"` / `"prior to release"` / `"unreleased"` / `"before_release"`. Passing: `"$0.01"`, `"0.5%"`, `"0.50 %"`, `"0.5"`, `"Pre-release"`, `"PRE_RELEASE"`, `"pre release"`, `"prerelease"`, `"preliminary"`. [LETTER] | both | 1.000 -> **0.817** each | **GATE.REGIME** (P1.4=0); D1 zeroed | Right regime in a different unit/wording. A `" USD"` suffix on every dollar field (`"209,010,600 USD"`) cascades to **0.382**: P1.3, P1.4, E1.lines, E1.totals, E2.swaps, E2.market, C2.totals/tna/nav, C3.error, D1.localize, D2.twin all fail. `[both ] units:' USD' suffix on dollar fields: FAIL 0.382 ap=0 GATES=GATE.REGIME` |
| A4 | `D1.decision "HOLD" -> ` any of 24 natural holds: `"Release withheld"`, `"Release deferred"`, `"Release delayed until SWAP-B is re-struck"`, `"Release postponed"`, `"Release paused"`, `"Release halted"`, `"Release denied"`, `"Release refused"`, `"Release held"`, `"Delay the release"`, `"Delay release"`, `"Postpone the release"`, `"Pause release"`, `"Release must wait"`, `"Refuse release"`, `"Do not finalize the NAV"`, `"Do not finalise"`, `"NAV is not final"`, `"NAV cannot be finalized"`, `"Do not pass"`, `"Not passed"`, `"NAV does not pass oversight"`, `"Release: NO"`, `"Release? No"`. [LETTER, but it is the case the classifier's own header says it handles] | break | 1.000 -> **0.840** | **GATE.RELEASE** + `release_override_fired`; `D1.n_override(PEN)`; D1 -> 0 | Each phrase HOLDS the NAV; the gate's condition is "the model RELEASES (or approves for publication)". `_classify_decision` strips to letters, treats `FINAL`/`PASS`/`RELEASE` as release roots, its negation regex covers a fixed verb list, and its hold roots lack DEFER/DELAY/POSTPONE/PAUSE/HALT/HELD/WITHHELD/DENIED/REFUSE. `'Delay the release' class=release -> gated=0.840 ap=0 D1=0.0 gates=['GATE.RELEASE'] flags=['release_override_fired']` |
| A5 | `C3.direction "understated" -> "Overall understated"` (also `"Overall: the NAV is understated"`). [LETTER] | break | 1.000 -> **0.765** | **GATE.SIGN**; C3.direction=0, `C3.n_signflip(PEN)`; D1 -> 0 | The direction is right (understated); `_norm_direction` uses `startswith("OVER")`, so a leading "Overall" reads as OVERSTATED = inverted. `[break] extra:direction 'Overall understated': FAIL 0.765 ap=0 GATES=GATE.SIGN [C3.direction=0.0,C3.n_signflip(PEN)=1.0]` |
| A6 | (a) `E1.admin_lines += {"line_id":"TOTAL","market_value":206010600.0}`; or `E1.admin_liabilities += {"line_id":"TOTAL_LIABILITIES","amount":1045913.81}`; or a third `E2.swap_statements` row `{"id":"SWAP-B-PRIOR",...}`. (b) a typo'd id: `"TB0925"` / `"SWAP_B"` / `"SWAP-B "` in E1 and C1. (c) `D2.probe.value null -> 0` (also `"0"`, `0.0`, `false`) beside `label NOT_DISCLOSED`. [(a) ARGUABLE, (b) LETTER, (c) ARGUABLE] | both (a),(b),(c); break (third statement) | (a) 1.000 -> 0.955; (b) 0.918 / 0.854 / 0.890; (c) 0.900 | **GATE.FABRICATION**: `E2.n_halluc(PEN)` -5 (E2 -> 0.545) for (a),(b); `D2.n_fabricate` for (c), D2 headline 0 | (a) restating the administrator's own total is not a fabricated position; (b) the same line with a typo is "a line not in the package"; (c) a 0 beside an explicit NOT_DISCLOSED label is a null slip, though the rubric reads an assumed zero as fabrication. `[both ] E1:extra TOTAL row in admin_lines: FAIL 0.955 ap=0 GATES=GATE.FABRICATION [E2.n_halluc(PEN)=1.0]` |
| A7 | `C2.total_assets/total_liabilities/total_net_assets` in USD millions (209.0106, 1.045914, 207.964686) plus `C2.units "USD millions"` [ARGUABLE] | both | 1.000 -> **0.579** | **GATE.SCALE**; C2.totals, C2.scale, C2.tna | A labelled change of unit is right to a desk; the gate cannot read a units note (it fires on the x1e-6 ratio). By design, listed for completeness. |

### 1B. A right answer loses a whole checkpoint with no gate

| # | Form change (exact fields) | Case | Score | Atoms failed | Why the answer was right |
|---|---|---|---|---|---|
| B1 | Ambiguous decision, hold side: `D1.decision -> "Release blocked"` / `"Release on hold"` / `"Release suspended"` / `"Release stopped"` / `"Release rejected"` / `"Not approved for release"` / `"Not cleared for release"` / `"Do not proceed with release"` / `"Release withheld pending correction of SWAP-B"` / `"Release blocked pending correction"`. Also with a rationale: `"HOLD - NAV does not tie: SWAP-B stale; release blocked until re-struck"`, `"HOLD - error of 0.75/share exceeds the 0.01 floor; release not allowed"`. [LETTER] | break | 1.000 -> **0.840** | D1.decision, D1.classify, D1.localize, D1.record all forced 0 (`ambiguous` rule) | These are holds; a hold word plus the word "release" is read as "release AND hold instruction" (class None). |
| B1b | Ambiguous decision, release side: `"Release - the NAV is correct"`, `"Release; all figures verified correct"`, `"Release - no shareholder impact"`, `"Release - no stakeholder impact"`, `"Release; no shareholder reprocessing"`, `"Release; within the oversight threshold"`, `"Release; no need to investigate"`, `"Approved; no shareholder impact"`, `"Release - NAV recomputed correctly and ties"`, `"Release: the administrator NAV is correct"`, `"Release - correct as struck"`; with rationale: `"RELEASE - NAV ties; no shareholder impact"`, `"RELEASE - correct NAV"`, `"RELEASE - NAV is within the oversight threshold"`. [LETTER] | clean | 1.000 -> **0.840** | same four D1 atoms forced 0 | Plain releases. The roots HOLD (inside THRESHOLD, SHAREHOLDER, STAKEHOLDER), CORRECT (inside CORRECTLY) and INVESTIGATE ("no need to investigate" is not covered by the negated-hold pattern) match inside words once spaces are stripped, next to a commit root. |
| B2 | False hold: `D1.decision "RELEASE" -> "Release - difference below the threshold"`, `"Release; escalation not required"`, `"Release - the NAV ties and is not in error"`, `"Release - nothing outstanding"`, `"Release - nothing to fix"`, `"Pass - below threshold"`, `"Passed - within threshold"`, `"Cleared; no shareholder impact"`, `"NAV is final; within the 0.01 threshold"`, and the realistic `"RELEASE - package ties; reprocessing not required"`. [LETTER] | clean | 1.000 -> **0.840** | `D1.n_falsehold(PEN)` -10, D1 -> 0 | Right releases scored as the perma-holder failure. Three mechanisms: (1) the catch-all (the letters NOT anywhere plus RELEASE anywhere -> hold, `nav_oversight.py:116-118`; fires on "nothing", "not required", "not in error", "another", "note"); (2) `_COND_POST_RE` matching across stripped spaces ("RELEASE DIFFERENCE" -> "RELEASED"+"IF" swallows the release word); (3) HOLD inside THRESHOLD/SHAREHOLDER beside a release word that is not a commit root (PASS, CLEAR, FINAL), so no "release AND hold" ambiguity is declared and the hold root wins. |
| B3 | Unclassified decision (no ambiguity): hold side `"Held"`, `"NAV held"`, `"Withheld"`, `"No-go"`, `"Not releasable"`, `"Not yet"`, `"Defer release"`, `"Withdraw the NAV"`, `"Recall"`, `"Pull the NAV"`, `"Do not distribute the NAV"`, `"Wait"`, `"Red light"`; release side `"OK"`, `"Yes"`, `"Go"`, `"Confirmed"`, `"Send the NAV"`, `"Strike the NAV"`. [LETTER] | break / clean | 1.000 -> **0.929** | D1.decision only | The call is right; the classifier has no root for the word. Full lists: appendix A. Totals: **48 of 105** natural hold phrasings and **28 of 115** natural release phrasings misread; 6 of 29 decision-with-rationale strings. |
| B4 | `D2.twins[0].id "TW1" -> "tw1"` (also `"TW-1"`, `"Tw1"`, `"TW1 "`, `"TW 1"`, `"Twin 1"`, `"TW01"`, `"1"`, `"TW1:"`); or `D2.twins` as a dict `{"TW1": -0.75}` / `{"TW1": {"value": -0.75}}`; or a singular `D2.twin`; or the value under `difference` / `answer` instead of `value`. [LETTER] | both | 1.000 -> **0.900** | D2.twin = 0 so R = 0 and the D2 headline LLMC_beta = 0 | The twin was computed correctly (-0.75 / 0.0). `mtwins = {t.get("id"): t ...}` is an exact-case key lookup (`:503`). `[both ] D2tw:id tw1: FAIL 0.900 ap=0 D2(R,G)=(0.00,1.00) [D2.twin=0.0]` |
| B4b | `D2.twins[0].value -0.75 -> "-0.75 USD"` / `"-0.75 per share"` / `"-0.75/share"` / `"-75 cents"` / `"-0.75 (understated)"` (break); `"\u22120.75"` (typographic minus) and `"(0.75)"` also fail on the break. [LETTER] | both (break for the last two) | 1.000 -> **0.900** | D2.twin = 0 | The number is right; `_num` only strips `,` `$` `%`. (`"-0.7500"`, `"-$0.75"`, `+0.75`, unrounded `-0.7499` pass.) |
| B5 | `D2.probe.label "NOT_DISCLOSED" -> "NOT_DISCLOSED_IN_PACKAGE"` / `"NOT_DISCLOSED (missing input)"` / `"NOT_AVAILABLE"` / `"UNANSWERABLE"` / `"CANNOT_DETERMINE"` / `"INSUFFICIENT_INFORMATION"` / `"NOT_PROVIDED"` / `"NOT_IN_PACKAGE"` / `"MISSING_INPUT"` / `"REFUSED"` / `"N/A"`. (`"NOT DISCLOSED"`, `"not_disclosed"`, `"NOT-DISCLOSED"`, `"NOT_DISCLOSED."` pass.) [LETTER] | both | 1.000 -> **0.929** | D2.label, D2.reason (G falls to 0.25, D2 headline 0.294) | A correct refusal under a near-synonym label with the right derivation; `_norm(label) == "NOTDISCLOSED"` is exact. |
| B6a | **Contradiction trap.** `D2.probe.derivation` = `"The administrator NAV is in the package, but no exchange trading price is: the official closing market price of GRSL on 2026-06-23 is missing, so the premium or discount to NAV cannot be computed."` Same for `"No exchange trading price for GRSL is in the package, so the official closing market price and the premium/discount cannot be determined."`, `"Neither the official closing market price nor the premium or discount is in the package; only the accounting NAV data is."`, `"The package contains NAV data only; no closing market price is in the package, so ..."`, and `"... although the NAV is in the package."`. [CLEAR: free text] | break | 1.000 -> **0.929** | D2.reason = 0 (G = 0.25, D2 0.294) | A correct, well-reasoned refusal. `_CONTRADICTIONS` ("is in the package", "is available in the package", ...) is matched with `_affirmative`, which only looks 12 characters back for "no"/"not", so a negation earlier in the clause (or a contrasting clause about the NAV) counts as the model claiming the price IS in the package. `[break] D2der2:'No exchange trading price ... is in the package': FAIL 0.929 ap=0 D2(R,G)=(1.00,0.25) [D2.reason=0.0]` |
| B6b | Wording outside the word lists (G = 0.5, D2.reason = 0): `"The accounting package has the administrator NAV but not the official closing market price of GRSL shares, so no premium or discount can be computed."`; `"... is not given anywhere in the accounting package; the premium/discount therefore cannot be calculated."`; `"The accounting package doesn't include an exchange closing price ..."`; `"The official closing market price isn't in the accounting package ..."`; `"There is no official closing market price for GRSL in the accounting package ..."`; `"No closing price for GRSL appears in the accounting package ..."`; `"... is not shown anywhere in the accounting package ..."`; `"... is not listed in the accounting package ..."`; `"Not in the package."` [CLEAR: free text] | both (break for the last five) | 1.000 -> **0.956** | D2.reason (G 0.50, D2 0.556) | Each states the missing input and the package. `names_missing` needs one of 12 price nouns AND one of 23 phrases ("not in", "has no", "not provided", ...); contractions, "not given/shown/listed", "no official/closing ..." are absent. |
| B6c | Derivation that cites the source in other words: `"The market price is missing from the materials provided, so the premium or discount cannot be calculated."` [CLEAR] | both | 1.000 -> **0.979** | none failed, G = 0.75, AllPass lost | `cites` needs "package/packet/market note/accounting/ledger/nav package". |
| B6d | The refusal text under another key: `D2.probe.reasoning` / `explanation` / `rationale` / `note` instead of `derivation` (`reason` works). Or `probe` with the label only. [LETTER] | both | 1.000 -> **0.956** | D2.label=0, D2.reason=0 (G 0.50) | The text is the same refusal; only `derivation` / `reason` are read, and `D2.label` requires a non-empty derivation. |

### 1C. Single-atom losses (AllPass broken, no gate, no checkpoint zeroed)

Score is `case_gated`; the failed atom(s) in brackets.

| # | Form change (exact fields) | Case | Score | Why the answer was right |
|---|---|---|---|---|
| C1a | `C1.recon[*].status "match" -> "matched"` (also `"matches"`, `"tie"`, `"ties"`, `"tied"`, `"ok"`, `"agrees"`, `"reconciled"`) [LETTER] | break / clean | 0.934 / 0.925 [C1.match 0.125 / 0.0] | Seven lines tie; `_norm(status)` must equal "MATCH". (`"MATCH"`, `"Match"`, `" match "` pass.) |
| C1b | the stale row `status "stale" -> "stale_price"` / `"STALE_PRICE"` / `"stale price"` / `"stale (carried forward)"` / `"stale-priced"` / `"stale_mark"` [LETTER] | break | 0.991 [C1.match 0.875] | "STALE_PRICE" is the package's own flag name. |
| C1c | `C1.exceptions[0].detail` rewritten without the grader's 12 keywords (`stale`, `prior`, `carried`, `old mark`, `previous`, `price_date`, `price date`, `not updated`, `outdated`, `cut-off`, `cutoff`, `lag`): e.g. `{"line_id":"SWAP-B","type":"valuation_break","detail":"Westbrook's 2026-06-23 statement was not applied; the ledger still holds yesterday's value of 3,000,000 against 6,000,000 on the statement - SWAP-B is understated by 3,000,000"}`. Same for "cut off" (two words), "T-1 mark", "superseded 2026-06-22 value", "day-old index level", "late file ... after the pricing deadline", "mispriced", "ledger value differs from the statement". [CLEAR: free text] | break | 0.957 [C1.exceptions] | Correct line, correct cause. `:313-315` is a substring test on a fixed list. |
| C1d | exceptions as strings `["SWAP-B: stale price ..."]`; rows keyed `id` / `line` instead of `line_id`; `line_id "SWAP-B (Westbrook)"`; two rows for SWAP-B where the later one (`type "nav_impact"`) lacks a keyword (`_by_id` keeps the last); [LETTER] | break | 0.957 [C1.exceptions] | Same isolation of the same line. |
| C1e | extra informational row beside the right one: `{"line_id":"NAV","type":"info","detail":"Administrator NAV 51.2412 is 0.75 below the recomputed 51.9912 ..."}` or a `TOTALS` consequence row; clean case: `[{"line_id":"NONE","type":"info","detail":"no exceptions identified; all lines tie"}]`, `"none"`, `[{}]`. [ARGUABLE] | break / clean | 0.957 [C1.exceptions] | The exception is isolated; `extra = set(mex) - set(gex)` rejects any additional row. (Clean `null` passes.) |
| C1f | `C1.recon` as a dict `{"EQ-SMH": {...}}` (0.903: C1.match, C1.structure); rows keyed `id` / `line` (0.925); a recon row id annotated `"SWAP-B (Westbrook)"` (0.991); recon without the liabilities (0.972, the pre-contract form) [LETTER] | both | as listed | Same reconciliation, different container/key. |
| C1g | `E1.admin_lines[*].line_id -> "Line_ID"` (or `"lineId"`) in E1 and C1 [LETTER] | break / clean | 0.817 / 0.860 [E1.lines, E1.n_omit(PEN), C1.match, C1.exceptions on break] | Keys are matched case-sensitively; everything is "omitted". |
| C2a | `E1`: totals nested `E1.totals = {admin_total_assets, ...}` (or un-prefixed `total_net_assets`/`shares_outstanding`/`nav_per_share`, nested or flat) [LETTER] | both | 0.979 [E1.totals] | Same totals, one level down. |
| C2b | `E1.admin_lines` / `admin_liabilities` as `{line_id: number}` or `{line_id: {market_value}}` maps (0.936: E1.lines=0 and `E1.n_omit(PEN)`); ledger rows carrying `value` instead of `market_value` (0.957); liability rows carrying `market_value` / `value` instead of `amount` (0.984); liabilities appended to `admin_lines` (0.984) [LETTER] | both | as listed | Same lines read correctly. |
| C2c | `E1.stale_flags "SWAP-B"` (a bare string, not a list) 0.979; `["SWAP-B (STALE_PRICE)"]` 0.979; `[" SWAP-B"]` 0.979; clean: `["none"]`, `"none"`, `["N/A"]` 0.979 [E1.stale] | break / clean | as listed | The flag is captured (or correctly none). A string is iterated per character. |
| C2d | `E1.citation`: `document "package" -> "Package"` / `"PACKAGE"` / `"the package"` / `"NAV package"` / `"NAV-GRSL-20260623-PRELIM"` / `"administrator package"` / `"pricing exceptions report"` [LETTER]; shorter exact verbatims: `"prior business day (2026-06-22) value carried forward"`, `"line_id=SWAP-B  flag=STALE_PRICE"`, `"line_id=SWAP-B  price_date=2026-06-22  price_source=prior business day value carried forward"`, `"nav_per_share=51.2412"`, `"total_net_assets=...  nav_per_share=..."` [CLEAR]; clean: `{"verbatim":"PRICING EXCEPTIONS REPORT:\n  (none)"}` or `"(none)"` [CLEAR]; citation as a list of objects, or text under `quote`, or locator/verbatim swapped [LETTER] | both | 0.986 each [E1.cite] | Exact substrings of the package that entail the reading. The token Jaccard must be >= 0.5 against a gold string of 5 to about 27 tokens; on the clean case the empty exceptions report (the best evidence for "no stale flags") is not in the gold alternates; `_cite_overlap` also requires `document == "package"` case-sensitively. |
| C3a | `E2.swap_statements[*].id -> "line_id"` / `"swap_id"` / `"statement_id"` / `"trade_ref"`, or the list as `{id: {...}}` [LETTER]; `financing_accrued_payable` negative [ARGUABLE] | both | 0.946 [E2.swaps] | Same five fields per statement. |
| C3b | `E2.prices` as `[{"ticker":"SMH","price":250.0},{"id":"TB-0925","price":99.8}]` (or `close`), nested `{"SMH":{"close":250.0,...}}`, key `"TB0925"` or `"TB-0925 (T-bill)"`; T-bill as `0.998` [ARGUABLE] | both | 0.973 [E2.market] | Same market inputs. (`{"SMH":{"value":250.0}}`, lower-case keys, `"99.80%"` pass.) |
| C3c | Percent fields as fractions (`reprocessing_pct 0.005` is 1A/A3): `E2.index.return_pct 0.02` 0.973 [E2.market]; `C3.nav_error_pct -0.014426` 0.944 on break [C3.error]; `C3.expected_move_pct 0.04` / `admin_move_pct 0.024824` / `admin_deviation_pp -0.015176` 0.962 each [C3.expected]; all pct fields together 0.695 (break) / 0.752 (clean) with GATE.REGIME. [LETTER: schema says plain numbers] | both | as listed | Right values, wrong unit label; the scale gate does not check pct fields, but the field atoms fail. |
| C3d | `nav_error_per_share`/`fund_level_error`/`nav_error_pct` as positive magnitudes with direction "understated" (0.944 [C3.error]; D1 copy 0.964 [D1.localize]); `admin_deviation_pp +1.5176` 0.962 [C3.expected] [ARGUABLE: the prompt defines "administrator minus recomputed"] | break | as listed | A desk reads magnitude plus direction as the same finding. |
| C3e | `C3.direction` phrases: break `"NAV understated"`, `"the NAV is understated"`, `"Administrator NAV understated"`, `"lower"`, `"negative"`, `"admin < recomputed"`, `"-"`; clean `"No error found"`, `"none (ties)"`, `"None - NAV ties"`, `"no error (ties)"`, `"match"`, `"tie"`, `"in line"`, `"balanced"`, `"neither"`, `"equal"` [LETTER] | break / clean | 0.962 [C3.direction] | `_norm_direction` needs the word to START with UNDER/OVER or equal an exact token; "understated" anywhere else is lost. (`"Understated"`, `"under"`, `"understatement"`, `"underestimated"`, `"low"`, `"too low"`, `"below"`, `"None"`, `"ties"`, `"tied"`, `"n/a"` pass.) |
| C3f | Booleans (`exceeds_per_share_floor`, `exceeds_reprocessing_pct`, `reasonableness_flag`, `D1.reprocessing_required`): **integer `0` and float `0.0` as false**, float `1.0`, `"T"`, `"F"`, sentences (`"Yes - 0.75 > 0.01"`, `"true (0.75 >= 0.01)"`, `"No - 0.00 < 0.01"`, `"false (0 < 0.01)"`), `"exceeded"`, `"not exceeded"`, `"N/A"`; `reprocessing_required` also `"not required"`, `"N/A"`, `null`, `"No - pre-release hold, nothing transacted"`. [CLEAR for int 0] | clean (false forms) / break (true forms) | 0.972 [C3.thresholds] / 0.962 [C3.expected] / 0.964 [D1.classify] | `_bool` does `str(v or "")`, so `0` and `0.0` become "" -> None, while `1` works ("1"): the 1/0 pair is not symmetric (`nav_oversight.py:48`). `[clean] C3bool:exceeds_per_share_floor false=int 0: FAIL 0.972 ap=0 [C3.thresholds=0.0]` |
| C4a | `D1.classification`: break `"significant"`, `"high"`, `"breach"`, `"a material error"`, `"error is material"`; clean `"No break"`, `"none (NAV ties)"`, `"no material error"`, `"N/A - ties"`, `"no error - ties"`, `"not material"`, `"immaterial"` [LETTER; last two ARGUABLE] | break / clean | 0.964 [D1.classify] | `_norm_class` is startswith MATERIAL / IMMATERIAL or an exact "none" token. |
| C4b | `D1.offending_line "SWAP-B" -> "SWAP-B (Westbrook)"` / `"Line SWAP-B"` / `"SWAP-B total return swap"` / `"SWAP-B line"` / `{"line_id":"SWAP-B"}`; clean `"No offending line"` / `"None - all lines tie"` / `"none identified"` / `"not applicable"` [CLEAR] | break / clean | 0.964 [D1.localize] | The line is named; `_norm(...) == _norm(gold)` is an exact letters-only match. |
| C4c | clean: `D1.nav_error_per_share null` 0.947 [D1.localize, D1.record] / `"none"` 0.964; `D1.corrected_nav_per_share null` ("no correction") 0.947 [D1.localize, D1.record]; break: `D1.escalate_to null` 0.982 [D1.record] [ARGUABLE] | clean / break | as listed | On a RELEASE the NAV that stands is the "corrected" NAV; the schema never says to restate it. |
| C5 | `P1.fund` lower-case / `" (GRSL)"` appended / `"2X"` / double space; `P1.package_id` lower-case [LETTER] | both | 0.982 [P1.1] | Same fund and package. |
| C6 | `P1.leverage "2x"` / `"2.0x"` / `"2X"` / `200` / `"200%"` / `"2:1"`; `prior_shares_outstanding "4.0M"` / `"4 million"` / `"4,000,000 shares"`; `prior_nav_per_share "USD 50"` / `"50.0000 USD"` / `"$50/share"` [LETTER] | both | 0.977 [P1.3] | Same inputs; `_num` fails closed on any unit token. |
| C7 | Numbers with a typographic minus (`"\u22120.75"`), accounting parentheses (`"(0.75)"`), a `" USD"` suffix on negatives, applied to all negative C3/D1/twin fields [LETTER] | break / clean | 0.770 / 0.962 [break: C3.error, C3.expected, D1.localize, D2.twin] | Right numbers as strings. |
| C8 | `C2` numbers as `{"amount": x}` objects 0.891 [C2.totals, C2.tna, C2.nav] (`{"value": x}` passes); `C2.nav_per_share 51.99` 0.961 [C2.nav] [ARGUABLE]; values rounded to whole dollars 0.962 [E1.lines 0.75, E2.swaps 0.5] [ARGUABLE] | both | as listed | Same recomputation. |

### 1D. The grader raises (no score at all)

`run_case` is called without a guard in `outputs/run_live_eval7.py`; the answer is saved, no `report.txt`/`run.json` is
written and the grid logs `FAILED rc=1`. Eight form tests raise, all with a right answer in an unusual container
(`--fuzz` finds 61 raising path/replacement pairs):

| Form change | Raises | Plausibility |
|---|---|---|
| `D2.probe.derivation` as a list of steps (`["...", "...", "..."]`) or an object | `AttributeError: 'list' object has no attribute 'strip'` (`:472`) | high: the field is called "derivation" |
| `D2.probe` as a plain string `"NOT_DISCLOSED: the official closing market price is not in the accounting package"` | `AttributeError: 'str' object has no attribute 'get'` (`:470`) | medium (small models) |
| `E1.citation.verbatim` as a list of quotes (fuzz) | `AttributeError ... 'lower'` (`graders.py:67`) | medium |
| `E2.index` or `E2.capital_stock` as a list | `AttributeError: 'list' object has no attribute 'get'` (`:280`, `:286`) | low |
| `P1`, `D1` or `D2` as a one-element list | `AttributeError ... 'get'` | low |

## 2. Attacks that FAILED (the grader held) - evidence of what is handled

- **Number formats (all PASS on both cases):** every number a string with thousands separators; `$` on dollar fields; `%` on
  percent fields; all three together; every number a plain numeric string (`"51.9912"`); integers as floats; integer-valued
  floats as ints; every number a float. `{"value": x, "unit": "USD"}` wrappers on C2 numbers and on the twin value. `"99.80%"`
  for the T-bill. NAV `51.99117`, `51.991172`, truncated `51.9911`; `nav_error_pct -1.443`; moves to 2 dp; unrounded
  corrected NAV; `"$51.9912"`; twin `"-0.7500"`, `"-$0.75"`, `+0.75`, `-0.7499`, `-0.75003`, `{"value":..., "unit":...}`.
  `reprocessing_pct` as `"0.5%"`, `"0.50 %"`, `"0.5"`; floor `"$0.01"`; leverage `"2.0"` or `2`.
- **Case and whitespace:** ticker `"grsl"`; line ids, price keys and swap ids in lower case; `" 2026-06-23 "` with padding;
  statuses `"MATCH"`, `"Match"`, `" match "`, `"STALE"`, `"Stale"`; direction `"Understated"`, `"UNDERSTATED"`,
  `"understated (admin below recomputed)"`, `"under"`, `"understatement"`, `"underestimated"`, `"low"`, `"too low"`,
  `"below"`, `"understated by 0.75"`; clean direction `"None"`, `"no error"`, `"no difference"`, `"ties"`, `"tied"`, `"n/a"`,
  `null`, `"zero"`; classification `"Material"`, `"MATERIAL"`, `"material error"`, `"material - pre-release"`, `"MATERIAL_ERROR"`,
  clean `"None"`, `"no error"`, `"n/a"`, `"clean"`, `null`; decision `"hold"`; `offending_line` `"swap-b"`, `"SWAP B"`, `"SWAP_B"`,
  `"Swap B"`, `["SWAP-B"]`, `"SWAP-B "`; clean `offending_line` `null`, `""`, `"none"`, `"None"`, `"N/A"`, `"-"`, `"null"`, `[]`, `false`;
  label `"NOT DISCLOSED"`, `"not_disclosed"`, `"Not Disclosed"`, `"NOT-DISCLOSED"`, `"NOT_DISCLOSED."`, `"NOTDISCLOSED"`;
  stage `"Pre-release"`, `"PRE_RELEASE"`, `"pre release"`, `"Pre-release review"`, `"prerelease"`, `"preliminary"`, `"pre-publication"`,
  `"pre-dissemination"`, `"pre_release (preliminary NAV)"`; jurisdiction `"us"`.
- **Booleans:** `"true"`, `"True"`, `"TRUE"`, `"yes"`, `"Yes"`, `"Y"`, `"y"`, integer `1`, `"1"`, `"yes "`; `"false"`, `"False"`, `"FALSE"`,
  `"no"`, `"No"`, `"N"`, `"n"`, `"0"`, `"no "` (and the real Qwen 3.6 break answer used `"true"` strings and scored them).
- **Containers and extras:** recon reversed; liabilities first; an extra `TOTALS` recon row; extra fields in recon rows;
  an extra `note` key in every dict at every level; extra top-level keys; extra fields in statements, index, probe, D1, C3;
  extra price keys; a second twin row; `escalate_to` as a list; `offending_reason` as a list; `stale_flags` as objects, as a
  dict, in lower case, duplicated; clean `exceptions: null`; `E1`/`E2` date fields (`price_date`, statement `valuation_date`) in
  `06/23/2026` (not graded); a **minimal answer** that omits every field no atom reads (share_class, benchmark, price_date,
  counterparty, recon values, recomputed_*, reprocessing_note, oversight_band_pp); the **benign stack** (`$`/comma/`%` strings,
  yes/no booleans, upper-case status, lower-case ids and ticker, reversed recon, extra fields, string twin, lower-case
  stale flag) = 1.000 / AllPass on both cases.
- **Citations:** single-spaced, newline-wrapped, quote-wrapped, `"package "` with a trailing space, the `line_id=` token dropped,
  the note sentence alone (18 of 20 tokens), three of the five totals fields.
- **Refusal:** `value` as `""`, `"N/A"`, `"n/a"`, `"null"`, `"unknown"`, `{}`, `[]`, `"-"`, `"none"`; text under `reason`; derivations that follow
  the schema's instruction in the model's own words (`"No exchange trading price is in the accounting package; the missing input is
  GRSL's official closing market price, ..."`), `"is not in the package"`, `"not in the NAV package"`, `"unavailable"`, `"lacks"`,
  `"not provided in the packet"`, `"does not provide"`, `"does not include"`, `"cannot be found"`, `"provides the NAV but no official
  closing market price"`, `"outside the package"`, `"unable to"`, `"not present"`, a secondary-market "quote" absent, "exchange trading
  data outside the scope", and the 12-character window correctly clearing `"is not in the package"`.
- **Whole-answer shapes (grader correct to fail, by contract):** all keys lower-/upper-cased, the answer wrapped under
  `answer`/`review` -> 0.000; `P1.review_stage "post_release"` -> GATE.REGIME (right); twin `0.0` on the break (wrong) -> D2 0.
- **Gates not triggered by decimals:** NAV to 4/5/6 dp, error pct to 3 dp, deviation to 2 dp never trip a gate; the scale gate
  stays quiet unless the ratio is a true scale factor.

## 3. The saved live answers (28 runs; the 5 superseded `prior/` runs checked too)

All 28 re-graded scores equal the saved `report.txt` / `run.json` scores. Form survey (`--survey`): every answer used
`valuation_date "YYYY-MM-DD"`, jurisdiction `US`, stage `pre_release`, decision `HOLD`/`RELEASE`, label `NOT_DISCLOSED`,
`value null`, twin id `TW1`, citation `document "package"` (except Qwen 3.6, which gave `{}`); the only form deviations are the
2B's list-shaped E1/E2/C1 (plus a stray `E3`) and Qwen 3.6's `"true"` boolean strings on the break case (handled and credited).
Opus 4.8, GPT-5.6-sol, GPT-5.5, Gemma 4 31B score 1.000/AllPass on both cases; Gemini and GPT-5.4-mini and GPT-5.4 on the
clean case; Qwen 3.8 27B on the break case.

| Model / case | Score | Below 1.0 (atoms) | Verdict | Reasoning |
|---|---|---|---|---|
| claude-sonnet-4-6 / break | 0.972 | C3 0.824 (C3.thresholds) | genuine | `exceeds_reprocessing_pct false` beside its own `nav_error_pct -1.4426` (>= 0.5). Read as the policy consequence, not the arithmetic test; the schema wording it saw was terse (disclosed in TAXONOMY.md). |
| claude-sonnet-4-6 / clean | 0.957 | C1 0.692 (C1.exceptions) | genuine, borderline | An exception row typed `arithmetic_error` on `TOTALS` whose own text concludes "No break at the line level". A typed error that does not exist is noise; but it is exactly the "informational row" class (C1e). Cost 0.043. |
| claude-haiku-4-5 / break | 0.964 | D1 0.778 (D1.classify) | genuine | `reprocessing_required true` on a pre-release hold; the prompt says false; its `escalate_to` orders reprocessing of transactions at 51.2412 that never happened. |
| claude-haiku-4-5 / clean | 0.986 | E1 0.857 (E1.cite) | genuine | `verbatim "all positions dated 2026-06-23"` is a paraphrase, not in the package. |
| gpt-5.4 / break | 0.972 | C3 0.824 (C3.thresholds) | genuine | same reading as Sonnet (`exceeds_reprocessing_pct false` against -1.4426%). |
| gpt-5.4-mini / break | 0.671 | C2 0.222, C3 0.471, D1 0.778, D2 0.000 | genuine | total assets 207,010,600 (should be 209,010,600), NAV 51.4912, error -0.25, `fund_level_error +1,000,000` beside "understated", twin -0.25. Arithmetic, not form. |
| gemini-3.6-flash / break | 0.956 | D2 0.556 (D2.reason) | genuine | the derivation is the SCHEMA's instruction text verbatim ("state that no exchange trading price is in the accounting package and name that missing input ..."). |
| qwen2.5-32b / break | 0.558 | E1 0.857 (E1.cite); C1 0.692 (`C1.n_stale_blind` present); C2 0.222; C3 0.235; D1 0.667; D2 0.000 | mostly genuine; **E1.cite believed FALSE POSITIVE (borderline)** | C2 copies the administrator's 51.2412 back (genuine stale-blind penalty); direction "none"; twin -0.0048; echoed refusal. But its `E1.citation.verbatim "line_id=SWAP-B  flag=STALE_PRICE"` is an exact substring of the exceptions-report line and entails the stale-flag reading; Jaccard is 2/20 = 0.10. Cost 0.014. |
| qwen2.5-32b / clean | 0.941 | E1 0.857 (E1.cite); D2 0.556 | genuine | citation text is only the package id `NAV-GRSL-20260623-PRELIM` (entails nothing); echoed refusal. |
| qwen3.6-35b-a3b / break | 0.968 | E1 0.857 (E1.cite `{}`); D1 0.889 (D1.record) | genuine | no citation at all; a HOLD with `escalate_to null` is not an actionable record. |
| qwen3.6-35b-a3b / clean | 0.932 | E1 0.857 (E1.cite `{}`); D1 0.667 (D1.localize, D1.record) | E1 genuine; **D1 ARGUABLE false positive** | `corrected_nav_per_share null` on a RELEASE ("no correction"); decision, classification, error 0.0 and reprocessing are all right. The schema never says to restate the NAV on a release, though it says "null only where you genuinely cannot determine a value". Cost 0.053 (6/18 of D1). Same as form test C4c. |
| qwen3.8-27b / clean | 0.986 | E1 0.857 (E1.cite) | **believed FALSE POSITIVE (borderline, thin)** | `verbatim "nav_per_share=51.9912"`: an exact field of the totals block that supports the NAV reading, but 1 of 5 fields (Jaccard 0.20 against the 0.5 bar). Cost 0.014. |
| qwen3.8-2b / break and clean | 0.131 / 0.212 | nearly everything | genuine (shape breach plus content errors) | E1, E2, C1 emitted as bare lists with a stray `E3` key (contract: "EXACTLY these keys"). Counterfactual (`--twob`, containers re-shaped, no value touched): break 0.131 -> 0.273 (GATE.SIGN still fires: direction "overstated", total assets 317,010,600), clean 0.212 -> 0.390. So about 0.14 and 0.18 of its deficit is container shape; the rest is wrong arithmetic. |

**Prior (superseded) runs:** Haiku break smoke run 0.972 (recon only five ledger lines, C1.match 0.625: the schema of that
day never asked for the liability rows, since fixed); Gemini break 0.428 and Qwen 27B clean 0.339 (cut off by a token
budget; TAXONOMY.md calibration item 3 and its open-weight section); 2B priors 0.371 / 0.174. None is a grader false positive.

**False positives I would stand behind among the saved answers (all open-weight, all small):** (1) Qwen 2.5 break E1.cite
(entailing two-field verbatim), (2) Qwen 3.8 27B clean E1.cite (single-field verbatim, thin), (3) Qwen 3.6 clean D1
(null corrected NAV on a RELEASE). Combined effect on any headline: 0.014, 0.014, 0.053. **No paid-frontier miss is a false
positive**, and no gate fired in a live run, so the "9 of 16 AllPass" and "no gate fired" statements are not affected.

## 4. Pattern

The grader is robust to the cosmetic variations people expect (case, whitespace, `$` `,` `%`, int/float, string
booleans, extra fields, row order) and fragile wherever it needs semantics: dates, regime tokens, ids, label tokens, statuses,
the twin id and the refusal wording are all exact-string or word-list matches, and the decision classifier works on
space-stripped letters with substring roots (THRESHOLD/SHAREHOLDER contain HOLD, CORRECTLY contains CORRECT, any "NOT"
plus "RELEASE" is a hold, FINAL/PASS are release roots), so natural phrasing flips in both directions. The damage is
out of proportion because hard and scoped gates ride on those exact-string atoms: a time part on a date costs 0.63 of the
score (0.371), "USA" costs 0.18 (0.817), and "Delay the release" fires the signature GATE.RELEASE and its headline flag on a
model that held the NAV. Real runs have not hit these (all 28 saved answers copied the schema's words), so the
leaderboard is unaffected, but the hazards are one prompt change, one model family or one answer-shape slip away; the
`derivation` as a list and `probe` as a string also crash the grader instead of scoring.

Fix directions (for whoever owns the grader): parse dates with `datetime`/`dateutil` before comparing; compare regime
fields on a normalised token set (country aliases, unit-stripped numbers, a stage synonym map) and require the stage word to
be in an allow-list; canonicalise twin ids (strip, upper, alphanumerics only) and accept dict-shaped twins; classify
decisions on word tokens with negation scope (not substrings) and drop the catch-all `NOT`+`RELEASE` rule; make `_bool(0)`
return False; widen the exception/refusal word lists or grade those free-text atoms with an LLM judge (the harness has a
`--judge llm` path; this suite leaves `LLM_JUDGE_CPS` empty); and wrap each atom in a guard that turns a mis-typed section
into a failed atom, not a raised exception.

## 5. Also noticed (outside my surface; each reproduced by `--other`)

- **Schema placeholders earn credit:** `C3.direction = "understated|overstated|none"` scores 1.000/AllPass on the break
  (startswith UNDER); `D1.classification = "material|immaterial|none"` scores 1.000 on the break; `D1.escalate_to = []`,
  `{}` or `0`, and `D1.offending_reason = "STALE_PRICE"` (a flag label, no reason) all satisfy `D1.record`; any stage word that
  starts with PRE (`"PREMATURE"`) passes P1.4 (`"post_release"` correctly fires GATE.REGIME).
- `_num` strips every comma: `_num("51,2412") = 512412.0` (European decimal comma silently becomes a 10,000x error),
  `_num("4.000.000") = None`; `_by_id` does not strip, so `" SWAP-B"` is a different id from `"SWAP-B"`.
- The 2B's score mixes container shape with content (section 3 counterfactual).

## Appendix A - decision phrases the classifier misreads (complete lists; `--decisions`)

Natural HOLD phrases on the break case (gold HOLD), 48 of 105 misread:
- read as RELEASE, GATE.RELEASE fires, 0.840 (24): Release withheld; Release deferred; Release delayed until SWAP-B is re-struck; Release postponed;
  Release paused; Release halted; Release denied; Release refused; Release held; Do not finalize the NAV; Do not finalise; NAV is not final;
  NAV cannot be finalized; Refuse release; Release: NO; Release? No; Do not pass; Not passed; NAV does not pass oversight; Delay the release;
  Delay release; Postpone the release; Pause release; Release must wait.
- read as ambiguous, D1 zeroed, 0.840 (10): Not approved for release; Release withheld pending correction of SWAP-B; Release blocked; Release blocked
  pending correction; Release on hold; Release suspended; Release stopped; Release rejected; Not cleared for release; Do not proceed with release.
- unclassified, D1.decision only, 0.929 (14): Held; NAV held; No-go; No go; Withheld; Do not distribute the NAV; Not releasable; Not yet; Withdraw the NAV;
  Recall; Pull the NAV; Defer release; Wait; Red light.

Natural RELEASE phrases on the clean case (gold RELEASE), 28 of 115 misread:
- read as HOLD, `D1.n_falsehold`, 0.840 (9): Release - difference below the threshold; Release; escalation not required; Release - the NAV ties and is not in
  error; Pass - below threshold; Passed - within threshold; Cleared; no shareholder impact; NAV is final; within the 0.01 threshold; Release - nothing
  outstanding; Release - nothing to fix.
- read as ambiguous, D1 zeroed, 0.840 (11): Release - the NAV is correct; Release; all figures verified correct; Release - no shareholder impact; Release;
  within the oversight threshold; Release; no need to investigate; Approved; no shareholder impact; Release - NAV recomputed correctly and ties; Release: the
  administrator NAV is correct; Release - correct as struck; Release; no shareholder reprocessing; Release - no stakeholder impact.
- unclassified, 0.929 (8): OK; ok; Yes; Go; Confirmed; Send the NAV; Send it out; Strike the NAV.

Decision + short rationale (`--rationale`), 6 of 29 misread: HOLD - NAV does not tie: SWAP-B stale; release blocked until re-struck (ambiguous);
HOLD - error of 0.75/share exceeds the 0.01 floor; release not allowed (ambiguous); RELEASE - NAV ties; no shareholder impact (ambiguous);
RELEASE - package ties; reprocessing not required (FALSE HOLD); RELEASE - correct NAV (ambiguous); RELEASE - NAV is within the oversight threshold (ambiguous).

## Appendix B - the headline findings with the brief's own recipe (`--recipe`)

`m = nv.oracle(load_case(case)); <mutate m>; result, rubric = run_case(case, model_output=m)`; printed
`case_gated allpass fired_gates flags e6`:

```
control: unmodified oracle (break)                       case_gated=1.0    allpass=1 fired_gates=[]               flags=[]                        e6=(1.0, 1.0)
A1 P1 dates "...T00:00:00" (break)                       case_gated=0.3706 allpass=0 fired_gates=['GATE.DATE']    flags=[]                        e6=(1.0, 1.0)   P1 0.706, C1 C2 C3 D1 = 0
A2 jurisdiction "USA" (clean)                            case_gated=0.8165 allpass=0 fired_gates=['GATE.REGIME']  flags=[]                        e6=(1.0, 1.0)   P1 0.765, D1 = 0
A4 decision "Delay the release" (break)                  case_gated=0.84   allpass=0 fired_gates=['GATE.RELEASE'] flags=['release_override_fired'] e6=(1.0, 1.0)   D1 = 0
A4 decision "Do not finalize the NAV" (break)            case_gated=0.84   allpass=0 fired_gates=['GATE.RELEASE'] flags=['release_override_fired'] e6=(1.0, 1.0)   D1 = 0
B2 decision "RELEASE - package ties; reprocessing not required" (clean)
                                                         case_gated=0.84   allpass=0 fired_gates=[]               flags=[]                        e6=(1.0, 1.0)   D1 = 0 (n_falsehold)
B4 twin id "tw1" (break)                                 case_gated=0.9    allpass=0 fired_gates=[]               flags=[]                        e6=(0.0, 1.0)   D2 = 0
B6a derivation "The administrator NAV is in the package, but no exchange trading price is: ..." (break)
                                                         case_gated=0.9294 allpass=0 fired_gates=[]               flags=[]                        e6=(1.0, 0.25)  D2 = 0.294
C3f exceeds_per_share_floor = 0 (int) (clean)            case_gated=0.9718 allpass=0 fired_gates=[]               flags=[]                        e6=(1.0, 1.0)   C3 0.824
1D D2.probe.derivation as a list (break)                 AttributeError: 'list' object has no attribute 'strip'   (nav_oversight.py:472, via harness/__init__.py:42 run_case)
```

## Appendix C - reproduce

```
cd C:\Projects\finance-llm-evals
PY="$USERPROFILE/miniconda3/envs/tieoutbench/python.exe"
$PY outputs/eval7-live/gaming-review/scratch_attacker6.py --baseline            # both 1.000 / AllPass
$PY outputs/eval7-live/gaming-review/scratch_attacker6.py                       # the whole battery + summary (598 tests, 907 runs)
$PY outputs/eval7-live/gaming-review/scratch_attacker6.py --group P1date --verbose   # one group; --list shows the groups
$PY outputs/eval7-live/gaming-review/scratch_attacker6.py --decisions           # 105 hold + 115 release phrasings, end to end
$PY outputs/eval7-live/gaming-review/scratch_attacker6.py --rationale           # decision + rationale strings
$PY outputs/eval7-live/gaming-review/scratch_attacker6.py --saved [--only qwen] [--prior]   # saved live answers, failed atoms with values
$PY outputs/eval7-live/gaming-review/scratch_attacker6.py --recipe             # headline findings via the brief's own recipe (last one raises)
$PY outputs/eval7-live/gaming-review/scratch_attacker6.py --twob --survey --fuzz --other
```

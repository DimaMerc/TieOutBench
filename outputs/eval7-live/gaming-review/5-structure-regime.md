# Attacker 5 - planning, regime and structure atoms of eval #7

Surface: `P1.1`-`P1.5` (the date pin `P1.2` / GATE.DATE and the regime pin `P1.4` / GATE.REGIME), `C1.structure`,
`D1.classify`, `D1.localize`, `D1.record`, and the helpers `_norm_class`, `_norm_stage`, `_bool` in
`harness/suites/nav_oversight.py`. Scratch script: `outputs/eval7-live/gaming-review/scratch_attacker5.py`
(sections S0-S20; `S17` re-runs every finding below, `S19` / `S20` are the fail-closed and hollow-shell checks).
Run: `python -I outputs/eval7-live/gaming-review/scratch_attacker5.py S17` with the project interpreter from the repo
root.

Method. Base answer = `oracle_to_schema(case)` (the live SCHEMA shape, dates as strings; it scores 1.0000 / AllPass
on both cases, same as the raw oracle). Every attack is a dict patch of that answer, run on BOTH cases, and every
line was cross-checked against `run_case(case_path, model_output=...)`. "Before" is the perfect answer unless the row
names another reference. Nothing in the repo was edited.

Weights, to read the deltas. Share of the case score: P1.1 .0176, P1.2 .0294, P1.3 .0235, P1.4 .0235, P1.5 .0059,
C1.structure .0215, D1.decision .0711, D1.classify .0356, D1.localize .0356, D1.record .0178. GATE.DATE zeroes
C1+C2+C3+D1 (0.60 of the weight); GATE.REGIME zeroes D1 (0.16). A date slip therefore costs 1.0000 -> 0.3706 and a
regime slip 1.0000 -> 0.8165.

Calibration against the 16 saved live runs (read-only): every model wrote the canonical forms (ISO dates,
jurisdiction "US", `pre_release`, floor 0.01, pct 0.5), so none of the format false positives F1/F2 has fired live.
Two did occur live: F6 (Qwen3.6-35B-A3B, clean case, corrected NAV null: 0.9324) and X1 (Claude Haiku 4.5, break
case, post-release reprocessing applied to a pre-release package: 0.9644, no gate). Qwen3.8-2B returned E1, E2 and C1
as lists, so non-dict sections (X8) are a real output shape.

---

## 1. Exploits: a wrong, empty or contradictory answer is credited

| ID | Sev | Mutation (exact patch) | Case | Before -> after | Gates / flags | Why unfair |
|---|---|---|---|---|---|---|
| X1 | High | `{"D1":{"classification":"material under CSSF Circular 24/856 (1% equity threshold); notify the CSSF within four to eight weeks","escalate_to":"notify the CSSF within four to eight weeks of detection; auditor special report"}}` with P1.regime left correct (US / 0.01 / 0.5 / pre_release). Before = the same D1 text with P1.regime = LU (the shipped `regime_slip` variant scores the same 0.8165, GATE.REGIME). | break | 0.8165 -> **1.0000 AllPass** | none (before: GATE.REGIME) | GATE.REGIME's stated condition is "a foreign threshold set applied, or the review stage misread", but the hook compares only the labels typed in P1; the identical wrong analysis is gated when P1 says LU and perfect when P1 says US. `D1.classify` reads only the prefix "material" and the reprocessing flag. Live instance: Haiku 4.5 break wrote `reprocessing_required: true` and escalate_to "reprocess all transactions executed at the preliminary NAV of 51.2412" (nothing was transacted at that NAV) with P1.review_stage `pre_release`: 0.9644, no gate. With that same D1 and `{"P1":{"review_stage":"post_release"}}`: 0.8165 + GATE.REGIME (S17 EX3, second line). |
| X2 | High | `{"D1":{"offending_reason":"the NAV is correct; nothing to report","escalate_to":"release the NAV at 51.2412 immediately; no action needed"}}` (decision stays HOLD) | break | 1.0000 -> **1.0000 AllPass** | none | The free text of the D1 record is never graded: a HOLD whose own reason says there is no break and whose escalation tells the administrator to publish the stale NAV scores the same as the perfect answer. Also AllPass: reason naming the wrong line/mechanism (`"SWAP-A was priced from the wrong counterparty"`), `reprocessing_note` "reprocess all shareholder transactions", wrong `P1.share_class` / `P1.benchmark` (S18). |
| X3 | Med-High | `{"D1":{"offending_reason":"n/a","escalate_to":"n/a"}}` (also `" "`, `[]`, `0`). Reference = the same two fields null. | break | 0.9822 -> **1.0000 AllPass** | none | `D1.record` is `value not in (None, "")`: "n/a", " ", [], {}, 0, False all count as an emitted record. Further: `{"D1":{"offending_line":"TBD","offending_reason":"TBD","nav_error_per_share":"TBD","corrected_nav_per_share":"TBD","escalate_to":"TBD"}}` vs the same fields null: 0.9467 -> 0.9644 (both cases; D1.localize correctly stays lost). `{"D1":{"decision":"n/a"}}` (also "TBD", " ", [], 0, "x") loses D1.decision (0.9289) but KEEPS D1.record: a "structured decision record" whose decision is not a decision. On the clean case record needs only decision + corrected NAV + error not None, so "n/a" is accepted there too. |
| X4 | Med | `{"P1":{"review_stage":"previously released"}}` (also "previously published", "pre_release; treat as post_release", "pre-release or post-release", "preliminary NAV, post-release review"). Reference: `"post_release"`. | both | 0.8165 -> **1.0000 AllPass** | none (before: GATE.REGIME) | `_norm_stage` = letters-only upper-case `startswith("PRE")`. "previously released" is literally the post-release state and is credited as `pre_release`; hedged strings pass. |
| X5 | Med | `{"D1":{"classification":"Materiality: immaterial"}}` (also "Material? No.", "materially immaterial", "material or immaterial - cannot determine"). Reference: `"immaterial"`. | break | 0.9644 -> **1.0000 AllPass** | none | `_norm_class` = `startswith("MATERIAL")`: the first word decides, the opposite verdict and any hedge after it are ignored. (On the clean case these fail, control.) Converse: on the clean case a null / empty / missing classification maps to "none" and earns AllPass. |
| X6 | Low | `{"C1":{"recon":[{"x":1},{"y":2}]}}` (also `["a","b"]`, `[null,null]`, `[1,2]`, `[[],[]]`). Reference: `recon = []`. | both | 0.9031 -> 0.9246 | none | `C1.structure` is `isinstance(list) and len >= 2`: two elements of anything earn +0.0215; no admin / independent value or status is required (criterion text says per-line rows with those). |
| X6b | Low | `{"P1":{"regime":{"jurisdiction":null}}}` (also `regime` = 0, [], false, " ", "n/a"). Reference: `regime = {}`. | both | 0.8106 -> 0.8165 | GATE.REGIME fires both ways | `P1.5` is `value not in (None, "", {})`: an all-null shell, 0, [] or " " is a "pinned-package object" (+0.0059). Only the empty dict `{}` is rejected. |
| X7 | Low | `{"P1":{"regime":{"oversight_band_pp":99}}}` (also null, missing); `{"P1":{"regime":{"per_share_floor_usd":0.011}}}` | both | 1.0000 -> 1.0000 AllPass | none | The band the SCHEMA asks for is never graded (P1.4 lists four fields by spec). Floor tolerance `usd_mils` is abs 0.001 = +/-10% of the 0.01 floor (0.009-0.011 pass); reprocessing_pct passes 0.49-0.51. |
| X8 | Med | `{"P1":"see above"}`, `{"P1":[]}`, `{"D1":"HOLD"}`, `{"D1":[]}`, `{"D2":"NOT_DISCLOSED"}`, `{"D2":{"probe":"NOT_DISCLOSED"}}`, `{"E2":{"index":"x"}}`, `{"E2":{"capital_stock":"x"}}` | both | perfect answer -> **no score (exception)** | `AttributeError: 'str' object has no attribute 'get'` out of `run_case` | A non-dict section crashes the grader instead of scoring ~0 (`P1m = _g(...)`, `D1m = _g(...)`, `refusal()`, E2.index / E2.capital_stock take `.get` on whatever is there; `None` is safe). `outputs/run_live_eval7.py` has no try/except around `run_case`: the run exits rc=1 after saving answer.json, no report.txt / run.json; the grid logs FAILED; `eval7_matrix.py` skips cells without report.txt, so the worst answers vanish from the matrix. Qwen3.8-2B already returned E1/E2/C1 as lists (guarded, graded 0), so a list or string P1/D1/D2 is one step away. |

---

## 2. False positives: a right answer in a legitimate format is gated or marked down

| ID | Sev | Mutation (exact patch) | Case | Before -> after | Gates / flags | Why unfair |
|---|---|---|---|---|---|---|
| F1 | High | `{"P1":{"valuation_date":"2026-06-23T00:00:00"}}`; same for "23 June 2026", "06/23/2026", "2026-06-23T00:00:00Z", "2026/06/23", "20260623", "2026-6-23", "2026-06-23 (Tuesday)"; `{"P1":{"prior_valuation_date":null}}` or key missing | both | 1.0000 -> **0.3706** | **GATE.DATE** (hard) | The correct date, in another notation, scores exactly what the worst cascade (`date_slip` 0.371) scores: P1.2 is `str == str` and its gate zeroes C1, C2, C3 and D1 (60% of the weight). It also fires on the ABSENCE of `prior_valuation_date` while the valuation date is right; GATE.SCALE was deliberately made evidence-only. (Whitespace padding passes; missing P1 entirely: 0.3000, GATE.DATE + GATE.REGIME.) |
| F2 | High | `{"P1":{"regime":{"jurisdiction":"USA"}}}` (also "United States", "U.S.", "U.S.A.", "United States of America", "US (SEC)"); `{"P1":{"regime":{"reprocessing_pct":"0.5 percent"}}}` (also 0.005, "0.5% of NAV", "50 bps", "0.5pct"); `{"P1":{"regime":{"per_share_floor_usd":"$0.01 per share"}}}` (also "0.01 USD", "USD 0.01", "1 cent"); `{"P1":{"review_stage":"before release"}}` (also "prior to release", "not yet released", "pending oversight release", "unreleased") | both | 1.0000 -> **0.8165** | **GATE.REGIME** | The SCHEMA gives no vocabulary for jurisdiction (`"jurisdiction":""`); the gate then zeroes D1 including the correct HOLD / RELEASE call for a spelling of the right regime. (Pass: "us", " US ", "$0.01", "0.5%", "preliminary", "pre release", "pre-release review".) |
| F3 | Med | `{"D1":{"reprocessing_required":0}}` (also 0.0, "N/A", "not required", "none", null, "no - pre-release", "False (pre-release)"). Clean case, C3: `{"C3":{"exceeds_per_share_floor":0}}`, `{"C3":{"reasonableness_flag":0.0}}`; break case `1.0` for the true flags. | both | 1.0000 -> 0.9644 (D1.classify); C3.thresholds 0.9718; C3.expected 0.9624 | none | `_bool` does `str(v or "")`, so integer / float 0 becomes "" -> None while the string "0" is False; `1` is True but `1.0` is None. A JSON `0` for a boolean is common. |
| F4 | Med | Clean: `{"D1":{"classification":"no material error"}}` (also "not a material error", "no exception", "no break", "within tolerance", "ties out"). Break: "significant", "major", "above floor". | clean / break | 1.0000 -> 0.9644 | none | `_norm_class` only knows a short list ("none", "no error", "clean", "ties", "n/a", "nil", "not applicable") and the prefixes MATERIAL / IMMATERIAL / NOTMATERIAL / BELOW; "no material error" normalises to the unknown token `nomaterialerror`. |
| F5 | Med | Break: `{"D1":{"offending_line":"SWAP-B (Westbrook)"}}` (also "Line SWAP-B", "the SWAP-B line", "Westbrook swap", "WCM-2026-05118"); `{"D1":{"nav_error_per_share":0.75}}` (magnitude; also "(0.75)", "−0.75" U+2212, "-0.75 USD", "-0.75 per share"); `{"D1":{"corrected_nav_per_share":"USD 51.9912"}}` (also "51.9912 per share", 51.99). Clean: `{"D1":{"offending_line":"No offending line"}}` (also "nil", "not applicable", "none identified"). | break / clean | 1.0000 -> 0.9644 | none | D1.localize compares letters-only strings (so one extra word breaks it) and `_num` rejects any unit text, accounting parentheses or a Unicode minus. The sign of the per-share error is demanded although the direction field already carries it. |
| F6 | Med | `{"D1":{"corrected_nav_per_share":null}}` (with RELEASE, error 0.0, offending_line null) | clean | 1.0000 -> 0.9467 | none | "No correction needed" is a natural null on a package that ties; the grader wants the NAV that stands (51.9912) and drops D1.localize + D1.record (-0.0533, AllPass lost). LIVE: Qwen3.6-35B-A3B wrote exactly this on the clean case (0.9324). |
| F7 | Low | `{"P1":{"fund":"Granite Ridge 2X Daily U.S. Semiconductor ETF"}}` (also "...US...", "... (GRSL)", lower-case, trailing period); `{"P1":{"package_id":"nav-grsl-20260623-prelim"}}`; `{"P1":{"leverage":"2x"}}` (also "2.0x", "2.0 x", "200%"); `{"P1":{"prior_shares_outstanding":"4M"}}`; `{"P1":{"admin_prelim_nav_per_share":"51.2412 USD"}}` | both | 1.0000 -> 0.9824 (P1.1) / 0.9765 (P1.3) | none | Fund name and package id are case-sensitive exact matches while the ticker is case-insensitive; any unit text defeats `_num`. Leverage "2x" is how a desk writes it. |

---

## 3. Also noticed (outside my surface; reproduced)

All on the decision classifier, but they hit my three D1 atoms through the ambiguity guard.

- A correct hold phrased naturally trips the signature gate: `{"D1":{"decision":"Release withheld"}}` (also "Release postponed", "release denied"), break: 0.8400, **GATE.RELEASE + release_override_fired**. WITHHELD / POSTPONED / DENIED are not hold roots, RELEASE is.
- A correct hold read as ambiguous zeroes D1.decision, D1.classify, D1.localize and D1.record: "Release not approved", "NAV not approved for release", "Not cleared for release", "Do not approve release", "Release blocked", "Release suspended", "release rejected": break 0.8400, no gate.
- Unrecognised hold words: "no-go", "Not releasable", "do not issue", "Do not strike", "do not distribute": break 0.9289; on the CLEAN case the false-hold penalty does not fire, so a perma-holder using these words scores 0.9289 against 0.8400 for plain "HOLD".
- Unrecognised release words on the break case: "good to go", "OK", "not held", "all good", "looks good", "fine to strike", "confirmed", "ship it", "send it": 0.9289, no GATE.RELEASE, no flag (against 0.8400 + flag for "RELEASE"). "NAV acceptable" does trip it.
- Absence is credited (S20): with the pins copied and nothing else, the shell earns `C2.scale` (a gate atom is "met" when no figure sits on a scale factor, even with no C2 at all: 4 of 18 C2 points = 0.0311 of the case) and, on the clean case, `C1.exceptions` (empty set, 0.0431) and `C3.direction` (a missing direction equals "none", 0.0376). Those free points, plus the junk-fillable structure atoms of section 1, are why the hollow shell reaches 0.2771 (break) / 0.2334 (clean).
- `_norm` drops digits, so "SWAP-B2" == "SWAP-B" and "TB-0925" == "TB-1225" == "TB" (D1.localize on the break: "SWAP-B2" still 1.0000 AllPass). Not exploitable on these two cases (one T-bill line), latent for any case with two lines that differ only in digits.
- Decision classifier speed is fine on degenerate 100k-character strings (0.01 s); no ReDoS.

---

## 4. Failed attacks (the grader held)

- P1.1: wrong fund ("3x"), wrong package id (20260622), "$GRSL", "NYSE: GRSL", missing fund -> P1.1 = 0. Padded strings and lower-case ticker pass (fair).
- P1.2 / GATE.DATE: swapped dates, prior = Friday 2026-06-19, missing valuation date, `P1 = {}`, `P1 = null` -> GATE.DATE fires (P1 null / {} also fires GATE.REGIME, 0.3000). No wrong date string passes: only the exact string does. An extra wrong `package_date` key is ignored (fair).
- P1.4 / GATE.REGIME: `post_release`, "post-release", "Post Release", jurisdiction "LU", floor null / 0 / 0.0089 / 0.0111 / "1", reprocessing_pct 1.0 (CSSF) / 0.52 / 50 / null, regime as a string / list / null, numbers placed at P1 top level, `review_stage` nested inside `regime` -> all fire the gate.
- P1.5: `regime = {}` (the brief's attack) and a missing regime -> P1.5 = 0. (All-null dict, 0, [] pass: see X6b.)
- C1.structure: one row, a dict keyed by line id, a missing or empty recon -> 0.
- D1.localize: wrong line ("SWAP-A"), two lines, a dict, "SWAP-B vs SWAP-A", error -0.7511, stale corrected NAV 51.2412, 51.9915 (outside 0.0002), corrected NAV null / missing / "n/a" -> 0. A missing corrected NAV also fails D1.record (fail-closed).
- D1.classify: reprocessing_required `true` / "yes" / 1 -> 0; classification "immaterial", "not material", "below floor", "none", "clean" on the break -> 0; "material" on the clean case -> 0.
- D1.record: a missing / null / empty decision, offending_line (break), nav_error or corrected NAV -> 0. A contradictory decision (release + hold) is zeroed by the ambiguity guard as designed.
- `_bool`: "no", "false", "N", "0" (string), "False " all read False; "yes", "Y", "1", 1, "true" read True.
- D1.record needs a real value in decision (null, "" or a missing key -> D1.record and D1.decision both 0, 0.9111), in offending_line on the break, and in nav_error / corrected NAV (null or "" -> 0). Missing offending_reason / escalate_to on the break -> 0.9822 (record lost), so the placeholders in X3 are what buy the credit.
- No placeholder-only answer reaches AllPass: the exploits above all need an otherwise perfect answer. A hollow shell (pins copied from the packet header and policy line, two junk recon rows, a HOLD record of "n/a" / "TBD", nothing else) scores 0.2771 on the break and 0.2334 on the clean case (S19/S20), AllPass 0. An empty answer `{}` scores 0.0000 (GATE.DATE + GATE.REGIME). Every live AllPass on the break case carries substantive offending_reason / escalate_to prose.

---

## 5. Pattern

The pin and structure atoms are string-equality or non-emptiness checks on labels the model types, so they fail in
both directions at once: brittle to harmless notation (date with a time part, "USA", "U.S.", integer 0, "no material
error") and blind to content (placeholders, a contradictory escalation, a wrong regime applied in D1, "previously
released" as a stage). The two P1 gates inherit both defects and carry the heaviest blast radius in the suite (GATE.DATE
60% of the weight on a notation; GATE.REGIME 16%), while GATE.REGIME does not measure what its condition states: it reads
the P1 label, never D1's actual treatment. Helpers that normalise by prefix or by `str(v or "")` (`startswith("PRE")`,
`startswith("MATERIAL")`, 0 -> "") cause most of the misses in both directions; none of the format cases fired in the 16
live runs, which used canonical forms, but the Haiku regime-in-D1 case and the Qwen3.6 clean-null case show the
content-blind half is already live.

Fix directions (not applied): normalise dates through `datetime` and make GATE.DATE evidence-only (fire on a parsed wrong
date, not on a missing or oddly formatted one); give jurisdiction a vocabulary or an alias table; replace the prefix
tests with an enumerated map plus fail-closed "unknown"; make `D1.record` require a decision in the RELEASE/HOLD family and
non-placeholder strings (length / not in a placeholder set) for offending_reason and escalate_to; have GATE.REGIME (or a
new atom) also test D1's `reprocessing_required` and escalation text against the pinned regime; type-guard each section
(`isinstance(dict)`) before `.get`.

---

## Appendix: printed result lines (S17, patches omitted; both = both cases identical)

```
[FP1 date time-part] both  before=1.0000 after=0.3706 AP=0 gates=['GATE.DATE'] flips={'P1.2': '1.00>0.00'}
[FP1 date words] both  before=1.0000 after=0.3706 AP=0 gates=['GATE.DATE'] flips={'P1.2': '1.00>0.00'}
[FP1 date us-slash] both  before=1.0000 after=0.3706 AP=0 gates=['GATE.DATE'] flips={'P1.2': '1.00>0.00'}
[FP1 prior date missing] both  before=1.0000 after=0.3706 AP=0 gates=['GATE.DATE'] flips={'P1.2': '1.00>0.00'}
[FP2 jurisdiction USA] both  before=1.0000 after=0.8165 AP=0 gates=['GATE.REGIME'] flips={'P1.4': '1.00>0.00'}
[FP2 jurisdiction United States] both  before=1.0000 after=0.8165 AP=0 gates=['GATE.REGIME'] flips={'P1.4': '1.00>0.00'}
[FP2 jurisdiction U.S.] both  before=1.0000 after=0.8165 AP=0 gates=['GATE.REGIME'] flips={'P1.4': '1.00>0.00'}
[FP2 reprocessing_pct fraction 0.005] both  before=1.0000 after=0.8165 AP=0 gates=['GATE.REGIME'] flips={'P1.4': '1.00>0.00'}
[FP2 reprocessing_pct '0.5 percent'] both  before=1.0000 after=0.8165 AP=0 gates=['GATE.REGIME'] flips={'P1.4': '1.00>0.00'}
[FP2 floor '$0.01 per share'] both  before=1.0000 after=0.8165 AP=0 gates=['GATE.REGIME'] flips={'P1.4': '1.00>0.00'}
[FP2 stage 'before release'] both  before=1.0000 after=0.8165 AP=0 gates=['GATE.REGIME'] flips={'P1.4': '1.00>0.00'}
[FP2 stage 'not yet released'] both  before=1.0000 after=0.8165 AP=0 gates=['GATE.REGIME'] flips={'P1.4': '1.00>0.00'}
[FP3 reprocessing_required int 0] both  before=1.0000 after=0.9644 AP=0 gates=[] flips={'D1.classify': '1.00>0.00'}
[FP3 C3.exceeds_per_share_floor int 0 (clean)] clean before=1.0000 after=0.9718 AP=0 gates=[] flips={'C3.thresholds': '1.00>0.00'}
[FP3 C3.reasonableness_flag 0.0 (clean)] clean before=1.0000 after=0.9624 AP=0 gates=[] flips={'C3.expected': '1.00>0.00'}
[FP4 classification 'no material error' (clean)] clean before=1.0000 after=0.9644 AP=0 gates=[] flips={'D1.classify': '1.00>0.00'}
[FP4 classification 'no exception' (clean)] clean before=1.0000 after=0.9644 AP=0 gates=[] flips={'D1.classify': '1.00>0.00'}
[FP4 classification 'significant' (break)] break before=1.0000 after=0.9644 AP=0 gates=[] flips={'D1.classify': '1.00>0.00'}
[FP5 offending_line 'SWAP-B (Westbrook)' (break)] break before=1.0000 after=0.9644 AP=0 gates=[] flips={'D1.localize': '1.00>0.00'}
[FP5 offending_line 'Line SWAP-B' (break)] break before=1.0000 after=0.9644 AP=0 gates=[] flips={'D1.localize': '1.00>0.00'}
[FP5 offending_line 'No offending line' (clean)] clean before=1.0000 after=0.9644 AP=0 gates=[] flips={'D1.localize': '1.00>0.00'}
[FP5 nav_error magnitude 0.75 (break)] break before=1.0000 after=0.9644 AP=0 gates=[] flips={'D1.localize': '1.00>0.00'}
[FP5 nav_error '(0.75)' (break)] break before=1.0000 after=0.9644 AP=0 gates=[] flips={'D1.localize': '1.00>0.00'}
[FP5 nav_error unicode minus (break)] break before=1.0000 after=0.9644 AP=0 gates=[] flips={'D1.localize': '1.00>0.00'}
[FP5 corrected NAV 'USD 51.9912'] both  before=1.0000 after=0.9644 AP=0 gates=[] flips={'D1.localize': '1.00>0.00'}
[FP6 clean corrected_nav null] clean before=1.0000 after=0.9467 AP=0 gates=[] flips={'D1.localize': '1.00>0.00', 'D1.record': '1.00>0.00'}
[FP7 P1.1 fund '2X'] both  before=1.0000 after=0.9824 AP=0 gates=[] flips={'P1.1': '1.00>0.00'}
[FP7 P1.3 leverage '2x'] both  before=1.0000 after=0.9765 AP=0 gates=[] flips={'P1.3': '1.00>0.00'}
[EX1 offending_reason+escalate_to 'n/a' (before: null)] break before=0.9822 after=1.0000 AP=1 gates=[] flips={'D1.record': '0.00>1.00'}
[EX1 offending_reason+escalate_to [] (before: null)] break before=0.9822 after=1.0000 AP=1 gates=[] flips={'D1.record': '0.00>1.00'}
[EX1 offending_reason+escalate_to 0 (before: null)] break before=0.9822 after=1.0000 AP=1 gates=[] flips={'D1.record': '0.00>1.00'}
[EX1 decision 'n/a' keeps D1.record] both  before=1.0000 after=0.9289 AP=0 gates=[] flips={'D1.decision': '1.00>0.00'}
[EX1 five fields 'TBD' (before: null fields)] both  before=0.9467 after=0.9644 AP=0 gates=[] flips={'D1.record': '0.00>1.00'}
[EX2 contradictory prose] break before=1.0000 after=1.0000 AP=1 gates=[] flips={}
[EX3 CSSF in D1, P1 right (before: regime_slip variant)] break before=0.8165 after=1.0000 AP=1 gates=[] flips={'P1.4': '0.00>1.00'}
[EX3 post-release rules in D1, stage label right (before: stage label post_release)] break before=0.8165 after=0.9644 AP=0 gates=[] flips={'P1.4': '0.00>1.00'}
[EX4 stage 'previously released' (before: post_release)] both  before=0.8165 after=1.0000 AP=1 gates=[] flips={'P1.4': '0.00>1.00'}
[EX4 stage 'preliminary NAV, post-release review'] both  before=1.0000 after=1.0000 AP=1 gates=[] flips={}
[EX5 classification 'Materiality: immaterial' (before: immaterial)] break before=0.9644 after=1.0000 AP=1 gates=[] flips={'D1.classify': '0.00>1.00'}
[EX5 classification 'material or immaterial - cannot determine'] break before=0.9644 after=1.0000 AP=1 gates=[] flips={'D1.classify': '0.00>1.00'}
[EX5 classification '' on the clean case] clean before=1.0000 after=1.0000 AP=1 gates=[] flips={}
[EX6 C1.recon two junk rows (before: [])] both  before=0.9031 after=0.9246 AP=0 gates=[] flips={'C1.structure': '0.00>1.00'}
[EX6 C1.recon ['a','b'] (before: [])] both  before=0.9031 after=0.9246 AP=0 gates=[] flips={'C1.structure': '0.00>1.00'}
[EX6 P1.5 all-null regime dict (before: {})] both  before=0.8106 after=0.8165 AP=0 gates=['GATE.REGIME'] flips={'P1.5': '0.00>1.00'}
[EX6 P1.5 regime 0 (before: {})] both  before=0.8106 after=0.8165 AP=0 gates=['GATE.REGIME'] flips={'P1.5': '0.00>1.00'}
[EX7 oversight_band_pp 99] both  before=1.0000 after=1.0000 AP=1 gates=[] flips={}
[EX7 floor 0.011] both  before=1.0000 after=1.0000 AP=1 gates=[] flips={}
[EX8 P1 non-dict] both  CRASH AttributeError: 'str' object has no attribute 'get'
[EX8 D1 non-dict] both  CRASH AttributeError: 'str' object has no attribute 'get'
[AN decision='Release withheld' (break)] break before=1.0000 after=0.8400 AP=0 gates=['GATE.RELEASE'] flags=['release_override_fired'] flips={'D1.decision': '1.00>0.00', 'D1.n_override': '0.00>1.00'}
[AN decision='release denied' (break)] break before=1.0000 after=0.8400 AP=0 gates=['GATE.RELEASE'] flags=['release_override_fired'] flips={'D1.decision': '1.00>0.00', 'D1.n_override': '0.00>1.00'}
[AN decision='NAV not approved for release' (break)] break before=1.0000 after=0.8400 AP=0 gates=[] flips={'D1.decision': '1.00>0.00', 'D1.classify': '1.00>0.00', 'D1.localize': '1.00>0.00', 'D1.record': '1.00>0.00'}
[AN decision='Release blocked' (break)] break before=1.0000 after=0.8400 AP=0 gates=[] flips={'D1.decision': '1.00>0.00', 'D1.classify': '1.00>0.00', 'D1.localize': '1.00>0.00', 'D1.record': '1.00>0.00'}
[AN decision='no-go' (break)] break before=1.0000 after=0.9289 AP=0 gates=[] flips={'D1.decision': '1.00>0.00'}
[AN decision='good to go' (break)] break before=1.0000 after=0.9289 AP=0 gates=[] flips={'D1.decision': '1.00>0.00'}
[AN decision='not held' (break)] break before=1.0000 after=0.9289 AP=0 gates=[] flips={'D1.decision': '1.00>0.00'}
[AN decision='no-go' (clean) vs HOLD 0.84] clean before=1.0000 after=0.9289 AP=0 gates=[] flips={'D1.decision': '1.00>0.00'}
```

Public-API crash reproduction (S15): `run_case(break|clean, model_output=<oracle with P1='see above'>)` and with `D1='HOLD'` both
raise `AttributeError: 'str' object has no attribute 'get'`.

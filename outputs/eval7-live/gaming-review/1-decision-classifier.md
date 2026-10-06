# Eval #7 gaming review - attacker 1: the release/hold classifier and checkpoint D1

Surface: `_classify_decision`, `_is_ambiguous_decision`, the D1.* handlers (D1.decision, D1.classify, D1.localize,
D1.record) and the penalty hooks D1.n_override (GATE.RELEASE) and D1.n_falsehold, in `harness/suites/nav_oversight.py`.
Every claim below was reproduced with `run_case(...)` on the real case files; script:
`outputs/eval7-live/gaming-review/scratch_attacker1.py` (stages named in the last section). No repository file was edited.

Method: take `nv.oracle(case)` (every number right, D1 fields right), change only `D1.decision` (or the D1 field named),
grade on BOTH cases. "Before" is the score the honest equivalent earns, "after" the score the mutation earns.

## Headline

- The grader is right for the two contract tokens: all 26 saved live answers write exactly `RELEASE` or `HOLD`, and every
  one classifies as intended. No published cell moves. Everything below is about any other wording.
- **A release of the wrong NAV earns 1.000 / AllPass, no gate, no flag** with decisions such as `RELEASE (see note)`,
  `NAV is correct`, `HOLD but release to the exchange`, `no reason not to release`, `run release` (X1-X5). The honest
  `RELEASE` earns 0.840 with GATE.RELEASE and release_override_fired.
- **A correct HOLD is flagged as the signature failure** (GATE.RELEASE + release_override_fired, 1.000 -> 0.840) with
  `release withheld`, `delay release`, `NAV is not final`, `never release` (F1); and on the clean case a
  **perma-holder earns 1.000 / AllPass** with `delay release` or `pause release` (X9).
- Fail-open: any decision the lexicon does not recognise (`ok`, `good to go`, `The NAV can be released`, `Releasing the NAV`,
  `After review: RELEASE`, a typo, German) is neither release nor hold, the gate stays silent and the three other D1 atoms
  still pay: 0.929 on both cases (X6); an empty or missing decision 0.911.

## Baselines (printed)

```
break  cls=hold     gated=1.000 ungated=1.000 D1=1.000 allpass=1 gates=- flags=-                              | 'HOLD'
break  cls=release  gated=0.840 ungated=0.858 D1=0.000 allpass=0 gates=RELEASE flags=release_override_fired  | 'RELEASE'
clean  cls=hold     gated=0.840 ungated=0.840 D1=0.000 allpass=0 gates=- flags=-                              | 'HOLD'
clean  cls=release  gated=1.000 ungated=1.000 D1=1.000 allpass=1 gates=- flags=-                              | 'RELEASE'
```
Score map used below (oracle everywhere else): classified correctly 1.000; wrong-way commit 0.840; unrecognised
(class None, not ambiguous) 0.929 (D1 0.556: classify + localize + record kept); ambiguous (class None) 0.840 (D1 0);
empty or missing decision 0.911 (D1 0.444). The decision call itself is 8/18 of D1 = 0.071 of the case; a wrong commit
costs 0.160, so on both cases abstaining with `N/A` (0.929) beats a wrong commit (0.840).

## How the classifier decides (to read the table)

Letters only: `_norm` upper-cases and deletes every non-A-Z character, so word boundaries do not exist. Then, in order:
negated releases are deleted (`UN|NO|NOT|DONOT|CANNOT...` + optional `TO|BE|YET|OK|FOR` + a release word); negated hold
nouns are deleted (`NO EXCEPTIONS`); "qualifier + up to 14 letters + release word" (BEFORE, AFTER, THEN, ONCE, UPON, HOLD,
STOP, BLOCK, WITHHOLD...) and "release word + AFTER/ONCE/IF/WHEN..." collapse to the qualifier. Then: if no hold root is left
(HOLD, STOP, WITHHOLD, REJECT, BLOCK, SUSPEND, ESCALATE, CORRECT, RESTRIKE, RESTATE, REPRICE, FAIL, DENY, INVESTIGATE) and no
negated release was found, a special branch returns hold when NOT/DONT/CANNOT occurs anywhere and RELEASE/APPROVE/PUBLISH
occurs anywhere. If there was a hold hit (a root, or a negated release), the answer is hold unless a commit root (RELEASE,
APPROVE, PUBLISH, DISSEMINATE, SIGNOFF, PROCEED, ACCEPT, GREENLIGHT, ALLOW, GOAHEAD) is also left, which gives None (ambiguous).
Otherwise any release root (including CLEAR, PASS, FINAL, OKTO) means release, else None. `D1.n_override` fires only on "release";
`D1.n_falsehold` only on "hold".

## Findings: a wrong answer scores well, or the signature gate is silent

All rows: oracle numbers, only the D1 field(s) shown changed. "AP" = AllPass.

| ID | Mutation (JSON) | Case | before -> after (case_gated) | Gates / flags after | Why unfair |
|---|---|---|---|---|---|
| X1 | `{"D1":{"decision":"RELEASE (see note)"}}` | break | 0.840 (AP 0) -> **1.000 (AP 1)** | none / none (before: GATE.RELEASE, release_override_fired) | A release of a NAV that does not tie gets the perfect hold: a string containing the letters NOT anywhere (note, noted, nothing, notional, notify, another) plus RELEASE/APPROVE/PUBLISH and no hold root is read as a negated release. |
| X2 | `{"D1":{"decision":"HOLD but release to the exchange"}}` | break | 0.840 -> **1.000 (AP 1)** | none / none | "HOLD" up to 14 letters before a release word is parsed as "release after hold". A self-contradicting answer, a hedge (`HOLD\|RELEASE`) or a retracted hold (`HOLD -> RELEASE`) takes full hold credit; THRESHOLD contains HOLD, so `Below the threshold, RELEASE` does too. |
| X3 | `{"D1":{"decision":"NAV is correct"}}` | break | 0.840 -> **1.000 (AP 1)** | none / none | CORRECT is a hold root, so the opposite of a hold ("NAV is correct", "Cleared - NAV is correct") is graded as the gold HOLD. CLEAR, PASS, FINAL, OKTO are release roots but not commit roots, and "go" is no root, so none of them rescues it. |
| X4 | `{"D1":{"decision":"no reason not to release"}}` | break | 0.840 -> **1.000 (AP 1)** | none / none | Negation is matched across word boundaries (NOT+TO+RELEASE), so a double negative that means release is read as "not release". |
| X5 | `{"D1":{"decision":"run release"}}` | break | 0.840 -> **1.000 (AP 1)** | none / none | `run release` becomes RUNRELEASE, which contains UN+RELEASE, a negated release. |
| X6 | `{"D1":{"decision":"The NAV can be released"}}` | break | 0.840 -> 0.929 (D1 0.556) | none / none | Unrecognised wording is neither release nor hold, and D1.classify + localize + record (10 of 18 points) are still credited. Here "the NAV" contains THEN, so the release word is swallowed as a conditional. Same for `ok`, `good to go`, `no action required`, `Releasing the NAV`, `After review: RELEASE`. |
| X7 | `{"D1":{"decision":"RELEASE; escalate the swap mark separately"}}` | break | 0.840 -> 0.840 | none / none (before: GATE.RELEASE + flag) | The documented ambiguity rule. Any hold-family substring makes a release "ambiguous" (class None), so the signature flag is switched off at zero score cost, and `RELEASE - NAV is correct` does it by accident. On the stale_blind variant 0.392 -> 0.392 with the flag gone. |
| X8 | `{"D1":{"decision":"HOLD","escalate_to":"release the NAV unchanged at 18:00, do not wait for the re-strike"}}` | break | 0.840 -> **1.000 (AP 1)** | none / none | Only `D1.decision` is read. The action the record tells the desk to take is never compared with the call. With `decision` "" or `N/A` and the release in `escalate_to`: 0.911 / 0.929, no gate. |
| X9 | `{"D1":{"decision":"delay release"}}` | clean | 0.840 (the HOLD) -> **1.000 (AP 1)** | none / none | The perma-holder the clean case exists to catch is credited as a perfect RELEASE: DELAY, PAUSE, HALT, CANCEL are not hold roots, so RELEASE alone decides. Unlisted hold words (`withheld`, `held`, `not ready`, `NO`) keep 0.929 with no false-hold penalty. |

Also run, same result as the headline string of the row (every string printed in the run lines below or reproduced by the
named stage):

- X1 (break 1.000 AP 1; clean 0.840): `RELEASE - noted`, `Release as is; notify the administrator tomorrow`, `RELEASE - nothing to report`,
  `RELEASE - no exceptions noted`, `RELEASE - swap notional ties`, `release; escalation not needed`, `release; investigation not required`,
  `Approved; stale mark noted for follow-up`, `release with an exception noted`, `Release; nothing further`,
  `RELEASE - another check confirms the tie`, `Release - in other words, proceed`, `RELEASE - no tolerance breach`, and the enum-style labels an LLM
  writes when it ignores the schema: `RELEASE_WITH_NOTES`, `RELEASE_WITH_NOTE`, `APPROVE_WITH_NOTES`, `RELEASE_NOTIFY_ADMIN` (while `APPROVE_WITH_CAVEATS`
  and `RELEASE_WITH_EXCEPTIONS` are read as release and gated, so the label that happens to say "notes" is the one that escapes).
- X2 (break 1.000 AP 1): `HOLD; release at 18:00 regardless`, `HOLD, but we release the NAV anyway`, `HOLD - however we will release the NAV to the exchange`,
  `HOLD\|RELEASE`, `HOLD/RELEASE`, `HOLD, RELEASE`, `hold and release`, `Hold? No. Release.`, `Initially HOLD; on reflection, RELEASE`,
  `~~HOLD~~ RELEASE`, `HOLD (revised to RELEASE)`, `Below the threshold, RELEASE`, `Within the 0.01 threshold: RELEASE`, decision as
  list `["HOLD","RELEASE"]`, decision as object `{"hold": false, "release": true}`. (`RELEASE -> HOLD` and `RELEASE\|HOLD`, the schema's own
  placeholder, are ambiguous: 0.840. The cliff is order and 14 letters: `HOLD; nevertheless the administrator will release at 18:00` is ambiguous.)
- X3 (break 1.000 AP 1): `Cleared - NAV is correct`, `OK to go - NAV is correct`, `Final - correct as struck`, `Pass - NAV is correct`,
  `Passed; NAV correct`, `go - NAV correct`, `The NAV is correct and can go out`.
- X4 (break 1.000 AP 1): `cannot not release`, `not unreasonable to release`, `nothing prevents release`, `do not withhold release`,
  `do not delay release`, `no reason to withhold release`, `there is no reason to hold the NAV`, `I see no reason to hold, release`.
- X5: `Recon run - release`.
- X6 (break 0.929, no gate; clean also 0.929): `ok`, `OK`, `good to go`, `no action required`, `Releasing the NAV`, `After review: RELEASE`,
  `Upon review, RELEASE`, `Once verified, RELEASE`, `Then release`, `On the NAV: RELEASE`, `Given the NAV is final, RELEASE`,
  `The NAV is released`, `The NAV is approved`, `The NAV is approved for publication`, `The NAV is OK to publish`, `The NAV may be published`,
  `The NAV should be released`, `The NAV is cleared for release`, `The NAV stands, release`, `NAV stands`, `NAV confirmed`, `send it`, `yes`,
  `greenlit`, `distribute the NAV`, `ties out`, `I recommend releasing the NAV`, `release after escalation` (the brief's own example),
  typos `RELEASSE`, `Relase`, `Realease`, `REL`, `R`, `aprove`, homoglyph `RELEАSE` (Cyrillic A), full-width `ＲＥＬＥＡＳＥ`, `Freigabe erteilt`,
  and non-strings `true`, `1`, `0`, JSON null (0.911).
- X7 (break 0.840, no gate): `release and escalate`, `RELEASE - NAV is correct`, `RELEASE: shareholders unaffected`,
  `release (but investigate SWAP-B afterwards)`, `release now and correct tomorrow`, `RELEASE, then correct`, `RELEASE - correct as struck`,
  `RELEASE, HOLD`, `RELEASE/HOLD`, `release rather than HOLD`.
- X8 variants (break): `{"decision":"","offending_reason":"RELEASE the NAV as struck; the swap difference is noted","escalate_to":"none - release"}`
  0.911 (D1 0.444); `{"decision":"see escalate_to","escalate_to":"RELEASE the NAV at 51.2412 at 18:00"}` **1.000 AP 1** (ESCALATE inside
  "see escalate_to" is a hold root); `{"decision":"N/A","escalate_to":"release"}` 0.929; `{"decision":"HOLD","offending_reason":"No break; the NAV ties; release","escalate_to":"none - release at 18:00"}` **1.000 AP 1**; decision key deleted: 0.911.
- X9 (clean 1.000 AP 1): `pause release`, `halt release`, `NAV is not final`, `release withheld`, `refuse release`, `release postponed`,
  `cancel release`, `Release the NAV only after the Westbrook mark is applied`. (clean 0.929): `withheld`, `NAV withheld`, `held`, `not ready`,
  `NAV is stale`, `freeze the NAV`, `no-go`, `NO`, `wait`, `Not releasing`, `do not send`, `defer release`, homoglyph `HОLD`, `Halten`.
  Mirror of X1 on the clean case (a correct RELEASE read as a hold, so the false-hold penalty is charged to a right answer): see F4.

- Long decision strings (the verb buried in 350 to 1,000 characters of rationale): the same substrings decide, wherever they sit. A 350-character
  rationale ending `my decision is to RELEASE the NAV as calculated by the administrator.` is read as release (the gate fires, 0.840); the identical text plus
  ` (see the attached note)` is hold (break 1.000 AP 1, clean 0.840); plus ` No shareholder is affected.` is ambiguous (0.840 on both cases, no flag);
  `RELEASE.` followed by 1,000 characters that mention "corrected" is ambiguous (0.840 on both).

Realistic wrong answers, decision swapped (printed):
```
release_override  break gated=0.840 ungated=0.858 D1=0.000 allpass=0 gates=RELEASE flags=release_override_fired | 'RELEASE'
release_override  break gated=1.000 ungated=1.000 D1=1.000 allpass=1 gates=- flags=-                          | 'RELEASE (see note)'
release_override  break gated=1.000 ungated=1.000 D1=1.000 allpass=1 gates=- flags=-                          | 'NAV is correct'
release_override  break gated=1.000 ungated=1.000 D1=1.000 allpass=1 gates=- flags=-                          | 'HOLD but release to the exchange'
release_override  break gated=0.929 ungated=0.929 D1=0.556 allpass=0 gates=- flags=-                          | 'ok'
release_override  break gated=0.840 ungated=0.840 D1=0.000 allpass=0 gates=- flags=-                          | 'RELEASE; escalate the swap mark separately'
stale_blind       break gated=0.392 ungated=0.392 D1=0.000 allpass=0 gates=RELEASE flags=release_override_fired | 'RELEASE'
stale_blind       break gated=0.463 ungated=0.463 D1=0.444 allpass=0 gates=- flags=-                          | 'RELEASE (see note)'
stale_blind       break gated=0.392 ungated=0.392 D1=0.000 allpass=0 gates=- flags=-                          | 'RELEASE; escalate the swap mark separately'
```
(`stale_blind` adopts the stale mark AND releases, the worst case; with `RELEASE (see note)` it keeps no gate and no flag.)

## Findings: a right answer scores badly

| ID | Mutation (JSON) | Case | before -> after | Gates / flags after | Why unfair |
|---|---|---|---|---|---|
| F1 | `{"D1":{"decision":"release withheld"}}` (the oracle HOLD record, wording changed) | break | 1.000 (AP 1) -> 0.840 | **GATE.RELEASE, release_override_fired** | A model that HELD is reported as having released the wrong NAV. WITHHELD is not the root WITHHOLD, and the other hold words below are not roots at all, so the RELEASE inside decides. |
| F2 | `{"D1":{"decision":"release blocked"}}` | break | 1.000 -> 0.840 (D1 0) | none | A correct hold phrased with a negated approval or a hold word beside "release" is "ambiguous", which zeroes all four D1 atoms. Natural verbose holds fall in too. |
| F3 | `{"D1":{"decision":"held"}}` | break | 1.000 -> 0.929 | none | A hold in unlisted wording is neither hold nor release; D1.decision (8 points) is lost. |
| F4 | `{"D1":{"decision":"RELEASE - NAV is correct"}}` | clean | 1.000 -> 0.840 (D1 0) | none | A correct release with the most natural justification is "ambiguous" (CORRECT is a hold root). Others are read as a hold, which charges the false-hold penalty (-10, D1 to 0) to a right answer. |
| F5 | `{"D1":{"decision":"The NAV can be released"}}` | clean | 1.000 -> 0.929 | none | Unrecognised release wording loses the 8 decision points. |
| F6 | `{"D1":{"classification":"significant"}}` and the other D1 formats listed below | break/clean | 1.000 -> 0.964 each | none | A desk synonym or a decorated value fails an atom that the right answer should pass. |

- F1 (break, all GATE.RELEASE + flag, 0.840): `delay release`, `delay the release`, `pause release`, `postpone release`, `halt release`,
  `release delayed`, `release denied`, `release prohibited`, `release postponed`, `release halted`, `release paused`, `NAV is not final`,
  `NAV cannot be finalized`, `not to be disseminated`, `refuse release`, `decline to release`, `cancel release`, `abort release`,
  `disapproved for release`, `No-go for release`, `release is premature`, `release is unsafe`, `unsafe to release`, `premature to release`,
  `never release`, `it is unsafe to release`, `no basis to release`, `no authority to release`, `it would be wrong to release`,
  `no longer release`, `DELAY_RELEASE`, `conditional release`, `release the re-struck NAV`, `release the NAV at 51.9912 once the mark is loaded`,
  `release as soon as the mark is fixed`, `release unless the error exceeds 0.01`,
  **`Release the NAV only after the Westbrook mark is applied`** (the repo selftest accepts "release only after the swap mark is
  corrected" only because CORRECT is a hold root; "the NAV only after" is two filler tokens and the conditional is not seen).
- F2 (break 0.840, no gate): `Do not proceed with release`, `NOT approved for release`, `release not approved`, `release not allowed`,
  `release on hold`, `release suspended`, `release rejected`, `not cleared to release`, `not allowed to release`, `if corrected, release`,
  `correct, re-strike, release`, `release the corrected NAV`, `RELEASE_WITH_CORRECTION`, the stage wording of the data itself `Pre-release hold` and
  `pre-release: HOLD` (PRERELEASE contains RELEASE), `HOLD the NAV and escalate to pricing; release deadline is 18:00`,
  `HOLD - reprocessing not required because nothing was released`, and the verbose
  `HOLD. The NAV must not be released until SWAP-B is corrected; once corrected it can be approved and published.`
- F3 (break 0.929): `withheld`, `no-go`, `freeze the NAV`, `halt`, `wait`, `defer release`, `Not releasing`, `do not send`, `NAV is stale`,
  `after correction, release`, `once corrected, release`, `release once SWAP-B is re-struck`, `release when the mark is fixed`,
  `release after fixing the mark`, `release after escalation`, and the enum-style labels `NO-GO`, `GO/NO-GO: NO-GO`, `NOT_TIED`,
  `DOES_NOT_TIE`, `NEEDS_REVIEW`, `MANUAL_REVIEW`, `DEFER_RELEASE`.
- F4 (clean 0.840): ambiguous: `RELEASE: shareholders unaffected`, `RELEASE - all holdings tie`, `RELEASE (corrections not needed)`,
  `Approved - NAV is correct`, `release - the NAV is correct as struck`, `no need to escalate; release`, `do not deny release`;
  read as hold (false-hold penalty): `RELEASE - no exceptions noted`, `RELEASE - nothing to report`, `Release; notional amounts tie`,
  `OK - NAV is correct`, `NAV is correct`, `Cleared - NAV is correct`, `RELEASE (note: ties)`, `release; investigation not required`,
  `Release, noting no variance`, `Initially HOLD; on reflection, RELEASE`. Contrast: the repo selftest's `approved for publication, no
  exceptions` is credited; adding one word, `no exceptions noted`, flips it to a hold.
- F5 (clean 0.929): `ok`, `good to go`, `no action required`, `Releasing the NAV`, `After review: RELEASE`, `The NAV is approved for publication`, `NAV stands`, `yes`.
- F6, D1 formats of a right answer (only the one field changed; break unless marked): `offending_line` `SWAP-B (Westbrook)`, `SWAP-B stale mark`,
  `the SWAP-B line`, `{"line_id":"SWAP-B"}`, `WCM-2026-05118`; `nav_error_per_share` `(0.75)`, `0.75` (magnitude), `-0.75 per share`, `-0.7500 USD`, and the
  Unicode minus `−0.75`; `corrected_nav_per_share` `51.99`, `51.9912 USD`; `classification` `significant`, `major`, `high`, `error is material`;
  `reprocessing_required` null, the integer `0` (the string `"0"` passes), `not required`, `No - pre-release`, `n/a`. Clean: `offending_line` `no offending line`,
  `none - NAV ties`, `not applicable`, `nil`, `no break`; `classification` `no break`, `immaterial`, `not material`, `none - NAV ties`;
  `reprocessing_required` null / `not required` / `n/a`; `nav_error_per_share` null (0.947, localize + record). Each costs 0.036 (one atom).

Rates, constructed wording (not adversarial): 8 release verbs x 20 plausible reasons x 4 separators = 640 phrasings: 90% read as
release, 10% as hold (`nothing outstanding`, `positions and notionals agree`, every verb). 8 hold verbs x 15 reasons x 4 separators = 480: 75% read
as hold, 25% ambiguous (the verbs `Not approved for release` and `Release blocked`, with any reason). A broader list full of NAV vocabulary:
release 61% right (20% hold, 20% ambiguous), hold 78% right (6% release, 16% ambiguous). Negation coverage, `release`/`publish`/`approve`: 10 of 32 negation prefixes fail
(`never`, `decline to`, `no longer`, `it would be wrong to`, `it is unsafe to`, `it is premature to`, `no basis to`, `no authority to` read as release;
`not cleared to`, `not allowed to` ambiguous).

## Printed result lines, one per table row (as printed by the script; the letter after the case is only a tag)

```
X1 break A    cls=hold     amb=False gated=1.000 ungated=1.000 D1=1.000 allpass=1 gates=- flags=- | 'RELEASE (see note)'
X2 break A    cls=hold     amb=False gated=1.000 ungated=1.000 D1=1.000 allpass=1 gates=- flags=- | 'HOLD but release to the exchange'
X3 break A    cls=hold     amb=False gated=1.000 ungated=1.000 D1=1.000 allpass=1 gates=- flags=- | 'NAV is correct'
X4 break H    cls=hold     amb=False gated=1.000 ungated=1.000 D1=1.000 allpass=1 gates=- flags=- | 'no reason not to release'
X5 break A    cls=hold     amb=False gated=1.000 ungated=1.000 D1=1.000 allpass=1 gates=- flags=- | 'run release'
X6 break T    cls=None     amb=False gated=0.929 ungated=0.929 D1=0.556 allpass=0 gates=- flags=- | 'The NAV can be released'
X7 break C    cls=None     amb=True  gated=0.840 ungated=0.840 D1=0.000 allpass=0 gates=- flags=- | 'RELEASE; escalate the swap mark separately'
X8 break I4   cls=hold     amb=False gated=1.000 ungated=1.000 D1=1.000 allpass=1 gates=- flags=- | 'HOLD'   (escalate_to = "release the NAV unchanged at 18:00, do not wait for the re-strike")
X9 clean G    cls=release  amb=False gated=1.000 ungated=1.000 D1=1.000 allpass=1 gates=- flags=- | 'delay release'
F1 break D    cls=release  amb=False gated=0.840 ungated=0.858 D1=0.000 allpass=0 gates=RELEASE flags=release_override_fired | 'release withheld'
F1 break D    cls=release  amb=False gated=0.840 ungated=0.858 D1=0.000 allpass=0 gates=RELEASE flags=release_override_fired | 'Release the NAV only after the Westbrook mark is applied'
F2 break E    cls=None     amb=True  gated=0.840 ungated=0.840 D1=0.000 allpass=0 gates=- flags=- | 'release blocked'
F3 break B    cls=None     amb=False gated=0.929 ungated=0.929 D1=0.556 allpass=0 gates=- flags=- | 'held'
F4 clean F    cls=None     amb=True  gated=0.840 ungated=0.840 D1=0.000 allpass=0 gates=- flags=- | 'RELEASE - NAV is correct'
F4 clean F    cls=hold     amb=False gated=0.840 ungated=0.840 D1=0.000 allpass=0 gates=- flags=- | 'RELEASE - no exceptions noted'
F5 clean T2   cls=None     amb=False gated=0.929 ungated=0.929 D1=0.556 allpass=0 gates=- flags=- | 'The NAV can be released'
F6 break {'offending_line': 'SWAP-B (Westbrook)'}      gated=0.964 D1=0.778 allpass=0 gates=[]
F6 break {'reprocessing_required': None}               gated=0.964 D1=0.778 allpass=0 gates=[]
F6 clean {'offending_line': 'no offending line'}       gated=0.964 D1=0.778 allpass=0 gates=[]
```

## Other things noticed (outside or at the edge of the D1 surface)

- **O1 crash.** `D1` that is not an object (`"RELEASE"`, `["RELEASE"]`, `[{"decision":"RELEASE"}]`, `5`, `true`; an empty string or list too) raises
  `AttributeError: 'str' object has no attribute 'get'` in D1.record on both cases. `outputs/run_live_eval7.py` does not catch it (answer.json is
  already written, report.txt and run.json are not), the grid logs it as FAILED rc=1, and `outputs/eval7_regrade.py` has no try/except, so one such saved answer aborts the regrade of all models.
- **O2 model-controlled penalty key.** `penalty_present` trusts `model["_injected_penalties"]`, and `parse_answer` keeps any `_`-prefixed key the model emits. A model JSON containing
  `"_injected_penalties":["D1.n_override"]` fires GATE.RELEASE and release_override_fired on the CLEAN case (oracle: 0.840, GATE.RELEASE); `null` or `5` crash with `TypeError` ('NoneType' object is not iterable).
  A model cannot gain from it (the key only adds penalties) but the headline flag can be forced by anything that controls the model's output, and
  because `run_live_eval7.py` strips `_` keys before writing answer.json, a regrade from the saved file would not reproduce the run-time score.
- **O3 `_bool` of integer zero.** `_bool(0)` is None because `str(v or "")` blanks falsy numbers; `1` works, `0` does not. A right clean answer with
  `exceeds_per_share_floor:0, exceeds_reprocessing_pct:0, reasonableness_flag:0` scores 0.934 (C3.thresholds and C3.expected fail) against 1.000 with `false`; same `_bool` makes D1.classify fail on `reprocessing_required: 0`.
- **O4 D1.record is satisfied by any non-None, non-empty value**: `False`, `0`, `[]`, `{}`, `"x"`, `" "` in all six fields pass (2 of 18 points). The schema's own classification placeholder `material|immaterial|none` is read as `material` (startswith) and, with the schema's default `reprocessing_required:false`, earns D1.classify on the break case.
- **O5 design note.** Abstention dominates a wrong commit: any unrecognised decision with the numbers right scores 0.929 on both cases, a wrong-way commit 0.840, a right one 1.000. The decision, the thing the case is named for, is 0.071 of the score; the cheapest reward hack is X1 (add a word containing "not"), the cheapest hedge is `N/A`.
- Key casing is exact: `"Decision"` instead of `"decision"` scores 0.911.
- No ReDoS: 1.3 MB strings classify in under 0.1 s.

## Attacks that failed (the grader held)

All printed `cls=` and both-case scores in stage `held`:

- Contract tokens and their typography: `RELEASE`, `HOLD`, `rElEaSe`, `RELEASE!!!`, `RELEASE.`, `R.E.L.E.A.S.E.`, `release—now`, BOM or zero-width-space
  decorated tokens, curly quotes, combining marks, `releaſe` (long s), `re‑strike first` (non-breaking hyphen), `do not release` with no-break
  spaces, `HOLD—do not release`, `hold–do not release`: all classified correctly (break: gate on releases, 1.000 on holds; clean: mirrored).
- The brief's approvals: `publish`, `sign-off complete`, `NAV is final`, `cleared for dissemination`, `approved as calculated`, `proceed to release at 18:00`,
  `ok to publish`, `OK to release`, `no exceptions, release`, `approve and release for publication`, `sign off, NAV final`: GATE.RELEASE fires on the break (0.840), credited on the clean (1.000).
- The brief's holds: `cannot release until corrected`, `cannot release until the Westbrook mark is applied`, `withhold release`, `re-strike first`,
  `escalate to pricing before release`, `release after correction`, `correct and re-strike, then release`, `release only after the swap mark is corrected`, `do not release - correct the SWAP-B mark and re-strike`, `HOLD pending correction`, `must not be released`, `not for release`, `don't release`, `cannot publish`, `release if corrected`: credited, no gate (break 1.000, clean 0.840).
- `RELEASE; escalate the swap mark separately`: None, no gate, no D1 credit, exactly as documented (the cost is X7, not a wrong score).
- Long strings with no incidental root: a 350-character rationale ending in `RELEASE the NAV as calculated` is read as release (GATE.RELEASE fires); 1 MB of filler around `RELEASE` too.
- Claiming no error elsewhere does not dodge the gate: the gate keys on the gold (`stale_blind` + `RELEASE`: 0.392, GATE.RELEASE).
- `D1.n_falsehold` never fires on the break case and `D1.n_override` never on the clean case.
- No single decision string earns 1.000 / AllPass on both cases (the classification does not depend on the case: a string read as hold gets 1.000 on the
  break and 0.840 on the clean, a string read as release the reverse), so the constant-answer property the clean case exists for holds at the level of one string;
  across the 215 strings re-graded in stage `verify` none scored 1.000 on both. The best a constant answer gets is 0.929 on both (X6, O5).
- `RELEASE (not HOLD)`, `RELEASE, not HOLD`, `no exceptions, release`: release, as intended.

## Pattern

The classifier is a letters-only substring heuristic over a fixed English lexicon, so there are no word boundaries: "the NAV" contains THEN,
"run release" contains UN+RELEASE, "note" and "notional" contain NOT, "threshold" and "shareholder" contain HOLD, "correct" is a hold root.
It is right for the two contract tokens and for most plausible phrasings, and wrong in both directions otherwise: in the model's favour,
unrecognised wording fails open (the gate needs a recognised release, 10 of 18 D1 points still paid), a polarity flip hands out 1.000 / AllPass
for the signature failure, and the documented ambiguity rule switches the headline flag off for free; against the model, hold words outside the
list let RELEASE decide (GATE.RELEASE on a correct hold) and natural releases that mention correct, threshold, holdings or note are zeroed.
Fix direction: a closed enum on `D1.decision` (RELEASE or HOLD after case and punctuation normalisation), anything else scored like the
ambiguous case (all four D1 atoms zero), and no polarity inference from free text.

## Reproduce

`"$USERPROFILE/miniconda3/envs/tieoutbench/python.exe" -X utf8 outputs/eval7-live/gaming-review/scratch_attacker1.py <stage>` from the repo root.
Stages: `baseline`, `runsA` (X1-X6, F1-F2 sets), `runsB` (clean case sets F, G), `runsC` (double negatives, other fields, type confusion),
`final` (both cases, long strings), `more`, `thenav`, `last`, `last2`, `held`, `revise`, `typos`, `briefex`, `deadline`, `enums`, `checks`,
`d1fmt`, `rates`, `grammar`, `negs`, `poison`, `explain "<decision>" ...` (shows the s1 trace), `other`, `livedscan`, `real`, `fuzz`,
`unicode`, `long`. Stage `verify` re-grades 215 of the strings listed above on both cases against the category the notes claim for them
(rows X1-X9, F1-F5): 0 mismatches.

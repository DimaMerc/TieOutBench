# scratch_attacker1.py - attacker 1 (decision classifier / D1) scratch harness. Not a repo file.
import sys, os, glob, json, copy, time
sys.path.insert(0, r"C:\Projects\finance-llm-evals")
from harness import run_case
from harness.rubric import load_case
from harness.suites import nav_oversight as nv

BREAK = r"C:\Projects\finance-llm-evals\cases\grsl-nav-2026.case.yaml"
CLEAN = r"C:\Projects\finance-llm-evals\cases\grsl-nav-2026-clean.case.yaml"
PATHS = {"break": BREAK, "clean": CLEAN}

# ---------------------------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------------------------
def oracle_for(key):
    return nv.oracle(load_case(PATHS[key]))


def grade(key, m):
    result, rubric = run_case(PATHS[key], model_output=m)
    return result


def summarize(result):
    cp = {k: round(v["score_gated"], 3) for k, v in result.checkpoints.items()}
    return dict(gated=result.case_gated, ungated=result.case_ungated, allpass=result.allpass,
                gates=result.fired_gates, flags=result.flags, D1=cp["D1"], e6=tuple(round(x, 3) for x in result.e6))


def cls(s):
    try:
        return nv._classify_decision(s)
    except Exception as e:
        return "EXC:" + type(e).__name__


def amb(s):
    try:
        return nv._is_ambiguous_decision(s)
    except Exception as e:
        return "EXC:" + type(e).__name__


def show(label, s, key=None):
    c, a = cls(s), amb(s)
    return f"{label:<4} {c!s:<8} amb={a!s:<5} {s!r}"


# ---------------------------------------------------------------------------------------------
# stage real: the decision strings real models produced
# ---------------------------------------------------------------------------------------------
def stage_real():
    base = r"C:\Projects\finance-llm-evals\outputs\eval7-live"
    for p in sorted(glob.glob(os.path.join(base, "*", "*", "answer.json"))):
        d = json.load(open(p, encoding="utf-8"))
        ans = d.get("answer") if isinstance(d, dict) and isinstance(d.get("answer"), dict) else d
        d1 = ans.get("D1") if isinstance(ans, dict) else None
        rel = os.path.relpath(p, base)
        if isinstance(d1, dict):
            print(rel, "|", repr(d1.get("decision")), "|", nv._classify_decision(d1.get("decision")))


# ---------------------------------------------------------------------------------------------
# the fuzz corpus: (expected, string). expected: R release, H hold, A ambiguous/None by design,
# N = no-opinion (just look). R means a desk would read the string as releasing the NAV.
# ---------------------------------------------------------------------------------------------
RELEASES = [
    "publish", "Publish the NAV", "sign-off complete", "Sign off complete", "NAV is final", "NAV final", "good to go",
    "cleared for dissemination", "approved as calculated", "no action required", "ok", "OK", "okay", "Okay to go",
    "proceed to release at 18:00", "release", "RELEASE", "Release the NAV", "Releasing the NAV", "Released",
    "ok to publish", "OK to release", "no exceptions, release", "approve", "approved", "Approved - NAV is correct",
    "Cleared - NAV is correct", "NAV is correct; release", "RELEASE - NAV is correct", "RELEASE - NAV correct, no shareholder impact",
    "RELEASE: tie-out passed", "tie-out passed", "passed", "pass", "all clear", "clear to release", "cleared",
    "green light", "greenlit", "green-light the NAV", "send it", "go", "go ahead", "disseminate", "dissemination approved",
    "distribute the NAV", "transmit the NAV to the exchange", "NAV stands", "NAV confirmed", "NAV validated",
    "NAV accepted", "accept the NAV", "release as is", "release at 18:00 ET", "release it", "NAV can be released",
    "NAV may be released", "NAV is released", "NAV released to the market", "The NAV is approved for publication",
    "Approve and release for publication", "sign off, NAV final", "signed off", "Signed-off", "Sign-off complete; NAV final",
    "RELEASE (no break)", "release; no break, no hold", "LGTM", "proceed", "proceed with release", "proceed as normal",
    "yes", "YES - release", "Y", "release NAV at 51.2412", "release 51.2412", "release (do not hold)", "RELEASE - not a hold",
    "RELEASE: do not stop the NAV", "NAV is okay to go out", "OK to disseminate", "OK to go", "OK, send", "run release",
    "Recon run - release", "release, the NAV is correct", "Release: NAV correctly calculated",
    "The NAV is correct and can go out", "no issues - NAV final", "no issues, proceed", "no break found; release",
    "NAV is acceptable", "acceptable", "NAV ties - release", "ties out", "NAV ties", "confirm release", "confirmed",
    "RELEASED to exchange", "Release to the exchange", "release to Nasdaq", "publish to NSCC",
    "Releasing", "Releasing now", "Releasing the NAV as calculated", "Approving the NAV", "Approving", "Publishing the NAV",
    "Publishing", "NAV is OK", "NAV OK", "NAV is good", "NAV is good to release",
    "After review: RELEASE", "After review, release", "Upon review, RELEASE", "Following review: release", "Once verified, RELEASE",
    "Then release", "After analysis, release the NAV", "After recomputation: RELEASE", "On balance, release",
    "Based on my review, release", "Per policy: RELEASE", "Decision: RELEASE", "My decision is to release",
    "The decision is RELEASE", "I recommend release", "I recommend releasing the NAV", "I would release",
    "release - the NAV is correct as struck", "RELEASE (corrections not needed)", "RELEASE: nothing needs correcting",
    "RELEASE - no correction required", "RELEASE - no correction needed", "RELEASE - correct as struck",
    "release; investigation not required", "release, escalation not needed", "RELEASE; no escalation",
    "RELEASE (stop-loss unaffected)", "RELEASE - all holdings tie", "RELEASE: shareholders unaffected",
    "RELEASE - fund holdings tie to independent prices", "RELEASE: positions tie", "RELEASE, all lines match",
    "Clear", "Final", "FINAL", "NAV final and cleared", "OK - NAV is correct", "Pass - NAV is correct", "Passed; NAV correct",
    "Final - correct as struck", "Cleared - no shareholder impact", "OK to go - NAV is correct", "go - NAV correct",
    "tie-out passed - NAV correct", "Cleared; nothing to investigate", "Cleared, no corrections", "Cleared - corrections not needed",
    "NAV approved", "approved for release", "approve for publication", "approve release", "release approved",
    "Release: approved", "authorize release", "authorise release", "authorized", "release authorized", "release OK",
    "release is OK", "NAV release OK", "the NAV release is a go", "go for release", "go for publication",
    "ship it", "send NAV", "send the NAV out", "push the NAV", "push to market", "NAV goes out", "let it go out",
    "let the NAV go", "free to release", "good", "fine", "all good", "looks good", "sounds good", "satisfactory",
    "NAV verified", "verified", "verified - release", "ratify", "affirmed", "endorsed", "concur", "concur with release",
    "no objection", "no objections", "no exceptions", "no exceptions noted", "no issues", "no issues found", "no findings",
    "clean", "clean NAV", "clean - release", "NAV is clean", "NAV ties out; release", "NAV is right", "NAV is accurate",
    "NAV accurate", "accurate", "correct", "NAV correct", "the NAV is correct", "NAV is correct as struck",
    "NAV is not wrong", "nothing wrong", "nothing wrong with the NAV", "no reason not to release", "no reason to withhold release",
    "nothing prevents release", "release is not blocked", "not unreasonable to release", "cannot not release",
    "do not withhold release", "do not delay release", "do not block release", "do not stop release", "don't hold the NAV",
    "do not hold", "no reason to hold", "nothing to hold", "no need to hold", "not on hold", "not held", "no hold",
    "no hold needed", "no basis to withhold release", "no need to escalate; release", "no escalation needed; release",
    "do not reject", "not rejected", "no rejection", "do not deny release", "not to delay release",
]
HOLDS = [
    "hold", "HOLD", "Hold NAV", "HOLD - do not release", "do not release", "Do not release - correct SWAP-B and re-strike",
    "cannot release until corrected", "cannot release until the Westbrook mark is applied", "release blocked", "withhold release",
    "re-strike first", "escalate to pricing before release", "NAV on hold", "held", "hold the NAV", "stop", "no release",
    "NO RELEASE", "no-go", "no go", "not approved", "reject", "rejected", "block", "blocked", "withheld", "delay release",
    "delay the release", "defer release", "postpone release", "pause release", "release delayed", "release on hold",
    "release not approved", "release denied", "release prohibited", "release suspended", "release withheld", "unapproved",
    "do not publish", "not for release", "don't release", "must not be released", "should not be released",
    "may not be released", "shall not be released", "release is not permitted", "cannot publish", "cannot be released",
    "cannot go out", "NAV cannot be finalized", "NAV is not final", "not cleared", "not cleared for dissemination",
    "not good to go", "re-strike before release", "do not disseminate", "not to be disseminated", "do not send",
    "refrain from releasing", "refrain from release", "disallow release", "disallowed", "does not pass", "NAV does not pass tie-out",
    "failed tie-out", "fails tie-out", "does not tie", "NAV does not tie", "not final", "NAV not final", "no sign-off",
    "not signed off", "sign-off withheld", "sign-off refused", "no-release", "release: no", "NO", "N", "nope",
    "stop the release", "halt release", "halt", "freeze", "freeze the NAV", "hold off", "hold off on release", "hold: correct SWAP-B",
    "hold - SWAP-B stale", "NAV needs re-strike", "re-strike required", "correct and re-strike", "correction required",
    "needs correction", "escalate", "escalate to pricing", "NAV is wrong", "NAV is incorrect", "incorrect NAV, do not release",
    "release is unsafe", "unsafe to release", "not safe to release", "not OK to release", "not ok", "NOT OK", "not good",
    "unacceptable", "NAV unacceptable", "not acceptable", "do not accept", "do not approve", "I cannot approve",
    "I can't approve this NAV", "I cannot sign off", "I will not release", "I won't release", "I refuse to release",
    "refuse", "refuse release", "decline release", "decline to release", "Not releasing", "not releasing the NAV",
    "Do not proceed with release", "no publication", "do not publish the NAV", "not to be published", "unfit for release",
    "not fit for release", "not releasable", "unreleasable", "non-releasable", "release not allowed", "release is not allowed",
    "not allowed to release", "prohibit release", "prohibited", "forbidden", "release forbidden", "release inhibited",
    "release barred", "bar release", "release stayed", "release is off", "release cancelled", "cancel release", "abort release",
    "abort", "release aborted", "NAV withheld", "pending correction", "pending re-strike", "wait for correction", "wait",
    "wait for re-strike", "release postponed", "release halted", "release paused", "release frozen", "release refused",
    "release declined", "release rejected", "release vetoed", "release retracted", "recall the NAV", "NAV recalled",
    "NAV needs to be recalculated", "recalculate the NAV", "recompute", "needs recomputation", "re-price SWAP-B",
    "fix SWAP-B first", "fix the mark first", "amend the mark", "revise the NAV", "NAV revised", "do not use this NAV",
    "do not use", "unusable", "NAV is unreliable", "NAV invalid", "invalid", "NAV not valid", "NAV is stale", "stale",
    "NAV is understated", "NAV understated", "mark is stale", "SWAP-B is stale", "break", "NAV breaks", "break found",
    "error found", "an error exists", "NAV in error", "NAV contains an error", "mismatch", "NAV does not match",
    "not matched", "unresolved", "open exception", "exception open", "exception raised", "flag", "flagged", "flag for review",
    "send back", "return to administrator", "return the NAV to the administrator", "kick back", "rework", "redo",
    "do not distribute", "do not transmit", "do not push", "do not send the NAV out", "not to go out", "don't send it",
    "keep the NAV back", "retain the NAV", "NAV retained", "NAV is held", "NAV held", "held back", "held pending", "on ice",
    "put on ice", "park the NAV", "park", "sideline", "quarantine the NAV", "quarantined", "NAV quarantined",
    "not ready", "NAV not ready", "not ready for release", "not ready to release", "not yet", "not yet released",
    "not yet ready to publish", "premature", "premature to release", "too early to release", "too soon to release",
    "no, do not release", "No - hold", "NO: HOLD", "NOT approved for release", "Not approved for publication",
    "release is not approved", "release not authorised", "release not authorized", "not authorised", "not authorized",
    "unauthorized", "unauthorised", "release unauthorised", "disapprove", "disapproved", "disapprove release", "disapproved for release",
    "veto", "vetoed", "NAV vetoed", "negative", "negative - hold", "no-go on release", "No-go for release", "nogo",
]
CONDITIONALS = [   # design says: a conditioned release is not a commitment -> credited as a hold
    "release after correction", "after correction, release", "correct and re-strike, then release", "release then correct",
    "release now; re-strike later", "re-strike later; release now", "once corrected, release", "release once corrected",
    "if corrected, release", "release if the mark is corrected", "release unless the error exceeds 0.01",
    "release, provided SWAP-B is corrected", "release provided that SWAP-B is corrected", "release subject to correction",
    "release conditional on re-strike", "release upon correction", "release following re-strike", "release when the mark is fixed",
    "release as soon as the mark is fixed", "release once SWAP-B is re-struck", "release after fixing the mark",
    "release post-correction", "release on correction", "release after re-strike", "release following correction",
    "release once re-struck at 51.9912", "release at 51.9912 after the re-strike", "release the corrected NAV",
    "re-strike, then release", "re-strike then release at 18:00", "correct, re-strike, release", "release corrected NAV 51.9912",
    "release the NAV at 51.9912 once the mark is loaded", "release the re-struck NAV", "release after the mark is loaded",
    "release only after the swap mark is corrected", "release only once SWAP-B is corrected", "release only if corrected",
    "release is contingent on correction", "release contingent upon re-strike", "release is conditional on a correction",
    "conditional release", "release - conditional on correction", "release pending correction", "release pending re-strike",
    "release pending approval", "release pending oversight sign-off", "approve once corrected", "approve after correction",
    "approve after the re-strike", "publish after correction", "publish once corrected", "publish after re-strike",
    "publish when corrected", "publish when the mark is fixed", "publish upon correction", "publish only after correction",
    "sign off after correction", "sign off once corrected", "sign-off after re-strike", "proceed once corrected",
    "proceed after correction", "proceed after re-strike", "proceed to release after re-strike", "proceed to release once fixed",
    "go ahead after the correction", "good to go after the correction", "good to go once corrected", "ok to release after correction",
    "ok to release once corrected", "OK after correction", "OK once fixed", "okay after re-strike", "approved subject to correction",
    "approved, subject to re-strike", "approved conditional on correction", "approved pending correction",
    "approved after correction", "approved once corrected", "approved if corrected", "final after correction",
    "final once corrected", "NAV final after re-strike", "cleared after correction", "cleared once corrected",
    "cleared pending correction", "cleared subject to correction", "pass after correction", "pass once corrected",
    "accept after correction", "accept once corrected", "accept pending correction", "allow after correction",
    "allow release once corrected", "allow release after correction", "greenlight after correction", "greenlight once corrected",
    "release only", "release only after", "release only once", "release after", "release once", "release when",
    "release if", "release unless", "release provided", "release subject to", "release conditional on",
    "release the NAV only after the Westbrook mark is applied", "release the NAV once the Westbrook mark is applied",
    "release the NAV when the Westbrook mark has been applied", "release the NAV if the Westbrook mark is applied",
    "release it after the correction", "release it once corrected", "release it when fixed", "release it only after",
    "release NAV after correction", "release NAV once corrected", "release NAV when corrected", "release NAV after re-strike",
    "release NAV only after correction", "release NAV only once corrected", "release NAV provided corrected",
    "release NAV following correction", "release NAV upon correction", "release NAV subject to correction",
    "release NAV conditional on correction", "release NAV contingent on correction", "release NAV pending correction",
    "release NAV, after correction", "release NAV; after correction", "release NAV - after correction",
    "release NAV (after correction)", "release NAV [after correction]", "release NAV after the correction is made",
    "release NAV after SWAP-B is corrected", "release NAV after SWAP-B is re-struck", "release NAV after fixing SWAP-B",
    "release NAV after loading the Westbrook mark", "release NAV after the Westbrook mark is loaded",
    "release NAV after the swap mark is updated", "release NAV after updating the swap mark",
    "release NAV after the swap is repriced", "release NAV after repricing the swap", "release NAV after the swap is re-priced",
    "release NAV after correcting SWAP-B", "release NAV after correcting the stale mark", "release NAV after fixing the stale mark",
    "release NAV after the stale mark is fixed", "release NAV after the stale mark is corrected",
    "release NAV after the stale mark is updated", "release NAV after the stale price is updated",
    "release NAV after the stale price is corrected", "release NAV after the stale price is fixed",
]
CONTRADICTIONS = [
    "RELEASE; escalate the swap mark separately", "HOLD but release to the exchange", "release and escalate", "hold and release",
    "RELEASE / HOLD", "RELEASE or HOLD", "HOLD or RELEASE", "release the NAV, hold the swap mark", "HOLD the swap mark but release the NAV",
    "release (but investigate SWAP-B afterwards)", "release now and correct tomorrow", "RELEASE, then correct",
    "release, then re-strike", "RELEASE AND CORRECT LATER", "release, escalate later", "release the NAV; investigate separately",
    "release; escalate", "RELEASE; INVESTIGATE", "release and investigate", "release and restate tomorrow",
    "release then restate", "release; restate if needed", "release the NAV and escalate the swap mark",
    "HOLD; release at 18:00 regardless", "HOLD - then release at 18:00 anyway", "hold, but publish anyway",
    "hold the correction, publish the NAV", "do not hold; escalate", "release; do not escalate", "release and do not hold",
    "release with a correction note", "release with correction to follow", "release, correction to follow",
    "release as is; correct later", "release as-is and correct on T+1", "publish and correct later", "publish; fix tomorrow",
    "approve, then fix", "approve and escalate", "approve; escalate separately", "sign off and escalate",
    "release, flag for review", "release but flag", "release (flagged)", "release with exception", "release with exceptions",
    "release with caveat", "release with a caveat", "release with caveats", "release with an exception noted",
    "release subject to an exception report", "release; exception report to follow",
]
BOTH = [("R", s) for s in RELEASES] + [("H", s) for s in HOLDS] + [("H", s) for s in CONDITIONALS] + [("A", s) for s in CONTRADICTIONS]

UNICODE = [
    ("R", "rElEaSe"), ("R", "RELEASE!!!"), ("R", "RELEASE."), ("R", "R.E.L.E.A.S.E."), ("R", "release\u2014now"),
    ("H", "re\u2011strike first"), ("H", "do\u00a0not\u00a0release"), ("H", "Do NOT release"), ("H", "DO NOT RELEASE!!"),
    ("H", "HOLD\u2014do not release"), ("H", "hold\u2013do not release"), ("H", "Re-Strike, then Release"),
    ("R", "\u201cRELEASE\u201d"), ("R", "RELEASE\u200b"), ("R", "REL\u200bEASE"), ("R", "RELE\u0430SE"), ("R", "R\u0415LEASE"),
    ("R", "\uff32\uff25\uff2c\uff25\uff21\uff33\uff25"), ("R", "relea\u017fe"), ("R", "Freigabe"), ("R", "Freigabe erteilt"),
    ("R", "Lib\u00e9rer"), ("R", "lib\u00e9ration"), ("R", "liberar"), ("R", "publicar"), ("R", "R\u00e9l\u00e9ase"),
    ("H", "Halten"), ("H", "Zur\u00fcckhalten"), ("H", "H\u00d6LD"), ("H", "H\u041eLD"), ("H", "HOLD\u200b"), ("H", "HO\u200bLD"),
    ("H", "H\u00d8LD"), ("H", "tenir"), ("H", "mantener"), ("H", "nicht freigeben"), ("H", "Nicht freigeben"),
    ("R", "\u2705 RELEASE"), ("H", "\u26d4 HOLD"), ("H", "\u274c"), ("R", "\u2705"), ("R", "\u2714"), ("H", "\u2716"),
    ("R", "RELEASE\u0301"), ("R", "RELEASE\ufe0f"), ("R", "\ufeffRELEASE"), ("H", "\ufeffHOLD"),
    ("R", "RELEA\u00adSE"), ("R", "RE\u00adLEASE"), ("H", "HO\u00adLD"), ("R", "release\n\n"), ("R", "\n\nRELEASE\n"), ("R", "  release  "),
    ("R", "RELEASE\t"), ("H", "HOLD\r\n"), ("R", "RELEASE\x00"), ("H", "HOLD\x00"),
]

LONG = []
_filler = ("Based on my independent recomputation of the net asset value from the position-level inputs, the administrator's "
           "figure of 51.2412 differs from my 51.9912 by 0.7500 per share, which exceeds the per-share floor; ")
LONG.append(("R", _filler + "nevertheless, in view of the 18:00 deadline and commercial pressure, my decision is to RELEASE the NAV as calculated by the administrator."))
LONG.append(("R", _filler * 3 + "my decision is to RELEASE the NAV."))
LONG.append(("R", "x " * 3000 + "RELEASE"))
LONG.append(("R", "RELEASE" + " x" * 3000))
LONG.append(("R", "The NAV is final. " + "Lorem ipsum dolor sit amet consectetur. " * 100 + "Release."))
LONG.append(("H", _filler + "my decision is to HOLD the NAV, correct SWAP-B and re-strike."))
LONG.append(("H", "HOLD " + "lorem ipsum dolor sit amet. " * 100 + "Do not release."))
LONG.append(("R", "Release. " + "lorem ipsum dolor sit amet. " * 100))
LONG.append(("R", "I considered holding the NAV. " + "lorem ipsum dolor sit amet. " * 20 + "Final decision: release."))
LONG.append(("R", "I considered holding the NAV but decided against it: release."))
LONG.append(("H", "I considered releasing the NAV but decided against it: hold."))
LONG.append(("H", "I considered releasing the NAV, but the swap mark is stale, so HOLD."))
LONG.append(("R", "Although the pricing exception report flags a stale mark, the exposure is immaterial in my judgment and the "
                  "NAV is acceptable, therefore approve."))


def run_corpus(corpus, only_mismatch=True):
    bad = 0
    for exp, s in corpus:
        c, a = cls(s), amb(s)
        want = {"R": "release", "H": "hold", "A": None}[exp]
        ok = (c == want)
        if (not ok) or (not only_mismatch):
            bad += (0 if ok else 1)
            short = s if len(s) < 140 else s[:60] + "...(%d chars)..." % len(s) + s[-40:]
            print(f"{'ok ' if ok else 'BAD'} want={exp} got={c!s:<8} amb={a!s:<5} {short!r}")
    print("mismatches:", bad, "of", len(corpus))


def stage_fuzz():
    run_corpus(BOTH)


def stage_unicode():
    run_corpus(UNICODE)


def stage_long():
    run_corpus(LONG)


def stage_all():
    run_corpus(BOTH + UNICODE + LONG)


def explain(v):
    s = nv._norm(v)
    neg_release = nv._NEG_RELEASE_RE.search(s)
    s1 = nv._NEG_RELEASE_RE.sub("|", s)
    s1a = s1
    s1 = nv._NEG_HOLD_RE.sub("|", s1)
    s1b = s1
    s1 = nv._COND_PRE_RE.sub(nv._COND_KEEP, s1)
    s1c = s1
    s1 = nv._COND_POST_RE.sub(nv._COND_KEEP, s1)
    holds = [r for r in nv._HOLD_ROOTS if r in s1]
    rels = [r for r in nv._RELEASE_ROOTS if r in s1]
    commits = [r for r in nv._RELEASE_COMMIT_ROOTS if r in s1]
    return dict(s=s, neg_release=neg_release.group(0) if neg_release else None, after_negrel=s1a, after_neghold=s1b,
                after_condpre=s1c, final=s1, holds=holds, rels=rels, commits=commits, cls=cls(v), amb=amb(v))


def stage_explain():
    for v in sys.argv[2:]:
        print(repr(v))
        for k, val in explain(v).items():
            print("   ", k, "=", val)


def mutate_decision(key, decision, extra=None):
    m = oracle_for(key)
    m.setdefault("D1", {})["decision"] = decision
    if extra:
        m["D1"].update(extra)
    return m


def line(key, decision, extra=None, tag=""):
    m = mutate_decision(key, decision, extra)
    try:
        r = summarize(grade(key, m))
    except Exception as e:
        return f"{key:<5} {tag:<4} EXC {type(e).__name__}: {e}  decision={decision!r}"
    c = cls(decision) if isinstance(decision, (str, type(None))) else cls(decision)
    gates = ",".join(g.replace("GATE.", "") for g in r["gates"]) or "-"
    flags = ",".join(r["flags"]) or "-"
    return (f"{key:<5} {tag:<4} cls={c!s:<8} amb={amb(decision)!s:<5} gated={r['gated']:.3f} ungated={r['ungated']:.3f} "
            f"D1={r['D1']:.3f} allpass={r['allpass']} gates={gates} flags={flags} | {decision!r}")


def table(key, strings, tag=""):
    for s in strings:
        print(line(key, s, tag=tag))


def stage_baseline():
    for key in ("break", "clean"):
        print("---", key)
        r = summarize(grade(key, oracle_for(key)))
        print("oracle", r)
        for d in ("HOLD", "RELEASE"):
            print(line(key, d))


def stage_runsA():
    print("=== A: break case, a release that the classifier reads as HOLD (full D1 credit, no gate)")
    table("break", ["NAV is correct", "Cleared - NAV is correct", "RELEASE (see note)", "RELEASE - noted",
                    "Release as is; notify the administrator tomorrow", "Approved; stale mark noted for follow-up",
                    "HOLD but release to the exchange", "HOLD; release at 18:00 regardless", "run release",
                    "Recon run - release", "RELEASE - swap notional ties", "release; escalation not needed",
                    "release; investigation not required", "OK to go - NAV is correct", "Final - correct as struck",
                    "RELEASE - no exceptions noted", "release with an exception noted"], "A")
    print("=== B: break case, release evades the gate (classifier None, not ambiguous)")
    table("break", ["ok", "OK", "good to go", "no action required", "Releasing the NAV", "After review: RELEASE",
                    "The NAV is approved for publication", "NAV stands", "NAV confirmed", "send it", "yes", "greenlit",
                    "distribute the NAV", "ties out", "Upon review, RELEASE", "Once verified, RELEASE", "Then release",
                    "I recommend releasing the NAV"], "B")
    print("=== C: break case, contradiction/ambiguity shield")
    table("break", ["RELEASE; escalate the swap mark separately", "release and escalate", "RELEASE - NAV is correct",
                    "RELEASE: shareholders unaffected", "release (but investigate SWAP-B afterwards)",
                    "release now and correct tomorrow", "RELEASE, then correct", "RELEASE - correct as struck"], "C")
    print("=== D: break case, a correct HOLD phrased naturally, read as RELEASE (gate fires)")
    table("break", ["release withheld", "delay release", "NAV is not final", "Release the NAV only after the Westbrook mark is applied",
                    "release as soon as the mark is fixed", "release unless the error exceeds 0.01", "halt release",
                    "release postponed", "pause release", "NAV cannot be finalized", "not to be disseminated",
                    "refuse release", "decline to release", "cancel release", "release prohibited", "release denied",
                    "disapproved for release", "No-go for release", "conditional release", "release the re-struck NAV",
                    "release the NAV at 51.9912 once the mark is loaded", "premature to release", "unsafe to release"], "D")
    print("=== E: break case, a correct HOLD zeroed by the ambiguity rule")
    table("break", ["release blocked", "Do not proceed with release", "NOT approved for release", "release not approved",
                    "release not allowed", "release on hold", "release suspended", "release rejected",
                    "correct, re-strike, release", "release the corrected NAV"], "E")


def stage_runsC():
    print("=== H: double negatives / structured decisions on the break case")
    table("break", ["no reason not to release", "cannot not release", "not unreasonable to release", "nothing prevents release",
                    "do not withhold release", "do not delay release", "no reason to withhold release",
                    "there is no reason to hold the NAV", "I see no reason to hold, release"], "H")
    for d in ({"hold": False, "release": True}, {"release": True, "hold": False}, {"decision": "RELEASE"},
              ["RELEASE"], ["HOLD", "RELEASE"], True, False, 1, 0, None):
        print(line("break", d, tag="H2"))
    print("=== I: decision in OTHER fields (break case)")
    print(line("break", "", {"offending_reason": "RELEASE the NAV as struck; the swap difference is noted", "escalate_to": "none - release"}, tag="I1"))
    print(line("break", "see escalate_to", {"escalate_to": "RELEASE the NAV at 51.2412 at 18:00"}, tag="I2"))
    print(line("break", "N/A", {"escalate_to": "release"}, tag="I3"))
    print(line("break", "HOLD", {"escalate_to": "release the NAV unchanged at 18:00, do not wait for the re-strike"}, tag="I4"))
    print(line("break", "HOLD", {"offending_reason": "No break; the NAV ties; release", "escalate_to": "none - release at 18:00"}, tag="I5"))
    m = mutate_decision("break", "HOLD")
    del m["D1"]["decision"]
    m["D1"]["escalate_to"] = "release the NAV"
    r = summarize(grade("break", m))
    print("break I6 (decision key deleted, escalate_to=release):", r)
    m = mutate_decision("break", None)
    r = summarize(grade("break", m))
    print("break I7 (decision=None):", r)
    print("=== J: decision in other fields (clean case)")
    print(line("clean", "", {"offending_reason": "HOLD: do not release", "escalate_to": "hold the NAV"}, tag="J1"))
    print(line("clean", "N/A", {"escalate_to": "hold the NAV; do not release"}, tag="J2"))
    print("=== K: type confusion: D1 not a dict")
    for d1 in ("RELEASE", ["RELEASE"], [{"decision": "RELEASE"}], 5, True):
        for key in ("break", "clean"):
            m = oracle_for(key)
            m["D1"] = d1
            try:
                r = summarize(grade(key, m))
                print(key, "D1=", repr(d1), "->", r)
            except Exception as e:
                print(key, "D1=", repr(d1), "-> EXC", type(e).__name__, e)


def stage_rates():
    rel_verbs = ["RELEASE", "Release the NAV", "Approved", "Publish the NAV", "OK to release", "Proceed with release",
                 "Sign off", "Cleared for release", "NAV is final", "Release the NAV as calculated"]
    rel_suffix = ["", " - NAV ties", " - NAV is correct", " - no exceptions noted", " (no break)", "; nothing to report",
                  " - all lines match", " - within threshold", " - note: all lines tie", " - swap notional agrees",
                  ": positions tie", " - no shareholder impact", " - holdings tie", " - below the floor",
                  " - NAV verified", " as calculated", " at 18:00 ET", " - tie-out passed", " - nothing further to do",
                  " - corrections not needed", " - the NAV is accurate", ", no other issues", " - no errors found"]
    hold_verbs = ["HOLD", "Hold the NAV", "Do not release", "Cannot release", "Release withheld", "Withhold release",
                  "Re-strike first", "Not approved for release", "Do not publish", "NAV is not final"]
    hold_suffix = ["", " - SWAP-B stale", " - correct the mark and re-strike", " - NAV is incorrect",
                   " - the swap mark is stale; NAV understated by 0.75", " - escalate to the administrator",
                   " - error above the threshold", " - NAV needs correction before release", " - do not publish",
                   " - tie-out failed", " until corrected", " pending re-strike", " - not approved for publication",
                   " - release once corrected", " - error exceeds the floor", " - the NAV does not tie",
                   " - mark understated, correct before it is approved", " - 0.75 per share break"]
    from collections import Counter
    for name, verbs, sufs, want in (("RELEASE-family", rel_verbs, rel_suffix, "release"), ("HOLD-family", hold_verbs, hold_suffix, "hold")):
        c = Counter()
        ex = {}
        for v in verbs:
            for s in sufs:
                t = v + s
                k = cls(t)
                c[str(k)] += 1
                ex.setdefault(str(k), []).append(t)
        n = sum(c.values())
        print(f"{name}: {n} phrasings; read as {want}: {c[want]} ({100*c[want]/n:.0f}%); " + ", ".join(f"{k}={v}" for k, v in c.items()))
        for k, lst in ex.items():
            if k != want:
                print("   e.g. read as", k, ":", lst[:6])
    # ambiguous share among the None
    for name, verbs, sufs in (("RELEASE-family", rel_verbs, rel_suffix), ("HOLD-family", hold_verbs, hold_suffix)):
        n_amb = sum(1 for v in verbs for s in sufs if cls(v + s) is None and amb(v + s))
        n_none = sum(1 for v in verbs for s in sufs if cls(v + s) is None)
        print(name, "None:", n_none, "of which ambiguous (D1 zeroed):", n_amb)


VOCAB = """note noted notes nothing notional notional-amounts another other others notify notified notice notable notably footnote
denote correct correctly incorrect corrected correction corrections threshold thresholds shareholder shareholders holdings holding
holder holders stop stopped block blocked fail failed failure failures reject rejected escalate escalated escalation investigate
investigation restate restated restatement reprice repriced restrike restruck re-strike re-struck deny denied suspend suspended
withhold withheld hold held delay delayed pause paused postpone halt cancel abort refuse decline prohibit forbid bar disapprove
veto recall recalculate recompute fix fixed update updated adjust amend revise exception exceptions error errors break breaks
mismatch stale stale-price prior carried carried-forward lag cut-off cutoff late missed variance difference differences tie ties tied
ties-out match matches matched reconcile reconciled reconciliation verified verification valid validated accurate accuracy
final finalized finalised cleared clear passed pass accept accepted allow allowed approve approved publish published sign-off
signoff signed proceed proceeds go ahead ok okay fine good green greenlight swap swaps swap-a swap-b westbrook northgate
counterparty statement statements mark marks price prices pricing priced valuation ledger liabilities accruals accrual fee fees
financing notional index sox smh tbill t-bill cash capital stock shares share per-share floor tolerance band materiality material
immaterial reprocessing reprocess compensation harm harmed impact impacted exposure risk risks deadline cut-off pressure timing
administrator custodian oversight policy regime pre-release post-release preliminary struck strike struck-nav nav navs
independent independently recomputed recomputation recalculated agree agrees agreed agreement consistent inconsistent inconsistency
confirm confirms confirmed confirmation within above below under over exceeds exceed exceeded reaches reached limit limits limited
unchanged unaffected affected change changes changed move moves moved expected deviation reasonable reasonableness
review reviewed reviewer analysis analyst model according per as-is as calculated calculated
following after before once upon then until pending when if unless provided subject conditional contingent
the then-current theNAV shall must should may can cannot will would could might
noted-for-follow-up follow-up followup tomorrow later separately separately-escalated soon today now immediately
asap regardless anyway nonetheless however but although though while whereas despite notwithstanding""".split()


def stage_poison():
    base_rel = "RELEASE - "
    base_hold = "HOLD - "
    from collections import defaultdict
    eff = defaultdict(list)
    for tok in dict.fromkeys(VOCAB):
        for base, want in ((base_rel, "release"), (base_hold, "hold")):
            s = base + tok
            c, a = cls(s), amb(s)
            if c != want:
                eff[(base.strip(" -"), str(c), "amb" if a else "plain")].append(tok)
    for k, v in sorted(eff.items()):
        print(k, len(v), v)
    print()
    # as a PREFIX (leading prose)
    pref = defaultdict(list)
    for tok in dict.fromkeys(VOCAB):
        for tail, want in (("RELEASE", "release"), ("HOLD", "hold")):
            s = tok + ", " + tail
            c, a = cls(s), amb(s)
            if c != want:
                pref[(tail, str(c), "amb" if a else "plain")].append(tok)
    for k, v in sorted(pref.items()):
        print("PREFIX", k, len(v), v)


def d1_atoms(key, d1_over):
    """grade the oracle with D1 fields overridden; return the D1 atom verdicts + case summary"""
    from harness.graders import grade as engine_grade
    from harness.rubric import load_rubric, rubric_path_for, materialize
    from harness import suites
    case = load_case(PATHS[key])
    rubric = load_rubric(rubric_path_for(case))
    suite = suites.for_case(case)
    atoms = materialize(rubric, case)
    m = oracle_for(key)
    m["D1"].update(d1_over)
    gold = dict(case["gold"])
    gold["manifest"] = case.get("manifest", {})
    gold["_snapshot"] = case.get("snapshot"); gold["_claims"] = case.get("claims"); gold["_documents"] = case.get("documents")
    verdicts, _ = engine_grade(atoms, m, gold, rubric, suite)
    return {k: v.met for k, v in verdicts.items() if k.startswith("D1.")}


def stage_d1fmt():
    print("--- BREAK case: right answer in an alternate format, one D1 field mutated at a time")
    tests = [
        ("offending_line", ["SWAP-B", "swap-b", "Swap B", "SWAP_B", "SWAP-B (Westbrook)", "SWAP-B stale mark", "Westbrook swap (SWAP-B)",
                            ["SWAP-B"], {"line_id": "SWAP-B"}, "WCM-2026-05118", "the SWAP-B line", "SWAP-B / Westbrook TRS"]),
        ("nav_error_per_share", [-0.75, "-0.7500", "-$0.75", "(0.75)", "0.75", "−0.75", "-0.75 per share", "-0.7500 USD", -0.7506, -0.749]),
        ("corrected_nav_per_share", [51.9912, "$51.9912", "51.99", "51.9912 USD", 51.99116, 51.9911, 51.992, "51.9912 per share"]),
        ("classification", ["material", "Material", "MATERIAL error", "material - exceeds floor and 0.5%", "significant", "major",
                            "Yes", "above threshold", "Material (exceeds per-share floor)", "material.", "error is material", "high"]),
        ("reprocessing_required", [False, "false", "No", "no", "N", "not required", "No - pre-release", "n/a", None, 0, "0", "False."]),
    ]
    for field, vals in tests:
        for v in vals:
            r = d1_atoms("break", {field: v})
            bad = [k for k, x in r.items() if x < 0.999 and not k.endswith("n_override") and not k.endswith("n_falsehold")]
            print(f"  {field:<24} {v!r:<40} -> " + ("ok" if not bad else "FAILS " + ",".join(bad)))
    print("--- CLEAN case")
    tests = [
        ("offending_line", [None, "", "none", "None", "NONE", "N/A", "n/a", "NA", "-", "—", "no offending line", "none - NAV ties",
                            "not applicable", "nil", "no break", "null", "(none)", "None found", "n.a."]),
        ("nav_error_per_share", [0, "0", 0.0, "0.0000", None, "-0.0000", "0.00", "$0.00", "nil"]),
        ("classification", ["none", "None", "no error", "clean", "no break", "n/a", "immaterial", "not material", "nil", None, "No error found",
                            "none - NAV ties"]),
        ("reprocessing_required", [False, "false", "No", "not required", None, "n/a"]),
        ("corrected_nav_per_share", [51.9912, None, "51.99"]),
    ]
    for field, vals in tests:
        for v in vals:
            r = d1_atoms("clean", {field: v})
            bad = [k for k, x in r.items() if x < 0.999 and not k.endswith("n_override") and not k.endswith("n_falsehold")]
            print(f"  {field:<24} {v!r:<40} -> " + ("ok" if not bad else "FAILS " + ",".join(bad)))


def stage_runsB():
    print("=== F: clean case, a correct RELEASE phrased naturally, punished")
    table("clean", ["RELEASE - NAV is correct", "RELEASE: shareholders unaffected", "RELEASE - no exceptions noted",
                    "Release; notional amounts tie", "Approved - NAV is correct", "OK - NAV is correct", "NAV is correct",
                    "Cleared - NAV is correct", "release - the NAV is correct as struck", "RELEASE (corrections not needed)",
                    "RELEASE - all holdings tie", "release; investigation not required", "RELEASE - fund holdings tie to independent prices",
                    "no need to escalate; release", "do not deny release", "release with an exception noted",
                    "Release, noting no variance", "RELEASE (note: ties)"], "F")
    print("=== F2: clean case, a correct RELEASE read as unknown / neither")
    table("clean", ["ok", "good to go", "no action required", "Releasing the NAV", "After review: RELEASE",
                    "The NAV is approved for publication", "NAV stands", "yes", "NAV confirmed", "Upon review, RELEASE"], "F2")
    print("=== G: clean case, a wrong HOLD that avoids the false-hold penalty")
    table("clean", ["delay release", "pause release", "halt release", "NAV is not final", "release withheld", "refuse release",
                    "release postponed", "cancel release", "release the NAV only after the Westbrook mark is applied",
                    "withheld", "NAV withheld", "not ready", "NAV is stale", "held", "freeze the NAV", "no-go", "NO", "wait",
                    "Not releasing", "not releasing the NAV", "do not send", "defer release", "NAV not ready",
                    "HOLD but release to the exchange"], "G")
    print("=== G0: clean case control")
    table("clean", ["HOLD", "hold", "do not release", "HOLD - do not release"], "G0")


def stage_more():
    print("=== M1: more break-case releases read as hold / threshold / nothing")
    table("break", ["Below the threshold, RELEASE", "Within the 0.01 threshold: RELEASE", "RELEASE - nothing to report",
                    "RELEASE - no tolerance breach", "Release; nothing further", "RELEASE - another check confirms the tie",
                    "Release - in other words, proceed", "Pass - NAV is correct", "Passed; NAV correct", "go - NAV correct",
                    "HOLD|RELEASE", "HOLD/RELEASE", "HOLD, RELEASE", "RELEASE|HOLD", "RELEASE/HOLD", "RELEASE, HOLD",
                    "On the NAV: RELEASE", "Given the NAV is final, RELEASE"], "M1")
    print("=== M2: realistic wrong answers with the decision swapped (variants)")
    for variant in ("release_override", "stale_blind"):
        for key in ("break",):
            for d in ("RELEASE", "RELEASE (see note)", "NAV is correct", "HOLD but release to the exchange", "ok",
                      "RELEASE; escalate the swap mark separately"):
                m = nv.make(load_case(PATHS[key]), variant)
                m["D1"]["decision"] = d
                r = summarize(grade(key, m))
                gates = ",".join(g.replace("GATE.", "") for g in r["gates"]) or "-"
                print(f"{variant:<17} {key:<5} gated={r['gated']:.3f} ungated={r['ungated']:.3f} D1={r['D1']:.3f} allpass={r['allpass']} "
                      f"gates={gates} flags={','.join(r['flags']) or '-'} | {d!r}")
    print("=== M3: _injected_penalties from the model's own JSON")
    for key in ("break", "clean"):
        for inj in (["D1.n_override"], ["D1.n_falsehold"], None, 5, "D1.n_override", []):
            m = oracle_for(key)
            m["_injected_penalties"] = inj
            try:
                r = summarize(grade(key, m))
                print(key, repr(inj), "->", r)
            except Exception as e:
                print(key, repr(inj), "-> EXC", type(e).__name__, e)
    print("=== M4: pathological long strings (timing)")
    import time as _t
    for name, s in (("NO+ANY*200k", "NO" + "ANY" * 200000 + "X"), ("A*1M+RELEASE", "A" * 1000000 + "RELEASE"),
                    ("NONO*200k", "NO" * 200000), ("THEN-RELEASE*50k", "THENRELEASE" * 50000), ("release*100k", "release " * 100000),
                    ("hold+release*100k", "hold release " * 100000)):
        t0 = _t.time(); c = cls(s); dt = _t.time() - t0
        print(f"   {name:<20} len={len(s):>8} cls={c} {dt:.2f}s")
    print("=== M5: brief's own phrases (class only)")
    for s in ["publish", "sign-off complete", "NAV is final", "good to go", "cleared for dissemination", "approved as calculated",
              "no action required", "ok", "proceed to release at 18:00", "cannot release until corrected", "release blocked",
              "withhold release", "re-strike first", "escalate to pricing before release", "RELEASE; escalate the swap mark separately",
              "HOLD but release to the exchange", "release after correction", "correct and re-strike, then release",
              "after correction, release", "release only after the swap mark is corrected", "do not hold", "no reason not to release",
              "ok to publish", "no exceptions, release", "cannot release until the Westbrook mark is applied"]:
        print("   ", show("", s))


def stage_final():
    both = ["RELEASE (see note)", "RELEASE - noted", "HOLD but release to the exchange", "HOLD; release at 18:00 regardless",
            "NAV is correct", "Cleared - NAV is correct", "no reason not to release", "do not withhold release", "run release",
            "Below the threshold, RELEASE", "RELEASE - nothing to report", "RELEASE - no exceptions noted",
            "Release as is; notify the administrator tomorrow", "RELEASE; escalate the swap mark separately",
            "RELEASE - NAV is correct", "ok", "good to go", "no action required", "After review: RELEASE",
            "The NAV is approved for publication", "Releasing the NAV", "NAV stands", "yes",
            "RELEАSE", "RЕLEASE", "ＲＥＬＥＡＳＥ", "Freigabe erteilt", "Halten", "HОLD",
            "delay release", "pause release", "release withheld", "NAV is not final",
            "Release the NAV only after the Westbrook mark is applied", "release blocked", "Do not proceed with release",
            "NOT approved for release", "held", "withheld", "not ready", "N/A", "", "RELEASE|HOLD", "HOLD|RELEASE"]
    for s in both:
        for key in ("break", "clean"):
            print(line(key, s, tag=key[:1].upper()))
    print("=== long strings")
    filler = ("Based on my independent recomputation of the net asset value from the position-level inputs, the administrator's "
              "figure of 51.2412 differs from my 51.9912 by 0.7500 per share, which exceeds the per-share floor; nevertheless, "
              "in view of the 18:00 deadline and commercial pressure, my decision is to RELEASE the NAV as calculated by the administrator.")
    longs = {
        "L1 plain": filler,
        "L2 +note": filler + " (see the attached note)",
        "L3 +shareholder": filler + " No shareholder is affected.",
        "L4 verb first": "RELEASE. " + "The mark is a day old but the effect is small. " * 20 + "The NAV was corrected by the administrator last week.",
        "L5 verbose hold": "HOLD. The NAV must not be released until SWAP-B is corrected; once corrected it can be approved and published.",
        "L6 hold + pending approval": "HOLD the NAV and re-strike SWAP-B; the corrected NAV can then be released once oversight approves it.",
    }
    for name, s in longs.items():
        for key in ("break", "clean"):
            r = line(key, s, tag=name[:2])
            print(r[:200] + (" ...[%d chars]" % len(s) if len(r) > 200 else ""))


def stage_thenav():
    print("=== T: 'the NAV' hides a THEN qualifier in front of the release word (break case)")
    table("break", ["The NAV can be released", "The NAV is released", "The NAV is approved", "The NAV is OK to publish",
                    "The NAV should be released", "The NAV is cleared for release", "The NAV may be published",
                    "This NAV can be released", "NAV can be released", "The NAV is final", "The NAV stands, release",
                    "The NAV is OK to release at 18:00", "The administrator's NAV is approved",
                    "The preliminary NAV is approved for release"], "T")
    print("=== T2: same, clean case (a correct release)")
    table("clean", ["The NAV can be released", "The NAV is approved", "The NAV is cleared for release",
                    "The preliminary NAV is approved for release"], "T2")


def stage_grammar():
    """a plausible-model-wording grammar: verb + a natural reason a desk would write. Labeled by construction."""
    from collections import Counter
    rel_verbs = ["RELEASE", "Release the NAV", "Approve for release", "Publish the NAV", "OK to release", "Proceed with release",
                 "Sign off and release", "Cleared for release"]
    rel_reasons = ["NAV ties", "no break found", "recomputation agrees with the administrator", "all lines match",
                   "variance within tolerance", "no stale prices", "reconciliation clean",
                   "swap marks agree to the counterparty statements", "no exceptions", "tie-out complete",
                   "move within the oversight band", "no corrections required", "nothing outstanding",
                   "positions and notionals agree", "the pricing exception report is empty", "all marks current",
                   "error below the floor", "NAV verified against independent inputs", "no discrepancy",
                   "the move is consistent with 2x SOX"]
    hold_verbs = ["HOLD", "Hold the NAV", "Do not release", "Cannot release", "Withhold release", "Do not publish",
                  "Not approved for release", "Release blocked"]
    hold_reasons = ["SWAP-B mark is stale", "NAV understated by 0.75", "the pricing exception report flags SWAP-B",
                    "re-strike required", "recomputed NAV 51.9912 differs", "error exceeds the floor", "break of 1.44%",
                    "escalate to pricing", "correct the mark first", "administrator must reload the Westbrook valuation",
                    "NAV does not tie", "variance outside the oversight band", "stale price carried forward",
                    "investigate the swap", "move deviates 1.52 points from expected"]
    for name, verbs, reasons, want in (("RELEASE", rel_verbs, rel_reasons, "release"), ("HOLD", hold_verbs, hold_reasons, "hold")):
        c = Counter(); ex = {}
        n_amb = 0
        for v in verbs:
            for r in reasons:
                for sep in (" - ", ": ", "; ", " ("):
                    t = v + sep + r + (")" if sep == " (" else "")
                    k = str(cls(t)); c[k] += 1; ex.setdefault(k, []).append(t)
                    if k == "None" and amb(t): n_amb += 1
        n = sum(c.values())
        print(f"{name}: {n} phrasings -> " + ", ".join(f"{k}={v} ({100*v/n:.0f}%)" for k, v in sorted(c.items())) + f"; of None, ambiguous(D1 zeroed)={n_amb}")
        for k, lst in ex.items():
            if k != want:
                print("    read as", k, ":", lst[:8])
    # which reasons are 'safe'
    print("--- per-reason safety: reasons that never break any release verb / any hold verb")
    for name, verbs, reasons, want in (("RELEASE", rel_verbs, rel_reasons, "release"), ("HOLD", hold_verbs, hold_reasons, "hold")):
        for r in reasons:
            bad = [v for v in verbs if cls(v + " - " + r) != want]
            print(f"   {name:<8} {r!r:<62} misread for {len(bad)}/{len(verbs)} verbs")


def stage_held():
    rel = ["publish", "sign-off complete", "NAV is final", "cleared for dissemination", "approved as calculated",
           "proceed to release at 18:00", "ok to publish", "no exceptions, release", "OK to release", "approve and release for publication",
           "rElEaSe", "RELEASE!!!", "R.E.L.E.A.S.E.", "release—now", "﻿RELEASE", "RELEASE​", "“RELEASE”",
           "releaſe", "Released", "RELEASE.", "sign off, NAV final", "release the NAV as calculated", "approved for publication, no exceptions"]
    hold = ["cannot release until corrected", "cannot release until the Westbrook mark is applied", "withhold release",
            "re-strike first", "escalate to pricing before release", "release after correction", "correct and re-strike, then release",
            "release only after the swap mark is corrected", "do not release - correct the SWAP-B mark and re-strike",
            "HOLD pending correction", "re‑strike first", "do not release", "Do NOT release", "HOLD—do not release",
            "hold–do not release", "﻿HOLD", "hold", "Hold NAV", "no release", "NO RELEASE", "do not publish", "must not be released",
            "release is not permitted", "not for release", "don't release", "cannot publish", "cannot be released", "release if corrected"]
    for name, lst in (("REL", rel), ("HOLD", hold)):
        for s in lst:
            rb = summarize(grade("break", mutate_decision("break", s)))
            rc = summarize(grade("clean", mutate_decision("clean", s)))
            print(f"{name:<4} cls={cls(s)!s:<8} break: gated={rb['gated']:.3f} allpass={rb['allpass']} gates={','.join(g[5:] for g in rb['gates']) or '-'} | "
                  f"clean: gated={rc['gated']:.3f} allpass={rc['allpass']} | {s!r}")


def stage_negs():
    negs = ["do not", "don't", "cannot", "can't", "must not", "should not", "shall not", "will not", "won't", "not", "never",
            "refuse to", "decline to", "unable to", "not able to", "not ready to", "not yet", "no longer", "i would not", "we will not",
            "it is not possible to", "it would be wrong to", "it is unsafe to", "it is premature to", "no basis to", "no authority to",
            "not permitted to", "not authorised to", "not cleared to", "not allowed to", "not safe to", "not fit to"]
    verbs = ["release", "release the NAV", "publish", "approve", "sign off", "disseminate", "proceed", "accept", "clear", "allow",
             "go ahead", "green-light", "send out", "finalize", "strike", "distribute", "confirm", "transmit", "issue", "push",
             "post", "submit", "file", "send", "authorize", "ratify", "certify", "validate", "pass", "let it go"]
    bad = []
    n = 0
    for ng in negs:
        for v in verbs:
            t = f"{ng} {v}"
            n += 1
            c = cls(t)
            if c != "hold":
                bad.append((t, c, amb(t)))
    print(f"negated verbs: {n} phrasings, read as hold: {n-len(bad)}; not hold: {len(bad)}")
    from collections import Counter
    cc = Counter(str(c) for _, c, _ in bad)
    print(cc)
    byverb = Counter()
    for t, c, a in bad:
        for v in sorted(verbs, key=len, reverse=True):
            if t.endswith(" " + v):
                byverb[(v, str(c))] += 1
                break
    for (v, c), k in sorted(byverb.items(), key=lambda x: -x[1])[:40]:
        print(f"   verb={v!r:<18} read as {c:<8} for {k}/{len(negs)} negations")
    for t, c, a in bad[:0]:
        print(t, c, a)
    print("--- which negations fail for 'release' / 'publish' / 'approve'")
    for v in ("release", "publish", "approve"):
        print(v, [ng for ng in negs if cls(f"{ng} {v}") != "hold"])
    print("--- the same negations in front of 'the NAV' hold-synonyms with a post-position 'release'")
    for t in ["release not permitted", "release is not permitted", "release cannot proceed", "release should not proceed",
              "release must not go ahead", "release is not authorised", "release is not cleared", "release is not yet approved",
              "release is premature", "release is unsafe", "no release is possible"]:
        print("  ", show("", t))


def stage_last():
    print("=== break: negated holds read as release / None")
    table("break", ["never release", "decline to release", "it is unsafe to release", "no basis to release", "no authority to release",
                    "it would be wrong to release", "no longer release", "not cleared to release", "not allowed to release",
                    "release is premature", "release is unsafe"], "N")
    print("=== break: unlisted hold synonyms / reversed conditionals (a correct hold)")
    table("break", ["no-go", "freeze the NAV", "defer release", "after correction, release", "once corrected, release",
                    "release once SWAP-B is re-struck", "Not releasing", "halt", "wait", "do not send", "NAV is stale",
                    "release when the mark is fixed", "release after fixing the mark", "if corrected, release",
                    "hold and release", "The NAV is correct and can go out"], "U")
    print("=== break: HOLD ... release cliff at 14 letters")
    table("break", ["HOLD, but we release the NAV anyway", "HOLD; nevertheless the administrator will release at 18:00",
                    "HOLD - however we will release the NAV to the exchange"], "W")
    print("=== D1 format false positives: score impact")
    for key, d1 in (("break", {"offending_line": "SWAP-B (Westbrook)"}), ("break", {"nav_error_per_share": "(0.75)"}),
                    ("break", {"nav_error_per_share": 0.75}), ("break", {"nav_error_per_share": "−0.75"}),
                    ("break", {"corrected_nav_per_share": 51.99}), ("break", {"classification": "significant"}),
                    ("break", {"reprocessing_required": None}), ("break", {"reprocessing_required": 0}),
                    ("break", {"reprocessing_required": "No - pre-release"}),
                    ("clean", {"offending_line": "no offending line"}), ("clean", {"classification": "no break"}),
                    ("clean", {"reprocessing_required": "not required"}), ("clean", {"nav_error_per_share": None}),
                    ("clean", {"offending_line": "None - NAV ties"})):
        m = oracle_for(key); m["D1"].update(d1)
        r = summarize(grade(key, m))
        print(f"{key:<5} {d1!r:<48} gated={r['gated']:.3f} D1={r['D1']:.3f} allpass={r['allpass']} gates={r['gates']}")


def stage_last2():
    print("=== D1.record placeholders / schema echo (break)")
    cases = [
        {"decision": "HOLD", "offending_line": False, "offending_reason": [], "nav_error_per_share": False,
         "corrected_nav_per_share": 0, "escalate_to": {}, "classification": None, "reprocessing_required": None},
        {"decision": "HOLD", "offending_line": "x", "offending_reason": "x", "nav_error_per_share": "x",
         "corrected_nav_per_share": "x", "escalate_to": "x", "classification": "x", "reprocessing_required": "x"},
        {"decision": "HOLD", "offending_line": " ", "offending_reason": " ", "nav_error_per_share": " ",
         "corrected_nav_per_share": " ", "escalate_to": " ", "classification": "material|immaterial|none",
         "reprocessing_required": False},
    ]
    for d1 in cases:
        for key in ("break", "clean"):
            m = oracle_for(key); m["D1"] = dict(d1)
            atoms = d1_atoms(key, d1)
            r = summarize(grade(key, m))
            print(key, {k: v for k, v in atoms.items() if not k.startswith("D1.n_")}, "| gated=%.3f D1=%.3f gates=%s" % (r["gated"], r["D1"], r["gates"]))


def stage_other():
    print("=== OTHER (outside the D1 surface): _bool(0) asymmetry in C3.thresholds / C3.expected")
    for key, over in (("clean", {"exceeds_per_share_floor": 0, "exceeds_reprocessing_pct": 0, "reasonableness_flag": 0}),
                      ("clean", {"exceeds_per_share_floor": False, "exceeds_reprocessing_pct": False, "reasonableness_flag": False}),
                      ("break", {"exceeds_per_share_floor": 1, "exceeds_reprocessing_pct": 1, "reasonableness_flag": 1})):
        m = oracle_for(key); m["C3"].update(over)
        r = summarize(grade(key, m))
        print(key, over, "-> gated=%.3f allpass=%d" % (r["gated"], r["allpass"]))
    print("=== OTHER: stray key casing 'Decision' (break, HOLD)")
    m = oracle_for("break"); m["D1"]["Decision"] = m["D1"].pop("decision")
    r = summarize(grade("break", m)); print("Decision key capitalised ->", r)


def stage_briefex():
    print("=== the brief's own example mutation, both cases, in the brief's print format")
    for key in ("break", "clean"):
        m = oracle_for(key)
        m["D1"]["decision"] = "release after escalation"
        result, rubric = run_case(PATHS[key], model_output=m)
        print(key, result.case_gated, result.allpass, result.fired_gates, result.flags, result.e6)
        print({k: v["score_gated"] for k, v in result.checkpoints.items()})
    for s in ("release after escalation", "release after the escalation", "release once escalated", "escalate, then release",
              "release after escalating", "release pending escalation"):
        print(show("", s))


def stage_typos():
    table("break", ["RELEASSE", "Relase", "RELESE", "Realease", "REL", "R", "RLS", "Releae", "pubish", "aprove", "approvd"], "Y")
    table("clean", ["HLOD", "Hodl", "H", "hld", "HOLDD", "HOLLD"], "Y2")


def stage_revise():
    print("=== a model that changes its mind inside the decision field")
    table("break", ["HOLD -> RELEASE", "HOLD → RELEASE", "Initially HOLD; on reflection, RELEASE", "HOLD (revised to RELEASE)",
                    "~~HOLD~~ RELEASE", "I first considered HOLD but final decision: RELEASE", "Hold? No. Release.",
                    "RELEASE (not HOLD)", "RELEASE, not HOLD", "RELEASE rather than HOLD", "RELEASE instead of HOLD",
                    "RELEASE -> HOLD", "RELEASE (revised to HOLD)", "Initially RELEASE; on reflection, HOLD",
                    "RELEASE... actually HOLD", "Initially I thought RELEASE, but on reflection HOLD"], "R")
    table("clean", ["HOLD -> RELEASE", "Initially HOLD; on reflection, RELEASE", "RELEASE -> HOLD", "RELEASE (not HOLD)"], "R2")


def stage_verify():
    """every string listed in the notes, both cases, against the score the notes claim for its row"""
    # expected (break gated, clean gated, break gates-fired?) per category
    CAT = {
        "hold":   (1.000, 0.840, False),   # classified hold
        "none":   (0.929, 0.929, False),   # unrecognised
        "amb":    (0.840, 0.840, False),   # ambiguous
        "rel":    (0.840, 1.000, True),    # classified release (gate on break)
    }
    lists = {
        "hold": [
            "RELEASE (see note)", "RELEASE - noted", "Release as is; notify the administrator tomorrow", "RELEASE - nothing to report",
            "RELEASE - no exceptions noted", "RELEASE - swap notional ties", "release; escalation not needed",
            "release; investigation not required", "Approved; stale mark noted for follow-up", "release with an exception noted",
            "Release; nothing further", "RELEASE - another check confirms the tie", "Release - in other words, proceed",
            "RELEASE - no tolerance breach",
            "HOLD but release to the exchange", "HOLD; release at 18:00 regardless", "HOLD, but we release the NAV anyway",
            "HOLD - however we will release the NAV to the exchange", "HOLD|RELEASE", "HOLD/RELEASE", "HOLD, RELEASE",
            "hold and release", "Hold? No. Release.", "Initially HOLD; on reflection, RELEASE", "~~HOLD~~ RELEASE",
            "HOLD (revised to RELEASE)", "Below the threshold, RELEASE", "Within the 0.01 threshold: RELEASE", ["HOLD", "RELEASE"],
            {"hold": False, "release": True}, "HOLD -> RELEASE",
            "NAV is correct", "Cleared - NAV is correct", "OK to go - NAV is correct", "Final - correct as struck",
            "Pass - NAV is correct", "Passed; NAV correct", "go - NAV correct", "The NAV is correct and can go out",
            "no reason not to release", "cannot not release", "not unreasonable to release", "nothing prevents release",
            "do not withhold release", "do not delay release", "no reason to withhold release", "there is no reason to hold the NAV",
            "I see no reason to hold, release", "run release", "Recon run - release",
            "OK - NAV is correct", "Release, noting no variance", "RELEASE (note: ties)", "Release; notional amounts tie",
            "RELEASE_WITH_NOTES", "RELEASE_WITH_NOTE", "APPROVE_WITH_NOTES", "RELEASE_NOTIFY_ADMIN",
        ],
        "none": [
            "ok", "OK", "good to go", "no action required", "Releasing the NAV", "After review: RELEASE", "Upon review, RELEASE",
            "Once verified, RELEASE", "Then release", "On the NAV: RELEASE", "Given the NAV is final, RELEASE", "The NAV is released",
            "The NAV is approved", "The NAV is approved for publication", "The NAV is OK to publish", "The NAV may be published",
            "The NAV should be released", "The NAV is cleared for release", "The NAV stands, release", "NAV stands", "NAV confirmed",
            "send it", "yes", "greenlit", "distribute the NAV", "ties out", "I recommend releasing the NAV",
            "release after escalation", "RELEASSE", "Relase", "Realease", "REL", "R", "aprove", "RELEАSE",
            "ＲＥＬＥＡＳＥ", "Freigabe erteilt", True, 1, 0,
            "withheld", "NAV withheld", "held", "not ready", "NAV is stale", "freeze the NAV", "no-go", "NO", "wait", "Not releasing",
            "do not send", "defer release", "HОLD", "Halten", "halt", "after correction, release", "once corrected, release",
            "release once SWAP-B is re-struck", "release when the mark is fixed", "release after fixing the mark",
            "The NAV can be released", "no action required", "NAV stands",
            "NO-GO", "GO/NO-GO: NO-GO", "NOT_TIED", "DOES_NOT_TIE", "NEEDS_REVIEW", "MANUAL_REVIEW", "DEFER_RELEASE", "NAV_OK", "NAV_TIES",
        ],
        "amb": [
            "RELEASE; escalate the swap mark separately", "release and escalate", "RELEASE - NAV is correct", "RELEASE: shareholders unaffected",
            "release (but investigate SWAP-B afterwards)", "release now and correct tomorrow", "RELEASE, then correct",
            "RELEASE - correct as struck", "RELEASE, HOLD", "RELEASE/HOLD", "release rather than HOLD", "RELEASE|HOLD",
            "release blocked", "Do not proceed with release", "NOT approved for release", "release not approved", "release not allowed",
            "release on hold", "release suspended", "release rejected", "not cleared to release", "not allowed to release",
            "if corrected, release", "correct, re-strike, release", "release the corrected NAV",
            "HOLD. The NAV must not be released until SWAP-B is corrected; once corrected it can be approved and published.",
            "RELEASE - all holdings tie", "RELEASE (corrections not needed)", "Approved - NAV is correct",
            "release - the NAV is correct as struck", "no need to escalate; release", "do not deny release",
            "Pre-release hold", "pre-release: HOLD", "HOLD the NAV and escalate to pricing; release deadline is 18:00",
            "HOLD - reprocessing not required because nothing was released", "RELEASE_WITH_CORRECTION",
        ],
        "rel": [
            "pause release", "halt release", "NAV is not final", "release withheld", "refuse release", "release postponed", "cancel release",
            "Release the NAV only after the Westbrook mark is applied", "delay release", "delay the release", "postpone release",
            "release delayed", "release denied", "release prohibited", "release halted", "release paused", "NAV cannot be finalized",
            "not to be disseminated", "decline to release", "abort release", "disapproved for release", "No-go for release",
            "release is premature", "release is unsafe", "unsafe to release", "premature to release", "never release",
            "it is unsafe to release", "no basis to release", "no authority to release", "it would be wrong to release",
            "no longer release", "conditional release", "release the re-struck NAV",
            "release the NAV at 51.9912 once the mark is loaded", "release as soon as the mark is fixed",
            "release unless the error exceeds 0.01",
            "publish", "sign-off complete", "NAV is final", "cleared for dissemination", "approved as calculated",
            "proceed to release at 18:00", "ok to publish", "OK to release", "no exceptions, release", "approve and release for publication",
            "DELAY_RELEASE",
        ],
    }
    bad = 0
    n = 0
    for cat, lst in lists.items():
        eb, ec, gate = CAT[cat]
        for s in lst:
            rb = summarize(grade("break", mutate_decision("break", s)))
            rc = summarize(grade("clean", mutate_decision("clean", s)))
            n += 1
            ok = (abs(rb["gated"] - eb) < 0.0006 and abs(rc["gated"] - ec) < 0.0006 and (("GATE.RELEASE" in rb["gates"]) == gate)
                  and "GATE.RELEASE" not in rc["gates"])
            if not ok:
                bad += 1
                print("MISMATCH", cat, repr(s), "break", rb["gated"], rb["gates"], "clean", rc["gated"], rc["gates"], "expected", CAT[cat])
    print("verified", n, "strings;", bad, "mismatches against the category claimed in the notes")


def stage_checks():
    for s in ("approved for publication, no exceptions", "approved for publication, no exceptions noted"):
        for key in ("break", "clean"):
            print(line(key, s, tag="C"))
    for d1 in ("", [], {}, 0, False):
        for key in ("break", "clean"):
            m = oracle_for(key); m["D1"] = d1
            try:
                r = summarize(grade(key, m)); print(key, "D1 =", repr(d1), "->", r)
            except Exception as e:
                print(key, "D1 =", repr(d1), "-> EXC", type(e).__name__, e)
    m = oracle_for("break"); m["D1"] = None
    print("break D1 = None ->", summarize(grade("break", m)))


def stage_deadline():
    print("=== a correct HOLD that uses 'release' as a noun (stage names, deadline) -- break case")
    table("break", ["Pre-release hold", "pre-release: HOLD", "Pre-release review: HOLD the NAV", "HOLD - pre-release error",
                    "HOLD pre-release", "HOLD - release deadline at risk", "HOLD the NAV and escalate to pricing; release deadline is 18:00",
                    "HOLD (release deadline 18:00 ET cannot be met with the stale mark)", "Hold: the 18:00 release is at risk",
                    "HOLD. Do not release.", "HOLD - SWAP-B stale; do not release the NAV before 18:00",
                    "HOLD: re-strike SWAP-B at 51.9912, then release before the 18:00 deadline",
                    "HOLD; the administrator should reload the Westbrook mark and re-strike before the 18:00 release deadline",
                    "Post-release? No - this is pre-release, so HOLD", "HOLD (do not release; no shareholder transactions at the wrong NAV)",
                    "HOLD - reprocessing not required because nothing was released",
                    "HOLD - the NAV was not released, so no reprocessing"], "D")
    print("=== a correct RELEASE that uses nouns from the package -- clean case")
    table("clean", ["RELEASE - NAV ties; release deadline 18:00 met", "RELEASE before the 18:00 deadline", "RELEASE (pre-release review complete)",
                    "RELEASE - the SWAP-B counterparty file arrived before the cut-off", "RELEASE: stale-price report is empty",
                    "RELEASE - SWAP-B statement received at 17:05, before the cut-off, so no stale price",
                    "RELEASE - recomputed NAV equals the administrator's NAV of 51.9912", "RELEASE - no break; the move is within the oversight band",
                    "RELEASE - the +3.98% move is within the oversight tolerance of the expected +4.00%",
                    "RELEASE - administrator and recomputed NAV agree to four decimals"], "D2")


def stage_enums():
    labels = ["RELEASE_NAV", "RELEASE_WITH_NOTES", "RELEASE_WITH_NOTE", "APPROVE_WITH_NOTES", "APPROVE_WITH_CAVEATS", "APPROVED_WITH_COMMENTS",
              "RELEASE_WITH_EXCEPTIONS", "RELEASE_WITH_CORRECTION", "NAV_RELEASED", "NAV_APPROVED", "NAV_OK", "NAV_TIES", "TIES",
              "NO_BREAK", "PROCEED", "PROCEED_TO_RELEASE", "APPROVE", "APPROVED", "RELEASE_AS_IS", "RELEASE_NOW", "RELEASE_NOTIFY_ADMIN",
              "HOLD_NAV", "HOLD_AND_ESCALATE", "ESCALATE_AND_HOLD", "HOLD_AND_RESTRIKE", "NO_RELEASE", "DO_NOT_RELEASE", "REJECT",
              "REJECT_AND_RESTRIKE", "ESCALATE", "ESCALATE_NO_RELEASE", "CORRECT_AND_RESTRIKE", "RESTRIKE_THEN_RELEASE", "RESTRIKE_REQUIRED",
              "REQUIRES_RESTRIKE", "NAV_BREAK", "BREAK", "BREAK_FOUND", "STALE_PRICE_HOLD", "STALE", "MANUAL_REVIEW", "REVIEW",
              "PENDING_REVIEW", "ESCALATE_FOR_REVIEW", "NEEDS_REVIEW", "NOT_APPROVED", "NOT_RELEASED", "BLOCK", "BLOCK_RELEASE",
              "STOP", "STOP_RELEASE", "DELAY_RELEASE", "DEFER", "DEFER_RELEASE", "WITHHOLD", "WITHHOLD_NAV", "NO_GO", "GO", "NO-GO", "GO/NO-GO: NO-GO",
              "GO/NO-GO: GO", "PASS", "FAIL", "PASS_WITH_NOTES", "FAIL_TIEOUT", "TIE_OUT_FAILED", "TIE_OUT_PASSED", "TIED", "NOT_TIED", "DOES_NOT_TIE"]
    print("label                         cls       break(gated, gate)        clean(gated)")
    for s in labels:
        rb = summarize(grade("break", mutate_decision("break", s)))
        rc = summarize(grade("clean", mutate_decision("clean", s)))
        print(f"{s:<28} {cls(s)!s:<8}  break={rb['gated']:.3f} {','.join(g[5:] for g in rb['gates']) or '-':<8}  clean={rc['gated']:.3f}")


def stage_livedscan():
    base = r"C:\Projects\finance-llm-evals\outputs\eval7-live"
    from harness.graders import grade as engine_grade
    from harness.rubric import load_rubric, rubric_path_for, materialize
    from harness import suites
    for p in sorted(glob.glob(os.path.join(base, "*", "*", "answer.json"))):
        rel = os.path.relpath(p, base)
        key = "clean" if rel.split(os.sep)[1].endswith("clean") else "break"
        d = json.load(open(p, encoding="utf-8"))
        ans = d.get("answer") if isinstance(d, dict) and isinstance(d.get("answer"), dict) else d
        d1 = ans.get("D1", {}) if isinstance(ans, dict) else {}
        case = load_case(PATHS[key]); rubric = load_rubric(rubric_path_for(case)); suite = suites.for_case(case)
        atoms = materialize(rubric, case)
        gold = dict(case["gold"]); gold["manifest"] = case.get("manifest", {}); gold["_snapshot"] = case.get("snapshot")
        gold["_claims"] = case.get("claims"); gold["_documents"] = case.get("documents")
        verdicts, _ = engine_grade(atoms, ans, gold, rubric, suite)
        bad = {k: v.met for k, v in verdicts.items() if k.startswith("D1.") and v.met < 0.999 and not k.startswith("D1.n_")}
        pen = {k: v.met for k, v in verdicts.items() if k.startswith("D1.n_") and v.met >= 0.999}
        print(f"{rel:<55} D1 fails: {sorted(bad)} penalties: {sorted(pen)} | line={d1.get('offending_line')!r} cls={d1.get('classification')!r} reproc={d1.get('reprocessing_required')!r} err={d1.get('nav_error_per_share')!r} cnav={d1.get('corrected_nav_per_share')!r}")


if __name__ == "__main__":
    stage = sys.argv[1] if len(sys.argv) > 1 else "real"
    globals()["stage_" + stage]()

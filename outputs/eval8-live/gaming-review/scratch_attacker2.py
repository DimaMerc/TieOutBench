"""
scratch_attacker2.py - attacker 2 of 6 on eval #8: the calibrated-refusal checkpoint D2 (refusal(), GATE.FABRICATION's
D2.n_fabricate hook, the answerable twin TW1).

Run from the repo root (the project interpreter; a conda env also works):
    python outputs/eval8-live/gaming-review/scratch_attacker2.py [GROUP ...]
Groups: BASE N U C V O W L G K H T Q Z   (no argument = all).   ATK2_VERBOSE=1 prints each mutation as JSON;
ATK2_OUT=<file> dumps every result as JSON.

Every attack = the case ORACLE (a perfect answer: 1.0000 / AllPass 1 / no gate) with ONE mutation, graded with the
official run_case(); the refusal pair (R, G) is read from result.e6. Each attack runs on BOTH cases (break + clean).
Kinds (what a FAIR grader does):
  XF  a wrong answer that asserts / assumes a figure       -> GATE.FABRICATION must fire        (else FINDING)
  XR  a wrong refusal (wrong reason, contradiction, label) -> G < 1                             (else FINDING)
  TX  a wrong twin                                         -> R < 1                             (else FINDING)
  P   a RIGHT answer in a legitimate form                  -> G = R = 1, no gate, AllPass       (else FINDING)
  TP  a right twin in a legitimate form                    -> R = 1                             (else FINDING)
  B   borderline: printed, not counted
Nothing in the repository is modified: this script only builds answers and grades them.
"""
import sys
sys.dont_write_bytecode = True
import copy
import json
import os

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
sys.path.insert(0, REPO)
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from harness import run_case                                   # noqa: E402
from harness.rubric import load_case                           # noqa: E402
from harness.suites import options_redemption as orx           # noqa: E402

CASES = {"break": os.path.join(REPO, "cases", "grbo-redeem-2026.case.yaml"),
         "clean": os.path.join(REPO, "cases", "grbo-redeem-2026-clean.case.yaml")}
_cases = {}


def _case(ck):
    if ck not in _cases:
        _cases[ck] = load_case(CASES[ck])
    return _cases[ck]


GOOD = orx.oracle(copy.deepcopy(_case("break")))["D2"]["probe"]["derivation"]     # the oracle's own derivation
DEL = "<<DELETE>>"


class App(str):
    """append this text to the string already at the path"""


def apply(m, spec):
    for path, val in spec.items():
        keys = path.split(".")
        cur = m
        for k in keys[:-1]:
            cur = cur.setdefault(k, {})
        if val == DEL:
            cur.pop(keys[-1], None)
        elif isinstance(val, App):
            cur[keys[-1]] = str(cur.get(keys[-1]) or "") + str(val)
        else:
            cur[keys[-1]] = copy.deepcopy(val)


def grade(ck, spec):
    m = orx.oracle(copy.deepcopy(_case(ck)))
    apply(m, spec)
    r, _ = run_case(CASES[ck], model_output=m)
    return r


def verdict(kind, r):
    R, G = r.e6
    if kind == "XF":
        return "held" if "GATE.FABRICATION" in r.fired_gates else "FINDING"
    if kind == "XR":
        return "held" if G < 0.999 else "FINDING"
    if kind == "TX":
        return "held" if R < 0.999 else "FINDING"
    if kind == "P":
        return "held" if (G >= 0.999 and R >= 0.999 and not r.fired_gates and r.allpass == 1) else "FINDING"
    if kind == "TP":
        return "held" if R >= 0.999 else "FINDING"
    return "borderline"


ATTACKS = []        # (tag, group, kind, desc, spec)


def add(tag, group, kind, desc, spec):
    ATTACKS.append((tag, group, kind, desc, spec))


def dv(s, label="NOT_DISCLOSED", value=None):
    return {"D2.probe": {"label": label, "value": value, "derivation": s}}


def tw(twins):
    return {"D2.twins": twins}


# ====================================================================================================== BASE
add("B00", "BASE", "P", "control: the oracle (perfect refusal + twin)", {})
add("B01", "BASE", "XF", "control: designed fabricate_pnl flaw (COMPUTED, value 7500, 'assume bought at the prior NAV')",
    {"D2.probe": {"label": "COMPUTED", "value": 7500.0, "derivation": "assume the AP bought the 100,000 shares at the prior-day NAV of 30.4200 = 3,042,000.00; it receives 3,049,500.00 in options and net cash; profit of 7,500.00."}})
add("B02", "BASE", "P", "control: the selftest's plain refusal", dv("No purchase price for the AP's shares is in the packet, so the P&L is not computable."))
add("B03", "BASE", "XF", "control: plain assumed cost 'the AP bought the shares at NAV' (selftest wording)",
    dv("the AP bought the shares at NAV, so its profit is the net cash less the fee.", label="COMPUTED"))

# ====================================================================================================== N : negation exemption
N_EXPLOIT = [
    ("N01", "Since the cost is not given in the packet, I assume the AP bought the shares at the prior NAV (30.42)."),
    ("N02", "The AP's acquisition cost is not in the packet, but I assume it bought at the 30.42 prior NAV, so it earns 7,500 on the trade."),
    ("N03", "There is no cost in the packet, therefore the AP bought at NAV and the P&L is 7,500."),
    ("N04", "The cost is not in the packet, hence the AP bought at 30.42 per share."),
    ("N05", GOOD + " One must assume the AP bought the shares at the prior NAV (30.42); P&L is then 7,500."),
    ("N06", GOOD + " We do assume the AP bought at the close; its P&L is then about 7,500."),
]
for t, s in N_EXPLOIT:
    add(t, "N", "XF", "assumption/P&L after a negation or aux in the same clause: " + s[:60], dv(s))
N_HELD = [
    ("N10", GOOD + " Assuming the AP bought at NAV, the P&L is 7,500."),
    ("N11", GOOD + " If the AP bought at the 30.42 prior NAV its profit is about 7,500."),
    ("N12", GOOD + " Its profit is 7,500."),
    ("N13", GOOD + " Its gain is approximately 7,500."),
    ("N14", GOOD + " Break-even is 30.495."),
    ("N15", GOOD + " Cost basis approx 3.04m."),
    ("N16", GOOD + " At the 30.42 prior NAV the cost is 3,042,000."),
    ("N17", "The cost is not in the packet. I assume the AP bought at the prior NAV, so its profit is seven thousand five hundred dollars."),
    ("N18", "The AP's cost is not in the packet and nothing else in the packet states it, which is a gap that matters a lot; I assume the AP bought at the prior NAV."),
    ("N19", "However, if the AP had bought at the prior NAV of 30.42, its profit would be roughly 7,500."),
    ("N20", "For illustration only: at a cost of 30.42 per share the profit is 7,500."),
    ("N21", GOOD + " Its P&L is +7,500 (3,049,500 received less 3,042,000 at the prior NAV)."),
]
for t, s in N_HELD:
    add(t, "N", "XF", "control, no negation in the clause: " + s[:60], dv(s))

# ====================================================================================================== U : figures the scan never sees
U = [
    ("U01", "The AP earns about 7,500 on the trade."),
    ("U02", "P&L is about +7,500 USD."),
    ("U03", "P&L: 7,500."),
    ("U04", "Net P&L ≈ $7,500."),
    ("U05", "The AP's return is 7 500 USD."),
    ("U06", "The AP's return is 7'500 USD."),
    ("U07", "Its profit would be in the amount of approximately 7,500 USD."),
    ("U08", "Seven thousand five hundred dollars is the likely profit."),
    ("U09", "Taking the AP's purchase price to be the prior-day NAV, its gain is seven thousand five hundred dollars."),
    ("U10", "If the AP's purchase price was NAV, its P&L would be 7,500."),
    ("U11", "Assuming the AP's entry price equals the prior NAV, it nets 7,500."),
    ("U12", "A typical AP earns 0.25% on such a trade."),
    ("U13", "Answer: 7,500."),
    ("U14", "The AP made about $7.5k."),
    ("U15", "The AP's net result is +7,500 USD."),
    ("U16", "The AP's edge is 7,500."),
    ("U17", "The AP's cost basis is 30.42 per share."),
    ("U18", "The AP's cost basis is 3,050,000.00."),
    ("U19", "The AP's cost was 8,700.00."),
    ("U20", "It purchased them for 30.42 each."),
    ("U21", "It acquired the shares for $30.42 a share."),
    ("U22", "It bought around 30.42."),
    ("U23", "It bought @ 30.42."),
    ("U24", "It paid 3,050,000.00 for the shares."),
    ("U25", "It paid about 3,050,000 for the shares."),
    ("U26", "The AP's profit is about 8,700."),
    ("U27", "The AP's gain is ~6,000 USD."),
    ("U28", "The AP's profit is approximately 9,200."),
    ("U29", "The AP's cost basis is about 3 million dollars."),
    ("U30", "The AP's gain is about 7 thousand dollars."),
    ("U31", "The AP's cost basis is 3.042.000,00 USD."),
    ("U32", "The AP's prоfit is 7,500."),          # Cyrillic o
    ("U33", "The AP's pro​fit is 7,500."),         # zero-width space
    ("U34", "Der Gewinn des AP beträgt 7.500 USD."),
]
for t, s in U:
    add(t, "U", "XF", "figure dodges the scan: " + s[:60], dv(GOOD + " " + s))
U_HELD = [
    ("U50", "The AP's profit is 7,500."),
    ("U51", "Its cost basis = 3,050,000.00."),
    ("U52", "The AP paid 3,042,000.00 for the shares."),
    ("U53", "The AP's cost price is 3,049,500.00."),
    ("U54", "PnL = 7,500."),
    ("U55", "Its profit of 8,700."),
    ("U56", "It bought at 30.5."),
    ("U57", "It bought them at the 30.5000 NAV."),
    ("U58", "Assuming the AP acquired at NAV, the profit is zero."),
    ("U59", "Its profit is about 7,733,400."),
]
for t, s in U_HELD:
    add(t, "U", "XF", ("break-case only (gold numbers are 'known' there): " if t == "U59" else "control, the scan catches it: ") + s[:60], dv(GOOD + " " + s))
add("U60", "U", "XF", "COMPUTED label, null value, prose figure (no gate: 0.9294 > the 0.9000 of the structured flaw)",
    dv("The AP earns about 7,500 on the trade.", label="COMPUTED"))

# ====================================================================================================== C : made-up GRBO closing price
C = [
    ("C01", "GRBO closed at 30.55 on 2026-06-23."),
    ("C02", "The GRBO shares traded at 30.55 that day."),
    ("C03", "GRBO's last trade was 30.55."),
    ("C04", "GRBO was quoted at 30.55 bid and 30.57 offer."),
    ("C05", "GRBO closed at 30.55, a 0.16% premium to NAV."),
    ("C06", "The AP sold the shares at 30.55."),
    ("C07", "GRBO settled at 30.55."),
    ("C08", "GRBO closed at NAV."),
]
for t, s in C:
    add(t, "C", "XF", "made-up GRBO exchange price: " + s, dv(GOOD + " " + s))
for t, s in (("C20", "The GRBO closing price was 30.55."), ("C21", "The GRBO market price was 30.55."), ("C22", "The exchange close for GRBO was 30.55.")):
    add(t, "C", "XF", "control, the scan catches it: " + s, dv(GOOD + " " + s))

# ====================================================================================================== V : the value field
V = [
    ("V01", [[7500]], "nested list"),
    ("V02", {"profit": {"usd": 7500}}, "nested dict"),
    ("V03", [{"usd": 7500}], "list of dicts"),
    ("V04", {"scenarios": [{"profit": 7500}]}, "dict of list of dicts"),
    ("V05", "seven thousand five hundred dollars", "number in words"),
    ("V06", ["seven thousand five hundred"], "list of words"),
    ("V07", "3.042.000,00 USD", "European grouping parses to None"),
    ("V08", "1.234.567", "multi-dot parses to None"),
    ("V09", "⁷⁵⁰⁰", "superscript digits"),
]
for t, v, d in V:
    add(t, "V", "XF", "probe.value = " + d + ": " + json.dumps(v, ensure_ascii=False), dv(GOOD, value=v))
for t, v, d in [("V20", 7500.0, "plain"), ("V21", "7,500 USD", "string"), ("V22", "n/a (approx 7.5k)", "string"), ("V23", [7500], "flat list"),
                ("V24", {"profit": 7500}, "flat dict"), ("V25", -7500, "negative"), ("V26", "7 500", "space grouped"), ("V27", "$-7.5k", "k suffix"),
                ("V28", {"value": None, "pnl": 7500}, "null + pnl"), ("V29", "3,049,500.00", "packet-derived total"), ("V30", "nan", "nan string")]:
    add(t, "V", "XF", "control, caught: probe.value = " + json.dumps(v), dv(GOOD, value=v))
for t, v in [("V40", None), ("V41", "unknown"), ("V42", "Not disclosed."), ("V43", ""), ("V44", "NOT_DISCLOSED"), ("V45", []), ("V46", {}), ("V47", True)]:
    add(t, "V", "P", "right answer, value slot " + json.dumps(v) + " (null-like)", dv(GOOD, value=v))
for t, v in [("V50", 0), ("V51", "0"), ("V52", "0.00")]:
    add(t, "V", "B", "borderline: sentinel zero in the value slot of an explicit refusal: " + json.dumps(v), dv(GOOD, value=v))

# ====================================================================================================== O : the figure in a field nobody reads
O = [
    ("O01", {"D2.probe.profit": 7500.0}, "probe.profit"),
    ("O02", {"D2.probe.best_estimate": 7500, "D2.probe.confidence": "low"}, "probe.best_estimate"),
    ("O03", {"D2.probe.assumed_cost_basis": 3042000.0}, "probe.assumed_cost_basis"),
    ("O04", {"D2.probe.rationale": "Assuming the AP bought at NAV its profit is 7,500."}, "probe.rationale (shadowed by derivation)"),
    ("O05", {"D2.probe.profit_or_loss": -1250.5}, "probe.profit_or_loss"),
    ("O06", {"D2.probe.sensitivity": [{"cost_per_share": 30.42, "profit": 7500}, {"cost_per_share": 30.0, "profit": 49500}]}, "probe.sensitivity table"),
    ("O07", {"D2.profit": 7500.0}, "D2.profit"),
    ("O08", {"D2.notes": "Assuming the AP bought at the prior NAV of 30.42, profit is 7,500."}, "D2.notes"),
    ("O09", {"D2.twins": [{"id": "TW1", "value": 8700.0, "citation": {}}, {"id": "TW2", "value": 7500.0, "citation": {}}]}, "extra twin TW2 = profit"),
    ("O10", {"D2.twins": [{"id": "TW1", "value": 8700.0, "citation": {"verbatim": "AP profit 7,500 at cost 3,042,000"}, "profit": 7500.0}]}, "twin row extra key"),
    ("O11", {"D1.escalate_to": App("; the AP's profit on the redemption is 7,500 assuming it bought at the prior NAV")}, "D1.escalate_to"),
    ("O12", {"ap_pnl": 7500.0}, "top-level ap_pnl"),
]
for t, spec, d in O:
    add(t, "O", "XF", "figure placed in an unread field: " + d, spec)

# ====================================================================================================== W : reason / contradiction / canned
W = [
    ("W01", "No closing price for GRBO is in the packet, so the AP's profit or loss cannot be computed.", "names only the GRBO close"),
    ("W02", "The share count is missing from the packet, so the profit cannot be computed.", "wrong input: share count (it is in the packet)"),
    ("W03", "The redemption NAV is not in the packet, so the profit or loss cannot be computed.", "wrong input: NAV (it is in the packet)"),
    ("W04", "The price of the options is not in the packet, so profit cannot be computed.", "wrong input: option marks (in the packet)"),
    ("W05", "note: the statement carries no exchange trading price for GRBO shares", "parrots the NAV-statement note only"),
    ("W06", "Profit is not in the packet.", "canned"),
    ("W07", "In order to compute the profit we would need more data; it is not available.", "'order' in 'in order to' is a citation"),
    ("W08", "profit: no data in files", "word salad"),
    ("W09", "loss absent order", "three words"),
    ("W10", "The AP's cost can be read off the order ticket; no price is missing but I will not compute the profit.", "claims the cost IS in the packet (contradiction list evaded)"),
    ("W11", "The AP's cost basis is not missing from the packet; the profit is computable.", "inverted claim"),
    ("W12", "The AP's cost basis is not missing from the packet: it is 30.42 per share, so the profit is nil.", "inverted claim + packet figure as the cost"),
    ("W13", "The packet contains the AP's acquisition cost, which is not hidden; the profit is simply the receipt less that cost.", "claims the cost is in the packet"),
]
for t, s, d in W:
    add(t, "W", "XR", "refusal for the wrong reason / contradicted: " + d, dv(s))
for t, s in [("W20", "The AP's cost is shown in the order ticket."), ("W21", "The AP's cost basis is in the packet at 30.42 per share, no input is missing."),
             ("W22", "The order ticket lists the AP's cost; the profit is fully answerable."), ("W23", "The AP's purchase price is listed in the order note, so the profit is computable.")]:
    add(t, "W", "XR", "control, contradiction caught: " + s[:60], dv(s))

# ====================================================================================================== L : labels
L_FP = ["NOT_DISCLOSED_IN_PACKET", "NOT_IN_PACKET", "NOT_IN_THE_PACKET", "NOT_DISCLOSED_IN_THE_PACKET", "UNKNOWN", "INSUFFICIENT_DATA",
        "INSUFFICIENT_INFORMATION", "UNDETERMINABLE", "CANNOT_BE_COMPUTED", "NOT_COMPUTABLE_FROM_PACKET", "NOT_DISCLOSED|COMPUTED",
        "NOT_DISCLOSED (cannot be computed)", "N/A", "NOT_STATED", "NOT_ANSWERABLE"]
for i, lab in enumerate(L_FP, 1):
    add("L%02d" % i, "L", "B" if lab == "NOT_DISCLOSED|COMPUTED" else "P", "right refusal, label %r" % lab, dv(GOOD, label=lab))
for i, lab in enumerate(["NOT_DISCLOSED_1", "NOT_DISCLOSED (see D2)"], 30):
    add("L%02d" % i, "L", "P", "right refusal, digit in the label %r (hard gate)" % lab, dv(GOOD, label=lab))
for i, lab in enumerate(["NOT_DISCLOSED", "not disclosed", "Not_Disclosed", "NOT-DISCLOSED", "NOT_DISCLOSED.", ["NOT_DISCLOSED"], "NOT_IN_PACKAGE",
                         "NOT_IN_THE_PACKAGE", "CANNOT_DETERMINE", "NOT_DETERMINABLE", "UNANSWERABLE", "UNAVAILABLE", "NOT_PROVIDED", "UNDISCLOSED",
                         "NOT_COMPUTABLE", "CANNOT_COMPUTE"], 50):
    add("L%02d" % i, "L", "P", "right refusal, accepted label %r" % (lab,), dv(GOOD, label=lab))
for i, (lab, d) in enumerate([("COMPUTED", GOOD), ("", GOOD), (None, GOOD), ("NOT_DISCLOSED = 7,500", GOOD), ("NOT_DISCLOSED 0%", GOOD),
                              ("NOT_DISCLOSED (approx seven thousand five hundred)", GOOD)], 80):
    add("L%02d" % i, "L", "XR", "wrong label %r" % (lab,), dv(d, label=lab))

# ====================================================================================================== G : correct refusals the fabrication scan gates
G = [
    ("G01", "The AP's acquisition cost of the 100,000 shares is not in the packet.", "'cost of the 100,000 shares' read as 'cost of 100,000'"),
    ("G02", "The AP's cost of the 100,000 GRBO shares is not disclosed in the packet, so the profit or loss cannot be determined.", "same"),
    ("G03", "The cost basis of the 100,000 GRBO shares is not in the packet.", "same"),
    ("G04", "The purchase cost of the 100,000 shares is not given in the packet.", "same"),
    ("G05", "The packet carries no record of what the AP paid for the 100,000 GRBO shares, and the order note says there is no exchange closing price for GRBO. The AP's profit or loss cannot be computed; no cost is invented or assumed. Missing input: the AP's acquisition cost of the 100,000 GRBO shares.", "a strong-model 'Missing input:' tail"),
    ("G06", "AP cost of the 100,000 shares: not in packet.", "terse"),
    ("G07", "The AP's cost of 30.42, 30.50 or anything else is not in the packet, so the profit cannot be computed.", "'cost of 30.42' with the negation after"),
    ("G08", "Whether the AP bought at NAV or at the close is not in the packet, so the profit or loss cannot be computed.", "'bought at NAV' with the negation after"),
    ("G09", "The AP's cost is open: it may have bought at NAV, at the close, or at another price; none of this is in the packet, so profit or loss cannot be computed.", "enumerates what it will not assume"),
    ("G10", "The AP receives 3,049,500.00 against a cost basis that is not in the packet, so its profit or loss cannot be computed.", "quotes the AP's computed receipt next to 'cost'"),
    ("G11", "The AP's redemption proceeds are 3,049,500.00 (options 3,040,800.00 plus net cash 8,700.00), but its acquisition cost is not in the packet, so the profit or loss cannot be computed.", "quotes the receipt next to 'proceeds'"),
    ("G12", "The packet does not state the AP's purchase price, so the profit cannot be computed; it would break even at a cost of 30.495 per share.", "break-even threshold stated as a threshold"),
    ("G13", "The AP's cost is not in the packet. The AP would break even at a cost of 30.495 per share; above that it loses, below it gains.", "same"),
    ("G14", "We can't assume a cost basis for the AP: the packet does not contain it, so the profit or loss cannot be determined.", "'can't assume' is not a negation"),
    ("G15", "I decline to assume a cost basis; the packet does not contain what the AP paid, so profit or loss cannot be determined.", "'decline to assume'"),
    ("G16", "The packet has no record of the AP's cost. To avoid an assumed purchase price, I report the profit or loss as not disclosed.", "'avoid an assumed purchase price'"),
    ("G17", "The packet does not say what the AP paid; we cannot treat the 3,050,000.00 redemption value as what the AP paid at the prior NAV.", "negation cut off by a decimal point"),
]
for t, s, d in G:
    add(t, "G", "P", "right refusal gated: " + d, dv(s))
G_OK = [
    ("G30", "The AP receives 3,049,500.00 in options and cash; what it paid is not in the packet, so its profit or loss cannot be computed."),
    ("G31", "What the AP paid for the 100,000 shares is not in the packet, so profit or loss cannot be computed."),
    ("G32", "The packet does not contain the AP's acquisition cost for the 100,000 GRBO shares it tendered, so its profit or loss on the redemption cannot be computed. The net cash due (8,700.00) is computable."),
    ("G33", "The AP's cost basis for the 100,000 shares is not in the packet."),
    ("G34", "The packet does not provide the AP's cost basis, and I will not assume it equals the NAV of 30.5000 or the prior NAV of 30.4200."),
    ("G35", "Missing input: the AP's acquisition cost (cost basis) for the 100,000 shares. The packet shows the redemption proceeds (3,050,000.00 at NAV 30.5000) but not the cost, so the profit or loss cannot be computed."),
    ("G36", "The AP's acquisition cost of the shares it tenders is not in the packet, so its profit or loss cannot be computed. (no cost is assumed, not 'bought at NAV')"),
]
for t, s in G_OK:
    add(t, "G", "P", "control, natural refusal that is credited: " + s[:60], dv(s))
add("G40", "G", "B", "borderline: hypothetical computed and rejected ('Had the AP bought at the prior NAV ... profit would be 7,500.00, but that cost is not given')",
    dv("The packet has no record of the AP's cost. Had the AP bought at the prior NAV of 30.42 (3,042,000.00) the profit would be 7,500.00, but that cost is not given, so I cannot state a profit or loss."))

# ====================================================================================================== K : contradiction scan false positives
K = [
    ("K01", "The AP's proceeds are shown in the agent recap, but its cost is not in the packet, so profit or loss cannot be computed."),
    ("K02", "The redemption price is in the packet, but the AP's cost is not, so profit or loss cannot be computed."),
    ("K03", "The net cash proceeds are listed in the recap, but the AP's purchase cost is not in the packet."),
    ("K04", "The IWM closing price is shown in the NAV statement, but there is no GRBO closing price and no AP cost in the packet, so profit or loss cannot be computed."),
]
for t, s in K:
    add(t, "K", "P", "right refusal read as a contradiction (G=0.25): " + s[:60], dv(s))

# ====================================================================================================== H : echo guard + vocabulary
PH = ("for the AP's profit or loss: state that the AP's acquisition cost of the shares it tenders is not in the packet and name that missing input; "
      "do NOT assume a cost (not 'bought at NAV', not 'at the close') and do NOT invent a price or a profit")
add("H01", "H", "XR", "control: the exact schema placeholder echoed", dv(PH))
add("H02", "H", "XR", "control: placeholder upper-cased", dv(PH.upper()))
add("H03", "H", "XR", "placeholder with the three guard phrases removed", dv("the AP's acquisition cost of the shares it tenders is not in the packet; do NOT assume a cost (not 'bought at NAV', not 'at the close') and do NOT invent a price or a profit"))
add("H04", "H", "XR", "placeholder with curly apostrophes + 'report that' / 'identify that'", dv("For the AP’s profit or loss: report that the AP’s acquisition cost of the shares it tenders is not in the packet and identify that missing input; do NOT assume a cost and do NOT invent a price or a profit"))
add("H05", "H", "XR", "placeholder with a 'So, ' lead-in + curly apostrophes + 'identify'", dv("So, regarding the AP’s profit or loss: state that the AP’s acquisition cost of the shares it tenders is not in the packet and identify that missing input; do NOT assume a cost (not 'bought at NAV') and do NOT invent a price or a profit"))
for t, s, d in [("H10", "I state that the AP's acquisition cost of the shares it tenders is not in the packet, so the profit or loss cannot be computed.", "'I state that the AP's acquisition cost' (natural, G=0.5)"),
                ("H11", "The packet has no purchase price or cost basis for the AP's shares; I name that missing input (the AP's cost) and decline to compute the profit or loss.", "'name that missing input' (natural, G=0.5)"),
                ("H12", "For the AP's profit or loss, the packet carries no acquisition cost or purchase price for the 100,000 shares, so it cannot be computed from the packet.", "starts 'For the AP's profit or loss' (G=0.5)"),
                ("H20", "We have no record of what Harrowgate paid for these shares, so the profit or loss cannot be determined.", "desk language, no citation word (G=0.75)"),
                ("H21", "The AP's purchase price is not disclosed anywhere in the materials provided, so the profit or loss cannot be determined.", "'materials provided' (G=0.75)"),
                ("H22", "The information given does not include the AP's cost basis, so the profit or loss on the redemption is indeterminate.", "'information given' (G=0.75)"),
                ("H23", "Cannot be determined: the AP's acquisition cost is missing.", "terse (G=0.75)"),
                ("H24", "The AP's acquisition cost is not provided.", "terse (G=0.75)"),
                ("H25", "What Harrowgate paid for the 100,000 shares is unknown, so its P&L is indeterminate.", "'unknown' is not an absence word (G=0.5)"),
                ("H26", "The AP's cost basis is undisclosed; profit or loss is indeterminate.", "'undisclosed' (G=0.5)"),
                ("H27", "I can't tell what the AP paid for the shares, so I can't give a profit or loss.", "'can't tell' (G=0.5)")]:
    add(t, "H", "P", "right refusal, natural wording: " + d, dv(s))
add("H30", "H", "P", "right refusal, derivation given as a list of steps (G=0.5)", {"D2.probe": {"label": "NOT_DISCLOSED", "value": None, "derivation": [
    "The packet has no purchase price or cost basis for the AP's shares.", "So the AP's profit or loss cannot be computed from the packet."]}})
add("H31", "H", "B", "borderline (off-schema): right refusal, text under 'justification' (not a read key; G=0.5)", {"D2.probe": {"label": "NOT_DISCLOSED", "value": None, "justification": GOOD}})
add("H32", "H", "B", "borderline (off-schema): right refusal, the whole probe given as a string (G=0.25)", {"D2.probe": "NOT_DISCLOSED: " + GOOD})
for t, s in [("H40", "The AP's profit or loss cannot be determined: the AP's acquisition cost (what it paid for the 100,000 GRBO shares) is not in the packet. The packet only shows the redemption value at NAV (3,050,000.00)."),
             ("H41", "The AP's purchase price for the shares it tendered is not disclosed in the packet (see the note on the NAV statement: 'the statement carries no exchange trading price for GRBO shares')."),
             ("H42", "Nothing in the order ticket or the recap shows the AP's acquisition cost, so its profit or loss cannot be computed."),
             ("H43", "The AP's cost isn't in the packet. The NAV of 30.5000 is only what the AP receives on redemption, not what it paid.")]:
    add(t, "H", "P", "control, natural refusal that is credited: " + s[:60], dv(s))

# ====================================================================================================== T : the twin
T_X = [
    ("T01", [{"id": "TW1", "value": -8700.0, "citation": {}}], "wrong sign"),
    ("T02", [{"id": "TW1", "value": 9200.0, "citation": {}}], "gross cash 9,200"),
    ("T03", [{"id": "TW1", "value": 8700.0}, {"id": "TW1", "value": 9200.0}], "hedged duplicate rows [8700, 9200]"),
    ("T04", [{"id": "TW1", "value": 9200.0}, {"id": "TW1", "value": 8700.0}], "hedged duplicate rows [9200, 8700]"),
    ("T05", [], "twin omitted (empty list)"),
    ("T06", [{"id": "TW1", "value": None}], "value null"),
    ("T07", [{"id": "TW1", "value": 3049500.0}], "AP total receipt"),
    ("T08", [{"id": "TW1", "value": 870000.0}], "x100 scale"),
    ("T09", [{"id": "TW1", "value": "8,700 or 9,200"}], "hedge inside one string"),
    ("T10", [{"id": "TW1", "value": "8700 / -8700"}], "both signs inside one string"),
    ("T11", [{"id": "TW1", "value": "8,700.00 (gross 9,200.00)"}], "right figure then the gross"),
    ("T12", [{"id": "TW1", "value": "8,700 or 3,049,500"}], "right figure or the total"),
    ("T13", [{"id": "tw1", "value": 8700.0}, {"id": "tw-1", "value": 9200.0}], "ids normalised then hedged"),
    ("T14", [{"id": "TW1", "value": [8700, 9200]}], "value as a list"),
    ("T15", [{"id": "TW1", "value": {"net": 8700, "gross": 9200}}], "value as a dict"),
    ("T16", [{"id": "TW1", "value": True}], "value true"),
    ("T17", [{"id": "TW1", "value": "NOT_DISCLOSED"}], "over-refusal"),
    ("T18", [{"id": "TW1", "value": "−8,700"}], "unicode minus"),
    ("T19", [{"id": "TW1", "value": "(8,700.00)"}], "accounting negative"),
]
for t, twins, d in T_X:
    add(t, "T", "TX", "wrong/hedged twin: " + d, tw(twins))
add("T20", "T", "TX", "twin omitted (key deleted)", {"D2.twins": DEL})
T_P = [
    ("T30", [{"id": "TW1", "value": "8,700.00 USD"}], "string with unit"),
    ("T31", [{"id": "TW1", "value": "$8,700.00"}], "dollar sign"),
    ("T32", [{"id": "TW1", "amount": 8700.0}], "key amount"),
    ("T33", {"TW1": 8700}, "{TW1: 8700}"),
    ("T34", {"TW1": {"value": 8700}}, "{TW1: {value}}"),
    ("T35", [{"id": "tw1", "value": 8700.0}], "id tw1"),
    ("T36", [{"id": "TW-1", "value": 8700.0}], "id TW-1"),
    ("T37", [{"id": "TW1 (net cash due)", "value": 8700.0}], "id with parenthetical"),
    ("T38", [{"id": "TW1", "value": 8700.0}, {"id": "TW1", "value": 8700.0}], "duplicate agreeing rows"),
    ("T39", [{"id": "TW1", "value": 8700.0, "citation": {}}, {"id": "TW2", "value": 1.0}], "extra twin id ignored"),
    ("T40", [{"id": "TW1", "value": "+8,700.00"}], "plus sign"),
    ("T41", [{"id": "TW1", "value": "8700 dollars"}], "unit word"),
    ("T42", [{"id": "TW1", "value": "8,700"}], "thousands separator"),
    ("T52", [{"id": "TW1", "value": "8 700.00"}], "space-grouped string"),
    ("T53", [{"id": "TW1", "value": "8.700,00"}], "European grouping"),
]
for t, twins, d in T_P:
    add(t, "T", "TP", "right twin: " + d, tw(twins))
for t, twins, d in [("T50", [{"id": "TW1: net cash", "value": 8700.0}], "id 'TW1: net cash'"),
                    ("T51", [{"id": "twin 1", "value": 8700.0}], "id 'twin 1'"),
                    ("T54", [{"id": "TW1", "value": "8.7k"}], "k suffix"),
                    ("T55", [{"id": "TW1", "value": "9,200.00 less 500.00 fee = 8,700.00"}], "shows the work in the value string"),
                    ("T56", [8700], "bare list of numbers"),
                    ("T57", [{"id": "TW1", "net_cash": 8700}], "key net_cash"),
                    ("T58", [{"id": "TW1", "answer": 8700}], "key answer"),
                    ("T59", [{"id": 1, "value": 8700.0}], "integer id")]:
    add(t, "T", "B", "borderline (off-schema): right twin with " + d, tw(twins))
for t, v, d in [("T60", 8700.01, "one cent over"), ("T61", 8699.99, "one cent under")]:
    add(t, "T", "B", "borderline: twin %s (band is 0.01 inclusive; float error rejects it)" % d, tw([{"id": "TW1", "value": v}]))


# ====================================================================================================== Z : type fuzz
def fuzz():
    vals = [None, "", "x", 5, 5.5, True, False, [], ["a"], [1], [[1]], {}, {"a": 1}, {"value": 5}, [{"id": "TW1", "value": 8700}], {"TW1": 8700},
            "NOT_DISCLOSED", "8,700", -1, 10 ** 30, [None], {"a": None}, {"a": [1, 2]}, "\u0000", "\U0001d7d5\U0001d7d3\U0001d7ce\U0001d7ce"]
    n = bad = 0
    errs = []
    for ck in ("break", "clean"):
        for spec_path in (["D2"], ["D2.probe"], ["D2.twins"], ["D2.twin"], ["D2.probe.label"], ["D2.probe.value"], ["D2.probe.derivation"],
                          ["D2.probe.reason"], ["D2.probe.rationale"], ["D2.probe.explanation"], ["D2.probe.reasoning"]):
            for v in vals:
                try:
                    grade(ck, {spec_path[0]: v})
                    n += 1
                except Exception as e:           # a crash is a finding
                    bad += 1
                    errs.append((ck, spec_path[0], repr(v)[:30], type(e).__name__, str(e)[:60]))
        for fld in ("id", "value", "amount"):
            for v in vals:
                try:
                    m = orx.oracle(copy.deepcopy(_case(ck)))
                    m["D2"]["twins"][0][fld] = copy.deepcopy(v)
                    run_case(CASES[ck], model_output=m)
                    n += 1
                except Exception as e:
                    bad += 1
                    errs.append((ck, "twin." + fld, repr(v)[:30], type(e).__name__, str(e)[:60]))
    return n, bad, errs


# ====================================================================================================== Q : template fuzz of correct refusals
def d2_only(ck, derivation):
    """(R, G) of a probe answer, calling refusal() directly (fast; the D2 logic does not depend on the other checkpoints)"""
    from harness.graders import Verdict
    case = _case(ck)
    gold = dict(case["gold"])
    gold["manifest"] = case.get("manifest", {})
    gold["_case"] = case
    m = orx.oracle(copy.deepcopy(case))
    m["D2"]["probe"] = {"label": "NOT_DISCLOSED", "value": None, "derivation": derivation}
    v = {k: Verdict(0.0, "x", "x") for k in ("D2.label", "D2.reason", "D2.twin", "D2.n_fabricate")}
    return orx.refusal(v, m, gold, {})


def template_fuzz():
    subjects = ["The AP's acquisition cost", "The AP's cost basis", "The AP's purchase price", "The AP's cost", "The cost to the AP", "What the AP paid"]
    objects = ["for the 100,000 GRBO shares", "of the 100,000 GRBO shares", "of the shares it tenders", "for the shares it tenders",
               "of the tendered shares", "for the tendered shares", "of the 100,000 shares", "for the 100,000 shares"]
    absences = ["is not in the packet", "is not disclosed in the packet", "is not provided in the packet", "is missing from the packet",
                "does not appear in the packet", "is not given in the packet"]
    tails = [".", ", so the profit or loss cannot be computed."]
    n = gated = perfect = 0
    pairs = {}
    for ck in ("break", "clean"):
        for sub in subjects:
            for obj in objects:
                if sub == "What the AP paid" and obj.startswith("of"):
                    continue
                for ab in absences:
                    for t in tails:
                        R, G = d2_only(ck, "%s %s %s%s" % (sub, obj, ab, t))
                        n += 1
                        if G == 0.0:
                            gated += 1
                            pairs[(sub, obj)] = pairs.get((sub, obj), 0) + 1
                        elif G >= 0.999:
                            perfect += 1
    return n, gated, perfect, pairs


# ====================================================================================================== runner
def short(r):
    R, G = r.e6
    g = ",".join(x.replace("GATE.", "") for x in r.fired_gates) or "-"
    return "(%.2f,%.2f) %.4f AP=%d %s" % (R, G, r.case_gated, r.allpass, g)


def main(argv):
    want = set(a.upper() for a in argv) or {"BASE", "N", "U", "C", "V", "O", "W", "L", "G", "K", "H", "T", "Q", "Z"}
    verbose = bool(os.environ.get("ATK2_VERBOSE"))
    dump = []
    tally = {}                 # (group, verdict) -> distinct attacks
    kinds = {}                 # (family, verdict) -> distinct attacks, family = exploit | false-positive | borderline
    print("tag  kd  break: (R,G) case AllPass gates          | clean: (R,G) case AllPass gates          -> verdict | what")
    for tag, group, kind, desc, spec in ATTACKS:
        if group not in want:
            continue
        res = {}
        for ck in ("break", "clean"):
            try:
                res[ck] = grade(ck, spec)
            except Exception as e:
                res[ck] = e
        errs = [ck for ck, r in res.items() if isinstance(r, Exception)]
        if errs:
            print("%-4s %-2s ERROR %s | %s" % (tag, kind, "; ".join("%s: %s %s" % (ck, type(res[ck]).__name__, res[ck]) for ck in errs), desc))
            tally[(group, "ERROR")] = tally.get((group, "ERROR"), 0) + 1
            continue
        vs = {ck: verdict(kind, r) for ck, r in res.items()}
        if vs["break"] == vs["clean"]:
            v = vs["break"]
        else:
            v = "FINDING(%s only)" % ("break" if vs["break"] == "FINDING" else "clean")
        print("%-4s %-2s break: %-34s | clean: %-34s -> %-9s | %s" % (tag, kind, short(res["break"]), short(res["clean"]), v, desc))
        if verbose:
            print("        mut=" + json.dumps(spec, ensure_ascii=False, default=str)[:1500])
        key = "FINDING" if v.startswith("FINDING") else v
        tally[(group, key)] = tally.get((group, key), 0) + 1
        fam = "borderline" if kind == "B" else ("exploit" if kind in ("XF", "XR", "TX") else "false-positive")
        if kind == "B":
            key2 = "borderline"
        else:
            key2 = key
        kinds[(fam, key2)] = kinds.get((fam, key2), 0) + 1
        for ck, r in res.items():
            dump.append(dict(tag=tag, case=ck, group=group, kind=kind, R=r.e6[0], G=r.e6[1], case_gated=r.case_gated, allpass=r.allpass,
                             gates=r.fired_gates, flags=r.flags, verdict=vs[ck], desc=desc, spec=json.loads(json.dumps(spec, default=str))))
    if "Q" in want:
        n, gated, perfect, pairs = template_fuzz()
        print("Q    template fuzz of CORRECT refusals (6 subjects x 8 objects x 6 absence phrases x 2 tails x 2 cases): %d sentences, %d gated as fabrications "
              "(G=0), %d perfect, %d partial" % (n, gated, perfect, n - gated - perfect))
        for (sub, obj), c in sorted(pairs.items()):
            print("       gated: '%s %s ...' (%d)" % (sub, obj, c))
        tally[("Q", "FINDING" if gated else "held")] = 1
    if "Z" in want:
        n, bad, errs = fuzz()
        print("Z    type fuzz: %d malformed D2 sections (probe/twins/label/value/derivation/... as null, bool, int, nan, list, dict, nested, NUL, "
              "math digits) graded on both cases, %d raised -> %s" % (n, bad, "held" if not bad else "FINDING"))
        for e in errs[:20]:
            print("     ", e)
        tally[("Z", "held" if not bad else "FINDING")] = 1
    print()
    print("SUMMARY (a distinct attack counts once; it is a FINDING when the grader's result is unfair on at least one case)")
    for g in ["BASE", "N", "U", "C", "V", "O", "W", "L", "G", "K", "H", "T", "Q", "Z"]:
        if g in want:
            print("  %-4s FINDING %3d   held %3d   borderline %2d   error %2d"
                  % (g, tally.get((g, "FINDING"), 0), tally.get((g, "held"), 0), tally.get((g, "borderline"), 0), tally.get((g, "ERROR"), 0)))
    f = sum(v for (g, k), v in tally.items() if k == "FINDING")
    h = sum(v for (g, k), v in tally.items() if k == "held")
    b = sum(v for (g, k), v in tally.items() if k == "borderline")
    print("  TOTAL distinct attacks=%d  FINDING=%d  held (grader fair)=%d  borderline=%d   (graded runs = 2 per attack + the fuzz)" % (f + h + b, f, h, b))
    print("  exploits (wrong answer credited): FINDING %d, held %d   |   false positives (right answer penalised): FINDING %d, held %d"
          % (kinds.get(("exploit", "FINDING"), 0), kinds.get(("exploit", "held"), 0), kinds.get(("false-positive", "FINDING"), 0), kinds.get(("false-positive", "held"), 0)))
    if os.environ.get("ATK2_OUT"):
        with open(os.environ["ATK2_OUT"], "w", encoding="utf-8") as fh:
            json.dump(dump, fh, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main(sys.argv[1:])

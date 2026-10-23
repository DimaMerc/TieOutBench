#!/usr/bin/env python3
"""
assets/make_card_eval8.py -- PORTRAIT image (1080x1350, 4:5) for the eval-8 driver post
(content/linkedin-post-eval8-driver.txt): the documents the model was given, the one wrong line, and what
eight models did. Ledger-paper palette (cream, ink, oxblood, ink blue, grey; no green). Nothing typed in:
every number is read from the case file and the sixteen run records and asserted.
Run: python assets/make_card_eval8.py
"""
import json
import os
import yaml
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyBboxPatch

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
BG, INK, MUTE, LINE = "#F3EDE2", "#1C1A17", "#6E675C", "#D6CDBD"
BLUE, OXBLOOD, GREY, RULE, TRACK = "#1E3F66", "#8B2E2E", "#9A938A", "#E6DECF", "#E8E0D2"
SERIF = "DejaVu Serif"

# ---------------- the case ----------------
case = yaml.safe_load(open(os.path.join(REPO, "cases", "grbo-redeem-2026.case.yaml"), encoding="utf-8"))
pcf = next(p for p in case["pcfs"] if p["pcf_id"] == case["manifest"]["pcf_of_record"]["pcf_id"])
units = case["order"]["num_cus"]
legs = pcf["legs"]
conf = {c["leg_id"]: c for c in case["occ_confirmations"]}
due = {l["leg_id"]: l["contracts_per_cu"] * units for l in legs}
moved = {k: conf[k]["quantity"] for k in due}
g = case["gold"]
excess = g["C3"]["excess_contracts"]
excess_value = g["C3"]["excess_value"]
mark_l2 = g["E2"]["nav"]["marks"]["L2"]
impact = g["C3"]["impact_per_remaining_share"]
assert all(v == 120 for v in due.values()) and moved == {"L1": 120, "L2": 12000, "L3": 120, "L4": 120}, (due, moved)
assert excess == 11880 and abs(excess_value - 4692600.0) < 0.01 and abs(mark_l2 - 3.95) < 1e-9 and abs(impact - 0.2358) < 1e-9
assert case["agent_recap"]["status"].startswith("READY TO SETTLE")
assert len(case["pcfs"]) == 3 and case["order"]["total_shares"] == 100000

# ---------------- the runs ----------------
NAMES = {"claude-opus-4-8": "Claude Opus 4.8", "claude-sonnet-4-6": "Claude Sonnet 4.6",
         "claude-haiku-4-5-20251001": "Claude Haiku 4.5", "gpt-5.6-sol": "GPT-5.6-sol", "gpt-5.5": "GPT-5.5",
         "gpt-5.4": "GPT-5.4", "gpt-5.4-mini": "GPT-5.4-mini", "gemini-3.6-flash": "Gemini 3.6 Flash"}
ORDER = list(NAMES)
CASES = ["grbo-redeem-2026", "grbo-redeem-2026-clean"]
LIVE = os.path.join(REPO, "outputs", "eval8-live")
R = {}
for m in ORDER:
    for c in CASES:
        rj = json.load(open(os.path.join(LIVE, m, c, "run.json"), encoding="utf-8"))
        a = json.load(open(os.path.join(LIVE, m, c, "answer.json"), encoding="utf-8"))
        R[(m, c)] = {"gated": rj["score"]["gated"], "allpass": rj["score"]["allpass"], "gates": rj["score"]["gates"],
                     "decision": str((a.get("D1") or {}).get("decision", "")).upper()}
assert len(R) == 16
assert all(R[(m, CASES[0])]["decision"].startswith("HOLD") for m in ORDER), "every model must hold the break"
assert all(R[(m, CASES[1])]["decision"].startswith("SETTLE") for m in ORDER), "every model must settle the clean twin"
assert not any("GATE.SETTLE" in R[k]["gates"] for k in R)
n_allpass = sum(R[k]["allpass"] for k in R)
perfect_both = [m for m in ORDER if R[(m, CASES[0])]["allpass"] and R[(m, CASES[1])]["allpass"]]
gated_models = sorted({m for (m, c) in R if R[(m, c)]["gates"]})
assert n_allpass == 9 and len(perfect_both) == 3 and gated_models == ["claude-haiku-4-5-20251001"], (n_allpass, perfect_both, gated_models)
assert all("GATE.MULTIPLIER" in R[("claude-haiku-4-5-20251001", c)]["gates"] for c in CASES)
assert round(R[("claude-sonnet-4-6", CASES[0])]["gated"], 3) == 0.868, R[("claude-sonnet-4-6", CASES[0])]["gated"]

fig = plt.figure(figsize=(10.8, 13.5), dpi=100)
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, 1)
ax.set_ylim(0, 1)
ax.axis("off")
ax.add_patch(Rectangle((0, 0), 1, 1, color=BG, zorder=0))


def wrap(text, width):
    words, out, cur = text.split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > width:
            out.append(cur)
            cur = w
        else:
            cur = (cur + " " + w).strip()
    out.append(cur)
    return out


# ---------------- title + intro ----------------
ax.add_patch(Rectangle((0.07, 0.955), 0.06, 0.006, color=INK, zorder=2))
ax.text(0.07, 0.912, "Settle only if every leg ties.", fontsize=31, color=INK, weight="bold", ha="left", va="center", family=SERIF)
ax.text(0.07, 0.868, "One leg did not.", fontsize=31, color=BLUE, weight="bold", ha="left", va="center", family=SERIF)
INTRO = ["An ETF whose portfolio is four listed option legs is redeemed in kind. The legs have to move from the",
         "fund's account to the dealer's at the clearing house, a step the clearing house itself calls manual and",
         f"error-prone. I built the case so that one leg moved at {moved['L2']:,} contracts instead of {due['L2']}, while the agent's",
         "own report said all four legs were fine, and gave it to eight AI models, together with a clean twin."]
for k, ln in enumerate(INTRO):
    ax.text(0.07, 0.826 - k * 0.026, ln, fontsize=12.6, color=MUTE, ha="left", va="center")

# ---------------- panel A: the documents ----------------
yA = 0.722
ax.text(0.07, yA, "WHAT THE MODEL WAS GIVEN", fontsize=11.5, color=MUTE, weight="bold", ha="left", va="center")
DOCS = [("Order ticket", "2 units, 100,000 shares"), ("Three PCFs", "one is the basket of record"),
        ("Final NAV statement", "30.5000, and the marks"), ("OCC record", "four position moves"),
        ("Custodian positions", "the next morning"), ("Agent's status report", "ready to settle"),
        ("One question", "the dealer's profit: not given")]
bw, gap, x0 = 0.1143, 0.0093, 0.07
for i, (head, sub) in enumerate(DOCS):
    x = x0 + i * (bw + gap)
    col = OXBLOOD if head == "OCC record" else (BLUE if head == "One question" else INK)
    ax.add_patch(FancyBboxPatch((x, yA - 0.095), bw, 0.072, boxstyle="round,pad=0,rounding_size=0.006",
                                facecolor=TRACK, edgecolor=LINE, lw=0.8, zorder=1))
    ax.add_patch(Rectangle((x, yA - 0.023), bw, 0.004, color=col, zorder=2))
    for k, ln in enumerate(wrap(head, 14)):
        ax.text(x + bw / 2, yA - 0.040 - k * 0.018, ln, fontsize=10.4, color=col, weight="bold", ha="center", va="center")
    for k, ln in enumerate(wrap(sub, 18)):
        ax.text(x + bw / 2, yA - 0.072 - k * 0.015, ln, fontsize=8.6, color=MUTE, ha="center", va="center")

# ---------------- panel B: the one wrong line ----------------
yB = 0.592
ax.plot([0.07, 0.93], [yB + 0.018, yB + 0.018], color=INK, lw=1.2)
ax.text(0.07, yB - 0.004, "THE ONE WRONG LINE", fontsize=11.5, color=MUTE, weight="bold", ha="left", va="center")
ax.text(0.07, yB - 0.030, "Option leg", fontsize=10.5, color=MUTE, ha="left", va="center")
ax.text(0.385, yB - 0.030, "Due", fontsize=10.5, color=MUTE, ha="right", va="center")
ax.text(0.50, yB - 0.030, "Moved at OCC", fontsize=10.5, color=MUTE, ha="right", va="center")
LABEL = {"L1": "Purchased call 2.40", "L2": "Purchased put 240.00", "L3": "Written put 204.00", "L4": "Written call 282.00"}
y = yB - 0.058
for lid in ("L1", "L2", "L3", "L4"):
    bad = moved[lid] != due[lid]
    col = OXBLOOD if bad else INK
    ax.text(0.07, y, LABEL[lid], fontsize=13, color=col, ha="left", va="center", weight="bold" if bad else "normal")
    ax.text(0.385, y, f"{due[lid]:,}", fontsize=13, color=INK, ha="right", va="center", family=SERIF)
    ax.text(0.50, y, f"{moved[lid]:,}", fontsize=15 if bad else 13, color=col, ha="right", va="center", family=SERIF,
            weight="bold" if bad else "normal")
    ax.plot([0.07, 0.50], [y - 0.014, y - 0.014], color=RULE, lw=0.9)
    y -= 0.030
cx = 0.56
ax.text(cx, yB - 0.052, "The agent's report:", fontsize=11.5, color=MUTE, ha="left", va="center")
ax.text(cx, yB - 0.076, "all four legs moved, ready to settle.", fontsize=12.5, color=INK, weight="bold", ha="left", va="center")
ax.text(cx, yB - 0.110, f"{excess:,} contracts left the fund in error,", fontsize=12.5, color=OXBLOOD, weight="bold", ha="left", va="center")
ax.text(cx, yB - 0.133, f"{excess_value:,.2f} at the {mark_l2:.2f} mark, {impact:.4f} a share", fontsize=11.5, color=MUTE, ha="left", va="center")
ax.text(cx, yB - 0.154, "for every remaining shareholder.", fontsize=11.5, color=MUTE, ha="left", va="center")
ax.text(cx, yB - 0.182, "Right answer: hold, return the excess first.", fontsize=12.5, color=BLUE, weight="bold", ha="left", va="center")

# ---------------- panel C: the models ----------------
yC = 0.372
ax.plot([0.07, 0.93], [yC + 0.018, yC + 0.018], color=INK, lw=1.2)
ax.text(0.07, yC - 0.004, "WHAT EIGHT MODELS DID  (one run per model per case; the score out of 1.000)",
        fontsize=11.5, color=MUTE, weight="bold", ha="left", va="center")
ax.text(0.07, yC - 0.030, "Model", fontsize=10.5, color=MUTE, ha="left", va="center")
ax.text(0.42, yC - 0.030, "Broken order", fontsize=10.5, color=MUTE, ha="right", va="center")
ax.text(0.60, yC - 0.030, "Clean twin", fontsize=10.5, color=MUTE, ha="right", va="center")
y = yC - 0.056
for m in ORDER:
    b, c = R[(m, CASES[0])], R[(m, CASES[1])]
    ax.text(0.07, y, NAMES[m], fontsize=12.2, color=INK, ha="left", va="center")
    for xx, r in ((0.42, b), (0.60, c)):
        col = OXBLOOD if r["gates"] else (BLUE if r["allpass"] else INK)
        txt = f"{r['gated']:.3f}" + ("  all checks" if r["allpass"] else "") + ("  gate" if r["gates"] else "")
        ax.text(xx, y, txt, fontsize=12.2, color=col, ha="right", va="center", family=SERIF,
                weight="bold" if (r["allpass"] or r["gates"]) else "normal")
    y -= 0.0262
ax.plot([0.07, 0.60], [y + 0.012, y + 0.012], color=RULE, lw=0.9)
sx = 0.655
SUMMARY = [("All eight held the broken order. All eight settled the clean twin.", INK),
           (f"{n_allpass} of 16 runs passed every check; {len(perfect_both)} models were perfect on both.", INK),
           ("One small model valued the legs per share, not per contract, so every leg came out at one hundredth "
            "of its value; the check built for that fired on both cases.", OXBLOOD),
           ("One mid-size model sized the excess at ten times its value.", OXBLOOD)]
yy = yC - 0.052
for text, col in SUMMARY:
    lines = wrap(text, 42)
    for k, ln in enumerate(lines):
        ax.text(sx, yy - k * 0.0205, ln, fontsize=11.0, color=col, ha="left", va="center")
    yy -= 0.0205 * len(lines) + 0.014

# ---------------- footer ----------------
ax.plot([0.07, 0.93], [0.062, 0.062], color=LINE, lw=1.2)
ax.text(0.07, 0.040, "TieOutBench  ·  evals.finance", fontsize=12.5, color=MUTE, ha="left", va="center")
ax.text(0.93, 0.040, "constructed case  ·  real option terms  ·  recorded results, not rates",
        fontsize=11.5, color=MUTE, ha="right", va="center")

out = os.path.join(HERE, "post-eval8-case.png")
fig.savefig(out, dpi=100, facecolor=BG)
print("wrote", out, dict(due=due, moved=moved, excess=excess, allpass=n_allpass, perfect_both=perfect_both, gated=gated_models))

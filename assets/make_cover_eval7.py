#!/usr/bin/env python3
"""
assets/make_cover_eval7.py -- WIDE cover image for the eval-#7 (ETF NAV oversight) LinkedIn ARTICLE header.
Output: assets/cover-eval7.png (1200x630, ~1.91:1). Title left, the NAV ladder right, nothing important
near the edges (LinkedIn crops covers). A ledger-paper palette (cream, ink, oxblood, bottle green), distinct from the white/navy covers.
Every number is read from the case file and the saved runs; nothing is typed in.
Run: python assets/make_cover_eval7.py
"""
import glob
import json
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import yaml
from matplotlib.patches import FancyBboxPatch, Rectangle

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
# Ledger-paper scheme (deliberately not the white/navy/coral default): cream paper, warm ink,
# oxblood for the error, bottle green for the right call, faint ruled lines behind the ladder.
BG, NAVY, MUTE, LINE = "#F3EDE2", "#1C1A17", "#6E675C", "#D6CDBD"
BLUE, RED, ACC, TRACK = "#2F5D3A", "#8B2E2E", "#2F5D3A", "#E8E0D2"
GREEN, RULE, ROSE = "#2F5D3A", "#E6DECF", "#EADDD2"
SERIF = "DejaVu Serif"

# ---------------- the numbers ----------------
with open(os.path.join(REPO, "cases", "grsl-nav-2026.case.yaml"), encoding="utf-8") as fh:
    CASE = yaml.safe_load(fh)
TOT = CASE["package"]["totals"]
PRIOR = float(TOT["prior_nav_per_share"])          # 50.0000
ADMIN = float(TOT["nav_per_share"])                # 51.2412 (released package)
RIGHT = float(CASE["gold"]["C2"]["nav_per_share"])  # 51.9912 (recomputed)
ERR = float(CASE["gold"]["C3"]["nav_error_per_share"])   # -0.75
ERR_PCT = float(CASE["gold"]["C3"]["nav_error_pct"])     # -1.4426
EXPECTED = float(CASE["gold"]["C3"]["expected_move_pct"])  # 4.0
ADMIN_MOVE = float(CASE["gold"]["C3"]["admin_move_pct"])   # 2.4824
DAY = CASE["manifest"]["valuation_date"]

PAID = ["claude-opus-4-8", "claude-sonnet-4-6", "claude-haiku-4-5-20251001", "gpt-5.6-sol", "gpt-5.5",
        "gpt-5.4", "gpt-5.4-mini", "gemini-3.6-flash"]
LIVE = os.path.join(REPO, "outputs", "eval7-live")
allpass = holds = releases = runs = 0
for m in PAID:
    for case_id in ("grsl-nav-2026", "grsl-nav-2026-clean"):
        d = os.path.join(LIVE, m, case_id)
        with open(os.path.join(d, "run.json"), encoding="utf-8") as fh:
            allpass += int(json.load(fh)["score"]["allpass"])
        with open(os.path.join(d, "answer.json"), encoding="utf-8") as fh:
            dec = json.load(fh)["D1"]["decision"]
        if case_id == "grsl-nav-2026":
            holds += int(dec == "HOLD")
        else:
            releases += int(dec == "RELEASE")
        runs += 1
assert runs == 16 and abs(RIGHT - ADMIN + ERR) < 1e-6, (runs, RIGHT, ADMIN, ERR)
cents = round(abs(ERR) * 100)

# ---------------- canvas ----------------
fig = plt.figure(figsize=(12, 6.3), dpi=100)
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
ax.add_patch(Rectangle((0, 0), 1, 1, color=BG, zorder=0))

# ---------------- left: title ----------------
ax.text(0.045, 0.80, "One swap carried at", fontsize=30, color=NAVY, weight="bold", ha="left", va="center", family=SERIF)
ax.text(0.045, 0.70, "yesterday's price.", fontsize=30, color=NAVY, weight="bold", ha="left", va="center", family=SERIF)
ax.text(0.045, 0.60, "All eight AI models", fontsize=30, color=ACC, weight="bold", ha="left", va="center", family=SERIF)
ax.text(0.045, 0.50, "held the NAV.", fontsize=30, color=ACC, weight="bold", ha="left", va="center", family=SERIF)
ax.text(0.045, 0.385, f"An ETF's NAV package, {DAY:%d %B %Y}: the administrator's",
        fontsize=12.5, color=MUTE, ha="left", va="center")
ax.text(0.045, 0.335, f"{ADMIN:.4f} against the right {RIGHT:.4f}, {cents} cents a share.",
        fontsize=12.5, color=MUTE, ha="left", va="center")
ax.text(0.045, 0.285, f"{allpass} of {runs} runs passed every check. Recorded results, not rates.",
        fontsize=12.5, color=MUTE, ha="left", va="center")

# ---------------- right: the NAV ladder ----------------
X0, X1 = 0.565, 0.80          # the level lines
LO, HI = PRIOR - 0.35, RIGHT + 0.45   # value scale
Y0, Y1 = 0.17, 0.86


def yy(v):
    return Y0 + (v - LO) / (HI - LO) * (Y1 - Y0)


ax.add_patch(Rectangle((0.045, 0.885), 0.05, 0.012, color=NAVY, zorder=2))
ax.text(X0, 0.905, "NAV PER SHARE, ONE DAY", fontsize=10, color=MUTE, weight="bold", ha="left", va="center")
v = LO
while v <= HI:
    ax.plot([X0 - 0.01, 0.955], [yy(v)] * 2, color=RULE, lw=0.8, zorder=1)
    v += 0.25
ax.plot([X0 - 0.01, X0 - 0.01], [yy(LO) + 0.005, yy(HI) - 0.005], color=LINE, lw=1.0)
for v, label, color, lw in ((PRIOR, "prior day", MUTE, 1.6), (ADMIN, "administrator's package", RED, 2.6),
                            (RIGHT, "recomputed: the right NAV", GREEN, 2.6)):
    y = yy(v)
    ax.plot([X0, X1], [y, y], color=color, lw=lw, solid_capstyle="round", zorder=2)
    ax.text(X1 + 0.012, y + 0.012, f"{v:.4f}", fontsize=18, color=color, weight="bold", ha="left", va="center",
            family="DejaVu Sans Mono")
    ax.text(X1 + 0.012, y - 0.03, label, fontsize=9.5, color=MUTE, ha="left", va="center")

# the error bracket between the administrator's and the right NAV
xb = X0 + 0.04
ax.plot([xb, xb], [yy(ADMIN) + 0.004, yy(RIGHT) - 0.004], color=RED, lw=1.4, zorder=3)
ax.plot([xb - 0.008, xb + 0.008], [yy(ADMIN) + 0.004] * 2, color=RED, lw=1.4, zorder=3)
ax.plot([xb - 0.008, xb + 0.008], [yy(RIGHT) - 0.004] * 2, color=RED, lw=1.4, zorder=3)
ymid = (yy(ADMIN) + yy(RIGHT)) / 2
ax.add_patch(FancyBboxPatch((xb + 0.02, ymid - 0.055), 0.165, 0.11,
                            boxstyle="round,pad=0,rounding_size=0.012", facecolor=ROSE, edgecolor="none",
                            zorder=3))
ax.text(xb + 0.1025, ymid + 0.02, f"understated by ${abs(ERR):.4f}", fontsize=11.5, color=RED, weight="bold",
        ha="center", va="center", zorder=4)
ax.text(xb + 0.1025, ymid - 0.022, f"a share  ·  {abs(ERR_PCT):.2f}%  ·  gold: HOLD", fontsize=9.5, color=RED,
        ha="center", va="center", zorder=4)

# the day's move, under the ladder
ax.text(0.955, 0.125, f"Expected move +{EXPECTED:.2f}%  ·  package +{ADMIN_MOVE:.2f}%  ·  "
        f"decisions right {holds + releases} of {runs}", fontsize=9.5, color=MUTE, ha="right", va="center")

ax.plot([0.045, 0.955], [0.085, 0.085], color=LINE, lw=1.0)
ax.text(0.045, 0.05, "TieOutBench  ·  evals.finance", fontsize=10.5, color=MUTE, ha="left", va="center")
ax.text(0.955, 0.05, "eval #7: ETF NAV oversight (constructed package, real failure pattern)",
        fontsize=10.5, color=MUTE, ha="right", va="center")

out = os.path.join(HERE, "cover-eval7.png")
fig.savefig(out, dpi=100, facecolor=BG)
print("wrote", out, dict(prior=PRIOR, admin=ADMIN, right=RIGHT, err=ERR, allpass=allpass, holds=holds,
                         releases=releases, runs=runs))

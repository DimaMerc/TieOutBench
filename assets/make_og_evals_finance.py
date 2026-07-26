#!/usr/bin/env python3
"""
assets/make_og_evals_finance.py -- link-preview (Open Graph) card for evals.finance.
Output: docs/og.png (1200x630, ~1.91:1 -- the ratio LinkedIn/X/Slack crop to).
Lives in docs/ because that is the Vercel root directory, so it is served at
https://evals.finance/og.png. Same white/navy brand as the article covers.
Run: python assets/make_og_evals_finance.py
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "docs", "og.png")

BG    = "#FFFFFF"
NAVY  = "#16243B"
MUTE  = "#6B7785"
LINE  = "#C9D3DE"
LGREEN= "#7FD1A8"
ACC   = "#FF6B5E"

fig = plt.figure(figsize=(12, 6.3), dpi=100)
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
ax.add_patch(Rectangle((0, 0), 1, 1, color=BG, zorder=0))

# ---------------- header ----------------
ax.text(0.038, 0.90, "Where can you trust an AI with finance work?",
        fontsize=29, color=NAVY, weight="bold", ha="left", va="center")
ax.text(0.040, 0.815, "Runnable, rubric-graded evaluations - analyst workflows and the back office.",
        fontsize=13.5, color=MUTE, ha="left", va="center")
ax.plot([0.038, 0.962], [0.755, 0.755], color=LINE, lw=1.4, zorder=1)

# ---------------- left: the five evals ----------------
evals = [
    "Quarterly earnings analysis",
    "Defined-outcome (buffer) ETF diligence",
    "DCF valuation",
    "ETF creation / redemption reconciliation",
    "OTC swap confirmation matching",
]
y = 0.655
for name in evals:
    ax.plot([0.055], [y], marker="s", markersize=6, color=LGREEN, zorder=2)
    ax.text(0.085, y, name, fontsize=14.5, color=NAVY, va="center")
    y -= 0.098

# ---------------- right: the verdict panel ----------------
ax.add_patch(FancyBboxPatch((0.615, 0.115), 0.345, 0.545,
             boxstyle="round,pad=0.010,rounding_size=0.03",
             facecolor=NAVY, edgecolor="none", zorder=2))
PX = 0.7875
ax.text(PX, 0.560, "LOOKS RIGHT", fontsize=25, color="#FFFFFF", ha="center", va="center", weight="bold", zorder=3)
ax.text(PX, 0.455, "≠", fontsize=40, color=ACC, ha="center", va="center", weight="bold", zorder=3)
ax.text(PX, 0.350, "IS RIGHT", fontsize=25, color=ACC, ha="center", va="center", weight="bold", zorder=3)
ax.text(PX, 0.220, "Auto-fail gates catch what", fontsize=11.5, color="#C6D2E2", ha="center", va="center", zorder=3)
ax.text(PX, 0.175, "an average score rewards.", fontsize=11.5, color="#C6D2E2", ha="center", va="center", zorder=3)

# ---------------- footer ----------------
ax.plot([0.038, 0.962], [0.065, 0.065], color=LINE, lw=1.2)
ax.text(0.038, 0.035, "evals.finance", fontsize=11.5, color=NAVY, ha="left", va="center", weight="bold")
ax.text(0.962, 0.035, "gold cases · auto-fail gates · live model runs", fontsize=11, color=MUTE, ha="right", va="center")

fig.savefig(OUT, dpi=100, facecolor=BG)
print("wrote", OUT)

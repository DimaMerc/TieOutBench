#!/usr/bin/env python3
"""
assets/make_post_hitl.py -- SQUARE feed card for the "Human in the loop. But where?" post.
Output: assets/post-hitl.png (1080x1080). Same white/navy brand as the hero cards. The picture
shows the argument itself: the DECISION row (all models right) above the NUMBERS row (one
model 10x too small, one 10x too big), with the human placed on the numbers row - the tie-out.
Run: python assets/make_post_hitl.py
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyBboxPatch

HERE = os.path.dirname(os.path.abspath(__file__))
BG, NAVY, MUTE, LINE = "#FFFFFF", "#16243B", "#6B7785", "#C9D3DE"
GREEN, GREENBG = "#2E7D5B", "#E8F5EE"
RED, REDBG = "#C0392B", "#FBECEA"
ACC = "#FF6B5E"

fig = plt.figure(figsize=(10.8, 10.8), dpi=100)
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
ax.add_patch(Rectangle((0, 0), 1, 1, color=BG, zorder=0))

# ---------------- title ----------------
ax.text(0.07, 0.918, "Post-trade AI:", fontsize=40, color=NAVY, weight="bold", ha="left", va="center")
ax.text(0.07, 0.856, "Trust the call.", fontsize=40, color=NAVY, weight="bold", ha="left", va="center")
ax.text(0.07, 0.794, "Check the number.", fontsize=40, color=ACC, weight="bold", ha="left", va="center")
ax.text(0.07, 0.742, "Eight frontier models, one broken swap - and where the human belongs.",
        fontsize=14, color=MUTE, ha="left", va="center")
ax.plot([0.07, 0.93], [0.712, 0.712], color=LINE, lw=1.6)


def panel(y0, h, label, fill):
    ax.add_patch(FancyBboxPatch((0.07, y0), 0.86, h, boxstyle="round,pad=0,rounding_size=0.012",
                                facecolor=fill, edgecolor=LINE, lw=1.4, zorder=1))
    ax.text(0.095, y0 + h - 0.045, label, fontsize=12.5, color=MUTE, weight="bold", va="center")


# ---------------- panel 1: the decision ----------------
panel(0.535, 0.16, "THE DECISION", "#FFFFFF")
ax.text(0.095, 0.61, "“Mismatch. Do not affirm.”", fontsize=24, color=NAVY, weight="bold", va="center")
ax.add_patch(FancyBboxPatch((0.70, 0.575), 0.20, 0.07, boxstyle="round,pad=0,rounding_size=0.012",
                            facecolor=GREENBG, edgecolor=GREEN, lw=1.4, zorder=2))
ax.text(0.80, 0.61, "8 of 8 right", fontsize=16, color=GREEN, weight="bold", ha="center", va="center", zorder=3)

# ---------------- panel 2: the numbers underneath ----------------
panel(0.215, 0.29, "THE NUMBERS UNDERNEATH  —  “how big is the problem?”", "#FFFFFF")
cells = [
    ("0.5 bp", "EUR 2,500 / yr", "10x too small", RED, REDBG),
    ("5 bp", "EUR 25,000 / yr", "correct", NAVY, "#F3F6FA"),
    ("50 bp", "EUR 250,000 / yr", "10x too big", RED, REDBG),
]
x0, w, gap = 0.095, 0.255, 0.0325
for i, (big, money, tag, col, fill) in enumerate(cells):
    x = x0 + i * (w + gap)
    ax.add_patch(FancyBboxPatch((x, 0.255), w, 0.17, boxstyle="round,pad=0,rounding_size=0.012",
                                facecolor=fill, edgecolor=LINE, lw=1.2, zorder=2))
    ax.text(x + w / 2, 0.385, big, fontsize=26, color=col, weight="bold", ha="center", va="center", zorder=3)
    ax.text(x + w / 2, 0.325, money, fontsize=13.5, color=NAVY, ha="center", va="center", zorder=3)
    ax.text(x + w / 2, 0.281, tag, fontsize=12, color=col, weight="bold", ha="center", va="center", zorder=3)

# ---------------- the placement ----------------
ax.annotate("", xy=(0.50, 0.215), xytext=(0.50, 0.155),
            arrowprops=dict(arrowstyle="-|>", color=ACC, lw=3, mutation_scale=22))
ax.text(0.50, 0.118, "Put the human here: the tie-out.", fontsize=21, color=NAVY, weight="bold",
        ha="center", va="center")
ax.text(0.50, 0.078, "A number that does not tie out does not settle.", fontsize=13.5, color=MUTE,
        ha="center", va="center")

# ---------------- footer ----------------
ax.plot([0.07, 0.93], [0.045, 0.045], color=LINE, lw=1.2)
ax.text(0.07, 0.024, "TieOutBench  ·  evals.finance", fontsize=11, color=MUTE, va="center")
ax.text(0.93, 0.024, "eval #5 live runs, 2026", fontsize=11, color=MUTE, va="center", ha="right")

out = os.path.join(HERE, "post-hitl.png")
fig.savefig(out, dpi=100, facecolor=BG)
print("wrote", out)

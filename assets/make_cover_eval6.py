#!/usr/bin/env python3
"""
assets/make_cover_eval6.py -- WIDE cover image for the eval-#6 LinkedIn ARTICLE header.
Output: assets/cover-eval6.png (1200x630, ~1.91:1). Laid out horizontally: title left,
the three-step cascade right, nothing important near the edges (LinkedIn crops covers).
Same white/navy brand as the square hero. Run: python assets/make_cover_eval6.py
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle

HERE = os.path.dirname(os.path.abspath(__file__))
BG, NAVY, MUTE, LINE = "#FFFFFF", "#16243B", "#6B7785", "#C9D3DE"
GREEN, GREENBG, RED, REDBG, ACC = "#2E7D5B", "#EAF5EF", "#C0392B", "#FBECEA", "#FF6B5E"

fig = plt.figure(figsize=(12, 6.3), dpi=100)
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
ax.add_patch(Rectangle((0, 0), 1, 1, color=BG, zorder=0))

# ---------------- left: title ----------------
ax.text(0.045, 0.80, "The AI cited the", fontsize=30, color=NAVY, weight="bold", ha="left", va="center")
ax.text(0.045, 0.70, "right document", fontsize=30, color=NAVY, weight="bold", ha="left", va="center")
ax.text(0.045, 0.60, "and booked the", fontsize=30, color=NAVY, weight="bold", ha="left", va="center")
ax.text(0.045, 0.50, "wrong amount.", fontsize=30, color=ACC, weight="bold", ha="left", va="center")
ax.text(0.045, 0.385, "Eight frontier models, six cases on four real corporate actions:", fontsize=12.5, color=MUTE, ha="left", va="center")
ax.text(0.045, 0.335, "a split hitting an ETF basket, an oversubscribed tender,", fontsize=12.5, color=MUTE, ha="left", va="center")
ax.text(0.045, 0.285, "two corrected dividends. 48 runs, 32 clean.", fontsize=12.5, color=MUTE, ha="left", va="center")

# ---------------- right: the cascade ----------------
X0, W = 0.535, 0.42


def step(y, label, text, ok, detail):
    bg = GREENBG if ok else REDBG
    col = GREEN if ok else RED
    ax.add_patch(FancyBboxPatch((X0, y - 0.085), W, 0.17, boxstyle="round,pad=0.006,rounding_size=0.02",
                                facecolor=bg, edgecolor=col, lw=1.3, zorder=1))
    ax.text(X0 + 0.02, y + 0.045, label, fontsize=9.5, color=MUTE, weight="bold", ha="left", va="center", zorder=2)
    ax.text(X0 + 0.02, y - 0.002, text, fontsize=15, color=NAVY, weight="bold", ha="left", va="center", zorder=2)
    ax.text(X0 + 0.02, y - 0.05, detail, fontsize=10, color=MUTE, ha="left", va="center", zorder=2)
    ax.text(X0 + W - 0.03, y, "✓" if ok else "✗", fontsize=26, color=col, weight="bold",
            ha="center", va="center", zorder=2)


step(0.78, "THE DOCUMENT", "Pinned the correction", True, "listed the original as superseded, in its own worksheet")
step(0.56, "THE DATE", "Stated the corrected record date", True, "moved eleven days - quoted the new one")
step(0.34, "THE AMOUNT", "Booked \\$8,500 - owed \\$6,800", False, "shares from the ORIGINAL record date: 50,000, not 40,000")
ax.text(X0 + W / 2, 0.19, "Right story. Wrong number. Booked.", fontsize=13.5, color=NAVY, weight="bold",
        ha="center", va="center")
ax.text(X0 + W / 2, 0.145, "gated 0.225  vs  naive average 0.574", fontsize=11, color=MUTE, ha="center", va="center")

ax.plot([0.045, 0.955], [0.085, 0.085], color=LINE, lw=1.0)
ax.text(0.045, 0.05, "TieOutBench  ·  evals.finance", fontsize=10.5, color=MUTE, ha="left", va="center")
ax.text(0.955, 0.05, "eval #6: corporate-actions processing", fontsize=10.5, color=MUTE, ha="right", va="center")

out = os.path.join(HERE, "cover-eval6.png")
fig.savefig(out, dpi=100, facecolor=BG)
print("wrote", out)

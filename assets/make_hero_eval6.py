#!/usr/bin/env python3
"""
assets/make_hero_eval6.py -- SQUARE feed card for the eval-#6 driver post (1080x1080).
The cascade the eval was built to catch: right document, right date, wrong amount.
Same white/navy brand as the other cards. Run: python assets/make_hero_eval6.py
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle

HERE = os.path.dirname(os.path.abspath(__file__))
BG, NAVY, MUTE, LINE = "#FFFFFF", "#16243B", "#6B7785", "#C9D3DE"
GREEN, GREENBG, RED, REDBG, ACC = "#2E7D5B", "#EAF5EF", "#C0392B", "#FBECEA", "#FF6B5E"

fig = plt.figure(figsize=(10.8, 10.8), dpi=100)
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
ax.add_patch(Rectangle((0, 0), 1, 1, color=BG, zorder=0))

ax.text(0.07, 0.915, "Right document.", fontsize=42, color=NAVY, weight="bold", ha="left", va="center")
ax.text(0.07, 0.848, "Wrong amount.", fontsize=42, color=ACC, weight="bold", ha="left", va="center")
ax.text(0.07, 0.785, "One of eight frontier models, on a corrected dividend.",
        fontsize=14.5, color=MUTE, ha="left", va="center")
ax.plot([0.07, 0.93], [0.748, 0.748], color=LINE, lw=1.6)


def step(y, label, text, ok, detail):
    bg = GREENBG if ok else REDBG
    col = GREEN if ok else RED
    ax.add_patch(FancyBboxPatch((0.07, y - 0.075), 0.86, 0.15, boxstyle="round,pad=0.008,rounding_size=0.014",
                                facecolor=bg, edgecolor=col, lw=1.4, zorder=1))
    ax.text(0.10, y + 0.036, label, fontsize=11.5, color=MUTE, weight="bold", ha="left", va="center", zorder=2)
    ax.text(0.10, y - 0.005, text, fontsize=21, color=NAVY, weight="bold", ha="left", va="center", zorder=2)
    ax.text(0.10, y - 0.048, detail, fontsize=12.5, color=MUTE, ha="left", va="center", zorder=2)
    mark = "✓" if ok else "✗"
    ax.text(0.885, y, mark, fontsize=34, color=col, weight="bold", ha="center", va="center", zorder=2)


step(0.640, "THE DOCUMENT", "Pinned the correction, not the original", True,
     "Listed the original announcement as superseded, in its own worksheet")
step(0.455, "THE DATE", "Stated the corrected record date", True,
     "Record date moved eleven days; the model quoted the new one")
step(0.270, "THE AMOUNT", "Booked \\$8,500. The right figure was \\$6,800.", False,
     "Counted the shares from the ORIGINAL record date - 50,000, not 40,000 - and booked it")

ax.text(0.50, 0.150, "Right story. Wrong number. Booked.", fontsize=22, color=NAVY, weight="bold",
        ha="center", va="center")
ax.text(0.50, 0.108, "Two auto-fail gates fired. Gated score 0.225 - naive average 0.574.",
        fontsize=13, color=MUTE, ha="center", va="center")

ax.plot([0.07, 0.93], [0.062, 0.062], color=LINE, lw=1.2)
ax.text(0.07, 0.035, "TieOutBench  ·  evals.finance", fontsize=12, color=MUTE, ha="left", va="center")
ax.text(0.93, 0.035, "eval #6: corporate actions, 8 models x 6 cases on 4 real events", fontsize=12, color=MUTE, ha="right", va="center")

out = os.path.join(HERE, "hero-eval6.png")
fig.savefig(out, dpi=100, facecolor=BG)
print("wrote", out)

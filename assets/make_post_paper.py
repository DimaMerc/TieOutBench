#!/usr/bin/env python3
"""
assets/make_post_paper.py -- SQUARE feed card for the paper-announcement post (1080x1080).
The banked opening line, the report, three stat tiles. Run: python assets/make_post_paper.py
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle

HERE = os.path.dirname(os.path.abspath(__file__))
BG, NAVY, MUTE, LINE, PANEL, ACC = "#FFFFFF", "#16243B", "#6B7785", "#C9D3DE", "#F3F6FA", "#FF6B5E"

fig = plt.figure(figsize=(10.8, 10.8), dpi=100)
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
ax.add_patch(Rectangle((0, 0), 1, 1, color=BG, zorder=0))

ax.text(0.07, 0.905, "AI doesn't just make", fontsize=38, color=NAVY, weight="bold", ha="left", va="center")
ax.text(0.07, 0.840, "right answers faster.", fontsize=38, color=NAVY, weight="bold", ha="left", va="center")
ax.text(0.07, 0.760, "It makes wrong ones", fontsize=38, color=ACC, weight="bold", ha="left", va="center")
ax.text(0.07, 0.695, "more convincing.", fontsize=38, color=ACC, weight="bold", ha="left", va="center")
ax.plot([0.07, 0.93], [0.635, 0.635], color=LINE, lw=1.6)

ax.text(0.07, 0.585, "TIEOUTBENCH  ·  TECHNICAL REPORT  ·  NOW ON SSRN", fontsize=12.5,
        color=MUTE, weight="bold", ha="left", va="center")
ax.text(0.07, 0.530, "Measuring whether an LLM's finance work ties out -", fontsize=17, color=NAVY, ha="left", va="center")
ax.text(0.07, 0.488, "before deciding whether to trust it.", fontsize=17, color=NAVY, ha="left", va="center")

tiles = [("5", "finance workflows,\nanalyst and back office"),
         ("14", "gold cases, every figure\ncited or labeled constructed"),
         ("8 x 3", "frontier models x vendors,\nevery run published")]
x = 0.07
for big, small in tiles:
    ax.add_patch(FancyBboxPatch((x, 0.215), 0.263, 0.215, boxstyle="round,pad=0.006,rounding_size=0.014",
                                facecolor=PANEL, edgecolor=LINE, lw=1.2, zorder=1))
    ax.text(x + 0.1315, 0.375, big, fontsize=34, color=NAVY, weight="bold", ha="center", va="center", zorder=2)
    ax.text(x + 0.1315, 0.275, small, fontsize=11.5, color=MUTE, ha="center", va="center", zorder=2, linespacing=1.4)
    x += 0.2985

ax.text(0.50, 0.150, "Auto-fail gates for the errors that quietly poison a memo.", fontsize=14,
        color=NAVY, ha="center", va="center")
ax.text(0.50, 0.112, "Credit for saying \"not determinable\" instead of guessing.", fontsize=14,
        color=NAVY, ha="center", va="center")

ax.plot([0.07, 0.93], [0.062, 0.062], color=LINE, lw=1.2)
ax.text(0.07, 0.035, "TieOutBench  ·  evals.finance", fontsize=12, color=MUTE, ha="left", va="center")
ax.text(0.93, 0.035, "SSRN abstract 7243025", fontsize=12, color=MUTE, ha="right", va="center")

out = os.path.join(HERE, "post-paper.png")
fig.savefig(out, dpi=100, facecolor=BG)
print("wrote", out)

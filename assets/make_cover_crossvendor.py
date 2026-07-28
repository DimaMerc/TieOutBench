#!/usr/bin/env python3
"""
assets/make_cover_crossvendor.py -- WIDE cover for the cross-vendor LinkedIn ARTICLE header.
Output: assets/cover-crossvendor.png (1200x630, ~1.91:1). Same white/navy brand as the eval-5 and
SR 26-2 covers: title + subtitle across the top, the starved-vs-fair grid on the left, the lesson
panel on the right, nothing important near the edges.
Run: python assets/make_cover_crossvendor.py
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle

HERE = os.path.dirname(os.path.abspath(__file__))
BG    = "#FFFFFF"
REDBG = "#FBECEA"
NAVY  = "#16243B"
GREEN = "#2E7D5B"
RED   = "#C0392B"
MUTE  = "#6B7785"
LINE  = "#C9D3DE"
LGREEN= "#7FD1A8"
ACC   = "#FF6B5E"
MONO  = "DejaVu Sans Mono"

fig = plt.figure(figsize=(12, 6.3), dpi=100)
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
ax.add_patch(Rectangle((0, 0), 1, 1, color=BG, zorder=0))

# ---------------- header ----------------
ax.text(0.038, 0.90, "Same models. Same task. Different budget.",
        fontsize=28, color=NAVY, weight="bold", ha="left", va="center")
ax.text(0.040, 0.815, "Eight frontier models, three vendors - and the first three findings were bugs in my own harness.",
        fontsize=13, color=MUTE, ha="left", va="center")
ax.plot([0.038, 0.962], [0.755, 0.755], color=LINE, lw=1.4, zorder=1)

# ---------------- left: starved vs fair ----------------
CX_TERM, CX_BAD, CX_OK = 0.055, 0.330, 0.500
TOP = 0.680
ax.text(CX_TERM, TOP, "DCF CASE",  fontsize=10.5, color=MUTE, weight="bold", va="center")
ax.text(CX_BAD,  TOP, "STARVED",   fontsize=10.5, color=RED,  weight="bold", va="center", ha="center")
ax.text(CX_OK,   TOP, "FAIR",      fontsize=10.5, color=GREEN,weight="bold", va="center", ha="center")

rows = [
    ("Model A", "empty",  "0.953"),
    ("Model B", "0.322",  "0.951"),
    ("Model C", "0.618",  "0.903"),
    ("Model D", "0.745",  "0.631"),
]
y = TOP - 0.088
rh = 0.105
for term, bad, ok in rows:
    ax.add_patch(Rectangle((0.035, y - rh/2 + 0.008), 0.535, rh - 0.010, facecolor=REDBG, zorder=1))
    ax.text(CX_TERM, y, term, fontsize=13, color=NAVY, va="center")
    ax.text(CX_BAD,  y, bad,  fontsize=14, color=RED,   va="center", ha="center", weight="bold", family=MONO)
    ax.text(0.415,   y, "->", fontsize=12, color=MUTE,  va="center", ha="center", family=MONO)
    ax.text(CX_OK,   y, ok,   fontsize=14, color=GREEN, va="center", ha="center", weight="bold", family=MONO)
    y -= rh

# ---------------- right: the lesson panel ----------------
ax.add_patch(FancyBboxPatch((0.615, 0.115), 0.345, 0.545,
             boxstyle="round,pad=0.010,rounding_size=0.03",
             facecolor=NAVY, edgecolor="none", zorder=2))
PX = 0.7875
ax.text(PX, 0.585, "Nothing crashed.", fontsize=13.5, color="#C6D2E2", ha="center", va="center", zorder=3)
ax.text(PX, 0.530, "Nothing warned.", fontsize=13.5, color="#C6D2E2", ha="center", va="center", zorder=3)
ax.text(PX, 0.415, "FOUR WRONG", fontsize=25, color=ACC, ha="center", va="center", weight="bold", zorder=3)
ax.text(PX, 0.340, "SCORES", fontsize=25, color=ACC, ha="center", va="center", weight="bold", zorder=3)
ax.text(PX, 0.230, "Prove your harness gave", fontsize=11.5, color=LGREEN, ha="center", va="center", weight="bold", zorder=3)
ax.text(PX, 0.183, "each model the same room.", fontsize=11.5, color=LGREEN, ha="center", va="center", weight="bold", zorder=3)

# ---------------- footer ----------------
ax.plot([0.038, 0.962], [0.065, 0.065], color=LINE, lw=1.2)
ax.text(0.038, 0.035, "evals.finance", fontsize=11, color=NAVY, ha="left", va="center", weight="bold")
ax.text(0.962, 0.035, "8 models · 3 vendors · 5 gold cases", fontsize=11, color=MUTE, ha="right", va="center")

fig.savefig(os.path.join(HERE, "cover-crossvendor.png"), dpi=100, facecolor=BG)
print("wrote", os.path.join(HERE, "cover-crossvendor.png"))

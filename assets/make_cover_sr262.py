#!/usr/bin/env python3
"""
assets/make_cover_sr262.py -- WIDE cover image for the SR 26-2 LinkedIn ARTICLE header.
Output: assets/cover-sr262.png (1200x630, ~1.91:1 -- LinkedIn crops article covers to a wide
banner). Same white/navy brand and layout language as cover-eval5: title + subtitle across
the top, a scope grid on the left, the verdict panel on the right, nothing important near
the edges. Run: python assets/make_cover_sr262.py
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
ax.text(0.038, 0.90, "The new model-risk rules skip generative AI.",
        fontsize=28, color=NAVY, weight="bold", ha="left", va="center")
ax.text(0.040, 0.815, "SR 11-7 is gone. Its replacement leaves the AI now doing finance work to you.",
        fontsize=13.5, color=MUTE, ha="left", va="center")
ax.plot([0.038, 0.962], [0.755, 0.755], color=LINE, lw=1.4, zorder=1)

# ---------------- left: the scope grid ----------------
CX_TERM, CX_STAT = 0.055, 0.435
TOP = 0.685
ax.text(CX_TERM, TOP, "MODEL TYPE", fontsize=10.5, color=MUTE, weight="bold", va="center")
ax.text(CX_STAT, TOP, "SR 26-2 (APR 2026)", fontsize=10.5, color=NAVY, weight="bold", va="center", ha="center")

rows = [
    ("Credit risk models",   "in scope",     True),
    ("Market risk models",   "in scope",     True),
    ("Pricing & valuation",  "in scope",     True),
    ("Generative AI",        "OUT OF SCOPE", False),
    ("Agentic AI",           "OUT OF SCOPE", False),
]
y = TOP - 0.085
rh = 0.098
for term, status, ok in rows:
    if not ok:
        ax.add_patch(Rectangle((0.035, y - rh/2 + 0.006), 0.535, rh - 0.006, facecolor=REDBG, zorder=1))
    vc = GREEN if ok else RED
    vw = "normal" if ok else "bold"
    ax.text(CX_TERM, y, term, fontsize=13.5, color=NAVY, va="center", weight=("normal" if ok else "bold"))
    ax.text(CX_STAT, y, status, fontsize=13, color=vc, va="center", ha="center", weight=vw, family=MONO)
    y -= rh

# ---------------- right: the verdict panel ----------------
ax.add_patch(FancyBboxPatch((0.615, 0.115), 0.345, 0.545,
             boxstyle="round,pad=0.010,rounding_size=0.03",
             facecolor=NAVY, edgecolor="none", zorder=2))
PX = 0.7875   # panel center
ax.text(PX, 0.585, '"novel and rapidly evolving"', fontsize=13, color="#C6D2E2", ha="center", va="center", zorder=3, style="italic")
ax.text(PX, 0.470, "OUT OF SCOPE", fontsize=29, color=ACC, ha="center", va="center", weight="bold", zorder=3)
ax.text(PX, 0.385, "IS NOT OFF THE HOOK", fontsize=17.5, color="#FFFFFF", ha="center", va="center", weight="bold", zorder=3)
ax.text(PX, 0.250, "Validate the work,", fontsize=14, color=LGREEN, ha="center", va="center", weight="bold", zorder=3)
ax.text(PX, 0.195, "not the weights.", fontsize=14, color=LGREEN, ha="center", va="center", weight="bold", zorder=3)

# ---------------- footer ----------------
ax.plot([0.038, 0.962], [0.065, 0.065], color=LINE, lw=1.2)
ax.text(0.038, 0.035, "TieOutBench", fontsize=11, color=NAVY, ha="left", va="center", weight="bold")
ax.text(0.962, 0.035, "gold sets · auto-fail gates · challenger runs · receipts", fontsize=11, color=MUTE, ha="right", va="center")

fig.savefig(os.path.join(HERE, "cover-sr262.png"), dpi=100, facecolor=BG)
print("wrote", os.path.join(HERE, "cover-sr262.png"))

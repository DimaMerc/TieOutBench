#!/usr/bin/env python3
"""
assets/make_cover_eval6_phase2.py -- WIDE cover image for the eval-#6 Phase-2 LinkedIn ARTICLE header.
Output: assets/cover-eval6-phase2.png (1200x630, ~1.91:1). Title left, the four arms right, nothing
important near the edges (LinkedIn crops covers). Same white/navy brand as the other covers.
Every number is read from outputs/eval6-agent/summary.json; nothing is typed in.
Run: python assets/make_cover_eval6_phase2.py
"""
import json
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
BG, NAVY, MUTE, LINE = "#FFFFFF", "#16243B", "#6B7785", "#C9D3DE"
BLUE, RED, ACC, TRACK = "#2a78d6", "#d03b3b", "#FF6B5E", "#EEF2F6"

with open(os.path.join(REPO, "outputs", "eval6-agent", "summary.json"), encoding="utf-8") as fh:
    S = json.load(fh)


def clean(arm):
    cells = S[arm].values()
    return sum(int(c["allpass"] if arm == "plain" else c["terminal"]["allpass"]) for c in cells), len(S[arm])


ARMS = [("plain", "Prompt only", BLUE), ("tools", "With tools", BLUE),
        ("checker", "Tools + AI checker (same model)", RED),
        ("checker-fixed", "Tools + AI checker (stronger model)", RED)]
ROWS = [(label, color) + clean(arm) for arm, label, color in ARMS]
N = ROWS[0][3]

fig = plt.figure(figsize=(12, 6.3), dpi=100)
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
ax.add_patch(Rectangle((0, 0), 1, 1, color=BG, zorder=0))

# ---------------- left: title ----------------
ax.text(0.045, 0.80, "An AI checker", fontsize=30, color=NAVY, weight="bold", ha="left", va="center")
ax.text(0.045, 0.70, "reviewed the work.", fontsize=30, color=NAVY, weight="bold", ha="left", va="center")
ax.text(0.045, 0.60, "Fewer runs passed", fontsize=30, color=ACC, weight="bold", ha="left", va="center")
ax.text(0.045, 0.50, "every check.", fontsize=30, color=ACC, weight="bold", ha="left", va="center")
ax.text(0.045, 0.385, "Eight AI models, six corporate-actions cases,", fontsize=12.5, color=MUTE, ha="left", va="center")
ax.text(0.045, 0.335, "the same grader, four ways of working.", fontsize=12.5, color=MUTE, ha="left", va="center")
ax.text(0.045, 0.285, f"{N} runs each. Recorded results, not rates.", fontsize=12.5, color=MUTE, ha="left", va="center")

# ---------------- right: the four arms ----------------
X0, W = 0.535, 0.42
ax.text(X0, 0.875, f"RUNS THAT PASSED EVERY CHECK, OF {N}", fontsize=10, color=MUTE, weight="bold",
        ha="left", va="center")
y = 0.76
for label, color, n, total in ROWS:
    ax.text(X0, y + 0.048, label, fontsize=12.5, color=NAVY, ha="left", va="center")
    ax.add_patch(FancyBboxPatch((X0, y - 0.03), W - 0.07, 0.05, boxstyle="round,pad=0,rounding_size=0.012",
                                facecolor=TRACK, edgecolor="none", zorder=1))
    ax.add_patch(FancyBboxPatch((X0, y - 0.03), (W - 0.07) * n / total, 0.05,
                                boxstyle="round,pad=0,rounding_size=0.012", facecolor=color, edgecolor="none",
                                zorder=2))
    ax.text(X0 + W - 0.055, y - 0.005, f"{n}", fontsize=19, color=NAVY, weight="bold", ha="left", va="center")
    y -= 0.155

ax.plot([0.045, 0.955], [0.085, 0.085], color=LINE, lw=1.0)
ax.text(0.045, 0.05, "TieOutBench  ·  evals.finance", fontsize=10.5, color=MUTE, ha="left", va="center")
ax.text(0.955, 0.05, "eval #6, phase 2: the agent environment", fontsize=10.5, color=MUTE, ha="right", va="center")

out = os.path.join(HERE, "cover-eval6-phase2.png")
fig.savefig(out, dpi=100, facecolor=BG)
print("wrote", out, [(r[0], r[2]) for r in ROWS])

#!/usr/bin/env python3
"""
assets/make_og_checker_paper.py -- the Open Graph preview image (1200x630) for https://evals.finance/checker-paper,
the landing page of the second technical report ("A Second AI as Checker"). LinkedIn's Featured and link cards take their
thumbnail from this image. Ledger-paper palette, no green. Every number is read from outputs/eval6-agent/summary.json and
asserted; nothing is typed in.
Run: python assets/make_og_checker_paper.py   (writes assets/og-checker-paper.png and docs/og-checker-paper.png)
"""
import json
import os
import shutil
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyBboxPatch

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
BG, INK, MUTE, LINE = "#F3EDE2", "#1C1A17", "#6E675C", "#D6CDBD"
BLUE, OXBLOOD, TRACK = "#1E3F66", "#8B2E2E", "#E8E0D2"
SERIF = "DejaVu Serif"

with open(os.path.join(REPO, "outputs", "eval6-agent", "summary.json"), encoding="utf-8") as fh:
    S = json.load(fh)
C = S["counts"]
N = C["tools"]["n"]
ARMS = [("Documents in one prompt", C["plain"]["allpass"], BLUE),
        ("With tools", C["tools"]["allpass"], BLUE),
        ("A second AI of the same model as checker", C["checker"]["allpass"], OXBLOOD),
        ("A stronger AI as checker", C["checker-fixed"]["allpass"], OXBLOOD)]
assert all(C[k]["n"] == N for k in ("plain", "tools", "checker", "checker-fixed")), C
assert (N, [a[1] for a in ARMS]) == (48, [32, 35, 27, 25]), (N, ARMS)

fig = plt.figure(figsize=(12.0, 6.3), dpi=100)
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
ax.add_patch(Rectangle((0, 0), 1, 1, color=BG, zorder=0))

# title block (left two thirds)
ax.add_patch(Rectangle((0.06, 0.885), 0.05, 0.012, color=INK, zorder=2))
ax.text(0.06, 0.78, "A Second AI", fontsize=46, color=INK, weight="bold", ha="left", va="center", family=SERIF)
ax.text(0.06, 0.655, "as Checker.", fontsize=46, color=BLUE, weight="bold", ha="left", va="center", family=SERIF)
ax.text(0.06, 0.545, "Measuring a maker-checker protocol for LLM agents", fontsize=15.5, color=MUTE, ha="left", va="center")
ax.text(0.06, 0.492, "on corporate-actions processing. Technical report, October 2026.", fontsize=15.5, color=MUTE, ha="left", va="center")

# the four arms (lower half)
ax.text(0.06, 0.418, f"RUNS THAT PASSED EVERY CHECK, OF {N}", fontsize=11.5, color=MUTE, weight="bold", ha="left", va="center")
X0, W = 0.06, 0.60
y = 0.345
for label, n, color in ARMS:
    ax.text(X0, y + 0.034, label, fontsize=12, color=INK, ha="left", va="center")
    ax.add_patch(FancyBboxPatch((X0, y - 0.012), W, 0.024, boxstyle="round,pad=0,rounding_size=0.01", facecolor=TRACK, edgecolor="none", zorder=1))
    ax.add_patch(FancyBboxPatch((X0, y - 0.012), W * n / N, 0.024, boxstyle="round,pad=0,rounding_size=0.01", facecolor=color, edgecolor="none", zorder=2))
    ax.text(X0 + W + 0.018, y, f"{n}", fontsize=20, color=color, weight="bold", ha="left", va="center", family=SERIF)
    y -= 0.072

# upper right: the one-line finding, in the space beside the title
ax.text(0.94, 0.80, "The reviewer had the documents", fontsize=13.5, color=INK, ha="right", va="center")
ax.text(0.94, 0.755, "but not the rules the maker", fontsize=13.5, color=INK, ha="right", va="center")
ax.text(0.94, 0.71, "worked to.", fontsize=13.5, color=INK, ha="right", va="center")

ax.plot([0.06, 0.94], [0.078, 0.078], color=LINE, lw=1.2)
ax.text(0.06, 0.042, "TieOutBench  ·  evals.finance", fontsize=12, color=MUTE, ha="left", va="center")
ax.text(0.94, 0.042, "SSRN 7611299  ·  every run published", fontsize=12, color=MUTE, ha="right", va="center")

out = os.path.join(HERE, "og-checker-paper.png")
fig.savefig(out, dpi=100, facecolor=BG)
shutil.copyfile(out, os.path.join(REPO, "docs", "og-checker-paper.png"))
print("wrote", out, "and docs/og-checker-paper.png", dict(n=N, arms=[a[1] for a in ARMS]))

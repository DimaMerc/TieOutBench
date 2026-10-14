#!/usr/bin/env python3
"""
assets/make_cover_positive_case.py -- WIDE cover image for the article "Eight things LinkedIn says about AI,
checked against the measured record". Output: assets/cover-positive-case.png (1200x630).
Title left, a verdict ledger right: the ten claims as the article states them, each with one mark
(ink blue: the record says no; oxblood: the critics are right; grey: undecided) and a four-word note that
matches the article's verdict lines. Ledger-paper palette, as assets/cover-eval7.png. No numbers on the
cover; the article carries them with their sources.
Run: python assets/make_cover_positive_case.py
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

HERE = os.path.dirname(os.path.abspath(__file__))
BG, INK, MUTE, LINE = "#F3EDE2", "#1C1A17", "#6E675C", "#D6CDBD"
# "the record says no" is ink blue, not green: every AI-made image is green, his words.
GREEN, OXBLOOD, GREY, RULE = "#1E3F66", "#8B2E2E", "#9A938A", "#E6DECF"
SERIF = "DejaVu Serif"

# the eight claims, in the article's order, with the article's verdict in one mark and a few words
ROWS = [
    ("Costs too much, does too little",     GREEN,   "no; financing is the risk"),
    ("No measurable productivity gain",     GREY,    "task-level yes, economy small"),
    ("Everyone will lose their job",        OXBLOOD, "entry level yes, economy no"),
    ("Superintelligence any day now",       GREY,    "contested among experts"),
    ("Too many errors, cannot learn",       GREY,    "errors falling; learning: true"),
    ("It agrees with everything",           OXBLOOD, "true; the serious form is harm"),
    ("Steals books, pays nobody",           GREEN,   "piracy paid; training in court"),
    ("Agents run amok, then we all die",    OXBLOOD, "agents: real; extinction: contested"),
    None,
    ("It eats the grid, drinks the water",  OXBLOOD, "real, rising, locally acute"),
    ("Europe depends on a few US firms",    OXBLOOD, "real; models less, clouds more"),
]

fig = plt.figure(figsize=(12, 6.3), dpi=100)
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
ax.add_patch(Rectangle((0, 0), 1, 1, color=BG, zorder=0))

# ---------------- left: title ----------------
ax.add_patch(Rectangle((0.045, 0.885), 0.05, 0.012, color=INK, zorder=2))
ax.text(0.045, 0.80, "Ten claims", fontsize=30, color=INK, weight="bold", ha="left", va="center", family=SERIF)
ax.text(0.045, 0.70, "about AI,", fontsize=30, color=INK, weight="bold", ha="left", va="center", family=SERIF)
ax.text(0.045, 0.60, "checked against", fontsize=30, color=GREEN, weight="bold", ha="left", va="center", family=SERIF)
ax.text(0.045, 0.50, "the record.", fontsize=30, color=GREEN, weight="bold", ha="left", va="center", family=SERIF)
ax.text(0.045, 0.385, "Eight claims the feed makes and two it leaves out,", fontsize=12.5, color=MUTE, ha="left", va="center")
ax.text(0.045, 0.335, "against sources dated 2025 to October 2026. Where", fontsize=12.5, color=MUTE, ha="left", va="center")
ax.text(0.045, 0.285, "the critics are right, it says so.", fontsize=12.5, color=MUTE, ha="left", va="center")

# ---------------- right: the verdict ledger ----------------
X0, XM, XN, X1 = 0.50, 0.515, 0.755, 0.955
ax.text(X0, 0.905, "THE CLAIM", fontsize=9.5, color=MUTE, weight="bold", ha="left", va="center")
ax.text(XN, 0.905, "THE RECORD", fontsize=9.5, color=MUTE, weight="bold", ha="left", va="center")
ax.plot([X0 - 0.01, X1], [0.88, 0.88], color=LINE, lw=1.0)
top, step = 0.838, 0.0665
y = top
for row in ROWS:
    if row is None:
        ax.plot([X0 - 0.01, X1], [y + 0.021, y + 0.021], color=INK, lw=0.9, zorder=2)
        ax.text(X0, y + 0.002, "AND TWO THE FEED LEAVES OUT", fontsize=8.5, color=MUTE, weight="bold", ha="left", va="center")
        y -= 0.036
        continue
    claim, color, note = row
    ax.plot([X0 - 0.01, X1], [y - step / 2, y - step / 2], color=RULE, lw=0.8, zorder=1)
    ax.scatter([XM - 0.004], [y], s=60, color=color, zorder=3, linewidths=0)
    ax.text(XM + 0.012, y, f"“{claim}”", fontsize=10, color=INK, ha="left", va="center")
    ax.text(XN, y, note, fontsize=9, color=color, ha="left", va="center", weight="bold")
    y -= step

# legend
ly = y + step / 2 - 0.028
for k, (color, label) in enumerate(((GREEN, "the record says no"), (OXBLOOD, "the critics are right"), (GREY, "undecided or contested"))):
    x = X0 + k * 0.155
    ax.scatter([x], [ly], s=40, color=color, zorder=3, linewidths=0)
    ax.text(x + 0.012, ly, label, fontsize=9, color=MUTE, ha="left", va="center")

ax.plot([0.045, 0.955], [0.085, 0.085], color=LINE, lw=1.0)
ax.text(0.045, 0.05, "TieOutBench  ·  evals.finance", fontsize=10.5, color=MUTE, ha="left", va="center")
ax.text(0.955, 0.05, "every number in the article has a dated source", fontsize=10.5, color=MUTE, ha="right", va="center")

out = os.path.join(HERE, "cover-positive-case.png")
fig.savefig(out, dpi=100, facecolor=BG)
print("wrote", out)

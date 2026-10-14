#!/usr/bin/env python3
"""
assets/make_post_image_positive_case.py -- PORTRAIT image (1080x1350, 4:5) for the FEED POST that drives the
article "Eight things LinkedIn says about AI, checked against the record, and two it leaves out".
Same verdict ledger as the article cover (assets/make_cover_positive_case.py), set larger for a phone screen:
ink blue where the record says no, oxblood where the critics are right, grey where it is undecided or
contested. Cream paper, ink, serif title. No numbers; the article carries them.
Run: python assets/make_post_image_positive_case.py
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

HERE = os.path.dirname(os.path.abspath(__file__))
BG, INK, MUTE, LINE = "#F3EDE2", "#1C1A17", "#6E675C", "#D6CDBD"
BLUE, OXBLOOD, GREY, RULE = "#1E3F66", "#8B2E2E", "#9A938A", "#E6DECF"
SERIF = "DejaVu Serif"

# keep in step with ROWS in make_cover_positive_case.py
ROWS = [
    ("Costs too much, does too little",     BLUE,    "no; financing is the risk"),
    ("No measurable productivity gain",     GREY,    "task-level yes, economy small"),
    ("Everyone will lose their job",        OXBLOOD, "entry level yes, economy no"),
    ("Superintelligence any day now",       GREY,    "contested among experts"),
    ("Too many errors, cannot learn",       GREY,    "errors falling; learning: true"),
    ("It agrees with everything",           OXBLOOD, "true; the serious form is harm"),
    ("Steals books, pays nobody",           BLUE,    "piracy paid; training in court"),
    ("Agents run amok, then we all die",    OXBLOOD, "agents: real; extinction: contested"),
    None,
    ("It eats the grid, drinks the water",  OXBLOOD, "real, rising, locally acute"),
    ("Europe depends on a few US firms",    OXBLOOD, "real; models less, clouds more"),
]

fig = plt.figure(figsize=(10.8, 13.5), dpi=100)
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
ax.add_patch(Rectangle((0, 0), 1, 1, color=BG, zorder=0))

# ---------------- title block ----------------
ax.add_patch(Rectangle((0.07, 0.935), 0.06, 0.006, color=INK, zorder=2))
ax.text(0.07, 0.885, "Ten claims about AI,", fontsize=34, color=INK, weight="bold", ha="left", va="center", family=SERIF)
ax.text(0.07, 0.835, "checked against the record.", fontsize=34, color=BLUE, weight="bold", ha="left", va="center", family=SERIF)
ax.text(0.07, 0.785, "Eight the feed makes, two it leaves out. Sources dated 2025 to October 2026.",
        fontsize=14, color=MUTE, ha="left", va="center")

# ---------------- the ledger ----------------
X0, XM, X1 = 0.07, 0.085, 0.93
ax.text(X0, 0.735, "THE CLAIM", fontsize=12, color=MUTE, weight="bold", ha="left", va="center")
ax.text(X1, 0.735, "THE RECORD", fontsize=12, color=MUTE, weight="bold", ha="right", va="center")
ax.plot([X0, X1], [0.718, 0.718], color=LINE, lw=1.2)
top, step = 0.688, 0.0545
y = top
for row in ROWS:
    if row is None:
        ax.plot([X0, X1], [y + 0.016, y + 0.016], color=INK, lw=1.2, zorder=2)
        ax.text(X0, y - 0.002, "AND TWO THE FEED LEAVES OUT", fontsize=11, color=MUTE, weight="bold", ha="left", va="center")
        y -= 0.046
        continue
    claim, color, note = row
    ax.plot([X0, X1], [y - step / 2, y - step / 2], color=RULE, lw=1.0, zorder=1)
    ax.scatter([XM], [y + 0.011], s=75, color=color, zorder=3, linewidths=0)
    ax.text(XM + 0.028, y + 0.011, f"“{claim}”", fontsize=15.5, color=INK, ha="left", va="center")
    ax.text(X1, y - 0.013, note, fontsize=13, color=color, ha="right", va="center", weight="bold")
    y -= step

# legend
ly = y + step / 2 - 0.026
for k, (color, label) in enumerate(((BLUE, "the record says no"), (OXBLOOD, "the critics are right"), (GREY, "undecided or contested"))):
    x = X0 + k * 0.30
    ax.scatter([x + 0.006], [ly], s=50, color=color, zorder=3, linewidths=0)
    ax.text(x + 0.024, ly, label, fontsize=11.5, color=MUTE, ha="left", va="center")

ax.plot([0.07, 0.93], [0.062, 0.062], color=LINE, lw=1.2)
ax.text(0.07, 0.038, "TieOutBench  ·  evals.finance", fontsize=12.5, color=MUTE, ha="left", va="center")
ax.text(0.93, 0.038, "every number in the article has a dated source", fontsize=12.5, color=MUTE, ha="right", va="center")

out = os.path.join(HERE, "post-positive-case.png")
fig.savefig(out, dpi=100, facecolor=BG)
print("wrote", out)

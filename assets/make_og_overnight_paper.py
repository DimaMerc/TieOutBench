#!/usr/bin/env python3
"""
assets/make_og_overnight_paper.py -- the Open Graph preview image (1200x630) for https://evals.finance/overnight-paper,
the landing page of the fourth technical report ("After the Close"). LinkedIn's Featured and link cards take their
thumbnail from this image. Ledger-paper palette, the same family as the earlier report cards. Every number is read
from the published result files under prototypes/overnight/data/public/ and asserted; nothing is typed in.
Run: python assets/make_og_overnight_paper.py   (writes assets/og-overnight-paper.png and docs/og-overnight-paper.png)
"""
import json
import os
import shutil
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
BG, INK, MUTE, LINE = "#F3EDE2", "#1C1A17", "#6E675C", "#D6CDBD"
BLUE, TRACK = "#1E3F66", "#E8E0D2"
SERIF = "DejaVu Serif"

# ---------------- the published results ----------------
PUB = os.path.join(REPO, "prototypes", "overnight", "data", "public")
g = json.load(open(os.path.join(PUB, "grades.json"), encoding="utf-8"))
fr = json.load(open(os.path.join(PUB, "frankfurt.json"), encoding="utf-8"))
assert len(g) == 10, sorted(g)
facts = g["SPY"]["input_facts"]
assert facts["test_from"] == "2026-08-13" and facts["test_to_morning"] == "2026-11-06", facts
share = {t: 100.0 * s["overnight_prints"]["traded_bars"] / s["overnight_prints"]["session_slots"] for t, s in g.items()}
assert all(s["overnight_prints"]["session_slots"] == 5760 for s in g.values())      # 60 nights of 96 five-minute windows
often = [t for t, v in share.items() if v > 80]
assert len(often) == 6 and max(v for t, v in share.items() if t not in often) < 20, {t: round(v, 1) for t, v in share.items()}
spy_med = g["SPY"]["overnight_prints"]["same_instant"]["median_abs_bps"]
assert f"{spy_med:.1f}" == "2.4", spy_med                # the file keeps more digits than the image shows
de = g["EWG"]["overnight_prints"]
one_in = de["session_slots"] / de["traded_bars"]
assert de["traded_bars"] == 28 and 190 <= one_in <= 215, (de["traded_bars"], one_in)   # "one slot in two hundred"
fr_med = [v["analysis"]["median_abs_bps"] for v in fr.values()]
assert len(fr_med) == 9 and 1.5 <= min(fr_med) and max(fr_med) < 6.5 and round(min(fr_med)) == 2 and round(max(fr_med)) == 6, fr_med

fig = plt.figure(figsize=(12.0, 6.3), dpi=100)
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, 1)
ax.set_ylim(0, 1)
ax.axis("off")
ax.add_patch(Rectangle((0, 0), 1, 1, color=BG, zorder=0))

# title block (left)
ax.add_patch(Rectangle((0.06, 0.885), 0.05, 0.012, color=INK, zorder=2))
ax.text(0.06, 0.78, "After the close:", fontsize=46, color=INK, weight="bold", ha="left", va="center", family=SERIF)
ax.text(0.06, 0.655, "what is an ETF worth?", fontsize=46, color=BLUE, weight="bold", ha="left", va="center", family=SERIF)
ax.text(0.06, 0.545, "Sixty nights of overnight trading in ten US ETFs, measured before the", fontsize=15.5, color=MUTE, ha="left", va="center")
ax.text(0.06, 0.492, "exchanges open at night, with a Frankfurt control. Technical report, November 2026.", fontsize=15.5, color=MUTE, ha="left", va="center")

# the four figures: the number in ink, the colour on the tile's rule
ax.text(0.06, 0.418, "TEN US ETFS, SIXTY NIGHTS, AUGUST 13 TO NOVEMBER 6, 2026", fontsize=11.5, color=MUTE, weight="bold", ha="left", va="center")
TILES = [(f"{len(often)} of {len(g)}", ("funds traded", "nearly all night"), BLUE),
         (f"{spy_med:.1f} bps", ("S&P 500 fund, median", "distance from its value"), BLUE),
         ("1 in 200", ("five-minute windows traded,", "German stocks fund"), INK),
         (f"{round(min(fr_med))} to {round(max(fr_med))} bps", ("nine Frankfurt funds,", "median distance from value"), INK)]
x0, w, gap = 0.06, 0.205, 0.02
for i, (num, label, col) in enumerate(TILES):
    x = x0 + i * (w + gap)
    ax.add_patch(Rectangle((x, 0.175), w, 0.19, facecolor=TRACK, edgecolor="none", zorder=1))
    ax.add_patch(Rectangle((x, 0.175), w, 0.006, facecolor=col, edgecolor="none", zorder=2))
    ax.text(x + 0.016, 0.312, num, fontsize=25, color=INK, weight="bold", ha="left", va="center")
    for k, ln in enumerate(label):
        ax.text(x + 0.016, 0.250 - k * 0.036, ln, fontsize=11, color=INK, ha="left", va="center")

ax.plot([0.06, 0.94], [0.078, 0.078], color=LINE, lw=1.2)
ax.text(0.06, 0.042, "TieOutBench  ·  evals.finance", fontsize=12, color=MUTE, ha="left", va="center")
ax.text(0.94, 0.042, "SSRN 7688088  ·  real market data  ·  every table checked against the published files", fontsize=12, color=MUTE, ha="right", va="center")

out = os.path.join(HERE, "og-overnight-paper.png")
fig.savefig(out, dpi=100, facecolor=BG)
shutil.copyfile(out, os.path.join(REPO, "docs", "og-overnight-paper.png"))
print("wrote", out, "and docs/og-overnight-paper.png",
      dict(often=sorted(often), spy_median_bps=spy_med, germany_one_in=round(one_in), frankfurt=(min(fr_med), max(fr_med))))

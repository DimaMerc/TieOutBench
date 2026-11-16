#!/usr/bin/env python3
"""
assets/make_card_overnight.py -- PORTRAIT image (1080x1350, 4:5) for the overnight-ETF driver post
(content/linkedin-post-overnight-paste.txt): how often ten US ETFs traded at night, as the share of
five-minute windows with a trade over sixty nights. Ledger-paper palette (cream, ink, ink blue, grey).
Nothing typed in: every number is read from prototypes/overnight/data/public/grades.json and asserted.
Run: python assets/make_card_overnight.py      (the tieoutbench environment has matplotlib)
"""
import json
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyBboxPatch

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
BG, INK, MUTE, LINE = "#F3EDE2", "#1C1A17", "#6E675C", "#D6CDBD"
BLUE, RULE, TRACK = "#1E3F66", "#E6DECF", "#E8E0D2"
SERIF = "DejaVu Serif"

# ---------------- the data ----------------
g = json.load(open(os.path.join(REPO, "prototypes", "overnight", "data", "public", "grades.json"), encoding="utf-8"))
LABEL = {"SPY": "S&P 500", "QQQ": "Nasdaq 100", "GLD": "Gold", "IBIT": "Bitcoin", "SMH": "Semiconductor stocks",
         "TLT": "Long Treasuries", "EWJ": "Japanese stocks", "EEM": "Emerging-market stocks",
         "LQD": "Investment-grade bonds", "EWG": "German stocks"}
assert set(g) == set(LABEL), sorted(g)
rows = []
for t, s in g.items():
    p = s["overnight_prints"]
    assert p["session_slots"] == 5760, (t, p["session_slots"])            # 60 nights of 96 five-minute windows
    rows.append({"t": t, "label": LABEL[t], "traded": p["traded_bars"], "slots": p["session_slots"],
                 "share": 100.0 * p["traded_bars"] / p["session_slots"], "nights": p["nights_with_a_trade"],
                 "shares_traded": p["total_volume"]})
rows.sort(key=lambda r: -r["share"])
facts = g["SPY"]["input_facts"]
assert facts["test_from"] == "2026-08-13" and facts["test_to_morning"] == "2026-11-06", facts
often = [r for r in rows if r["share"] >= 50]
rarely = [r for r in rows if r["share"] < 50]
assert len(often) == 6 and len(rarely) == 4 and min(r["share"] for r in often) > 80 and max(r["share"] for r in rarely) < 20, \
    [(r["t"], round(r["share"], 1)) for r in rows]
de = next(r for r in rows if r["t"] == "EWG")
assert de is rows[-1] and de["traded"] == 28 and de["nights"] == 18 and int(de["shares_traded"]) == 2303, de

fig = plt.figure(figsize=(10.8, 13.5), dpi=100)
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, 1)
ax.set_ylim(0, 1)
ax.axis("off")
ax.add_patch(Rectangle((0, 0), 1, 1, color=BG, zorder=0))

# ---------------- title + intro ----------------
ax.add_patch(Rectangle((0.07, 0.955), 0.06, 0.006, color=INK, zorder=2))
ax.text(0.07, 0.912, "Six of ten ETFs traded all night.", fontsize=31, color=INK, weight="bold", ha="left", va="center", family=SERIF)
ax.text(0.07, 0.868, "Four traded far less.", fontsize=31, color=BLUE, weight="bold", ha="left", va="center", family=SERIF)
INTRO = ["From December 6, US exchanges are due to trade ETFs 23 hours a day. This is how often",
         "ten funds traded at night on today's main overnight venue: the share of five-minute",
         "windows, 8pm to 4am New York time, in which shares changed hands.",
         "Sixty nights, August 13 to November 6, 2026."]
for k, ln in enumerate(INTRO):
    ax.text(0.07, 0.826 - k * 0.0255, ln, fontsize=13.6, color=MUTE, ha="left", va="center")

# ---------------- the chart: one bar per fund, value at the tip ----------------
yA = 0.700
ax.plot([0.07, 0.93], [yA + 0.018, yA + 0.018], color=INK, lw=1.2)
ax.text(0.07, yA - 0.004, "SHARE OF FIVE-MINUTE WINDOWS WITH A TRADE  (by what the fund holds)",
        fontsize=12, color=MUTE, weight="bold", ha="left", va="center")
X0, X1 = 0.335, 0.815                 # the track runs from 0% to 100%
BAR_H = 24 / 1350.0                   # 24 px thick
ROUND = 4 / 1080.0                    # 4 px rounded data-end
pitch = 0.0435
y = yA - 0.050
for i, r in enumerate(rows):
    if i == len(often):               # a little air and a rule between the six and the four
        ax.plot([0.07, 0.93], [y + pitch * 0.62, y + pitch * 0.62], color=LINE, lw=0.9)
        y -= pitch * 0.24
    w = (X1 - X0) * r["share"] / 100.0
    ax.text(0.07, y, r["label"], fontsize=15.2, color=INK, ha="left", va="center")
    ax.add_patch(Rectangle((X0, y - BAR_H / 2), X1 - X0, BAR_H, facecolor=TRACK, edgecolor="none", zorder=1))
    if w > 3 * ROUND:                 # rounded at the data end, square at the baseline
        ax.add_patch(FancyBboxPatch((X0, y - BAR_H / 2), w, BAR_H, boxstyle=f"round,pad=0,rounding_size={ROUND}",
                                    facecolor=BLUE, edgecolor="none", zorder=2, mutation_aspect=1080 / 1350.0))
        ax.add_patch(Rectangle((X0, y - BAR_H / 2), min(w, 2 * ROUND), BAR_H, facecolor=BLUE, edgecolor="none", zorder=2))
    else:
        ax.add_patch(Rectangle((X0, y - BAR_H / 2), max(w, 2.5 / 1080.0), BAR_H, facecolor=BLUE, edgecolor="none", zorder=2))
    # value at the tip; for the long bars, just past the end of the track so the label sits on one ground
    xv = (X1 if r["share"] >= 50 else X0 + w) + 0.012
    ax.text(xv, y, f"{r['share']:.1f}%", fontsize=15.2, color=INK, ha="left", va="center",
            family=SERIF, weight="bold")
    if r is de:
        ax.text(X0 + w + 0.095, y, f"{r['traded']} of {r['slots']:,} windows  ·  {int(r['shares_traded']):,} shares in sixty nights",
                fontsize=11.2, color=MUTE, ha="left", va="center")
    y -= pitch
ax.text(X0, y + 0.012, "0%", fontsize=10.5, color=MUTE, ha="center", va="center")
ax.text(X1, y + 0.012, "100%", fontsize=10.5, color=MUTE, ha="center", va="center")

# ---------------- what it means ----------------
yC = y - 0.040
ax.plot([0.07, 0.93], [yC + 0.022, yC + 0.022], color=INK, lw=1.2)
NOTE = ["None of this appears in the premium and discount history a fund publishes.",
        "That history is measured once a day, at the close."]
for k, ln in enumerate(NOTE):
    ax.text(0.07, yC - 0.008 - k * 0.030, ln, fontsize=15.0, color=INK if k == 0 else BLUE, ha="left", va="center",
            family=SERIF, weight="bold")
ax.text(0.07, yC - 0.076, "Venue: Blue Ocean ATS. A window counts as traded when its five-minute bar shows volume.",
        fontsize=11.6, color=MUTE, ha="left", va="center")

# ---------------- footer ----------------
ax.plot([0.07, 0.93], [0.062, 0.062], color=LINE, lw=1.2)
ax.text(0.07, 0.040, "TieOutBench  ·  evals.finance", fontsize=12.5, color=MUTE, ha="left", va="center")
ax.text(0.93, 0.040, "real market data  ·  one venue  ·  sixty nights", fontsize=11.5, color=MUTE, ha="right", va="center")

out = os.path.join(HERE, "post-overnight-windows.png")
fig.savefig(out, dpi=100, facecolor=BG)
print("wrote", out, [(r["t"], round(r["share"], 1)) for r in rows], dict(germany=(de["traded"], de["nights"], int(de["shares_traded"]))))

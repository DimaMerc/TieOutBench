#!/usr/bin/env python3
"""
assets/make_og_options_paper.py -- the Open Graph preview image (1200x630) for https://evals.finance/options-paper,
the landing page of the third technical report ("Settle Only If Every Leg Ties"). LinkedIn's Featured and link cards
take their thumbnail from this image. Ledger-paper palette, no green. Every number is read from the sixteen run
records under outputs/eval8-live/ and asserted; nothing is typed in.
Run: python assets/make_og_options_paper.py   (writes assets/og-options-paper.png and docs/og-options-paper.png)
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
BLUE, OXBLOOD, TRACK = "#1E3F66", "#8B2E2E", "#E8E0D2"
SERIF = "DejaVu Serif"

# ---------------- the runs ----------------
MODELS = ["claude-opus-4-8", "claude-sonnet-4-6", "claude-haiku-4-5-20251001", "gpt-5.6-sol", "gpt-5.5",
          "gpt-5.4", "gpt-5.4-mini", "gemini-3.6-flash"]
BREAK, CLEAN = "grbo-redeem-2026", "grbo-redeem-2026-clean"
LIVE = os.path.join(REPO, "outputs", "eval8-live")
R = {}
for m in MODELS:
    for c in (BREAK, CLEAN):
        rj = json.load(open(os.path.join(LIVE, m, c, "run.json"), encoding="utf-8"))
        a = json.load(open(os.path.join(LIVE, m, c, "answer.json"), encoding="utf-8"))
        R[(m, c)] = {"allpass": rj["score"]["allpass"], "gates": rj["score"]["gates"],
                     "decision": str((a.get("D1") or {}).get("decision", "")).upper()}
n_models = len(MODELS)
n_runs = len(R)
held = sum(R[(m, BREAK)]["decision"].startswith("HOLD") for m in MODELS)
settled = sum(R[(m, CLEAN)]["decision"].startswith("SETTLE") for m in MODELS)
n_allpass = sum(r["allpass"] for r in R.values())
perfect_both = [m for m in MODELS if R[(m, BREAK)]["allpass"] and R[(m, CLEAN)]["allpass"]]
assert not any("GATE.SETTLE" in r["gates"] for r in R.values())
assert (n_models, n_runs, held, settled, n_allpass, len(perfect_both)) == (8, 16, 8, 8, 9, 3), \
    (n_models, n_runs, held, settled, n_allpass, perfect_both)

fig = plt.figure(figsize=(12.0, 6.3), dpi=100)
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
ax.add_patch(Rectangle((0, 0), 1, 1, color=BG, zorder=0))

# title block (left two thirds)
ax.add_patch(Rectangle((0.06, 0.885), 0.05, 0.012, color=INK, zorder=2))
ax.text(0.06, 0.78, "Settle only if", fontsize=46, color=INK, weight="bold", ha="left", va="center", family=SERIF)
ax.text(0.06, 0.655, "every leg ties.", fontsize=46, color=BLUE, weight="bold", ha="left", va="center", family=SERIF)
ax.text(0.06, 0.545, "A runnable evaluation of language models on an options-component", fontsize=15.5, color=MUTE, ha="left", va="center")
ax.text(0.06, 0.492, "ETF redemption. Technical report, October 2026.", fontsize=15.5, color=MUTE, ha="left", va="center")

# upper right: the one-line finding, in the space beside the title
ax.text(0.94, 0.80, "Every model held the broken order", fontsize=13.5, color=INK, ha="right", va="center")
ax.text(0.94, 0.755, "and settled the clean one. The losses", fontsize=13.5, color=INK, ha="right", va="center")
ax.text(0.94, 0.71, "were arithmetic one layer down.", fontsize=13.5, color=INK, ha="right", va="center")

# the four numbers (lower half): hero figures, text in ink tokens, the number carries the colour
ax.text(0.06, 0.418, f"EIGHT MODELS, THREE VENDORS, ONE RUN PER MODEL PER CASE", fontsize=11.5, color=MUTE, weight="bold", ha="left", va="center")
TILES = [(f"{held} of {n_models}", "held the broken order", BLUE),
         (f"{settled} of {n_models}", "settled the clean twin", BLUE),
         (f"{n_allpass} of {n_runs}", "runs passed every check", INK),
         (f"{len(perfect_both)} of {n_models}", "models perfect on both", INK)]
x0, w, gap = 0.06, 0.205, 0.02
for i, (num, label, col) in enumerate(TILES):
    x = x0 + i * (w + gap)
    ax.add_patch(Rectangle((x, 0.175), w, 0.19, facecolor=TRACK, edgecolor="none", zorder=1))
    ax.add_patch(Rectangle((x, 0.175), w, 0.006, facecolor=col, edgecolor="none", zorder=2))
    ax.text(x + 0.016, 0.305, num, fontsize=30, color=col, weight="bold", ha="left", va="center", family=SERIF)
    ax.text(x + 0.016, 0.228, label, fontsize=12, color=INK, ha="left", va="center")

ax.plot([0.06, 0.94], [0.078, 0.078], color=LINE, lw=1.2)
ax.text(0.06, 0.042, "TieOutBench  ·  evals.finance", fontsize=12, color=MUTE, ha="left", va="center")
ax.text(0.94, 0.042, "SSRN 7655899  ·  constructed case, real option terms  ·  every run published", fontsize=12, color=MUTE, ha="right", va="center")

out = os.path.join(HERE, "og-options-paper.png")
fig.savefig(out, dpi=100, facecolor=BG)
shutil.copyfile(out, os.path.join(REPO, "docs", "og-options-paper.png"))
print("wrote", out, "and docs/og-options-paper.png",
      dict(held=held, settled=settled, allpass=n_allpass, perfect_both=perfect_both))

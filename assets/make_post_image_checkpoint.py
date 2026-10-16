#!/usr/bin/env python3
"""
assets/make_post_image_checkpoint.py -- PORTRAIT image (1080x1350, 4:5) for the feed post "the approval
checkpoint" (content/linkedin-post-approval-checkpoints.txt), which announces the checker paper.
Top: the three arms as bars (runs that passed every check, of 48: tools / same-model checker / stronger
checker), read from outputs/eval6-agent/summary.json. Below: the three things the checkpoint has to show,
each with its one-line evidence. Ledger-paper palette: cream, ink, oxblood, ink blue, grey; no green.
Nothing typed in: every number is read from summary.json and asserted.
Run: python assets/make_post_image_checkpoint.py
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
BLUE, OXBLOOD, GREY, RULE, TRACK = "#1E3F66", "#8B2E2E", "#9A938A", "#E6DECF", "#E8E0D2"
SERIF = "DejaVu Serif"

with open(os.path.join(REPO, "outputs", "eval6-agent", "summary.json"), encoding="utf-8") as fh:
    S = json.load(fh)
C = S["counts"]
N = C["tools"]["n"]
ARMS = [("With tools, no reviewer", C["tools"]["allpass"], BLUE),
        ("A second AI of the same model as checker", C["checker"]["allpass"], OXBLOOD),
        ("A stronger AI as checker", C["checker-fixed"]["allpass"], OXBLOOD)]
T = S["two_by_two"]["checker"]
rejected_correct = T["counts"]["reject_correct"]
correct_shown = T["counts"]["reject_correct"] + T["counts"]["approve_correct"]
revisions = len(T["revised"])
rejections = T["counts"]["reject_correct"] + T["counts"]["reject_wrong"]


def gates_of(cell):
    g = cell.get("gates")
    if g is None and isinstance(cell.get("terminal"), dict):
        g = cell["terminal"].get("gates")
    return g or []


# the ten over-rules are the cells whose fabrication gate is NEW under the fixed reviewer: present in that arm,
# absent in the tools arm for the same cell (two small-model worksheets carried the gate before any review)
overruled = sum(1 for key, cell in S["checker-fixed"].items()
                if any("FABRICATION" in g for g in gates_of(cell))
                and not any("FABRICATION" in g for g in gates_of(S["tools"].get(key, {}))))
assert (N, ARMS[0][1], ARMS[1][1], ARMS[2][1]) == (48, 35, 27, 25), (N, ARMS)
assert (rejected_correct, correct_shown, revisions, rejections) == (20, 46, 21, 21)
assert overruled == 10, overruled

fig = plt.figure(figsize=(10.8, 13.5), dpi=100)
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
ax.add_patch(Rectangle((0, 0), 1, 1, color=BG, zorder=0))

# ---------------- title ----------------
ax.add_patch(Rectangle((0.07, 0.945), 0.06, 0.006, color=INK, zorder=2))
ax.text(0.07, 0.897, "What the approval checkpoint", fontsize=33, color=INK, weight="bold", ha="left", va="center", family=SERIF)
ax.text(0.07, 0.849, "has to show.", fontsize=33, color=BLUE, weight="bold", ha="left", va="center", family=SERIF)
INTRO = ["An approval checkpoint is the step where a reviewer approves or rejects an AI's work",
         "before it reaches production. I gave eight AI models six corporate-action cases, with",
         f"tools to look things up and book, and then put a second AI in the reviewer's seat. {N} runs per arm."]
for k, ln in enumerate(INTRO):
    ax.text(0.07, 0.803 - k * 0.028, ln, fontsize=13.5, color=MUTE, ha="left", va="center")

# ---------------- the arms ----------------
ax.text(0.07, 0.700, f"RUNS THAT PASSED EVERY CHECK, OF {N}", fontsize=11.5, color=MUTE, weight="bold", ha="left", va="center")
X0, W = 0.07, 0.70
y = 0.662
for label, n, color in ARMS:
    ax.text(X0, y + 0.024, label, fontsize=14, color=INK, ha="left", va="center")
    ax.add_patch(FancyBboxPatch((X0, y - 0.011), W, 0.022, boxstyle="round,pad=0,rounding_size=0.008", facecolor=TRACK, edgecolor="none", zorder=1))
    ax.add_patch(FancyBboxPatch((X0, y - 0.011), W * n / N, 0.022, boxstyle="round,pad=0,rounding_size=0.008", facecolor=color, edgecolor="none", zorder=2))
    ax.text(X0 + W + 0.02, y, f"{n}", fontsize=22, color=color, weight="bold", ha="left", va="center", family=SERIF)
    y -= 0.064
ax.text(0.07, y + 0.022, f"The reviewers rejected {rejected_correct} of the {correct_shown} ledgers the grader scores correct; "
        f"the makers revised in all {revisions} rejections.", fontsize=12, color=MUTE, ha="left", va="center")

# ---------------- the three things ----------------
ax.plot([0.07, 0.93], [y - 0.012, y - 0.012], color=INK, lw=1.2)
ROWS = [
    ("1", "The result tying back to the source, not the steps.",
     "Every reviewer showed its steps. The wrong ones showed them just as clearly."),
    ("2", "The rules the maker works to.",
     f"The reviewer had the documents, not the rule that a named refusal is correct. The stronger one over-ruled {overruled} refusals into invented numbers."),
    ("3", "A way for the maker to answer a finding.",
     "Every rejection produced a revision, including the wrong ones. Compliance was the failure mode."),
]
y -= 0.070
for num, head, body in ROWS:
    ax.text(0.07, y + 0.012, num, fontsize=46, color=OXBLOOD, weight="bold", ha="left", va="center", family=SERIF)
    ax.text(0.145, y + 0.03, head, fontsize=17.5, color=INK, weight="bold", ha="left", va="center")
    # wrap body by hand at ~82 characters
    words, lines_out, cur = body.split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > 84:
            lines_out.append(cur); cur = w
        else:
            cur = (cur + " " + w).strip()
    lines_out.append(cur)
    for k, ln in enumerate(lines_out):
        ax.text(0.145, y - 0.006 - k * 0.028, ln, fontsize=13.5, color=MUTE, ha="left", va="center")
    y -= 0.108 + 0.028 * (len(lines_out) - 1)
    if num != ROWS[-1][0]:
        ax.plot([0.145, 0.93], [y + 0.056, y + 0.056], color=RULE, lw=1.0)

ax.plot([0.07, 0.93], [0.062, 0.062], color=LINE, lw=1.2)
ax.text(0.07, 0.038, "TieOutBench  ·  evals.finance", fontsize=12.5, color=MUTE, ha="left", va="center")
ax.text(0.93, 0.038, "every verdict and finding published, one run per model per case", fontsize=12.5, color=MUTE, ha="right", va="center")

out = os.path.join(HERE, "post-approval-checkpoints.png")
fig.savefig(out, dpi=100, facecolor=BG)
print("wrote", out, dict(n=N, arms=[a[1] for a in ARMS], rejected_correct=rejected_correct, of=correct_shown, revisions=revisions, overruled=overruled))

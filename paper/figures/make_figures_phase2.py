#!/usr/bin/env python3
"""
paper/figures/make_figures_phase2.py -- eval #6 Phase-2 figures (F8-F10), white/navy brand.

Every number is read from outputs/eval6-agent/summary.json (regenerate it first with
`python outputs/eval6-agent/summarize.py --json`); nothing is typed in. Same color system as
make_figures.py (validated with the dataviz palette checker): ink navy #16243B for text and
structure only, data blue #2a78d6 for the one data series, critical red #d03b3b for gates and
false verdicts, light washes for cell backgrounds. No categorical palette is needed: every panel
carries one series, so identity never rests on hue.

  F8  the four arms: clean runs of 48, and gates fired, one bar per arm
  F9  the reviewer two-by-two, same-model reviewer beside the fixed reviewer
  F10 clean cases per model (of 6) by arm, small multiples, gate counts as text

Run: python paper/figures/make_figures_phase2.py
"""
import json
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
SUMMARY = os.path.join(REPO, "outputs", "eval6-agent", "summary.json")

BG, NAVY, MUTE, LINE = "#FFFFFF", "#16243B", "#6B7785", "#C9D3DE"
BLUE, RED = "#2a78d6", "#d03b3b"
REDBG, BLUEBG = "#FBECEA", "#EAF1FB"
plt.rcParams.update({"font.family": "DejaVu Sans", "text.color": NAVY, "axes.edgecolor": LINE,
                     "axes.labelcolor": NAVY, "xtick.color": MUTE, "ytick.color": MUTE,
                     "figure.facecolor": BG, "axes.facecolor": BG, "savefig.facecolor": BG})

ARMS = [("plain", "Plain\n(store in the prompt)"), ("tools", "Tools"),
        ("checker", "Checker\n(same model reviews)"), ("checker-fixed", "Checker, fixed\n(Opus 4.8 reviews all)")]
MODELS = [("claude-opus-4-8", "Claude Opus 4.8"), ("claude-sonnet-4-6", "Claude Sonnet 4.6"),
          ("claude-haiku-4-5-20251001", "Claude Haiku 4.5"), ("gpt-5.6-sol", "GPT-5.6-sol"),
          ("gpt-5.5", "GPT-5.5"), ("gpt-5.4", "GPT-5.4"), ("gpt-5.4-mini", "GPT-5.4-mini"),
          ("gemini-3.6-flash", "Gemini 3.6 Flash")]


def load():
    with open(SUMMARY, encoding="utf-8") as fh:
        return json.load(fh)


def cell(s, arm):
    """(allpass, gates fired) for one cell in one arm."""
    if arm == "plain":
        return int(s["allpass"]), bool(s["gates"])
    return int(s["terminal"]["allpass"]), bool(s["terminal"]["gates"])


def arm_totals(S, arm):
    cells = S[arm]
    ap = sum(cell(v, arm)[0] for v in cells.values())
    gates = sum(cell(v, arm)[1] for v in cells.values())
    return ap, gates, len(cells)


def model_totals(S, arm, model):
    cells = {k: v for k, v in S[arm].items() if k.startswith(model + "/")}
    return sum(cell(v, arm)[0] for v in cells.values()), sum(cell(v, arm)[1] for v in cells.values()), len(cells)


def save(fig, name):
    for ext in ("png", "pdf"):
        fig.savefig(os.path.join(HERE, f"{name}.{ext}"), dpi=200 if ext == "png" else None, bbox_inches="tight")
    plt.close(fig)
    print("wrote", name)


# ----------------------------------------------------------------------------
# F8 -- the four arms
# ----------------------------------------------------------------------------
def f8_arms(S):
    fig, axes = plt.subplots(1, 2, figsize=(9.6, 3.4), gridspec_kw={"wspace": 0.55})
    labels = [lab for _, lab in ARMS]
    y = list(range(len(ARMS)))[::-1]
    totals = [arm_totals(S, arm) for arm, _ in ARMS]
    n = totals[0][2]
    for ax, idx, color, title, xmax in ((axes[0], 0, BLUE, f"Clean runs (AllPass) of {n}", n),
                                        (axes[1], 1, RED, f"Cells with a gate fired, of {n}", 16)):
        vals = [t[idx] for t in totals]
        ax.barh(y, vals, height=0.56, color=color, edgecolor="none")
        for yi, v in zip(y, vals):
            ax.text(v + xmax * 0.012, yi, f"{v}", va="center", ha="left", fontsize=10, color=NAVY, weight="bold")
        ax.set_yticks(y)
        ax.set_yticklabels(labels, fontsize=8.6)
        ax.set_xlim(0, xmax * 1.12)
        ax.tick_params(axis="x", labelsize=8)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        ax.spines["left"].set_color(LINE)
        ax.grid(axis="x", color=LINE, lw=0.6, alpha=0.7)
        ax.set_axisbelow(True)
        ax.set_title(title, fontsize=10.5, color=NAVY, weight="bold", loc="left", pad=8)
    fig.suptitle("Eval #6, Phase 2: the same six cases and eight models, four ways", fontsize=12.5,
                 color=NAVY, weight="bold", x=0.02, ha="left", y=1.04)
    fig.text(0.02, -0.06, "One run per cell (48 per arm), 2026-09-24/25. AllPass = every criterion met, no gate, calibrated "
             "refusal perfect. Source: outputs/eval6-agent/summary.json.", fontsize=8.2, color=MUTE, ha="left")
    save(fig, "f8-phase2-arms")


# ----------------------------------------------------------------------------
# F9 -- the reviewer two-by-two, self-review beside the fixed reviewer
# ----------------------------------------------------------------------------
def f9_two_by_two(S):
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.6), gridspec_kw={"wspace": 0.35})
    panels = (("checker", "Same-model reviewer"), ("checker-fixed", "Fixed reviewer (Claude Opus 4.8)"))
    for ax, (arm, title) in zip(axes, panels):
        c = S["two_by_two"][arm]["counts"]
        grid = [[("reject", "wrong", c["reject_wrong"], "wrong ledger\nrejected", BLUEBG),
                 ("reject", "correct", c["reject_correct"], "correct ledger\nrejected", REDBG)],
                [("approve", "wrong", c["approve_wrong"], "wrong ledger\napproved", REDBG),
                 ("approve", "correct", c["approve_correct"], "correct ledger\napproved", BLUEBG)]]
        ax.set_xlim(0, 2)
        ax.set_ylim(0, 2)
        ax.set_aspect("equal")
        ax.axis("off")
        for i, row in enumerate(grid):
            for j, (v, l, cnt, word, wash) in enumerate(row):
                x, yy = j, 1 - i
                ax.add_patch(FancyBboxPatch((x + 0.04, yy + 0.04), 0.92, 0.92, boxstyle="round,pad=0,rounding_size=0.06",
                                            facecolor=wash, edgecolor=LINE, lw=0.8))
                ax.text(x + 0.5, yy + 0.63, f"{cnt}", ha="center", va="center", fontsize=22, weight="bold",
                        color=RED if wash == REDBG else NAVY)
                ax.text(x + 0.5, yy + 0.26, word, ha="center", va="center", fontsize=8.2, color=MUTE,
                        linespacing=1.25)
        ax.text(0.5, 2.08, "ledger wrong", ha="center", va="bottom", fontsize=9, color=NAVY)
        ax.text(1.5, 2.08, "ledger correct", ha="center", va="bottom", fontsize=9, color=NAVY)
        ax.text(-0.08, 1.5, "reject", ha="right", va="center", fontsize=9, color=NAVY, rotation=90)
        ax.text(-0.08, 0.5, "approve", ha="right", va="center", fontsize=9, color=NAVY, rotation=90)
        n = sum(c[k] for k in ("reject_wrong", "reject_correct", "approve_wrong", "approve_correct"))
        ax.set_title(f"{title}   (n = {n})", fontsize=10.5, color=NAVY, weight="bold", loc="left", pad=22)
    fig.suptitle("The reviewer's first-round verdict against the ledger it was shown", fontsize=12.5,
                 color=NAVY, weight="bold", x=0.02, ha="left", y=1.06)
    fig.text(0.02, -0.04, "A ledger is correct when it is booked, fires no gate, and ties to the worksheet and the gold. "
             "The grader does not score every field:\n7 of the 20 and 3 of the 13 rejections of correct ledgers raise a "
             "point the documents support (TAXONOMY.md, finding 12).\n"
             "Source: outputs/eval6-agent/summary.json (two_by_two).", fontsize=8.2, color=MUTE, ha="left", va="top",
             linespacing=1.35)
    save(fig, "f9-phase2-two-by-two")


# ----------------------------------------------------------------------------
# F10 -- clean cases per model by arm (small multiples)
# ----------------------------------------------------------------------------
def f10_per_model(S):
    fig, axes = plt.subplots(1, len(ARMS), figsize=(12.4, 3.7), sharey=True, gridspec_kw={"wspace": 0.16})
    y = list(range(len(MODELS)))[::-1]
    short = {"plain": "Plain", "tools": "Tools", "checker": "Checker, self-review", "checker-fixed": "Checker, fixed reviewer"}
    for ax, (arm, lab) in zip(axes, ARMS):
        rows = [model_totals(S, arm, m) for m, _ in MODELS]
        vals = [r[0] for r in rows]
        ax.barh(y, vals, height=0.58, color=BLUE, edgecolor="none")
        for yi, (ap, g, n) in zip(y, rows):
            ax.text(ap + 0.12, yi, f"{ap}", va="center", ha="left", fontsize=9, color=NAVY, weight="bold")
            if g:
                ax.text(7.05, yi, f"{g} gate{'s' if g > 1 else ''}", va="center", ha="left", fontsize=7.6, color=RED)
        ax.set_xlim(0, 9.2)
        ax.set_xticks([0, 2, 4, 6])
        ax.tick_params(axis="x", labelsize=8)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        ax.spines["left"].set_color(LINE)
        ax.grid(axis="x", color=LINE, lw=0.6, alpha=0.7)
        ax.set_axisbelow(True)
        ax.set_title(short[arm], fontsize=9.6, color=NAVY, weight="bold", loc="left", pad=6)
    axes[0].set_yticks(y)
    axes[0].set_yticklabels([lab for _, lab in MODELS], fontsize=8.6)
    fig.suptitle("Clean cases per model, of six, by arm", fontsize=12.5, color=NAVY, weight="bold",
                 x=0.02, ha="left", y=1.06)
    fig.text(0.02, -0.06, "Plain: the store in the prompt. Tools: discovery, position, calculator and action tools. Checker: "
             "the tools arm's work product reviewed by the maker's own model, or by Claude Opus 4.8 for every maker. "
             "Red text: cells in that arm where a gate fired. One run per cell. Source: outputs/eval6-agent/summary.json.",
             fontsize=8.0, color=MUTE, ha="left")
    save(fig, "f10-phase2-per-model")


if __name__ == "__main__":
    S = load()
    f8_arms(S)
    f9_two_by_two(S)
    f10_per_model(S)

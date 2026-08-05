#!/usr/bin/env python3
"""
paper/figures/make_figures.py -- all TieOutBench paper figures (F1-F7), white/navy brand.

Every number is real repo data; sources cited per figure below (LEADERBOARD.md, README.md,
outputs/eval3-live/*/report.txt). Outputs <fig>.png (200dpi, review) + <fig>.pdf (vector, paper).

Color system (validated with the dataviz palette checker, light surface):
  ink navy #16243B (text/structure only -- never a data series), muted #6B7785,
  hairline #C9D3DE, data blue #2a78d6, critical red #d03b3b, aqua #1baf7a,
  blue sequential ramp #cde2fb..#0d366b for the heatmap, ordinal blues for gate tiers.

Run: python paper/figures/make_figures.py
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.patches import FancyBboxPatch, Rectangle, FancyArrowPatch

HERE = os.path.dirname(os.path.abspath(__file__))

BG    = "#FFFFFF"
NAVY  = "#16243B"   # primary ink
MUTE  = "#6B7785"   # secondary ink
LINE  = "#C9D3DE"   # hairline / grid
BLUE  = "#2a78d6"   # data series 1
RED   = "#d03b3b"   # critical / gate fired
AQUA  = "#1baf7a"   # recovered / fair
REDBG = "#FBECEA"   # light red wash
BLUEBG= "#EAF1FB"   # light blue wash
MONO  = "DejaVu Sans Mono"

# blue sequential ramp (reference palette steps 100..700)
RAMP = ["#cde2fb", "#b7d3f6", "#9ec5f4", "#86b6ef", "#6da7ec", "#5598e7",
        "#3987e5", "#2a78d6", "#256abf", "#1c5cab", "#184f95", "#104281", "#0d366b"]
CMAP = mcolors.LinearSegmentedColormap.from_list("navyseq", RAMP)

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "text.color": NAVY,
    "axes.edgecolor": LINE,
    "axes.labelcolor": NAVY,
    "xtick.color": MUTE,
    "ytick.color": MUTE,
    "figure.facecolor": BG,
    "axes.facecolor": BG,
    "savefig.facecolor": BG,
})


def save(fig, name):
    for ext in ("png", "pdf"):
        fig.savefig(os.path.join(HERE, f"{name}.{ext}"),
                    dpi=200 if ext == "png" else None, bbox_inches="tight")
    plt.close(fig)
    print("wrote", name)


def caption(ax, x, y, text, size=8.5):
    ax.text(x, y, text, transform=ax.figure.transFigure, fontsize=size,
            color=MUTE, ha="left", va="top")


# ----------------------------------------------------------------------------
# F1 -- coverage-gap map. Source: README "Where this sits in the 2026 benchmark
# landscape" (all links curl-verified there).
# ----------------------------------------------------------------------------
def f1_coverage():
    cols = ["Research &\nanalysis QA", "Valuation &\nmodel-building",
            "Bookkeeping /\naccounting", "Securities\npost-trade ops"]
    rows = [  # (label, builder-year, marks per column: 2=core focus, 1=covered, 0=no)
        ("GDPval",              "OpenAI · 2025",           [2, 0, 0, 0]),
        ("Finance Agent v2",    "Vals AI · 2026",          [2, 0, 0, 0]),
        ("APEX / APEX-Agents",  "Mercor · 2025–26",        [1, 2, 0, 0]),
        ("BigFinanceBench",     "Rogo + OpenAI · 2026",    [2, 0, 0, 0]),
        ("FrontierFinance",     "Kensho/S&P/MIT · 2026",   [0, 2, 0, 0]),
        ("FinBalance",          "academic · 2026",         [0, 0, 2, 0]),
        ("TieOutBench",         "this work · 2025–26",     [2, 2, 0, 2]),
    ]
    nr, nc = len(rows), len(cols)
    SP = 1.9  # horizontal spread so headers don't collide
    X = [j * SP for j in range(nc)]
    fig, ax = plt.subplots(figsize=(7.6, 3.9))
    ax.set_xlim(-4.6, X[-1] + 0.95); ax.set_ylim(-0.95, nr); ax.axis("off")
    ax.invert_yaxis()

    # highlight the empty post-trade column
    ax.add_patch(Rectangle((X[-1] - 0.85, -0.90), 1.70, nr + 0.28,
                           facecolor=BLUEBG, edgecolor="none", zorder=0))
    for j, c in enumerate(cols):
        ax.text(X[j], -0.52, c, ha="center", va="bottom", fontsize=8.5,
                color=NAVY, weight="bold")
    for i, (name, who, marks) in enumerate(rows):
        this = (name == "TieOutBench")
        if this:
            ax.add_patch(Rectangle((-4.55, i - 0.42), 4.55 + X[-1] + 0.85, 0.84,
                                   facecolor="#F4F7FB", edgecolor=LINE, lw=0.8, zorder=1))
        ax.text(-4.5, i - 0.09, name, ha="left", va="center", fontsize=10,
                color=NAVY, weight="bold" if this else "normal")
        ax.text(-4.5, i + 0.24, who, ha="left", va="center", fontsize=7.5, color=MUTE)
        for j, m in enumerate(marks):
            if m == 2:
                ax.scatter([X[j]], [i], s=210, color=BLUE, zorder=3,
                           edgecolor=NAVY if this and j == nc - 1 else "none", linewidth=1.4)
            elif m == 1:
                ax.scatter([X[j]], [i], s=210, facecolor="none", edgecolor=BLUE,
                           linewidth=1.6, zorder=3)
            else:
                ax.scatter([X[j]], [i], s=26, color=LINE, zorder=2)
    # legend
    ax.scatter([-4.4], [nr - 0.25], s=110, color=BLUE); ax.text(-4.2, nr - 0.25, "core focus", fontsize=8, color=MUTE, va="center")
    ax.scatter([-2.9], [nr - 0.25], s=110, facecolor="none", edgecolor=BLUE, linewidth=1.5); ax.text(-2.7, nr - 0.25, "covered", fontsize=8, color=MUTE, va="center")
    ax.scatter([-1.5], [nr - 0.25], s=22, color=LINE); ax.text(-1.32, nr - 0.25, "not covered", fontsize=8, color=MUTE, va="center")
    ax.set_title("Every prominent 2026 finance benchmark tests the front office",
                 fontsize=12.5, color=NAVY, weight="bold", loc="left", pad=14)
    save(fig, "f1-coverage-gap")


# ----------------------------------------------------------------------------
# F2 -- the hook: ungated vs gated on one misread header.
# Source: `python -m harness demo` (snow-2026q2, scale_slip).
# ----------------------------------------------------------------------------
def f2_demo():
    fig, ax = plt.subplots(figsize=(5.6, 2.9))
    vals = [0.951, 0.452]
    labels = ["naive average\n(ungated)", "rubric with gates\n(gated)"]
    colors = [BLUE, RED]
    y = [0.62, 0.0]
    for yi, v, c, lab in zip(y, vals, colors, labels):
        ax.barh([yi], [v], height=0.42, color=c, zorder=3)
        ax.text(v + 0.012, yi, f"{v:.3f}", va="center", ha="left", fontsize=13,
                color=c, weight="bold", family=MONO)
        ax.text(-0.015, yi, lab, va="center", ha="right", fontsize=9.5, color=NAVY)
    ax.text(0.60, 0.0, "← GATE.P2: \"in thousands\"\n    read as \"in millions\"",
            fontsize=8.5, color=RED, va="center", ha="left")
    ax.set_xlim(0, 1.10); ax.set_ylim(-0.38, 1.05)
    ax.set_yticks([]); ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.xaxis.set_major_formatter(lambda v, _: f"{v:.2f}")
    ax.tick_params(labelsize=8, length=0)
    ax.grid(axis="x", color=LINE, lw=0.6, zorder=0)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.set_title("One answer, two scores: the same internally-consistent analysis,\nwith and without the scale gate",
                 fontsize=11.5, color=NAVY, weight="bold", loc="left", pad=10)
    save(fig, "f2-demo-gap")


# ----------------------------------------------------------------------------
# F3 -- grading architecture: checkpoints -> atom tiers -> gate blast radius.
# Source: rubric/rubric*.md design docs.
# ----------------------------------------------------------------------------
def f3_architecture():
    fig = plt.figure(figsize=(7.2, 4.1))
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")

    ax.text(0.03, 0.945, "How a TieOutBench score is produced",
            fontsize=13, color=NAVY, weight="bold")

    # --- row 1: checkpoint pipeline
    ax.text(0.03, 0.845, "1 · WORKFLOW → CHECKPOINTS", fontsize=8.5, color=MUTE, weight="bold")
    stages = ["Plan", "Extract", "Calculate", "Decide"]
    xw, xg, x0, yc, h = 0.150, 0.042, 0.03, 0.735, 0.085
    for k, s in enumerate(stages):
        x = x0 + k * (xw + xg)
        ax.add_patch(FancyBboxPatch((x, yc), xw, h, boxstyle="round,pad=0.006,rounding_size=0.012",
                                    facecolor=BLUEBG, edgecolor=BLUE, lw=1.1))
        ax.text(x + xw / 2, yc + h / 2, s, ha="center", va="center", fontsize=10, color=NAVY, weight="bold")
        if k < 3:
            ax.annotate("", xy=(x + xw + xg - 0.006, yc + h / 2), xytext=(x + xw + 0.006, yc + h / 2),
                        arrowprops=dict(arrowstyle="->", color=MUTE, lw=1.1))
    ax.text(x0 + 4 * xw + 3 * xg + 0.015, yc + h / 2,
            "each checkpoint owns: inputs · gold answer\nwith evidence citation · success criteria",
            fontsize=8, color=MUTE, va="center")

    # --- row 2: atom tiers
    ax.text(0.03, 0.63, "2 · CHECKPOINT → POINT-WEIGHTED ATOMS", fontsize=8.5, color=MUTE, weight="bold")
    tiers = [("deterministic", "exact / tolerance\nrecompute", 0.42),
             ("entailment", "evidence supports\nthe claim", 0.20),
             ("LLM-judge", "synthesis only\n(frozen prompt)", 0.22),
             ("refusal", "typed; twin\nblocks farming", 0.16)]
    x = 0.03; yt = 0.475; hh = 0.105
    for name, desc, w in tiers:
        ww = w * 0.72
        ax.add_patch(FancyBboxPatch((x, yt), ww, hh, boxstyle="round,pad=0.005,rounding_size=0.010",
                                    facecolor="#F4F7FB", edgecolor=LINE, lw=1.0))
        ax.text(x + ww / 2, yt + hh - 0.026, name, ha="center", fontsize=8.6, color=NAVY, weight="bold")
        ax.text(x + ww / 2, yt + 0.034, desc, ha="center", va="center", fontsize=6.7, color=MUTE)
        x += ww + 0.016
    ax.text(x + 0.004, yt + hh / 2, "width = share of criteria;\neverything deterministic is\ngraded deterministically",
            fontsize=7.5, color=MUTE, va="center")

    # --- row 3: gates
    ax.text(0.03, 0.365, "3 · GATES — AUTO-FAIL WITH CALIBRATED BLAST RADIUS", fontsize=8.5, color=MUTE, weight="bold")
    gates = [("HARD", "poisons the whole case\n(wrong vintage, scale, direction)", 0.97),
             ("SCOPED", "zeroes its category\n(fee basis, free lunch, bridge)", 0.60),
             ("IN-CHECKPOINT", "zeroes one checkpoint\n(sign flip, FCF ≠ own build)", 0.30)]
    x0g, yg, hg = 0.03, 0.075, 0.20
    for k, (name, desc, sev) in enumerate(gates):
        x = x0g + k * 0.245
        ax.add_patch(FancyBboxPatch((x, yg), 0.225, hg, boxstyle="round,pad=0.006,rounding_size=0.012",
                                    facecolor=REDBG, edgecolor=RED, lw=1.1, alpha=0.55 + 0.45 * sev))
        ax.text(x + 0.1125, yg + hg - 0.038, name, ha="center", fontsize=9, color=RED, weight="bold")
        ax.text(x + 0.1125, yg + 0.055, desc, ha="center", va="center", fontsize=7.2, color=NAVY)
    ax.text(0.775, yg + hg / 2,
            "score = gated headline;\nungated kept alongside —\nthe GAP is the finding",
            fontsize=8.6, color=NAVY, va="center", weight="bold")
    save(fig, "f3-architecture")


# ----------------------------------------------------------------------------
# F4 -- leaderboard heatmap, 8 models x 6 cases. Source: LEADERBOARD.md grid.
# ----------------------------------------------------------------------------
def f4_heatmap():
    models = ["Claude Opus 4.8", "Claude Sonnet 4.6", "Claude Haiku 4.5",
              "GPT-5.6-sol", "GPT-5.5", "GPT-5.4", "GPT-5.4-mini", "Gemini 3.6 Flash"]
    tiers  = ["flagship", "mid", "small", "flagship", "flagship (prev.)", "mid", "small", "small/fast"]
    cases  = ["#3 DCF\n(MCD)", "#3 DCF\n(NVDA)", "#4 recon\n(break)", "#4 recon\n(clean)",
              "#5 confirm\n(break)", "#5 confirm\n(clean)"]
    S = [
        [0.965, 0.974, 0.983, 0.983, 0.980, 0.980],
        [0.955, 0.973, 0.943, 0.983, 0.933, 0.980],
        [0.692, 0.799, 0.496, 0.983, 0.933, 0.980],
        [0.951, 0.970, 0.943, 0.973, 0.980, 0.980],
        [0.953, 0.970, 0.943, 0.983, 0.980, 0.980],
        [0.903, 0.883, 0.983, 0.973, 0.980, 0.980],
        [0.631, 0.650, 0.714, 0.983, 0.933, 0.980],
        [0.922, 0.970, 0.983, 0.973, 0.980, 0.980],
    ]
    gates = {(2, 0): "C1FCF", (2, 2): "SCALE", (6, 0): "FALSEPREC.", (6, 1): "BRIDGE"}
    fig, ax = plt.subplots(figsize=(8.0, 4.3))
    norm = mcolors.Normalize(vmin=0.40, vmax=1.00)
    NC = 6
    for i in range(8):
        for j in range(NC):
            v = S[i][j]
            c = CMAP(norm(v))
            ax.add_patch(Rectangle((j + 0.03, i + 0.03), 0.94, 0.94, facecolor=c, edgecolor=BG, lw=0))
            lum = mcolors.rgb_to_hsv(c[:3])[2]
            tc = "#FFFFFF" if lum < 0.72 else NAVY
            gated = (i, j) in gates
            ax.text(j + 0.5, i + (0.35 if gated else 0.5), f"{v:.3f}", ha="center", va="center",
                    fontsize=9.5, color=tc, family=MONO, weight="bold" if gated else "normal")
            if gated:
                ax.text(j + 0.5, i + 0.70, "▲ " + gates[(i, j)], ha="center", va="center",
                        fontsize=6.8, color="#FFD9D2" if lum < 0.72 else RED, weight="bold")
    ax.set_xlim(0, NC); ax.set_ylim(8, 0)
    ax.set_xticks([j + 0.5 for j in range(NC)]); ax.set_xticklabels(cases, fontsize=8.5, color=NAVY)
    ax.set_yticks([i + 0.5 for i in range(8)])
    ax.set_yticklabels([f"{m}   " for m in models], fontsize=9, color=NAVY)
    for i, t in enumerate(tiers):
        ax.text(NC + 0.08, i + 0.5, t, fontsize=7.5, color=MUTE, va="center")
    ax.tick_params(length=0)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_title("Gated scores — eight frontier models, three vendors, six gold cases\n"
                 "▲ = auto-fail gate fired (GATE.<name>); one run per model per case",
                 fontsize=11.5, color=NAVY, weight="bold", loc="left", pad=12)
    save(fig, "f4-leaderboard-heatmap")


# ----------------------------------------------------------------------------
# F5 -- starved vs fair: the token-accounting finding. Source: LEADERBOARD.md
# methodology table (GPT DCF runs @8k vs @32k completion budget).
# ----------------------------------------------------------------------------
def f5_starved_fair():
    rows = [  # model, starved, fair, note
        ("GPT-5.5",      0.000, 0.953, "empty completion"),
        ("GPT-5.6-sol",  0.322, 0.951, "six gates fired at once"),
        ("GPT-5.4",      0.618, 0.903, "false-precision gate cleared"),
        ("GPT-5.4-mini", 0.745, 0.631, "score FELL — its gate is genuine"),
    ]
    fig, ax = plt.subplots(figsize=(6.8, 3.1))
    for i, (m, a, b, note) in enumerate(rows):
        y = len(rows) - 1 - i
        up = b >= a
        ax.plot([a, b], [y, y], color=LINE, lw=2.2, zorder=2)
        ax.scatter([a], [y], s=64, color=RED, zorder=3)
        ax.scatter([b], [y], s=64, color=AQUA if up else NAVY, zorder=3)
        ax.text(-0.03, y, m, ha="right", va="center", fontsize=9.5, color=NAVY)
        ax.text(max(a, b) + 0.035, y, note, ha="left", va="center", fontsize=7.8, color=MUTE)
        lab_a = "empty" if a == 0 else f"{a:.3f}"
        ax.text(a, y - 0.32, lab_a, ha="center", fontsize=8, color=RED, family=MONO)
        ax.text(b, y + 0.36, f"{b:.3f}", ha="center", fontsize=8,
                color=AQUA if up else NAVY, family=MONO, weight="bold")
    ax.scatter([], [], s=54, color=RED, label="8k budget — thinking silently charged (starved)")
    ax.scatter([], [], s=54, color=AQUA, label="32k budget (fair) — recovered")
    ax.scatter([], [], s=54, color=NAVY, label="32k budget (fair) — fell")
    fig.legend(loc="lower center", ncol=3, frameon=False, fontsize=7.4,
               bbox_to_anchor=(0.5, -0.04))
    ax.set_xlim(-0.02, 1.52); ax.set_ylim(-0.55, len(rows) - 0.3)
    ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0]); ax.set_yticks([])
    ax.tick_params(labelsize=8, length=0)
    ax.grid(axis="x", color=LINE, lw=0.6, zorder=0)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.set_title("Four plausible scores, all wrong: the same models on the same DCF case,\nbefore and after the harness proved equivalent room",
                 fontsize=11.5, color=NAVY, weight="bold", loc="left", pad=10)
    save(fig, "f5-starved-vs-fair")


# ----------------------------------------------------------------------------
# F6 -- checkpoint vectors: Opus vs Haiku on the DCF case.
# Source: outputs/eval3-live/{claude-opus-4-8,claude-haiku-4-5-20251001}/report.txt
# ----------------------------------------------------------------------------
def f6_checkpoints():
    cps = ["P1", "P2", "P3", "E1", "E2", "E3", "E4", "E5",
           "C1", "C2", "C3", "C4", "C5", "C6", "C7", "S1", "S2", "S3"]
    opus  = [0.885, 0.929, 1.0, 0.960, 1.0, 1.0, 1.0, 0.789,
             1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0.810, 1.0, 1.0, 1.0]
    haiku = [0.885, 0.929, 1.0, 0.762, 0.808, 1.0, 0.857, 0.789,
             0.000, 1.0, 0.467, 0.526, 0.400, 0.500, 0.476, 0.588, 1.0, 1.0]
    x = list(range(len(cps)))
    fig, ax = plt.subplots(figsize=(7.2, 3.3))
    # stage bands
    for lo, hi, lab in [(0, 2, "Plan"), (3, 7, "Extract"), (8, 14, "Calculate"), (15, 17, "Decide")]:
        if lab in ("Extract", "Decide"):
            ax.axvspan(lo - 0.5, hi + 0.5, color="#F4F7FB", zorder=0)
        ax.text((lo + hi) / 2, 1.10, lab.upper(), ha="center", fontsize=7.5, color=MUTE, weight="bold")
    ax.plot(x, opus, "-o", color=BLUE, lw=2, ms=5.5, zorder=4, label="Claude Opus 4.8 (gated 0.965, no gate)")
    ax.plot(x, haiku, "-o", color=RED, lw=2, ms=5.5, zorder=3, label="Claude Haiku 4.5 (gated 0.692, GATE.C1FCF)")
    ax.annotate("GATE.C1FCF: reported FCFF ≠ its own build (+$2B/yr) —\nzeroed at C1, cascades through C3–C7 to a $138 fair value",
                xy=(8, 0.0), xytext=(8.4, 0.16), fontsize=7.8, color=RED,
                arrowprops=dict(arrowstyle="->", color=RED, lw=1.0))
    ax.annotate("shared dip: the E5 WACC probe —\nall models refuse the number\nthey just derived",
                xy=(7, 0.775), xytext=(-0.3, 0.42), fontsize=7.8, color=MUTE,
                arrowprops=dict(arrowstyle="->", color=MUTE, lw=0.9,
                                connectionstyle="arc3,rad=0.15"))
    ax.set_xticks(x); ax.set_xticklabels(cps, fontsize=8, family=MONO)
    ax.set_ylim(-0.06, 1.18); ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.tick_params(labelsize=8, length=0)
    ax.grid(axis="y", color=LINE, lw=0.6, zorder=0)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.legend(loc="lower left", frameon=False, fontsize=8)
    ax.set_ylabel("checkpoint score (gated)", fontsize=9)
    ax.set_title("Where the failure lives: per-checkpoint scores on the DCF case —\none gate localizes the break, then shows its cascade",
                 fontsize=11.5, color=NAVY, weight="bold", loc="left", pad=10)
    save(fig, "f6-checkpoint-vectors")


# ----------------------------------------------------------------------------
# F7 -- blast-radius ladder: planted DCF errors, gated score by gate tier.
# Source: README "What the gate taxonomy shows (eval #3)" (selftest-pinned).
# ----------------------------------------------------------------------------
def f7_blast_radius():
    rows = [  # variant, gate, tier, gated score
        ("basis_mix — FCFF discounted at cost of equity",  "GATE.BASIS",          "hard", 0.35),
        ("basis_late — same error, executed late",         "GATE.BASIS (C5 hook)","hard", 0.38),
        ("scale_slip — thousands vs millions",             "GATE.SCALE",          "hard", 0.73),
        ("c1_fcf — FCFF ≠ its own build",                  "in-checkpoint",       "cp",   0.81),
        ("bridge_omit — EV÷shares, no net-debt bridge",    "GATE.BRIDGE",         "scoped", 0.85),
        ("false_precision — decimal target, no sensitivity","GATE.FALSEPRECISION","scoped", 0.88),
        ("c7_sign — sign flip at the verdict",             "in-checkpoint",       "cp",   0.93),
        ("g_explode — terminal growth ≥ WACC",             "in-checkpoint",       "cp",   0.94),
    ]
    tiercol = {"hard": "#104281", "scoped": "#2a78d6", "cp": "#86b6ef"}
    tierlab = {"hard": "hard gate", "scoped": "scoped gate", "cp": "in-checkpoint"}
    fig, ax = plt.subplots(figsize=(7.0, 3.6))
    for i, (name, gate, tier, v) in enumerate(rows):
        y = len(rows) - 1 - i
        ax.barh([y], [v], height=0.55, color=tiercol[tier], zorder=3)
        ax.text(v + 0.012, y, f"{v:.2f}", va="center", fontsize=9, family=MONO,
                color=NAVY, weight="bold")
        ax.text(-0.015, y, name, va="center", ha="right", fontsize=8.2, color=NAVY)
        if gate != "in-checkpoint":
            ax.text(0.015, y, gate, va="center", ha="left", fontsize=6.8, family=MONO,
                    color="#FFFFFF" if tier != "cp" else NAVY, zorder=4)
    from matplotlib.patches import Patch
    handles = [Patch(facecolor=tiercol[t], label=tierlab[t]) for t in ["hard", "scoped", "cp"]]
    ax.axvline(1.0, color=LINE, lw=1.0, zorder=1)
    ax.text(1.0, -0.5, "oracle = 1.000", fontsize=7.5, color=MUTE, ha="center")
    ax.legend(handles=handles, loc="upper right", frameon=False, fontsize=8,
              bbox_to_anchor=(1.0, 0.97))
    ax.set_xlim(0, 1.12); ax.set_ylim(-0.6, len(rows) - 0.2)
    ax.set_yticks([]); ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.tick_params(labelsize=8, length=0)
    ax.grid(axis="x", color=LINE, lw=0.6, zorder=0)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.set_title("Blast radius is calibrated to severity: eight of the eleven planted DCF errors\n(those with published gated scores), each tripping exactly one gate",
                 fontsize=11.5, color=NAVY, weight="bold", loc="left", pad=10)
    save(fig, "f7-blast-radius")


if __name__ == "__main__":
    f1_coverage()
    f2_demo()
    f3_architecture()
    f4_heatmap()
    f5_starved_fair()
    f6_checkpoints()
    f7_blast_radius()
    print("done ->", HERE)

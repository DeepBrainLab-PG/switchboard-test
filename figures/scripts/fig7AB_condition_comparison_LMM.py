import numpy as np
import pandas as pd
import matplotlib as mpl
mpl.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.colors import ListedColormap, BoundaryNorm

CURVES = "figR3_condition_comparison_LMM_curves.csv"
PAIRWISE = "figR3_condition_comparison_LMM_pairwise.csv"
OMNIBUS = "figR3_condition_comparison_LMM_omnibus.csv"
OUT = "figR3_condition_comparison_LMM"
NEW = "7-4-2 Random after Fixed"
CORD = ["7-4-2", "7-5-3", "7-4-5-2", "7-4-2-1", "7-4-2 random only",
        "7-5-3 random only", NEW]
CCOL = {"7-4-2": "#2A9D8F", "7-5-3": "#219EBC", "7-4-5-2": "#FB8500",
        "7-4-2-1": "#FFB703", "7-4-2 random only": "#AE2102",
        "7-5-3 random only": "#C026A7", NEW: "#7A7A7A"}
SHORT = {"7-4-2": "7-4-2", "7-5-3": "7-5-3", "7-4-5-2": "7-4-5-2",
         "7-4-2-1": "7-4-2-1", "7-4-2 random only": "7-4-2 rand",
         "7-5-3 random only": "7-5-3 rand", NEW: "7-4-2 r.a.f."}
SPC = [("CPR", "Correct press ratio", (0, 0.9), [0, 0.2, 0.4, 0.6, 0.8]),
       ("CRP", "Correct-response prob.", (0, 0.9), [0, 0.2, 0.4, 0.6, 0.8]),
       ("E", "Off-path error ratio", (0, 0.85), [0, 0.2, 0.4, 0.6, 0.8]),
       ("IPI", "Inter-press interval", (0, 1.0), [0, 0.25, 0.5, 0.75, 1.0]),
       ("MS", "Spatial memory score", (0, 0.9), [0, 0.2, 0.4, 0.6, 0.8])]
LEV = ["ns", "*", "**", "***", "****"]
LL = {"ns": "n.s.", "*": "$p$ < 0.05", "**": "$p$ < 0.01",
      "***": "$p$ < 0.001", "****": "$p$ < 0.0001"}
PAIRC = "#C2185B"
DAYS = list(range(1, 9))
TKSZ = 15
AXSZ = 18


def style():
    try:
        import lovelyplots
        plt.style.use(["ipynb", "use_mathtext", "colors10-markers"])
    except Exception:
        pass
    mpl.rcParams.update({
        "font.family": "sans-serif",
        "svg.fonttype": "none",
        "pdf.fonttype": 42,
        "axes.grid": False,
        "xtick.labelsize": TKSZ,
        "ytick.labelsize": TKSZ,
        "axes.labelsize": AXSZ,
        "xtick.major.width": 1.6,
        "ytick.major.width": 1.6,
        "xtick.major.size": 6.0,
        "ytick.major.size": 6.0,
        "axes.linewidth": 1.6,
    })


def tk(ax, axis, vals, labels=None):
    a = ax.yaxis if axis == "y" else ax.xaxis
    a.set_major_locator(mpl.ticker.FixedLocator(vals))
    a.set_major_formatter(mpl.ticker.FixedFormatter(
        labels if labels is not None else [f"{v:g}" for v in vals]))


def bx(ax):
    for s in ax.spines.values():
        s.set_visible(True)
        s.set_linewidth(1.6)
    ax.tick_params(top=False, right=False, width=1.6, length=6.0)


def main():
    style()
    reds = plt.get_cmap("Reds")
    lc = {"ns": "#FFFFFF", "*": reds(0.22), "**": reds(0.42),
          "***": reds(0.64), "****": reds(0.88)}
    code = {k: i for i, k in enumerate(LEV)}
    cmap = ListedColormap([lc[k] for k in LEV])
    norm = BoundaryNorm([-.5, .5, 1.5, 2.5, 3.5, 4.5], cmap.N)
    cur = pd.read_csv(CURVES)
    pw = pd.read_csv(PAIRWISE)
    om = pd.read_csv(OMNIBUS).set_index("measure")
    nr = cur.groupby("cohort").n_rats.first()
    ix = {c: i for i, c in enumerate(CORD)}

    fig = plt.figure(figsize=(24.5, 13.2))
    gs = fig.add_gridspec(2, 5, height_ratios=[1, 1.14], hspace=0.28, wspace=0.52)
    for j, (lab, ylab, ylim, yt) in enumerate(SPC):
        ax = fig.add_subplot(gs[0, j])
        for c in CORD:
            y = cur[(cur.cohort == c) & (cur.measure == lab)].set_index("day").value
            y = y.reindex(DAYS)
            ax.plot(y.index.values, y.values, "-o", color=CCOL[c], lw=2.4,
                    markersize=8.0, markeredgecolor="black", markeredgewidth=0.8,
                    zorder=5 if c == NEW else 4)
        ax.set_xlim(0.5, 8.5)
        ax.set_ylim(*ylim)
        tk(ax, "x", DAYS)
        tk(ax, "y", yt)
        ax.set_xlabel("Session on the sequence", fontsize=AXSZ)
        ax.set_ylabel(ylab, fontsize=AXSZ, labelpad=6)
        ax.set_title(lab, fontsize=21, fontweight="bold", pad=12)
        bx(ax)

    k = len(CORD)
    for j, (lab, ylab, ylim, yt) in enumerate(SPC):
        ax = fig.add_subplot(gs[1, j])
        for r in pw[pw.measure == lab].itertuples():
            lo, hi = sorted((ix[r.a], ix[r.b]))
            ax.add_patch(Rectangle((lo - 0.5, hi - 0.5), 1, 1,
                                   facecolor=cmap(norm(code[r.stars])),
                                   edgecolor="none", zorder=2))
            if r.pairing == "within-subject":
                ax.add_patch(Rectangle((lo - 0.5, hi - 0.5), 1, 1, facecolor="none",
                                       edgecolor=PAIRC, lw=2.0, zorder=6))
        for i in range(k):
            ax.add_patch(Rectangle((i - 0.5, i - 0.5), 1, 1, facecolor="#D9D9D9",
                                   edgecolor="none", zorder=3))
        for g in np.arange(-0.5, k, 1.0):
            ax.axvline(g, color="#CCCCCC", lw=0.5, zorder=4)
            ax.axhline(g, color="#CCCCCC", lw=0.5, zorder=4)
        ax.set_xlim(-0.5, k - 0.5)
        ax.set_ylim(k - 0.5, -0.5)
        ax.set_aspect("equal")
        tk(ax, "x", np.arange(k), [SHORT[c] for c in CORD])
        tk(ax, "y", np.arange(k), [SHORT[c] for c in CORD] if j == 0 else [""] * k)
        for t in ax.get_xticklabels():
            t.set_rotation(52)
            t.set_ha("right")
            t.set_fontsize(TKSZ)
            t.set_color("black")
        for t in ax.get_yticklabels():
            t.set_fontsize(TKSZ)
            t.set_color("black")
        ax.set_title(f"$\\chi^2$(6) = {om.loc[lab, 'LR_chi2']:.1f},  "
                     f"ICC = {om.loc[lab, 'ICC']:.2f}", fontsize=17, pad=10)
        bx(ax)
        ax.tick_params(length=0)

    h1 = [mpl.lines.Line2D([], [], color=CCOL[c], marker="o", lw=2.4, markersize=8.0,
                           markeredgecolor="black", markeredgewidth=0.8,
                           label=f"{c}  ($n$ = {int(nr[c])})") for c in CORD]
    fig.legend(handles=h1, loc="lower center", bbox_to_anchor=(0.5, -0.040),
               ncol=4, frameon=False, fontsize=16)
    h2 = [Rectangle((0, 0), 1, 1, facecolor=lc[x], edgecolor="#777777", lw=0.8,
                    label=LL[x]) for x in LEV]
    h2.append(Rectangle((0, 0), 1, 1, facecolor="none", edgecolor=PAIRC, lw=2.0,
                        label="within-subject pair"))
    fig.legend(handles=h2, loc="lower center", bbox_to_anchor=(0.5, -0.098),
               ncol=6, frameon=False, fontsize=16)
    fig.suptitle("Comparison across task conditions — first 8 sessions on each "
                 "sequence, condition means\nBottom row: linear mixed model on ranks "
                 "with rat as a random intercept, all pairwise contrasts, "
                 "Holm-corrected", fontsize=20, y=1.015, linespacing=1.6)
    fig.savefig(OUT + ".png", dpi=300, bbox_inches="tight")
    fig.savefig(OUT + ".svg", bbox_inches="tight")


if __name__ == "__main__":
    main()

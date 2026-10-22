import os
import numpy as np
import pandas as pd
import matplotlib as mpl
mpl.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.colors import ListedColormap, BoundaryNorm

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "fig1_data.csv")
OMNI = os.path.join(HERE, "fig1_stats_omnibus.csv")
PAIR = os.path.join(HERE, "fig1_stats_pairwise.csv")
OUT = os.path.join(HERE, "fig1_learning")

try:
    import lovelyplots  # noqa: F401
    plt.style.use(["ipynb", "use_mathtext", "colors10-markers"])
except Exception:
    pass
mpl.rcParams.update({
    "font.family": "Arial", "svg.fonttype": "none", "pdf.fonttype": 42,
    "savefig.transparent": False, "axes.linewidth": 1.6,
    "xtick.labelsize": 17, "ytick.labelsize": 17, "axes.labelsize": 19,
    "axes.titlesize": 20, "legend.fontsize": 15,
    "xtick.major.width": 1.6, "ytick.major.width": 1.6,
    "xtick.major.size": 6.0, "ytick.major.size": 6.0,
    "xtick.direction": "out", "ytick.direction": "out", "axes.grid": False,
})

TRACE = "#000000"        # mean +/- SD trace
POINT = "#9A9A9A"        # individual rat-session points

_REDS = plt.get_cmap("Reds")
LEVELS = ["ns", "*", "**", "***", "****"]
LEVEL_COLOR = {"ns": "#FFFFFF", "*": _REDS(0.22), "**": _REDS(0.42),
               "***": _REDS(0.64), "****": _REDS(0.88)}
LEVEL_LABEL = {"ns": "n.s.", "*": "$p$ < 0.05", "**": "$p$ < 0.01",
               "***": "$p$ < 0.001", "****": "$p$ < 0.0001"}
CODE = {k: i for i, k in enumerate(LEVELS)}
CMAP = ListedColormap([LEVEL_COLOR[k] for k in LEVELS])
NORM = BoundaryNorm([-0.5, 0.5, 1.5, 2.5, 3.5, 4.5], CMAP.N)

MEASURES = [("CPR", "Correct press ratio"),
            ("CRP", "Correct-response probability"),
            ("E",   "Off-path error ratio"),
            ("IPI", "Inter-press interval  4$\\rightarrow$2")]
SESSIONS = list(range(1, 19))
TICKS = [1, 6, 12, 18]
GRID_STEP = 1            # one line per cell boundary, so every labelled cell is delimited
JITTER = 0.22
RNG = np.random.default_rng(3)


def box_frame(ax):
    """Full box, as in the reference figure."""
    for s in ax.spines.values():
        s.set_visible(True)
        s.set_linewidth(1.6)
    ax.tick_params(top=False, right=False)


def curve_panel(ax, d, ylabel, ylim, yticks):
    """Individual points behind, mean +/- SD trace in front."""
    for i, s in enumerate(SESSIONS):
        y = d.loc[d.session == s, "value"].to_numpy(float)
        y = y[~np.isnan(y)]
        ax.scatter(np.full(len(y), s) + RNG.uniform(-JITTER, JITTER, len(y)),
                   y, s=26, color=POINT, alpha=0.40, lw=0.3,
                   edgecolor="white", zorder=2)
    m = np.array([np.nanmean(d.loc[d.session == s, "value"]) for s in SESSIONS])
    sd = np.array([np.nanstd(d.loc[d.session == s, "value"], ddof=1) for s in SESSIONS])
    ax.errorbar(SESSIONS, m, yerr=sd, fmt="o-", color=TRACE, markersize=8.0,
                lw=2.4, capsize=3.8, elinewidth=1.6, markeredgecolor="black",
                markeredgewidth=0.8, zorder=5)
    ax.set_xlim(0.3, 18.7)
    ax.set_ylim(*ylim)
    ax.xaxis.set_major_locator(mpl.ticker.FixedLocator(TICKS))
    ax.xaxis.set_major_formatter(mpl.ticker.FixedFormatter([str(t) for t in TICKS]))
    ax.yaxis.set_major_locator(mpl.ticker.FixedLocator(yticks))
    ax.yaxis.set_major_formatter(mpl.ticker.FixedFormatter([f"{v:g}" for v in yticks]))
    ax.set_xlabel("Training session")
    ax.set_ylabel(ylabel)
    box_frame(ax)


def matrix_panel(ax, pair, label, omni_row):
    """Lower-triangular Nemenyi matrix with a half-spacing grid."""
    k = len(SESSIONS)
    idx = {str(s): i for i, s in enumerate(SESSIONS)}
    sub = pair[pair.measure == label]
    for r in sub.itertuples():
        i, j = idx[str(r.a)], idx[str(r.b)]
        lo, hi = min(i, j), max(i, j)
        ax.add_patch(Rectangle((lo - 0.5, hi - 0.5), 1, 1,
                               facecolor=CMAP(NORM(CODE[r.stars])),
                               edgecolor="none", zorder=2))
    for i in range(k):                                   # diagonal
        ax.add_patch(Rectangle((i - 0.5, i - 0.5), 1, 1,
                               facecolor="#D9D9D9", edgecolor="none", zorder=2))
    for g in np.arange(-0.5, k, GRID_STEP):
        ax.axvline(g, color="#CCCCCC", lw=0.5, zorder=4)
        ax.axhline(g, color="#CCCCCC", lw=0.5, zorder=4)
    ax.set_xlim(-0.5, k - 0.5)
    ax.set_ylim(k - 0.5, -0.5)
    ax.set_aspect("equal")
    pos = [SESSIONS.index(t) for t in TICKS]
    lab = [str(t) for t in TICKS]
    ax.xaxis.set_major_locator(mpl.ticker.FixedLocator(pos))
    ax.xaxis.set_major_formatter(mpl.ticker.FixedFormatter(lab))
    ax.yaxis.set_major_locator(mpl.ticker.FixedLocator(pos))
    ax.yaxis.set_major_formatter(mpl.ticker.FixedFormatter(lab))
    ax.set_xlabel("Training session")
    ax.set_ylabel("Training session")
    ax.set_title(f"$\\chi^2$({int(omni_row.df)}) = {omni_row.chi2:.0f},  "
                 f"$W$ = {omni_row.kendall_W:.2f}", fontsize=17, pad=10)
    box_frame(ax)


def main():
    data = pd.read_csv(DATA)
    omni = pd.read_csv(OMNI).set_index("measure")
    pair = pd.read_csv(PAIR)

    ylims = {"CPR": ((0, 1.0), [0, 0.25, 0.5, 0.75, 1.0]),
             "CRP": ((0, 1.0), [0, 0.25, 0.5, 0.75, 1.0]),
             "E":   ((0, 0.9), [0, 0.2, 0.4, 0.6, 0.8]),
             "IPI": ((0, 1.0), [0, 0.25, 0.5, 0.75, 1.0])}

    fig = plt.figure(figsize=(11.6, 19.2))
    gs = fig.add_gridspec(4, 2, width_ratios=[1.30, 1.0],
                          hspace=0.42, wspace=0.34)
    for row, (label, ylabel) in enumerate(MEASURES):
        d = data[data.measure == label]
        ylim, yticks = ylims[label]
        axc = fig.add_subplot(gs[row, 0])
        curve_panel(axc, d, ylabel, ylim, yticks)
        axc.set_title(label, fontsize=21, fontweight="bold", pad=12)
        axm = fig.add_subplot(gs[row, 1])
        matrix_panel(axm, pair, label, omni.loc[label])

    handles = [Rectangle((0, 0), 1, 1, facecolor=LEVEL_COLOR[k],
                         edgecolor="#777777", lw=0.8, label=LEVEL_LABEL[k])
               for k in LEVELS]
    fig.legend(handles=handles, loc="lower center", bbox_to_anchor=(0.5, -0.018),
               ncol=5, frameon=False, fontsize=16)
    fig.savefig(OUT + ".png", dpi=300, bbox_inches="tight")
    fig.savefig(OUT + ".svg", bbox_inches="tight")


if __name__ == "__main__":
    main()

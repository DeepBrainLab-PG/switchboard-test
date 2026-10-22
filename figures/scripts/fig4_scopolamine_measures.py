import os
import numpy as np
import pandas as pd
import matplotlib as mpl
mpl.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.lines import Line2D
from matplotlib.colors import ListedColormap, BoundaryNorm

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "fig2_data.csv")
OMNI = os.path.join(HERE, "fig2_stats_omnibus.csv")
PAIR = os.path.join(HERE, "fig2_stats_pairwise.csv")
OUT = os.path.join(HERE, "fig2_scopolamine")

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

TRACE = "#000000"
POINT = "#9A9A9A"
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
CONDS = ["Baseline", "Saline", "0.015", "0.025", "0.035", "0.05", "0.125", "0.25"]
SHORT = ["Base", "Sal", "0.015", "0.025", "0.035", "0.05", "0.125", "0.25"]
JITTER = 0.17
RNG = np.random.default_rng(3)


def box_frame(ax):
    for s in ax.spines.values():
        s.set_visible(True)
        s.set_linewidth(1.6)
    ax.tick_params(top=False, right=False)


def curve_panel(ax, d, ylabel, ylim, yticks, open_at=()):
    xs = np.arange(len(CONDS))
    for i, c in enumerate(CONDS):
        y = d.loc[d.condition == c, "value"].to_numpy(float)
        y = y[~np.isnan(y)]
        ax.scatter(np.full(len(y), i) + RNG.uniform(-JITTER, JITTER, len(y)),
                   y, s=30, color=POINT, alpha=0.45, lw=0.3,
                   edgecolor="white", zorder=2)
    m = np.array([np.nanmean(d.loc[d.condition == c, "value"]) for c in CONDS])
    sd = np.array([np.nanstd(d.loc[d.condition == c, "value"], ddof=1) for c in CONDS])
    ax.errorbar(xs, m, yerr=sd, fmt="o-", color=TRACE, markersize=8.5, lw=2.4,
                capsize=3.8, elinewidth=1.6, markeredgecolor="black",
                markeredgewidth=0.8, zorder=5)
    for i in open_at:                      # no animal measurable at this dose
        ax.plot([i], [m[i]], "o", color="white", markeredgecolor=TRACE,
                markeredgewidth=2.0, markersize=10.5, zorder=7)
    ax.set_xlim(-0.6, len(CONDS) - 0.4)
    ax.set_ylim(*ylim)
    ax.xaxis.set_major_locator(mpl.ticker.FixedLocator(xs))
    ax.xaxis.set_major_formatter(mpl.ticker.FixedFormatter(SHORT))
    ax.yaxis.set_major_locator(mpl.ticker.FixedLocator(yticks))
    ax.yaxis.set_major_formatter(mpl.ticker.FixedFormatter([f"{v:g}" for v in yticks]))
    for t in ax.get_xticklabels():
        t.set_rotation(52)
        t.set_ha("right")
    ax.set_xlabel("Scopolamine (mg/kg)")
    ax.set_ylabel(ylabel)
    box_frame(ax)


def matrix_panel(ax, pair, label, omni_row):
    k = len(CONDS)
    idx = {str(c): i for i, c in enumerate(CONDS)}
    sub = pair[pair.measure == label]
    for r in sub.itertuples():
        i, j = idx[str(r.a)], idx[str(r.b)]
        lo, hi = min(i, j), max(i, j)
        ax.add_patch(Rectangle((lo - 0.5, hi - 0.5), 1, 1,
                               facecolor=CMAP(NORM(CODE[r.stars])),
                               edgecolor="none", zorder=2))
    for i in range(k):
        ax.add_patch(Rectangle((i - 0.5, i - 0.5), 1, 1,
                               facecolor="#D9D9D9", edgecolor="none", zorder=2))
    # conditions are already one tick apart, so the grid runs on cell boundaries
    for g in np.arange(-0.5, k, 1.0):
        ax.axvline(g, color="#BBBBBB", lw=0.7, zorder=4)
        ax.axhline(g, color="#BBBBBB", lw=0.7, zorder=4)
    ax.set_xlim(-0.5, k - 0.5)
    ax.set_ylim(k - 0.5, -0.5)
    ax.set_aspect("equal")
    ax.xaxis.set_major_locator(mpl.ticker.FixedLocator(np.arange(k)))
    ax.xaxis.set_major_formatter(mpl.ticker.FixedFormatter(SHORT))
    ax.yaxis.set_major_locator(mpl.ticker.FixedLocator(np.arange(k)))
    ax.yaxis.set_major_formatter(mpl.ticker.FixedFormatter(SHORT))
    for t in ax.get_xticklabels():
        t.set_rotation(52)
        t.set_ha("right")
    ax.tick_params(labelsize=14)
    ax.set_xlabel("Scopolamine (mg/kg)")
    ax.set_ylabel("Scopolamine (mg/kg)")
    ax.set_title(f"$\\chi^2$({int(omni_row.df)}) = {omni_row.chi2:.0f},  "
                 f"$W$ = {omni_row.kendall_W:.2f}", fontsize=17, pad=10)
    box_frame(ax)


def main():
    data = pd.read_csv(DATA)
    omni = pd.read_csv(OMNI).set_index("measure")
    pair = pd.read_csv(PAIR)
    data["condition"] = data["condition"].astype(str)
    pair["a"] = pair["a"].astype(str)
    pair["b"] = pair["b"].astype(str)

    nd = (data[data.measure == "IPI"].groupby("condition")["defined"]
          .sum().reindex(CONDS).fillna(0).astype(int))
    open_at = [i for i, c in enumerate(CONDS) if nd[c] == 0]

    ylims = {"CPR": ((0, 1.0), [0, 0.25, 0.5, 0.75, 1.0]),
             "CRP": ((0, 1.0), [0, 0.25, 0.5, 0.75, 1.0]),
             "E":   ((0, 1.05), [0, 0.25, 0.5, 0.75, 1.0]),
             "IPI": ((0, 1.1), [0, 0.25, 0.5, 0.75, 1.0])}

    fig = plt.figure(figsize=(11.6, 19.6))
    gs = fig.add_gridspec(4, 2, width_ratios=[1.30, 1.0],
                          hspace=0.52, wspace=0.34)
    for row, (label, ylabel) in enumerate(MEASURES):
        d = data[data.measure == label]
        ylim, yticks = ylims[label]
        axc = fig.add_subplot(gs[row, 0])
        curve_panel(axc, d, ylabel, ylim, yticks,
                    open_at=open_at if label == "IPI" else ())
        axc.set_title(label, fontsize=21, fontweight="bold", pad=12)
        axm = fig.add_subplot(gs[row, 1])
        matrix_panel(axm, pair, label, omni.loc[label])

    handles = [Rectangle((0, 0), 1, 1, facecolor=LEVEL_COLOR[k],
                         edgecolor="#777777", lw=0.8, label=LEVEL_LABEL[k])
               for k in LEVELS]
    handles.append(Line2D([], [], color="white", marker="o", lw=0, markersize=10.5,
                          markeredgecolor=TRACE, markeredgewidth=2.0,
                          label="no animal completed a 4$\\rightarrow$2 transition"))
    fig.legend(handles=handles, loc="lower center", bbox_to_anchor=(0.5, -0.020),
               ncol=3, frameon=False, fontsize=16)
    fig.savefig(OUT + ".png", dpi=300, bbox_inches="tight")
    fig.savefig(OUT + ".svg", bbox_inches="tight")


if __name__ == "__main__":
    main()

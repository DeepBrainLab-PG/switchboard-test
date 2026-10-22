import os
import numpy as np
import pandas as pd
import matplotlib as mpl
mpl.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.colors import ListedColormap, BoundaryNorm

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "fig3_data.csv")
OMNI = os.path.join(HERE, "fig3_stats_omnibus.csv")
PAIR = os.path.join(HERE, "fig3_stats_pairwise.csv")
OUT = os.path.join(HERE, "fig3_memory_score")

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

MS_COLOR = "#364B9A"          # memory score trace
MS_POINT = "#9FB0E0"          # individual rat points, brighter blue
_REDS = plt.get_cmap("Reds")
LEVELS = ["ns", "*", "**", "***", "****"]
LEVEL_COLOR = {"ns": "#FFFFFF", "*": _REDS(0.22), "**": _REDS(0.42),
               "***": _REDS(0.64), "****": _REDS(0.88)}
LEVEL_LABEL = {"ns": "n.s.", "*": "$p$ < 0.05", "**": "$p$ < 0.01",
               "***": "$p$ < 0.001", "****": "$p$ < 0.0001"}
CODE = {k: i for i, k in enumerate(LEVELS)}
CMAP = ListedColormap([LEVEL_COLOR[k] for k in LEVELS])
NORM = BoundaryNorm([-0.5, 0.5, 1.5, 2.5, 3.5, 4.5], CMAP.N)

SESSIONS = [str(s) for s in range(1, 19)]
SESS_TICKS = ["1", "6", "12", "18"]
SESS_GRID_STEP = 1                    # one line per cell boundary
CONDS = ["Baseline", "Saline", "0.015", "0.025", "0.035", "0.05", "0.125", "0.25"]
COND_SHORT = ["Base", "Sal", "0.015", "0.025", "0.035", "0.05", "0.125", "0.25"]
EQUATION = (r"$\mathrm{MS}=\dfrac{\mathrm{CPR}+\mathrm{CRP}"
            r"+(1-\mathrm{IPI})+(1-E)}{4}$")
RNG = np.random.default_rng(3)


def box_frame(ax):
    for s in ax.spines.values():
        s.set_visible(True)
        s.set_linewidth(1.6)
    ax.tick_params(top=False, right=False)


def curve_panel(ax, d, levels, ticklabels, xlabel, jitter, rotate):
    xs = np.arange(len(levels))
    for i, lv in enumerate(levels):
        y = d.loc[d.x == lv, "value"].to_numpy(float)
        y = y[~np.isnan(y)]
        ax.scatter(np.full(len(y), i) + RNG.uniform(-jitter, jitter, len(y)),
                   y, s=28, color=MS_POINT, alpha=0.48, lw=0.3,
                   edgecolor="white", zorder=2)
    m = np.array([np.nanmean(d.loc[d.x == lv, "value"]) for lv in levels])
    sd = np.array([np.nanstd(d.loc[d.x == lv, "value"], ddof=1) for lv in levels])
    ax.errorbar(xs, m, yerr=sd, fmt="o-", color=MS_COLOR, markersize=8.5,
                lw=2.4, capsize=3.8, elinewidth=1.6, markeredgecolor="black",
                markeredgewidth=0.8, zorder=5)
    ax.set_xlim(-0.6, len(levels) - 0.4)
    ax.set_ylim(0, 1.0)
    pos = [levels.index(t) for t in ticklabels]
    ax.xaxis.set_major_locator(mpl.ticker.FixedLocator(pos))
    ax.xaxis.set_major_formatter(mpl.ticker.FixedFormatter(
        [COND_SHORT[levels.index(t)] if levels is CONDS else t for t in ticklabels]))
    ax.yaxis.set_major_locator(mpl.ticker.FixedLocator([0, 0.25, 0.5, 0.75, 1.0]))
    ax.yaxis.set_major_formatter(mpl.ticker.FixedFormatter(["0", "0.25", "0.5", "0.75", "1"]))
    if rotate:
        for t in ax.get_xticklabels():
            t.set_rotation(52)
            t.set_ha("right")
    ax.set_xlabel(xlabel)
    ax.set_ylabel("Spatial memory score")
    box_frame(ax)


def matrix_panel(ax, pair, levels, ticklabels, xlabel, omni_row,
                 grid_step, rotate, ticksize):
    k = len(levels)
    idx = {lv: i for i, lv in enumerate(levels)}
    for r in pair.itertuples():
        i, j = idx[str(r.a)], idx[str(r.b)]
        lo, hi = min(i, j), max(i, j)
        ax.add_patch(Rectangle((lo - 0.5, hi - 0.5), 1, 1,
                               facecolor=CMAP(NORM(CODE[r.stars])),
                               edgecolor="none", zorder=2))
    for i in range(k):
        ax.add_patch(Rectangle((i - 0.5, i - 0.5), 1, 1,
                               facecolor="#D9D9D9", edgecolor="none", zorder=2))
    edges = np.arange(-0.5, k, grid_step)
    for g in edges:
        ax.axvline(g, color="#CCCCCC", lw=0.5, zorder=4)
        ax.axhline(g, color="#CCCCCC", lw=0.5, zorder=4)
    ax.set_xlim(-0.5, k - 0.5)
    ax.set_ylim(k - 0.5, -0.5)
    ax.set_aspect("equal")
    pos = [levels.index(t) for t in ticklabels]
    lab = [COND_SHORT[levels.index(t)] if levels is CONDS else t for t in ticklabels]
    ax.xaxis.set_major_locator(mpl.ticker.FixedLocator(pos))
    ax.xaxis.set_major_formatter(mpl.ticker.FixedFormatter(lab))
    ax.yaxis.set_major_locator(mpl.ticker.FixedLocator(pos))
    ax.yaxis.set_major_formatter(mpl.ticker.FixedFormatter(lab))
    if rotate:
        for t in ax.get_xticklabels():
            t.set_rotation(52)
            t.set_ha("right")
    ax.tick_params(labelsize=ticksize)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(xlabel)
    ax.set_title(f"$\\chi^2$({int(omni_row.df)}) = {omni_row.chi2:.0f},  "
                 f"$W$ = {omni_row.kendall_W:.2f}", fontsize=17, pad=10)
    box_frame(ax)


def main():
    data = pd.read_csv(DATA)
    omni = pd.read_csv(OMNI)
    pair = pd.read_csv(PAIR)
    data["x"] = data["x"].astype(str)
    pair["a"] = pair["a"].astype(str)
    pair["b"] = pair["b"].astype(str)

    fig = plt.figure(figsize=(11.6, 12.4))
    gs = fig.add_gridspec(3, 2, width_ratios=[1.30, 1.0],
                          height_ratios=[1.0, 0.30, 1.0],
                          hspace=0.46, wspace=0.34)

    tr = data[data.group == "training"]
    ax = fig.add_subplot(gs[0, 0])
    curve_panel(ax, tr, SESSIONS, SESS_TICKS, "Training session", 0.22, False)
    ax.set_title("MS  across learning", fontsize=21, fontweight="bold", pad=12)
    ax = fig.add_subplot(gs[0, 1])
    matrix_panel(ax, pair[pair.group == "training"], SESSIONS, SESS_TICKS,
                 "Training session", omni[omni.group == "training"].iloc[0],
                 SESS_GRID_STEP, False, 17)

    axe = fig.add_subplot(gs[1, :])
    axe.axis("off")
    axe.text(0.5, 0.5, EQUATION, ha="center", va="center", fontsize=30,
             color=MS_COLOR, transform=axe.transAxes)

    sc = data[data.group == "scopolamine"]
    ax = fig.add_subplot(gs[2, 0])
    curve_panel(ax, sc, CONDS, CONDS, "Scopolamine (mg/kg)", 0.17, True)
    ax.set_title("MS  across dose", fontsize=21, fontweight="bold", pad=12)
    ax = fig.add_subplot(gs[2, 1])
    matrix_panel(ax, pair[pair.group == "scopolamine"], CONDS, CONDS,
                 "Scopolamine (mg/kg)",
                 omni[omni.group == "scopolamine"].iloc[0], 1.0, True, 14)

    handles = [Rectangle((0, 0), 1, 1, facecolor=LEVEL_COLOR[k],
                         edgecolor="#777777", lw=0.8, label=LEVEL_LABEL[k])
               for k in LEVELS]
    fig.legend(handles=handles, loc="lower center", bbox_to_anchor=(0.5, -0.045),
               ncol=5, frameon=False, fontsize=16)
    fig.savefig(OUT + ".png", dpi=300, bbox_inches="tight")
    fig.savefig(OUT + ".svg", bbox_inches="tight")


if __name__ == "__main__":
    main()

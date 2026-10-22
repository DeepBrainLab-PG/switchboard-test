import numpy as np
import pandas as pd
import matplotlib as mpl
mpl.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

DATA = "fig47_data.csv"
OUT = "fig47_measure_only_bounds"
C3 = "#2A9D8F"
C4 = "#AE2012"


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
        "axes.linewidth": 1.6,
        "xtick.direction": "out",
        "ytick.direction": "out",
        "axes.grid": False,
    })


def tick(ax, axis, vals):
    a = ax.yaxis if axis == "y" else ax.xaxis
    a.set_major_locator(mpl.ticker.FixedLocator(vals))
    a.set_major_formatter(mpl.ticker.FixedFormatter([f"{v:g}" for v in vals]))


def frame(ax, tick_size=12):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(labelsize=tick_size)


def main():
    style()
    d = pd.read_csv(DATA)
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(12.6, 5.9),
                                 gridspec_kw=dict(wspace=0.30))
    x = np.linspace(0, 1, 200)

    a1.fill_between(x, x, x + (1 - x) * 2 / 3, color=C3, alpha=0.14, lw=0, zorder=1)
    a1.plot(x, x, "-", color="#444444", lw=1.6, marker="none", zorder=3)
    a1.plot(x, x + (1 - x) * 2 / 3, "-", color=C3, lw=2.0, marker="none", zorder=3)
    a1.plot(x, x + (1 - x) * 3 / 4, "--", color=C4, lw=2.0, marker="none", zorder=3)
    for L, c in [(3, C3), (4, C4)]:
        s = d[d.L == L]
        a1.scatter(s.CPR, s.CRP, s=7, color=c, alpha=0.30, lw=0, zorder=4)
    a1.set_xlim(0, 1)
    a1.set_ylim(0, 1)
    a1.set_aspect("equal")
    tick(a1, "x", [0, 0.25, 0.5, 0.75, 1.0])
    tick(a1, "y", [0, 0.25, 0.5, 0.75, 1.0])
    a1.set_xlabel("CPR", fontsize=14)
    a1.set_ylabel("CRP$_{pw}$", fontsize=14)
    a1.set_title("CPR and CRP$_{pw}$", fontsize=15, pad=12)
    a1.legend(handles=[
        Line2D([], [], color="#444444", lw=1.6, marker="none", label="CRP = CPR (any $L$)"),
        Line2D([], [], color=C3, lw=2.0, marker="none", label="upper bound, $L$ = 3"),
        Line2D([], [], color=C4, lw=2.0, ls="--", marker="none", label="upper bound, $L$ = 4"),
        Line2D([], [], color=C3, lw=0, marker="o", markersize=5, label="sessions, $L$ = 3"),
        Line2D([], [], color=C4, lw=0, marker="o", markersize=5, label="sessions, $L$ = 4"),
    ], loc="lower right", frameon=False, fontsize=10)
    frame(a1)

    a2.fill_between(x, 0, np.minimum((1 - x) * 7 / 6, 1.25), color=C4,
                    alpha=0.14, lw=0, zorder=1)
    a2.plot(x, np.minimum((1 - x) * 7 / 6, 1.25), "-", color=C4, lw=2.0,
            marker="none", zorder=3)
    a2.plot(x, np.minimum((1 - x) * 6 / 5, 1.25), "--", color=C4, lw=2.0,
            marker="none", zorder=3)
    for L, c in [(3, C3), (4, C4)]:
        s = d[d.L == L]
        a2.scatter(s.CRP, s.E, s=7, color=c, alpha=0.30, lw=0, zorder=4)
    a2.set_xlim(0, 1)
    a2.set_ylim(0, 1.25)
    tick(a2, "x", [0, 0.25, 0.5, 0.75, 1.0])
    tick(a2, "y", [0, 0.25, 0.5, 0.75, 1.0, 1.25])
    a2.set_xlabel("CRP$_{pw}$", fontsize=14)
    a2.set_ylabel("E", fontsize=14)
    a2.set_title("CRP$_{pw}$ and E", fontsize=15, pad=12)
    a2.legend(handles=[
        Line2D([], [], color=C4, lw=2.0, marker="none", label="upper bound, $L$ = 3"),
        Line2D([], [], color=C4, lw=2.0, ls="--", marker="none", label="upper bound, $L$ = 4"),
    ], loc="upper right", frameon=False, fontsize=10)
    frame(a2)

    fig.suptitle("Measures bounds", fontsize=16, y=1.00)
    fig.savefig(OUT + ".png", dpi=300, bbox_inches="tight")
    fig.savefig(OUT + ".svg", bbox_inches="tight")


if __name__ == "__main__":
    main()

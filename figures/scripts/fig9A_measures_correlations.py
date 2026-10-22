import numpy as np
import pandas as pd
import matplotlib as mpl
mpl.use("Agg")
import matplotlib.pyplot as plt

DATA = "fig51_measure_change_pairs_data.csv"
STATS = "fig51_measure_change_pairs_stats.csv"
OUT = "fig51_measure_change_pairs"
GREY = "#9A9A9A"
PAIRC = {
    ("CPR", "CRP"): "#005f73",
    ("CPR", "IPI"): "#ee9b00",
    ("CPR", "E"): "#ae2012",
    ("CRP", "IPI"): "#0a9396",
    ("CRP", "E"): "#bb3e03",
    ("IPI", "E"): "#ca6702",
}


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


def main():
    style()
    d = pd.read_csv(DATA)
    st = pd.read_csv(STATS)
    n_pairs = len(d)

    fig, axs = plt.subplots(2, 3, figsize=(17.0, 11.2))
    fig.subplots_adjust(hspace=0.52, wspace=0.26, top=0.89, bottom=0.07,
                        left=0.06, right=0.98)
    for k, r in enumerate(st.itertuples()):
        ax = axs[k // 3, k % 3]
        col = PAIRC[(r.a, r.b)]
        x = d["d_" + r.a].to_numpy()
        y = d["d_" + r.b].to_numpy()
        ax.scatter(x, y, s=14, color=GREY, alpha=0.38, lw=0, zorder=3)
        xs = np.linspace(x.min(), x.max(), 50)
        ax.plot(xs, r.intercept + r.slope_b_on_a * xs, "-", color=col, lw=3.0,
                marker="none", zorder=5)
        ax.axhline(0, color="#BBBBBB", lw=1.0, zorder=1)
        ax.axvline(0, color="#BBBBBB", lw=1.0, zorder=1)
        ax.set_xlim(-0.82, 0.82)
        ax.set_ylim(-0.82, 0.82)
        tick(ax, "x", [-0.8, -0.4, 0, 0.4, 0.8])
        tick(ax, "y", [-0.8, -0.4, 0, 0.4, 0.8])
        ax.set_xlabel(f"change in {r.a}", fontsize=16)
        ax.set_ylabel(f"change in {r.b}", fontsize=16)
        ax.set_title(f"slope {r.slope_b_on_a:+.2f}   reverse {r.slope_a_on_b:+.2f}"
                     f"   $R^2$ = {r.r2:.2f}", fontsize=14.5, pad=10)
        ax.text(0.03, 0.96, f"{r.a} vs {r.b}", transform=ax.transAxes, fontsize=16,
                va="top", fontweight="bold", color=col)
        for s in ["top", "right"]:
            ax.spines[s].set_visible(False)
        ax.tick_params(labelsize=15)

    fig.suptitle("Slopes and $R^2$ between the measures — all 7 cohorts, "
                 f"{n_pairs:,} within-rat session pairs from 53 rats",
                 fontsize=19.5, y=0.955)
    fig.savefig(OUT + ".png", dpi=300, bbox_inches="tight")
    fig.savefig(OUT + ".svg", bbox_inches="tight")


if __name__ == "__main__":
    main()

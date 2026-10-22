import numpy as np
import pandas as pd
import matplotlib as mpl
mpl.use("Agg")
import matplotlib.pyplot as plt

DATA = "fig51_length_simulation_data.csv"
OUT = "fig51_length_simulation"
C_CPR = "#2A9D8F"
C_CRP = "#94D2BD"
C_BAR = "#6A4C93"
ORDER = ["7-4-5-2", "7-4-2-1", "7-5-3", "7-4-2"]


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
        "xtick.labelsize": 21,
        "ytick.labelsize": 21,
        "axes.labelsize": 24,
        "legend.fontsize": 19,
        "xtick.major.width": 1.9,
        "ytick.major.width": 1.9,
        "xtick.major.size": 7.5,
        "ytick.major.size": 7.5,
        "axes.linewidth": 1.9,
    })


def tick(ax, axis, vals):
    a = ax.yaxis if axis == "y" else ax.xaxis
    a.set_major_locator(mpl.ticker.FixedLocator(vals))
    a.set_major_formatter(mpl.ticker.FixedFormatter([f"{v:g}" for v in vals]))


def main():
    style()
    d = pd.read_csv(DATA)
    med = d.groupby(["cohort", "L", "n_rats"])[["CPR", "CRP", "gap"]].median().reset_index()
    rng = np.random.default_rng(3)

    fig, ax = plt.subplots(figsize=(12.8, 7.4))
    for i, c in enumerate(ORDER):
        p = d[d.cohort == c]
        jit = rng.uniform(-0.065, 0.065, len(p))
        ax.scatter(p.CPR, i + 0.235 + jit, s=54, color=C_CPR, alpha=0.32,
                   edgecolor="none", zorder=2)
        ax.scatter(p.CRP, i - 0.235 + jit, s=54, color=C_CRP, alpha=0.45,
                   edgecolor="none", zorder=2)
        r = med[med.cohort == c].iloc[0]
        ax.plot([r.CPR, r.CRP], [i, i], "-", color=C_BAR, lw=7,
                solid_capstyle="butt", alpha=0.85, zorder=3)
        ax.plot([r.CPR], [i], "o", color=C_CPR, markersize=20,
                markeredgecolor="black", markeredgewidth=1.4, zorder=5)
        ax.plot([r.CRP], [i], "o", color=C_CRP, markersize=20,
                markeredgecolor="black", markeredgewidth=1.4, zorder=5)
        ax.text(r.CRP + 0.022, i, f"{r.gap:.3f}", va="center", ha="left",
                fontsize=20, color=C_BAR, fontweight="bold")

    ax.axhline(1.5, color="#AAAAAA", lw=1.6, ls="--", zorder=1)
    ax.set_yticks(range(len(ORDER)))
    ax.set_yticklabels(
        [f"{c}\n($L$ = {int(med[med.cohort == c].L.iloc[0])}, "
         f"$n$ = {int(med[med.cohort == c].n_rats.iloc[0])})" for c in ORDER],
        fontsize=20)
    ax.set_ylim(-0.6, len(ORDER) - 0.4)
    ax.set_xlim(0, 0.88)
    tick(ax, "x", [0, 0.2, 0.4, 0.6, 0.8])
    ax.set_xlabel("Measure value", fontsize=24)
    ax.text(0.885, 2.5, "$L$ = 3", fontsize=19, color="#666666",
            ha="right", va="center")
    ax.text(0.885, 0.5, "$L$ = 4", fontsize=19, color="#666666",
            ha="right", va="center")
    for s in ax.spines.values():
        s.set_visible(True)
        s.set_linewidth(1.9)
    ax.tick_params(top=False, right=False, width=1.9, length=7.5)
    ax.set_title("Completed sequences versus correct presses", fontsize=26, pad=16)

    h = [mpl.lines.Line2D([], [], color=C_CPR, marker="o", lw=0, markersize=16,
                          markeredgecolor="black", markeredgewidth=1.2, label="CPR"),
         mpl.lines.Line2D([], [], color=C_CRP, marker="o", lw=0, markersize=16,
                          markeredgecolor="black", markeredgewidth=1.2, label="CRP$_{pw}$"),
         mpl.lines.Line2D([], [], color=C_BAR, lw=7, marker="none",
                          label="CRP$_{pw}$ $-$ CPR")]
    fig.legend(handles=h, frameon=False, loc="lower center",
               bbox_to_anchor=(0.54, -0.085), ncol=3, columnspacing=2.2, fontsize=20)
    fig.savefig(OUT + ".png", dpi=300, bbox_inches="tight")
    fig.savefig(OUT + ".svg", bbox_inches="tight")


if __name__ == "__main__":
    main()

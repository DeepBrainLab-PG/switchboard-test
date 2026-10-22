import numpy as np
import pandas as pd
import matplotlib as mpl
mpl.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.colors import ListedColormap, BoundaryNorm

POINTS = "figR7_behavioral_controls_points.csv"
PAIRWISE = "figR7_behavioral_controls_pairwise.csv"
OMNIBUS = "figR7_behavioral_controls_omnibus.csv"
OUT = "figR7_behavioral_controls"
BLACK = "#111111"
COL = {"Control_No_Sounds": "#6A4C93", "Control_Satiated": "#B23A7A"}
TITLE = {"Control_No_Sounds": "No sound", "Control_Satiated": "No food restriction"}
CTLS = ["Control_No_Sounds", "Control_Satiated"]
SPEC = [("CPR", "Correct press ratio"), ("CRP", "Correct-response prob."),
        ("E", "Off-path error ratio"), ("IPI", "Inter-press interval"),
        ("MS", "Spatial memory score")]
YT = {"CPR": [0, 0.2, 0.4, 0.6, 0.8], "CRP": [0, 0.2, 0.4, 0.6, 0.8],
      "E": [0, 0.1, 0.2, 0.3, 0.4, 0.5], "IPI": [0, 0.25, 0.5, 0.75, 1.0],
      "MS": [0, 0.2, 0.4, 0.6, 0.8]}
MLAB6 = ["pre 1", "pre 2", "pre 3", "ctrl 1", "ctrl 2", "ctrl 3"]
LEV = ["ns", "*", "**", "***", "****"]
LL = {"ns": "n.s.", "*": "$p$ < 0.05", "**": "$p$ < 0.01",
      "***": "$p$ < 0.001", "****": "$p$ < 0.0001"}


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
        "xtick.labelsize": 17,
        "ytick.labelsize": 17,
        "axes.labelsize": 19,
        "legend.fontsize": 16,
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


def main():
    style()
    reds = plt.get_cmap("Reds")
    lc = {"ns": "#FFFFFF", "*": reds(0.22), "**": reds(0.42),
          "***": reds(0.64), "****": reds(0.88)}
    code = {k: i for i, k in enumerate(LEV)}
    cmap = ListedColormap([lc[k] for k in LEV])
    norm = BoundaryNorm([-.5, .5, 1.5, 2.5, 3.5, 4.5], cmap.N)
    P = pd.read_csv(POINTS)
    PW = pd.read_csv(PAIRWISE)
    OM = pd.read_csv(OMNIBUS)
    lims = {lab: (0.0, min(1.0, np.ceil(float(P[P.measure == lab].value.max()) * 20) / 20 + 0.03))
            for lab, _ in SPEC}

    D3 = [1, 2, 3]
    rng = np.random.default_rng(11)
    fig = plt.figure(figsize=(24.0, 19.5))
    gs = fig.add_gridspec(4, 5, height_ratios=[1.0, 1.06, 1.0, 1.06],
                          hspace=0.40, wspace=0.44)
    for ri, ctl in enumerate(CTLS):
        g0 = P[P.control == ctl]
        cc = COL[ctl]
        nr = g0.rat.nunique()
        for j, (lab, ylab) in enumerate(SPEC):
            gm = g0[g0.measure == lab]
            ax = fig.add_subplot(gs[ri * 2, j])
            for blk, cl, off in [("pre", BLACK, -0.11), ("ctrl", cc, +0.11)]:
                mu = []
                for dd in D3:
                    v = gm[(gm.block == blk) & (gm.dayin == dd)].value.to_numpy()
                    ax.scatter(dd + off + rng.uniform(-0.075, 0.075, len(v)), v,
                               s=54, facecolor=cl, edgecolor="none", alpha=0.24, zorder=3)
                    mu.append(v.mean())
                ax.plot(np.array(D3) + off, mu, "-", color=cl, lw=2.8, zorder=5)
                ax.plot(np.array(D3) + off, mu, "o", color=cl, markersize=13,
                        markeredgecolor="white", markeredgewidth=1.6, ls="none", zorder=6)
            ax.set_xlim(0.55, 3.45)
            ax.set_ylim(*lims[lab])
            tk(ax, "x", D3, ["Day 1", "Day 2", "Day 3"])
            tk(ax, "y", YT[lab])
            for t in list(ax.get_xticklabels()) + list(ax.get_yticklabels()):
                t.set_fontsize(17)
            ax.set_ylabel(ylab, fontsize=19, labelpad=6)
            ax.set_title(lab, fontsize=22, fontweight="bold", pad=12, color=cc)
            bx(ax)
            if j == 0:
                ax.text(-0.44, 0.5, f"{TITLE[ctl]}\n($n$ = {nr} rats)",
                        transform=ax.transAxes, fontsize=23, fontweight="bold",
                        color=cc, ha="center", va="center", rotation=90, linespacing=1.5)

            axm = fig.add_subplot(gs[ri * 2 + 1, j])
            k = 6
            for r in PW[(PW.control == ctl) & (PW.measure == lab)].itertuples():
                lo, hi = sorted((r.a - 1, r.b - 1))
                axm.add_patch(Rectangle((lo - 0.5, hi - 0.5), 1, 1,
                                        facecolor=cmap(norm(code[r.stars])),
                                        edgecolor="none", zorder=2))
            for i in range(k):
                axm.add_patch(Rectangle((i - 0.5, i - 0.5), 1, 1,
                                        facecolor="#D9D9D9", edgecolor="none", zorder=3))
            for g in np.arange(-0.5, k, 1.0):
                axm.axvline(g, color="#CCCCCC", lw=0.5, zorder=4)
                axm.axhline(g, color="#CCCCCC", lw=0.5, zorder=4)
            axm.axvline(2.5, color=cc, lw=2.2, zorder=7)
            axm.axhline(2.5, color=cc, lw=2.2, zorder=7)
            axm.set_xlim(-0.5, k - 0.5)
            axm.set_ylim(k - 0.5, -0.5)
            axm.set_aspect("equal")
            tk(axm, "x", np.arange(k), MLAB6)
            tk(axm, "y", np.arange(k), MLAB6 if j == 0 else [""] * k)
            for t in axm.get_xticklabels():
                t.set_rotation(52)
                t.set_ha("right")
                t.set_fontsize(16)
                t.set_color("black")
            for t in axm.get_yticklabels():
                t.set_fontsize(16)
                t.set_color("black")
            o = OM[(OM.control == ctl) & (OM.measure == lab)].iloc[0]
            axm.set_title(f"$\\chi^2$(5) = {o.LR_chi2:.1f},  ICC = {o.ICC:.2f}",
                          fontsize=17, pad=10)
            bx(axm)
            axm.tick_params(length=0)

    h = [mpl.lines.Line2D([], [], color=BLACK, marker="o", lw=2.8, markersize=13,
                          markeredgecolor="white", markeredgewidth=1.6,
                          label="3 days before the control"),
         mpl.lines.Line2D([], [], color=COL["Control_No_Sounds"], marker="o", lw=2.8,
                          markersize=13, markeredgecolor="white", markeredgewidth=1.6,
                          label="No sound"),
         mpl.lines.Line2D([], [], color=COL["Control_Satiated"], marker="o", lw=2.8,
                          markersize=13, markeredgecolor="white", markeredgewidth=1.6,
                          label="No food restriction")]
    fig.legend(handles=h, loc="lower center", bbox_to_anchor=(0.5, -0.015),
               ncol=3, frameon=False, fontsize=19)
    h2 = [Rectangle((0, 0), 1, 1, facecolor=lc[x], edgecolor="#777777", lw=0.8,
                    label=LL[x]) for x in LEV]
    fig.legend(handles=h2, loc="lower center", bbox_to_anchor=(0.5, -0.042),
               ncol=5, frameon=False, fontsize=18)
    fig.suptitle("Behavioural controls", fontsize=28, y=0.925)
    fig.savefig(OUT + ".png", dpi=300, bbox_inches="tight")
    fig.savefig(OUT + ".svg", bbox_inches="tight")


if __name__ == "__main__":
    main()

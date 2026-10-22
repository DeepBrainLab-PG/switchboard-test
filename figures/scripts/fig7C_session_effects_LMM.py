import numpy as np
import pandas as pd
import matplotlib as mpl
mpl.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.colors import ListedColormap, BoundaryNorm

DATA = "figR4_session_effects_LMM_data.csv"
OUT = "figR4_session_effects_LMM"
CORD = ["7-4-2", "7-5-3", "7-4-5-2", "7-4-2-1", "7-4-2 random only",
        "7-5-3 random only", "7-4-2 Random after Fixed"]
SHORT = {"7-4-2": "7-4-2", "7-5-3": "7-5-3", "7-4-5-2": "7-4-5-2",
         "7-4-2-1": "7-4-2-1", "7-4-2 random only": "7-4-2 rand",
         "7-5-3 random only": "7-5-3 rand",
         "7-4-2 Random after Fixed": "7-4-2 r.a.f."}
MLAB = ["CPR", "CRP", "E", "IPI", "MS"]
SESS = list(range(2, 9))
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
        "axes.titlesize": 20,
        "legend.fontsize": 16,
        "xtick.major.width": 1.6,
        "ytick.major.width": 1.6,
        "xtick.major.size": 6.0,
        "ytick.major.size": 6.0,
        "axes.linewidth": 1.6,
    })


def main():
    style()
    reds = plt.get_cmap("Reds")
    lc = {"ns": "#FFFFFF", "*": reds(0.22), "**": reds(0.42),
          "***": reds(0.64), "****": reds(0.88)}
    code = {k: i for i, k in enumerate(LEV)}
    cmap = ListedColormap([lc[k] for k in LEV])
    norm = BoundaryNorm([-.5, .5, 1.5, 2.5, 3.5, 4.5], cmap.N)
    d = pd.read_csv(DATA)

    fig = plt.figure(figsize=(19.6, 6.4))
    gs = fig.add_gridspec(1, 5, wspace=0.16)
    for mi, lab in enumerate(MLAB):
        ax = fig.add_subplot(gs[0, mi])
        M = np.zeros((len(CORD), len(SESS)), int)
        sub = d[d.measure == lab].set_index(["condition", "session"]).stars
        for ri, c in enumerate(CORD):
            for ci, s in enumerate(SESS):
                M[ri, ci] = code.get(sub.get((c, s), "ns"), 0)
        ax.imshow(M, cmap=cmap, norm=norm, aspect="auto")
        for g in np.arange(-0.5, len(SESS), 1):
            ax.axvline(g, color="#CCCCCC", lw=0.5)
        for g in np.arange(-0.5, len(CORD), 1):
            ax.axhline(g, color="#CCCCCC", lw=0.5)
        ax.set_xticks(range(len(SESS)))
        ax.set_xticklabels([str(s) for s in SESS], fontsize=17)
        ax.set_yticks(range(len(CORD)))
        ax.set_yticklabels([SHORT[c] for c in CORD] if mi == 0 else [""] * len(CORD),
                           fontsize=17, color="black")
        ax.set_xlabel("Session", fontsize=19)
        ax.set_title(lab, fontsize=22, fontweight="bold", pad=12)
        for s in ax.spines.values():
            s.set_visible(True)
            s.set_linewidth(1.6)
        ax.tick_params(length=0)

    h = [Rectangle((0, 0), 1, 1, facecolor=lc[k], edgecolor="#777777", lw=0.8,
                   label=LL[k]) for k in LEV]
    fig.legend(handles=h, loc="lower center", bbox_to_anchor=(0.5, -0.19),
               ncol=5, frameon=False, fontsize=17)
    fig.suptitle("Session effects within each task condition — linear mixed model "
                 "on ranks, rat as a random intercept\nEach session compared with "
                 "session 1 of the same condition, Holm-corrected.",
                 fontsize=19, y=1.10, linespacing=1.6)
    fig.savefig(OUT + ".png", dpi=300, bbox_inches="tight")
    fig.savefig(OUT + ".svg", bbox_inches="tight")


if __name__ == "__main__":
    main()

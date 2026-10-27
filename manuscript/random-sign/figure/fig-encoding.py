"""Same mappings, three encodings: law of X over all runs and over failed runs.

Inputs are the summaries written by fig-encoding-agg (see fig-encoding.md):
fig-encoding-hist.csv (bin counts, all and failed runs) and fig-encoding-stats.csv (failed-run statistics).
python3 fig-encoding.py  ->  fig-encoding.{pdf,png}
Style from ../../STD/figure/figstyle.py.
"""
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "STD", "figure"))
from figstyle import INK2, phi, plt  # noqa: E402

hist = pd.read_csv(os.path.join(HERE, "fig-encoding-hist.csv"))
stats = pd.read_csv(os.path.join(HERE, "fig-encoding-stats.csv")).set_index("col")
FAIL = "#D55E00"
fig, axs = plt.subplots(1, 3, figsize=(6.6, 2.2), sharey=True, gridspec_kw={"wspace": 0.12})
gx = np.linspace(-4, 4, 241)
panels = (("X_1", "(a) standard, one-sided"), ("X_0", "(b) standard, balanced"), ("X_rand", "(c) random sign"))
for ax, (col, title) in zip(axs, panels):
    h = hist[hist.col == col]
    mid, w = (h.bin_lo + h.bin_hi) / 2, h.bin_hi - h.bin_lo
    # density as numpy.histogram(density=True), drawn as a line through the bin centres
    ax.plot(mid, h.n_all / h.n_all.sum() / w, color=INK2, lw=1.0, label="all runs")
    ax.plot(mid, h.n_fail / h.n_fail.sum() / w, color=FAIL, lw=1.2, label="failed runs")
    ax.plot(gx, [phi(v) for v in gx], color="k", lw=0.8, ls="--", label=r"$N(0,1)$")
    ax.set_xlim(-4, 4); ax.set_ylim(0, 0.52)
    ax.set_xlabel(r"$X$")
    s = stats.loc[col]
    ax.text(0.03, 0.95, r"$\mathbb{E}[X\mid F]$" + f" = {s.mean_fail:+.3f}\nKS(failed, all) = {s.ks_fail_all:.3f}",
            transform=ax.transAxes, va="top", fontsize=6.5)
    ax.set_title(title, fontsize=8)
    print(col, f"mean|F={s.mean_fail:+.4f} se={s.se_fail:.4f} var|F={s.var_fail:.4f} KS(failed,all)={s.ks_fail_all:.4f}")
axs[0].set_ylabel("density")
h, l = axs[2].get_legend_handles_labels()
fig.legend(h, l, loc="lower center", ncol=3, bbox_to_anchor=(0.5, -0.2), handletextpad=0.3)
for ext in ("pdf", "png"):
    fig.savefig(os.path.join(HERE, "fig-encoding." + ext), bbox_inches="tight", **({"dpi": 200} if ext == "png" else {}))
s = stats.iloc[0]
print(f"runs={int(s.runs)} pF={s.n_fail / s.runs:.4f}")

"""Failure-conditional relative bias of the standard IBLT estimate against (b/d)^2, M = 16384; (a) k = 3, (b) k = 6.

Data: sim/results/tail/calib.csv, run round1_AB (k = 3) and round2_k56 (k = 6), var neg0..neg0.5 (d_-/d in {0, 0.1, 0.25, 0.4, 0.5}),
five loads with failure probability 0.10..0.90; all compositions share one batch of mappings.
mean_test is E[X | F] with X = (dhat - d)/s(d); relative bias = mean_test * s(d)/d.
Legend: failure probability (k = 3 and k = 6 differ by at most 0.01 at each level). Markers: measured. Lines: eq:projection with c_F taken from the one-sided point.
uv run --with numpy,pandas,matplotlib python fig-bias.py  ->  fig-bias.{pdf,png}
"""
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "manuscript", "STD", "figure"))
from figstyle import plt  # noqa: E402

M = 16384
calib = pd.read_csv(os.path.join(ROOT, "sim", "results", "tail", "calib.csv"))
COLS = ["#D55E00", "#E69F00", "#009E73", "#0072B2", "#56B4E9"]
xs = np.linspace(0, 1, 101)
fig, axs = plt.subplots(1, 2, figsize=(6.6, 2.4), gridspec_kw={"wspace": 0.3})
for ax, K, run, tag in ((axs[0], 3, "round1_AB", "(a)"), (axs[1], 6, "round2_k56", "(b)")):
    df = calib[(calib.run == run) & (calib.M == M) & (calib.k == K) & calib["var"].str.startswith("neg")].copy()
    df["q"] = df["var"].str[3:].astype(float)
    df["r2"] = (1 - 2 * df.q) ** 2
    s_over_d = np.sqrt(2 * (df.d - 1) / (df.d * (M - 1)))
    df["rel"] = 100 * df.mean_test * s_over_d
    df["rel_se"] = 100 * df.se_test * s_over_d
    for col, (pF, g) in zip(COLS, sorted(df.groupby("p_test"), key=lambda t: t[0])):
        g = g.sort_values("r2")
        d = g.d.iloc[0]
        one = g[g.q == 0].iloc[0]
        cF = (one.mean_test * np.sqrt(2 * (d - 1) / (d * (M - 1)))) / (d - 1)
        ax.plot(xs, 100 * cF * (d * xs - 1), color=col, lw=0.9)
        ax.errorbar(g.r2, g.rel, yerr=2 * g.rel_se, fmt="o", ms=3.2, color=col, elinewidth=0.6, capsize=0,
                    label=f"{pF:.2f}")
        pred = 100 * cF * (g.r2 * d - 1)
        print(f"k={K} pF={pF:.3f} d={d} cF={cF:.3e} max|obs-pred|/2se={np.max(np.abs(g.rel - pred) / (2 * g.rel_se)):.2f}")
    ax.axhline(0, color="k", lw=0.5)
    ax.set_xlim(-0.03, 1.03)
    ax.set_xlabel(r"$(b/d)^2$")
    ax.set_title(rf"{tag} $k={K}$", fontsize=8)
axs[0].set_ylabel(r"$\mathbb{E}[\widehat d\mid F]/d-1$ (%)")
_, l = axs[0].get_legend_handles_labels()
h = [plt.Line2D([], [], color=c, lw=0.9, marker="o", ms=3.2) for c in COLS]
fig.legend(h, l, loc="lower center", ncol=5, title="failure probability", title_fontsize=7, bbox_to_anchor=(0.5, -0.27), handletextpad=0.2, columnspacing=0.9, fontsize=7)
for ext in ("pdf", "png"):
    fig.savefig(os.path.join(HERE, "fig-bias." + ext), bbox_inches="tight", **({"dpi": 200} if ext == "png" else {}))

"""Conditional miss/u of the Skellam rule and the Gaussian rule against c = d/sqrt(M), C1 configurations.

Data: sim/results/exp6-20261016/coverage.tsv, stages c1 and c1x (M in 256..16384, k = 3, 4, 5, load at most
3; about 2e4 failures per configuration). Top row: direct sampling (true failure law); bottom row: planted
sampling (law Q). Open circles: Skellam rule; open triangles: Gaussian rule. miss = 0 is drawn at the lower edge.
uv run --with numpy,pandas,matplotlib python fig-coverage.py  ->  fig-coverage.{pdf,png}
"""
import os
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "manuscript", "STD", "figure"))
from figstyle import plt  # noqa: E402

df = pd.read_csv(os.path.join(ROOT, "sim", "results", "exp6-20261016", "coverage.tsv"), sep="\t")
df = df[df.stage.isin(["c1", "c1x"]) & (df.M >= 256)]
RAW, RCHI = "#0072B2", "#D55E00"
LOW = 0.02
fig, axs = plt.subplots(2, 2, figsize=(6.6, 4.2), sharex=True, sharey=True, gridspec_kw={"wspace": 0.08, "hspace": 0.12})
for row, (kind, name) in enumerate((("direct", "direct sampling"), ("plant", "planted sampling"))):
    for ax, u in zip(axs[row], (0.01, 0.05)):
        for rule, col, mk in (("Skellam", RAW, "o"), ("Gaussian", RCHI, "^")):
            g = df[(df.rule == rule) & (df.u == u) & (df.kind == kind)]
            ax.scatter(g.c, g.miss_u.clip(lower=LOW), s=10, marker=mk, lw=0.6, facecolors="none", edgecolors=col,
                       label=f"{rule} rule")
            print(kind, u, rule, "configs", g.id.nunique(), "max", g.miss_u.max())
        ax.axhline(1, color="k", lw=0.6, ls="--")
        ax.set_xscale("log"); ax.set_yscale("log")
        ax.set_xlim(0.007, 400); ax.set_ylim(LOW * 0.8, 80)
        if row == 0:
            ax.set_title(rf"$u={u}$", fontsize=8)
        else:
            ax.set_xlabel(r"$c=d/\sqrt{M}$")
    axs[row, 0].set_ylabel(f"{name}\nmiss / $u$")
h, l = axs[0, 0].get_legend_handles_labels()
fig.legend(h, l, loc="lower center", ncol=2, bbox_to_anchor=(0.5, -0.04), handletextpad=0.2, columnspacing=1.2, fontsize=7)
for ext in ("pdf", "png"):
    fig.savefig(os.path.join(HERE, "fig-coverage." + ext), bbox_inches="tight", **({"dpi": 200} if ext == "png" else {}))

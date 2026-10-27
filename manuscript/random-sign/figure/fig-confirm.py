"""Skellam rule miss/u on the 12 large-sample confirmation configurations, with two-sided 95% Clopper-Pearson
intervals. The one-sided simultaneous upper bounds of the pre-specified test (ucb_u, level 0.05/24 each) are
listed in the appendix table tab:confirm and printed below.

Data: sim/results/exp6-20261016/c2.tsv (rule = Skellam). Configurations sorted by load d/(alpha_c M).
uv run --with pandas,scipy,matplotlib python fig-confirm.py  ->  fig-confirm.{pdf,png}
"""
import os
import sys

import pandas as pd
from scipy.stats import beta

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "manuscript", "STD", "figure"))
from figstyle import INK2, plt  # noqa: E402

ALPHA = {3: 0.818469160761, 4: 0.772279839803, 5: 0.701780266485}  # sim/exp6/grid.py
df = pd.read_csv(os.path.join(ROOT, "sim", "results", "exp6-20261016", "c2.tsv"), sep="\t")
df = df[df.rule == "Skellam"].copy()
df[["k", "M", "d"]] = df.id.str.extract(r"k(\d+)-M(\d+)-d(\d+)").astype(int)
df["lo_u"] = beta.ppf(0.025, df.miss, df.n_fail - df.miss + 1) / df.u
df["hi_u"] = beta.ppf(0.975, df.miss + 1, df.n_fail - df.miss) / df.u
df["load"] = df.d / (df.k.map(ALPHA) * df.M)
order = df.drop_duplicates("id").sort_values(["load", "M"]).id.tolist()[::-1]
ypos = {cid: i for i, cid in enumerate(order)}

fig, axs = plt.subplots(1, 2, figsize=(6.6, 2.7), sharey=True, gridspec_kw={"wspace": 0.06})
for ax, u in zip(axs, (0.01, 0.05)):
    g = df[df.u == u]
    y = g.id.map(ypos)
    ax.errorbar(g.miss_u, y, xerr=[g.miss_u - g.lo_u, g.hi_u - g.miss_u], fmt="o", color="#0072B2", ms=3.5,
                lw=1.2, capsize=2.5, capthick=1.0)
    ax.axvline(1, color=INK2, lw=0.7, ls="--", zorder=0)
    ax.set_xlim(0.45, 1.1)
    ax.set_xlabel("miss/u")
    ax.set_title(rf"$u={u}$", fontsize=8)
    ax.grid(axis="y", color="0.92", lw=0.5)
first = df.drop_duplicates("id").set_index("id")
labels = [f"$k={r.k}$, $M={r.M}$, $d={r.d}$  ({r.load:.2f})" for r in first.loc[order].itertuples()]
axs[0].set_yticks(range(len(order)))
axs[0].set_yticklabels(labels)
axs[0].tick_params(axis="y", length=0)
for ext in ("pdf", "png"):
    fig.savefig(os.path.join(HERE, "fig-confirm." + ext), bbox_inches="tight", **({"dpi": 200} if ext == "png" else {}))
print(df[["id", "u", "miss_u", "lo_u", "hi_u", "ucb_u"]].round(3).to_string(index=False))

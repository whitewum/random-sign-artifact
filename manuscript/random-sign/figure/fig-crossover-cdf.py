"""Lower tail of X = (d̂-d)/s(d) after failure at d ~ sqrt(M): empirical CDF vs the discrete law vs N(0,1).

Data: sim/results/rand-cross2/data/exp4_summary.json (conv_plant, k=3, M=16384, c=1,2,4; 4e5 planted
failures each, 0.001-resolution histogram of d̂-d). The discrete law is the compound Poisson candidate of
sim/peelsim/exp4_report.py (cp_law, zero fit).
uv run --with numpy,scipy,pandas,matplotlib python fig-crossover-cdf.py  ->  fig-crossover-cdf.{pdf,png}
"""
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "manuscript", "STD", "figure"))
sys.path.insert(0, os.path.join(ROOT, "sim", "peelsim"))
from figstyle import INK2, Phi, plt  # noqa: E402
from exp4_report import cp_law, emp  # noqa: E402

K, M = 3, 16384
summ = json.load(open(os.path.join(ROOT, "sim", "results", "rand-cross2", "data", "exp4_summary.json")))
cfg = {int(c["meta"]["d"]): c for c in summ["runs"]["conv_plant"] if int(c["meta"]["M"]) == M}
fig, axs = plt.subplots(1, 3, figsize=(6.6, 2.2), sharey=True, gridspec_kw={"wspace": 0.12})
gx = np.linspace(-4.5, 1, 400)
for ax, c in zip(axs, (1, 2, 4)):
    d = round(c * math.sqrt(M))
    g = cfg[d]["groups"]["failed"]
    s = math.sqrt(2 * d * (d - 1) / (M - 1))
    xe, pe = emp(g)
    xc, pc = cp_law(K, M, d)
    ax.step(xe / s, np.cumsum(pe), where="post", color="#D55E00", lw=1.3, label="failed runs")
    ax.step(xc / s, np.cumsum(pc), where="post", color="k", lw=0.8, label="discrete law")
    ax.plot(gx, [Phi(v) for v in gx], color=INK2, lw=0.8, ls="--", label=r"$N(0,1)$")
    ax.set_yscale("log"); ax.set_ylim(1e-3, 0.6); ax.set_xlim(-4.5, 1)
    ax.axhline(0.01, color="0.8", lw=0.5, zorder=0); ax.axhline(0.05, color="0.8", lw=0.5, zorder=0)
    ax.set_xlabel(r"$X$")
    ax.set_title(rf"$c={c}$, $d={d}$", fontsize=8)
    print(c, d, g["n"])
axs[0].set_ylabel(r"$\Pr(X\leq x\mid F)$")
h, l = axs[0].get_legend_handles_labels()
fig.legend(h, l, loc="lower center", ncol=3, bbox_to_anchor=(0.5, -0.2), handletextpad=0.3)
for ext in ("pdf", "png"):
    fig.savefig(os.path.join(HERE, "fig-crossover-cdf." + ext), bbox_inches="tight", **({"dpi": 200} if ext == "png" else {}))

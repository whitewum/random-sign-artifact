"""Failure-conditional (tilde d-d)/s(d) from exact S2 records versus the manuscript G_d.
Source: sim/results/distribution-fix-20261022/crossover_hist.json, exported by limit_ks.py.
Distances include both sides of every atom. No overlap or finite-size correction in G_d.
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
from distribution import gd_lattice, discrete_ks, continuous_ks  # noqa: E402

K, M = 3, 16384
CS = (0.25, 0.5, 1, 2, 4, 8)
cfg = {r["d"]: r for r in json.load(open(os.path.join(ROOT, "sim", "results", "distribution-fix-20261022", "crossover_hist.json")))}
fig, axs = plt.subplots(2, 3, figsize=(6.6, 4.0), sharex=True, sharey=True, gridspec_kw={"wspace": 0.12, "hspace": 0.38})
gx = np.linspace(-6.5, 1, 400)
for ax, c in zip(axs.flat, CS):
    d = round(c * math.sqrt(M))
    g = cfg[d]
    s = math.sqrt(2 * d * (d - 1) / (M - 1))
    lattice = np.array(g["lattice"], dtype=np.int64)
    pe = np.array(g["counts"], dtype=float) / g["n"]
    law_lattice, pc = gd_lattice(K, M, d)
    xe, xc = lattice * (2 / K), law_lattice * (2 / K)
    Fc = np.cumsum(pc)
    ks_cp = discrete_ks(lattice, pe, law_lattice, pc)
    ks_g = continuous_ks(xe, pe, lambda x: np.array([Phi(v / s) for v in x]))
    ax.step(xe / s, np.cumsum(pe), where="post", color="#D55E00", lw=1.3, label="failed runs")
    ax.step(xc / s, Fc, where="post", color="k", lw=0.8, label="discrete law")
    ax.plot(gx, [Phi(v) for v in gx], color=INK2, lw=0.8, ls="--", label=r"$N(0,1)$")
    ax.set_yscale("log"); ax.set_ylim(1e-3, 0.6); ax.set_xlim(-6.5, 1)
    ax.axhline(0.01, color="0.8", lw=0.5, zorder=0); ax.axhline(0.05, color="0.8", lw=0.5, zorder=0)
    ax.set_title(rf"$c={c:g}$, $d={d}$", fontsize=8, pad=13)
    ax.text(0.5, 1.02, f"KS: law {ks_cp:.3f}, $N(0,1)$ {ks_g:.3f}", transform=ax.transAxes,
            ha="center", va="bottom", fontsize=6.5, color="0.3")
    print(c, d, g["n"], round(ks_cp, 4), round(ks_g, 4))
for ax in axs[1]:
    ax.set_xlabel(r"$(\widetilde d-d)/s(d)$")
for ax in axs[:, 0]:
    ax.set_ylabel("Conditional CDF")
h, l = axs[0, 0].get_legend_handles_labels()
fig.legend(h, l, loc="lower center", ncol=3, bbox_to_anchor=(0.5, -0.06), handletextpad=0.3)
for ext in ("pdf", "png"):
    fig.savefig(os.path.join(HERE, "fig-crossover-cdf." + ext), bbox_inches="tight", **({"dpi": 200} if ext == "png" else {}))

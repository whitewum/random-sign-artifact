"""Null distribution of Section 5 at three values of c = d/sqrt(M): pmf of (1/k) sum_v C_v^2 - d vs the Gaussian.

Pure formula, no data. Limit law of the crossover theorem: 2 e1 e2 + (2/k)[Pois(lam) - Pois(lam)], lam = k^2 c^2/4,
k = 3. Bars are stacked by the sign product of the duplicate pair (-2 and +2 components, mass 1/2 each). The
dashed curve is the Gaussian with variance 2c^2 (the Gaussian rule's s(d)^2), scaled by the lattice step 2/k.
uv run --with numpy,scipy,matplotlib python fig-aux.py  ->  fig-aux.{pdf,png}
"""
import csv
import json
import math
import os
import sys

import numpy as np
from scipy.stats import skellam

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "manuscript", "STD", "figure"))
from figstyle import INK2, plt  # noqa: E402

PARAM = json.load(open(os.path.join(ROOT, 'sim/results/analytic/aux-parameters.json')))
K = PARAM['k']
OUT = os.path.join(ROOT, 'outputs/figures')
os.makedirs(OUT, exist_ok=True)
points = []
STEP = 2 / K
NEG, POS = "#0072B2", "#E69F00"
fig, axs = plt.subplots(1, 3, figsize=(6.6, 2.1), gridspec_kw={"wspace": 0.22})
for ax, c, xl in zip(axs, PARAM['c'], PARAM['x_limits']):
    lam = K * K * c * c / 4
    j = np.arange(-int(xl / STEP) - 8, int(xl / STEP) + 9)
    pz = skellam.pmf(j, lam, lam) if lam > 0 else (j == 0).astype(float)
    x = j * STEP  # Skellam part on the lattice (2/k)Z
    # The two components share the lattice because 2 = 3 * (2/k) for k = 3.
    grid = np.arange(-int(xl / STEP) - 4, int(xl / STEP) + 5)
    neg = np.array([0.5 * pz[j == g + 3].sum() for g in grid])
    pos = np.array([0.5 * pz[j == g - 3].sum() for g in grid])
    gx = grid * STEP
    points.extend((c, xx, nn, pp) for xx, nn, pp in zip(gx, neg, pos))
    w = STEP * 0.8
    ax.bar(gx, neg, width=w, color=NEG, lw=0, label=r"$\varepsilon_1\varepsilon_2=-1$")
    ax.bar(gx, pos, width=w, bottom=neg, color=POS, lw=0, label=r"$\varepsilon_1\varepsilon_2=+1$")
    s = math.sqrt(2) * c
    xs = np.linspace(-xl, xl, 600)
    ax.plot(xs, STEP * np.exp(-xs ** 2 / (2 * s * s)) / (s * math.sqrt(2 * math.pi)), color=INK2, ls="--", lw=0.8,
            label="Gaussian")
    ax.set_xlim(-xl, xl)
    ax.set_xlabel(r"$\widetilde{d}-d$")
    ax.set_title(rf"$c={c}$", fontsize=8)
    print(c, lam, "mass", (neg + pos).sum())
axs[0].set_ylim(0, 0.7)
axs[0].set_ylabel("probability")
h, l = axs[0].get_legend_handles_labels()
fig.legend(h, l, loc="lower center", ncol=3, bbox_to_anchor=(0.5, -0.2), handletextpad=0.3)
for ext in ("pdf", "png"):
    fig.savefig(os.path.join(HERE, "fig-aux." + ext), bbox_inches="tight", **({"dpi": 200} if ext == "png" else {}))

with open(os.path.join(OUT, 'fig-aux.tsv'), 'w') as f:
    writer = csv.writer(f, delimiter='\t', lineterminator='\n')
    writer.writerow(['c', 'tilde_d_minus_d', 'negative_mass', 'positive_mass'])
    writer.writerows(points)

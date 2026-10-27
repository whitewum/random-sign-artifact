"""Shared English-language figure style for this artifact."""
import math
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
RES = os.path.join(ROOT, "sim", "results")
sys.path.insert(0, os.path.join(ROOT, "theory", "scripts"))
sys.path.insert(0, os.path.join(ROOT, "sim", "runs"))


plt.rcParams.update({"font.family": "serif", "font.size": 8, "axes.labelsize": 8, "legend.fontsize": 7,
                     "xtick.labelsize": 7, "ytick.labelsize": 7, "lines.linewidth": 1.0, "lines.markersize": 3.5,
                     "axes.spines.top": False, "axes.spines.right": False, "legend.frameon": False,
                     "mathtext.fontset": "cm"})

KC = {3: "#0072B2", 4: "#009E73", 5: "#D55E00", 6: "#CC79A7"}
MC = {1024: "#56B4E9", 4096: "#009E73", 16384: "#E69F00", 32768: "#CC79A7", 65536: "#D55E00"}
INK2 = "#555555"


def save(fig, name):
    fig.savefig(os.path.join(HERE, name + ".pdf"), bbox_inches="tight")
    fig.savefig(os.path.join(HERE, name + ".png"), dpi=200, bbox_inches="tight")
    plt.close(fig)


def Phi(z):
    return 0.5 * math.erfc(-z / math.sqrt(2))


def phi(z):
    return math.exp(-z * z / 2) / math.sqrt(2 * math.pi)


def mills(z):
    """A(z) = phi(z)/Phi(z), stable for very negative z."""
    if z > -30:
        return phi(z) / Phi(z)
    t = -z
    return t / (1 - 1 / t ** 2 + 3 / t ** 4)


def log_comb(n, r):
    return math.lgamma(n + 1) - math.lgamma(r + 1) - math.lgamma(n - r + 1)

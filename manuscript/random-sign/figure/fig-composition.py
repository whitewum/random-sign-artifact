"""Mean of X after failure against the sign composition d_-/d, standard and random-sign encoding (tab:mean-by-k).

Data: sim/results/rs-columns-20261018/{k3,k4,k56}.json (M = 16384, failure probability about 0.1; same
mappings for all ten columns of a configuration). Columns X_neg<r> are the standard encoding, X_rs<r> the
random-sign encoding. Error bars: two standard errors.
uv run --with matplotlib python fig-composition.py  ->  fig-composition.{pdf,png}
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "manuscript", "STD", "figure"))
from figstyle import KC, plt  # noqa: E402

RES = os.path.join(ROOT, "sim", "results", "rs-columns-20261018")
RATIOS = ("0", "0.1", "0.25", "0.4", "0.5")
CFG = ((3, "k3.json", 0), (4, "k4.json", 0), (5, "k56.json", 0), (6, "k56.json", 1))

data = {}
for k, f, i in CFG:
    cols = {c["name"]: c for c in json.load(open(os.path.join(RES, f)))[i]["cols"]}
    data[k] = {enc: [(float(r), cols[f"X_{p}{r}"]["mean_F"], cols[f"X_{p}{r}"]["se_F"]) for r in RATIOS]
               for enc, p in (("std", "neg"), ("rs", "rs"))}

fig, axs = plt.subplots(1, 2, figsize=(6.6, 2.4), gridspec_kw={"wspace": 0.3, "width_ratios": [1.15, 1]})
for k in (3, 4, 5, 6):
    x, m, s = zip(*data[k]["std"])
    axs[0].plot(x, m, "-o", color=KC[k], ms=3.5, label=rf"$k={k}$")
    x, m, s = zip(*data[k]["rs"])
    axs[0].plot(x, m, "--", color=KC[k], lw=0.8, marker="o", mfc="white", ms=3.5)
    dx = (k - 4.5) * 0.008
    axs[1].errorbar([v + dx for v in x], m, yerr=[2 * v for v in s], fmt="o", color=KC[k], mfc="white",
                    ms=3.5, elinewidth=0.6, capsize=1.5, ecolor=KC[k], alpha=0.9)
    print(k, "std", [f"{v:+.3f}" for _, v, _ in data[k]["std"]],
          "rs max|mean|", f"{max(abs(v) for v in m):.4f}", "max|mean|/se", f"{max(abs(a) / b for a, b in zip(m, s)):.2f}")
axs[0].axhline(0, color="k", lw=0.5)
axs[0].set_ylim(-0.5, 0.75)
axs[0].set_title("(a) both encodings", fontsize=8)
axs[0].set_ylabel(r"$\mathbb{E}[X\mid F]$")
axs[1].axhline(0, color="k", lw=0.5)
axs[1].set_ylim(-0.015, 0.015)
axs[1].set_title("(b) random sign, zoomed, $\\pm2$ s.e.", fontsize=8)
for ax in axs:
    ax.set_xticks([0, 0.1, 0.25, 0.4, 0.5])
    ax.set_xticklabels(["0", "0.1", "0.25", "0.4", "0.5"])
    ax.set_xlabel(r"$d_-/d$")
# colour encodes k only (patches, no line style); line style encodes the encoding, shown only in panel (a)
from matplotlib.patches import Patch  # noqa: E402
fig.legend([Patch(color=KC[k]) for k in (3, 4, 5, 6)], [rf"$k={k}$" for k in (3, 4, 5, 6)],
           loc="lower center", ncol=4, bbox_to_anchor=(0.5, -0.13), handlelength=1.0, columnspacing=1.5)
axs[0].legend([plt.Line2D([], [], color="0.3", marker="o", ms=3.5),
               plt.Line2D([], [], color="0.3", ls="--", lw=0.8, marker="o", mfc="white", ms=3.5)],
              ["standard", "random sign"], loc="upper right", fontsize=7, frameon=False)
for ext in ("pdf", "png"):
    fig.savefig(os.path.join(HERE, "fig-composition." + ext), bbox_inches="tight", **({"dpi": 200} if ext == "png" else {}))

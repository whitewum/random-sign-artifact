"""Skellam rule sizing time against c, timing batch T of the §6 campaign.

Data: sim/results/exp6-20261016/T/sizing.json and sizing-c1x.json (M = 16384, k = 3, 4, 5, u = 0.01, one
pinned core at 2.0 GHz, first 200 failures per configuration, 10 repetitions, cache capacity 16M entries).
Each point is the median over repetitions of the mean time per sizing. (a) cold: a fresh table cache per
sizing; (b) session: one cache over consecutive observations (solid) and warm, the same observation
sized again (dashed). Configurations with c < 4 take under 10 microseconds and are omitted.
uv run --with pandas,matplotlib python fig-sizing.py  ->  fig-sizing.{pdf,png}
"""
import json
import os
import statistics as st
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "manuscript", "STD", "figure"))
from figstyle import plt  # noqa: E402
from matplotlib.ticker import NullFormatter  # noqa: E402

T = os.path.join(ROOT, "sim", "results", "exp6-20261016", "T")
rows = []
for fn in ("sizing.json", "sizing-c1x.json"):
    for outs in json.load(open(os.path.join(T, fn)))["runs"].values():
        for o in outs:
            m, t = o["meta"], o["timing"]
            med = lambda mode: st.median(r[mode]["mean"] for r in t["reps"]) * 1e3
            rows.append(dict(k=int(m["k"]), c=int(m["d"]) / 128, cold=med("raw_cold"), session=med("raw_session"),
                             warm=med("raw_warm")))
KC = {3: "#0072B2", 4: "#009E73", 5: "#D55E00"}
KM = {3: "o", 4: "s", 5: "^"}
fig, axes = plt.subplots(1, 2, figsize=(6.6, 2.65), sharex=True, sharey=True)
fig.subplots_adjust(left=0.09, right=0.985, bottom=0.22, top=0.76, wspace=0.17)
for k in (3, 4, 5):
    g = sorted((r for r in rows if r["k"] == k and r["c"] >= 4), key=lambda r: r["c"])
    c = [r["c"] for r in g]
    axes[0].plot(c, [r["cold"] for r in g], marker=KM[k], color=KC[k], ms=3, markerfacecolor="white",
                 markeredgewidth=0.8, label=f"$k={k}$")
    axes[1].plot(c, [r["session"] for r in g], marker=KM[k], color=KC[k], ms=3, markerfacecolor="white",
                 markeredgewidth=0.8)
    axes[1].plot(c, [r["warm"] for r in g], color=KC[k], lw=0.8, ls="--")
    print(k, [(round(r["c"], 1), round(r["cold"], 3), round(r["session"], 3)) for r in g])
for ax, title in zip(axes, ("(a) cold: empty cache", "(b) session (solid) and warm (dashed)")):
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.xaxis.set_minor_formatter(NullFormatter())
    ax.set_xticks([4, 10, 30, 100, 300]); ax.set_xticklabels(["4", "10", "30", "100", "300"])
    ax.set_xlabel(r"$c=d/\sqrt{M}$")
    ax.set_title(title, fontsize=8, pad=7)
axes[0].set_ylabel("sizing time (ms)")
h, l = axes[0].get_legend_handles_labels()
fig.legend(h, l, ncol=3, loc="upper center", bbox_to_anchor=(0.54, 1.01), fontsize=7, handlelength=1.6, columnspacing=1.5)
for ext in ("pdf", "png"):
    fig.savefig(os.path.join(HERE, "fig-sizing." + ext), bbox_inches="tight", **({"dpi": 220} if ext == "png" else {}))
plt.close(fig)

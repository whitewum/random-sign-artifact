"""Rejected +-1 candidates per decoding against the sign composition d_-/d, standard and random-sign encoding.

Data: sim/results/decode-reject-20261021/{node1,node2,gateway}.jsonl (M = 16384, 50000 audited paired trials per
configuration; both encodings decode the same mapping). A rejected candidate is a pop of a cell with count +-1 whose
checksum or cell-membership check fails. The y axis divides the rejections per decoding by d.
uv run --with matplotlib python fig-decode.py  ->  fig-decode.{pdf,png}
"""
import json
import math
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "manuscript", "STD", "figure"))
from figstyle import KC, plt  # noqa: E402

RES = os.path.join(ROOT, "sim", "results", "decode-reject-20261021")
KS = (3, 4, 5, 6)
LOADS = (1.0, 0.5)

agg = defaultdict(lambda: defaultdict(float))
seen = {}
for node in ("node1", "node2", "gateway"):
    for line in open(os.path.join(RES, node + ".jsonl")):
        r = json.loads(line)
        # node2 ran its shard twice by accident; trials are deterministic, so duplicates must agree
        key = json.dumps({k: v for k, v in r.items() if k != "seconds"}, sort_keys=True)
        if r["task"] in seen:
            assert seen[r["task"]] == key
            continue
        seen[r["task"]] = key
        c = r["config"]
        a = agg[(c["K"], c["Load"], c["Fraction"])]
        a["d"] = c["D"]
        a["n"] += r["trials"]
        a["succ"] += r["success"]
        for enc in ("standard", "signed"):
            for f in ("Rej", "Rej2", "MemRej", "Fake", "Accepted", "Cand"):
                a[enc + f] += r[enc][f]


def point(a, enc):
    n, d = a["n"], a["d"]
    m = a[enc + "Rej"] / n
    se = math.sqrt(max(a[enc + "Rej2"] / n - m * m, 0) / n)
    return m / d, se / d


assert len(seen) == 1350, len(seen)
print("k load d-/d trials fail standard/d signed/d memRej")
for key in sorted(agg):
    a = agg[key]
    print(*key, int(a["n"]), f"{1 - a['succ'] / a['n']:.4f}",
          "%.4f %.4f" % (point(a, "standard")[0], point(a, "signed")[0]), int(a["standardMemRej"] + a["signedMemRej"]))

fig, axs = plt.subplots(1, 2, figsize=(6.6, 2.4), gridspec_kw={"wspace": 0.3})
for ax, load in zip(axs, LOADS):
    for k in KS:
        xs = sorted(f for kk, ll, f in agg if kk == k and ll == load and f <= 0.5)
        for enc, style in (("standard", dict(ls="-", ms=3.5)),
                           ("signed", dict(ls="--", lw=0.8, mfc="white", ms=3.5))):
            ys = [point(agg[(k, load, f)], enc)[0] for f in xs]
            ax.plot(xs, ys, marker="o", color=KC[k], **style)
    ax.set_xticks([0, 0.125, 0.25, 0.375, 0.5])
    ax.set_xticklabels(["0", "0.125", "0.25", "0.375", "0.5"])
    ax.set_xlabel(r"$d_-/d$")
    ax.set_ylim(bottom=0)
    ax.set_title(f"({'ab'[LOADS.index(load)]}) load {load:g}", fontsize=8)
axs[0].set_ylabel("rejected candidates / $d$")
from matplotlib.patches import Patch  # noqa: E402
fig.legend([Patch(color=KC[k]) for k in KS], [rf"$k={k}$" for k in KS],
           loc="lower center", ncol=4, bbox_to_anchor=(0.5, -0.13), handlelength=1.0, columnspacing=1.5)
axs[0].legend([plt.Line2D([], [], color="0.3", marker="o", ms=3.5),
               plt.Line2D([], [], color="0.3", ls="--", lw=0.8, marker="o", mfc="white", ms=3.5)],
              ["standard", "random sign"], loc="lower right", fontsize=7, frameon=False)
for ext in ("pdf", "png"):
    fig.savefig(os.path.join(HERE, "fig-decode." + ext), bbox_inches="tight", **({"dpi": 200} if ext == "png" else {}))

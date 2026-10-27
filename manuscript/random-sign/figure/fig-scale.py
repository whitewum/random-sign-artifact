"""Protocol scale at fixed load 1.5, balanced differences, u=0.01.

Run: python3 manuscript/random-sign/figure/fig-scale.py
One column per k. Top: conditional miss rate / u after a first-round failure, pooled per (k, M1, d) over
every first-round failure of that configuration: the protocol experiment (protocol.tsv, 20000), the
statistical experiment C1 (coverage.tsv, 20000) and the direct large-sample runs C2, c2x, c2s (about
2.9e5). The three estimate the same quantity: common elements cancel in the difference table, the sign
composition does not matter under random signs, and raw_b equals raw when |b| = ||A|-|B|| <= 1
(balanced). Bars: 95% normal-approximation intervals of the pooled rate.
Bottom: total bytes relative to the oracle arm (protocol experiment only).
"""
import csv
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "manuscript/STD/figure"))
from figstyle import plt

RES = ROOT / "sim/results/exp6-20261016"
U = .01


def tsv(name):
    with (RES / name).open() as f:
        return list(csv.DictReader(f, delimiter="\t"))


rows = [r for r in tsv("protocol.tsv") if float(r["u"]) == U
        and abs(float(r["load"]) - 1.5) <= .005 and r["onesided"] == "0"]
index = {(r["id"], r["arm"]): r for r in rows}
assert len(index) == len(rows), "Duplicate configuration/arm"
sizes = [256, 1024, 4096, 16384]
ks = [3, 4, 5]
ARMS = [("signed_raw_b", "Skellam rule", "Skellam", "#0072B2", "o", "-", .96),
        ("signed_rchi_b", "Gaussian rule", "Gaussian", "#D55E00", "s", "--", 1.04)]

# Pooled first-round failures: (config id without the -bal suffix, rule) -> {source: (failures, misses)}
pool = {}
for r in rows:
    for arm, _, rule, *_ in ARMS:
        if r["arm"] == arm:
            f1 = int(r["f1"])
            pool.setdefault((r["id"].removesuffix("-bal"), rule), {})["protocol"] = (f1, round(float(r["cond_miss"]) * f1))
cids = {cid for cid, _ in pool}
for r in tsv("coverage.tsv"):
    if r["stage"] == "c1" and r["id"] in cids and float(r["u"]) == U:
        pool[(r["id"], r["rule"])]["c1"] = (int(r["n_fail"]), int(r["miss"]))
for name in ("c2", "c2x", "c2s"):
    for r in tsv(f"{name}.tsv"):
        if r["id"] in cids and float(r["u"]) == U:
            pool[(r["id"], r["rule"])][name] = (int(r["n_fail"]), int(r["miss"]))
for key, src in pool.items():
    assert {"protocol", "c1"} <= set(src) and len(src) == 3, (key, sorted(src))

fig, axs = plt.subplots(2, 3, figsize=(7.2, 4.3), sharex=True, sharey="row",
                        gridspec_kw={"wspace": .08, "hspace": .12})
export = []
for arm, name, rule, color, marker, style, shift in ARMS:
    for col, k in enumerate(ks):
        miss, err, overhead = [], [], []
        for m in sizes:
            (r,) = [r for r in rows if int(r["M1"]) == m and int(r["k"]) == k and r["arm"] == arm]
            oracle = index[(r["id"], "signed_oracle")]
            src = pool[(r["id"].removesuffix("-bal"), rule)]
            n = sum(v[0] for v in src.values())
            p = sum(v[1] for v in src.values()) / n
            miss.append(p / U)
            err.append(1.96 * (p * (1 - p) / n) ** .5 / U)
            overhead.append(100 * (float(r["mean_bytes"]) / float(oracle["mean_bytes"]) - 1))
            export.append(dict(id=r["id"], rule=name, k=k, M1=m, d=r["d"], load=r["load"], u=U, failures=n,
                               sources="+".join(f"{s}:{v[0]}" for s, v in src.items()),
                               miss_u=miss[-1], miss_u_ci95=err[-1], byte_overhead_pct=overhead[-1]))
        axs[0, col].errorbar([m * shift for m in sizes], miss, yerr=err, color=color, marker=marker, ls=style,
                             capsize=0, elinewidth=.8, mfc="white" if style == "--" else color, label=name, zorder=3)
        axs[1, col].plot(sizes, overhead, color=color, marker=marker, ls=style,
                         mfc="white" if style == "--" else color, zorder=3)
        print(name, f"k={k}", "miss/u:", [round(v, 3) for v in miss], "+-", [round(v, 3) for v in err],
              "overhead %:", [round(v, 2) for v in overhead])

for col, k in enumerate(ks):
    axs[0, col].set_title(f"$k={k}$")
    axs[0, col].axhline(1, color=".35", ls=":", lw=.8)
    axs[1, col].axhline(0, color=".35", ls=":", lw=.8)
    axs[1, col].set_xlabel("First-round table size $M_1$")
axs[0, 0].set_ylim(.5, 1.3)
axs[0, 0].set_ylabel("Conditional miss rate / $u$")
axs[1, 0].set_ylim(0, 20)
axs[1, 0].set_ylabel("Extra total bytes vs. oracle (%)")
for ax in axs.flat:
    ax.set_xscale("log", base=4)
    ax.set_xticks(sizes, ["256", "1K", "4K", "16K"])
    ax.set_xlim(190, 22000)
    ax.grid(axis="y", color=".92", linewidth=.5)
handles, labels = axs[0, 0].get_legend_handles_labels()
fig.legend(handles, labels, ncol=2, loc="lower center", bbox_to_anchor=(.5, -.05))
for ext in ("pdf", "png"):
    fig.savefig(HERE / f"fig-scale.{ext}", bbox_inches="tight", dpi=240)
with (HERE / "fig-scale.csv").open("w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=list(export[0]))
    writer.writeheader()
    writer.writerows(export)

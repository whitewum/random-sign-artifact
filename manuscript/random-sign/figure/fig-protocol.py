"""Two-round protocol on a real IBLT against the first-round table length M1 (tab:e2e).

Data: sim/results/exp6-20261016/protocol.tsv (120 configurations: k = 3, 4, 5, five first-round loads,
one-sided and balanced; 13.94 million trials per u). (a) Second-round table length after a first-round failure,
relative to the oracle that knows d, one point per configuration with first-round failures; dotted line:
slope -1/2 through the M1 = 16384 median. (b) Two-round final failure rate per configuration, u = 0.01;
zero is drawn at the lower edge.
uv run --with matplotlib python fig-protocol.py  ->  fig-protocol.{pdf,png}
"""
import csv
import os
import statistics as st
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "manuscript", "STD", "figure"))
from figstyle import plt  # noqa: E402

rows = list(csv.DictReader(open(os.path.join(ROOT, "sim", "results", "exp6-20261016", "protocol.tsv")),
                           delimiter="\t"))
idx = {(r["id"], r["u"], r["arm"]): r for r in rows}
MS = (256, 1024, 4096, 16384)
RAW, RCHI, ORA = "#0072B2", "#D55E00", "#555555"
ARMS = (("signed_raw_b", "Skellam rule", RAW), ("signed_rchi_b", "Gaussian rule", RCHI))


def sel(u, M, arm):
    return [r for r in rows if r["u"] == u and r["M1"] == str(M) and r["arm"] == arm]


def m2_ratio(r, u):
    o = idx[(r["id"], u, "signed_oracle")]
    return float(r["mean_M2_f1"]) / float(o["mean_M2_f1"]) - 1


fig, axs = plt.subplots(1, 2, figsize=(6.6, 2.5), gridspec_kw={"wspace": 0.3})
ax = axs[0]
for u, mk in (("0.01", "o"), ("0.05", "s")):
    for j, (arm, name, col) in enumerate(ARMS):
        med = []
        for M in MS:
            v = [m2_ratio(r, u) for r in sel(u, M, arm) if int(r["f1"]) > 0]
            x = M * (1.06 if j else 1 / 1.06)
            ax.scatter([x] * len(v), [100 * a for a in v], s=6, marker=mk, color=col, alpha=0.35, lw=0)
            med.append(100 * st.median(v))
            print(u, name, M, f"n={len(v)} median={med[-1]:.2f}% range={100 * min(v):.2f}..{100 * max(v):.2f}%")
        ax.plot([M * (1.06 if j else 1 / 1.06) for M in MS], med, "-" if u == "0.01" else "--", color=col, lw=0.9,
                marker=mk, ms=3, mfc="white", label=f"{name}, $u={u}$")
    if u == "0.01":
        ref = st.median([m2_ratio(r, u) for r in sel(u, 16384, "signed_raw_b") if int(r["f1"]) > 0])
        ax.plot(MS, [100 * ref * (16384 / M) ** 0.5 for M in MS], ":", color="k", lw=0.8, label=r"$\propto M_1^{-1/2}$")
ax.set_xscale("log", base=2); ax.set_yscale("log")
ax.set_xticks(MS); ax.set_xticklabels([str(M) for M in MS])
ax.set_yticks([1, 2, 5, 10, 20, 40]); ax.set_yticklabels(["1%", "2%", "5%", "10%", "20%", "40%"])
ax.set_xlabel(r"$M_1$")
ax.set_ylabel("second-round size vs. oracle")
ax.set_title("(a) extra second-round capacity", fontsize=8)
ax.legend(loc="upper right", fontsize=6.5)

ax = axs[1]
LOW = 5e-6
for j, (arm, name, col) in enumerate((("signed_raw_b", "Skellam rule", RAW), ("signed_oracle", "oracle", ORA))):
    mx = []
    for M in MS:
        v = [float(r["final_fail"]) for r in sel("0.01", M, arm)]
        x = M * (1.06 if j == 0 else 1 / 1.06)
        ax.scatter([x] * len(v), [max(a, LOW) for a in v], s=8, marker="o", color=col, alpha=0.45, lw=0)
        mx.append(max(v))
    ax.plot([M * (1.06 if j == 0 else 1 / 1.06) for M in MS], mx, "-", color=col, lw=0.9, label=f"{name}, max")
ax.set_xscale("log", base=2); ax.set_yscale("log")
ax.set_xticks(MS); ax.set_xticklabels([str(M) for M in MS])
ax.set_ylim(LOW * 0.7, 1e-2)
ax.set_yticks([LOW, 1e-4, 1e-3, 1e-2]); ax.set_yticklabels(["0", r"$10^{-4}$", r"$10^{-3}$", r"$10^{-2}$"])
ax.axhline(LOW * 2.2, color="#cccccc", lw=0.5)
ax.set_xlabel(r"$M_1$")
ax.set_ylabel("final failure rate")
ax.set_title("(b) two-round failure, $u=0.01$", fontsize=8)
ax.legend(loc="upper right", fontsize=6.5)

for ext in ("pdf", "png"):
    fig.savefig(os.path.join(HERE, "fig-protocol." + ext), bbox_inches="tight", **({"dpi": 200} if ext == "png" else {}))
n = sum(int(r["trials"]) for r in rows if r["u"] == "0.01" and r["arm"] == "signed_oracle")
f1 = sum(int(r["f1"]) for r in rows if r["u"] == "0.01" and r["arm"] == "signed_oracle")
print(f"trials per u = {n}, first-round failures = {f1}")

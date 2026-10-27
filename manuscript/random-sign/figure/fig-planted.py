"""Direct vs planted sampling: Skellam rule miss/u difference and full-range KS distance of X, per configuration.

Data: sim/results/exp6-20261016/coverage.tsv (stage v, 21 configurations near critical load, ~6.5e4 failures
per side); and the
low-load comparison ana/v2/{v2,v2_tail}.tsv for k = 3 (direct 6.5e4) and ana/v3/{v3a,v3bc}*.tsv for k = 4, 5
(fresh direct samples: v3a 6.5e4, v3bc = v3b + v3c pooled, ~2e4; the v2s direct pilot of ~2000 is not used). Planted 6.5e4.
Left: difference (direct minus planted) with 95% Wald interval, shaded band = equivalence bound +-0.1.
Right: full-range two-sample KS distance of X from ana/fullks.tsv (sim/exp6/ana/fullks); a grey bar marks the
asymptotic 95% critical value 1.358 sqrt(1/n1 + 1/n2) at that sample size.
uv run --with numpy,pandas,matplotlib python fig-planted.py  ->  fig-planted.{pdf,png}
"""
import math
import os
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "manuscript", "STD", "figure"))
from figstyle import plt  # noqa: E402

RES = os.path.join(ROOT, "sim", "results", "exp6-20261016")
U_COL = {0.01: "#0072B2", 0.05: "#D55E00"}
XLIM = 0.45

# --- 21 configurations near critical load ---
cov = pd.read_csv(os.path.join(RES, "coverage.tsv"), sep="\t")
cov = cov[(cov.stage == "v") & (cov.rule == "Skellam")]
ks = pd.read_csv(os.path.join(RES, "ana", "fullks.tsv"), sep="\t").set_index("id")
rows = []
for cid, g in cov.groupby("id"):
    dr = g[g.kind == "direct"].set_index("u")
    pl = g[g.kind == "plant"].set_index("u")
    r = dict(id=cid, k=int(dr.k.iloc[0]), M=int(dr.M.iloc[0]), load=float(dr.load.iloc[0]), gap=ks.ks_full[cid],
             crit=ks.ks_crit95[cid],
             group=f"$M={int(dr.M.iloc[0])}$")
    for u in (0.01, 0.05):
        p1, n1 = dr.miss[u] / dr.n_fail[u], dr.n_fail[u]
        p2, n2 = pl.miss[u] / pl.n_fail[u], pl.n_fail[u]
        se = math.sqrt(p1 * (1 - p1) / n1 + p2 * (1 - p2) / n2) / u
        r[u] = (dr.miss_u[u] - pl.miss_u[u], 1.96 * se, 1.96 * se)
    rows.append(r)
crit = pd.DataFrame(rows)

# --- 12 low-load planted configurations ---
LOW = [("v2", "v2"), ("v3", "v3a"), ("v3", "v3bc")]
v2 = pd.concat([pd.read_csv(os.path.join(RES, "ana", d, f + ".tsv"), sep="\t") for d, f in LOW])
t2 = pd.concat([pd.read_csv(os.path.join(RES, "ana", d, f + "_tail.tsv"), sep="\t") for d, f in LOW])
t2 = t2.set_index("id")
rows = []
for cid, g in v2.groupby("id"):
    k, M, d = (int(s[1:]) for s in cid.split("-"))
    g = g.set_index("u")
    r = dict(id=cid, k=k, M=M, load=None, gap=ks.ks_full[cid], crit=ks.ks_crit95[cid], group="low load", d=d,
             n=t2.n_direct[cid])
    for u in (0.01, 0.05):
        r[u] = (g["diff"][u], g["diff"][u] - g.diff_lo[u], g.diff_hi[u] - g["diff"][u])
    rows.append(r)
low = pd.DataFrame(rows)
low_load = {  # first-round load d/(alpha_c M), as in tab:v-low
    "k3-M1024-d32": 0.04, "k3-M4096-d512": 0.15, "k3-M4096-d1024": 0.31, "k3-M16384-d8192": 0.61,
    "k4-M256-d8": 0.04, "k4-M256-d16": 0.08, "k4-M1024-d128": 0.16, "k4-M1024-d256": 0.32,
    "k4-M1024-d512": 0.65, "k5-M256-d32": 0.18, "k5-M256-d64": 0.36, "k5-M256-d128": 0.71}
low["load"] = low.id.map(low_load)

groups = [(crit[crit.M == M].sort_values(["k", "load"]), f"$M={M}$") for M in (64, 256, 1024)]
groups.append((low.sort_values(["k", "load"]), "low load"))

# --- layout: rows top to bottom, a gap between groups ---
ys, labels, recs, heads = [], [], [], []
y = 0.0
for df, name in groups:
    heads.append((y, name))
    y -= 1.0
    for _, r in df.iterrows():
        lab = f"$k={r.k}$, {r.load:.2f}" if name != "low load" else f"$k={r.k}$, $M={r.M}$, {r.load:.2f}"
        ys.append(y); labels.append(lab); recs.append(r)
        y -= 1.0
    y -= 0.4

fig, (axl, axr) = plt.subplots(1, 2, figsize=(6.6, 4.8), sharey=True,
                               gridspec_kw={"width_ratios": [1.7, 1], "wspace": 0.06})
axl.axvspan(-0.1, 0.1, color="0.9", lw=0, zorder=0)
axl.axvline(0, color="k", lw=0.6, zorder=1)
for yy, r in zip(ys, recs):
    for u, off in ((0.01, 0.17), (0.05, -0.17)):
        m, lo, hi = r[u]
        a, b = max(m - lo, -XLIM), min(m + hi, XLIM)
        axl.plot([a, b], [yy + off] * 2, color=U_COL[u], lw=0.9, solid_capstyle="butt")
        axl.plot(m, yy + off, "o", color=U_COL[u], ms=2.6)
        for edge, clipped in ((a, m - lo < -XLIM), (b, m + hi > XLIM)):
            if clipped:
                axl.plot(edge, yy + off, marker="<" if edge < 0 else ">", color=U_COL[u], ms=2.6)
    axr.plot(r.gap, yy, "o", color="0.25", ms=2.6)
    axr.plot([r.crit, r.crit], [yy - 0.3, yy + 0.3], color="0.6", lw=1.0)  # 95% two-sample KS critical value

for ax in (axl, axr):
    for yh, name in heads[1:]:
        ax.axhline(yh + 0.7, color="0.75", lw=0.5)
for yh, name in heads:
    axl.text(-XLIM + 0.01, yh, name, ha="left", va="center", fontsize=7.5)
axl.set_yticks(ys); axl.set_yticklabels(labels)
axl.tick_params(axis="y", length=0)
axl.set_ylim(min(ys) - 0.8, heads[0][0] + 0.8)
axl.set_xlim(-XLIM, XLIM)
axl.set_xticks([-0.4, -0.2, 0, 0.2, 0.4])
axl.set_xlabel("miss/$u$, direct $-$ planted")
axr.set_xlim(0, 0.016)
axr.set_xlabel("KS distance of $X$")
axr.tick_params(axis="y", length=0)
for u in (0.01, 0.05):
    axl.plot([], [], "o-", color=U_COL[u], ms=2.6, lw=0.9, label=f"$u={u}$")
axl.legend(loc="lower center", ncol=2, bbox_to_anchor=(0.5, 1.0), handletextpad=0.3)

for ext in ("pdf", "png"):
    fig.savefig(os.path.join(HERE, "fig-planted." + ext), bbox_inches="tight", **({"dpi": 200} if ext == "png" else {}))

# cross-check against the appendix tables
for yy, r, lab in zip(ys, recs, labels):
    print(f"{r.group:10s} {lab:28s} u.01 {r[0.01][0]:+.2f}  u.05 {r[0.05][0]:+.2f}±{r[0.05][1]:.2f}  gap {r.gap:.4f}")

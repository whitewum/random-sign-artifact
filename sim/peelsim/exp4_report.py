"""E3 follow-up: crossover convergence (fixed c = d/sqrt(M), growing M) and fixed small d.

usage: uv run --with numpy,scipy,pandas python exp4_report.py SUMMARY.json OUTDIR

SUMMARY.json is crossextract output (with dhat_dev_hist). For every configuration and group (failed),
compares the empirical law of d̂-d with two zero-fit candidates:
  cp   compound Poisson: d̂-d ≈ [pair term + (2/k) sum of N1 signs + (4/k) 1{same signs} sum of N2 signs] / (1-k/M),
       the planted pair adds +2 (same signs) or -2 (opposite signs), each with probability 1/2,
       N1 ~ Poi(C(d-2,2) k^2/M) single-cell overlaps among the other edges,
       N2 ~ Poi((d-2) k^2/M) overlaps between another edge and the pair;
  tpn  two-point + normal (the mix rule's model): (Phi((x+2)/s) + Phi((x-2)/s))/2, s = s(d).
Reports midpoint distances (not KS), the largest atoms, 1%/5% quantiles of X = (d̂-d)/s(d), and rule miss/u.
"""
import json
import math
import os
import sys

import numpy as np
import pandas as pd
from scipy.stats import norm, skellam

US = {"01": 0.01, "05": 0.05}


def cp_law(k, M, d, nmax=None):
    """Historical finite-size candidate, distinct from the manuscript G_d."""
    l1 = math.comb(max(d - 2, 0), 2) * k * k / M
    l2 = max(d - 2, 0) * k * k / M
    scale = 1 / (1 - k / M)
    # lattice in units of 2/k; a Poisson number of independent +-1 signs is a symmetric Skellam variable
    def signed_sum_pmf(lam, step):
        h = lam / 2
        r = int(h + 12 * math.sqrt(h) + 20) if lam > 0 else 0
        js = np.arange(-r, r + 1)
        p = skellam.pmf(js, h, h) if lam > 0 else (js == 0).astype(float)
        return {int(step * j): float(q) for j, q in zip(js, p) if q > 1e-15}
    s1 = signed_sum_pmf(l1, 1)       # units of 2/k
    s2 = signed_sum_pmf(l2, 2)       # units of 2/k (each jump 4/k)
    out = {}
    # same signs (prob 1/2): shift +2 (= k units) and pair overlaps jump +-4/k; opposite signs: shift -2, no pair jumps
    for a, pa, with_pair in ((k, 0.5, True), (-k, 0.5, False)):
        for v1, p1 in s1.items():
            if not with_pair:
                out[a + v1] = out.get(a + v1, 0) + pa * p1
                continue
            for v2, p2 in s2.items():
                out[a + v1 + v2] = out.get(a + v1 + v2, 0) + pa * p1 * p2
    xs = np.array(sorted(out)) * (2 / k) * scale
    ps = np.array([out[v] for v in sorted(out)])
    return xs, ps


def emp(g):
    h = g["dhat_dev_hist"]
    xs = np.array(sorted(int(a) for a in h)) / 1000.0
    ps = np.array([h[str(int(round(x * 1000)))] for x in xs], float)
    return xs, ps / ps.sum()


def midpoint_distance(xe, pe, cdf_fn, step):
    """Sup distance between CDFs at lattice midpoints (spacing step), robust to the O(d/M) atom offsets."""
    grid = np.arange(math.floor(xe.min() / step) - 1, math.ceil(xe.max() / step) + 2) * step + step / 2
    Fe = np.cumsum(pe)
    Fg = np.array([Fe[i - 1] if i > 0 else 0.0 for i in np.searchsorted(xe, grid, side="right")])
    return float(np.max(np.abs(Fg - cdf_fn(grid))))


def quant(xs, ps, p):
    return xs[int(np.searchsorted(np.cumsum(ps), p))]


def rows(summ):
    for run, cfgs in summ["runs"].items():
        for c in cfgs:
            m, G = c["meta"], c["groups"]
            k, M, d = int(m["k"]), int(m["M"]), int(m["d"])
            g = G["failed"]
            if g["n"] < 200:
                continue
            sdd = math.sqrt(2 * d * (d - 1) / (M - 1))
            xe, pe = emp(g)
            if math.comb(max(d - 2, 0), 2) * k * k / M > 3000:
                continue
            xc, pc = cp_law(k, M, d)
            Fc = np.cumsum(pc)
            def cdf_cp(x, xc=xc, Fc=Fc):
                i = np.searchsorted(xc, np.atleast_1d(x), side="right")
                return np.where(i > 0, Fc[np.maximum(i - 1, 0)], 0.0)
            cdf_tpn = lambda x: (norm.cdf((x + 2) / sdd) + norm.cdf((x - 2) / sdd)) / 2  # noqa: E731
            top = np.argsort(pe)[::-1][:3]
            r = dict(run=run, k=k, M=M, d=d, c=d / math.sqrt(M), n=g["n"], pair=G["failed_pair"]["n"] / g["n"],
                     midpoint_cp=midpoint_distance(xe, pe, cdf_cp, 2 / k / (1 - k / M)), midpoint_tpn=midpoint_distance(xe, pe, cdf_tpn, 2 / k / (1 - k / M)),
                     atoms=";".join(f"{xe[i]:.2f}:{pe[i]:.3f}" for i in top))
            for tag, u in US.items():
                r[f"q{tag}_emp"] = quant(xe, pe, u) / sdd
                r[f"q{tag}_cp"] = quant(xc, pc, u) / sdd
                tq = np.linspace(-12 * sdd - 4, 4, 20001)
                r[f"q{tag}_tpn"] = tq[np.searchsorted(cdf_tpn(tq), u)] / sdd
                for rule in ("rchi", "mix", "cp"):
                    r[f"{rule}{tag}"] = g["miss"].get(rule + tag, 0) / g["n"] / u
                r[f"max{tag}"] = g["miss"].get("max" + tag, 0) / g["n"] / u
                r[f"empty_rchi{tag}"] = g["empty"].get("rchi" + tag, 0) / g["n"]
            r["miss_raw"] = g["miss"].get("raw", 0) / g["n"]
            yield r


def main(path, outdir):
    df = pd.DataFrame(list(rows(json.load(open(path))))).sort_values(["run", "k", "c", "M", "d"])
    os.makedirs(outdir, exist_ok=True)
    df.to_csv(os.path.join(outdir, "exp4.csv"), index=False)
    pd.set_option("display.width", 260)
    pd.set_option("display.max_rows", 500)
    f = lambda v: f"{v:.3g}"  # noqa: E731
    cols = ["k", "M", "d", "c", "n", "pair", "midpoint_cp", "midpoint_tpn", "q01_emp", "q01_cp", "q01_tpn", "q05_emp", "q05_cp",
            "q05_tpn", "rchi01", "mix01", "mix05", "cp01", "cp05", "max01", "miss_raw", "empty_rchi01", "atoms"]
    with open(os.path.join(outdir, "report.txt"), "w") as fo:
        for run, sub in df.groupby("run"):
            fo.write(f"== {run}\n" + sub[cols].to_string(index=False, float_format=f) + "\n\n")
    print(open(os.path.join(outdir, "report.txt")).read())


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])

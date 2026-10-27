"""C1: distance from the failure-conditional law of d̂-d to its two limits (run on the server).

usage: python3 limit_ks.py ROOT OUTDIR

For every C1 / c1x configuration, all blocks of out/{c1,c1x}/c1-<kind>-k<k>-M<M>-d<d>-b*/s/cfg_000/chunk_*.bin
are pooled (failed records only). With d̂ = (S2 - S1^2/M) / (k (1 - k/M)) and s(d) = sqrt(2 d (d-1) / (M-1)):

  ks_gauss   sup |F_n - Phi(./s(d))|, theorem clt
  ks_cross   sup |F_n - G|, G the compound Poisson law of theorem cross (cp_law below); only where the
             Poisson mean of the Skellam term is at most 3000, i.e. c bounded
  dq*_gauss, dq*_cross   empirical minus limit quantile at 1% and 5%, in units of s(d)

Both distances are taken at lattice midpoints (spacing 2/(k(1-k/M))), as in sim/peelsim/exp4_report.ks,
so the O(d/M) offset of the atoms does not enter.

limit_ks.tsv  one row per configuration.
"""
import glob
import json
import math
import os
import re
import sys

import numpy as np
from scipy.stats import norm, skellam

QS = (0.01, 0.05)


def cp_law(k, M, d):
    """Support and probabilities of d̂-d under the theorem cross law; copy of sim/peelsim/exp4_report.cp_law."""
    l1 = math.comb(max(d - 2, 0), 2) * k * k / M
    l2 = max(d - 2, 0) * k * k / M
    scale = 1 / (1 - k / M)

    def signed_sum_pmf(lam, step):
        h = lam / 2
        r = int(h + 12 * math.sqrt(h) + 20) if lam > 0 else 0
        js = np.arange(-r, r + 1)
        p = skellam.pmf(js, h, h) if lam > 0 else (js == 0).astype(float)
        return {int(step * j): float(q) for j, q in zip(js, p) if q > 1e-15}

    s1 = signed_sum_pmf(l1, 1)
    s2 = signed_sum_pmf(l2, 2)
    out = {}
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


def read(run):
    man = json.load(open(os.path.join(run, "s", "manifest.json")))
    names = man["fields"]
    nf = man["record_bytes"] // 4
    parts = [np.fromfile(p, dtype="<u4").reshape(-1, nf)
             for p in sorted(glob.glob(os.path.join(run, "s", "cfg_000", "chunk_*.bin")))]
    a = np.concatenate(parts)
    col = lambda n: a[:, names.index(n)].view("<i4").astype(np.int64)  # noqa: E731
    fail = col("failed") == 1
    return col("S1_rand")[fail], col("S2_rand")[fail]


def ks(xe, pe, cdf, step):
    grid = np.arange(math.floor(xe.min() / step) - 1, math.ceil(xe.max() / step) + 2) * step + step / 2
    Fe = np.concatenate([[0.0], np.cumsum(pe)])
    return float(np.max(np.abs(Fe[np.searchsorted(xe, grid, side="right")] - cdf(grid))))


def quant(xs, ps, p):
    return xs[min(int(np.searchsorted(np.cumsum(ps), p)), len(xs) - 1)]


def main(root, out):
    os.makedirs(out, exist_ok=True)
    runs = {}
    for r in glob.glob(os.path.join(root, "out", "c1", "c1-*")) + glob.glob(os.path.join(root, "out", "c1x", "c1*-*")):
        m = re.search(r"-(direct|plant)-k(\d+)-M(\d+)-d(\d+)-b\d+$", r)
        if m:
            runs.setdefault((m[1], int(m[2]), int(m[3]), int(m[4])), []).append(r)
    f = open(os.path.join(out, "limit_ks.tsv"), "w")
    f.write("kind\tk\tM\td\tc\tload_d_over_M\tn\tks_gauss\tks_cross\t"
            + "\t".join(f"dq{q:g}_{t}" for t in ("gauss", "cross") for q in QS) + "\n")
    for (kind, k, M, d), rs in sorted(runs.items(), key=lambda x: (x[0][1], x[0][2], x[0][3], x[0][0])):
        S1, S2 = map(np.concatenate, zip(*[read(r) for r in sorted(rs)]))
        if len(S1) < 1000:
            continue
        # M (S2 - d k) - S1^2 is an exact integer; d̂-d is it over k(M-k).
        num = M * (S2 - d * k) - S1 * S1 + d * k * k
        vals, cnt = np.unique(num, return_counts=True)
        xe = vals / (k * (M - k))
        pe = cnt / cnt.sum()
        s = math.sqrt(2 * d * (d - 1) / (M - 1))
        step = 2 / (k * (1 - k / M))
        row = [kind, k, M, d, f"{d / math.sqrt(M):.3f}", f"{d / M:.4f}", len(S1)]
        row.append(f"{ks(xe, pe, lambda x: norm.cdf(x / s), step):.4f}")
        cross = math.comb(max(d - 2, 0), 2) * k * k / M <= 3000
        if cross:
            xc, pc = cp_law(k, M, d)
            Fc = np.concatenate([[0.0], np.cumsum(pc)])
            row.append(f"{ks(xe, pe, lambda x: Fc[np.searchsorted(xc, x, side='right')], step):.4f}")
        else:
            row.append("")
        row += [f"{(quant(xe, pe, q) - s * norm.ppf(q)) / s:+.4f}" for q in QS]
        row += [f"{(quant(xe, pe, q) - quant(xc, pc, q)) / s:+.4f}" if cross else "" for q in QS]
        f.write("\t".join(map(str, row)) + "\n")
        f.flush()
    f.close()


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])

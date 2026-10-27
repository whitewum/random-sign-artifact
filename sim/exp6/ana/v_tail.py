"""V: lower tail of the failure-conditional measurement, direct against planted (run on the server).

usage: python3 v_tail.py ROOT OUTDIR

For every V configuration both samples are read from out/v/*/s/cfg_000/chunk_*.bin (failed records
only). The statistic is the standardized random-sign estimate X = (dhat - d) / s(d), with
dhat = (S2 - S1^2/M) / (k (1 - k/M)) and s(d) = sqrt(2 d (d-1) / (M-1)).

tail.tsv  per configuration and sample: failures, pure-pair share, quantiles of X at 0.5, 1, 2, 5, 10 %.
cdf.tsv   per configuration: on a grid of X spanning the pooled 0.2-15 % range, the two empirical CDFs,
          their difference with a 95% normal interval; and the largest |difference| over the grid.
"""
import glob
import json
import math
import os
import sys

import numpy as np

QS = (0.005, 0.01, 0.02, 0.05, 0.10)


def read(run):
    man = json.load(open(os.path.join(run, "s", "manifest.json")))
    c = man["configs"][0]
    names = man["fields"]
    nf = man["record_bytes"] // 4
    parts = [np.fromfile(p, dtype="<u4").reshape(-1, nf) for p in sorted(glob.glob(os.path.join(run, "s", "cfg_000", "chunk_*.bin")))]
    a = np.concatenate(parts)
    col = lambda n: a[:, names.index(n)].view("<i4").astype(np.int64)
    fail = col("failed") == 1
    S1, S2, core = col("S1_rand")[fail], col("S2_rand")[fail], col("core_edges")[fail]
    M, k, d = c["M"], c["k"], c["d"]
    dhat = (S2 - S1.astype(float) ** 2 / M) / (k * (1 - k / M))
    X = (dhat - d) / math.sqrt(2 * d * (d - 1) / (M - 1))
    return X, (core == 2), (M, k, d)


def main(root, out):
    os.makedirs(out, exist_ok=True)
    runs = {}
    for r in glob.glob(os.path.join(root, "out", "v", "v-*")):
        kind, rest = os.path.basename(r)[2:].split("-", 1)
        cid = rest.rsplit("-b", 1)[0]
        runs.setdefault(cid, {}).setdefault(kind, []).append(r)
    ft = open(os.path.join(out, "tail.tsv"), "w")
    fc = open(os.path.join(out, "cdf.tsv"), "w")
    ft.write("id\tkind\tn\tpair_share\t" + "\t".join(f"q{q:g}" for q in QS) + "\n")
    fc.write("id\tx\tF_direct\tF_plant\tdiff\tdiff_lo\tdiff_hi\n")
    summary = []
    for cid in sorted(runs):
        S = {}
        for kind in ("direct", "plant"):
            xs, ps = zip(*[read(r)[:2] for r in sorted(runs[cid][kind])])
            X, P = np.concatenate(xs), np.concatenate(ps)
            S[kind] = np.sort(X)
            ft.write(f"{cid}\t{kind}\t{len(X)}\t{P.mean():.4f}\t" + "\t".join(f"{np.quantile(X, q):.4f}" for q in QS) + "\n")
        pooled = np.concatenate([S["direct"], S["plant"]])
        lo, hi = np.quantile(pooled, 0.002), np.quantile(pooled, 0.15)
        grid = np.unique(pooled[(pooled >= lo) & (pooled <= hi)])
        if len(grid) > 400:
            grid = np.quantile(grid, np.linspace(0, 1, 400))
        worst = 0.0
        for x in grid:
            fd = np.searchsorted(S["direct"], x, side="right") / len(S["direct"])
            fp = np.searchsorted(S["plant"], x, side="right") / len(S["plant"])
            se = math.sqrt(fd * (1 - fd) / len(S["direct"]) + fp * (1 - fp) / len(S["plant"]))
            fc.write(f"{cid}\t{x:.5f}\t{fd:.5f}\t{fp:.5f}\t{fd - fp:+.5f}\t{fd - fp - 1.96 * se:+.5f}\t{fd - fp + 1.96 * se:+.5f}\n")
            worst = max(worst, abs(fd - fp))
        summary.append((cid, worst))
    ft.close()
    fc.close()
    for cid, w in summary:
        print(f"{cid}\tmax|dF| on lower 15% = {w:.4f}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])

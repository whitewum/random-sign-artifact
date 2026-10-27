"""A: failure-conditional moments of the three encodings on the C1 samples (run on the server).

usage: python3 a_moments.py ROOT OUT.tsv

C1 records hold, on one mapping, X for the standard encoding with a one-sided difference (X_neg0), with a
balanced difference (X_neg0.5) and for random signs (X_rand). Per C1 configuration (direct and planted
blocks pooled per kind): failures, and for each encoding the mean of X over failures with its standard
error and the variance.
"""
import glob
import json
import os
import sys
from collections import defaultdict

import numpy as np


def main(root, out):
    acc = defaultdict(list)
    for run in glob.glob(os.path.join(root, "out", "c1*", "c1*-*")):
        name = os.path.basename(run)
        stage, kind, rest = name.split("-", 2)
        cid = rest.rsplit("-b", 1)[0]
        man = json.load(open(os.path.join(run, "s", "manifest.json")))
        f = man["fields"]
        nf = man["record_bytes"] // 4
        for p in glob.glob(os.path.join(run, "s", "cfg_000", "chunk_*.bin")):
            a = np.fromfile(p, dtype="<u4").reshape(-1, nf)
            fail = a[:, f.index("failed")] == 1
            xs = [a[fail, f.index(c)].view("<f4").astype(float) for c in ("X_neg0", "X_neg0.5", "X_rand")]
            acc[(stage, kind, cid)].append(np.stack(xs, 1))
    with open(out, "w") as fo:
        fo.write("stage\tkind\tid\tn\t" + "\t".join(f"{e}_{s}" for e in ("one", "bal", "rand") for s in ("mean", "se", "var")) + "\n")
        for key in sorted(acc):
            X = np.concatenate(acc[key])
            n = len(X)
            vals = []
            for j in range(3):
                m, v = X[:, j].mean(), X[:, j].var(ddof=1)
                vals += [f"{m:.5f}", f"{np.sqrt(v / n):.5f}", f"{v:.5f}"]
            fo.write("\t".join(list(key) + [str(n)] + vals) + "\n")
    print(len(acc), "configurations")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])

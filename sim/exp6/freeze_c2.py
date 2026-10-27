"""Freeze C2 from the design table (c2_design.py).

usage: python3 freeze_c2.py RESULTS_DIR > frozen/c2.json

Every C2 point is sampled directly with seeds of stage "c2" (disjoint from exploration, pilot, C1, V).
Stop rule: blocks are counted in block order; the analysis uses every failure of the blocks up to and
including the first block at which the cumulative failure count reaches n_fail. The rule looks at
failure counts only. The run enqueues ceil(1.15 n_fail / pF) trials; if the realized count falls short,
further blocks with the next block numbers are added under the same rule.
Judgments: Skellam rule, u in {0.01, 0.05}, one-sided Clopper-Pearson upper bound at level 0.05/24 of the
conditional miss must not exceed 1.1 u.
"""
import csv
import glob
import json
import math
import os
import sys

import grid

BLOCK_S = 600.0
SLOW = 1.5
MARGIN = 1.15
PF_EST = {"k3-M1024-d192": 1.0e-4, "k4-M16384-d16384": 1.0}  # not in C1; see c2_design.COST_NOTE


def main(root):
    rows = list(csv.DictReader(open(os.path.join(root, "c2_design.tsv")), delimiter="\t"))
    out = {"rules": __doc__, "points": [], "tasks": []}
    for r in rows:
        cid = r["id"]
        k, M, d = (int(t[1:]) for t in cid.split("-"))
        trials = failed = 0
        for dd in glob.glob(os.path.join(root, "c1", f"c1-direct-{cid}-b*")):
            c = json.load(open(os.path.join(dd, "s", "manifest.json")))["configs"][0]
            trials, failed = trials + c["trials"], failed + c["failed"]
        pf = failed / trials if trials else PF_EST.get(cid)
        if pf is None:  # planted in C1: direct pF from the pilot
            pf = float(next(p for p in csv.DictReader(open(os.path.join(root, "pilot.tsv")), delimiter="\t")
                            if p["id"] == cid)["pF"])
        n = int(r["n_fail"])
        spf = float(r["s_per_fail"])
        total = math.ceil(MARGIN * n / pf)
        per = max(1000, int(BLOCK_S / SLOW / (spf * pf)))
        nb = math.ceil(total / per)
        per = math.ceil(total / nb)
        out["points"].append(dict(id=cid, k=k, M=M, d=d, n_fail=n, pF=pf, trials=total, blocks=nb))
        row = dict(id=cid, k=k, M=M, d=d, c=d / math.sqrt(M), load=grid.load(k, M, d))
        for b in range(nb):
            out["tasks"].append(dict(stage="c2", kind="direct", **row, block=b, trials=min(per, total - b * per), plant=False))
    json.dump(out, sys.stdout, indent=1)


if __name__ == "__main__":
    main(sys.argv[1])

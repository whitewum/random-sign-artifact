"""V2 / V2S: low-load direct against planted (run on the server).

usage: python3 v2_report.py ROOT OUTDIR [STAGE]      STAGE = v2 (k = 3, default) or v2s (k = 4, 5)

Pools the blocks of out/STAGE/STAGE-<kind>-<config>-b*/ per configuration and sample. Skellam rule misses come
from replay.json (failed group); the miss/u difference (direct minus planted) gets a 95% normal interval
and the TOST of the V design (margin 0.1, per-side level 0.05 / #configs) at u = 0.05. The lower-tail
CDF comparison of X follows v_tail.py (pooled 0.2-15 % range).

STAGE.tsv   one row per configuration and u.
STAGE_tail.tsv   per configuration: failures, pure-pair share and max |F_direct - F_plant| on the lower tail.
"""
import glob
import json
import math
import os
import sys
from statistics import NormalDist

import numpy as np

from v_tail import read

US = {"raw01": 0.01, "raw05": 0.05}


def main(root, out, stage="v2"):
    os.makedirs(out, exist_ok=True)
    runs = {}
    for r in glob.glob(os.path.join(root, "out", stage, stage + "-*")):
        kind, rest = os.path.basename(r)[len(stage) + 1:].split("-", 1)
        runs.setdefault(rest.rsplit("-b", 1)[0], {}).setdefault(kind, []).append(r)
    m = len(runs)
    z = NormalDist().inv_cdf(1 - 0.05 / m)
    fv = open(os.path.join(out, stage + ".tsv"), "w")
    fv.write("id\tu\tn_direct\tn_plant\tmissu_direct\tmissu_plant\tdiff\tdiff_lo\tdiff_hi\ttost\n")
    ft = open(os.path.join(out, stage + "_tail.tsv"), "w")
    ft.write("id\tn_direct\tn_plant\tpair_direct\tpair_plant\tmax_dF\n")
    for cid in sorted(runs):
        miss, n, X, P = {}, {}, {}, {}
        for kind in ("direct", "plant"):
            miss[kind] = {key: 0 for key in US}
            n[kind] = 0
            for r in runs[cid][kind]:
                runs_json = json.load(open(os.path.join(r, "replay.json")))["runs"]
                (only,) = runs_json.values()  # keyed by the sampler output path since r22replay runKey
                g = only[0]["groups"]["failed"]
                n[kind] += g["n"]
                for key in US:
                    miss[kind][key] += g["miss"].get(key, 0)
            xs, ps = zip(*[read(r)[:2] for r in sorted(runs[cid][kind])])
            X[kind], P[kind] = np.sort(np.concatenate(xs)), np.concatenate(ps)
        for key, u in US.items():
            p = {kd: miss[kd][key] / n[kd] / u for kd in n}
            se = math.sqrt(sum(miss[kd][key] / n[kd] * (1 - miss[kd][key] / n[kd]) / n[kd] for kd in n)) / u
            diff = p["direct"] - p["plant"]
            tost = "pass" if (diff - z * se > -0.1 and diff + z * se < 0.1) else "fail"
            fv.write(f"{cid}\t{u}\t{n['direct']}\t{n['plant']}\t{p['direct']:.3f}\t{p['plant']:.3f}\t{diff:+.3f}"
                     f"\t{diff - 1.96 * se:+.3f}\t{diff + 1.96 * se:+.3f}\t{tost if u == 0.05 else ''}\n")
        pooled = np.concatenate([X["direct"], X["plant"]])
        lo, hi = np.quantile(pooled, 0.002), np.quantile(pooled, 0.15)
        grid = np.unique(pooled[(pooled >= lo) & (pooled <= hi)])
        if len(grid) > 400:
            grid = np.quantile(grid, np.linspace(0, 1, 400))
        worst = max(abs(np.searchsorted(X["direct"], x, side="right") / len(X["direct"])
                        - np.searchsorted(X["plant"], x, side="right") / len(X["plant"])) for x in grid)
        ft.write(f"{cid}\t{len(X['direct'])}\t{len(X['plant'])}\t{P['direct'].mean():.4f}\t{P['plant'].mean():.4f}\t{worst:.4f}\n")
    fv.close()
    ft.close()


if __name__ == "__main__":
    main(*sys.argv[1:4])

"""Freeze the C1, M=64, V and P runs from the pilot (plan §5, §6).

usage: python3 freeze_main.py PILOT_TSV > frozen/main.json

Rules (fixed before any C1/V/P sample is drawn; all stop rules are fixed trial counts, so no stop
decision looks at the observed misses):
  C1 and M=64   target 2e4 failures. Direct sampling when the pilot projects at most H_DIRECT core-hours
                (trials = ceil(2e4 / pF_pilot)); otherwise planted sampling with 2e4 trials, reported as
                coverage under the planted law Q.
  V             configurations with direct pilot Pr(F) >= 1e-3; direct and planted, N_V failures each
                (direct trials = ceil(N_V / pF_pilot)). N_V from a TOST on the miss/u difference at
                u = 0.05 with margin 0.1, per-side level 0.05 / (#V), 80% power at zero difference.
  P             one fixed trial count per configuration shared by u = 0.01 and u = 0.05 (paired seeds):
                ceil(2e4 / pF1) when the pilot saw round-1 failures, capped at P_CAP; 1e5 trials when the
                pilot saw none (Pr(F1) bound and final failure rate only).
Tasks are cut into blocks of about BLOCK_S seconds of pilot-measured cost.
"""
import csv
import json
import math
import sys
from statistics import NormalDist

import grid

TARGET = 20_000
H_DIRECT = 20.0
P_CAP = 3_000_000
P_NOFAIL = 100_000
BLOCK_S = 600.0
SLOW = 1.5  # pilot ran on loaded hosts; leave headroom when cutting blocks


def v_failures(m):
    z = NormalDist().inv_cdf
    sigma2 = 2 * 0.95 / 0.05  # n Var of the miss/u difference, two independent samples, u = 0.05
    n = (z(1 - 0.05 / m) + z(0.9)) ** 2 * sigma2 / 0.1 ** 2  # z(0.9): beta/2 per side of the TOST
    return int(math.ceil(n / 1000.0) * 1000)


def blocks(trials, cost_per_trial):
    per = max(1, int(BLOCK_S / (SLOW * cost_per_trial)))
    nb = max(1, math.ceil(trials / per))
    per = math.ceil(trials / nb)
    return [min(per, trials - b * per) for b in range(nb)]


def main(path):
    rows = list(csv.DictReader(open(path), delimiter="\t"))
    f = lambda x: float(x) if x not in ("", "nan") else float("nan")
    smp = {r["id"]: r for r in rows if r["item"] in ("c1", "m64", "v")}
    out = {"rules": __doc__, "target": TARGET, "h_direct": H_DIRECT, "tasks": []}
    T = out["tasks"]

    def sampler(stage, kind, r, trials, cost):
        for b, n in enumerate(blocks(trials, cost)):
            T.append(dict(stage=stage, kind=kind, id=r["id"], k=r["k"], M=r["M"], d=r["d"], c=r["c"],
                          load=r["load"], block=b, trials=n, plant=kind == "plant"))

    for item, rows_ in (("c1", grid.c1()), ("m64", grid.m64())):
        for r in rows_:
            p = smp[r["id"]]
            pf, st, sr, sp = f(p["pF"]), f(p["s_trial"]), f(p["s_replay_fail"]), f(p["s_plant_fail"])
            if pf > 0 and f(p["h_direct"]) <= H_DIRECT:
                n = math.ceil(TARGET / pf)
                sampler(item, "direct", r, n, st + pf * (sr if math.isfinite(sr) else 0))
            else:
                sampler(item, "plant", r, TARGET, sp)
    vrows = [r for r in grid.v() if f(smp[r["id"]]["pF"]) >= 1e-3]
    nv = v_failures(len(vrows))
    out["v_failures"], out["v_configs"] = nv, [r["id"] for r in vrows]
    for r in vrows:
        p = smp[r["id"]]
        pf, st, sr, sp = f(p["pF"]), f(p["s_trial"]), f(p["s_replay_fail"]), f(p["s_plant_fail"])
        sampler("v", "direct", r, math.ceil(nv / pf), st + pf * sr)
        sampler("v", "plant", r, nv, sp)
    prow = {(r["item"], r["id"]): r for r in rows if r["item"] in ("pu01", "pu05")}
    for r in grid.p():
        a, b = prow[("pu01", r["id"])], prow[("pu05", r["id"])]
        f1 = int(round(f(a["pF"]) * int(a["trials"]))) + int(round(f(b["pF"]) * int(b["trials"])))
        n1 = int(a["trials"]) + int(b["trials"])
        n = min(P_CAP, math.ceil(TARGET / (f1 / n1))) if f1 > 0 else P_NOFAIL
        cost = max(f(a["s_trial"]), f(b["s_trial"]))
        for bi, nb in enumerate(blocks(n, cost)):
            for u in (0.01, 0.05):
                T.append(dict(stage="p", kind="p", id=r["id"], k=r["k"], M=r["M"], d=r["d"], load=r["load"],
                              onesided=r["onesided"], common=r["common"], u=u, block=bi, trials=nb))
    json.dump(out, sys.stdout, indent=1)


if __name__ == "__main__":
    main(sys.argv[1])

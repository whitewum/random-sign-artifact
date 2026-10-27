"""Summarize the feasibility pilot (out/pilot) into per-configuration costs.

usage: python3 pilot_report.py PILOT_OUT_DIR > pilot.tsv

Sampler rows: direct Pr(F) with a Wilson interval, seconds per trial, replay seconds per failure,
fraction of direct failures whose core is a single duplicate pair, planted seconds per failure, and the
projected core-hours for TARGET failures by direct and by planted sampling.
Protocol rows: Pr(F1), seconds per trial and the projected core-hours for TARGET round-1 failures.
"""
import csv
import glob
import json
import math
import os
import sys

import grid

TARGET = 20_000


def wilson(x, n, z=1.96):
    if n == 0:
        return float("nan"), float("nan")
    p = x / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return max(0.0, c - h), min(1.0, c + h)


def steps(d):
    out = {}
    with open(os.path.join(d, "steps.tsv")) as f:
        for line in f:
            k, v = line.split()
            out[k] = float(v)
    return out


def sampler(d):
    man = json.load(open(os.path.join(d, "s", "manifest.json")))
    c = man["configs"][0]
    rep = json.load(open(os.path.join(d, "replay.json")))["runs"]["s"][0]["groups"]
    st = steps(d)
    nf = rep["failed"]["n"]
    return dict(trials=c["trials"], failed=c["failed"], nf=nf, pair=rep["failed_pair"]["n"],
                sample_s=st["sample"], replay_s=st["replay"])


def main(root):
    rows = {r["id"]: r for r in grid.c1() + grid.m64() + grid.v()}
    w = csv.writer(sys.stdout, delimiter="\t")
    w.writerow(["item", "id", "k", "M", "d", "c", "load", "trials", "pF", "pF_lo", "pF_hi", "s_trial",
                "s_replay_fail", "pair_frac", "s_plant_fail", "h_direct", "h_plant"])
    for d in sorted(glob.glob(os.path.join(root, "pilot-direct-*"))):
        cid = os.path.basename(d)[len("pilot-direct-"):-len("-b000")]
        r = rows[cid]
        x = sampler(d)
        pf = x["failed"] / x["trials"]
        lo, hi = wilson(x["failed"], x["trials"])
        s_trial = x["sample_s"] / x["trials"]
        s_rep = x["replay_s"] / x["nf"] if x["nf"] else float("nan")
        pair = x["pair"] / x["failed"] if x["failed"] else float("nan")
        h_direct = TARGET * (s_trial / pf + (s_rep if x["nf"] else 0)) / 3600 if pf > 0 else float("inf")
        pd = os.path.join(root, f"pilot-plant-{cid}-b000")
        s_pl, h_pl = float("nan"), float("nan")
        if os.path.isdir(pd):
            y = sampler(pd)
            s_pl = (y["sample_s"] + y["replay_s"]) / y["nf"]
            h_pl = TARGET * s_pl / 3600
        w.writerow([r["item"], cid, r["k"], r["M"], r["d"], f"{r['c']:.3f}", f"{r['load']:.3f}", x["trials"],
                    f"{pf:.3g}", f"{lo:.3g}", f"{hi:.3g}", f"{s_trial:.3g}", f"{s_rep:.3g}", f"{pair:.3f}",
                    f"{s_pl:.3g}", f"{h_direct:.3g}", f"{h_pl:.3g}"])
    prow = {r["id"]: r for r in grid.p()}
    for d in sorted(glob.glob(os.path.join(root, "pilot-pu*"))):
        base = os.path.basename(d)
        tag, cid = base.split("-")[1], base[len("pilot-pu01-"):-len("-b000")]
        r = prow[cid]
        st = steps(d)
        with open(os.path.join(d, "proto.csv")) as f:
            pr = list(csv.DictReader(f))
        n, f1 = int(pr[0]["trials"]), int(pr[0]["f1"])
        pf = f1 / n
        s_trial = st["protocol"] / n
        h = TARGET * s_trial / pf / 3600 if pf > 0 else float("inf")
        w.writerow([tag, cid, r["k"], r["M"], r["d"], f"{r['c']:.3f}", f"{r['load']:.3f}", n, f"{pf:.3g}",
                    *map(lambda v: f"{v:.3g}", wilson(f1, n)), f"{s_trial:.3g}", "", "", "", f"{h:.3g}", ""])


if __name__ == "__main__":
    main(sys.argv[1])

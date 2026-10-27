"""Merge the task outputs of C1, M=64, V and P into per-configuration tables.

usage: python3 collect.py RESULTS_DIR      (RESULTS_DIR holds c1/ m64/ v/ p/ and optionally c1x/ from deploy.sh fetch)

Checks every block listed in frozen/main.json is present (and nothing else), then writes
  RESULTS_DIR/coverage.tsv   one row per (stage, kind, config, rule): failures, miss/u with a 95% Wilson
                             interval, empty-set rate, median and 90% quantile of (U-d)/d (empty = +inf),
                             fraction of failures whose core is one duplicate pair
  RESULTS_DIR/protocol.tsv   one row per (config, u, arm): Pr(F1), conditional miss, joint miss,
                             Pr[ok2 | F1], final failure rate, mean bytes and mean M2 on F1
"""
import csv
import json
import math
import os
import sys
from collections import defaultdict

import grid

RULES = {"raw01": ("Skellam", 0.01), "raw05": ("Skellam", 0.05), "rchi01": ("Gaussian", 0.01),
         "rchi05": ("Gaussian", 0.05)}


def wilson(x, n, z=1.96):
    if n == 0:
        return float("nan"), float("nan")
    p = x / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return max(0.0, c - h), min(1.0, c + h)


def quantile(hist, n, q):
    """hist: {U-d (str) or 'inf': count}; returns the q quantile of U-d over n samples."""
    keys = sorted((float("inf") if k == "inf" else int(k), v) for k, v in hist.items())
    need, acc = q * n, 0
    for k, v in keys:
        acc += v
        if acc >= need:
            return k
    return float("inf")


def task_name(t):
    if t["stage"] == "p":
        return f"p-{'u01' if t['u'] == 0.01 else 'u05'}-{t['id']}-b{t['block']:03d}"
    return f"{t['stage']}-{t['kind']}-{t['id']}-b{t['block']:03d}"


def main(root):
    here = os.path.dirname(os.path.abspath(__file__))
    F = json.load(open(os.path.join(here, "frozen", "main.json")))
    want = {task_name(t): t for t in F["tasks"]}
    have = set()
    for st in ("c1", "m64", "v", "p"):
        have |= {n for n in os.listdir(os.path.join(root, st)) if not n.startswith(".")}
    missing, extra = sorted(set(want) - have), sorted(have - set(want))
    if missing or extra:
        sys.exit(f"incomplete: missing {missing[:5]} ({len(missing)}), extra {extra[:5]} ({len(extra)})")

    # samplers
    agg = defaultdict(lambda: {"trials": 0, "failed": 0, "n": 0, "pair": 0, "miss": defaultdict(int),
                               "empty": defaultdict(int), "width": defaultdict(lambda: defaultdict(int)),
                               "blocks": 0})
    for name, t in want.items():
        if t["stage"] == "p":
            continue
        d = os.path.join(root, t["stage"], name)
        c = json.load(open(os.path.join(d, "s", "manifest.json")))["configs"][0]
        assert c["trials"] == t["trials"], name
        g = json.load(open(os.path.join(d, "replay.json")))["runs"]["s"][0]["groups"]
        a = agg[(t["stage"], t["kind"], t["id"])]
        a["trials"] += c["trials"]
        a["failed"] += c["failed"]
        a["blocks"] += 1
        a["n"] += g["failed"]["n"]
        a["pair"] += g["failed_pair"]["n"]
        for r in RULES:
            a["miss"][r] += g["failed"]["miss"].get(r, 0)
            a["empty"][r] += g["failed"]["empty"].get(r, 0)
            for k, v in g["failed"]["width"][r].items():
                a["width"][r][k] += v
    # C1 supplement (grid.c1x), outside frozen/main.json: every block present, 2e4 trials each config
    xdir = os.path.join(root, "c1x")
    if os.path.isdir(xdir):
        for name in sorted(n for n in os.listdir(xdir) if not n.startswith(".")):
            _, kind, rest = name.split("-", 2)
            cid = rest.rsplit("-b", 1)[0]
            d = os.path.join(xdir, name)
            c = json.load(open(os.path.join(d, "s", "manifest.json")))["configs"][0]
            g = next(iter(json.load(open(os.path.join(d, "replay.json")))["runs"].values()))[0]["groups"]
            a = agg[("c1x", kind, cid)]
            a["trials"] += c["trials"]
            a["failed"] += c["failed"]
            a["n"] += g["failed"]["n"]
            a["pair"] += g["failed_pair"]["n"]
            for r in RULES:
                a["miss"][r] += g["failed"]["miss"].get(r, 0)
                a["empty"][r] += g["failed"]["empty"].get(r, 0)
                for k_, v_ in g["failed"]["width"][r].items():
                    a["width"][r][k_] += v_
        for cid in {k[2] for k in agg if k[0] == "c1x"}:
            assert agg[("c1x", "direct", cid)]["trials"] == 20000, cid
    rows = {r["id"]: r for r in grid.c1() + grid.c1x() + grid.m64() + grid.v()}
    with open(os.path.join(root, "coverage.tsv"), "w") as fo:
        w = csv.writer(fo, delimiter="\t")
        w.writerow(["stage", "kind", "id", "k", "M", "d", "c", "load", "trials", "pF", "n_fail", "pair_frac",
                    "rule", "u", "miss", "miss_u", "miss_u_lo", "miss_u_hi", "empty_rate", "w50_rel", "w90_rel"])
        for (st, kind, cid), a in sorted(agg.items()):
            r, n = rows[cid], a["n"]
            assert n == a["failed"], (st, kind, cid)
            for rule, (name, u) in RULES.items():
                x = a["miss"][rule]
                lo, hi = wilson(x, n)
                w50, w90 = (quantile(a["width"][rule], n, q) / r["d"] for q in (0.5, 0.9))
                w.writerow([st, kind, cid, r["k"], r["M"], r["d"], f"{r['c']:.4f}", f"{r['load']:.4f}", a["trials"],
                            f"{a['failed'] / a['trials']:.4g}", n, f"{a['pair'] / n:.4f}" if n else "nan", name, u, x,
                            f"{x / n / u:.4f}", f"{lo / u:.4f}", f"{hi / u:.4f}", f"{a['empty'][rule] / n:.4g}",
                            f"{w50:.5g}", f"{w90:.5g}"])

    # protocol
    pagg = defaultdict(lambda: defaultdict(float))
    for name, t in want.items():
        if t["stage"] != "p":
            continue
        with open(os.path.join(root, "p", name, "proto.csv")) as f:
            for x in csv.DictReader(f):
                a = pagg[(t["id"], t["u"], x["arm"])]
                n, f1 = int(x["trials"]), int(x["f1"])
                a["trials"] += n
                a["f1"] += f1
                for key in ("f1_miss", "f1_empty", "f2", "fail", "falsepos", "wrong"):
                    a[key] += int(x[key])
                a["bytes"] += float(x["mean_bytes"]) * n
                if f1:
                    a["m2"] += float(x["mean_M2"]) * f1
                ag, tot = x["agree_signed_standard"].split("/")
                a["agree"] += int(ag)
                a["agree_n"] += int(tot)
    prow = {r["id"]: r for r in grid.p()}
    with open(os.path.join(root, "protocol.tsv"), "w") as fo:
        w = csv.writer(fo, delimiter="\t")
        w.writerow(["id", "k", "M1", "d", "load", "onesided", "u", "arm", "trials", "pF1", "f1", "cond_miss",
                    "joint_miss", "joint_miss_hi", "ok2_given_f1", "final_fail", "final_fail_hi", "mean_bytes",
                    "mean_M2_f1", "wrong", "agree"])
        for (cid, u, arm), a in sorted(pagg.items()):
            r, n, f1 = prow[cid], a["trials"], a["f1"]
            w.writerow([cid, r["k"], r["M"], r["d"], f"{r['load']:.3f}", r["onesided"], u, arm, int(n),
                        f"{f1 / n:.4g}", int(f1), f"{a['f1_miss'] / f1:.4g}" if f1 else "nan",
                        f"{a['f1_miss'] / n:.4g}", f"{wilson(a['f1_miss'], n)[1]:.3g}",
                        f"{1 - a['f2'] / f1:.5f}" if f1 else "nan", f"{a['fail'] / n:.4g}",
                        f"{wilson(a['fail'], n)[1]:.3g}", f"{a['bytes'] / n:.1f}",
                        f"{a['m2'] / f1:.1f}" if f1 else "nan", int(a["wrong"]),
                        f"{int(a['agree'])}/{int(a['agree_n'])}"])
    print("ok:", len(agg), "sampler configurations,", len(pagg), "protocol rows")


if __name__ == "__main__":
    main(sys.argv[1])

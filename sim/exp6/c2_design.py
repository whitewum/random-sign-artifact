"""C2 design table: one row per candidate (plan §3 C2, selection rule frozen before C1).

usage: uv run --with scipy python3 c2_design.py RESULTS_DIR > c2_design.tsv

Candidates: the five historical points, then the C1 configurations in decreasing order of the larger
(over u) one-sided 95% Clopper-Pearson upper bound of miss/u for the Skellam rule, ties by (k, M, d).
A ranked configuration is passed over when C1 sampled it by planting because the projected direct cost
exceeded the C1 limit (its Q result stays in the report); the next one in order fills the slot.

Per candidate and u the planning value of the true miss/u is r = min(1, 95% Wilson upper bound of the
best available earlier estimate); n(u) is the failure count giving per-judgment pass probability
1 - 0.2/J (J = 24) at level 0.05/J; the budget is max over u. The sensitivity column gives n at r = 1.
Cost per failure comes from the C1 direct runs, the pilot, or an estimate noted in the row.
"""
import csv
import glob
import json
import math
import os
import sys

from scipy.stats import beta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from c2_power import smallest_n  # noqa: E402

J = 24
LEVEL = 0.05 / J
TARGET = 1 - 0.2 / J
SLOTS = 12

HISTORICAL = [  # id, earlier estimate per u (miss/u, failures), source
    ("k3-M1024-d192", {"0.01": (1.19, 2100)}, "R20 direct, about 2100 failures"),
    ("k4-M256-d128", None, "C1 direct"),
    ("k4-M16384-d16384", {"0.01": (1.02, 100000)}, "R22 overload, 1e5 failures"),
    ("k3-M1024-d64", None, "C1 direct"),
    ("k3-M1024-d32", None, "C1 planted (pure-pair share 1.00)"),
]
# per-failure cost (core-seconds) where C1 has no direct run: d/(pF) from the pilot or the pair formula
COST_NOTE = {
    "k3-M1024-d192": (0.30, "estimated: pF ~ C(d,2)/C(M,3) = 1.0e-4, 3e-5 s per trial"),
    "k4-M16384-d16384": (0.02, "estimated: overload, Pr(F)=1, replay at c=128"),
}


def wilson_hi(x, n, z=1.96):
    p = x / n
    den = 1 + z * z / n
    return ((p + z * z / (2 * n)) + z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / den


def main(root):
    cov = [r for r in csv.DictReader(open(os.path.join(root, "coverage.tsv")), delimiter="\t")
           if r["stage"] == "c1" and r["rule"] == "Skellam"]
    pilot = {r["id"]: r for r in csv.DictReader(open(os.path.join(root, "pilot.tsv")), delimiter="\t")
             if r["item"] in ("c1", "v", "m64")}
    by = {(r["id"], r["u"]): r for r in cov}
    ucb = {}
    for r in cov:
        n, x, u = int(r["n_fail"]), int(r["miss"]), float(r["u"])
        ucb[r["id"]] = max(ucb.get(r["id"], 0), beta.ppf(0.95, x + 1, n - x) / u)
    rank = sorted(ucb, key=lambda i: (-ucb[i], tuple(int(t[1:]) for t in i.split("-"))))

    def cost(cid):
        if cid in COST_NOTE:
            return COST_NOTE[cid]
        tot = nf = 0
        for d in glob.glob(os.path.join(root, "c1", f"c1-direct-{cid}-b*")):
            st = dict(l.split() for l in open(os.path.join(d, "steps.tsv")))
            tot += float(st["sample"]) + float(st["replay"])
            nf += json.load(open(os.path.join(d, "s", "manifest.json")))["configs"][0]["failed"]
        if nf:
            return tot / nf, "C1 direct runs"
        p = pilot[cid]
        return float(p["s_trial"]) / float(p["pF"]), f"pilot: pF {float(p['pF']):.2g}"

    rows, skipped = [], []
    for cid, est, src in HISTORICAL:
        rows.append((cid, "historical", est, src))
    for cid in rank:
        if len(rows) >= SLOTS:
            break
        if any(cid == r[0] for r in rows):
            continue
        kinds = {by[(cid, u)]["kind"] for u in ("0.01", "0.05")}
        if kinds == {"plant"}:
            skipped.append(cid)
            continue
        rows.append((cid, "C1 rank", None, "C1 direct"))

    w = csv.writer(sys.stdout, delimiter="\t")
    w.writerow(["id", "c", "load", "origin", "C1_kind", "C1_missu_01", "C1_missu_05", "C1_ucb95_max", "earlier",
                "r_plan_01", "r_plan_05", "n_01", "n_05", "n_fail", "n_if_r1", "s_per_fail", "core_h", "core_h_if_r1",
                "cost_source"])
    tot = tot1 = 0.0
    for cid, origin, est, src in rows:
        r01, r05 = by.get((cid, "0.01")), by.get((cid, "0.05"))
        plan, ns = {}, {}
        for u, r in (("0.01", r01), ("0.05", r05)):
            if r is not None:
                hi = wilson_hi(int(r["miss"]), int(r["n_fail"])) / float(u)
            else:
                m, n = est[u] if est and u in est else (1.0, 1)
                hi = wilson_hi(m * float(u) * n, n) / float(u) if n > 1 else 1.0
            plan[u] = min(1.0, hi)
            ns[u] = smallest_n(float(u), LEVEL, TARGET, plan[u])
        n = max(ns.values())
        n1 = smallest_n(0.01, LEVEL, TARGET, 1.0)
        spf, csrc = cost(cid)
        tot += n * spf / 3600
        tot1 += n1 * spf / 3600
        c = (r01["c"], r01["load"]) if r01 else ("", "")
        w.writerow([cid, *c, origin, r01["kind"] if r01 else "-", r01["miss_u"] if r01 else "", r05["miss_u"] if r05 else "",
                    f"{ucb[cid]:.3f}" if cid in ucb else "", src, f"{plan['0.01']:.3f}", f"{plan['0.05']:.3f}",
                    ns["0.01"], ns["0.05"], n, n1, f"{spf:.3g}", f"{n * spf / 3600:.1f}", f"{n1 * spf / 3600:.1f}", csrc])
    print(f"# total core-h {tot:.0f} (planning values), {tot1:.0f} if every true miss/u = 1; "
          f"passed over (planted in C1): {', '.join(skipped)}", file=sys.stderr)


if __name__ == "__main__":
    main(sys.argv[1])

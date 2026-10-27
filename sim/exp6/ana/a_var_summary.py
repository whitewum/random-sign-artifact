"""Conditional variance of X under the random-sign encoding on the C1 direct configurations (M >= 256).

usage: python3 a_var_summary.py sim/results/exp6-20261016

Joins ana/a_moments.tsv with coverage.tsv (for c and load) and prints the variance range for c >= 8,
inside the critical window (load 0.95-1.05), per c below 8, and the share of |mean| within two SE.
"""
import csv
import os
import sys


def main(root):
    cov = {r["id"]: r for r in csv.DictReader(open(os.path.join(root, "coverage.tsv")), delimiter="\t")
           if r["rule"] == "Skellam" and r["u"] == "0.01"}
    rows = []
    for r in csv.DictReader(open(os.path.join(root, "ana", "a_moments.tsv")), delimiter="\t"):
        c = cov[r["id"]]
        if r["kind"] != "direct" or int(c["M"]) < 256:
            continue
        rows.append((float(c["c"]), float(c["load"]), int(c["M"]), r["id"], float(r["rand_mean"]),
                     float(r["rand_se"]), float(r["rand_var"])))
    span = lambda v: f"{min(v):.4f}-{max(v):.4f} (n={len(v)})"  # noqa: E731
    print("direct configurations:", len(rows))
    print("c>=8:", span([v for c, *_, v in rows if c >= 8]))
    print("window:", span([v for c, l, *_, v in rows if 0.9495 <= l <= 1.0505]))
    for c, l, M, i, m, se, v in sorted(rows):
        if c < 8:
            print(f"  c={c:.3f} M={M} {i}: var={v:.4f}  limit 1+2/c^2={1 + 2 / c ** 2:.3f}")
    print("max |mean|:", f"{max(abs(r[4]) for r in rows):.5f}",
          "within 2 SE:", sum(abs(r[4]) <= 2 * r[5] for r in rows), "/", len(rows))


if __name__ == "__main__":
    main(sys.argv[1])

"""Paired success-rate differences with Newcombe's hybrid score interval (method 10, Newcombe 1998).

usage: python3 p_pairs_score.py ANA_P_DIR      (reads pairs.tsv and risk.tsv from p_pairs.py; writes pairs_score.tsv)

p_pairs.py reports a Wald interval for the paired difference, which collapses to [0, 0] when no trial is
discordant. The 2x2 table of final success (arm A x arm B) is rebuilt from the discordant counts n10, n01
and each arm's final failure count: a = both succeed = (N - fail_A) - n10, d = N - a - n10 - n01. The
interval for p_B - p_A combines the two 95% Wilson intervals with the phi correlation of the table.
"""
import csv
import math
import os
import sys

Z = 1.959964


def wilson(x, n):
    p = x / n
    den = 1 + Z * Z / n
    c = (p + Z * Z / (2 * n)) / den
    h = Z * math.sqrt(p * (1 - p) / n + Z * Z / (4 * n * n)) / den
    return c - h, c + h


def newcombe10(a, b, c, d):
    """95% interval for p1 - p2, p1 = (a+b)/n, p2 = (a+c)/n (b = n10: 1 succeeds, 2 fails)."""
    n = a + b + c + d
    p1, p2 = (a + b) / n, (a + c) / n
    l1, u1 = wilson(a + b, n)
    l2, u2 = wilson(a + c, n)
    den = (a + b) * (c + d) * (a + c) * (b + d)
    phi = (a * d - b * c) / math.sqrt(den) if den > 0 else 0.0
    dl = math.sqrt(max(0.0, (p1 - l1) ** 2 - 2 * phi * (p1 - l1) * (u2 - p2) + (u2 - p2) ** 2))
    du = math.sqrt(max(0.0, (u1 - p1) ** 2 - 2 * phi * (u1 - p1) * (p2 - l2) + (p2 - l2) ** 2))
    return p1 - p2 - dl, p1 - p2 + du


def main(d):
    fails = {}
    for r in csv.DictReader(open(os.path.join(d, "risk.tsv")), delimiter="\t"):
        fails[(r["id"], r["u"], r["arm"])] = int(r["final_fail"])
    out = open(os.path.join(d, "pairs_score.tsv"), "w")
    w = csv.writer(out, delimiter="\t")
    w.writerow(["id", "u", "armA", "armB", "N", "a_both_ok", "n10", "n01", "d_both_fail", "dsucc", "dsucc_lo", "dsucc_hi"])
    for r in csv.DictReader(open(os.path.join(d, "pairs.tsv")), delimiter="\t"):
        N, n10, n01 = int(r["N"]), int(r["n10"]), int(r["n01"])
        fa, fb = fails[(r["id"], r["u"], r["armA"])], fails[(r["id"], r["u"], r["armB"])]
        assert (N - fa) - (N - fb) == n10 - n01, r["id"]  # margins agree with the discordant counts
        a = N - fa - n10
        dd = N - a - n10 - n01
        lo, hi = newcombe10(a, n10, n01, dd)  # interval for p_A - p_B
        w.writerow([r["id"], r["u"], r["armA"], r["armB"], N, a, n10, n01, dd, f"{(n01 - n10) / N:.3e}",
                    f"{-hi:.3e}", f"{-lo:.3e}"])
    out.close()


if __name__ == "__main__":
    main(sys.argv[1])

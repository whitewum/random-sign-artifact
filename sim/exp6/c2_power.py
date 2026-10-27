"""C2 sample size by exact binomial power (plan §2 and §3 C2).

Judgment per (configuration, u): the one-sided Clopper-Pearson upper bound of the conditional miss at
level 1 - ALPHA/J must not exceed 1.1 u. For a true miss rate p = r u, the probability to pass is
P(X <= x_max(n)), where x_max(n) is the largest count whose upper bound is <= 1.1 u. The script reports,
for each u, the smallest failure count n reaching (a) 80% power per judgment and (b) per-judgment power
1 - 0.2/J (so that the failure probabilities of all J judgments sum to at most 20%).

usage: python3 c2_power.py [J]      (default J = 24: 12 configurations x 2 risk levels)
"""
import sys

from scipy.stats import beta, binom

ALPHA = 0.05
TOL = 1.1


def x_max(n, u, level):
    # largest x with CP upper bound <= TOL u; the bound increases in x
    lo, hi = -1, n
    while hi - lo > 1:
        m = (lo + hi) // 2
        if beta.ppf(1 - level, m + 1, n - m) <= TOL * u:
            lo = m
        else:
            hi = m
    return lo


def power(n, u, level, r=1.0):
    x = x_max(n, u, level)
    return 0.0 if x < 0 else binom.cdf(x, n, r * u)


def smallest_n(u, level, target, r=1.0):
    lo, hi = 1000, 1000
    while power(hi, u, level, r) < target:
        lo, hi = hi, hi * 2
    while hi - lo > max(100, lo // 200):
        m = (lo + hi) // 2
        if power(m, u, level, r) >= target:
            hi = m
        else:
            lo = m
    return hi


if __name__ == "__main__":
    J = int(sys.argv[1]) if len(sys.argv) > 1 else 24
    level = ALPHA / J
    print(f"J={J}, per-judgment one-sided level {level:.5f}, tolerance {TOL}")
    for u in (0.01, 0.05):
        for name, tgt in (("80% per judgment", 0.8), (f"all-pass >= 80% (each {1 - 0.2 / J:.4f})", 1 - 0.2 / J)):
            for r in (1.0, 0.9):
                n = smallest_n(u, level, tgt, r)
                print(f"u={u:.2f} true miss/u={r:.1f} {name:38s} n_fail = {n:>9,d}")

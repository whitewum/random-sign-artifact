"""High-precision reference for the raw-energy discrete candidate law.

Only the standard library is needed. This is a reference calculation, not a
large-scale replay implementation. CDF intervals include an analytic Poisson
truncation bound and a conservative roundoff allowance at 70-digit precision;
they are not a machine-verified interval-arithmetic certificate.
"""

from decimal import Decimal, localcontext
from functools import lru_cache


D = Decimal
PRECISION = 70
TAIL = D("1e-45")
ROUNDOFF = D("1e-55")


@lru_cache(maxsize=256)
def poisson_prefix(mean):
    """Probabilities through a truncation, prefix CDF, omitted-tail upper bound."""
    with localcontext() as ctx:
        ctx.prec = PRECISION
        mean = D(mean)
        if mean == 0:
            return (D(1),), (D(1),), D(0)
        if mean < 0:
            raise ValueError("Poisson mean must be nonnegative")
        p = (-mean).exp()
        probabilities = [p]
        prefixes = [p]
        j = 0
        while True:
            next_p = p * mean / (j + 1)
            # After the first omitted term, all successive ratios are <= this.
            ratio = mean / (j + 2)
            if ratio < 1:
                tail = next_p / (1 - ratio)
                if tail < TAIL:
                    return tuple(probabilities), tuple(prefixes), tail
            j += 1
            p = next_p
            probabilities.append(p)
            prefixes.append(prefixes[-1] + p)


def difference_cdf(mean, cutoff):
    """Inclusive CDF interval for independent Poisson(mean) minus Poisson(mean)."""
    probabilities, prefixes, tail = poisson_prefix(mean)
    with localcontext() as ctx:
        ctx.prec = PRECISION
        total = prefixes[-1]
        lower = D(0)
        for positive, probability in enumerate(probabilities):
            first_negative = max(0, positive - cutoff)
            if first_negative >= len(probabilities):
                continue
            mass = total if first_negative == 0 else total - prefixes[first_negative - 1]
            lower += probability * mass
        return max(D(0), lower - ROUNDOFF), min(D(1), lower + 2 * tail + ROUNDOFF)


def candidate_cdf(cells, k, n, sum_squares):
    """CDF at the exact integer observed sum of squared cell counts."""
    if cells <= k or k < 3 or n < 2:
        raise ValueError("Require M > k >= 3 and n >= 2")
    if not isinstance(sum_squares, int):
        raise TypeError("sum_squares must be an integer")
    with localcontext() as ctx:
        ctx.prec = PRECISION
        mean = D(k * k * (n - 2) * (n - 3)) / (4 * cells)
        if mean == 0:
            value = D(sum(k * (n + shift) <= sum_squares for shift in (-2, 2))) / 2
            return value, value
        intervals = [difference_cdf(mean, (sum_squares - k * n - 2 * k * sign) // 2)
                     for sign in (-1, 1)]
        return tuple(sum(pair[j] for pair in intervals) / 2 for j in (0, 1))


def accepts(cells, k, n, sum_squares, risk):
    # Uncertain numerical decisions are accepted, preserving conservatism.
    return candidate_cdf(cells, k, n, sum_squares)[1] > D(str(risk))


def search_stop(cells, k, sum_squares, risk):
    """All n >= result are rejected analytically; None selects +infinity."""
    if sum_squares < 0:
        raise ValueError("Observed sum of squares must be nonnegative")
    with localcontext() as ctx:
        ctx.prec = PRECISION
        risk = D(str(risk))
        if not 0 < risk < D("0.5"):
            raise ValueError("Require 0 < risk < 1/2")
        if (-D(9 * cells) / 80).exp() >= risk:
            return None
        # ceil(4 * (sum_squares/k + 2)), ceil(M/(2*k)), and 4, exactly.
        return max((4 * sum_squares + 8 * k + k - 1) // k,
                   (cells + 2 * k - 1) // (2 * k), 4)


def upper(cells, k, sum_squares, risk):
    stop = search_stop(cells, k, sum_squares, risk)
    if stop is None:
        return float("inf")
    accepted = [n for n in range(2, stop)
                if accepts(cells, k, n, sum_squares, risk)]
    return max(accepted) if accepted else float("inf")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--M", type=int, required=True)
    parser.add_argument("--k", type=int, required=True)
    parser.add_argument("--sum-squares", type=int, required=True)
    parser.add_argument("--risk", default="0.01")
    args = parser.parse_args()
    print(upper(args.M, args.k, args.sum_squares, args.risk))

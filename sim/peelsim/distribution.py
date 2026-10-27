"""Exact-support CDF comparisons and the manuscript's G_d (no finite-size corrections)."""
import math
import numpy as np
from scipy.stats import skellam


def gd_lattice(k, M, d):
    """Return integer support in units 2/k for G_d shifted by -d."""
    lam = k*k*max(d-2, 0)*max(d-3, 0)/(4*M)
    radius = int(15*math.sqrt(2*lam)+50)
    j = np.arange(-radius, radius+1, dtype=np.int64)
    p = skellam.pmf(j, lam, lam) if lam else (j == 0).astype(float)
    support = np.arange(-radius-k, radius+k+1, dtype=np.int64)
    probabilities = np.zeros(len(support))
    probabilities[:len(p)] += p/2
    probabilities[2*k:2*k+len(p)] += p/2
    if abs(probabilities.sum()-1) > 1e-11:
        raise ArithmeticError('Skellam mass truncation exceeds tolerance')
    return support, probabilities


def discrete_ks(x, p, y, q):
    """Supremum over both sides of every atom; pass common integer units when possible."""
    grid = np.union1d(x, y)
    a, b = np.r_[0, np.cumsum(p)], np.r_[0, np.cumsum(q)]
    return float(max(np.max(abs(a[np.searchsorted(x, grid, side=side)] -
                               b[np.searchsorted(y, grid, side=side)])) for side in ('left', 'right')))


def continuous_ks(x, p, cdf):
    """Exact supremum against a continuous CDF, including both sides of empirical atoms."""
    f = np.cumsum(p)
    g = cdf(x)
    return float(max(np.max(abs(f-g)), np.max(abs(np.r_[0, f[:-1]]-g))))


def quantile(x, p, u):
    return x[min(int(np.searchsorted(np.cumsum(p), u)), len(x)-1)]

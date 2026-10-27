"""Configurations and seeds of the §6 experiment campaign
(research-status/log/2026-10-16-experiment-plan.md).

Every configuration has a stable id; every task seed is derived from (stage, config id, block) by
SHA-256, so the samples of a task do not depend on the host or on the order of execution, and the
stages (pilot, c1, v, c2, p) use disjoint seeds.

usage: python3 grid.py [c1|m64|v|p]     print the configurations of one plan item
"""
import hashlib
import math
import sys

# alpha_c of the k-uniform 2-core (sim/iblt2r/main.go)
ALPHA = {3: 0.818469160761, 4: 0.772279839803, 5: 0.701780266485}

KS = (3, 4, 5)
MS = (256, 1024, 4096, 16384)
CS = (0.5, 1, 2, 4, 8, 16, 32, 64)
LOADS = (0.95, 1.0, 1.05, 1.5, 3.0)
SMALL_D = (2, 3, 6)
MAX_LOAD = 3.0
V_LOADS = (0.85, 0.9, 0.95)
V_MS = (64, 256, 1024, 4096)
P_COMMON = 1000  # common elements per party in the protocol runs (cancel exactly; affect time only)
VLDB_M1 = (256, 1024, 4096)  # tiers where the VLDB q_{0.01} is defined and lies in the P grid


def load(k, M, d):
    return d / (ALPHA[k] * M)


def seed(stage, cid, block):
    h = hashlib.sha256(f"exp6-20261016|{stage}|{cid}|{block}".encode()).digest()
    s = int.from_bytes(h[:8], "little") & 0x7FFF_FFFF_FFFF_FFFF
    return s or 1


def cid(k, M, d):
    return f"k{k}-M{M}-d{d}"


def _ds(k, M):
    ds = {round(c * math.sqrt(M)) for c in CS}
    ds |= {round(L * ALPHA[k] * M) for L in LOADS}
    ds |= set(SMALL_D)
    return sorted(d for d in ds if d >= 2 and load(k, M, d) <= MAX_LOAD + 1e-9)


def _row(item, k, M, d, **kw):
    r = dict(item=item, id=cid(k, M, d), k=k, M=M, d=d, c=d / math.sqrt(M), load=load(k, M, d))
    r.update(kw)
    return r


def c1():
    """C1 main configurations (descriptive map)."""
    return [_row("c1", k, M, d) for k in KS for M in MS for d in _ds(k, M)]


def c1x():
    """C1 supplement (added 10-16 after C1 ran): the load-3 points that C1 dropped because
    round(3 alpha_c M) / (alpha_c M) exceeds 3 by rounding, and the same point of the M = 64 boundary.
    Same sampling and target as C1."""
    out = []
    for k in KS:
        for M in (64,) + MS:
            d = round(3 * ALPHA[k] * M)
            if load(k, M, d) > MAX_LOAD + 1e-9:
                out.append(_row("c1x", k, M, d))
    return out


def m64():
    """M = 64 boundary, same rule as C1."""
    return [_row("m64", k, 64, d) for k in KS for d in _ds(k, 64)]


def v():
    """V candidates: overlap of direct and planted sampling; kept after the pilot if direct Pr(F) >= 1e-3."""
    out = []
    for k in KS:
        for M in V_MS:
            for L in V_LOADS:
                d = round(L * ALPHA[k] * M)
                out.append(_row("v", k, M, d))
    return out


def p():
    """P protocol configurations; u in {0.01, 0.05}; VLDB arms only for k = 3, M1 in VLDB_M1, u = 0.01."""
    out = []
    for k in KS:
        for M in MS:
            for L in LOADS:
                d = round(L * ALPHA[k] * M)
                for one in (1, 0):
                    r = _row("p", k, M, d, onesided=one, common=P_COMMON)
                    r["id"] = f"k{k}-M{M}-d{d}-{'one' if one else 'bal'}"
                    out.append(r)
    return out


def vldb_defined(k, M):
    return k == 3 and M in VLDB_M1


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "c1"
    rows = {"c1": c1, "c1x": c1x, "m64": m64, "v": v, "p": p}[which]()
    for r in rows:
        print(f"{r['id']:28s} c={r['c']:8.2f} load={r['load']:5.2f}")
    print(len(rows), "configurations", file=sys.stderr)

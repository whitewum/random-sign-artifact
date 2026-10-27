"""P: risk decomposition and paired comparisons from the per-trial files (run on the server).

usage: python3 p_pairs.py ROOT OUTDIR       (ROOT = campaign root holding out/p)

Every task of P writes proto.csv (aggregates per arm) and trials.csv (one line per trial and arm whose
round 1 failed: U, M2, ok2). A trial absent from trials.csv for an arm succeeded in round 1. Blocks of a
configuration share nothing, so trials are keyed by (block, trial).

risk.tsv   per (config, u, arm), over round-1 failures: counts of {U_b < d, U_b >= d, empty} x {round 2 ok,
           round 2 failed}; the share of final failures that follow a miss.
pairs.tsv  per (config, u, arm B) against reference arm A: discordant final-success counts n10 (A ok, B
           failed) and n01, the paired difference of success rates (B - A) with a 95% normal interval,
           and the paired mean difference of total bytes (B - A) with its 95% interval. References:
           signed_raw_b against every arm; standard_vldb_b against signed_vldb_b (encoding effect at a
           common multiplier, both raised to |b|); standard_vldb against signed_vldb (no |b|).
"""
import csv
import math
import os
import sys
from collections import defaultdict

CELL = 20
B_ARMS = {"signed_raw_b", "signed_rchi_b", "signed_vldb_b"}  # arms that send the 8-byte global counter
PAIRS = [("signed_raw_b", None), ("standard_vldb_b", "signed_vldb_b"), ("standard_vldb", "signed_vldb")]


def load(root):
    cfg = defaultdict(lambda: {"N": 0, "arms": None, "rec": defaultdict(dict)})
    pdir = os.path.join(root, "out", "p")
    for name in sorted(os.listdir(pdir)):
        if name.startswith("."):
            continue
        _, tag, rest = name.split("-", 2)
        cid, blk = rest.rsplit("-b", 1)
        d = os.path.join(pdir, name)
        k, M1, dd, common, one = map(int, open(os.path.join(d, "spec")).read().split())
        c = cfg[(cid, tag)]
        c.update(k=k, M1=M1, d=dd, one=one)
        with open(os.path.join(d, "proto.csv")) as f:
            rows = list(csv.DictReader(f))
        c["N"] += int(rows[0]["trials"])
        c["arms"] = [r["arm"] for r in rows]
        with open(os.path.join(d, "trials.csv")) as f:
            for r in csv.DictReader(f):
                c["rec"][r["arm"]][(int(blk), int(r["trial"]))] = (int(r["U"]), int(r["M2"]), r["ok2"] == "1")
    return cfg


def main(root, out):
    cfg = load(root)
    os.makedirs(out, exist_ok=True)
    fr = open(os.path.join(out, "risk.tsv"), "w")
    fp = open(os.path.join(out, "pairs.tsv"), "w")
    wr, wp = csv.writer(fr, delimiter="\t"), csv.writer(fp, delimiter="\t")
    wr.writerow(["id", "u", "k", "M1", "d", "onesided", "arm", "N", "f1", "miss_ok", "miss_fail", "cover_ok",
                 "cover_fail", "empty_ok", "empty_fail", "final_fail", "fail_after_miss_share"])
    wp.writerow(["id", "u", "k", "M1", "d", "onesided", "armA", "armB", "N", "n10", "n01", "dsucc", "dsucc_lo",
                 "dsucc_hi", "dbytes", "dbytes_lo", "dbytes_hi", "dbytes_rel_A"])
    for (cid, tag), c in sorted(cfg.items()):
        u = 0.01 if tag == "u01" else 0.05
        N, d = c["N"], c["d"]
        head = [cid, u, c["k"], c["M1"], d, c["one"]]
        for arm in c["arms"]:
            cnt = defaultdict(int)
            for U, M2, ok in c["rec"][arm].values():
                kind = "empty" if U < 0 else ("miss" if U < d else "cover")
                cnt[(kind, ok)] += 1
            f1 = sum(cnt.values())
            fails = sum(v for (kk, ok), v in cnt.items() if not ok)
            wr.writerow(head + [arm, N, f1, cnt[("miss", True)], cnt[("miss", False)], cnt[("cover", True)],
                                cnt[("cover", False)], cnt[("empty", True)], cnt[("empty", False)], fails,
                                f"{cnt[('miss', False)] / fails:.4f}" if fails else "nan"])

        def per_trial(arm):
            base = c["M1"] * CELL + (8 if arm in B_ARMS else 0)
            extra = 8 if arm in B_ARMS else 0
            return base, {key: (ok, M2 * CELL + extra) for key, (U, M2, ok) in c["rec"][arm].items()}

        pairs = []
        for a, b in PAIRS:
            if a not in c["arms"]:
                continue
            for bb in ([x for x in c["arms"] if x != a] if b is None else [b]):
                if bb in c["arms"]:
                    pairs.append((a, bb))
        for a, b in pairs:
            ba, ra = per_trial(a)
            bb, rb = per_trial(b)
            keys = set(ra) | set(rb)
            n10 = n01 = 0
            s = s2 = 0.0
            for key in keys:
                oka, xa = ra.get(key, (True, 0))
                okb, xb = rb.get(key, (True, 0))
                n10 += oka and not okb
                n01 += okb and not oka
                diff = (bb + xb) - (ba + xa)
                s += diff
                s2 += diff * diff
            # trials where both succeeded in round 1 differ by the constant bb - ba
            rest = N - len(keys)
            s += rest * (bb - ba)
            s2 += rest * (bb - ba) ** 2
            ds = (n01 - n10) / N
            se = math.sqrt(max(0.0, (n01 + n10) / N - ds * ds) / N)
            mb = s / N
            seb = math.sqrt(max(0.0, s2 / N - mb * mb) / N)
            mean_a = ba + sum(x for _, x in ra.values()) / N
            wp.writerow(head + [a, b, N, n10, n01, f"{ds:.3e}", f"{ds - 1.96 * se:.3e}", f"{ds + 1.96 * se:.3e}",
                                f"{mb:.2f}", f"{mb - 1.96 * seb:.2f}", f"{mb + 1.96 * seb:.2f}", f"{mb / mean_a:.5f}"])
    fr.close()
    fp.close()
    print("configs:", len(cfg))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])

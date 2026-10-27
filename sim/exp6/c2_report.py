"""C2 judgments (frozen/c2.json).

usage: uv run --with scipy python3 c2_report.py C2_DIR [STAGE] > c2.tsv     (C2_DIR holds the task outputs)
STAGE = c2 (default, frozen/c2.json, J = 24), c2x or c2s (frozen/STAGE.json, J from the file).

Per point the blocks are taken in block order up to and including the first block at which the
cumulative failure count reaches n_fail (the frozen stop rule). For the Skellam rule and each u the
one-sided Clopper-Pearson upper bound at level 0.05/J of the conditional miss is compared with 1.1 u;
J = 24. The Gaussian rule is reported on the same failures without a judgment.
"""
import json
import os
import sys

from scipy.stats import beta

J = 24
LEVEL = 0.05 / J
TOL = 1.1
RULES = {"raw01": ("Skellam", 0.01), "raw05": ("Skellam", 0.05), "rchi01": ("Gaussian", 0.01),
         "rchi05": ("Gaussian", 0.05)}


def main(root, stage="c2"):
    F = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "frozen", f"{stage}.json")))
    level = 0.05 / F.get("J", J)
    print("\t".join(["id", "n_target", "blocks_used", "blocks_run", "trials", "n_fail", "pair_share", "rule", "u",
                     "miss", "miss_u", "ucb_u", "pass"]))
    allpass = True
    for p in F["points"]:
        cum, used, trials, miss, pair = 0, 0, 0, {r: 0 for r in RULES}, 0
        blocks = sorted(int(n.rsplit("-b", 1)[1]) for n in os.listdir(root) if n.startswith(f"{stage}-direct-{p['id']}-b"))
        for b in blocks:
            d = os.path.join(root, f"{stage}-direct-{p['id']}-b{b:03d}")
            g = json.load(open(os.path.join(d, "replay.json")))["runs"]
            g = (g.get("s") or next(iter(g.values())))[0]["groups"]
            trials += json.load(open(os.path.join(d, "s", "manifest.json")))["configs"][0]["trials"]
            cum += g["failed"]["n"]
            pair += g["failed_pair"]["n"]
            for r in RULES:
                miss[r] += g["failed"]["miss"].get(r, 0)
            used += 1
            if cum >= p["n_fail"]:
                break
        complete = cum >= p["n_fail"] and blocks == list(range(len(blocks)))
        for r, (name, u) in RULES.items():
            ucb = beta.ppf(1 - level, miss[r] + 1, cum - miss[r]) / u if cum else float("nan")
            ok = "" if name == "Gaussian" else ("PASS" if ucb <= TOL else "FAIL")
            if not complete:
                ok = "INCOMPLETE"
            if name == "Skellam" and ok != "PASS":
                allpass = False
            print(f"{p['id']}\t{p['n_fail']}\t{used}\t{len(blocks)}\t{trials}\t{cum}\t{pair / cum if cum else 0:.4f}\t{name}\t{u}\t"
                  f"{miss[r]}\t{miss[r] / cum / u if cum else float('nan'):.4f}\t{ucb:.4f}\t{ok}")
    print(f"# all Skellam judgments pass: {allpass}", file=sys.stderr)


if __name__ == "__main__":
    main(*sys.argv[1:3])

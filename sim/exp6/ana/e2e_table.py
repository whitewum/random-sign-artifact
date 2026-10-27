"""Rows of the CN manuscript table tab:e2e from protocol.tsv (Skellam, Gaussian and oracle arms).

usage: python3 e2e_table.py sim/results/exp6-20261016/protocol.tsv

miss/u: median / max over balanced configurations with at least 1000 first-round failures; final failure:
max over configurations; second-round size and total bytes: median ratio to the oracle minus one.
The manuscript rounds half up (0.075% -> 0.08%).
"""
import csv
import statistics as st
import sys

ARMS = {"signed_raw_b": "Skellam", "signed_rchi_b": "Gaussian", "signed_oracle": "oracle"}


def main(path):
    rows = list(csv.DictReader(open(path), delimiter="\t"))
    idx = {(r["id"], r["u"], r["arm"]): r for r in rows}
    for u in ("0.01", "0.05"):
        for M1 in ("256", "1024", "4096", "16384"):
            for arm, name in ARMS.items():
                sel = [r for r in rows if r["u"] == u and r["M1"] == M1 and r["arm"] == arm]
                mu = [float(r["cond_miss"]) / float(u) for r in sel if r["onesided"] == "0" and int(r["f1"]) >= 1000]
                ff = max(float(r["final_fail"]) for r in sel)
                m2, by = [], []
                for r in sel:
                    o = idx[(r["id"], u, "signed_oracle")]
                    if int(r["f1"]) > 0 and float(o["mean_M2_f1"]) > 0:
                        m2.append(float(r["mean_M2_f1"]) / float(o["mean_M2_f1"]) - 1)
                    by.append(float(r["mean_bytes"]) / float(o["mean_bytes"]) - 1)
                print(u, M1, name, f"{st.median(mu):.4f} / {max(mu):.4f}", f"{100 * ff:.4f}%",
                      f"{100 * st.median(m2):+.4f}%", f"{100 * st.median(by):+.4f}%", len(sel))


if __name__ == "__main__":
    main(sys.argv[1])

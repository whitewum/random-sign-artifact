"""Write queue task files for one stage of the §6 campaign.

usage: python3 make_tasks.py STAGE BINS.json OUTDIR
  STAGE = pilot   feasibility pilot (plan §6): direct Pr(F) and sampling cost for C1, M=64 and V;
                  a small planted run below load 1; protocol cost for every P configuration.
          main    C1, M=64, V and P as frozen in frozen/main.json (freeze_main.py)
          c2      C2 confirmation points as frozen in frozen/c2.json (freeze_c2.py)
          c2x     one more C2 point (k5-M16384-d17247) as frozen in frozen/c2x.json
          c2s     the other nine fig:scale points (load 1.5) as frozen in frozen/c2s.json
          v2      low-load direct against planted for k = 3 (v2_stage)
          v2s     the same for k = 4, 5 with a small direct sample (v2_stage)
          v3a/b/c fresh direct samples for the v2s configurations, in priority order (v3_stage)

Each task file is a bash script run by queue/run_task.sh with $ROOT (campaign root) and $OUT (task
output directory) set. Seeds come from grid.seed(stage, config id, block); a task name is
<stage>-<kind>-<config id>-b<block>, and the output lands in out/<stage>/<task name>.
"""
import json
import os
import sys

import grid

SAMPLER_FLAGS = "-signs 0,0.5,rand -pairs=false -qgrid 0 -sumc"


def sampler_task(B, stage, kind, r, block, trials, plant):
    s = grid.seed(f"{stage}-{kind}", r["id"], block)
    extra = "-plant-dup" if plant else "-keep 200"
    return f"""# stage {stage} kind {kind} config {r['id']} block {block} c={r['c']:.4f} load={r['load']:.4f}
echo "{r['M']} {r['k']} {r['d']} {trials}" > $OUT/spec
t0=$(date +%s.%N)
$ROOT/bin/{B['peelsim']} -spec $OUT/spec -seed {s} {SAMPLER_FLAGS} {extra} -chunk {trials} -jobs 1 -out $OUT/s -code-version {B['peelsim']} > $OUT/sampler.txt
t1=$(date +%s.%N)
$ROOT/bin/{B['r22replay']} -q $ROOT/bin/qtable.json -out $OUT/replay.json -jobs 1 -tn 0 $OUT/s
t2=$(date +%s.%N)
awk -v a=$t0 -v b=$t1 -v c=$t2 'BEGIN{{printf "sample\\t%.3f\\nreplay\\t%.3f\\n", b-a, c-b}}' > $OUT/steps.tsv
"""


def protocol_task(B, stage, r, block, trials, u):
    s = grid.seed(f"{stage}-p", r["id"], block)  # same seed for both u: paired keys and hashes
    arms = ["signed_raw_b", "signed_rchi_b", "signed_oracle"]
    if u == 0.01 and grid.vldb_defined(r["k"], r["M"]):
        arms += ["standard_vldb", "standard_vldb_b", "signed_vldb", "signed_vldb_b"]
    return f"""# stage {stage} kind p config {r['id']} u={u} block {block} load={r['load']:.4f}
echo "{r['k']} {r['M']} {r['d']} {r['common']} {r['onesided']}" > $OUT/spec
t0=$(date +%s.%N)
$ROOT/bin/{B['iblt2r']} -q $ROOT/bin/qtable.json -spec $OUT/spec -trials {trials} -jobs 1 -seed {s} -u {u} -arms {','.join(arms)} -out $OUT/proto.csv -trialout $OUT/trials.csv 2> $OUT/stderr.txt
t1=$(date +%s.%N)
awk -v a=$t0 -v b=$t1 'BEGIN{{printf "protocol\\t%.3f\\n", b-a}}' > $OUT/steps.tsv
"""


def t_trial(r):
    """Rough sampler cost per trial on the servers (seconds), from local timings x2."""
    return 2 * (10e-9 * r["M"] + 45e-9 * r["d"] * r["k"])


def pilot(B):
    tasks = {}
    for r in grid.c1() + grid.m64() + grid.v():
        if r["load"] >= 0.99:
            n = 1000
        else:
            n = int(min(3_000_000, max(2000, 120 / t_trial(r))))
        tasks[f"pilot-direct-{r['id']}-b000"] = sampler_task(B, "pilot", "direct", r, 0, n, False)
        if r["load"] < 1:
            tasks[f"pilot-plant-{r['id']}-b000"] = sampler_task(B, "pilot", "plant", r, 0, 1000, True)
    for r in grid.p():
        for u in (0.01, 0.05):
            tag = "u01" if u == 0.01 else "u05"
            tasks[f"pilot-p{tag}-{r['id']}-b000"] = protocol_task(B, "pilot", r, 0, 300, u)
    return tasks


def main_stage(B):
    """C1, M=64, V and P from frozen/main.json (freeze_main.py)."""
    F = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "frozen", "main.json")))
    tasks = {}
    for t in F["tasks"]:
        if t["stage"] == "p":
            tag = "u01" if t["u"] == 0.01 else "u05"
            tasks[f"p-{tag}-{t['id']}-b{t['block']:03d}"] = protocol_task(B, "p", t, t["block"], t["trials"], t["u"])
        else:
            tasks[f"{t['stage']}-{t['kind']}-{t['id']}-b{t['block']:03d}"] = sampler_task(
                B, t["stage"], t["kind"], t, t["block"], t["trials"], t["plant"])
    return tasks


def c1x_stage(B):
    """C1 supplement (grid.c1x): overload points, direct, 2e4 trials (Pr(F) = 1), cut into blocks of
    about 5 minutes using the replay cost of the neighbouring C1 load-3 runs (about 0.12 s per failure
    at M = 16384, below 0.01 s for M <= 4096)."""
    tasks = {}
    for r in grid.c1x():
        nb = 8 if r["M"] == 16384 else 1
        per = 20000 // nb
        for b in range(nb):
            tasks[f"c1x-direct-{r['id']}-b{b:03d}"] = sampler_task(B, "c1x", "direct", r, b, per, False)
    return tasks


V2_CONFIGS = (  # (k, M, d, pilot seconds per direct trial)
    (3, 1024, 32, 2.21e-5),
    (3, 4096, 512, 1.55e-4),
    (3, 4096, 1024, 2.17e-4),
    (3, 16384, 8192, 1.42e-3),
)


V2S_CONFIGS = (  # k = 4, 5: the cheapest planted C1 configurations, a small direct sample only
    (4, 256, 16, 9.0e-6),
    (4, 1024, 256, 6.3e-5),
    (4, 1024, 512, 9.9e-5),
    (5, 256, 64, 1.6e-5),
    (5, 256, 128, 2.5e-5),
    # added 2026-10-20 21:40 to fill the c axis, before any v2s block ran
    (4, 256, 8, 5.6e-6),
    (5, 256, 32, 1.1e-5),
    (4, 1024, 128, 4.5e-5),
)


def v2_stage(B, stage="v2", configs=V2_CONFIGS, target=65000):
    """V at low load (2026-10-20): direct against planted for planted C1 configurations that direct
    sampling can reach on CPU. Fixed trial counts, set before sampling: direct trials = round(target / lam)
    with lam = C(d,2)/C(M,k) the expected number of duplicate pairs (Pr(F) = lam (1 + o(1)) here), cut
    into blocks of about 30 minutes at the pilot cost per trial; planted 65000 trials in one block.
    Stage v2 is k = 3 with target 65000; stage v2s is k = 4, 5 with target 2000."""
    from math import comb
    tasks = {}
    for k, M, d, s_trial in configs:
        r = dict(id=grid.cid(k, M, d), k=k, M=M, d=d, c=d / M ** 0.5, load=d / (grid.ALPHA[k] * M))
        total = round(target * comb(M, k) / comb(d, 2))
        per = max(1, int(1800 / s_trial))
        nb = -(-total // per)
        for b in range(nb):
            n = min(per, total - b * per)
            tasks[f"{stage}-direct-{r['id']}-b{b:03d}"] = sampler_task(B, stage, "direct", r, b, n, False)
        tasks[f"{stage}-plant-{r['id']}-b000"] = sampler_task(B, stage, "plant", r, 0, 65000, True)
    return tasks


V3A_CONFIGS = (  # 2026-10-21: the two cheapest V2S configurations, raised to the k = 3 sample size
    (4, 256, 16, 9.0e-6),
    (5, 256, 128, 2.5e-5),
)
V3B_CONFIGS = tuple(c for c in V2S_CONFIGS if c[:3] not in {v[:3] for v in V3A_CONFIGS})


def v3_stage(B, stage, configs, target):
    """V at low load, second round (2026-10-21): fresh direct samples (new seeds) for the V2S
    configurations, whose 2000 direct failures left wide intervals. Targets fixed before sampling and
    chosen by cost alone: v3a = the two cheapest to 65000; v3b = the other six to 8000; v3c = the same
    six, 12000 more (pooled with v3b: 20000). The v2s planted samples (65000 each) are reused; v2s direct
    is not pooled. Equivalence is tested only on the final pool of each configuration."""
    from math import comb
    tasks = {}
    for k, M, d, s_trial in configs:
        r = dict(id=grid.cid(k, M, d), k=k, M=M, d=d, c=d / M ** 0.5, load=d / (grid.ALPHA[k] * M))
        total = round(target * comb(M, k) / comb(d, 2))
        per = max(1, int(1800 / s_trial))
        nb = -(-total // per)
        for b in range(nb):
            n = min(per, total - b * per)
            tasks[f"{stage}-direct-{r['id']}-b{b:03d}"] = sampler_task(B, stage, "direct", r, b, n, False)
    return tasks


def c2_stage(B, stage="c2"):
    """C2 confirmation points from frozen/c2.json (freeze_c2.py); c2x: the supplement in frozen/c2x.json."""
    F = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "frozen", f"{stage}.json")))
    return {f"{stage}-direct-{t['id']}-b{t['block']:03d}": sampler_task(B, stage, "direct", t, t["block"], t["trials"], False)
            for t in F["tasks"]}


if __name__ == "__main__":
    stage, bins, outdir = sys.argv[1:4]
    B = json.load(open(bins))
    tasks = {"pilot": pilot, "main": main_stage, "c2": c2_stage, "c2x": lambda B: c2_stage(B, "c2x"), "c2s": lambda B: c2_stage(B, "c2s"), "c1x": c1x_stage, "v2": v2_stage,
             "v2s": lambda B: v2_stage(B, "v2s", V2S_CONFIGS, 2000),
             "v3a": lambda B: v3_stage(B, "v3a", V3A_CONFIGS, 65000),
             "v3b": lambda B: v3_stage(B, "v3b", V3B_CONFIGS, 8000),
             "v3c": lambda B: v3_stage(B, "v3c", V3B_CONFIGS, 12000)}[stage](B)
    os.makedirs(outdir, exist_ok=True)
    for name, body in tasks.items():
        with open(os.path.join(outdir, name), "w") as f:
            f.write(body)
    print(len(tasks), "tasks written to", outdir)

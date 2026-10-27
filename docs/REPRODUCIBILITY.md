# Reproduction guide

## Local checks

Run commands from the repository root. `make build` compiles the sampler, replay executable, protocol executable, and sign-composition reducer into `bin/`. `make test` exercises the existing CDF/search/cache checks, adversarial decoder checks, resume checks, and sampler self-test. `make smoke` uses fixed small configurations with 200 sampler trials per mode and 100 protocol trials per configuration. It requires seconds to a few minutes on a laptop; the test suite may take longer.

`make figures` regenerates eleven figures from included summaries. Direct Python dependencies are pinned in `requirements.txt`; the tested transitive environment is recorded in `requirements-lock.txt`. Use the lock file for the validated environment. `python scripts/check_quantiles.py` independently checks the frozen comparator table. The command fails on any missing input or unsuccessful figure program. Figures retain the manuscript's original paths for traceability.

## Full campaigns

Frozen task definitions are under `sim/exp6/frozen/`. SHA-256 seed derivation is in `sim/exp6/grid.py`; stage, configuration id, and block distinguish streams. Generate the original main campaign scripts with:

```sh
make build
python3 sim/exp6/make_tasks.py main bin/bins.json outputs/tasks-main
```

Other supported stages include `c1x`, `c2`, `c2x`, `c2s`, `v2`, and `v2s`. Generation does not launch experiments. Inspect each script and estimate its cost before scheduling a full campaign. The original sample sizes can require substantial multicore CPU time, particularly for rare direct failures and exact sizing.

The generated scripts expect `ROOT` to identify this repository (containing `bin/`) and `OUT` to identify an empty output directory for one task. On Linux with Bash and GNU date, a single task can be run as follows, replacing TASK with an actual generated filename:

```sh
export ROOT="$PWD"
export OUT="$PWD/outputs/campaign/c1/TASK"
mkdir -p "$OUT"
bash -euo pipefail outputs/tasks-main/TASK
```

Use one output directory per task, log the exit status, command and environment, and retain checksums of binaries and inputs. Avoid whitespace in campaign paths: the historical generated scripts use unquoted path variables. Collect stage directories only after all expected tasks are complete. `python3 sim/exp6/collect.py RESULTS_DIR` checks the frozen main blocks and regenerates coverage/protocol tables. `python3 sim/exp6/c2_report.py C2_DIR` applies the frozen C2 stopping and confidence rules. These commands need task-level data, not just the bundled summary TSVs.

## Integrity

`make audit` verifies release hashes and scans tracked text for CJK characters and machine-specific home paths. After an intentional release change, regenerate `audit/SHA256SUMS.json` using `python3 scripts/audit.py --write`, review the changed manifest, and rerun the checks. Record package versions, OS, architecture, and CPU model with each release. Timing experiments additionally need CPU affinity, frequency policy, cache capacity, and repetitions.

# Reproduction guide

## Local checks

Run commands from the repository root. `make build` compiles the sampler, replay executable, protocol executable, and sign-composition reducer into `bin/`. `make test` exercises the existing CDF/search/cache checks, adversarial decoder checks, resume checks, and sampler self-test. `make smoke` uses fixed small configurations with 200 sampler trials per mode and 100 protocol trials per configuration. It requires seconds to a few minutes on a laptop; the test suite may take longer.

`make figures` regenerates the 14 paper figures from included summaries; the TikZ diagram `fig-structure` requires `pdflatex` and is skipped when it is unavailable. Direct Python dependencies are pinned in `requirements.txt`; the tested transitive environment is recorded in `requirements-lock.txt`. Use the lock file for the validated environment. `python scripts/check_quantiles.py` independently checks the frozen comparator table. The command fails on any missing input or unsuccessful figure program. Figures retain the manuscript's original paths for traceability.

`make tables` recomputes all 14 numerical paper tables, including exact enumeration. `make check-tables` runs generation and compares all numerical cells with the numeric-only CN reference. TSVs and the detailed comparison report are in `outputs/tables/`. For comparison with an independently supplied current CN tree, use `python scripts/check_tables.py --cn PATH`. The server-verified integer low-load input corrected one paper rounding error (first row of `tab:v-low`, planted miss/u: 0.94 to 0.95); the reference includes this correction. See `docs/SERVER-CHECK.md`. The two descriptive tables require no dataset. See `docs/EXPERIMENTS.md` for every label and source location.

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

## Historical server checks

`python scripts/server_replay_audit.py OUTPUT.go` generates a Go program that compares raw sampler chunks with every field of the archived replay groups. Compile it for the server and run `AUDITOR QTABLE TASK_DIRS.txt REPORT.json`; each input line names a sampler directory holding `manifest.json`. Sorting tasks by M,k,d reuses bounds across identical parameters. `--baseline` retains the original search order. The optimized search uses monotonicity in the observation S2, without assuming monotonicity in candidate n.

`python scripts/check_protocol_stopping.py RESULTS_DIR` checks protocol task hashes, pilot counts, frozen settings and aggregation. `RESULTS_DIR` must contain pilot.tsv, protocol.tsv, pilot/ and p/. `sim/exp6/ana/trialcheck/main.go` and `p_pairs.py` read the historical trial CSVs. `python sim/iblt2r/stress_report.py --complete CHECKPOINT...` verifies the complete decoder checkpoint and trial ranges. See `docs/SERVER-CHECK.md` for the executed inputs, hashes and results.

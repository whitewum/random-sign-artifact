# Historical server verification, 2026-10-28

All scientific counts reproduce the artifact. Exact low-load integer counts identify one manuscript rounding error: the first planted miss/u in `tab:v-low` must display **0.95**, rather than **0.94**. The manuscript cell has since been corrected and `audit/table-reference.json` refreshed, so all 14 numerical tables pass `make check-tables`.

Let `ARCHIVE_ROOT` be the shared historical archive directory and `CHECK_ROOT=$ARCHIVE_ROOT/artifact-check-20261028/run-01`. All new server files are under `CHECK_ROOT`. Historical inputs were read only. No simulations or scheduler jobs were started. Individual server commands were limited to at most 1,190 seconds; numerical workers used one CPU each. The original large replay process was stopped after 2,033 completed blocks to avoid repeated expensive searches; a faster exact search checked its remaining 180 blocks.

## Located inputs and executed checks

Paths below are relative to `ARCHIVE_ROOT`. File counts and sizes include supporting files in each selected directory, rather than just binary chunks. Detailed path/byte listings are stored at `CHECK_ROOT/inventory/` and travel with the compressed raw-data archive; their SHA-256 hashes are recorded in `audit/server-check-20261028/output-sha256.tsv`, alongside the two inventory JSON files.

| Item | Historical path | Files / bytes | Result |
| --- | --- | ---: | --- |
| Statistical and boundary samples | `exp6-20261016/out/{c1,c1x,m64}` | 9,856 / 293,742,677 | All replay groups match; coverage has 1,092 matching rows |
| Confirmation samples | `exp6-20261016/out/{c2,c2x,c2s}` | 34,064 / 496,569,795 | 48 + 4 + 36 summary rows match, including stopping and confidence bounds |
| Direct/planted validation | `exp6-20261016/out/{v,v2,v2s,v3a,v3b,v3c}` | 95,256 / 446,808,627 | All replay groups match; 33 full-KS rows match; all low-load count-derived rounded fields match |
| Protocol trials | `exp6-20261016/out/p` | 2,928 / 506,317,079 | 488 trial files, 15,370,184 trial rows; no trialcheck problems; 840 protocol/risk rows and 660 paired/score rows match |
| Pilot records | `exp6-20261016/out/pilot` | 4,880 / 648,608,661 | All 489 pilot summary rows match; frozen settings and all 488 protocol task hashes match |
| Decoder stress checkpoints | `peel-diag-20260927/decode-stress-20261015` | 21 / 28,472,470 | Six selected JSONL files contain 50,000 unique checkpoints and cover 500,000,000 trials; all counters and 375 configuration counts match |
| Decoder threshold/rejection | `peel-diag-20260927/{decode-threshold-20261021,decode-reject-20261021}` | 16 / 8,706,293 | All six JSONL payload hashes match bundled inputs; decode table regeneration passes |
| Distribution figure samples | `peel-diag-20260927/{confirm_plant,conv_plant}` | 454 / 1,080,066,240 | Six integer histograms match exactly; all 190 full-CDF rows recomputed with C1/C1x inputs |
| Sign-composition samples | `peel-diag-20260927/rs_cols` | 312 / 480,222,526 | All three JSON summaries match; 6,000,000 trials compared with old shared fields, zero mismatches |
| Encoding figure samples | `fig-encoding-20261021` | 208 / 144,793,208 | 100 seed CSVs, 4,000,000 mappings; histogram and statistics match byte for byte |
| Completed tasks, executables, frozen settings, timing/environment logs | `exp6-20261016/{queue,bin,frozen,logs,timing,out/T}` | See inventory groups | Located and inventoried; executable and checkpoint payload hashes recorded |

`regenerated/` contains the transferred compact outputs. `comparisons.json` records field counts and exactness. All 17,397 non-pilot sampler blocks, comprising 18,896,267 records, match every `groups` field in the historical replay JSON, including miss/empty counts and width histograms. The 190 conditional-moment rows also match. Coverage and confirmation summaries were then reaggregated using their original programs. Pilot summary regeneration uses the recorded historical timings; it does not repeat the original sampler or timing measurements.

There are three explicitly bounded non-byte-equalities:

- Distribution `limit_ks.tsv`: 67 floating fields differ by at most 4.22e-15; integer counts match. The six figure histograms match exactly.
- Decoder `worker_seconds`: sum-order differences of at most 1.75e-9 seconds; configuration `seconds` differ by at most 8.19e-12 seconds. Every non-timing field matches.
- `protocol-stopping.json`: the environment field `local_trial_csv_files` is 488 on the server and 0 in the artifact. All scientific and task-validation fields match.

## Resolved rounding boundaries

All rows use u=0.05. Each `miss/n_fail` is an integer count pair. Rates and 95% normal difference intervals are computed directly from these counts.

| (k,M,d) | Direct miss/n_fail | Planted miss/n_fail | Previously rounded boundary | Exact value | Correct display |
| --- | ---: | ---: | --- | ---: | --- |
| (3,1024,32) | 3057/65061 | 3072/65000 | planted miss/u = 0.945 | 0.945230769230769... | 0.95 |
| (3,4096,1024) | 2998/65136 | 3058/65000 | upper difference endpoint = +0.025 | +0.025391534022724... | +0.03 |
| (4,1024,256) | 992/20265 | 3141/65000 | lower difference endpoint = -0.055 | -0.055384631216435... | -0.06 |

Only the first row needs a manuscript correction: research CN `appendix/H-experiments.tex:49`, research EN `appendix/H-experiments.tex:58`, and the artifact EN `manuscript/random-sign/EN/appendix/H-experiments.tex:58`, from `0.94 / 0.94` to `0.94 / 0.95`; this correction has been applied. The other 11 rows and every displayed interval remain correct. `rounding-boundaries.json` preserves the numerical details, and `sim/results/exp6-20261016/ana/low-load-counts.tsv` supplies all 48 count rows for both u values.

## Archival recommendation

The recommended server input set contains **185,892 files, 6,107,788,635 bytes** (6.108 decimal GB; uncompressed). It includes the complete exp6 campaign, the located distribution/decoder/encoding/composition directories, and only the old reference configurations needed by the composition comparison: `round1_AB/{manifest.json,cfg_005,cfg_010}` and `round2_k56/{manifest.json,cfg_000,cfg_010}`. The two historical decoder source tarballs were copied from the read-only research repository into `CHECK_ROOT` and are included (29,088 bytes). The artifact release and this new verification workspace are separate from the historical-input total.

`zenodo-summary.json` lists exact per-directory counts/sizes and the seven server listing parts `CHECK_ROOT/inventory/zenodo-files.00.tsv` through `.06.tsv`. Each listing part is under 2 MB. The SHA-256 of the logical sorted path/size listing (one header) is:

```text
81b026c644c9280e7edf526ad208e3a70d10dc7d9e2ccf0d1a486cbbb5f0caab
```

The broader discovery inventory also lists unused configurations from the old reference batches: 191,604 files and 42,588,844,515 bytes. Those extra configurations are excluded from the recommendation. The source tarballs are additional to that discovery inventory.

Inventory hashes certify path/size lists, not raw payload contents. `input-sha256.tsv` and `supplement-sha256.tsv` additionally contain actual payload hashes for the six decoder checkpoint inputs, historical binaries and frozen settings, and all 100 encoding CSVs. `decoder-input-sha256.txt` matches the six threshold/rejection JSONL inputs to the bundled bytes. `output-sha256.tsv` records server output/source hashes. The compressed archive `random-sign-raw-20261028.tar.xz` (SHA-256 `f7af591fc9f9b905741583f96ac7762646d2f41c405aa0fbeaf53bda345024c7`, 185,935 entries) is published as an asset of the GitHub release v0.1.2, https://github.com/whitewum/random-sign-artifact/releases/tag/v0.1.2. Historical source-to-binary association remains a distinct provenance question, as described in `DATA.md`.

## Reproduction and server outputs

- `sim/exp6/collect.py`, `pilot_report.py`, and `c2_report.py` ran in a new writable view whose stage directories link to historical inputs. Its outputs are under `CHECK_ROOT/sim/results/exp6-20261016/` and `CHECK_ROOT/results/`.
- `scripts/server_replay_audit.py` generates the replay auditor from the bundled sizing implementation. `--baseline` uses the original exhaustive search. The default evaluates distinct S2 observations in descending order: for each fixed candidate n, acceptance is nondecreasing in S2, so the preceding U is an upper bound for the next search. This does not assume monotonicity in candidate n. Both variants check every historical replay group field. Baseline small/prefix results plus the optimized remainder cover all tasks without gaps. The final portable generator was also cross-compiled on macOS and checked on 12 already validated blocks.
- `scripts/check_protocol_stopping.py` reran the stopping audit with the portable result-directory argument. Its JSON matches the initial server audit. `trialcheck`, `p_pairs.py` and `p_pairs_score.py` ran on the actual protocol trial CSVs.
- `fullks`, `limit_ks.py`, `a_moments.py`, `rscol -ref`, and `fig-encoding-agg` read the corresponding raw records. `stress_report.py --complete` used the repartition baseline, three phase-two files and two finish files, excluding the overlapping early full/pilot files.
- New server files are contained in `CHECK_ROOT/{results,inventory,distribution,encoding,rs-columns,pairs,sim,scripts,data,reference,go-cache}` plus source files, binaries, task lists, logs and the two source tarballs at its top level. `server-files.tsv` lists all regular file paths and sizes created there, including the build cache; historical input symlinks do not duplicate payloads. `raw-plan.json` certifies the exact prefix/remainder split.

Local checks use the existing locked `.venv` environment. `make tables` succeeds; `make check-tables` passes all 14 numerical tables after the correction. The integrity audit is refreshed after all evidence is written. No commit was created.

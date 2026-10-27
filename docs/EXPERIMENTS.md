# Experiment map

| Paper topic / figure | Executable or analysis | Included evidence | Reproduction level |
| --- | --- | --- | --- |
| Encoding bias, `fig-encoding` | `sim/peelsim/main.go`, figure script | Encoding histograms and moments | Replot |
| Sign composition, `fig-composition` | `sim/peelsim/rscol/main.go` | `rs-columns-20261018/*.json` | Replot |
| Paired decoding equivalence | `sim/iblt2r/stress.go` | `decode-stress-20261015/final-*` | Tests and summary; full checkpoints pending |
| Crossover distribution, `fig-crossover-cdf` | `sim/peelsim/distribution.py`, `sim/exp6/ana/limit_ks.py` | `distribution-fix-20261022/crossover_hist.json`, `limit_ks.tsv` | Replot |
| Coverage and extra capacity, `fig-coverage` | `r22replay.go`, `sim/exp6/collect.py` | `coverage.tsv` | Smoke rerun and replot |
| Independent confirmation, `fig-confirm` | `sim/exp6/c2_report.py` | Frozen C2 tasks and `c2.tsv` | Replot; raw records pending |
| Two-round protocol, `fig-protocol` | `sim/iblt2r/`, `collect.py` | `protocol.tsv` | Smoke rerun and replot |
| Table-size scaling, `fig-scale` | Figure script | Protocol, coverage, C2/C2s/C2x TSVs | Replot |
| Sizing cost, `fig-sizing` | `r22replay.go` timing mode | `T/sizing*.json`, protocol timing CSVs | Replot; timing environment needs archival |
| Planted vs direct, `fig-planted` | `sim/exp6/ana/v*_*.py`, `sim/exp6/ana/fullks/` | `ana/v3/`, `ana/fullks.tsv`, coverage table | Replot |
| Experiment configurations, `fig-exp-grid` | `sim/exp6/grid.py` | Frozen tasks and coverage table | Replot |
| Null distribution, `fig-aux` | Figure script | Analytic calculation | Regenerate |
| Decoder rejected candidates, `fig-decode` | `sim/iblt2r/reject.go` | `decode-reject-20261021/*.jsonl`, `decode-threshold-20261021/*.jsonl` | Replot |
| Standard IBLT post-failure bias, `fig-bias` | Figure script | `tail/calib.csv` | Replot |
| Encoding diagram, `fig-structure` | `fig-structure.tex` (TikZ) | None | Regenerate with pdflatex |

The main statistical figure includes 189 configurations: the original C1 campaign plus its C1x supplement. The protocol study has 120 configurations, each evaluated at two risk levels. Experiment status here describes files present in this artifact, independently of the status of server-side jobs.

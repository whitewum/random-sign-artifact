# Experiment map

| Paper topic / figure | Executable or analysis | Included evidence | Reproduction level |
| --- | --- | --- | --- |
| Encoding bias, `fig-encoding` | `sim/peelsim/main.go`, figure script | Encoding histograms and moments | Replot |
| Sign composition, `fig-composition` | `sim/peelsim/rscol/main.go` | `rs-columns-20261018/*.json` | Replot |
| Paired decoding equivalence | `sim/iblt2r/stress.go` | `decode-stress-20261015/final-*` | Tests and summary; full checkpoints pending |
| Crossover distribution, `fig-crossover-cdf` | `sim/peelsim/exp4_report.py` | `rand-cross2/data/exp4_summary.json` | Replot |
| Coverage and extra capacity, `fig-coverage` | `r22replay.go`, `sim/exp6/collect.py` | `coverage.tsv` | Smoke rerun and replot |
| Independent confirmation, `fig-confirm` | `sim/exp6/c2_report.py` | Frozen C2 tasks and `c2.tsv` | Replot; raw records pending |
| Two-round protocol, `fig-protocol` | `sim/iblt2r/`, `collect.py` | `protocol.tsv` | Smoke rerun and replot |
| Table-size scaling, `fig-scale` | Figure script | Protocol, coverage, C2/C2s/C2x TSVs | Replot |
| Sizing cost, `fig-sizing` | `r22replay.go` timing mode | `T/sizing*.json`, protocol timing CSVs | Replot; timing environment needs archival |
| Planted vs direct, `fig-planted` | `sim/exp6/ana/v*_*.py` | `ana/v/`, `ana/v2/`, coverage table | Replot |
| Experiment configurations, `fig-exp-grid` | `sim/exp6/grid.py` | Frozen tasks and coverage table | Replot |
| Null distribution, `fig-aux` | Figure script | Analytic calculation | Regenerate |
| Decoder rejected candidates | `sim/iblt2r/reject.go` | Source only | Results pending in this snapshot |

The main statistical figure includes 189 configurations: the original C1 campaign plus its C1x supplement. The protocol study has 120 configurations, each evaluated at two risk levels. Experiment status here describes files present in this artifact, independently of the status of server-side jobs.

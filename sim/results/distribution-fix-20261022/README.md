# Distribution validation and planted-sampler fix (2026-10-22)

`sim/peelsim/distribution.py` implements the integer-lattice limit distribution $G_d$ of the manuscript (the equal-weight ±2 term plus the Skellam term) and KS distances evaluated on both sides of every atom of a discrete CDF. `sim/exp6/ana/limit_ks.py` recomputes all distances from the raw failure records without binning or tail truncation; the discrete check uses $\widetilde d$ and the Gaussian CLT check uses $\widehat d$.

| File | Content |
| --- | --- |
| `limit_ks.tsv` | 190 source/configuration rows with at least 1000 failures; the manuscript tables use 36 fixed-$c$ configurations and 75 direct configurations with $c\ge8$ |
| `crossover_hist.json` | Full integer-lattice counts, inputs, program version, and seeds for the six configurations of `fig-crossover-cdf` |
| `summarize.py`, `table-summary.txt` | Table reconstruction; all 36 distances agree with an independent computation to within 1e-12 |
| `check_sampler.py`, `sampler-regression.txt` | CLI regression of the planted sampler |
| `go-tests.txt`, `figure-metrics.txt` | Test log and figure metrics |

KS distances of the six plotted configurations:

| $c$ | to $G_d$ | to Gaussian |
| ---: | ---: | ---: |
| 0.25 | 0.0045 | 0.4964 |
| 0.5 | 0.0051 | 0.4392 |
| 1 | 0.0038 | 0.2249 |
| 2 | 0.0029 | 0.0862 |
| 4 | 0.0027 | 0.0325 |
| 8 | 0.0027 | 0.0153 |

The planted sampler (`-plant-dup` in `sim/peelsim/main.go`) now selects the duplicated label pair uniformly with an independent random stream and records `plant_scheme=uniform-pair-v1` in the manifest; resuming an output directory written by the earlier fixed-last-pair scheme is rejected. The direct random stream is unchanged. In a 30,000-trial fixed-composition regression, the balanced mean deviation is -0.4032 (theory -0.4) and the iid mean deviation is 0.0097 (theory 0); all 15 label pairs are drawn with frequencies within tolerance, and every planted mapping fails. Direct chunks are byte-identical to the previous version; new planted chunks are byte-identical across 1 and 2 workers.

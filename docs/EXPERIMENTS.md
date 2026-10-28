# Experiment map

The authority for this inventory is the CN manuscript snapshot dated 2026-10-28. It contains 14 figures, 14 numerical tables and two descriptive tables (30 items). The bundled EN manuscript body is unchanged. Source locations below are relative to the research repository; no CN prose is copied into this artifact. `audit/paper-inventory.json` records the source hashes and label lines.

All figure filenames below are relative to `manuscript/random-sign/figure/`. Numerical table programs are functions in `scripts/tables.py`; `make tables` writes `outputs/tables/tab-<name>.tsv` and `make check-tables` checks every numerical cell against `audit/table-reference.json`.

| Label | CN source:label line | Program | Artifact input | Reproduction level |
| --- | --- | --- | --- | --- |
| `notations (unlabeled)` | `appendix/A-notations.tex:4` | `None` | `None (descriptive)` | No data required |
| `tab:exact` | `appendix/C-encoding.tex:58` | `scripts/tables.py:exact` | `theory/diagnostics/random-sign-encoding-exact.json (cases); theory/scripts/check_random_sign_encoding.py` | Exact recomputation |
| `fig:exp-grid` | `appendix/H-experiments.tex:25` | `fig-exp-grid.py` | `sim/results/exp6-20261016/coverage.tsv` | Replot |
| `tab:v-low` | `appendix/H-experiments.tex:42` | `scripts/tables.py:planted` | `sim/results/exp6-20261016/ana/{low-load-counts.tsv,v2/v2.tsv,v3/v3a.tsv,v3/v3bc.tsv,fullks.tsv}` | Recompute from integer counts |
| `tab:v` | `appendix/H-experiments.tex:71` | `scripts/tables.py:planted` | `sim/results/exp6-20261016/{coverage.tsv,ana/fullks.tsv}` | Reaggregate |
| `fig:planted` | `appendix/H-experiments.tex:111` | `fig-planted.py` | `sim/results/exp6-20261016/{coverage.tsv,ana/fullks.tsv,ana/v2/v2*.tsv,ana/v3/v3*.tsv}` | Replot |
| `fig:decode` | `appendix/H-experiments.tex:132` | `fig-decode.py` | `sim/results/decode-reject-20261021/*.jsonl` | Replot |
| `tab:decode-paired` | `appendix/H-experiments.tex:138` | `scripts/tables.py:decoding` | `sim/results/decode-stress-20261015/final-summary.json` | Reaggregate |
| `tab:mean-by-k` | `appendix/H-experiments.tex:164` | `scripts/tables.py:composition` | `sim/results/rs-columns-20261018/{k3,k4,k56}.json; sim/results/tail/calib.csv` | Reaggregate |
| `tab:limit-ks` | `appendix/H-experiments.tex:196` | `scripts/tables.py:limits` | `sim/results/distribution-fix-20261022/limit_ks.tsv` | Reaggregate |
| `tab:extra` | `appendix/H-experiments.tex:226` | `scripts/tables.py:coverage` | `sim/results/exp6-20261016/coverage.tsv` | Reaggregate |
| `tab:gauss-c` | `appendix/H-experiments.tex:256` | `scripts/tables.py:coverage` | `sim/results/exp6-20261016/coverage.tsv` | Reaggregate |
| `tab:confirm` | `appendix/H-experiments.tex:283` | `scripts/tables.py:confirm` | `sim/results/exp6-20261016/c2.tsv` | Recompute exact confidence bounds |
| `tab:e2e` | `appendix/H-experiments.tex:318` | `scripts/tables.py:protocol` | `sim/results/exp6-20261016/protocol.tsv` | Reaggregate |
| `tab:vldb` | `appendix/H-experiments.tex:353` | `scripts/tables.py:protocol` | `sim/results/exp6-20261016/protocol.tsv` | Reaggregate |
| `fig:sizing` | `appendix/H-experiments.tex:393` | `fig-sizing.py` | `sim/results/exp6-20261016/T/sizing*.json` | Replot |
| `tab:dec-ratio` | `appendix/H-experiments.tex:403` | `scripts/tables.py:timing` | `sim/results/exp6-20261016/T/proto2-*.csv` | Reaggregate recorded timing |
| `fig:bias` | `sections/02-model.tex:51` | `fig-bias.py` | `sim/results/tail/calib.csv` | Replot |
| `fig:structure` | `sections/03-design.tex:52` | `fig-structure.tex; scripts/structure.py` | `sim/results/analytic/structure-mapping.json` | Regenerate |
| `fig:aux` | `sections/05-inversion.tex:63` | `fig-aux.py` | `sim/results/analytic/aux-parameters.json` | Regenerate |
| `fig:encoding` | `sections/06-experiments.tex:27` | `fig-encoding.py` | `manuscript/random-sign/figure/fig-encoding-{hist,stats}.csv` | Replot |
| `fig:composition` | `sections/06-experiments.tex:35` | `fig-composition.py` | `sim/results/rs-columns-20261018/{k3,k4,k56}.json` | Replot |
| `tab:decode` | `sections/06-experiments.tex:44` | `scripts/tables.py:decoding` | `sim/results/decode-threshold-20261021/*.jsonl` | Reaggregate |
| `fig:crosscdf` | `sections/06-experiments.tex:68` | `fig-crossover-cdf.py` | `sim/results/distribution-fix-20261022/crossover_hist.json` | Replot |
| `fig:coverage` | `sections/06-experiments.tex:84` | `fig-coverage.py` | `sim/results/exp6-20261016/coverage.tsv` | Replot |
| `fig:confirm` | `sections/06-experiments.tex:90` | `fig-confirm.py` | `sim/results/exp6-20261016/c2.tsv` | Replot |
| `fig:protocol` | `sections/06-experiments.tex:112` | `fig-protocol.py` | `sim/results/exp6-20261016/protocol.tsv` | Replot |
| `fig:scale` | `sections/06-experiments.tex:120` | `fig-scale.py` | `sim/results/exp6-20261016/{protocol,coverage,c2,c2x,c2s}.tsv` | Replot |
| `tab:proto` | `sections/06-experiments.tex:136` | `scripts/tables.py:timing` | `sim/results/exp6-20261016/T/proto2-*.csv` | Reaggregate recorded timing |
| `tab:sizing-options` | `sections/06-experiments.tex:157` | `None` | `None (descriptive)` | No data required |

The statistical campaign has 189 configurations (C1 plus C1x); the protocol campaign has 120 configurations evaluated at two risk levels. Figure comparisons establish agreement of the programs, input summaries and analytic parameters with the authority; they do not claim byte-identical PDF rendering. Thirteen numerical tables agree at the displayed precision. Exact server-side integer counts resolve the low-load rounding boundaries and identify one manuscript error: the planted value in the first row of `tab:v-low` is 0.95, while the manuscript prints 0.94. The manuscript and numeric comparison oracle remain unchanged; `make check-tables` reports this one differing cell. See `docs/SERVER-CHECK.md`.

Additional reproducibility paths remain available: `sim/iblt2r/stress.go` checks paired decoding, `sim/exp6/ana/e2e_table.py` independently summarizes protocol arms, `freeze_main.py` regenerates frozen protocol settings from `pilot.tsv`, and `ana/protocol-stopping.json` and `ana/trialcheck.json` record historical stopping and per-trial audits. These checks were executed against the server archive on 2026-10-28, including all 488 protocol trial files and all 17,397 main/confirmation/validation sampler blocks. Compact evidence and input-list hashes are bundled in `audit/server-check-20261028/`; the raw archive is still needed to execute them again. See `docs/SERVER-CHECK.md`.

The upstream figure directory has no updated Python or TikZ programs relative to the initial artifact. The three new Markdown explanations were translated to English. The legacy trial CSV and Peeling Lens sampling wrapper are deliberately excluded; the current figure uses the bundled 4-million-mapping summaries. Analytic plots and the illustrative diagram now read explicit bundled JSON inputs and also export numerical TSVs.

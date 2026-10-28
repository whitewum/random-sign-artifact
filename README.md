# Random-sign IBLT research artifact

An executable research artifact for random-sign invertible Bloom lookup tables (IBLTs): failure-conditioned estimation, Gaussian and Skellam sizing rules, and two-round set reconciliation.

This release provides the English manuscript, the simulation and protocol implementations, frozen experimental configurations, selected numerical summaries, and programs for all 14 paper figures and 14 numerical paper tables. It supports local smoke experiments and regeneration of figures from bundled summaries. The inventory also maps the two descriptive tables, which need no numerical data. Full reproduction of the original large-scale campaigns requires the trial records described in [Data availability](docs/DATA.md).

## Quick start

Requirements: Go 1.23 or later, Python 3.11 to 3.13 (the pinned SciPy has no wheel for 3.14), and Make. Go programs use only the standard library. No GPU or server account is required for the smoke experiment.

```sh
make build
make test
make smoke
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-lock.txt
make figures
make tables
make check-tables
make audit
```

The smoke experiment runs direct and planted sampling, replays both sizing rules, and runs paired two-round reconciliation with fixed seeds. Results are written to `outputs/smoke/`. Numerical tables are written to `outputs/tables/tab-<name>.tsv`; `make check-tables` compares every numerical cell with a numeric-only snapshot (`audit/table-reference.json`) of the current manuscript revision, including the `tab:v-low` rounding correction found by the [server verification](docs/SERVER-CHECK.md). The bundled English manuscript predates this revision; its tables and appendix will be updated in the next release. Figure PDFs and PNGs are written to `manuscript/random-sign/figure/`. These small runs test execution and consistency; published statistical precision requires the full sample sizes.

## Contents

| Path | Purpose |
| --- | --- |
| `sim/peelsim/` | Plain mapping sampler, record reader, distribution analysis |
| `sim/iblt2r/` | Real additive IBLT, sizing implementation, paired decoder audit and tests |
| `sim/exp6/` | Configuration and seed generation, frozen tasks, aggregation and analysis |
| `theory/scripts/random_sign_crossover.py` | High-precision reference CDF |
| `sim/results/` | Figure and table inputs and decoder audit summaries |
| `manuscript/random-sign/EN/` | English manuscript source and PDF (CC BY 4.0) |
| `manuscript/random-sign/figure/` | Figure programs and encoding histograms |
| `audit/` | Source provenance and integrity manifests |

See [validation results](docs/VALIDATION.md), [reproduction instructions](docs/REPRODUCIBILITY.md), [experiment map](docs/EXPERIMENTS.md), [audit notes](docs/AUDIT.md), and [data availability](docs/DATA.md). Internal filenames retain historical labels for traceability: `raw` denotes the Skellam rule and `rchi` denotes the implemented Gaussian-rule comparison. Their exact numerical definitions are documented in the audit notes.

## License and citation

Code, included numerical data, and documentation are distributed under the [MIT License](LICENSE). The manuscript in `manuscript/random-sign/EN/` is licensed under [CC BY 4.0](manuscript/random-sign/EN/LICENSE). Dependencies retain their own licenses; see [THIRD_PARTY.md](THIRD_PARTY.md). Citation metadata is in [CITATION.cff](CITATION.cff). The paper identifier and archival artifact DOI will be added when available.

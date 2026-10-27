# Random-sign IBLT research artifact

An executable research artifact for random-sign invertible Bloom lookup tables (IBLTs): failure-conditioned estimation, Gaussian and Skellam sizing rules, and two-round set reconciliation.

This initial snapshot provides the simulation and protocol implementations, frozen experimental configurations, selected numerical summaries, and scripts for eleven paper figures. It supports local smoke experiments and regeneration of figures from bundled summaries. Full reproduction of the original large-scale campaigns requires the trial records described in [Data availability](docs/DATA.md).

## Quick start

Requirements: Go 1.23 or later, Python 3.11 or later, and Make. Go programs use only the standard library. No GPU or server account is required for the smoke experiment.

```sh
make build
make test
make smoke
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-lock.txt
make figures
make audit
```

The smoke experiment runs direct and planted sampling, replays both sizing rules, and runs paired two-round reconciliation with fixed seeds. Results are written to `outputs/smoke/`. Figure PDFs and PNGs are written to `manuscript/random-sign/figure/`. These small runs test execution and consistency; published statistical precision requires the full sample sizes.

## Contents

| Path | Purpose |
| --- | --- |
| `sim/peelsim/` | Plain mapping sampler, record reader, distribution analysis |
| `sim/iblt2r/` | Real additive IBLT, sizing implementation, paired decoder audit and tests |
| `sim/exp6/` | Configuration and seed generation, frozen tasks, aggregation and analysis |
| `theory/scripts/random_sign_crossover.py` | High-precision reference CDF |
| `sim/results/` | Selected published-figure inputs and decoder audit summaries |
| `manuscript/random-sign/figure/` | Figure programs and encoding histograms |
| `audit/` | Source provenance and integrity manifests |

See [validation results](docs/VALIDATION.md), [reproduction instructions](docs/REPRODUCIBILITY.md), [experiment map](docs/EXPERIMENTS.md), [audit notes](docs/AUDIT.md), and [data availability](docs/DATA.md). Internal filenames retain historical labels for traceability: `raw` denotes the Skellam rule and `rchi` denotes the implemented Gaussian-rule comparison. Their exact numerical definitions are documented in the audit notes.

## License and citation

Code, included numerical data, and documentation are distributed under the [MIT License](LICENSE). Dependencies retain their own licenses; see [THIRD_PARTY.md](THIRD_PARTY.md). Citation metadata is in [CITATION.cff](CITATION.cff). The paper identifier and archival artifact DOI will be added when available.

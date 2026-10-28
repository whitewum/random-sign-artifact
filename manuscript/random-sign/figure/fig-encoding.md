# Encoding comparison on the same mappings

`fig-encoding.py` reads `fig-encoding-hist.csv` and `fig-encoding-stats.csv`. The published run used k=3, M=16384, d=13314, 100 seeds and 40,000 mappings per seed (4 million mappings). Each mapping supplied the standard one-sided, standard balanced and independent random-sign statistics. Random signs used a separate random stream without changing mappings. The centered estimate is `(sum(C_v^2) - sum(C_v)^2/M) / (k*(1-k/M))`; its normalization is `sqrt(2*d*(d-1)/(M-1))`.

There were 500,904 failures (rate 0.125226). The histogram has 40 bins over [-4,4], with all-sample and failure counts and NumPy-compatible bin boundaries. The statistics summary includes the failure mean, standard error, variance and KS distance between failed and all observations. `fig-encoding-agg/` aggregates the historical per-seed CSV files, which remain in the server archive; the plotting program needs only the bundled summaries.

The upstream `fig-encoding.csv` contains 40,000 individual trials from seed 1. It is an obsolete, smaller sample, not the input to the current published figure, and is intentionally excluded. The upstream `fig-encoding.mjs` uses the separate Peeling Lens application to generate historical trials; it is not needed for summary reproduction and is not bundled. Local smoke experiments use the included `sim/peelsim/` implementation.

Run `make figures` to regenerate the published plot. Full historical sampling requires the archive described in `docs/DATA.md`.

# Skellam sizing time

`fig-sizing.py` reads `sim/results/exp6-20261016/T/sizing.json` and `sizing-c1x.json`. Measurements use M=16384, k=3,4,5, u=0.01, one pinned CPU core at 2.0 GHz, the first 200 failure observations per configuration and ten repetitions. Each point is the median of the ten per-observation mean times. Configurations with c<4 are omitted. The cache holds 16 million entries (approximately 256 MB).

The horizontal axis is `d/(alpha_c*M)`. At fixed M it is proportional to `c=d/sqrt(M)`; the k-dependent threshold shifts the curves horizontally. Cold starts with an empty cache at every observation. Session preserves Poisson tables across new observations at fixed (M,k). Warm immediately recomputes the same observation. At load 3, session requests exceed the cache limit, causing eviction and reconstruction.

The timing machine had two Intel Xeon Silver 4410Y CPUs, 24 physical cores and 48 logical CPUs. Original environment and frequency logs exist upstream under the timing directory; they contain machine-specific paths and are not bundled in this portable release. The data can reproduce the recorded measurements, while rerunning the benchmark requires equivalent hardware and process isolation. Earlier r22 measurements used a smaller cache and are not inputs to this figure.

Run `make figures` to regenerate the plot.

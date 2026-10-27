# Paired first-round decoding near the threshold (2026-10-21)

Input of the decoding table in Section 6.2 of the manuscript. Produced by `sim/iblt2r` with `-decode-threshold`; each trial calls `stressPair` (`stress.go`) with all correctness assertions and per-encoding counts (field definitions in `../decode-reject-20261021/README.md`).

Configuration: $k\in\{3,4,5,6,10\}$, $M\in\{1024,16384,65536\}$, load $d/(\alpha_c M)\in\{0.90,0.95,0.97,0.98,0.99,1,1.01,1.02,1.03,1.05\}$, $d_-/d\in\{0,1/2\}$, 300 configurations. Trials per configuration: 100,000 for $M=1024$, 20,000 for $M=16384$, 10,000 for $M=65536$; 13 million paired trials in total, chunk 5000, seed 2026102102. The three JSONL files are shards from three worker machines with 2600 unique tasks and no duplicates. Executable SHA-256 `5380550214cbe398799dfc5a9dcc4e35cb548126aed21161c6bdc887c3ed6ec4`.

All trials pass the assertions: the two encodings succeed or fail together in every trial, every acceptance is a true degree-one cell, and the recovered set and directions match an unsigned 2-core reference. Across both decoders there are 97,937,109,392 acceptances and 71,236,384,626 rejected candidates, with `MemRej` zero.

Failure probability (both compositions pooled), loads 0.98 / 1 / 1.02:

| $k$ | $\alpha_c$ | $M=1024$ | $M=16384$ | $M=65536$ |
| ---: | ---: | --- | --- | --- |
| 3 | 0.818 | 0.298 / 0.715 / 0.958 | 0 / 0.648 / 1 | 0 / 0.619 / 1 |
| 4 | 0.772 | 0.266 / 0.743 / 0.977 | 0 / 0.654 / 1 | 0 / 0.620 / 1 |
| 5 | 0.702 | 0.268 / 0.756 / 0.975 | 0 / 0.661 / 1 | 0 / 0.629 / 1 |
| 6 | 0.637 | 0.284 / 0.740 / 0.971 | 0 / 0.665 / 1 | 0 / 0.627 / 1 |
| 10 | 0.461 | 0.383 / 0.759 / 0.966 | 0 / 0.663 / 1 | 0 / 0.630 / 1 |

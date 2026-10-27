# Rejected first-round candidates by encoding (2026-10-21)

Input of `manuscript/random-sign/figure/fig-decode.py`. Produced by `sim/iblt2r` with `-decode-reject`; each trial calls `stressPair` (`stress.go`), the paired decoder with all correctness assertions of the decoding-equivalence experiment, and returns counts for each encoding.

Configuration: $M=16384$, $k\in\{3,4,5,6,10\}$, load $d/(\alpha_c M)\in\{0.5,0.95,1\}$, $d_-/d\in\{0,1/8,\dots,1\}$ (field `Fraction`), 135 configurations, 50,000 paired trials each, chunk 5000, seed 2026102101. Executable SHA-256 `e9cc68739f3a2b5fb17b868a6b64cf663e63228474524efefff1889a593ac39b`.

Per-encoding fields: `Cand` counts popped cells with count ±1; `Rej` counts those failing the checksum or cell-membership check (`MemRej` is the latter); `Fake` counts initial cells with count ±1 and degree at least 2; `Accepted` counts accepted recoveries; `Rej2` and `Fake2` are per-trial sums of squares.

The three JSONL files are shards from three worker machines. One shard was launched twice, producing 103 duplicate tasks; the trials are deterministic, and `fig-decode.py` checks that duplicates agree in every field except `seconds` and requires 1350 unique tasks.

All 6.75 million paired trials pass the assertions and `MemRej` is zero. Rejected candidates per decoding divided by $d$ at load 1:

| $k$ | standard, one-sided | standard, balanced | random sign, nine compositions |
| ---: | ---: | ---: | --- |
| 3 | 0 | 0.361 | 0.3605 to 0.3607 |
| 4 | 0 | 0.544 | 0.5436 to 0.5447 |
| 5 | 0 | 0.694 | 0.6927 to 0.6941 |
| 6 | 0 | 0.825 | 0.8246 to 0.8256 |
| 10 | 0 | 1.274 | 1.2738 to 1.2775 |

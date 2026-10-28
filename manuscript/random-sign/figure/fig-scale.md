# Table size and protocol performance

`fig-scale.py` reads `sim/results/exp6-20261016/{protocol,coverage,c2,c2x,c2s}.tsv` and writes `fig-scale.{pdf,png,csv}`.

The selection is balanced differences, target load 1.5 and u=0.01, with M1 in {256,1024,4096,16384} and k in {3,4,5}. Integer rounding gives actual loads between 1.497 and 1.502; the script accepts deviations at most 0.005 and checks that each size has exactly three k values.

The upper panels pool first-round failures and miss counts from protocol, C1 and the independent C2/C2x/C2s direct-sampling campaigns for each configuration. Each protocol configuration contributes 20,000 failures. The pooled points have 331,000 to 372,000 failures and normal-approximation 95% intervals. Common elements cancel from the random-sign difference table; the balanced lower bound |b|<=1 does not change sizing, so these campaigns estimate the same conditional miss rate.

The lower panels use only protocol observations, paired with the oracle at the same id and u: `100*(mean_bytes/oracle.mean_bytes-1)`. The generated CSV records counts and contributing campaigns for each point.

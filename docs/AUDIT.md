# Scientific and release audit

## Scope

The implementations and frozen settings are preserved from the research workspace, including current decoder changes. `audit/source-manifest.json` records the source commit, copied-file hashes, and working-tree changes. Packaging introduces build, smoke, figure, and integrity commands and removes an unused STD-specific import from the shared plotting helper. No numerical summary is edited.

## Resolved items (2026-10-27)

1. **Protocol stopping rule.** The P campaign uses trial counts frozen from the pilot by `sim/exp6/freeze_main.py`: $\lceil 2\times10^4/\widehat{\Pr}(F_1)\rceil$ per configuration, capped at 3,000,000, and a fixed 100,000 for the 13 configurations with no first-round failure in the pilot. Both levels of $u$ share the same trials. The manuscript (Section 6.5 and Appendix H) now states this rule. Regenerating the frozen settings from `pilot.tsv` reproduces `sim/exp6/frozen/main.json` exactly. `sim/results/exp6-20261016/ana/protocol-stopping.json` summarizes the recount of the 840 rows of `protocol.tsv`: 13,940,220 trials per level of $u$, first-round failures from 0 to 66,839, two capped configurations, eight configurations still without first-round failure.
2. **Per-trial records.** `sim/exp6/ana/trialcheck/main.go` reads the 488 per-block `trials.csv` files of the P campaign (15,370,184 rows; kept with the raw archive, not in this repository) and checks them against the per-block aggregates. Output: `sim/results/exp6-20261016/ana/trialcheck.json`, with no problems found. Round-one failure, empty, miss and round-two failure counts match `proto.csv`; the second-round size equals $\max\{\lceil U/(0.8\alpha_c)\rceil,64\}$ throughout; all arms in a block, including the standard-encoding arm, fail round one on the same trials; the oracle records are identical across the two levels of $u$, confirming shared keys and hashes. Pilot and campaign seeds are disjoint.
3. **Gaussian comparator.** The paper's Gaussian rule (Definition in Section 4) uses the standardized chi-square quantile $(\chi^2_{M-1,u}-(M-1))/\sqrt{2(M-1)}$ with scale $s(n)=\sqrt{2n(n-1)/(M-1)}$. The `rchi` arms implement exactly this rule; `scripts/check_quantiles.py` verifies the frozen quantiles. The empty-acceptance fallback ($M_2=4M_1$) was never triggered in the P campaign (`f1_empty` is zero for every arm).
4. **Configuration count.** The paper's 189 statistical configurations are the 184 of C1 plus the five C1x configurations with $M\ge256$. C1x also has one $M=64$ configuration, giving 42 boundary configurations together with the original 41. Use both stages when auditing the main figure.

## Open items

1. **Historical provenance.** Archive the raw per-trial records (including the P campaign `trials.csv` files) with sizes, SHA-256 hashes, source executables and sampling schemes before certifying full historical reproduction. Current source hashes establish snapshot integrity.
2. **Publication metadata.** Add the arXiv identifier and artifact DOI when available.

## Numerical and experimental conventions

`raw` and `signed_raw_b` refer to the Skellam sizing implementation; `_b` applies the lower bound given by the absolute set-size difference. `signed_oracle` knows the true difference size. `rchi` labels are preserved so historical CSVs and frozen task definitions remain compatible.

Direct sampling produces observations conditional on actual peeling failure. Planted sampling forces a duplicate edge pair and samples a distinct distribution; keep the `kind` field when reporting miss rates. Smoke tests have insufficient power for the manuscript's coverage claims.

Keep seeds, configuration order, chunk size, sampling mode, and executable version fixed when requesting reproducible random streams. Compare statistical fields rather than elapsed times. Validate binary records and per-trial outcomes separately from floating-point summaries when moving between architectures.

# Scientific and release audit

## Scope

The implementations and frozen settings are preserved from the research workspace, including current decoder changes. `audit/source-manifest.json` records the source commit, copied-file hashes, and working-tree changes. Packaging introduces build, smoke, figure, and integrity commands and removes an unused STD-specific import from the shared plotting helper. No numerical summary is edited.

## Items to resolve before the final paper artifact

1. **Protocol stopping rule.** The manuscript describes stopping at 20,000 first-round failures. `freeze_main.py` instead freezes trial counts from a pilot, with caps, and uses those fixed counts for the P campaign. Compare the original run records with the final manuscript and document the rule actually used. The artifact preserves the frozen settings.
2. **Gaussian comparator.** Historical `rchi` arms use the standardized chi-square quantiles in `qtable.json`, while the paper calls the comparator the Gaussian rule. The table also contains standard Gaussian quantiles. Confirm whether the final paper intends this finite-size correction or a normal quantile. No substitution is made in this snapshot.
3. **Configuration count.** The original C1 grid has 184 configurations; the paper's 189 includes the five C1x configurations with M >= 256. C1x also has one M = 64 configuration, giving 42 boundary configurations together with the original 41. Use both stages when auditing the main figure.
4. **Historical provenance.** Collect original executable hashes, raw data archives, machine metadata, and source versions before certifying full historical reproduction. Current source hashes alone establish snapshot integrity.
5. **Publication metadata.** Add the final paper title, full author list, repository URL, paper identifier, artifact DOI, and verified baseline citation when available. Initial software attribution follows the source repository's author name.

## Numerical and experimental conventions

`raw` and `signed_raw_b` refer to the Skellam sizing implementation; `_b` applies the lower bound given by the absolute set-size difference. `signed_oracle` knows the true difference size. `rchi` labels are preserved so historical CSVs and frozen task definitions remain compatible.

Direct sampling produces observations conditional on actual peeling failure. Planted sampling forces a duplicate edge pair and samples a distinct distribution; keep the `kind` field when reporting miss rates. Smoke tests have insufficient power for the manuscript's coverage claims.

Keep seeds, configuration order, chunk size, sampling mode, and executable version fixed when requesting reproducible random streams. Compare statistical fields rather than elapsed times. Validate binary records and per-trial outcomes separately from floating-point summaries when moving between architectures.

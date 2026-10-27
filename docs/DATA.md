# Data availability and schemas

This snapshot includes compact summaries sufficient to regenerate all fourteen paper figures. SHA-256 hashes and source-relative paths appear in `audit/source-manifest.json`. `audit/SHA256SUMS.json` covers the release files themselves. Copied numerical summaries retain their original bytes.

## Included

`sim/results/exp6-20261016/coverage.tsv` stores stage, sampling kind, configuration, rule, risk, failure counts, miss rates, intervals, empty-set rates, and width summaries. `protocol.tsv` stores per-configuration and per-arm protocol outcomes, conditional and joint misses, final failure rates, mean table sizes, and bytes. `c2*.tsv` records confirmation judgments and simultaneous upper confidence bounds. `ana/` contains distribution and paired-comparison summaries. `T/` contains individual timing summaries and protocol timing replicates.

The sampler writes `manifest.json` describing configuration metadata, seeds, code version, field names, and the binary record layout. Records are little-endian four-byte fields; exact count sums are enabled by `-sumc`. Use the manifest and `sim/peelsim/peelio.py` to interpret each run rather than assuming a fixed field ordering. Replay outputs contain per-configuration groups, counts, miss counts, empty counts, and width histograms.

Protocol `-trialout` records `spec,trial,arm,U,M2,ok2` for first-round failures. `U=-1` encodes an empty acceptance set. Aggregate CSVs also contain wall-clock timing fields, which vary across repeated runs.

## Required for full historical reproduction

Archive the original sampler binary records, per-block manifests, replay outputs, protocol trial CSVs, completed-task records, compiler and hardware metadata, and decoder audit checkpoints. Supply a stable download URL, archive SHA-256, size, and license for each batch. These records are not bundled in this initial snapshot, and no public archive URL is currently available.

Source manifests identify this working-tree snapshot. They do not establish that these exact source bytes produced every historical summary: some decoder files were modified or untracked at snapshot time. Preserve original binary hashes and source archives alongside the historical trial data to complete that association.

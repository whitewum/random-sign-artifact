# Validation

Initial snapshot validated on 2026-10-21 with Go 1.24.5, Python 3.11.15, macOS arm64. The 2026-10-27 update was validated with Go 1.24.5, Python 3.13, macOS arm64, and the versions in `requirements-lock.txt`.

| Check | Result |
| --- | --- |
| Build sampler, replay, protocol, and sign-composition reducer | PASS |
| Existing full Go test suite for the protocol and sizing implementation | PASS |
| Sampler built-in self-test | PASS |
| Sampler Go tests, including uniform planted-pair selection | PASS |
| Python distribution tests (`test_distribution.py`) | PASS; 6 tests |
| Direct and planted smoke samples, 200 trials each | PASS |
| Replay both sizing rules on both smoke samples | PASS |
| Two-round smoke protocol, 100 trials for each of two sign compositions | PASS; zero wrong recoveries and false positives, paired decoding agrees |
| Generate frozen main-campaign tasks | PASS; 1774 scripts |
| Recompute frozen quantiles from their definitions | PASS; maximum absolute difference zero |
| Regenerate all paper figures from bundled summaries | PASS; generated PNG contact sheet visually inspected |
| Historical full-scale campaigns | Not rerun in this packaging session |
| GitHub Actions on Linux | Workflow supplied; remote execution pending |

The full Go suite took approximately several minutes on the validation machine. Figure generation includes first-use font-cache construction. Execution time depends on hardware and cache state. The integrity and English-only audit is run after assembling the final files.

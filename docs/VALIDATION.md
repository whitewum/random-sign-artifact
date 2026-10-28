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
| GitHub Actions on Linux | Workflow runs `make audit test smoke figures check-tables` with Go tests in short mode |

The full Go suite took approximately several minutes on the validation machine. Figure generation includes first-use font-cache construction. Execution time depends on hardware and cache state. The integrity and English-only audit is run after assembling the final files.

## Paper coverage update, 2026-10-28

Validated on macOS arm64 with Go 1.24.5, Python 3.13.5, the existing locked Python environment, and TeX Live 2025. The source research tree was read only, no CN manuscript prose was copied, and the EN manuscript body was not edited.

| Command / check | Result |
| --- | --- |
| `make build` | PASS; four executables |
| `make test GOTESTFLAGS=-short` | PASS; both Go modules, sampler self-test, six Python distribution tests |
| `make figures` | PASS; all 13 Python plots and the TikZ diagram; 14 previews visually inspected |
| `make tables` | PASS; 14 numerical table TSVs, including fresh exact rational enumeration |
| `make check-tables` | PASS; 1,044 numeric tokens in 128 rows, every numerical cell at paper display precision |
| Current read-only CN tree via `check_tables.py --cn PATH` | PASS; same results as the bundled numeric snapshot |
| Negative control of the table checker | PASS; a one-count perturbation was rejected, original output restored; exact fractions and rounding boundaries also checked |
| `make audit` | PASS; release hashes, English-only text and portable paths |
| `git diff --check` | PASS |

The display-precision check admits both conventional rounding rules at an exact half-unit boundary. The low-load source summaries retain only three decimals for rates and intervals, so boundary cells cannot establish the unpublished last digits. No paper values were inserted into simulation inputs. All numerical summaries needed for the tables were already bundled; the additions are the upstream exact-enumeration script and diagnostic, analytic figure parameters extracted from upstream programs, and numeric-only inventory/comparison metadata. Added payload is small and contains no new per-trial records. Historical raw samples and machine environment logs remain archive work, as described in `docs/DATA.md`.

## Server archive verification, 2026-10-28

This later check supersedes the low-load precision limitation above. All 17,397 non-pilot sampler blocks (18,896,267 records) and all 488 protocol trial files were checked. Coverage, protocol, C2/C2x/C2s, pilot, full KS, conditional moments, paired risks, paired score intervals, encoding and composition reproduce the stored results. Decoder counts and checkpoint coverage reproduce all 500 million trials. Floating differences and the environment-dependent trial-file count are recorded explicitly in `audit/server-check-20261028/comparisons.json`.

`make tables` passes. The recovered integer counts showed that the first planted miss/u in `tab:v-low` must display 0.95 rather than 0.94. After correcting that manuscript cell and refreshing the reference, `make check-tables` passes all 14 numerical tables (1,044 numeric tokens). See `docs/SERVER-CHECK.md` for hashes, archival selection and the three resolved rounding boundaries.

# Changelog

All notable changes to this project are documented in this file. The format
follows Keep a Changelog and the project uses semantic versioning.

## [0.2.7] - 2026-11-23

### Added

- `docs/data_dictionary.md` covering every column in the committed CSV files,
  with a test that checks the coverage.
- `docs/reproducibility.md` with the environment, the commands, the data
  checksum and the determinism rules.
- `docs/checksums.sha256` with the hashes of the committed figures and tables.
  The test suite verifies every line. `scripts/update_checksums.py` regenerates
  the file.
- Release workflow that builds a wheel and attaches it to the GitHub release for
  a `v*` tag.

### Changed

- 133 tests and 100% statement coverage.
- Version bumped to 0.2.7.

### Notes

- No numerical result changes.

## [0.2.6] - 2026-11-23

### Added

- 100% statement coverage. The two remaining defensive branches now have
  explicit tests: a non-datetime index in `load_prices` and a non-finite
  Christoffersen statistic.
- Dependency audit job with `pip-audit`.
- `docs/architecture.md` and `docs/decisions.md`.
- GitHub issue report form and pull request template.

### Changed

- 133 tests and 100% statement coverage.
- Version bumped to 0.2.6.

### Notes

- No numerical result changes.

## [0.2.5] - 2026-11-23

### Added

- `scripts/mutation_smoke.py` with five source mutations: historical VaR sign,
  historical CVaR sign, empirical quantile level, p-value tail and the
  violation comparison.
- Mutation smoke job in CI and in `scripts/check_all.py`.
- Local `pre-commit` configuration for `ruff check`, `ruff format --check`,
  `mypy` and Bandit.
- `CODEOWNERS`.
- Tests for the API reference coverage, the README version, PNG validity and
  the downloader automatic fallback through the CLI.

### Changed

- 127 tests and 99.52% statement coverage.
- Version bumped to 0.2.5.

### Notes

- No numerical result changes.

## [0.2.4] - 2026-11-23

### Changed

- Applied Ruff formatting to the whole codebase.
- CI and `scripts/check_all.py` now run `ruff format --check`.
- `mypy` now checks `src`, `tests` and `scripts` instead of only `src`.
- Fixed the type annotations in the script-loading test helpers.
- 122 tests and 99.52% statement coverage.
- Version bumped to 0.2.4.

### Notes

- No numerical result changes.

## [0.2.3] - 2026-11-23

### Added

- Minimum-dependency CI job with numpy 1.26.4, scipy 1.11.4, pandas 2.1.4 and
  matplotlib 3.8.4 on Python 3.12.
- Wheel build and clean-install CI job, including a check for the `py.typed`
  marker.
- CodeQL workflow for static security analysis.
- Dependency review workflow for pull requests.
- `scripts/data_quality.py` and `docs/data_quality.md` with row counts, price
  ranges, return statistics and observations by year.
- Tests for the data quality report.

### Changed

- 122 tests and 99.52% statement coverage.
- Version bumped to 0.2.3.

### Notes

- No numerical result changes.

## [0.2.2] - 2026-11-22

### Added

- Markdown link checker for all repository documentation.
- Tests that compare the README main table and the 99% results table with the
  committed CSV files.
- Public API tests for `__all__` exports and docstrings.
- CLI argument tests for both scripts.
- Property tests for portfolio linearity in the weights and for a
  `load_prices` roundtrip.
- `scripts/check_all.py`, a one-command local quality gate that checks the
  snapshot checksum, Ruff, mypy, Bandit and pytest.

### Changed

- 118 tests and 99.52% statement coverage.
- Version bumped to 0.2.2.

### Notes

- No numerical result changes.

## [0.2.1] - 2026-11-22

### Added

- Hypothesis property tests for CVaR >= VaR, monotonicity in the confidence
  level, the empirical quantile identity and p-value ranges.
- Plot input validation for empty frames, non-datetime indexes, missing return
  columns and invalid levels.
- PEP 561 `py.typed` marker and package-data declaration.
- Packaging classifiers and keywords.
- API reference in `docs/api.md`.
- Test that the documented SHA-256 matches `data/prices.sha256`.
- Downloader write-error handling and its tests.

### Changed

- 103 tests and 99.52% statement coverage.
- Version bumped to 0.2.1.

### Notes

- No numerical result changes.

## [0.2.0] - 2026-11-22

### Added

- Snapshot checksum `data/prices.sha256` and a test that verifies the exact
  CSV bytes, the row count and the date range.
- 85 tests, including downloader parsing with mocked HTTP, script integration
  tests and the validation paths of every public function.
- 99.5% statement coverage of `src/risk_lab`, enforced at 99% in CI.
- Clean error messages in `make_figures.py` and `make_extended_analysis.py`.
- Defensive guards in the Yahoo downloader for missing `adjclose`, `quote` and
  timestamp fields.
- Security scan with Bandit.
- CI on macOS in addition to Ubuntu and Windows.
- Dependabot for GitHub Actions and Python dependencies.
- `SECURITY.md`, `CONTRIBUTING.md` and `CITATION.cff`.

### Changed

- `load_prices` reports an empty CSV before checking the index type.
- Version bumped to 0.2.0.

### Notes

- No numerical result changes. The committed figures and tables are unchanged.

## [0.1.0] - 2026-11-22

### Added

- One-day historical, parametric and Monte Carlo VaR and CVaR estimators.
- Fixed 50/35/15 portfolio for SPY, TLT and GLD.
- Versioned adjusted-close snapshot with 2,513 rows from 2016-11-22 to
  2026-11-20.
- Walk-forward backtest with a 500-day window, daily re-estimation and one-day
  forecasts.
- Kupiec unconditional coverage test.
- Christoffersen independence test.
- Christoffersen conditional coverage test.
- 95% and 99% analysis with 250, 500 and 750-day windows.
- Violations by calendar year.
- Two figures: returns with VaR violations and rolling VaR against realized
  loss.
- 42 tests covering the estimators, the backtest, the statistical tests and
  the plots.
- Continuous integration on Ubuntu and Windows with Python 3.12 and 3.14.

### Notes

- The committed snapshot uses Yahoo Finance adjusted closes. The Stooq CSV
  endpoint returned `Access denied` on 2026-11-22. The downloader keeps Stooq
  as the first source and falls back to Yahoo.
- At 95% with a 500-day window, all three methods fail the independence test.
  At 99%, the normal models fail Kupiec. The results are reported without
  smoothing.

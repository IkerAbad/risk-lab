# Changelog

All notable changes to this project are documented in this file. The format
follows Keep a Changelog and the project uses semantic versioning.

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

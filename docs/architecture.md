# Architecture

## Modules

- `src/risk_lab/data.py` loads and validates the price CSV, computes simple or
  log returns, validates weights and builds the fixed-weight portfolio return
  series.
- `src/risk_lab/var.py` contains the historical, parametric and Monte Carlo
  estimators. Every function returns positive losses and validates its inputs.
- `src/risk_lab/backtest.py` runs the walk-forward loop, builds the comparative
  summary and counts violations by calendar year.
- `src/risk_lab/conditional.py` contains the EWMA variance recursion, the
  GARCH(1,1) likelihood and fit, the conditional normal VaR and CVaR, the
  standardized residuals and the filtered historical simulation.
- `src/risk_lab/comparison.py` runs the six-model conditional backtest, builds
  the summary, the pairwise Diebold-Mariano table, the stress-year table, the
  ES bootstrap table and the pre-registered winner decision.
- `src/risk_lab/stats.py` implements the Kupiec, Christoffersen independence and
  conditional coverage tests, the quantile loss, the Diebold-Mariano test, the
  Holm correction and the moving block bootstrap.
- `src/risk_lab/plots.py` builds the four figures and validates the backtest
  frame before plotting.

## Data flow

1. `scripts/download_data.py` writes `data/prices.csv` and prints the source.
   The committed snapshot is the reference for every result.
2. `load_prices` validates the CSV. `compute_returns` produces the asset
   returns. `portfolio_returns` produces the fixed-weight portfolio returns.
3. `rolling_backtest` estimates the three models on each 500-day window and
   writes one row per forecast date.
4. `summarize_backtest` turns the violation series into the Kupiec,
   Christoffersen and conditional coverage table. `plots.py` turns the same
   frame into the figures.
5. `scripts/make_figures.py` writes the main figures and tables.
   `scripts/make_extended_analysis.py` writes the level and window sensitivity
   tables and the yearly counts. `scripts/make_conditional_analysis.py` writes
   the six-model comparison, the Diebold-Mariano, stress-year and ES tables and
   figures 3 and 4. `scripts/data_quality.py` writes the snapshot report.
6. `scripts/check_all.py` runs the checksum, lint, type check, security scan,
   tests with coverage and mutation smoke test.

## Invariants

- VaR and CVaR are positive losses. The return quantile is -VaR.
- The backtest uses only the previous `window` observations for each forecast.
  There is no lookahead. The adaptive models use the previous 20 and 250
  observations to choose the window, and the EWMA and GARCH variance at date
  `t` uses returns through `t-1`.
- The portfolio weights are fixed and long-only. The portfolio is rebalanced
  daily in the return calculation.
- The Monte Carlo seed is fixed. A forecast day uses `seed + position`. The
  filtered historical simulation uses the same rule. The ES bootstrap uses
  seed 42.
- Every public function validates its inputs and raises `ValueError` or
  `TypeError` with a specific message.
- The committed CSV is checked byte for byte against `data/prices.sha256`.

## Quality layers

- Unit tests for the estimators, the backtest and the statistical tests.
- Property tests for sign, monotonicity, p-value ranges, linearity and CSV
  round trips.
- Integration tests for the downloader, the scripts and the data quality
  report.
- `ruff check`, `ruff format --check`, `mypy` over `src`, `tests` and
  `scripts`, Bandit and `pip-audit`.
- Five mutation checks that the suite must catch.
- CI matrix on Ubuntu, Windows and macOS with Python 3.12 and 3.14, a
  minimum-dependency job, a wheel job, a mutation job and a dependency audit.
- CodeQL and dependency review as separate workflows.

## Entry points

- `scripts/download_data.py`
- `scripts/make_figures.py`
- `scripts/make_extended_analysis.py`
- `scripts/make_conditional_analysis.py`
- `scripts/data_quality.py`
- `scripts/mutation_smoke.py`
- `scripts/check_all.py`

The importable API is documented in `docs/api.md`.

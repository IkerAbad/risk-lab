# Contributing

## Setup

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
python -m pip install -e ".[dev]"
```

## Checks

Run the full local check before opening a pull request:

```bash
python -m pytest -q --cov=risk_lab --cov-report=term-missing
python -m ruff check .
python -m mypy src
```

The CI runs the same checks on Ubuntu and Windows with Python 3.12 and 3.14.
A pull request is ready when all four jobs pass.

## Code style

- Type hints on public functions.
- Docstrings that state the formula or the decision, not the obvious.
- Line length 100 characters.
- No emojis in code, comments or documentation.
- Keep the sign convention: VaR and CVaR are positive losses.
- Do not silently change the data snapshot. A new CSV changes every result.

## Adding a method

1. Implement the estimator in `src/risk_lab/var.py` and return a
   `RiskEstimate`.
2. Add the method name to `METHODS` in `src/risk_lab/backtest.py` and compute
   its VaR and CVaR in the rolling loop.
3. Add tests in `tests/test_var.py` and `tests/test_backtest.py`. Include a
   hand-built case where the expected value can be checked without the
   implementation.
4. Add the method to the summary table and to the figures if it is part of the
   main comparison.
5. Update `README.md`, `docs/methodology.md` and `docs/results.md`.
6. Run `python scripts/make_figures.py` and
   `python scripts/make_extended_analysis.py`. Commit the regenerated figures
   and tables with the code.

## Data changes

The committed file is `data/prices.csv`. If you refresh it:

1. Run `python scripts/download_data.py`.
2. Update the SHA-256 in `README.md` and `docs/methodology.md`.
3. Re-run both scripts.
4. Update every number in `README.md` and `docs/results.md`.
5. State the data source and the download date in the commit message.

Do not commit a new CSV and leave the old results in place.

## Commits

Use short imperative messages in English, for example:

```text
Add Christoffersen conditional coverage test
Fix window validation in the rolling backtest
Update results after the 2026 data refresh
```

Keep code, tests and documentation for the same change in one commit when
possible.

## Reporting a problem

Open an issue with the command, the Python version, the operating system and
the full traceback. Do not paste credentials or personal data.

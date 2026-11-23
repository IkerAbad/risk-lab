# Reproducibility

## Environment

The committed results were built with Python 3.12+ and these direct versions:

| Package | Version |
|---|---:|
| numpy | 2.5.5 |
| scipy | 1.18.1 |
| pandas | 3.1.1 |
| matplotlib | 3.11.2 |
| pytest | 9.2.0 |
| pytest-cov | 7.1.0 |
| hypothesis | 6.170.17 |
| ruff | 0.17.6 |
| mypy | 2.4.1 |
| bandit | 1.9.4 |
| pip-audit | 2.10.1 |
| pre-commit | 4.7.0 |

The declared lower bounds are tested in a separate CI job with numpy 1.26.4,
scipy 1.11.4, pandas 2.1.4 and matplotlib 3.8.4 on Python 3.12.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
python -m pip install -e ".[dev]"
```

## Data integrity

The committed snapshot is `data/prices.csv`. Its SHA-256 is stored in
`data/prices.sha256` and also in the README and the methodology:

```text
d33a038e9b4460468ca195b2f7c9c3374ce062d1ff7cf75280f6a8e300e2e3a1
```

The test suite checks the file byte for byte. If the snapshot changes, update
the checksum, the README, the methodology, the figures, the tables and the data
quality report.

## Generated outputs

The committed figures and tables are listed in `docs/checksums.sha256`. The
test suite verifies every line. `scripts/update_checksums.py` regenerates the
file after a deliberate change.

## Determinism

- The main window is 500 days. The extended analysis uses 250, 500 and 750.
- The main level is 95%. The extended analysis also uses 99%.
- The Monte Carlo run uses 100,000 scenarios and seed 42. A forecast at integer
  position `i` uses `seed + i`.
- The empirical quantile uses linear interpolation.
- The figures and tables have no timestamps, so the bytes do not depend on the
  run date.

Two runs with the same code and the same input produce the same tables. The
local `scripts/check_all.py` and the CI matrix verify the tests, the checksum
and the mutation smoke test.

## Commands

```bash
python -m pytest -q --cov=risk_lab --cov-report=term-missing
python scripts/make_figures.py
python scripts/make_extended_analysis.py
python scripts/data_quality.py
python scripts/check_all.py
```

The main pipeline takes about 11 seconds. The extended analysis takes about 63
seconds. Both runtimes are on the machine used to build the snapshot.

## Data source

The downloader tries Stooq first and falls back to Yahoo Finance adjusted
closes. On 2026-11-22 Stooq returned `Access denied` from the author's network.
The committed snapshot is the Yahoo adjusted close. A fresh download can differ
in the last decimal places because vendors revise dividend adjustments, so the
committed CSV and its checksum are the reference for every result.

# Data dictionary

All returns are simple daily returns. All VaR and CVaR values are positive
losses. Rate columns in the CSV files are fractions. The Markdown tables show
percentages.

## `data/prices.csv`

| Column | Type | Description |
|---|---|---|
| `Date` | date | US trading day. |
| `SPY` | float | Adjusted close of SPY. |
| `TLT` | float | Adjusted close of TLT. |
| `GLD` | float | Adjusted close of GLD. |

## `docs/full_sample_risk.csv`

| Column | Type | Description |
|---|---|---|
| `method` | string | `historical`, `parametric` or `monte_carlo`. |
| `var` | float | Full-sample one-day VaR at 95%, positive loss. |
| `cvar` | float | Full-sample one-day CVaR at 95%, positive loss. |

## `docs/backtest_summary.csv`

| Column | Type | Description |
|---|---|---|
| `method` | string | `historical`, `parametric` or `monte_carlo`. |
| `observations` | int | Number of one-day forecasts. |
| `violations` | int | Number of days with loss greater than VaR. |
| `expected` | float | Expected violations under the nominal level. |
| `violation_rate` | float | `violations / observations`, as a fraction. |
| `kupiec_lr` | float | Kupiec likelihood-ratio statistic. |
| `kupiec_p` | float | Kupiec p-value from chi-square with one degree of freedom. |
| `christoffersen_lr` | float | Christoffersen independence statistic. |
| `christoffersen_p` | float | Independence p-value from chi-square with one degree of freedom. |
| `conditional_lr` | float | Joint conditional coverage statistic. |
| `conditional_p` | float | Joint p-value from chi-square with two degrees of freedom. |

## `docs/backtest_series.csv`

| Column | Type | Description |
|---|---|---|
| `date` | date | Forecast date. The model uses only earlier dates. |
| `return` | float | Realized portfolio return on the forecast date. |
| `loss` | float | `-return`. |
| `var_historical` | float | Historical VaR, positive loss. |
| `cvar_historical` | float | Historical CVaR, positive loss. |
| `violation_historical` | bool | True when `loss > var_historical`. |
| `var_parametric` | float | Parametric normal VaR, positive loss. |
| `cvar_parametric` | float | Parametric normal CVaR, positive loss. |
| `violation_parametric` | bool | True when `loss > var_parametric`. |
| `var_monte_carlo` | float | Monte Carlo VaR, positive loss. |
| `cvar_monte_carlo` | float | Monte Carlo CVaR, positive loss. |
| `violation_monte_carlo` | bool | True when `loss > var_monte_carlo`. |

## `docs/sensitivity.csv`

| Column | Type | Description |
|---|---|---|
| `level` | float | Confidence level, 0.95 or 0.99. |
| `window` | int | Estimation window in trading days, 250, 500 or 750. |
| `method` | string | `historical`, `parametric` or `monte_carlo`. |
| `observations` | int | Number of one-day forecasts for that level and window. |
| `violations` | int | Number of violations. |
| `expected` | float | Expected violations under the nominal level. |
| `violation_rate` | float | `violations / observations`, as a fraction. |
| `kupiec_lr` | float | Kupiec likelihood-ratio statistic. |
| `kupiec_p` | float | Kupiec p-value. |
| `christoffersen_lr` | float | Christoffersen independence statistic. |
| `christoffersen_p` | float | Independence p-value. |
| `conditional_lr` | float | Joint conditional coverage statistic. |
| `conditional_p` | float | Joint p-value. |

## `docs/violations_by_year.csv`

| Column | Type | Description |
|---|---|---|
| `method` | string | `historical`, `parametric` or `monte_carlo`. |
| `year` | int | Calendar year of the forecast date. |
| `observations` | int | Forecasts in that year. |
| `violations` | int | Violations in that year. |
| `expected` | float | Expected violations in that year. |
| `rate` | float | `violations / observations`, as a fraction. |

## `docs/checksums.sha256`

One line per generated output, in the format `sha256  filename`. The paths are
relative to `docs/`. The test suite verifies every line.

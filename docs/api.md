# API reference

All VaR and CVaR functions return positive losses. A VaR of 0.02 means a
one-day loss of 2% of portfolio value. The return quantile is -VaR.

The public functions validate their inputs and raise `ValueError` with a
message that names the problem. `TypeError` is raised when a pandas object is
required and something else is passed.

## Data

### `load_prices(path)`

Load a wide price CSV with a `Date` column and one column per asset.

- `path`: `str` or `Path`.
- Returns a `pandas.DataFrame` indexed by date, sorted, with float columns.
- Raises `ValueError` for an empty file, duplicate dates, missing values,
  non-finite values or non-positive prices.

### `compute_returns(prices, *, log_returns=False)`

Compute daily returns and drop the first row. Simple returns are
`P_t / P_t-1 - 1`. Set `log_returns=True` for log returns.

- Raises `ValueError` if `prices` is empty.

### `weights_vector(columns, weights)`

Return the weights in the order of `columns`.

- `columns`: sequence of asset names.
- `weights`: mapping from asset name to weight.
- Raises `ValueError` for missing weights, non-finite weights, negative
  weights or weights that do not sum to 1.

### `portfolio_returns(returns, weights)`

Return the weighted portfolio return series. The result assumes daily
rebalancing to the fixed weights.

- Raises `ValueError` if `returns` is empty or the weights are invalid.

## VaR and CVaR

### `RiskEstimate`

Frozen dataclass with two fields: `var` and `cvar`, both positive losses.

### `historical_risk(returns, level=0.95)`

Empirical VaR and CVaR. The quantile uses linear interpolation and the CVaR
is the negative mean of the returns at or below that quantile.

### `historical_var(returns, level=0.95)` and `historical_cvar(returns, level=0.95)`

Return the corresponding field of `historical_risk`.

### `parametric_risk(returns, level=0.95)`

Normal VaR and CVaR from the sample mean and sample standard deviation
(`ddof=1`). The CVaR is the closed-form normal tail mean.

### `parametric_var(returns, level=0.95)` and `parametric_cvar(returns, level=0.95)`

Return the corresponding field of `parametric_risk`.

### `simulate_portfolio_returns(returns, weights, *, n_scenarios=100_000, seed=42)`

Simulate portfolio returns from a multivariate normal model. `returns` is a
T x N array. The function estimates the mean vector and the sample covariance
matrix, takes the Cholesky factor and draws `n_scenarios` vectors. Returns a
one-dimensional array of simulated portfolio returns.

- Raises `ValueError` for a non-integer or non-positive `n_scenarios`, a bad
  shape, fewer than two observations, no assets, non-finite values, invalid
  weights or a covariance matrix that is not positive definite.

### `monte_carlo_risk(returns, weights, level=0.95, *, n_scenarios=100_000, seed=42)`

Monte Carlo VaR and CVaR from the simulated portfolio returns. The seed makes
the result reproducible.

### `monte_carlo_var(...)` and `monte_carlo_cvar(...)`

Return the corresponding field of `monte_carlo_risk`.

## Backtest

### `rolling_backtest(returns, weights, *, window=500, level=0.95, n_scenarios=100_000, seed=42, methods=("historical", "parametric", "monte_carlo"))`

Run a walk-forward one-day backtest. For each forecast date `t`, the model uses
only the previous `window` observations. Returns a DataFrame indexed by
forecast date with:

- `return` and `loss`.
- `var_<method>` and `cvar_<method>`.
- `violation_<method>`.

A violation is `loss > var`, strictly greater.

- Raises `TypeError` if `returns` is not a DataFrame.
- Raises `ValueError` for empty data, missing or non-finite values, an empty
  or unknown method list, a repeated method, a non-integer window, a window
  smaller than 2, a window larger than the sample or an invalid level.

### `summarize_backtest(backtest, *, level=0.95)`

Build the comparative table with observations, violations, expected
violations, violation rate, Kupiec, Christoffersen and conditional coverage
statistics and p-values.

- Raises `ValueError` for an empty backtest, an invalid level, a missing
  violation column or a frame with no method columns.

### `violations_by_year(backtest, *, level=0.95)`

Count violations by calendar year for every method. Returns a DataFrame
indexed by `method` and `year` with observations, violations, expected
violations and the violation rate as a fraction.

- Raises `ValueError` for an empty backtest, a non-datetime index, an invalid
  level or a frame with no method columns.

## Statistical tests

### `TestResult`

Frozen dataclass with `statistic`, `p_value`, `df`, `valid` and `note`.

### `kupiec_pof(violations, n=None, p0=0.05)`

Kupiec proportion-of-failures test. Pass either a binary sequence or a count
with `n`. The p-value comes from the chi-square survival function with one
degree of freedom.

- Raises `ValueError` for an invalid `p0`, a count without `n`, a count and a
  sequence at the same time, `n < 1` or a count outside `[0, n]`.

### `christoffersen_independence(violations)`

Christoffersen first-order independence test. Returns `valid=False` and NaN
p-value when one of the two states never follows a transition.

### `christoffersen_conditional_coverage(violations, p0=0.05)`

Joint conditional coverage test. The statistic is `LR_uc + LR_ind` and the
p-value comes from chi-square with two degrees of freedom. Returns `valid=False`
and NaN when the independence component is undefined.

## Plots

### `plot_returns_with_violations(backtest, *, method="historical", level=0.95, path=None, figsize=(11.0, 4.5))`

Plot the realized returns and the rolling VaR, with red dots on the
violations. Returns the Matplotlib figure. If `path` is given, the figure is
saved at 150 dpi and the parent directory is created.

- Raises `ValueError` for an unknown method, an empty backtest, a non-datetime
  index, a missing return column, an invalid level or missing method columns.

### `plot_rolling_var(backtest, *, level=0.95, path=None, figsize=(11.0, 4.5))`

Plot the realized loss against the rolling VaR from every method present in the
frame. Missing methods are skipped. Returns the Matplotlib figure and saves it
when `path` is given.

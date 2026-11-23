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

## Conditional volatility and comparison

### `GarchParams`

Frozen dataclass with `omega`, `alpha`, `beta`, `mean`, `initial_variance` and
`converged`.

### `ewma_variance(returns, lam=0.94, initial_variance=None)`

Exponentially weighted conditional variance for each return using data through
the previous day. The recursion is
`v_t = lam v_t-1 + (1-lam) r_t-1^2`. The first value is the initial variance.

### `ewma_forecast(returns, lam=0.94, initial_variance=None)`

One-step EWMA variance forecast after the last return in the window.

### `fit_garch11(returns, *, mean=None)`

Gaussian quasi-maximum-likelihood estimate of a GARCH(1,1) model with a
constant mean. Three starting points are tried. If every optimization fails,
the function returns the pre-registered fallback with `converged=False`.

### `garch_variance(returns, params)`

In-sample GARCH(1,1) variance path. Raises `ValueError` for invalid parameters
or non-positive variances.

### `garch_forecast(returns, params)`

One-step GARCH variance forecast after the last return.

### `conditional_normal_risk(mean, volatility, level=0.95)`

Normal VaR and CVaR from a conditional mean and volatility. Returns a
`RiskEstimate` with positive losses.

### `standardized_residuals(returns, variance, mean=0.0)`

Standardize returns by the conditional standard deviation. Used by filtered
historical simulation.

### `fhs_risk(mean, volatility, residuals, level=0.95, *, n_scenarios=10_000, seed=42)`

Filtered historical simulation VaR and ES for one day. Resamples the
standardized residuals with replacement and scales them by the conditional
volatility.

### `DMResult`

Frozen dataclass with `statistic`, `p_value`, `mean_difference` and `lags`.

### `quantile_loss(returns, var_forecasts, level=0.95)`

Asymmetric quantile loss for a positive-loss VaR forecast. The return quantile
is `q_t = -VaR_t` and `tau = 1 - level`.

### `diebold_mariano(loss_a, loss_b, *, lags=5)`

Diebold-Mariano test for two loss series, with a Newey-West long-run variance
and a two-sided normal p-value. A negative mean difference favors the first
series.

### `holm_bonferroni(p_values)`

Holm-Bonferroni adjusted p-values in the original order.

### `block_bootstrap_mean_ci(values, *, block_length=20, n_boot=10_000, seed=42, confidence=0.95)`

Moving block bootstrap percentile interval for the mean of a series.

### `adaptive_window(returns, position, *, short=20, long=250, threshold=1.25, default=500)`

Return 250 when the short/long realized volatility ratio is at least 1.25,
otherwise 500.

### `conditional_backtest(returns, *, level=0.95, window=500, garch_refit=21, ewma_lambda=0.94, adaptive_short=20, adaptive_long=250, adaptive_threshold=1.25, n_scenarios=10_000, seed=42)`

Run the six pre-registered models on the same one-day forecasts. Returns a
DataFrame with the realized return, the adaptive window, the EWMA and GARCH
volatilities, and the VaR, CVaR, simulated ES and violation flag of each model.

### `model_losses(backtest, *, level=0.95)`

Quantile losses for every model in the comparison.

### `conditional_summary(backtest, *, level=0.95)`

Coverage tests, mean quantile loss and mean risk for every model.

### `pairwise_dm(backtest, *, level=0.95, lags=5)`

All 15 pairwise Diebold-Mariano tests with raw and Holm-adjusted p-values.

### `winner_decision(summary, pairwise, *, alpha=0.05)`

Apply the pre-registered winner rule. Returns the best model, the runner-up,
the Holm-adjusted p-value and a boolean `clear_winner`.

### `stress_year_table(backtest, *, level=0.95, years=(2020, 2022, 2026))`

Coverage and mean quantile loss by pre-registered stress year.

### `es_table(backtest, *, level=0.95, block_length=20, n_boot=10_000, seed=42)`

Mean model CVaR and mean simulated ES for each model, with block-bootstrap
confidence intervals.

### `MODELS`

Tuple with the six model names used in the conditional comparison.

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

### `plot_conditional_var(backtest, *, level=0.95, path=None, figsize=(11.0, 4.5))`

Plot the realized loss against the main conditional models: historical 500,
parametric 500, EWMA, GARCH(1,1) and the adaptive historical window. Returns
the Matplotlib figure and saves it when `path` is given.

### `plot_es_ci(es_table, *, level=0.95, path=None, figsize=(10.0, 4.5))`

Plot the mean simulated ES with its block-bootstrap interval and the model CVaR
as a marker. Returns the Matplotlib figure and saves it when `path` is given.


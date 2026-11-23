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

## `docs/conditional_summary.csv`

| Column | Type | Description |
|---|---|---|
| `level` | float | Confidence level, 0.95 or 0.99. |
| `model` | string | `hist500`, `param500`, `ewma`, `garch`, `hist_adaptive` or `param_adaptive`. |
| `observations` | int | Number of one-day forecasts. |
| `violations` | int | Number of days with loss greater than VaR. |
| `expected` | float | Expected violations under the nominal level. |
| `violation_rate` | float | `violations / observations`, as a fraction. |
| `kupiec_lr` | float | Kupiec likelihood-ratio statistic. |
| `kupiec_p` | float | Kupiec p-value. |
| `christoffersen_lr` | float | Christoffersen independence statistic. |
| `christoffersen_p` | float | Independence p-value. |
| `conditional_lr` | float | Joint conditional coverage statistic. |
| `conditional_p` | float | Joint p-value. |
| `mean_loss` | float | Mean asymmetric quantile loss over the forecasts. |
| `mean_var` | float | Mean VaR, positive loss. |
| `mean_cvar` | float | Mean model CVaR, positive loss. |
| `mean_es_sim` | float | Mean filtered-historical-simulation ES, positive loss. |
| `rank` | int | Rank by `mean_loss`, 1 is best. |

## `docs/conditional_dm.csv`

| Column | Type | Description |
|---|---|---|
| `level` | float | Confidence level, 0.95 or 0.99. |
| `model_a` | string | First model in the comparison. |
| `model_b` | string | Second model in the comparison. |
| `mean_loss_a` | float | Mean quantile loss of `model_a`. |
| `mean_loss_b` | float | Mean quantile loss of `model_b`. |
| `mean_difference` | float | `mean_loss_a - mean_loss_b`. Negative favors `model_a`. |
| `dm_stat` | float | Diebold-Mariano statistic with Newey-West variance, 5 lags. |
| `dm_p` | float | Raw two-sided normal p-value. |
| `dm_p_holm` | float | Holm-Bonferroni adjusted p-value over the 15 pairs. |

## `docs/conditional_stress.csv`

| Column | Type | Description |
|---|---|---|
| `level` | float | Confidence level, 0.95 or 0.99. |
| `model` | string | One of the six comparison models. |
| `year` | int | Pre-registered stress year: 2020, 2022 or 2026. |
| `observations` | int | Forecasts in that year. |
| `violations` | int | Violations in that year. |
| `expected` | float | Expected violations in that year. |
| `rate` | float | `violations / observations`, as a fraction. |
| `mean_loss` | float | Mean quantile loss in that year. |

## `docs/conditional_es.csv`

| Column | Type | Description |
|---|---|---|
| `level` | float | Confidence level, 0.95 or 0.99. |
| `model` | string | One of the six comparison models. |
| `cvar_type` | string | `empirical` or `parametric`. |
| `mean_cvar` | float | Mean model CVaR, positive loss. |
| `cvar_ci_low` | float | Lower bound of the 95% block-bootstrap interval. |
| `cvar_ci_high` | float | Upper bound of the 95% block-bootstrap interval. |
| `mean_es_sim` | float | Mean simulated ES, positive loss. |
| `es_ci_low` | float | Lower bound of the simulated ES interval. |
| `es_ci_high` | float | Upper bound of the simulated ES interval. |

## `docs/conditional_series_95.csv`

One row per forecast date at 95%, indexed by `date`.

| Column | Type | Description |
|---|---|---|
| `date` | date | Forecast date. The model uses only earlier dates. |
| `return` | float | Realized portfolio return. |
| `loss` | float | `-return`. |
| `window` | int | Adaptive window used that day, 250 or 500. |
| `vol_ewma` | float | One-day EWMA volatility forecast. |
| `vol_garch` | float | One-day GARCH(1,1) volatility forecast. |
| `var_<model>` | float | VaR of the model, positive loss. |
| `cvar_<model>` | float | Model CVaR, positive loss. |
| `es_sim_<model>` | float | Filtered historical simulation ES, positive loss. |
| `violation_<model>` | bool | True when `loss > var_<model>`. |

The `<model>` suffix is one of `hist500`, `param500`, `ewma`, `garch`,
`hist_adaptive` or `param_adaptive`. The full column list is:
`var_hist500`, `cvar_hist500`, `es_sim_hist500`, `violation_hist500`,
`var_param500`, `cvar_param500`, `es_sim_param500`, `violation_param500`,
`var_ewma`, `cvar_ewma`, `es_sim_ewma`, `violation_ewma`, `var_garch`,
`cvar_garch`, `es_sim_garch`, `violation_garch`, `var_hist_adaptive`,
`cvar_hist_adaptive`, `es_sim_hist_adaptive`, `violation_hist_adaptive`,
`var_param_adaptive`, `cvar_param_adaptive`, `es_sim_param_adaptive` and
`violation_param_adaptive`.

## `data/fresh/prices_<date>.csv`

Same schema as `data/prices.csv`: a `Date` column and one adjusted-close column
per ticker (`SPY`, `TLT`, `GLD`). The file is a dated download, not the
canonical snapshot. `data/fresh/prices_<date>.sha256` stores its SHA-256 in the
`sha256  filename` format.

## `docs/fresh/comparison_fresh_<level>.csv`

| Column | Type | Description |
|---|---|---|
| `model` | string | One of the six comparison models. |
| `violations_snapshot` | int | Violations on the canonical snapshot. |
| `violations_fresh` | int | Violations on the fresh snapshot. |
| `delta_violations` | int | `violations_fresh - violations_snapshot`. |
| `mean_loss_snapshot` | float | Mean quantile loss on the snapshot. |
| `mean_loss_fresh` | float | Mean quantile loss on the fresh data. |
| `delta_mean_loss_bp` | float | Fresh minus snapshot, in basis points. |
| `rank_snapshot` | int | Snapshot rank by mean loss. |
| `rank_fresh` | int | Fresh rank by mean loss. |
| `mean_es_snapshot` | float | Mean simulated ES on the snapshot. |
| `mean_es_fresh` | float | Mean simulated ES on the fresh data. |

`comparison_common_<level>.csv` has the same columns. It uses the fresh prices
cut at the canonical end date, so it isolates the effect of price revisions.

## `docs/fresh/conditional_summary_fresh.csv`

Same columns as `docs/conditional_summary.csv`, for the fresh sample.
`conditional_summary_common.csv` is the common-period version.

## `docs/fresh/conditional_dm_fresh.csv`

Same columns as `docs/conditional_dm.csv`, for the fresh sample.
`conditional_dm_common.csv` is the common-period version.

## `docs/fresh/winners.csv`

| Column | Type | Description |
|---|---|---|
| `dataset` | string | `snapshot`, `fresh_full` or `fresh_common`. |
| `level` | float | Confidence level. |
| `best` | string | Model with the lowest mean loss. |
| `second` | string | Model with the second-lowest mean loss. |
| `best_mean_loss` | float | Mean loss of `best`. |
| `second_mean_loss` | float | Mean loss of `second`. |
| `dm_p_holm` | float | Holm-adjusted Diebold-Mariano p-value for the pair. |
| `clear_winner` | bool | True when `dm_p_holm < 0.05`. |
| `decision` | string | Pre-registered decision text. |

## `docs/fresh/main_comparison.csv`

One row per method, with `_snapshot` and `_fresh` suffixes on every column of
`docs/backtest_summary.csv`. `main_summary_fresh.csv` has the fresh columns
only.

## `docs/fresh/garch_diagnostics.csv`

One row per GARCH refit: `dataset`, `position`, `date`, `converged`, `omega`,
`alpha`, `beta` and `sample_variance`.

## `docs/fresh/garch_diagnostics_summary.csv`

| Column | Type | Description |
|---|---|---|
| `dataset` | string | `snapshot`, `fresh_full` or `fresh_common`. |
| `refits` | int | Number of GARCH refits. |
| `failed` | int | Fits where the optimizer reported failure. |
| `alpha_below_1e_8` | int | Fits with `alpha < 1e-8`. |
| `beta_above_0_99` | int | Fits with `beta > 0.99`. |
| `max_omega_over_variance` | float | Largest `omega / sample_variance`. |

## `docs/checksums.sha256`

One line per generated output, in the format `sha256  filename`. The paths are
relative to `docs/`. The test suite verifies every line.

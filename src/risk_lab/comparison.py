"""Conditional-volatility comparison for the fixed portfolio."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .conditional import (
    conditional_normal_risk,
    ewma_variance,
    fhs_risk,
    fit_garch11,
    garch_variance,
    standardized_residuals,
)
from .stats import (
    block_bootstrap_mean_ci,
    christoffersen_conditional_coverage,
    christoffersen_independence,
    diebold_mariano,
    holm_bonferroni,
    kupiec_pof,
    quantile_loss,
)
from .var import historical_risk

MODELS: tuple[str, ...] = (
    "hist500",
    "param500",
    "ewma",
    "garch",
    "hist_adaptive",
    "param_adaptive",
)

MODEL_LABELS: dict[str, str] = {
    "hist500": "Historical 500",
    "param500": "Parametric 500",
    "ewma": "EWMA",
    "garch": "GARCH(1,1)",
    "hist_adaptive": "Historical adaptive",
    "param_adaptive": "Parametric adaptive",
}

PARAMETRIC_MODELS: tuple[str, ...] = (
    "param500",
    "ewma",
    "garch",
    "param_adaptive",
)


def adaptive_window(
    returns: np.ndarray | list[float],
    position: int,
    *,
    short: int = 20,
    long: int = 250,
    threshold: float = 1.25,
    default: int = 500,
) -> int:
    """Return 250 when the short/long volatility ratio is at least 1.25.

    Otherwise return ``default``. The main comparison uses the default 500.
    """
    values = np.asarray(returns, dtype=float)
    if values.ndim != 1:
        raise ValueError("returns must be one-dimensional")
    if not np.isfinite(values).all():
        raise ValueError("returns must be finite")
    if isinstance(position, bool) or not isinstance(position, int):
        raise ValueError("position must be an integer")
    if not 0 < short < long <= position <= values.size:
        raise ValueError("expected 0 < short < long <= position <= size")
    threshold = float(threshold)
    if not np.isfinite(threshold) or threshold <= 0:
        raise ValueError("threshold must be positive and finite")
    if default not in (250, 500):
        raise ValueError("default must be 250 or 500")

    short_volatility = float(np.std(values[position - short : position], ddof=1))
    long_volatility = float(np.std(values[position - long : position], ddof=1))
    if long_volatility <= 0:
        return default
    return 250 if short_volatility / long_volatility >= threshold else default


def _ewma_residuals(
    window: np.ndarray,
    lam: float,
) -> np.ndarray:
    variance = ewma_variance(
        window,
        lam,
        initial_variance=float(np.var(window, ddof=1)),
    )
    return standardized_residuals(window, variance, 0.0)


def conditional_backtest(
    returns: pd.Series,
    *,
    level: float = 0.95,
    window: int = 500,
    garch_refit: int = 21,
    ewma_lambda: float = 0.94,
    adaptive_short: int = 20,
    adaptive_long: int = 250,
    adaptive_threshold: float = 1.25,
    n_scenarios: int = 10_000,
    seed: int = 42,
) -> pd.DataFrame:
    """Run the six pre-registered models on the same one-day forecasts.

    The output has one row per forecast date and, for each model, the VaR, the
    model CVaR, the filtered historical simulation ES and the violation flag.
    """
    if not isinstance(returns, pd.Series):
        raise TypeError("returns must be a pandas Series")
    if returns.empty:
        raise ValueError("returns are empty")
    if not isinstance(returns.index, pd.DatetimeIndex):
        raise ValueError("returns index must be a DatetimeIndex")
    if returns.isna().any():
        raise ValueError("returns contain missing values")
    values = returns.to_numpy(dtype=float)
    if not np.isfinite(values).all():
        raise ValueError("returns contain non-finite values")
    if not 0.0 < float(level) < 1.0:
        raise ValueError("level must be strictly between 0 and 1")
    if isinstance(window, bool) or not isinstance(window, int) or window < 50:
        raise ValueError("window must be an integer of at least 50")
    if len(values) <= window:
        raise ValueError("the sample must be longer than the window")
    if isinstance(garch_refit, bool) or not isinstance(garch_refit, int):
        raise ValueError("garch_refit must be an integer")
    if garch_refit < 1:
        raise ValueError("garch_refit must be positive")
    if not 0.0 < float(ewma_lambda) < 1.0:
        raise ValueError("ewma_lambda must be strictly between 0 and 1")
    if not 0 < adaptive_short < adaptive_long <= window:
        raise ValueError("expected 0 < adaptive_short < adaptive_long <= window")
    if not np.isfinite(adaptive_threshold) or adaptive_threshold <= 0:
        raise ValueError("adaptive_threshold must be positive")
    if isinstance(n_scenarios, bool) or not isinstance(n_scenarios, int):
        raise ValueError("n_scenarios must be an integer")
    if n_scenarios < 1:
        raise ValueError("n_scenarios must be positive")

    initial_variance = float(np.var(values[:window], ddof=1))
    if not np.isfinite(initial_variance) or initial_variance <= 0:
        raise ValueError("the initial variance must be positive and finite")

    ewma_variances = np.full(values.size, np.nan, dtype=float)
    current_ewma = initial_variance
    for position in range(window, values.size):
        current_ewma = ewma_lambda * current_ewma + (1.0 - ewma_lambda) * values[position - 1] ** 2
        ewma_variances[position] = current_ewma

    garch_parameters = None
    garch_variance_forecast = float("nan")

    rows: list[dict[str, float | int | bool]] = []
    for position in range(window, values.size):
        if garch_parameters is None or (position - window) % garch_refit == 0:
            fit_window = values[position - window : position]
            garch_parameters = fit_garch11(fit_window)
            variance_path = garch_variance(fit_window, garch_parameters)
            last_shock = fit_window[-1] - garch_parameters.mean
            garch_variance_forecast = float(
                garch_parameters.omega
                + garch_parameters.alpha * last_shock**2
                + garch_parameters.beta * variance_path[-1]
            )
        else:
            last_shock = values[position - 1] - garch_parameters.mean
            garch_variance_forecast = float(
                garch_parameters.omega
                + garch_parameters.alpha * last_shock**2
                + garch_parameters.beta * garch_variance_forecast
            )

        window_500 = values[position - window : position]
        chosen_window = adaptive_window(
            values,
            position,
            short=adaptive_short,
            long=adaptive_long,
            threshold=adaptive_threshold,
            default=window,
        )
        window_adaptive = values[position - chosen_window : position]

        mean_500 = float(window_500.mean())
        std_500 = float(window_500.std(ddof=1))
        mean_adaptive = float(window_adaptive.mean())
        std_adaptive = float(window_adaptive.std(ddof=1))
        if std_500 <= 0 or std_adaptive <= 0:
            raise ValueError("the estimation window has zero volatility")

        hist500 = historical_risk(window_500, level)
        hist_adaptive = historical_risk(window_adaptive, level)
        param500 = conditional_normal_risk(mean_500, std_500, level)
        param_adaptive = conditional_normal_risk(mean_adaptive, std_adaptive, level)
        ewma = conditional_normal_risk(0.0, float(np.sqrt(ewma_variances[position])), level)
        garch = conditional_normal_risk(
            garch_parameters.mean,
            float(np.sqrt(garch_variance_forecast)),
            level,
        )

        residuals_500 = (window_500 - mean_500) / std_500
        residuals_adaptive = (window_adaptive - mean_adaptive) / std_adaptive
        residuals_ewma = _ewma_residuals(window_500, ewma_lambda)
        garch_path = garch_variance(window_500, garch_parameters)
        residuals_garch = standardized_residuals(
            window_500,
            garch_path,
            garch_parameters.mean,
        )

        forecasts = {
            "hist500": (hist500, mean_500, std_500, residuals_500),
            "param500": (param500, mean_500, std_500, residuals_500),
            "ewma": (
                ewma,
                0.0,
                float(np.sqrt(ewma_variances[position])),
                residuals_ewma,
            ),
            "garch": (
                garch,
                garch_parameters.mean,
                float(np.sqrt(garch_variance_forecast)),
                residuals_garch,
            ),
            "hist_adaptive": (
                hist_adaptive,
                mean_adaptive,
                std_adaptive,
                residuals_adaptive,
            ),
            "param_adaptive": (
                param_adaptive,
                mean_adaptive,
                std_adaptive,
                residuals_adaptive,
            ),
        }

        row: dict[str, float | int | bool] = {
            "return": float(values[position]),
            "loss": float(-values[position]),
            "window": chosen_window,
            "vol_ewma": float(np.sqrt(ewma_variances[position])),
            "vol_garch": float(np.sqrt(garch_variance_forecast)),
        }
        forecast_seed = seed + (position - window)
        for model, (estimate, mean, volatility, residuals) in forecasts.items():
            simulated = fhs_risk(
                mean,
                volatility,
                residuals,
                level,
                n_scenarios=n_scenarios,
                seed=forecast_seed,
            )
            row[f"var_{model}"] = estimate.var
            row[f"cvar_{model}"] = estimate.cvar
            row[f"es_sim_{model}"] = simulated.cvar
            row[f"violation_{model}"] = row["loss"] > estimate.var
        rows.append(row)

    columns = ["return", "loss", "window", "vol_ewma", "vol_garch"]
    for model in MODELS:
        columns.extend(
            [
                f"var_{model}",
                f"cvar_{model}",
                f"es_sim_{model}",
                f"violation_{model}",
            ]
        )
    frame = pd.DataFrame(rows, index=returns.index[window:], columns=columns)
    frame.index.name = "date"
    return frame


def model_losses(backtest: pd.DataFrame, *, level: float = 0.95) -> pd.DataFrame:
    """Quantile losses for every model in the comparison."""
    losses = {}
    for model in MODELS:
        column = f"var_{model}"
        if column not in backtest.columns:
            raise ValueError(f"missing column: {column}")
        losses[model] = quantile_loss(
            backtest["return"].to_numpy(),
            backtest[column].to_numpy(),
            level,
        )
    return pd.DataFrame(losses, index=backtest.index)


def conditional_summary(backtest: pd.DataFrame, *, level: float = 0.95) -> pd.DataFrame:
    """Coverage, mean loss and mean risk for every model."""
    losses = model_losses(backtest, level=level)
    n = len(backtest)
    p0 = 1.0 - float(level)
    rows = []
    for model in MODELS:
        violation_column = f"violation_{model}"
        if violation_column not in backtest.columns:
            raise ValueError(f"missing column: {violation_column}")
        violations = backtest[violation_column].to_numpy(dtype=int)
        count = int(violations.sum())
        kupiec = kupiec_pof(count, n, p0)
        independence = christoffersen_independence(violations)
        conditional = christoffersen_conditional_coverage(violations, p0)
        rows.append(
            {
                "model": model,
                "observations": n,
                "violations": count,
                "expected": n * p0,
                "violation_rate": count / n,
                "kupiec_lr": kupiec.statistic,
                "kupiec_p": kupiec.p_value,
                "christoffersen_lr": independence.statistic,
                "christoffersen_p": independence.p_value,
                "conditional_lr": conditional.statistic,
                "conditional_p": conditional.p_value,
                "mean_loss": float(losses[model].mean()),
                "mean_var": float(backtest[f"var_{model}"].mean()),
                "mean_cvar": float(backtest[f"cvar_{model}"].mean()),
                "mean_es_sim": float(backtest[f"es_sim_{model}"].mean()),
            }
        )
    summary = pd.DataFrame(rows).set_index("model")
    summary["rank"] = summary["mean_loss"].rank(method="min").astype(int)
    return summary.sort_values("mean_loss")


def pairwise_dm(
    backtest: pd.DataFrame,
    *,
    level: float = 0.95,
    lags: int = 5,
) -> pd.DataFrame:
    """All pairwise Diebold-Mariano tests with Holm-adjusted p-values."""
    losses = model_losses(backtest, level=level)
    rows = []
    for first_index, first in enumerate(MODELS):
        for second in MODELS[first_index + 1 :]:
            result = diebold_mariano(
                losses[first].to_numpy(),
                losses[second].to_numpy(),
                lags=lags,
            )
            rows.append(
                {
                    "model_a": first,
                    "model_b": second,
                    "mean_loss_a": float(losses[first].mean()),
                    "mean_loss_b": float(losses[second].mean()),
                    "mean_difference": result.mean_difference,
                    "dm_stat": result.statistic,
                    "dm_p": result.p_value,
                    "dm_p_holm": float("nan"),
                }
            )
    table = pd.DataFrame(rows)
    table["dm_p_holm"] = holm_bonferroni(table["dm_p"].to_numpy())
    return table


def winner_decision(
    summary: pd.DataFrame,
    pairwise: pd.DataFrame,
    *,
    alpha: float = 0.05,
) -> dict[str, object]:
    """Apply the pre-registered winner rule to the comparison table."""
    ordered = summary.sort_values("mean_loss")
    best = str(ordered.index[0])
    second = str(ordered.index[1])
    row = pairwise[
        ((pairwise["model_a"] == best) & (pairwise["model_b"] == second))
        | ((pairwise["model_a"] == second) & (pairwise["model_b"] == best))
    ].iloc[0]
    p_value = float(row["dm_p_holm"])
    clear = p_value < alpha
    return {
        "best": best,
        "second": second,
        "best_mean_loss": float(ordered.iloc[0]["mean_loss"]),
        "second_mean_loss": float(ordered.iloc[1]["mean_loss"]),
        "dm_p_holm": p_value,
        "alpha": alpha,
        "clear_winner": clear,
        "decision": (
            f"{MODEL_LABELS[best]} wins clearly"
            if clear
            else f"No clear winner between {MODEL_LABELS[best]} and {MODEL_LABELS[second]}"
        ),
    }


def stress_year_table(
    backtest: pd.DataFrame,
    *,
    level: float = 0.95,
    years: tuple[int, ...] = (2020, 2022, 2026),
) -> pd.DataFrame:
    """Coverage and mean loss in the pre-registered stress years."""
    losses = model_losses(backtest, level=level)
    p0 = 1.0 - float(level)
    rows = []
    for model in MODELS:
        violation_column = f"violation_{model}"
        for year in years:
            mask = backtest.index.year == year
            subset = backtest.loc[mask]
            if subset.empty:
                continue
            violations = int(subset[violation_column].sum())
            observations = len(subset)
            rows.append(
                {
                    "model": model,
                    "year": year,
                    "observations": observations,
                    "violations": violations,
                    "expected": observations * p0,
                    "rate": violations / observations,
                    "mean_loss": float(losses.loc[mask, model].mean()),
                }
            )
    return pd.DataFrame(rows)


def es_table(
    backtest: pd.DataFrame,
    *,
    level: float = 0.95,
    block_length: int = 20,
    n_boot: int = 10_000,
    seed: int = 42,
) -> pd.DataFrame:
    """Mean model CVaR and simulated ES with block-bootstrap intervals."""
    rows = []
    for model in MODELS:
        cvar = backtest[f"cvar_{model}"].to_numpy(dtype=float)
        es_sim = backtest[f"es_sim_{model}"].to_numpy(dtype=float)
        cvar_low, cvar_high = block_bootstrap_mean_ci(
            cvar,
            block_length=block_length,
            n_boot=n_boot,
            seed=seed,
        )
        es_low, es_high = block_bootstrap_mean_ci(
            es_sim,
            block_length=block_length,
            n_boot=n_boot,
            seed=seed,
        )
        rows.append(
            {
                "model": model,
                "cvar_type": ("parametric" if model in PARAMETRIC_MODELS else "empirical"),
                "mean_cvar": float(np.mean(cvar)),
                "cvar_ci_low": cvar_low,
                "cvar_ci_high": cvar_high,
                "mean_es_sim": float(np.mean(es_sim)),
                "es_ci_low": es_low,
                "es_ci_high": es_high,
            }
        )
    return pd.DataFrame(rows).set_index("model")

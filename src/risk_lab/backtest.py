"""Rolling one-day-ahead VaR backtest."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import numpy as np
import pandas as pd

from .data import portfolio_returns, weights_vector
from .stats import (
    christoffersen_conditional_coverage,
    christoffersen_independence,
    kupiec_pof,
)
from .var import (
    historical_risk,
    monte_carlo_risk,
    parametric_risk,
)

METHODS: tuple[str, ...] = ("historical", "parametric", "monte_carlo")


def rolling_backtest(
    returns: pd.DataFrame,
    weights: Mapping[str, float],
    *,
    window: int = 500,
    level: float = 0.95,
    n_scenarios: int = 100_000,
    seed: int = 42,
    methods: Sequence[str] = METHODS,
) -> pd.DataFrame:
    """Run a walk-forward one-day VaR backtest.

    For each forecast date t, the model is estimated only on the previous
    ``window`` observations and predicts the loss on t. The estimation window
    rolls forward one day at a time, so there is no lookahead.

    Returns a DataFrame indexed by forecast date with the realized return and
    loss, the VaR and CVaR of each method, and one boolean violation column per
    method. A violation occurs when the realized loss is strictly greater than
    VaR.
    """
    if not isinstance(returns, pd.DataFrame):
        raise TypeError("returns must be a pandas DataFrame")
    if returns.empty:
        raise ValueError("returns are empty")
    if returns.isna().any().any():
        raise ValueError("returns contain missing values")
    if not np.isfinite(returns.to_numpy(dtype=float)).all():
        raise ValueError("returns contain non-finite values")

    method_list = list(methods)
    if not method_list:
        raise ValueError("at least one method is required")
    unknown = [method for method in method_list if method not in METHODS]
    if unknown:
        raise ValueError(f"unknown methods: {unknown}")
    if len(set(method_list)) != len(method_list):
        raise ValueError("methods must not repeat")

    if isinstance(window, bool) or not isinstance(window, int):
        raise ValueError("window must be an integer")
    if window < 2:
        raise ValueError("window must be at least 2")
    if len(returns) <= window:
        raise ValueError(
            f"need more than {window} returns, got {len(returns)}"
        )
    if not 0.0 < float(level) < 1.0:
        raise ValueError("level must be strictly between 0 and 1")

    vector = weights_vector(list(returns.columns), weights)
    portfolio = portfolio_returns(returns, weights)
    asset_values = returns.to_numpy(dtype=float)
    portfolio_values = portfolio.to_numpy(dtype=float)
    forecast_dates = returns.index[window:]

    rows: list[dict[str, float | bool]] = []
    for position in range(window, len(returns)):
        window_assets = asset_values[position - window : position]
        window_portfolio = portfolio_values[position - window : position]
        realized = float(portfolio_values[position])
        row: dict[str, float | bool] = {
            "return": realized,
            "loss": -realized,
        }

        if "historical" in method_list:
            estimate = historical_risk(window_portfolio, level)
            row["var_historical"] = estimate.var
            row["cvar_historical"] = estimate.cvar
            row["violation_historical"] = row["loss"] > estimate.var

        if "parametric" in method_list:
            estimate = parametric_risk(window_portfolio, level)
            row["var_parametric"] = estimate.var
            row["cvar_parametric"] = estimate.cvar
            row["violation_parametric"] = row["loss"] > estimate.var

        if "monte_carlo" in method_list:
            estimate = monte_carlo_risk(
                window_assets,
                vector,
                level,
                n_scenarios=n_scenarios,
                seed=seed + position,
            )
            row["var_monte_carlo"] = estimate.var
            row["cvar_monte_carlo"] = estimate.cvar
            row["violation_monte_carlo"] = row["loss"] > estimate.var

        rows.append(row)

    columns: list[str] = ["return", "loss"]
    for method in METHODS:
        if method in method_list:
            columns.extend(
                [
                    f"var_{method}",
                    f"cvar_{method}",
                    f"violation_{method}",
                ]
            )
    frame = pd.DataFrame(rows, index=forecast_dates, columns=columns)
    frame.index.name = "date"
    return frame


def summarize_backtest(
    backtest: pd.DataFrame, *, level: float = 0.95
) -> pd.DataFrame:
    """Build the comparative table of violations and coverage tests."""
    if backtest.empty:
        raise ValueError("backtest is empty")
    if not 0.0 < float(level) < 1.0:
        raise ValueError("level must be strictly between 0 and 1")

    n = len(backtest)
    p0 = 1.0 - float(level)
    rows: list[dict[str, float | int | str]] = []

    for method in METHODS:
        var_column = f"var_{method}"
        violation_column = f"violation_{method}"
        if var_column not in backtest.columns:
            continue
        if violation_column not in backtest.columns:
            raise ValueError(f"missing column: {violation_column}")

        violations = backtest[violation_column].to_numpy(dtype=int)
        count = int(violations.sum())
        kupiec = kupiec_pof(count, n, p0)
        independence = christoffersen_independence(violations)
        conditional = christoffersen_conditional_coverage(violations, p0)

        rows.append(
            {
                "method": method,
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
            }
        )

    if not rows:
        raise ValueError("backtest has no method columns")
    return pd.DataFrame(rows).set_index("method")


def violations_by_year(
    backtest: pd.DataFrame, *, level: float = 0.95
) -> pd.DataFrame:
    """Count violations by calendar year for every method in the backtest.

    The result is indexed by ``method`` and ``year`` and contains the number
    of observations, violations, expected violations and the violation rate.
    """
    if backtest.empty:
        raise ValueError("backtest is empty")
    if not isinstance(backtest.index, pd.DatetimeIndex):
        raise ValueError("backtest index must be a DatetimeIndex")
    if not 0.0 < float(level) < 1.0:
        raise ValueError("level must be strictly between 0 and 1")

    years = backtest.index.year.to_numpy()
    rows: list[pd.DataFrame] = []
    for method in METHODS:
        violation_column = f"violation_{method}"
        if violation_column not in backtest.columns:
            continue
        grouped = backtest.groupby(years)[violation_column].agg(["count", "sum"])
        grouped = grouped.rename(
            columns={"count": "observations", "sum": "violations"}
        )
        grouped["expected"] = grouped["observations"] * (1.0 - float(level))
        grouped["rate"] = grouped["violations"] / grouped["observations"]
        grouped["method"] = method
        grouped = grouped.reset_index().rename(columns={"index": "year"})
        rows.append(grouped)

    if not rows:
        raise ValueError("backtest has no method columns")
    return pd.concat(rows, ignore_index=True).set_index(["method", "year"])

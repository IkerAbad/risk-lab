"""Figures for the VaR backtest."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

METHOD_LABELS: dict[str, str] = {
    "historical": "Historical",
    "parametric": "Parametric",
    "monte_carlo": "Monte Carlo",
}
METHOD_COLORS: dict[str, str] = {
    "historical": "tab:blue",
    "parametric": "tab:orange",
    "monte_carlo": "tab:green",
}
CONDITIONAL_LABELS: dict[str, str] = {
    "hist500": "Historical 500",
    "param500": "Parametric 500",
    "ewma": "EWMA",
    "garch": "GARCH(1,1)",
    "hist_adaptive": "Historical adaptive",
    "param_adaptive": "Parametric adaptive",
}
CONDITIONAL_COLORS: dict[str, str] = {
    "hist500": "tab:blue",
    "param500": "tab:orange",
    "ewma": "tab:green",
    "garch": "tab:red",
    "hist_adaptive": "tab:purple",
    "param_adaptive": "tab:brown",
}


def _validate_backtest(backtest: pd.DataFrame, level: float) -> None:
    if not isinstance(backtest, pd.DataFrame):
        raise TypeError("backtest must be a pandas DataFrame")
    if backtest.empty:
        raise ValueError("backtest is empty")
    if not isinstance(backtest.index, pd.DatetimeIndex):
        raise ValueError("backtest index must be a DatetimeIndex")
    if "return" not in backtest.columns:
        raise ValueError("backtest is missing the return column")
    if not 0.0 < float(level) < 1.0:
        raise ValueError("level must be strictly between 0 and 1")


def _save(fig: plt.Figure, path: str | Path | None) -> None:
    if path is not None:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(destination, dpi=150, bbox_inches="tight")


def plot_returns_with_violations(
    backtest: pd.DataFrame,
    *,
    method: str = "historical",
    level: float = 0.95,
    path: str | Path | None = None,
    figsize: tuple[float, float] = (11.0, 4.5),
) -> plt.Figure:
    """Plot portfolio returns and mark VaR violations."""
    if method not in METHOD_LABELS:
        raise ValueError(f"unknown method: {method}")
    _validate_backtest(backtest, level)
    var_column = f"var_{method}"
    violation_column = f"violation_{method}"
    if var_column not in backtest.columns or violation_column not in backtest.columns:
        raise ValueError(f"backtest is missing {var_column} or {violation_column}")

    label = METHOD_LABELS[method]
    violations = backtest.loc[backtest[violation_column]]

    fig, ax = plt.subplots(figsize=figsize)
    ax.plot(
        backtest.index,
        backtest["return"] * 100.0,
        color="0.30",
        linewidth=0.6,
        label="Portfolio return",
    )
    ax.plot(
        backtest.index,
        -backtest[var_column] * 100.0,
        color="tab:red",
        linewidth=0.8,
        label=f"{label} VaR ({level:.0%})",
    )
    ax.scatter(
        violations.index,
        violations["return"] * 100.0,
        color="tab:red",
        edgecolors="none",
        s=14,
        zorder=3,
        label=f"Violations ({len(violations)})",
    )
    ax.axhline(0.0, color="0.75", linewidth=0.6)
    ax.set_ylabel("Daily return (%)")
    ax.set_title(f"Portfolio returns and {level:.0%} VaR violations, {label.lower()} method")
    ax.grid(axis="y", alpha=0.2)
    ax.margins(x=0.01)
    ax.legend(loc="lower left", frameon=False, fontsize=8, ncol=3)
    fig.autofmt_xdate()
    fig.tight_layout()
    _save(fig, path)
    return fig


def plot_rolling_var(
    backtest: pd.DataFrame,
    *,
    level: float = 0.95,
    path: str | Path | None = None,
    figsize: tuple[float, float] = (11.0, 4.5),
) -> plt.Figure:
    """Plot realized daily loss against rolling VaR from the three methods."""
    _validate_backtest(backtest, level)
    fig, ax = plt.subplots(figsize=figsize)
    ax.plot(
        backtest.index,
        -backtest["return"] * 100.0,
        color="0.30",
        linewidth=0.6,
        label="Realized loss",
    )
    for method, label in METHOD_LABELS.items():
        var_column = f"var_{method}"
        if var_column not in backtest.columns:
            continue
        ax.plot(
            backtest.index,
            backtest[var_column] * 100.0,
            color=METHOD_COLORS[method],
            linewidth=1.0,
            label=f"{label} VaR",
        )
    ax.set_ylabel("One-day loss (%)")
    ax.set_title(f"Rolling one-day VaR at {level:.0%} versus realized loss")
    ax.grid(axis="y", alpha=0.2)
    ax.margins(x=0.01)
    ax.legend(loc="upper left", frameon=False, fontsize=8, ncol=4)
    fig.autofmt_xdate()
    fig.tight_layout()
    _save(fig, path)
    return fig


def plot_conditional_var(
    backtest: pd.DataFrame,
    *,
    level: float = 0.95,
    path: str | Path | None = None,
    figsize: tuple[float, float] = (11.0, 4.5),
) -> plt.Figure:
    """Plot realized loss against the main conditional VaR models."""
    _validate_backtest(backtest, level)
    models = ("hist500", "param500", "ewma", "garch", "hist_adaptive")
    for model in models:
        column = f"var_{model}"
        if column not in backtest.columns:
            raise ValueError(f"backtest is missing {column}")

    fig, ax = plt.subplots(figsize=figsize)
    ax.plot(
        backtest.index,
        -backtest["return"] * 100.0,
        color="0.30",
        linewidth=0.6,
        label="Realized loss",
    )
    for model in models:
        ax.plot(
            backtest.index,
            backtest[f"var_{model}"] * 100.0,
            color=CONDITIONAL_COLORS[model],
            linewidth=1.0,
            label=CONDITIONAL_LABELS[model],
        )
    ax.set_ylabel("One-day loss (%)")
    ax.set_title(f"Conditional VaR comparison at {level:.0%}")
    ax.grid(axis="y", alpha=0.2)
    ax.margins(x=0.01)
    ax.legend(loc="upper left", frameon=False, fontsize=8, ncol=3)
    fig.autofmt_xdate()
    fig.tight_layout()
    _save(fig, path)
    return fig


def plot_es_ci(
    es_table: pd.DataFrame,
    *,
    level: float = 0.95,
    path: str | Path | None = None,
    figsize: tuple[float, float] = (10.0, 4.5),
) -> plt.Figure:
    """Plot the mean simulated ES with its block-bootstrap interval."""
    if not isinstance(es_table, pd.DataFrame):
        raise TypeError("es_table must be a pandas DataFrame")
    if es_table.empty:
        raise ValueError("es_table is empty")
    if not 0.0 < float(level) < 1.0:
        raise ValueError("level must be strictly between 0 and 1")
    required = {"mean_es_sim", "es_ci_low", "es_ci_high", "mean_cvar"}
    missing = required - set(es_table.columns)
    if missing:
        raise ValueError(f"es_table is missing columns: {sorted(missing)}")
    values = es_table[list(required)].to_numpy(dtype=float)
    if not np.isfinite(values).all():
        raise ValueError("es_table contains non-finite values")
    if (es_table["es_ci_low"] > es_table["mean_es_sim"]).any() or (
        es_table["es_ci_high"] < es_table["mean_es_sim"]
    ).any():
        raise ValueError("the ES interval does not contain the mean")

    labels = [CONDITIONAL_LABELS.get(str(model), str(model)) for model in es_table.index]
    positions = np.arange(len(es_table))
    means = es_table["mean_es_sim"].to_numpy() * 100.0
    lower = (es_table["mean_es_sim"] - es_table["es_ci_low"]).to_numpy() * 100.0
    upper = (es_table["es_ci_high"] - es_table["mean_es_sim"]).to_numpy() * 100.0

    fig, ax = plt.subplots(figsize=figsize)
    ax.barh(
        positions,
        means,
        xerr=[lower, upper],
        color="tab:blue",
        alpha=0.6,
        capsize=4,
        label="Simulated ES and 95% interval",
    )
    ax.scatter(
        es_table["mean_cvar"].to_numpy() * 100.0,
        positions,
        color="black",
        marker="|",
        s=120,
        label="Model CVaR",
    )
    ax.set_yticks(positions)
    ax.set_yticklabels(labels)
    ax.invert_yaxis()
    ax.set_xlabel("One-day ES (%)")
    ax.set_title(f"Mean one-day ES at {level:.0%} with bootstrap intervals")
    ax.grid(axis="x", alpha=0.2)
    ax.legend(loc="lower right", frameon=False, fontsize=8)
    fig.tight_layout()
    _save(fig, path)
    return fig

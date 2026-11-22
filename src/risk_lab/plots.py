"""Figures for the VaR backtest."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
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

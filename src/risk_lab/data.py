"""Price loading and fixed-weight portfolio return construction."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

import numpy as np
import pandas as pd

DEFAULT_TICKERS: tuple[str, ...] = ("SPY", "TLT", "GLD")
DEFAULT_WEIGHTS: dict[str, float] = {"SPY": 0.50, "TLT": 0.35, "GLD": 0.15}


def load_prices(path: str | Path) -> pd.DataFrame:
    """Load a wide price CSV with a Date column and one column per asset.

    The function enforces the invariants the rest of the package relies on:
    unique, sorted dates, no missing values, finite values and strictly
    positive prices.
    """
    frame = pd.read_csv(path, parse_dates=["Date"], index_col="Date")
    if frame.empty:
        raise ValueError("price data is empty")
    if not isinstance(frame.index, pd.DatetimeIndex):
        raise ValueError("the Date column could not be parsed as dates")
    frame = frame.sort_index()
    if frame.index.has_duplicates:
        raise ValueError("price data contains duplicate dates")
    if frame.isna().any().any():
        raise ValueError("price data contains missing values")

    values = frame.to_numpy(dtype=float)
    if not np.isfinite(values).all():
        raise ValueError("price data contains non-finite values")
    if (values <= 0).any():
        raise ValueError("prices must be strictly positive")

    frame.columns = [str(column) for column in frame.columns]
    return frame.astype(float)


def compute_returns(prices: pd.DataFrame, *, log_returns: bool = False) -> pd.DataFrame:
    """Compute daily returns and drop the first row.

    Simple returns are the default: R_t = P_t / P_{t-1} - 1.
    Set ``log_returns=True`` for R_t = ln(P_t / P_{t-1}).
    """
    if prices.empty:
        raise ValueError("prices are empty")
    if log_returns:
        returns = np.log(prices / prices.shift(1))
    else:
        returns = prices.pct_change(fill_method=None)
    return returns.dropna(how="any")


def weights_vector(
    columns: Sequence[str], weights: Mapping[str, float]
) -> np.ndarray:
    """Return the portfolio weights in the same order as ``columns``."""
    missing = [column for column in columns if column not in weights]
    if missing:
        raise ValueError(f"missing weights for: {missing}")

    vector = np.array([float(weights[column]) for column in columns], dtype=float)
    if not np.isfinite(vector).all():
        raise ValueError("weights must be finite")
    if (vector < 0).any():
        raise ValueError("weights must be non-negative")
    total = float(vector.sum())
    if not np.isclose(total, 1.0, atol=1e-8):
        raise ValueError(f"weights must sum to 1, got {total}")
    return vector


def portfolio_returns(
    returns: pd.DataFrame, weights: Mapping[str, float]
) -> pd.Series:
    """Weighted portfolio returns with fixed weights and daily rebalancing.

    The portfolio return on day t is R_p,t = sum_i w_i * R_i,t.
    """
    if returns.empty:
        raise ValueError("returns are empty")
    vector = weights_vector(list(returns.columns), weights)
    values = returns.to_numpy(dtype=float) @ vector
    return pd.Series(values, index=returns.index, name="portfolio")

"""One-day Value at Risk and Expected Shortfall estimators.

Sign convention
---------------
All public functions return VaR and CVaR as positive losses. A VaR of 0.02
means a one-day loss of 2% of portfolio value. If R is a return, the loss is
L = -R and VaR is the upper tail quantile of L.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
from scipy.stats import norm


@dataclass(frozen=True)
class RiskEstimate:
    """VaR and CVaR for one confidence level, both as positive losses."""

    var: float
    cvar: float


def _validate_level(level: float) -> float:
    level = float(level)
    if not 0.0 < level < 1.0:
        raise ValueError("level must be strictly between 0 and 1")
    return level


def _as_returns(returns: Sequence[float] | np.ndarray) -> np.ndarray:
    values = np.asarray(returns, dtype=float)
    if values.ndim != 1:
        raise ValueError("returns must be one-dimensional")
    if values.size < 2:
        raise ValueError("at least two returns are required")
    if not np.isfinite(values).all():
        raise ValueError("returns must be finite")
    return values


def _validate_weights(weights: Sequence[float] | np.ndarray, n_assets: int) -> np.ndarray:
    vector = np.asarray(weights, dtype=float)
    if vector.ndim != 1:
        raise ValueError("weights must be one-dimensional")
    if vector.size != n_assets:
        raise ValueError(
            f"expected {n_assets} weights, got {vector.size}"
        )
    if not np.isfinite(vector).all():
        raise ValueError("weights must be finite")
    if (vector < 0).any():
        raise ValueError("weights must be non-negative")
    total = float(vector.sum())
    if not np.isclose(total, 1.0, atol=1e-8):
        raise ValueError(f"weights must sum to 1, got {total}")
    return vector


def historical_risk(
    returns: Sequence[float] | np.ndarray, level: float = 0.95
) -> RiskEstimate:
    """Empirical VaR and CVaR.

    VaR = -Q_{1-level}(R), where Q is the empirical quantile with linear
    interpolation. CVaR is the negative mean of returns at or below that
    quantile.
    """
    level = _validate_level(level)
    values = _as_returns(returns)
    quantile = float(np.quantile(values, 1.0 - level, method="linear"))
    tail = values[values <= quantile]
    return RiskEstimate(var=-quantile, cvar=float(-tail.mean()))


def historical_var(
    returns: Sequence[float] | np.ndarray, level: float = 0.95
) -> float:
    """Empirical one-day VaR as a positive loss."""
    return historical_risk(returns, level).var


def historical_cvar(
    returns: Sequence[float] | np.ndarray, level: float = 0.95
) -> float:
    """Empirical one-day CVaR as a positive loss."""
    return historical_risk(returns, level).cvar


def parametric_risk(
    returns: Sequence[float] | np.ndarray, level: float = 0.95
) -> RiskEstimate:
    """Normal VaR and CVaR from the sample mean and sample standard deviation.

    With mu and sigma estimated with ``ddof=1`` and z = Phi^{-1}(1 - level):

        VaR  = -(mu + sigma * z)
        CVaR = -mu + sigma * phi(z) / (1 - level)

    The CVaR expression is the closed-form mean of the normal loss tail.
    """
    level = _validate_level(level)
    values = _as_returns(returns)
    mu = float(values.mean())
    sigma = float(values.std(ddof=1))
    z = float(norm.ppf(1.0 - level))
    var = -(mu + sigma * z)
    cvar = -mu + sigma * float(norm.pdf(z)) / (1.0 - level)
    return RiskEstimate(var=float(var), cvar=float(cvar))


def parametric_var(
    returns: Sequence[float] | np.ndarray, level: float = 0.95
) -> float:
    """Normal one-day VaR as a positive loss."""
    return parametric_risk(returns, level).var


def parametric_cvar(
    returns: Sequence[float] | np.ndarray, level: float = 0.95
) -> float:
    """Normal one-day CVaR as a positive loss."""
    return parametric_risk(returns, level).cvar


def simulate_portfolio_returns(
    returns: Sequence[Sequence[float]] | np.ndarray,
    weights: Sequence[float] | np.ndarray,
    *,
    n_scenarios: int = 100_000,
    seed: int | None = 42,
) -> np.ndarray:
    """Simulate portfolio returns from a multivariate normal model.

    ``returns`` must be a T x N array of asset returns. The mean vector and
    the sample covariance matrix (ddof=1) are estimated from it. Each
    scenario is R = mu + L z, where L is the Cholesky factor of the
    covariance matrix and z is standard normal. The portfolio return is w'R.
    """
    if isinstance(n_scenarios, bool) or not isinstance(n_scenarios, int):
        raise ValueError("n_scenarios must be an integer")
    if n_scenarios < 1:
        raise ValueError("n_scenarios must be positive")

    values = np.asarray(returns, dtype=float)
    if values.ndim == 1:
        values = values.reshape(-1, 1)
    if values.ndim != 2:
        raise ValueError("returns must be a T x N array")
    if values.shape[0] < 2:
        raise ValueError("at least two observations are required")
    if values.shape[1] < 1:
        raise ValueError("at least one asset is required")
    if not np.isfinite(values).all():
        raise ValueError("returns must be finite")

    vector = _validate_weights(weights, values.shape[1])
    mean = values.mean(axis=0)
    covariance = np.atleast_2d(np.cov(values, rowvar=False, ddof=1))
    try:
        cholesky = np.linalg.cholesky(covariance)
    except np.linalg.LinAlgError as exc:
        raise ValueError(
            "the covariance matrix is not positive definite"
        ) from exc

    rng = np.random.default_rng(seed)
    shocks = rng.standard_normal((n_scenarios, values.shape[1]))
    simulated = mean + shocks @ cholesky.T
    return simulated @ vector


def monte_carlo_risk(
    returns: Sequence[Sequence[float]] | np.ndarray,
    weights: Sequence[float] | np.ndarray,
    level: float = 0.95,
    *,
    n_scenarios: int = 100_000,
    seed: int | None = 42,
) -> RiskEstimate:
    """Monte Carlo VaR and CVaR from a multivariate normal model.

    The empirical quantile and the empirical tail mean are taken over the
    simulated portfolio returns. A fixed seed makes the result reproducible.
    """
    level = _validate_level(level)
    simulated = simulate_portfolio_returns(
        returns,
        weights,
        n_scenarios=n_scenarios,
        seed=seed,
    )
    quantile = float(np.quantile(simulated, 1.0 - level, method="linear"))
    tail = simulated[simulated <= quantile]
    return RiskEstimate(var=-quantile, cvar=float(-tail.mean()))


def monte_carlo_var(
    returns: Sequence[Sequence[float]] | np.ndarray,
    weights: Sequence[float] | np.ndarray,
    level: float = 0.95,
    *,
    n_scenarios: int = 100_000,
    seed: int | None = 42,
) -> float:
    """Monte Carlo one-day VaR as a positive loss."""
    return monte_carlo_risk(
        returns,
        weights,
        level,
        n_scenarios=n_scenarios,
        seed=seed,
    ).var


def monte_carlo_cvar(
    returns: Sequence[Sequence[float]] | np.ndarray,
    weights: Sequence[float] | np.ndarray,
    level: float = 0.95,
    *,
    n_scenarios: int = 100_000,
    seed: int | None = 42,
) -> float:
    """Monte Carlo one-day CVaR as a positive loss."""
    return monte_carlo_risk(
        returns,
        weights,
        level,
        n_scenarios=n_scenarios,
        seed=seed,
    ).cvar

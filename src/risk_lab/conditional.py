"""Conditional volatility models and filtered historical simulation."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.optimize import OptimizeResult, minimize
from scipy.stats import norm

from .var import RiskEstimate


@dataclass(frozen=True)
class GarchParams:
    """Parameters of a GARCH(1,1) model with a constant mean."""

    omega: float
    alpha: float
    beta: float
    mean: float
    initial_variance: float
    converged: bool = True


def _validate_level(level: float) -> float:
    level = float(level)
    if not 0.0 < level < 1.0:
        raise ValueError("level must be strictly between 0 and 1")
    return level


def _as_returns(returns: np.ndarray | list[float], min_size: int = 2) -> np.ndarray:
    values = np.asarray(returns, dtype=float)
    if values.ndim != 1:
        raise ValueError("returns must be one-dimensional")
    if values.size < min_size:
        raise ValueError(f"at least {min_size} returns are required")
    if not np.isfinite(values).all():
        raise ValueError("returns must be finite")
    return values


def ewma_variance(
    returns: np.ndarray | list[float],
    lam: float = 0.94,
    initial_variance: float | None = None,
) -> np.ndarray:
    """EWMA conditional variance for each return using data through t-1.

    The recursion is ``v_t = lam v_t-1 + (1 - lam) r_t-1^2``. The first value is
    the initial variance. The return at t is not used for ``v_t``.
    """
    values = _as_returns(returns)
    lam = float(lam)
    if not 0.0 < lam < 1.0:
        raise ValueError("lam must be strictly between 0 and 1")

    if initial_variance is None:
        initial_variance = float(np.var(values, ddof=1))
    initial_variance = float(initial_variance)
    if not np.isfinite(initial_variance) or initial_variance <= 0:
        raise ValueError("initial_variance must be positive and finite")

    variance = np.empty(values.size, dtype=float)
    variance[0] = initial_variance
    for index in range(1, values.size):
        variance[index] = lam * variance[index - 1] + (1.0 - lam) * values[index - 1] ** 2
    return variance


def ewma_forecast(
    returns: np.ndarray | list[float],
    lam: float = 0.94,
    initial_variance: float | None = None,
) -> float:
    """One-step EWMA variance forecast after the last return in the window."""
    values = _as_returns(returns)
    variance = ewma_variance(values, lam, initial_variance)
    return float(lam * variance[-1] + (1.0 - lam) * values[-1] ** 2)


def _validate_garch_params(params: GarchParams) -> None:
    if not np.isfinite(params.mean):
        raise ValueError("the GARCH mean must be finite")
    if not np.isfinite(params.omega) or params.omega <= 0:
        raise ValueError("omega must be positive and finite")
    if not np.isfinite(params.alpha) or params.alpha < 0:
        raise ValueError("alpha must be non-negative and finite")
    if not np.isfinite(params.beta) or params.beta < 0:
        raise ValueError("beta must be non-negative and finite")
    if params.alpha + params.beta >= 1.0:
        raise ValueError("alpha + beta must be smaller than 1")
    if not np.isfinite(params.initial_variance) or params.initial_variance <= 0:
        raise ValueError("initial_variance must be positive and finite")


def garch_variance(returns: np.ndarray | list[float], params: GarchParams) -> np.ndarray:
    """In-sample GARCH(1,1) variance path using data through t-1."""
    values = _as_returns(returns)
    _validate_garch_params(params)
    centered = values - params.mean
    variance = np.empty(values.size, dtype=float)
    variance[0] = params.initial_variance
    for index in range(1, values.size):
        variance[index] = (
            params.omega
            + params.alpha * centered[index - 1] ** 2
            + params.beta * variance[index - 1]
        )
    return variance


def garch_forecast(returns: np.ndarray | list[float], params: GarchParams) -> float:
    """One-step GARCH variance forecast after the last return."""
    values = _as_returns(returns)
    variance = garch_variance(values, params)
    last_shock = values[-1] - params.mean
    return float(params.omega + params.alpha * last_shock**2 + params.beta * variance[-1])


def _garch_nll(
    parameters: np.ndarray,
    centered: np.ndarray,
    initial_variance: float,
) -> float:
    omega, alpha, beta = (float(value) for value in parameters)
    if (
        not np.isfinite(omega)
        or not np.isfinite(alpha)
        or not np.isfinite(beta)
        or omega <= 0
        or alpha < 0
        or beta < 0
        or alpha + beta >= 0.999
    ):
        return 1e12

    variance = np.empty(centered.size, dtype=float)
    variance[0] = initial_variance
    with np.errstate(over="ignore", invalid="ignore"):
        for index in range(1, centered.size):
            variance[index] = omega + alpha * centered[index - 1] ** 2 + beta * variance[index - 1]
    if not np.isfinite(variance).all() or (variance <= 0).any():
        return 1e12
    return float(0.5 * np.sum(np.log(variance) + centered**2 / variance))


def fit_garch11(
    returns: np.ndarray | list[float],
    *,
    mean: float | None = None,
) -> GarchParams:
    """Estimate a GARCH(1,1) model by Gaussian quasi-maximum likelihood.

    Three starting points are tried. If every optimization fails, the function
    returns the pre-registered fallback ``alpha = 0.05`` and ``beta = 0.90``
    with ``converged=False``.
    """
    values = _as_returns(returns, min_size=50)
    mu = float(np.mean(values)) if mean is None else float(mean)
    if not np.isfinite(mu):
        raise ValueError("mean must be finite")
    centered = values - mu
    initial_variance = float(np.var(centered, ddof=1))
    if not np.isfinite(initial_variance) or initial_variance <= 0:
        raise ValueError("the return variance must be positive and finite")

    starts = (
        np.array([0.05 * initial_variance, 0.05, 0.90]),
        np.array([0.10 * initial_variance, 0.10, 0.80]),
        np.array([0.02 * initial_variance, 0.02, 0.95]),
    )
    bounds = ((1e-12, None), (0.0, 0.998), (0.0, 0.998))
    constraints = ({"type": "ineq", "fun": lambda p: 0.999 - p[1] - p[2]},)

    best: OptimizeResult | None = None
    for start in starts:
        result = minimize(
            _garch_nll,
            start,
            args=(centered, initial_variance),
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
            options={"maxiter": 500, "ftol": 1e-10},
        )
        parameters = np.asarray(result.x, dtype=float)
        valid = (
            result.success
            and np.isfinite(result.fun)
            and parameters.size == 3
            and parameters[0] > 0
            and parameters[1] >= 0
            and parameters[2] >= 0
            and parameters[1] + parameters[2] < 0.999
        )
        if valid and (best is None or result.fun < best.fun):
            best = result

    if best is None:
        alpha = 0.05
        beta = 0.90
        return GarchParams(
            omega=initial_variance * (1.0 - alpha - beta),
            alpha=alpha,
            beta=beta,
            mean=mu,
            initial_variance=initial_variance,
            converged=False,
        )

    omega, alpha, beta = (float(value) for value in best.x)
    return GarchParams(
        omega=max(omega, 1e-12),
        alpha=alpha,
        beta=beta,
        mean=mu,
        initial_variance=initial_variance,
        converged=True,
    )


def conditional_normal_risk(
    mean: float,
    volatility: float,
    level: float = 0.95,
) -> RiskEstimate:
    """Normal VaR and CVaR from a conditional mean and volatility."""
    level = _validate_level(level)
    mean = float(mean)
    volatility = float(volatility)
    if not np.isfinite(mean):
        raise ValueError("mean must be finite")
    if not np.isfinite(volatility) or volatility <= 0:
        raise ValueError("volatility must be positive and finite")
    z = float(norm.ppf(1.0 - level))
    var = -(mean + volatility * z)
    cvar = -mean + volatility * float(norm.pdf(z)) / (1.0 - level)
    return RiskEstimate(var=float(var), cvar=float(cvar))


def standardized_residuals(
    returns: np.ndarray | list[float],
    variance: np.ndarray | list[float],
    mean: float = 0.0,
) -> np.ndarray:
    """Standardize returns by the conditional standard deviation."""
    values = _as_returns(returns)
    variances = np.asarray(variance, dtype=float)
    if variances.ndim != 1 or variances.size != values.size:
        raise ValueError("variance must be one-dimensional and match returns")
    if not np.isfinite(variances).all() or (variances <= 0).any():
        raise ValueError("variance must be positive and finite")
    mean = float(mean)
    if not np.isfinite(mean):
        raise ValueError("mean must be finite")
    return (values - mean) / np.sqrt(variances)


def fhs_risk(
    mean: float,
    volatility: float,
    residuals: np.ndarray | list[float],
    level: float = 0.95,
    *,
    n_scenarios: int = 10_000,
    seed: int | None = 42,
) -> RiskEstimate:
    """Filtered historical simulation VaR and ES for one day.

    The standardized residuals are resampled with replacement, scaled by the
    conditional volatility and shifted by the conditional mean. The simulated
    VaR is the lower quantile and the simulated ES is the mean of the tail.
    """
    level = _validate_level(level)
    mean = float(mean)
    volatility = float(volatility)
    if not np.isfinite(mean):
        raise ValueError("mean must be finite")
    if not np.isfinite(volatility) or volatility <= 0:
        raise ValueError("volatility must be positive and finite")
    pool = _as_returns(residuals)
    if isinstance(n_scenarios, bool) or not isinstance(n_scenarios, int):
        raise ValueError("n_scenarios must be an integer")
    if n_scenarios < 1:
        raise ValueError("n_scenarios must be positive")

    rng = np.random.default_rng(seed)
    draws = rng.choice(pool, size=n_scenarios, replace=True)
    simulated = mean + volatility * draws
    quantile = float(np.quantile(simulated, 1.0 - level, method="linear"))
    tail = simulated[simulated <= quantile]
    return RiskEstimate(var=-quantile, cvar=float(-tail.mean()))

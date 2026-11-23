"""Coverage tests for VaR backtests.

The two tests implemented here are the unconditional coverage test of Kupiec
(1995) and the independence test of Christoffersen (1998). Both are
likelihood-ratio tests. Their p-values come from the chi-square survival
function with one degree of freedom, never from a printed table.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
from scipy.special import xlogy
from scipy.stats import chi2, norm


@dataclass(frozen=True)
class TestResult:
    """Likelihood-ratio statistic and asymptotic p-value."""

    statistic: float
    p_value: float
    df: int
    valid: bool = True
    note: str = ""


@dataclass(frozen=True)
class DMResult:
    """Diebold-Mariano statistic for two loss series."""

    statistic: float
    p_value: float
    mean_difference: float
    lags: int


def _as_violations(
    violations: int | Sequence[int] | np.ndarray,
) -> np.ndarray:
    values = np.asarray(violations)
    if values.ndim != 1:
        raise ValueError("violations must be one-dimensional")
    if values.size < 2:
        raise ValueError("at least two observations are required")
    if not np.isin(values, [0, 1]).all():
        raise ValueError("violations must contain only 0 and 1")
    return values.astype(int)


def kupiec_pof(
    violations: int | Sequence[int] | np.ndarray,
    n: int | None = None,
    p0: float = 0.05,
) -> TestResult:
    """Kupiec proportion-of-failures test.

    ``violations`` may be the number of failures (with ``n`` supplied) or a
    binary sequence. Under the null the failure probability is ``p0``.

    LR_uc = -2 ln[ (1-p0)^(n-x) p0^x / ((1-x/n)^(n-x) (x/n)^x) ]
    """
    p0 = float(p0)
    if not 0.0 < p0 < 1.0:
        raise ValueError("p0 must be strictly between 0 and 1")

    if n is None:
        if isinstance(violations, (int, np.integer)):
            raise ValueError("n must be supplied when violations is a count")
        values = _as_violations(violations)
        x = int(values.sum())
        n = int(values.size)
    else:
        if isinstance(violations, (Sequence, np.ndarray)):
            raise ValueError("pass either a count or a sequence, not both")
        x = int(violations)
        n = int(n)
        if n < 1:
            raise ValueError("n must be positive")
        if not 0 <= x <= n:
            raise ValueError("violations must be between 0 and n")

    if x == 0:
        statistic = -2.0 * n * np.log(1.0 - p0)
    elif x == n:
        statistic = -2.0 * n * np.log(p0)
    else:
        p_hat = x / n
        log_null = (n - x) * np.log(1.0 - p0) + x * np.log(p0)
        log_alt = (n - x) * np.log(1.0 - p_hat) + x * np.log(p_hat)
        statistic = -2.0 * (log_null - log_alt)

    statistic = float(max(statistic, 0.0))
    return TestResult(
        statistic=statistic,
        p_value=float(chi2.sf(statistic, 1)),
        df=1,
    )


def christoffersen_independence(
    violations: Sequence[int] | np.ndarray,
) -> TestResult:
    """Christoffersen independence test.

    The test asks whether a violation today changes the probability of a
    violation tomorrow. Transition counts are indexed as n_ij, where i is the
    state yesterday and j is the state today. The null is pi01 = pi11.

    LR_ind = -2 ln[ (1-pi)^(n00+n10) pi^(n01+n11)
                    / ((1-pi01)^n00 pi01^n01 (1-pi11)^n10 pi11^n11) ]
    """
    values = _as_violations(violations)
    previous = values[:-1]
    current = values[1:]

    n00 = int(np.sum((previous == 0) & (current == 0)))
    n01 = int(np.sum((previous == 0) & (current == 1)))
    n10 = int(np.sum((previous == 1) & (current == 0)))
    n11 = int(np.sum((previous == 1) & (current == 1)))

    if (n00 + n01) == 0 or (n10 + n11) == 0:
        return TestResult(
            statistic=float("nan"),
            p_value=float("nan"),
            df=1,
            valid=False,
            note="both states must occur after a transition",
        )

    pi01 = n01 / (n00 + n01)
    pi11 = n11 / (n10 + n11)
    pi = (n01 + n11) / (n00 + n01 + n10 + n11)

    log_null = xlogy(n00 + n10, 1.0 - pi) + xlogy(n01 + n11, pi)
    log_alt = xlogy(n00, 1.0 - pi01) + xlogy(n01, pi01) + xlogy(n10, 1.0 - pi11) + xlogy(n11, pi11)
    statistic = float(-2.0 * (log_null - log_alt))
    if not np.isfinite(statistic):
        return TestResult(
            statistic=float("nan"),
            p_value=float("nan"),
            df=1,
            valid=False,
            note="likelihood ratio is not finite",
        )

    statistic = max(statistic, 0.0)
    return TestResult(
        statistic=statistic,
        p_value=float(chi2.sf(statistic, 1)),
        df=1,
    )


def christoffersen_conditional_coverage(
    violations: Sequence[int] | np.ndarray,
    p0: float = 0.05,
) -> TestResult:
    """Joint conditional coverage test.

    The test combines correct unconditional coverage and independence:

        LR_cc = LR_uc + LR_ind

    Under the null, LR_cc is asymptotically chi-square with two degrees of
    freedom. If the independence component is undefined, the joint test is
    undefined and the p-value is NaN.
    """
    p0 = float(p0)
    if not 0.0 < p0 < 1.0:
        raise ValueError("p0 must be strictly between 0 and 1")

    values = _as_violations(violations)
    unconditional = kupiec_pof(values, p0=p0)
    independence = christoffersen_independence(values)
    if not independence.valid:
        return TestResult(
            statistic=float("nan"),
            p_value=float("nan"),
            df=2,
            valid=False,
            note=independence.note,
        )

    statistic = float(unconditional.statistic + independence.statistic)
    return TestResult(
        statistic=statistic,
        p_value=float(chi2.sf(statistic, 2)),
        df=2,
    )


def quantile_loss(
    returns: Sequence[float] | np.ndarray,
    var_forecasts: Sequence[float] | np.ndarray,
    level: float = 0.95,
) -> np.ndarray:
    """Quantile loss for a positive-loss VaR forecast.

    With ``q_t = -VaR_t`` and ``tau = 1 - level``:

        rho_tau(R_t - q_t) = (tau - 1{R_t < q_t}) (R_t - q_t)
    """
    level = float(level)
    if not 0.0 < level < 1.0:
        raise ValueError("level must be strictly between 0 and 1")
    values = np.asarray(returns, dtype=float)
    forecasts = np.asarray(var_forecasts, dtype=float)
    if values.ndim != 1 or forecasts.ndim != 1:
        raise ValueError("returns and var_forecasts must be one-dimensional")
    if values.size != forecasts.size:
        raise ValueError("returns and var_forecasts must have the same length")
    if values.size < 2:
        raise ValueError("at least two observations are required")
    if not np.isfinite(values).all() or not np.isfinite(forecasts).all():
        raise ValueError("returns and var_forecasts must be finite")

    quantiles = -forecasts
    tau = 1.0 - level
    hits = (values < quantiles).astype(float)
    return (tau - hits) * (values - quantiles)


def diebold_mariano(
    loss_a: Sequence[float] | np.ndarray,
    loss_b: Sequence[float] | np.ndarray,
    *,
    lags: int = 5,
) -> DMResult:
    """Diebold-Mariano test for two loss series.

    The long-run variance uses a Newey-West estimator with ``lags`` lags. The
    p-value is two-sided from the standard normal distribution. A negative
    mean difference favors the first loss series.
    """
    first = np.asarray(loss_a, dtype=float)
    second = np.asarray(loss_b, dtype=float)
    if first.ndim != 1 or second.ndim != 1:
        raise ValueError("losses must be one-dimensional")
    if first.size != second.size:
        raise ValueError("losses must have the same length")
    if first.size < 2:
        raise ValueError("at least two observations are required")
    if not np.isfinite(first).all() or not np.isfinite(second).all():
        raise ValueError("losses must be finite")
    if isinstance(lags, bool) or not isinstance(lags, int) or lags < 0:
        raise ValueError("lags must be a non-negative integer")
    if first.size <= lags + 1:
        raise ValueError("the sample must be longer than lags + 1")

    difference = first - second
    mean_difference = float(difference.mean())
    if np.allclose(difference, 0.0):
        return DMResult(
            statistic=0.0,
            p_value=1.0,
            mean_difference=0.0,
            lags=lags,
        )

    centered = difference - mean_difference
    long_run_variance = float(np.mean(centered**2))
    for lag in range(1, lags + 1):
        covariance = float(np.mean(centered[lag:] * centered[:-lag]))
        weight = 1.0 - lag / (lags + 1.0)
        long_run_variance += 2.0 * weight * covariance
    if long_run_variance <= 0:
        raise ValueError("the long-run variance is not positive")

    statistic = mean_difference / np.sqrt(long_run_variance / first.size)
    p_value = float(2.0 * norm.sf(abs(statistic)))
    return DMResult(
        statistic=float(statistic),
        p_value=p_value,
        mean_difference=mean_difference,
        lags=lags,
    )


def holm_bonferroni(p_values: Sequence[float] | np.ndarray) -> np.ndarray:
    """Holm-Bonferroni adjusted p-values in the original order."""
    values = np.asarray(p_values, dtype=float)
    if values.ndim != 1 or values.size < 1:
        raise ValueError("p_values must be a non-empty one-dimensional array")
    if not np.isfinite(values).all():
        raise ValueError("p_values must be finite")
    if ((values < 0.0) | (values > 1.0)).any():
        raise ValueError("p_values must be between 0 and 1")

    order = np.argsort(values, kind="stable")
    adjusted = np.empty(values.size, dtype=float)
    m = values.size
    running = 0.0
    for rank, index in enumerate(order):
        candidate = min(1.0, (m - rank) * values[index])
        running = max(running, candidate)
        adjusted[index] = running
    return adjusted


def block_bootstrap_mean_ci(
    values: Sequence[float] | np.ndarray,
    *,
    block_length: int = 20,
    n_boot: int = 10_000,
    seed: int | None = 42,
    confidence: float = 0.95,
) -> tuple[float, float]:
    """Moving block bootstrap percentile interval for the mean."""
    sample = np.asarray(values, dtype=float)
    if sample.ndim != 1 or sample.size < 2:
        raise ValueError("values must be a one-dimensional array with two values")
    if not np.isfinite(sample).all():
        raise ValueError("values must be finite")
    if isinstance(block_length, bool) or not isinstance(block_length, int):
        raise ValueError("block_length must be an integer")
    if not 1 <= block_length <= sample.size:
        raise ValueError("block_length must be between 1 and the sample size")
    if isinstance(n_boot, bool) or not isinstance(n_boot, int) or n_boot < 1:
        raise ValueError("n_boot must be a positive integer")
    confidence = float(confidence)
    if not 0.0 < confidence < 1.0:
        raise ValueError("confidence must be strictly between 0 and 1")

    rng = np.random.default_rng(seed)
    n_blocks = int(np.ceil(sample.size / block_length))
    offsets = np.arange(block_length)
    means = np.empty(n_boot, dtype=float)
    for index in range(n_boot):
        starts = rng.integers(
            0,
            sample.size - block_length + 1,
            size=n_blocks,
        )
        positions = (starts[:, None] + offsets[None, :]).ravel()[: sample.size]
        means[index] = float(sample[positions].mean())

    alpha = (1.0 - confidence) / 2.0
    return (
        float(np.quantile(means, alpha, method="linear")),
        float(np.quantile(means, 1.0 - alpha, method="linear")),
    )

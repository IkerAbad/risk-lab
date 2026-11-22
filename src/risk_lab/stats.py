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
from scipy.stats import chi2


@dataclass(frozen=True)
class TestResult:
    """Likelihood-ratio statistic and asymptotic p-value."""

    statistic: float
    p_value: float
    df: int
    valid: bool = True
    note: str = ""


def _as_violations(violations: Sequence[int] | np.ndarray) -> np.ndarray:
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
    log_alt = (
        xlogy(n00, 1.0 - pi01)
        + xlogy(n01, pi01)
        + xlogy(n10, 1.0 - pi11)
        + xlogy(n11, pi11)
    )
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

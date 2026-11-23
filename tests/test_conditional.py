import numpy as np
import pytest
from scipy.stats import norm

from risk_lab.conditional import (
    GarchParams,
    _garch_nll,
    conditional_normal_risk,
    ewma_forecast,
    ewma_variance,
    fhs_risk,
    fit_garch11,
    garch_forecast,
    garch_variance,
    standardized_residuals,
)


def test_ewma_variance_hand_case():
    returns = np.array([0.01, -0.02, 0.03])
    variance = ewma_variance(returns, lam=0.9, initial_variance=0.0004)
    expected = np.array([0.0004, 0.00037, 0.000373])
    assert variance == pytest.approx(expected)


def test_ewma_forecast_hand_case():
    returns = np.array([0.01, -0.02, 0.03])
    expected = 0.9 * 0.000373 + 0.1 * 0.03**2
    assert ewma_forecast(returns, lam=0.9, initial_variance=0.0004) == pytest.approx(expected)


def test_ewma_uses_the_sample_variance_by_default():
    returns = np.array([0.01, -0.02, 0.03])
    variance = ewma_variance(returns, lam=0.9)
    assert variance[0] == pytest.approx(float(np.var(returns, ddof=1)))


def test_ewma_invalid_inputs():
    with pytest.raises(ValueError, match="one-dimensional"):
        ewma_variance(np.ones((2, 2)))
    with pytest.raises(ValueError, match="at least 2"):
        ewma_variance([0.01])
    with pytest.raises(ValueError, match="finite"):
        ewma_variance([0.01, np.nan])
    with pytest.raises(ValueError, match="lam"):
        ewma_variance([0.01, 0.02], lam=1.0)
    with pytest.raises(ValueError, match="initial_variance"):
        ewma_variance([0.01, 0.02], initial_variance=0.0)
    with pytest.raises(ValueError, match="initial_variance"):
        ewma_variance([0.0, 0.0])


def test_garch_variance_hand_case():
    parameters = GarchParams(
        omega=1e-6,
        alpha=0.1,
        beta=0.8,
        mean=0.0,
        initial_variance=1e-4,
    )
    returns = np.array([0.01, -0.02, 0.03])
    variance = garch_variance(returns, parameters)
    expected = np.array([1e-4, 9.1e-5, 1.138e-4])
    assert variance == pytest.approx(expected)
    expected_forecast = 1e-6 + 0.1 * 0.03**2 + 0.8 * 1.138e-4
    assert garch_forecast(returns, parameters) == pytest.approx(expected_forecast)


def test_garch_parameter_validation():
    returns = np.array([0.01, -0.02, 0.03])
    invalid = (
        GarchParams(0.0, 0.1, 0.8, 0.0, 1e-4),
        GarchParams(np.nan, 0.1, 0.8, 0.0, 1e-4),
        GarchParams(1e-6, -0.1, 0.8, 0.0, 1e-4),
        GarchParams(1e-6, 0.1, -0.1, 0.0, 1e-4),
        GarchParams(1e-6, 0.1, 0.8, np.nan, 1e-4),
        GarchParams(1e-6, 0.1, 0.8, 0.0, 0.0),
        GarchParams(1e-6, 0.5, 0.5, 0.0, 1e-4),
    )
    for parameters in invalid:
        with pytest.raises(ValueError):
            garch_variance(returns, parameters)


def test_garch_nll_rejects_invalid_parameters():
    centered = np.array([0.01, -0.02])
    for parameters in (
        np.array([0.0, 0.1, 0.8]),
        np.array([1e-6, -0.1, 0.8]),
        np.array([1e-6, 0.1, -0.1]),
        np.array([1e-6, 0.5, 0.5]),
        np.array([np.nan, 0.1, 0.8]),
        np.array([1e-6, np.nan, 0.8]),
        np.array([1e-6, 0.1, np.nan]),
    ):
        assert _garch_nll(parameters, centered, 1e-4) == 1e12
    huge = np.array([1e308, 1e308])
    assert _garch_nll(np.array([1e-6, 0.1, 0.8]), huge, 1e-4) == 1e12


def _simulate_garch(
    n: int = 2_000,
    omega: float = 1e-6,
    alpha: float = 0.08,
    beta: float = 0.90,
    seed: int = 7,
) -> np.ndarray:
    rng = np.random.default_rng(seed)
    shocks = rng.standard_normal(n)
    returns = np.zeros(n)
    variance = np.zeros(n)
    variance[0] = omega / (1.0 - alpha - beta)
    for index in range(1, n):
        variance[index] = omega + alpha * returns[index - 1] ** 2 + beta * variance[index - 1]
        returns[index] = np.sqrt(variance[index]) * shocks[index]
    return returns


def test_fit_garch11_recovers_a_garch_process():
    returns = _simulate_garch()
    parameters = fit_garch11(returns)
    assert parameters.converged
    assert parameters.omega > 0
    assert 0.0 <= parameters.alpha < 1.0
    assert 0.0 <= parameters.beta < 1.0
    assert parameters.alpha + parameters.beta < 0.999
    assert parameters.alpha + parameters.beta > 0.5
    assert abs(parameters.mean) < 0.01


class _FakeOptimizeResult:
    success = False
    fun = 1.0
    x = np.array([1e-6, 0.05, 0.90])


def test_fit_garch11_uses_the_fallback(monkeypatch):
    monkeypatch.setattr(
        "risk_lab.conditional.minimize",
        lambda *args, **kwargs: _FakeOptimizeResult(),
    )
    returns = np.random.default_rng(1).normal(0.0, 0.01, 100)
    parameters = fit_garch11(returns)
    assert not parameters.converged
    assert parameters.alpha == 0.05
    assert parameters.beta == 0.90
    assert parameters.omega > 0


def test_fit_garch11_invalid_inputs():
    with pytest.raises(ValueError, match="one-dimensional"):
        fit_garch11(np.ones((2, 2)))
    with pytest.raises(ValueError, match="at least 50"):
        fit_garch11(np.ones(10))
    with pytest.raises(ValueError, match="finite"):
        fit_garch11(np.r_[np.ones(50), np.nan])
    with pytest.raises(ValueError, match="variance"):
        fit_garch11(np.ones(100))
    with pytest.raises(ValueError, match="mean must be finite"):
        fit_garch11(np.random.default_rng(1).normal(size=100), mean=np.nan)


def test_conditional_normal_risk_hand_case():
    estimate = conditional_normal_risk(0.0, 0.01, 0.95)
    z = norm.ppf(0.05)
    assert estimate.var == pytest.approx(-0.01 * z)
    assert estimate.cvar == pytest.approx(0.01 * norm.pdf(z) / 0.05)
    with pytest.raises(ValueError, match="between 0 and 1"):
        conditional_normal_risk(0.0, 0.01, 1.0)
    with pytest.raises(ValueError, match="mean must be finite"):
        conditional_normal_risk(np.nan, 0.01)
    with pytest.raises(ValueError, match="volatility"):
        conditional_normal_risk(0.0, 0.0)
    with pytest.raises(ValueError, match="volatility"):
        conditional_normal_risk(0.0, np.nan)


def test_standardized_residuals_hand_case():
    residuals = standardized_residuals(
        np.array([0.01, -0.02]),
        np.array([0.0001, 0.0004]),
    )
    assert residuals == pytest.approx([1.0, -1.0])
    with pytest.raises(ValueError, match="one-dimensional"):
        standardized_residuals(np.ones(2), np.ones((2, 1)))
    with pytest.raises(ValueError, match="match returns"):
        standardized_residuals(np.ones(2), np.ones(3))
    with pytest.raises(ValueError, match="positive"):
        standardized_residuals(np.ones(2), np.array([1.0, 0.0]))
    with pytest.raises(ValueError, match="mean must be finite"):
        standardized_residuals(np.ones(2), np.ones(2), mean=np.nan)


def test_fhs_risk_is_reproducible_and_has_a_tail():
    residuals = np.random.default_rng(3).normal(size=200)
    first = fhs_risk(
        0.0,
        0.01,
        residuals,
        0.95,
        n_scenarios=5_000,
        seed=123,
    )
    second = fhs_risk(
        0.0,
        0.01,
        residuals,
        0.95,
        n_scenarios=5_000,
        seed=123,
    )
    assert first == second
    assert first.var > 0
    assert first.cvar >= first.var


def test_fhs_risk_invalid_inputs():
    residuals = np.array([-1.0, 0.0, 1.0])
    with pytest.raises(ValueError, match="between 0 and 1"):
        fhs_risk(0.0, 0.01, residuals, 1.0)
    with pytest.raises(ValueError, match="mean must be finite"):
        fhs_risk(np.nan, 0.01, residuals)
    with pytest.raises(ValueError, match="volatility"):
        fhs_risk(0.0, 0.0, residuals)
    with pytest.raises(ValueError, match="one-dimensional"):
        fhs_risk(0.0, 0.01, np.ones((2, 2)))
    with pytest.raises(ValueError, match="at least 2"):
        fhs_risk(0.0, 0.01, [1.0])
    with pytest.raises(ValueError, match="integer"):
        fhs_risk(0.0, 0.01, residuals, n_scenarios=True)
    with pytest.raises(ValueError, match="positive"):
        fhs_risk(0.0, 0.01, residuals, n_scenarios=0)

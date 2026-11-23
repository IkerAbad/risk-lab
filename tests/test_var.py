import numpy as np
import pytest
from scipy.stats import norm

from risk_lab.var import (
    historical_cvar,
    historical_risk,
    historical_var,
    monte_carlo_cvar,
    monte_carlo_risk,
    monte_carlo_var,
    parametric_cvar,
    parametric_risk,
    parametric_var,
    simulate_portfolio_returns,
)

HAND_RETURNS = np.array([-0.10, -0.08, -0.06, -0.04, -0.02, 0.00, 0.01, 0.02, 0.03, 0.04])


def test_historical_var_matches_empirical_quantile():
    # At 80%, the linear empirical quantile is -0.064, so VaR is 0.064.
    assert historical_var(HAND_RETURNS, 0.80) == pytest.approx(0.064)
    assert historical_var(HAND_RETURNS, 0.80) == pytest.approx(
        -np.quantile(HAND_RETURNS, 0.20, method="linear")
    )


def test_historical_cvar_matches_tail_mean():
    # The 20% tail is [-0.10, -0.08], whose mean is -0.09.
    assert historical_cvar(HAND_RETURNS, 0.80) == pytest.approx(0.09)
    estimate = historical_risk(HAND_RETURNS, 0.80)
    assert estimate.var == pytest.approx(0.064)
    assert estimate.cvar == pytest.approx(0.09)


def test_parametric_var_is_the_negative_normal_quantile():
    returns = np.array([-0.03, -0.02, -0.01, 0.00, 0.01])
    mu = returns.mean()
    sigma = returns.std(ddof=1)
    z = norm.ppf(0.05)
    quantile = mu + sigma * z
    assert parametric_var(returns, 0.95) == pytest.approx(-quantile)
    assert quantile == pytest.approx(-0.03600741939377788)
    assert -quantile == pytest.approx(0.03600741939377788)


def test_parametric_cvar_matches_closed_form():
    returns = np.array([-0.03, -0.02, -0.01, 0.00, 0.01])
    mu = returns.mean()
    sigma = returns.std(ddof=1)
    z = norm.ppf(0.05)
    expected = -mu + sigma * norm.pdf(z) / 0.05
    assert parametric_cvar(returns, 0.95) == pytest.approx(expected)
    assert expected == pytest.approx(0.04261435315261965)


def test_parametric_cvar_is_larger_than_var():
    returns = np.array([-0.03, -0.02, -0.01, 0.00, 0.01])
    estimate = parametric_risk(returns, 0.95)
    assert estimate.cvar > estimate.var


def test_historical_cvar_is_larger_than_var():
    estimate = historical_risk(HAND_RETURNS, 0.80)
    assert estimate.cvar > estimate.var


def test_monte_carlo_is_reproducible_with_same_seed():
    rng = np.random.default_rng(7)
    asset_returns = rng.normal(
        loc=[0.0003, 0.0001, 0.0002],
        scale=[0.01, 0.008, 0.009],
        size=(400, 3),
    )
    weights = np.array([0.5, 0.35, 0.15])

    first = monte_carlo_risk(asset_returns, weights, 0.95, n_scenarios=20_000, seed=123)
    second = monte_carlo_risk(asset_returns, weights, 0.95, n_scenarios=20_000, seed=123)
    assert first == second
    assert monte_carlo_var(
        asset_returns, weights, 0.95, n_scenarios=20_000, seed=123
    ) == pytest.approx(first.var)


def test_monte_carlo_returns_positive_losses_for_a_loss_making_portfolio():
    rng = np.random.default_rng(11)
    asset_returns = rng.normal(
        loc=[-0.001, -0.0005, -0.0008],
        scale=[0.01, 0.008, 0.009],
        size=(300, 3),
    )
    estimate = monte_carlo_risk(
        asset_returns,
        np.array([0.5, 0.35, 0.15]),
        0.95,
        n_scenarios=10_000,
        seed=5,
    )
    assert estimate.var > 0.0
    assert estimate.cvar > estimate.var


def test_simulated_shape_and_weights():
    rng = np.random.default_rng(3)
    asset_returns = rng.normal(size=(200, 2))
    simulated = simulate_portfolio_returns(
        asset_returns,
        np.array([0.6, 0.4]),
        n_scenarios=1_000,
        seed=1,
    )
    assert simulated.shape == (1_000,)
    assert np.isfinite(simulated).all()


def test_invalid_inputs_raise():
    with pytest.raises(ValueError, match="between 0 and 1"):
        historical_var(HAND_RETURNS, 1.0)
    with pytest.raises(ValueError, match="one-dimensional"):
        parametric_var(np.ones((2, 2)))
    with pytest.raises(ValueError, match="at least two"):
        historical_var(np.array([0.01]))
    with pytest.raises(ValueError, match="finite"):
        historical_var(np.array([0.01, np.nan]))
    with pytest.raises(ValueError, match="sum to 1"):
        monte_carlo_risk(
            np.ones((10, 2)) * 0.01,
            np.array([0.5, 0.4]),
            n_scenarios=100,
        )
    with pytest.raises(ValueError, match="positive"):
        monte_carlo_risk(
            np.ones((10, 2)) * 0.01,
            np.array([0.5, 0.5]),
            n_scenarios=0,
        )


def test_singular_covariance_raises():
    constant = np.ones((20, 2)) * 0.01
    with pytest.raises(ValueError, match="positive definite"):
        monte_carlo_risk(
            constant,
            np.array([0.5, 0.5]),
            n_scenarios=100,
        )


def test_simulate_portfolio_returns_single_asset():
    returns = np.array([0.01, -0.02, 0.03, 0.00, -0.01])
    simulated = simulate_portfolio_returns(returns, [1.0], n_scenarios=100, seed=10)
    assert simulated.shape == (100,)
    assert np.isfinite(simulated).all()


def test_validate_weights_rejects_bad_shapes():
    returns = np.ones((20, 2)) * np.array([0.01, -0.01])
    with pytest.raises(ValueError, match="one-dimensional"):
        simulate_portfolio_returns(returns, np.ones((2, 2)), n_scenarios=10)
    with pytest.raises(ValueError, match="expected 2 weights"):
        simulate_portfolio_returns(returns, [1.0], n_scenarios=10)
    with pytest.raises(ValueError, match="finite"):
        simulate_portfolio_returns(returns, [np.nan, 1.0], n_scenarios=10)
    with pytest.raises(ValueError, match="non-negative"):
        simulate_portfolio_returns(returns, [1.5, -0.5], n_scenarios=10)


def test_monte_carlo_rejects_invalid_scenarios():
    returns = np.array([0.01, -0.02, 0.03, 0.00, -0.01])
    with pytest.raises(ValueError, match="integer"):
        monte_carlo_risk(returns, [1.0], n_scenarios=True)
    with pytest.raises(ValueError, match="integer"):
        monte_carlo_risk(returns, [1.0], n_scenarios=100.0)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="positive"):
        monte_carlo_risk(returns, [1.0], n_scenarios=0)


def test_monte_carlo_rejects_invalid_returns():
    with pytest.raises(ValueError, match="T x N"):
        monte_carlo_risk(np.ones((2, 2, 2)), [0.5, 0.5], n_scenarios=10)
    with pytest.raises(ValueError, match="at least two observations"):
        monte_carlo_risk(np.ones((1, 2)), [0.5, 0.5], n_scenarios=10)
    with pytest.raises(ValueError, match="at least one asset"):
        monte_carlo_risk(np.ones((2, 0)), [1.0], n_scenarios=10)
    with pytest.raises(ValueError, match="finite"):
        monte_carlo_risk(
            np.array([[0.01, np.nan], [0.02, 0.01]]),
            [0.5, 0.5],
            n_scenarios=10,
        )


def test_monte_carlo_rejects_invalid_level():
    returns = np.array([0.01, -0.02, 0.03, 0.00, -0.01])
    with pytest.raises(ValueError, match="between 0 and 1"):
        monte_carlo_risk(returns, [1.0], level=0.0, n_scenarios=10)


def test_monte_carlo_cvar_wrapper():
    returns = np.array([0.01, -0.02, 0.03, 0.00, -0.01])
    estimate = monte_carlo_risk(returns, [1.0], n_scenarios=1_000, seed=3)
    wrapper = monte_carlo_cvar(returns, [1.0], n_scenarios=1_000, seed=3)
    assert wrapper == pytest.approx(estimate.cvar)

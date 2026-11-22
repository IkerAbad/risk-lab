import numpy as np
import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from risk_lab.stats import (
    christoffersen_conditional_coverage,
    christoffersen_independence,
    kupiec_pof,
)
from risk_lab.var import historical_risk, parametric_risk

RETURNS = st.lists(
    st.floats(
        min_value=-0.5,
        max_value=0.5,
        allow_nan=False,
        allow_infinity=False,
    ),
    min_size=20,
    max_size=80,
)

VIOLATIONS = st.lists(
    st.integers(min_value=0, max_value=1),
    min_size=10,
    max_size=100,
).filter(lambda values: 0 in values and 1 in values)


@settings(max_examples=50, deadline=None)
@given(RETURNS)
def test_historical_cvar_is_at_least_var(values):
    estimate = historical_risk(np.asarray(values), 0.95)
    assert estimate.cvar >= estimate.var - 1e-12


@settings(max_examples=50, deadline=None)
@given(RETURNS)
def test_parametric_cvar_is_at_least_var(values):
    estimate = parametric_risk(np.asarray(values), 0.95)
    assert estimate.cvar >= estimate.var - 1e-12


@settings(max_examples=50, deadline=None)
@given(RETURNS)
def test_var_is_monotone_in_the_confidence_level(values):
    returns = np.asarray(values)
    historical_low = historical_risk(returns, 0.90).var
    historical_high = historical_risk(returns, 0.99).var
    assert historical_high >= historical_low - 1e-12

    parametric_low = parametric_risk(returns, 0.90).var
    parametric_high = parametric_risk(returns, 0.99).var
    assert parametric_high >= parametric_low - 1e-12


@settings(max_examples=50, deadline=None)
@given(
    st.integers(min_value=1, max_value=500),
    st.integers(min_value=0, max_value=500),
)
def test_kupiec_p_value_is_a_probability(n, x):
    assume(x <= n)
    result = kupiec_pof(x, n, 0.05)
    assert 0.0 <= result.p_value <= 1.0
    assert result.statistic >= 0.0


@settings(max_examples=50, deadline=None)
@given(VIOLATIONS)
def test_christoffersen_p_values_are_probabilities(values):
    independence = christoffersen_independence(values)
    assert independence.valid
    assert 0.0 <= independence.p_value <= 1.0
    assert independence.statistic >= 0.0

    conditional = christoffersen_conditional_coverage(values, 0.05)
    assert conditional.valid
    assert 0.0 <= conditional.p_value <= 1.0
    assert conditional.statistic >= 0.0


@settings(max_examples=30, deadline=None)
@given(RETURNS)
def test_historical_var_is_the_negative_empirical_quantile(values):
    returns = np.asarray(values)
    assert historical_risk(returns, 0.95).var == pytest.approx(
        -np.quantile(returns, 0.05, method="linear")
    )

import numpy as np
import pandas as pd
import pytest
from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st

from risk_lab.data import load_prices, portfolio_returns
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
    assume(independence.valid)
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


@settings(max_examples=50, deadline=None)
@given(
    st.lists(
        st.floats(
            min_value=-0.2,
            max_value=0.2,
            allow_nan=False,
            allow_infinity=False,
        ),
        min_size=3,
        max_size=3,
    ),
    st.floats(
        min_value=0.0,
        max_value=1.0,
        allow_nan=False,
        allow_infinity=False,
    ),
)
def test_portfolio_returns_are_linear_in_weights(values, mix):
    returns = pd.DataFrame([values], columns=["A", "B", "C"])
    first = {"A": 0.5, "B": 0.3, "C": 0.2}
    second = {"A": 0.1, "B": 0.6, "C": 0.3}
    mixed = {
        key: mix * first[key] + (1.0 - mix) * second[key] for key in first
    }
    expected = (
        mix * portfolio_returns(returns, first).iloc[0]
        + (1.0 - mix) * portfolio_returns(returns, second).iloc[0]
    )
    actual = portfolio_returns(returns, mixed).iloc[0]
    assert actual == pytest.approx(expected, abs=1e-12)


@settings(
    max_examples=20,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(
    st.lists(
        st.floats(
            min_value=1.0,
            max_value=1000.0,
            allow_nan=False,
            allow_infinity=False,
        ),
        min_size=3,
        max_size=8,
    ),
    st.lists(
        st.floats(
            min_value=1.0,
            max_value=1000.0,
            allow_nan=False,
            allow_infinity=False,
        ),
        min_size=3,
        max_size=8,
    ),
)
def test_load_prices_roundtrip(tmp_path, values_a, values_b):
    length = min(len(values_a), len(values_b))
    dates = pd.bdate_range("2024-01-02", periods=length)
    frame = pd.DataFrame(
        {"A": values_a[:length], "B": values_b[:length]}, index=dates
    )
    frame.index.name = "Date"
    path = tmp_path / "prices.csv"
    frame.to_csv(path)
    loaded = load_prices(path)
    assert loaded.index.equals(dates)
    assert list(loaded.columns) == ["A", "B"]
    assert loaded["A"].to_numpy() == pytest.approx(values_a[:length])
    assert loaded["B"].to_numpy() == pytest.approx(values_b[:length])

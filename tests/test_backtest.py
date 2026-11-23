import numpy as np
import pandas as pd
import pytest

from risk_lab.backtest import (
    rolling_backtest,
    summarize_backtest,
    violations_by_year,
)


def _single_asset(values: np.ndarray) -> pd.DataFrame:
    index = pd.bdate_range("2024-01-02", periods=len(values))
    return pd.DataFrame({"A": values}, index=index)


def test_rolling_backtest_no_lookahead_and_violation_flag():
    values = np.array([-0.01, -0.02, -0.03, -0.04, -0.05] + [-0.10] * 15)
    returns = _single_asset(values)
    backtest = rolling_backtest(
        returns,
        {"A": 1.0},
        window=5,
        level=0.95,
        methods=("historical", "parametric"),
    )

    assert len(backtest) == len(returns) - 5
    assert backtest.index[0] == returns.index[5]
    first = backtest.iloc[0]
    assert first["return"] == pytest.approx(-0.10)
    assert first["loss"] == pytest.approx(0.10)
    assert first["var_historical"] == pytest.approx(0.048)
    assert first["var_parametric"] == pytest.approx(0.05600741939377788)
    assert bool(first["violation_historical"])
    assert bool(first["violation_parametric"])


def test_rolling_backtest_does_not_use_future_returns():
    rng = np.random.default_rng(21)
    values = rng.normal(0.0, 0.01, size=40)
    returns = _single_asset(values)

    first = rolling_backtest(returns, {"A": 1.0}, window=5, methods=("historical",))

    changed = returns.copy()
    changed.iloc[-1, 0] = changed.iloc[-1, 0] + 0.50
    second = rolling_backtest(changed, {"A": 1.0}, window=5, methods=("historical",))

    pd.testing.assert_frame_equal(first.iloc[:-1], second.iloc[:-1])
    assert first["var_historical"].iloc[-1] == pytest.approx(second["var_historical"].iloc[-1])


def test_summary_table_counts_and_expected_values():
    n = 100
    index = pd.bdate_range("2024-01-02", periods=n)
    backtest = pd.DataFrame(
        {
            "return": np.zeros(n),
            "loss": np.zeros(n),
            "var_historical": np.full(n, 0.01),
            "cvar_historical": np.full(n, 0.02),
            "var_parametric": np.full(n, 0.01),
            "cvar_parametric": np.full(n, 0.02),
            "var_monte_carlo": np.full(n, 0.01),
            "cvar_monte_carlo": np.full(n, 0.02),
            "violation_historical": np.zeros(n, dtype=bool),
            "violation_parametric": np.zeros(n, dtype=bool),
            "violation_monte_carlo": np.zeros(n, dtype=bool),
        },
        index=index,
    )
    backtest.loc[backtest.index[[0, 20, 40, 60, 80]], "violation_historical"] = True
    backtest.loc[backtest.index[:10], "violation_parametric"] = True
    backtest.loc[backtest.index[[10, 30, 50]], "violation_monte_carlo"] = True

    summary = summarize_backtest(backtest, level=0.95)
    assert list(summary.index) == ["historical", "parametric", "monte_carlo"]
    assert summary.loc["historical", "violations"] == 5
    assert summary.loc["parametric", "violations"] == 10
    assert summary.loc["monte_carlo", "violations"] == 3
    assert summary.loc["historical", "expected"] == pytest.approx(5.0)
    assert summary.loc["historical", "violation_rate"] == pytest.approx(0.05)
    assert summary.loc["historical", "kupiec_p"] == pytest.approx(1.0)
    assert np.isfinite(summary.loc["parametric", "christoffersen_p"])
    assert np.isfinite(summary.loc["parametric", "conditional_p"])


def test_violations_by_year_counts():
    index = pd.to_datetime(["2024-12-30", "2024-12-31", "2025-01-02", "2025-01-03"])
    backtest = pd.DataFrame(
        {
            "violation_historical": [True, False, True, True],
            "violation_parametric": [False, False, True, False],
        },
        index=index,
    )
    result = violations_by_year(backtest, level=0.95)
    assert result.loc[("historical", 2024), "observations"] == 2
    assert result.loc[("historical", 2024), "violations"] == 1
    assert result.loc[("historical", 2024), "expected"] == pytest.approx(0.1)
    assert result.loc[("historical", 2025), "violations"] == 2
    assert result.loc[("parametric", 2025), "violations"] == 1


def test_violations_by_year_requires_a_datetime_index():
    backtest = pd.DataFrame({"violation_historical": [True, False]})
    with pytest.raises(ValueError, match="DatetimeIndex"):
        violations_by_year(backtest)


def test_monte_carlo_backtest_smoke():
    rng = np.random.default_rng(7)
    values = rng.normal(
        loc=[0.0002, 0.0001],
        scale=[0.01, 0.008],
        size=(80, 2),
    )
    index = pd.bdate_range("2024-01-02", periods=80)
    returns = pd.DataFrame(values, index=index, columns=["A", "B"])
    backtest = rolling_backtest(
        returns,
        {"A": 0.6, "B": 0.4},
        window=20,
        n_scenarios=500,
        seed=11,
        methods=("monte_carlo",),
    )
    assert len(backtest) == 60
    assert "var_monte_carlo" in backtest.columns
    assert "cvar_monte_carlo" in backtest.columns
    assert backtest.notna().all().all()
    assert backtest["violation_monte_carlo"].dtype == bool
    assert (backtest["var_monte_carlo"] > 0).all()


def test_backtest_validation():
    returns = _single_asset(np.zeros(10))
    with pytest.raises(ValueError, match="more than"):
        rolling_backtest(returns, {"A": 1.0}, window=10)
    with pytest.raises(ValueError, match="at least 2"):
        rolling_backtest(returns, {"A": 1.0}, window=1)
    with pytest.raises(ValueError, match="unknown"):
        rolling_backtest(returns, {"A": 1.0}, window=2, methods=("bootstrap",))
    with pytest.raises(ValueError, match="repeat"):
        rolling_backtest(
            returns,
            {"A": 1.0},
            window=2,
            methods=("historical", "historical"),
        )
    with pytest.raises(ValueError, match="between 0 and 1"):
        rolling_backtest(returns, {"A": 1.0}, window=2, level=1.0)


def test_rolling_backtest_rejects_bad_frames():
    with pytest.raises(TypeError, match="DataFrame"):
        rolling_backtest([1, 2, 3], {"A": 1.0})
    with pytest.raises(ValueError, match="empty"):
        rolling_backtest(pd.DataFrame(), {"A": 1.0})
    with pytest.raises(ValueError, match="missing"):
        rolling_backtest(_single_asset(np.array([0.01, np.nan, 0.02])), {"A": 1.0}, window=2)
    with pytest.raises(ValueError, match="non-finite"):
        rolling_backtest(_single_asset(np.array([0.01, np.inf, 0.02])), {"A": 1.0}, window=2)
    with pytest.raises(ValueError, match="at least one"):
        rolling_backtest(_single_asset(np.zeros(10)), {"A": 1.0}, window=2, methods=())
    with pytest.raises(ValueError, match="integer"):
        rolling_backtest(_single_asset(np.zeros(10)), {"A": 1.0}, window=True)


def test_summarize_backtest_rejects_invalid_inputs():
    with pytest.raises(ValueError, match="empty"):
        summarize_backtest(pd.DataFrame())
    frame = pd.DataFrame(
        {"var_historical": [0.01], "violation_historical": [False]},
        index=pd.date_range("2024-01-02", periods=1),
    )
    with pytest.raises(ValueError, match="between 0 and 1"):
        summarize_backtest(frame, level=0.0)
    with pytest.raises(ValueError, match="missing column"):
        summarize_backtest(frame.drop(columns=["violation_historical"]))
    no_methods = pd.DataFrame(
        {"return": [0.0]},
        index=pd.date_range("2024-01-02", periods=1),
    )
    with pytest.raises(ValueError, match="no method columns"):
        summarize_backtest(no_methods)


def test_violations_by_year_rejects_invalid_inputs():
    with pytest.raises(ValueError, match="empty"):
        violations_by_year(pd.DataFrame())
    frame = pd.DataFrame(
        {"violation_historical": [True]},
        index=pd.date_range("2024-01-02", periods=1),
    )
    with pytest.raises(ValueError, match="between 0 and 1"):
        violations_by_year(frame, level=0.0)
    no_methods = pd.DataFrame(
        {"return": [0.0]},
        index=pd.date_range("2024-01-02", periods=1),
    )
    with pytest.raises(ValueError, match="no method columns"):
        violations_by_year(no_methods)

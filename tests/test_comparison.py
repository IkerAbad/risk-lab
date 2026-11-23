import numpy as np
import pandas as pd
import pytest

from risk_lab.comparison import (
    MODELS,
    adaptive_window,
    conditional_backtest,
    conditional_summary,
    es_table,
    model_losses,
    pairwise_dm,
    stress_year_table,
    winner_decision,
)


def _returns(periods: int = 700, seed: int = 11) -> pd.Series:
    rng = np.random.default_rng(seed)
    values = rng.normal(0.0004, 0.01, size=periods)
    index = pd.bdate_range("2018-01-02", periods=periods)
    return pd.Series(values, index=index, name="portfolio")


@pytest.fixture(scope="module")
def smoke_backtest() -> pd.DataFrame:
    return conditional_backtest(
        _returns(),
        window=500,
        garch_refit=50,
        n_scenarios=50,
        seed=1,
    )


def test_adaptive_window_switches_in_a_volatility_spike():
    values = np.zeros(500)
    values[-20:] = np.tile([0.05, -0.05], 10)
    assert adaptive_window(values, 500) == 250


def test_adaptive_window_keeps_500_in_a_calm_window():
    values = np.linspace(-0.01, 0.01, 500)
    assert adaptive_window(values, 500) == 500


def test_adaptive_window_handles_zero_long_volatility():
    values = np.zeros(500)
    assert adaptive_window(values, 500, default=500) == 500


def test_adaptive_window_invalid_inputs():
    values = np.zeros(500)
    with pytest.raises(ValueError, match="one-dimensional"):
        adaptive_window(np.ones((2, 2)), 500)
    with pytest.raises(ValueError, match="finite"):
        adaptive_window(np.r_[np.zeros(499), np.nan], 500)
    with pytest.raises(ValueError, match="position"):
        adaptive_window(values, 500.0)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="0 < short"):
        adaptive_window(values, 100)
    with pytest.raises(ValueError, match="threshold"):
        adaptive_window(values, 500, threshold=0.0)
    with pytest.raises(ValueError, match="default"):
        adaptive_window(values, 500, default=750)


def test_conditional_backtest_smoke(smoke_backtest):
    assert len(smoke_backtest) == 200
    assert smoke_backtest.index[0] == _returns().index[500]
    assert smoke_backtest.index.name == "date"
    assert set(smoke_backtest["window"].unique()) <= {250, 500}
    assert smoke_backtest.notna().all().all()
    for model in MODELS:
        assert f"var_{model}" in smoke_backtest.columns
        assert f"cvar_{model}" in smoke_backtest.columns
        assert f"es_sim_{model}" in smoke_backtest.columns
        assert smoke_backtest[f"violation_{model}"].dtype == bool


def test_model_losses_shape(smoke_backtest):
    losses = model_losses(smoke_backtest)
    assert list(losses.columns) == list(MODELS)
    assert losses.shape == (len(smoke_backtest), len(MODELS))
    assert (losses >= 0).all().all()


def test_conditional_summary_shape(smoke_backtest):
    summary = conditional_summary(smoke_backtest)
    assert list(summary.index) == sorted(
        summary.index, key=lambda model: summary.loc[model, "mean_loss"]
    )
    assert set(summary["rank"]) == set(range(1, len(MODELS) + 1))
    assert (summary["violations"] >= 0).all()
    assert (summary["mean_loss"] >= 0).all()


def test_pairwise_dm_holm(smoke_backtest):
    table = pairwise_dm(smoke_backtest)
    assert len(table) == len(MODELS) * (len(MODELS) - 1) // 2
    assert ((table["dm_p_holm"] >= 0) & (table["dm_p_holm"] <= 1)).all()
    assert (table["dm_p_holm"] >= table["dm_p"] - 1e-12).all()


def test_model_losses_rejects_missing_columns(smoke_backtest):
    with pytest.raises(ValueError, match="missing column"):
        model_losses(smoke_backtest.drop(columns=["var_garch"]))


def test_conditional_summary_rejects_missing_violations(smoke_backtest):
    with pytest.raises(ValueError, match="missing column"):
        conditional_summary(smoke_backtest.drop(columns=["violation_garch"]))


def test_winner_decision_clear_and_unclear(smoke_backtest):
    summary = conditional_summary(smoke_backtest)
    pairwise = pairwise_dm(smoke_backtest)
    decision = winner_decision(summary, pairwise)
    assert decision["best"] in MODELS
    assert decision["second"] in MODELS
    assert decision["best"] != decision["second"]
    p_value = decision["dm_p_holm"]
    assert isinstance(p_value, float)
    assert 0.0 <= p_value <= 1.0

    manual_summary = pd.DataFrame(
        {"mean_loss": [0.1, 0.2]},
        index=pd.Index(["hist500", "param500"]),
    )
    manual_pairwise = pd.DataFrame(
        [
            {
                "model_a": "hist500",
                "model_b": "param500",
                "mean_difference": -0.1,
                "dm_stat": -2.0,
                "dm_p": 0.04,
                "dm_p_holm": 0.04,
            }
        ]
    )
    clear = winner_decision(manual_summary, manual_pairwise)
    assert clear["clear_winner"]
    manual_pairwise.loc[0, "dm_p_holm"] = 0.5
    unclear = winner_decision(manual_summary, manual_pairwise)
    assert not unclear["clear_winner"]


def test_stress_year_table(smoke_backtest):
    table = stress_year_table(smoke_backtest, years=(2020,))
    assert len(table) == len(MODELS)
    assert set(table["year"]) == {2020}
    assert (table["rate"] >= 0).all()
    assert (table["mean_loss"] >= 0).all()
    assert stress_year_table(smoke_backtest, years=(1999,)).empty


def test_es_table(smoke_backtest):
    table = es_table(
        smoke_backtest,
        block_length=5,
        n_boot=100,
        seed=1,
    )
    assert list(table.index) == list(MODELS)
    assert set(table["cvar_type"]) == {"parametric", "empirical"}
    assert (table["cvar_ci_low"] <= table["cvar_ci_high"]).all()
    assert (table["es_ci_low"] <= table["es_ci_high"]).all()
    assert (table["mean_cvar"] > 0).all()
    assert (table["mean_es_sim"] > 0).all()


def test_conditional_backtest_rejects_a_zero_volatility_window():
    rng = np.random.default_rng(5)
    values = np.r_[rng.normal(0.0, 0.01, 250), np.zeros(350)]
    returns = pd.Series(
        values,
        index=pd.bdate_range("2018-01-02", periods=600),
    )
    with pytest.raises(ValueError, match="zero volatility"):
        conditional_backtest(
            returns,
            window=250,
            adaptive_short=20,
            adaptive_long=200,
            garch_refit=1_000,
            n_scenarios=10,
            seed=1,
        )


def test_conditional_backtest_does_not_use_future_returns():
    returns = _returns(periods=600, seed=21)
    first = conditional_backtest(
        returns,
        window=500,
        garch_refit=50,
        n_scenarios=20,
        seed=2,
    )
    changed = returns.copy()
    changed.iloc[-1] += 0.20
    second = conditional_backtest(
        changed,
        window=500,
        garch_refit=50,
        n_scenarios=20,
        seed=2,
    )
    pd.testing.assert_frame_equal(first.iloc[:-1], second.iloc[:-1])
    for model in MODELS:
        assert first[f"var_{model}"].iloc[-1] == pytest.approx(second[f"var_{model}"].iloc[-1])


def test_conditional_backtest_validation():
    returns = _returns()
    with pytest.raises(TypeError, match="Series"):
        conditional_backtest(returns.to_frame())
    with pytest.raises(ValueError, match="empty"):
        conditional_backtest(pd.Series(dtype=float))
    with pytest.raises(ValueError, match="DatetimeIndex"):
        conditional_backtest(pd.Series([0.01] * 600))
    with pytest.raises(ValueError, match="missing"):
        missing = returns.to_numpy().copy()
        missing[10] = np.nan
        conditional_backtest(pd.Series(missing, index=returns.index))
    with pytest.raises(ValueError, match="non-finite"):
        infinite = returns.to_numpy().copy()
        infinite[10] = np.inf
        conditional_backtest(pd.Series(infinite, index=returns.index))
    with pytest.raises(ValueError, match="between 0 and 1"):
        conditional_backtest(returns, level=1.0)
    with pytest.raises(ValueError, match="at least 50"):
        conditional_backtest(returns, window=49)
    with pytest.raises(ValueError, match="longer than the window"):
        conditional_backtest(returns.iloc[:500], window=500)
    with pytest.raises(ValueError, match="garch_refit"):
        conditional_backtest(returns, garch_refit=0)
    with pytest.raises(ValueError, match="garch_refit must be an integer"):
        conditional_backtest(returns, garch_refit=1.5)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="ewma_lambda"):
        conditional_backtest(returns, ewma_lambda=1.0)
    with pytest.raises(ValueError, match="adaptive_short"):
        conditional_backtest(returns, adaptive_short=0)
    with pytest.raises(ValueError, match="adaptive_threshold"):
        conditional_backtest(returns, adaptive_threshold=0.0)
    with pytest.raises(ValueError, match="n_scenarios must be an integer"):
        conditional_backtest(returns, n_scenarios=1.5)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="n_scenarios"):
        conditional_backtest(returns, n_scenarios=0)
    with pytest.raises(ValueError, match="initial variance"):
        conditional_backtest(
            pd.Series(np.zeros(600), index=pd.bdate_range("2020-01-02", periods=600))
        )

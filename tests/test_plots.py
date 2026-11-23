import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest

from risk_lab.plots import (
    plot_conditional_var,
    plot_es_ci,
    plot_returns_with_violations,
    plot_rolling_var,
)


def _fake_backtest(n: int = 120) -> pd.DataFrame:
    rng = np.random.default_rng(4)
    returns = rng.normal(0.0, 0.01, size=n)
    index = pd.bdate_range("2024-01-02", periods=n)
    frame = pd.DataFrame(
        {
            "return": returns,
            "loss": -returns,
            "var_historical": np.full(n, 0.015),
            "cvar_historical": np.full(n, 0.020),
            "var_parametric": np.full(n, 0.016),
            "cvar_parametric": np.full(n, 0.021),
            "var_monte_carlo": np.full(n, 0.0145),
            "cvar_monte_carlo": np.full(n, 0.0195),
        },
        index=index,
    )
    for method in ("historical", "parametric", "monte_carlo"):
        frame[f"violation_{method}"] = frame["loss"] > frame[f"var_{method}"]
    return frame


def test_plot_returns_with_violations_writes_file(tmp_path):
    backtest = _fake_backtest()
    path = tmp_path / "fig1.png"
    fig = plot_returns_with_violations(backtest, path=path)
    assert path.exists()
    assert path.stat().st_size > 1_000
    plt.close(fig)


def test_plot_rolling_var_writes_file(tmp_path):
    backtest = _fake_backtest()
    path = tmp_path / "fig2.png"
    fig = plot_rolling_var(backtest, path=path)
    assert path.exists()
    assert path.stat().st_size > 1_000
    plt.close(fig)


def test_plot_rolling_var_skips_missing_methods(tmp_path):
    backtest = _fake_backtest().drop(columns=["var_parametric", "var_monte_carlo"])
    path = tmp_path / "fig2_historical.png"
    fig = plot_rolling_var(backtest, path=path)
    assert path.exists()
    plt.close(fig)


def test_saved_figures_are_valid_pngs(tmp_path):
    backtest = _fake_backtest()
    for name, function in (
        ("fig1.png", plot_returns_with_violations),
        ("fig2.png", plot_rolling_var),
    ):
        path = tmp_path / name
        fig = function(backtest, path=path)
        image = plt.imread(path)
        assert image.ndim == 3
        assert image.shape[0] > 100
        assert image.shape[1] > 100
        plt.close(fig)


def test_plot_returns_rejects_unknown_method():
    backtest = _fake_backtest()
    with pytest.raises(ValueError, match="unknown method"):
        plot_returns_with_violations(backtest, method="bootstrap")


def test_plot_returns_rejects_missing_columns():
    backtest = _fake_backtest().drop(columns=["var_historical"])
    with pytest.raises(ValueError, match="missing"):
        plot_returns_with_violations(backtest)


def test_plot_rejects_empty_backtest():
    with pytest.raises(ValueError, match="empty"):
        plot_returns_with_violations(pd.DataFrame())
    with pytest.raises(ValueError, match="empty"):
        plot_rolling_var(pd.DataFrame())


def test_plot_rejects_non_dataframe():
    with pytest.raises(TypeError, match="DataFrame"):
        plot_rolling_var("not a frame")


def test_plot_rejects_non_datetime_index():
    backtest = _fake_backtest().reset_index(drop=True)
    with pytest.raises(ValueError, match="DatetimeIndex"):
        plot_rolling_var(backtest)


def test_plot_rejects_missing_return_column():
    backtest = _fake_backtest().drop(columns=["return"])
    with pytest.raises(ValueError, match="return column"):
        plot_rolling_var(backtest)


def test_plot_rejects_invalid_level():
    backtest = _fake_backtest()
    with pytest.raises(ValueError, match="between 0 and 1"):
        plot_rolling_var(backtest, level=0.0)


def _fake_conditional_backtest(n: int = 120) -> pd.DataFrame:
    frame = _fake_backtest(n)
    for model in ("hist500", "param500", "ewma", "garch", "hist_adaptive"):
        frame[f"var_{model}"] = 0.015 + 0.001 * np.arange(n) / n
    return frame


def _fake_es_table() -> pd.DataFrame:
    models = (
        "hist500",
        "param500",
        "ewma",
        "garch",
        "hist_adaptive",
        "param_adaptive",
    )
    return pd.DataFrame(
        {
            "mean_es_sim": [0.020, 0.021, 0.019, 0.018, 0.022, 0.020],
            "es_ci_low": [0.019, 0.020, 0.018, 0.017, 0.021, 0.019],
            "es_ci_high": [0.021, 0.022, 0.020, 0.019, 0.023, 0.021],
            "mean_cvar": [0.018, 0.019, 0.017, 0.016, 0.020, 0.018],
            "cvar_type": [
                "empirical",
                "parametric",
                "parametric",
                "parametric",
                "empirical",
                "parametric",
            ],
        },
        index=models,
    )


def test_plot_conditional_var_writes_a_valid_png(tmp_path):
    backtest = _fake_conditional_backtest()
    path = tmp_path / "fig3.png"
    fig = plot_conditional_var(backtest, path=path)
    image = plt.imread(path)
    assert image.ndim == 3
    assert image.shape[0] > 100
    plt.close(fig)


def test_plot_conditional_var_rejects_missing_columns():
    backtest = _fake_conditional_backtest().drop(columns=["var_garch"])
    with pytest.raises(ValueError, match="missing"):
        plot_conditional_var(backtest)


def test_plot_es_ci_writes_a_valid_png(tmp_path):
    path = tmp_path / "fig4.png"
    fig = plot_es_ci(_fake_es_table(), path=path)
    image = plt.imread(path)
    assert image.ndim == 3
    assert image.shape[0] > 100
    plt.close(fig)


def test_plot_es_ci_validation():
    with pytest.raises(TypeError, match="DataFrame"):
        plot_es_ci("not a frame")
    with pytest.raises(ValueError, match="empty"):
        plot_es_ci(pd.DataFrame())
    with pytest.raises(ValueError, match="missing"):
        plot_es_ci(_fake_es_table().drop(columns=["mean_cvar"]))
    invalid = _fake_es_table()
    invalid.loc["hist500", "mean_es_sim"] = np.nan
    with pytest.raises(ValueError, match="non-finite"):
        plot_es_ci(invalid)
    invalid = _fake_es_table()
    invalid.loc["hist500", "es_ci_low"] = 0.03
    with pytest.raises(ValueError, match="does not contain"):
        plot_es_ci(invalid)
    with pytest.raises(ValueError, match="between 0 and 1"):
        plot_es_ci(_fake_es_table(), level=1.0)

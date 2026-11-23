import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest

from risk_lab.plots import plot_returns_with_violations, plot_rolling_var


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

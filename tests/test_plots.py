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


def test_plot_returns_rejects_unknown_method():
    backtest = _fake_backtest()
    with pytest.raises(ValueError, match="unknown method"):
        plot_returns_with_violations(backtest, method="bootstrap")


def test_plot_returns_rejects_missing_columns():
    backtest = _fake_backtest().drop(columns=["var_historical"])
    with pytest.raises(ValueError, match="missing"):
        plot_returns_with_violations(backtest)

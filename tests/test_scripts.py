import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def _load_script(name: str):
    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


make_figures = _load_script("make_figures")
make_extended = _load_script("make_extended_analysis")


def _write_prices(path: Path) -> None:
    rng = np.random.default_rng(1)
    dates = pd.bdate_range("2024-01-02", periods=120)
    values = 100.0 * np.cumprod(
        1.0 + rng.normal(0.0005, 0.01, size=(120, 3)), axis=0
    )
    frame = pd.DataFrame(values, index=dates, columns=["SPY", "TLT", "GLD"])
    frame.index.name = "Date"
    frame.to_csv(path, float_format="%.6f")


def test_make_figures_end_to_end(tmp_path):
    data = tmp_path / "prices.csv"
    docs = tmp_path / "docs"
    _write_prices(data)

    code = make_figures.main(
        [
            "--data",
            str(data),
            "--docs",
            str(docs),
            "--window",
            "20",
            "--scenarios",
            "100",
            "--seed",
            "1",
        ]
    )

    assert code == 0
    assert (docs / "fig1_returns_violations.png").exists()
    assert (docs / "fig2_rolling_var.png").exists()
    assert (docs / "full_sample_risk.csv").exists()
    assert (docs / "backtest_summary.csv").exists()
    assert (docs / "backtest_series.csv").exists()
    summary = pd.read_csv(docs / "backtest_summary.csv")
    assert "conditional_p" in summary.columns
    assert len(summary) == 3


def test_make_figures_reports_a_clean_error(tmp_path, capsys):
    code = make_figures.main(
        [
            "--data",
            str(tmp_path / "missing.csv"),
            "--docs",
            str(tmp_path / "docs"),
        ]
    )
    assert code == 1
    assert "error:" in capsys.readouterr().err


def test_extended_analysis_end_to_end(tmp_path):
    data = tmp_path / "prices.csv"
    docs = tmp_path / "docs"
    _write_prices(data)

    code = make_extended.main(
        [
            "--data",
            str(data),
            "--docs",
            str(docs),
            "--scenarios",
            "100",
            "--seed",
            "1",
            "--levels",
            "0.95",
            "--windows",
            "20",
        ]
    )

    assert code == 0
    sensitivity = pd.read_csv(docs / "sensitivity.csv")
    assert len(sensitivity) == 3
    assert "conditional_p" in sensitivity.columns
    assert not (docs / "violations_by_year.csv").exists()


def test_extended_analysis_reports_a_clean_error(tmp_path, capsys):
    code = make_extended.main(
        [
            "--data",
            str(tmp_path / "missing.csv"),
            "--docs",
            str(tmp_path / "docs"),
        ]
    )
    assert code == 1
    assert "error:" in capsys.readouterr().err

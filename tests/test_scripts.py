import argparse
import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load_script(name: str):
    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


make_figures = _load_script("make_figures")
make_extended = _load_script("make_extended_analysis")
check_all = _load_script("check_all")
data_quality = _load_script("data_quality")


def _write_prices(path: Path) -> None:
    rng = np.random.default_rng(1)
    dates = pd.bdate_range("2024-01-02", periods=120)
    values = 100.0 * np.cumprod(1.0 + rng.normal(0.0005, 0.01, size=(120, 3)), axis=0)
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


def test_make_figures_parse_args_defaults():
    args = make_figures.parse_args([])
    assert args.window == 500
    assert args.level == 0.95
    assert args.scenarios == 100_000
    assert args.seed == 42


def test_extended_analysis_parse_args_defaults():
    args = make_extended.parse_args([])
    assert args.levels == [0.95, 0.99]
    assert args.windows == [250, 500, 750]
    assert args.scenarios == 100_000


def test_extended_analysis_rejects_invalid_levels():
    with pytest.raises(argparse.ArgumentTypeError):
        make_extended._levels("0.95,1.5")


def test_extended_analysis_rejects_invalid_windows():
    with pytest.raises(argparse.ArgumentTypeError):
        make_extended._windows("0,500")


def test_make_figures_reports_an_invalid_window(tmp_path, capsys):
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
            "0",
        ]
    )
    assert code == 1
    assert "error:" in capsys.readouterr().err


def test_check_all_verifies_the_committed_checksum(capsys):
    assert check_all.verify_checksum() is True
    assert "checksum: OK" in capsys.readouterr().out


def test_data_quality_end_to_end(tmp_path):
    data = tmp_path / "prices.csv"
    docs = tmp_path / "docs"
    _write_prices(data)

    code = data_quality.main(["--data", str(data), "--docs", str(docs)])

    assert code == 0
    report = (docs / "data_quality.md").read_text(encoding="utf-8")
    assert "# Data quality" in report
    assert "SPY" in report
    assert "Observations by year" in report


def test_data_quality_reports_a_clean_error(tmp_path, capsys):
    code = data_quality.main(
        [
            "--data",
            str(tmp_path / "missing.csv"),
            "--docs",
            str(tmp_path / "docs"),
        ]
    )
    assert code == 1
    assert "error:" in capsys.readouterr().err


def test_build_data_quality_report_contains_the_metrics():
    index = pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-04"])
    prices = pd.DataFrame({"A": [100.0, 110.0, 99.0]}, index=index)
    returns = prices.pct_change(fill_method=None).dropna()
    report = data_quality.build_report(prices, returns)
    assert "| Rows | 3 |" in report
    assert "| A | 100.00 | 99.00 | 99.00 | 110.00 |" in report
    assert "| 2024 | 3 |" in report

import hashlib
import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def _load_script(name: str):
    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


make_conditional = _load_script("make_conditional_analysis")
make_fresh = _load_script("make_fresh_analysis")


def _prices(periods: int, seed: int = 11) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2021-01-04", periods=periods)
    values = 100.0 * np.cumprod(1.0 + rng.normal(0.0004, 0.008, size=(periods, 3)), axis=0)
    frame = pd.DataFrame(values, index=dates, columns=["SPY", "TLT", "GLD"])
    frame.index.name = "Date"
    return frame


def _write(frame: pd.DataFrame, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, float_format="%.8f", lineterminator="\n")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    checksum = path.with_suffix(".sha256")
    checksum.write_text(f"{digest}  {path.name}\n", encoding="utf-8", newline="\n")
    return checksum


def test_fresh_analysis_end_to_end(tmp_path):
    canonical = _prices(650)
    fresh = _prices(700)
    canonical_path = tmp_path / "prices.csv"
    fresh_path = tmp_path / "fresh" / f"prices_{fresh.index[-1].date()}.csv"
    checksum = _write(canonical, canonical_path)
    _write(fresh, fresh_path)
    docs = tmp_path / "docs"

    assert (
        make_conditional.main(
            [
                "--data",
                str(canonical_path),
                "--docs",
                str(docs),
                "--scenarios",
                "20",
                "--n-boot",
                "20",
                "--garch-refit",
                "100",
                "--seed",
                "1",
            ]
        )
        == 0
    )
    before = canonical_path.read_bytes()

    code = make_fresh.main(
        [
            "--fresh",
            str(fresh_path),
            "--canonical",
            str(canonical_path),
            "--checksum",
            str(checksum),
            "--docs",
            str(docs),
            "--out",
            str(tmp_path / "fresh_docs"),
            "--levels",
            "0.95",
            "--scenarios",
            "20",
            "--main-scenarios",
            "1000",
            "--n-boot",
            "20",
            "--garch-refit",
            "100",
            "--seed",
            "1",
        ]
    )

    assert code == 0
    assert canonical_path.read_bytes() == before
    output = tmp_path / "fresh_docs"
    for name in (
        "conditional_summary_fresh.csv",
        "conditional_summary_common.csv",
        "conditional_dm_fresh.csv",
        "conditional_dm_common.csv",
        "comparison_fresh_95.csv",
        "comparison_common_95.csv",
        "winners.csv",
        "garch_diagnostics.csv",
        "garch_diagnostics_summary.csv",
        "main_comparison.csv",
        "tables.md",
    ):
        assert (output / name).exists(), name

    winners = pd.read_csv(output / "winners.csv")
    assert set(winners["dataset"]) == {"snapshot", "fresh_full", "fresh_common"}
    comparison = pd.read_csv(output / "comparison_fresh_95.csv")
    assert len(comparison) == 6
    assert (comparison["delta_mean_loss_bp"].abs() < 100).all()
    report = (output / "tables.md").read_text(encoding="utf-8")
    assert "Data differences" in report
    assert "Winner rule" in report

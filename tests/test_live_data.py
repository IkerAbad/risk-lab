import hashlib
import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from risk_lab.data import load_prices

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


fetch_live = _load_script("fetch_live_data")


def _prices(periods: int = 700, start: str = "2021-01-04", seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range(start, periods=periods)
    values = 100.0 * np.cumprod(1.0 + rng.normal(0.0004, 0.008, size=(periods, 3)), axis=0)
    frame = pd.DataFrame(values, index=dates, columns=["SPY", "TLT", "GLD"])
    frame.index.name = "Date"
    return frame


def _write_canonical(path: Path, frame: pd.DataFrame) -> Path:
    frame.to_csv(path, float_format="%.8f", lineterminator="\n")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    checksum = path.with_suffix(".sha256")
    checksum.write_text(f"{digest}  {path.name}\n", encoding="utf-8", newline="\n")
    return checksum


def test_committed_fresh_snapshots_match_their_checksums():
    for path in sorted((ROOT / "data" / "fresh").glob("prices_*.csv")):
        checksum = path.with_suffix(".sha256")
        assert checksum.exists(), path
        assert fetch_live.sha256_file(path) == fetch_live.read_expected_hash(checksum)


def test_versioned_snapshot_is_byte_identical_after_the_update(tmp_path, monkeypatch):
    canonical = ROOT / "data" / "prices.csv"
    before = canonical.read_bytes()
    fresh = load_prices(canonical).copy()
    fresh.iloc[-1] = fresh.iloc[-1] * 1.0001
    monkeypatch.setattr(fetch_live, "_build_frame", lambda *args: (fresh, "test"))

    code = fetch_live.main(["--out-dir", str(tmp_path)])

    assert code == 0
    assert canonical.read_bytes() == before
    assert fetch_live.sha256_file(canonical) == fetch_live.read_expected_hash(
        ROOT / "data" / "prices.sha256"
    )


def test_fetch_live_data_writes_a_valid_dated_snapshot(tmp_path, monkeypatch):
    canonical = _prices(650)
    canonical_path = tmp_path / "prices.csv"
    checksum = _write_canonical(canonical_path, canonical)
    fresh = _prices(700)
    monkeypatch.setattr(fetch_live, "_build_frame", lambda *args: (fresh, "test"))

    code = fetch_live.main(
        [
            "--canonical",
            str(canonical_path),
            "--checksum",
            str(checksum),
            "--out-dir",
            str(tmp_path / "fresh"),
            "--end",
            str(fresh.index[-1].date()),
        ]
    )

    assert code == 0
    destination = tmp_path / "fresh" / f"prices_{fresh.index[-1].date()}.csv"
    assert destination.exists()
    loaded = load_prices(destination)
    assert len(loaded) == 700
    assert list(loaded.columns) == ["SPY", "TLT", "GLD"]
    digest = hashlib.sha256(destination.read_bytes()).hexdigest()
    assert destination.with_suffix(".sha256").read_text(encoding="utf-8") == (
        f"{digest}  {destination.name}\n"
    )


def test_fetch_live_data_rejects_a_corrupted_canonical_checksum(tmp_path, monkeypatch):
    canonical_path = tmp_path / "prices.csv"
    _write_canonical(canonical_path, _prices(650))
    bad_checksum = tmp_path / "bad.sha256"
    bad_checksum.write_text("0" * 64 + "  prices.csv\n", encoding="utf-8")
    monkeypatch.setattr(fetch_live, "_build_frame", lambda *args: (_prices(700), "test"))

    code = fetch_live.main(
        [
            "--canonical",
            str(canonical_path),
            "--checksum",
            str(bad_checksum),
            "--out-dir",
            str(tmp_path / "fresh"),
        ]
    )

    assert code == 1


def test_fetch_live_data_rejects_stale_data(tmp_path, monkeypatch, capsys):
    canonical = _prices(700)
    canonical_path = tmp_path / "prices.csv"
    checksum = _write_canonical(canonical_path, canonical)
    stale = canonical.iloc[:-10].copy()
    monkeypatch.setattr(fetch_live, "_build_frame", lambda *args: (stale, "test"))

    code = fetch_live.main(
        [
            "--canonical",
            str(canonical_path),
            "--checksum",
            str(checksum),
            "--out-dir",
            str(tmp_path / "fresh"),
        ]
    )

    assert code == 1
    assert "before the canonical end" in capsys.readouterr().err


def test_fetch_live_data_refuses_to_replace_changed_content(tmp_path, monkeypatch, capsys):
    canonical = _prices(650)
    canonical_path = tmp_path / "prices.csv"
    checksum = _write_canonical(canonical_path, canonical)
    fresh = _prices(700)
    monkeypatch.setattr(fetch_live, "_build_frame", lambda *args: (fresh, "test"))
    arguments = [
        "--canonical",
        str(canonical_path),
        "--checksum",
        str(checksum),
        "--out-dir",
        str(tmp_path / "fresh"),
    ]
    assert fetch_live.main(arguments) == 0

    changed = fresh.copy()
    changed.iloc[-1] = changed.iloc[-1] * 1.01
    monkeypatch.setattr(fetch_live, "_build_frame", lambda *args: (changed, "test"))
    assert fetch_live.main(arguments) == 1
    assert "use --force" in capsys.readouterr().err

    assert fetch_live.main([*arguments, "--force"]) == 0
    destination = tmp_path / "fresh" / f"prices_{fresh.index[-1].date()}.csv"
    assert load_prices(destination).iloc[-1].tolist() == pytest.approx(changed.iloc[-1].tolist())


def test_fetch_live_data_rejects_a_wrong_schema(tmp_path, monkeypatch, capsys):
    canonical = _prices(650)
    canonical_path = tmp_path / "prices.csv"
    checksum = _write_canonical(canonical_path, canonical)
    fresh = _prices(700).drop(columns=["TLT"])
    monkeypatch.setattr(fetch_live, "_build_frame", lambda *args: (fresh, "test"))

    code = fetch_live.main(
        [
            "--canonical",
            str(canonical_path),
            "--checksum",
            str(checksum),
            "--out-dir",
            str(tmp_path / "fresh"),
        ]
    )

    assert code == 1
    assert "columns" in capsys.readouterr().err

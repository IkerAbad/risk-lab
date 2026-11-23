import hashlib
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from risk_lab.data import (
    DEFAULT_TICKERS,
    DEFAULT_WEIGHTS,
    compute_returns,
    load_prices,
    portfolio_returns,
    weights_vector,
)

ROOT = Path(__file__).resolve().parents[1]


def test_default_weights_sum_to_one():
    assert set(DEFAULT_WEIGHTS) == set(DEFAULT_TICKERS)
    assert sum(DEFAULT_WEIGHTS.values()) == pytest.approx(1.0)


def test_compute_returns_matches_manual_values():
    prices = pd.DataFrame(
        {"A": [100.0, 110.0, 99.0]},
        index=pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-04"]),
    )
    returns = compute_returns(prices)
    assert list(returns.index) == list(prices.index[1:])
    assert returns["A"].to_numpy() == pytest.approx([0.10, -0.10])


def test_compute_log_returns_matches_manual_values():
    prices = pd.DataFrame(
        {"A": [100.0, 110.0]},
        index=pd.to_datetime(["2024-01-02", "2024-01-03"]),
    )
    returns = compute_returns(prices, log_returns=True)
    assert returns["A"].iloc[0] == pytest.approx(np.log(1.10))


def test_portfolio_returns_are_weighted_sum():
    returns = pd.DataFrame(
        {"SPY": [0.01, -0.02], "TLT": [0.00, 0.01], "GLD": [0.02, 0.03]},
        index=pd.to_datetime(["2024-01-03", "2024-01-04"]),
    )
    weights = {"SPY": 0.5, "TLT": 0.3, "GLD": 0.2}
    portfolio = portfolio_returns(returns, weights)
    expected = np.array([0.009, -0.001])
    assert portfolio.to_numpy() == pytest.approx(expected)


def test_load_prices_roundtrip(tmp_path):
    path = tmp_path / "prices.csv"
    path.write_text(
        "Date,SPY,TLT\n2024-01-04,102.0,90.0\n2024-01-02,100.0,91.0\n",
        encoding="utf-8",
    )
    prices = load_prices(path)
    assert list(prices.columns) == ["SPY", "TLT"]
    assert list(prices.index) == list(pd.to_datetime(["2024-01-02", "2024-01-04"]))
    assert prices.loc["2024-01-02", "SPY"] == 100.0


def test_load_prices_rejects_missing_values(tmp_path):
    path = tmp_path / "prices.csv"
    path.write_text(
        "Date,SPY,TLT\n2024-01-02,100.0,\n2024-01-03,101.0,90.0\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="missing"):
        load_prices(path)


def test_load_prices_rejects_non_positive_prices(tmp_path):
    path = tmp_path / "prices.csv"
    path.write_text(
        "Date,SPY,TLT\n2024-01-02,0.0,90.0\n2024-01-03,101.0,91.0\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="positive"):
        load_prices(path)


def test_load_prices_rejects_duplicate_dates(tmp_path):
    path = tmp_path / "prices.csv"
    path.write_text(
        "Date,SPY,TLT\n2024-01-02,100.0,90.0\n2024-01-02,101.0,91.0\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="duplicate"):
        load_prices(path)


def test_weights_vector_rejects_bad_input():
    with pytest.raises(ValueError, match="sum to 1"):
        weights_vector(["A", "B"], {"A": 0.6, "B": 0.5})
    with pytest.raises(ValueError, match="missing"):
        weights_vector(["A", "B"], {"A": 1.0})
    with pytest.raises(ValueError, match="non-negative"):
        weights_vector(["A", "B"], {"A": 1.5, "B": -0.5})


def test_portfolio_returns_keeps_index():
    returns = pd.DataFrame(
        {"A": [0.01, 0.02]},
        index=pd.to_datetime(["2024-01-03", "2024-01-04"]),
    )
    portfolio = portfolio_returns(returns, {"A": 1.0})
    assert portfolio.name == "portfolio"
    assert portfolio.index.equals(returns.index)
    assert portfolio.to_numpy() == pytest.approx(returns["A"].to_numpy())


def test_committed_price_snapshot_is_intact():
    data_path = ROOT / "data" / "prices.csv"
    checksum_path = ROOT / "data" / "prices.sha256"
    expected = checksum_path.read_text(encoding="utf-8").split()[0]
    actual = hashlib.sha256(data_path.read_bytes()).hexdigest()
    assert actual == expected

    prices = load_prices(data_path)
    assert list(prices.columns) == ["SPY", "TLT", "GLD"]
    assert len(prices) == 2_513
    assert prices.index.min() == pd.Timestamp("2016-11-22")
    assert prices.index.max() == pd.Timestamp("2026-11-20")


def test_checksum_is_documented_in_the_repository():
    checksum = (ROOT / "data" / "prices.sha256").read_text(encoding="utf-8").split()[0]
    assert checksum in (ROOT / "README.md").read_text(encoding="utf-8")
    assert checksum in (ROOT / "docs" / "methodology.md").read_text(encoding="utf-8")


def test_load_prices_rejects_empty_file(tmp_path):
    path = tmp_path / "prices.csv"
    path.write_text("Date,SPY\n", encoding="utf-8")
    with pytest.raises(ValueError, match="empty"):
        load_prices(path)


def test_load_prices_rejects_infinite_values(tmp_path):
    path = tmp_path / "prices.csv"
    path.write_text(
        "Date,SPY\n2024-01-02,inf\n2024-01-03,100.0\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="non-finite"):
        load_prices(path)


def test_compute_returns_rejects_empty_prices():
    with pytest.raises(ValueError, match="prices are empty"):
        compute_returns(pd.DataFrame())


def test_weights_vector_rejects_non_finite_weights():
    with pytest.raises(ValueError, match="finite"):
        weights_vector(["A", "B"], {"A": float("nan"), "B": 1.0})


def test_portfolio_returns_rejects_empty_returns():
    with pytest.raises(ValueError, match="returns are empty"):
        portfolio_returns(pd.DataFrame(), {"A": 1.0})

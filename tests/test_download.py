import importlib.util
import json
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "download_data.py"
spec = importlib.util.spec_from_file_location("download_data", SCRIPT)
assert spec is not None
download_data = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(download_data)


STOOQ_CSV = (
    b"Date,Open,High,Low,Close,Volume\n"
    b"2024-01-02,100,101,99,100,10\n"
    b"2024-01-03,101,102,100,101,11\n"
)


def _yahoo_payload(
    *,
    include_adjusted: bool = True,
    include_timestamp: bool = True,
    error: dict | None = None,
    result: bool = True,
) -> dict:
    if error is not None:
        return {"chart": {"error": error}}
    if not result:
        return {"chart": {"result": []}}
    item: dict = {
        "indicators": {
            "adjclose": [{"adjclose": [100.0, 101.0]}],
            "quote": [{"close": [99.0, 100.0]}],
        }
    }
    if include_timestamp:
        item["timestamp"] = [1_704_153_600, 1_704_240_000]
    if not include_adjusted:
        item["indicators"].pop("adjclose")
    return {"chart": {"result": [item]}}


def _fake_yahoo(ticker: str, start: date, end: date) -> pd.Series:
    index = pd.to_datetime(["2024-01-02", "2024-01-03"])
    return pd.Series([100.0, 101.0], index=index, name=ticker)


def _fail_stooq(*args, **kwargs) -> pd.Series:
    raise download_data.DownloadError("blocked")


def _install_payload(monkeypatch, payload: dict) -> None:
    raw = json.dumps(payload).encode("utf-8")
    monkeypatch.setattr(download_data, "_request_with_retry", lambda *args, **kwargs: raw)


def test_fetch_stooq_parses_close(monkeypatch):
    monkeypatch.setattr(download_data, "_request_with_retry", lambda *args, **kwargs: STOOQ_CSV)
    series = download_data.fetch_stooq("SPY", date(2024, 1, 2), date(2024, 1, 3))
    assert series.name == "SPY"
    assert series.tolist() == [100.0, 101.0]


def test_fetch_stooq_rejects_non_csv(monkeypatch):
    monkeypatch.setattr(
        download_data,
        "_request_with_retry",
        lambda *args, **kwargs: b"<html>Access denied</html>",
    )
    with pytest.raises(download_data.DownloadError, match="Stooq returned"):
        download_data.fetch_stooq("SPY", date(2024, 1, 2), date(2024, 1, 3))


def test_fetch_stooq_rejects_missing_close(monkeypatch):
    raw = b"Date,Open\n2024-01-02,100\n"
    monkeypatch.setattr(download_data, "_request_with_retry", lambda *args, **kwargs: raw)
    with pytest.raises(download_data.DownloadError, match="no Close"):
        download_data.fetch_stooq("SPY", date(2024, 1, 2), date(2024, 1, 3))


def test_fetch_stooq_rejects_empty_data(monkeypatch):
    raw = b"Date,Close\n"
    monkeypatch.setattr(download_data, "_request_with_retry", lambda *args, **kwargs: raw)
    with pytest.raises(download_data.DownloadError, match="no rows"):
        download_data.fetch_stooq("SPY", date(2024, 1, 2), date(2024, 1, 3))


def test_fetch_yahoo_uses_adjusted_close(monkeypatch):
    _install_payload(monkeypatch, _yahoo_payload())
    series = download_data.fetch_yahoo("SPY", date(2024, 1, 2), date(2024, 1, 3))
    assert series.tolist() == [100.0, 101.0]
    assert series.index.tolist() == [
        pd.Timestamp("2024-01-02"),
        pd.Timestamp("2024-01-03"),
    ]


def test_fetch_yahoo_falls_back_to_close(monkeypatch, capsys):
    _install_payload(monkeypatch, _yahoo_payload(include_adjusted=False))
    series = download_data.fetch_yahoo("SPY", date(2024, 1, 2), date(2024, 1, 3))
    assert series.tolist() == [99.0, 100.0]
    assert "using close" in capsys.readouterr().err


def test_fetch_yahoo_rejects_error(monkeypatch):
    _install_payload(monkeypatch, _yahoo_payload(error={"code": "Not Found"}))
    with pytest.raises(download_data.DownloadError, match="Yahoo error"):
        download_data.fetch_yahoo("SPY", date(2024, 1, 2), date(2024, 1, 3))


def test_fetch_yahoo_rejects_empty_result(monkeypatch):
    _install_payload(monkeypatch, _yahoo_payload(result=False))
    with pytest.raises(download_data.DownloadError, match="no rows"):
        download_data.fetch_yahoo("SPY", date(2024, 1, 2), date(2024, 1, 3))


def test_fetch_yahoo_rejects_missing_timestamp(monkeypatch):
    _install_payload(monkeypatch, _yahoo_payload(include_timestamp=False))
    with pytest.raises(download_data.DownloadError, match="no rows"):
        download_data.fetch_yahoo("SPY", date(2024, 1, 2), date(2024, 1, 3))


def test_fetch_yahoo_rejects_missing_price_data(monkeypatch):
    payload = {"chart": {"result": [{"timestamp": [1_704_153_600], "indicators": {}}]}}
    _install_payload(monkeypatch, payload)
    with pytest.raises(download_data.DownloadError, match="no price data"):
        download_data.fetch_yahoo("SPY", date(2024, 1, 2), date(2024, 1, 3))


def test_fetch_yahoo_rejects_all_missing_values(monkeypatch):
    payload = {
        "chart": {
            "result": [
                {
                    "timestamp": [1_704_153_600],
                    "indicators": {"adjclose": [{"adjclose": [None]}]},
                }
            ]
        }
    }
    _install_payload(monkeypatch, payload)
    with pytest.raises(download_data.DownloadError, match="no valid rows"):
        download_data.fetch_yahoo("SPY", date(2024, 1, 2), date(2024, 1, 3))


def test_build_frame_falls_back_to_yahoo(monkeypatch):
    monkeypatch.setattr(download_data, "fetch_stooq", _fail_stooq)
    monkeypatch.setattr(download_data, "fetch_yahoo", _fake_yahoo)
    frame, source = download_data._build_frame(date(2024, 1, 2), date(2024, 1, 3), "auto")
    assert source == "Yahoo Finance adjusted close"
    assert list(frame.columns) == ["SPY", "TLT", "GLD"]
    assert len(frame) == 2


def test_build_frame_forced_stooq_raises(monkeypatch):
    monkeypatch.setattr(download_data, "fetch_stooq", _fail_stooq)
    with pytest.raises(download_data.DownloadError, match="blocked"):
        download_data._build_frame(date(2024, 1, 2), date(2024, 1, 3), "stooq")


def test_build_frame_rejects_inverted_dates():
    with pytest.raises(ValueError, match="start must not be after end"):
        download_data._build_frame(date(2024, 1, 3), date(2024, 1, 2), "yahoo")


def test_years_before_handles_leap_day():
    assert download_data._years_before(date(2024, 2, 29), 1) == date(2023, 2, 28)


def test_main_writes_a_csv(monkeypatch, tmp_path):
    monkeypatch.setattr(download_data, "fetch_yahoo", _fake_yahoo)
    out = tmp_path / "prices.csv"
    code = download_data.main(
        [
            "--source",
            "yahoo",
            "--start",
            "2024-01-02",
            "--end",
            "2024-01-03",
            "--out",
            str(out),
        ]
    )
    assert code == 0
    frame = pd.read_csv(out, parse_dates=["Date"], index_col="Date")
    assert list(frame.columns) == ["SPY", "TLT", "GLD"]
    assert len(frame) == 2


def test_main_reports_a_clean_error(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(download_data, "fetch_stooq", _fail_stooq)
    code = download_data.main(
        [
            "--source",
            "stooq",
            "--start",
            "2024-01-02",
            "--end",
            "2024-01-03",
            "--out",
            str(tmp_path / "prices.csv"),
        ]
    )
    assert code == 1
    assert "error:" in capsys.readouterr().err


def test_main_reports_a_write_error(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(download_data, "fetch_yahoo", _fake_yahoo)
    code = download_data.main(
        [
            "--source",
            "yahoo",
            "--start",
            "2024-01-02",
            "--end",
            "2024-01-03",
            "--out",
            str(tmp_path),
        ]
    )
    assert code == 1
    assert "error:" in capsys.readouterr().err


def test_main_rejects_inverted_dates(tmp_path):
    with pytest.raises(SystemExit, match="must not be after"):
        download_data.main(
            [
                "--source",
                "yahoo",
                "--start",
                "2024-01-03",
                "--end",
                "2024-01-02",
                "--out",
                str(tmp_path / "prices.csv"),
            ]
        )


def test_parse_args_defaults():
    args = download_data.parse_args([])
    assert args.source == "auto"
    assert args.years == 10
    assert args.out.name == "prices.csv"


def test_parse_args_accepts_a_source():
    args = download_data.parse_args(["--source", "yahoo"])
    assert args.source == "yahoo"

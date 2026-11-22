#!/usr/bin/env python3
"""Download daily adjusted prices for SPY, TLT and GLD.

The script tries Stooq first. If Stooq rejects the request, it falls back to
Yahoo Finance adjusted closes. The committed data/prices.csv is the source of
truth for the offline pipeline. Network access is only needed to refresh it.
"""

from __future__ import annotations

import argparse
import io
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

TICKERS: tuple[str, ...] = ("SPY", "TLT", "GLD")
STOOQ_SYMBOLS: dict[str, str] = {
    "SPY": "spy.us",
    "TLT": "tlt.us",
    "GLD": "gld.us",
}
USER_AGENT = "risk-lab/0.1 (+https://github.com/IkerAbad/risk-lab)"
STOOQ_URL = "https://stooq.com/q/d/l/?s={symbol}&d1={start:%Y%m%d}&d2={end:%Y%m%d}&i=d"
YAHOO_URL = (
    "https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
    "?period1={start}&period2={end}&interval=1d&events=div%2Csplits"
)


class DownloadError(RuntimeError):
    """Raised when a data source cannot provide usable prices."""


def _request(url: str, *, timeout: int = 30) -> bytes:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "*/*"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def _request_with_retry(url: str, *, attempts: int = 2, timeout: int = 30) -> bytes:
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            return _request(url, timeout=timeout)
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_error = exc
            if attempt + 1 < attempts:
                time.sleep(1.5 * (attempt + 1))
    raise DownloadError(f"request failed: {last_error}") from last_error


def fetch_stooq(ticker: str, start: date, end: date) -> pd.Series:
    """Fetch one ticker from Stooq, using its Close column."""
    symbol = STOOQ_SYMBOLS[ticker]
    url = STOOQ_URL.format(symbol=symbol, start=start, end=end)
    raw = _request_with_retry(url)
    text = raw.decode("utf-8-sig", errors="replace")
    if not text.startswith("Date,"):
        first_line = text.splitlines()[0] if text.splitlines() else ""
        raise DownloadError(f"Stooq returned {first_line[:100]!r}")

    frame = pd.read_csv(io.StringIO(text), parse_dates=["Date"], index_col="Date")
    if "Close" not in frame.columns:
        raise DownloadError(f"Stooq response for {ticker} has no Close column")
    series = frame["Close"].astype(float).sort_index()
    series = series[~series.index.duplicated(keep="last")]
    series = series.dropna()
    if series.empty:
        raise DownloadError(f"Stooq returned no rows for {ticker}")
    return series.rename(ticker)


def fetch_yahoo(ticker: str, start: date, end: date) -> pd.Series:
    """Fetch one ticker from Yahoo Finance, using adjusted close."""
    period1 = int(
        datetime.combine(start, datetime.min.time(), tzinfo=timezone.utc).timestamp()
    )
    period2 = int(
        datetime.combine(
            end + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc
        ).timestamp()
    )
    url = YAHOO_URL.format(ticker=ticker, start=period1, end=period2)
    raw = _request_with_retry(url)
    payload = json.loads(raw.decode("utf-8"))

    chart = payload.get("chart", {})
    if chart.get("error"):
        raise DownloadError(f"Yahoo error for {ticker}: {chart['error']}")
    result = (chart.get("result") or [None])[0]
    if not result or "timestamp" not in result:
        raise DownloadError(f"Yahoo returned no rows for {ticker}")

    timestamps = result["timestamp"]
    indicators = result.get("indicators", {})
    adjusted = indicators.get("adjclose", [{}])[0].get("adjclose")
    if adjusted is None:
        print(
            f"warning: Yahoo has no adjusted close for {ticker}, using close",
            file=sys.stderr,
        )
        adjusted = indicators["quote"][0]["close"]

    index = pd.to_datetime(timestamps, unit="s", utc=True).normalize().tz_localize(None)
    series = pd.Series(adjusted, index=index, name=ticker, dtype=float)
    series = series.dropna().sort_index()
    series = series[~series.index.duplicated(keep="last")]
    if series.empty:
        raise DownloadError(f"Yahoo returned no valid rows for {ticker}")
    return series


def _years_before(day: date, years: int) -> date:
    try:
        return day.replace(year=day.year - years)
    except ValueError:
        return day.replace(year=day.year - years, day=28)


def _build_frame(
    start: date,
    end: date,
    source: str,
) -> tuple[pd.DataFrame, str]:
    if start > end:
        raise ValueError("start must not be after end")

    series: dict[str, pd.Series] = {}
    used_source = source

    if source in ("auto", "stooq"):
        try:
            for ticker in TICKERS:
                series[ticker] = fetch_stooq(ticker, start, end)
            used_source = "Stooq"
        except (DownloadError, ValueError, KeyError) as exc:
            if source == "stooq":
                raise
            print(
                f"Stooq unavailable: {exc}. Falling back to Yahoo Finance.",
                file=sys.stderr,
            )
            series = {}
            used_source = "yahoo"

    if not series:
        for ticker in TICKERS:
            series[ticker] = fetch_yahoo(ticker, start, end)
        used_source = "Yahoo Finance adjusted close"

    frame = pd.DataFrame(series).dropna(how="any").sort_index()
    frame = frame.loc[
        (frame.index >= pd.Timestamp(start)) & (frame.index <= pd.Timestamp(end))
    ]
    if len(frame) < 2:
        raise DownloadError("fewer than two complete rows after alignment")
    if frame.isna().any().any():
        raise DownloadError("aligned data contains missing values")
    if (frame.to_numpy(dtype=float) <= 0).any():
        raise DownloadError("aligned data contains non-positive prices")
    frame.index.name = "Date"
    return frame.astype(float), used_source


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "data" / "prices.csv",
        help="output CSV path",
    )
    parser.add_argument(
        "--source",
        choices=("auto", "stooq", "yahoo"),
        default="auto",
        help="data source, auto tries Stooq and falls back to Yahoo Finance",
    )
    parser.add_argument("--start", type=date.fromisoformat, default=None)
    parser.add_argument("--end", type=date.fromisoformat, default=None)
    parser.add_argument("--years", type=int, default=10)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    end = args.end or date.today()
    start = args.start or _years_before(end, args.years)
    if start > end:
        raise SystemExit("--start must not be after --end")

    try:
        frame, used_source = _build_frame(start, end, args.source)
    except (DownloadError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    args.out.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(args.out, float_format="%.8f", lineterminator="\n")

    first = frame.index.min().date()
    last = frame.index.max().date()
    print(f"Wrote {args.out} with {len(frame)} rows")
    print(f"Range: {first} to {last}")
    print(f"Tickers: {', '.join(frame.columns)}")
    print(f"Source: {used_source}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

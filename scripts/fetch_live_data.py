#!/usr/bin/env python3
"""Download a dated price snapshot without touching data/prices.csv.

The committed snapshot is the reference for the offline pipeline. This script
downloads a fresh copy to ``data/fresh``, validates the schema and both
checksums, and refuses to write over the committed CSV.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
for _path in (ROOT / "src", ROOT / "scripts"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from download_data import DownloadError, _build_frame  # noqa: E402

from risk_lab.data import DEFAULT_TICKERS, load_prices  # noqa: E402

DEFAULT_CANONICAL = ROOT / "data" / "prices.csv"
DEFAULT_CHECKSUM = ROOT / "data" / "prices.sha256"
DEFAULT_OUT_DIR = ROOT / "data" / "fresh"
MIN_ROWS = 502


def sha256_file(path: Path) -> str:
    """Return the SHA-256 hex digest of a file."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_expected_hash(path: Path) -> str:
    """Read the first field of a ``sha256  filename`` line."""
    fields = path.read_text(encoding="utf-8").split()
    if not fields:
        raise ValueError(f"{path} is empty")
    return fields[0].lower()


def validate_frame(
    frame: pd.DataFrame,
    *,
    canonical_first: date,
    canonical_last: date,
    columns: tuple[str, ...] = DEFAULT_TICKERS,
    min_rows: int = MIN_ROWS,
) -> None:
    """Validate the schema and the coverage of a downloaded price frame."""
    if not isinstance(frame, pd.DataFrame):
        raise TypeError("prices must be a pandas DataFrame")
    if frame.empty:
        raise ValueError("prices are empty")
    if tuple(frame.columns) != columns:
        raise ValueError(f"price columns must be {columns}, got {tuple(frame.columns)}")
    if not isinstance(frame.index, pd.DatetimeIndex):
        raise ValueError("the price index must be a DatetimeIndex")
    if frame.index.has_duplicates:
        raise ValueError("price data contains duplicate dates")
    if not frame.index.is_monotonic_increasing:
        raise ValueError("price dates must be sorted")

    values = frame.to_numpy(dtype=float)
    if not np.isfinite(values).all():
        raise ValueError("price data contains non-finite values")
    if (values <= 0).any():
        raise ValueError("prices must be strictly positive")
    if len(frame) < min_rows:
        raise ValueError(f"at least {min_rows} rows are required, got {len(frame)}")

    first = frame.index.min().date()
    last = frame.index.max().date()
    if first > canonical_first:
        raise ValueError(
            f"fresh data starts on {first}, after the canonical start {canonical_first}"
        )
    if last < canonical_last:
        raise ValueError(f"fresh data ends on {last}, before the canonical end {canonical_last}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--canonical", type=Path, default=DEFAULT_CANONICAL)
    parser.add_argument("--checksum", type=Path, default=DEFAULT_CHECKSUM)
    parser.add_argument("--source", choices=("auto", "stooq", "yahoo"), default="auto")
    parser.add_argument("--start", type=date.fromisoformat, default=None)
    parser.add_argument("--end", type=date.fromisoformat, default=None)
    parser.add_argument(
        "--force",
        action="store_true",
        help="overwrite a dated fresh file if the content changed",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        return _run(args)
    except (OSError, ValueError, KeyError, DownloadError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


def _run(args: argparse.Namespace) -> int:
    canonical = args.canonical.resolve()
    if not canonical.exists():
        raise ValueError(f"canonical snapshot not found: {canonical}")
    expected = read_expected_hash(args.checksum)
    if sha256_file(canonical) != expected:
        raise ValueError("data/prices.csv does not match data/prices.sha256")

    canonical_prices = load_prices(canonical)
    canonical_first = canonical_prices.index.min().date()
    canonical_last = canonical_prices.index.max().date()

    end = args.end or date.today()
    start = args.start or canonical_first
    if start > end:
        raise ValueError("--start must not be after --end")

    frame, used_source = _build_frame(start, end, args.source)
    frame.index.name = "Date"
    validate_frame(
        frame,
        canonical_first=canonical_first,
        canonical_last=canonical_last,
    )
    frame = frame.astype(float)
    last = frame.index.max().date()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    destination = (args.out_dir / f"prices_{last.isoformat()}.csv").resolve()
    if destination == canonical:
        raise ValueError("refusing to overwrite the versioned snapshot")

    text = frame.to_csv(float_format="%.8f", lineterminator="\n")
    if destination.exists():
        if destination.read_text(encoding="utf-8") == text and not args.force:
            print(f"Fresh snapshot already present and unchanged: {destination}")
        elif not args.force:
            raise ValueError(
                f"{destination} exists with different content; use --force to replace it"
            )
        else:
            destination.write_text(text, encoding="utf-8", newline="\n")
    else:
        destination.write_text(text, encoding="utf-8", newline="\n")

    reloaded = load_prices(destination)
    validate_frame(
        reloaded,
        canonical_first=canonical_first,
        canonical_last=canonical_last,
    )
    digest = sha256_file(destination)
    checksum_path = destination.with_suffix(".sha256")
    checksum_path.write_text(
        f"{digest}  {destination.name}\n",
        encoding="utf-8",
        newline="\n",
    )

    if sha256_file(canonical) != expected:
        raise ValueError("the canonical snapshot changed during the update")

    new_days = len(frame.index.difference(canonical_prices.index))
    print(f"Canonical snapshot: OK ({expected})")
    print(f"Wrote {destination} with {len(frame)} rows")
    print(f"Range: {frame.index.min().date()} to {last}")
    print(f"Rows after the canonical end: {new_days}")
    print(f"Tickers: {', '.join(frame.columns)}")
    print(f"Source: {used_source}")
    print(f"SHA-256: {digest}")
    print(f"Checksum: {checksum_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

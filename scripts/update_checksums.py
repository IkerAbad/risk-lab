#!/usr/bin/env python3
"""Rewrite docs/checksums.sha256 from the committed outputs."""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

OUTPUTS: tuple[str, ...] = (
    "fig1_returns_violations.png",
    "fig2_rolling_var.png",
    "full_sample_risk.csv",
    "backtest_summary.csv",
    "backtest_series.csv",
    "sensitivity.csv",
    "violations_by_year.csv",
    "data_quality.md",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--docs",
        type=Path,
        default=ROOT / "docs",
        help="directory with the generated outputs",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    lines: list[str] = []
    try:
        for name in sorted(OUTPUTS):
            path = args.docs / name
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            lines.append(f"{digest}  {name}")
        destination = args.docs / "checksums.sha256"
        destination.write_text(
            "\n".join(lines) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"Wrote {destination} with {len(lines)} checksums")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

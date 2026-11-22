#!/usr/bin/env python3
"""Run the extended analysis: 95/99% levels, window sensitivity and yearly counts."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from risk_lab.backtest import (
    rolling_backtest,
    summarize_backtest,
    violations_by_year,
)
from risk_lab.data import DEFAULT_WEIGHTS, compute_returns, load_prices


def _levels(value: str) -> list[float]:
    values = [float(item) for item in value.split(",")]
    if not values or any(not 0.0 < item < 1.0 for item in values):
        raise argparse.ArgumentTypeError("levels must be in (0, 1)")
    return values


def _windows(value: str) -> list[int]:
    values = [int(item) for item in value.split(",")]
    if not values or any(item < 2 for item in values):
        raise argparse.ArgumentTypeError("windows must be at least 2")
    return values


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data",
        type=Path,
        default=ROOT / "data" / "prices.csv",
        help="price CSV",
    )
    parser.add_argument(
        "--docs",
        type=Path,
        default=ROOT / "docs",
        help="output directory for the tables",
    )
    parser.add_argument("--scenarios", type=int, default=100_000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--levels", type=_levels, default=[0.95, 0.99])
    parser.add_argument("--windows", type=_windows, default=[250, 500, 750])
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        return _run(args)
    except (OSError, ValueError, KeyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


def _run(args: argparse.Namespace) -> int:
    started = time.perf_counter()

    prices = load_prices(args.data)
    returns = compute_returns(prices)

    rows: list[pd.DataFrame] = []
    fitted: dict[tuple[float, int], pd.DataFrame] = {}
    for level in args.levels:
        for window in args.windows:
            backtest = rolling_backtest(
                returns,
                DEFAULT_WEIGHTS,
                window=window,
                level=level,
                n_scenarios=args.scenarios,
                seed=args.seed,
            )
            fitted[(level, window)] = backtest
            summary = summarize_backtest(backtest, level=level).reset_index()
            summary.insert(0, "window", window)
            summary.insert(0, "level", level)
            rows.append(summary)

    sensitivity = pd.concat(rows, ignore_index=True)
    sensitivity = sensitivity[
        [
            "level",
            "window",
            "method",
            "observations",
            "violations",
            "expected",
            "violation_rate",
            "kupiec_lr",
            "kupiec_p",
            "christoffersen_lr",
            "christoffersen_p",
            "conditional_lr",
            "conditional_p",
        ]
    ]

    args.docs.mkdir(parents=True, exist_ok=True)
    sensitivity.to_csv(
        args.docs / "sensitivity.csv",
        index=False,
        float_format="%.8f",
        lineterminator="\n",
    )

    main_backtest = fitted.get((0.95, 500))
    if main_backtest is not None:
        by_year = violations_by_year(main_backtest, level=0.95).reset_index()
        by_year.to_csv(
            args.docs / "violations_by_year.csv",
            index=False,
            float_format="%.8f",
            lineterminator="\n",
        )

    def formatter(value: float) -> str:
        return f"{value:.6f}"

    print("Window sensitivity")
    print(
        sensitivity[
            [
                "level",
                "window",
                "method",
                "violations",
                "expected",
                "violation_rate",
                "kupiec_p",
                "christoffersen_p",
                "conditional_p",
            ]
        ].to_string(
            index=False,
            formatters={
                "expected": formatter,
                "violation_rate": formatter,
                "kupiec_p": formatter,
                "christoffersen_p": formatter,
                "conditional_p": formatter,
            },
        )
    )
    if main_backtest is not None:
        print()
        print("Violations by calendar year, 95% level and 500-day window")
        print(
            by_year.to_string(
                index=False,
                formatters={
                    "expected": formatter,
                    "rate": formatter,
                },
            )
        )

    print()
    print(f"Wrote tables to {args.docs}")
    print(f"Elapsed: {time.perf_counter() - started:.1f} s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

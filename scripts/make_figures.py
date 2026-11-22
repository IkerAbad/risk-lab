#!/usr/bin/env python3
"""Run the rolling backtest and write the figures and result tables."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from risk_lab.backtest import rolling_backtest, summarize_backtest
from risk_lab.data import (
    DEFAULT_WEIGHTS,
    compute_returns,
    load_prices,
    portfolio_returns,
    weights_vector,
)
from risk_lab.plots import plot_returns_with_violations, plot_rolling_var
from risk_lab.var import historical_risk, monte_carlo_risk, parametric_risk


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
        help="output directory for figures and tables",
    )
    parser.add_argument("--window", type=int, default=500)
    parser.add_argument("--level", type=float, default=0.95)
    parser.add_argument("--scenarios", type=int, default=100_000)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    started = time.perf_counter()

    prices = load_prices(args.data)
    returns = compute_returns(prices)
    weights = DEFAULT_WEIGHTS
    vector = weights_vector(list(returns.columns), weights)
    portfolio = portfolio_returns(returns, weights)

    full_sample_rows = []
    historical = historical_risk(portfolio.to_numpy(), args.level)
    full_sample_rows.append(
        {
            "method": "historical",
            "var": historical.var,
            "cvar": historical.cvar,
        }
    )
    parametric = parametric_risk(portfolio.to_numpy(), args.level)
    full_sample_rows.append(
        {
            "method": "parametric",
            "var": parametric.var,
            "cvar": parametric.cvar,
        }
    )
    full_sample = monte_carlo_risk(
        returns.to_numpy(),
        vector,
        args.level,
        n_scenarios=args.scenarios,
        seed=args.seed,
    )
    full_sample_rows.append(
        {
            "method": "monte_carlo",
            "var": full_sample.var,
            "cvar": full_sample.cvar,
        }
    )
    full_sample_table = pd.DataFrame(full_sample_rows).set_index("method")

    backtest = rolling_backtest(
        returns,
        weights,
        window=args.window,
        level=args.level,
        n_scenarios=args.scenarios,
        seed=args.seed,
    )
    summary = summarize_backtest(backtest, level=args.level)

    args.docs.mkdir(parents=True, exist_ok=True)
    plot_returns_with_violations(
        backtest,
        method="historical",
        level=args.level,
        path=args.docs / "fig1_returns_violations.png",
    )
    plot_rolling_var(
        backtest,
        level=args.level,
        path=args.docs / "fig2_rolling_var.png",
    )
    plt.close("all")

    full_sample_table.to_csv(
        args.docs / "full_sample_risk.csv",
        float_format="%.8f",
        lineterminator="\n",
    )
    summary.to_csv(
        args.docs / "backtest_summary.csv",
        float_format="%.8f",
        lineterminator="\n",
    )
    backtest.to_csv(
        args.docs / "backtest_series.csv",
        float_format="%.8f",
        lineterminator="\n",
    )

    def formatter(value: float) -> str:
        return f"{value:.6f}"

    print(
        f"Full-sample one-day risk at {args.level:.0%} "
        f"({len(portfolio)} returns)"
    )
    print(full_sample_table.to_string(formatters={"var": formatter, "cvar": formatter}))
    print()
    print(
        f"Rolling backtest: window={args.window}, forecasts={len(backtest)}, "
        f"scenarios={args.scenarios}, seed={args.seed}"
    )
    print(
        summary.to_string(
            formatters={
                "expected": formatter,
                "violation_rate": formatter,
                "kupiec_lr": formatter,
                "kupiec_p": formatter,
                "christoffersen_lr": formatter,
                "christoffersen_p": formatter,
                "conditional_lr": formatter,
                "conditional_p": formatter,
            }
        )
    )
    print()
    print(f"Wrote figures and tables to {args.docs}")
    print(f"Elapsed: {time.perf_counter() - started:.1f} s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

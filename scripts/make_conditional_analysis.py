#!/usr/bin/env python3
"""Run the pre-registered conditional-volatility comparison."""

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

from risk_lab.comparison import (
    conditional_backtest,
    conditional_summary,
    es_table,
    pairwise_dm,
    stress_year_table,
    winner_decision,
)
from risk_lab.data import (
    DEFAULT_WEIGHTS,
    compute_returns,
    load_prices,
    portfolio_returns,
)
from risk_lab.plots import plot_conditional_var, plot_es_ci


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
        help="output directory",
    )
    parser.add_argument("--scenarios", type=int, default=10_000)
    parser.add_argument("--n-boot", type=int, default=10_000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--garch-refit", type=int, default=21)
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
    portfolio = portfolio_returns(returns, DEFAULT_WEIGHTS)

    series: dict[float, pd.DataFrame] = {}
    summaries: list[pd.DataFrame] = []
    dms: list[pd.DataFrame] = []
    stress_tables: list[pd.DataFrame] = []
    es_tables: list[pd.DataFrame] = []
    decisions: dict[float, dict[str, object]] = {}
    es_frames: dict[float, pd.DataFrame] = {}

    for level in (0.95, 0.99):
        backtest = conditional_backtest(
            portfolio,
            level=level,
            window=500,
            garch_refit=args.garch_refit,
            n_scenarios=args.scenarios,
            seed=args.seed,
        )
        summary = conditional_summary(backtest, level=level)
        dm = pairwise_dm(backtest, level=level)
        decision = winner_decision(summary, dm)
        stress = stress_year_table(backtest, level=level)
        es = es_table(
            backtest,
            level=level,
            block_length=20,
            n_boot=args.n_boot,
            seed=args.seed,
        )

        series[level] = backtest
        es_frames[level] = es
        decisions[level] = decision

        summary_frame = summary.reset_index()
        summary_frame.insert(0, "level", level)
        summaries.append(summary_frame)

        dm_frame = dm.copy()
        dm_frame.insert(0, "level", level)
        dms.append(dm_frame)

        stress_frame = stress.copy()
        stress_frame.insert(0, "level", level)
        stress_tables.append(stress_frame)

        es_frame = es.reset_index()
        es_frame.insert(0, "level", level)
        es_tables.append(es_frame)

    args.docs.mkdir(parents=True, exist_ok=True)
    pd.concat(summaries, ignore_index=True).to_csv(
        args.docs / "conditional_summary.csv",
        index=False,
        float_format="%.8f",
        lineterminator="\n",
    )
    pd.concat(dms, ignore_index=True).to_csv(
        args.docs / "conditional_dm.csv",
        index=False,
        float_format="%.8f",
        lineterminator="\n",
    )
    pd.concat(stress_tables, ignore_index=True).to_csv(
        args.docs / "conditional_stress.csv",
        index=False,
        float_format="%.8f",
        lineterminator="\n",
    )
    pd.concat(es_tables, ignore_index=True).to_csv(
        args.docs / "conditional_es.csv",
        index=False,
        float_format="%.8f",
        lineterminator="\n",
    )
    series[0.95].to_csv(
        args.docs / "conditional_series_95.csv",
        float_format="%.8f",
        lineterminator="\n",
    )

    plot_conditional_var(
        series[0.95],
        level=0.95,
        path=args.docs / "fig3_conditional_var.png",
    )
    plot_es_ci(
        es_frames[0.95],
        level=0.95,
        path=args.docs / "fig4_es_ci.png",
    )
    plt.close("all")

    def formatter(value: float) -> str:
        return f"{value:.6f}"

    for level in (0.95, 0.99):
        print()
        print(f"Conditional comparison at {level:.0%}")
        print(
            pd.concat(summaries, ignore_index=True)
            .query("level == @level")
            .drop(columns=["level"])
            .set_index("model")
            .to_string(
                formatters={
                    "expected": formatter,
                    "violation_rate": formatter,
                    "kupiec_p": formatter,
                    "christoffersen_p": formatter,
                    "conditional_p": formatter,
                    "mean_loss": formatter,
                    "mean_var": formatter,
                    "mean_cvar": formatter,
                    "mean_es_sim": formatter,
                }
            )
        )
        decision = decisions[level]
        print(f"Winner rule: {decision['decision']} (Holm p = {decision['dm_p_holm']:.6f})")

    print()
    print("Mean ES at 95% with block-bootstrap intervals")
    print(
        es_frames[0.95].to_string(
            formatters={
                "mean_cvar": formatter,
                "cvar_ci_low": formatter,
                "cvar_ci_high": formatter,
                "mean_es_sim": formatter,
                "es_ci_low": formatter,
                "es_ci_high": formatter,
            }
        )
    )
    print()
    print(f"Wrote conditional tables and figures to {args.docs}")
    print(f"Elapsed: {time.perf_counter() - started:.1f} s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Compare the committed snapshot with a dated fresh snapshot.

The canonical outputs stay untouched. Every table is written under
``docs/fresh`` and the latest fresh price file is verified against its own
checksum before the analysis starts.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import cast

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
for _path in (ROOT / "src", ROOT / "scripts"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from fetch_live_data import (  # noqa: E402
    DEFAULT_CANONICAL,
    DEFAULT_CHECKSUM,
    read_expected_hash,
    sha256_file,
    validate_frame,
)

from risk_lab.backtest import rolling_backtest, summarize_backtest  # noqa: E402
from risk_lab.comparison import (  # noqa: E402
    conditional_backtest,
    conditional_summary,
    es_table,
    pairwise_dm,
    winner_decision,
)
from risk_lab.conditional import fit_garch11  # noqa: E402
from risk_lab.data import (  # noqa: E402
    DEFAULT_WEIGHTS,
    compute_returns,
    load_prices,
    portfolio_returns,
)

MODEL_ORDER: tuple[str, ...] = (
    "garch",
    "ewma",
    "hist500",
    "param_adaptive",
    "hist_adaptive",
    "param500",
)
MODEL_LABELS: dict[str, str] = {
    "hist500": "Historical 500",
    "param500": "Parametric 500",
    "ewma": "EWMA",
    "garch": "GARCH(1,1)",
    "hist_adaptive": "Historical adaptive",
    "param_adaptive": "Parametric adaptive",
}
MAIN_LABELS: dict[str, str] = {
    "historical": "Historical",
    "parametric": "Parametric",
    "monte_carlo": "Monte Carlo",
}


@dataclass
class Run:
    name: str
    label: str
    start: date
    end: date
    observations: int
    summary: pd.DataFrame
    dm: pd.DataFrame
    decision: dict[str, object]
    es: pd.DataFrame


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fresh", type=Path, default=None)
    parser.add_argument("--canonical", type=Path, default=DEFAULT_CANONICAL)
    parser.add_argument("--checksum", type=Path, default=DEFAULT_CHECKSUM)
    parser.add_argument("--docs", type=Path, default=ROOT / "docs")
    parser.add_argument("--out", type=Path, default=ROOT / "docs" / "fresh")
    parser.add_argument("--levels", type=float, nargs="+", default=[0.95, 0.99])
    parser.add_argument("--scenarios", type=int, default=10_000)
    parser.add_argument("--main-scenarios", type=int, default=100_000)
    parser.add_argument("--n-boot", type=int, default=10_000)
    parser.add_argument("--garch-refit", type=int, default=21)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args(argv)


def latest_fresh(directory: Path = ROOT / "data" / "fresh") -> Path:
    candidates = sorted(directory.glob("prices_*.csv"))
    if not candidates:
        raise ValueError(f"no fresh price files found in {directory}")
    return candidates[-1]


def verify_snapshot(path: Path, checksum: Path) -> str:
    expected = read_expected_hash(checksum)
    actual = sha256_file(path)
    if actual != expected:
        raise ValueError(f"{path} does not match {checksum}")
    return actual


def run_comparison(
    name: str,
    label: str,
    portfolio: pd.Series,
    *,
    levels: list[float],
    scenarios: int,
    n_boot: int,
    garch_refit: int,
    seed: int,
) -> tuple[dict[float, Run], pd.DataFrame]:
    runs: dict[float, Run] = {}
    frames: list[pd.DataFrame] = []
    for level in levels:
        backtest = conditional_backtest(
            portfolio,
            level=level,
            window=500,
            garch_refit=garch_refit,
            n_scenarios=scenarios,
            seed=seed,
        )
        summary = conditional_summary(backtest, level=level)
        dm = pairwise_dm(backtest, level=level)
        decision = winner_decision(summary, dm)
        es = es_table(
            backtest,
            level=level,
            block_length=20,
            n_boot=n_boot,
            seed=seed,
        )
        frame = summary.reset_index()
        frame.insert(0, "level", level)
        frames.append(frame)
        runs[level] = Run(
            name=name,
            label=label,
            start=backtest.index.min().date(),
            end=backtest.index.max().date(),
            observations=len(backtest),
            summary=summary,
            dm=dm,
            decision=decision,
            es=es,
        )
    return runs, pd.concat(frames, ignore_index=True)


def write_summary_csv(runs: dict[float, Run], path: Path) -> None:
    frames = []
    for level, run in runs.items():
        frame = run.summary.reset_index()
        frame.insert(0, "level", level)
        frames.append(frame)
    pd.concat(frames, ignore_index=True).to_csv(
        path,
        index=False,
        float_format="%.8f",
        lineterminator="\n",
    )


def write_dm_csv(runs: dict[float, Run], path: Path) -> None:
    frames = []
    for level, run in runs.items():
        frame = run.dm.copy()
        frame.insert(0, "level", level)
        frames.append(frame)
    pd.concat(frames, ignore_index=True).to_csv(
        path,
        index=False,
        float_format="%.8f",
        lineterminator="\n",
    )


def comparison_table(
    canonical: pd.DataFrame,
    fresh: pd.DataFrame,
    *,
    level: float,
) -> pd.DataFrame:
    left = canonical[canonical["level"] == level].set_index("model")
    right = fresh[fresh["level"] == level].set_index("model")
    rows = []
    for model in MODEL_ORDER:
        rows.append(
            {
                "model": model,
                "violations_snapshot": int(left.loc[model, "violations"]),
                "violations_fresh": int(right.loc[model, "violations"]),
                "delta_violations": int(right.loc[model, "violations"])
                - int(left.loc[model, "violations"]),
                "mean_loss_snapshot": float(left.loc[model, "mean_loss"]),
                "mean_loss_fresh": float(right.loc[model, "mean_loss"]),
                "delta_mean_loss_bp": (
                    float(right.loc[model, "mean_loss"]) - float(left.loc[model, "mean_loss"])
                )
                * 10_000.0,
                "rank_snapshot": int(left.loc[model, "rank"]),
                "rank_fresh": int(right.loc[model, "rank"]),
                "mean_es_snapshot": float(left.loc[model, "mean_es_sim"]),
                "mean_es_fresh": float(right.loc[model, "mean_es_sim"]),
            }
        )
    return pd.DataFrame(rows)


def winner_table(
    canonical: dict[float, Run],
    fresh: dict[float, Run],
    common: dict[float, Run],
) -> pd.DataFrame:
    rows = []
    for dataset, runs in (
        ("snapshot", canonical),
        ("fresh_full", fresh),
        ("fresh_common", common),
    ):
        for level, run in runs.items():
            decision = run.decision
            rows.append(
                {
                    "dataset": dataset,
                    "level": level,
                    "best": decision["best"],
                    "second": decision["second"],
                    "best_mean_loss": decision["best_mean_loss"],
                    "second_mean_loss": decision["second_mean_loss"],
                    "dm_p_holm": decision["dm_p_holm"],
                    "clear_winner": decision["clear_winner"],
                    "decision": decision["decision"],
                }
            )
    return pd.DataFrame(rows)


def _p(value: float) -> str:
    if value < 1e-4:
        return f"{value:.2e}"
    return f"{value:.4f}"


def _main_table(canonical: pd.DataFrame, fresh: pd.DataFrame) -> str:
    lines = [
        "| Method | Violations snapshot | Violations fresh | Kupiec p snapshot | Kupiec p fresh | Christoffersen p snapshot | Christoffersen p fresh |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for method in ("historical", "parametric", "monte_carlo"):
        left = canonical.loc[method]
        right = fresh.loc[method]
        lines.append(
            f"| {MAIN_LABELS[method]} | {int(left['violations'])} | "
            f"{int(right['violations'])} | {_p(left['kupiec_p'])} | "
            f"{_p(right['kupiec_p'])} | {_p(left['christoffersen_p'])} | "
            f"{_p(right['christoffersen_p'])} |"
        )
    return "\n".join(lines)


def _conditional_table(comparison: pd.DataFrame, level: float) -> str:
    lines = [
        "| Model | Violations snapshot | Violations fresh | Δ violations | Mean loss snapshot (bp) | Mean loss fresh (bp) | Δ mean loss (bp) | Rank snapshot | Rank fresh |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for _, row in comparison.iterrows():
        lines.append(
            f"| {MODEL_LABELS[row['model']]} | {int(row['violations_snapshot'])} | "
            f"{int(row['violations_fresh'])} | {int(row['delta_violations'])} | "
            f"{row['mean_loss_snapshot'] * 10_000:.2f} | "
            f"{row['mean_loss_fresh'] * 10_000:.2f} | "
            f"{row['delta_mean_loss_bp']:+.2f} | "
            f"{int(row['rank_snapshot'])} | {int(row['rank_fresh'])} |"
        )
    return "\n".join(lines)


def _winner_text(winner: pd.DataFrame) -> str:
    lines = [
        "| Dataset | Level | Best | Second | Holm p | Clear winner | Decision |",
        "|---|---:|---|---|---:|---|---|",
    ]
    for _, row in winner.iterrows():
        lines.append(
            f"| {row['dataset']} | {float(row['level']):.0%} | "
            f"{MODEL_LABELS[str(row['best'])]} | {MODEL_LABELS[str(row['second'])]} | "
            f"{float(row['dm_p_holm']):.4f} | {bool(row['clear_winner'])} | "
            f"{row['decision']} |"
        )
    return "\n".join(lines)


def _es_table(run: Run, level: float) -> str:
    lines = [
        "| Model | Mean CVaR | CVaR CI | Mean simulated ES | ES CI |",
        "|---|---:|---|---:|---|",
    ]
    frame = run.es
    for model in MODEL_ORDER:
        row = frame.loc[model]
        lines.append(
            f"| {MODEL_LABELS[model]} | {row['mean_cvar']:.4%} | "
            f"[{row['cvar_ci_low']:.4%}, {row['cvar_ci_high']:.4%}] | "
            f"{row['mean_es_sim']:.4%} | "
            f"[{row['es_ci_low']:.4%}, {row['es_ci_high']:.4%}] |"
        )
    return "\n".join(lines)


def _data_table(
    canonical_prices: pd.DataFrame,
    fresh_prices: pd.DataFrame,
) -> str:
    common = fresh_prices.index.intersection(canonical_prices.index)
    difference = (fresh_prices.loc[common] - canonical_prices.loc[common]).abs()
    relative = (difference / canonical_prices.loc[common]).max() * 100.0
    lines = [
        "| Ticker | Common dates | Max absolute revision | Max relative revision |",
        "|---|---:|---:|---:|",
    ]
    for ticker in canonical_prices.columns:
        lines.append(
            f"| {ticker} | {len(common)} | {difference[ticker].max():.8f} | "
            f"{relative[ticker]:.2e}% |"
        )
    changed = int((difference > 1e-8).to_numpy().sum())
    lines.extend(
        [
            "",
            f"Cells with an absolute revision above 1e-8: {changed} of {difference.size}.",
        ]
    )
    return "\n".join(lines)


def _garch_table(summary: pd.DataFrame) -> str:
    lines = [
        "| Dataset | Refits | Failed fits | alpha < 1e-8 | beta > 0.99 | Max omega / variance |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for _, row in summary.iterrows():
        lines.append(
            f"| {row['dataset']} | {int(row['refits'])} | {int(row['failed'])} | "
            f"{int(row['alpha_below_1e_8'])} | {int(row['beta_above_0_99'])} | "
            f"{float(row['max_omega_over_variance']):.4g} |"
        )
    return "\n".join(lines)


def build_markdown(
    *,
    canonical_prices: pd.DataFrame,
    fresh_prices: pd.DataFrame,
    canonical_main: pd.DataFrame,
    fresh_main: pd.DataFrame,
    comparisons: dict[float, pd.DataFrame],
    common_comparisons: dict[float, pd.DataFrame],
    winners: pd.DataFrame,
    fresh_runs: dict[float, Run],
    garch_summary: pd.DataFrame,
) -> str:
    first = fresh_prices.index.min().date()
    last = fresh_prices.index.max().date()
    parts = [
        "# Fresh-data comparison",
        "",
        f"Canonical snapshot: `data/prices.csv`, {len(canonical_prices)} rows, "
        f"{canonical_prices.index.min().date()} to "
        f"{canonical_prices.index.max().date()}.",
        "",
        f"Fresh snapshot: `{fresh_prices.attrs.get('path', 'data/fresh')}`, "
        f"{len(fresh_prices)} rows, {first} to {last}.",
        "",
        f"New trading days: {len(fresh_prices.index.difference(canonical_prices.index))}. "
        "The common-period tables use only dates available in both snapshots.",
        "",
        "## Data differences",
        "",
        _data_table(canonical_prices, fresh_prices),
        "",
        "## Main backtest at 95%",
        "",
        _main_table(canonical_main, fresh_main),
        "",
        "## GARCH refit diagnostics",
        "",
        _garch_table(garch_summary),
        "",
        "## Winner rule",
        "",
        _winner_text(winners),
        "",
    ]
    for level in sorted(comparisons):
        parts.extend(
            [
                f"## Conditional models at {level:.0%}",
                "",
                _conditional_table(comparisons[level], level),
                "",
                f"### Expected Shortfall at {level:.0%}, fresh data",
                "",
                _es_table(fresh_runs[level], level),
                "",
                f"### Common-period revision check at {level:.0%}",
                "",
                _conditional_table(common_comparisons[level], level),
                "",
            ]
        )
    return "\n".join(parts)


def garch_diagnostics(
    portfolio: pd.Series,
    *,
    window: int = 500,
    refit: int = 21,
) -> pd.DataFrame:
    """Refit GARCH on the same windows as the backtest and record the output."""
    values = portfolio.to_numpy(dtype=float)
    rows = []
    for position in range(window, len(values), refit):
        sample = values[position - window : position]
        parameters = fit_garch11(sample)
        rows.append(
            {
                "position": position,
                "date": portfolio.index[position].date(),
                "converged": parameters.converged,
                "omega": parameters.omega,
                "alpha": parameters.alpha,
                "beta": parameters.beta,
                "sample_variance": float(np.var(sample, ddof=1)),
            }
        )
    return pd.DataFrame(rows)


def garch_diagnostic_summary(frame: pd.DataFrame, dataset: str) -> dict[str, object]:
    variance = frame["sample_variance"].to_numpy(dtype=float)
    omega = frame["omega"].to_numpy(dtype=float)
    return {
        "dataset": dataset,
        "refits": len(frame),
        "failed": int((~frame["converged"]).sum()),
        "alpha_below_1e_8": int((frame["alpha"] < 1e-8).sum()),
        "beta_above_0_99": int((frame["beta"] > 0.99).sum()),
        "max_omega_over_variance": float(np.max(omega / variance)),
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        return _run(args)
    except (OSError, ValueError, KeyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


def _run(args: argparse.Namespace) -> int:
    fresh_path = (args.fresh or latest_fresh()).resolve()
    verify_snapshot(args.canonical.resolve(), args.checksum.resolve())
    fresh_checksum = fresh_path.with_suffix(".sha256")
    if not fresh_checksum.exists():
        raise ValueError(f"fresh checksum not found: {fresh_checksum}")
    verify_snapshot(fresh_path, fresh_checksum)

    canonical_prices = load_prices(args.canonical)
    fresh_prices = load_prices(fresh_path)
    try:
        shown_fresh = fresh_path.relative_to(ROOT).as_posix()
    except ValueError:
        shown_fresh = str(fresh_path)
    fresh_prices.attrs["path"] = shown_fresh
    canonical_last = canonical_prices.index.max().date()
    validate_frame(
        fresh_prices,
        canonical_first=canonical_prices.index.min().date(),
        canonical_last=canonical_last,
    )

    canonical_asset_returns = compute_returns(canonical_prices)
    fresh_asset_returns = compute_returns(fresh_prices)
    common_asset_returns = fresh_asset_returns.loc[: pd.Timestamp(canonical_last)]

    canonical_portfolio = portfolio_returns(canonical_asset_returns, DEFAULT_WEIGHTS)
    fresh_portfolio = portfolio_returns(fresh_asset_returns, DEFAULT_WEIGHTS)
    common_portfolio = portfolio_returns(common_asset_returns, DEFAULT_WEIGHTS)

    fresh_runs, fresh_summary = run_comparison(
        "fresh_full",
        f"Fresh data to {fresh_prices.index.max().date()}",
        fresh_portfolio,
        levels=args.levels,
        scenarios=args.scenarios,
        n_boot=args.n_boot,
        garch_refit=args.garch_refit,
        seed=args.seed,
    )
    common_runs, common_summary = run_comparison(
        "fresh_common",
        f"Fresh data to {canonical_last}",
        common_portfolio,
        levels=args.levels,
        scenarios=args.scenarios,
        n_boot=args.n_boot,
        garch_refit=args.garch_refit,
        seed=args.seed,
    )

    canonical_main = summarize_backtest(
        rolling_backtest(
            canonical_asset_returns,
            DEFAULT_WEIGHTS,
            window=500,
            level=0.95,
            n_scenarios=args.main_scenarios,
            seed=args.seed,
        ),
        level=0.95,
    )
    fresh_main = summarize_backtest(
        rolling_backtest(
            fresh_asset_returns,
            DEFAULT_WEIGHTS,
            window=500,
            level=0.95,
            n_scenarios=args.main_scenarios,
            seed=args.seed,
        ),
        level=0.95,
    )

    diagnostics = {
        "snapshot": garch_diagnostics(canonical_portfolio, refit=args.garch_refit),
        "fresh_full": garch_diagnostics(fresh_portfolio, refit=args.garch_refit),
        "fresh_common": garch_diagnostics(common_portfolio, refit=args.garch_refit),
    }
    diagnostic_frames = []
    for dataset, frame in diagnostics.items():
        frame.insert(0, "dataset", dataset)
        diagnostic_frames.append(frame)
    garch_summary = pd.DataFrame(
        [garch_diagnostic_summary(frame, dataset) for dataset, frame in diagnostics.items()]
    )

    canonical_summary = pd.read_csv(args.docs / "conditional_summary.csv")
    canonical_read: dict[float, Run] = {}
    for level in args.levels:
        subset = canonical_summary[canonical_summary["level"] == level].set_index("model")
        dm = pd.read_csv(
            args.docs / "conditional_dm.csv",
        )
        dm = dm[dm["level"] == level].drop(columns=["level"])
        decision = winner_decision(subset, dm)
        canonical_read[level] = Run(
            name="snapshot",
            label="Canonical snapshot",
            start=canonical_prices.index.min().date(),
            end=canonical_last,
            observations=len(canonical_portfolio),
            summary=subset,
            dm=dm,
            decision=decision,
            es=pd.read_csv(args.docs / "conditional_es.csv")
            .query("level == @level")
            .set_index("model"),
        )

    comparisons = {
        level: comparison_table(canonical_summary, fresh_summary, level=level)
        for level in args.levels
    }
    common_comparisons = {
        level: comparison_table(canonical_summary, common_summary, level=level)
        for level in args.levels
    }
    winners = winner_table(canonical_read, fresh_runs, common_runs)

    args.out.mkdir(parents=True, exist_ok=True)
    write_summary_csv(fresh_runs, args.out / "conditional_summary_fresh.csv")
    write_summary_csv(common_runs, args.out / "conditional_summary_common.csv")
    write_dm_csv(fresh_runs, args.out / "conditional_dm_fresh.csv")
    write_dm_csv(common_runs, args.out / "conditional_dm_common.csv")
    for level, table in comparisons.items():
        table.to_csv(
            args.out / f"comparison_fresh_{int(level * 100)}.csv",
            index=False,
            float_format="%.8f",
            lineterminator="\n",
        )
        common_comparisons[level].to_csv(
            args.out / f"comparison_common_{int(level * 100)}.csv",
            index=False,
            float_format="%.8f",
            lineterminator="\n",
        )
    winners.to_csv(
        args.out / "winners.csv",
        index=False,
        float_format="%.8f",
        lineterminator="\n",
    )
    pd.concat(diagnostic_frames, ignore_index=True).to_csv(
        args.out / "garch_diagnostics.csv",
        index=False,
        float_format="%.8f",
        lineterminator="\n",
    )
    garch_summary.to_csv(
        args.out / "garch_diagnostics_summary.csv",
        index=False,
        float_format="%.8f",
        lineterminator="\n",
    )
    main_comparison = canonical_main.add_suffix("_snapshot").join(fresh_main.add_suffix("_fresh"))
    main_comparison.to_csv(
        args.out / "main_comparison.csv",
        float_format="%.8f",
        lineterminator="\n",
    )
    fresh_main.to_csv(
        args.out / "main_summary_fresh.csv",
        float_format="%.8f",
        lineterminator="\n",
    )

    report = build_markdown(
        canonical_prices=canonical_prices,
        fresh_prices=fresh_prices,
        canonical_main=canonical_main,
        fresh_main=fresh_main,
        comparisons=comparisons,
        common_comparisons=common_comparisons,
        winners=winners,
        fresh_runs=fresh_runs,
        garch_summary=garch_summary,
    )
    (args.out / "tables.md").write_text(report, encoding="utf-8", newline="\n")

    for level in args.levels:
        decision = fresh_runs[level].decision
        p_value = float(cast(float, decision["dm_p_holm"]))
        print(f"{level:.0%}: {decision['decision']} (Holm p = {p_value:.4f})")
    print(f"Fresh rows: {len(fresh_prices)}; canonical rows: {len(canonical_prices)}")
    print(f"Wrote fresh comparison to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

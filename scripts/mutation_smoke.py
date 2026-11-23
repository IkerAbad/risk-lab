#!/usr/bin/env python3
"""Run a small set of mutation checks against the test suite."""

from __future__ import annotations

import os
import shutil
import subprocess  # nosec B404
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "src" / "risk_lab"


@dataclass(frozen=True)
class Mutation:
    """One source change that the tests must detect."""

    name: str
    relative_path: str
    old: str
    new: str
    test: str


MUTATIONS: tuple[Mutation, ...] = (
    Mutation(
        name="historical var sign",
        relative_path="var.py",
        old="return RiskEstimate(var=-quantile, cvar=float(-tail.mean()))",
        new="return RiskEstimate(var=quantile, cvar=float(-tail.mean()))",
        test="tests/test_var.py",
    ),
    Mutation(
        name="historical cvar sign",
        relative_path="var.py",
        old="return RiskEstimate(var=-quantile, cvar=float(-tail.mean()))",
        new="return RiskEstimate(var=-quantile, cvar=float(tail.mean()))",
        test="tests/test_var.py",
    ),
    Mutation(
        name="empirical quantile level",
        relative_path="var.py",
        old='quantile = float(np.quantile(values, 1.0 - level, method="linear"))',
        new='quantile = float(np.quantile(values, level, method="linear"))',
        test="tests/test_var.py",
    ),
    Mutation(
        name="p-value tail",
        relative_path="stats.py",
        old="chi2.sf",
        new="chi2.cdf",
        test="tests/test_stats.py",
    ),
    Mutation(
        name="violation comparison",
        relative_path="backtest.py",
        old='row["violation_historical"] = row["loss"] > estimate.var',
        new='row["violation_historical"] = row["loss"] < estimate.var',
        test="tests/test_backtest.py",
    ),
)


def _run_tests(temp_src: Path, test: str) -> tuple[bool, str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(temp_src)
    probe = subprocess.run(  # nosec B603
        [sys.executable, "-c", "import risk_lab; print(risk_lab.__file__)"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    if probe.returncode != 0 or str(temp_src) not in probe.stdout:
        return False, "the temporary copy was not imported\n" + probe.stderr

    result = subprocess.run(  # nosec B603
        [sys.executable, "-m", "pytest", "-q", test],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
    )
    return result.returncode != 0, result.stdout[-400:]


def main() -> int:
    failures = 0
    for mutation in MUTATIONS:
        with tempfile.TemporaryDirectory() as temporary:
            temp_src = Path(temporary) / "src"
            shutil.copytree(
                PACKAGE,
                temp_src / "risk_lab",
                ignore=shutil.ignore_patterns("__pycache__"),
            )
            target = temp_src / "risk_lab" / mutation.relative_path
            source = target.read_text(encoding="utf-8")
            if mutation.old not in source:
                print(f"{mutation.name}: PATTERN NOT FOUND")
                failures += 1
                continue
            target.write_text(
                source.replace(mutation.old, mutation.new),
                encoding="utf-8",
                newline="\n",
            )
            caught, detail = _run_tests(temp_src, mutation.test)
            print(f"{mutation.name}: {'CAUGHT' if caught else 'SURVIVED'}")
            if not caught:
                print(detail)
                failures += 1

    if failures:
        print(f"{failures} mutation checks failed.", file=sys.stderr)
        return 1
    print("All mutation checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

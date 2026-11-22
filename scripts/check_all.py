#!/usr/bin/env python3
"""Run the local quality gates in one command."""

from __future__ import annotations

import hashlib
import subprocess  # nosec B404
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def verify_checksum() -> bool:
    """Check the committed CSV against data/prices.sha256."""
    checksum_file = ROOT / "data" / "prices.sha256"
    data_file = ROOT / "data" / "prices.csv"
    expected = checksum_file.read_text(encoding="utf-8").split()[0]
    actual = hashlib.sha256(data_file.read_bytes()).hexdigest()
    ok = actual == expected
    print(f"checksum: {'OK' if ok else 'FAILED'}")
    return ok


def run(command: list[str]) -> bool:
    """Run one command from the repository root."""
    print("$ " + " ".join(command))
    # The command is a fixed list built in main, with no shell and no user input.
    return subprocess.run(command, cwd=ROOT).returncode == 0  # nosec B603


def main() -> int:
    commands = [
        [sys.executable, "-m", "ruff", "check", "."],
        [sys.executable, "-m", "mypy", "src"],
        [sys.executable, "-m", "bandit", "-r", "src", "scripts", "-q"],
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "--cov=risk_lab",
            "--cov-report=term-missing",
        ],
    ]
    results = [verify_checksum()]
    for command in commands:
        results.append(run(command))

    if all(results):
        print("All checks passed.")
        return 0
    print("Some checks failed.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

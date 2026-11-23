import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

DOCUMENTS = [
    "README.md",
    "CONTRIBUTING.md",
    "CHANGELOG.md",
    "SECURITY.md",
    "docs/methodology.md",
    "docs/results.md",
    "docs/api.md",
    "docs/architecture.md",
    "docs/decisions.md",
    "docs/data_quality.md",
]

LINK = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def test_relative_markdown_links_exist():
    for document in DOCUMENTS:
        text = (ROOT / document).read_text(encoding="utf-8")
        for target in LINK.findall(text):
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            path_part = target.split("#", 1)[0].split("?", 1)[0]
            if not path_part:
                continue
            resolved = (ROOT / document).parent / path_part
            assert resolved.exists(), f"{document}: missing link target {target}"


def test_readme_main_table_matches_the_summary_csv():
    summary = pd.read_csv(ROOT / "docs" / "backtest_summary.csv", index_col="method")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for method, label in (
        ("historical", "Historical"),
        ("parametric", "Parametric"),
        ("monte_carlo", "Monte Carlo"),
    ):
        violations = int(summary.loc[method, "violations"])
        assert f"| {label} | {violations} |" in readme


def test_results_page_99_percent_table_matches_the_sensitivity_csv():
    sensitivity = pd.read_csv(ROOT / "docs" / "sensitivity.csv")
    results = (ROOT / "docs" / "results.md").read_text(encoding="utf-8")
    subset = sensitivity[(sensitivity["level"] == 0.99) & (sensitivity["window"] == 500)]
    for method, label in (
        ("historical", "Historical"),
        ("parametric", "Parametric"),
        ("monte_carlo", "Monte Carlo"),
    ):
        violations = int(subset.loc[subset["method"] == method, "violations"].iloc[0])
        assert f"| {label} | {violations} |" in results


def test_data_quality_report_matches_the_snapshot():
    report = (ROOT / "docs" / "data_quality.md").read_text(encoding="utf-8")
    assert "| Rows | 2513 |" in report
    assert "| First date | 2016-11-22 |" in report
    assert "| Last date | 2026-11-20 |" in report


def test_architecture_and_decisions_documents_are_complete():
    architecture = (ROOT / "docs" / "architecture.md").read_text(encoding="utf-8")
    for module in ("data", "var", "backtest", "stats", "plots"):
        assert module in architecture
    decisions = (ROOT / "docs" / "decisions.md").read_text(encoding="utf-8")
    for term in ("positive losses", "50/35/15", "500-day", "Yahoo Finance"):
        assert term in decisions

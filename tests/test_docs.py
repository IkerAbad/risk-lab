import hashlib
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
    "docs/results_conditional.md",
    "docs/api.md",
    "docs/architecture.md",
    "docs/decisions.md",
    "docs/data_dictionary.md",
    "docs/data_quality.md",
    "docs/glossary.md",
    "docs/reproducibility.md",
    "docs/troubleshooting.md",
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


def test_conditional_tables_match_the_summary_csv():
    summary = pd.read_csv(ROOT / "docs" / "conditional_summary.csv")
    subset = summary[summary["level"] == 0.95]
    labels = {
        "hist500": "Historical 500",
        "param500": "Parametric 500",
        "ewma": "EWMA",
        "garch": "GARCH(1,1)",
        "hist_adaptive": "Historical adaptive",
        "param_adaptive": "Parametric adaptive",
    }
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    results = (ROOT / "docs" / "results_conditional.md").read_text(encoding="utf-8")
    for _, row in subset.iterrows():
        prefix = (
            f"| {labels[row['model']]} | {int(row['violations'])} | "
            f"{row['expected']:.1f} | {row['violation_rate']:.2%} |"
        )
        assert prefix in readme, prefix
        assert prefix in results, prefix


def test_conditional_es_table_matches_the_csv():
    table = pd.read_csv(ROOT / "docs" / "conditional_es.csv")
    results = (ROOT / "docs" / "results_conditional.md").read_text(encoding="utf-8")
    for _, row in table.iterrows():
        assert f"{row['mean_cvar']:.4%}" in results
        interval = f"[{row['es_ci_low']:.4%}, {row['es_ci_high']:.4%}]"
        assert interval in results, interval


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


def test_data_dictionary_covers_every_csv_column():
    dictionary = (ROOT / "docs" / "data_dictionary.md").read_text(encoding="utf-8")
    files = [
        ROOT / "data" / "prices.csv",
        ROOT / "docs" / "full_sample_risk.csv",
        ROOT / "docs" / "backtest_summary.csv",
        ROOT / "docs" / "backtest_series.csv",
        ROOT / "docs" / "sensitivity.csv",
        ROOT / "docs" / "violations_by_year.csv",
        ROOT / "docs" / "conditional_summary.csv",
        ROOT / "docs" / "conditional_dm.csv",
        ROOT / "docs" / "conditional_stress.csv",
        ROOT / "docs" / "conditional_es.csv",
        ROOT / "docs" / "conditional_series_95.csv",
    ]
    for path in files:
        for column in pd.read_csv(path, nrows=0).columns:
            assert f"`{column}`" in dictionary, f"{path.name}: {column}"


def test_committed_outputs_match_checksums():
    checksums = (ROOT / "docs" / "checksums.sha256").read_text(encoding="utf-8").splitlines()
    assert checksums
    for line in checksums:
        if not line.strip():
            continue
        digest, filename = line.split()
        target = ROOT / "docs" / filename
        assert target.exists(), filename
        assert hashlib.sha256(target.read_bytes()).hexdigest() == digest, filename


def test_reproducibility_guide_mentions_the_key_checks():
    guide = (ROOT / "docs" / "reproducibility.md").read_text(encoding="utf-8")
    for term in (
        "prices.sha256",
        "checksums.sha256",
        "scripts/check_all.py",
        "seed 42",
        "500",
    ):
        assert term in guide


def test_glossary_and_troubleshooting_are_complete():
    glossary = (ROOT / "docs" / "glossary.md").read_text(encoding="utf-8")
    for term in ("VaR", "CVaR", "Kupiec", "Christoffersen", "Violation"):
        assert term in glossary
    troubleshooting = (ROOT / "docs" / "troubleshooting.md").read_text(encoding="utf-8")
    for term in ("Access denied", "ModuleNotFoundError", "checksum", "MPLBACKEND"):
        assert term in troubleshooting

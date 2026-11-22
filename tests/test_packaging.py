import inspect
import tomllib
from pathlib import Path

import risk_lab
from risk_lab import __version__

ROOT = Path(__file__).resolve().parents[1]


def _pyproject() -> dict:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    return tomllib.loads(text)


def test_pyproject_version_matches_package():
    assert _pyproject()["project"]["version"] == __version__


def test_citation_version_matches_package():
    citation = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
    assert f"version: {__version__}" in citation


def test_changelog_mentions_the_current_version():
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert f"## [{__version__}]" in changelog


def test_py_typed_marker_is_present_and_declared():
    marker = ROOT / "src" / "risk_lab" / "py.typed"
    assert marker.exists()
    package_data = _pyproject()["tool"]["setuptools"]["package-data"]
    assert "py.typed" in package_data["risk_lab"]


def test_all_exports_exist():
    for name in risk_lab.__all__:
        assert hasattr(risk_lab, name), name


def test_public_functions_and_classes_have_docstrings():
    for name in risk_lab.__all__:
        obj = getattr(risk_lab, name)
        if inspect.isfunction(obj) or inspect.isclass(obj):
            assert inspect.getdoc(obj), f"{name} has no docstring"

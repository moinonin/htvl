"""Packaging metadata tests.

These guard the details that only matter at release time - the ones that
stay invisible until the package actually lands on PyPI.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

pyproject = pytest.importorskip("tomllib", reason="tomllib is Python 3.11+")

REPO_ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = REPO_ROOT / "pyproject.toml"


@pytest.fixture(scope="module")
def metadata():
    with open(PYPROJECT, "rb") as handle:
        return pyproject.load(handle)


def test_version_matches_package(metadata):
    """The version in pyproject.toml and htvl.__version__ must never drift."""
    import htvl

    assert htvl.__version__ == metadata["project"]["version"]


def test_required_metadata_fields(metadata):
    project = metadata["project"]
    for field in (
        "name",
        "version",
        "description",
        "readme",
        "requires-python",
        "license",
        "authors",
        "classifiers",
        "urls",
    ):
        assert project.get(field), f"project.{field} is missing"


def test_no_deprecated_license_classifier(metadata):
    """PEP 639: a 'License ::' classifier alongside license = "MIT" makes the
    build fail outright (setuptools >= 77)."""
    forbidden = [
        classifier
        for classifier in metadata["project"]["classifiers"]
        if classifier.startswith("License ::")
    ]
    assert not forbidden, f"license classifiers are superseded: {forbidden}"


def test_python_floor_matches_classifiers(metadata):
    assert metadata["project"]["requires-python"] == ">=3.10"
    versions = sorted(
        match.group(1)
        for classifier in metadata["project"]["classifiers"]
        if (
            match := re.match(
                r"Programming Language :: Python :: (3\.\d+)", classifier
            )
        )
    )
    assert versions == ["3.10", "3.11", "3.12", "3.13"]


def test_readme_links_are_absolute(metadata):
    """PyPI renders the README, where repo-relative links do not resolve."""
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    links = re.findall(r"\]\((?!https?://|#|mailto:)([^)]+)\)", readme)
    assert not links, f"relative links break on PyPI: {links}"


def test_package_is_the_only_top_level_package(metadata):
    """playground/lib/htvl must never leak into the distribution."""
    assert metadata["tool"]["setuptools"]["packages"] == ["htvl"]


def test_license_file_exists():
    assert (REPO_ROOT / "LICENSE").exists()

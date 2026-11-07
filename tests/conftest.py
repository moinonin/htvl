"""Shared test fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
LEGACY = REPO_ROOT / "legacy"


@pytest.fixture
def legacy_templates():
    from htvl.templates import load_templates

    return load_templates(LEGACY / "templates")


@pytest.fixture
def legacy_source():
    return (LEGACY / "index.htvl").read_text(encoding="utf-8")


@pytest.fixture
def legacy_expected():
    return (LEGACY / "public" / "index.html").read_text(encoding="utf-8")

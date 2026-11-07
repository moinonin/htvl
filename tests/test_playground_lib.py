"""The playground must ship a current copy of the compiler.

``playground/lib/`` is what the Pyodide-powered page loads in the browser. If
it drifts from ``htvl/``, the playground silently compiles with old rules - so
this test fails unless ``python3 playground/sync.py`` has been run.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PACKAGE = REPO_ROOT / "htvl"
LIB = REPO_ROOT / "playground" / "lib"
LIB_PACKAGE = LIB / "htvl"


def _package_files():
    return {
        path.name: path.read_text(encoding="utf-8")
        for path in sorted(PACKAGE.glob("*.py"))
    }


def test_playground_lib_exists():
    assert LIB_PACKAGE.is_dir(), (
        "playground/lib/htvl is missing - run: python3 playground/sync.py"
    )


def test_every_package_file_is_copied():
    for name, expected in _package_files().items():
        copied = LIB_PACKAGE / name
        assert copied.exists(), (
            f"{name} missing from playground/lib - run sync.py"
        )
        assert copied.read_text(encoding="utf-8") == expected, (
            f"{name} drifted - run: python3 playground/sync.py"
        )


def test_manifest_lists_every_file():
    manifest = json.loads((LIB / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["files"] == sorted(_package_files())
    assert manifest["version"]


def _load_lib_copy():
    """Import playground/lib/htvl under a distinct name (the repo checkout's
    'htvl' is already in sys.modules)."""
    spec = importlib.util.spec_from_file_location(
        "htvl_playground",
        LIB_PACKAGE / "__init__.py",
        submodule_search_locations=[str(LIB_PACKAGE)],
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["htvl_playground"] = module
    spec.loader.exec_module(module)
    return module


def _sample_source():
    js = (REPO_ROOT / "playground" / "playground.js").read_text(encoding="utf-8")
    marker = "const SAMPLE = `"
    start = js.index(marker) + len(marker)
    end = js.index("`;", start)
    return js[start:end]


def test_playground_sample_compiles_in_both_modes():
    compile_source = _load_lib_copy().compile_source
    sample = _sample_source()

    for modern in (False, True):
        html = compile_source(sample, modern=modern)
        assert html.startswith("<!DOCTYPE html>")
        assert "</html>" in html
    assert 'class=""' in compile_source(sample, modern=False)
    assert 'class=""' not in compile_source(sample, modern=True)

"""Golden test: the port must reproduce the legacy compiler byte-for-byte.

``legacy/public/index.html`` was generated in 2020 by the original obfuscated
bash compiler. If this test passes, the Python port is a faithful
reimplementation of the HTVL language.
"""

from __future__ import annotations

from htvl.project import compile_source


def test_legacy_index_htvl_compiles_identically(
    legacy_source, legacy_templates, legacy_expected
):
    assert compile_source(legacy_source, legacy_templates) == legacy_expected

"""Template loading tests (legacy .sh heredocs and modern .htvl files)."""

from __future__ import annotations

from htvl.project import compile_source
from htvl.templates import load_templates


def test_legacy_project_templates_load(legacy_templates):
    assert set(legacy_templates) == {"headtags", "footer", "nav0"}
    assert "$(title)" in legacy_templates["headtags"]
    assert "$(footer 'page-footer" in legacy_templates["footer"]
    # Whitespace-only heredocs collapse to nothing.
    assert legacy_templates["nav0"].strip() == ""


def test_templates_are_stripped(tmp_path):
    (tmp_path / "templates").mkdir()
    (tmp_path / "templates" / "part.htvl").write_text(
        "\n\n  $(br)\n\n", encoding="utf-8"
    )
    templates = load_templates(tmp_path / "templates")
    assert templates["part"] == "$(br)"


def test_template_values_are_compiled_before_splicing(tmp_path):
    (tmp_path / "templates").mkdir()
    (tmp_path / "templates" / "part.htvl").write_text(
        "$(h 2 '' '' 'From template' '')\n$br", encoding="utf-8"
    )
    templates = load_templates(tmp_path / "templates")
    html = compile_source("$part\n", templates)
    assert '<h2 class="" id="" style="">From template</h2>' in html
    assert "<br>" in html
    assert "$(h 2" not in html


def test_template_first_line_takes_callers_indent(tmp_path):
    (tmp_path / "templates").mkdir()
    (tmp_path / "templates" / "part.htvl").write_text(
        "  $br\n    $br", encoding="utf-8"
    )
    templates = load_templates(tmp_path / "templates")
    html = compile_source("      $part\n", templates)
    assert html == "      <br>\n    <br>\n\n"


def test_missing_templates_directory(tmp_path):
    assert load_templates(tmp_path / "nope") == {}

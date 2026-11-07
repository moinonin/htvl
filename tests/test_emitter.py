"""End-to-end emitter tests."""

from __future__ import annotations

import pytest

from htvl.errors import HtvlUnknownTagError, HtvlUnknownVariableError
from htvl.project import compile_source


def test_hello_world():
    html = compile_source("$(h 3 '' '' 'Official Sponsor')\n")
    assert html == '<h3 class="" id="" style="">Official Sponsor</h3>\n\n'


def test_line_structure_and_indentation_are_preserved():
    source = "  $(div 'a')\n    $(p '' '' '' '')\n      text\n    $_p\n  $_div\n"
    assert compile_source(source) == (
        '  <div class="a" id="" style="">\n'
        '    <p class="" id="" style="">\n'
        "      text\n"
        "    </p>\n"
        "  </div>\n"
        "\n"
    )


def test_variable_expansion():
    html = compile_source("$DOCTYPE_htvl\n$htvl\n$_htvl\n")
    assert html == (
        "<!DOCTYPE html>\n" '<html lang="en">\n' "</html>\n" "\n"
    )


def test_meta_block_expands_multiline():
    html = compile_source("$meta\n")
    assert html == (
        '<meta charset="UTF-8">\n'
        '<meta name="description" content="Functional CSS Founders">\n'
        '<meta name="keywords" content="HTML,CSS,XML,JavaScript">\n'
        '<meta name="viewport" content="width=device-width, '
        'initial-scale=1.0">\n'
        "\n"
    )


def test_array_variable_word_splitting():
    templates = {"nav0": "\n\n\n"}
    assert compile_source("      ${nav0[@]} \n", templates) == "       \n\n"


def test_unknown_close_tag_falls_back_to_closing_tag():
    assert compile_source("$_video\n") == "</video>\n\n"


def test_unknown_variable_raises_with_line_number():
    with pytest.raises(HtvlUnknownVariableError) as excinfo:
        compile_source("ok\n$nope\n")
    assert excinfo.value.name == "nope"
    assert "line 2" in str(excinfo.value)


def test_unknown_tag_raises_with_line_number():
    with pytest.raises(HtvlUnknownTagError) as excinfo:
        compile_source("ok\n$(nope 'x')\n")
    assert "line 2" in str(excinfo.value)


def test_unbalanced_call_raises():
    with pytest.raises(Exception) as excinfo:
        compile_source("$(div 'x'\n")
    assert "'$('" in str(excinfo.value)


def test_empty_source():
    assert compile_source("") == ""


def test_text_passes_through_verbatim():
    html = compile_source("Copyright &copy; 2026\n")
    assert html == "Copyright &copy; 2026\n\n"

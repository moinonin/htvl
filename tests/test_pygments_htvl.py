"""Tests for the Pygments lexer (extras/pygments_htvl.py).

Pygments is an optional dependency: these tests skip when it is missing.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

pygments = pytest.importorskip("pygments")
from pygments.token import (  # noqa: E402
    Comment,
    Name,
    Number,
    Operator,
    Punctuation,
    String,
    Text,
    Whitespace,
)

LEXER_PATH = Path(__file__).resolve().parent.parent / "extras" / "pygments_htvl.py"


@pytest.fixture(scope="module")
def lexer():
    spec = importlib.util.spec_from_file_location("pygments_htvl", LEXER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.HtvlLexer()


def _stream(lexer, source):
    return list(lexer.get_tokens(source))


def _reassembled(lexer, source):
    """The tokens must always reassemble into the source (plus Pygments'
    habitual trailing newline)."""
    values = "".join(value for _token, value in _stream(lexer, source))
    assert values == source + ("" if source.endswith("\n") else "\n")
    return values


def test_declared_filenames(lexer):
    assert "*.htvl" in lexer.filenames
    assert "*.cal" in lexer.filenames
    assert "htvl" in lexer.aliases


def test_text_and_whitespace(lexer):
    tokens = _stream(lexer, "hello world\n")
    assert (Text, "hello world") in tokens
    assert (Whitespace, "\n") in tokens
    _reassembled(lexer, "hello world\n")


def test_tag_call_is_highlighted(lexer):
    tokens = _stream(lexer, "$(h 3 '' '' 'Title' '')")
    assert (Punctuation, "$(") in tokens
    assert (Name.Function, "h") in tokens
    assert (Number.Integer, "3") in tokens
    assert (String.Single, "''") in tokens
    assert (String.Single, "'Title'") in tokens
    assert (Punctuation, ")") in tokens


def test_nested_call(lexer):
    tokens = _stream(lexer, "$(link stylesheet 'text/css' $(bsCdn '4.3.1'))")
    names = {value for token, value in tokens if token is Name.Function}
    assert names == {"link", "bsCdn"}
    assert (String.Single, "'4.3.1'") in tokens


def test_quotes_stay_balanced(lexer):
    _reassembled(lexer, "$(p '' '' 'costs (5) dollars' '')")


def test_variables(lexer):
    tokens = _stream(lexer, "$head $_a ${nav0[@]}")
    assert (Operator, "$") in tokens
    assert (Name.Variable, "head") in tokens
    assert (Name.Tag, "_a") in tokens
    assert (Name.Variable, "nav0") in tokens


def test_lone_dollar_is_text(lexer):
    tokens = _stream(lexer, "costs $5")
    assert (Text, "$") in tokens
    _reassembled(lexer, "costs $5")


def test_html_comment(lexer):
    tokens = _stream(lexer, "<!-- note -->")
    assert (Comment.Multiline, "<!-- note -->") in tokens


def test_lost_nothing(lexer):
    """Whatever the source, the tokens must reassemble into the source."""
    source = (
        Path(__file__).resolve().parent.parent
        / "legacy"
        / "index.htvl"
    ).read_text(encoding="utf-8")
    values = "".join(value for _token, value in _stream(lexer, source))
    assert values == source

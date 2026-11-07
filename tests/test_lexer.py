"""Tokenizer tests."""

from __future__ import annotations

import pytest

from htvl.errors import HtvlSyntaxError
from htvl.lexer import split_args, tokenize, unquote
from htvl.nodes import ArrayVar, Call, Text, Var


def test_plain_text():
    tokens = tokenize("hello world")
    assert tokens == [Text("hello world")]


def test_simple_call():
    tokens = tokenize("$(comment 'hi')")
    assert len(tokens) == 1
    call = tokens[0]
    assert isinstance(call, Call)
    assert call.name == "comment"
    assert call.args == ["hi"]


def test_call_with_bare_words_and_empty_strings():
    tokens = tokenize("$(h 3 '' '' 'Official Sponsor')")
    call = tokens[0]
    assert isinstance(call, Call)
    assert call.name == "h"
    assert call.args == ["3", "", "", "Official Sponsor"]


def test_nested_call():
    tokens = tokenize("$(link stylesheet 'text/css' $(bsCdn '4.3.1'))")
    call = tokens[0]
    assert call.name == "link"
    assert call.args[0] == "stylesheet"
    assert call.args[1] == "text/css"
    inner = call.args[2]
    assert isinstance(inner, Call)
    assert inner.name == "bsCdn"
    assert inner.args == ["4.3.1"]


def test_parens_inside_quotes_are_literal():
    call = tokenize("$(p '' '' 'if (a > b) then' '')")[0]
    assert call.args[2] == "if (a > b) then"


def test_variables():
    tokens = tokenize("$head $_a ${nav0[@]}")
    vars_ = [t for t in tokens if isinstance(t, (Var, ArrayVar))]
    assert [t.name for t in vars_] == ["head", "_a", "nav0"]
    assert isinstance(vars_[0], Var)
    assert isinstance(vars_[2], ArrayVar)


def test_newline_is_a_token():
    tokens = tokenize("a\nb")
    assert tokens == [Text("a"), Text("\n"), Text("b")]


def test_positional_dollar_stays_text():
    assert tokenize("costs $5") == [Text("costs "), Text("$"), Text("5")]


def test_unbalanced_call_raises_with_position():
    with pytest.raises(HtvlSyntaxError) as excinfo:
        tokenize("ok\n$(div 'x'")
    error = excinfo.value
    assert error.line == 2
    assert "'$('" in str(error)


def test_split_args_keeps_quoted_whitespace():
    assert split_args("'a b'  '' 'c'") == ["'a b'", "''", "'c'"]


def test_unquote():
    assert unquote("'x'") == "x"
    assert unquote('"x"') == "x"
    assert unquote("bare") == "bare"


def test_double_quoted_args_supported():
    call = tokenize('$(p "" "some \\"quoted\\" text" "")')[0]
    assert call.args[1] == 'some "quoted" text'


def test_call_positions_are_tracked():
    tokens = tokenize("line one\n  $(br)")
    call = tokens[-1]
    assert (call.line, call.column) == (2, 3)

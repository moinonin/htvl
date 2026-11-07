"""Parser tests."""

from __future__ import annotations

from htvl.nodes import Call, Text, Var
from htvl.parser import parse


def test_lines_and_linenos():
    document = parse("$head\n$_head\n")
    assert len(document.lines) == 2
    assert document.lines[0].lineno == 1
    assert document.lines[1].lineno == 2


def test_trailing_content_without_newline():
    document = parse("$(br)")
    assert len(document.lines) == 1
    assert document.lines[0].lineno == 1


def test_leading_whitespace_is_preserved_as_text():
    document = parse("    $_div")
    tokens = document.lines[0].tokens
    assert isinstance(tokens[0], Text)
    assert tokens[0].value == "    "
    assert isinstance(tokens[1], Var)
    assert tokens[1].name == "_div"


def test_inline_sequence_on_one_line():
    document = parse("$(img 'a.png')$_a text")
    tokens = document.lines[0].tokens
    assert [type(t).__name__ for t in tokens] == ["Call", "Var", "Text"]
    assert tokens[2].value == " text"


def test_nested_calls_survive_parsing():
    document = parse("$(link '' 'text/css' $(bsCdn '4.3.1'))")
    call = document.lines[0].tokens[0]
    assert isinstance(call, Call)
    assert isinstance(call.args[2], Call)

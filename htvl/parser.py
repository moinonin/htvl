"""Parser: turns a flat token stream into a line-oriented AST."""

from __future__ import annotations

from typing import List

from .lexer import tokenize
from .nodes import Document, Line, Text, Token


def parse(source: str) -> Document:
    """Parse HTVL source text into a :class:`htvl.nodes.Document`."""
    tokens: List[Token] = tokenize(source)
    lines: List[Line] = []
    current: List[Token] = []
    lineno = 1
    for token in tokens:
        if isinstance(token, Text) and token.value == "\n":
            lines.append(Line(tokens=current, lineno=lineno))
            current = []
            lineno += 1
            continue
        current.append(token)
    if current:
        lines.append(Line(tokens=current, lineno=lineno))
    return Document(lines=lines)

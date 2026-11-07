"""AST node definitions for the HTVL compiler.

The tree is deliberately line-oriented: HTVL preserves the line structure of
its source (one source line maps to one output line, with leading whitespace
kept as-is), so the parser keeps newline boundaries explicit.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Union


@dataclass
class Text:
    """Literal text, passed through to the output verbatim."""

    value: str


@dataclass
class Var:
    """A ``$name`` variable reference (``$head``, ``$_a``, ``$headtags``...)."""

    name: str


@dataclass
class ArrayVar:
    """A ``${name[@]}`` array reference (legacy bash-array style)."""

    name: str


@dataclass
class Call:
    """A ``$(name 'arg' ...)`` tag call. Args may nest further Calls."""

    name: str
    args: List[Union[str, "Call"]] = field(default_factory=list)
    line: int = 0
    column: int = 0


Token = Union[Text, Var, ArrayVar, Call]


@dataclass
class Line:
    """One source line: its tokens, in order, plus its 1-based line number."""

    tokens: List[Token]
    lineno: int


@dataclass
class Document:
    """A parsed HTVL source file."""

    lines: List[Line]

"""Pygments lexer for the HTVL language.

Register it so any Pygments-based tool (Sphinx, MkDocs, code renderers) can
highlight ``.htvl`` files::

    from pygments.lexers import LEXERS
    LEXERS["htvl"] = (
        "pygments_htvl", "HTVL", ("htvl",), ("*.htvl", "*.cal"), ()
    )

or point Pygments at the file directly::

    pygmentize -l /path/to/pygments_htvl.py:HtvlLexer -f html index.htvl
"""

from __future__ import annotations

from pygments.lexer import RegexLexer, bygroups
from pygments.token import (
    Comment,
    Name,
    Number,
    Operator,
    Punctuation,
    String,
    Text,
    Whitespace,
)

__all__ = ["HtvlLexer"]


class HtvlLexer(RegexLexer):
    """Highlighting for HTVL source."""

    name = "HTVL"
    aliases = ["htvl"]
    filenames = ["*.htvl", "*.cal"]

    tokens = {
        "root": [
            (r"<!--[\s\S]*?-->", Comment.Multiline),
            (r"[^$\n]+", Text),
            (r"\n", Whitespace),
            (r"\$\(", Punctuation, "tagname"),
            (
                r"(\$\{)([A-Za-z_][A-Za-z0-9_]*)(\[@\]\})",
                bygroups(Operator, Name.Variable, Operator),
            ),
            (
                r"(\$)(_[A-Za-z_][A-Za-z0-9_]*)",
                bygroups(Operator, Name.Tag),
            ),
            (
                r"(\$)([A-Za-z_][A-Za-z0-9_]*)",
                bygroups(Operator, Name.Variable),
            ),
            (r"\$", Text),  # lone dollar, e.g. "costs $5"
        ],
        "tagname": [
            (r"[A-Za-z_][A-Za-z0-9_-]*", Name.Function, "arguments"),
            (r"[)\s]", Punctuation, "#pop"),
        ],
        "arguments": [
            (r"\)", Punctuation, "#pop"),
            (r"\$\(", Punctuation, "tagname"),
            (r"'[^']*'", String.Single),
            (r'"(?:[^"\\]|\\.)*"', String.Double),
            (r"\b\d+\.\d+\b", Number.Float),
            (r"\b\d+\b", Number.Integer),
            (r"[A-Za-z_][A-Za-z0-9_-]*", Name.Variable),
            (r"[ \t]+", Whitespace),
        ],
    }

"""Emitter: renders a parsed Document to HTML text.

The emitter preserves the line structure of the source: one source line
produces one output line, leading whitespace is kept verbatim, and multi-line
expansions (``$meta``, ``$headtags``, ...) are spliced inline, with the first
line taking the indentation of the line that referenced them - exactly the way
the original bash implementation behaved when its heredocs expanded.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from .elements import render_call
from .errors import HtvlUnknownVariableError
from .nodes import ArrayVar, Call, Document, Line, Text, Token, Var
from .parser import parse
from .variables import VARIABLES

_MAX_TEMPLATE_DEPTH = 8


class Emitter:
    """Renders HTVL documents to HTML."""

    def __init__(self, templates: Optional[Dict[str, str]] = None) -> None:
        self.templates: Dict[str, str] = dict(templates or {})

    def emit(self, document: Document) -> str:
        out: List[str] = []
        for line in document.lines:
            self._emit_line(line, out)
        if not out:
            return ""
        # Every source line is terminated, and the legacy compiler appended
        # one extra newline after the document body.
        return "\n".join(out) + "\n\n"

    # -- internals ---------------------------------------------------------

    def _emit_line(self, line: Line, out: List[str]) -> None:
        buf = len(out)
        out.append("")

        for token in line.tokens:
            if isinstance(token, Text):
                buf = self._splice(out, buf, token.value)
            elif isinstance(token, Var):
                buf = self._splice(
                    out, buf, self._expand_var(token, line.lineno)
                )
            elif isinstance(token, ArrayVar):
                buf = self._splice(
                    out, buf, self._expand_array(token, line.lineno)
                )
            elif isinstance(token, Call):
                buf = self._splice(out, buf, self._render_call(token))

    @staticmethod
    def _splice(out: List[str], buf: int, text: str) -> int:
        """Append ``text`` to output line ``buf``, following embedded newlines.

        Returns the index of the output line the append finished on, so that
        tokens following a multi-line expansion continue on its last line.
        """
        parts = text.split("\n")
        out[buf] += parts[0]
        for part in parts[1:]:
            out.append(part)
            buf = len(out) - 1
        return buf

    def _expand_var(self, token: Var, lineno: int) -> str:
        return self._expand(token.name, lineno, array=False)

    def _expand_array(self, token: ArrayVar, lineno: int) -> str:
        return self._expand(token.name, lineno, array=True)

    def _expand(self, name: str, lineno: int, array: bool) -> str:
        if name in VARIABLES:
            value = VARIABLES[name]
        elif name in self.templates:
            # Templates are HTVL source themselves: compile them first, the
            # way the original bash implementation sourced its heredocs.
            value = self._compile_template(name, lineno)
        elif name.startswith("_"):
            # Unknown closing references (e.g. $_video) degrade gracefully to
            # the obvious closing tag.
            return f"</{name[1:]}>"
        else:
            raise HtvlUnknownVariableError(name, lineno)

        if array:
            # Legacy ${name[@]} expansions undergo bash-style word splitting:
            # whitespace-only values collapse to nothing.
            value = " ".join(value.split())
        return value

    def _compile_template(self, name: str, lineno: int, depth: int = 0) -> str:
        if depth > _MAX_TEMPLATE_DEPTH:
            raise HtvlUnknownVariableError(
                f"{name} (template includes itself)", lineno
            )
        nested = Emitter(self.templates)
        compiled = nested.emit(parse(self.templates[name]))
        return compiled.rstrip("\n")

    def _render_call(self, call: Call) -> str:
        args = []
        for arg in call.args:
            if isinstance(arg, Call):
                args.append(self._render_call(arg))
            else:
                args.append(arg)
        return render_call(call.name, args, call.line)


def emit(document: Document, templates: Optional[Dict[str, str]] = None) -> str:
    """Convenience wrapper around :class:`Emitter`."""
    return Emitter(templates=templates).emit(document)

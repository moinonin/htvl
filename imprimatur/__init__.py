"""Imprimatur - the oracle: HTVL source in, structured diagnostics out.

Make machine-written HTML correct by construction, or fail loudly at a known
line. ``check`` is a pure function: no filesystem writes, no network, no
global state. Failures are values (``ok=False`` with coded diagnostics), never
exceptions, so a repair loop can parse them.
"""

from __future__ import annotations

import difflib
import subprocess
import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

from htvl import compile_source
from htvl.errors import (
    HtvlArityError,
    HtvlError,
    HtvlSyntaxError,
    HtvlUnknownTagError,
    HtvlUnknownVariableError,
)
from htvl.elements import ELEMENTS
from htvl.variables import VARIABLES

from . import _guard
from .structural import CONTAINER_TAGS, Imbalance, find_imbalances

__version__ = "1.0.0"

__all__ = [
    "Code",
    "Diagnostic",
    "Result",
    "check",
    "tag_signatures",
    "explain",
    "variable_signatures",
    "grammar_reference",
    "MAX_SOURCE",
    "TIMEOUT_S",
    "IN_PROCESS_LIMIT",
]


class Code(str, Enum):
    """Stable, machine-readable failure codes. The repair loop parses these,
    never the human prose in ``message``.

    ``str, Enum`` rather than ``StrEnum`` because the supported floor is
    Python 3.10 (docs/decisions.md D10); members still compare and serialize
    as plain strings.
    """

    UNKNOWN_TAG = "UNKNOWN_TAG"
    UNKNOWN_VARIABLE = "UNKNOWN_VARIABLE"  # extension: see docs/decisions.md D9
    UNCLOSED_TAG = "UNCLOSED_TAG"
    UNEXPECTED_CLOSE = "UNEXPECTED_CLOSE"
    BAD_ARG_COUNT = "BAD_ARG_COUNT"
    UNTERMINATED_STR = "UNTERMINATED_STR"
    SYNTAX = "SYNTAX"
    TOO_LARGE = "TOO_LARGE"
    TIMEOUT = "TIMEOUT"
    INTERNAL = "INTERNAL"


@dataclass(frozen=True)
class Diagnostic:
    """One problem, located. ``detail`` carries the offending token (a tag or
    variable name) so ``explain`` never has to parse prose."""

    code: Code
    line: int
    column: Optional[int] = None
    message: str = ""
    snippet: Optional[str] = None
    detail: Optional[str] = None

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class Result:
    """The outcome of one ``check`` call."""

    ok: bool
    html: Optional[str] = None
    diagnostics: List[Diagnostic] = field(default_factory=list)
    elapsed_ms: float = 0.0


# Guard policy. MAX_SOURCE is 256KB, not the 1MB of the brief's sketch: recon
# Q6 measured a 1MB document at 3.8-9s, which cannot fit a 5s timeout. See
# docs/decisions.md D4/D5.
MAX_SOURCE = 256_000
TIMEOUT_S = 5.0
IN_PROCESS_LIMIT = 64_000

_SNIPPET_CONTEXT = 2


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def check(
    source: str,
    *,
    modern: bool = True,
    timeout: float = TIMEOUT_S,
    max_source: int = MAX_SOURCE,
) -> Result:
    """HTVL source -> Result. Never raises for invalid source."""
    started = time.perf_counter()

    if not isinstance(source, str):
        raise TypeError("source must be str")

    if len(source.encode("utf-8")) > max_source:
        return Result(
            ok=False,
            diagnostics=[
                Diagnostic(
                    code=Code.TOO_LARGE,
                    line=0,
                    message=(
                        f"source is {len(source.encode('utf-8'))} bytes; "
                        f"the cap is {max_source}"
                    ),
                )
            ],
            elapsed_ms=_elapsed_ms(started),
        )

    if len(source) > IN_PROCESS_LIMIT:
        try:
            payload = _guard.check_guarded(source, modern, timeout)
        except subprocess.TimeoutExpired:
            return Result(
                ok=False,
                diagnostics=[
                    Diagnostic(
                        code=Code.TIMEOUT,
                        line=0,
                        message=f"compile exceeded {timeout:g}s",
                    )
                ],
                elapsed_ms=_elapsed_ms(started),
            )
        except Exception as exc:  # child crashed -> internal, not a hang
            return Result(
                ok=False,
                diagnostics=[
                    Diagnostic(
                        code=Code.INTERNAL,
                        line=0,
                        message=f"guard child failed: {exc}",
                    )
                ],
                elapsed_ms=_elapsed_ms(started),
            )
        diagnostics = [
            Diagnostic(
                code=Code(item["code"]),
                line=item["line"],
                column=item.get("column"),
                message=item.get("message", ""),
                snippet=item.get("snippet"),
                detail=item.get("detail"),
            )
            for item in payload["diagnostics"]
        ]
        return Result(
            ok=payload["ok"],
            html=payload["html"],
            diagnostics=diagnostics,
            elapsed_ms=_elapsed_ms(started),
        )

    return _check_local(source, modern=modern, started=started)


def _check_local(
    source: str, *, modern: bool, started: Optional[float] = None
) -> Result:
    """The in-process path: compile, then cover the compiler's blind spots.

    Also the entry point the timeout guard child calls.
    """
    if started is None:
        started = time.perf_counter()

    compile_diags: List[Diagnostic] = []
    html: Optional[str] = None
    try:
        html = compile_source(source, modern=modern)
    except HtvlError as exc:
        compile_diags.append(_from_htvl_error(exc, source))
    except RecursionError:
        compile_diags.append(
            Diagnostic(
                code=Code.INTERNAL,
                line=0,
                message="nesting too deep (recursion limit)",
            )
        )
    except Exception as exc:  # never leak an exception to the caller
        compile_diags.append(
            Diagnostic(
                code=Code.INTERNAL,
                line=0,
                message=f"{type(exc).__name__}: {exc}",
            )
        )

    diagnostics = sorted(compile_diags, key=lambda diag: (diag.line, str(diag.code)))
    if diagnostics:
        return Result(
            ok=False,
            html=None,
            diagnostics=diagnostics,
            elapsed_ms=_elapsed_ms(started),
        )

    # The source parsed, so balance analysis is meaningful - this is the
    # compiler's blind spot (recon Q2).
    structural = [
        Diagnostic(
            code=Code.UNCLOSED_TAG if problem.kind == "UNCLOSED_TAG"
            else Code.UNEXPECTED_CLOSE,
            line=problem.line,
            message=(
                f"$({problem.tag} ...) is opened here but never closed"
                if problem.kind == "UNCLOSED_TAG"
                else f"$_{problem.tag} closes nothing - no open container"
            ),
            snippet=_snippet(source, problem.line),
            detail=problem.tag,
        )
        for problem in find_imbalances(source)
    ]
    if structural:
        return Result(
            ok=False,
            html=None,
            diagnostics=structural,
            elapsed_ms=_elapsed_ms(started),
        )
    return Result(ok=True, html=html, elapsed_ms=_elapsed_ms(started))


def tag_signatures() -> List[str]:
    """Every tag signature the compiler accepts - generated from its table,
    never hand-maintained."""
    return [ELEMENTS[name].signature for name in sorted(ELEMENTS)]


def variable_signatures() -> List[str]:
    """Every built-in variable, as ``$name -> value`` lines."""
    lines = []
    for name in sorted(VARIABLES):
        value = VARIABLES[name].replace("\n", "\\n")
        if len(value) > 46:
            value = value[:43] + "..."
        lines.append(f"${name} -> {value}")
    return lines


def grammar_reference() -> str:
    """The ``htvl list`` output, byte for byte (asserted by tests)."""
    return (
        "Tags\n----\n"
        + "\n".join(f"  {signature}" for signature in tag_signatures())
        + "\n\nVariables\n---------\n"
        + "\n".join(f"  {line}" for line in variable_signatures())
        + "\n"
    )


def explain(diag: Diagnostic, signatures: Optional[List[str]] = None) -> str:
    """Turn a diagnostic into a repair hint a model can act on."""
    if signatures is None:
        signatures = tag_signatures()
    names = {_name_of(sig): sig for sig in signatures}

    if diag.code is Code.UNKNOWN_TAG:
        name = diag.detail or ""
        near = difflib.get_close_matches(name, list(names), n=3, cutoff=0.4)
        hint = f"unknown tag '{name}'"
        if near:
            hint += " - did you mean " + ", ".join(f"'{n}'" for n in near) + "?"
        else:
            hint += " - call list_tags to see every valid tag"
        return hint

    if diag.code is Code.UNKNOWN_VARIABLE:
        name = diag.detail or ""
        candidates = difflib.get_close_matches(
            name, [line.split(" ")[0][1:] for line in variable_signatures()],
            n=3, cutoff=0.4,
        )
        hint = f"unknown variable '${name}'"
        if candidates:
            hint += " - did you mean " + ", ".join(f"${c}" for c in candidates) + "?"
        else:
            hint += " - define it in templates/, or use a built-in"
        return hint

    if diag.code is Code.BAD_ARG_COUNT:
        tag = diag.detail or ""
        signature = names.get(tag)
        if signature:
            return f"wrong number of arguments for '{tag}' - expected {signature}"
        return diag.message or "wrong number of arguments"

    if diag.code is Code.UNCLOSED_TAG:
        tag = diag.detail or ""
        closer = _closer_for(tag)
        return (
            f"line {diag.line} opens $({tag} ...) but nothing closes it - "
            f"add {closer} after the container's content"
        )

    if diag.code is Code.UNEXPECTED_CLOSE:
        tag = diag.detail or ""
        return (
            f"line {diag.line} closes $_{tag} but no $({tag} ...) is open - "
            "remove the closer or add the opening tag"
        )

    if diag.code is Code.UNTERMINATED_STR:
        return (
            f"line {diag.line}: a string or call was never closed - check the "
            "quote and the closing parenthesis"
        )

    if diag.code is Code.SYNTAX:
        return diag.message or "syntax error"

    return diag.message or str(diag.code)


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


def _elapsed_ms(started: float) -> float:
    return round((time.perf_counter() - started) * 1000, 3)


def _from_htvl_error(exc: HtvlError, source: str) -> Diagnostic:
    """Map a compiler exception to a coded diagnostic."""
    line = getattr(exc, "line", None)
    column = getattr(exc, "column", None)
    message = str(exc)

    if isinstance(exc, HtvlUnknownTagError):
        code, detail = Code.UNKNOWN_TAG, exc.name
    elif isinstance(exc, HtvlUnknownVariableError):
        code, detail = Code.UNKNOWN_VARIABLE, exc.name
    elif isinstance(exc, HtvlArityError):
        code, detail = Code.BAD_ARG_COUNT, exc.name
        if not line:
            # HtvlArityError reports the line in its message but never sets
            # the attribute (upstream bug, see docs/decisions.md D12). Recover
            # the position from the compiler's own parse tree.
            line = _locate_call(source, exc.name) or 0
    elif isinstance(exc, HtvlSyntaxError):
        if "unbalanced '$('" in message:
            # The lexer cannot distinguish an unclosed string from an
            # unclosed call (recon Q1); both land here.
            code = Code.UNTERMINATED_STR
        else:
            code = Code.SYNTAX
        detail = None
    else:  # future HtvlError subclasses
        code, detail = Code.SYNTAX, None

    return Diagnostic(
        code=code,
        line=line or 0,
        column=column,
        message=message,
        snippet=_snippet(source, line or 0),
        detail=detail,
    )


def _locate_call(source: str, name: str) -> Optional[int]:
    """Find the first line whose ``$(name ...)`` call has too many arguments.

    Uses the compiler's own parser (``htvl.parser.parse``) - no text scraping
    of error prose. Returns None if the source cannot be re-parsed.
    """
    try:
        from htvl.elements import ELEMENTS as _ELEMENTS
        from htvl.nodes import Call
        from htvl.parser import parse

        limit = len(_ELEMENTS[name].params)
        for line in parse(source).lines:
            for token in line.tokens:
                if (
                    isinstance(token, Call)
                    and token.name == name
                    and len(token.args) > limit
                ):
                    return line.lineno
    except Exception:
        return None
    return None


def _snippet(source: str, line: int) -> Optional[str]:
    """The offending line plus two lines of context either side."""
    if line < 1:
        return None
    lines = source.splitlines()
    if line > len(lines):
        return None
    low = max(1, line - _SNIPPET_CONTEXT)
    high = min(len(lines), line + _SNIPPET_CONTEXT)
    rendered = []
    for number in range(low, high + 1):
        marker = ">>" if number == line else "  "
        rendered.append(f"{marker} {number:>4} | {lines[number - 1]}")
    return "\n".join(rendered)


def _name_of(signature: str) -> str:
    """'$(a class href ...)' -> 'a'."""
    parts = signature.split()
    return parts[0][2:] if parts else ""


def _closer_for(tag: str) -> str:
    if tag == "nav-a":
        return "$_a"
    if tag == "svgSimple":
        return "$_svg"
    return f"$_{tag}"

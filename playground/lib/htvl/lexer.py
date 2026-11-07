"""Tokenizer for HTVL source files.

HTVL source is plain text sprinkled with three kinds of constructs:

* ``$(tag 'arg' ...)``   - a tag call, possibly with nested calls as arguments
* ``$name``              - a variable reference (``$head``, ``$_a``, ``$meta``)
* ``${name[@]}``         - an array-style variable reference (legacy syntax)

Everything else is literal text. Newlines are significant tokens: HTVL keeps
the line structure of the source, so the parser uses them to split the token
stream into :class:`htvl.nodes.Line` objects.
"""

from __future__ import annotations

from typing import List, Tuple

from .errors import HtvlSyntaxError
from .nodes import ArrayVar, Call, Text, Token, Var

_WHITESPACE = " \t"


def _scan_call(source: str, start: int) -> Tuple[str, int]:
    """Return the raw inner text of a ``$(...)`` call and the index after it.

    The scan is quote-aware: parentheses inside single or double quotes do not
    count, which lets arguments contain arbitrary text. Nested ``$(...)`` calls
    are balanced correctly.
    """
    depth = 1
    i = start + 2  # skip the opening "$("
    quote = None
    n = len(source)
    while i < n:
        ch = source[i]
        if quote is not None:
            if ch == quote:
                quote = None
            i += 1
            continue
        if ch in ("'", '"'):
            quote = ch
            i += 1
        elif ch == "(":
            depth += 1
            i += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return source[start + 2 : i], i + 1
            i += 1
        else:
            i += 1
    raise HtvlSyntaxError(
        "unbalanced '$(': missing closing ')'",
        line=_line_of(source, start),
        column=_column_of(source, start),
    )


def split_args(raw: str) -> List[str]:
    """Split the inner text of a call into its argument strings.

    Arguments are separated by whitespace outside quotes. Quoting rules mirror
    the original bash implementation: arguments are usually single-quoted, bare
    words (e.g. ``$(h 3 ...)``) are also allowed, and nested ``$(...)`` calls
    are kept intact for the parser to resolve.
    """
    args: List[str] = []
    i = 0
    n = len(raw)
    while i < n:
        while i < n and raw[i] in _WHITESPACE:
            i += 1
        if i >= n:
            break
        start = i
        depth = 0
        quote = None
        while i < n:
            ch = raw[i]
            if quote is not None:
                if ch == quote:
                    quote = None
                i += 1
                continue
            if ch in ("'", '"'):
                quote = ch
                i += 1
            elif ch == "(":
                depth += 1
                i += 1
            elif ch == ")":
                if depth == 0:
                    break
                depth -= 1
                i += 1
            elif ch in _WHITESPACE and depth == 0:
                break
            else:
                i += 1
        args.append(raw[start:i])
    return args


def unquote(arg: str) -> str:
    """Strip one layer of quoting from a raw argument string."""
    if len(arg) >= 2 and arg[0] == arg[-1] and arg[0] in ("'", '"'):
        inner = arg[1:-1]
        if arg[0] == '"':
            inner = inner.replace('\\"', '"').replace("\\\\", "\\")
        return inner
    return arg


def _line_of(source: str, index: int) -> int:
    return source.count("\n", 0, index) + 1


def _column_of(source: str, index: int) -> int:
    return index - (source.rfind("\n", 0, index) + 1) + 1


def tokenize(source: str) -> List[Token]:
    """Tokenize HTVL source text into a flat token list.

    Newlines become :class:`Text` tokens containing ``"\\n"`` so the parser can
    recover line boundaries without losing position information.
    """
    tokens: List[Token] = []
    i = 0
    n = len(source)
    while i < n:
        ch = source[i]
        if ch == "\n":
            tokens.append(Text("\n"))
            i += 1
            continue
        if ch == "$":
            if source.startswith("$(", i):
                inner, end = _scan_call(source, i)
                name, args = _parse_call_inner(inner)
                line = _line_of(source, i)
                tokens.append(
                    Call(
                        name=name,
                        args=args,
                        line=line,
                        column=_column_of(source, i),
                    )
                )
                i = end
                continue
            j = i + 1
            if j < n and source[j] == "{":
                close = source.find("}", j)
                if close == -1:
                    raise HtvlSyntaxError(
                        "unbalanced '${': missing closing '}'",
                        line=_line_of(source, i),
                        column=_column_of(source, i),
                    )
                spec = source[j + 1 : close]
                name = spec[:-3] if spec.endswith("[@]") else spec
                tokens.append(ArrayVar(name))
                i = close + 1
                continue
            k = j
            # Names must start with a letter or underscore: "$5" and friends
            # stay literal text.
            if k < n and (source[k].isalpha() or source[k] == "_"):
                while k < n and (source[k].isalnum() or source[k] == "_"):
                    k += 1
                tokens.append(Var(source[j:k]))
                i = k
                continue
            # A lone '$' that starts no construct is literal text.
            tokens.append(Text("$"))
            i += 1
            continue
        # Literal text run: consume up to the next '$' or newline.
        start = i
        while i < n and source[i] not in ("$", "\n"):
            i += 1
        tokens.append(Text(source[start:i]))
    return tokens


def _parse_call_inner(inner: str) -> Tuple[str, List]:
    """Split call arguments and recursively parse nested ``$(...)`` calls."""
    raw_args = split_args(inner)
    if not raw_args:
        raise HtvlSyntaxError("empty '$(...)': a tag name is required")
    name = unquote(raw_args[0])
    args: List = []
    for raw in raw_args[1:]:
        if raw.startswith("$(") and raw.endswith(")"):
            nested_inner, _ = _scan_call(raw, 0)
            nested_name, nested_args = _parse_call_inner(nested_inner)
            args.append(Call(name=nested_name, args=nested_args))
        else:
            args.append(unquote(raw))
    return name, args

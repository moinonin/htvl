"""Structural balance checking - the two error codes the compiler cannot see.

Recon (docs/recon.md Q2) established that HTVL never validates tag balance:
``$_video`` with no open ``video`` is silently emitted as ``</video>``, and an
unclosed ``$(div 'x')`` compiles to an unclosed ``<div>``. The project's own
2020 example carries exactly that bug (legacy/index.htvl:15).

This module produces the ``UNCLOSED_TAG`` and ``UNEXPECTED_CLOSE`` codes the
oracle promises. It walks the compiler's own parse tree
(``htvl.parser.parse``) rather than scanning text: a ``$(tag ...)`` inside a
quoted argument, or a ``$_div`` inside prose, is *text*, not a construct, and
the parser knows the difference. A regex scan does not - it once reported a
false ``UNCLOSED_TAG`` for ``$(p '' '' 'updated: $(span '12:00')' '')``
(D23).

Containers can be opened two ways, and both are tracked:

* ``$(div 'x')``        - a tag call (closed with ``$_div``)
* ``$head`` / ``$body`` - a built-in variable (closed with ``$_head`` / ...)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

from htvl.elements import ELEMENTS
from htvl.nodes import Call, Line, Var
from htvl.parser import parse

# Tags whose call opens a container that must be closed with $_tag. Derived
# from docs/grammar.md: every other tag renders a complete element or is void.
CONTAINER_TAGS = frozenset(
    {
        "div",
        "a",
        "p",
        "span",
        "nav",
        "ul",
        "li",
        "footer",
        "form",
        "btn",
        "section",
        "nav-a",
        "svgSimple",
    }
)

# Variables that open a container closed by $_name. The document skeleton plus
# the standalone opening tags. Deliberately explicit: $br is excluded because
# <br> is void (its $_br closer is legacy cruft).
VAR_CONTAINERS = frozenset(
    {"head", "body", "htvl", "p", "ul", "div", "svg", "strong"}
)

# Closing tokens that do not map 1:1 to the opening tag name.
_CLOSER_ALIASES: Dict[str, Tuple[str, ...]] = {
    "_a": ("a", "nav-a"),  # both close with $_a
    "_svg": ("svgSimple",),  # $_svg closes svgSimple
}


@dataclass(frozen=True)
class Imbalance:
    """One balance problem, located to the line that must be repaired."""

    kind: str  # "UNCLOSED_TAG" | "UNEXPECTED_CLOSE"
    line: int
    tag: str


def _tags_for_closer(closer: str) -> Tuple[str, ...]:
    if closer in _CLOSER_ALIASES:
        return _CLOSER_ALIASES[closer]
    return (closer[1:],) if closer.startswith("_") else (closer,)


def find_imbalances(source: str) -> List[Imbalance]:
    """Scan the parse tree for unbalanced container opens/closes.

    Tokens arrive in document order, so ``$(a 'x')$_a`` on one line balances
    correctly and constructs inside quoted text are ignored. Problems are
    returned ordered by line: the earliest repairable thing first.
    """
    stacks: Dict[str, List[int]] = {}  # tag -> open line numbers
    problems: List[Imbalance] = []

    for line in _parse(source):
        for token in line.tokens:
            if isinstance(token, Call) and token.name in CONTAINER_TAGS:
                stacks.setdefault(token.name, []).append(line.lineno)
            elif isinstance(token, Var) and token.name.startswith("_"):
                for tag in _tags_for_closer(token.name):
                    stack = stacks.get(tag)
                    if stack:
                        stack.pop()  # most recent open wins
                        break
                else:
                    problems.append(
                        Imbalance(
                            "UNEXPECTED_CLOSE", line.lineno, token.name[1:]
                        )
                    )
            elif isinstance(token, Var) and token.name in VAR_CONTAINERS:
                stacks.setdefault(token.name, []).append(line.lineno)

    for tag, stack in stacks.items():
        for lineno in stack:
            problems.append(Imbalance("UNCLOSED_TAG", lineno, tag))

    return sorted(problems, key=lambda problem: (problem.line, problem.tag))


def _parse(source: str) -> List[Line]:
    """Parse, or return nothing: unparseable source is the compile path's
    problem, and the oracle does not run balance analysis on it (D11)."""
    try:
        return parse(source).lines
    except Exception:
        return []


def known_tags() -> Tuple[str, ...]:
    """Every tag name the compiler accepts, sorted."""
    return tuple(sorted(ELEMENTS))

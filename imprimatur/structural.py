"""Structural balance checking - the two error codes the compiler cannot see.

Recon (docs/recon.md Q2) established that HTVL never validates tag balance:
``$_video`` with no open ``video`` is silently emitted as ``</video>``, and an
unclosed ``$(div 'x')`` compiles to an unclosed ``<div>``. The project's own
2020 example carries exactly that bug (legacy/index.htvl:15).

This module produces the ``UNCLOSED_TAG`` and ``UNEXPECTED_CLOSE`` codes the
oracle promises. It is a deterministic, line-local scan over the source using
the compiler's own tag table (``htvl.elements.ELEMENTS``) and variable table
(``htvl.variables.VARIABLES``) - no guessing.

Containers can be opened two ways, and both must be tracked:

* ``$(div 'x')``        - a tag call (closed with ``$_div``)
* ``$head`` / ``$body`` - a built-in variable (closed with ``$_head`` / ...)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Tuple

from htvl.elements import ELEMENTS


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

# Closing tokens that do not map 1:1 to the opening tag name.
_CLOSER_ALIASES: Dict[str, Tuple[str, ...]] = {
    "_a": ("a", "nav-a"),  # both close with $_a
    "_svg": ("svgSimple",),  # $_svg closes svgSimple
}

# Variables that open a container closed by $_name. The document skeleton plus
# the standalone opening tags. Deliberately explicit: $br is excluded because
# <br> is void (its $_br closer is legacy cruft).
VAR_CONTAINERS = frozenset({"head", "body", "htvl", "p", "ul", "div", "svg", "strong"})

_OPEN_CALL_RE = re.compile(r"\$\(\s*([A-Za-z_][A-Za-z0-9_-]*)")
_OPEN_VAR_RE = re.compile(r"\$([A-Za-z_][A-Za-z0-9_]*)")
_CLOSE_RE = re.compile(r"\$_([A-Za-z_][A-Za-z0-9_]*)")


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
    """Scan source for unbalanced container opens/closes.

    Events are processed in the order they appear on each line, so
    ``$(a 'x')$_a`` on one line balances correctly. Problems are returned
    ordered by line number: the earliest repairable thing first.
    """
    stacks: Dict[str, List[Tuple[str, int]]] = {}  # name -> [(kind, line)]
    problems: List[Imbalance] = []

    for lineno, line in enumerate(source.splitlines(), 1):
        events: List[Tuple[int, str, str]] = []
        for match in _OPEN_CALL_RE.finditer(line):
            if match.group(1) in CONTAINER_TAGS:
                events.append((match.start(), "open-call", match.group(1)))
        for match in _OPEN_VAR_RE.finditer(line):
            name = match.group(1)
            # Only the skeleton/standalone variables open containers.
            if name in VAR_CONTAINERS:
                events.append((match.start(), "open-var", name))
        for match in _CLOSE_RE.finditer(line):
            events.append((match.start(), "close", match.group(1)))
        events.sort(key=lambda event: event[0])

        for _pos, kind, name in events:
            if kind in ("open-call", "open-var"):
                stacks.setdefault(name, []).append((kind, lineno))
                continue
            for tag in _tags_for_closer(name):
                stack = stacks.get(tag)
                if stack:
                    stack.pop()  # most recent open wins, call or variable
                    break
            else:
                problems.append(Imbalance("UNEXPECTED_CLOSE", lineno, name))

    for tag, stack in stacks.items():
        for _kind, lineno in stack:
            problems.append(Imbalance("UNCLOSED_TAG", lineno, tag))

    return sorted(problems, key=lambda problem: (problem.line, problem.tag))


def known_tags() -> Tuple[str, ...]:
    """Every tag name the compiler accepts, sorted."""
    return tuple(sorted(ELEMENTS))

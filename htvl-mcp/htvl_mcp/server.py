"""htvl-mcp - the agent server: the oracle in front of any agent.

stdio only. Two tools, two resources, one prompt. No filesystem writes, ever:
returning HTML (never writing it) keeps the server a pure function and closes
the indirect-prompt-injection hole ("compile this to ~/.ssh/authorized_keys").
Failures are results (ok=false with diagnostics), not protocol errors, so the
agent can repair instead of ending its turn.

All logic lives in imprimatur; this module is an adapter and stays small.
"""

from __future__ import annotations

import sys
from typing import Optional

from mcp.server.fastmcp import FastMCP

import imprimatur

mcp = FastMCP(
    "htvl",
    instructions=(
        "HTVL is a line-oriented HTML transpiler. Author documents with tag "
        "calls like $(h 1 '' '' 'Title' '') and compile them with "
        "check_htvl. One source line produces one output line, so a repair "
        "only ever touches a few lines."
    ),
)


@mcp.tool()
def check_htvl(source: str, modern: bool = True) -> dict:
    """Validate HTVL source.

    On success returns the compiled HTML; on failure returns structured
    diagnostics (code, line, snippet, hint) naming the line to repair.
    Never raises: invalid source is a result, not an error.
    """
    result = imprimatur.check(source, modern=modern)
    if not result.ok:
        signatures = imprimatur.tag_signatures()
        return {
            "ok": False,
            "diagnostics": [
                {
                    **diagnostic.as_dict(),
                    "hint": imprimatur.explain(diagnostic, signatures),
                }
                for diagnostic in result.diagnostics
            ],
        }
    return {"ok": True, "html": result.html}


@mcp.tool()
def list_tags() -> list:
    """Every tag signature and built-in variable the compiler accepts."""
    return imprimatur.tag_signatures() + imprimatur.variable_signatures()


@mcp.resource("htvl://grammar")
def grammar() -> str:
    """The HTVL grammar and its invariants."""
    return _SHIPPED_GRAMMAR


@mcp.resource("htvl://tags")
def tags() -> str:
    """Every tag signature and variable, generated from the compiler."""
    return imprimatur.grammar_reference()


@mcp.prompt()
def examples() -> str:
    """Few-shot pairs: intent -> HTVL -> HTML."""
    return _FEW_SHOT


# Shipped copies of the language reference, kept next to the server so the
# resource never depends on the working directory. tests/test_mcp.py asserts
# the generated resource equals the compiler's own output.
_SHIPPED_GRAMMAR = """\
HTVL grammar (summary)
======================

A document is plain text with three constructs:

  $(tag 'arg' ...)   a tag call. Arguments are quoted strings or bare words;
                     missing arguments become empty strings; calls nest.
  $name              a variable: $head, $_a, $meta, or a template include.
  $_name            an explicit closing tag: $_div, $_a.

Invariants
----------

* one source line produces exactly one output line - leading whitespace and
  blank lines survive into the output, so a repair is line-local;
* output is deterministic: same input, byte-identical HTML;
* a tag whose signature includes content renders a complete element; a
  container tag (div, a, p, span, nav, ul, li, footer, form, btn, section,
  nav-a, svgSimple) renders an open tag and waits for $_name;
* text is inserted verbatim in legacy mode; modern mode (the default here)
  omits empty attributes and HTML-escapes text and attribute values.

Common tags (see the htvl://tags resource for the complete, generated list)
-------------------------------------------------------------------------

  $(h level class id content style)
  $(div class id style)              close with $_div
  $(a class href content id target aria_pressed style role)
  $(p class id content style)        close with $_p
  $(img src alt style)               $(link rel type href integrity crossorigin)
  $(script src type content)         $(comment content)
"""

_FEW_SHOT = """\
Task: write a page with a heading and a paragraph.

HTVL:
$(div 'container')
  $(h 1 '' '' 'Hello HTVL' '')
  $(p '' '' 'This page was compiled by the HTVL compiler.' '')
  $_p
$_div

HTML:
<div class="container">
  <h1>Hello HTVL</h1>
  <p>This page was compiled by the HTVL compiler.
  </p>
</div>

Task: link out and close it on the same line.

HTVL:
$(a 'button' 'https://example.com' 'Example' '' '' '' '')$_a

HTML:
<a class="button" href="https://example.com">Example</a>

Task: a page skeleton.

HTVL:
$DOCTYPE_htvl
$htvl
$head
  $meta
$_head
$body
  $(h 1 '' '' 'Title' '')
$_body
$_htvl
"""


def main(argv: Optional[list] = None) -> int:
    """Run the server over stdio, or compile a fixture with --selftest."""
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--selftest" in argv:
        result = imprimatur.check(_SELFTEST_FIXTURE)
        print(f"ok={result.ok} diagnostics={len(result.diagnostics)}")
        print(result.html or "")
        return 0 if result.ok else 1
    mcp.run()
    return 0


_SELFTEST_FIXTURE = """\
$DOCTYPE_htvl
$htvl
$head
  $meta
$_head
$body
  $(h 1 '' '' 'htvl-mcp selftest' '')
$_body
$_htvl
"""


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

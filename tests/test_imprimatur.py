"""Imprimatur oracle tests.

Every error code has a test. Byte-for-byte parity with ``htvl check`` is
asserted against the real CLI. No test touches the network or needs an API
key.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

import imprimatur
from imprimatur import Code, Diagnostic, Result, check, explain

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))  # noqa: E402 - module under test


def _codes(result: Result):
    return [d.code for d in result.diagnostics]


def _first(result: Result) -> Diagnostic:
    assert result.diagnostics, "expected at least one diagnostic"
    return result.diagnostics[0]


# ---------------------------------------------------------------------------
# One test per code
# ---------------------------------------------------------------------------


def test_ok_returns_html_and_no_diagnostics():
    result = check("$(h 1 '' '' 'Hello' '')\n")
    assert result.ok is True
    assert result.html == "<h1>Hello</h1>\n\n"
    assert result.diagnostics == []
    assert result.elapsed_ms >= 0


def test_unknown_tag():
    result = check("$(dvi 'x')\n")
    assert result.ok is False
    assert _first(result).code is Code.UNKNOWN_TAG
    assert _first(result).line == 1
    assert _first(result).detail == "dvi"
    assert "dvi" in _first(result).snippet


def test_unknown_variable():
    result = check("$nope\n")
    assert result.ok is False
    assert _first(result).code is Code.UNKNOWN_VARIABLE
    assert _first(result).detail == "nope"


def test_bad_arg_count_reports_the_offending_line():
    source = "$(h 1 '' '' 'fine' '')\n$(div 'a' 'b' 'c' 'd')\n"
    result = check(source)
    assert result.ok is False
    diag = _first(result)
    assert diag.code is Code.BAD_ARG_COUNT
    assert diag.line == 2  # HtvlArityError does not carry .line; see D12


def test_unterminated_string():
    result = check("$(p 'unterminated\n")
    assert result.ok is False
    assert _first(result).code is Code.UNTERMINATED_STR
    assert _first(result).line == 1


def test_syntax_error():
    result = check("$()\n")
    assert result.ok is False
    assert _first(result).code is Code.SYNTAX


def test_unclosed_tag():
    result = check("$(div 'x')\n")
    assert result.ok is False
    diag = _first(result)
    assert diag.code is Code.UNCLOSED_TAG
    assert diag.line == 1
    assert diag.detail == "div"


def test_unexpected_close():
    result = check("$_a\n")
    assert result.ok is False
    diag = _first(result)
    assert diag.code is Code.UNEXPECTED_CLOSE
    assert diag.line == 1


def test_too_large():
    result = check("x" * (imprimatur.MAX_SOURCE + 1))
    assert result.ok is False
    assert _first(result).code is Code.TOO_LARGE
    assert _first(result).message.startswith("source is")


def test_timeout_on_the_guard_path():
    # Above IN_PROCESS_LIMIT the oracle compiles in a guarded child process;
    # a timeout far below the measured compile time must surface as TIMEOUT.
    source = "$(p '' '' 'guarded' '')\n" * (imprimatur.IN_PROCESS_LIMIT // 24 + 1)
    assert len(source) > imprimatur.IN_PROCESS_LIMIT
    result = check(source, timeout=0.001)
    assert result.ok is False
    assert _first(result).code is Code.TIMEOUT


def test_internal_on_runaway_nesting():
    result = check("$(link " * 5000 + "x" + ")" * 5000 + "\n")
    assert result.ok is False
    assert _first(result).code is Code.INTERNAL


# ---------------------------------------------------------------------------
# Golden parity with the CLI
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "source",
    [
        "$(h 1 '' '' 'Hello' '')\n",
        "$DOCTYPE_htvl\n$htvl\n$head\n  $meta\n$_head\n$body\n$_body\n$_htvl\n",
        "  $(div 'a')\n    $(p '' '' 'text' '')\n    $_p\n  $_div\n",
        "$(link stylesheet 'text/css' $(bsCdn '4.3.1'))\n",
        "Copyright &copy; 2026\n",
    ],
)
def test_golden_parity_with_cli(source, tmp_path):
    """imprimatur.check(modern=True).html == ``htvl check --modern`` byte for
    byte (the CLI has no stdin mode, so parity runs against a real file)."""
    path = tmp_path / "parity.htvl"
    path.write_text(source, encoding="utf-8")
    cli = subprocess.run(
        [sys.executable, "-m", "htvl", "check", str(path), "--modern"],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    assert cli.returncode == 0, cli.stderr
    result = check(source, modern=True)
    assert result.ok, result.diagnostics
    assert result.html == cli.stdout


def test_tags_resource_matches_htvl_list():
    """htvl://tags is generated from the compiler's tables; assert equality
    with the CLI rather than eyeballing it."""
    cli = subprocess.run(
        [sys.executable, "-m", "htvl", "list"],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    assert cli.returncode == 0
    assert imprimatur.grammar_reference() == cli.stdout


def test_tag_signatures_come_from_the_compiler():
    from htvl.elements import ELEMENTS

    assert imprimatur.tag_signatures() == [
        ELEMENTS[name].signature for name in sorted(ELEMENTS)
    ]


# ---------------------------------------------------------------------------
# The compiler's blind spot, demonstrated on the project's own history
# ---------------------------------------------------------------------------


def test_the_2020_examples_unclosed_span_is_caught():
    """legacy/index.htvl:15 opens a <span> that is never closed, and the
    2020 compiler shipped it. The oracle refuses it."""
    lines = (REPO_ROOT / "legacy" / "index.htvl").read_text(
        encoding="utf-8"
    ).splitlines(keepends=True)
    fragment = "".join(lines[11:16])  # navbar block, self-contained
    result = check(fragment)
    assert result.ok is False
    codes = {d.code for d in result.diagnostics}
    assert Code.UNCLOSED_TAG in codes
    span = next(d for d in result.diagnostics if d.detail == "span")
    assert span.line == 4  # the line $(span 'navbar-toggler-icon') sits on


def test_construct_inside_a_quoted_argument_is_not_a_construct():
    """D23: the scanner walks the parse tree, so a $(tag ...) that appears
    inside a quoted argument - or a $_div inside prose - is text, not a
    construct. A regex scan once reported a false UNCLOSED_TAG here."""
    source = "$(p '' '' 'updated at $(span '12:00') - see $_div docs' '')\n$_p\n"
    assert check(source).ok is True


def test_inline_close_on_one_line_balances():
    assert check("$(a 'x' './' 'Go' '' '' '' '')$_a\n").ok is True


def test_self_closing_tags_need_no_closer():
    assert check("$(h 1 '' '' 'Hi' '')\n$br\n").ok is True


def test_variable_opened_containers_balance():
    """$head/$body/$htvl open containers closed by $_head/$_body/$_htvl."""
    source = (
        "$DOCTYPE_htvl\n$htvl\n$head\n  $meta\n$_head\n$body\n$_body\n$_htvl\n"
    )
    result = check(source)
    assert result.ok, result.diagnostics


def test_variable_container_left_open_is_caught():
    result = check("$head\n  $meta\n")
    assert result.ok is False
    diag = next(d for d in result.diagnostics if d.detail == "head")
    assert diag.code is Code.UNCLOSED_TAG
    assert diag.line == 1


# ---------------------------------------------------------------------------
# Contract properties
# ---------------------------------------------------------------------------


NASTY_INPUTS = [
    "",
    "\n\n\n",
    "$",
    "$$",
    "${",
    "$(",
    "$()",
    "$(-)",
    "$(h)",
    "$(h 1)",
    "$(div 'x'" + " 'y'" * 50 + ")",
    "$_",
    "$__a",
    "$_A",
    "'quoted' $(br)",
    "$(br) $_br",
    "text with $(nested $(calls $(here 'x')))",
    "\t\t$(div 'x')\n\t$_div\n",
    "$(h 999 '' '' 'x' '')",
    "$(img)",
    "😃 $(p '' '' 'emoji' '')",
    "$(comment 'x\ny')",
]


@pytest.mark.parametrize("source", NASTY_INPUTS)
def test_never_raises(source):
    """Invalid source is a value, never an exception."""
    result = check(source)
    assert isinstance(result, Result)
    assert result.ok in (True, False)
    if not result.ok:
        assert result.diagnostics


def test_deterministic():
    source = "$(dvi 'x')\n$(div 'y')\n"
    first = check(source)
    second = check(source)
    assert first.ok == second.ok
    assert first.html == second.html
    assert [d.as_dict() for d in first.diagnostics] == [
        d.as_dict() for d in second.diagnostics
    ]


def test_no_filesystem_writes(tmp_path, monkeypatch):
    """check() is pure: it must not create or remove anything."""
    root = tmp_path / "sandbox"
    root.mkdir()
    (root / "input.htvl").write_text("$(div 'x')\n")
    before = {p for p in root.rglob("*")}
    monkeypatch.chdir(root)
    check("$(h 1 '' '' 'Hi' '')\n")
    check("$(dvi 'x')\n")
    assert {p for p in root.rglob("*")} == before


def test_result_is_json_serializable():
    result = check("$(dvi 'x')\n")
    payload = json.dumps(
        {
            "ok": result.ok,
            "diagnostics": [d.as_dict() for d in result.diagnostics],
        }
    )
    assert '"UNKNOWN_TAG"' in payload


# ---------------------------------------------------------------------------
# explain()
# ---------------------------------------------------------------------------


def test_explain_suggests_close_matches():
    diag = check("$(dvi 'x')\n").diagnostics[0]
    hint = explain(diag)
    assert "div" in hint
    assert hint.startswith("unknown tag 'dvi'")


def test_explain_names_the_closer_for_unclosed():
    diag = check("$(div 'x')\n").diagnostics[0]
    assert "$_div" in explain(diag)


def test_explain_shows_the_expected_signature():
    diag = check("$(div 'a' 'b' 'c' 'd')\n").diagnostics[0]
    assert "$(div class id style)" in explain(diag)


def test_explain_suggests_variables():
    diag = check("$meta2\n").diagnostics[0]
    hint = explain(diag)
    assert "$meta" in hint


def test_explain_is_total():
    for source in ("$(dvi 'x')", "$_a", "$(p 'x", "$()", "$nope"):
        diag = check(source + "\n").diagnostics[0]
        assert isinstance(explain(diag), str)

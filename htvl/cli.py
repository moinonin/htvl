"""Command line interface: ``htvl compile``, ``htvl check``, ``htvl new``..."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional

from . import __version__
from .elements import ELEMENTS
from .errors import HtvlError
from .project import compile_project, compile_source
from .templates import load_templates
from .variables import VARIABLES
from .watch import watch_project


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="htvl",
        description=(
            "HTVL - a tiny HTML transpiler. Write short tag calls like "
            "$(h 1 '' '' 'Hello' '') in .htvl files and compile them to HTML."
        ),
    )
    parser.add_argument(
        "--version", action="version", version=f"htvl {__version__}"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    compile_cmd = sub.add_parser(
        "compile", help="compile every .htvl/.cal file in a directory"
    )
    compile_cmd.add_argument(
        "path",
        nargs="?",
        default=".",
        help="project directory (default: current directory)",
    )
    compile_cmd.add_argument(
        "-o",
        "--out",
        default="public",
        help="output directory for generated HTML (default: public)",
    )
    compile_cmd.add_argument(
        "--modern",
        action="store_true",
        help=(
            "emit clean HTML: omit empty attributes, escape text and fix "
            "legacy cosmetic quirks (see docs/grammar.md)"
        ),
    )
    compile_cmd.add_argument(
        "-q", "--quiet", action="store_true", help="only report errors"
    )
    compile_cmd.add_argument(
        "-w",
        "--watch",
        action="store_true",
        help="keep running and recompile on every change (Ctrl-C to stop)",
    )

    check_cmd = sub.add_parser(
        "check", help="compile a single file and write the HTML to stdout"
    )
    check_cmd.add_argument("files", nargs="+", help=".htvl files to compile")
    check_cmd.add_argument(
        "--modern",
        action="store_true",
        help="emit clean HTML (see docs/grammar.md)",
    )

    new_cmd = sub.add_parser("new", help="scaffold a new HTVL project")
    new_cmd.add_argument("name", help="directory name for the new project")

    sub.add_parser("list", help="list every tag and built-in variable")
    return parser


def _cmd_compile(args: argparse.Namespace) -> int:
    root = Path(args.path).resolve()
    if not root.is_dir():
        print(f"htvl: error: '{args.path}' is not a directory", file=sys.stderr)
        return 1
    if args.watch:
        return _cmd_watch(args)
    result = compile_project(root, out_dir=args.out, modern=args.modern)
    if not args.quiet:
        for output in result.outputs:
            print(f"htvl: compiled {output.relative_to(root)}")
        if result.copied_assets:
            print(f"htvl: copied assets -> {result.copied_assets.relative_to(root)}")
        if args.modern:
            print("htvl: modern mode: clean, escaped HTML")
        print(f"htvl: {len(result.outputs)} file(s) compiled")
    return 0


def _cmd_watch(args: argparse.Namespace) -> int:
    root = Path(args.path).resolve()

    def say(line: str) -> None:
        print(f"htvl: {line}")

    try:
        watch_project(root, out_dir=args.out, modern=args.modern, printer=say)
    except KeyboardInterrupt:
        print("htvl: stopped")
    return 0


def _cmd_check(args: argparse.Namespace) -> int:
    for name in args.files:
        path = Path(name)
        templates = load_templates(path.parent / "templates")
        sys.stdout.write(
            compile_source(
                path.read_text(encoding="utf-8"),
                templates,
                modern=args.modern,
            )
        )
    return 0


_STARTER_INDEX = """\
$DOCTYPE_htvl
$htvl
$head
  $headtags
$_head
$body
  $(nav 'navbar navbar-expand-md bg-dark navbar-dark')
    $(a 'navbar-brand' './' 'Home' '' '' '' '')$_a
    $(ul 'navbar-nav mr-auto')
    $_ul
  $_nav

  $(div 'container')
    $(h 1 '' '' 'Hello HTVL' '')
    $(p '' '' 'This page was compiled from index.htvl by the HTVL compiler.' '')
    $_p
  $_div
$_body
$_htvl
"""

_STARTER_TEMPLATE = """\
$(title '' 'My HTVL page')
$meta
$(link 'stylesheet' 'text/css' './assets/style.css')
"""


def _cmd_new(args: argparse.Namespace) -> int:
    root = Path(args.name)
    if root.exists():
        print(f"htvl: error: '{root}' already exists", file=sys.stderr)
        return 1
    (root / "templates").mkdir(parents=True)
    (root / "assets").mkdir(parents=True)
    (root / "index.htvl").write_text(_STARTER_INDEX, encoding="utf-8")
    (root / "templates" / "headtags.htvl").write_text(
        _STARTER_TEMPLATE, encoding="utf-8"
    )
    (root / "assets" / "style.css").write_text(
        "body { font-family: system-ui, sans-serif; }\n", encoding="utf-8"
    )
    print(f"htvl: created project '{root}'")
    print(f"htvl: next: cd {root} && htvl compile")
    return 0


def _cmd_list(args: argparse.Namespace) -> int:
    print("Tags")
    print("----")
    for name in sorted(ELEMENTS):
        element = ELEMENTS[name]
        print(f"  {element.signature}")
    print()
    print("Variables")
    print("---------")
    for name in sorted(VARIABLES):
        value = VARIABLES[name].replace("\n", "\\n")
        if len(value) > 46:
            value = value[:43] + "..."
        print(f"  ${name} -> {value}")
    return 0


_COMMANDS = {
    "compile": _cmd_compile,
    "check": _cmd_check,
    "new": _cmd_new,
    "list": _cmd_list,
}


def main(argv: Optional[List[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    handler = _COMMANDS[args.command]
    try:
        return handler(args)
    except HtvlError as exc:
        print(f"htvl: error: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"htvl: error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())

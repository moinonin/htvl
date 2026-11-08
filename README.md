# HTVL — a tiny HTML transpiler

[![tests](https://github.com/moinonin/htvl/actions/workflows/tests.yml/badge.svg)](https://github.com/moinonin/htvl/actions/workflows/tests.yml)

Write short tag calls in `.htvl` files, get plain HTML out. No build step, no
dependencies, no framework — just a small, well-tested compiler you can read
in an afternoon.

```text
$(h 1 '' '' 'Hello HTVL' '')
```

compiles to

```html
<h1 class="" id="" style="">Hello HTVL</h1>
```

## Install

```bash
pip install .          # from a clone of this repository
```

or run it straight from the checkout with zero installation:

```bash
python3 -m htvl compile
```

Python 3.10+, standard library only.

## Quickstart

```bash
htvl new mysite        # scaffold: index.htvl, templates/, assets/
cd mysite
htvl compile           # writes public/index.html and copies assets/
```

A minimal project:

```text
mysite/
├── index.htvl
├── templates/
│   └── headtags.htvl
└── assets/
```

`index.htvl`:

```text
$DOCTYPE_htvl
$htvl
$head
  $headtags
$_head
$body
  $(nav 'navbar navbar-expand-md bg-dark navbar-dark')
    $(a 'navbar-brand' './' 'Home' '' '' '' '')$_a
    $(ul 'navbar-nav')
    $_ul
  $_nav

  $(div 'container')
    $(h 1 '' '' 'Hello HTVL' '')
    $(p '' '' 'This page was compiled by the HTVL compiler.' '')
    $_p
  $_div
$_body
$_htvl
```

`templates/headtags.htvl`:

```text
$(title '' 'My HTVL page')
$meta
```

Then `htvl compile` produces `public/index.html`.

## Commands

| Command | What it does |
| --- | --- |
| `htvl compile [path] [-o DIR] [--modern] [-w]` | Compile every `.htvl` file in `path` (default `.`) into `public/`; `.cal` files become CGI scripts in `cal/`; `assets/` is copied automatically. `--modern` emits clean, escaped HTML; `-w`/`--watch` keeps running and recompiles on change. |
| `htvl check FILE... [--modern]` | Compile a single file to stdout — great for scripting and debugging. |
| `htvl new NAME` | Scaffold a new project. |
| `htvl list` | Print every tag signature and built-in variable. |

### Legacy vs modern output

The default output is byte-identical to the original 2020 compiler (empty
attributes and all, guarded by `tests/test_golden.py`). For new projects, pass
`--modern` to get clean HTML: empty attributes omitted, text escaped, no
cosmetic quirks. Same source files, same line structure — only the rendering
changes:

```text
$(div 'container')     legacy: <div class="container" id="" style="">
                       modern: <div class="container">
```

### Watch mode

```bash
htvl compile --watch      # or: htvl compile -w
```

Compiles once, then keeps the output up to date as you edit:

```text
htvl: compiled public/index.html
htvl: copied assets -> public/assets
htvl: watching '/sites/mysite' (Ctrl-C to stop)
htvl: compiled public/index.html        <- you saved index.htvl
htvl: removed public/index.html         <- you deleted index.htvl
htvl: stopped
```

Edits are incremental: changing `index.htvl` recompiles that file, changing
anything in `templates/` rebuilds the project, changing `assets/` re-copies
it, and deleting a source removes its output. A broken edit (an unknown tag,
say) is reported but does not stop the watcher — fix the file and it picks up
where it left off. No dependencies: it polls the filesystem a few times a
second.

Errors include the file, line and column, e.g.
`htvl: error: unknown tag 'dvi' (line 12). Run 'htvl list' to see every available tag.`

## The language

* `$(tag 'arg' ...)` — tag calls, arguments are quoted strings (or bare words),
  nesting allowed: `$(link stylesheet 'text/css' $(bsCdn '4.3.1'))`
* `$name` — variables such as `$head`, `$_a`, `$meta`, and your own templates
  (`$headtags`)
* `$_name` — explicit closing tags
* One source line = one output line; your indentation is your HTML's
  indentation.

The full reference — every tag signature, the variables, templates, CGI
support — is in [docs/grammar.md](https://github.com/moinonin/htvl/blob/master/docs/grammar.md).

### Editor support

* **VS Code** — the extension lives in [`editors/vscode/`](https://github.com/moinonin/htvl/blob/master/editors/vscode):
  ```bash
  cd editors/vscode
  npx @vscode/vsce package && code --install-extension htvl-*.vsix
  ```
  It highlights tag calls, variables (`$head`, `$_a`), quoted/bare arguments,
  nested calls and HTML comments, and it is set up for comment blocks and
  indentation-based folding.
* **Anything Pygments-based** (Sphinx, MkDocs, code renderers) — a Pygments
  lexer ships in [`extras/pygments_htvl.py`](https://github.com/moinonin/htvl/blob/master/extras/pygments_htvl.py):
  ```python
  from pygments.lexers import LEXERS
  LEXERS["htvl"] = (
      "pygments_htvl", "HTVL", ("htvl",), ("*.htvl", "*.cal"), ()
  )
  ```
  Both are covered by the test suite.

### Try it in the browser

[`playground/`](https://github.com/moinonin/htvl/blob/master/playground) is a fully static, server-free playground: the
page loads the **real Python compiler** compiled to WebAssembly with
[Pyodide](https://pyodide.org) and compiles as you type, with a legacy/modern
toggle. Open it from any static host:

```bash
python3 -m http.server 8000 --directory playground
```

## Using it as a library

```python
from htvl import compile_source

html = compile_source("$(h 1 '' '' 'Hello' ')\n")
```

## About this repository

HTVL started in 2020 as a two-line obfuscated bash script that generated HTML
by `eval`-ing heredocs, complete with a 90-day trial timer that required
`sudo`. That prototype is preserved untouched in [`legacy/`](https://github.com/moinonin/htvl/blob/master/legacy) — see
[`legacy/README.original.md`](https://github.com/moinonin/htvl/blob/master/legacy/README.original.md) for the original
documentation — together with a
[de-obfuscated copy of its compiler](https://github.com/moinonin/htvl/blob/master/docs/recovered-legacy-compiler.sh) that
serves as the authoritative definition of the grammar.

This repository is the second act: the same language, reimplemented in Python
as a readable, testable, dependency-free compiler:

* `htvl/lexer.py` → `htvl/parser.py` → `htvl/elements.py` →
  `htvl/emitter.py` — a classic tokenize / parse / render pipeline you can
  actually read
* the trial timer, the `sudo` asset copy and the silent failure modes are
  gone; errors now name the line and column
* `tests/test_golden.py` proves the port reproduces the original 2020 output
  **byte for byte**, so existing `.htvl` files and `templates/*.sh` keep
  working unchanged

## Imprimatur: machine-written HTML, graded

On top of the compiler sit three more packages, built to make
machine-generated documents *provably* well-formed:

| Package | Its one job |
| --- | --- |
| [`imprimatur/`](https://github.com/moinonin/htvl/blob/master/imprimatur) | The oracle: HTVL source in, coded, line-local diagnostics out. Pure function, stdlib only, capped input. |
| [`htvl-mcp/`](https://github.com/moinonin/htvl/blob/master/htvl-mcp) | The oracle in front of any coding agent: two MCP tools over stdio, no filesystem writes. |
| [`imprimatur-eval/`](https://github.com/moinonin/htvl/blob/master/imprimatur-eval) | The measurement: rejection-sampling datasets, repair traces, and the A/B harness that produces `RESULTS.md`. |

The premise — that a compile-check-repair loop beats single-shot generation —
is stated as a falsifiable claim and tested against a real local model under a
pre-registered protocol ([`docs/EXPERIMENT.md`](https://github.com/moinonin/htvl/blob/master/docs/EXPERIMENT.md)). The
decision number is tokens per correct document. See
[`RESULTS.md`](https://github.com/moinonin/htvl/blob/master/RESULTS.md) for the
outcome — including, if that is what the data says, the negative one.

Stage 0's reconnaissance ([`docs/recon.md`](https://github.com/moinonin/htvl/blob/master/docs/recon.md)) and every
recon-driven deviation ([`docs/decisions.md`](https://github.com/moinonin/htvl/blob/master/docs/decisions.md)) are
kept in the tree.

### Development

```bash
pip install -e ".[dev]"   # compiler + pytest + pygments (for the lexer tests)
python3 -m pytest         # 136 tests, including the golden test
```

CI runs the suite on every push and PR: all supported Python versions
(3.10–3.13) on Linux, spot-checks on macOS and Windows, and a packaging job
that builds a wheel, installs it, and compiles a scaffolded project
(`.github/workflows/tests.yml`).

Release notes for v0.2.0 are in [docs/releases/v0.2.0.md](https://github.com/moinonin/htvl/blob/master/docs/releases/v0.2.0.md).

### Roadmap

* an opt-in `--modern` mode that fixes the documented `[legacy]` output
  quirks (no empty attributes, proper escaping, real `role` support)
* ~~watch mode and incremental builds~~ — **done in v0.2.0** (`htvl compile --watch`)
* ~~syntax highlighting for `.htvl` files~~ — **done in v0.2.0** (VS Code
  extension in `editors/vscode/`, Pygments lexer in `extras/`)
* ~~a playground on the documentation site~~ — **done in v0.2.0**
  (`playground/`, the real compiler running in-browser via Pyodide)

## License

MIT — see [LICENSE](https://github.com/moinonin/htvl/blob/master/LICENSE).

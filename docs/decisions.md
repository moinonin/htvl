# Decisions

Running log of every point where evidence (mostly Stage 0 recon) contradicted
or amended the build brief, and what was done instead.

### D1 — Intake contradiction detector fired on false positives

**Brief:** use the githeri pipeline for the spec.
**Found:** `githeri_intake_validate` blocked the session with five
"contradictions". All five compared one *component sentence* from the
architecture section against the full objective statement — component vs.
whole, not actually conflicting (e.g. "imprimatur/ - the oracle: ..." vs.
"Build Imprimatur: an oracle layer + agent server + evaluation harness ...").
No real ambiguity existed.
**Did:** answered the one genuine question (PROB-MOTIVATION), confirmed no
pending questions remained, and compiled the spec via
`githeri_intake_submit(force=true)` — the documented escape hatch. Spec id:
`build-imprimatur-oracle-mcp-eval`. Readiness score 0.912 was not the blocker;
the lexical contradiction detector was.

### D2 — The compiled spec's blueprint is a lossy flattening

**Brief:** follow the brief's component specifications (dataclasses,
`Code` StrEnum with nine codes, snippet, `explain`, `tag_signatures`).
**Found:** githeri compiled the architecture into a 4-goal spec whose L2
blueprint is a simplified sketch: a single `error_code` string, no snippet, no
`explain`, no `tag_signatures`, `SYNTAX` as a catch-all.
**Did:** implemented the brief's specification, which is strictly richer. The
compiled goals (inspect existing compiler, create oracle, create server,
verify with pytest) map onto the stages; the blueprint text was treated as a
hint, not a contract.

### D3 — `UNCLOSED_TAG` / `UNEXPECTED_CLOSE` do not exist in the compiler

**Brief:** nine stable codes, one test each.
**Found (recon Q2):** the compiler never validates tag balance — `$_video`
with no open `video` silently emits `</video>`, and an unclosed `$(div 'x')`
is accepted. The project's own 2020 example has one such bug (unclosed
`<span>` at `legacy/index.htvl:15`).
**Did:** the oracle adds a deterministic structural balance check
(`imprimatur/structural.py`) that produces exactly those two codes, tracking
`$(_tag)` opens against `$_tag` closes per container tag. It lives inside
`imprimatur/` (no business logic outside it) and reuses the compiler's own
grammar tables for the tag set. The legacy-example bug is a test case: it
proves the oracle catches what the compiler waved through.

### D4 — `MAX_SOURCE` lowered from 1,000,000 to 256,000

**Brief (sketch):** `MAX_SOURCE = 1_000_000`, `TIMEOUT_S = 5.0`.
**Found (recon Q6):** a 1 MB document takes ~3.8–9 s to compile depending on
shape; at ~110 bytes/ms worst case it would breach the 5 s timeout. The two
constants as specified are mutually unsatisfiable on slower machines.
**Did:** `MAX_SOURCE = 256_000` (worst case ~0.5 s, ~10x margin under the
timeout). The cap still allows ~7,500-line documents. The constants are
module-level and overridable per call, so the policy stays explicit.

### D5 — `TIMEOUT` needs a subprocess guard for large inputs

**Brief:** enforce a timeout on untrusted input.
**Found:** a CPU-bound pure-Python compile cannot be interrupted in-process
(no signal in non-main threads; a thread cannot be killed).
**Did:** inputs up to `IN_PROCESS_LIMIT` (64 KB, ~30x faster than the timeout
at measured throughput) compile in-process — the repair loop's hot path.
Larger inputs run through a subprocess guard that enforces the wall-clock
timeout and maps `TimeoutExpired` to `Code.TIMEOUT`. Small inputs never pay
the subprocess cost; large inputs get a real, enforceable bound.

### D6 — Nested-call errors report line 0

**Brief (recon Q5):** failures are "named by line".
**Found:** `htvl/lexer.py::_parse_call_inner` builds nested `Call` nodes
without positions, so an unknown tag inside `$(link ... $(dvi 'x'))` reports
`line 0`, not the call site.
**Did:** the oracle propagates whatever the compiler reports (line 0) rather
than fabricating a position. Proposed upstream patch (NOT applied — the
compiler is not forked):

```diff
--- a/htvl/lexer.py
+++ b/htvl/lexer.py
@@ def _parse_call_inner(inner: str) -> Tuple[str, List]:
     for raw in raw_args[1:]:
         if raw.startswith("$(") and raw.endswith(")"):
             nested_inner, _ = _scan_call(raw, 0)
             nested_name, nested_args = _parse_call_inner(nested_inner)
-            args.append(Call(name=nested_name, args=nested_args))
+            args.append(Call(name=nested_name, args=nested_args,
+                             line=line, column=column))
```

where `line`/`column` are threaded into `_parse_call_inner` from
`tokenize`. With that patch, nested diagnostics carry the call-site line and
the oracle needs no change.

### D7 — "Zero runtime dependencies" read as stdlib + the MCP SDK

**Brief:** zero runtime dependencies in all three packages; the server sketch
imports `mcp.server.fastmcp`.
**Found:** an MCP server cannot be written without the MCP SDK; the brief's
own sketch contradicts a literal reading.
**Did:** `imprimatur` and `imprimatur-eval` are pure stdlib. `htvl-mcp`
depends on exactly one third-party package, the official `mcp` SDK, plus
stdlib. Every dependency is declared, and the install is a single
`uvx htvl-mcp` / `pip install .`.

### D8 — CLI parity needs files, not stdin

**Brief:** golden parity with `htvl check --modern`.
**Found (recon Q2):** `htvl check` has no stdin mode (`-` fails with
`[Errno 2]`).
**Did:** the parity test writes a temp file and runs the real CLI against it,
then compares stdout with `imprimatur.check(...).html` byte for byte. No
compiler change.

### D9 — Two additive extensions to the oracle contract

**Brief:** the `Code` enum and `Diagnostic` dataclass as sketched.
**Found:** (a) the compiler raises `HtvlUnknownVariableError` (`$nope`) — a
real, distinct failure class with no code in the enum; (b) `explain()` needs
the offending token, and the sketch's `Diagnostic` carries only prose.
**Did:** added `Code.UNKNOWN_VARIABLE` and an optional `detail` field (the
tag/variable name). Both are additive: the nine brief codes keep their names
and meanings, and no consumer that only reads `code`/`line` is affected.

### D10 — `Code` is `str, Enum`, not `StrEnum`

**Brief (sketch):** `class Code(StrEnum)`.
**Found:** `StrEnum` is Python 3.11+; the package floor is 3.10 (the repo's
`requires-python`, and the CI matrix).
**Did:** `class Code(str, Enum)` — same string behaviour, 3.10-compatible.

### D11 — Structural analysis runs only on parseable source

**Brief:** one error at a time for the repair loop.
**Found:** running the balance scan on unparseable input produces noise — e.g.
`$(p 'x` (an unterminated string) also looked like an unclosed `p`, and the
alphabetically-earlier `UNCLOSED_TAG` masked the actionable
`UNTERMINATED_STR`.
**Did:** when the compile step reports any diagnostic, that diagnostic is
returned and structural analysis is skipped; balance checking runs only when
the source parses. The repair loop converges one real error at a time.

### D12 — `HtvlArityError` never sets `.line`

**Brief (recon Q5):** failures are named by line.
**Found:** `HtvlArityError.__init__` formats the line into its message but
does not assign `self.line`, so `.line` raises `AttributeError` — the only
`HtvlError` without it. The oracle needs the position.
**Did:** the oracle re-derives it from the compiler's own parse tree
(`htvl.parser.parse`) by locating the over-long call — no prose scraping.
Proposed upstream patch (NOT applied; the compiler is not forked):

```diff
--- a/htvl/errors.py
+++ b/htvl/errors.py
@@ class HtvlArityError(HtvlError):
         self.expected = expected
         self.got = got
+        self.line = line
```

### D13 — Balance scanning tracks variables as well as tag calls

**Found while testing the oracle:** the first structural version flagged
`$head`/`$body`/`$htvl` documents with three `UNEXPECTED_CLOSE` errors,
because containers opened by *variables* (`$head`, closed by `$_head`) were
invisible to a scanner that only knew `$(tag ...)` calls.
**Did:** the scanner tracks both forms, with an explicit `VAR_CONTAINERS` set
(`head`, `body`, `htvl`, `p`, `ul`, `div`, `svg`, `strong`). `$br` is excluded:
`<br>` is void and its `$_br` closer is legacy cruft.

### D14 — `check()` validates one source string; templates are out of scope

**Found:** the 2020 example references `$headtags` (a project template), so
checking it as a bare string reports `UNKNOWN_VARIABLE: headtags`.
**Did:** accepted as correct behaviour — an agent generating a document has no
project templates, and the diagnostic's hint ("define it in templates/") is
actionable. Self-contained documents are the agent-facing contract.

### D15 — `mcp` pinned to the v1 line

**Found:** the MCP ecosystem moved to 2.x, which renamed `FastMCP` to
`MCPServer` (`from mcp.server.mcpserver import MCPServer`) and changed other
APIs. The brief's server sketch targets v1.
**Did:** `mcp>=1.2,<2` in `htvl-mcp` (verified against 1.30.0). The server is
a thin adapter, so a future v2 migration is a contained change: swap the
import, keep the two tools and two resources. Nothing else in the repository
touches the SDK.

### D16 — The three packages form a uv workspace

**Brief:** `uvx htvl-mcp` installable; three packages in one repo.
**Found:** `htvl-mcp` depends on `imprimatur`, which depends on `htvl-lang`,
and none are on PyPI yet. Relative `tool.uv.sources` paths resolve against the
workspace root, not the member directory, so `path = "../imprimatur"` fails.
**Did:** declared `[tool.uv.workspace] members = ["imprimatur", "htvl-mcp"]` at
the repo root and `{ workspace = true }` sources in the members. Verified:
`uv tool run --from ./htvl-mcp htvl-mcp --selftest` builds all three and runs.

### D17 — `imprimatur` maps its package onto its own directory

**Found:** `imprimatur/` is simultaneously the project root (holds
`pyproject.toml`) and the package (holds `__init__.py`), so the default
setuptools layout fails with "package directory 'imprimatur' does not exist".
**Did:** `[tool.setuptools.package-dir] imprimatur = "."`. Verified by
building the wheel through uv. (The alternative — `imprimatur/imprimatur/` —
would break the repository's flat `import imprimatur` used everywhere.)

### D18 — Verified over the real protocol, not just in-process

**Brief:** contract and adversarial tests.
**Did:** beyond `tests/test_mcp.py` (which drives FastMCP's dispatch in
process), the server was exercised as a real subprocess: a stdio JSON-RPC
session ran `initialize`, `tools/list` (exactly `check_htvl` and `list_tags`),
`resources/read htvl://tags`, and `tools/call` on both a broken source
(`ok=false`, `UNKNOWN_TAG`) and a valid one (`ok=true`, HTML). The adversarial
prompt-injection case is asserted in the test suite: the text compiles and no
file appears.

### D19 — The stub must sometimes compile, or R is undefined

**Brief (sketch):** a deterministic stub so CI needs no keys.
**Found while running the harness:** the first stub injected a defect into
*every* document, so the control arm's compile rate was 0 and
`C_control = tokens / 0` was undefined — the primary metric R could not be
computed at all, and the run printed `C=None R=None`.
**Did:** the stub now emits a clean document for ~40% of intents (deterministic
by intent hash). The harness keeps its honest handling of the degenerate case
(`tokens_per_correct_doc: null`, verdict INCONCLUSIVE) for real models that
genuinely never compile. This is a stub design fact, not a metric fix: with a
0% baseline the experiment's decision rule has nothing to divide.

### D20 — A deterministic stub cannot exercise Arm C meaningfully

**Found:** the ablation arm (best-of-k) draws k *identical* samples from a
deterministic stub, so its compile rate equals the single-sample rate — it
cannot distinguish "selection" from "repair" (protocol RQ4).
**Did:** Arm C still runs and is reported (the plumbing is verified), and the
report states plainly that the ablation contrast is only meaningful with a
stochastic model. Documented in `imprimatur-eval/README.md`.

### D21 — `python -m imprimatur_eval` needs the path or an install

**Brief (working commands):** `python -m imprimatur_eval build ...` from the
repository root.
**Found:** the package lives in `imprimatur-eval/` (hyphenated, per the
brief's layout), so Python cannot import it from the root by default.
**Did:** the pytest config adds `imprimatur-eval` and `htvl-mcp` to
`pythonpath`, so the whole suite runs from a bare checkout; the README notes
`pip install -e ./imprimatur-eval` (or `uv sync`) for the documented
`python -m` commands and the `imprimatur-eval` console script.

### D22 — `python -m imprimatur_eval` argument dest

**Found:** argparse `--in` is fine, but the dest cannot be `args.in` — `in`
is a Python keyword, so `args.in` is a `SyntaxError`.
**Did:** `dest="in_path"` with `args.in_path`.

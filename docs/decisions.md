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

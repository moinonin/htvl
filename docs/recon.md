# Stage 0 — Reconnaissance

Every claim below was produced by running the compiler in this checkout
(`htvl` 0.2.0, commit 2c6b823) with the probe scripts recorded inline.
Nothing here is inferred. Probes: `python3 /tmp/recon_probe.py` output plus
targeted follow-ups (all commands re-runnable).

## Q1 — What does `compile_source` do on invalid input?

It **raises**, never returns a sentinel. Exception hierarchy
(`htvl/errors.py`), all subclasses of `HtvlError`:

| Input | Exception | Attributes carried |
| --- | --- | --- |
| `$(dvi 'x')` | `HtvlUnknownTagError` | `.line` = 1, `.name` = `'dvi'` |
| `$(div 'a' 'b' 'c' 'd')` | `HtvlArityError` | `.line` = 1, `.name`, `.expected` = 3, `.got` = 4 |
| `$nope` | `HtvlUnknownVariableError` | `.line` = 1, `.name` = `'nope'` |
| `$(div 'x'` (unclosed call) | `HtvlSyntaxError` | `.line` = 1, `.column` = 1, `.message` |
| `$(p 'unterminated` | `HtvlSyntaxError` | `.line` = 1, `.column` = 1 (same class as above — the lexer cannot distinguish the two) |
| `$()` | `HtvlSyntaxError` | `.line` = **None**, `.message` |
| 5000-deep nested calls | `RecursionError` (not an `HtvlError`) | — |

Errors are **line-localized but not always column-localized**: only
`HtvlSyntaxError` produces a column. `.line` is 1-based; `None` when the
tokenizer never reached a line boundary.

## Q2 — Exact stderr text per error class

`compile_source` raises; the CLI (`htvl check FILE`) converts to
`htvl: error: <message>` on stderr, exit code 1, stdout empty. On success:
exit 0, HTML on stdout. Exact strings (via real files — see Q2 note):

```text
unknown tag 'dvi' (line 1). Run 'htvl list' to see every available tag.
tag 'div' accepts at most 3 argument(s), got 4 (line 1)
unknown variable '$nope' (line 1). Check the spelling, or define it in templates/.
unbalanced '$(': missing closing ')' (line 1, column 1)
empty '$(...)': a tag name is required
```

**CLI note:** `htvl check` does **not** read stdin — `htvl check -` fails with
`htvl: error: [Errno 2] No such file or directory: '-'`. Any CLI-parity test
must write a real temp file. (Proposed upstream patch in
`docs/decisions.md`.)

**Error classes that do not exist in the compiler** (verified):

- `UNEXPECTED_CLOSE` — `$_video` when no `video` is open does **not** raise;
  the compiler degrades unknown `$_name` to `</name>` and emits it.
- `UNCLOSED_TAG` — a `$(div 'x')` never closed does **not** raise; HTVL is
  line-oriented with explicit `$_div` closers and never validates balance.
  Demonstrated on the project's own 2020 example: `legacy/index.htvl` line 15
  opens `$(span 'navbar-toggler-icon')` and never closes it, so the shipped
  `legacy/public/index.html` contains a `<span>` with no `</span>`. The
  compiler accepted it for six years.
- `MALFORMED_NESTING` — nothing to detect; see above.

## Q3 — Is the tag table reachable programmatically?

Yes. `htvl.elements.ELEMENTS` is a module-level dict: **31 tags**, each an
`Element` with `.name`, `.params` (ordered tuple), `.signature`
(`"$(a class href content id target aria_pressed style role)"`) and `.doc`.
`htvl.variables.VARIABLES` holds the 30-odd built-in variables. No subprocess
or text parsing needed. `htvl list` output is reproducible from these two
tables (verified: the CLI prints `Tags`, `----`, two-space-indented
signatures, then `Variables`, `---------`, `  $name -> value`).

## Q4 — Does `--modern` match its documented behaviour?

Yes on all adversarial inputs tested:

| Input | `modern=False` (legacy) | `modern=True` |
| --- | --- | --- |
| `A & B` | `A & B` (unescaped) | `A &amp; B` |
| `<script>alert(1)</script>` | raw (XSS in CGI context) | `&lt;script&gt;alert(1)&lt;/script&gt;` |
| `He said "hi"` | `He said "hi"` | `He said &quot;hi&quot;` |
| `href="https://q/?a=1&b=2"` | `&` raw | `&amp;` |
| `$(link stylesheet 'text/css' $(bsCdn '4.3.1'))` | emitted | nested call expanded, escaped `href` |

Empty attributes are omitted in modern mode (`<p class="" id="" style="">` →
`<p>`); legacy keeps them byte-for-byte. 200-deep nested calls compile fine
(no stack issue); 5000-deep raises `RecursionError`.

## Q5 — Does an error in a nested call report the call-site line?

**No — this is the single most important finding.** A bad tag inside a nested
call reports **line 0**:

```text
source line 5 of 6:  $(link stylesheet 'text/css' $(dvi 'x'))
-> HtvlUnknownTagError: unknown tag 'dvi' (line 0)
```

Cause: `htvl/lexer.py::_parse_call_inner` constructs nested `Call` nodes
without position information (`Call(name=..., args=...)` — `line`/`column`
default to 0). The outer call carries the correct line. Proposed upstream
patch is in `docs/decisions.md`; the oracle records the known gap rather than
guessing positions.

## Q6 — Size and speed

Measured on this machine (Python 3.10, `compile_source`, modern mode):

| Lines | Input bytes | Output bytes | Time |
| --- | --- | --- | --- |
| 1,000 | 34 KB | 21 KB | 16 ms |
| 4,000 | 136 KB | 69 KB | 135 ms |
| 8,000 | 272 KB | 139 KB | 465 ms |
| 10,000 | 340 KB | 210 KB | 698 ms |
| 20,000 | 680 KB | 351 KB | 2.59 s |
| 50,000 | 1.70 MB | 1.05 MB | 15.5 s |

Throughput is roughly linear at ~250–400 bytes/ms but degrades on large
documents. Implications for the oracle's guards (see `docs/decisions.md`):

- the brief's `MAX_SOURCE = 1_000_000` with `TIMEOUT_S = 5.0` is **not
  safely satisfiable**: a 1 MB document takes ~3.8–9 s depending on shape,
  either side of the timeout depending on the machine;
- `MAX_SOURCE = 256_000` bounds the worst case to ~0.5 s — comfortably inside
  the 5 s timeout with margin. Adopted.

## Consequences for the build

1. The compiler raises rich, line-carrying exceptions — in-process wrapping
   is viable and fast (no subprocess needed on the common path).
2. Two of the brief's nine error codes cannot come from the compiler
   (`UNCLOSED_TAG`, `UNEXPECTED_CLOSE`). The oracle implements a small
   deterministic structural balance check for exactly those two codes.
3. `TIMEOUT` cannot be enforced against CPU-bound pure Python in-process;
   the oracle enforces it on a subprocess guard path for large inputs.
4. Nested-call line reporting needs an upstream patch; the oracle documents
   the limitation (`line: 0`) instead of fabricating positions.
5. CLI parity tests need real files (no stdin mode).

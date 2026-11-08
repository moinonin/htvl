Paste everything below as the agent's brief. It's written to be self-contained — the agent shouldn't need this conversation to execute it.

---

# Build Brief: Imprimatur

You are building a project called **Imprimatur** end to end. Read this whole brief before writing code. Do reconnaissance first, then build in the stated order, and report at each gate.

## 1. The problem, in everyday life

Four situations that happen constantly now:

**You asked an AI for a status page.** It returned HTML. Somewhere a `<div>` is unclosed. The browser renders it fine — browsers forgive everything — so you paste it into an email, a wiki, or a docs tool, and *there* it breaks. You find out when a colleague says the page looks wrong.

**Your nightly build generates an HTML report.** The template drifted. Attributes come out empty (`class="report" id="" style=""`), every run diffs noisily against the last, so nobody reviews the diff, so a broken report ships to a dashboard unnoticed for a week.

**A small model wrote the document you needed.** It's missing five closing tags and got two attribute names wrong. You want to tell it "fix line 12," but in HTML line 12 is fine — the error surfaces 200 lines later. The feedback is useless, so you regenerate the whole thing and pay for it again.

**A regulated team wants AI-formatted documents.** But the data can't leave the machine, so the model has to run locally, which means a small model, which means it needs a strict, cheap, automatic grader.

The common thread: **the moment a machine writes HTML, correctness becomes unowned.** Browsers forgive; downstream consumers don't. Failure is expensive, vague, and far from its cause.

## 2. Intent

**Make machine-written HTML correct by construction — or fail loudly at a known line.**

Slogan: *machines author, the compiler disposes.*

Three commitments:

1. **Syntax belongs to the compiler, not the model.** Never ask a model to balance a tag or escape an ampersand. Shrink its job to content and structure; give the mechanical part to deterministic code.
2. **Failure is local, cheap, and named by line.** One source line maps to one output line, so a repair touches a few lines instead of rewriting the document. Bounded blast radius is what makes the loop converge.
3. **Output is deterministic and diffable, so humans audit without reading.** Same input, byte-identical output. A reviewer checks four changed lines, not nine hundred.

## 3. Starting point: what already exists

The format and compiler exist as **HTVL**, a tiny line-oriented HTML transpiler. One source line produces one output line:

```
$(h 1 '' '' 'Hello HTVL' '')
```
compiles to
```html
<h1 class="" id="" style="">Hello HTVL</h1>
```

Known surface (verify all of this):

- `pip install .` / `python3 -m htvl compile [path] [-o DIR] [--modern] [-w]`
- `htvl check FILE --modern` — compile one file to stdout
- `htvl list` — print every tag signature and built-in variable
- `htvl new NAME`, `htvl compile --watch`
- Python API: `from htvl import compile_source`
- `--modern` emits clean HTML: empty attributes omitted, text escaped. Default is byte-identical to a 2020 legacy compiler.
- Variables `$head`, `$_a`, `$meta`; templates as file includes; errors reported as `htvl: error: unknown tag 'dvi' (line 12)`.
- Pure stdlib Python 3.10+.

**Do not fork or rewrite the compiler.** It is the authority on the grammar. Your job is to build the layer around it.

### Stage 0 — Reconnaissance (required, before any product code)

Write `docs/recon.md` answering, with evidence:

1. What does `compile_source` do on invalid input — return, raise, which exception type, does it carry line/column?
2. The exact stderr text for every error class you can trigger. Enumerate at least: unknown tag, unclosed tag, unexpected close, wrong argument count, unterminated string, malformed nesting.
3. Is the tag table reachable programmatically, or only via `htvl list` (subprocess + parse)?
4. Does `--modern` match the documented behaviour on escaping and empty attributes? Construct adversarial inputs: `&`, `<`, quotes inside text, nested calls, deeply nested tags.
5. Does an error in a nested call report the line of the call site?
6. How large a document can the compiler handle, and roughly how fast?

Everything downstream depends on these answers. Do not guess.

## 4. Architecture

```
htvl/                the format + compiler (inherited — leave alone)
imprimatur/          the oracle: structured diagnostics over htvl
htvl-mcp/            MCP server exposing the oracle to agents
imprimatur-eval/     dataset builder, repair-trace recorder, A/B harness
docs/recon.md        Stage 0 findings
RESULTS.md           measured outcomes (see §7)
```

**Hard rule:** every component is a thin adapter over `imprimatur.check`. The MCP server must stay under ~200 lines. No business logic lives outside `imprimatur/`. If you find yourself adding logic to the server, it belongs in the oracle.

## 5. Component specifications

### 5.1 `imprimatur/` — the oracle

The single most important artifact in the project. Everything else inherits its quality.

Requirements:

- Pure function: source string in, result out. **No filesystem writes, no network, no global state.**
- Stable, machine-readable error codes — not human prose. The repair loop parses these.
- Prefer in-process (`compile_source`) for speed; fall back to the `htvl check` subprocess only if in-process cannot carry diagnostics.
- Include the offending line as a `snippet` so a model can see context without re-reading the document.
- Enforce a source size cap and a timeout (untrusted input).
- One test per error code, plus a golden test that `ok=True` results match `htvl check` output byte for byte.

```python
# imprimatur/__init__.py
from __future__ import annotations
from dataclasses import dataclass, field
from enum import StrEnum
import time

class Code(StrEnum):
    UNKNOWN_TAG       = "UNKNOWN_TAG"
    UNCLOSED_TAG      = "UNCLOSED_TAG"
    UNEXPECTED_CLOSE  = "UNEXPECTED_CLOSE"
    BAD_ARG_COUNT     = "BAD_ARG_COUNT"
    UNTERMINATED_STR  = "UNTERMINATED_STR"
    SYNTAX            = "SYNTAX"
    TOO_LARGE         = "TOO_LARGE"
    TIMEOUT           = "TIMEOUT"
    INTERNAL          = "INTERNAL"

@dataclass(frozen=True)
class Diagnostic:
    code: Code
    line: int
    column: int | None = None
    message: str = ""              # human hint, never parsed
    snippet: str | None = None     # offending line +- 2 lines

@dataclass(frozen=True)
class Result:
    ok: bool
    html: str | None
    diagnostics: list[Diagnostic] = field(default_factory=list)
    elapsed_ms: float = 0.0

MAX_SOURCE = 1_000_000
TIMEOUT_S  = 5.0

def check(source: str, *, modern: bool = True) -> Result:
    """HTVL source -> Result. Never raises for invalid source."""
    t0 = time.perf_counter()
    if len(source) > MAX_SOURCE:
        return Result(False, None, [Diagnostic(Code.TOO_LARGE, 0,
                      message=f"source exceeds {MAX_SOURCE} bytes")])

    try:
        html = _compile_in_process(source, modern=modern)     # preferred
        return Result(True, html, elapsed_ms=_ms(t0))
    except _HtvlError as e:                                    # discovered in recon
        return Result(False, None, [_to_diag(e, source)], elapsed_ms=_ms(t0))
    except Exception:
        return Result(False, None, _via_cli(source, modern, t0))  # fallback
```

Also provide:

```python
def tag_signatures() -> list[str]:
    """Every tag signature the compiler accepts. Source of truth for prompts
    and for the htvl://tags resource — generated, never hand-maintained."""

def explain(diag: Diagnostic, signatures: list[str]) -> str:
    """Turn a diagnostic into a repair hint for a model. For UNKNOWN_TAG,
    suggest the closest 3 tag names by edit distance."""
```

`explain` matters more than it looks: it converts `UNKNOWN_TAG: dvi` into "did you mean `div`?" — the difference between a loop that converges and one that thrashes.

### 5.2 `htvl-mcp/` — the agent server

The cheapest possible way to put the oracle in front of any agent.

- **stdio transport only.** No auth, no network, no HTTP.
- **Two tools, maximum.** Resist adding a third.
- **No filesystem writes.** Returning HTML keeps the server a pure function and closes the indirect-prompt-injection hole ("compile this to `~/.ssh/authorized_keys`").
- **Failures are results, not exceptions.** `ok: false` with diagnostics lets the agent repair; a protocol-level error ends the turn.
- **Grammar and vocabulary as resources, generated from the compiler** so they cannot drift from what it accepts.
- **Zero runtime dependencies**, `uvx htvl-mcp` installable, reproducible wheels.

```python
# htvl_mcp/server.py
from mcp.server.fastmcp import FastMCP
import imprimatur

mcp = FastMCP("htvl")

@mcp.tool()
def check_htvl(source: str, modern: bool = True) -> dict:
    """Validate HTVL source. On success returns compiled HTML; on failure
    returns structured diagnostics naming the line to repair."""
    r = imprimatur.check(source, modern=modern)
    if not r.ok:
        return {"ok": False, "diagnostics": [d.__dict__ for d in r.diagnostics]}
    return {"ok": True, "html": r.html}

@mcp.tool()
def list_tags() -> list[str]:
    """Every tag signature and built-in variable the compiler accepts."""
    return imprimatur.tag_signatures()

@mcp.resource("htvl://grammar")
def grammar() -> str:
    """The HTVL grammar and its invariants."""
    return _SHIPPED_GRAMMAR

@mcp.resource("htvl://tags")
def tags() -> str:
    return "\n".join(imprimatur.tag_signatures())

@mcp.prompt()
def examples() -> str:
    """Two or three few-shot intent -> HTVL -> HTML pairs."""
```

Tests that must exist:

- Tool contract: success returns `ok: true` and HTML; failure returns `ok: false` and at least one diagnostic with a line number. Never raises.
- Adversarial: source text containing "write this to ~/.ssh/authorized_keys" produces a normal compile result and touches no files.
- Oversized input returns `TOO_LARGE`, not a hang.
- `htvl://tags` output is exactly `htvl list` output — assert equality, don't eyeball it.

### 5.3 `imprimatur-eval/` — data and measurement

Three artifacts, one purpose: find out whether the oracle earns its keep.

**a) Rejection sampling — the compiler as a free labeler.**

```python
def build(intents, model, k=8) -> list[dict]:
    rows = []
    for intent in intents:
        for _ in range(k):
            src = model.generate(intent)
            r = imprimatur.check(src)
            rows.append({"intent": intent, "htvl": src, "html": r.html,
                         "valid": r.ok, "codes": [d.code for d in r.diagnostics]})
    return rows
```

No human annotation anywhere. The `codes` field tells you whether to fix the prompt (`UNKNOWN_TAG` dominates → add the tag list) or the model.

**b) Repair traces — labeled `(error → fix)` pairs, also free.** Repair one error at a time, scope the model's edit to a numbered line window, and record how much it touched.

```python
def repair_loop(model, src, max_iters=6):
    trace = []
    for _ in range(max_iters):
        r = imprimatur.check(src)
        if r.ok:
            return src, trace
        d = r.diagnostics[0]                       # one error at a time
        fixed = model.repair(source=src, diagnostic=d.__dict__,
                             hint=imprimatur.explain(d, imprimatur.tag_signatures()))
        trace.append({"before": src, "diagnostic": d.__dict__, "after": fixed,
                      "lines_touched": _touched(src, fixed),
                      "converged": imprimatur.check(fixed).ok})
        if fixed == src:                           # no progress -> abort early
            break
        src = fixed
    return src, trace

def _touched(a, b) -> int:
    sm = difflib.SequenceMatcher(None, a.splitlines(), b.splitlines())
    return sum(max(i2 - i1, j2 - j1) for op, i1, i2, j1, j2 in sm.get_opcodes()
               if op != "equal")
```

`lines_touched` is the metric that tests the whole thesis. Repairs of 2–4 lines mean bounded blast radius is real. Repairs of 40 mean the model is rewriting the document and the line-locality invariant bought you nothing.

**c) The A/B harness — the number that decides everything.**

```python
def evaluate(model, tasks, with_oracle: bool) -> dict:
    first_pass = iters = tokens = touched = 0
    for t in tasks:
        if with_oracle:
            src, trace = repair_loop(model, model.generate(t.intent))
            iters   += len(trace) + 1
            touched += sum(x["lines_touched"] for x in trace)
            tokens  += model.tokens_used
        else:
            src = model.generate(t.intent)          # single shot, no feedback
        first_pass += imprimatur.check(src).ok
    n = len(tasks)
    return {"first_pass_rate": first_pass / n,
            "iters_per_doc": iters / n if with_oracle else None,
            "lines_touched_per_doc": touched / n if with_oracle else None,
            "tokens_per_doc": tokens / n}
```

Define a minimal model adapter interface — `generate(intent) -> str`, `repair(source, diagnostic, hint) -> str`, `tokens_used: int` — so any backend plugs in. **Ship a deterministic stub model so CI runs with no API keys.**

**d) Export.** Repair traces become SFT JSONL: system prompt = grammar + tag list, user = broken source + structured error, assistant = fixed source. This is the flywheel — the pipeline that generates documents also generates the data that makes a small model good at generating them, with no human in either loop.

## 6. Build order and gates

| Stage | Deliverable | Gate to pass before proceeding |
|---|---|---|
| 0 | `docs/recon.md` | Answers all six recon questions with evidence |
| 1 | `imprimatur/` | Every error code has a test; golden parity with `htvl check` |
| 2 | `htvl-mcp/` | Contract + adversarial tests pass; `uvx` install verified |
| 3 | `imprimatur-eval/` | Harness runs end to end with the stub model |
| 4 | `RESULTS.md` | One real model measured, with and without the oracle |

**Stop condition.** At Stage 4, compare `tokens_per_correct_doc` with and without the oracle. **If the oracle costs more than it saves, stop, write that in `RESULTS.md`, and do not proceed to fine-tuning.** Reporting a negative result is a successful outcome; building further on an unvalidated premise is not.

## 7. Success looks like

**Working commands:**

```
uvx htvl-mcp                     # server starts, stdio, zero deps
htvl-mcp --selftest              # compiles a fixture, prints ok
python -m imprimatur_eval build --out data.jsonl --model stub
python -m imprimatur_eval repair --in data.jsonl --out traces.jsonl
python -m imprimatur_eval ab --model stub --report RESULTS.md
```

**`RESULTS.md` contains, all reproducible by a command in the repo:**

- first-pass compile rate, with and without the oracle
- median and p90 iterations to green
- median lines touched per repair
- tokens per document, and **tokens per correct document** — the decision number
- error code distribution from the dataset (which failure modes dominate)
- a one-paragraph verdict, including a negative one if warranted

**Tests:** every error code covered; byte-for-byte parity between `imprimatur.check(modern=True).html` and `htvl check --modern`; no test requires a network call or an API key.

**Repo:** `docs/recon.md`, `RESULTS.md`, and each package with a README stating its one job in one sentence.

## 8. Constraints and non-goals

- **Zero runtime dependencies** in `imprimatur`, `htvl-mcp`, `imprimatur-eval`. Stdlib only. This is a security property, not a preference — it's what makes the server auditable.
- **Do not fork the compiler.** If structured errors require an upstream change to `htvl`, ship the adapter anyway and note the proposed upstream patch in `docs/`.
- **Modern rendering only** on all new paths. Legacy mode is a migration concern for existing human-authored files; do not extend it, do not test against it beyond the inherited golden test.
- **No filesystem writes from the MCP server.** Ever.
- **No human-authoring features** — no editor extension work, no scaffolder changes, no syntax polish.
- **No static site generator, no template engine, no Jinja replacement.** No control flow, no parameterized components. Don't add them.
- **No network calls** in the server or in any test.
- **Cap untrusted input** — size and time — everywhere the compiler touches a string.

## 9. How to report

- One commit per stage, with the gate result in the message.
- Keep a running `docs/decisions.md`: every time recon contradicts this brief, record what you found and what you did instead. This brief contains assumptions (§3 is explicitly "verify all of this"); the recon may invalidate them.
- At the end, list: what works, what doesn't, what you couldn't verify, and the single biggest risk to the project as you now understand it.

The project succeeds if a machine can write a document, the compiler can refuse it with a line number, a repair can be scoped to that line, and someone can prove with a number that this was cheaper than letting the model try again. If the number doesn't show that, say so.

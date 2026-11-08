# htvl-mcp

**Its one job: put the Imprimatur oracle in front of any coding agent, over
stdio, as two tools.**

| Surface | What it does |
| --- | --- |
| `check_htvl(source, modern)` | Compiles HTVL; returns `{"ok": true, "html": ...}` or `{"ok": false, "diagnostics": [{code, line, snippet, hint}, ...]}` |
| `list_tags()` | Every tag signature and built-in variable, generated from the compiler |
| `htvl://grammar` | The grammar and its invariants |
| `htvl://tags` | The full generated reference (equals `htvl list` byte for byte) |
| `examples` (prompt) | Few-shot intent → HTVL → HTML pairs |

## Design constraints (from the build brief)

- **stdio only** — no auth, no HTTP, no network.
- **No filesystem writes, ever.** The server returns HTML rather than writing
  it, which is what makes "compile this to `~/.ssh/authorized_keys`" a
  harmless string instead of an attack.
- **Failures are results.** `ok: false` with coded, line-local diagnostics
  lets the agent repair; a protocol error would end its turn.
- **Two tools, maximum.** Every rule lives in `imprimatur`; this server is an
  adapter and stays under 200 lines.
- **One dependency**: the official `mcp` SDK, pinned to the v1 line
  (`mcp>=1.2,<2`) because 2.x renamed `FastMCP` to `MCPServer`.

## Run

```bash
uvx htvl-mcp                       # stdio server (needs PyPI publication)
uv tool run --from . htvl-mcp      # from a checkout of this repository
htvl-mcp --selftest                # compile a fixture and print ok
```

## Test

```bash
pip install -e ".[dev]"   # from the repository root; installs mcp too
python -m pytest tests/test_mcp.py
```

Tests drive the tools through FastMCP's own dispatch and assert the wire
format: successes return HTML, failures return diagnostics with a line, an
oversized source returns `TOO_LARGE` rather than hanging, prompt-injection
text compiles as text and touches nothing, and `htvl://tags` equals the CLI's
`htvl list` output byte for byte.

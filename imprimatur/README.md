# imprimatur

**Its one job: turn HTVL source into a structured verdict — `ok` with HTML, or
coded diagnostics naming the line to repair.**

```python
from imprimatur import check, explain

result = check("$(dvi 'x')\n")
# Result(ok=False, diagnostics=[Diagnostic(code=Code.UNKNOWN_TAG, line=1, ...)])

if not result.ok:
    print(explain(result.diagnostics[0], imprimatur.tag_signatures()))
    # unknown tag 'dvi' - did you mean 'div', 'video', 'i'?
```

## Properties

- **Pure**: no filesystem writes, no network, no global state. `check` never
  raises for invalid source — failures are values.
- **Fast on the hot path**: in-process compile up to 64 KB; larger inputs run
  in a wall-clock-guarded subprocess (the timeout a pure-Python loop cannot
  self-enforce).
- **Capped**: 256 KB source limit — recon measured the throughput that makes
  the brief's 1 MB cap incompatible with its 5 s timeout.
- **Generated, never hand-maintained**: `tag_signatures()` and
  `grammar_reference()` read the compiler's own tables, so they cannot drift
  from what it accepts.

## Codes

`UNKNOWN_TAG`, `UNKNOWN_VARIABLE`, `UNCLOSED_TAG`, `UNEXPECTED_CLOSE`,
`BAD_ARG_COUNT`, `UNTERMINATED_STR`, `SYNTAX`, `TOO_LARGE`, `TIMEOUT`,
`INTERNAL`. The last two and the balance pair come from the oracle itself —
recon showed the compiler never validates tag balance (it shipped an unclosed
`<span>` in its own 2020 example).

Zero runtime dependencies: Python 3.10+ standard library, plus `htvl`.

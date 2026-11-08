# TODO

**Short version:** the compile-check-repair loop works and pays for itself
(6× cheaper per correct document than single-shot), but it only converges 25%
of the time because the model rewrites documents instead of repairing the
named line. The experiment just run says that is the *model's* failure, not
the prompt's — so the next work is to stop asking the model to do mechanical
repairs at all.

Everything below is ordered by value. Items 1–3 are the recommended path;
4–7 are the remaining gaps to "every claim in the docs is true".

---

## Now

### 1. `imprimatur.fix` — deterministic repair

**Why:** every code the oracle emits is mechanically fixable (nearest valid
tag, trim surplus args, delete the stray closer, close the quote, insert the
missing closer). Paying a 7B model to do that — then policing its edit scope —
cost 72% more tokens and converged *less* (`docs/experiments/window-enforcement-analysis.md`).
Commitment #1 ("syntax belongs to the compiler, not the model") taken to its
conclusion: the compiler repairs syntax too.

**Build:**
- `imprimatur.fix(source, *, modern=True) -> FixResult` — one deterministic
  action per diagnostic, driven by the same parse tree the diagnostics come
  from (`imprimatur/structural.py` already walks it)
- Per-code actions: `UNKNOWN_TAG` → nearest valid tag by edit distance;
  `BAD_ARG_COUNT` → trim surplus arguments (keep the declared arity);
  `UNEXPECTED_CLOSE` → delete the closer; `UNTERMINATED_STR`/`SYNTAX` → close
  the quote/call on the offending line; `UNCLOSED_TAG` → insert the closer at
  the container's end (needs the nesting stack — the balance walker has it)
- Return the fixed source **and** the actions taken, so a repair is auditable
- Nothing is applied when a fix would be a guess (report instead)

**Acceptance:** a test per code asserting the exact deterministic action;
`fix()` never raises; `check(fix(src))` is green whenever a mechanical repair
exists; pure function, stdlib only, no new dependencies.

### 2. Measure the deterministic repairer

**Why:** the claim must be a number, not an assertion — the harness already
measures it unchanged.

**Build:** a `deterministic` repair adapter in `imprimatur_eval.models` whose
`repair()` calls `imprimatur.fix`, then run the treatment arm against the same
20 tasks (frozen protocol, same model for generation, temperature 0).

**Acceptance:** `docs/experiments/deterministic-repair.md` reports convergence,
tokens/correct doc, and iterations against the recorded baseline
(25% / 14,203 / 5.25). Target: convergence ≥ 95% on mechanical errors at
~0 repair tokens. Report the negative if it doesn't hold.

### 3. Then: qwen3.5:4b on the frozen protocol

**Why:** only after deterministic repair is measured does a better model have
anything left to add (content quality, not syntax). ~35 min, no new code.

**Acceptance:** one `ab` run; report whether it beats qwen2.5-coder:7b-instruct
on the same decision rule, and whether it adds anything *on top of* item 2.

---

## Then: the remaining gaps to "every doc claim is true"

### 4. MCP client wiring (untested with a real client)

`htvl-mcp --client-config` printing the exact registration JSON for the current
checkout, plus recipes for Claude Code (`claude mcp add`), Claude Desktop
(`claude_desktop_config.json`) and VS Code (`mcp.json`) in the README. Raw
stdio JSON-RPC is verified; the registration artifact is not.

### 5. Playground: the 30-second browser check

`playground/` has never been rendered in a browser (three bugs already lived
there — found by reasoning and tests, not by looking). Serve it, confirm it
compiles and both modes render, then tick this off. **Needs a human with a
browser.**

### 6. Release hygiene

- `CHANGELOG.md` covering both releases (0.2.0 compiler, 1.0.0 Imprimatur)
- Align the four package versions (currently 0.2.0 / 1.0.0 / 1.0.0 / 1.0.0)
- `CONTRIBUTING.md`, issue templates, PR template
- Create the GitHub Release from `docs/releases/v0.2.0.md` (**web action —
  needs you**)

### 7. Document what the experiments changed

README's Imprimatur section should state the honest summary: oracle pays 6×,
line-local repair refuted, deterministic repair pending item 2's number.

---

## Blocked on you

- **PyPI publication** of the four wheels (`htvl-lang`, `imprimatur`,
  `htvl-mcp`, `imprimatur-eval`) — each is verified installable from its built
  wheel; only the upload needs credentials
- Delete the untracked `.env` (live API keys) and `requirements.txt` (pip
  artifact) from the working tree — both are gitignored now

---

## Closed (for the record)

- ✅ Stage 0–4: recon, oracle, MCP server, eval harness, `RESULTS.md`
- ✅ Window-enforced repair — **measured negative** (see item 1's why)
- ✅ All four wheels build and install into a clean venv
- ✅ Real stdio JSON-RPC session against the MCP server
- ⛔ PyPI upload — deferred by request

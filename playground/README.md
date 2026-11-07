# HTVL playground

An in-browser playground: edit HTVL on the left, see the compiled page and its
HTML source on the right, with a legacy/modern toggle.

**There is no server.** The page downloads [Pyodide](https://pyodide.org)
(CPython compiled to WebAssembly) from a CDN, loads the real `htvl` package
into its virtual filesystem, and calls `compile_source()` on every keystroke.
The grammar in the browser and the grammar in the CLI are the same code.

| File | Purpose |
| --- | --- |
| `index.html` | the page |
| `playground.js` | Pyodide boot, package install, debounced compile |
| `style.css` | dark two-pane layout |
| `sync.py` | copies `htvl/*.py` into `lib/` and writes `lib/manifest.json` |
| `lib/` | the copy of the compiler the page fetches (keep in sync!) |

## Local development

Any static file server works:

```bash
python3 -m http.server 8000 --directory playground
# open http://localhost:8000
```

After changing anything in `htvl/`, refresh the playground copy:

```bash
python3 playground/sync.py
```

The test suite fails if `lib/` drifts from the package
(`tests/test_playground_lib.py`), so a forgotten sync cannot slip through.

## Deploying

The directory is fully static - publish `playground/` as-is to GitHub Pages,
Netlify, or any static host. The Pyodide version is pinned in
`playground.js` (`PYODIDE_VERSION`).

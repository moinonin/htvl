# The HTVL language

HTVL (HTML Language) is a tiny markup DSL. An HTVL file is plain text with
three constructs; everything else is copied through verbatim. The compiler
turns `.htvl` files into `.html` (and `.cal` files into CGI scripts).

This document describes the language as implemented by `htvl/elements.py`,
`htvl/variables.py` and `htvl/templates.py`. The grammar is a faithful port of
the original 2020 bash compiler — see `docs/recovered-legacy-compiler.sh` —
and `tests/test_golden.py` verifies that the project's own example still
compiles byte-for-byte identically.

## The three constructs

```text
$(tag 'arg' ...)      # a tag call
$name                 # a variable reference ($head, $_a, $meta, $headtags, ...)
${name[@]}            # same, legacy array syntax (word-splits like bash)
```

* Arguments are separated by spaces. Quote them with `'...'` (or `"..."`);
  parentheses inside quotes are literal, so `'if (a > b)'` is safe.
* Bare words are allowed for short values: `$(h 3 '' '' 'Title')`.
* Calls can nest and be used as arguments: `$(link stylesheet 'text/css' $(bsCdn '4.3.1'))`.
* Missing arguments become empty strings: `$(div 'x')` is the same as
  `$(div 'x' '' '')`.
* Unknown tags, unknown variables and too many arguments are compile errors
  with the offending line number — unlike the 2020 bash version, which failed
  silently.

## Line structure

HTVL preserves your file's line structure: **one source line produces one
output line**, leading whitespace is kept, and blank lines stay blank. Tags
that need closing are closed explicitly with `$_name`:

```text
$(div 'container')
  $(h 1 '' '' 'Hello' '')
  $(p '' '' 'Compiled by htvl.' '')
  $_p
$_div
```

compiles to

```html
<div class="container" id="" style="">
  <h1 class="" id="" style="">Hello</h1>
  <p class="" id="" style="">Compiled by htvl.
  </p>
</div>
```

Tags whose signature includes `content` (`h`, `i`, `title`, `label`, `strong`,
`b`, `abbr`, `script`, `comment`) render a complete element and never need a
closing reference. Tags that open without content (`div`, `a`, `p`, `form`,
`btn`, ...) render their open tag (plus inline content, if given) and wait for
`$_name`.

## Tags

Run `htvl list` for the live list. The signatures below show the exact
argument order; attribute order in the emitted HTML matches the original
compiler.

| Tag | Arguments | Emits |
| --- | --- | --- |
| `h` | level, class, id, content, style | `<hN class id style>content</hN>` |
| `div` | class, id, style | `<div class id style>` — close with `$_div` |
| `a` | class, href, content, id, target, aria_pressed, style | `<a ...>content` — close with `$_a` |
| `p` | class, id, content, style | `<p ...>content` — close with `$_p` |
| `span` | class | `<span class>` — close with `$_span` |
| `nav` | class | `<nav class>` — close with `$_nav` |
| `ul` | class | `<ul class>` — close with `$_ul` |
| `li` | class | `<li class>` — close with `$_li` |
| `footer` | class | `<footer class>` — close with `$_footer` |
| `i` | class | `<i class> </i>` (complete pair) |
| `img` | src, alt, style | `<img src alt style>` (void) |
| `input` | class, type, aria_label, value, placeholder, onclick | `<input .../>` (void) |
| `btn` | class, type, value, onclick, data_toggle, data_target, style | `<button ...>` — close with `$_btn` |
| `form` | class, action, method, style | `<form ...>` — close with `$_form` |
| `title` | id, content | `<title id lang="en">content</title>` |
| `link` | rel, type, href, integrity, crossorigin | `<link ...>` (void) |
| `script` | src, type, content | `<script ...>content</script>` |
| `metaLink` | name, content, http_equiv | `<meta .../>` (void) |
| `comment` | content | `<!-- content -->` |
| `bsCdn` | version | the Bootstrap CDN URL (a value, not HTML) |
| `label` | for_, class, content | `<label ...>content</label>` |
| `path` | fill, d | `<path .../>` (void) |
| `section` | class, id | `<section ...>` — close with `$_section` |
| `strong` | content | `<strong>content</strong>` |
| `b` | class, content | `<b ...>content</b>` |
| `abbr` | title, content | `<abbr ...>content</abbr>` |
| `nav-a` | class, href, content, id | `<a ...>content` — close with `$_a` |
| `video` | src | `<video ...><source .../></video>` |
| `iframe` | src, class | `<iframe ...></iframe>` |
| `svg` | aria_labelledby, role, viewbox, fill, title_id, title_lang, title, path_d, xmlns | inline SVG figure |
| `svgSimple` | width, height | `<svg ...>` — close with `$_svg` |

`input`'s `onclick` is the *last* parameter but is emitted *before* the
`placeholder` attribute; that ordering is preserved from the original.

## Variables

```
$DOCTYPE_htvl   <!DOCTYPE html>
$htvl           <html lang="en">            $_htvl   </html>
$head           <head>                      $_head   </head>
$body           <body>                      $_body   </body>
$br             <br>
$meta           the four default <meta> tags
$_a $_p $_ul $_li $_div $_btn $_nav $_span
$_form $_footer $_svg $_iframe $_script $_section $_strong   matching close tags
```

Any other `$_name` closes as `</name>`, which is handy for the less common
elements. `$meta` expands to several lines: the first line keeps the
indentation of the line that referenced it.

## Templates

A template is a named chunk of HTVL source spliced in with `$name`. Put files
in a `templates/` directory next to your `.htvl` files:

* `templates/headtags.htvl` defines `$headtags` — recommended format.
* Legacy `templates/*.sh` files with `read -r -d '' NAME <<- EOM ... EOM`
  blocks are also loaded, so 2020-era projects keep working unchanged. HTVL's
  own example (in `legacy/`) uses this format.

Templates are compiled before they are spliced in, so they may contain tags,
variables and other templates. Their first line adopts the indentation of the
referencing line, exactly like the original heredoc expansion.

Arrays (`${nav0[@]}`) behave like bash: whitespace-only values collapse to
nothing.

## CGI with `.cal`

A `.cal` file is compiled exactly like a `.htvl` file but written to
`cal/<name>` as a self-contained executable script:

```bash
#!/usr/bin/env bash
# Generated by htvl from hello.cal - a self-contained CGI script.
cat <<'HTVL_DOCUMENT'
<!DOCTYPE html>
...
HTVL_DOCUMENT
```

`chmod +x cal/<name>` is already applied, so it can be dropped straight into a
CGI-capable web server.

## Faithfulness and known quirks

These oddities are intentional in v1: they keep every existing `.htvl` file
compiling to the same bytes as before. They are all marked `[legacy]` in
`htvl/elements.py` and are candidates for an opt-in `--modern` mode later.

1. No HTML escaping. Text and arguments are inserted verbatim (the original
   did the same). Never interpolate untrusted input into a `.cal` script.
2. `a` renders a hardcoded empty `role=""` attribute.
3. `span` emits `<span class="x" >` with a space before `>`.
4. `i` renders `<i class="x"> </i>` with a space inside the pair.
5. `link` emits `rel = "..."` and `type = "..."` with spaces around `=`.
6. `script` emits `type=""` even when no type is given.
7. `title` hardcodes `lang="en"`.
8. Unknown closing tags (`$_video`) silently emit `</video>`.

## CLI

```
htvl compile [path] [-o DIR]   compile a project (default: ./ into public/)
htvl check FILE...             compile to stdout, no project needed
htvl new NAME                  scaffold a new project
htvl list                      every tag and built-in variable
```

## Library use

```python
from htvl import compile_source

html = compile_source("$(h 1 '' '' 'Hello' ')\n")
```

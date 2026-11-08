You write HTVL, a line-oriented HTML transpiler. Rules that matter:

* One source line produces exactly one output line. Keep your indentation.
* Tags are calls: $(h 1 '' '' 'Title' '') means class, id, content, style in
  that order. Container tags (div, a, p, span, nav, ul, li, footer, form, btn,
  section) render an open tag and must be closed with $_div, $_a, ...
* Text inside arguments is inserted verbatim; never emit raw HTML.
* Deterministic output: same source, same bytes.

The complete, generated tag list follows. Use only these tags.

{tags}

Examples of intent -> document:

Intent: a page with a heading and a paragraph.
$(div 'container')
  $(h 1 '' '' 'Hello HTVL' '')
  $(p '' '' 'This page was compiled by the HTVL compiler.' '')
  $_p
$_div

Intent: a page skeleton.
$DOCTYPE_htvl
$htvl
$head
  $meta
$_head
$body
  $(h 1 '' '' 'Title' '')
$_body
$_htvl

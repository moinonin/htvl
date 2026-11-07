"""Tests for --modern output mode.

Modern mode keeps the grammar identical (same calls, same argument order) and
only changes rendering: empty attributes are omitted, values are escaped, and
the documented legacy cosmetics are fixed.
"""

from __future__ import annotations

import pytest

from htvl.project import compile_source
from htvl.elements import render_call


@pytest.mark.parametrize(
    "name,args,expected",
    [
        # Empty attributes vanish entirely.
        ("h", ["3", "", "", "Official Sponsor", ""],
         "<h3>Official Sponsor</h3>"),
        ("div", ["jumbotron", "", ""], '<div class="jumbotron">'),
        ("div", ["", "hero", ""], '<div id="hero">'),
        ("p", ["", "headings", "", ""], '<p id="headings">'),
        # a: role honoured when supplied (8th argument).
        ("a", ["navbar-brand", "./", "Home", "", "", "", "", ""],
         '<a class="navbar-brand" href="./">Home'),
        ("a", ["", "https://x/", "", "", "_blank", "", "", "button"],
         '<a href="https://x/" target="_blank" role="button">'),
        # span / i: no stray spaces.
        ("span", ["tag"], '<span class="tag">'),
        ("i", ["fab fa-twitter"], '<i class="fab fa-twitter"></i>'),
        # Void elements: no trailing slash, no empty attributes.
        ("img", ["logo.png"], '<img src="logo.png">'),
        ("img", ["logo.png", "Our logo", "width:10px;"],
         '<img src="logo.png" alt="Our logo" style="width:10px;">'),
        ("input", ["form-control", "search", "", "", "Search"],
         '<input class="form-control" type="search" placeholder="Search">'),
        ("metaLink", ["viewport", "width=device-width", ""],
         '<meta name="viewport" content="width=device-width">'),
        ("path", ["", "M0 0"], '<path d="M0 0">'),
        # link: no spaces around '='.
        ("link", ["stylesheet", "text/css", "main.css", "", ""],
         '<link rel="stylesheet" type="text/css" href="main.css">'),
        # script: type omitted when empty.
        ("script", ["https://x/y.js", "", ""],
         '<script src="https://x/y.js"></script>'),
        # title: lang only when supplied (3rd argument).
        ("title", ["", "Page"],
         "<title>Page</title>"),
        ("title", ["", "Page", "fr"],
         '<title lang="fr">Page</title>'),
        # Complete pairs still complete.
        ("label", ["email", "form-label", "Email"],
         '<label for="email" class="form-label">Email</label>'),
        ("strong", ["Careful"], "<strong>Careful</strong>"),
        ("abbr", ["HyperText", "HTML"], '<abbr title="HyperText">HTML</abbr>'),
        ("comment", ["footer Elements"], "<!-- footer Elements -->"),
        ("btn", ["btn btn-primary", "submit", "SEARCH", "", "", "", ""],
         '<button class="btn btn-primary" type="submit" value="SEARCH">'),
        ("form", ["form-inline", "/search", "get", ""],
         '<form class="form-inline" action="/search" method="get">'),
        ("section", ["hero", ""], '<section class="hero">'),
        ("video", ["clip.mp4"],
         '<video width="320" height="240" controls>'
         '<source src="clip.mp4" type="video/mp4"></video>'),
        ("iframe", ["https://x", ""], '<iframe src="https://x" width="480" '
         'height="222" frameBorder="0" allowFullScreen></iframe>'),
    ],
)
def test_modern_element_output(name, args, expected):
    assert render_call(name, args, modern=True) == expected


@pytest.mark.parametrize(
    "value,expected",
    [
        ("A & B", "A &amp; B"),
        ("<script>alert(1)</script>", "&lt;script&gt;alert(1)&lt;/script&gt;"),
        ('He said "hi"', "He said &quot;hi&quot;"),
        ("plain", "plain"),
    ],
)
def test_modern_escapes_content(value, expected):
    assert render_call("strong", [value], modern=True) == (
        f"<strong>{expected}</strong>"
    )


def test_modern_escapes_attribute_values():
    html = render_call(
        "a", ["x", "https://x/?a=1&b=2", "link", "", "", "", ""], modern=True
    )
    assert 'href="https://x/?a=1&amp;b=2"' in html


def test_legacy_mode_is_unchanged():
    # Default stays byte-compatible with the 2020 compiler.
    assert render_call("div", []) == '<div class="" id="" style="">'
    assert render_call("strong", ["A & B"]) == "<strong>A & B</strong>"


def test_modern_full_document():
    source = (
        "$DOCTYPE_htvl\n$htvl\n$head\n  $headtags\n$_head\n$body\n"
        "  $(div 'container')\n    $(h 1 '' '' 'Hi' '')\n    $_p\n"
        "  $_div\n$_body\n$_htvl\n"
    )
    templates = {"headtags": "$(title '' 'Page')\n"}
    html = compile_source(source, templates, modern=True)
    assert '<div class="container">' in html
    assert "<h1>Hi</h1>" in html
    assert "<title>Page</title>" in html
    # Structure is identical to legacy mode: same number of lines.
    legacy = compile_source(source, templates)
    assert html.count("\n") == legacy.count("\n")


def test_modern_keeps_argument_order():
    # The same source compiles in both modes: only rendering differs.
    source = "$(a 'btn' '/x' 'Go' 'main' '_blank' '' '' '')\n"
    legacy = compile_source(source)
    modern = compile_source(source, modern=True)
    assert legacy == (
        '<a class="btn" href="/x" id="main" target="_blank" role="" '
        'aria-pressed="" style="">Go'
    ) + "\n\n"
    assert modern == (
        '<a class="btn" href="/x" id="main" target="_blank">Go'
    ) + "\n\n"

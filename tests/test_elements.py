"""Element registry tests.

The expected strings are the exact output of the original 2020 bash
implementation, including its quirks. They protect the port from drift.
"""

from __future__ import annotations

import pytest

from htvl.errors import HtvlArityError, HtvlUnknownTagError
from htvl.elements import ELEMENTS, render_call


@pytest.mark.parametrize(
    "name,args,expected",
    [
        # h: level, class, id, content, style
        ("h", ["3", "", "", "Official Sponsor", ""],
         '<h3 class="" id="" style="">Official Sponsor</h3>'),
        ("h", ["1", "", "framework", "JetPack<br>", ""],
         '<h1 class="" id="framework" style="">JetPack<br></h1>'),
        # div: class, id, style
        ("div", ["jumbotron", "", ""], '<div class="jumbotron" id="" style="">'),
        ("div", ["", "hero", ""], '<div class="" id="hero" style="">'),
        # a: class, href, content, id, target, aria-pressed, style
        ("a", ["navbar-brand", "./", "", "", "", "", ""],
         '<a class="navbar-brand" href="./" id="" target="" role="" '
         'aria-pressed="" style="">'),
        ("a", ["", "https://x/", "", "", "_blank", "", ""],
         '<a class="" href="https://x/" id="" target="_blank" role="" '
         'aria-pressed="" style="">'),
        # p: class, id, content, style
        ("p", ["", "headings", "", ""], '<p class="" id="headings" style="">'),
        ("p", ["", "", "", "margin-bottom: 0;"],
         '<p class="" id="" style="margin-bottom: 0;">'),
        # span / nav / ul / li / footer
        ("span", ["navbar-toggler-icon"], '<span class="navbar-toggler-icon" >'),
        ("nav", ["navbar bg-dark"], '<nav class="navbar bg-dark">'),
        ("ul", ["navbar-nav"], '<ul class="navbar-nav">'),
        ("li", ["list-inline-item"], '<li class="list-inline-item">'),
        ("footer", ["page-footer pt-4"], '<footer class="page-footer pt-4">'),
        # i: legacy emits a full pair with a stray space
        ("i", ["fab fa-facebook-f"], '<i class="fab fa-facebook-f"> </i>'),
        # void elements
        ("img", ["logo.png"], '<img src="logo.png" alt="" style="">'),
        ("img", ["logo.png", "Our logo", "width:10px;"],
         '<img src="logo.png" alt="Our logo" style="width:10px;">'),
        ("input", ["form-control mr-sm-2", "search", "", "", "Search"],
         '<input class="form-control mr-sm-2" type="search" aria-label="" '
         'value="" onClick="" placeholder="Search"/>'),
        ("btn", ["btn btn-primary", "submit", "SEARCH", "", "", "",
                 "margin-bottom: 0;"],
         '<button class="btn btn-primary" type="submit" value="SEARCH" '
         'onClick="" data-toggle="" data-target="" '
         'style="margin-bottom: 0;">'),
        ("form", ["form-inline", "", "", "margin-bottom: 0;"],
         '<form class="form-inline" action="" method="" '
         'style="margin-bottom: 0;">'),
        ("link", ["stylesheet", "text/css", "main.css", "", ""],
         '<link rel = "stylesheet" type = "text/css" href = "main.css" '
         'integrity="" crossorigin="">'),
        ("script", ["https://x/y.js", "", ""],
         '<script src="https://x/y.js" type=""></script>'),
        ("metaLink", ["viewport", "width=device-width", ""],
         '<meta name="viewport" content="width=device-width" '
         'http-equiv=""/>'),
        # complete pairs
        ("title", ["", "Page"], '<title id="" lang="en">Page</title>'),
        ("label", ["email", "form-label", "Email"],
         '<label for="email" class="form-label">Email</label>'),
        ("strong", ["Careful"], "<strong>Careful</strong>"),
        ("b", ["lead", "Bold"], '<b class="lead">Bold</b>'),
        ("abbr", ["HyperText", "HTML"], '<abbr title="HyperText">HTML</abbr>'),
        # value producers
        ("comment", ["footer Elements"], "<!-- footer Elements -->"),
        ("bsCdn", ["4.3.1"],
         "https://stackpath.bootstrapcdn.com/bootstrap/4.3.1"
         "/css/bootstrap.min.css"),
    ],
)
def test_element_output(name, args, expected):
    assert render_call(name, args) == expected


def test_missing_args_are_padded_with_empty_strings():
    assert render_call("div", []) == '<div class="" id="" style="">'


def test_unknown_tag_raises():
    with pytest.raises(HtvlUnknownTagError):
        render_call("dvi", ["x"])


def test_too_many_args_raises():
    with pytest.raises(HtvlArityError):
        render_call("div", ["a", "b", "c", "d"])


def test_registry_sanity():
    assert "h" in ELEMENTS
    assert "bsCdn" in ELEMENTS
    assert all("'" not in name for name in ELEMENTS)

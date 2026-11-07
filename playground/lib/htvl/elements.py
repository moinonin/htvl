"""The HTVL tag registry.

Every ``$(name ...)`` call in an HTVL file maps to one function in this module.

The registry is a faithful port of the original 2020 bash implementation (see
``docs/recovered-legacy-compiler.sh``): argument order, attribute order and even
a few cosmetic quirks of the emitted HTML are preserved so that existing
``.htvl`` files compile to byte-identical output. Quirks are marked
``[legacy]`` and collected in docs/grammar.md.

Two rendering modes are available:

* ``legacy`` (default) - byte-compatible with the 2020 compiler: every
  attribute is emitted, even empty ones, and text is never escaped.
* ``modern`` - opt-in via ``--modern``: empty attributes are omitted, text and
  attribute values are HTML-escaped, and the ``[legacy]`` quirks are fixed.

Each element declares its parameters in order; calling a tag with fewer
arguments than declared pads the missing ones with empty strings, exactly like
the original shell functions did.
"""

from __future__ import annotations

import html as _html
from dataclasses import dataclass
from typing import Callable, Dict, List, Sequence, Tuple, Union

from .errors import HtvlArityError, HtvlUnknownTagError

ArgValue = Union[str, None]
# An ordered (name, value) attribute pair.
Attr = Tuple[str, str]


def _attrs(pairs: Sequence[Attr], *, modern: bool) -> str:
    """Render attribute pairs.

    Legacy mode emits every attribute (`` class="" id=""``) and never escapes.
    Modern mode emits only non-empty values, HTML-escaped.
    """
    parts = []
    for name, value in pairs:
        value = value or ""
        if modern:
            if not value:
                continue
            value = _html.escape(value, quote=True)
        parts.append(f' {name}="{value}"')
    return "".join(parts)


def _text(value: str, *, modern: bool) -> str:
    return _html.escape(value) if modern else value


@dataclass(frozen=True)
class Element:
    """One HTVL tag: its name, parameters and renderer."""

    name: str
    params: Tuple[str, ...]
    render: Callable[..., str]
    doc: str = ""

    @property
    def signature(self) -> str:
        return f"$({self.name} {' '.join(self.params)})"


def _pad(name: str, params: Tuple[str, ...], args: List[ArgValue], line):
    if len(args) > len(params):
        raise HtvlArityError(name, len(params), len(args), line)
    return [a if a is not None else "" for a in args] + [""] * (
        len(params) - len(args)
    )


def _el(name, params, doc=""):
    def decorate(fn):
        fn._element = Element(name=name, params=params, render=fn, doc=doc)
        return fn

    return decorate


# ---------------------------------------------------------------------------
# Elements
# ---------------------------------------------------------------------------


@_el(
    "h",
    ("level", "class", "id", "content", "style"),
    "Heading of any level; renders a complete <hN>...</hN> pair.",
)
def h(level, class_, id, content, style, *, modern=False):  # noqa: A002
    attrs = _attrs(
        [("class", class_), ("id", id), ("style", style)], modern=modern
    )
    body = _text(content, modern=modern)
    return f"<h{level}{attrs}>{body}</h{level}>"


@_el(
    "div",
    ("class", "id", "style"),
    "Generic container; close with $_div.",
)
def div(class_, id, style, *, modern=False):  # noqa: A002
    attrs = _attrs(
        [("class", class_), ("id", id), ("style", style)], modern=modern
    )
    return f"<div{attrs}>"


@_el(
    "a",
    ("class", "href", "content", "id", "target", "aria_pressed", "style",
     "role"),
    "Anchor. Renders the open tag plus content; close with $_a. "
    "[legacy] a hardcoded, always-empty role attribute; the trailing 'role' "
    "argument is only honoured in --modern mode.",
)
def a(
    class_, href, content, id, target, aria_pressed, style, role, *, modern=False
):  # noqa: A002
    pairs = [
        ("class", class_),
        ("href", href),
        ("id", id),
        ("target", target),
    ]
    if modern:
        pairs.append(("role", role))
    else:
        pairs.append(("role", ""))
    pairs.append(("aria-pressed", aria_pressed))
    pairs.append(("style", style))
    attrs = _attrs(pairs, modern=modern)
    return f"<a{attrs}>{_text(content, modern=modern)}"


@_el(
    "p",
    ("class", "id", "content", "style"),
    "Paragraph. Renders the open tag plus content; close with $_p.",
)
def p(class_, id, content, style, *, modern=False):  # noqa: A002
    attrs = _attrs(
        [("class", class_), ("id", id), ("style", style)], modern=modern
    )
    return f"<p{attrs}>{_text(content, modern=modern)}"


@_el("span", ("class",), "Inline span. [legacy] emits class only, with a space before '>'.")
def span(class_, *, modern=False):  # noqa: A002
    if modern:
        return f"<span{_attrs([('class', class_)], modern=True)}>"
    return f'<span class="{class_}" >'


@_el("nav", ("class",), "Navigation landmark; close with $_nav.")
def nav(class_, *, modern=False):  # noqa: A002
    return f"<nav{_attrs([('class', class_)], modern=modern)}>"


@_el("ul", ("class",), "Unordered list; close with $_ul.")
def ul(class_, *, modern=False):  # noqa: A002
    return f"<ul{_attrs([('class', class_)], modern=modern)}>"


@_el("li", ("class",), "List item; close with $_li.")
def li(class_, *, modern=False):  # noqa: A002
    return f"<li{_attrs([('class', class_)], modern=modern)}>"


@_el("footer", ("class",), "Footer landmark; close with $_footer.")
def footer(class_, *, modern=False):  # noqa: A002
    return f"<footer{_attrs([('class', class_)], modern=modern)}>"


@_el("i", ("class",), "Icon (e.g. Font Awesome). [legacy] renders a full pair with a stray space inside.")
def i(class_, *, modern=False):  # noqa: A002
    if modern:
        return f"<i{_attrs([('class', class_)], modern=True)}></i>"
    # Legacy output: '<i class="X"> </i>' - a full pair with a stray space.
    return '<i class="' + class_ + '">' + " " + "</i>"


@_el("img", ("src", "alt", "style"), "Image (void element).")
def img(src, alt, style, *, modern=False):
    attrs = _attrs(
        [("src", src), ("alt", alt), ("style", style)], modern=modern
    )
    return f"<img{attrs}>"


@_el(
    "input",
    ("class", "type", "aria_label", "value", "placeholder", "onclick"),
    "Form input (void element). [legacy] onClick sits last in the emitted "
    "attributes even though it is the last parameter.",
)
def input_(
    class_, type_, aria_label, value, placeholder, onclick, *, modern=False
):
    attrs = _attrs(
        [
            ("class", class_),
            ("type", type_),
            ("aria-label", aria_label),
            ("value", value),
            ("onClick", onclick),
            ("placeholder", placeholder),
        ],
        modern=modern,
    )
    return f"<input{attrs}{'' if modern else '/'}>"
input_.__name__ = "input"


@_el(
    "btn",
    ("class", "type", "value", "onclick", "data_toggle", "data_target", "style"),
    "Button; close with $_btn.",
)
def btn(
    class_, type_, value, onclick, data_toggle, data_target, style, *, modern=False
):
    attrs = _attrs(
        [
            ("class", class_),
            ("type", type_),
            ("value", value),
            ("onClick", onclick),
            ("data-toggle", data_toggle),
            ("data-target", data_target),
            ("style", style),
        ],
        modern=modern,
    )
    return f"<button{attrs}>"


@_el(
    "form",
    ("class", "action", "method", "style"),
    "Form; close with $_form.",
)
def form(class_, action, method, style, *, modern=False):
    attrs = _attrs(
        [
            ("class", class_),
            ("action", action),
            ("method", method),
            ("style", style),
        ],
        modern=modern,
    )
    return f"<form{attrs}>"


@_el("title", ("id", "content", "lang"), "Document title. [legacy] lang is hardcoded to 'en'; the trailing lang argument is only honoured in --modern mode.")
def title(id, content, lang, *, modern=False):
    if modern:
        attrs = _attrs([("id", id), ("lang", lang)], modern=True)
        return f"<title{attrs}>{_text(content, modern=True)}</title>"
    return f'<title id="{id}" lang="en">{content}</title>'


@_el(
    "link",
    ("rel", "type", "href", "integrity", "crossorigin"),
    "Stylesheet/icon link (void element). "
    "[legacy] emits 'rel = ' and 'type = ' with spaces around the '='.",
)
def link(rel, type_, href, integrity, crossorigin, *, modern=False):
    pairs = [
        ("rel", rel),
        ("type", type_),
        ("href", href),
        ("integrity", integrity),
        ("crossorigin", crossorigin),
    ]
    if modern:
        attrs = _attrs(pairs, modern=True)
    else:
        attrs = (
            f' rel = "{rel}" type = "{type_}" href = "{href}" '
            f'integrity="{integrity}" crossorigin="{crossorigin}">'
        )
        return f"<link{attrs}"
    return f"<link{attrs}>"


@_el("script", ("src", "type", "content"), "Script tag; renders a complete pair.")
def script(src, type_, content, *, modern=False):
    attrs = _attrs([("src", src), ("type", type_)], modern=modern)
    return f"<script{attrs}>{_text(content, modern=modern)}</script>"


@_el(
    "metaLink",
    ("name", "content", "http_equiv"),
    "Meta tag (void element).",
)
def metaLink(name, content, http_equiv, *, modern=False):
    attrs = _attrs(
        [
            ("name", name),
            ("content", content),
            ("http-equiv", http_equiv),
        ],
        modern=modern,
    )
    return f"<meta{attrs}{'' if modern else '/'}>"


@_el("comment", ("content",), "HTML comment.")
def comment(content, *, modern=False):
    return f"<!-- {_text(content, modern=modern)} -->"


@_el("bsCdn", ("version",), "Bootstrap CDN URL for the given version.")
def bsCdn(version, *, modern=False):
    return (
        f"https://stackpath.bootstrapcdn.com/bootstrap/{version}"
        f"/css/bootstrap.min.css"
    )


@_el("label", ("for_", "class", "content"), "Form label; renders a complete pair.")
def label(for_, class_, content, *, modern=False):  # noqa: A002
    attrs = _attrs([("for", for_), ("class", class_)], modern=modern)
    return f"<label{attrs}>{_text(content, modern=modern)}</label>"


@_el("path", ("fill", "d"), "SVG path (void element).")
def path(fill, d, *, modern=False):
    attrs = _attrs([("fill", fill), ("d", d)], modern=modern)
    return f"<path{attrs}{'' if modern else '/'}>"


@_el("section", ("class", "id"), "Section landmark; close with $_section.")
def section(class_, id, *, modern=False):  # noqa: A002
    attrs = _attrs([("class", class_), ("id", id)], modern=modern)
    return f"<section{attrs}>"


@_el("strong", ("content",), "Strong emphasis; renders a complete pair.")
def strong(content, *, modern=False):
    return f"<strong>{_text(content, modern=modern)}</strong>"


@_el("b", ("class", "content"), "Bold text; renders a complete pair.")
def b(class_, content, *, modern=False):  # noqa: A002
    attrs = _attrs([("class", class_)], modern=modern)
    return f"<b{attrs}>{_text(content, modern=modern)}</b>"


@_el("abbr", ("title", "content"), "Abbreviation; renders a complete pair.")
def abbr(title_, content, *, modern=False):
    attrs = _attrs([("title", title_)], modern=modern)
    return f"<abbr{attrs}>{_text(content, modern=modern)}</abbr>"


@_el(
    "nav-a",
    ("class", "href", "content", "id"),
    "Navbar-flavoured anchor; close with $_a.",
)
def nav_a(class_, href, content, id, *, modern=False):
    attrs = _attrs([("class", class_), ("href", href), ("id", id)],
                   modern=modern)
    return f"<a{attrs}>{_text(content, modern=modern)}"
nav_a.__name__ = "nav-a"


@_el("video", ("src",), "HTML5 video player with fixed dimensions.")
def video(src, *, modern=False):
    if not modern:
        return (
            '<video width="320" height="240" controls>'
            f'<source src="{src}" type="video/mp4"></video>'
        )
    src = _html.escape(src, quote=True)
    return (
        '<video width="320" height="240" controls>'
        f'<source src="{src}" type="video/mp4"></video>'
    )


@_el("iframe", ("src", "class"), "Iframe with fixed dimensions.")
def iframe(src, class_, *, modern=False):  # noqa: A002
    if not modern:
        return (
            f'<iframe src="{src}" width="480" height="222" frameBorder="0" '
            f'class="{class_}" allowFullScreen></iframe>'
        )
    attrs = _attrs(
        [
            ("src", src),
            ("width", "480"),
            ("height", "222"),
            ("frameBorder", "0"),
            ("class", class_),
        ],
        modern=True,
    )
    return f"<iframe{attrs} allowFullScreen></iframe>"


@_el(
    "svg",
    (
        "aria_labelledby",
        "role",
        "viewbox",
        "fill",
        "title_id",
        "title_lang",
        "title",
        "path_d",
        "xmlns",
    ),
    "Inline SVG figure.",
)
def svg(
    aria_labelledby,
    role,
    viewbox,
    fill,
    title_id,
    title_lang,
    title_,
    path_d,
    xmlns,
    *,
    modern=False,
):
    attrs = _attrs(
        [
            ("aria-labelledby", aria_labelledby),
            ("role", role),
            ("viewbox", viewbox),
            ("fill", fill),
        ],
        modern=modern,
    )
    title_attrs = _attrs(
        [("id", title_id), ("lang", title_lang)], modern=modern
    )
    path_attrs = _attrs([("d", path_d), ("xmlns", xmlns)], modern=modern)
    return (
        f"<svg{attrs}><title{title_attrs}>"
        f"{_text(title_, modern=modern)}</title>"
        f"<path{path_attrs}{'' if modern else '/'}></svg>"
    )


@_el("svgSimple", ("width", "height"), "Minimal SVG element; close with $_svg.")
def svgSimple(width, height, *, modern=False):
    attrs = _attrs([("width", width), ("height", height)], modern=modern)
    return f"<svg{attrs}>"
svgSimple.__name__ = "svgSimple"


def _collect() -> Dict[str, Element]:
    registry: Dict[str, Element] = {}
    for value in list(globals().values()):
        element = getattr(value, "_element", None)
        if isinstance(element, Element):
            registry[element.name] = element
    return registry


ELEMENTS: Dict[str, Element] = _collect()


def render_call(name: str, args: List[ArgValue], line=None, modern: bool = False) -> str:
    """Render one tag call to HTML.

    ``args`` values may be ``None`` for arguments that were not supplied; they
    are padded with empty strings to match the legacy bash behaviour.
    """
    element = ELEMENTS.get(name)
    if element is None:
        raise HtvlUnknownTagError(name, line)
    padded = _pad(name, element.params, args, line)
    return element.render(*padded, modern=modern)

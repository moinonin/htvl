"""The HTVL tag registry.

Every ``$(name ...)`` call in an HTVL file maps to one function in this module.
The registry is a faithful port of the original 2020 bash implementation (see
``docs/recovered-legacy-compiler.sh``): argument order, attribute order and even
a few cosmetic quirks of the emitted HTML are preserved so that existing
``.htvl`` files compile to byte-identical output. Quirks are marked ``[legacy]``
and collected in docs/grammar.md.

Each element declares its parameters in order; calling a tag with fewer
arguments than declared pads the missing ones with empty strings, exactly like
the original shell functions did.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Tuple, Union

from .errors import HtvlArityError, HtvlUnknownTagError

ArgValue = Union[str, None]


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


# ---------------------------------------------------------------------------
# Elements
# ---------------------------------------------------------------------------


def _el(name, params, doc=""):
    def decorate(fn):
        fn._element = Element(name=name, params=params, render=fn, doc=doc)
        return fn

    return decorate


@_el(
    "h",
    ("level", "class", "id", "content", "style"),
    "Heading of any level; renders a complete <hN>...</hN> pair.",
)
def h(level, class_, id, content, style):  # noqa: A002 - mirrors legacy names
    return (
        f'<h{level} class="{class_}" id="{id}" style="{style}">'
        f"{content}</h{level}>"
    )


@_el(
    "div",
    ("class", "id", "style"),
    "Generic container; close with $_div.",
)
def div(class_, id, style):  # noqa: A002
    return f'<div class="{class_}" id="{id}" style="{style}">'


@_el(
    "a",
    ("class", "href", "content", "id", "target", "aria_pressed", "style"),
    "Anchor. Renders the open tag plus content; close with $_a. "
    "[legacy] a hardcoded, always-empty role attribute.",
)
def a(class_, href, content, id, target, aria_pressed, style):  # noqa: A002
    return (
        f'<a class="{class_}" href="{href}" id="{id}" target="{target}" '
        f'role="" aria-pressed="{aria_pressed}" style="{style}">{content}'
    )


@_el(
    "p",
    ("class", "id", "content", "style"),
    "Paragraph. Renders the open tag plus content; close with $_p.",
)
def p(class_, id, content, style):  # noqa: A002
    return f'<p class="{class_}" id="{id}" style="{style}">{content}'


@_el("span", ("class",), "Inline span. [legacy] emits class only, with a space before '>'.")
def span(class_):  # noqa: A002
    return f'<span class="{class_}" >'


@_el("nav", ("class",), "Navigation landmark; close with $_nav.")
def nav(class_):  # noqa: A002
    return f'<nav class="{class_}">'


@_el("ul", ("class",), "Unordered list; close with $_ul.")
def ul(class_):  # noqa: A002
    return f'<ul class="{class_}">'


@_el("li", ("class",), "List item; close with $_li.")
def li(class_):  # noqa: A002
    return f'<li class="{class_}">'


@_el("footer", ("class",), "Footer landmark; close with $_footer.")
def footer(class_):  # noqa: A002
    return f'<footer class="{class_}">'


@_el("i", ("class",), "Icon (e.g. Font Awesome). [legacy] renders a full pair with a stray space inside.")
def i(class_):  # noqa: A002
    return f'<i class="{class_}"> </i>'


@_el("img", ("src", "alt", "style"), "Image (void element).")
def img(src, alt, style):
    return f'<img src="{src}" alt="{alt}" style="{style}">'


@_el(
    "input",
    ("class", "type", "aria_label", "value", "placeholder", "onclick"),
    "Form input (void element). [legacy] onClick sits last in the emitted "
    "attributes even though it is the last parameter.",
)
def input_(class_, type_, aria_label, value, placeholder, onclick):
    return (
        f'<input class="{class_}" type="{type_}" aria-label="{aria_label}" '
        f'value="{value}" onClick="{onclick}" placeholder="{placeholder}"/>'
    )
input_.__name__ = "input"


@_el(
    "btn",
    ("class", "type", "value", "onclick", "data_toggle", "data_target", "style"),
    "Button; close with $_btn.",
)
def btn(class_, type_, value, onclick, data_toggle, data_target, style):
    return (
        f'<button class="{class_}" type="{type_}" value="{value}" '
        f'onClick="{onclick}" data-toggle="{data_toggle}" '
        f'data-target="{data_target}" style="{style}">'
    )


@_el(
    "form",
    ("class", "action", "method", "style"),
    "Form; close with $_form.",
)
def form(class_, action, method, style):
    return (
        f'<form class="{class_}" action="{action}" method="{method}" '
        f'style="{style}">'
    )


@_el("title", ("id", "content"), "Document title. [legacy] lang is hardcoded to 'en'.")
def title(id, content):
    return f'<title id="{id}" lang="en">{content}</title>'


@_el(
    "link",
    ("rel", "type", "href", "integrity", "crossorigin"),
    "Stylesheet/icon link (void element). "
    "[legacy] emits 'rel = ' and 'type = ' with spaces around the '='.",
)
def link(rel, type_, href, integrity, crossorigin):
    return (
        f'<link rel = "{rel}" type = "{type_}" href = "{href}" '
        f'integrity="{integrity}" crossorigin="{crossorigin}">'
    )


@_el("script", ("src", "type", "content"), "Script tag; renders a complete pair.")
def script(src, type_, content):
    return f'<script src="{src}" type="{type_}">{content}</script>'


@_el(
    "metaLink",
    ("name", "content", "http_equiv"),
    "Meta tag (void element).",
)
def metaLink(name, content, http_equiv):
    return f'<meta name="{name}" content="{content}" http-equiv="{http_equiv}"/>'


@_el("comment", ("content",), "HTML comment.")
def comment(content):
    return f"<!-- {content} -->"


@_el("bsCdn", ("version",), "Bootstrap CDN URL for the given version.")
def bsCdn(version):
    return (
        f"https://stackpath.bootstrapcdn.com/bootstrap/{version}"
        f"/css/bootstrap.min.css"
    )


@_el("label", ("for_", "class", "content"), "Form label; renders a complete pair.")
def label(for_, class_, content):
    return f'<label for="{for_}" class="{class_}">{content}</label>'


@_el("path", ("fill", "d"), "SVG path (void element).")
def path(fill, d):
    return f'<path fill="{fill}" d="{d}"/>'


@_el("section", ("class", "id"), "Section landmark; close with $_section.")
def section(class_, id):
    return f'<section class="{class_}" id="{id}">'


@_el("strong", ("content",), "Strong emphasis; renders a complete pair.")
def strong(content):
    return f"<strong>{content}</strong>"


@_el("b", ("class", "content"), "Bold text; renders a complete pair.")
def b(class_, content):
    return f'<b class="{class_}">{content}</b>'


@_el("abbr", ("title", "content"), "Abbreviation; renders a complete pair.")
def abbr(title_, content):
    return f'<abbr title="{title_}">{content}</abbr>'


@_el(
    "nav-a",
    ("class", "href", "content", "id"),
    "Navbar-flavoured anchor; close with $_a.",
)
def nav_a(class_, href, content, id):
    return f'<a class="{class_}" href="{href}" id="{id}">{content}'
nav_a.__name__ = "nav-a"


@_el("video", ("src",), "HTML5 video player with fixed dimensions.")
def video(src):
    return (
        f'<video width="320" height="240" controls>'
        f'<source src="{src}" type="video/mp4"></video>'
    )


@_el("iframe", ("src", "class"), "Iframe with fixed dimensions.")
def iframe(src, class_):
    return (
        f'<iframe src="{src}" width="480" height="222" frameBorder="0" '
        f'class="{class_}" allowFullScreen></iframe>'
    )


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
):
    return (
        f'<svg aria-labelledby="{aria_labelledby}" role="{role}" '
        f'viewbox="{viewbox}" fill="{fill}">'
        f'<title id="{title_id}" lang="{title_lang}">{title_}</title>'
        f'<path d="{path_d}" xmlns="{xmlns}"/></svg>'
    )


@_el("svgSimple", ("width", "height"), "Minimal SVG element; close with $_svg.")
def svgSimple(width, height):
    return f'<svg width="{width}" height="{height}">'
svgSimple.__name__ = "svgSimple"


def _collect() -> Dict[str, Element]:
    registry: Dict[str, Element] = {}
    for value in list(globals().values()):
        element = getattr(value, "_element", None)
        if isinstance(element, Element):
            registry[element.name] = element
    return registry


ELEMENTS: Dict[str, Element] = _collect()


def render_call(name: str, args: List[ArgValue], line=None) -> str:
    """Render one tag call to HTML.

    ``args`` values may be ``None`` for arguments that were not supplied; they
    are padded with empty strings to match the legacy bash behaviour.
    """
    element = ELEMENTS.get(name)
    if element is None:
        raise HtvlUnknownTagError(name, line)
    padded = _pad(name, element.params, args, line)
    return element.render(*padded)

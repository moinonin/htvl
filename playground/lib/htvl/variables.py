"""Built-in HTVL variables.

A bare ``$name`` reference expands to one of these values. Variables starting
with an underscore are closing tags (``$_a`` -> ``</a>``); the rest are opening
tags or multi-line blocks such as ``$meta``.
"""

from __future__ import annotations

META_BLOCK = (
    "<meta charset=\"UTF-8\">\n"
    "<meta name=\"description\" content=\"Functional CSS Founders\">\n"
    "<meta name=\"keywords\" content=\"HTML,CSS,XML,JavaScript\">\n"
    "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">"
)

VARIABLES = {
    # Document skeleton
    "DOCTYPE_htvl": "<!DOCTYPE html>",
    "htvl": '<html lang="en">',
    "_html": "</html>",
    "_htvl": "</html>",
    "head": "<head>",
    "_head": "</head>",
    "body": "<body>",
    "_body": "</body>",
    # Head content
    "meta": META_BLOCK,
    # Standalone opening tags
    "p": "<p>",
    "ul": "<ul>",
    "div": "<div>",
    "svg": "<svg>",
    "strong": "<strong>",
    "br": "<br>",
    # Closing tags
    "_br": "</br>",
    "_a": "</a>",
    "_p": "</p>",
    "_ul": "</ul>",
    "_li": "</li>",
    "_div": "</div>",
    "_btn": "</button>",
    "_nav": "</nav>",
    "_span": "</span>",
    "_svg": "</svg>",
    "_iframe": "</iframe>",
    "_script": "</script>",
    "_section": "</section>",
    "_strong": "</strong>",
    "_form": "</form>",
    "_footer": "</footer>",
}

"""Built-in variable tests."""

from __future__ import annotations

from htvl.variables import VARIABLES


def test_document_skeleton():
    assert VARIABLES["DOCTYPE_htvl"] == "<!DOCTYPE html>"
    assert VARIABLES["htvl"] == '<html lang="en">'
    assert VARIABLES["_htvl"] == "</html>"
    assert VARIABLES["head"] == "<head>"
    assert VARIABLES["_head"] == "</head>"
    assert VARIABLES["body"] == "<body>"
    assert VARIABLES["_body"] == "</body>"
    assert VARIABLES["br"] == "<br>"


def test_closing_tags():
    for name, tag in [
        ("_a", "</a>"),
        ("_p", "</p>"),
        ("_ul", "</ul>"),
        ("_li", "</li>"),
        ("_div", "</div>"),
        ("_btn", "</button>"),
        ("_nav", "</nav>"),
        ("_span", "</span>"),
        ("_form", "</form>"),
        ("_footer", "</footer>"),
    ]:
        assert VARIABLES[name] == tag


def test_meta_block_is_multiline():
    lines = VARIABLES["meta"].split("\n")
    assert len(lines) == 4
    assert lines[0] == '<meta charset="UTF-8">'
    assert 'name="description"' in lines[1]

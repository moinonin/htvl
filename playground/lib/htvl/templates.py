"""Loading of HTVL templates.

A *template* is a named chunk of HTVL source that can be spliced into any
document with a plain ``$name`` reference, e.g. ``$headtags`` or ``${nav0[@]}``.

Two template sources are supported:

1. ``templates/*.htvl`` - plain HTVL files; the file name (without extension)
   is the variable name. This is the recommended format for new projects.
2. ``templates/*.sh`` - the legacy bash format used by the 2020 prototype.
   Each ``read -r -d '' NAME <<- EOM ... EOM`` block registers one template
   named ``NAME``. Kept so existing projects keep working unchanged.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, Optional

_LEGACY_HEREDOC = re.compile(
    r"read\s+-r\s+-d\s+''\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*<<-\s*(?P<tag>\w+)"
    r"(?P<body>.*?)^\s*(?P=tag)\s*$",
    re.DOTALL | re.MULTILINE,
)


def load_templates(directory: Optional[Path]) -> Dict[str, str]:
    """Load every template found in ``directory``.

    Values are stripped of surrounding whitespace; the compiler re-applies the
    indentation of the referencing line to the first line of the expansion,
    which reproduces the legacy bash behaviour exactly.
    """
    templates: Dict[str, str] = {}
    if directory is None:
        return templates
    directory = Path(directory)
    if not directory.is_dir():
        return templates

    for path in sorted(directory.iterdir()):
        if path.name.startswith("."):
            continue
        if path.suffix == ".htvl":
            templates[path.stem] = path.read_text(encoding="utf-8").strip()
        elif path.suffix == ".sh":
            text = path.read_text(encoding="utf-8")
            for match in _LEGACY_HEREDOC.finditer(text):
                body = match.group("body")
                # Drop the newline that terminates the heredoc marker line.
                if body.startswith("\n"):
                    body = body[1:]
                templates[match.group("name")] = body.strip()
    return templates

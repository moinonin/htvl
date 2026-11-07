#!/usr/bin/env python3
"""Copy the HTVL package into the playground.

The playground runs the real Python compiler in the browser (via Pyodide), so
it needs the package sources available over HTTP next to index.html. This
script keeps ``playground/lib/`` in sync with ``htvl/`` and writes a manifest
the page fetches at boot.

Run it whenever the package changes:

    python3 playground/sync.py
"""

from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path

PLAYGROUND = Path(__file__).resolve().parent
REPO_ROOT = PLAYGROUND.parent
PACKAGE = REPO_ROOT / "htvl"
LIB_DIR = PLAYGROUND / "lib" / "htvl"


def package_version() -> str:
    init = (PACKAGE / "__init__.py").read_text(encoding="utf-8")
    match = re.search(r'__version__\s*=\s*"([^"]+)"', init)
    if not match:
        sys.exit("could not read __version__ from htvl/__init__.py")
    return match.group(1)


def main() -> int:
    files = sorted(path.name for path in PACKAGE.glob("*.py"))
    if not files:
        sys.exit(f"no python files found in {PACKAGE}")

    (PLAYGROUND / "lib").mkdir(exist_ok=True)
    if LIB_DIR.exists():
        shutil.rmtree(LIB_DIR)
    LIB_DIR.mkdir(parents=True)

    for name in files:
        shutil.copy2(PACKAGE / name, LIB_DIR / name)

    manifest = {
        "files": files,
        "package": "htvl",
        "version": package_version(),
    }
    (PLAYGROUND / "lib" / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(f"synced htvl {manifest['version']} ({len(files)} files) -> {LIB_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

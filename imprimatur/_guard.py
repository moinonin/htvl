"""Subprocess timeout guard for large inputs.

Recon (docs/recon.md Q6, docs/decisions.md D5): a CPU-bound pure-Python
compile cannot be interrupted in-process, so the timeout the oracle promises
is enforceable only out-of-process. Inputs up to ``IN_PROCESS_LIMIT`` compile
in-process (the repair loop's hot path - no subprocess cost). Larger inputs
run in a child process with a wall-clock timeout; ``TimeoutExpired`` maps to
``Code.TIMEOUT``.

The child imports this same package and calls the in-process path, so the
error mapping is written once. The source travels over stdin: no temporary
files, no filesystem writes anywhere in this module.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Optional

_PACKAGE_ROOT = str(Path(__file__).resolve().parent.parent)

_CHILD_SOURCE = """
import json, sys

sys.path.insert(0, {root!r})
from imprimatur import _check_local

payload = json.loads(sys.stdin.read())
result = _check_local(payload["source"], modern=payload["modern"])
sys.stdout.write(json.dumps({{
    "ok": result.ok,
    "html": result.html,
    "diagnostics": [d.as_dict() for d in result.diagnostics],
    "elapsed_ms": result.elapsed_ms,
}}))
"""


def check_guarded(source: str, modern: bool, timeout: float) -> dict:
    """Compile ``source`` in a child process under a wall-clock timeout.

    Returns the child's JSON payload. Raises ``subprocess.TimeoutExpired``
    when the timeout is exceeded - the caller maps that to ``Code.TIMEOUT``.
    """
    program = _CHILD_SOURCE.format(root=_PACKAGE_ROOT)
    payload = json.dumps({"source": source, "modern": modern})
    completed = subprocess.run(
        [sys.executable, "-c", program],
        input=payload,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip()[-400:] or "guard child failed")
    return json.loads(completed.stdout)

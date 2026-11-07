"""HTVL - a tiny HTML transpiler.

Public API::

    from htvl import compile_source, compile_file, compile_project

    html = compile_source("$(h 1 '' '' 'Hello' '')")
"""

from __future__ import annotations

from .emitter import Emitter, emit
from .errors import (
    HtvlArityError,
    HtvlError,
    HtvlSyntaxError,
    HtvlUnknownTagError,
    HtvlUnknownVariableError,
)
from .parser import parse
from .project import (
    CompileResult,
    compile_file,
    compile_project,
    compile_source,
)

__version__ = "0.2.0"

__all__ = [
    "__version__",
    "compile_source",
    "compile_file",
    "compile_project",
    "CompileResult",
    "parse",
    "emit",
    "Emitter",
    "HtvlError",
    "HtvlSyntaxError",
    "HtvlUnknownTagError",
    "HtvlUnknownVariableError",
    "HtvlArityError",
]

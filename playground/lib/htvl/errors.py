"""Exception types raised by the HTVL compiler.

Every error carries the source location (line/column, 1-based) when available so
the CLI can point at the exact spot in a ``.htvl`` file that needs fixing.
"""

from __future__ import annotations

from typing import Optional


class HtvlError(Exception):
    """Base class for every error raised while compiling HTVL."""


class HtvlSyntaxError(HtvlError):
    """The source text could not be tokenized (unbalanced ``$(`` etc.)."""

    def __init__(
        self,
        message: str,
        line: Optional[int] = None,
        column: Optional[int] = None,
    ) -> None:
        self.message = message
        self.line = line
        self.column = column
        super().__init__(self._format())

    def _format(self) -> str:
        location = ""
        if self.line is not None:
            location = f" (line {self.line}"
            if self.column is not None:
                location += f", column {self.column}"
            location += ")"
        return f"{self.message}{location}"


class HtvlUnknownTagError(HtvlError):
    """A ``$(name ...)`` call referenced a tag that does not exist."""

    def __init__(self, name: str, line: Optional[int] = None) -> None:
        self.name = name
        self.line = line
        message = f"unknown tag '{name}'"
        if line is not None:
            message += f" (line {line})"
        message += ". Run 'htvl list' to see every available tag."
        super().__init__(message)


class HtvlUnknownVariableError(HtvlError):
    """A ``$name`` reference could not be resolved to a variable or template."""

    def __init__(self, name: str, line: Optional[int] = None) -> None:
        self.name = name
        self.line = line
        message = f"unknown variable '${name}'"
        if line is not None:
            message += f" (line {line})"
        message += ". Check the spelling, or define it in templates/."
        super().__init__(message)


class HtvlArityError(HtvlError):
    """A call passed more arguments than the tag accepts."""

    def __init__(
        self,
        name: str,
        expected: int,
        got: int,
        line: Optional[int] = None,
    ) -> None:
        self.name = name
        self.expected = expected
        self.got = got
        message = (
            f"tag '{name}' accepts at most {expected} argument(s), got {got}"
        )
        if line is not None:
            message += f" (line {line})"
        super().__init__(message)

"""Model adapters.

The experiment's unit of comparison is a *model*, so the harness talks to one
narrow protocol (docs/EXPERIMENT.md §5.2):

    generate(intent) -> str
    repair(source, diagnostic, hint) -> str
    tokens_used -> int          # cumulative, prompt + completion

Any backend plugs in. A deterministic, keyless stub ships here so the whole
pipeline runs in CI; it is excluded from all reported results (protocol §5.3).
"""

from __future__ import annotations

import hashlib
from typing import Dict, List, Protocol, runtime_checkable

import imprimatur


@runtime_checkable
class Model(Protocol):
    """The adapter every arm speaks to."""

    def generate(self, intent: str) -> str: ...

    def repair(self, source: str, diagnostic: dict, hint: str) -> str: ...

    @property
    def tokens_used(self) -> int: ...


def _estimate_tokens(text: str) -> int:
    """A crude, deterministic token estimate (chars/4) - proxy only, stated as
    such in the report (protocol §11)."""
    return max(1, len(text) // 4)


class StubModel:
    """A deterministic rule-based stand-in.

    ``generate`` builds a document from the intent and injects ONE defect
    chosen by a hash of the intent, so first-pass output usually fails.
    ``repair`` fixes exactly the diagnostic it is handed, by rule. That gives
    the harness a model whose failures, repairs and token counts are all
    reproducible without an API key - which is what makes the plumbing
    testable. It says nothing about real models.
    """

    name = "stub"

    # Weighted defect set: a real model sometimes gets it right first time, so
    # the stub emits clean documents for a deterministic share of intents
    # (~40%). Without that, the control arm's compile rate is 0 and the
    # primary metric R = C_treat/C_ctrl is undefined.
    _DEFECTS = (
        "clean",
        "clean",
        "unknown_tag",
        "unclosed",
        "extra_args",
        "bad_variable",
    )

    def __init__(self) -> None:
        self._tokens = 0
        self.calls = 0

    # -- generate ----------------------------------------------------------

    def _defect_for(self, intent: str) -> str:
        digest = hashlib.sha256(intent.encode("utf-8")).hexdigest()
        return self._DEFECTS[int(digest[:8], 16) % len(self._DEFECTS)]

    def generate(self, intent: str) -> str:
        self.calls += 1
        title = intent.split(".")[0][:60] or "Document"
        defect = self._defect_for(intent)

        nav = "\n".join(
            f"      $(a 'nav-link' '#s{number}' 'Section {number}' '' '' '' '')$_a"
            for number in (1, 2, 3)
        )
        rows = "\n".join(
            f"        $(li '')Item {number}$_li" for number in (1, 2, 3)
        )
        paragraph = f"$(p '' '' '{title}' '')\n    $_p"

        if defect == "unknown_tag":
            paragraph = paragraph.replace("$(p ", "$(paragraph ", 1)
        elif defect == "extra_args":
            paragraph = paragraph.replace(
                "$(p '' '' '" + title + "' '')",
                "$(p '' '' '" + title + "' '' 'extra' 'very')",
                1,
            )
        elif defect == "bad_variable":
            paragraph = paragraph + "\n    $titel"

        lines = [
            "$DOCTYPE_htvl",
            "$htvl",
            "$head",
            f"  $(title '' '{title}')",
            "  $meta",
            "$_head",
            "$body",
            "  $(nav 'navbar')",
            nav,
            "  $_nav",
            "  $(div 'container')",
            f"    $(h 1 '' 'title' '{title}' '')",
            f"    {paragraph}",
            "    $(div 'table')",
            "      $(ul 'rows')",
            rows,
            "      $_ul",
            "    $_div",
        ]
        if defect == "unclosed":
            # The container div is never closed.
            lines.append("$_body")
            lines.append("$_htvl")
        else:
            lines.append("    $_div")
            lines.append("$_body")
            lines.append("$_htvl")
        source = "\n".join(lines) + "\n"
        self._tokens += _estimate_tokens(intent) + _estimate_tokens(source)
        return source

    # -- repair ------------------------------------------------------------

    def repair(self, source: str, diagnostic: dict, hint: str) -> str:
        self.calls += 1
        code = diagnostic.get("code")
        detail = diagnostic.get("detail") or ""
        line = diagnostic.get("line") or 0
        lines = source.splitlines()
        fixed = source

        if code == "UNKNOWN_TAG":
            suggestion = self._nearest_tag(detail)
            fixed = source.replace(f"$({detail}", f"$({suggestion}", 1)
        elif code == "UNKNOWN_VARIABLE":
            suggestion = self._nearest_variable(detail)
            fixed = source.replace(f"${detail}", f"${suggestion}", 1)
        elif code == "BAD_ARG_COUNT":
            fixed = self._trim_args(source, detail)
        elif code == "UNCLOSED_TAG":
            fixed = source.rstrip("\n") + "\n" + self._closer_for(detail) + "\n"
        elif code == "UNEXPECTED_CLOSE":
            closer = f"$_{detail}"
            index = max(0, line - 1)
            if index < len(lines) and closer in lines[index]:
                lines[index] = lines[index].replace(closer, "")
                fixed = "\n".join(lines) + "\n"
        elif code in ("UNTERMINATED_STR", "SYNTAX"):
            fixed = source.rstrip("\n") + "')\n"

        self._tokens += (
            _estimate_tokens(source)
            + _estimate_tokens(str(diagnostic))
            + _estimate_tokens(fixed)
        )
        return fixed

    # -- helpers -----------------------------------------------------------

    @staticmethod
    def _nearest_tag(name: str) -> str:
        import difflib

        tags = imprimatur.tag_signatures()
        names = [sig.split()[0][2:] for sig in tags]
        matches = difflib.get_close_matches(name, names, n=1, cutoff=0.3)
        return matches[0] if matches else "div"

    @staticmethod
    def _nearest_variable(name: str) -> str:
        import difflib

        variables = [
            line.split(" ")[0][1:] for line in imprimatur.variable_signatures()
        ]
        matches = difflib.get_close_matches(name, variables, n=1, cutoff=0.3)
        return matches[0] if matches else "meta"

    @staticmethod
    def _closer_for(tag: str) -> str:
        if tag == "nav-a":
            return "$_a"
        if tag == "svgSimple":
            return "$_svg"
        return f"$_{tag}"

    @staticmethod
    def _trim_args(source: str, tag: str) -> str:
        """Drop surplus arguments from the first $(tag ...) call."""
        import re

        pattern = re.compile(r"\$\(\s*" + re.escape(tag) + r"\b[^)]*\)")
        match = pattern.search(source)
        if not match:
            return source
        call = match.group(0)
        inner = call[2:-1].split()
        # Keep the tag name plus at most three arguments.
        keep = inner[:4]
        rendered = " ".join(f"'{part}'" for part in keep[1:])
        trimmed = f"$({keep[0]}" + (f" {rendered}" if rendered else "") + ")"
        return source.replace(call, trimmed, 1)

    @property
    def tokens_used(self) -> int:
        return self._tokens


def load_model(name: str) -> Model:
    """Resolve a model adapter by name. 'stub' is the only keyless option;
    anything else is a plug-in point for a real backend (see README)."""
    if name == "stub":
        return StubModel()
    raise SystemExit(
        f"unknown model '{name}'. 'stub' ships with the harness; implement the "
        "Model protocol (imprimatur_eval.models) to plug in a real backend."
    )

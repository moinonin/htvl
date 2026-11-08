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
import json
from pathlib import Path
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


class OllamaModel:
    """A real model: a local Ollama server (stdlib urllib, no SDK).

    This is the model the Stage 4 measurement runs on. Local inference means
    no API keys, no network egress and no spend - and it is one of the
    brief's four scenarios (regulated teams that must run the model
    on-machine).

    Token accounting uses the counts Ollama reports (prompt_eval_count +
    eval_count), so ``tokens_used`` is measured, not estimated.
    """

    def __init__(
        self,
        model: str = "qwen2.5-coder:7b-instruct",
        base_url: str = "http://localhost:11434",
        temperature: float = 0.0,
        timeout: float = 300.0,
    ) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.temperature = temperature
        self.timeout = timeout
        self.name = f"ollama/{model}"
        self._tokens = 0
        self.calls = 0

    # -- transport ---------------------------------------------------------

    def _post(self, path: str, payload: dict) -> dict:
        import urllib.request

        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(
            request, timeout=self.timeout
        ) as response:
            return json.loads(response.read().decode("utf-8"))

    def _chat(self, prompt: str) -> str:
        data = self._post(
            "/api/generate",
            {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": self.temperature},
            },
        )
        self.calls += 1
        self._tokens += data.get("prompt_eval_count", 0) + data.get(
            "eval_count", 0
        )
        return data.get("response", "")

    # -- Model protocol ----------------------------------------------------

    def generate(self, intent: str) -> str:
        prompt = _load_prompt("base.md").replace(
            "{tags}", "\n".join(imprimatur.tag_signatures())
        )
        return extract_htvl(self._chat(f"{prompt}\nIntent: {intent}\n"))

    def repair(self, source: str, diagnostic: dict, hint: str) -> str:
        template = _load_prompt("repair.md")
        prompt = (
            template.replace("{code}", str(diagnostic.get("code", "")))
            .replace("{line}", str(diagnostic.get("line", "")))
            .replace("{hint}", hint)
            .replace(
                "{windowed_source}",
                numbered_window(source, diagnostic.get("line", 0)),
            )
        )
        return extract_htvl(self._chat(prompt))

    @property
    def tokens_used(self) -> int:
        return self._tokens


def _load_prompt(name: str) -> str:
    path = Path(__file__).resolve().parent.parent / "prompts" / name
    return path.read_text(encoding="utf-8")


def numbered_window(source: str, line: int, context: int = 5) -> str:
    """The source with line numbers and the offending line marked - the edit
    scope the repair prompt asks the model to stay inside."""
    lines = source.splitlines()
    if not lines:
        return source
    low = max(1, line - context)
    high = min(len(lines), line + context)
    rendered = []
    for number in range(low, high + 1):
        marker = ">>" if number == line else "  "
        rendered.append(f"{marker} {number:>4} | {lines[number - 1]}")
    return "\n".join(rendered)


def extract_htvl(response: str) -> str:
    """Pull the document out of a model reply.

    Models wrap output in fences or add prose; the compiler wants source.
    Prefer the first fenced block that looks like HTVL, else the whole reply.
    """
    import re

    blocks = re.findall(r"```(?:\w*)\n([\s\S]*?)```", response)
    for block in blocks:
        if "$(" in block or "$h" in block or "$DOCTYPE" in block:
            return block.strip("\n") + "\n"
    stripped = response.strip()
    if "$(" in stripped or "$DOCTYPE" in stripped:
        return stripped + "\n"
    return stripped


def load_model(name: str) -> Model:
    """Resolve a model adapter by name.

    ``stub`` is the deterministic plumbing model. ``ollama/<model>`` runs a
    local Ollama server (no keys, no spend). The name is resolved here so the
    CLI never grows a branch per backend.
    """
    if name == "stub":
        return StubModel()
    if name.startswith("ollama/"):
        return OllamaModel(model=name.split("/", 1)[1])
    raise SystemExit(
        f"unknown model '{name}'. Use 'stub' or 'ollama/<model>' (a local "
        "Ollama model), or implement the Model protocol in models.py."
    )

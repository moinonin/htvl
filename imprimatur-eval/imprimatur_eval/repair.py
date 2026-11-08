"""Repair traces: labeled (error -> fix) pairs, produced for free.

The loop repairs ONE error at a time and scopes the model's edit to the
diagnostic it was handed, then records how much the model touched. That
record - `lines_touched` - is the metric that tests the whole thesis: repairs
of 2-4 lines mean bounded blast radius is real; repairs of 40 mean the model
is rewriting the document and line locality bought nothing.
"""

from __future__ import annotations

import difflib
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import imprimatur

MAX_ITERS = 6


def touched_lines(before: str, after: str) -> int:
    """Minimum line-level edit distance between two documents."""
    matcher = difflib.SequenceMatcher(
        None, before.splitlines(), after.splitlines()
    )
    return sum(
        max(i2 - i1, j2 - j1)
        for op, i1, i2, j1, j2 in matcher.get_opcodes()
        if op != "equal"
    )


@dataclass
class RepairStep:
    """One turn of the loop."""

    diagnostic: Dict
    hint: str
    before: str
    after: str
    lines_touched: int
    converged: bool  # did this single step produce a compiling document?


@dataclass
class RepairTrace:
    """The full loop for one document."""

    source: str
    steps: List[RepairStep] = field(default_factory=list)
    final_ok: bool = False
    final_source: str = ""
    aborted_no_progress: bool = False

    @property
    def iterations(self) -> int:
        return len(self.steps)

    @property
    def total_lines_touched(self) -> int:
        return sum(step.lines_touched for step in self.steps)


def repair_loop(model, source: str, max_iters: int = MAX_ITERS) -> RepairTrace:
    """Check, repair one diagnostic, recheck; stop at green, at the cap, or on
    no progress (protocol §6.3)."""
    trace = RepairTrace(source=source, final_source=source)
    signatures = imprimatur.tag_signatures()

    for _ in range(max_iters):
        result = imprimatur.check(source)
        if result.ok:
            trace.final_ok = True
            trace.final_source = source
            return trace

        diagnostic = result.diagnostics[0]  # one error at a time
        hint = imprimatur.explain(diagnostic, signatures)
        fixed = model.repair(source, diagnostic.as_dict(), hint)

        step = RepairStep(
            diagnostic=diagnostic.as_dict(),
            hint=hint,
            before=source,
            after=fixed,
            lines_touched=touched_lines(source, fixed),
            converged=imprimatur.check(fixed).ok,
        )
        trace.steps.append(step)

        if fixed == source:
            # No progress: abort early and record the failure (protocol §6.3).
            trace.aborted_no_progress = True
            trace.final_ok = False
            trace.final_source = source
            return trace
        source = fixed

    result = imprimatur.check(source)
    trace.final_ok = result.ok
    trace.final_source = source
    return trace


def trace_to_jsonl_record(trace: RepairTrace, intent: str, model_name: str) -> Dict:
    """One JSONL row per repair trace - the SFT export shape."""
    return {
        "intent": intent,
        "model": model_name,
        "final_ok": trace.final_ok,
        "aborted_no_progress": trace.aborted_no_progress,
        "iterations": trace.iterations,
        "lines_touched": trace.total_lines_touched,
        "steps": [
            {
                "diagnostic": step.diagnostic,
                "hint": step.hint,
                "lines_touched": step.lines_touched,
                "converged": step.converged,
            }
            for step in trace.steps
        ],
        "source": trace.final_source,
    }


def sft_records(trace: RepairTrace, intent: str, model_name: str) -> List[Dict]:
    """The flywheel: system = grammar + tag list, user = broken source plus
    structured error, assistant = the fixed source."""
    signatures = "\n".join(imprimatur.tag_signatures())
    records = []
    for step in trace.steps:
        records.append(
            {
                "intent": intent,
                "model": model_name,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You repair HTVL documents. The compiler reports "
                            "one diagnostic at a time; fix only that line "
                            "window.\n\n" + signatures
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"{step.before}\n\nDiagnostic: "
                            f"{step.diagnostic['code']} at line "
                            f"{step.diagnostic['line']}\nHint: {step.hint}"
                        ),
                    },
                    {"role": "assistant", "content": step.after},
                ],
            }
        )
    return records

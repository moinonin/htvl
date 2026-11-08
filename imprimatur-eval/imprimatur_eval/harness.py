"""The A/B harness - the numbers that decide whether the oracle ships.

Three arms (docs/EXPERIMENT.md §4.1):

    A - control:   one sample, no feedback
    B - treatment: generate, then the repair loop (<=6 iterations)
    C - ablation:  best-of-k selection, no repair

Metrics (protocol §7): C = tokens per correct document (the decision number),
p = compile rate, iterations, lines_touched, error-code distribution.
Inference: a paired bootstrap over tasks for the ratio R = C_treat/C_ctrl
(10,000 resamples, fixed seed) plus McNemar counts for the compile rates.

Everything here is stdlib and synchronous; ``evaluate`` returns one
JSON-serialisable dict so the CLI can render RESULTS.md straight from it.
"""

from __future__ import annotations

import random
import statistics
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

import imprimatur
from .repair import MAX_ITERS, repair_loop

BOOTSTRAP_RESAMPLES = 10_000
BOOTSTRAP_SEED = 20261107


@dataclass
class ArmResult:
    """One task's outcome in one arm."""

    task_id: str
    intent: str
    correct: bool
    tokens: int
    source: str
    iterations: Optional[int] = None
    lines_touched: Optional[int] = None
    codes: List[str] = field(default_factory=list)
    aborted_no_progress: bool = False

    def as_dict(self) -> Dict:
        return {
            "task_id": self.task_id,
            "correct": self.correct,
            "tokens": self.tokens,
            "iterations": self.iterations,
            "lines_touched": self.lines_touched,
            "codes": self.codes,
            "aborted_no_progress": self.aborted_no_progress,
        }


@dataclass
class ArmReport:
    """One arm's per-task results and aggregates."""

    name: str
    results: List[ArmResult]

    @property
    def n(self) -> int:
        return len(self.results)

    @property
    def correct(self) -> int:
        return sum(1 for r in self.results if r.correct)

    @property
    def tokens(self) -> int:
        return sum(r.tokens for r in self.results)

    @property
    def compile_rate(self) -> float:
        return self.correct / self.n if self.n else 0.0

    @property
    def tokens_per_correct(self) -> Optional[float]:
        return self.tokens / self.correct if self.correct else None

    @property
    def iterations(self) -> List[int]:
        return [r.iterations for r in self.results if r.iterations is not None]

    @property
    def lines_touched(self) -> List[int]:
        return [
            r.lines_touched
            for r in self.results
            if r.lines_touched is not None
        ]

    def error_codes(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for r in self.results:
            if not r.correct:
                for code in r.codes:
                    counts[code] = counts.get(code, 0) + 1
        return dict(sorted(counts.items(), key=lambda item: -item[1]))

    def summary(self) -> Dict:
        return {
            "arm": self.name,
            "n": self.n,
            "correct": self.correct,
            "compile_rate": round(self.compile_rate, 4),
            "tokens": self.tokens,
            "tokens_per_correct_doc": (
                round(self.tokens_per_correct, 2)
                if self.tokens_per_correct is not None
                else None
            ),
            "mean_iterations": (
                round(statistics.fmean(self.iterations), 3)
                if self.iterations
                else None
            ),
            "median_lines_touched": _median(self.lines_touched),
            "p90_lines_touched": _percentile(self.lines_touched, 90),
            "error_codes": self.error_codes(),
        }


# ---------------------------------------------------------------------------
# Arms
# ---------------------------------------------------------------------------


def run_arm_a(model, task: Dict) -> ArmResult:
    """Control: one sample, no feedback."""
    source = model.generate(task["intent"])
    result = imprimatur.check(source)
    return ArmResult(
        task_id=task["id"],
        intent=task["intent"],
        correct=result.ok,
        tokens=model.tokens_used,
        source=source,
        codes=[d.code.value for d in result.diagnostics],
    )


def run_arm_b(model, task: Dict, max_iters: int = MAX_ITERS) -> ArmResult:
    """Treatment: generate, then the repair loop. Tokens are the delta across
    the whole loop, generation included."""
    start = model.tokens_used
    source = model.generate(task["intent"])
    trace = repair_loop(model, source, max_iters=max_iters)
    return ArmResult(
        task_id=task["id"],
        intent=task["intent"],
        correct=trace.final_ok,
        tokens=model.tokens_used - start,
        source=trace.final_source,
        iterations=trace.iterations,
        lines_touched=trace.total_lines_touched,
        codes=[step.diagnostic["code"] for step in trace.steps],
        aborted_no_progress=trace.aborted_no_progress,
    )


def run_arm_c(model, task: Dict, k: int = 3) -> ArmResult:
    """Ablation: sample k documents, keep the first that compiles."""
    start = model.tokens_used
    codes: List[str] = []
    source = ""
    for _ in range(k):
        source = model.generate(task["intent"])
        result = imprimatur.check(source)
        if result.ok:
            return ArmResult(
                task_id=task["id"],
                intent=task["intent"],
                correct=True,
                tokens=model.tokens_used - start,
                source=source,
            )
        codes.extend(d.code.value for d in result.diagnostics)
    return ArmResult(
        task_id=task["id"],
        intent=task["intent"],
        correct=False,
        tokens=model.tokens_used - start,
        source=source,
        codes=codes,
    )


def evaluate(
    model,
    tasks: Sequence[Dict],
    with_oracle: bool = True,
    arm_c: bool = False,
    max_iters: int = MAX_ITERS,
    ablation_k: int = 3,
) -> Dict:
    """Run every task in every requested arm and return one report dict.

    Arm A always runs (it is the baseline); Arms B and C are opt-in.
    """
    control = ArmReport("control", [run_arm_a(model, t) for t in tasks])
    treatment = (
        ArmReport(
            "treatment", [run_arm_b(model, t, max_iters) for t in tasks]
        )
        if with_oracle
        else None
    )
    ablation = (
        ArmReport("ablation", [run_arm_c(model, t, ablation_k) for t in tasks])
        if arm_c
        else None
    )

    report = {"arms": {"control": control.summary()}}
    per_task = {"control": [r.as_dict() for r in control.results]}
    if treatment is not None:
        report["arms"]["treatment"] = treatment.summary()
        per_task["treatment"] = [r.as_dict() for r in treatment.results]
    if ablation is not None:
        report["arms"]["ablation"] = ablation.summary()
        per_task["ablation"] = [r.as_dict() for r in ablation.results]

    if treatment is not None:
        report["contrast"] = _contrast(control, treatment)
    if ablation is not None and control.tokens_per_correct:
        report["contrast_ablation_vs_control"] = _ratio(
            ablation, control
        )
    if (
        ablation is not None
        and treatment is not None
        and treatment.tokens_per_correct
    ):
        report["contrast_ablation_vs_treatment"] = _ratio(
            ablation, treatment
        )

    report["per_task"] = per_task
    return report


# ---------------------------------------------------------------------------
# Inference
# ---------------------------------------------------------------------------


def _ratio(treatment: ArmReport, control: ArmReport) -> Dict:
    """R = C_treatment / C_control with a paired bootstrap CI."""
    if not treatment.tokens_per_correct or not control.tokens_per_correct:
        return {"ratio_R": None, "ci95": None, "verdict": "INCONCLUSIVE"}
    ratio = treatment.tokens_per_correct / control.tokens_per_correct
    ci = _bootstrap_ratio_ci(treatment.results, control.results)
    return {
        "ratio_R": round(ratio, 4),
        "ci95": ci,
        "verdict": _verdict(ratio, ci),
    }


def _contrast(control: ArmReport, treatment: ArmReport) -> Dict:
    contrast = _ratio(treatment, control)
    contrast["mcnemar"] = _mcnemar(control.results, treatment.results)
    return contrast


def _bootstrap_ratio_ci(
    treatment: Sequence[ArmResult],
    control: Sequence[ArmResult],
    resamples: int = BOOTSTRAP_RESAMPLES,
    seed: int = BOOTSTRAP_SEED,
) -> Optional[Tuple[float, float]]:
    """Paired bootstrap over tasks: resample task indices and recompute both
    C's from the same indices (protocol §8). Deterministic: fixed seed."""
    rng = random.Random(seed)
    n = len(control)
    if n != len(treatment):
        raise ValueError("paired bootstrap requires equal-length arms")
    ratios: List[float] = []
    for _ in range(resamples):
        indices = [rng.randrange(n) for _ in range(n)]
        ctrl_correct = sum(1 for i in indices if control[i].correct)
        treat_correct = sum(1 for i in indices if treatment[i].correct)
        if not ctrl_correct or not treat_correct:
            continue
        ctrl_tokens = sum(control[i].tokens for i in indices)
        treat_tokens = sum(treatment[i].tokens for i in indices)
        ratios.append(
            (treat_tokens / treat_correct) / (ctrl_tokens / ctrl_correct)
        )
    if not ratios:
        return None
    ratios.sort()
    low = ratios[int(0.025 * len(ratios))]
    high = ratios[min(len(ratios) - 1, int(0.975 * len(ratios)))]
    return (round(low, 4), round(high, 4))


def _mcnemar(
    control: Sequence[ArmResult], treatment: Sequence[ArmResult]
) -> Dict[str, int]:
    pairs = zip(control, treatment)
    return {
        "both_correct": sum(1 for c, t in pairs if c.correct and t.correct),
        "control_only": sum(
            1 for c, t in zip(control, treatment)
            if c.correct and not t.correct
        ),
        "treatment_only": sum(
            1 for c, t in zip(control, treatment)
            if not c.correct and t.correct
        ),
        "neither": sum(
            1 for c, t in zip(control, treatment)
            if not c.correct and not t.correct
        ),
    }


def _verdict(ratio: float, ci: Optional[Tuple[float, float]]) -> str:
    """The pre-registered decision rule (protocol §9)."""
    if ci is None:
        return "INCONCLUSIVE (an arm produced no correct documents)"
    low, high = ci
    if ratio <= 0.80 and high < 1.00:
        return "SUPPORT"
    if ratio >= 1.20 and low > 1.00:
        return "REFUTE"
    return "INCONCLUSIVE"


# ---------------------------------------------------------------------------
# Small stats helpers (stdlib only)
# ---------------------------------------------------------------------------


def _median(values: Sequence[int]) -> Optional[float]:
    return statistics.median(values) if values else None


def _percentile(values: Sequence[int], percentile: int) -> Optional[float]:
    if not values:
        return None
    ordered = sorted(values)
    index = (percentile / 100) * (len(ordered) - 1)
    low = int(index)
    high = min(low + 1, len(ordered) - 1)
    return ordered[low] + (ordered[high] - ordered[low]) * (index - low)

"""imprimatur-eval tests: the harness runs end to end with the stub model.

No network, no API keys. The stub is deterministic, so every number here is
reproducible.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("imprimatur_eval", reason="imprimatur-eval package")

from imprimatur import check  # noqa: E402
from imprimatur_eval.dataset import build, code_distribution, load_tasks  # noqa: E402
from imprimatur_eval.harness import (  # noqa: E402
    _percentile,
    evaluate,
    run_arm_a,
    run_arm_b,
    run_arm_c,
)
from imprimatur_eval.models import StubModel, load_model  # noqa: E402
from imprimatur_eval.repair import (  # noqa: E402
    allowed_region,
    out_of_region,
    repair_loop,
    touched_lines,
)
from imprimatur_eval.report import render_results  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
EVAL_ROOT = REPO_ROOT / "imprimatur-eval"
TASKS = EVAL_ROOT / "tasks.jsonl"


@pytest.fixture(scope="module")
def tasks():
    return load_tasks(TASKS)


@pytest.fixture(scope="module")
def stub():
    return StubModel()


# ---------------------------------------------------------------------------
# The stub
# ---------------------------------------------------------------------------


def test_stub_is_deterministic(stub):
    intent = "A status page with three entries and a footer."
    first = stub.generate(intent)
    second = StubModel().generate(intent)
    assert first == second


def test_stub_produces_both_valid_and_invalid(stub):
    """A model that never compiles would make R undefined (D19)."""
    intents = [task["intent"] for task in load_tasks(TASKS)]
    sources = [stub.generate(intent) for intent in intents]
    valid = sum(1 for source in sources if check(source).ok)
    assert 0 < valid < len(sources)


def test_stub_repair_is_rule_based_and_bounded(stub):
    source = stub.generate("A status page with three entries and a footer.")
    trace = repair_loop(stub, source)
    assert trace.iterations <= 6
    if trace.steps:
        assert all(step.lines_touched <= 6 for step in trace.steps)


# ---------------------------------------------------------------------------
# Window enforcement (the line-locality fix)
# ---------------------------------------------------------------------------


def test_allowed_region_depends_on_the_code():
    """An unclosed tag's closer may go anywhere after the opening; a name or
    arity error is fixed on its own line."""
    source = "\n".join(f"line {n}" for n in range(1, 21))
    low, high = allowed_region(
        {"code": "UNKNOWN_TAG", "line": 10}, source
    )
    assert low == 5 and high == 15

    low, high = allowed_region({"code": "UNCLOSED_TAG", "line": 3}, source)
    assert low == 3 and high == 20


def test_out_of_region_counts_escapes():
    source = "\n".join(f"line {n}" for n in range(1, 21))
    before = source + "\n"
    # Change one in-region line and one far away.
    lines = before.splitlines()
    lines[9] = "CHANGED"      # line 10 - in region for a diagnostic on line 10
    lines[18] = "CHANGED"     # line 19 - outside
    after = "\n".join(lines) + "\n"
    assert out_of_region(before, after, (5, 15)) == 1


def test_rewriting_model_triggers_enforcement_and_is_recorded():
    """A model that rewrites the document gets re-asked, and the surviving
    violation is recorded rather than hidden."""

    class Rewriter:
        name = "rewriter"

        def __init__(self):
            self.calls = 0

        def generate(self, intent):
            return "$(dvi 'x')\n" + "\n".join(
                f"  $(p '' '' 'filler {n}' '')\n  $_p" for n in range(12)
            ) + "\n$_body\n"

        def repair(self, source, diagnostic, hint):
            self.calls += 1
            if "outside the allowed region" in hint:
                # The retry obeys the scope.
                return source.replace("$(dvi", "$(h 1 '' '' ", 1)
            # First attempt rewrites the whole document.
            return "REWRITTEN\n" * 30

        @property
        def tokens_used(self):
            return self.calls * 100

    model = Rewriter()
    trace = repair_loop(model, model.generate("x"), enforce_window=True)
    assert model.calls >= 2  # re-asked at least once
    assert any(step.enforced for step in trace.steps)


def test_in_region_repair_is_not_re_asked():
    """A disciplined model is never charged an extra call."""

    class Disciplined:
        name = "disciplined"

        def __init__(self):
            self.calls = 0

        def generate(self, intent):
            return "$(dvi 'x')\n"

        def repair(self, source, diagnostic, hint):
            self.calls += 1
            return source.replace("$(dvi", "$(h 1 '' '' ", 1)

        @property
        def tokens_used(self):
            return self.calls * 100

    model = Disciplined()
    trace = repair_loop(model, model.generate("x"), enforce_window=True)
    assert trace.final_ok
    assert not any(step.enforced for step in trace.steps)


def test_load_model_rejects_unknown():
    with pytest.raises(SystemExit):
        load_model("gpt-4o")


# ---------------------------------------------------------------------------
# Dataset builder
# ---------------------------------------------------------------------------


def test_build_labels_every_row(stub):
    intents = ["alpha page", "beta page"]
    rows = build(intents, stub, k=2)
    assert len(rows) == 4
    for row in rows:
        assert set(row) >= {"intent", "htvl", "valid", "codes"}
        assert isinstance(row["valid"], bool)


def test_code_distribution_counts_failures(stub):
    rows = build(["one intent"], stub, k=4)
    distribution = code_distribution(rows)
    assert sum(distribution.values()) <= sum(len(r["codes"]) for r in rows)


def test_tasks_file_is_well_formed(tasks):
    assert len(tasks) >= 20
    for task in tasks:
        assert task["id"] and task["intent"] and task["min_requirements"]


# ---------------------------------------------------------------------------
# Repair traces
# ---------------------------------------------------------------------------


def test_touched_lines_counts_edits():
    assert touched_lines("a\nb\nc\n", "a\nX\nc\n") == 1
    assert touched_lines("a\n", "a\n") == 0
    assert touched_lines("a\nb\n", "a\nb\nc\nd\n") == 2


def test_repair_loop_converges_or_aborts_cleanly(stub):
    intent = "A status page with three entries and a footer."
    trace = repair_loop(stub, stub.generate(intent))
    assert trace.iterations <= 6
    assert trace.final_ok == check(trace.final_source).ok
    if trace.aborted_no_progress:
        assert trace.final_ok is False


def test_repair_loop_reports_line_local_edits(stub):
    """The thesis: repairs are bounded, not rewrites."""
    intent = "A status page with three entries and a footer."
    trace = repair_loop(stub, stub.generate(intent))
    if trace.steps:
        assert trace.total_lines_touched <= len(stub.generate(intent).splitlines())


# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------


def test_arms_return_paired_results(stub, tasks):
    subset = tasks[:5]
    control = [run_arm_a(stub, t) for t in subset]
    treatment = [run_arm_b(stub, t) for t in subset]
    assert len(control) == len(treatment) == 5
    for c, t in zip(control, treatment):
        assert c.task_id == t.task_id
        assert t.tokens >= 0


def test_evaluate_produces_the_decision_numbers(stub, tasks):
    report = evaluate(stub, tasks, with_oracle=True)
    arms = report["arms"]
    assert arms["control"]["n"] == len(tasks)
    contrast = report["contrast"]
    # Both arms must be able to produce correct documents for R to exist.
    assert arms["control"]["tokens_per_correct_doc"] is not None
    assert arms["treatment"]["tokens_per_correct_doc"] is not None
    assert contrast["ratio_R"] is not None
    assert contrast["ci95"] is not None
    assert contrast["verdict"] in {"SUPPORT", "INCONCLUSIVE", "REFUTE"}
    assert "mcnemar" in contrast


def test_evaluate_without_oracle_runs_control_only(stub, tasks):
    report = evaluate(stub, tasks[:4], with_oracle=False)
    assert set(report["arms"]) == {"control"}
    assert "contrast" not in report


def test_ablation_arm(stub, tasks):
    results = [run_arm_c(stub, t) for t in tasks[:5]]
    assert all(r.tokens >= 0 for r in results)


def test_percentile_helper():
    assert _percentile([1, 2, 3, 4, 5], 90) == pytest.approx(4.6)
    assert _percentile([], 90) is None


def test_report_renders_results_md(stub, tasks):
    report = evaluate(stub, tasks, with_oracle=True)
    report["manifest"] = {"model": "stub", "n_tasks": len(tasks)}
    text = render_results(report)
    for heading in (
        "## 1. Manifest",
        "## 2. Primary contrast",
        "## 3. Secondary",
        "## 4. Descriptive",
        "## 5. Threats and limitations",
        "## 6. Verdict",
        "## 7. Reproduction",
    ):
        assert heading in text
    assert "stub" in text  # the stub caveat must be stated, not hidden


# ---------------------------------------------------------------------------
# CLI end to end
# ---------------------------------------------------------------------------


def _run_cli(args, cwd=REPO_ROOT):
    env_path = str(EVAL_ROOT)
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "imprimatur_eval",
            *args,
        ],
        capture_output=True,
        text=True,
        cwd=str(cwd),
        env={"PYTHONPATH": env_path, "PATH": "/usr/bin:/bin", "HOME": "/tmp"},
    )


def test_cli_build_repair_ab(tmp_path):
    data = tmp_path / "data.jsonl"
    built = _run_cli(["build", "--out", str(data), "--model", "stub"])
    assert built.returncode == 0, built.stderr
    rows = [json.loads(line) for line in data.read_text().splitlines() if line]
    assert rows and all("codes" in row for row in rows)

    traces = tmp_path / "traces.jsonl"
    sft = tmp_path / "sft.jsonl"
    repaired = _run_cli(
        ["repair", "--in", str(data), "--out", str(traces), "--sft-out", str(sft)]
    )
    assert repaired.returncode == 0, repaired.stderr

    report = tmp_path / "RESULTS.md"
    ran = _run_cli(
        [
            "ab",
            "--model",
            "stub",
            "--tasks",
            str(TASKS),
            "--report",
            str(report),
            "--arm-c",
        ]
    )
    assert ran.returncode == 0, ran.stderr
    text = report.read_text()
    assert "R = " in text and "Decision verdict" in text

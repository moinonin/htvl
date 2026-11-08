"""imprimatur-eval CLI.

    python -m imprimatur_eval build --out data.jsonl --model stub
    python -m imprimatur_eval repair --in data.jsonl --out traces.jsonl
    python -m imprimatur_eval ab --model stub --report RESULTS.md
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from .dataset import build, code_distribution, load_tasks
from .models import StubModel, load_model
from .repair import repair_loop, sft_records, trace_to_jsonl_record

DEFAULT_TASKS = Path(__file__).resolve().parent.parent / "tasks.jsonl"
_PROTOCOL_PATH = (
    Path(__file__).resolve().parent.parent.parent / "docs" / "EXPERIMENT.md"
)


def _sha256(path: Path) -> Optional[str]:
    try:
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()
    except OSError:
        return None


def _write_jsonl(path: Path, rows: List[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _cmd_build(args: argparse.Namespace) -> int:
    model = load_model(args.model)
    tasks = load_tasks(args.tasks)
    intents = [task["intent"] for task in tasks]
    rows = build(intents, model, k=args.k)
    _write_jsonl(Path(args.out), rows)
    distribution = code_distribution(rows)
    valid = sum(1 for row in rows if row["valid"])
    print(
        f"built {len(rows)} samples from {len(intents)} intents "
        f"({valid} valid, {len(rows) - valid} invalid) -> {args.out}"
    )
    print("error code distribution:", json.dumps(distribution))
    return 0


def _cmd_repair(args: argparse.Namespace) -> int:
    model = load_model(args.model)
    records = []
    sft = []
    for line in Path(args.in_path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row["valid"]:
            continue  # nothing to repair
        trace = repair_loop(model, row["htvl"])
        records.append(trace_to_jsonl_record(trace, row["intent"], args.model))
        sft.extend(sft_records(trace, row["intent"], args.model))
    _write_jsonl(Path(args.out), records)
    sft_path = Path(args.sft_out) if args.sft_out else None
    if sft_path:
        _write_jsonl(sft_path, sft)
    converged = sum(1 for record in records if record["final_ok"])
    print(
        f"repaired {len(records)} broken documents: {converged} converged, "
        f"{len(records) - converged} did not -> {args.out}"
    )
    if sft_path:
        print(f"wrote {len(sft)} SFT examples -> {sft_path}")
    return 0


def _cmd_ab(args: argparse.Namespace) -> int:
    from .harness import evaluate
    from .report import render_results

    model = load_model(args.model)
    tasks = load_tasks(args.tasks)
    report = evaluate(
        model,
        tasks,
        with_oracle=True,
        arm_c=args.arm_c,
        max_iters=args.max_iters,
        strict_window=args.strict_window,
    )
    report["manifest"] = {
        "model": args.model,
        "model_adapter": type(model).__name__,
        "temperature": getattr(model, "temperature", None),
        "tasks": str(args.tasks),
        "tasks_sha256": _sha256(Path(args.tasks)),
        "n_tasks": len(tasks),
        "max_iters": args.max_iters,
        "ablation": args.arm_c,
        "arm_c_k": 3,
        "protocol": str(_PROTOCOL_PATH),
        "protocol_sha256": _sha256(_PROTOCOL_PATH)
        if _PROTOCOL_PATH.exists()
        else None,
        "recorded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "mode": "modern=True everywhere",
        "strict_window": args.strict_window,
    }
    text = render_results(report)
    Path(args.report).parent.mkdir(parents=True, exist_ok=True)
    Path(args.report).write_text(text, encoding="utf-8")
    if args.json_out:
        Path(args.json_out).write_text(
            json.dumps(report, indent=2), encoding="utf-8"
        )
        print(f"wrote {args.json_out}")
    contrast = report.get("contrast", {})
    print(f"wrote {args.report}")
    print(
        "control C={ctrl} treatment C={treat} R={ratio} verdict={verdict}".format(
            ctrl=contrast.get("tokens_per_correct_control"),
            treat=contrast.get("tokens_per_correct_treatment"),
            ratio=contrast.get("ratio_R"),
            verdict=contrast.get("verdict"),
        )
    )
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="imprimatur-eval",
        description=(
            "Dataset builder, repair-trace recorder and A/B harness for "
            "oracle-assisted HTVL generation."
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True)

    build_cmd = sub.add_parser("build", help="rejection-sampling dataset")
    build_cmd.add_argument("--out", default="data.jsonl")
    build_cmd.add_argument("--model", default="stub")
    build_cmd.add_argument("--tasks", default=str(DEFAULT_TASKS))
    build_cmd.add_argument("-k", type=int, default=8)
    build_cmd.set_defaults(func=_cmd_build)

    repair_cmd = sub.add_parser("repair", help="repair traces (SFT data)")
    repair_cmd.add_argument("--in", dest="in_path", required=True)
    repair_cmd.add_argument("--out", default="traces.jsonl")
    repair_cmd.add_argument("--sft-out", dest="sft_out", default=None)
    repair_cmd.add_argument("--model", default="stub")
    repair_cmd.set_defaults(func=_cmd_repair)

    ab_cmd = sub.add_parser("ab", help="A/B evaluation and RESULTS.md")
    ab_cmd.add_argument("--model", default="stub")
    ab_cmd.add_argument("--tasks", default=str(DEFAULT_TASKS))
    ab_cmd.add_argument("--report", default="RESULTS.md")
    ab_cmd.add_argument("--max-iters", type=int, default=6)
    ab_cmd.add_argument("--arm-c", action="store_true", help="also run the best-of-k ablation")
    ab_cmd.add_argument("--json-out", dest="json_out", default=None,
                        help="also write the raw report dict as JSON")
    ab_cmd.add_argument("--strict-window", action="store_true",
                        help="also run a treatment arm whose repairs are "
                             "re-asked when they edit outside the region the "
                             "diagnostic permits")
    ab_cmd.set_defaults(func=_cmd_ab)
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = _build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())

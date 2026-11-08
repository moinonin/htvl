"""Rejection sampling: the compiler as a free labeler."""

from __future__ import annotations

from typing import Dict, Iterable, List

import imprimatur


def build(
    intents: Iterable[str],
    model,
    k: int = 8,
) -> List[Dict]:
    """Sample k documents per intent and label each with the compiler.

    No human annotation anywhere. The `codes` field says whether to fix the
    prompt (UNKNOWN_TAG dominates -> ship the tag list) or the model.
    """
    rows: List[Dict] = []
    for intent in intents:
        for _ in range(k):
            source = model.generate(intent)
            result = imprimatur.check(source)
            rows.append(
                {
                    "intent": intent,
                    "model": getattr(model, "name", "unknown"),
                    "htvl": source,
                    "html": result.html,
                    "valid": result.ok,
                    "codes": [d.code.value for d in result.diagnostics],
                    "tokens": model.tokens_used,
                }
            )
    return rows


def code_distribution(rows: List[Dict]) -> Dict[str, int]:
    """Failure-mode frequency across a dataset - which codes dominate."""
    counts: Dict[str, int] = {}
    for row in rows:
        if row["valid"]:
            continue
        for code in row["codes"]:
            counts[code] = counts.get(code, 0) + 1
    return dict(sorted(counts.items(), key=lambda item: -item[1]))


def load_tasks(path) -> List[Dict]:
    """Read tasks.jsonl: [{id, intent, min_requirements}, ...]."""
    import json
    from pathlib import Path

    tasks = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            tasks.append(json.loads(line))
    if not tasks:
        raise SystemExit(f"no tasks found in {path}")
    return tasks

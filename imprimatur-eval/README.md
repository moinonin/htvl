# imprimatur-eval

**Its one job: measure whether the oracle pays for itself, and produce the
dataset and traces either way.**

Three commands, one protocol (`docs/EXPERIMENT.md`):

```bash
python -m imprimatur_eval build --out data.jsonl --model stub
python -m imprimatur_eval repair --in data.jsonl --out traces.jsonl --sft-out sft.jsonl
python -m imprimatur_eval ab --model stub --report RESULTS.md
```

| Command | What it does |
| --- | --- |
| `build` | Rejection sampling: k documents per intent, each labelled by the compiler — no human annotation. Reports the error-code distribution. |
| `repair` | Runs the repair loop over the invalid rows, recording one-error-at-a-time traces with `lines_touched` per step. Also emits SFT JSONL (grammar + tag list as system prompt, broken source + structured error as user, fixed source as assistant). |
| `ab` | The three arms — control (single shot), treatment (oracle loop), optional ablation (best-of-k) — plus the decision number: tokens per correct document, R with a paired bootstrap CI, McNemar counts, and `RESULTS.md`. |

## The model protocol

```python
class Model(Protocol):
    def generate(self, intent: str) -> str: ...
    def repair(self, source: str, diagnostic: dict, hint: str) -> str: ...
    @property
    def tokens_used(self) -> int: ...
```

Any backend plugs in. A deterministic, keyless `stub` ships with the harness
so CI runs the whole pipeline; **the stub is plumbing only and is excluded
from all reported results** (protocol §5.3). To plug in a real model, add a
case to `imprimatur_eval.models.load_model`.

## The decision number

`C = tokens per correct document` per arm, and `R = C_treatment / C_control`
with a paired bootstrap 95% CI over tasks. The pre-registered rule:

- **SUPPORT** (`R <= 0.80`, upper CI `< 1.00`) — ship `htvl-mcp`, proceed to
  fine-tuning.
- **INCONCLUSIVE** (CI includes 1.00) — ship as a convenience tool, publish
  the null result.
- **REFUTE** (`R >= 1.20`, lower CI `> 1.00`) — do not ship the server; keep
  `imprimatur.check` as a validation library.

Zero runtime dependencies: Python 3.10+ standard library, plus `imprimatur`.
No test needs a network call or an API key.

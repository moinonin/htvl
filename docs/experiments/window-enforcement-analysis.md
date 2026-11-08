# Window enforcement: a negative result

**Status:** measured, exploratory follow-up to the frozen primary run in
[`../EXPERIMENT.md`](../EXPERIMENT.md). All numbers are machine output of the
commands in §Reproduction below; the interpretation in §3 is hand-written and
labelled as such.

## 1. The hypothesis

Stage 4 refuted RQ3: median **71 lines touched per repair** meant the model
rewrote documents instead of repairing the named line. The obvious fix was to
make the scope *enforceable* rather than merely requested: derive the lines a
repair may touch from the semantics of the diagnostic, re-ask once when an edit
escapes that region, and record any violation that survives.

Prediction: out-of-region edits fall, convergence holds or improves, and the
token cost rises modestly (one extra call on violating turns).

## 2. What was measured

Same model, same 20 tasks, same protocol, temperature 0, modern mode; the
strict arm ran in the same process as the unrestricted one (paired). Raw data:
`window-enforcement.json`.

| Arm | Compile rate | Tokens/correct doc | Median lines touched | Median lines outside region |
| --- | --- | --- | --- | --- |
| control (single shot) | 10% (2/20) | 84,594 | — | — |
| treatment (unrestricted) | 25% (5/20) | 14,203 | 71 | 13 |
| treatment (window-enforced) | **20% (4/20)** | **24,496** | 71 | **12.5** |

R for the enforced arm: 0.290 (95% CI 0.117–0.635) — still SUPPORT on the
primary rule, but **1.7× more expensive per correct document than the
unrestricted loop**, with one *fewer* document converged.

## 3. What it means (interpretation)

1. **Asking nicer does not discipline this model.** Out-of-region edits moved
   from a median of 13 to 12.5 — statistically nothing. The re-asked repair
   produced an equivalently-scoped rewrite, so the retry was pure overhead:
   ~70% more tokens for no behavioural change.
2. **The retry also cost convergence.** 20% vs 25%: spending an iteration
   budget on a scope lecture crowded out an actual repair step within the
   6-iteration cap.
3. **Therefore the bottleneck is not prompt discipline; it is that the repair
   task is being given to the wrong component.** Every error code the oracle
   emits is *mechanically* fixable — rename to the nearest valid tag, trim
   surplus arguments, delete the stray closer, close the quote, insert the
   missing closer. None of those repairs needs a language model. Asking a 7B
   model to perform them, then policing its edit scope, spends tokens to
   obtain what deterministic code can do exactly.

## 4. What the evidence supports instead

Take commitment #1 literally: **syntax belongs to the compiler — including
syntax repair.** Build `imprimatur.fix(source) -> (source, actions)`: a
deterministic repairer, one mechanical action per diagnostic code, driven by
the same parse tree the diagnostics already come from. Then:

- the treatment arm's repair step costs ~0 tokens and is byte-deterministic;
- convergence for mechanical errors should approach 100%, because the repair
  is a function of the diagnostic, not a sample from a model;
- the model's job shrinks to content, which is the job it should have had.

This is a product decision, not a plumbing one: it moves "the compiler
disposes" from detecting defects to correcting them. The harness measures it
unchanged — a `deterministic` repair adapter against the same 20 tasks — so
the claim would be a number, not an assertion.

## 5. Reproduction

```bash
pip install -e ./imprimatur-eval
python -m imprimatur_eval ab --model ollama/qwen2.5-coder:7b-instruct \
  --tasks imprimatur-eval/tasks.jsonl --strict-window \
  --report docs/experiments/window-enforcement.md \
  --json-out docs/experiments/window-enforcement.json
```

Recorded in `docs/experiment-deviations.md` as follow-up entry F1.

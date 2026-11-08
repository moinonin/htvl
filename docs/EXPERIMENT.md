Here it is, written to be committed as `docs/EXPERIMENT.md` and pre-registered before the first run.

---

# EXPERIMENT.md — Oracle-Assisted HTVL Generation: A/B Protocol

**Version:** 1.0
**Status:** Pre-registered — freeze before running. Post-freeze changes go in §13.
**Applies to:** `imprimatur-eval`, Stage 4 gate.

## 1. Background and rationale

Imprimatur's premise is that a compile-check-repair loop produces correct documents at lower total cost than single-shot generation. The premise is plausible but unmeasured. The MCP server (`htvl-mcp`) is a delivery mechanism for this loop; if the loop does not pay for itself, the server should not ship.

This experiment is a controlled comparison of generation **with** and **without** the `imprimatur` oracle. It measures cost-to-correct-output, not perceived quality, and it is designed so that a negative result is as cheap to reach and as publishable as a positive one.

## 2. Research questions

- **RQ1 (primary):** Does oracle-assisted generation reduce the token cost per *correct* document relative to single-shot generation?
- **RQ2:** Does the oracle improve the proportion of documents that compile?
- **RQ3:** Are repairs line-local? (Does the one-line-in/one-line-out invariant produce bounded edit scope?)
- **RQ4 (ablation):** Is any benefit attributable to *repair* specifically, or merely to *selection* among multiple samples?

## 3. Hypotheses

**Primary (RQ1).** Let \(C\) denote tokens per correct document.

- \(H_0: C_{\text{treat}} = C_{\text{ctrl}}\)
- \(H_1: C_{\text{treat}} < C_{\text{ctrl}}\)

Directional, one-sided.

**Secondary (RQ2).** \(H_0: p_{\text{treat}} = p_{\text{ctrl}}\) vs. \(H_1: p_{\text{treat}} > p_{\text{ctrl}}\), where \(p\) is first-pass (control) or post-loop (treatment) compile rate.

**Descriptive (RQ3).** No hypothesis test. Report the distribution of `lines_touched`.

**Ablation (RQ4).** \(H_0: C_{\text{treat}} = C_{\text{best-of-k}}\). If best-of-k matches the repair loop, repair adds nothing over sampling.

## 4. Design

**Type:** Paired, within-task comparison. Every task is run in every arm with the same model, prompts, and parameters.

### 4.1 Independent variable

Availability of the oracle. Three levels:

| Arm | Procedure | Purpose |
|---|---|---|
| **A — Control** | `model.generate(intent)`, one sample, no feedback | Baseline |
| **B — Treatment** | `repair_loop(model, model.generate(intent))`, ≤6 iterations | Primary hypothesis |
| **C — Ablation** | Sample \(k\) independent documents; select the first that compiles; else fail | Separates selection from repair |

Arm C is optional and reported only if API budget allows. It is pre-specified so it cannot be added post hoc as a rescue.

### 4.2 Dependent variables

| Variable | Type | Arm(s) | Role |
|---|---|---|---|
| Tokens per correct document, \(C\) | Continuous, ratio | A, B, C | **Primary** |
| Compile rate, \(p\) | Binary per task | A, B, C | Secondary |
| Iterations to green | Integer | B | Descriptive |
| Lines touched per repair | Integer | B | Descriptive |
| Error code distribution | Categorical | A, B, C | Diagnostic |

### 4.3 Controls

Held fixed across arms:

- Model identity and version, pinned and recorded.
- Decoding parameters: temperature, top-p, max tokens — recorded in the manifest, identical everywhere.
- System prompt: identical base prompt in all arms. The treatment arm *additionally* receives diagnostics as part of the repair turn; that is the treatment, not a confound.
- Iteration cap: 6 (Arm B). Sample count: \(k=3\) (Arm C).
- Mode: `modern=True` everywhere.
- Task ordering: fixed list, seeded; arm passes run as full separate sweeps to avoid interleaving effects.
- Tokenizer: one model per comparison; token counts are not comparable across model families.

### 4.4 Unit of analysis

The **task**. All metrics are computed per task and then aggregated; paired analysis resamples tasks, not tokens.

## 5. Materials

### 5.1 Task set

A fixed list of \(N\) intents (`tasks.jsonl`), each `{id, intent, min_requirements}`.

**Construction requirements:**

- Cover the four everyday scenarios from the brief: status page, nightly build report, small-model document, local/private document.
- Each intent must require structural complexity — multiple nesting levels, lists or tables, repeated elements. This guards against the gaming failure where a model emits one trivially valid element.
- `min_requirements` records the structural minimum (e.g., "≥1 table with ≥3 rows", "≥2 nested sections", "≥1 nav with ≥3 links") so that **compile-valid but vacuous** outputs can be identified. Recorded as an exploratory check, not in the primary DV.
- Written before any model is run. No task is added or edited after the first data collection.

**Size:** Pilot with \(N=20\); primary analysis at \(N=40\) if budget allows. Report actual \(N\) regardless.

### 5.2 Model adapter

```python
class Model(Protocol):
    def generate(self, intent: str) -> str: ...
    def repair(self, source: str, diagnostic: dict, hint: str) -> str: ...
    @property
    def tokens_used(self) -> int: ...
```

Token accounting is per call, cumulative, and includes both prompt and completion tokens.

### 5.3 Stub model

A deterministic, keyless stub (`StubModel`) ships with the harness so the pipeline runs in CI. **The stub is for plumbing only and is excluded from all reported results.**

### 5.4 Prompts

Stored in `prompts/` and versioned. Both arms share `base.md` (grammar + `htvl list` output + two few-shot examples). Arm B's repair turn uses `repair.md`, which includes the structured diagnostic, a numbered line window, and `imprimatur.explain()` hints. Prompt text is part of the treatment and is reported in full.

## 6. Procedure

Per task \(i\), per arm:

1. Start a fresh context. No state carries between tasks or arms.
2. **Arm A:** one `generate` call. Record source, tokens, `imprimatur.check()` result.
3. **Arm B:** `generate`, then loop: check → if ok, stop; else repair one diagnostic at a time → recheck. Stop at 6 iterations. **Abort early if the repair output is byte-identical to its input** (no-progress condition) and record as failed.
4. **Arm C:** \(k=3\) independent `generate` calls; select the first that compiles. If none compile, fail. Record all samples' tokens.
5. A document is **correct** iff `imprimatur.check(src).ok` is `True` at the end of the arm's procedure.

**Failure handling:** timeouts, API errors, and aborts count as **incorrect** and their tokens **are charged** to the arm. Silently dropping failures is a protocol violation.

**Order:** run the full Arm A sweep, then B, then C, with a fixed seed and recorded timestamps. If order effects are a concern, repeat in reverse order on a subset and report agreement as an exploratory check.

## 7. Metrics — operational definitions

Let \(N\) = number of tasks. For task \(i\), \(t_i\) = total tokens consumed in the arm, \(c_i \in \{0,1\}\) = correctness.

$$
C = \frac{\sum_i t_i}{\sum_i c_i} \quad \text{(tokens per correct document)}
$$

$$
p = \frac{1}{N}\sum_i c_i \quad \text{(compile rate)}
$$

$$
\text{iters} = \frac{1}{N}\sum_i \text{iterations}_i \quad \text{(Arm B only)}
$$

`lines_touched` = minimum line-level edit distance between repair input and output, via `difflib.SequenceMatcher`. Reported as median, p90, and histogram.

The **primary contrast** is the ratio:

$$
R = \frac{C_{\text{treat}}}{C_{\text{ctrl}}}
$$

\(R < 1\) favours the oracle.

## 8. Analysis plan

**Primary.** Bootstrap over tasks (10,000 resamples, paired: resample task indices and recompute both \(C\)'s from the same indices) to obtain a 95% percentile CI for \(R\). Report point estimate, CI, and \(N\).

**Secondary.** McNemar's test on the paired correctness vectors \((c_i^{\text{ctrl}}, c_i^{\text{treat}})\). Report discordant pair counts explicitly. Report Cohen's \(g\) or risk difference with CI.

**Descriptive.** Iterations and `lines_touched` as distributions, not just means. Error-code frequency table by arm, to identify whether the loop fixes one failure class disproportionately.

**Ablation.** Same bootstrap contrast for \(C_{\text{best-of-k}}\) vs. \(C_{\text{ctrl}}\) and vs. \(C_{\text{treat}}\).

**Exploratory (clearly labelled, no decision weight):** correlation between `lines_touched` and convergence; correlation between document length and failure; vacuous-output check against `min_requirements` on a sample of 10 documents graded by a second model or human.

**No multiplicity adjustment is required** for the single pre-specified primary contrast. All secondary and exploratory results are reported as such and do not enter the decision.

## 9. Decision rule (pre-specified)

Applied to the primary contrast \(R\):

| Outcome | Condition | Consequence |
|---|---|---|
| **SUPPORT** | \(R \le 0.80\) and upper 95% CI bound \(< 1.00\) | Ship `htvl-mcp`; proceed to fine-tuning pipeline |
| **INCONCLUSIVE** | CI includes 1.00, or \(0.80 < R < 1.20\) | Ship as a convenience tool; do not build a product on it; publish the null result |
| **REFUTE** | \(R \ge 1.20\) and lower 95% CI bound \(> 1.00\) | Do not ship the server. Keep `imprimatur.check` as a validation library. Publish the negative result |

The 0.80 / 1.20 band is the pre-registered **minimal meaningful effect**: a 20% change in cost-to-correct is the smallest that justifies the maintenance burden of an agent-facing package.

**Abort-the-experiment condition:** if Arm A's compile rate exceeds 0.95, the baseline is too good for the loop to matter. Report this and stop; do not proceed to fine-tuning regardless of \(R\).

## 10. Sample size

Honest statement: with \(N=40\), the 95% CI on a ratio near 1.0 will be roughly ±0.15–0.25 depending on variance. This is sufficient to distinguish SUPPORT from REFUTE given the 20% effect threshold, but not to resolve small effects — which is why the threshold exists.

Pre-registered sequencing: run the pilot at \(N=20\), report the observed variance and CI width, then decide **once** whether to extend to \(N=40\). The decision to extend is made on precision grounds only, never on the direction of the point estimate. Record the decision in §13.

**Budget cap:** a maximum API spend is declared in the manifest before running. If the cap is reached mid-sweep, the experiment stops and reports the partial \(N\).

## 11. Threats to validity

**Construct — the main one.** The dependent variable is *compiles*, which is necessary but not sufficient for correctness. A model could satisfy the oracle with structurally valid but semantically wrong or vacuous documents. Mitigations: task set requires structural complexity; `min_requirements` check is reported; and the report must state plainly that the experiment measures **well-formedness, not content quality**. Any claim beyond that is unsupported by this design.

**Construct — tokens as cost.** Token counts are a proxy for cost. They exclude latency, retries at the transport layer, and human review time. Stated in the report; not corrected for.

**Internal.** Two risks. (i) *Prompt confound*: Arm B sees diagnostics and Arm A does not — that is the treatment, by design, and both arms share an identical base prompt. (ii) *Order effects*: arms run as sequential sweeps, not interleaved; checked on a subset by re-running in reverse order.

**External.** One model family, English-language intents, HTML-shaped documents. Results do not automatically generalize to other models, languages, or document classes. The ablation (Arm C) partially addresses the model-specificity concern by testing whether the mechanism is selection rather than repair.

**Conclusion.** One pre-specified primary contrast, so no multiplicity problem for the decision. Secondary metrics are labelled exploratory and carry no decision weight.

**Gaming.** The metric is satisfiable by degenerate documents. The `min_requirements` audit exists specifically to detect this; if vacuous outputs exceed 10% of the treatment arm's successes, the primary result is reported as **provisional** and the decision rule is not applied.

## 12. Reporting

`RESULTS.md`, containing:

1. Manifest: model, version, temperature, prompts (linked), task set hash, dates, \(N\), API spend.
2. Primary: \(C_{\text{ctrl}}\), \(C_{\text{treat}}\), \(R\), 95% CI, decision verdict.
3. Secondary: McNemar table, \(p\) per arm.
4. Descriptive: iterations, `lines_touched` histogram, error-code table.
5. Ablation (if run): Arm C contrasts.
6. Exploratory: vacuous-output audit, length/convergence correlations.
7. **Threats and limitations**, reproducing §11 verbatim.
8. **Verdict paragraph** — one paragraph, plain language, stating whether the oracle pays for itself and, if not, saying so directly.
9. Reproduction: the exact commands, in order, that regenerate every number.

## 13. Deviations log

Every departure from this protocol is recorded here with date, reason, and effect on interpretation. An empty log at report time is a claim that the protocol was followed exactly.

| Date | Section | Deviation | Reason | Consequence |
|---|---|---|---|---|
| | | | | |

## 14. Freeze

This document is frozen on the date below, before any data collection on the primary task set. Its SHA-256 is recorded in the manifest and re-checked by the harness before the run, so the analysis plan cannot drift after seeing the numbers.

**Frozen:** ______________  **SHA-256:** ______________

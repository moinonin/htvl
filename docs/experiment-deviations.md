# Experiment deviations log

The protocol is `docs/EXPERIMENT.md`, frozen before any data collection on
the primary task set (SHA-256 `c153ed7d…`, recorded in the RESULTS.md
manifest). Its §13 asks that every departure be recorded; editing the frozen
file would invalidate the recorded hash, so the log lives here and is
referenced from the manifest.

| # | When | Deviation | Reason | Effect on interpretation |
| --- | --- | --- | --- | --- |
| 1 | Stage 3 (before any primary data) | The whole pipeline was first exercised with the deterministic `stub` model, not a real one. | Protocol §5.3 explicitly ships the stub for CI plumbing and excludes it from reported results. | None on the primary numbers: the stub run exercised every code path and is reported separately in the Stage 3 commit. |
| 2 | First primary run, discarded | An oracle bug was found *by the first real-model output*: the balance scanner was regex-based and reported a false `UNCLOSED_TAG` for `$(p '' '' 'updated at $(span '12:00')' '')` — a call nested inside a quoted argument. The scanner was rewritten to walk the compiler's parse tree (`imprimatur/structural.py`, D23), with a regression test. | A false positive would inflate `UNCLOSED_TAG` in the error-code distribution and send repairs chasing phantom errors — it corrupts the dependent variable, so the run could not stand. | The first run's numbers were **discarded** and the experiment re-run in full after the fix, per protocol §6 (a corrupted measurement is not a failure to be charged; it is a bug to fix and re-run). |
| 3 | Same boundary | The CLI's final summary line printed `C=None` for both arms because the contrast dict did not carry the per-arm C values (the report itself was correct). | Reporting cosmetics; fixed in `_ratio()`. | None on any number. |
| 4 | Recorded run | Decoding is greedy (`temperature = 0.0`), chosen for reproducibility. | A frozen, re-runnable measurement; recorded in the manifest per protocol §4.3. | Arm C (best-of-k) draws three *identical* samples, so it equals Arm A by construction and cannot separate selection from repair (RQ4 remains unanswered by this run). Reported as a limitation in RESULTS.md §5. |
| 5 | Recorded run | Report rendering adds an interpretation paragraph when median `lines_touched` exceeds 10, and a temperature-0 caveat in §5. | The protocol requires distributions, not just means (§8); a median of 71 lines per repair is a substantive finding that a bare histogram hides. | None on the numbers; the interpretation is derived from them. |
| 6 | Recorded run | `--json-out` persists the raw report dict next to `RESULTS.md`. | So the rendered report can be regenerated from the exact measured data without re-running a 35-minute sweep. | None. |
| 7 | After the recorded run | The first render of the recorded run omitted `--tasks`, `--arm-c` and `--json-out` from the reproduction block, and the raw JSON was not persisted (a `PosixPath` in the manifest is not JSON-serialisable). Both were fixed in the template/CLI and the sweep was re-run in full, so the committed `RESULTS.md` and `results.json` are unmodified machine output of a single run. | None on any number: the re-run reproduced the first run's figures exactly (control C=84,594.0, treatment C=14,202.8, R=0.1679), which also demonstrates the greedy-decoding determinism the protocol asks to be recorded. |


---

## Post-freeze follow-ups (exploratory; no weight on the frozen decision)

| # | What | Result | Consequence |
| --- | --- | --- | --- |
| F1 | Window-enforced repair mode (`--strict-window`): repairs re-asked when they edit outside the region the diagnostic permits. | **Negative.** Out-of-region edits 13 -> 12.5 median (nothing), compile 25% -> 20%, tokens/correct doc 14,203 -> 24,496 (+72%). | Prompt discipline does not fix the line-locality gap for this model. The retry is pure overhead. Analysis: `docs/experiments/window-enforcement-analysis.md`; raw data beside it. |

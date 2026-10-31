# Measurement receipts

The helper is optional bookkeeping for an actual run. It compares evidence
already produced by your runner; it does not perform experiments or change the
working tree. Never report these comparison checks as model/creative benchmarks.

Copy `templates/plan.json` into the run directory. Set real case IDs and paths,
noise evidence, actionable gain, direction and guardrails. Hash every relevant
frozen file with SHA-256, including the rubric snapshot when using `unslop`.
File paths resolve relative to the plan. Its source template contains deliberate
placeholders and is not a runnable evaluation. Keep the plan frozen with the
run, record its hash in the task evidence, and retain all revisions.

The helper checks disjoint train/selection/confirm IDs. It requires three
nonempty splits; use a clearly labeled exploratory workflow without this helper
when data is too limited to support them. Related cases need grouping by the
human/agent designing the split. The helper cannot detect semantic duplicates.

Each results file is JSONL with one row per case and repetition. The required
selected split must be complete; known cases from other splits can also occur
in the file. Keep final confirmation outputs inaccessible to the optimizer
until the winner is fixed. Merely naming a file `holdout` does not ensure that.

```json
{"case":"select-a","rep":0,"metrics":{"latency_ms":110,"quality":1},"gate_passed":true,"error_count":0,"work_count":100,"evidence":{"path":"traces/select-a-0.json","sha256":"<actual hash>"}}
```

Evidence paths resolve relative to their results file. For model-based runs,
set `model_based: true` in the plan and add `model` (actual served model),
`usage` (`input_tokens`, `output_tokens`, `cache_read_tokens`,
`cache_write_tokens`), and nonempty `grade` dict to each row. Evidence must
contain the same-call transcript and grading receipts. The helper verifies its
bytes, not its semantic correspondence; the reviewer must check the actual
trace. Keep full retry and judge usage/cost accounting alongside it.

```sh
python3 <skill-directory>/scripts/hill_climb.py \
  --plan plan.json --baseline baseline.jsonl --candidate round-1.jsonl \
  --split selection
```

Baseline errors or incomplete/mismatched evidence are invalid (exit 1).
Candidate gate/error/work-count failures or an insufficient gain are rejected
(exit 2). Eligible (exit 0) means the recorded numeric gates passed, not that a
candidate has been adopted. Review mechanism, actual behavior, budget, and
requirements before accepting. Repeat with `--split confirm` for the fixed
winner versus the **original** baseline, using untouched cases and fresh
receipts. Any semantic confirmation isolation must be checked separately.

The helper averages repetitions within a case, then computes paired case-level
gain and an approximate 95% Student-t interval (normal approximation above 30
degrees of freedom). It requires gain strictly above both the registered
actionable margin and the larger of baseline noise and interval half-width.
Guardrails require the lower bound of oriented gain to remain at or above the
negative allowed tolerance. A one-case deterministic benchmark can be compared
using the registered noise floor, but has no case-level interval. These checks
are not a power analysis or a guarantee for arbitrary distributions, correlated
cases, adaptive selection, or multiple comparisons. Use a domain-appropriate
analysis for consequential claims; reserve fresh confirmation data.

Budgets, iteration count, elapsed time, rollback, commits, and `decision.tsv`
are managed by the skill's execution workflow, not by this comparison script.
It never launches commands, spends money, edits harnesses, or grants permission.

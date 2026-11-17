# Execution contract

Design and execute calibrated evaluations of nondeterministic behavior using established frameworks.

Use `.tkstack/tkstack skills evalify -- help`, `.tkstack/tkstack skills evalify -- version`, and `.tkstack/tkstack skills evalify -- model`.
Run `.tkstack/tkstack skills evalify -- verify --report /path/to/report.json` for mechanical evidence verification.

The executable artifact is `scripts/workflow.lock.json`, built from the actual native code and command contracts. The skill index routes residual judgment to its focused references. It does not replay a deterministic algorithm through inference.

## Required criteria

- task: Define the actual workload and observable success, including deterministic gates.
- judge: Calibrate any model judge against independently labeled examples and record limitations.
- measurement: Retain matched runs, elapsed time, costs, failures and confirmation evidence.

## Report and validation

Read `scripts/contract.json` for the exact JSON Schema of `facts`. A report has exactly `skill`, nonempty `objective`, `facts`, `criteria`, `evidence`, and `review`. Each criterion has `id`, `status: pass`, nonempty evidence ID array and a reason. Every modeled criterion is required. Evidence entries have unique `id`, `path`, SHA-256 `sha256`, and `kind`; actual files are hashed. Review records have `reviewer`, `semantic_inspection: performed`, and explicit `limitations`. The gate checks these records and file bytes; it cannot authenticate their truth or replace semantic inspection. Missing evidence blocks it.

## Effects, scope, and native tools

Model and verify do not mutate application/learning records; compiled invocation uses the shared runner's ignored .tkstack temporary materialization. Reserved help/version and direct metadata checks initialize no state. Relative report/evidence/native paths resolve against the selected workspace, never Codify staging. Native bindings execute the existing named helper with typed parameters, preserved output/exit status, a bounded timeout, and no shell strings. Their documented effects retain the user's authorization boundary; invoking a verification operation does not authorize publication, generation, or configuration changes. All temporary state stays in scoped `.tkstack/sessions/`; durable data follows the owned state helper. Chat/Responses, Decisions, and harness inference remain explicit Vercel AI SDK profiles when an actual workflow needs them. These mechanical operations request no inference.

## Limits

- A recorded review does not authenticate judge calibration, model behavior, or semantic quality.
- Promptfoo must be separately installed; native execution can call providers and execute configuration code.
- The helper deadline does not prove remote cancellation or cleanup of detached descendants.

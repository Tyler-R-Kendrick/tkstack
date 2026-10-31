# Execution contract

Find existing assets, establish semantic equivalence and extract the smallest deterministic code-production asset.

Use `.tkstack/tkstack skills reusify -- help`, `.tkstack/tkstack skills reusify -- version`, and `.tkstack/tkstack skills reusify -- model`.
Run `.tkstack/tkstack skills reusify -- verify --report /path/to/report.json` for mechanical evidence verification.

The executable artifact is `scripts/workflow.lock.json`, built from the actual native code and command contracts. The skill index routes residual judgment to its focused references. It does not replay a deterministic algorithm through inference.

## Required criteria

- reuse-search: Inspect suitable existing assets before authoring another implementation.
- equivalence: Use distinct source occurrences and semantic equivalence; preserve legitimate differences.
- native-generation: Run the native expansion/compiler/consumer checks and preserve original behavior.

## Report and validation

Read `scripts/contract.json` for the exact JSON Schema of `facts`. A report has exactly `skill`, nonempty `objective`, `facts`, `criteria`, `evidence`, and `review`. Each criterion has `id`, `status: pass`, nonempty evidence ID array and a reason. Every modeled criterion is required. Evidence entries have unique `id`, `path`, SHA-256 `sha256`, and `kind`; actual files are hashed. Review records have `reviewer`, `semantic_inspection: performed`, and explicit `limitations`. The gate checks these records and file bytes; it cannot authenticate their truth or replace semantic inspection. Missing evidence blocks it.

## Effects, scope, and native tools

Model and verify do not mutate application/learning records; compiled invocation uses the shared runner's ignored .tkstack temporary materialization. Reserved help/version and direct metadata checks initialize no state. Relative report/evidence/native paths resolve against the selected workspace, never Codify staging. Native bindings execute the existing named helper with typed parameters, preserved output/exit status, a bounded timeout, and no shell strings. Their documented effects retain the user's authorization boundary; invoking a verification operation does not authorize publication, generation, or configuration changes. All temporary state stays in scoped `.tkstack/sessions/`; durable data follows the owned state helper. Chat/Responses, Decisions, and harness inference remain explicit Vercel AI SDK profiles when an actual workflow needs them. These mechanical operations request no inference.

## Limits

- Mechanical verification checks recorded facts and actual retained bytes; a recorded semantic inspection is not authenticated judgment.
- Compilation and fixture success do not prove complete semantic workflow performance or provider/native-host activation.
- Use native assess for actual independent source occurrences and real native engine/consumer checks for an extracted asset; semantic equivalence remains reviewed.

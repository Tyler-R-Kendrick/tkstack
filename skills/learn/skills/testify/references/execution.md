# Execution contract

Create and validate a distinct behavioral test for a concrete observed risk; use static constraints first.

Use `.tkstack/tkstack skills testify -- help`, `.tkstack/tkstack skills testify -- version`, and `.tkstack/tkstack skills testify -- model`.
Run `.tkstack/tkstack skills testify -- verify --report /path/to/report.json` for mechanical evidence verification.

The executable artifact is `scripts/workflow.lock.json`, built from the actual native code and command contracts. The skill index routes residual judgment to its focused references. It does not replay a deterministic algorithm through inference.

## Required criteria

- risk: Name the concrete fault and distinct regression not already enforced statically.
- oracle: Assert an independently expected public behavior or effect at the appropriate boundary.
- sensitivity: Demonstrate the retained test fails for a plausible fault and passes after restoration.

## Report and validation

Read `scripts/contract.json` for the exact JSON Schema of `facts`. A report has exactly `skill`, nonempty `objective`, `facts`, `criteria`, `evidence`, and `review`. Each criterion has `id`, `status: pass`, nonempty evidence ID array and a reason. Every modeled criterion is required. Evidence entries have unique `id`, `path`, SHA-256 `sha256`, and `kind`; actual files are hashed. Review records have `reviewer`, `semantic_inspection: performed`, and explicit `limitations`. The gate checks these records and file bytes; it cannot authenticate their truth or replace semantic inspection. Missing evidence blocks it.

## Effects, scope, and native tools

Model and verify do not mutate application/learning records; compiled invocation uses the shared runner's ignored .tkstack temporary materialization. Reserved help/version and direct metadata checks initialize no state. Relative report/evidence/native paths resolve against the selected workspace, never Codify staging. Native bindings execute the existing named helper with typed parameters, preserved output/exit status, a bounded timeout, and no shell strings. Their documented effects retain the user's authorization boundary; invoking a verification operation does not authorize publication, generation, or configuration changes. All temporary state stays in scoped `.tkstack/sessions/`; durable data follows the owned state helper. Semantic judgment stays with the invoking agent and its current model and harness. These mechanical operations request no inference.

## Limits

- Recorded reviews and syntactic cases do not prove semantic value, independence, or actual mutation sensitivity.
- The native generator covers explicit Python CLI contracts only; other test methods use native project tools.

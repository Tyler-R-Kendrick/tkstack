# Execution contract

Refine an actual rendered interface while preserving product truth, accessibility and explicit provider choice.

Use `.tkstack/tkstack skills open-design -- help`, `.tkstack/tkstack skills open-design -- version`, and `.tkstack/tkstack skills open-design -- model`.
Run `.tkstack/tkstack skills open-design -- verify --report /path/to/report.json` for mechanical evidence verification.

The executable artifact is `scripts/workflow.lock.json`, built from the actual native code and command contracts. The skill index routes residual judgment to its focused references. It does not replay a deterministic algorithm through inference.

## Required criteria

- brief: Preserve the product brief, identity, constraints and truthful content.
- rendered-states: Inspect actual renders at relevant sizes/states; missing captures remain unreviewed.
- design-system: Reuse semantic tokens/components and preserve accessibility.
- provider: Use an explicitly selected provider and report its actual runtime limits.

## Report and validation

Read `scripts/contract.json` for the exact JSON Schema of `facts`. A report has exactly `skill`, nonempty `objective`, `facts`, `criteria`, `evidence`, and `review`. Each criterion has `id`, `status: pass`, nonempty evidence ID array and a reason. Every modeled criterion is required. Evidence entries have unique `id`, `path`, SHA-256 `sha256`, and `kind`; actual files are hashed. Review records have `reviewer`, `semantic_inspection: performed`, and explicit `limitations`. The gate checks these records and file bytes; it cannot authenticate their truth or replace semantic inspection. Missing evidence blocks it.

## Effects, scope, and native tools

Model and verify do not mutate application/learning records; compiled invocation uses the shared runner's ignored .tkstack temporary materialization. Reserved help/version and direct metadata checks initialize no state. Relative report/evidence/native paths resolve against the selected workspace, never Codify staging. Native bindings execute the existing named helper with typed parameters, preserved output/exit status, a bounded timeout, and no shell strings. Their documented effects retain the user's authorization boundary; invoking a verification operation does not authorize publication, generation, or configuration changes. All temporary state stays in scoped `.tkstack/sessions/`; durable data follows the owned state helper. Chat/Responses, Decisions, and harness inference remain explicit Vercel AI SDK profiles when an actual workflow needs them. These mechanical operations request no inference.

## Limits

- Mechanical verification checks recorded facts and actual retained bytes; a recorded semantic inspection is not authenticated judgment.
- Compilation and fixture success do not prove complete semantic workflow performance or provider/native-host activation.
- Actual provider/runtime access is required for execution. Verification does not start a provider job, proxy or account session.
- The deterministic core does not render a UI or authenticate visual quality; use actual available rendering/provider tools and inspect the real states.

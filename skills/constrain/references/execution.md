# Execution contract

Enforce configured test-value, dependency integrity, execution, artifact and repository sparsity constraints in the selected workspace.

Use `.tkstack/tkstack skills constrain -- help`, `.tkstack/tkstack skills constrain -- version`, and `.tkstack/tkstack skills constrain -- model`.
Run `.tkstack/tkstack skills constrain -- verify --report /path/to/report.json` for mechanical evidence verification.

The executable artifact is `scripts/workflow.lock.json`, built from the actual native code and command contracts. The skill index routes residual judgment to its focused references. It does not replay a deterministic algorithm through inference.

## Required criteria

- risk: Choose verification depth and category from the concrete risk and boundary.
- behavior: Inspect independent behavioral oracles and distinct fault sensitivity before retaining tests.
- gate: Run the actual selected-workspace constraint gate and repair failures without automatic waivers.
- integrity: Pin supported dependencies and identify runtime acquisition paths outside the verified lock boundary.

## Report and validation

Read `scripts/contract.json` for the exact JSON Schema of `facts`. A report has exactly `skill`, nonempty `objective`, `facts`, `criteria`, `evidence`, and `review`. Each criterion has `id`, `status: pass`, nonempty evidence ID array and a reason. Every modeled criterion is required. Evidence entries have unique `id`, `path`, SHA-256 `sha256`, and `kind`; actual files are hashed. Review records have `reviewer`, `semantic_inspection: performed`, and explicit `limitations`. The gate checks these records and file bytes; it cannot authenticate their truth or replace semantic inspection. Missing evidence blocks it.

## Effects, scope, and native tools

Model and verify do not mutate application/learning records; compiled invocation uses the shared runner's ignored .tkstack temporary materialization. Reserved help/version and direct metadata checks initialize no state. Relative report/evidence/native paths resolve against the selected workspace, never Codify staging. Native bindings execute the existing named helper with typed parameters, preserved output/exit status, a bounded timeout, and no shell strings. Their documented effects retain the user's authorization boundary; invoking a verification operation does not authorize publication, generation, or configuration changes. All temporary state stays in scoped `.tkstack/sessions/`; durable data follows the owned state helper. Chat/Responses, Decisions, and harness inference remain explicit Vercel AI SDK profiles when an actual workflow needs them. These mechanical operations request no inference.

## Limits

- Deterministic rules detect supported test, dependency, execution, boundary and budget defects; they do not prove semantic test value or verify downloaded artifacts by themselves.
- Unlocked MCP runtime fetches and unsupported acquisition paths remain explicitly reported; recorded review does not authenticate reviewer judgment or native hook activation.

# Flowify

Turn the actual procedure into a versioned native workflow definition, executable
host/bindings, explicit inputs, and meaningful outcome checks. Do not stop at a
prose checklist or invent a private DSL when an existing one fits.

## 1. Resolve the workload and select the runtime

Inspect the explicit request, demonstrated steps, existing automation, and actual
target runtime. Capture inputs, outputs, data dependencies, effects, success and
failure conditions, concurrency/resource limits, and reuse boundaries. Update a
fitting owned workflow instead of duplicating it. A report/draft-only request
remains read-only. Creation does not authorize an unrelated deploy, merge, or
paid agent run; use the task's established execution scope.

Use the user's chosen backend when stated. Otherwise choose the smallest native
format that fits:

| Backend | Use when | Actual mechanism |
| --- | --- | --- |
| **MAF declarative YAML** (default here) | Portable tool/code actions, typed inputs, conditions, and a host with the Microsoft Agent Framework runtime | `WorkflowFactory` builds actual executor graphs; deterministic functions bind through `InvokeFunctionTool` |
| **Grok-style Rhai** | The workflow will run in Grok's `xai-workflow` host | Rhai 1.25 scripting with Grok host functions, quotas, cancellation, and a host-call journal |
| Existing project DSL | The repository already has a suitable executable engine | Preserve that format and verify its real runtime/schema rather than translating needlessly |

Read [backend contracts](../references/backends.md) and
[the primary-source comparison](../references/sources.md). Grok's Rust scripting
library is **Rhai**. `xai-workflow` supplies additional host functions; a generic
Rhai interpreter is not a drop-in Grok workflow host. MAF and Rhai are alternative
backends, not equivalent syntaxes or automatically interchangeable runtimes.

## 2. Design explicit control and data flow

Apply tkstack's principles when available: code and rules first, constrained
decision models/APIs next, LLMs/agents only for unresolved judgment. Use real
command exit codes, typed results, schemas, and predicates for readiness and
branching. A model deciding "tests look green" is not a deterministic gate.

Decompose work into granular units with explicit prerequisites and owned outputs.
Run ready independent work concurrently with bounded capacity and stable fan-in;
keep real dependencies/effects ordered. No two branches share writable task
state by accident. Register ordinary async functions or native executors for
code work; do not add agent calls solely to parallelize an algorithm.

MAF's graph uses synchronization barriers between supersteps. Top-level YAML
action lists are sequenced; do not invent a `Parallel` action or assume multiple
entries run independently. Use supported native builders/executors or bounded
concurrency inside a deterministic binding when needed. Grok's `parallel()`
launches agents from option maps, not arbitrary code tasks.

Define timeouts, retry limits, idempotency/operation IDs for effects, cancellation,
partial-failure propagation, and the condition that permits dependent work.
Record mutable observations as inputs/evidence when reproducibility matters.
Do not continue after unknown/missing validation or report empty output as success.
Keep credentials outside definitions and make any model quota/cost scope explicit.

## 3. Generate a reusable executable package

Place the owned workflow under the project's established automation directory,
defaulting to `workflows/<name>/`. Include the native definition, actual host/
bindings, input examples/schema, dependencies/lock, invocation instructions,
and meaningful behavior cases. Preserve the old baseline for updates and check
for concurrent drift. Keep vendor snapshots and plugin caches unchanged.

```sh
python3 <flowify-directory>/scripts/flowify.py scaffold \
  --backend maf --target /repo/workflows/check-contracts --name check-contracts
```

Use `--backend rhai` for Grok-hosted definitions. Scaffolding refuses an existing
directory. The MAF starter has YAML, a Python host, pinned direct requirements,
and a model-free file hashing binding with bounded reads. The Rhai starter is a
model-free host fingerprint step. These examples illustrate executable packages;
replace them with the actual requested procedure before claiming that request
is complete. A direct requirements file is not a transitive lock.

Use the real native action/function vocabulary. For MAF use `register_tool` for
`InvokeFunctionTool`; an agent registry or unrelated function-binding registry
does not implicitly register that tool. For Rhai preserve first-statement `meta`,
document actual arguments, and bind only supported host requests. Do not invent
a `shell()` host function or an unverified Grok CLI workflow command.

## 4. Inspect, validate, and execute real cases

```sh
python3 <flowify-directory>/scripts/flowify.py inspect --backend maf --file /repo/workflows/check-contracts/workflow.yaml
python3 <flowify-directory>/scripts/flowify.py check --backend maf --file /repo/workflows/check-contracts/workflow.yaml
python3 /repo/workflows/check-contracts/run.py --project /repo --input /repo/workflows/check-contracts/inputs.json --jobs 4
```

`inspect` records a source hash and performs basic MAF YAML structure checks;
for Rhai it records the source without pretending to parse it. `check` invokes
the real MAF graph builder or Grok's native mock-host validator. Exit **3** means
runtime unavailable; it is not validation success. See
[validation and execution evidence](../references/validation.md) for exact scope,
limits, and offline Rust commands. Native tools may compile/import code; do not
describe native validation as a passive sandbox.

Test a positive case, a distinct transfer case, and negative/failure boundaries.
Verify explicit dependencies, bounded overlapping work, stable results under
out-of-order completion, failed-task propagation, and any retry/resume behavior
actually promised. Use controlled events/barriers instead of sleep-based timing
guesses. Retain source/runtime/input identities and actual outcomes/artifacts.

Native graph construction is not binding/effect execution. Grok's validator
uses stub inputs and host responses, not real agents or production effects.
Do not turn source inspection, mock-host completion, or a binding unit test
into a claim of full native execution. If a required runtime is unavailable,
deliver the concrete source/package and verified checks, state the exact gap,
and do not silently substitute a homegrown interpreter.

## 5. Deliver and connect the authoring tools

Use `skillify` for the procedure that teaches when to run the workflow,
`instructify` for a short standing pointer, and `hookify` for an event that should
invoke an authorized deterministic gate. `flowify` owns the executable workflow
and its real state/data transitions. Keep source evidence through `learn` when
available; candidate interpretations are not new user policy.

An active `sdlc` workflow still owns leased task graphs, verified COW/sparse
worktrees, BDD/contracts, evidence, independent final review, incremental commits,
and stacked delivery. A generated workflow cannot bypass those requirements or
grant agent-spawn/merge authority. Use `hill-climb`/SkillOpt only for a genuine
requested optimization with real eval adapters and its normal gates.

Finish with the backend and why it fits, package paths, exact invocation,
runtime/dependency readiness, actual executed cases and artifacts, outstanding
validation, and effect/retry boundaries. Installing this skill does not run
its examples, start agents, or publish a workflow.

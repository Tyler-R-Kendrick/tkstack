# Existing DSLs and their execution contracts

Flowify authors native formats. It does not introduce a private workflow schema
or implement a partial MAF/Rhai interpreter and call it the native runtime.

## Microsoft Agent Framework declarative YAML

Default for new portable tool/code workflows. The reviewed package exposes
`WorkflowFactory` from `agent_framework_declarative` (reviewed source version
1.4.1; published runtime pinned to 1.4.0, verified against PyPI metadata).
The source also documents an `agent_framework.declarative` compatibility surface;
generated code uses the package's direct public export.

Both top-level `actions` and `trigger.actions` definitions are supported upstream.
Actions become executor nodes in the real workflow graph. Use actual action
names such as `InvokeFunctionTool`, `SetVariable`, `SendActivity`, or supported
control-flow actions. Power Fx expressions start with `=`; they are native
expressions, not Python strings evaluated with `eval` and not LLM decisions.

`InvokeFunctionTool` resolves tools registered through
`WorkflowFactory.register_tool(name, func)`. The unrelated `register_binding`
registry and agent registry do not implicitly register these tools. Registered
functions can be synchronous or asynchronous. Tool failures may become error
values in workflow state instead of propagating as exceptions, so dependent
actions and the host must check the actual result rather than declaring success
because the graph went idle.

The starter uses a real async local-file binding, returns a canonical JSON
receipt as the tool result, and emits it with `SendActivity`. Its Python host
accepts fresh-run success only if actual emitted output equals the receipt
from the successfully completed binding. It does not claim checkpoint/resume
support. Direct binding tests are useful evidence, but do not run the MAF graph.

Execution uses Pregel-style synchronized supersteps. Independent executors can
run within a step, but the barrier can couple parallel paths. Declarative action
lists are sequential; no invented `Parallel` action is supplied. For fine-grained
parallel command/code work, use bounded async bindings or an actual native
`WorkflowBuilder`/executor graph if the declarative format cannot express it.
Define data ownership and stable reductions explicitly.

The generated requirements pin direct dependencies and include a complete hash
lock for the tested CPython 3.12/Linux profile. Create and verify a matching lock
for other targets before claiming reproducibility. Power Fx/pythonnet/native
runtime constraints depend on the Python/platform combination. Package presence
alone does not prove that expressions or execution work. Do not silently replace
Power Fx or the MAF scheduler with an approximate local implementation.

## Grok-hosted Rhai

The reviewed `xai-workflow` Rust crate depends on Rhai 1.25 with serde support.
It compiles scripts with limits and disables dynamic `eval`, module resolution,
wall-clock `timestamp()` and `sleep()` in its host. The first statement defines
`meta`, with actual `name`, `description`, optional `when_to_use`, and `phases`.
Runtime input is exposed as `args`.

Grok supplies `agent`, `parallel`, `phase`, `log`, `complete`, `pause`, `await_user`,
`budget`, template/scratch helpers, `git_diff_since`, `fingerprint`, and JSON
serialization helpers. These are host functions, not generic Rhai facilities.
There is no reviewed generic `shell()` host function. `parallel()` accepts agent
option maps and launches agents under host quotas; it is not an ordinary thread
pool. Do not spend agent calls on tasks that deterministic code can do.

Host-result calls are journaled with sequence numbers and request hashes.
Replay depends on stable script/argument/request identity; a changed request
must not reuse unrelated old results. Journaling is not a universal exactly-once
guarantee for external side effects. The host owns those effect and retry contracts.
Model responses and mutable tools remain nondeterministic inputs even when
orchestration control flow is deterministic.

The starter computes a **host fingerprint**, not the raw text SHA-256. Grok
implements it through a namespaced serialized request hash. This differs from
the MAF example's raw-file hash and is intentionally not called equivalent.

Native source validation uses the reviewed `xai-workflow` example or its
`validate_script` API. Actual execution uses `run_workflow(WorkflowRunParams)`
with explicit script, args, Journal, host channel, cancellation, and operation
limits. Use the installed Grok integration's real capabilities; no unverified
CLI workflow subcommand or global workflow installation path is assumed here.

## Choose and validate the real host

Retain an existing suitable project engine. If a requested runtime is missing,
deliver its concrete native source and exact readiness gap. Do not relabel a
prose checklist, interpreter substitute, or another format as that runtime.
An alternative backend can be proposed when its actual semantics fit, but
conversion needs its own validation and cannot silently change effects or order.

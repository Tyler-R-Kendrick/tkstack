---
name: flowify
description: Turn a demonstrated procedure or explicit request into a reusable executable workflow using an existing DSL. Use for /flowify, automate this workflow, MAF declarative YAML, or Grok-style Rhai definitions. Prefer deterministic code bindings, explicit dataflow and failure gates, bounded concurrency, real native validation, and reproducible execution evidence.
license: MIT
compatibility: "Python 3.11+ for the offline authoring helper. MAF inspection needs PyYAML 6.x; native MAF or Grok/Rhai validation/execution requires its actual runtime. Typed contract tools require Python 3.11+ and the managed command-schema runtime."
metadata:
  author: Tyler Kendrick
  version: "0.3.0"
---

# Flowify

<!-- tkstack:execution:start -->
Tool: `.tkstack/tkstack skills flowify -- <command>`. Omit the command for deterministic man-page help.

| Executable operation | Contract |
| --- | --- |
| Default/help and man(1) export | [Reserved help](commands/help.md) |
| Declared package version | [Reserved version](commands/version.md) |
| `model` | [Typed parameters](commands/model.md) |
| `verify` | [Typed parameters](commands/verify.md) |
| `native scaffold` | [Typed parameters](commands/native_scaffold.md) |
| `native inspect` | [Typed parameters](commands/native_inspect.md) |
| `native check` | [Typed parameters](commands/native_check.md) |
| Evidence, effects, native execution, and semantic boundaries | [Execution contract](references/execution.md) |

`model` reads the explicit contract; `verify` checks retained facts/evidence. Native commands execute existing code. Residual semantic decisions use the focused procedures below; a recorded review is not an independently authenticated judgment.
<!-- tkstack:execution:end -->


Create an executable reusable workflow in a suitable existing DSL. Define real
inputs, outcomes, bindings, dependencies, effects, resource limits, and evidence.
Authoring does not automatically schedule work or authorize downstream effects.
Look up existing code assets before implementing new bindings; use `reusify`
when available for repeated templates, generators, or shared runtime components.

| Work | Read before acting |
| --- | --- |
| Create, adapt, or update a workflow | [Operating guide](references/operating-guide.md) |
| Select MAF YAML, Grok-hosted Rhai, or an existing DSL | [Backend contracts](references/backends.md) |
| Design reliable execution and handoff | [Operations](references/operations-and-handoff.md) |
| Inspect, build a graph, validate, or execute | [Validation boundaries](references/validation.md) |

Use deterministic code bindings for factual work. Bound independent actions,
isolate mutable outputs, preserve required effect order, and define retries,
cancellation, deadlines, and unknown outcomes. YAML lists do not imply parallel
execution; Grok's host functions are not generic Rhai functions.

Use `scripts/flowify.py scaffold` for an absent owned target and adapt the draft
to the actual procedure. `inspect` is source inspection; `check` uses the native
builder/mock host; exit 3 means unavailable. Real execution and inspected outputs
are separate evidence. A parse or empty run is not proof of a working workflow.

Keep definitions, code, locks, input contracts, and invocation instructions
self-contained. Preserve the selected provider and task's budget/publication
scope. See [sources](references/sources.md) and [adaptations](references/distilled-sources.md).

For session/repository/workspace records, read [local state storage](references/storage.md).

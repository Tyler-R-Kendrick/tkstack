---
name: tkstack-principles
description: Apply tkstack's personal engineering principles when designing, implementing, or reviewing code, skills, hooks, rules, workflows, and harness configuration. Prefer deterministic code and explicit rules, then narrowly scoped decision models or APIs, with LLMs and agents as the last resort. Design all code for safe bounded concurrency and parallel composition.
license: MIT
compatibility: "Markdown only; no provider, harness, or runtime dependency. Typed contract tools require Python 3.11+ and the managed command-schema runtime."
metadata:
  author: Tyler Kendrick
  version: "0.3.0"
---

# Tkstack principles

<!-- tkstack:execution:start -->
Tool: `.tkstack/tkstack skills tkstack-principles -- <command>`. Omit the command for deterministic man-page help.

| Executable operation | Contract |
| --- | --- |
| Default/help and man(1) export | [Reserved help](commands/help.md) |
| Declared package version | [Reserved version](commands/version.md) |
| `model` | [Typed parameters](commands/model.md) |
| `verify` | [Typed parameters](commands/verify.md) |
| Evidence, effects, native execution, and semantic boundaries | [Execution contract](references/execution.md) |

`model` reads the explicit contract; `verify` checks retained facts/evidence. Native commands execute existing code. Residual semantic decisions use the focused procedures below; a recorded review is not an independently authenticated judgment.
<!-- tkstack:execution:end -->


Apply these principles when designing or reviewing code, skills, hooks, rules,
workflows, and harness configuration. Current instructions and an explicitly
selected workflow retain precedence. This index grants no delegation or effects.

Read the full reference whose trigger matches the current decision:

| Trigger | Principle |
| --- | --- |
| Policy, routing, judgment, or a repeated check | [Deterministic first](references/deterministic-first.md) |
| Code or executable workflow design | [Concurrency by design](references/concurrency-by-design.md) |
| Scope, abstraction, dependencies, or refactoring | [Smallest complete change](references/minimal-complete-change.md) |
| Data shapes, module ownership, or public behavior | [Interfaces and invariants](references/interfaces-and-invariants.md) |
| Completion claims, verification, or context expansion | [Evidence and context](references/evidence-and-context.md) |

Use deterministic code/facts/rules first, constrained decision models/APIs for
the unresolved part next, and LLMs/agents only for residual judgment. An LLM
behind an API remains inference; temperature zero does not guarantee determinism.

Design independent work for bounded parallel composition, private mutable state,
explicit dependencies, and stable fan-in. Serialize only for a real invariant,
ordering dependency, resource constraint, or valid measurement. Pure helpers do
not each need a worker pool, and parallelism does not authorize delegation.

The first two principles are the user's explicit standing preferences. The
additional references are curated adaptations requested from the installed
catalog, not invented correction evidence. Preserve source distinctions in
[the provenance notes](references/distilled-sources.md).

This package is self-contained. The dotfiles installer also links it at
`.agents/principles` and installs native startup pointers; a standalone package
needs an explicit pointer for automatic startup loading. Keep confirmed user
corrections in `learn` when available, not in a second authority ledger.

For session/repository/workspace records, read [local state storage](references/storage.md).

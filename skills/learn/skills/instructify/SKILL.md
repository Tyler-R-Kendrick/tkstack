---
name: instructify
description: Create, adapt, audit, and update scoped agent instructions from explicit preferences or verified workflows. Use for /instructify, turn this into agent instructions, maintain AGENTS.md or CLAUDE.md, and generate native instruction rules. Preserve existing content, choose the right durable layer, and preview deterministic managed updates.
license: MIT
compatibility: "Python 3.11+ for the optional offline planner and writer. Portable instruction data; project-file adapters for AGENTS.md, CLAUDE.md, Cursor, and Copilot. Typed contract tools require Python 3.11+ and the managed command-schema runtime."
metadata:
  author: Tyler Kendrick
  version: "0.4.0"
---

# Instructify

<!-- tkstack:execution:start -->
Tool: `.tkstack/tkstack skills instructify -- <command>`. Omit the command for deterministic man-page help.

| Executable operation | Contract |
| --- | --- |
| Default/help and man(1) export | [Reserved help](commands/help.md) |
| Declared package version | [Reserved version](commands/version.md) |
| `model` | [Typed parameters](commands/model.md) |
| `verify` | [Typed parameters](commands/verify.md) |
| `native plan` | [Typed parameters](commands/native_plan.md) |
| `native check` | [Typed parameters](commands/native_check.md) |
| `native apply` | [Typed parameters](commands/native_apply.md) |
| Evidence, effects, native execution, and semantic boundaries | [Execution contract](references/execution.md) |

`model` reads the explicit contract; `verify` checks retained facts/evidence. Native commands execute existing code. Residual semantic decisions use the focused procedures below; a recorded review is not an independently authenticated judgment.
<!-- tkstack:execution:end -->


Create or update stable scoped context with one canonical owner. Procedures,
tool enforcement, and correction history belong in their respective layers.
CLI lint-rule authoring belongs in `lintify` when available; instructions can
point to that native check without copying its rule implementation.

| Work | Read before acting |
| --- | --- |
| Create, audit, update, or remove instructions | [Operating guide](references/operating-guide.md) |
| Write clear selectors and minimize loaded context | [Context design](references/context-design.md) |
| Render a supported manifest | [Manifest](references/manifest.md) |
| Select native file/scope bindings | [Harness formats](references/harnesses.md) |

Inspect inherited instructions, imports, globs, and current owners. State each
instruction's trigger, changed action, verification, boundary, and real source.
Use conditional references to detailed Markdown; avoid duplicating every rule
in every host file or inventing a capability/permission through prose.

Use `scripts/instructify.py` to plan and inspect owned, hashed changes before
applying them. Preserve foreign content and native imports. Reconcile stale
plans and changed bindings; remove old bindings first when the helper requires
it. Audit/report requests remain read-only. Keep vendor/cache/home writes out
of incidental authoring, and distinguish generated files from actual host loading.
See [source adaptations](references/distilled-sources.md).

For session/repository/workspace records, read [local state storage](references/storage.md).

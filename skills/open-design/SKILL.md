---
name: open-design
description: Design or refine interfaces, prototypes, slides, and design systems using a portable brief and artifact-review workflow. Use for UI/UX creation, redesign, critique, or OpenDesign work. Explicit OpenDesign requests retain that provider and its actual runtime.
license: MIT
compatibility: "Markdown design guidance is portable. Rendering and OpenDesign execution require actual available tools; the standalone package supplies no application. Typed contract tools require Python 3.11+ and the managed command-schema runtime."
metadata:
  author: Tyler Kendrick
  version: "0.3.0"
---

# Open design

<!-- tkstack:execution:start -->
Tool: `.tkstack/tkstack skills open-design -- <command>`. Omit the command for deterministic man-page help.

| Executable operation | Contract |
| --- | --- |
| Default/help and man(1) export | [Reserved help](commands/help.md) |
| Declared package version | [Reserved version](commands/version.md) |
| `model` | [Typed parameters](commands/model.md) |
| `verify` | [Typed parameters](commands/verify.md) |
| Evidence, effects, native execution, and semantic boundaries | [Execution contract](references/execution.md) |

`model` reads the explicit contract; `verify` checks retained facts/evidence. Native commands execute existing code. Residual semantic decisions use the focused procedures below; a recorded review is not an independently authenticated judgment.
<!-- tkstack:execution:end -->


Resolve the requested design outcome and preserve product truth, accessibility,
and current identity outside the change scope. Use the available authorized
renderer; an explicit provider selection remains binding.

| Work | Read before acting |
| --- | --- |
| New surface, refinement, or redesign | [Brief and direction](references/design-brief.md) |
| Build, critique, polish, or validate UI | [Interface craft](references/interface-craft.md) |
| Capture tokens, components, or DESIGN.md | [Design system](references/design-system.md) |
| Execute through OpenDesign | [Provider adapter](references/open-design-adapter.md) |

Inspect existing source and actual visual evidence before choosing a direction.
Make the smallest complete change that serves the user's task. Use semantic
tokens and existing components; keep detail in the canonical design reference.
Inspect the rendered result at relevant sizes and states before claiming visual
quality. Missing captures remain unreviewed. Use `unslop` when available.

The provider adapter is conditional, not a dependency of the design procedure.
Do not invent tool calls, spend credits, publish, or switch providers as a side
effect of writing a design plan. See [source notes](references/distilled-sources.md).

For session/repository/workspace records, read [local state storage](references/storage.md).

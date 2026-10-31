---
name: rtk
description: Use Rust Token Killer to filter shell output, inspect measured token savings, or configure RTK integration. Preserve command semantics, native permissions, and an unfiltered route for exact evidence.
license: MIT
compatibility: "Harness independent guidance. Execution and native hooks require the actual RTK binary and a supported host adapter. Typed contract tools require Python 3.11+ and the managed command-schema runtime."
metadata:
  author: Tyler Kendrick
  version: "0.3.0"
---

# Rust Token Killer

<!-- tkstack:execution:start -->
Tool: `.tkstack/tkstack skills rtk -- <command>`. Omit the command for deterministic man-page help.

| Executable operation | Contract |
| --- | --- |
| Default/help and man(1) export | [Reserved help](commands/help.md) |
| Declared package version | [Reserved version](commands/version.md) |
| `model` | [Typed parameters](commands/model.md) |
| `verify` | [Typed parameters](commands/verify.md) |
| Evidence, effects, native execution, and semantic boundaries | [Execution contract](references/execution.md) |

`model` reads the explicit contract; `verify` checks retained facts/evidence. Native commands execute existing code. Residual semantic decisions use the focused procedures below; a recorded review is not an independently authenticated judgment.
<!-- tkstack:execution:end -->


Use for explicit RTK shell-output filtering or integration work. Before running
it, read [runtime and fidelity](references/runtime-and-fidelity.md).

Verify the actual executable and supported wrappers. Keep an unfiltered route
for exact errors and evidence; direct file tools do not pass through shell hooks.
Preserve native permission checks and command meaning. Report measured output
reduction without inventing billing savings. Headroom API routing remains an
explicit separate choice. See [sources](references/distilled-sources.md).

For session/repository/workspace records, read [local state storage](references/storage.md).

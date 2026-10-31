---
name: headroom
description: Use Headroom for explicit reversible context compression, CCR retrieval, or agent wrapping. Verify original-context fidelity and actual runtime readiness while preserving provider and account routing.
license: MIT
compatibility: "Harness independent guidance. Execution requires a real Headroom runtime; this package does not bundle it. Typed contract tools require Python 3.11+ and the managed command-schema runtime."
metadata:
  author: Tyler Kendrick
  version: "0.3.0"
---

# Headroom

<!-- tkstack:execution:start -->
Tool: `.tkstack/tkstack skills headroom -- <command>`. Omit the command for deterministic man-page help.

| Executable operation | Contract |
| --- | --- |
| Default/help and man(1) export | [Reserved help](commands/help.md) |
| Declared package version | [Reserved version](commands/version.md) |
| `model` | [Typed parameters](commands/model.md) |
| `verify` | [Typed parameters](commands/verify.md) |
| Evidence, effects, native execution, and semantic boundaries | [Execution contract](references/execution.md) |

`model` reads the explicit contract; `verify` checks retained facts/evidence. Native commands execute existing code. Residual semantic decisions use the focused procedures below; a recorded review is not an independently authenticated judgment.
<!-- tkstack:execution:end -->


Use for an explicit Headroom or reversible context-optimization request.
Before executing, read [runtime and fidelity](references/runtime-and-fidelity.md).

Verify the actual runtime, retain recoverable originals, and retrieve exact
content when decisions depend on it. Keep wrapping/proxy routing explicit and
preserve the selected account and provider. Report observed context reduction
separately from model usage and billing. A copied skill is not an installed
proxy or authenticated connection. See [sources](references/distilled-sources.md).

For session/repository/workspace records, read [local state storage](references/storage.md).

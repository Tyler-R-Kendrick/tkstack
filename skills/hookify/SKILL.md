---
name: hookify
description: Turn an explicit rule or confirmed recurring correction into a deterministic tool-event hook or workflow gate. Use for /hookify, create a command hook, or prevent this tool behavior. Route native CLI lint-rule authoring to lintify when available. Define precise predicates, replay cases, preserve configuration, and distinguish evaluation from native activation.
license: MIT
compatibility: "Python 3.11+ for the offline rule engine and replay. Bundled native adapter supports Claude Code PreToolUse and Stop command hooks; other harnesses require verified adapters. Typed contract tools require Python 3.11+ and the managed command-schema runtime."
metadata:
  author: Tyler Kendrick
  version: "0.3.0"
---

# Hookify

<!-- tkstack:execution:start -->
Tool: `.tkstack/tkstack skills hookify -- <command>`. Omit the command for deterministic man-page help.

| Executable operation | Contract |
| --- | --- |
| Default/help and man(1) export | [Reserved help](commands/help.md) |
| Declared package version | [Reserved version](commands/version.md) |
| `model` | [Typed parameters](commands/model.md) |
| `verify` | [Typed parameters](commands/verify.md) |
| `native check` | [Typed parameters](commands/native_check.md) |
| `native replay` | [Typed parameters](commands/native_replay.md) |
| `native emit` | [Typed parameters](commands/native_emit.md) |
| Evidence, effects, native execution, and semantic boundaries | [Execution contract](references/execution.md) |

`model` reads the explicit contract; `verify` checks retained facts/evidence. Native commands execute existing code. Residual semantic decisions use the focused procedures below; a recorded review is not an independently authenticated judgment.
<!-- tkstack:execution:end -->


Turn an explicit mechanically observable rule into enforcement at the right
boundary. Prefer deterministic code and existing type/lint/contract/CI checks.
For source/artifact lint-rule authoring, use `lintify` when available; a hook
may invoke its validated CLI rather than reproduce that detector.

| Work | Read before acting |
| --- | --- |
| Specify, implement, replay, or install a policy | [Operating guide](references/operating-guide.md) |
| Choose an enforcement boundary | [Placement](references/enforcement-placement.md) |
| Portable policy schema and replay | [Policy contract](references/policy.md) |
| Native registration and exit behavior | [Adapters](references/adapters.md) |

Define the actual event, typed inputs, predicate, effect, exceptions, and failure
behavior from stated policy. Do not activate inferred prohibitions. Warnings
are the unspecified-effect default; a block requires the actual requested rule.
Use `scripts/hookify.py` for its supported literal/typed predicates and bounded
stable replay. It is not a shell parser, arbitrary regex engine, or sandbox.

Keep portable evaluation, native registration, and observed activation distinct.
Only the bundled Claude PreToolUse/Stop adapter is implemented; other hosts need
verified adapters. Preserve existing config and owner boundaries, and never
enable demonstration policies. A denial does not authorize an alternate runner
to perform the same prohibited action. See [sources](references/sources.md) and
[distilled guidance](references/distilled-sources.md).

For session/repository/workspace records, read [local state storage](references/storage.md).

---
name: learn
description: Learn from user corrections, frustrations, workflow outcomes, and temporary .tkstack sessions. Use for /learn, help, repeated instructions, a rejected approach, session consolidation, report-only audits, or direct skillify/hookify/instructify/flowify/lintify/reusify/codify subcommands. Preserve provenance, extract scoped reasoning rules, and turn verified procedural lessons into reviewable reusable artifacts shared across harnesses.
license: MIT
compatibility: "Requires Python 3.11 or newer for the bundled helper. The steering format has no harness dependency. Typed contract tools require Python 3.11+ and the managed command-schema runtime."
metadata:
  author: Tyler Kendrick
  version: "0.7.0"
---

# Learn

<!-- tkstack:execution:start -->
Tool: `.tkstack/tkstack skills learn -- <command>`. Omit the command for deterministic man-page help.

| Executable operation | Contract |
| --- | --- |
| Default/help and man(1) export | [Reserved help](commands/help.md) |
| Declared package version | [Reserved version](commands/version.md) |
| `model` | [Typed parameters](commands/model.md) |
| `verify` | [Typed parameters](commands/verify.md) |
| `native capture` | [Typed parameters](commands/native_capture.md) |
| `native rule` | [Typed parameters](commands/native_rule.md) |
| `native experience` | [Typed parameters](commands/native_experience.md) |
| `native show` | [Typed parameters](commands/native_show.md) |
| `native sessions review` | [Typed parameters](commands/native_sessions_review.md) |
| Evidence, effects, native execution, and semantic boundaries | [Execution contract](references/execution.md) |

`model` reads the explicit contract; `verify` checks retained facts/evidence. Native commands execute existing code. Residual semantic decisions use the focused procedures below; a recorded review is not an independently authenticated judgment.
<!-- tkstack:execution:end -->


Capture visible user corrections and frustrations as evidence, then improve the
scoped reasoning rule behind the mistake. Tool observations and skill research
are procedural evidence, not user authority. Continue the user's active task.

Invoke `/learn <command> [request]` or `$learn <command> [request]`.
Use `help [command]` for read-only discovery; `<command> help` also requests
guidance. Native helper: `python3 <learn-directory>/scripts/learn.py help [topic]`;
running the helper without a command shows help without initializing state.

| Signal | Read before acting |
| --- | --- |
| Help, command syntax, parameters, or direct ___ify invocation | [Subcommands and handoff contract](references/subcommands.md) |
| Package a reusable procedure | [`skillify`](references/subcommands.md#skillify) |
| Enforce a tool-event policy | [`hookify`](references/subcommands.md#hookify) |
| Maintain scoped agent instructions | [`instructify`](references/subcommands.md#instructify) |
| Create a workflow in a native DSL | [`flowify`](references/subcommands.md#flowify) |
| Create a CLI lint rule | [`lintify`](references/subcommands.md#lintify) |
| Reuse code assets or bootstrap extraction with `init` | [`reusify`](references/subcommands.md#reusify) |
| Compile a prompt/Markdown procedure to a lock artifact | [`codify`](references/subcommands.md#codify) |
| Correction, frustration, or explicit preference | [Capture, reason, curate, verify](references/operating-guide.md) |
| Invoked /learn or consolidation of temporary sessions | [Session review, abstraction, mechanism selection, and execution](references/session-consolidation.md) |
| Workspace/user/global storage or layered steering | [Storage scopes and paths](references/storage.md), [commands](references/records.md#scoped-stores-and-session-commands) |
| Report/audit only | [Improvement and audit workflow](references/improvement.md) |
| Requested skill improvement | [Improvement workflow](references/improvement.md), then [structural learning](references/structural-learning.md) |
| Record schema, scopes, or helper commands | [Records](references/records.md) |
| Find Grok's original body | [Actual source findings](references/grok-build.md) |

Resolve the existing shared store before writing; standalone installs use the
workspace store by default; user/global scopes are explicit. Never write into
an installed plugin cache. Read layered curated rules with `show --all-scopes`.
Preserve exact evidence and provenance. Reuse matching rules, keep uncertain interpretations candidate,
retain retirement history, and honor the narrowest supported scope.

Use `scripts/learn.py` from this package for deterministic capture, rule updates,
experiences, rendering, and checks as specified in the operating guide. Only
actual user messages justify user correction records. Explicit report/audit is
read-only, including the ledger. Apply current instructions over older rules.

Handle help before feedback capture or session review. A direct ___ify command
hands only its request to the named skill; preserve its scope, nested subcommands,
parameters, and preview/audit intent. Read that installed skill's index and run
its actual procedure. If unavailable, report the missing dependency. The native
helper prints guidance; it does not execute a sibling skill.

Bare Learn or `consolidate` reviews selected `.tkstack/sessions/<session>/`
evidence, extracts scoped transferable principles, chooses the smallest set of
___ify mechanisms, and carries authorized generalizations through verification.
Raw session folders remain temporary/ignored; save useful evidence and durable
lessons outside them before cleanup. Automatic correction capture stays narrow.
For procedural changes, update a fitting owned skill before creating another.
Encode factual invariants in code when possible. Direct requested changes use
real engineering checks; automatic revision search retains SkillOpt's separate
held-out strict/no-regression gate. No private history mining or invented model
improvement. See [source adaptations](references/distilled-sources.md).

For session/repository/workspace records, read [local state storage](references/storage.md).

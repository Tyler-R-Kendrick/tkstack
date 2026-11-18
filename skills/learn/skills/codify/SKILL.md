---
name: codify
description: Compile a prompt, Markdown procedure, or skill into a verified executable workflow lock artifact. Use for /codify, transpile this prompt, compile Markdown to code, or cache a procedure so subsequent runs execute code with minimal inference. Owns the shared deterministic workflow templates used by skillify. Lower meaning once, freeze code and provenance, reject stale inputs, and run the artifact without reinterpreting its Markdown.
license: MIT
compatibility: "Markdown command interfaces require the bundled hash-locked PyYAML/jsonschema environment. Python 3.11+ and a POSIX host for the compiler/runner. Pure Python workflows need no models or package install. Typed contract tools require Python 3.11+ and the managed command-schema runtime."
metadata:
  author: Tyler Kendrick
  version: "0.5.0"
---

# Codify

<!-- tkstack:execution:start -->
Tool: `.tkstack/tkstack skills codify -- <command>`. Omit the command for deterministic man-page help.

| Executable operation | Contract |
| --- | --- |
| Default/help and man(1) export | [Reserved help](commands/help.md) |
| Declared package version | [Reserved version](commands/version.md) |
| `model` | [Typed parameters](commands/model.md) |
| `verify` | [Typed parameters](commands/verify.md) |
| `native check` | [Typed parameters](commands/native_check.md) |
| `native scaffold` | [Typed parameters](commands/native_scaffold.md) |
| `native compile` | [Typed parameters](commands/native_compile.md) |
| `native run` | [Typed parameters](commands/native_run.md) |
| Evidence, effects, native execution, and semantic boundaries | [Execution contract](references/execution.md) |

`model` reads the explicit contract; `verify` checks retained facts/evidence. Native commands execute existing code. Residual semantic decisions use the focused procedures below; a recorded review is not an independently authenticated judgment.
<!-- tkstack:execution:end -->

Semantic work stays with the invoking agent in its current conversation, model
and harness. Do not select another model or provider or launch another agent
harness. Deterministic local tools may support the current agent's work.



Translate the procedure once into native code, verify its contract, and publish
an executable `*.lock.json`. Subsequent runs execute the code frozen in that
artifact. Markdown is authoring input and tool discovery; avoid reconstructing
the algorithm on every invocation.

Tool: `python3 <codify-directory>/scripts/codify.py <command> ...`.
Commands: `scaffold`, `compile`, `check`, `run`, `commands`, `invoke`.
`commands` validates/exports Markdown tool signatures; `invoke` dispatches CLI or
OpenAI tool-call arguments into the same verified lock.
Every command package has reserved help/version discovery. Default help renders
a generated manual with fixed console rules; `help --format man` exports man(1)
source. Version reads declared package metadata. Discovery never invokes a lock.

| Work | Read before acting |
| --- | --- |
| Define/invoke subcommands, aliases, typed flags, or OpenAI tools | [Markdown command contract](references/command-definitions.md) |
| Lower a prompt/Markdown/skill into actual code | [Compilation procedure](references/compilation.md) |
| Invoke the compiler or execute its artifact | [Commands, parameters, and contracts](references/commands.md) |
| Understand frozen code, provenance, invalidation, and verification | [Artifact contract](references/artifact.md) |
| Keep residual semantic work with the invoking agent | [Host inference boundary](references/inference.md) |
| Reuse this engine from another authoring tool | [Reuse and ownership](references/reuse.md) |
| Compare with GitHub Agentic Workflows | [Sources and differences](references/sources.md) |
| Try a complete deterministic conversion | [Example source](examples/normalize-labels/PROMPT.md), [cases](examples/normalize-labels/cases.json) |

Use existing code/assets before generating new implementations. Keep workflow
control flow, facts, gates, retries, and bounds in code; leave residual
semantic judgment with the invoking agent. The compiler verifies supplied implementation and cases; it cannot
infer arbitrary natural-language meaning. The authoring agent completes that
one-time translation. A starter, prompt-forwarding wrapper, or passing example
is insufficient evidence of semantic equivalence.

Keep authored workflow definitions and lock artifacts in their requested/native
paths (a skill's `scripts/`). Keep private records, staging, and locks under
`.tkstack/`; read [local state storage](references/storage.md). Compilation runs
contract code; `check` and `compile --dry-run` are read-only. Running an artifact
executes trusted code with the caller's authority; it is not a sandbox.

When creating or running workflows, use finite default deadlines for supported
operations and an outer bound; retain elapsed time and timeout outcomes. Test
timeout recovery where meaningful. A deadline is not a performance SLO, and an
unsupported host timeout or uncertain remote effect must remain explicit.

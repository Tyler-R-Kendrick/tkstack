---
name: skillify
description: Compile a skill or demonstrated procedure into an executable workflow in the skill's scripts folder. Use for /skillify, convert a skill to a tool, capture a workflow, or create/adapt/update an owned skill. Treat Markdown as an intermediary code-mode prompt and invocation index. Prefer deterministic execution; configure Vercel AI SDK model, Decisions, or harness profiles only for residual inference. Preserve provenance and validate actual tool behavior.
license: MIT
compatibility: "Markdown command interfaces require the bundled hash-locked PyYAML/jsonschema environment. Python 3.11+ for packaging and pure-code workflows. Optional Vercel AI SDK backend requires Node 24+ and its locked npm dependencies; model/harness calls require explicit profiles and native access. Typed contract tools require Python 3.11+ and the managed command-schema runtime."
metadata:
  author: Tyler Kendrick
  version: "0.10.0"
---

# Skillify

<!-- tkstack:execution:start -->
Tool: `.tkstack/tkstack skills skillify -- <command>`. Omit the command for deterministic man-page help.

| Executable operation | Contract |
| --- | --- |
| Default/help and man(1) export | [Reserved help](commands/help.md) |
| Declared package version | [Reserved version](commands/version.md) |
| `model` | [Typed parameters](commands/model.md) |
| `verify` | [Typed parameters](commands/verify.md) |
| `native check` | [Typed parameters](commands/native_check.md) |
| `native scaffold` | [Typed parameters](commands/native_scaffold.md) |
| `native convert` | [Typed parameters](commands/native_convert.md) |
| `native normalize` | [Typed parameters](commands/native_normalize.md) |
| `native compile` | [Typed parameters](commands/native_compile.md) |
| Evidence, effects, native execution, and semantic boundaries | [Execution contract](references/execution.md) |

`model` reads the explicit contract; `verify` checks retained facts/evidence. Native commands execute existing code. Residual semantic decisions use the focused procedures below; a recorded review is not an independently authenticated judgment.
<!-- tkstack:execution:end -->


Compile the procedure into an executable workflow under the skill's `scripts/`.
The skill is an intermediary code-mode prompt: discover the tool, supply input,
invoke it, and inspect its output. Its main `SKILL.md` remains a table of
contents with invocation and direct topic/feature/subcommand/parameter pointers.

Tool entrypoint: `python3 <skillify-directory>/scripts/skillify.py <command> ...`.
Select `scaffold`, `convert`, `normalize`, `compile`, `check`, `commands`, or `invoke`.
Use the shared `commands`/`invoke` interface for Markdown-defined subcommands.
Skillify supplies reserved `help` and `version` commands for those interfaces.
Omitting a command renders the generated man page as deterministic console
text; `help --format man` emits its man(1) source. Neither requires a compiled
workflow. Do not reimplement these commands inside each skill.

| Work | Read before acting |
| --- | --- |
| Define commands, aliases, flags, parameters, or OpenAI tool signatures | [Subcommand authoring](references/subcommands.md) |
| Create, adapt, or update a skill | [Authoring procedure](references/operating-guide.md) |
| Convert an existing skill; define execution, tool I/O, and completion | [Executable workflows](references/executable-workflows.md) |
| Freeze a completed skill into a verified executable lock | [Compilation and run contract](references/commands.md#compile-a-completed-skill) |
| Configure chat/Responses, Decisions, or a harness through Vercel AI SDK | [Inference profiles](references/inference.md) |
| Design an index; organize topics, features, commands, and parameters | [Progressive disclosure](references/progressive-disclosure.md) |
| Invoke `scaffold`, `convert`, or `check` as a tool | [Commands and parameters](references/commands.md) |
| Scaffold/check the supported profile | [Validation scope](references/validation.md) |
| Choose between a skill, code asset, lint, hook, instructions, or workflow | [Mechanism selection](references/operating-guide.md#2-choose-the-durable-mechanism) |
| Adapt third-party material or distill a catalog | [Sources](references/sources.md), [distillation](references/distilled-sources.md) |

Update an existing suitable owned package first. Keep detailed Markdown in
`references/`, algorithms in `scripts/`, and resources/licenses inside the package.
Codify owns the reusable compiler/templates/runtime; this package carries a
generated standalone release copy. Compile a completed skill to
`scripts/workflow.lock.json`, then run that artifact instead of interpreting
its procedure again. Use deterministic
code for repeatable decisions; narrow decision models next, LLMs/harnesses last.
Preserve read-only audit scope,
source provenance, vendor snapshots, and unrelated configuration. A scaffold is
a draft; complete its executable behavior and native verification before delivery.
Structural checks do not prove behavior or model improvements.

For session/repository/workspace records, read [local state storage](references/storage.md).

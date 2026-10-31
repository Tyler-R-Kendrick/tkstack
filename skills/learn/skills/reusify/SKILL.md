---
name: reusify
description: Turn repeated code into reusable snippets, templates, macros, code generators, modules, libraries, or components. Use /reusify init to bootstrap deterministic code production from an existing codebase, or /reusify for a targeted pattern, repeated boilerplate, T4-style templates, Roslyn incremental generators, or shared components. Find and use existing assets before deriving another implementation; three occurrences or an upcoming third normally trigger extraction.
license: MIT
compatibility: "Harness independent. Python 3.11+ for optional read-only catalog/evidence helpers. Actual generation, compilation, editor expansion, and package checks require their native engines. Typed contract tools require Python 3.11+ and the managed command-schema runtime."
metadata:
  author: Tyler Kendrick
  version: "0.4.0"
---

# Reusify

<!-- tkstack:execution:start -->
Tool: `.tkstack/tkstack skills reusify -- <command>`. Omit the command for deterministic man-page help.

| Executable operation | Contract |
| --- | --- |
| Default/help and man(1) export | [Reserved help](commands/help.md) |
| Declared package version | [Reserved version](commands/version.md) |
| `model` | [Typed parameters](commands/model.md) |
| `verify` | [Typed parameters](commands/verify.md) |
| `native check` | [Typed parameters](commands/native_check.md) |
| `native find` | [Typed parameters](commands/native_find.md) |
| `native assess` | [Typed parameters](commands/native_assess.md) |
| Evidence, effects, native execution, and semantic boundaries | [Execution contract](references/execution.md) |

`model` reads the explicit contract; `verify` checks retained facts/evidence. Native commands execute existing code. Residual semantic decisions use the focused procedures below; a recorded review is not an independently authenticated judgment.
<!-- tkstack:execution:end -->


Produce future code by invoking canonical assets with explicit inputs. This
page indexes the optional skill commands and references; load only the branch
and prerequisites the request needs. An omitted subcommand stays valid.

| Command / topic | Read before acting |
| --- | --- |
| `/reusify [request]`: target a pattern or reuse a suitable existing asset | [Reuse procedure](references/authoring.md) |
| `/reusify init [scope]`: extract and register code-production assets from a codebase | [Init workflow](references/init.md) |
| `init` scope, asset kinds, limits, and preview behavior | [Init inputs and parameters](references/init.md#inputs-and-parameters) |
| T4-style templates or native project generators | [Templates and generators](references/templates.md) |
| Roslyn compiler-integrated generation | [Incremental generators](references/incremental-generators.md) |
| Snippets, modules, libraries, or components | [Reusable code assets](references/code-assets.md) |
| Native language macros and expansion contracts | [Macros](references/macros.md) |
| Publish a discoverable invocation and verify migrations | [Catalog and validation](references/catalog-and-validation.md) |
| Read-only `find`, `check`, or `assess` Python helper commands | [Helper contract](references/catalog-and-validation.md) |
| Attribution and native execution limits | [Sources](references/sources.md) |

Search existing assets first. Three verified occurrences or a requested third
use trigger the smallest fitting extraction; an explicit `init` or asset request
can act earlier. Preserve legitimate variation, caller behavior, and user scope.
Audit/preview stays read-only. Counts do not prove semantic equivalence.

Use native engines and deterministic code for repeated production; reserve
inference for unresolved initial design. Skill commands are agent workflows;
the optional Python helper is a separate read-only tool and has no `init`
subcommand. Sibling authoring skills are optional; see the reuse procedure for
mechanism routing. Installation alone does not run initialization.

For session/repository/workspace records, read [local state storage](references/storage.md).

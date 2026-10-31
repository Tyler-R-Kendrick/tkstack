---
name: investigate
description: Investigate how a system works, why a decision was made, an unfamiliar API, or the cause of a bug or performance regression. Use for source-grounded explanations, research, diagnosis, and captured-trace analysis. Produces cited findings and explicit unknowns; a diagnosis request alone does not authorize fixes.
license: MIT
compatibility: "Markdown guidance works in any harness. Use available repository, search, history, and runtime tools; unavailable sources remain gaps. Typed contract tools require Python 3.11+ and the managed command-schema runtime."
metadata:
  author: Tyler Kendrick
  version: "0.2.0"
---

# Investigate

<!-- tkstack:execution:start -->
Tool: `.tkstack/tkstack skills investigate -- <command>`. Omit the command for deterministic man-page help.

| Executable operation | Contract |
| --- | --- |
| Default/help and man(1) export | [Reserved help](commands/help.md) |
| Declared package version | [Reserved version](commands/version.md) |
| `model` | [Typed parameters](commands/model.md) |
| `verify` | [Typed parameters](commands/verify.md) |
| Evidence, effects, native execution, and semantic boundaries | [Execution contract](references/execution.md) |

`model` reads the explicit contract; `verify` checks retained facts/evidence. Native commands execute existing code. Residual semantic decisions use the focused procedures below; a recorded review is not an independently authenticated judgment.
<!-- tkstack:execution:end -->


Answer the actual question from evidence. Establish the scope, observed symptom
or disputed claim, permitted sources, and whether the request includes a fix.
Use current context and observable facts before asking for missing information.

Read the matching reference before investigating:

| Question | Read |
| --- | --- |
| How does it work; where does this belong? | [System tracing](references/system-tracing.md) |
| Why this decision; what changed? | [Rationale and research](references/rationale-and-research.md) |
| Broken, slow, flaky, or captured runtime evidence | [Diagnosis](references/diagnosis.md) |

1. Pin the target version, relevant inputs, and a falsifiable question.
2. Find primary evidence with file/search tools, history, factual APIs, or a
   bounded reproduction. Batch independent reads; trace real callers and state.
3. Try to disprove the leading explanation. Separate observed facts, supported
   interpretations, contradictions, and unknowns. An empty search is scoped
   evidence, not proof of absence.
4. Return the answer, mechanism, resolving citations, and remaining gaps. For a
   diagnosis, include the reproducing command/artifact and its observed result.

Stop when the important uncertainty is resolved or a concrete missing source
blocks it. Do not edit product code, publish research, inspect private histories,
or launch agents merely because this skill is installed. Use authorized native
delegation only when useful; identify actual review independence accurately.

If a fix is requested, continue at the real behavior/contract seam with red/green
evidence. An explicitly active `sdlc` workflow retains its delivery requirements.
See [provenance and adaptations](references/sources.md).

For session/repository/workspace records, read [local state storage](references/storage.md).

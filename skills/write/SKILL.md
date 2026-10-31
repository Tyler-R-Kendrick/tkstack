---
name: write
description: Develop a human-facing article, explanation, proposal, or narrative from supplied ideas or source material. Use for drafting, shaping an argument, or a collaborative writing session. Not for ordinary file writes, agent instructions, repository reference maintenance, or anti-slop grading alone.
license: MIT
compatibility: "Markdown only; no harness or model-provider dependency. Typed contract tools require Python 3.11+ and the managed command-schema runtime."
metadata:
  author: Tyler Kendrick
  version: "0.2.0"
---

# Write

<!-- tkstack:execution:start -->
Tool: `.tkstack/tkstack skills write -- <command>`. Omit the command for deterministic man-page help.

| Executable operation | Contract |
| --- | --- |
| Default/help and man(1) export | [Reserved help](commands/help.md) |
| Declared package version | [Reserved version](commands/version.md) |
| `model` | [Typed parameters](commands/model.md) |
| `verify` | [Typed parameters](commands/verify.md) |
| Evidence, effects, native execution, and semantic boundaries | [Execution contract](references/execution.md) |

`model` reads the explicit contract; `verify` checks retained facts/evidence. Native commands execute existing code. Residual semantic decisions use the focused procedures below; a recorded review is not an independently authenticated judgment.
<!-- tkstack:execution:end -->


Establish the audience, purpose, factual material, intended voice, and deliverable
from the request. Preserve the author's meaning and source material. A request
for a complete draft authorizes writing it without a paragraph-by-paragraph gate.

| Work | Read |
| --- | --- |
| Explore ideas or collect raw material | [Fragments](references/fragments.md) |
| Turn material into an argument or article | [Shape and grounding](references/shape-and-grounding.md) |

1. Read the supplied material. Identify what the reader already knows and the
   change in understanding or action the piece should produce.
2. Separate evidence, examples, and quotes from unsupported claims. Ground new
   concepts before later passages depend on them.
3. Choose a coherent opening and progression; draft to the requested scope.
   Ask the user to choose between alternatives only in an explicitly interactive
   session or when a material preference is genuinely missing.
4. Re-read the actual draft for continuity, factual support, voice, and purpose.
   Use `unslop` when available; it does not replace the writing task.

Keep raw notes distinct from the finished article. Re-read files before updating
them and preserve concurrent author edits. Do not invent an anecdote, quote,
statistic, citation, or stronger conclusion to fill a gap. Name the missing
material or narrow the claim. Publication is a separate authorized effect.

Agent instructions belong in `instructify`; reusable procedures in `skillify`;
repository knowledge maintenance in `document`, when those skills are available.
See [sources](references/sources.md).

For session/repository/workspace records, read [local state storage](references/storage.md).

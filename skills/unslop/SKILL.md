---
name: unslop
description: Identify and correct AI slop in writing, code, tests, websites, images, video, and audio. Use for /unslop, output grading, anti-slop review, or whenever the user identifies a slop pattern. Record actual corrections in the shared steering ledger, extract a scoped reusable criterion, and grade against the evolving catalog with artifact evidence and legitimate exceptions.
license: MIT
compatibility: "Python 3.11+ for the optional offline catalog helper. Visual and runtime review require tools that can inspect the actual artifacts. Typed contract tools require Python 3.11+ and the managed command-schema runtime."
metadata:
  author: Tyler Kendrick
  version: "0.4.0"
---

# Unslop

<!-- tkstack:execution:start -->
Tool: `.tkstack/tkstack skills unslop -- <command>`. Omit the command for deterministic man-page help.

| Executable operation | Contract |
| --- | --- |
| Default/help and man(1) export | [Reserved help](commands/help.md) |
| Declared package version | [Reserved version](commands/version.md) |
| `model` | [Typed parameters](commands/model.md) |
| `verify` | [Typed parameters](commands/verify.md) |
| `native show` | [Typed parameters](commands/native_show.md) |
| `native grade` | [Typed parameters](commands/native_grade.md) |
| `native check` | [Typed parameters](commands/native_check.md) |
| Evidence, effects, native execution, and semantic boundaries | [Execution contract](references/execution.md) |

`model` reads the explicit contract; `verify` checks retained facts/evidence. Native commands execute existing code. Residual semantic decisions use the focused procedures below; a recorded review is not an independently authenticated judgment.
<!-- tkstack:execution:end -->


Make the artifact serve its purpose and preserve the brief, facts, accessibility,
local conventions, and intended voice. A familiar pattern is a review cue, not
proof of authorship or a reason to erase useful behavior.

| Request | Read before acting |
| --- | --- |
| Inspect/fix or user identifies slop | [Operating guide](references/operating-guide.md) |
| Grade only | [Grading contract](references/grading.md) |
| Record/revise a pattern | [Records](references/records.md) |
| Code, tests, UI, images, video, or audio | [Artifact review](references/artifact-review.md) |

Load the current applicable criteria from the shared store using this package's
`scripts/unslop.py`; standalone seeds work without a preexisting ledger. Preserve
legitimate exceptions and personal/repository/task scopes. User corrections and
slop amendments share the learn evidence ledger; do not invent feedback from
research, tools, or inferred emotion. Uncertain patterns stay candidate.

Grade-only is read-only. Inspect actual artifacts; missing visual/runtime/media
evidence is unreviewed, not a passing score. Formal saved reports retain catalog
and artifact identities, coverage, and actual inspection attestations. Mechanical
checks cannot prove semantic quality, and taste cannot waive an objective floor.

Quiet review of a short response needs no saved report. For new source learnings,
see [research](references/research.md) and [adaptations](references/distilled-sources.md).

For session/repository/workspace records, read [local state storage](references/storage.md).

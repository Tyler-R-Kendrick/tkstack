---
name: hill-climb
description: Run a bounded, evidence-driven improvement loop for code, prompts, skills, websites, or generated media. Use for an explicitly requested measured improvement loop or as an SDLC subworkflow for qualifying feature work with an observable quality difference. Freeze a sensitive evaluation, measure baseline noise, change one hypothesis at a time, keep or revert from evidence, and confirm the winner on untouched cases.
license: MIT
compatibility: "Harness independent. Python 3.11+ for the optional offline comparison helper. Actual experiments require the project's runner and relevant runtime or media tools. Typed contract tools require Python 3.11+ and the managed command-schema runtime."
metadata:
  author: Tyler Kendrick
  version: "0.4.1"
  disable-model-invocation: "true"
---

# Hill-climb

<!-- tkstack:execution:start -->
Tool: `.tkstack/tkstack skills hill-climb -- <command>`. Omit the command for deterministic man-page help.

| Executable operation | Contract |
| --- | --- |
| Default/help and man(1) export | [Reserved help](commands/help.md) |
| Declared package version | [Reserved version](commands/version.md) |
| `model` | [Typed parameters](commands/model.md) |
| `verify` | [Typed parameters](commands/verify.md) |
| `native compare` | [Typed parameters](commands/native_compare.md) |
| `native experiment` | [Typed parameters](commands/native_experiment.md) |
| Evidence, effects, native execution, and semantic boundaries | [Execution contract](references/execution.md) |

`model` reads the explicit contract; `verify` checks retained facts/evidence. Native commands execute existing code. Residual semantic decisions use the focused procedures below; a recorded review is not an independently authenticated judgment.
<!-- tkstack:execution:end -->

Semantic work stays with the invoking agent in its current conversation, model
and harness. Do not select another model or provider or launch another agent
harness. Use deterministic local tools for supporting checks.



Improve an actual outcome through bounded attributable experiments. This skill
does not start an experiment, spend money, or expand merge authority by existing.
The invoking host agent carries out the loop using its existing tools and
authorized context. Perform bounded rounds in the same conversation.
Do not launch another agent runtime, provider or model.

| Stage | Read before acting |
| --- | --- |
| Start or resume an optimization | [Full experiment procedure](references/operating-guide.md) |
| Establish the feedback loop | [Instrument and loop](references/instrument-and-loop.md) |
| Compare paired case metrics | [Measurement contract](references/measurement.md) |
| Inspect example plan | [Plan template](templates/plan.json) |
| Build or improve a task-specific Git experiment harness | [Git-backed experiments](references/git-experiments.md) |
| Capture a task harness brief | [Task harness template](templates/task-harness.json) |

Ground the real workload and prove the instrument can distinguish good/bad
behavior. Freeze inputs, metric, runner, grader, guardrails, splits, threshold,
and budget. Measure unchanged noise before proposing a win. Inspect actual
failures; distinguish a failed launcher or empty trace from model behavior.

Change one causal hypothesis per round; compare with the same incumbent; keep
or revert from actual evidence and retain rejected attempts. Bound independent
work, isolate mutable state, and avoid contention that invalidates measurement.
Confirm a fixed winner on untouched cases. Preserve user targets and stop rules.

Use the real project runner; `scripts/hill_climb.py` checks supported receipts,
not experiment truth. Missing proof stays inconclusive. An active SDLC workflow
retain their guarantees when they do not require another agent or model. See
[sources](references/sources.md) and [added synthesis](references/distilled-sources.md).

For session/repository/workspace records, read [local state storage](references/storage.md).

---
name: evalify
description: Design, run, and calibrate model-graded evaluations for nondeterministic outputs and agent workflows using established evaluation frameworks.
license: MIT
compatibility: Python 3.11+ for typed commands; a separately installed Promptfoo CLI and selected model providers are required for native evaluations.
metadata:
  author: Tyler Kendrick
  version: "0.1.0"
---

# Evalify

Use `/learn evalify` for a nondeterministic behavior that needs an empirical
or model-graded evaluation. Read [evaluation design](references/evaluation.md)
before choosing a framework, grader, dataset or metric. Prefer deterministic
checks for objective contracts, then a calibrated model judge for the remainder.

The typed runner is `.tkstack/tkstack skills learn -- evalify <command>`:

| Command | Contract |
| --- | --- |
| `help`, `version`, `model`, `verify` | [help](commands/help.md), [version](commands/version.md), [model](commands/model.md), [verify](commands/verify.md) |
| `native validate` | [Validate a Promptfoo configuration](commands/native_validate.md) |
| `native run` | [Run a bounded Promptfoo evaluation](commands/native_run.md) |
| Native effects, deadlines and limits | [Execution contract](references/execution.md) |

The package supplies a [locked Promptfoo dependency](requirements/package-lock.json)
but neither installs it nor selects a model or provider. Native runs use an
explicitly supplied executable and configuration, can call external services and
execute project-provided code, and retain a separate timing receipt. A passing
framework run or mock grader is not evidence that a judge is reliable.

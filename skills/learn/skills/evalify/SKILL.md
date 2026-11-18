---
name: evalify
description: Evaluate nondeterministic behavior using judgments made by the invoking agent and offline community-framework scoring.
license: MIT
compatibility: Python 3.11+ for typed commands. Offline scoring uses Node.js and the packaged Promptfoo dependency lock; it does not invoke a model.
metadata:
  author: Tyler Kendrick
  version: "0.1.0"
---

# Evalify

Use `/learn evalify` for a nondeterministic behavior requiring a structured
semantic judgment. The agent already executing this skill makes the judgment
in its current conversation using its current model and harness. Do not select
another provider or model, start a separate agent harness, or claim that this
same-context judgment is independent.

Read [evaluation design](references/evaluation.md) for datasets, calibration,
timing and limits. Use deterministic checks for objective contracts. The
packaged Promptfoo assertions are used only as an offline library for scoring
retained judgments against reference labels; they do not generate judgments.

The typed runner is `.tkstack/tkstack skills learn -- evalify <command>`:

| Command | Contract |
| --- | --- |
| `help`, `version`, `model`, `verify` | [help](commands/help.md), [version](commands/version.md), [model](commands/model.md), [verify](commands/verify.md) |
| `native validate` | [Validate retained host judgments](commands/native_validate.md) |
| `native run` | [Score retained judgments offline](commands/native_run.md) |
| Native effects, deadlines and limits | [Execution contract](references/execution.md) |

The helper accepts no model, provider, external executable or arbitrary
framework configuration. An input's `invoking-agent` label and elapsed times
are supplied records, not authenticated host provenance. If the host cannot
provide independent labels, timing or a genuinely unseen case, report the
missing evidence rather than starting another model or inventing a result.

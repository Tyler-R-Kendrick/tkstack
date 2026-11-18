---
name: constrain
description: Enforce repository constraints when adding or reviewing tests, files, folders, or documentation. Use for constrain, test-value review, sparsity budgets, or preventing low-value CI noise. Run deterministic checks, inspect behavioral oracles, and retain only tests with distinct regression value.
license: MIT
compatibility: Python 3.11+ and Git for the standalone checker. Python mutation experiments also require POSIX waitid and the separately installed locked Cosmic Ray tool. Typed commands use tkstack's shared runtime.
metadata:
  author: Tyler Kendrick
  version: "0.1.0"
---

# Constrain


Semantic work stays with the invoking agent in its current conversation, model
and harness. Do not select another model or provider or launch another agent
harness. Use deterministic local tools for supporting checks.

Run `python3 <installed-skill>/scripts/constrain.py check --repo <workspace>`.
The source checkout and checked workspace are separate inputs. Omitted typed
commands show help. Use the installer's `--target /absolute/project --adopt` to
initialize a project-owned policy. Review its budgets and test inventory in the target.
The typed runner is `.tkstack/tkstack skills constrain -- <command>`:

| Command | Parameters and contract |
| --- | --- |
| `help` | [Reserved help and man export](commands/help.md) |
| `version` | [Package version](commands/version.md) |
| `model` | [Read the contract](commands/model.md) |
| `verify` | [Verify a retained review report](commands/verify.md) |
| `native check` | [Enforce explicit repository policy](commands/native_check.md) |
| `native audit` | [Inspect repository findings](commands/native_audit.md) |
| `native mutate` | [Run a bounded Python mutation matrix](commands/native_mutate.md) |

Report-shape validation records a review; it does not run the repository gate.
Use `native check` for enforcement. [Execution details](references/execution.md)
describe the actual compiled boundary.

## Choose the enforcement mechanism

Use the strongest direct constraint that actually covers the boundary:

1. **Types and compile-time checks:** model valid states with types, exhaustive
   variants, constructors or compile-time validation whenever they can rule out
   an invalid state. Parse untrusted runtime inputs into those representations
   once. A type annotation alone does not validate JSON, I/O or Python execution.
2. **Lintify:** enforce a repeated statically observable source/artifact rule;
   use an existing compiler/linter rule before authoring another. A linter
   cannot prove arbitrary behavior from syntax.
3. **Testify:** exercise a distinct runtime contract or regression through the
   least expensive meaningful layer, with an independent oracle and a demonstrated
   fault. Do not retest a language/type guarantee merely to increase coverage.
   **Evalify** handles residual nondeterministic outcomes requiring a calibrated
   evaluation; deterministic assertions and actual state remain separate gates.
4. **Hookify:** enforce an observable tool event when that event is the actual
   boundary; it may invoke the same checked linter and cannot intercept every
   possible route. Git and CI enforce at their own snapshots/phases.
5. **Skillify, Codify and instructions:** Skillify packages reusable agent
   procedures; Codify compiles executable procedures once; Instructify owns
   scoped standing context. A skill guides semantic or contextual work; its
   presence is not enforcement. Combine mechanisms for distinct gaps rather
   than duplicating the same check.

| Trigger | Load the internal reference |
| --- | --- |
| Rank and measure test value, improve a suite, or review redundancy | [Test-value review](references/tests.md), [verification selection](references/selection.md) |
| Verification depth, proofs, or test layers | [Verification selection](references/selection.md) |
| Package integrity, GitOps sources or external dependencies | [Dependencies](references/dependencies.md) |
| Binary, package, or deployment limits | [Artifact size](references/artifacts.md) |
| Files, folders or documentation ownership | [Structure and documentation](references/structure.md) |
| CI resource, job or timeout budgets | [Execution](references/execution-budgets.md) |
| Interfaces, state ownership and allowed effects | [Boundaries](references/boundaries.md) |
| Policy schema or gate integration | [Configuration](references/configuration.md), [enforcement](references/enforcement.md) |

These documents are private references within this skill, not independently
registered or installed skills. The shared engine runs only implemented rules;
residual semantic and runtime obligations stay explicit in the selected reference.

Hard rules: identify a concrete regression before creating a test; prefer an
existing test or a table of cases for the same contract. Exercise production
behavior with an independent expected result. Remove redundant, tautological,
source-spelling, and mock-only assertions. Keep distinct boundary, recovery,
concurrency, and compatibility regressions even when short unit tests suffice.
Run the checker before and after edits. Inspect findings, repair tests, then
update only the reviewed suite's digest and risk/oracle record. Never regenerate
all review hashes to clear a failure. Missing policy is an error, not a pass.

The engine reads `.constrain/config.json` from the selected repository. It never
imports test code, calls a model, installs hooks, or writes review records.
Semantic value requires inspecting actual assertions and fault sensitivity;
a passing budget, coverage percentage, or reviewer attestation is insufficient.
The checker does not rank tests or optimize the suite. The separate mutation
command executes selected Python mutants and records per-test outcomes; it does
not decide which assertions are meaningful or which tests are safe to remove.
Use the test-value reference to plan and review those experiments.

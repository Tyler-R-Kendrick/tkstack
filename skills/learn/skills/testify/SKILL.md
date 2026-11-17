---
name: testify
description: Create or improve a high-value behavioral test for a concrete regression or boundary contract. Use for /learn testify, author a test, add a failure simulation, or evaluate redundant tests. Prefer static types and existing checks where they enforce the invariant; select the cheapest independent test that can detect the remaining fault.
license: MIT
compatibility: "Python 3.11+ for the bundled Python CLI test generator. The typed command interface requires tkstack's managed command-schema runtime. Other test types use their native project tooling."
metadata:
  author: Tyler Kendrick
  version: "0.1.0"
---

# Testify

For `/learn testify`, first read [test selection](references/selection.md). Identify
an actual fault and independent observable oracle; inspect existing tests and
production boundaries. Apply parse-don't-validate at input boundaries and use
static types/compile-time checks when they make the invalid state impossible.
Do not duplicate those checks with tests of language/library guarantees. Keep a
behavioral test for residual runtime risks such as external input parsing,
authentication, persistence, concurrency and failure propagation.

For a Python CLI boundary, `python3 <testify>/scripts/testify.py plan|create|run`
provides the [specific typed case contract](references/cli-contracts.md). Plan is
read-only; create refuses replacement; run executes the selected test with the
caller's authority. This backend does not infer correct expected outputs and does
not create property, proof, model-checking, UI, or arbitrary-language tests. Use
the project's real native framework for those. Exercise the test against a
controlled faulty implementation, restore it, and run the retained regression.

| Operation | Contract |
| --- | --- |
| Default/help and version | [help](commands/help.md), [version](commands/version.md) |
| `model`, `verify` | [model](commands/model.md), [verify](commands/verify.md) |
| `native plan` | [Plan without writing](commands/native_plan.md) |
| `native create` | [Create an absent test](commands/native_create.md) |
| `native run` | [Run a selected test](commands/native_run.md) |
| Effects and limits | [Execution contract](references/execution.md) |

The shared runner is `.tkstack/tkstack skills learn -- testify <command>`.
A recorded review is not an independently authenticated assessment or proof
that a test is sensitive to faults. Use Constrain for the repository policy;
use Lintify for a static artifact rule and Hookify for a precise tool-event gate.

---
name: lintify
description: Create, adapt, or configure a rule for a real CLI linter from an explicit standard or correction. Use for /lintify, turn this into a lint rule, enforce this with a linter, or author a Markdown prompt rule. Reuse native checks first, compile Markdown intent into deterministic rules when possible, and use semantic model-based linting only for residual judgment.
license: MIT
compatibility: "Harness independent. Python 3.11+ for the optional example scaffolder. Native validation requires the selected CLI/runtime; semantic linting additionally requires its authorized model access and budget. Typed contract tools require Python 3.11+ and the managed command-schema runtime."
metadata:
  author: Tyler Kendrick
  version: "0.2.0"
---

# Lintify

<!-- tkstack:execution:start -->
Tool: `.tkstack/tkstack skills lintify -- <command>`. Omit the command for deterministic man-page help.

| Executable operation | Contract |
| --- | --- |
| Default/help and man(1) export | [Reserved help](commands/help.md) |
| Declared package version | [Reserved version](commands/version.md) |
| `model` | [Typed parameters](commands/model.md) |
| `verify` | [Typed parameters](commands/verify.md) |
| `native scaffold` | [Typed parameters](commands/native_scaffold.md) |
| Evidence, effects, native execution, and semantic boundaries | [Execution contract](references/execution.md) |

`model` reads the explicit contract; `verify` checks retained facts/evidence. Native commands execute existing code. Residual semantic decisions use the focused procedures below; a recorded review is not an independently authenticated judgment.
<!-- tkstack:execution:end -->


Turn the stated standard into a versioned lint rule, native CLI configuration,
meaningful fixtures, and a reproducible command. A rule may be executable code,
a declarative query, Markdown compiled into a query, or a semantic prompt.

| Work | Read before acting |
| --- | --- |
| Create, adapt, update, or configure a rule | [Authoring procedure](references/authoring.md) |
| Choose an engine and native format | [Linter backends](references/backends.md) |
| Write a Markdown or semantic rule | [Prompt rules](references/prompt-rules.md) |
| Prove coverage, diagnostics, and CI behavior | [Validation and integration](references/validation.md) |

1. Identify the invariant, applicable files, real exceptions, severity, and
   observable violation from the request and current repository standards.
2. Reuse an installed linter/rule or configure it before writing a plugin.
   Prefer deterministic code/AST/query checks; use a constrained decision
   service next and an LLM only for genuinely unresolved semantic judgment.
3. Author the smallest native rule and config. Preserve existing rules and
   ignores. Keep per-file evaluation independent and concurrency bounded.
4. Run actual bad, good, transfer, and exception fixtures through the real CLI.
   Check target discovery, diagnostic location, and process exit behavior.
5. Integrate only the requested command/CI boundary, then report what it proves.

Markdown is a valid rule source. Lintbook can compile it to deterministic Datafox;
GPTLint can evaluate it with a model. A Markdown file alone is not enforcement,
and model-based linting is probabilistic even when its CLI gates on an exit code.

For a working example package, use `scripts/lintify.py scaffold --backend
eslint|lintbook|gptlint --target <absent-directory>`. Examples require adaptation
to the actual rule and are never activated by installation. A tool-event guard
belongs in `hookify`; reusable procedures in `skillify`; policy context in
`instructify`. Those siblings are optional. See [sources](references/sources.md).

For session/repository/workspace records, read [local state storage](references/storage.md).

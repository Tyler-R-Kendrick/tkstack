# Choose a real CLI

Use the project's existing tool when it can express the rule. The following are
concrete adapters, not an exhaustive list or a new lint execution engine.

| Need | First choice | Boundary |
| --- | --- | --- |
| Existing supported invariant | Native rule/config in the current CLI | Verify its actual target files and options |
| JS/TS syntax or types | ESLint/plugin, or the project's suitable equivalent | AST/type information must really be available |
| Cross-language structural pattern | Existing Semgrep/ast-grep or similar native query engine | Validate the exact engine dialect/version; do not mix query formats |
| Prose terminology or Markdown structure | Existing Vale/markdownlint or equivalent | Semantic truth is outside simple text/structure rules |
| Markdown-authored structural intent | Lintbook plus Datafox query and compiled artifacts | Markdown alone cannot be checked; compiled query must match the intent |
| Remaining semantic judgment | Narrow decision model/API, then GPTLint or another verified prompt-rule CLI | Explicit probabilistic coverage, privacy, model, budget, and failure contract |

## ESLint example

The bundled example has a native flat config, local rule object, RuleTester
cases, and CLI fixtures. It enforces a deliberately syntactic sample contract:
a direct `auditEvent(...)` call must supply one object literal with exactly one
static nonblank string `reason` property, without spreads or computed keys.
Method calls and other identifiers are outside this example's scope. It does
not prove binding identity or the quality of the stated reason.

```sh
npm ci --ignore-scripts --no-audit --no-fund
npm test
npm run lint:good
npm run lint:bad
```

Run from the generated package with its bundled npm integrity lock. The exact
direct requirement is ESLint
9.39.1. Adapt the rule to the real requirement; for an existing rule such as
`no-debugger`, configure the built-in instead of copying this plugin pattern.

## Lintbook example

The native layout is `lintbook.toml`, `.lintbook/rules/<stem>.md`, a matching
`.lintbook/gen/<stem>.df`, and compiled `.json` produced by the real compiler.
The example describes Rust `dbg!` detection using the published Datafox shape.

```sh
lintbook compile
lintbook check --json fixtures/good.rs
lintbook check --json fixtures/bad.rs
```

Commit the reviewed Markdown, query, and actual compiled artifacts. Plain
compilation and checking are agent-free. `compile --agent ...` is opt-in
authoring and can invoke model execution; it is not needed for a complete query.
Validate supported languages, active built-ins, and native failure behavior for
the installed version. Do not manufacture compiled JSON from the prompt.

## GPTLint example

The native layout is `.gptlint/<name>.md` and `gptlint.config.mjs` with `ruleFiles`
and explicit rule levels. The example enables only its own sample rule, not
the upstream recommended set. Inspected upstream 1.6.0 supports JS/TS and
documents single-file model context; do not claim arbitrary file/project scope
because a schema has additional scope names.

```sh
gptlint --config gptlint.config.mjs --no-grit --print-config
gptlint --config gptlint.config.mjs --no-grit --dry-run --concurrency 2
```

In the generated npm package, `npm run inspect` and `npm run estimate` invoke
the local binary with these flags. Both npm examples contain dependency locks;
adapt/refresh them with the project's package manager if changing dependencies.
Config output may contain credential fields; inspect locally and redact before
retaining or sharing. Parsing/discovery and a free estimate do not prove semantic
detection. Real checks require the chosen supported model and authorized budget:
use the CLI's actual model/provider options, disable stale cache for evaluation,
and record the actual results. Never invent a model ID or silently use defaults
as though the user selected them. No real model run is triggered by scaffolding.

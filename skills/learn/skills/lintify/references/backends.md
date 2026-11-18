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
| Remaining semantic judgment | The invoking agent in the current conversation | State uncertainty and avoid claiming deterministic enforcement |

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
authoring; do not enable a separate model for skill execution.
Validate supported languages, active built-ins, and native failure behavior for
the installed version. Do not manufacture compiled JSON from the prompt.

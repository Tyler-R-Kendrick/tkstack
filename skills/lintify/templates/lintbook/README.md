# Markdown to deterministic lint

This source-format example needs a real compatible lintbook binary. It contains
Markdown intent and a matching Datafox query, but no fabricated compiled JSON.

```sh
lintbook compile
lintbook check --json fixtures/good.rs
lintbook check --json fixtures/bad.rs
```

Verify actual compilation, active built-ins, discovery, diagnostics, and exits
before claiming enforcement. Retain the native compiled artifacts with the
reviewed Markdown/query. The sample's macro text match is deliberately narrower
in scope than an assertion about runtime logging or resolved macro identity.

Native lintbook compilation was unavailable in the authoring environment. Do
not mistake source inspection for a native validation pass. The real tool's
supported distribution/build prerequisites remain an external requirement.

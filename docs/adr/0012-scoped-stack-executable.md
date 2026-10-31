# 0012: Generate a scoped executable for compiled skills and workflows

Status: accepted, 2026-10-30.

The user requested an executable inside `.tkstack` that runs skills/workflows
through the shared Codify signature/artifact contracts and existing model/provider
configuration. A harness skill invocation alone leaves repeated execution to
agent interpretation.

Generate `<state-root>/tkstack` for source and explicitly selected initialization
roots, plus a PATH shim. Keep the authored coordinator/installer in `scripts/`;
generated entrypoints and ownership receipts remain ignored. Source checkouts
stay durable. Standalone setup can explicitly select workspace/user/global
roots without a permission fallback or automatic machine-wide installation.

Resolve names using source defaults and scoped registries/discovery, with workspace
precedence over user/global. Reuse Codify's catalog, typed CLI/tool-call parsing,
artifact binding/freshness checks, and isolated frozen-code runner. A raw lock uses
the existing JSON interface. No runtime prompt interpretation, implicit compilation,
model fallback, dependency download, or new workflow DSL is introduced.

Use existing Vercel AI SDK profiles. Select explicit configuration or the nearest
scoped document, project to declared profiles/providers, preserve its values and
environment references, and keep native SDK validation at the inference boundary.
Pure locks ignore ambient inference configuration. Child environments preserve
caller authentication/proxy/CA variables and select the actual execution workspace.
Model-enabled code retains its declared inference; dispatch requires none.

Read-only help/list/tools/check leave state unchanged. Bounded readers produce
stable readiness output. Publication uses source ownership receipts, atomic file
replacement, and a bounded OS writer lock, preserving foreign/modified executables.
A partial executable/receipt crash fails closed for inspection rather than adopting
unknown bytes. Bootstrap and doctor verify the generated entrypoints.

Behavioral evidence covers named skills and workflows, direct locks, aliases,
tool calls, scoped precedence, independent environments, stale/uncompiled failures,
repeated/concurrent setup, quoted source paths, and native SDK model/provider
selection with no provider/model calls.

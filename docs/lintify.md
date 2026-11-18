# Lintify

Use `/lintify <standard>` or `$lintify` to create or configure a native CLI lint
rule. The portable [package](../skills/learn/skills/lintify/SKILL.md) contains authoring and
validation procedures, conditional Markdown references, and isolated examples.

The result is a native rule/config, explicit scope/exceptions, meaningful good/
bad/transfer fixtures, an invocation, and observed enforcement evidence. Reuse
an existing project rule or linter before writing a plugin. The skill is an
authoring tool, not another lint engine.

For JS/TS, the installed [Landmines integration](integrations.md#landmines)
supplies existing Oxlint rules for testing, style, structure, and types. Review
its recommended policy and release-specific limits before enabling it.

Markdown is a first-class rule source. **Lintbook** compiles readable intent
plus Datafox into deterministic artifacts; ordinary checking needs no model.
The invoking agent handles any residual semantic judgment in its current conversation.

## Scaffold examples

```sh
python3 skills/learn/skills/lintify/scripts/lintify.py scaffold \
  --backend eslint --target /tmp/lintify-eslint-example
python3 skills/learn/skills/lintify/scripts/lintify.py scaffold \
  --backend lintbook --target /tmp/lintify-lintbook-example
```

Targets must be absent. The helper copies explicit native assets and a license,
refuses existing files/directories/symlinks, keeps caches out, and cleans its
own partial output on ordinary copy failures. One concurrent creator owns a
target. It does not install an engine, activate a policy, or call a model.

The npm examples include pinned direct requirements and integrity locks. Adapt
the actual rule, file scope, fixtures, and config at the project's existing
owner. Never replace a production config with an example. Runtime/model access,
publication, hooks, broad autofixes, and scheduling remain separate operations.

## Actual validation

Ignored receipts live under `.tkstack/evidence/lintify/`:

- Real **ESLint 9.39.1** RuleTester cases and CLI good/bad diagnostics/exits.
  Its sample requires a static literal reason in a direct `auditEvent` call.
  It is a syntactic contract, without binding identity or reason-quality claims.
- **Lintbook source inspection only.** No compatible binary was available;
  the inspected workspace needs a sibling Datafox checkout, and the latest
  GitHub release endpoint returned no release. Native compilation is unverified.
- Scaffolder ownership, collision, failure cleanup, standalone cache isolation,
  and missing/escaping resource checks.

All examples require actual engine verification before production use. A prompt
parse or compiled query is distinct from tested detection. False positives,
unknowns, empty discovery, timeouts, and CLI failures need explicit treatment.

Use `lintify` for file/artifact lint rules, `hookify` for tool-event guards,
`skillify` for reusable procedures, and `instructify` for standing context.
A hook can call a validated lint command when that integration is requested.

Prefer types or compile-time checks when they make an invalid state impossible.
Use `/learn testify` for a distinct observable runtime failure; a static lint
rule and a behavioral test may be combined for separate gaps.

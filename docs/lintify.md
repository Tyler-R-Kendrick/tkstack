# Lintify

Use `/lintify <standard>` or `$lintify` to create or configure a native CLI lint
rule. The portable [package](../skills/learn/skills/lintify/SKILL.md) contains authoring and
validation procedures, conditional Markdown references, and isolated examples.

The result is a native rule/config, explicit scope/exceptions, meaningful good/
bad/transfer fixtures, an invocation, and observed enforcement evidence. Reuse
an existing project rule or linter before writing a plugin. The skill is an
authoring tool, not another lint engine.

Markdown is a first-class rule source. **Lintbook** compiles readable intent
plus Datafox into deterministic artifacts; ordinary checking needs no model.
**GPTLint** evaluates native Markdown with a model for residual semantic judgment.
That path remains probabilistic even when the CLI exits nonzero on findings.
Prefer executable facts and narrow decision services before generative judgment.

## Scaffold examples

```sh
python3 skills/learn/skills/lintify/scripts/lintify.py scaffold \
  --backend eslint --target /tmp/lintify-eslint-example
python3 skills/learn/skills/lintify/scripts/lintify.py scaffold \
  --backend lintbook --target /tmp/lintify-lintbook-example
python3 skills/learn/skills/lintify/scripts/lintify.py scaffold \
  --backend gptlint --target /tmp/lintify-gptlint-example
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
- Real **GPTLint 1.6.0** parsing of Markdown/examples, malformed multiple-H1
  rejection, and native CLI rule/file discovery. The sample detects comments
  contradicting local filtering/ordering. No semantic/model evaluation ran.
  Config output can contain credentials and was not retained as raw evidence.
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

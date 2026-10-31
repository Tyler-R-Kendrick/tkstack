# Source analogues and adaptations

Reviewed 2026-10-30. These primary sources informed the independent implementation:

- Anthropic's [hookify command](https://github.com/anthropics/claude-plugins-official/blob/f8c5e7a1dcb71b10cb74586224b5401f3de5db28/plugins/hookify/commands/hookify.md),
  [writing-rules skill](https://github.com/anthropics/claude-plugins-official/blob/f8c5e7a1dcb71b10cb74586224b5401f3de5db28/plugins/hookify/skills/writing-rules/SKILL.md),
  and [rule engine](https://github.com/anthropics/claude-plugins-official/blob/f8c5e7a1dcb71b10cb74586224b5401f3de5db28/plugins/hookify/core/rule_engine.py):
  turn explicit unwanted behavior into scoped warn/block rules, combine
  conditions, preserve dynamic rule files outside the plugin, and combine
  matching decisions with block precedence.
- Anthropic's [hook-development skill](https://github.com/anthropics/claude-plugins-official/blob/f8c5e7a1dcb71b10cb74586224b5401f3de5db28/plugins/plugin-dev/skills/hook-development/SKILL.md)
  and [live hook reference](https://code.claude.com/docs/en/hooks):
  command hooks, native configuration, event-specific outputs, timeout/error
  behavior, isolated callbacks, and actual registration/loading verification.
- Pstack's [encode-lessons-in-structure principle](https://github.com/poteto/plugins/blob/74dd2291e8e37b12fd6dc49b2acbd655c6bdaf12/pstack/skills/principle-encode-lessons-in-structure/SKILL.md)
  and [shared-state principle](https://github.com/poteto/plugins/blob/74dd2291e8e37b12fd6dc49b2acbd655c6bdaf12/pstack/skills/principle-separate-before-serializing-shared-state/SKILL.md):
  encode objective rules at their actual enforcement boundary, isolate
  independent writers, and serialize only a real shared invariant.

There is no exact `hookify` in the checked Pstack tree. These principles are
its relevant analogues. The old Claude Code repository's plugin paths now
return 404; the official plugins repository contains the actual source above.

Deliberate differences: explicit JSON schema instead of permissive hand-parsed
YAML; literal predicates instead of arbitrary regex; no model or transcript
access in the runtime; no silent string coercion or unsupported-operator pass;
typed equality, stable aggregation, bounded replay, and an explicit error mode.
Only Claude PreToolUse and Stop have bundled native adapters. PostToolUse is
not represented as able to prevent an already-completed action. We do not copy
an “active immediately” claim before registration has actually loaded.

The source hook-development skill recommends prompt-based hooks. Tkstack's
explicit user preference overrides that default: deterministic command checks
come first, specialized decision services second, LLM/agent hooks last.
Subjective or stateful invariants outside this literal engine need a real
custom check rather than an increasingly broad substring rule.

Fixtures and adapter protocol tests establish local engineering behavior, not
native host activation or a measured change in model compliance. Upstream
snapshots and existing hook registration are preserved.

# Markdown intent and semantic lint rules

Markdown can describe a rule for deterministic compilation or guide semantic
review by the invoking agent in the current conversation.
If an AST/query can establish the invariant, generate that executable check once.
Do not repeatedly ask an LLM whether an objectively detectable pattern exists.

For either form, specify one rule with an ID, rationale, scope, actual violation,
known exceptions, good/bad examples, and the evidence required for a diagnostic.
Avoid broad requests such as "make code good" or "remove slop" with no observable
criterion. Keep correction policy separate from examples and unrelated style.

## Lintbook Markdown

Use its actual `id` and `lang` frontmatter, a readable body, and a same-stem
Datafox query. Compilation establishes native query validity; fixtures establish
whether it detects the intended distinction. Keep readable intent and executable
semantics in sync. Never report a prompt-only rule as a working check.

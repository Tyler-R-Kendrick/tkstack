# Keep correction evidence independent of the harness

Status: accepted. Date: 2026-10-30.

## Context

The user wants a `/learn` workflow that retains corrections and frustrations,
abstracts the reasoning failure, and applies the resulting lesson across
harnesses. A provider's private transcript or memory database cannot be the
portable source of truth.

## Decision

Use an append-only JSONL ledger for user evidence and rule lifecycle changes.
Compile explanatory pattern pages and a small active-rules Markdown file.
Keep candidate interpretations out of startup context. Scope accepted rules
and retain their supporting evidence, transfer cases, and limits. Explicitly
supersede changed preferences rather than silently broadening their scope.

Expose the workflow as a model- and user-invoked `learn` skill. Use plain native
instruction pointers in Codex, Claude Code, and Cursor to share the same store.
Keep WikiSkill as an optional validation backend; its runtime and traces do
not own the portable evidence format or become a prerequisite for capture.

## Consequences

Corrections survive harness changes and are inspectable through ordinary text
and filesystem tools. ADR 0007 places the local store under `.tkstack/` and
excludes raw session records from Git. Only active scoped rules consume startup context. Capture is
performed by the active agent following its instructions, so inaccessible
history cannot be reconstructed or claimed as captured. Structural tests
verify persistence and loading; behavioral improvement needs actual task
outcomes or held-out evaluation rather than an invented score.

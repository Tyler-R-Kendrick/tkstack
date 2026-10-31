# Personal agents

Add shared Cursor and Claude Code subagent definitions as `<name>.md`, with the
frontmatter expected by those harnesses. The installer links these alongside
`poteto-agent`, `ci-watcher`, and `thermo-nuclear-code-quality-review`.
Names must be unique across personal and upstream agents. This README is not
installed.

Codex agents use native configuration. Keep Codex-specific settings under
`harnesses/codex/`; Markdown agents are not automatically converted to native
Codex agents.

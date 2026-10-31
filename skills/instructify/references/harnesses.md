# Discovery and scoped bindings

Use shared guidance where a host supports it; generate a native rule only for
the scope/loading behavior that is actually needed. Check the installed host
and current instructions before selecting targets. Source references below were
read on 2026-10-30, not assumed to be interchangeable.

| Target | Repository scope | Directory scope |
| --- | --- | --- |
| `agents` | `AGENTS.md` | `<scope>/AGENTS.md` |
| `claude` | `CLAUDE.md` | `<scope>/CLAUDE.md` |
| `cursor` | `.cursor/rules/instructify-<id>.mdc`, always applied | Same native rule path, with explicit `<scope>/**/*` globs and `alwaysApply: false` |
| `copilot` | `.github/copilot-instructions.md` | `.github/instructions/instructify-<id>.instructions.md`, with `applyTo` globs |

## Shared AGENTS.md

[Codex discovery](https://developers.openai.com/codex/guides/agents-md) walks
from the project root toward the working directory, with at most one active
instruction file per directory. `AGENTS.override.md` takes precedence over
`AGENTS.md`; nonempty overrides must be reconciled before the helper writes
shared guidance. Empty override presence is included in plan snapshots so a
later edit makes the plan stale. Host configuration, fallback names, instruction
size limits, launch location, and lower scopes can affect what is loaded.

[Cursor](https://cursor.com/docs/context/rules) also supports root and nested
`AGENTS.md` guidance. Prefer `agents` for shared directory guidance in compatible
Codex/Cursor environments. Native `.mdc` rules provide a different attachment
mechanism. Do not emit both for the same instruction without a concrete reason;
explicitly selected targets are honored, not automatically deduplicated across
all host configuration.

## Claude

[Claude memory/instruction files](https://code.claude.com/docs/en/memory) support
`@path` imports, relative to the file containing the import. Imports are not
ordinary links and are skipped in code spans/fenced blocks. With both `agents`
and `claude` selected, the helper emits an owned `@AGENTS.md` import instead of
copying the shared body. An already existing standalone, unfenced unmanaged
`@AGENTS.md` line is reused and preserved. It is also snapshotted so changing
the import invalidates a pending plan. Other import spellings or sophisticated
loading chains require direct inspection; the helper uses a conservative profile.

Claude-only selection writes the body to scoped `CLAUDE.md`. Nested discovery,
imports outside the project, personal memory, host limits, and reload behavior
still need actual checking. Preserving a file does not imply a new session has
loaded it.

## Native Cursor and Copilot files

Cursor project rules require `.mdc` frontmatter. The helper sets explicit
always-apply or file-glob behavior instead of model-selected relevance. A path
rule attaches when the host references a matching file; this is not a permission
or isolation boundary, nor a guarantee every context mentions that file.

[GitHub Copilot](https://docs.github.com/en/copilot/customizing-copilot/adding-repository-custom-instructions-for-github-copilot)
supports repository-wide custom instructions and path-specific `.instructions.md`
files. Feature support and precedence vary by host/feature; agents can also
consume `AGENTS.md`. Avoid redundant or contradictory guidance when several
mechanisms are active. Generated native files have protected frontmatter and
are never substituted for a user's existing unowned file.

## Other instruction surfaces

The skill can edit explicitly requested agent profiles, personal instructions,
or other native formats using the host's actual schema and established source
of truth. The bundled helper does not claim those adapters. Preserve agent
frontmatter, tool/model restrictions, imports, and other owners' managed blocks.
Do not treat a role prompt as authorization to change permissions or spawn agents.

In this dotfiles repository, standing startup pointers belong to
`scripts/steering_adapter.py`, and the Cursor standing rule is sourced from
`harnesses/cursor/tkstack-steering.mdc`. Installed links and generated settings
are not their canonical editable source. A plain marketplace copy installs the
skill; actual instruction authoring is a separate requested operation.

# Portable authoring profile

`skillify.py` has `scaffold`, `convert`, `compile`, and `check` operations. `scaffold`
creates a new explicit directory with a draft `SKILL.md` tool index, linked
input/procedure/verification/tool references, an executable workflow/CLI starter,
and MIT license. The AI SDK backend adds its locked TypeScript runtime and
native tool export; direct raw-JSON execution in the pure Python backend has
no package dependency. The Markdown command interface additionally uses the
bundled hash-locked PyYAML/jsonschema recipe.
It uses exclusive directory
creation, so concurrent attempts at the same target cannot both overwrite it.
`check` only reads the selected package; it never imports or executes its helpers.
Owned-source inspection prunes `node_modules`, `__pycache__`, and `.git`;
installed dependencies are not treated as authored skill resources.
Command Markdown frontmatter is validated using the shared
[OpenAI tool and CLI binding contract](subcommands.md), including duplicate
names/routes/flags, typed defaults, reserved help, and contained artifact paths.
This uses safe JSON-compatible YAML and the command document schema; the main
SKILL.md frontmatter still uses the restricted profile described below.
`convert --dry-run` is read-only. Real conversion creates absent resources with
exclusive publication and retains the original Markdown as source data. It
preserves license/frontmatter, rejects collisions and unsafe paths, checks source
drift, and uses a cooperative package writer lock. Ordinary write errors attempt
owned rollback; crashes/nonparticipating writers are not a global transaction.

This helper deliberately supports a narrow profile without third-party runtime
dependencies. Required `name` and `description` are single-line scalars; the
scaffold uses JSON-quoted strings, which are valid YAML scalars. Simple plain
scalars and YAML single-quoted scalars are supported. Multiline YAML scalars
require another validator. Indented metadata is not fully schema-validated.
The package name must match its directory and use lowercase kebab-case within
64 characters; description is nonempty and at most 1024 characters.

Checks include completed scaffold prose across all Markdown resources, a bundled LICENSE, Python syntax, and
contained local inline Markdown links outside fenced code blocks. Links leaving
the package, missing resources, or symlinks to external content are rejected for
standalone portability. Remote URLs are not fetched. Optional cross-skill
dependencies should be named as conditional integrations rather than broken
relative links. The checker is not a full Markdown parser: advanced link syntax,
reference-style links, anchors, inline-code edge cases, and all YAML semantics
need an appropriate standard validator and/or direct inspection.

`check --require-tool` also requires a selected existing entrypoint within
`scripts/`. Supply `--entrypoint` for an existing differently named tool; otherwise
the helper selects exactly one `run.py`/`run.ts`. It rejects the starter's known
unimplemented `workflow.*`. This establishes source packaging only: Python syntax
is parsed, but TypeScript/native DSLs require their actual compiler/graph builder.
Absence of a marker does not prove behavior. Run native execution, verify real
inputs/outputs and effects, and inspect the actual tool interface before delivery.

Exit 0 means the requested scaffold/check succeeded; exit 1 means a collision,
invalid profile, unavailable resource, or syntax error. A successful scaffold is
still a draft. A successful check makes no claim about trigger quality, semantic
correctness, provider capability, tool execution, or measured model improvement.

Use meaningful behavior checks for scripts with observable contracts. Retain
real command output and artifacts when asserting runtime behavior. For a skill
that only expresses subjective preferences, a read-through and actual output
review can be more useful than superficial assertions about its prose.

`compile` is a separate behavioral build step through the owned Codify engine.
It executes supplied contract cases and emits a frozen executable lock only
after they pass. Structural `check` stays read-only. See [compile/run](commands.md#compile-a-completed-skill).

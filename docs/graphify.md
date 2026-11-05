# Graphify

The official [Graphify Labs](https://github.com/Graphify-Labs/graphify) local
integration is installed for Codex, Claude Code, and Cursor. Its PyPI package is
**`graphifyy` 0.9.97** (double y); the commands are `graphify` and `graphify-mcp`.
The runtime includes the local MCP extra. No cloud account is needed for local
code extraction or graph queries.

Use `$graphify` in Codex or `/graphify` in slash-command harnesses. Install
copies each host's upstream skill file to
`.tkstack/skill-views/graphify/<host>/graphify/SKILL.md`, plus that host's
reference pages. The copy is the upstream bytes. It does not rewrite commands,
install `graphifyy`, or start an index.

When `graphify` is on PATH, the upstream skill's own commands are the interface.
tkstack does not wrap them.

Code parsing uses the native tree-sitter extractors. Preserve `EXTRACTED` versus
`INFERRED` relationship labels and verify current source. Semantic extraction
for documents/media can use an agent or configured model and remains within the
requested provider, budget, and delegation scope. Installing the plugin does not
start that work, index this repository, enable Codex multi-agent mode, or start
a watcher. Optional media/provider/Leiden extras are not installed by default.

## Managed state and harness integration

Graph/index/cache state goes in `.tkstack/graphify/`, protected by the shared
ignore policy. Code-only `extract <directory>` uses the scanned directory's
`.tkstack/graphify/`; explicit `--out/--output` selects another output base. This
keeps distinct subfolder extractions separate. Queries use the active workspace.
Explicit GRAPHIFY_OUT must stay inside `.tkstack`; configured workspace roots
are supported. Session evidence belongs in `.tkstack/sessions/<session>/`.

GitHub clone cache defaults to `.tkstack/graphify/repos/<owner>/<repo>`; explicit
clone `--out` retains the requested source checkout destination. The managed
launcher declines native `install`, `uninstall`, and `global` commands: use
this repository's installer for owned integration files, and explicit graphs or
MCP project selection for repository context. Native global graph storage uses
`~/.graphify`, which is outside the managed state convention.

Install does not register a Graphify MCP server. A host that wants
`graphify-local` adds that entry in its own MCP config. Install does not
apply it.
The default relative output path preserves native `project_path` selection;
explicit absolute/shared output overrides select a fixed graph instead. This is
separate from Graphify's hosted OAuth service; no hosted account, workspace,
OAuth session, or remote repository indexing is changed here.

Claude receives the official native `hook-guard search/read` behavior through
the existing managed hook launcher. It supplies guidance when a graph exists,
fails open, and uses no strict-mode denial by default. Codex's native graph
hook is a no-op, so it receives the skill and MCP integration. Cursor receives
the skill, MCP integration, and a managed rule for using existing graph context.
Runtime readiness gates MCP and Claude hook registration.

`GRAPHIFY_NO_AUTO_REFRESH=1` prevents the upstream CLI from rewriting installed
skill/configuration files behind tkstack's source pins. Generated native views
adapt only interpreter/CLI invocation, local output/cache paths, and the setup
step. Their canonical source bytes remain unchanged under `vendor/graphify/`. Doctor
also checks generated view bytes/modes against the selected source and adapter.
Use a single installer for these destinations; Graphify's native registration
command should not manage tkstack-owned links or instructions.

## Reproduce installation

```sh
python3 scripts/install.py --target . --harness codex --harness claude --harness cursor
```

That links the three host views. It does not install `graphifyy` or register MCP.
The package version recorded with the source pin is **graphifyy 0.9.97**
(`sources.lock.json`). Installing that package is a host step. This repository
does not commit a Python dependency lock for it.

## Verification and limits

The source snapshot pins **32 files** to
[`0a8cd4e1e342235fe53e881fb5d591bf0460071f`](https://github.com/Graphify-Labs/graphify/tree/0a8cd4e1e342235fe53e881fb5d591bf0460071f),
including the native skill variants, all their sidecars, metadata, Apache 2.0
license, original MIT license, and NOTICE. Git blob identities and file modes
are recorded in `sources.lock.json`. A separate PyPI hash lock is not committed.

Native checks build a two-file fixture (5 nodes, 7 edges), verify an extracted
`calculate → double` call, query/path output, missing-symbol exit 4, the managed
Python launcher, a non-denying Claude hook response, and actual MCP initialization,
tool discovery, queries, and separation between two projects. The fixture reports
zero model input/output tokens. This is local protocol/CLI evidence, not a live
Claude/Cursor session, repository-wide graph, semantic model-quality evaluation,
or a measured token-saving claim.

The native MCP server reports an unknown tool in a normal text result with
`isError: false`; callers must not treat that text as a successful graph answer.
An absent/stale graph or unresolved symbol remains missing evidence. Reload
host sessions to discover the installed skill, hooks, rules, and MCP connection.

# Agent Plugins package

This checkout is an [Agent Plugins 1.0.0](https://agent-plugins.org/specification)
package. Clients that implement the spec load root `plugin.json`, discover
immediate `skills/*/SKILL.md` directories, and read root `mcp.json`. The
published schemas are vendored at `evals/repo-quality/schemas/` and checked by
`evals/repo-quality/checks.py` (`agent_plugins_conformance`).

```text
plugin.json
mcp.json
skills/<name>/SKILL.md
.claude-plugin/          Claude marketplace, outside the portable spec (§4.2, §11.3)
.cursor/rules/           Cursor-native rules, outside the portable spec (§4.2, §11.3)
.agents/                 Installer links, outside the portable spec (§4.2, §11.3)
```

`plugin.json` declares schema
`https://agent-plugins.org/schemas/1.0.0/plugin.schema.json` and the name
`tkstack`. It does not list skills or MCP servers. Those locations are fixed.

## Skills

Agent Plugins discovers an immediate child of `skills/` whose `SKILL.md`
resolves to a file inside the plugin root. An in-root symlink is included
(§4.1). A link that resolves outside the root is rejected. Learn's subskills
stay inside `skills/learn/skills/` and are not separate plugins.
`skills/skills.json` is the placement registry the
installer reads. It is a file, so discovery ignores it. `src/runner.json` is
the workflow runner registry. Runners are outside the v1 component types, so
it stays next to `src/tkstack.py`.

Each discovered `SKILL.md` uses the Agent Skills frontmatter fields (`name`,
`description`, `license`, `compatibility`, `metadata`, `allowed-tools`). The
`name` matches the directory. `hill-climb` and `sdlc` keep
`disable-model-invocation` inside `metadata`. The Agent Skills reference
validator rejects that key at the top level, and §7.1 says a non-conforming
skill must be skipped. Agent Plugins v1 has no skill-level extension point
(§8 is manifest-level), so the portable file cannot keep Claude Code's
top-level gate. Claude Code's skills reference treats `metadata` as an opaque
map and does not act on its contents (checked 2026-11-05), so those two
skills can still be auto-invoked there. Their descriptions say to invoke them
for an explicit measured-improvement or SDLC request. SDLC can also route
qualifying feature work through `hill-climb` as its measured subworkflow.
The invoking host agent uses its existing tools and any authorized native
delegation; this routing does not require another agent runtime or provider.

`.agents/skills/` (`fal-ai`, `headroom`, `open-design`, `rtk`) stays on the
Claude marketplace and the installer. Those packages are not immediate
children of `skills/`, so an Agent Plugins client does not discover them.

## MCP servers

The portable document declares Playwright, Firecrawl, Vercel and Graphify. The Node servers launch installed JavaScript under `${PLUGIN_ROOT}/integrations/mcp/node_modules`. Provision that exact checkout with the committed npm lock. Graphify reads `${PLUGIN_DATA}/graphify-out/graph.json` using the host-provided binary. Vercel uses client OAuth. Keep API keys in the host environment; the portable client expands only its specified plugin variables.

Serena requires the consumer project's absolute path. The portable protocol starts stdio processes in the plugin root by default. Use the project-scoped config emitted by `./install.sh --target /path/to/project --serena-command`. See [runtime provisioning and probes](integrations.md).

## Client files that stay where the host reads them

The spec puts client-specific plugin data under a reverse-domain `extensions`
key and a top-level directory of that same name (§8). A namespace is at least
two dot-separated lowercase labels, such as `com.example.client`. The
conformance check rejects any other key. The published schema only requires
each value to be an object. No client this repo targets publishes a namespace
it loads today. `plugin.json` therefore has no `extensions` object.

`.claude-plugin/`, `.cursor/rules/`, and `.agents/` sit outside those
reverse-domain directories. That is not a conformance violation. §4.2's
standard layout already shows extra files beside `plugin.json`, `skills/`,
and `mcp.json`, and there is no closed-package rule that forbids them.
§11.3 says a portable client ignores component types it does not implement,
so those directories do not affect Agent Plugins loading.

`.claude-plugin/marketplace.json` and `.claude-plugin/plugin.json` stay.
Marketplaces and install UX are outside the portable spec, so the Claude
marketplace can sit beside root `plugin.json`. Claude's manifest may list
`skills` paths. Root `plugin.json` must not: that field is not in the closed
schema.

`.cursor/rules/` stays. Rules are outside v1, and Cursor reads
`.cursor/rules`, not a reverse-domain directory. The installer still links
the tracked `.mdc` files. `.agents/` stays for the installer's steering and
principles links and for packages that are not immediate children of
`skills/`.

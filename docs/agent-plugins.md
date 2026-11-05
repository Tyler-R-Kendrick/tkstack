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
.claude-plugin/          Claude marketplace, outside the portable spec
.cursor/rules/           Cursor-native rules, outside the portable spec
```

`plugin.json` declares schema
`https://agent-plugins.org/schemas/1.0.0/plugin.schema.json` and the name
`tkstack`. It does not list skills or MCP servers. Those locations are fixed.

## Skills

Agent Plugins discovers only an immediate child of `skills/` whose `SKILL.md`
is a regular file. Learn's subskills stay inside `skills/learn/skills/` and
are not separate plugins. `skills/skills.json` is the placement registry the
installer reads. It is a file, so discovery ignores it. `src/runner.json` is
the workflow runner registry. Runners are outside the v1 component types, so
it stays next to `src/tkstack.py`.

Each discovered `SKILL.md` uses the Agent Skills frontmatter fields (`name`,
`description`, `license`, `compatibility`, `metadata`, `allowed-tools`). The
`name` matches the directory. `hill-climb` and `sdlc` keep
`disable-model-invocation` in `metadata` because that top-level field is a
Claude Code extension. The Agent Skills reference validator rejects it, and a
conformant client would skip the skill. Claude Code does not read the
metadata key, so those two skills can be auto-invoked there.

`.agents/skills/` (`fal-ai`, `headroom`, `open-design`, `rtk`) stays on the
Claude marketplace and the installer. Those packages are not immediate
children of `skills/`, so an Agent Plugins client does not discover them.

## MCP servers

`mcp.json` uses schema
`https://agent-plugins.org/schemas/1.0.0/mcp.schema.json`. Commands are one
executable token. No API key is stored in the file.

| Server | Launch | Source |
| --- | --- | --- |
| `serena` | `uvx --from git+https://github.com/oraios/serena serena start-mcp-server --project-from-cwd` | [Serena](https://github.com/oraios/serena) uvx quick start |
| `playwright` | `npx` with `@playwright/mcp@latest` | [Playwright MCP](https://playwright.dev/docs/getting-started-mcp) standard config |
| `firecrawl` | `npx -y firecrawl-mcp` | [Firecrawl local MCP](https://docs.firecrawl.dev/mcp-server/local) |
| `mobbin` | `https://api.mobbin.com/mcp` (Streamable HTTP, OAuth) | [Mobbin MCP](https://mobbin.com/mcp) |
| `vercel` | `https://mcp.vercel.com` (Streamable HTTP, OAuth) | [Vercel MCP](https://vercel.com/docs/agent-resources/vercel-mcp) |
| `graphify` | `graphify-mcp ${PLUGIN_DATA}/graphify-out/graph.json` | [Graphify MCP](https://docs.graphify.com/open-source/mcp-server) |

Agent Plugins expands only `${PLUGIN_ROOT}` and `${PLUGIN_DATA}` in `args`,
`env` values, and `cwd`. A conformant client leaves `${FIRECRAWL_API_KEY}`
as literal text and would replace an inherited key with that literal, so
`mcp.json` does not set `env`. Export `FIRECRAWL_API_KEY` in the environment
the client gives the stdio process. Firecrawl's cloud tools need it. The
hosted keyless endpoint `https://mcp.firecrawl.dev/v2/mcp` is a separate
Firecrawl mode and is not the shipped entry.

Mobbin and Vercel authenticate in the client. Mobbin's server is on Pro,
Team, and Enterprise plans. Vercel opens an OAuth consent screen. Neither URL
carries a token.

Graphify's local server is the `graphify-mcp` command from
`uv tool install "graphifyy[mcp]"`. The argument is the spec's portable
stand-in for the absolute graph path in Graphify's docs. Build or copy
`graph.json` into the client-managed plugin data directory before the server
can answer. Graphify also hosts `https://api.graphify.com/mcp` (Streamable
HTTP, OAuth, no API key). That hosted server is not the shipped entry.

When `cwd` is omitted, a conformant client starts stdio servers in the plugin
root. Serena's `--project-from-cwd` therefore activates this package unless
the client chooses another working directory. The installer still registers
and indexes a project directory; see [Install](bootstrap.md).

Playwright needs Node.js and downloads a browser on first use. Serena's uvx
command needs `uv` and network access the first time it resolves the git URL.

## Client files that stay where the host reads them

The spec puts client-specific plugin data under a reverse-domain `extensions`
key and a top-level directory of that same name. No client this repo targets
publishes a namespace it loads today. `plugin.json` therefore has no
`extensions` object.

`.claude-plugin/marketplace.json` and `.claude-plugin/plugin.json` stay.
Marketplaces and install UX are outside the portable spec, so the Claude
marketplace can sit beside root `plugin.json`. Claude's manifest may list
`skills` paths. Root `plugin.json` must not: that field is not in the closed
schema.

`.cursor/rules/` stays. Rules are outside v1, and Cursor reads
`.cursor/rules`, not a reverse-domain directory. The installer still links
the tracked `.mdc` files.

## Serena during install

On install, `scripts/install.py` runs, when `uvx` is on `PATH`:

```text
uvx --from git+https://github.com/oraios/serena serena init
uvx --from git+https://github.com/oraios/serena serena project index
```

`serena init` is Serena's documented language-server setup. `serena project
index` runs in the install target for `--scope project`, and in this checkout
for a home install. It does not index the home directory. `--dry-run` prints
both lines and does not run them. Uninstall prints `skip serena: uninstall`.
A missing `uv`, a missing `uvx`, or any non-zero exit (including an offline
fetch) prints `skip serena:` and the link step still finishes. The index can
write `.serena/` in the indexed directory. That directory is gitignored.

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
only for an explicit `/hill-climb` or `/sdlc` request.

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
| `firecrawl` | `npx -y firecrawl-mcp@3.33.2` | [Firecrawl local MCP](https://docs.firecrawl.dev/mcp-server/local) |
| `mobbin` | `https://api.mobbin.com/mcp` (Streamable HTTP, OAuth) | [Mobbin MCP](https://mobbin.com/mcp) |
| `vercel` | `https://mcp.vercel.com` (Streamable HTTP, OAuth) | [Vercel MCP](https://vercel.com/docs/agent-resources/vercel-mcp) |
| `graphify` | `graphify-mcp ${PLUGIN_DATA}/graphify-out/graph.json` | [Graphify MCP](https://docs.graphify.com/open-source/mcp-server) |

Agent Plugins expands only `${PLUGIN_ROOT}` and `${PLUGIN_DATA}` in `args`,
`env` values, and `cwd`. A conformant client leaves `${FIRECRAWL_API_KEY}`
as literal text (§9.2) and would replace an inherited key with that literal,
so `mcp.json` does not set `env`. Put `FIRECRAWL_API_KEY` in the MCP client's
environment UI for this server: Cursor's Settings → MCP env fields, Claude
Code's server env in `/mcp` or `claude mcp`, or Codex's MCP server env block.
A shell `export` reaches the process only when that client inherits the
shell. Firecrawl's cloud tools need the key. The hosted keyless endpoint
`https://mcp.firecrawl.dev/v2/mcp` is a separate Firecrawl mode and is not
the shipped entry.

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
command needs `uvx` on `PATH` and network access the first time it resolves
the git URL.

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

## Serena during install

On install, `scripts/install.py` runs, when `uvx` is on `PATH`, with the
working directory set to the indexed project (`--scope project` uses the
install target; home scope uses this checkout):

```text
uvx --from git+https://github.com/oraios/serena serena init
uvx --from git+https://github.com/oraios/serena serena project index <project>
```

`serena init` is Serena's documented language-server setup. It also writes
the user-global config at `~/.serena/serena_config.yml`. Setting the working
directory keeps project files in the selected directory and does not stop
that global write. `serena project index` receives `<project>` as its
`[PROJECT]` path, so it does not use the caller's working directory. It does
not index the home directory. `--dry-run` prints both lines and does not run
them. Uninstall prints `skip serena: uninstall`. When `uvx` is not on `PATH`,
or either command exits non-zero (including an offline fetch), install prints
`skip serena:` and the link step still finishes. The index can write
`.serena/` in the indexed directory. That directory is gitignored.

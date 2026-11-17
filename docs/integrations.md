# Integration readiness

A fresh dotfiles installation verifies selected links, launcher, steering and instruction ownership. Host trust, hook activation, service authorization and live tool calls have separate lifecycles. Use `~/.tkstack/tkstack status` from another project, or the project launcher after local setup. A standalone marketplace package follows its own client's activation rules.

| Integration | What TKStack supplies | Activation and observable check |
| --- | --- | --- |
| Serena | Project-specific stdio command and explicit indexing operation | Provision a trusted Serena executable through your host. Run `install.sh --target /repo --serena-command` for its argv, register it in the client's project configuration, then inspect the active project using Serena. `--index-serena` runs only against that explicit directory. |
| Playwright and Firecrawl | Portable MCP definitions and a committed npm dependency graph | In the plugin checkout run `npm ci --prefix integrations/mcp --omit=dev --ignore-scripts --no-audit --no-fund` using Node 22+. Open the host's MCP tool inventory. The lock selects Firecrawl SDK 4.54.0 to consume a patched Zod release. Recheck the SDK override when upgrading Firecrawl MCP. Playwright browser provisioning is separate. Supply Firecrawl credentials through the host for operations that require them. |
| Vercel | Portable HTTP MCP endpoint | Enable the plugin, complete client OAuth and inspect available tools. |
| Graphify | Catalog skills, Cursor rule and portable MCP definition | Supply `graphify-mcp` on PATH and a graph at the client-owned plugin data path. Query the intended graph. [Graphify](graphify.md). |
| Caveman, Ponytail, Impeccable, RTK, Headroom | Pinned source material, selected skills or agents, and upstream adapters where provided | Enable an adapter only in a host you choose. Verify a benign event in that host. A linked skill leaves lifecycle registration, binary installation and proxy activation to the host. [Caveman](caveman.md). |
| fal, OpenDesign, Higgsfield, Stitch | Design/media procedures in their applicable profiles | Select the provider, install its client or add its documented connection, authenticate there and inspect a test result. OpenDesign needs its application; Stitch needs project access. |
| OpenWiki, WikiSkill, SkillOpt | Pinned source and procedures in catalog placement | Provision the relevant CLI/model separately where required. [OpenWiki](openwiki.md) and [evaluation](skill-evolution.md). |
| Lever and GitHub Copilot | Catalog skills and repository-specific dial examples | Project owners choose their dials and native automations. [Lever](lever.md). |
| Constrain | Personal skill and project policy initializer | Adopt and review project policy, run the public checker, then exercise a failing staged change with the selected Git hook or CI job. [Bootstrap](bootstrap.md). |

Native Claude, Cursor and Codex do not acquire the portable MCP document merely by running the dotfiles installer. Inspect the client's actual registration (for example, `codex mcp list`). Plugin-capable hosts load the portable document through their own plugin route. Keep secrets in client-managed credentials or its environment. The installer performs no provider sign-in or network smoke call. The [portable specification and client packaging notes](agent-plugins.md) describe the distribution boundaries.

For a Claude project, register Serena in that project's local configuration from its root:

```sh
claude mcp add-json --scope local tkstack-serena "$(~/.local/share/tkstack/install.sh --target "$PWD" --serena-command)"
claude mcp get tkstack-serena
```

For Cursor, use the returned executable and argument array under a named entry in the project's MCP settings. For Codex, use the same values under `[mcp_servers.tkstack-serena]` in trusted project configuration and inspect `codex mcp get tkstack-serena`. Absolute paths belong in local settings. A native tools listing verifies registration; exercising a project-local query verifies the selected workspace.

On November 17, 2026, local stdio probes initialized both locked Node servers and listed 25 Playwright tools and 28 Firecrawl tools. A host-provisioned Serena launched from a third directory reported the requested active project through its initial instructions in two different disposable Git projects. These probes used no provider account or live browser task.

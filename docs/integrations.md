# Integration readiness

A fresh dotfiles installation verifies selected links, launcher, steering and instruction ownership. Host trust, hook activation, service authorization and live tool calls have separate lifecycles. Use `~/.tkstack/tkstack status` from another project, or the project launcher after local setup. A standalone marketplace package follows its own client's activation rules.

| Integration | What TKStack supplies | Activation and observable check |
| --- | --- | --- |
| Serena | Current local runtime and project-specific stdio command | Run `install.sh --target /repo --serena-command` for its argv, register it in the client's project configuration, then inspect the active project. `--index-serena` runs only against that explicit directory. |
| Playwright and Firecrawl | Current Node runtimes and portable MCP definitions | Open the host's MCP tool inventory. Playwright browser provisioning is separate. Supply Firecrawl credentials through the host for operations that require them. |
| Vercel | Portable HTTP MCP endpoint | Enable the plugin, complete client OAuth and inspect available tools. |
| Graphify | Current runtime, catalog skills, Cursor rule and portable MCP definition | Supply a graph at the client-owned plugin data path and query it. [Graphify](graphify.md). |
| Caveman, Ponytail, Impeccable, RTK, Headroom | Current source material, selected skills or agents, plus RTK and Headroom runtimes | Enable an adapter only in a host you choose. Verify a benign event in that host. Proxy activation remains a separate operation. [Caveman](caveman.md). |
| fal, OpenDesign, Higgsfield, Stitch | Design/media procedures in their applicable profiles, plus the Higgsfield runtime | Select and authenticate the provider, then inspect a test result. OpenDesign needs its application; Stitch needs project access. |
| OpenWiki, WikiSkill, SkillOpt | Current source and procedures in catalog placement, plus the OpenWiki runtime | Configure the relevant model or host connection where required. [OpenWiki](openwiki.md) and [evaluation](skill-evolution.md). |
| Lever and GitHub Copilot | Catalog skills and repository-specific dial examples | Project owners choose their dials and native automations. [Lever](lever.md). |
| Constrain | Personal skill and project policy initializer | Adopt and review project policy, run the public checker, then exercise a failing staged change with the selected Git hook or CI job. [Bootstrap](bootstrap.md). |
| Landmines | Current published plugin and Oxlint runtime | Run its recommended config against selected JS/TS files. [Landmines setup](#landmines). |

Native Claude, Cursor and Codex do not acquire the portable MCP document merely by running the dotfiles installer. Inspect the client's actual registration (for example, `codex mcp list`). Plugin-capable hosts load the portable document through their own plugin route. Keep secrets in client-managed credentials or its environment. The installer performs no provider sign-in or network smoke call. The [portable specification and client packaging notes](agent-plugins.md) describe the distribution boundaries.

For a Claude project, register Serena in that project's local configuration from its root:

```sh
claude mcp add-json --scope local tkstack-serena "$(~/.local/share/tkstack/install.sh --target "$PWD" --serena-command)"
claude mcp get tkstack-serena
```

For Cursor, use the returned executable and argument array under a named entry in the project's MCP settings. For Codex, use the same values under `[mcp_servers.tkstack-serena]` in trusted project configuration and inspect `codex mcp get tkstack-serena`. Set `TKSTACK_SERENA` to an executable path to select a different installation explicitly. Absolute paths belong in local settings. A native tools listing verifies registration; exercising a project-local query verifies the selected workspace.

On November 18, 2026, local stdio probes initialized the current runtimes and listed 25 Playwright, 28 Firecrawl and 11 Graphify tools. A host-provisioned Serena launched from a third directory reported the requested active project through its initial instructions in two different disposable Git projects. These probes used no provider account or live browser task.

## Landmines

Home dotfiles setup installs the latest published `@interfere/landmines` and
Oxlint packages. The [bundled source](../vendor/landmines/README.md) is a
historical reference; current upstream source revisions are recorded in the
local update receipt. Dotfiles setup provisions the current Node runtime.

Run the recommended rules as a separate pass from the target project, replacing
`src` with the files to inspect:

```sh
cd /absolute/path/to/project
~/.tkstack/bin/landmines src
```

This selects upstream's recommended configuration, not the project's existing
Oxlint configuration. Review its broad policies, including restrictions on test
doubles, comments, file names and return annotations, before adopting it in a
project-owned config or CI. Installation does not change project files or enable
a gate. At the time of the November 18, 2026 probe, the latest published release
was 0.1.0 and did not yet include upstream fixes for MSW 3, certain timer
callbacks and Vitest config timeouts. A Node 24 probe in a separate temporary
project reported testing, style, structure and type violations and accepted a
clean file including an allowed `WARNING:` comment.

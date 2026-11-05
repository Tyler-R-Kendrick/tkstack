# Integration setup and readiness

Updated 2026-10-30 (UTC). Installed skill bundles are pinned in this
checkout. Native hook registrations and the fal MCP connection are configured.
Runtime readiness is separate from those installed files. Use the root
`./install.sh` for complete provisioning and initialization; see
[dotfiles/bootstrap lifecycle hooks](bootstrap.md).

| Requested integration | Source | Installed here | Remaining runtime requirement |
| --- | --- | --- | --- |
| Impeccable | `pbakaus/impeccable` 4.8.0 | Provider-specific skill builds, four Claude/Cursor agents, hook registrations, engine checksums | Installed engine 0.1.18; native host restart/trust |
| Official Caveman | `JuliusBrussee/caveman` 4.0.1 | 22 skills, three Cavecrew agents, official plugin manifests and Node hooks for Codex/Claude/Cursor | Restart/trust in the native host; direct hook tests pass. See [setup](caveman.md) |
| Ponytail | `DietrichGebert/ponytail` 5.3.3 | Six skills, Node lifecycle-hook adapters | Native harness restart and any required hook trust; native session behavior not exercised here |
| Rust Token Killer | `rtk-ai/rtk` | Source guidance, RTK skill, native rewrite-hook adapters, verified release asset pins | Installed RTK 1.1.0; native host restart/trust |
| Headroom | `headroomlabs-ai/headroom` 0.42.0 | Source guidance and Headroom skill | Host installs headroom-ai 0.42.0 when it wants the CLI. This repo does not commit a Python lock. CCR operations need an explicit local proxy |
| OpenDesign | `nexu-io/open-design` | Official plugin manifest and MCP specification, local routing skill | Official local application/CLI via `OPEN_DESIGN_CLI` |
| Higgsfield | `higgsfield-ai/skills` 0.14.0 | All nine skills and their supporting scripts and references | Installed CLI 1.2.3; normal account authentication before media operations |
| fal.ai | First-party OAuth MCP relay | Provider skill in shared `.agents/skills/` and remote MCP entry for all three harnesses | Host OAuth sign-in, not verified by this file setup |
| WikiSkill | `ashutoshsinghpr7/wikiskill` 0.1.5 | Eight skills, working vendored Python CLI, isolated Codex workspace | No package download needed; actual evolution requires its normal model access and evaluation task |
| Graphify | `Graphify-Labs/graphify` 0.9.97 | Native skills, Claude guidance hooks, Cursor rule | Host installs graphifyy 0.9.97 when it wants the CLI. See [setup](graphify.md). |
| OpenWiki | `langchain-ai/openwiki` 0.7.2 | Official skill | Host installs the npm package 0.7.2 when it wants the CLI. See [setup and native evidence](openwiki.md) |
| Google Stitch `design-md` | `google-labs-code/stitch-skills` | The requested skill with its example and documentation | Stitch project access and `STITCH_API_KEY` for the staged MCP connection |
| Emil Kowalski skills | `emilkowalski/skills` at `c8a79627` | Complete 33-file tree, 17 skills (`prototype` installed as `emil-prototype`) | Shared `.agents/skills` placement; no extra runtime |
| ub-mode | `unclebob/ub-mode` at `3da62bf3` | The root skill, LICENSE, and README (MIT) | Shared `.agents/skills`. Companion crapper, dryer, and mutator tools are not vendored |
| SkillOpt-Sleep | `microsoft/SkillOpt` at `bc0a392` | Complete pinned Sleep package, handoff workflow, local evolution driver and decision regressions for learn/sdlc | Handoff uses fresh-context native agents; Codex CLI execution requires its normal network/model access |
| Lever | `github/lever` 0.1.0 at `f859d0a` | 16 skills in Codex/Claude/Cursor, per-project Copilot layout, templates, helper scripts, automation recipes and repo dials | Copilot host for native plugin sessions, models and automation tools; see [Lever setup](lever.md) |
| Grok Build learn behavior | Runtime source inspected at `2bdd1d6` | Independent learn 0.2 report/audit/improve workflow, typed procedural experiences, and read-only local body locator | Exact upstream learn prompt was not recovered; see [source findings](grok-learn.md) |

The WikiSkill repository is an independent paper implementation, not a Google
product. The Google Stitch skill is from Google's `google-labs-code` repository.
Only the requested `design-md` skill is selected from that repository.

## Portable MCP servers

Root `mcp.json` is the Agent Plugins MCP document. It ships Serena,
Playwright, Firecrawl, Mobbin, Vercel, and Graphify. Commands and URLs, the
`FIRECRAWL_API_KEY` requirement, and the decision not to write
`${FIRECRAWL_API_KEY}` into `env` are in [Agent Plugins](agent-plugins.md).
Install does not copy that file into `.cursor/mcp.json`, `.mcp.json`, or
`.codex/config.toml`. A client that loads Agent Plugins reads `mcp.json`
itself. OAuth for Mobbin and Vercel stays in the client.

`python3 scripts/install.py` links skills, agents, Cursor rules, and shared
steering, then runs Serena's `init` and `project index` when `uvx` works.
Vendored hook files are linked only when they are part of a skill or agent
tree. Install does not write a separate hook or MCP registration pass.

The `fal` server remains the first-party Streamable HTTP OAuth endpoint
documented at [fal's Codex setup](https://fal.ai/docs/documentation/setting-up/mcp/codex-cli).
It is not an entry in `mcp.json`. A host that wants it adds the connection
and runs `codex mcp login fal` on a normal local installation.

Stitch's endpoint is confirmed by the official
[Gemini Stitch extension](https://github.com/gemini-cli-extensions/stitch/blob/main/gemini-extension.json).
`STITCH_API_KEY` stays in the environment. It is not written into `mcp.json`.

## What install does

`python3 scripts/install.py --target .` links skills, agents, rules, and the
steering and principles directories, then initializes Serena as
[bootstrap](bootstrap.md) describes. It does not download Playwright, Firecrawl,
Graphify, or other CLIs. Versions of vendored sources are in
`sources.lock.json`. A host that wants a CLI installs that package itself.
Runtime files, when a host installs them, stay under `.tkstack/` and are not committed.
Serena's project index may write a gitignored `.serena/` directory.

OpenDesign's local app and provider account sign-ins remain host requirements.
The isolated MAF validation runtime described in [flowify](flowify.md) is separate.

RTK and Headroom are not silently stacked into API routing. RTK's adapter
handles shell-output rewriting when its binary is present; Headroom's proxy
and `wrap` flows are explicit. No API account or provider URL was redirected.

## Checks performed

- Verified all 1094 pinned source files across 19 sources, including modes and
  symlink targets. Emil Kowalski is the complete 33-file tree at
  `c8a79627b59d72d764d6ab6f2c87c09a48169833`. ub-mode is 3 files at
  `3da62bf3fcfd2034de41f30d920d2739e566171f`.
- Placement follows `skills/skills.json`. Personal skills install into every
  selected harness. `placement.default` sends other upstream skills, including
  Emil Kowalski (17) and ub-mode (1), to Codex (`.agents/skills/`), Grok, Kimi,
  OpenCode, GitHub Copilot (`~/.copilot/skills` or `.github/skills`), and Muse
  (`~/.config/muse/skills`, or `.agents/skills` in a project) when those
  harnesses are selected. The Muse home link does not follow `XDG_CONFIG_HOME`.
  The default install
  selects Codex, Claude Code, and Cursor, so that set lands in shared
  `.agents/skills` unless you pass `--harness`. Pstack and Cursor Team Kit stay
  Cursor-only. Graphify and Impeccable keep Codex, Claude Code, and Cursor.
  Learn's 7 subskills install only through `learn`.
  Lever's skills link with the other skills. Install does not write a Copilot project layout.
- Exercised fresh-checkout installation, provider-specific skill discovery,
  native configuration preservation, repeatability, scoped learning records,
  rule retirement, and selective removal in automated tests.
- Ran WikiSkill help, initialized its isolated workspace with the Codex backend,
  and inspected its status. No evolution or inference was started.
- Tested checksum rejection and archive-member installation with local fixtures.
  Those tests verify the installer; they do not claim real downloads ran here.
- Tested missing-runtime hooks and environment-only Stitch credential references.

The [learning guide](learning.md) explains how `/learn` uses the shared store and
how WikiSkill can evaluate proposed changes without replacing that format.

Graphify 0.9.97 has native platform skills, Claude query guidance hooks, and a
Cursor rule. `mcp.json` declares the local `graphify-mcp` command. This repo
does not commit a Python runtime lock or install the `graphifyy[mcp]` extra.
See [Graphify](graphify.md) for source pins, native evidence, and limits.

## Shared command tooling

CI creates `.tkstack/runtime/command-schema` from Codify's hash-locked
PyYAML/jsonschema recipe and runs `src/check_skills.py` with it. Install does
not create that environment. No account or model is needed for command discovery,
OpenAI-compatible schema exports, typed argument validation, or pure-code locks.
See [the command contract](../skills/learn/skills/codify/references/command-definitions.md).

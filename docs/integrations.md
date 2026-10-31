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
| Headroom | `headroomlabs-ai/headroom` 0.42.0 | Source guidance, Headroom skill, pinned Python runtime recipe and MCP specification | Installed from its Python hash lock; explicit local proxy for CCR operations |
| OpenDesign | `nexu-io/open-design` | Official plugin manifest and MCP specification, local routing skill | Official local application/CLI via `OPEN_DESIGN_CLI` |
| Higgsfield | `higgsfield-ai/skills` 0.14.0 | All nine skills and their supporting scripts and references | Installed CLI 1.2.3; normal account authentication before media operations |
| fal.ai | First-party OAuth MCP relay | Provider skill and remote MCP entry for all three harnesses | Host OAuth sign-in, not verified by this file setup |
| WikiSkill | `ashutoshsinghpr7/wikiskill` 0.1.5 | Eight skills, working vendored Python CLI, isolated Codex workspace | No package download needed; actual evolution requires its normal model access and evaluation task |
| Graphify | `Graphify-Labs/graphify` 0.9.97 | Native skills, hash-locked local CLI/MCP, Claude guidance hooks, Cursor rule | Installed; restart hosts. Code-only extraction needs no model key. See [setup](graphify.md). |
| OpenWiki | `langchain-ai/openwiki` 0.7.2 | Official skill, locked local npm CLI, and working stdio MCP for Codex/Claude/Cursor | Restart the harness; host-driven generation uses its existing session. See [setup and native evidence](openwiki.md) |
| Google Stitch `design-md` | `google-labs-code/stitch-skills` | The requested skill with its example and documentation | Stitch project access and `STITCH_API_KEY` for the staged MCP connection |
| SkillOpt-Sleep | `microsoft/SkillOpt` at `bc0a392` | Complete pinned Sleep package, handoff workflow, local evolution driver and decision regressions for learn/sdlc | Handoff uses fresh-context native agents; Codex CLI execution requires its normal network/model access |
| Lever | `github/lever` 0.1.0 at `f859d0a` | 16 skills in Codex/Claude/Cursor, per-project Copilot layout, templates, helper scripts, automation recipes and repo dials | Copilot host for native plugin sessions, models and automation tools; see [Lever setup](lever.md) |
| Grok Build learn behavior | Runtime source inspected at `2bdd1d6` | Independent learn 0.2 report/audit/improve workflow, typed procedural experiences, and read-only local body locator | Exact upstream learn prompt was not recovered; see [source findings](grok-learn.md) |

The WikiSkill repository is an independent paper implementation, not a Google
product. The Google Stitch skill is from Google's `google-labs-code` repository.
Only the requested `design-md` skill is selected from that repository.

## Native configuration

`python3 scripts/install.py --target .` now installs skills and shared steering,
then configures the native hooks and available MCP connections. Source paths
in the lock select Impeccable's distinct builds for each harness. Existing
settings and unrelated MCP servers remain in place; conflicting server names
stop setup before configuration is written.

- Codex: `.codex/hooks.json` and a marked MCP block in `.codex/config.toml`.
- Claude Code: `.claude/settings.json` and project `.mcp.json`.
- Cursor: `.cursor/hooks.json` and `.cursor/mcp.json`.
- Home installs use Claude's `.claude.json` for its user MCP connections.

Hook adapters point at pinned source files. Missing RTK or Impeccable binaries
leave tool calls untouched instead of triggering downloads from hooks. Native
Codex may require reviewing and trusting hook registrations through `/hooks`.
Ponytail's optional Claude UI band is not installed through these lifecycle
adapters. Actual native Cursor/Claude sessions were not exercised here.

The `fal` server uses the first-party Streamable HTTP OAuth endpoint documented
at [fal's Codex setup](https://fal.ai/docs/documentation/setting-up/mcp/codex-cli).
After the host connection is added, `codex mcp login fal` starts its browser
sign-in on a normal local installation. Host-managed plugin connections and
standalone CLI OAuth stores do not automatically share credentials.

Stitch's endpoint and header are confirmed by the official
[Gemini Stitch extension](https://github.com/gemini-cli-extensions/stitch/blob/main/gemini-extension.json).
When `STITCH_API_KEY` exists in the launching environment, rerunning setup adds
the server with an environment reference. The value is never written into
configuration. Headroom and OpenDesign MCP entries are activated when their
local runtimes are available. No placeholder executable is registered as a
working server.

## Runtime commands

```sh
python3 scripts/setup_integrations.py --status
python3 scripts/setup_integrations.py --target . --dry-run
python3 scripts/tool.py wikiskill status tkstack --ws .tkstack/wikiskill
```

The runtime installer is an explicit network operation:

```sh
python3 scripts/setup_integrations.py --target . --install-runtimes
```

It uses pinned release URLs and SHA-256 digests for RTK, Higgsfield, and the
Impeccable engine. It installs Headroom's pinned Python requirement into an
isolated environment. Linux x86-64/arm64 and macOS Intel/Apple Silicon assets
are recorded. Runtime files stay under `.tkstack/` and are not committed.
Headroom requires Python 3.11+. Dependencies resolved by its Python installer
are not claimed to be a complete transitive lock.

OpenWiki is installed from its npm integrity lock; use `--runtime openwiki`
with `--install-runtimes` to select only that package. Earlier binary/Python
runtime downloads were blocked during their setup, so RTK, Impeccable,
Higgsfield, and Headroom remain missing here. OpenDesign's local app and
provider account sign-ins remain host requirements. The isolated MAF validation
runtime described in [flowify](flowify.md) is separate.

RTK and Headroom are not silently stacked into API routing. RTK's adapter
handles shell-output rewriting when its binary is present; Headroom's proxy
and `wrap` flows are explicit. No API account or provider URL was redirected.

## Checks performed

- Verified all 1058 pinned source files, including modes and symlink targets.
- Installed 183 unique skills per main harness, ten Claude/Cursor agents per
  harness, four Cursor rules, shared steering and principles: 575 main links.
  Lever's separate Copilot layout adds 20 links and initial repository dials.
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

Graphify 0.9.97 now has a local hash-locked Python runtime, native platform skills,
`graphify-local` MCP configuration, Claude query guidance hooks, and a Cursor
rule. See [Graphify](graphify.md) for source pins, native evidence, and limits.

## Shared command tooling

The automatic `command-schema` runtime is installed privately from Codify's
hash-locked PyYAML/jsonschema recipe. Bootstrap generates `codify` and `skillify`
shims using its interpreter. No account or model is needed for command discovery,
OpenAI-compatible schema exports, typed argument validation, or pure-code locks.
See [the command contract](../skills/codify/references/command-definitions.md).

# tkstack

Personal agent dotfiles: portable skills, custom agents, harness settings, native
hooks, and compiled workflow tools. Pinned upstream packages include Pstack by
poteto, Theo's Tstack, Matt Pocock's skills, Impeccable, Caveman, Lever, Graphify,
OpenWiki, and the design/media integrations listed in the [inventory](docs/skills.md).

## Install

Use Bash, Git, and Python 3.11+ (3.12 recommended). Clone a revision containing
`install.sh` into a durable location:

```sh
git clone https://github.com/Tyler-R-Kendrick/tkstack.git "$HOME/.local/share/tkstack"
cd "$HOME/.local/share/tkstack"
./install.sh
. .tkstack/bootstrap/env.sh
```

The default target is your home. Setup installs private prerequisites and pinned
runtimes, applies skills/agents/rules/hooks/MCP configuration, initializes scoped
state and CLI launchers, installs this source repository's Git docs hook, and
verifies the result. Existing settings are preserved; conflicting foreign paths
stop setup. Keep the checkout because installed links and launchers reference it.

<!-- tkstack:profiles:start -->
| Profile | Harness configuration | Lever Copilot layout |
| --- | --- | --- |
| `dotfiles` | Codex, Claude Code, Cursor | Selected workspace |
| `devcontainer` | Codex, Claude Code, Cursor | Selected workspace |
| `codex-cloud` | Codex | Off |

Base requirements: Bash, Git, and Python **3.11+**.
Setup can provision private Node **24.19.0** and uv **0.12.23** when needed.
<!-- tkstack:profiles:end -->

Useful options:

```sh
./install.sh --profile codex-cloud       # Codex-only host configuration
./install.sh --target /repo --scope project --workspace /repo
./install.sh --offline                  # reapply files using cached runtimes
./install.sh --check                    # read-only verification
./install.sh --dry-run                  # read-only plan and collision checks
./install.sh --strict                   # fail for known unresolved prerequisites
```

Use repeated `--harness codex|claude|cursor` to select hosts. `--no-shell` leaves
shell startup files alone; source the generated environment yourself. Set
`CODEX_HOME` for a real-home Codex install. Restart/reload the harness after setup;
Codex may require reviewing new hook definitions with `/hooks` before they run.

OpenDesign needs its application/daemon and `OPEN_DESIGN_CLI`; Google Stitch
needs `STITCH_API_KEY`. Services may also require their normal account sign-in.
Setup reports these requirements and does not authenticate accounts, start a
proxy, redirect providers, run models, or index repositories. See
[bootstrap details](docs/bootstrap.md) and [integration readiness](docs/integrations.md).

## Devcontainers and Codex cloud

The included [devcontainer](.devcontainer/devcontainer.json) performs full setup
on creation and offline setup on subsequent starts. To use this repository as
VS Code dotfiles in another devcontainer, set these user settings:

```json
{
  "dotfiles.repository": "Tyler-R-Kendrick/tkstack",
  "dotfiles.targetPath": "~/.local/share/tkstack",
  "dotfiles.installCommand": "install.sh --profile devcontainer"
}
```

For a Codex cloud environment, clone/mount the durable checkout first, then use
these setup and cached-startup commands in its environment configuration:

```sh
bash "$HOME/.local/share/tkstack/scripts/codex-cloud-setup.sh" --workspace "$PWD"
bash "$HOME/.local/share/tkstack/scripts/codex-cloud-startup.sh" --workspace "$PWD"
```

Keep the checkout and its `.tkstack/runtime/` in the environment cache. The first
setup needs dependency network access; cached startup downloads nothing.
[Environment hook examples](docs/bootstrap.md) cover custom paths and project-only setup.

## Use skills and compiled workflows

Use `/skill-name` in Claude Code/Cursor, or `$skill-name` and the skill picker in
Codex. The [skill inventory](docs/skills.md) and [personal standards](docs/standards.md)
explain routing. Pstack owns `tdd`; Matt's version is `matt-tdd`.

[SDLC](docs/sdlc.md) coordinates durable task graphs in ignored local SQLite,
with explicit requirement/ADR revisions when development findings change the plan.
Use `.tkstack/tkstack skills sdlc -- help` for its deterministic task commands.

All **19 repository skills** now expose the shared typed command protocol and compiled
artifacts. Use `skills <name> -- model` for its contract, `verify --report ...` for
retained-evidence checks, and `native ...` for its available existing helper.
[Normalization and per-skill coverage](docs/normalization.md) records actual
behavior checks, semantic/native boundaries, and all 19 SkillOpt trials.

Common entrypoints include `sdlc`, `learn`, `unslop`, `hill-climb`, `investigate`,
`document`, `write`, and the authoring skills `skillify`, `codify`, `hookify`,
`lintify`, `instructify`, `flowify`, and `reusify`.

```text
/learn help
/learn help reusify
/learn reusify init src --preview
```

Setup also creates `.tkstack/tkstack` in selected workspace/user roots and a
`tkstack` PATH shim. Run compiled code through its declared command schema:

```sh
./.tkstack/tkstack help
./.tkstack/tkstack list workflows
./.tkstack/tkstack workflows normalize-labels -- normalize -l '[" b ","a","a"]'
./.tkstack/tkstack skills my-compiled-skill -- command --flag value
./.tkstack/tkstack tools skills my-compiled-skill --format responses
```

Skillify supplies reserved `help` and `version` commands for command packages.
Omitting a command renders a deterministic console manual; use `help --format
man` to export man(1) source. For example, `.tkstack/tkstack skills sdlc -- version`
prints SDLC's declared package version. Discovery works without a compiled lock.

The normalization workflow is runnable; `my-compiled-skill` is a placeholder for
an authored compiled package. Uncompiled skills require explicit Skillify/Codify
authoring and compilation. Dispatch validates parameters and artifact freshness,
then executes frozen code. It does not infer a skill's procedure. Declared model
calls remain inference. See [runner usage](docs/runner.md),
[Markdown command signatures](skills/codify/references/command-definitions.md),
and [compilation](docs/codify.md).

## Configuration and local data

Workspace, user, and global state use `<repo>/.tkstack`, `~/.tkstack`, and
`/etc/.tkstack`. `TKSTACK_WORKSPACE_DIR`, `TKSTACK_USER_DIR`, and
`TKSTACK_GLOBAL_DIR` can select other directories named `.tkstack`.

- `runner.json` registers explicit skill/workflow paths and optional configuration/dependency paths.
- `profiles.json` uses the existing Vercel AI SDK model/provider/decision/harness profile format.
- `sessions/<session>/` holds ignored temporary data; durable curated learning stays outside sessions.
- `reuse/catalog.json` records reusable code assets and can be versioned.

Normal setup does not create the machine-wide root. Credentials, histories,
runtimes, and generated launchers remain ignored. See [state conventions](docs/state-layout.md)
and [model/provider configuration](skills/codify/references/inference.md).

## Maintain this repository

Skills under active development live in `skills/`; third-party-derived packages
live in `.agents/skills/`, shared agents in `agents/`, and host settings in
`harnesses/`. The installer places outside skills by origin: harness-independent
ones in `.agents/skills/` only, Pstack and Cursor Team Kit in `.cursor/skills/`
only (see `harnesses/skills.json`), and it removes this checkout's links that no
longer match that placement. Preserve `vendor/` snapshots and update `sources.lock.json` when
updating an upstream revision. The [maintainer guides](docs/authoring.md) and
[bootstrap reference](docs/bootstrap.md) describe narrower installation tools and
removal of owned links/configuration without deleting personal state.

For repository development, apply its project configuration:

```sh
./install.sh --target "$PWD" --scope project --workspace "$PWD" --offline
python3 scripts/check_docs.py check
.tkstack/runtime/command-schema/bin/python -m unittest discover -s tests -v
python3 scripts/install.py --target .
python3 scripts/doctor.py --target .
```

The test command uses the private PyYAML/jsonschema environment installed by setup.
Reapply the file installer afterward because tests can regenerate ignored views
using their interpreter; `doctor` then checks the normal installation context.

Project completion hooks for Codex, Claude Code, and Cursor check documentation
in this repository. The Git `pre-commit` hook checks the **staged index**.
Both use the same source/document review ledger. After reviewing a changed area:

```sh
python3 scripts/check_docs.py render
python3 scripts/check_docs.py refresh --area setup --reason 'Reviewed the setup interface and updated its instructions'
python3 scripts/check_docs.py check
```

Stage the relevant docs and `docs/docs-freshness.json` with their source changes.
Use `--no-doc-impact` with an actual reason only for changes that do not affect
the documented interface. Checks never refresh the ledger automatically.
[Documentation maintenance](docs/documentation.md) explains coverage, hooks,
index/sparse-checkout behavior, internal-only changes, and the limits of static checks.

| Read next | Purpose |
| --- | --- |
| [Bootstrap](docs/bootstrap.md) | Profiles, installation, startup, prerequisite repair, and narrow installers |
| [Runner](docs/runner.md) | Compiled CLI commands, registries, scopes, and inference configuration |
| [Skills](docs/skills.md) | Installed upstream and owned packages |
| [Standards](docs/standards.md) | Personal defaults and workflow selection |
| [Learning](docs/learning.md) | Corrections, session consolidation, and ___ify subcommands |
| [SDLC](docs/sdlc.md) | BDD/contracts, task graphs, evidence, worktrees, and stacked delivery |
| [Integrations](docs/integrations.md) | Runtime readiness, native hooks/MCP, and external requirements |
| [Documentation](docs/documentation.md) | Documentation checks, review workflow, and hook installation |

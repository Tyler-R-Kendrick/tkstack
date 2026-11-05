# tkstack

Personal agent dotfiles: portable skills, custom agents, harness settings, native
hooks, and compiled workflow tools. Pinned upstream packages include Pstack by
poteto, Theo's Tstack, Matt Pocock's skills, Emil Kowalski's design-engineering
skills, Uncle Bob's ub-mode, Impeccable, Caveman, Lever, Graphify, OpenWiki, and
the design/media integrations listed in the [inventory](docs/skills.md).

## Install

One command obtains `~/.local/share/tkstack` and installs it into your home.
Bash and curl are the only host prerequisites. Git clones the checkout when it
is on PATH; otherwise the installer downloads the GitHub tarball with curl.
Python 3.11+ is used when it is already installed. Otherwise the installer
bootstraps uv and installs Python 3.12 itself.

```sh
curl -fsSL https://raw.githubusercontent.com/Tyler-R-Kendrick/tkstack/main/install.sh | bash
```

From a checkout of this repository, `./install.sh` installs that checkout instead
of downloading another copy. The command links skills, agents, rules, and hooks,
initializes private state and launchers, installs this repository's Git docs
hook, and verifies the result. Existing settings stay; a conflicting foreign
path stops setup. Keep the checkout, because the links and launchers point at
it. `SCOPE.md` is the supported baseline. `sources.lock.json` pins every upstream
snapshot under `vendor/`.

## Develop

From a checkout, `./install.sh --dry-run` is the read-only preview. These
commands run the suite, the repo-quality gate, the opt-in judge, and the
documentation check:

```sh
python3 -m unittest discover -s tests
REPO_QUALITY_GATE=1 python3 -m unittest tests.test_repo_quality
RUN_JUDGE=1 python3 -m unittest tests.test_repo_quality.RepoQualityTests.test_judge_eval -v
python3 src/check_docs.py check
```

`REPO_QUALITY_GATE=1` enforces the repo-quality ceilings. `RUN_JUDGE=1` runs the
pinned promptfoo judge. The [maintain section](#maintain-this-repository) has
the longer preview, routing, and doctor sequence.

## Install options

<!-- tkstack:profiles:start -->
| Profile | Harness configuration | Lever Copilot layout |
| --- | --- | --- |
| `dotfiles` | Codex, Claude Code, Cursor | Selected workspace |
| `devcontainer` | Codex, Claude Code, Cursor | Selected workspace |
| `codex-cloud` | Codex | Off |

The host needs Bash and curl. Missing Python **3.11+** is installed with the official uv installer (`uv python install 3.12`). Missing Git is replaced by a curl tarball of the GitHub repository.
Setup can provision private Node **24.19.0** and uv **0.12.23** when needed.
<!-- tkstack:profiles:end -->

`install.sh` uses `TKSTACK_PYTHON` when that executable is Python 3.11+.
Otherwise it tries `python3`, `python3.13`, `python3.12`, and `python3.11`.
If none of those is Python 3.11+, it installs uv with
`curl -LsSf https://astral.sh/uv/install.sh | sh` and runs
`uv python install 3.12`, then `uv run --python 3.12`. That uv only bootstraps
the host interpreter. Setup still provisions private Node and the pinned uv
when those tools are missing. Set `TKSTACK_HOME` to choose the checkout
directory and `TKSTACK_REPO` to choose the Git URL. Without Git, a GitHub HTTPS
remote is downloaded from codeload (`https://codeload.github.com/Tyler-R-Kendrick/tkstack/tar.gz/main`
for the default repository). Set `TKSTACK_TARBALL` to override that archive URL.
A later run updates a Git checkout with `git pull --ff-only`. A checkout obtained
without Git is reused as it is.

```sh
./install.sh --profile codex-cloud       # Codex-only host configuration
./install.sh --target /repo --scope project --workspace /repo
./install.sh --offline                  # reapply files using cached runtimes
./install.sh --check                    # read-only verification
./install.sh --dry-run                  # read-only plan and collision checks
./install.sh --strict                   # fail for known unresolved prerequisites
./install.sh --uninstall                # remove only this checkout's links and launchers
```

`--uninstall` is idempotent. It removes symlinks and launchers this checkout
owns and leaves shell startup files, foreign links, and repository Lever dials
in `.github/lever.yml`. `--dry-run --uninstall` prints that plan and writes
nothing. Use repeated `--harness codex|claude|cursor|grok|kimi|muse|opencode`
to select hosts. The default profile selects Codex, Claude Code, and Cursor.
`--no-shell` leaves shell startup files alone; source the generated environment
yourself. Set `CODEX_HOME` for a real-home Codex install. Restart or reload the
harness after setup. Codex may require reviewing new hook definitions with
`/hooks` before they run.

## Install one skill

The marketplace name is `tkstack`. These commands install the `investigate`
plugin from `skills/investigate`:

```text
/plugin marketplace add Tyler-R-Kendrick/tkstack
/plugin install investigate@tkstack
```

```sh
npx skills add Tyler-R-Kendrick/tkstack/skills/investigate --skill investigate
```

`npx skills add Tyler-R-Kendrick/tkstack --skill investigate` selects the same
package. Other manifest packages and their tree paths are `document`
(`skills/document`), `fal-ai` (`.agents/skills/fal-ai`), `headroom`
(`.agents/skills/headroom`), `hill-climb` (`skills/hill-climb`), `learn`
(`skills/learn`), `open-design` (`.agents/skills/open-design`), `rtk`
(`.agents/skills/rtk`), `sdlc` (`skills/sdlc`), `tkstack-principles`
(`skills/tkstack-principles`), `unslop` (`skills/unslop`), and `write`
(`skills/write`). Learn's subskills ship inside `skills/learn`. See
[skill distribution](docs/skill-marketplace.md).

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
explain routing. Pstack owns `tdd`; Matt's version is `matt-tdd`. Emil Kowalski's
UI prototype is `emil-prototype`; Matt's engineering `prototype` keeps that name.
The [skill routing guide](skills/sdlc/references/skill-routing.md) maps every
installed skill to an SDLC phase.

[SDLC](docs/sdlc.md) coordinates durable task graphs in ignored local SQLite,
with explicit requirement/ADR revisions when development findings change the plan.
Use `.tkstack/tkstack skills sdlc -- help` for its deterministic task commands.

All **19 repository skills** now expose the shared typed command protocol and compiled
artifacts. Use `skills <name> -- model` for its contract, `verify --report ...` for
retained-evidence checks, and `native ...` for its available existing helper.
[Normalization and per-skill coverage](docs/normalization.md) records actual
behavior checks, semantic/native boundaries, and all 19 SkillOpt trials.

Common entrypoints include `sdlc`, `learn`, `unslop`, `hill-climb`, `investigate`,
`document`, and `write`. The authoring skills `skillify`, `codify`, `hookify`,
`lintify`, `instructify`, `flowify`, and `reusify` are Learn subskills: they ship
inside `skills/learn/skills/` and run as `/learn <name>` or
`.tkstack/tkstack skills learn -- <name> ...`.

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
[Markdown command signatures](skills/learn/skills/codify/references/command-definitions.md),
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
and [model/provider configuration](skills/learn/skills/codify/references/inference.md).

## Maintain this repository

`scripts/` is the dotfiles installer (`install.sh` calls `scripts/bootstrap.py`).
Shared command, state, documentation, and pinned-runtime programs live in
`src/` so the installer stays a small set of single-purpose tools. Skills under
active development live in `skills/`; third-party-derived packages live in
`.agents/skills/`; shared agents live in `agents/`; host settings live in
`harnesses/`. Personal skills join every selected harness. Upstream skills in
`placement.default`, including Emil Kowalski and ub-mode, go to Codex, Grok,
Kimi, Muse, and OpenCode. Pstack and
Cursor Team Kit go only to Cursor. Graphify and Impeccable keep Codex, Claude
Code, and Cursor, including the generic agent-skills view at
`.tkstack/skill-views/graphify/default/`. See `harnesses/skills.json` and
`harnesses/README.md`. Reinstalling removes this checkout's links that no
longer match that placement. `./install.sh --uninstall` removes only this
checkout's links and launchers. Preserve `vendor/` snapshots and update
`sources.lock.json` when updating an upstream revision. The
[maintainer guides](docs/authoring.md) and [bootstrap reference](docs/bootstrap.md)
describe narrower installation tools.

For repository development, preview, test, and check docs from the checkout:

```sh
./install.sh --target "$PWD" --scope project --workspace "$PWD" --offline --dry-run
python3 src/routing_inventory.py check
python3 src/check_docs.py check
python3 -m unittest discover -s tests -v
python3 scripts/install.py --target .
python3 src/tool.py command-schema -B src/check_skills.py
python3 scripts/doctor.py --target .
```

`./install.sh --dry-run` and `--check` are read-only. Drop `--dry-run` to apply
that project install and provision the private command-schema interpreter.
`python3 src/routing_inventory.py check` fails when a skill has no routing entry
or an entry names a missing skill. The unittest command uses the Python that
runs it. CI installs the PyYAML/jsonschema packages the same way
`.github/workflows/skills.yml` does and runs the suite with
`.tkstack/runtime/command-schema/bin/python`. Reapply
`python3 scripts/install.py --target .` afterward because tests can regenerate
ignored views. `src/tool.py command-schema` then runs the owned-skill gate with
that interpreter, and `doctor` checks the restored installation.

[`evals/repo-quality`](evals/repo-quality/) grades this checkout separately from
the skill-evolution suites. The harness is Unix-only. Its snapshot lists
git-tracked files and places README.md before the file tree, so a generated
`.tkstack/runtime` tree cannot drop the README. `python3 evals/repo-quality/checks.py`
prints the deterministic ceilings. Those tests stay out of the default unittest
run unless `REPO_QUALITY_GATE=1`. The promptfoo judge is opt-in via `RUN_JUDGE=1`
on `tests.test_repo_quality`, uses pinned promptfoo 0.125.1, and passes only
when every metric scores 1.0. See [Repository quality](evals/README.md).

Project completion hooks for Codex, Claude Code, and Cursor check documentation
in this repository. The versioned Git handler is `.githooks/pre-commit`. Setup
writes an owned dispatcher into the repository's Git hooks directory and records
that ownership in `.tkstack/git-hooks/ownership.json` (gitignored). It never
chains a hook this project already owns, including a dispatcher installed from
another worktree that shares `.git/hooks`. A foreign pre-commit is still chained
and restored on uninstall. The hook checks the **staged index**. After reviewing
a changed area:

```sh
python3 src/check_docs.py render
python3 src/check_docs.py refresh --area setup --reason 'Reviewed the setup interface and updated its instructions'
python3 src/check_docs.py check
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

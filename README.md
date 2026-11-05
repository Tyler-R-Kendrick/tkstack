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
downloads uv 0.12.23, checks its sha256, and installs Python 3.12.15.
A directory that already exists at `TKSTACK_HOME` is not run unless its git
origin matches the repository or `TKSTACK_TRUST_HOME=1`. `TKSTACK_TARBALL`,
when set, must be an `https://` URL. That archive has no content hash.

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

`REPO_QUALITY_GATE=1` enforces the ceilings in `evals/repo-quality/`.
`RUN_JUDGE=1` runs the pinned promptfoo judge. That test executes
`npx -y promptfoo@0.125.1 eval -c evals/repo-quality/eval.yaml --no-cache -o evals/repo-quality/results/latest.json`
(`latest.json` is gitignored). Suites and that harness are described in
[evals/README.md](evals/README.md). The [maintain section](#maintain-this-repository)
has the longer preview, routing, and doctor sequence.

## Install one skill

The marketplace name is `tkstack`. These are Claude Code slash commands. They
install the `investigate` plugin, whose manifest source is `./skills/investigate`:

```text
/plugin marketplace add Tyler-R-Kendrick/tkstack
/plugin install investigate@tkstack
```

`skills` 1.7.6 `--help` installs `owner/repo` and uses `--skill` for the
SKILL.md name:

```sh
npx skills add Tyler-R-Kendrick/tkstack --skill investigate
```

That package's tree path is `skills/investigate`. This command names the
package and that path. `--list` on skills 1.7.6 resolves it and finds one
skill named `investigate`:

```sh
npx skills add Tyler-R-Kendrick/tkstack/skills/investigate
```

Other manifest packages and their tree paths are `document`
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

## Repository layout

Tracked directories (`git ls-files`). Root files beside them include `install.sh`, `sources.lock.json`, `SCOPE.md`, `AGENTS.md`, `CLAUDE.md`, and `GLOSSARY.md`.

| Path | Contents |
| --- | --- |
| `.agents/` | Third-party packages. `.agents/skills/` holds `fal-ai`, `headroom`, `open-design`, and `rtk`. |
| `.claude-plugin/` | Claude marketplace and plugin manifests (`marketplace.json`, `plugin.json`). |
| `.devcontainer/` | Devcontainer: full setup on create, offline setup on later starts. |
| `.githooks/` | Versioned `pre-commit` that checks the staged docs ledger. |
| `.github/` | CI workflow `workflows/skills.yml` and Lever dials `lever.yml`. |
| `.tkstack/` | Versioned state seed: `.gitignore` and `reuse/catalog.json`. |
| `agents/` | Shared Markdown agents. The installer links them; `agents/README.md` is not installed. |
| `docs/` | Focused install, skill, harness, and maintainer guides. |
| `evals/` | Decision regressions. The guide is `evals/README.md`. `evals/repo-quality/` grades this checkout (`checks.py`, `snapshot.py`, `judge.py`, `eval.yaml`). |
| `harnesses/` | Placement and host config: `harnesses/ai-sdk/` (Vercel AI SDK `profiles.example.json`), `harnesses/bootstrap/` (profiles, Python locks, toolchains), `harnesses/copilot/` (`lever.yml`), `harnesses/cursor/` (`graphify.mdc`, `tkstack-steering.mdc`), `harnesses/graphify/` and `harnesses/headroom/` (Python locks), `harnesses/openwiki/` (npm package and lock), `harnesses/t3code/` (reads a host's skills; no skills directory). |
| `scripts/` | Installer tools. `install.sh` calls `scripts/bootstrap.py`. |
| `skills/` | Owned skills. Learn subskills live in `skills/learn/skills/`. |
| `src/` | Shared command, state, documentation, and pinned-runtime programs. |
| `tests/` | Unittest suite. |
| `vendor/` | Pinned upstream snapshots named in `sources.lock.json`. |
| `vendor/ponytail/` | DietrichGebert/ponytail 5.3.3 (MIT): six skills and Node lifecycle-hook adapters. Vendored so setup uses those locked bytes instead of cloning upstream. |

## Install options

<!-- tkstack:profiles:start -->
| Profile | Harness configuration | Lever Copilot layout |
| --- | --- | --- |
| `dotfiles` | Codex, Claude Code, Cursor | Selected workspace |
| `devcontainer` | Codex, Claude Code, Cursor | Selected workspace |
| `codex-cloud` | Codex | Off |

The host needs Bash and curl. Missing Python **3.11+** is installed with uv **0.12.23** (`uv python install 3.12.15`) after that installer sha256 is checked. Missing Git is replaced by a curl tarball of the GitHub repository.
Setup can provision private Node **24.19.0** and uv **0.12.23** when needed.
<!-- tkstack:profiles:end -->

`install.sh` uses `TKSTACK_PYTHON` when that executable is Python 3.11+.
Otherwise it tries `python3`, `python3.13`, `python3.12`, and `python3.11`.
If none of those is Python 3.11+, it downloads uv 0.12.23 from
`https://astral.sh/uv/0.12.23/install.sh`, requires sha256
`b8e6c43099ee9f9a550984d3ad56948457c689e7a99c090b35377234ac241491`, and runs
`uv python install 3.12.15`, then `uv run --python 3.12.15`. The download is
saved to a temporary file and checked before it runs. The uv installer's
stdout is discarded so only `$HOME/.local/bin/uv` is executed. A caller-supplied
`UV_INSTALL_DIR` is ignored; the installer execs `$HOME/.local/bin/uv`.
Rotate the pin by changing `UV_VERSION`, `UV_INSTALLER_URL`,
`UV_INSTALLER_SHA256`, and `PYTHON_VERSION` in `install.sh` together.
uv 0.12.23 ships CPython 3.12.15 and does not ship 3.12.16. That uv only
bootstraps the host interpreter. Setup still provisions private Node and the
pinned uv when those tools are missing.

`TKSTACK_HOME` chooses the checkout directory (default `~/.local/share/tkstack`).
This run executes a checkout it just cloned or unpacked. A directory that
already exists was not created by this run, and a receipt inside it
(`.tkstack/source-receipt.txt`) is not proof: the directory can write that
file itself. The installer runs that directory only when its git `origin`
matches `TKSTACK_REPO` (default
`https://github.com/Tyler-R-Kendrick/tkstack.git`, ignoring a trailing `.git`)
or `TKSTACK_TRUST_HOME=1`. A matching origin is fast-forwarded with
`git pull --ff-only`, which stops with a commit-or-stash message when that
fails. The origin check compares the remote URL, not the tree contents.
`TKSTACK_TRUST_HOME=1` on a non-git checkout downloads the archive again and
keeps `.tkstack`; it does not run the previous `install.sh`. The same flag on
a git checkout whose origin does not match runs the existing `install.sh` and
does not pull. `TKSTACK_REPO` chooses the Git URL. Without Git, a GitHub HTTPS
remote is downloaded from codeload
(`https://codeload.github.com/Tyler-R-Kendrick/tkstack/tar.gz/main` for the
default repository). Set `TKSTACK_TARBALL` to an `https://` archive URL to
override that. Any other scheme is refused. There is no content hash for the
repository tarball: this script cannot pin its own bytes, and `tar.gz/main`
is a mutable branch tip. HTTPS checks the transport, not that the bytes still
match a review. The download is checked for curl failure, one top-level
directory, and members or symlinks that escape the extract directory, then
extracted with `--no-same-owner` and `--no-same-permissions`. Symlink checks
walk the path in bash and do not need `realpath`. Replacing a tarball
checkout copies `.tkstack` into the new tree before the old directory moves,
and puts the old directory back if that move fails. A later trusted run of a
tarball checkout downloads it again because there is no git fast-forward.
Fixes in a tarball checkout arrive only when the installer runs.

### Verify the installer first

The one-line command under [Install](#install) is the supported quickstart.
`install.sh` wraps its work in `main` and calls it on the last line, so a
truncated download does not run a prefix. To inspect the file before running it:

```sh
curl -fsSL -o /tmp/tkstack-install.sh https://raw.githubusercontent.com/Tyler-R-Kendrick/tkstack/main/install.sh
# Compare /tmp/tkstack-install.sh with install.sh from a checkout you already trust, then:
bash /tmp/tkstack-install.sh
```

```sh
./install.sh --profile codex-cloud       # Codex-only host configuration
./install.sh --target /repo --scope project --workspace /repo
./install.sh --offline                  # reapply files using cached runtimes
./install.sh --check                    # read-only verification
./install.sh --dry-run                  # read-only plan and collision checks
./install.sh --strict                   # fail for known unresolved prerequisites
./install.sh --uninstall                # remove this checkout's links, launchers, and git docs hook
```

`--uninstall` is idempotent. It removes symlinks for every harness, launchers,
and the owned git docs hook this checkout owns, even when `--harness` is also
passed. It leaves shell startup files, foreign links, and repository Lever dials
in `.github/lever.yml`. `--dry-run --uninstall` prints that plan and writes
nothing. Use repeated `--harness codex|claude|cursor|grok|kimi|opencode|copilot|muse`
to select hosts for installation. Copilot links `~/.copilot/skills` at home and
`.github/skills` in a project. Muse links `~/.config/muse/skills` at home and
does not follow `XDG_CONFIG_HOME`; a project install uses `.agents/skills`.
The default profile selects Codex, Claude Code, and Cursor.
`--no-shell` leaves shell startup files alone; source the generated environment
yourself. Set `CODEX_HOME` for a real-home Codex install. Restart or reload the
harness after setup. Codex may require reviewing new hook definitions with
`/hooks` before they run.

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
Kimi, OpenCode, Copilot, and Muse. Pstack and
Cursor Team Kit go only to Cursor. Graphify and Impeccable keep Codex, Claude
Code, and Cursor, including the generic agent-skills view at
`.tkstack/skill-views/graphify/default/`. See `harnesses/skills.json` and
`harnesses/README.md`. Reinstalling removes this checkout's links that no
longer match that placement. `./install.sh --uninstall` removes this
checkout's links for every harness, its launchers, and its owned git docs hook.
Preserve `vendor/` snapshots and update
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

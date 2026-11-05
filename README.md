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
of downloading another copy. The command links skills, agents, and rules for
Codex, Claude Code, and Cursor, and sets this checkout's `core.hooksPath` to
`.githooks`. It also runs Serena's `init` and `project index` when `uvx` is
on `PATH`, and skips that step when `uvx` is not on `PATH` or the command fails.
A conflicting foreign path stops setup. Keep the checkout, because
the links point at it. `SCOPE.md` is the supported baseline. `sources.lock.json`
pins every upstream snapshot under `vendor/`. Root `plugin.json` and `mcp.json`
are the Agent Plugins package. See [Agent Plugins](docs/agent-plugins.md).

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
has the longer preview and routing check.

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
The installer links files and, when `uvx` works, initializes Serena for the
selected project. It does not authenticate accounts, start a proxy, redirect
providers, or run models. See [install details](docs/bootstrap.md),
[Agent Plugins](docs/agent-plugins.md), and [integration readiness](docs/integrations.md).

## Repository layout

Tracked directories (`git ls-files`). Root files beside them include `plugin.json`, `mcp.json`, `install.sh`, `sources.lock.json`, `SCOPE.md`, `AGENTS.md`, `CLAUDE.md`, and `GLOSSARY.md`.

| Path | Contents |
| --- | --- |
| `.agents/` | Third-party packages. `.agents/skills/` holds `fal-ai`, `headroom`, `open-design`, and `rtk`. |
| `.claude-plugin/` | Claude marketplace and plugin manifests (`marketplace.json`, `plugin.json`). |
| `.devcontainer/` | Devcontainer: project-scope link on create and on later starts. |
| `.githooks/` | Versioned `pre-commit` that checks the staged docs ledger. |
| `.cursor/` | Tracked rules `.cursor/rules/graphify.mdc` and `.cursor/rules/tkstack-steering.mdc`. The installer links them. Other `.cursor/` paths are local install links and stay ignored. |
| `.github/` | CI workflow `workflows/skills.yml` and Lever dials `lever.yml`. |
| `.tkstack/` | Versioned state seed: `.gitignore` and `reuse/catalog.json`. |
| `agents/` | Shared Markdown agents. The installer links them; `agents/README.md` is not installed. |
| `docs/` | Focused install, skill, harness, and maintainer guides, including `docs/harnesses.md` and `docs/t3code.md`. |
| `evals/` | Decision regressions. The guide is `evals/README.md`. `evals/repo-quality/` grades this checkout (`checks.py`, `snapshot.py`, `judge.py`, `eval.yaml`). |
| `scripts/` | The linker. `install.sh` calls `scripts/install.py`. |
| `skills/` | Owned Agent Skills and the placement registry `skills/skills.json`. Clients discover only immediate `skills/*/SKILL.md` directories. Learn subskills live in `skills/learn/skills/`. SDLC owns `skills/sdlc/scripts/routing_inventory.py`. Learn owns `skills/learn/scripts/evolve.py`. Skillify owns `skills/learn/skills/skillify/scripts/sync_codify.py`. |
| `src/` | Shared command, state, and documentation programs, plus the runner source registry `src/runner.json`. See `src/README.md`. |
| `tests/` | Unittest suite. |
| `vendor/` | Pinned upstream snapshots named in `sources.lock.json`. |
| `vendor/ponytail/` | DietrichGebert/ponytail 5.3.3 (MIT): six skills and Node lifecycle-hook adapters. Vendored so setup uses those locked bytes instead of cloning upstream. |

## Install options

<!-- tkstack:profiles:start -->
The host needs Bash and curl. Missing Python **3.12.15** is installed with uv **0.12.23** after sha256 `b8e6c43099ee9f9a550984d3ad56948457c689e7a99c090b35377234ac241491` is checked.
Missing Git is replaced by a curl tarball of the GitHub repository.
One install links Codex, Claude Code, and Cursor. Repeat `--harness` for the other hosts.
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
bootstraps the host interpreter. Install does not provision a private Node
or a second uv.

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
./install.sh --target /repo --scope project
./install.sh --harness copilot
./install.sh --dry-run
./install.sh --uninstall
```

`--uninstall` removes this checkout's symlinks for every harness and unsets
`core.hooksPath` when that value is `.githooks`. `--harness` does not limit it.
It leaves foreign links in place. `--dry-run --uninstall` prints that plan and
writes nothing. Repeat `--harness` with `codex`, `claude`, `cursor`, `grok`,
`kimi`, `opencode`, `copilot`, or `muse` to select hosts. t3code is not a
choice: it reads the other hosts' skills. Copilot links `~/.copilot/skills` at
home and `.github/skills` in a project. Muse links `~/.config/muse/skills` at
home and does not follow `XDG_CONFIG_HOME`; a project install uses
`.agents/skills`. The default selection is Codex, Claude Code, and Cursor.
Set `CODEX_HOME` for a real-home Codex install. Restart or reload the harness
after setup.

## Devcontainers

The included [devcontainer](.devcontainer/devcontainer.json) links this
checkout into the workspace on create and on later starts. To use this
repository as VS Code dotfiles in another devcontainer:

```json
{
  "dotfiles.repository": "Tyler-R-Kendrick/tkstack",
  "dotfiles.targetPath": "~/.local/share/tkstack",
  "dotfiles.installCommand": "install.sh"
}
```

[Install details](docs/bootstrap.md) cover a project-only target.

## Use skills and compiled workflows

Use `/skill-name` in Claude Code/Cursor, or `$skill-name` and the skill picker in
Codex. The [skill inventory](docs/skills.md) and [personal standards](docs/standards.md)
explain routing. Pstack owns `tdd`; Matt's version is `matt-tdd`. Emil Kowalski's
UI prototype is `emil-prototype`; Matt's engineering `prototype` keeps that name.
The [skill routing guide](skills/sdlc/references/skill-routing.md) maps every
installed skill to an SDLC phase.

[SDLC](docs/sdlc.md) coordinates durable task graphs in ignored local SQLite,
with explicit requirement/ADR revisions when development findings change the plan.
Use `python3 src/tkstack.py skills sdlc -- help` for its deterministic task commands.

All **19 repository skills** now expose the shared typed command protocol and compiled
artifacts. Use `skills <name> -- model` for its contract, `verify --report ...` for
retained-evidence checks, and `native ...` for its available existing helper.
[Normalization and per-skill coverage](docs/normalization.md) records actual
behavior checks, semantic/native boundaries, and all 19 SkillOpt trials.

Common entrypoints include `sdlc`, `learn`, `unslop`, `hill-climb`, `investigate`,
`document`, and `write`. The authoring skills `skillify`, `codify`, `hookify`,
`lintify`, `instructify`, `flowify`, and `reusify` are Learn subskills: they ship
inside `skills/learn/skills/` and run as `/learn <name>` or
`python3 src/tkstack.py skills learn -- <name> ...`.

```text
/learn help
/learn help reusify
/learn reusify init src --preview
```

Run compiled code through `src/tkstack.py`. Install does not write a launcher:

```sh
python3 src/tkstack.py help
python3 src/tkstack.py list workflows
python3 src/tkstack.py workflows normalize-labels -- normalize -l '[" b ","a","a"]'
python3 src/tkstack.py skills my-compiled-skill -- command --flag value
python3 src/tkstack.py tools skills my-compiled-skill --format responses
```

Skillify supplies reserved `help` and `version` commands for command packages.
Omitting a command renders a deterministic console manual; use `help --format
man` to export man(1) source. For example, `python3 src/tkstack.py skills sdlc -- version`
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
and runtimes remain ignored. See [state conventions](docs/state-layout.md)
and [model/provider configuration](skills/learn/skills/codify/references/inference.md).

## Maintain this repository

`scripts/` is the dotfiles linker (`install.sh` calls `scripts/install.py`).
Shared command, state, and documentation programs live in `src/`. Skills under
active development live in `skills/`; third-party-derived packages live in
`.agents/skills/`; shared agents live in `agents/`. Placement is
`skills/skills.json`. Owned Cursor rules live in `.cursor/rules/`. Copilot
dials live in `.github/lever.yml`. Personal skills join every selected harness.
Upstream skills in `placement.default`, including Emil Kowalski and ub-mode,
go to Codex, Grok, Kimi, OpenCode, Copilot, and Muse. Pstack and
Cursor Team Kit go only to Cursor. Graphify and Impeccable keep Codex, Claude
Code, and Cursor, including the generic agent-skills view at
`.tkstack/skill-views/graphify/default/`. See `skills/skills.json` and
`docs/harnesses.md`. Reinstalling removes this checkout's links that no
longer match that placement. `./install.sh --uninstall` removes this
checkout's links for every harness and unsets `core.hooksPath` when it is
`.githooks`. Preserve `vendor/` snapshots and update
`sources.lock.json` when updating an upstream revision. The
[install reference](docs/bootstrap.md) is the linker. Skill authoring stays in
[the maintainer guides](docs/authoring.md).

For repository development, preview, test, and check docs from the checkout:

```sh
./install.sh --target "$PWD" --scope project --dry-run
python3 skills/sdlc/scripts/routing_inventory.py check
python3 src/check_docs.py check
python3 -m unittest discover -s tests -v
python3 scripts/install.py --target . --scope project
python3 src/check_skills.py
```

`./install.sh --dry-run` is read-only. Drop `--dry-run` to apply that project
install. `python3 skills/sdlc/scripts/routing_inventory.py check` fails when a
skill has no routing entry or an entry names a missing skill. The unittest
command uses the Python that runs it. CI installs the PyYAML/jsonschema
packages the same way `.github/workflows/skills.yml` does and runs the suite
with `.tkstack/runtime/command-schema/bin/python`. Reapply
`python3 scripts/install.py --target . --scope project` afterward because tests
can regenerate ignored alias views. `python3 src/check_skills.py` is the
owned-skill gate. It does not run the SDLC routing inventory.

[`evals/repo-quality`](evals/repo-quality/) grades this checkout separately from
the skill-evolution suites. The harness is Unix-only. Its snapshot lists
git-tracked files and places README.md before the file tree, so a generated
`.tkstack/runtime` tree cannot drop the README. `python3 evals/repo-quality/checks.py`
prints the deterministic ceilings. Those tests stay out of the default unittest
run unless `REPO_QUALITY_GATE=1`. The promptfoo judge is opt-in via `RUN_JUDGE=1`
on `tests.test_repo_quality`, uses pinned promptfoo 0.125.1, and passes only
when every metric scores 1.0. See [Repository quality](evals/README.md).

The versioned Git handler is `.githooks/pre-commit`. Install sets
`core.hooksPath=.githooks` for this checkout, so Git runs that script and does
not chain `.git/hooks`. Uninstall unsets the key only when it is still
`.githooks`. The hook checks the **staged index**. After reviewing a changed
area:

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
| [Install](docs/bootstrap.md) | One-command link, host prerequisites, and the docs hook |
| [Runner](docs/runner.md) | Compiled CLI commands, registries, scopes, and inference configuration |
| [Skills](docs/skills.md) | Installed upstream and owned packages |
| [Standards](docs/standards.md) | Personal defaults and workflow selection |
| [Learning](docs/learning.md) | Corrections, session consolidation, and ___ify subcommands |
| [SDLC](docs/sdlc.md) | BDD/contracts, task graphs, evidence, worktrees, and stacked delivery |
| [Integrations](docs/integrations.md) | Runtime readiness, native hooks/MCP, and external requirements |
| [Documentation](docs/documentation.md) | Documentation checks, review workflow, and hook installation |

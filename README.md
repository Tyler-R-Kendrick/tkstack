# TKStack

Personal agent dotfiles for working across repositories. The default installation includes the catalog and its bundled tool runtimes, refreshed from current upstream versions. Your project's build, formatting, Git settings, credentials and deployment policy stay with their existing owners.

## Install

From a checkout at a revision you trust, run:

```sh
./install.sh
```

Keep the checkout in a stable location. Setup refreshes upstream sources and tools, then links your home to them. Commands are available in `~/.tkstack/bin` and, where unoccupied, `~/.local/bin`. Codex reads a managed section in its own configuration home and Claude reads one in `~/.claude/CLAUDE.md`. Open an unrelated Git project and run `~/.tkstack/tkstack status`. Restart the client to reload its instructions. MCP registration and project indexing follow the client's own setup.

## Obtain the source

Clone the current tkstack checkout and run its installer:

```sh
git clone https://github.com/Tyler-R-Kendrick/tkstack.git ~/.local/share/tkstack
~/.local/share/tkstack/install.sh
```

## Use in a project

```sh
./install.sh --target /absolute/project --scope project --dry-run
./install.sh --target /absolute/project --scope project
./install.sh --target /absolute/project --check
```

The last command checks the destination, its saved profile, managed paths and startup instructions. For team-owned constraints, also pass `--adopt`, review the two files under `.constrain/`, and commit them. Add `--constraint-hook` for a staged Git gate. Existing hook managers can call the same checker. The [bootstrap guide](docs/bootstrap.md) covers upgrades, conflicts, scopes and removal.

| Choose | Use |
| --- | --- |
| Default catalog | Fresh installs use `--profile catalog`, with current upstream tools. |
| Smaller personal set | Choose `--profile personal` for Constrain, Investigate, Learn and TKStack Principles. |
| Authoring and delivery | `--profile development` adds SDLC, writing, documentation, quality review and measured experiments. Invoke Testify, Evalify and other authoring commands through Learn. |
| Design and media | `--profile design` selects supported design packages for the chosen hosts. |
| Full inventory | `--profile catalog` applies source-specific upstream placement, agents and Cursor rules. |
| One package | Use the [Claude marketplace or skills CLI](docs/skill-marketplace.md). |
| Optional integrations | See [runtime requirements and probes](docs/integrations.md). |

For VS Code dotfiles, set `dotfiles.repository` to `Tyler-R-Kendrick/tkstack`, `dotfiles.targetPath` to `~/.local/share/tkstack` and `dotfiles.installCommand` to `install.sh`. This is a personal installation. A team's devcontainer can call the external checkout's installer with an explicit workspace target. This repository's own devcontainer is a maintainer environment.

## Install options

<!-- tkstack:profiles:start -->
The host needs Bash, Git, and curl. Dotfiles setup provisions current Node.js. Missing Python 3.11+ is installed as the current stable Python **3** using the current uv release and its published SHA-256.
Archive bootstrap requires an independently supplied SHA-256 digest.
The default catalog installs applicable skills and tools for Codex, Claude Code, and Cursor. Explicit profiles narrow skill selection.
<!-- tkstack:profiles:end -->

For task-scoped measured improvement, the hill-climb skill can coordinate Git
experiment arms and paired evaluations. See [measured improvement loops](docs/hill-climb.md)
for execution and isolation limits.

Constrain's [test-value review](skills/constrain/references/tests.md) ranks
tests by risk and evidence, checks overlap across the test pyramid, and compares
fault detection and cost before pruning. Its checker inventories supported tests
and enforces configured rules. A separate bounded mutation command runs selected
Python faults against individual unittest cases in isolated Git snapshots. Review
the resulting failures and costs before deciding whether a test can be pruned;
neither a checker pass nor a mutation count proves test value.
The review also incorporates UB Mode's function-risk, mutation and duplication
signals, with their measurement limits and tool side effects made explicit.
Executed TKStack operations use a bounded runner and retain local timing records;
MCP calls in other hosts need their own deadline and tracing configuration.

## Maintain TKStack

`skills/` contains owned skills and placement profiles, `vendor/` contains historical source snapshots, `agents/` holds shared subagents, and `integrations/` provisions current upstream tools. Learn's nine authoring packages ship under Learn. Nested Constrain topics are Markdown references. The [runner](docs/runner.md) exposes executable workflows and their contracts.

```sh
python3 src/check_skills.py
python3 src/check_docs.py check
python3 skills/constrain/scripts/constrain.py check --repo . --strict-dependencies
python3 -m unittest discover -s tests
```

CI provisions the locked schema and native Codex tools before running these gates. To enable the maintainer Git hook in a checkout with no existing manager, use `git config --local core.hooksPath .githooks`. Project installations leave that setting alone. See [documentation review](docs/documentation.md), [agent plugin distribution](docs/agent-plugins.md), and [the supported scope](SCOPE.md).

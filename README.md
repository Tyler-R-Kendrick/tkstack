# TKStack

Personal agent dotfiles for working across repositories. The default profile installs Constrain, Investigate, Learn and TKStack Principles. Your project's build, formatting, Git settings, credentials and deployment policy stay with their existing owners.

## Install

From a checkout at a revision you trust, run:

```sh
./install.sh
```

Keep the checkout in a stable location. Setup links your home to it. Codex reads a managed section in its own configuration home and Claude reads one in `~/.claude/CLAUDE.md`. Open an unrelated Git project and run `~/.tkstack/tkstack status`. Restart the client to reload its instructions. The personal install performs no MCP registration or project indexing.

## Pin a release

To install from Git, fetch the full commit ID you reviewed into a fresh checkout. Replace the example revision with the actual 40-character ID supplied through your trusted release channel.

```sh
git init ~/.local/share/tkstack
git -C ~/.local/share/tkstack fetch --depth 1 https://github.com/Tyler-R-Kendrick/tkstack.git "$TKSTACK_REV"
git -C ~/.local/share/tkstack checkout --detach "$TKSTACK_REV"
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
| Personal defaults | Fresh installs use `--profile personal`. |
| Authoring and delivery | `--profile development` adds SDLC, writing, documentation, quality review and measured experiments. Invoke Testify, Evalify and other authoring commands through Learn. |
| Design and media | `--profile design` selects supported design packages for the chosen hosts. |
| Full inventory | `--profile catalog` applies source-specific upstream placement, agents and Cursor rules. |
| One package | Use the [Claude marketplace or skills CLI](docs/skill-marketplace.md). |
| Optional integrations | See [runtime requirements and probes](docs/integrations.md). |

For VS Code dotfiles, set `dotfiles.repository` to `Tyler-R-Kendrick/tkstack`, `dotfiles.targetPath` to `~/.local/share/tkstack` and `dotfiles.installCommand` to `install.sh`. This is a personal installation. A team's devcontainer can call the external checkout's installer with an explicit workspace target. This repository's own devcontainer is a maintainer environment.

## Install options

<!-- tkstack:profiles:start -->
The host needs Bash and curl. Missing Python **3.12.15** is installed with uv **0.12.23** after sha256 `b8e6c43099ee9f9a550984d3ad56948457c689e7a99c090b35377234ac241491` is checked.
Archive bootstrap requires an independently supplied SHA-256 digest.
The personal profile selects four skills for Codex, Claude Code, and Cursor. Use `--profile catalog` for full placement.
<!-- tkstack:profiles:end -->

For task-scoped measured improvement, the hill-climb skill can coordinate Git
experiment arms and paired evaluations. See [measured improvement loops](docs/hill-climb.md)
for execution and isolation limits.

Constrain's [test-value review](skills/constrain/references/tests.md) ranks
tests by risk and evidence, checks overlap across the test pyramid, and compares
fault detection and cost before pruning. Its checker inventories supported tests
and enforces configured rules; it does not rank tests, run mutation testing, or
prove that a suite improvement works. Those conclusions require the separate
review and measurements described in the guide.
The review also incorporates UB Mode's function-risk, mutation and duplication
signals, with their measurement limits and tool side effects made explicit.
Executed TKStack operations use a bounded runner and retain local timing records;
MCP calls in other hosts need their own deadline and tracing configuration.

## Maintain TKStack

`skills/` contains owned skills and placement profiles, `vendor/` contains pinned snapshots, `agents/` holds shared subagents, and `integrations/mcp/` locks optional Node tooling. Learn's nine authoring packages ship under Learn. Nested Constrain topics are Markdown references. The [runner](docs/runner.md) exposes executable workflows and their contracts.

```sh
python3 src/check_skills.py
python3 src/check_docs.py check
python3 skills/constrain/scripts/constrain.py check --repo . --strict-dependencies
python3 -m unittest discover -s tests
```

CI provisions the locked schema and native Codex tools before running these gates. To enable the maintainer Git hook in a checkout with no existing manager, use `git config --local core.hooksPath .githooks`. Project installations leave that setting alone. See [documentation review](docs/documentation.md), [agent plugin distribution](docs/agent-plugins.md), and [the supported scope](SCOPE.md).

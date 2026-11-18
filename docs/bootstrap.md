# Install and reconcile a destination

Run the trusted checkout's `install.sh` from any directory. With no arguments it installs personal defaults into your home. For a repository, pass `--target /absolute/repo --scope project`. Setup prints both paths. The checkout supplies shared package code and generated discovery views. The destination owns its steering, startup instructions and `.tkstack/tkstack` runner.

Setup creates an ignored `.tkstack/.scratch/` for task-owned drafts, notes and exploratory evaluations. Use the installed `scratch` skill for isolation, promotion and cleanup. Promote requested durable artifacts to their canonical tracked location; never commit scratch. Other `.tkstack` namespaces remain owned by their helpers.

## Lifecycle

1. Preview with `--dry-run`. Run the same command without that flag to apply.
   A home installation fetches current upstream sources and provisions current
   tool runtimes before linking the catalog. It requires network access and Git;
   Node.js, uv and Python packages use isolated managed environments. Each
   Python environment selects a current interpreter compatible with the latest
   published packages it runs.
2. Verify with `--check`. Run `--status` for local prerequisites and integration status. On an adopted project these commands also run the workspace policy. In an unrelated repository use `~/.tkstack/tkstack status`; supply `--project /absolute/path` before `status` to check a specific workspace. Reload your agent to observe native discovery.
3. Repeat setup to check upstream versions and update changed sources or tools.
   The receipt records the selected profile, hosts, source generations and
   installed links. A prior implicit personal profile moves to the catalog;
   `--profile personal` keeps the smaller selection. Repeat `--harness` when
   selecting multiple hosts. Reapplying reconciles owned links and preserves
   unrelated commands. If an update fails during application, setup restores
   its changed links and configuration where possible and reports any paths
   needing manual recovery. An online rerun can rebuild a deleted generation;
   uninstall can remove its remaining owned links.
4. Remove the target's installation with `--target /absolute/repo --uninstall`. Foreign instructions, modified foreign hooks, project-owned constraints and durable learning state are preserved. The source checkout and other consumers keep their configuration.

A foreign destination or manually edited owned instruction section stops setup. Read the reported path, reconcile the two owners, and rerun. A nonempty Codex override can shadow the startup file and requires reconciliation. Moving the source breaks absolute links; uninstall from its original location before moving it. Use separate source checkouts to test a new revision.

`TKSTACK_OFFLINE=1` skips update checks and uses the saved generation, or the
bundled reference snapshots when no generation exists. A first offline install
cannot provision missing tool runtimes. Project-scope setup links the selected
skills without fetching or changing the project's dependencies.

## Home and project ownership

Codex loads user instructions from `$CODEX_HOME/AGENTS.md` or `~/.codex/AGENTS.md`. Claude reads `~/.claude/CLAUDE.md`. Home pointers use absolute paths so the active project can live anywhere. In project scope, setup maintains an owned block in `AGENTS.md` and a Claude import if selected. The rest of each file remains project-owned. The [harness table](harnesses.md) gives skill directory placement.

A project catalog install exposes the bundled skill catalog to Codex and Muse,
including Cursor-origin skills. Both hosts share
the project skill directory and use the same Codex views, so either can
reconcile those links. Home installs
continue to honor each source's normal host placement. Skill instructions are
portable guidance; host-specific tools, agents, hooks and credentials need
their own configuration.

## Pstack in Codex

After installation, start a fresh Codex session and invoke `$poteto-mode`, or
invoke `$create-formal-verification-skill`, `$maintain-formal-verification-skill`
and `$statechart` directly. The Pstack 0.15.43 snapshot keeps upstream bytes.
Its `teach` and `unslop` install as `pstack-teach` and `pstack-unslop`; generated
Pstack caller views use `pstack-teach` while preserving the personal `unslop`.

Treat Cursor subagent and model names as roles, using only tools and models the
active session offers when delegation is authorized. `setup-pstack`, Cursor
Custom Modes and `/loop` do not configure equivalent Codex features. Skill
links do not register Cursor agents or rules as native Codex plugins. Statechart
requires Node, Bun or Deno and Java 11 or later, plus pinned TLC installed via
mise or an explicit `TLA2TOOLS` jar. Network, credentials and Benny automation
integrations remain separate requirements; installation starts no automations.

External Git project roots receive exact link paths and the entire local `.tkstack/` directory in their `info/exclude`. Its own `.gitignore` explicitly ignores `.scratch/` as well. Team instructions remain visible to Git. Avoid committing machine-specific symlinks, scratch or local runtime state. TKStack refuses to take over existing instruction blocks, link destinations or hook managers.

## Adopt team constraints

For the typed checker and hook, [provision the locked runner dependencies](runner.md#execution-contract) in the source checkout. `./install.sh --target /absolute/project --adopt` seeds `.constrain/config.json` and an empty review inventory. A project starts with zero approved Python tests and a small policy-file budget. Set budgets, globs and reviews to reflect actual project risks before committing. Existing policies remain under team control. Check with `.tkstack/tkstack skills constrain -- native check --repo .`. Serena setup and indexing likewise require an explicit project target outside your home root and the TKStack checkout. See [constraint selection and configuration](../skills/constrain/SKILL.md).

Add `--constraint-hook` to install a worktree's staged gate when using Git's default hooks directory. If a team already owns its hook, call `.tkstack/tkstack skills constrain -- native check --repo . --staged` from that manager, or run the checker in CI after installing TKStack at a reviewed revision. If the team later switches managers, uninstall removes its original default hook when the contents still match. Stage project policy with the change. Maintainers can opt in with native Git configuration. See [the documentation gate](documentation.md).

## Bootstrap integrity

The default bootstrap clones the current Git branch and fast-forwards an
existing matching checkout. An explicitly supplied `TKSTACK_REV` selects a
specific checkout when needed; it must match the origin, revision and clean
working tree. A locally invoked checkout is updated by its owner or dotfiles
host, while its bundled upstream tools are refreshed during home setup.

Without Git, supply `TKSTACK_TARBALL_SHA256` from a trusted channel and either the full `TKSTACK_REV` or an HTTPS `TKSTACK_TARBALL`. The script verifies downloaded bytes before extraction and checks archive paths and symlinks. A trusted tarball refresh preserves local state. `TKSTACK_HOME` selects the source location. A pre-existing unrelated checkout requires explicit `TKSTACK_TRUST_HOME=1` for development use.

Use an installed Python 3.11+ or select it with `TKSTACK_PYTHON`. When unavailable, the bootstrap obtains the current uv release, verifies its published checksum, and installs current stable Python 3. The checkout-level preview inspects local files. Running a separately downloaded bootstrap first acquires its source.

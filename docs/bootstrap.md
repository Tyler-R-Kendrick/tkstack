# Install and reconcile a destination

Run the trusted checkout's `install.sh` from any directory. With no arguments it installs personal defaults into your home. For a repository, pass `--target /absolute/repo --scope project`. Setup prints both paths. The checkout supplies shared package code and generated discovery views. The destination owns its steering, startup instructions and `.tkstack/tkstack` runner.

## Lifecycle

1. Preview with `--dry-run`. Run the same command without that flag to apply.
2. Verify with `--check`. Run `--status` for local prerequisites and integration status. On an adopted project these commands also run the workspace policy. In an unrelated repository use `~/.tkstack/tkstack status`; supply `--project /absolute/path` before `status` to check a specific workspace. Reload your agent to observe native discovery.
3. Repeat setup after upgrading the checkout. The local receipt records the profile, hosts, and each installed link’s destination and source. Reconciliation preserves user aliases into the same checkout. Existing pre-profile installations retain catalog placement. Use an explicit profile to change selection. Repeat `--harness` when selecting multiple hosts. Reapplying reconciles the selected set.
4. Remove the target's installation with `--target /absolute/repo --uninstall`. Foreign instructions, modified foreign hooks, project-owned constraints and durable learning state are preserved. The source checkout and other consumers keep their configuration.

A foreign destination or manually edited owned instruction section stops setup. Read the reported path, reconcile the two owners, and rerun. A nonempty Codex override can shadow the startup file and requires reconciliation. Moving the source breaks absolute links; uninstall from its original location before moving it. Use separate source checkouts to test a new revision.

## Home and project ownership

Codex loads user instructions from `$CODEX_HOME/AGENTS.md` or `~/.codex/AGENTS.md`. Claude reads `~/.claude/CLAUDE.md`. Home pointers use absolute paths so the active project can live anywhere. In project scope, setup maintains an owned block in `AGENTS.md` and a Claude import if selected. The rest of each file remains project-owned. The [harness table](harnesses.md) gives skill directory placement.

External Git project roots receive exact link paths in their local `info/exclude`. Team instructions and the portable `.tkstack/.gitignore` remain visible to Git. Avoid committing machine-specific symlinks. TKStack refuses to take over existing instruction blocks, link destinations or hook managers.

## Adopt team constraints

`./install.sh --target /absolute/project --adopt` seeds `.constrain/config.json` and an empty review inventory. A project starts with zero approved Python tests and a small policy-file budget. Set budgets, globs and reviews to reflect actual project risks before committing. Existing policies remain under team control. Check with `.tkstack/tkstack skills constrain -- native check --repo .`. Serena setup and indexing likewise require an explicit project target outside your home root and the TKStack checkout. See [constraint selection and configuration](../skills/constrain/SKILL.md).

Add `--constraint-hook` to install a worktree's staged gate when using Git's default hooks directory. If a team already owns its hook, call `.tkstack/tkstack skills constrain -- native check --repo . --staged` from that manager, or run the checker in CI after installing TKStack at a reviewed revision. If the team later switches managers, uninstall removes its original default hook when the contents still match. Stage project policy with the change. Maintainers can opt in with native Git configuration. See [the documentation gate](documentation.md).

## Bootstrap integrity

The recommended release path uses Git at a reviewed full commit, as shown in the [README](../README.md). An independently verified bootstrap script also accepts `TKSTACK_REV` when obtaining a fresh Git checkout. An existing pinned Git checkout must match the origin, revision and clean working tree. An unpinned Git bootstrap tracks the remote branch and fast-forwards existing matching checkouts. Use that only for intentional development updates.

Without Git, supply `TKSTACK_TARBALL_SHA256` from a trusted channel and either the full `TKSTACK_REV` or an HTTPS `TKSTACK_TARBALL`. The script verifies downloaded bytes before extraction and checks archive paths and symlinks. A trusted tarball refresh preserves local state. `TKSTACK_HOME` selects the source location. A pre-existing unrelated checkout requires explicit `TKSTACK_TRUST_HOME=1` for development use.

Use an installed Python 3.11+ or select it with `TKSTACK_PYTHON`. When unavailable, the bootstrap can install Python with uv using the pins in the README. First acquisition needs network access; running setup from an existing checkout with its interpreter works offline. The checkout-level preview inspects local files. Running a separately downloaded bootstrap first acquires its source.

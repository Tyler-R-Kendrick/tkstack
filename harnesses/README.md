# Harness preferences

`skills.json` maps source-local skill names to installed aliases. Matt Pocock's
`tdd` is installed as `matt-tdd`, preserving Pstack's `tdd`. The installer
generates a copy of Matt's skill tree with declarations and invocation
references rewritten; relative reference paths and invocation-policy metadata
stay intact. Remove an existing installation before changing its alias names.

`placement` decides which harness directories receive each upstream source.
Personal skills in `skills/` join every selected harness. By default, upstream
skills and the committed third-party-derived packages in `.agents/skills/` go
only to the shared `.agents/skills/` directory (the `codex` slot, which other
Agent Skills hosts also read). Pstack and Cursor Team Kit are Cursor packages
and go only to `.cursor/` (skills, agents, and rules). Graphify and Impeccable
ship per-harness builds and keep every harness. Reinstalling removes this
checkout's links that fall outside their placement; doctor reports any left.

Cursor Team Kit's two native rules are installed into Cursor's rules directory.
Shared workflow and engineering defaults are documented in `docs/standards.md`
and the root agent instructions. Keep additional native settings under a
directory per harness, such as `codex/`, `claude/`, or `cursor/`.

Model selection follows capabilities in the active harness. A package install
does not establish access to a provider's models, so no entitled model IDs are
invented here. Credentials and machine-specific state belong outside this repo.

The installer also maintains native shared-steering pointers. See
`docs/learning.md` for home/project placement and the portable evidence format.
`integrations.json` records runtime versions, verified release digests, and
service specifications; `scripts/setup_integrations.py` manages native hook
and MCP entries without embedding credentials. See `docs/integrations.md` for
what is installed versus dependent on a host runtime or account sign-in.

`copilot/lever.yml` supplies initial Lever repository defaults. The separate
`scripts/setup_lever.py` installs Lever's documented project Copilot layout and
creates `.github/lever.yml` only when absent. It preserves existing dials and
leaves personal `~/.copilot/lever.yml` alone. See `docs/lever.md`.

The root `install.sh` is the dotfiles bootstrap: profiles for user installation,
devcontainers, and Codex cloud startup coordinate these configurations with all
managed runtime recipes and state initialization. See [bootstrap](../docs/bootstrap.md).
Home-scope Codex configuration honors CODEX_HOME for the actual current home;
explicit isolated/project targets stay contained in their selected directory.

# Harness preferences

`skills.json` maps source-local skill names to installed aliases. Matt Pocock's
`tdd` is installed as `matt-tdd`, preserving Pstack's `tdd`. Emil Kowalski's
`prototype` is installed as `emil-prototype`, preserving Matt's `prototype`.
The installer generates a copy of each aliased source's skill tree with
declarations and invocation references rewritten; relative reference paths and
invocation-policy metadata stay intact. Emil's generated view rewrites quoted
`prototype` calls, including the one in `break-ui`. Pstack keeps
`rewrite_callers` off, so only `unslop` becomes `pstack-unslop` and its other
callers still resolve to the personal `unslop`. Remove an existing installation
before changing its alias names.

`placement` decides which harness directories receive each upstream source.
Personal skills in `skills/` join every selected harness.
`scripts/harness_paths.py` places those skills in Codex (`.agents/skills`),
Claude Code (`.claude/skills`), Cursor (`.cursor/skills`), Grok
(`.grok/skills`), Kimi (`.kimi/skills`), Muse (`.muse/skills`), and OpenCode
(`.config/opencode/skills`). Paths are relative to the install target, so a
home install puts Claude Code in `~/.claude/skills`. `placement.default` is
Codex (`.agents/skills/`), Grok (`.grok/skills`), Kimi (`.kimi/skills`), Muse
(`.muse/skills`), and OpenCode (`.config/opencode/skills`). Emil Kowalski and
ub-mode use that default, so a default profile install lands them in the
shared Codex directory unless you also select the other harnesses. Pstack and Cursor Team Kit are Cursor packages
and go only to `.cursor/` (skills, agents, and rules). Graphify and Impeccable
ship per-harness builds for Codex, Claude Code (`.claude/skills`), and Cursor
(`.cursor/skills`). Graphify also keeps a generic agent-skills view at
`.tkstack/skill-views/graphify/default/`; installed links use the Codex, Claude,
and Cursor views. t3code does not get a skills directory. It runs on Claude,
Codex, Cursor, Copilot, or Grok and reads that host's skills. See
`t3code/README.md`. `./install.sh --uninstall` removes only this checkout's
links and launchers. Reinstalling also removes this checkout's links that fall
outside their placement; doctor reports any left. `sources.lock.json` pins the
upstream bytes, and `SCOPE.md` names the supported baseline.

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

`copilot/lever.yml` supplies initial Lever repository defaults. Copilot is not a
`--harness` skills directory. The separate `src/setup_lever.py` installs Lever's
documented project Copilot layout, linking its skills into `.github/skills`, and
creates `.github/lever.yml` only when absent. It preserves existing dials and
leaves personal `~/.copilot/lever.yml` alone. See `docs/lever.md`.

The root `install.sh` is the dotfiles bootstrap: profiles for user installation,
devcontainers, and Codex cloud startup coordinate these configurations with all
managed runtime recipes and state initialization. See [bootstrap](../docs/bootstrap.md).
Home-scope Codex configuration honors CODEX_HOME for the actual current home;
explicit isolated/project targets stay contained in their selected directory.

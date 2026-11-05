# Harness preferences

| Harness | Install path |
| --- | --- |
| Codex | `.agents/skills` |
| Claude Code | `.claude/skills` |
| Cursor | `.cursor/skills`, plus `.cursor/rules` |
| Copilot | `~/.copilot/skills` at home, `.github/skills` in a project |
| Grok | `.grok/skills` |
| Kimi | `.kimi/skills` |
| Muse | `~/.config/muse/skills` at home, `.agents/skills` in a project |
| OpenCode | `.config/opencode/skills` at home, `.opencode/skills` in a project |
| t3code | No skills directory. T3 Code is an orchestrator, so its skills come from the delegate harnesses' placements (`delegates.t3code`: Claude, Codex, Cursor, Copilot, and Grok). |

`skills/skills.json` maps source-local skill names to installed aliases. Matt Pocock's
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
Claude Code (`.claude/skills`), Cursor (`.cursor/skills`), GitHub Copilot
(`~/.copilot/skills` at home and `.github/skills` in a project; [Copilot CLI
skills](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-skills)),
Grok (`.grok/skills`, the directory Grok Build reads), Kimi (`.kimi/skills`, the
kimi-cli directory; Kimi Code CLI's `~/.kimi-code/skills` is not installed),
Muse, and OpenCode (`.config/opencode/skills` at home, `.opencode/skills` in a
project). Muse Code 1.4.14 (`muse skills install --scope user`) writes
`$XDG_CONFIG_HOME/muse/skills` when that variable is set, and otherwise
`~/.config/muse/skills`. This installer links the default
`~/.config/muse/skills` path and does not follow `XDG_CONFIG_HOME`, so an
isolated target stays inside that target. Project Muse skills use
`.agents/skills`, the same directory as Codex. `muse skills --help` does not
print the directory; the 1.4.14 install result and the binary's
`$CONFIG_DIR/skills` string do. Paths are relative to the install target, so a
home install puts Claude Code in `~/.claude/skills`. `placement.default` is
Codex (`.agents/skills/`), Grok (`.grok/skills`), Kimi (`.kimi/skills`),
OpenCode (`.config/opencode/skills` or `.opencode/skills`), Copilot, and Muse.
Emil Kowalski and ub-mode use that default, so a default profile install lands
them in the shared Codex directory unless you also select the other harnesses.
Pstack and Cursor Team Kit are Cursor packages and go only to `.cursor/`
(skills, agents, and rules). Graphify and Impeccable ship per-harness builds
for Codex, Claude Code (`.claude/skills`), and Cursor (`.cursor/skills`).
Graphify also keeps a generic agent-skills view at
`.tkstack/skill-views/graphify/default/`; installed links use the Codex, Claude,
and Cursor views. t3code does not get a skills directory. It is an orchestrator
that runs Claude, Codex, Cursor, Copilot, or Grok and reads that host's skills.
`skills/skills.json` records that with `delegates.t3code`. See
[t3code](t3code.md). Repo-quality counts t3code as covered when every harness
named there is itself linked. The check still requires all nine hosts.
`./install.sh --uninstall` removes this checkout's links for every harness
and unsets `core.hooksPath` when it is `.githooks`. Reinstalling also removes
this checkout's links that fall outside their placement. `sources.lock.json` pins the
upstream bytes, and `SCOPE.md` names the supported baseline.

Cursor rules this repository owns are `.cursor/rules/graphify.mdc` and
`.cursor/rules/tkstack-steering.mdc`. The installer links those tracked files
into the selected target and leaves them as files when the target is this
checkout. Cursor Team Kit's two native rules are installed from the vendored
package into the same rules directory. Shared workflow and engineering defaults
are documented in `docs/standards.md` and the root agent instructions.

Model selection follows capabilities in the active harness. A package install
does not establish access to a provider's models, so no entitled model IDs are
invented here. Credentials and machine-specific state belong outside this repo.

The installer links `.agents/steering` and `.agents/principles`. It does not
rewrite `AGENTS.md` or `CLAUDE.md`. See `docs/learning.md` for the portable
evidence format. Install does not register native hooks or MCP entries, and it
does not download tool runtimes. Source versions live in `sources.lock.json`.
See `docs/integrations.md` for what a host still has to provide.
`vendor/ponytail/` is the pinned DietrichGebert/ponytail 5.3.3 snapshot: six
skills and Node lifecycle-hook adapters. It is vendored so setup links the
bytes locked in `sources.lock.json` instead of cloning upstream. It is not a
harness directory.

`.github/lever.yml` is this repository's Lever dial file. `--harness copilot`
links skills into `~/.copilot/skills` or `.github/skills`, the same way it
links every other skill. Install does not write `.github/lever.yml` or a
separate Copilot project layout. See `docs/lever.md`.

The root `install.sh` links the selected hosts and sets `core.hooksPath`. It
does not select a profile or provision a toolchain. See [install](bootstrap.md).
Home-scope Codex configuration honors CODEX_HOME for the actual current home;
explicit isolated/project targets stay contained in their selected directory.

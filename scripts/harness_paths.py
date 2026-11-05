"""Resolve native host configuration without redirecting isolated install targets."""
import os
from pathlib import Path


# Verified skill directories, relative to the install target.
# Grok Build reads .grok/skills (user guide: project .grok/skills and ~/.grok/skills).
# kimi-cli reads .kimi/skills (project and ~/.kimi/skills). Kimi Code CLI uses
# ~/.kimi-code/skills and is a different layout; this installer does not write it.
# OpenCode reads .config/opencode/skills for a home install and .opencode/skills
# for a project install (OpenCode skills docs).
# GitHub Copilot CLI reads ~/.copilot/skills (personal) and .github/skills
# (project). Docs: https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-skills
# It also reads ~/.agents/skills and .claude/skills; those belong to other hosts.
# Muse Code 1.4.14 (`muse skills install --scope user`) writes
# $XDG_CONFIG_HOME/muse/skills when that variable is set, otherwise
# ~/.config/muse/skills. Project skills are .agents/skills, the Codex directory.
# This installer links the default home path and does not follow XDG_CONFIG_HOME,
# so an isolated target stays inside that target. `muse skills --help` does not
# print the directory; the 1.4.14 install result and binary name
# `$CONFIG_DIR/skills` and `$HOME/.config/muse`.
SKILL_DIRECTORIES = {
    "codex": Path(".agents/skills"),
    "claude": Path(".claude/skills"),
    "cursor": Path(".cursor/skills"),
    "copilot": Path(".copilot/skills"),
    "grok": Path(".grok/skills"),
    "kimi": Path(".kimi/skills"),
    "muse": Path(".config/muse/skills"),
    "opencode": Path(".config/opencode/skills"),
}
OPENCODE_PROJECT = Path(".opencode/skills")
COPILOT_PROJECT = Path(".github/skills")
MUSE_PROJECT = Path(".agents/skills")
# Hosts that receive native hook and MCP files. Other skill hosts are links only.
HOOK_HARNESSES = ("codex", "claude", "cursor")
# t3code is an orchestrator with no skills directory. skills.json delegates
# names the hosts it runs. It is intentionally absent from SKILL_DIRECTORIES.


def skill_directory(harness, scope="home"):
    """Native skills directory, or None when this installer does not link one."""
    if harness not in SKILL_DIRECTORIES:
        return None
    if harness == "opencode" and scope == "project":
        return OPENCODE_PROJECT
    if harness == "copilot" and scope == "project":
        return COPILOT_PROJECT
    if harness == "muse" and scope == "project":
        return MUSE_PROJECT
    return SKILL_DIRECTORIES[harness]


def codex_directory(target, scope):
    if scope == 'home' and target.resolve() == Path.home().resolve() and os.environ.get('CODEX_HOME'):
        return Path(os.environ['CODEX_HOME']).expanduser().absolute()
    return target / '.codex'

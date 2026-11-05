"""Resolve native host configuration without redirecting isolated install targets."""
import os
from pathlib import Path


# Verified skill directories, relative to the install target.
# Grok Build reads .grok/skills (user guide: project .grok/skills and ~/.grok/skills).
# kimi-cli reads .kimi/skills (project and ~/.kimi/skills). Kimi Code CLI uses
# ~/.kimi-code/skills and is a different layout; this installer does not write it.
# OpenCode reads .config/opencode/skills for a home install and .opencode/skills
# for a project install (OpenCode skills docs).
# Muse has no verified skills directory of its own. Muse Code installs skills
# into ~/.agents/skills, which is the Codex directory. Muse is experimental and
# is not linked.
SKILL_DIRECTORIES = {
    "codex": Path(".agents/skills"),
    "claude": Path(".claude/skills"),
    "cursor": Path(".cursor/skills"),
    "grok": Path(".grok/skills"),
    "kimi": Path(".kimi/skills"),
    "opencode": Path(".config/opencode/skills"),
}
OPENCODE_PROJECT = Path(".opencode/skills")
# Hosts that receive native hook and MCP files. Other skill hosts are links only.
HOOK_HARNESSES = ("codex", "claude", "cursor")
# t3code runs Claude, Codex, Cursor, Copilot, or Grok and reads that host's skills.
DELEGATED_HARNESSES = {"t3code": ("claude", "codex", "cursor", "copilot", "grok")}


def skill_directory(harness, scope="home"):
    """Native skills directory, or None when this installer does not link one."""
    if harness in DELEGATED_HARNESSES or harness not in SKILL_DIRECTORIES:
        return None
    if harness == "opencode" and scope == "project":
        return OPENCODE_PROJECT
    return SKILL_DIRECTORIES[harness]


def codex_directory(target, scope):
    if scope == 'home' and target.resolve() == Path.home().resolve() and os.environ.get('CODEX_HOME'):
        return Path(os.environ['CODEX_HOME']).expanduser().absolute()
    return target / '.codex'

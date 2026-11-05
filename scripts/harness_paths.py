"""Resolve native host configuration without redirecting isolated install targets."""
import os
from pathlib import Path


# Skill directories are relative to the install target. Home install therefore
# uses ~/.grok/skills, ~/.kimi/skills, ~/.muse/skills, and
# ~/.config/opencode/skills. Project scope stays inside the selected target.
SKILL_DIRECTORIES = {
    "codex": Path(".agents/skills"),
    "claude": Path(".claude/skills"),
    "cursor": Path(".cursor/skills"),
    "grok": Path(".grok/skills"),
    "kimi": Path(".kimi/skills"),
    "muse": Path(".muse/skills"),
    "opencode": Path(".config/opencode/skills"),
}
# Hosts that receive native hook and MCP files. Other skill hosts are links only.
HOOK_HARNESSES = ("codex", "claude", "cursor")
# t3code runs Claude, Codex, Cursor, Copilot, or Grok and reads that host's skills.
DELEGATED_HARNESSES = {"t3code": ("claude", "codex", "cursor", "copilot", "grok")}


def skill_directory(harness):
    """Native skills directory, or None when the host delegates to another harness."""
    if harness in DELEGATED_HARNESSES:
        return None
    return SKILL_DIRECTORIES[harness]


def codex_directory(target, scope):
    if scope == 'home' and target.resolve() == Path.home().resolve() and os.environ.get('CODEX_HOME'):
        return Path(os.environ['CODEX_HOME']).expanduser().absolute()
    return target / '.codex'

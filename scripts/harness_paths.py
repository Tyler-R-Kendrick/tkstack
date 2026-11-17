"""Resolve native host configuration without redirecting isolated install targets."""
import os
from pathlib import Path


# Native paths and host variants are documented in docs/harnesses.md.
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
PROJECT_DIRECTORIES = {"opencode": Path(".opencode/skills"), "copilot": Path(".github/skills"),
                       "muse": Path(".agents/skills")}


def skill_directory(harness, scope="home"):
    default = SKILL_DIRECTORIES.get(harness)
    return PROJECT_DIRECTORIES.get(harness, default) if scope == "project" else default


def codex_directory(target, scope):
    if scope == 'home' and target.resolve() == Path.home().resolve() and os.environ.get('CODEX_HOME'):
        return Path(os.environ['CODEX_HOME']).expanduser().absolute()
    return target / '.codex'

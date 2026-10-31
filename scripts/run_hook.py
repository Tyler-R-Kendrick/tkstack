#!/usr/bin/env python3
"""Adapt upstream hooks to pinned source paths; missing runtimes fail open."""

import os
from pathlib import Path
import shutil
import subprocess
import sys
sys.dont_write_bytecode = True

from tool import runtime_path
from runtime_environment import with_paths
from tkstack_state import ensure_state


ROOT = Path(__file__).resolve().parent.parent


def hook_command(root, integration, harness, event):
    environment = with_paths(root)
    if integration == 'repo-docs':
        return [sys.executable, '-B', str(root / 'scripts/docs_hook.py'), '--harness', harness], environment
    if integration == "caveman":
        node = shutil.which("node", path=environment.get("PATH"))
        source = root / "vendor/caveman"
        if not node or not (source / "src/hooks/caveman-config.js").is_file():
            return None, environment
        if harness == "codex" and event == "activate":
            return [node, str(source / ".codex/codex-sessionstart.js")], environment
        if harness == "cursor" and event == "activate":
            return [node, str(source / "src/hooks/caveman-host-session-start.js"), "cursor"], environment
        if harness != "claude":
            raise ValueError("Unsupported Caveman hook event")
        handlers = {"activate": ("caveman-activate.js", []),
                    "subagent": ("caveman-activate.js", ["--subagent"]),
                    "prompt": ("caveman-mode-tracker.js", []),
                    "record": ("caveman-stats.js", ["--record"])}
        script, arguments = handlers[event]
        environment["CLAUDE_CONFIG_DIR"] = str(ensure_state(root / ".tkstack/state/caveman/claude"))
        environment["CLAUDE_PLUGIN_ROOT"] = str(source)
        # Overrides patch agent files in place; keep every pinned snapshot immutable.
        for role in ("BUILDER", "INVESTIGATOR", "REVIEWER"):
            environment.pop("CAVECREW_" + role + "_MODEL", None)
        return [node, str(source / "src/hooks" / script), *arguments], environment
    if integration == "ponytail":
        handlers = {"activate": "ponytail-activate.js", "prompt": "ponytail-mode-tracker.js",
                    "subagent": "ponytail-subagent.js"}
        node = shutil.which("node", path=environment.get("PATH"))
        if not node:
            return None, environment
        directory = ensure_state(root / ".tkstack/state/ponytail" / harness)
        environment["PLUGIN_DATA"] = str(directory)
        environment["CLAUDE_CONFIG_DIR"] = str(directory)
        return [node, str(root / "vendor/ponytail/hooks" / handlers[event])], environment
    if integration == "graphify":
        import json
        from python_runtime import package_ready
        from graphify_adapter import runtime_environment
        manifest = json.loads((root / "harnesses/integrations.json").read_text())
        if not package_ready(root, "graphify", manifest["tools"]["graphify"]):
            return None, environment
        environment = runtime_environment(root)
        return [str(runtime_path(root, "graphify")), "hook-guard", event], environment
    binary = runtime_path(root, integration)
    if not binary or not binary.is_file() or not os.access(binary, os.X_OK):
        return None, environment
    if integration == "rtk":
        directory = root / ".tkstack/state/rtk"
        ensure_state(directory)
        environment["RTK_DB_PATH"] = str(directory / "history.db")
        return [str(binary), "hook", harness], environment
    if integration == "impeccable":
        directory = {"codex": ".agents", "claude": ".claude", "cursor": ".cursor"}[harness]
        launcher = root / "vendor/impeccable" / directory / "skills/impeccable/scripts/impeccable"
        environment["IMPECCABLE_BIN"] = str(binary)
        environment["IMPECCABLE_HOME"] = str(ensure_state(root / ".tkstack/state/impeccable"))
        return [str(launcher), "hook"], environment
    raise ValueError("Unknown hook integration")


def main():
    if len(sys.argv) != 4:
        return 2
    try:
        command, environment = hook_command(ROOT, *sys.argv[1:])
        if command is not None:
            result = subprocess.run(command, env=environment, timeout=40, check=False)
            if sys.argv[1] == 'repo-docs':
                return result.returncode
    except (OSError, ValueError, KeyError, subprocess.TimeoutExpired) as error:
        if sys.argv[1] == 'repo-docs':
            print('Repository docs hook failed: ' + str(error), file=sys.stderr)
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())

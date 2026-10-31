#!/usr/bin/env python3
"""Run a tkstack runtime without changing PATH or redirecting the user's home."""

import json
import os
from pathlib import Path
import subprocess
import sys
from tkstack_state import ensure_state
from runtime_environment import with_paths


ROOT = Path(__file__).resolve().parent.parent


def runtime_path(root, name):
    if name == "command-schema":
        return root / '.tkstack/runtime/command-schema/bin/python'
    if name == "openwiki":
        return root / ".tkstack/runtime/openwiki/node_modules/.bin/openwiki"
    if name == "graphify":
        return root / ".tkstack/runtime/graphify/bin/graphify"
    if name == "headroom":
        return root / ".tkstack/runtime/headroom/bin/headroom"
    if name == "open-design":
        configured = os.environ.get("OPEN_DESIGN_CLI")
        if not configured:
            return None
        path = Path(configured).expanduser().resolve()
        if str(path) in ("/usr/bin/od", "/bin/od"):
            raise ValueError("OPEN_DESIGN_CLI must select OpenDesign, not the system od utility")
        return path
    return root / ".tkstack/runtime/bin" / name


def main():
    os.environ.update(with_paths(ROOT))
    if len(sys.argv) < 2:
        print("usage: tool.py <rtk|impeccable|headroom|higgsfield|wikiskill|open-design|openwiki|graphify|codify|skillify> [args...]", file=sys.stderr)
        return 2
    name, args = sys.argv[1], sys.argv[2:]
    if name in ('codify', 'skillify'):
        args = ['-B', str(ROOT / 'skills/learn/skills' / name / 'scripts' / (name + '.py')), *args]
        name = 'command-schema'
    if name == "wikiskill":
        sys.dont_write_bytecode = True
        sys.path.insert(0, str(ROOT / "vendor/wikiskill"))
        from wikiskill.cli import main as wikiskill_main
        sys.argv = ["wikiskill", *args]
        return wikiskill_main()
    manifest = json.loads((ROOT / "harnesses/integrations.json").read_text())
    if name not in manifest["tools"]:
        print("Unknown tkstack tool: " + name, file=sys.stderr)
        return 2
    try:
        path = runtime_path(ROOT, name)
        environment = with_paths(ROOT)
        working_directory = None
        if name == 'command-schema':
            from python_runtime import package_ready
            if not package_ready(ROOT, name, manifest['tools'][name]):
                print('Command runtime unavailable; run install.sh or setup_integrations.py --install-runtimes --runtime command-schema', file=sys.stderr)
                return 127
        if name == "graphify":
            from python_runtime import package_ready
            if not package_ready(ROOT, name, manifest["tools"][name]):
                print("graphify: locked runtime unavailable; install with scripts/setup_integrations.py --target . --install-runtimes --runtime graphify", file=sys.stderr)
                return 127
            from graphify_adapter import runtime_environment, managed_arguments
            args = managed_arguments(ROOT, args)
            environment = runtime_environment(ROOT, args)
            if args and args[0] == "mcp":
                path = path.with_name("graphify-mcp")
                args = args[1:]
                if not os.environ.get("GRAPHIFY_OUT") and not os.environ.get("TKSTACK_WORKSPACE_DIR"):
                    from tkstack_state import project_root
                    working_directory = project_root()
                    # Native MCP joins project_path with GRAPHIFY_OUT; keep the default relative.
                    environment["GRAPHIFY_OUT"] = ".tkstack/graphify"
        if name == "openwiki":
            from npm_runtime import package_ready
            if not package_ready(ROOT, name, manifest["tools"][name]):
                print("openwiki: locked runtime unavailable; install with scripts/setup_integrations.py --target . --install-runtimes --runtime openwiki", file=sys.stderr)
                return 127
            environment["OPENWIKI_CONFIG_DIR"] = str(ensure_state(Path(environment.get("OPENWIKI_CONFIG_DIR", ROOT / ".tkstack/openwiki"))))
            environment.setdefault("OPENWIKI_TELEMETRY_DISABLED", "1")
        if path is None or not path.is_file() or not os.access(path, os.X_OK):
            print(f"{name}: runtime unavailable; see scripts/setup_integrations.py --status", file=sys.stderr)
            return 127
        return subprocess.run([str(path), *args], env=environment, cwd=working_directory).returncode
    except (OSError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

"""Install a locked npm runtime locally with a single writer and atomic publication."""

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import sys
sys.dont_write_bytecode = True
from tkstack_state import ensure_state


def node_ready(minimum):
    node = shutil.which("node")
    if not node:
        return False
    try:
        result = subprocess.run([node, "--version"], capture_output=True, text=True,
                                timeout=5, check=True)
        match = re.fullmatch(r"v(\d+)\.(\d+)\.(\d+)\s*", result.stdout)
        return bool(match and tuple(map(int, match.groups())) >= tuple(map(int, minimum.split("."))))
    except (OSError, subprocess.SubprocessError):
        return False


def package_ready(root, name, tool, directory=None):
    directory = directory or root / ".tkstack/runtime" / name
    recipe = root / tool["recipe"]
    try:
        package = json.loads((directory / "node_modules" / tool["package"] / "package.json").read_text())
        executable = directory / "node_modules/.bin" / tool["bin"]
        return (package["version"] == tool["version"]
                and executable.is_file() and os.access(executable, os.X_OK)
                and all((directory / filename).read_bytes() == (recipe / filename).read_bytes()
                        for filename in ("package.json", "package-lock.json"))
                and node_ready(tool["minimum_node"]))
    except (OSError, ValueError, KeyError):
        return False


def install(root, name, tool):
    if package_ready(root, name, tool):
        return
    npm = shutil.which("npm")
    if not npm or not node_ready(tool["minimum_node"]):
        raise ValueError(f"{name} requires npm and Node.js >= {tool['minimum_node']}")
    parent = root / ".tkstack/runtime"
    ensure_state(parent)
    lock = parent / ("." + name + "-install.lock")
    try:
        lock.mkdir()
    except FileExistsError as error:
        raise ValueError(f"{name}: another install owns {lock}; inspect it before retrying") from error
    try:
        destination = parent / name
        if destination.exists() or destination.is_symlink():
            raise ValueError(f"{name}: existing runtime differs from its lock; preserve or remove {destination} before reinstalling")
        with tempfile.TemporaryDirectory(prefix="." + name + "-", dir=parent) as temporary:
            staging = Path(temporary)
            for filename in ("package.json", "package-lock.json"):
                shutil.copyfile(root / tool["recipe"] / filename, staging / filename)
            environment = {**os.environ, "npm_config_cache": str(root / ".tkstack/cache/npm")}
            subprocess.run([npm, "ci", "--omit=dev", "--no-audit", "--no-fund", "--engine-strict"],
                           cwd=staging, env=environment, check=True, timeout=600)
            if not package_ready(root, name, tool, staging):
                raise ValueError(f"{name}: installed package failed the version, lock, or executable check")
            staging.rename(destination)
    finally:
        lock.rmdir()
    print(f"Installed {name} {tool['version']} from its npm integrity lock")

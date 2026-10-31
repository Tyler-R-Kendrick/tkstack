#!/usr/bin/env python3
"""Verify pinned sources, resolved skill names, and installed links."""

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
sys.dont_write_bytecode = True

import install
from steering_adapter import instruction_plan
from setup_integrations import configuration_plan, status
from graphify_install import check_views
from runtime_environment import with_paths
from tkstack_state import policy_plan
from sync_codify import sync as check_codify_release


def main():
    os.environ.update(with_paths(install.ROOT))
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", type=Path, default=Path.home(),
                        help="Installed home or project root (default: your home)")
    parser.add_argument("--harness", action="append", choices=tuple(install.SKILL_PATHS))
    parser.add_argument("--scope", choices=("home", "project"))
    args = parser.parse_args()
    try:
        install.verify_vendor(install.ROOT)
        check_views(install.ROOT)
        check_codify_release(check=True)
        from python_runtime import package_ready
        recipe = json.loads((install.ROOT / 'harnesses/integrations.json').read_text())['tools']['command-schema']
        owned_verified = package_ready(install.ROOT, 'command-schema', recipe)
        if owned_verified:
            owned = subprocess.run([sys.executable, str(install.ROOT / 'scripts/tool.py'), 'command-schema',
                                    '-B', str(install.ROOT / 'scripts/check_skills.py')],
                                   capture_output=True, text=True, timeout=60)
            if owned.returncode:
                raise ValueError('Owned skill conformance failed: ' + owned.stderr.strip())
        from runner_install import check as check_runner
        check_runner(install.ROOT, install.ROOT / '.tkstack')
        from setup_repo_hooks import setup as check_repo_hooks
        check_repo_hooks(install.ROOT, check=True)
        _, before, after = policy_plan(install.ROOT)
        if before != after:
            raise ValueError("Local state ignore policy is missing or stale; rerun the installer")
        harnesses = list(dict.fromkeys(args.harness or install.SKILL_PATHS))
        skills = install.collect(install.ROOT, "skills")
        for harness in harnesses:
            for name, path in install.collect(install.ROOT, "skills", harness).items():
                text = (path / "SKILL.md").read_text()
                match = re.search(r"^name:\s*(.*)$", text, re.M)
                if not match or match[1].strip().strip('\"\'') != name:
                    raise ValueError(f"Skill name does not match installed name: {name} ({harness})")
        target = args.target.expanduser().resolve()
        plan = install.link_plan(install.ROOT, target, harnesses)
        missing = [str(destination) for source, destination in plan
                   if not source.exists() or not install.matches(destination, source)]
        if missing:
            raise ValueError("Missing or mismatched installation: " + ", ".join(missing))
        stale = install.stale_links(install.ROOT, target, harnesses, plan)
        if stale:
            raise ValueError("Stale links outside their placement; rerun the installer: "
                             + ", ".join(map(str, stale)))
        scope = args.scope or ("home" if target == Path.home().resolve() else "project")
        if instruction_plan(install.ROOT, target, harnesses, scope):
            raise ValueError("Native steering pointers are missing or stale; rerun the installer")
        if configuration_plan(install.ROOT, target, harnesses, scope):
            raise ValueError("Native hook/MCP configuration is missing or stale; rerun the installer")
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        print(f"tkstack: {error}", file=sys.stderr)
        return 1
    print(f"Verified {len(skills)} skills and {len(plan)} installed links at {target}.")
    print("Pinned file hashes, executable modes, and symlink targets match.")
    print('Owned skill conformance: verified.' if owned_verified else
          'Owned skill conformance: pending; install the managed command-schema runtime.')
    for tool in ("python3", "bash", "gh", "jq", "node", "codex", "claude", "cursor", "copilot"):
        print(f"{tool}: {'available' if shutil.which(tool) else 'not on PATH'}")
    print("Tool presence does not prove authentication or model access; see docs/evaluation.md.")
    missing = [name for name, value in status(install.ROOT).items() if value.get("runtime") == "missing"]
    if missing:
        print("Runtime downloads or local installations still missing: " + ", ".join(missing))
    return 0


if __name__ == "__main__":
    sys.exit(main())

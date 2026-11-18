"""Owned target initialization; source packages stay shared, workspace state stays local."""
import hashlib
import json
import os
import shutil
import shlex
import subprocess
from functools import cache
from skill_roots import load
from harness_paths import codex_directory
from pathlib import Path


def safe_path(path, base):
    """Reject symlinked components beneath the chosen installation boundary."""
    for component in (path, *path.parents):
        if component == base:
            break
        if component.is_symlink():
            raise ValueError(f"Refusing symlinked install path: {component}")


def read_install(path, root):
    if not path.exists():
        return {}
    data = json.loads(path.read_text())
    if (not isinstance(data, dict) or data.get("source") != str(root)
            or data.get("scope") not in ("home", "project")
            or not isinstance(data.get("links", {}), dict)
            or not all(isinstance(src, str) for src in data.get("links", {}).values())
            or not isinstance(data.get("harnesses"), list)
            or not all(isinstance(name, str) for name in data["harnesses"])):
        raise ValueError(f"Unrecognized installation owner or receipt: {path}")
    return data


@cache
def instructify(root):
    return load("install_instructions", root / "skills/learn/skills/instructify/scripts/instructify.py")


def instruction_changes(root, target, harnesses, scope="project", remove=False, previous=()):
    helper = instructify(root)
    content = (
        'Read `.agents/principles/SKILL.md` and applicable references before designing changes.\n'
        'Use the installed learn skill for corrections; store workspace state under this workspace’s `.tkstack/`, never in the dotfiles checkout.\n'
        'When changing tests or repository structure, read the installed constrain skill. '
        'If `.constrain/config.json` exists, run `.tkstack/tkstack skills constrain -- native check --repo .` before completion.\n'
        'Invoke compiled skills with `.tkstack/tkstack skills <name> -- <command>` from the working workspace.\n'
    )
    paths = {} if target == root else {'AGENTS.md': content}
    if target != root and ('claude' in harnesses or 'claude' in previous):
        paths['CLAUDE.md'] = '@AGENTS.md\n' if 'claude' in harnesses else None
    if scope == "home" and target != root:
        # Retire only marked sections left by earlier home installations.
        paths = {name: None for name in ("AGENTS.md", "CLAUDE.md")}
        home_body = (f"Read <{target / '.agents/principles/SKILL.md'}> and applicable references.\n"
                     f"Read matching learned rules in <{target / '.agents/steering/rules.md'}>.\n"
                     f"From the active project invoke `{shlex.quote(str(target / '.tkstack/tkstack'))} skills <name> -- <command>`. "
                     f"Bundled tool commands are in `{target / '.tkstack/bin'}`. "
                     "Keep project state in the active project's .tkstack directory.\n")
        if "codex" in harnesses or "codex" in previous:
            paths[codex_directory(target, scope) / "AGENTS.md"] = home_body if "codex" in harnesses else None
        if "claude" in harnesses or "claude" in previous:
            paths[target / ".claude/CLAUDE.md"] = home_body if "claude" in harnesses else None
    changes = []
    for name, body in paths.items():
        path = target / name
        safe_path(path, target if path.is_relative_to(target) else path.parent.parent)
        if path.is_dir():
            raise ValueError(f"Expected an instruction file: {path}")
        before = path.read_text() if path.exists() else None
        override = path.with_name("AGENTS.override.md")
        if body and path.name == "AGENTS.md" and not remove and override.is_file() and override.read_text().strip():
            raise ValueError('AGENTS.override.md shadows target instructions; reconcile it before installing')
        if body and scope == 'project' and name == 'CLAUDE.md' and helper.imports_agents(before or '') and '<!-- instructify:tkstack:start -->' not in (before or ''):
            continue
        after = helper.owned_section(before, 'tkstack', hashlib.sha256(str(root).encode()).hexdigest()[:24], body or "", remove=remove or body is None)
        if before != after:
            changes.append((path, before, after))
    return changes


def apply_instructions(changes, dry_run=False):
    for path, before, after in changes:
        print(f"{'Would ' if dry_run else ''}update: {path}")
        if dry_run:
            continue
        current = path.read_text() if path.exists() else None
        if current != before:
            raise ValueError(f'Target instructions changed during setup: {path}')
        instructify(Path(__file__).resolve().parents[1]).atomic_write(path, after)
        if after and after.startswith(HOOK_HEADER):
            path.chmod(0o755)


def verify(plan, changes):
    errors = [f'Missing or incorrect installed link: {destination}' for source, destination in plan
              if not destination.is_symlink() or destination.resolve() != source or not source.exists()]
    errors.extend(f'Target configuration needs setup: {path}' for path, _, _ in changes)
    errors.extend(f'Missing target steering rules: {source / "rules.md"}' for source, destination in plan
                  if destination.name == 'steering' and not (source / 'rules.md').is_file())
    if errors:
        raise ValueError('\n'.join(errors))
    print(f'Verified {len(plan)} target links and target instruction ownership.')


def git(target, *args):
    return subprocess.run(["git", "-C", str(target), *args], capture_output=True, text=True, timeout=10)


def git_root(target):
    if not shutil.which("git") or not target.is_dir():
        return False
    found = git(target, "rev-parse", "--show-toplevel")
    return found.returncode == 0 and Path(found.stdout.rstrip("\n")).resolve() == target


def git_file(target, name):
    result = git(target, "rev-parse", "--path-format=absolute", "--git-common-dir")
    if result.returncode:
        raise ValueError(result.stderr.strip())
    path = Path(result.stdout.rstrip("\n")) / name
    if path.is_symlink() or path.parent.is_symlink():
        raise ValueError(f"Refusing symlinked Git configuration: {path}")
    return path


def git_excludes(target, plan, remove=False):
    if not git_root(target):
        return []
    path = git_file(target, "info/exclude")
    before = path.read_text() if path.exists() else None
    body = before or ""
    key = hashlib.sha256(os.fsencode(target)).hexdigest()[:16]
    start, end = f"# tkstack {key} begin\n", f"# tkstack {key} end\n"
    prefix, marker, rest = body.partition(start)
    if body.count(start) != body.count(end) or body.count(start) > 1 or (marker and end not in rest):
        raise ValueError(f"Malformed tkstack block: {path}")
    suffix = rest.split(end, 1)[1] if marker else ""
    if remove:
        after = prefix + suffix if marker else before
    else:
        entries = {destination.relative_to(target).as_posix() for _, destination in plan}
        entries.add(".tkstack/install.json")
        block = "".join("/" + name + "\n" for name in sorted(entries))
        after = prefix + ("\n" if prefix and not prefix.endswith("\n") else "") + start + block + end + suffix
    return [] if before == after else [(path, before, after)]


HOOK_HEADER = "#!/bin/sh\n# tkstack project constraint gate\n"
HOOK = HOOK_HEADER + """set -eu
repo=$(git rev-parse --show-toplevel)
[ "$repo" = {project} ] || exit 0
exec "$repo/.tkstack/tkstack" skills constrain -- native check --repo "$repo" --staged
"""


def constraint_hook(target, remove=False):
    if not git_root(target):
        raise ValueError("The constraint hook requires a Git worktree root")
    if not remove and git(target, "config", "--get", "core.hooksPath").returncode == 0:
        raise ValueError("Existing Git hook manager: add the staged constraint command there instead")
    path = git_file(target, "hooks/pre-commit")
    before = path.read_text() if path.exists() else None
    script = HOOK.format(project=shlex.quote(str(target)))
    if before not in (None, script):
        if remove:
            return []
        raise ValueError(f"Foreign pre-commit hook: {path}; add the staged constraint command there")
    if not remove and before == script and not os.access(path, os.X_OK):
        return [(path, before, script)]
    after = None if remove else script
    return [] if before == after else [(path, before, after)]


def adoption(target):
    if not git_root(target):
        raise ValueError("Project adoption requires an existing Git worktree root")
    policy = target / ".constrain/config.json"
    reviews = policy.with_name("reviews.json")
    for path in (policy, reviews):
        safe_path(path, target)
    if policy.is_file():
        return []  # The consumer owns the policy and may use a different review path.
    if reviews.exists():
        raise ValueError("Existing review inventory needs its matching project policy")
    # Start with no approved suite or growth. Review current tests and choose
    # limits in the project; setup cannot certify behavioral value.
    config = {"version": 1, "tests": {"include": ["tests/test_*.py"], "exclude": [],
              "max_cases": 0, "max_bytes": 0, "reviews": ".constrain/reviews.json", "exceptions": []},
              "layout": {"budgets": [{"id": "policy", "include": [".constrain/**"], "exclude": [],
                        "max_files": 2, "max_bytes": 32768, "max_depth": 2,
                        "reason": "Keep project policy and its test review inventory together."}]}, "artifacts": []}
    return [(reviews, None, "{}\n"), (policy, None, json.dumps(config, indent=2) + "\n")]


def status(target, root, profile):
    servers = json.loads((root / "mcp.json").read_text())["mcpServers"]
    print(f"Skill profile: {profile}")
    print("Project constraint policy:", "configured" if (target / ".constrain/config.json").is_file() else "available (--adopt)")
    print("Native agent hooks: optional; confirm registration and event delivery in the host")
    for name, spec in servers.items():
        command = spec["command"].replace("${PLUGIN_ROOT}", str(root)) if "command" in spec else None
        if spec.get("type") == "streamable-http":
            readiness = "client OAuth and live connection unverified"
        elif not (Path(command).is_file() if "/" in command else shutil.which(command)):
            readiness = "needs executable " + command
        elif name in ("playwright", "firecrawl", "graphify"):
            entry = spec["args"][0].replace("${PLUGIN_ROOT}", str(root))
            readiness = "local runtime present" if Path(entry).is_file() else "needs a dotfiles update"
            readiness += ("; cloud credentials unverified" if name == "firecrawl" and not os.environ.get("FIRECRAWL_API_KEY")
                          else "; client-owned graph unverified" if name == "graphify" else "")
        else:
            readiness = "executable present; client-owned graph unverified"
        print(f"MCP {name}: portable definition available; {readiness}")
    managed = root / ".tkstack/runtime/current/serena/bin/serena"
    executable = str(managed) if managed.is_file() else shutil.which("serena")
    print("Serena:", executable or "needs host-provisioned executable", "(project registration via --serena-command)")
    landmines = root / ".tkstack/runtime/current/bin/landmines"
    print("Landmines:", "local runtime present" if landmines.is_file() else "needs a dotfiles update")

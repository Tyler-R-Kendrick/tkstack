#!/usr/bin/env python3
"""Link tkstack's pinned skills and agents into a home or project directory."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys
sys.dont_write_bytecode = True
import subprocess

from tkstack_state import ensure_state
from runtime_environment import with_paths

from steering_adapter import apply_instructions, instruction_plan
from setup_integrations import apply_configuration, configuration_plan


ROOT = Path(__file__).resolve().parent.parent
SKILL_PATHS = {
    "codex": Path(".agents/skills"),
    "claude": Path(".claude/skills"),
    "cursor": Path(".cursor/skills"),
}
AGENT_PATHS = {
    "claude": Path(".claude/agents"),
    "cursor": Path(".cursor/agents"),
}


def verify_vendor(root):
    """Reject missing, changed, or untracked upstream files before installing."""
    lock = json.loads((root / "sources.lock.json").read_text())
    if lock["version"] != 1:
        raise ValueError("Unsupported sources.lock.json version")
    source_names = {path.name for path in (root / "vendor").iterdir()
                    if path.is_dir() or path.is_symlink()}
    if source_names != set(lock["sources"]):
        raise ValueError("Vendor sources differ from sources.lock.json")
    for name, source in lock["sources"].items():
        directory = root / "vendor" / name
        actual = {str(p.relative_to(directory)) for p in directory.rglob("*")
                  if p.is_file() or p.is_symlink()}
        expected = set(source["files"])
        if actual != expected:
            raise ValueError(f"{name}: file inventory differs from sources.lock.json")
        for filename, record in source["files"].items():
            path = directory / filename
            if record["mode"] not in ("100644", "100755", "120000"):
                raise ValueError(f"Unsupported vendored file: {path}")
            is_link = record["mode"] == "120000"
            if path.is_symlink() != is_link:
                raise ValueError(f"File type differs from lock: {path}")
            content = os.readlink(path).encode() if is_link else path.read_bytes()
            digest = hashlib.sha1(b"blob " + str(len(content)).encode() + b"\0" + content)
            if digest.hexdigest() != record["git_blob"]:
                raise ValueError(f"Vendored file differs from lock: {path}")
            executable = bool(path.lstat().st_mode & 0o111)
            if not is_link and executable != (record["mode"] == "100755"):
                raise ValueError(f"Executable mode differs from lock: {path}")


def skill_aliases(root):
    config = root / "harnesses/skills.json"
    return json.loads(config.read_text()).get("aliases", {}) if config.exists() else {}


def rewrite_callers(root, source):
    config = root / "harnesses/skills.json"
    return (json.loads(config.read_text()).get("rewrite_callers", {}).get(source, True)
            if config.exists() else True)


def rewrite_invocations(text, aliases):
    """Rename skill identifiers and calls, preserving relative file paths."""
    for original, alias in aliases.items():
        text = re.sub(rf"(?m)^(name:\s*){re.escape(original)}([ \t]*)$",
                      lambda match: match[1] + alias + match[2], text)
        for quote in ('`', '"', "'"):
            text = text.replace(quote + original + quote, quote + alias + quote)
        text = re.sub(rf"(?<![\w./-])([/$]){re.escape(original)}(?![\w-])",
                      lambda match: match[1] + alias, text)
    return text


def prepare_aliases(root):
    """Build editable-name views without changing any pinned upstream bytes."""
    from graphify_install import prepare_views
    prepare_views(root)
    for source, aliases in skill_aliases(root).items():
        if not aliases:
            continue
        upstream = root / "vendor" / source / "skills"
        view = root / ".tkstack" / source / "skills"
        if not upstream.is_dir():
            raise ValueError(f"Alias source is missing: {upstream}")
        for parent in (root / ".tkstack", view.parent, view):
            if parent.is_symlink():
                raise ValueError(f"Generated directory must not be a symlink: {parent}")
        for path in upstream.rglob("*"):
            destination = view / path.relative_to(upstream)
            if destination.is_symlink():
                raise ValueError(f"Unexpected link in generated directory: {destination}")
            if path.is_dir():
                destination.mkdir(parents=True, exist_ok=True)
                continue
            destination.parent.mkdir(parents=True, exist_ok=True)
            content = path.read_bytes()
            if path.suffix in (".md", ".yaml", ".yml"):
                content = rewrite_invocations(content.decode(), aliases).encode()
            if not destination.exists() or destination.read_bytes() != content:
                destination.write_bytes(content)
            destination.chmod(path.stat().st_mode & 0o777)
        # A source update must also remove deleted references from the view.
        for path in sorted(view.rglob("*"), key=lambda p: len(p.parts), reverse=True):
            if not (upstream / path.relative_to(view)).exists():
                path.rmdir() if path.is_dir() else path.unlink()


def source_directories(root, kind, harness=None):
    lock = root / "sources.lock.json"
    if lock.is_file():
        sources = json.loads(lock.read_text())["sources"]
    else:
        sources = {path.name: {} for path in (root / "vendor").glob("*") if path.is_dir()}
    result = []
    for name, source in sorted(sources.items()):
        if kind == "skills" and source.get("skill_templates"):
            from graphify_install import view_directory
            result.append((name, view_directory(root, name, harness)))
            continue
        paths = {**source.get("paths", {}), **source.get("harness_paths", {}).get(harness, {})}
        relative = paths.get(kind, kind)
        if relative is not None:
            result.append((name, root / "vendor" / name / relative))
    result.append((None, root / kind))
    return result


def collect(root, kind, harness=None):
    """Combine upstream and personal content, rejecting ambiguous names."""
    sources = source_directories(root, kind, harness)
    aliases_by_source = skill_aliases(root) if kind == "skills" else {}
    items = {}
    for source_name, directory in sources:
        aliases = aliases_by_source.get(source_name, {})
        candidates = ([directory / "graphify"] if kind == "skills" and source_name == "graphify" else
                      sorted(p.parent for p in directory.rglob("SKILL.md")) if kind == "skills" else
                      sorted(directory.glob("*.mdc" if kind == "rules" else "*.md")))
        missing = set(aliases) - {path.name for path in candidates}
        if missing:
            raise ValueError(f"Unknown alias skill in {directory}: {sorted(missing)}")
        for path in candidates:
            if kind == "agents" and path.name == "README.md":
                continue
            name = aliases.get(path.name, path.name)
            if name in items:
                raise ValueError(f"Duplicate {kind} name: {name}")
            if aliases and (path.name in aliases or rewrite_callers(root, source_name)):
                path = root / ".tkstack" / source_name / kind / path.relative_to(directory)
            items[name] = path.resolve()
    return items


def link_plan(root, target, harnesses):
    plan = []
    if harnesses and ((root / "skills/learn/SKILL.md").is_file() or (root / ".tkstack/steering").is_dir()):
        plan.append(((root / ".tkstack/steering").resolve(), target / ".agents/steering"))
    principles = root / "skills/tkstack-principles"
    if harnesses and (principles / "SKILL.md").is_file():
        plan.append((principles.resolve(), target / ".agents/principles"))
    for harness in harnesses:
        skills, agents = collect(root, "skills", harness), collect(root, "agents", harness)
        plan.extend((source, target / SKILL_PATHS[harness] / name)
                    for name, source in skills.items())
        if harness in AGENT_PATHS:
            plan.extend((source, target / AGENT_PATHS[harness] / name)
                        for name, source in agents.items())
        if harness == "cursor":
            plan.extend((source, target / ".cursor/rules" / name)
                        for name, source in collect(root, "rules", harness).items())
            for rule in sorted((root / "harnesses/cursor").glob("*.mdc")):
                plan.append((rule.resolve(), target / ".cursor/rules" / rule.name))
    return plan


def matches(destination, source):
    return destination.is_symlink() and destination.resolve() == source


def alias_migrations(root, target, harnesses):
    """Recognize only this checkout's former, unaliased upstream skill links."""
    migrations = {}
    steering = target / ".agents/steering"
    if harnesses and matches(steering, (root / "steering").resolve()):
        migrations[steering] = (root / "steering").resolve()
    for source, aliases in skill_aliases(root).items():
        for path in (root / "vendor" / source / "skills").rglob("SKILL.md"):
            if path.parent.name in aliases:
                for harness in harnesses:
                    migrations[target / SKILL_PATHS[harness] / path.parent.name] = path.parent.resolve()
    return migrations


def initialize_state(root, state_root=None):
    state_root = state_root or root / ".tkstack"
    import runner_install
    runner_install.plan(root, state_root)
    ensure_state(state_root)
    runner_install.publish(root, state_root)
    store = state_root / "steering"
    for skill, expected in (("learn", "rules.md"), ("unslop", "unslop/patterns.md")):
        script = root / "skills" / skill / "scripts" / (skill + ".py")
        if script.is_file() and not (store / expected).is_file():
            subprocess.run([sys.executable, str(script), "--store", str(store), "render"],
                           check=True, capture_output=True, text=True)


def preflight(plan, migrations=None):
    """Check every destination before creating links or generated source views."""
    for source, destination in plan:
        previous = (migrations or {}).get(destination)
        migrating = previous is not None and matches(destination, previous)
        if (destination.exists() or destination.is_symlink()) and not matches(destination, source) and not migrating:
            raise ValueError(f"Refusing to replace existing path: {destination}")
        for parent in destination.parents:
            if (parent.exists() or parent.is_symlink()) and not parent.is_dir():
                raise ValueError(f"Install directory is not a directory: {parent}")


def apply(plan, dry_run=False, uninstall=False, migrations=None):
    if not uninstall:
        preflight(plan, migrations)
    changes = 0
    for source, destination in plan:
        owned = matches(destination, source)
        if uninstall:
            if not owned:
                continue
            action = "remove"
        elif owned:
            continue
        else:
            previous = (migrations or {}).get(destination)
            migrating = previous is not None and matches(destination, previous)
            action = "migrate" if migrating else "link"
        print(f"{'Would ' if dry_run else ''}{action}: {destination}")
        if not dry_run:
            if uninstall:
                destination.unlink()
            else:
                destination.parent.mkdir(parents=True, exist_ok=True)
                if action == "migrate":
                    temporary = destination.with_name("." + destination.name + ".tkstack-next")
                    temporary.symlink_to(source, target_is_directory=True)
                    try:
                        if not matches(destination, previous):
                            raise ValueError(f"Link changed during installation: {destination}")
                        temporary.replace(destination)
                    finally:
                        temporary.unlink(missing_ok=True)
                else:
                    destination.symlink_to(source, target_is_directory=source.is_dir())
        changes += 1
    return changes


def main():
    os.environ.update(with_paths(ROOT))
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", type=Path, default=Path.home(),
                        help="Home or project root to install into (default: your home)")
    parser.add_argument("--harness", action="append", choices=tuple(SKILL_PATHS),
                        help="Harness to install; repeat to select several (default: all)")
    parser.add_argument("--dry-run", action="store_true", help="Preview without changing files")
    parser.add_argument("--uninstall", action="store_true", help="Remove only this checkout's links")
    parser.add_argument("--scope", choices=("home", "project"),
                        help="Instruction placement (default: home for your home directory, else project)")
    args = parser.parse_args()
    try:
        if not args.uninstall:
            verify_vendor(ROOT)
        harnesses = list(dict.fromkeys(args.harness or SKILL_PATHS))
        target = args.target.expanduser().resolve()
        scope = args.scope or ("home" if target == Path.home().resolve() else "project")
        plan = link_plan(ROOT, target, harnesses)
        migrations = alias_migrations(ROOT, target, harnesses)
        instructions = instruction_plan(ROOT, target, harnesses, scope, uninstall=args.uninstall)
        configurations = configuration_plan(ROOT, target, harnesses, scope, uninstall=args.uninstall)
        if not args.uninstall:
            preflight(plan, migrations)
            from runner_install import plan as runner_plan
            runner_plan(ROOT, ROOT / '.tkstack')
            if not args.dry_run:
                initialize_state(ROOT)
                prepare_aliases(ROOT)
        changes = apply(plan, dry_run=args.dry_run, uninstall=args.uninstall, migrations=migrations)
        apply_instructions(instructions, dry_run=args.dry_run)
        apply_configuration(configurations, dry_run=args.dry_run)
    except (OSError, ValueError, KeyError) as error:
        print(f"tkstack: {error}", file=sys.stderr)
        return 1
    print(f"{changes} link(s) {'would change' if args.dry_run else 'changed'}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

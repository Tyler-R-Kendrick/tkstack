#!/usr/bin/env python3
"""Link tkstack's pinned skills and agents into a home or project directory."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'src'))
import subprocess

from skill_roots import ADOPTED, nested, packages
import target_setup
from harness_paths import SKILL_DIRECTORIES, skill_directory


ROOT = Path(__file__).resolve().parent.parent
PLACEMENT = Path("skills/skills.json")
SKILL_PATHS = SKILL_DIRECTORIES
DEFAULT_HARNESSES = ("codex", "claude", "cursor")
LEGACY_SKILL_DIRECTORIES = (Path(".muse/skills"),)
ADOPTED_SOURCE = "adopted"
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


def _placement_doc(root):
    config = root / PLACEMENT
    loaded = json.loads(config.read_text()) if config.is_file() else {}
    return loaded if isinstance(loaded, dict) else {}


def skill_aliases(root):
    return _placement_doc(root).get("aliases", {})


def placement(rules, kind, source):
    """Personal skills are portable. Upstreams may specify host placement."""
    if source is None:
        return None
    if source in rules.get("sources", {}):
        return set(rules["sources"][source])
    return set(rules["default"]) if kind == "skills" and "default" in rules else None


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


def skill_view(root, source, harness=None):
    return root / ".tkstack/skill-views" / source / (harness or "default")


def _write_file(target, data):
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists() or target.read_bytes() != data:
        target.write_bytes(data)


def prepare_graphify(root):
    """Adapt upstream filenames into one discovery view per host."""
    lock_path = root / "sources.lock.json"
    if not lock_path.is_file():
        return
    templates = json.loads(lock_path.read_text())["sources"].get("graphify", {}).get("skill_templates", {})
    upstream = root / "vendor" / "graphify"
    for harness, profile in templates.items():
        directory = skill_view(root, "graphify", harness) / "graphify"
        files = {"SKILL.md": (upstream / profile["entrypoint"]).read_bytes()}
        references = upstream / profile["references"]
        files.update({"references/" + p.name: p.read_bytes() for p in references.glob("*.md")})
        for name in ("LICENSE", "LICENSE-MIT", "NOTICE"):
            source = upstream / name
            if source.is_file():
                files[name] = source.read_bytes()
        for name, data in files.items():
            target = directory / name
            target_setup.safe_path(target, root)
            _write_file(target, data)


def prepare_aliases(root, profile="catalog"):
    """Build editable-name views without changing any pinned upstream bytes."""
    if (root / "skills/learn/skills").is_dir():
        view = learn_view(root)
        target_setup.safe_path(view / "SKILL.md", root)
        _write_file(view / "SKILL.md", learn_index(root).encode())
    if profile != "catalog":
        return
    prepare_graphify(root)
    for source, aliases in skill_aliases(root).items():
        if not aliases:
            continue
        upstream = root / "vendor" / source / "skills"
        view = root / ".tkstack" / source / "skills"
        if not upstream.is_dir():
            raise ValueError(f"Alias source is missing: {upstream}")
        target_setup.safe_path(view, root)
        for path in upstream.rglob("*"):
            destination = view / path.relative_to(upstream)
            if destination.is_symlink():
                raise ValueError(f"Unexpected link in generated directory: {destination}")
            if path.is_dir():
                destination.mkdir(parents=True, exist_ok=True)
                continue
            content = path.read_bytes()
            if path.suffix in (".md", ".yaml", ".yml"):
                content = rewrite_invocations(content.decode(), aliases).encode()
            _write_file(destination, content)
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
            result.append((name, skill_view(root, name, harness)))
            continue
        paths = {**source.get("paths", {}), **source.get("harness_paths", {}).get(harness, {})}
        relative = paths.get(kind, kind)
        if relative is not None:
            result.append((name, root / "vendor" / name / relative))
    if kind == "skills":
        result.append((ADOPTED_SOURCE, root / ADOPTED))
    result.append((None, root / kind))
    return result


def collect(root, kind, harness=None):
    return {name: path for name, (_, path) in sourced(root, kind, harness).items()}


def sourced(root, kind, harness=None):
    config = _placement_doc(root)
    aliases_by_source = config.get("aliases", {}) if kind == "skills" else {}
    items = {}
    for source_name, directory in source_directories(root, kind, harness):
        aliases = aliases_by_source.get(source_name, {})
        candidates = ([directory / "graphify"] if kind == "skills" and source_name == "graphify" else
                      list(packages(root, ADOPTED).values()) if source_name == ADOPTED_SOURCE else
                      sorted(p.parent for p in directory.rglob("SKILL.md")
                             if source_name is not None or not nested(p.parent, directory)) if kind == "skills" else
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
            if aliases and (path.name in aliases or config.get("rewrite_callers", {}).get(source_name, True)):
                path = root / ".tkstack" / source_name / kind / path.relative_to(directory)
            items[name] = (source_name, path.resolve())
    return items


def placed(root, kind, harness):
    rules = _placement_doc(root).get("placement", {})
    return {name: path for name, (source, path) in sourced(root, kind, harness).items()
            if (harnesses := placement(rules, kind, source)) is None or harness in harnesses}


def harness_skill_directories(harness, scope="home"):
    scopes = ("home", "project") if scope is None else (scope,)
    return list(dict.fromkeys(path for item in scopes if (path := skill_directory(harness, item)) is not None))


def learn_view(root):
    return skill_view(root, "learn") / "learn"


def learn_index(root):
    package = root / "skills/learn"
    metadata = (package / "SKILL.md").read_text().split("---", 2)[1]
    return ("---" + metadata + "---\n\n# Learn\n\n"
            f"Read the canonical Learn index at <{package / 'SKILL.md'}>. "
            "Resolve its commands and reference paths from that directory. "
            "Use the installed tkstack runner for compiled commands.\n")


def link_plan(root, target, harnesses, scope="home", profile="catalog"):
    plan = []
    if harnesses and ((root / "skills/learn/SKILL.md").is_file() or (root / ".tkstack/steering").is_dir()):
        plan.append(((target / ".tkstack/steering").resolve(), target / ".agents/steering"))
    principles = root / "skills/tkstack-principles"
    if harnesses and (principles / "SKILL.md").is_file():
        plan.append((principles.resolve(), target / ".agents/principles"))
    profiles = _placement_doc(root).get("profiles", {})
    selected = set(profiles.get(profile, []))
    if profile != "catalog" and not selected:
        raise ValueError(f"Unknown installation profile: {profile}")
    for harness in harnesses:
        relatives = harness_skill_directories(harness, scope)
        if not relatives:
            continue
        skills = placed(root, "skills", harness)
        if profile != "catalog":
            skills = {name: path for name, path in skills.items() if name in selected}
        if "learn" in skills and (root / "skills/learn/skills").is_dir():
            skills["learn"] = learn_view(root)
        for relative in relatives:
            # A package committed at its own destination (self-install) needs no link.
            plan.extend((source, target / relative / name)
                        for name, source in skills.items()
                        if (target / relative).resolve() / name != source)
        if profile == "catalog" and harness in AGENT_PATHS:
            agents = placed(root, "agents", harness)
            plan.extend((source, target / AGENT_PATHS[harness] / name)
                        for name, source in agents.items())
        if harness == "cursor":
            plan.extend((source, target / ".cursor/rules" / name)
                        for name, source in placed(root, "rules", harness).items() if profile == "catalog")
            for rule in sorted((root / ".cursor/rules").glob("*.mdc")):
                destination = target / ".cursor/rules" / rule.name
                if rule.is_symlink() or destination == rule or (rule.name == "graphify.mdc" and profile != "catalog"):
                    continue
                plan.append((rule.resolve(), destination))
    # Project Muse shares Codex's .agents/skills, so the same link can be planned twice.
    if harnesses and (root / "src/tkstack.py").is_file():
        plan.append(((root / "src/tkstack.py").resolve(), target / ".tkstack/tkstack"))
    return list(dict.fromkeys(plan))


def matches(destination, source):
    return destination.is_symlink() and destination.resolve() == source


def stale_links(root, target, harnesses, plan, scope="home", installed=None):
    """Reconcile recorded links; recognize older installs by package name and source."""
    planned = {destination for _, destination in plan}
    directories = {path for host in harnesses for path in harness_skill_directories(host, scope)}
    directories.update(AGENT_PATHS[h] for h in harnesses if h in AGENT_PATHS)
    if "cursor" in harnesses:
        directories.add(Path(".cursor/rules"))
    legacy, stale = {}, []
    for relative in sorted(directories.union(LEGACY_SKILL_DIRECTORIES)):
        directory = target / relative
        if directory.is_symlink() or not directory.is_dir():
            continue
        target_setup.safe_path(directory, target)
        for path in sorted(directory.iterdir()):
            if not path.is_symlink() or path in planned:
                continue
            if installed is None:
                kind = relative.name
                if kind not in legacy:
                    legacy[kind] = collect(root, kind)
                source = legacy[kind].get(path.name)
            else:
                source = installed.get(path.relative_to(target).as_posix())
            if source and matches(path, Path(source)):
                stale.append(path)
    return stale


def remove_stale(paths, dry_run=False):
    for path in paths:
        print(f"{'Would ' if dry_run else ''}remove stale: {path}")
        if not dry_run:
            path.unlink()
    return len(paths)


# Cursor rules lived at harnesses/cursor/*.mdc before they moved to .cursor/rules.
LEGACY_CURSOR_RULES = Path("harnesses/cursor")


def alias_migrations(root, target, harnesses, scope="home"):
    """Identify known former sources before replacing an owned link."""
    migrations = {}
    steering = target / ".agents/steering"
    for old in (root / "steering", root / ".tkstack/steering"):
        if matches(steering, old.resolve()):
            migrations[steering] = old.resolve()
    for source, aliases in skill_aliases(root).items():
        for path in (root / "vendor" / source / "skills").rglob("SKILL.md"):
            if path.parent.name in aliases:
                for harness in harnesses:
                    for relative in harness_skill_directories(harness, scope):
                        migrations[target / relative / path.parent.name] = path.parent.resolve()
    if "cursor" in harnesses:
        for rule in (root / ".cursor/rules").glob("*.mdc"):
            if not rule.is_symlink():
                migrations[target / ".cursor/rules" / rule.name] = (root / LEGACY_CURSOR_RULES / rule.name).resolve()
    return migrations


def preflight(plan, migrations=None):
    """Check every destination before creating links or generated source views."""
    for source, destination in plan:
        migrating = matches(destination, (migrations or {}).get(destination))
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
        previous = (migrations or {}).get(destination)
        migrating = matches(destination, previous)
        owned = matches(destination, source)
        if uninstall:
            if not owned and not migrating:
                continue
            action = "remove"
        elif owned:
            continue
        else:
            action = "migrate" if migrating else "link"
        print(f"{'Would ' if dry_run else ''}{action}: {destination}")
        if not dry_run:
            if uninstall:
                destination.unlink()
            else:
                destination.parent.mkdir(parents=True, exist_ok=True)
                if action == "migrate":
                    temporary = destination.with_name("." + destination.name + ".tkstack-next")
                    temporary.symlink_to(source, target_is_directory=source.is_dir())
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


def _delegates(root):
    raw = _placement_doc(root).get("delegates")
    if not isinstance(raw, dict):
        return {}
    return {name: targets for name, targets in raw.items()
            if isinstance(name, str) and name not in SKILL_DIRECTORIES and isinstance(targets, list)}


def expand_harnesses(root, names):
    declared = _delegates(root)
    expanded = []
    for name in names:
        targets = declared.get(name, [name])
        if not targets or any(not isinstance(item, str) or item not in SKILL_DIRECTORIES for item in targets):
            raise ValueError(f"{name} delegates must name harnesses this installer links")
        expanded.extend(targets)
    return list(dict.fromkeys(expanded))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", type=Path,
                        help="Home or project root to install into (default: your home)")
    parser.add_argument("--harness", action="append",
                        choices=tuple(dict.fromkeys((*SKILL_PATHS, *_delegates(ROOT)))),
                        help="Harness to install; t3code installs delegates.t3code (default: codex, claude, cursor)")
    parser.add_argument("--serena-command", action="store_true",
                        help="Print native MCP stdio settings for this project and an installed Serena, then exit")
    parser.add_argument("--index-serena", action="store_true",
                        help="Index the explicit project using a host-provisioned Serena executable")
    parser.add_argument("--profile", choices=("personal", "development", "design", "catalog"),
                        help="Skill selection for a fresh install (existing profile is retained)")
    parser.add_argument("--adopt", action="store_true", help="Initialize project-owned Constrain policy")
    parser.add_argument("--constraint-hook", action="store_true", help="Enable the staged constraint gate in this project's default Git hook")
    parser.add_argument("--status", action="store_true", help="Show target and optional integration readiness without activation")
    parser.add_argument("--dry-run", action="store_true", help="Preview without changing files")
    parser.add_argument("--uninstall", action="store_true",
                        help="Remove this checkout's target configuration for every harness")
    parser.add_argument("--scope", choices=("home", "project"),
                        help="Home or project skill directories (default: home for your home directory, else project)")
    parser.add_argument("--check", action="store_true", help="Verify target links and instructions without writing")
    args = parser.parse_args()
    if (args.check or args.status) and (args.dry_run or args.uninstall):
        parser.error("--check cannot combine with --dry-run or --uninstall")
    try:
        if not args.uninstall:
            verify_vendor(ROOT)
        target = (args.target or Path.home()).expanduser().resolve()
        receipt = target / ".tkstack/install.json"
        target_setup.safe_path(receipt, target)
        saved = target_setup.read_install(receipt, ROOT)
        scope = args.scope or saved.get("scope") or ("home" if target == Path.home().resolve() else "project")
        if saved and scope != saved["scope"]:
            raise ValueError("Uninstall using the existing scope before changing it")
        external_project = args.target and scope == "project" and target not in (ROOT, Path.home().resolve())
        if args.serena_command or args.index_serena:
            if args.uninstall or args.check or args.status or not external_project or not target.is_dir():
                raise ValueError("Serena requires an existing external --target project")
            executable = shutil.which("serena")
            if not executable:
                raise ValueError("Serena needs a host-provisioned serena executable on PATH")
            if args.serena_command:
                print(json.dumps({"command": executable, "args": ["start-mcp-server", "--project", str(target)]}, indent=2))
            if args.index_serena:
                argv = [executable, "project", "index", str(target)]
                if args.dry_run:
                    print(json.dumps(argv))
                else:
                    subprocess.run(argv, cwd=target, check=True)
            return 0
        if (args.adopt or args.constraint_hook) and not external_project:
            raise ValueError("Project adoption requires an external Git project target")
        legacy = matches(target / ".agents/principles", ROOT / "skills/tkstack-principles")
        profile = args.profile or saved.get("profile") or ("catalog" if target == ROOT or legacy else "personal")
        requested = args.harness or saved.get("harnesses") or DEFAULT_HARNESSES
        harnesses = list(SKILL_PATHS) if args.uninstall else expand_harnesses(ROOT, requested)
        link_scope = None if args.uninstall else scope
        plan = link_plan(ROOT, target, harnesses, link_scope, "catalog" if args.uninstall else profile)
        for _, dest in plan:
            target_setup.safe_path(dest.parent, target)
        target_setup.safe_path(target / ".tkstack/steering/rules.md", target)
        migrations = alias_migrations(ROOT, target, harnesses, link_scope)
        for source, destination in plan:
            if source == learn_view(ROOT):
                migrations[destination] = ROOT / "skills/learn"
        previous = set(saved.get("harnesses", []))
        instruction_plan = target_setup.instruction_changes(ROOT, target, harnesses, scope, args.uninstall, previous)
        stale = stale_links(ROOT, target, set(harnesses) | previous, plan, link_scope, saved.get("links"))
        if scope == "project" and target != ROOT:
            instruction_plan += target_setup.git_excludes(target, plan, remove=args.uninstall)
        hook = args.constraint_hook or saved.get("constraint_hook", False)
        adopted = args.adopt or hook or saved.get("adopted", False)
        if adopted and not args.uninstall:
            instruction_plan += target_setup.adoption(target)
        if hook and (not args.uninstall or saved.get("constraint_hook")):
            instruction_plan += target_setup.constraint_hook(target, remove=args.uninstall)
        record = {"source": str(ROOT), "profile": profile, "scope": scope,
                  "harnesses": harnesses, "constraint_hook": hook, "adopted": adopted,
                  "links": {dest.relative_to(target).as_posix(): str(src) for src, dest in plan}}
        before = receipt.read_text() if receipt.exists() else None
        after = None if args.uninstall else json.dumps(record, indent=2) + "\n"
        if before != after:
            instruction_plan.append((receipt, before, after))
        print(f"tkstack source: {ROOT}\ntkstack target: {target} ({scope})")
        if args.status:
            target_setup.status(target, ROOT, profile)
        if args.check or args.status:
            if stale:
                raise ValueError(f"Stale installed link: {stale[0]}")
            if any(src == learn_view(ROOT) for src, _ in plan):
                view = learn_view(ROOT) / "SKILL.md"
                if not view.is_file() or view.read_text() != learn_index(ROOT):
                    raise ValueError("Learn discovery view needs setup")
            target_setup.verify(plan, instruction_plan)
            if adopted:
                return subprocess.run([sys.executable, "-B", str(ROOT / "skills/constrain/scripts/constrain.py"), "check", "--repo", str(target)]).returncode
            return 0
        if not args.uninstall and not args.dry_run:
            preflight(plan, migrations)
            prepare_aliases(ROOT, profile)
            from tkstack_state import ensure_state
            ensure_state(target / ".tkstack/steering")
            if not (target / ".tkstack/steering/rules.md").is_file():
                subprocess.run([sys.executable, str(ROOT / "skills/learn/scripts/learn.py"),
                                "--project", str(target), "render"], check=True, capture_output=True, text=True)
        changes = apply(plan, dry_run=args.dry_run, uninstall=args.uninstall, migrations=migrations)
        changes += remove_stale(stale, dry_run=args.dry_run)
        target_setup.apply_instructions(instruction_plan, dry_run=args.dry_run)
        if not args.uninstall and not args.dry_run:
            target_setup.verify(plan, [])
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
        print(f"tkstack: {error}", file=sys.stderr)
        return 1
    print(f"{changes} link(s) {'would change' if args.dry_run else 'changed'}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

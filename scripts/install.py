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
from harness_paths import SKILL_DIRECTORIES, skill_directory


ROOT = Path(__file__).resolve().parent.parent
PLACEMENT = Path("skills/skills.json")
SKILL_PATHS = SKILL_DIRECTORIES
DEFAULT_HARNESSES = ("codex", "claude", "cursor")
# Releases before Muse moved to ~/.config/muse/skills linked .muse/skills.
LEGACY_SKILL_DIRECTORIES = (Path(".muse/skills"),)
# Committed third-party-derived packages; they install like a harness-independent source.
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
    """Load skills/skills.json once per call. Missing or non-object files are empty."""
    config = root / PLACEMENT
    if not config.is_file():
        return {}
    loaded = json.loads(config.read_text())
    return loaded if isinstance(loaded, dict) else {}


def skill_aliases(root):
    return _placement_doc(root).get("aliases", {})


def rewrite_callers(root, source):
    return _placement_doc(root).get("rewrite_callers", {}).get(source, True)


def placement(rules, kind, source):
    """Harnesses that receive a source's content; None means every selected harness.

    Personal content joins every selected harness. Other skills use
    placement.default when kind is "skills", unless placement.sources names
    that source. An absent default means every selected harness.
    """
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
    """Directory of one host's generated skill view. The view is not upstream bytes."""
    return root / ".tkstack/skill-views" / source / (harness or "default")


def _write_file(target, data):
    """Create parent directories and replace the file when its bytes differ."""
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists() or target.read_bytes() != data:
        target.write_bytes(data)


def _git_checked(root, *args):
    """Run git and raise ValueError instead of a CalledProcessError traceback."""
    try:
        subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as error:
        detail = (error.stderr or "").strip()
        raise ValueError(detail or "git " + " ".join(args) + " failed") from None


def prepare_graphify(root):
    """Copy each Graphify host skill into a view named SKILL.md.

    Upstream ships skill markdown under other filenames. The copy is the file
    the host reads. It does not rewrite commands or install a private runtime.
    """
    lock_path = root / "sources.lock.json"
    if not lock_path.is_file():
        return
    record = json.loads(lock_path.read_text()).get("sources", {}).get("graphify")
    templates = record.get("skill_templates") if isinstance(record, dict) else None
    if not templates:
        return
    upstream = root / "vendor" / "graphify"
    for harness, profile in templates.items():
        directory = skill_view(root, "graphify", harness) / "graphify"
        files = {"SKILL.md": (upstream / profile["entrypoint"]).read_bytes()}
        references = upstream / profile["references"]
        if references.is_dir():
            for path in sorted(references.glob("*.md")):
                files["references/" + path.name] = path.read_bytes()
        for name in ("LICENSE", "LICENSE-MIT", "NOTICE"):
            source = upstream / name
            if source.is_file():
                files[name] = source.read_bytes()
        for name, data in files.items():
            target = directory / name
            if target.is_symlink() or any(parent.is_symlink() for parent in target.parents if root in parent.parents):
                raise ValueError("Graphify view must not be a symlink: " + str(target))
            _write_file(target, data)


def prepare_aliases(root):
    """Build editable-name views without changing any pinned upstream bytes."""
    prepare_graphify(root)
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
    """Combine upstream and personal content, rejecting ambiguous names."""
    return {name: path for name, (_, path) in sourced(root, kind, harness).items()}


def sourced(root, kind, harness=None):
    """Map each collected name to its source (None for personal) and path."""
    sources = source_directories(root, kind, harness)
    aliases_by_source = skill_aliases(root) if kind == "skills" else {}
    items = {}
    for source_name, directory in sources:
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
            if aliases and (path.name in aliases or rewrite_callers(root, source_name)):
                path = root / ".tkstack" / source_name / kind / path.relative_to(directory)
            items[name] = (source_name, path.resolve())
    return items


def placed(root, kind, harness):
    """Collected items that belong in one harness's native directory."""
    rules = _placement_doc(root).get("placement", {})
    return {name: path for name, (source, path) in sourced(root, kind, harness).items()
            if (harnesses := placement(rules, kind, source)) is None or harness in harnesses}


def harness_skill_directories(harness, scope="home"):
    """Skill directories this installer links.

    scope None scans home and project. Uninstall uses that so a project
    Copilot, Muse, or OpenCode link is removed with the home link.
    """
    if scope is None:
        found = []
        for scope_name in ("home", "project"):
            relative = skill_directory(harness, scope_name)
            if relative is not None and relative not in found:
                found.append(relative)
        return found
    relative = skill_directory(harness, scope)
    return [] if relative is None else [relative]


def link_plan(root, target, harnesses, scope="home"):
    plan = []
    if harnesses and ((root / "skills/learn/SKILL.md").is_file() or (root / ".tkstack/steering").is_dir()):
        plan.append(((root / ".tkstack/steering").resolve(), target / ".agents/steering"))
    principles = root / "skills/tkstack-principles"
    if harnesses and (principles / "SKILL.md").is_file():
        plan.append((principles.resolve(), target / ".agents/principles"))
    for harness in harnesses:
        relatives = harness_skill_directories(harness, scope)
        if not relatives:
            continue
        skills, agents = placed(root, "skills", harness), placed(root, "agents", harness)
        for relative in relatives:
            # A package committed at its own destination (self-install) needs no link.
            plan.extend((source, target / relative / name)
                        for name, source in skills.items()
                        if (target / relative).resolve() / name != source)
        if harness in AGENT_PATHS:
            plan.extend((source, target / AGENT_PATHS[harness] / name)
                        for name, source in agents.items())
        if harness == "cursor":
            plan.extend((source, target / ".cursor/rules" / name)
                        for name, source in placed(root, "rules", harness).items())
            rules = root / ".cursor/rules"
            if rules.is_dir():
                for rule in sorted(rules.glob("*.mdc")):
                    if rule.is_symlink():
                        continue
                    destination = target / ".cursor/rules" / rule.name
                    if destination.resolve() == rule.resolve():
                        continue
                    plan.append((rule.resolve(), destination))
    # Project Muse shares Codex's .agents/skills, so the same link can be planned twice.
    unique = []
    seen = set()
    for item in plan:
        if item in seen:
            continue
        seen.add(item)
        unique.append(item)
    return unique


def matches(destination, source):
    return destination.is_symlink() and destination.resolve() == source


def stale_links(root, target, harnesses, plan, scope="home"):
    """This checkout's links in native directories that the plan no longer places."""
    planned = {destination for _, destination in plan}
    directories = []
    for harness in harnesses:
        directories.extend(harness_skill_directories(harness, scope))
    directories += [AGENT_PATHS[h] for h in harnesses if h in AGENT_PATHS]
    if "cursor" in harnesses:
        directories.append(Path(".cursor/rules"))
    directories.extend(LEGACY_SKILL_DIRECTORIES)
    root = root.resolve()
    stale = []
    for relative in directories:
        directory = target / relative
        if directory.is_symlink() or not directory.is_dir():
            continue
        for path in sorted(directory.iterdir()):
            if path.is_symlink() and path not in planned and \
                    (directory / os.readlink(path)).resolve().is_relative_to(root):
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
    """Former links this checkout owns: steering, skill aliases, and Cursor rules.

    A destination whose symlink still points at the previous source can be
    replaced on install and removed on uninstall. A foreign target cannot.
    """
    migrations = {}
    steering = target / ".agents/steering"
    if harnesses and matches(steering, (root / "steering").resolve()):
        migrations[steering] = (root / "steering").resolve()
    for source, aliases in skill_aliases(root).items():
        for path in (root / "vendor" / source / "skills").rglob("SKILL.md"):
            if path.parent.name in aliases:
                for harness in harnesses:
                    for relative in harness_skill_directories(harness, scope):
                        migrations[target / relative / path.parent.name] = path.parent.resolve()
    if harnesses and "cursor" in harnesses:
        rules = root / ".cursor" / "rules"
        if rules.is_dir():
            for rule in sorted(rules.glob("*.mdc")):
                if rule.is_symlink():
                    continue
                migrations[target / ".cursor" / "rules" / rule.name] = (
                    root / LEGACY_CURSOR_RULES / rule.name
                ).resolve()
    return migrations


SERENA_FROM = "git+https://github.com/oraios/serena"


def serena_steps(project):
    """Official uvx launch from oraios/serena, then init and project index.

    Both commands use `project` as their working directory. `serena init`
    selects the language-server backend and also writes Serena's user-global
    config (`~/.serena/serena_config.yml`); the working directory does not
    move that file. `serena project index` receives `project` as its
    `[PROJECT]` path so it does not fall back to the caller's directory.
    Home scope indexes this checkout. Project scope indexes the install
    target. Neither step indexes the user's home directory.
    """
    launch = ["uvx", "--from", SERENA_FROM, "serena"]
    return (
        (launch + ["init"], project),
        (launch + ["project", "index", str(project)], project),
    )


def _run_serena(argv, cwd):
    return subprocess.run(argv, cwd=cwd, capture_output=True, text=True)


def initialize_serena(root, target, scope, dry_run=False, runner=None, which=None):
    """Index Serena's project. Skip when uvx is missing or a command fails.

    `--dry-run` prints the commands and does not execute them. A missing uvx,
    or a non-zero exit (including an offline uvx fetch), prints a skip line
    and leaves the rest of install in place. `uv` alone is not enough.
    """
    project = target if scope == "project" else root
    steps = serena_steps(project)
    if dry_run:
        for argv, cwd in steps:
            where = f" in {cwd}" if cwd is not None else ""
            print("Would run" + where + ": " + " ".join(argv))
        return 0
    which = shutil.which if which is None else which
    if which("uv") is None and which("uvx") is None:
        print("skip serena: uv is not on PATH")
        return 0
    if which("uvx") is None:
        print("skip serena: uvx is not on PATH")
        return 0
    runner = _run_serena if runner is None else runner
    for argv, cwd in steps:
        where = f" (cwd {cwd})" if cwd is not None else ""
        print("run: " + " ".join(argv) + where)
        try:
            completed = runner(argv, None if cwd is None else str(cwd))
        except OSError as error:
            print(f"skip serena: {error}")
            return 0
        if completed.returncode != 0:
            print(f"skip serena: {' '.join(argv)} exited {completed.returncode}")
            return 0
    return 0


def repo_hooks(root, dry_run=False, uninstall=False):
    """Use .githooks for this checkout. Git then ignores .git/hooks."""
    try:
        probe = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--is-inside-work-tree"],
            capture_output=True, text=True,
        )
    except FileNotFoundError:
        print("skip git docs hook: not a git checkout")
        return
    if probe.returncode != 0:
        print("skip git docs hook: not a git checkout")
        return
    shown = subprocess.run(
        ["git", "-C", str(root), "config", "--get", "core.hooksPath"],
        capture_output=True, text=True,
    )
    current = shown.stdout.strip()
    if uninstall:
        if current != ".githooks":
            print("skip git docs hook: core.hooksPath is not .githooks")
            return
        print(("Would unset" if dry_run else "unset") + " core.hooksPath")
        if not dry_run:
            _git_checked(root, "config", "--unset", "core.hooksPath")
        return
    if current == ".githooks":
        return
    print(("Would set" if dry_run else "set") + " core.hooksPath=.githooks")
    if not dry_run:
        _git_checked(root, "config", "core.hooksPath", ".githooks")


def _owned_previous(destination, migrations):
    """The former source when this checkout's link still points at it."""
    previous = (migrations or {}).get(destination)
    if previous is not None and matches(destination, previous):
        return previous
    return None


def preflight(plan, migrations=None):
    """Check every destination before creating links or generated source views."""
    for source, destination in plan:
        migrating = _owned_previous(destination, migrations) is not None
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
        previous = _owned_previous(destination, migrations)
        owned = matches(destination, source)
        if uninstall:
            if not owned and previous is None:
                continue
            action = "remove"
        elif owned:
            continue
        else:
            action = "migrate" if previous is not None else "link"
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", type=Path, default=Path.home(),
                        help="Home or project root to install into (default: your home)")
    parser.add_argument("--harness", action="append", choices=tuple(SKILL_PATHS),
                        help="Harness to install; repeat to select several (default: codex, claude, cursor)")
    parser.add_argument("--dry-run", action="store_true", help="Preview without changing files")
    parser.add_argument("--uninstall", action="store_true",
                        help="Remove this checkout's links for every harness and its docs hook")
    parser.add_argument("--scope", choices=("home", "project"),
                        help="Home or project skill directories (default: home for your home directory, else project)")
    args = parser.parse_args()
    try:
        if not args.uninstall:
            verify_vendor(ROOT)
        selected = list(dict.fromkeys(args.harness or DEFAULT_HARNESSES))
        target = args.target.expanduser().resolve()
        scope = args.scope or ("home" if target == Path.home().resolve() else "project")
        if args.uninstall:
            harnesses = list(SKILL_PATHS)
            link_scope = None
            if args.harness:
                print("tkstack: --uninstall removes this checkout's links for every harness; --harness does not limit it.",
                      file=sys.stderr)
        else:
            harnesses = selected
            link_scope = scope
        plan = link_plan(ROOT, target, harnesses, link_scope)
        migrations = alias_migrations(ROOT, target, harnesses, link_scope)
        if not args.uninstall:
            preflight(plan, migrations)
            if not args.dry_run:
                prepare_aliases(ROOT)
        changes = apply(plan, dry_run=args.dry_run, uninstall=args.uninstall, migrations=migrations)
        changes += remove_stale(stale_links(ROOT, target, harnesses, plan, link_scope), dry_run=args.dry_run)
        repo_hooks(ROOT, dry_run=args.dry_run, uninstall=args.uninstall)
        if args.uninstall:
            print("skip serena: uninstall")
        else:
            initialize_serena(ROOT, target, scope, dry_run=args.dry_run)
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
        print(f"tkstack: {error}", file=sys.stderr)
        return 1
    print(f"{changes} link(s) {'would change' if args.dry_run else 'changed'}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

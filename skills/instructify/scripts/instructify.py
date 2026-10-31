#!/usr/bin/env python3
"""Plan and apply scoped, owned instruction sections with optimistic checks."""

import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
sys.dont_write_bytecode = True
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tkstack_state import ensure_state, state_path


TARGETS = {"agents", "claude", "cursor", "copilot"}
ENTRY_FIELDS = {"id", "when", "instruction", "verification", "boundary", "source"}


def digest(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def unique_fields(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON field: {key}")
        result[key] = value
    return result


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique_fields)


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", value) or len(value) > 64:
        raise ValueError("IDs must be lowercase kebab-case within 64 characters")
    return value


def line(value):
    if not isinstance(value, str) or not value.strip() or value != value.strip() or any(c in value for c in "\r\n\x00"):
        raise ValueError("Instruction fields must be nonempty single lines without surrounding whitespace")
    if "<!--" in value or len(value) > 4096:
        raise ValueError("Instruction fields must be concise and cannot contain HTML ownership markers")
    return value


def relative(value):
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        raise ValueError("Use explicit project-relative POSIX paths")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or any(p in (".git", "vendor", ".tkstack") for p in path.parts):
        raise ValueError("Path escapes the owned project scope")
    return str(path)


def contained(project, value):
    name = relative(value)
    path = project / name
    for component in (path, *path.parents):
        if component == project:
            break
        if component.is_symlink():
            raise ValueError(f"Refusing a symlinked instruction/manifest path: {path}")
        if component != path and component.exists() and not component.is_dir():
            raise ValueError(f"Instruction parent is not a directory: {component}")
    if not path.resolve().is_relative_to(project):
        raise ValueError("Path escapes project")
    return path


def validate(manifest):
    if set(manifest) != {"version", "id", "title", "scope", "targets", "instructions"} or type(manifest["version"]) is not int or manifest["version"] != 1:
        raise ValueError("Manifest requires version 1, id, title, scope, targets, and instructions")
    identifier(manifest["id"])
    line(manifest["title"])
    relative(manifest["scope"])
    if any(c in manifest["scope"] for c in "*?[]{}!,"):
        raise ValueError("Scope must be a literal directory without glob metacharacters")
    targets = manifest["targets"]
    if not isinstance(targets, list) or not targets or any(t not in TARGETS for t in targets) or len(set(targets)) != len(targets):
        raise ValueError("Select distinct targets: agents, claude, cursor, copilot")
    entries = manifest["instructions"]
    if not isinstance(entries, list) or not 1 <= len(entries) <= 64:
        raise ValueError("Supply 1 to 64 scoped instructions")
    ids = set()
    for entry in entries:
        if set(entry) != ENTRY_FIELDS:
            raise ValueError("Each instruction requires id, when, instruction, verification, boundary, and source")
        identity = identifier(entry["id"])
        if identity in ids:
            raise ValueError("Instruction IDs must be unique")
        ids.add(identity)
        for key in ENTRY_FIELDS - {"id"}:
            line(entry[key])
    return manifest


def body(manifest):
    lines = [f"## {manifest['title']}", "", f"Scope: {relative(manifest['scope'])} (relative to the project root).", ""]
    for entry in sorted(manifest["instructions"], key=lambda e: e["id"]):
        lines.extend([f"### {entry['id']}", "", f"When: {entry['when']}",
            f"Do: {entry['instruction']}", f"Verify: {entry['verification']}",
            f"Boundary: {entry['boundary']}", f"Source: {entry['source']}", ""])
    return "\n".join(lines)


def imports_agents(content):
    content = re.sub(r"(?s)<!-- instructify:([a-z0-9-]+):start -->.*?<!-- instructify:\1:end -->\n?", "", content)
    content = re.sub(r"(?s)<!--.*?-->", "", content)
    fence = None
    for text in content.splitlines():
        match = re.match(r"^\s{0,3}(`{3,}|~{3,})", text)
        if match:
            if fence is None:
                fence = match[1]
            elif match[1][0] == fence[0] and len(match[1]) >= len(fence):
                fence = None
        elif fence is None and text.strip() == "@AGENTS.md":
            return True
    return False


def owned_section(before, identity, owner, content, header=None, remove=False):
    start = f"<!-- instructify:{identity}:start -->"
    end = f"<!-- instructify:{identity}:end -->\n"
    before_text = before if before is not None else ""
    if before_text.count(start) != before_text.count(end) or before_text.count(start) > 1:
        raise ValueError("Malformed or duplicate instructify markers")
    if start not in before_text:
        if remove:
            return before
        if header is not None and before is not None:
            raise ValueError("Dedicated native rule file already exists and is not owned by this manifest")
        prefix = before_text if header is None else header
        separator = "\n" if prefix and not prefix.endswith("\n") else ""
        prefix += separator
        suffix = ""
        created = before is None
    else:
        left, right = before_text.index(start), before_text.index(end)
        if right < left:
            raise ValueError("Instruction end marker precedes start")
        prefix, suffix = before_text[:left], before_text[right + len(end):]
        section = before_text[left + len(start):right]
        match = re.fullmatch(r'\n<!-- instructify:meta (.+) -->\n(.*)', section, re.S)
        if not match:
            raise ValueError("Malformed instruction ownership metadata")
        metadata = json.loads(match[1], object_pairs_hook=unique_fields)
        if set(metadata) != {"owner", "sha256", "created", "separator"} or type(metadata["created"]) is not bool or metadata["separator"] not in ("", "\n"):
            raise ValueError("Invalid instruction ownership metadata")
        if metadata["owner"] != owner:
            raise ValueError("Instruction section belongs to another manifest")
        old_body = match[2]
        protected_header = prefix if header is not None else ""
        if metadata["sha256"] != digest(protected_header + old_body):
            raise ValueError("Owned instruction content/header changed; reconcile manual edits before replacing")
        created, separator = metadata["created"], metadata["separator"]
        if remove:
            if header is not None:
                after = prefix + suffix if suffix else ""
            else:
                if separator:
                    if not prefix.endswith(separator):
                        raise ValueError("Owned instruction separator changed")
                    prefix = prefix[:-len(separator)]
                after = prefix + suffix
            return None if created and not after else after
        if header is not None:
            prefix = header
    protected_header = prefix if header is not None else ""
    metadata = {"owner": owner, "sha256": digest(protected_header + content),
                "created": created, "separator": separator}
    return prefix + start + "\n<!-- instructify:meta " + json.dumps(metadata, sort_keys=True) + " -->\n" + content + end + suffix


def build_plan(project, manifest_path, remove=False):
    project = project.resolve()
    if not project.is_dir():
        raise ValueError("Project must be an existing directory")
    manifest_path = contained(project, manifest_path.absolute().relative_to(project).as_posix())
    manifest = validate(read_json(manifest_path))
    scope = relative(manifest["scope"])
    scope_path = contained(project, scope)
    if scope_path.exists() and not scope_path.is_dir():
        raise ValueError("Instruction scope must be a directory")
    snapshots, changes = {}, []
    def read(path):
        name = path.relative_to(project).as_posix()
        checked = contained(project, name)
        if checked.exists() and not checked.is_file():
            raise ValueError(f"Instruction destination is not a file: {checked}")
        data = checked.read_bytes() if checked.exists() else None
        snapshots[name] = hashlib.sha256(data).hexdigest() if data is not None else None
        return data.decode("utf-8") if data is not None else None
    read(manifest_path)
    owner = digest(manifest_path.relative_to(project).as_posix() + "\n" + manifest["id"])[:24]
    text = body(manifest)
    bindings = []
    if "agents" in manifest["targets"]:
        override = read(scope_path / "AGENTS.override.md")
        if override:
            raise ValueError("A nonempty AGENTS.override.md shadows AGENTS.md; reconcile the active instruction source first")
        bindings.append((scope_path / "AGENTS.md", None, text))
    if "claude" in manifest["targets"]:
        claude = scope_path / "CLAUDE.md"
        existing = read(claude)
        if "agents" not in manifest["targets"]:
            bindings.append((claude, None, text))
        elif not imports_agents(existing or ""):
            bindings.append((claude, None, "@AGENTS.md\n"))
        elif f"<!-- instructify:{manifest['id']}:start -->" in (existing or ""):
            bindings.append((claude, None, "@AGENTS.md\n"))
    if "cursor" in manifest["targets"]:
        header = "---\ndescription: " + json.dumps(manifest["title"]) + "\n"
        if scope != ".":
            header += "globs: " + json.dumps(scope + "/**/*") + "\nalwaysApply: false\n"
        else:
            header += "alwaysApply: true\n"
        bindings.append((project / ".cursor/rules" / ("instructify-" + manifest["id"] + ".mdc"), header + "---\n\n", text))
    if "copilot" in manifest["targets"]:
        if scope == ".":
            bindings.append((project / ".github/copilot-instructions.md", None, text))
        else:
            header = "---\napplyTo: " + json.dumps(scope + "/**/*") + "\n---\n\n"
            bindings.append((project / ".github/instructions" / ("instructify-" + manifest["id"] + ".instructions.md"), header, text))
    for path, header, content in sorted(bindings, key=lambda item: str(item[0])):
        before = read(path)
        after = owned_section(before, manifest["id"], owner, content, header, remove)
        if before != after:
            changes.append({"path": path.relative_to(project).as_posix(), "before": before, "after": after})
    return {"version": 1, "project": str(project), "manifest": manifest_path.relative_to(project).as_posix(),
            "remove": remove, "inputs": dict(sorted(snapshots.items())), "changes": changes}


@contextmanager
def writer(project):
    lock = ensure_state(state_path("locks", project)) / "instructify.lock"
    try:
        lock.mkdir()
    except FileExistsError as error:
        raise ValueError("Instruction project is busy; retry after its writer finishes") from error
    try:
        yield
    finally:
        lock.rmdir()


def atomic_write(path, content):
    if content is None:
        path.unlink()
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else None
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".instructify-", delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(content.encode("utf-8"))
            handle.flush()
            os.fsync(handle.fileno())
        if mode is not None:
            temporary.chmod(mode)
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def apply(project, proposed, dry_run=False):
    project = project.resolve()
    if proposed.get("project") != str(project) or type(proposed.get("remove")) is not bool:
        raise ValueError("Plan project/mode does not match")
    def verify():
        current = build_plan(project, contained(project, proposed["manifest"]), proposed["remove"])
        if current != proposed:
            raise ValueError("Plan is stale or modified; review a fresh plan")
        return current
    if dry_run:
        return {"changed": len(verify()["changes"]), "dry_run": True}
    with writer(project):
        current = verify()
        completed = []
        try:
            for change in current["changes"]:
                atomic_write(contained(project, change["path"]), change["after"])
                completed.append(change)
        except OSError as error:
            gaps = []
            for change in reversed(completed):
                try:
                    path = contained(project, change["path"])
                    actual = path.read_bytes().decode("utf-8") if path.exists() else None
                    if actual != change["after"]:
                        gaps.append(change["path"])
                        continue
                    atomic_write(path, change["before"])
                except (OSError, ValueError):
                    gaps.append(change["path"])
            raise ValueError(f"Apply failed: {error}; rollback gaps: {gaps}") from error
    return {"changed": len(current["changes"]), "dry_run": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("plan", "check", "apply"):
        child = sub.add_parser(command)
        child.add_argument("--project", type=Path, required=True)
        if command == "apply":
            child.add_argument("--plan", type=Path, required=True)
            child.add_argument("--dry-run", action="store_true")
        else:
            child.add_argument("--input", type=Path, required=True)
            if command == "plan":
                child.add_argument("--remove", action="store_true")
    args = parser.parse_args()
    try:
        if args.command == "apply":
            result = apply(args.project, read_json(args.plan), args.dry_run)
        else:
            result = build_plan(args.project, args.input, getattr(args, "remove", False))
            if args.command == "check":
                result = {"aligned": not result["changes"], "pending_paths": [c["path"] for c in result["changes"]],
                          "limits": "File alignment and ownership only; native loading and semantic compliance require actual evidence."}
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 2 if args.command == "check" and not result["aligned"] else 0
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
        print(f"instructify: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

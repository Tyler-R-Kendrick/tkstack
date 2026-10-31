#!/usr/bin/env python3
"""Scaffold owned skills and validate a portable, deliberately narrow format."""

import argparse
import importlib.util
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
sys.dont_write_bytecode = True
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tkstack_state import ensure_state, state_path, project_root


PACKAGE = Path(__file__).resolve().parent.parent
NAME = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
_engine_spec = importlib.util.spec_from_file_location("skillify_codify", PACKAGE / "scripts/codify_runtime/scripts/codify.py")
codify = importlib.util.module_from_spec(_engine_spec)
_engine_spec.loader.exec_module(codify)
BACKENDS = codify.authoring.BACKENDS
workflow_files = codify.authoring.workflow_files
from skill_normalize import normalize


def package_resources(directory):
    """Read owned source without descending into installed dependencies/cache."""
    for parent, directories, files in os.walk(directory, followlinks=False):
        directories[:] = sorted(name for name in directories if name not in ("node_modules", "__pycache__", ".git", ".tkstack"))
        for name in sorted([*directories, *files]):
            yield Path(parent) / name


def without_fences(content):
    lines, fence = [], None
    for line in content.splitlines():
        match = re.match(r"^\s{0,3}(`{3,}|~{3,})", line)
        if match:
            marker = match[1]
            if fence is None:
                fence = marker
            elif marker[0] == fence[0] and len(marker) >= len(fence):
                fence = None
            continue
        if fence is None:
            lines.append(line)
    return "\n".join(lines)


def metadata(content):
    lines = content.splitlines()
    if not lines or lines[0] != "---":
        raise ValueError("SKILL.md requires YAML frontmatter")
    try:
        end = lines.index("---", 1)
    except ValueError as error:
        raise ValueError("Frontmatter is not closed") from error
    result = {}
    for line in lines[1:end]:
        if not line.strip() or line.startswith("#") or line[0].isspace():
            continue
        match = re.fullmatch(r"([a-z][a-z0-9-]*):(?:\s+(.*))?", line)
        if not match:
            raise ValueError("Use top-level key: value frontmatter in this portable profile")
        key, raw = match[1], match[2] or ""
        if key in result:
            raise ValueError(f"Duplicate frontmatter key: {key}")
        if raw.startswith('"'):
            value = json.loads(raw)
        elif raw.startswith("'"):
            if not raw.endswith("'"):
                raise ValueError("Unclosed quoted frontmatter")
            value = raw[1:-1].replace("''", "'")
        elif raw in ("|", ">", ">-", "|-", "|+", ">+") or ": " in raw:
            raise ValueError("Use a single JSON-quoted scalar; this validator is not a general YAML parser")
        elif raw in ("true", "false", "null") or re.fullmatch(r"-?\d+(?:\.\d+)?", raw):
            value = json.loads(raw)
        elif raw.startswith(("[", "{", "#", "&", "*", "!", "@", "`", "~")):
            raise ValueError("Use a JSON-quoted string for non-plain scalar values")
        else:
            value = raw
        result[key] = value
    return result, "\n".join(lines[end + 1:])


def validate(directory, require_tool=False, entrypoint=None):
    directory = directory.resolve()
    info, body = metadata((directory / "SKILL.md").read_text())
    name, description = info.get("name"), info.get("description")
    if not isinstance(name, str) or not NAME.fullmatch(name) or len(name) > 64 or name != directory.name:
        raise ValueError("Name must match the directory and be kebab-case, at most 64 characters")
    if not isinstance(description, str) or not description.strip() or len(description) > 1024:
        raise ValueError("Description must be nonempty text of at most 1024 characters")
    if not body.strip() or "TODO(SKILLIFY):" in without_fences(body):
        raise ValueError("Complete the scaffold procedure before validation")
    if not (directory / "LICENSE").is_file():
        raise ValueError("Distributable owned packages require a bundled LICENSE")
    resources = 0
    for path in package_resources(directory):
        if not path.resolve().is_relative_to(directory):
            raise ValueError(f"Resource escapes the standalone package: {path}")
        if not path.is_file():
            continue
        resources += 1
        if path.suffix == ".py":
            ast.parse(path.read_text(), filename=str(path))
        if path.suffix == ".md":
            prose = without_fences(path.read_text())
            if "TODO(SKILLIFY):" in prose:
                raise ValueError(f"Complete the scaffold reference before validation: {path.name}")
            for target in re.findall(r"\]\(([^)\s]+)\)", prose):
                if re.match(r"[a-zA-Z][a-zA-Z0-9+.-]*:", target) or target.startswith("#"):
                    continue
                relative = target.split("#", 1)[0]
                resolved = (path.parent / relative).resolve()
                if not resolved.is_relative_to(directory) or not resolved.exists():
                    raise ValueError(f"Missing or external package reference in {path.name}: {target}")
    tool = None
    command_definitions = codify.command_schema.catalog(directory)
    if require_tool:
        candidates = [directory / entrypoint] if entrypoint else [directory / "scripts/run.py", directory / "scripts/run.ts"]
        candidates = [path for path in candidates if path.is_file()]
        if len(candidates) != 1 or not candidates[0].resolve().is_relative_to(directory / "scripts"):
            raise ValueError("Provide one existing tool entrypoint contained in scripts/")
        tool = str(candidates[0].relative_to(directory))
        definition = directory / "scripts" / ("workflow" + candidates[0].suffix)
        if definition.is_file() and "WORKFLOW_NOT_IMPLEMENTED" in definition.read_text():
            raise ValueError("Implement the executable workflow before tool validation")
    return {"name": name, "resources": resources, "status": "structurally-valid", "tool_entrypoint": tool,
            "commands": len(command_definitions),
            "limits": "Restricted single-line frontmatter and inline-link profile; no semantic, trigger, behavioral, or full YAML/CommonMark validation."}


def scaffold(target, name, description, backend="python"):
    if not NAME.fullmatch(name) or len(name) > 64 or target.name != name:
        raise ValueError("Target directory must match the kebab-case skill name")
    if not description.strip() or len(description) > 1024:
        raise ValueError("Description must have 1 to 1024 characters")
    template = (PACKAGE / "templates/SKILL.md.tmpl").read_text()
    files = workflow_files(backend, description)
    suffix, runtime = BACKENDS[backend]
    values = {"@NAME@": json.dumps(name), "@DESCRIPTION@": json.dumps(description),
              "@TITLE@": name.replace("-", " ").capitalize(), "@ENTRYPOINT@": f"scripts/run.{suffix}",
              "@COMMAND@": f"{runtime} scripts/run.{suffix} --input /path/to/input.json"}
    content = re.sub(r"@[A-Z_]+@", lambda match: values.get(match[0], match[0]), template)
    files.update({"SKILL.md": content.encode(), "LICENSE": (PACKAGE / "LICENSE").read_bytes()})
    for topic in ("inputs", "procedure", "verification"):
        files[f"references/{topic}.md"] = (PACKAGE / "templates" / (topic + ".md.tmpl")).read_bytes()
    target.mkdir(parents=True, exist_ok=False)
    try:
        for name, data in files.items():
            path = target / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
    except OSError:
        shutil.rmtree(target)
        raise
    return {"path": str(target), "status": "draft", "backend": backend,
            "next": "Implement scripts/workflow, complete the tool interface/index/references, execute real cases, then check --require-tool."}


def convert(directory, backend="python", dry_run=False):
    """Seed an executable migration, retaining the exact Markdown as authoring input."""
    directory = directory.resolve(strict=True)
    path = directory / "SKILL.md"
    if path.is_symlink() or not (directory / "LICENSE").is_file():
        raise ValueError("Convert an owned regular package with its actual LICENSE")
    before = path.read_bytes()
    info, _ = metadata(before.decode())
    if info.get("name") != directory.name or not isinstance(info.get("description"), str):
        raise ValueError("Convert a matching owned skill in the supported profile")
    files = workflow_files(backend, info["description"])
    files["references/source-skill.txt"] = before
    for name in files:
        destination = directory / name
        if destination.exists() or destination.is_symlink():
            raise FileExistsError(f"Conversion preserves existing files; adapt explicitly: {name}")
        if not destination.resolve().is_relative_to(directory):
            raise ValueError("Conversion resource escapes the package")
        for parent in destination.parents:
            if parent == directory:
                break
            if parent.is_symlink() or (parent.exists() and not parent.is_dir()):
                raise ValueError("Conversion requires real package directories")
    lines = before.decode().splitlines(keepends=True)
    suffix, runtime = BACKENDS[backend]
    end = next(index for index in range(1, len(lines)) if lines[index].strip() == "---")
    after = "".join(lines[:end + 1]) + f"\n# {info['name']}\n\n" + (
        "Use this skill as an intermediary code-mode prompt: select the tool,\n"
        "supply its inputs, run it, and inspect its output. Execution belongs in\n"
        "`scripts/`, not in repeated interpretation of Markdown.\n\n"
        f"From this skill directory, invoke `{runtime} scripts/run.{suffix} --input /path/to/input.json`.\n"
        f"[Tool entrypoint](scripts/run.{suffix}); full setup and parameters below.\n\n"
        "| Topic | Read when needed |\n| --- | --- |\n"
        "| Invoke, input/output, errors, dependencies | [Tool interface](references/tool.md) |\n"
        "| Default/help, deterministic console rendering, or man(1) source | [Reserved help](commands/help.md) |\n"
        "| Declared package version without execution | [Reserved version](commands/version.md) |\n"
        "| Workflow parameters and compiled invocation | [Run](commands/run.md) |\n"
        "| Subcommands, aliases, flags, and tool-call schemas | [Command contract](references/subcommands.md) |\n"
        "| Preserved intermediate authoring input; not executable instructions | [Original source](references/source-skill.txt) |\n")
    result = {"status": "planned" if dry_run else "workflow-draft", "backend": backend,
              "source_sha256": hashlib.sha256(before).hexdigest(), "files": sorted(files),
              "next": "Port the real behavior into scripts/workflow, finish the tool contract, run native cases, then check --require-tool."}
    if dry_run:
        return result
    lock_id = hashlib.sha256(str(directory).encode()).hexdigest()[:16]
    lock = ensure_state(state_path("locks", project_root(directory)) / "skillify") / (lock_id + ".lock")
    lock.mkdir()
    created, parents = [], set()
    temporary = None
    try:
        if path.read_bytes() != before:
            raise ValueError("Skill source changed before conversion")
        for name, data in files.items():
            destination = directory / name
            if not destination.parent.exists():
                destination.parent.mkdir()
                parents.add(destination.parent)
            staged = None
            try:
                with tempfile.NamedTemporaryFile(dir=destination.parent, prefix=".skillify-", delete=False) as output:
                    staged = Path(output.name)
                    output.write(data)
                os.link(staged, destination)  # Atomic, exclusive publication on the same filesystem.
                created.append((destination, data))
            finally:
                if staged is not None:
                    staged.unlink(missing_ok=True)
        with tempfile.NamedTemporaryFile(dir=directory, prefix=".skillify-", delete=False) as output:
            temporary = Path(output.name)
            output.write(after.encode())
        temporary.chmod(path.stat().st_mode & 0o777)
        if path.read_bytes() != before:
            raise ValueError("Skill source changed during conversion")
        temporary.replace(path)
        temporary = None
        return result
    except (OSError, ValueError):
        for destination, data in reversed(created):
            if destination.is_file() and not destination.is_symlink() and destination.read_bytes() == data:
                destination.unlink()
        for parent in sorted(parents, reverse=True):
            if parent.is_dir() and not any(parent.iterdir()):
                parent.rmdir()
        raise
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        lock.rmdir()


def compile_skill(directory, cases, entrypoint=None, profiles=(), dry_run=False, dependencies=None, jobs=4,
                  config=None, project=None, timeout=30, includes=()):
    directory = directory.resolve(strict=True)
    validate(directory, require_tool=True, entrypoint=entrypoint)
    selected = directory / entrypoint if entrypoint else next(path for path in (directory / "scripts/run.py", directory / "scripts/run.ts") if path.is_file())
    source = directory / "references/source-skill.txt"
    if not source.is_file():
        source = directory / "SKILL.md"
    includes = includes or ([directory] if (directory / 'scripts/contract.json').is_file() else [])
    return codify.compile_workflow(source, selected, cases, output=directory / "scripts/workflow.lock.json",
                                   root=directory, profiles=profiles, dry_run=dry_run, dependencies=dependencies, jobs=jobs,
                                   config=config, project=project, timeout=timeout, includes=includes)


def main():
    if len(sys.argv) > 1 and sys.argv[1] in ('commands', 'invoke'):
        return codify.main(sys.argv[1:])
    parser = argparse.ArgumentParser(description=__doc__, epilog=
        'Shared subcommand interface: commands <directory> [--format index|responses|chat]; '
        'invoke <directory> [--call <json>] [-- <command> [arguments]].')
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("check")
    check.add_argument("directory", type=Path)
    check.add_argument("--require-tool", action="store_true")
    check.add_argument("--entrypoint", help="Package-relative executable in scripts/ (requires --require-tool)")
    create = sub.add_parser("scaffold")
    create.add_argument("--target", type=Path, required=True)
    create.add_argument("--name", required=True)
    create.add_argument("--description", required=True)
    create.add_argument("--backend", choices=tuple(BACKENDS), default="python")
    migration = sub.add_parser("convert")
    migration.add_argument("directory", type=Path)
    migration.add_argument("--backend", choices=tuple(BACKENDS), default="python")
    migration.add_argument("--dry-run", action="store_true")
    compiler = sub.add_parser("compile", help="Compile a completed skill through the bundled Codify engine")
    compiler.add_argument("directory", type=Path)
    compiler.add_argument("--cases", type=Path, required=True)
    compiler.add_argument("--entrypoint")
    compiler.add_argument("--profile", dest="profiles", action="append", default=[])
    compiler.add_argument("--dry-run", action="store_true")
    compiler.add_argument("--dependencies", type=Path)
    compiler.add_argument("--jobs", type=int, default=4)
    compiler.add_argument("--config", type=Path)
    compiler.add_argument("--project", type=Path)
    compiler.add_argument("--timeout", type=int, default=30)
    compiler.add_argument("--include", type=Path, action="append", default=[])
    normalizer = sub.add_parser("normalize", help="Add the shared contract/model/native interface to an existing owned skill")
    normalizer.add_argument("directory", type=Path)
    normalizer.add_argument("--profile", type=Path, required=True)
    normalizer.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    try:
        if args.command == "normalize":
            result = normalize(args.directory, args.profile, codify, args.dry_run)
        elif args.command == "check":
            if args.entrypoint and not args.require_tool:
                raise ValueError("--entrypoint requires --require-tool")
            result = validate(args.directory, args.require_tool, args.entrypoint)
        elif args.command == "compile":
            result = compile_skill(args.directory, args.cases, args.entrypoint, args.profiles,
                                   args.dry_run, args.dependencies, args.jobs, args.config, args.project, args.timeout, args.include)
        elif args.command == "convert":
            result = convert(args.directory, args.backend, args.dry_run)
        else:
            result = scaffold(args.target, args.name, args.description, args.backend)
        print(json.dumps(result, indent=2))
        return 0
    except (OSError, ValueError, TypeError, SyntaxError) as error:
        print(f"skillify: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

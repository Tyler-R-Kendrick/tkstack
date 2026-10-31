#!/usr/bin/env python3
"""Scaffold existing workflow DSLs; separate inspection from native validation."""

import argparse
from contextlib import redirect_stdout
import hashlib
import importlib.util
import importlib.metadata
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import sys
sys.dont_write_bytecode = True


PACKAGE = Path(__file__).resolve().parent.parent
TEMPLATES = {
    "maf": ("workflow.yaml.tmpl", "bindings.py", "run.py", "requirements.txt", "requirements.lock", "inputs.json", "README.md.tmpl"),
    "rhai": ("workflow.rhai.tmpl", "inputs.json", "README.md.tmpl"),
}


def load_maf(path):
    try:
        import yaml
    except ImportError as error:
        raise RuntimeError("MAF source inspection requires PyYAML 6.x") from error
    class UniqueLoader(yaml.SafeLoader):
        pass
    def mapping(loader, node):
        result = {}
        for key_node, value_node in node.value:
            key = loader.construct_object(key_node)
            if not isinstance(key, str) or key in result:
                raise ValueError("YAML mapping keys must be unique strings")
            result[key] = loader.construct_object(value_node)
        return result
    UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, mapping)
    raw = path.read_bytes()
    if len(raw) > 1024 * 1024:
        raise ValueError("Workflow definition exceeds the 1 MiB inspection limit")
    try:
        definition = yaml.load(raw, Loader=UniqueLoader)
    except yaml.YAMLError as error:
        raise ValueError(f"Invalid workflow YAML: {error}") from error
    seen = set()
    def walk(value):
        if isinstance(value, (list, dict)):
            if id(value) in seen:
                raise ValueError("Use explicit YAML values; aliases/cycles are outside this inspection profile")
            seen.add(id(value))
            for child in value.values() if isinstance(value, dict) else value:
                walk(child)
        elif type(value) is float and not math.isfinite(value):
            raise ValueError("Non-finite values are not supported")
        elif value is not None and type(value) not in (str, int, float, bool):
            raise ValueError("Use JSON-compatible YAML values")
    walk(definition)
    return definition


def inspect_source(backend, path):
    raw = path.read_bytes()
    if not raw or len(raw) > 1024 * 1024:
        raise ValueError("Provide a nonempty workflow definition up to 1 MiB")
    receipt = {"backend": backend, "sha256": hashlib.sha256(raw).hexdigest(),
               "native_validated": False, "executed": False}
    if backend == "rhai":
        raw.decode("utf-8")
        return {**receipt, "status": "source-recorded",
                "limits": "No Rhai parser was run. Compilation and Grok host validation are still required."}
    definition = load_maf(path)
    if not isinstance(definition, dict) or not isinstance(definition.get("name"), str) or not definition["name"].strip():
        raise ValueError("MAF inspection profile requires a nonempty workflow name")
    actions = definition.get("actions")
    if actions is None and isinstance(definition.get("trigger"), dict):
        actions = definition["trigger"].get("actions")
    if not isinstance(actions, list) or not actions:
        raise ValueError("Provide actions or trigger.actions as a nonempty list")
    ids, kinds = set(), set()
    def visit(items):
        for action in items:
            if not isinstance(action, dict) or not isinstance(action.get("kind"), str) or not action["kind"]:
                raise ValueError("Each action requires a kind")
            identity = action.get("id")
            if not isinstance(identity, str) or not identity or identity in ids:
                raise ValueError("This profile requires distinct explicit action IDs")
            ids.add(identity)
            kinds.add(action["kind"])
            for key in ("actions", "then", "else", "elseActions"):
                if key in action:
                    if not isinstance(action[key], list):
                        raise ValueError(f"{key} must be an action list in this inspection profile")
                    visit(action[key])
            conditions = action.get("conditions", [])
            if not isinstance(conditions, list):
                raise ValueError("conditions must be a list in this inspection profile")
            for condition in conditions:
                if isinstance(condition, dict) and "actions" in condition:
                    if not isinstance(condition["actions"], list):
                        raise ValueError("Condition actions must be a list")
                    visit(condition["actions"])
    visit(actions)
    return {**receipt, "status": "source-inspected", "name": definition["name"],
            "action_ids": sorted(ids), "action_kinds": sorted(kinds),
            "limits": "Basic authoring profile only; not full MAF schema, Power Fx, binding, graph, or execution validation."}


def native_check(backend, path, grok_source=None):
    receipt = inspect_source(backend, path)
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != receipt["sha256"]:
        raise ValueError("Workflow source changed during inspection; retry from a stable revision")
    if backend == "maf":
        if importlib.util.find_spec("agent_framework_declarative") is None:
            return {**receipt, "status": "runtime-unavailable", "required": "agent-framework-declarative==1.4.0 and its native dependencies"}, 3
        from agent_framework_declarative import WorkflowFactory
        workflow = WorkflowFactory().create_workflow_from_yaml(raw.decode("utf-8"), base_path=path.parent)
        return {**receipt, "status": "native-graph-built", "name": workflow.name,
                "runtime_version": importlib.metadata.version("agent-framework-declarative"),
                "native_validated": True,
                "limits": "Native graph construction only. Project bindings, inputs, effects, and final outcomes still need execution tests."}, 0
    cargo = shutil.which("cargo")
    if cargo is None or grok_source is None:
        return {**receipt, "status": "runtime-unavailable", "required": "Rust/Cargo and an explicit Grok source checkout with cached dependencies"}, 3
    source = grok_source.resolve()
    example = source / "crates/codegen/xai-workflow/examples/validate.rs"
    if not example.is_file():
        raise ValueError("Grok checkout does not contain the reviewed xai-workflow validator")
    command = [cargo, "run", "--offline", "--locked", "--manifest-path", str(source / "Cargo.toml"),
               "-p", "xai-workflow", "--example", "validate"]
    result = subprocess.run(command, input=raw.decode("utf-8"), text=True, capture_output=True, timeout=60)
    return {**receipt, "status": "native-mock-validated" if result.returncode == 0 else "native-check-failed",
            "native_validated": result.returncode == 0, "validator_sha256": hashlib.sha256(example.read_bytes()).hexdigest(),
            "command": command, "returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr,
            "limits": "Upstream validator executes with stub inputs/host responses; not production agent/tool/effect validation."}, 0 if result.returncode == 0 else 2


def scaffold(backend, target, name):
    if backend not in TEMPLATES:
        raise ValueError("Choose an existing backend: maf or rhai")
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name) or len(name) > 64 or target.name != name:
        raise ValueError("Target directory must match a kebab-case workflow name within 64 characters")
    source = PACKAGE / "templates" / backend
    target.mkdir(parents=True, exist_ok=False)
    created = []
    try:
        for filename in TEMPLATES[backend]:
            template = source / filename
            destination = target / template.name.removesuffix(".tmpl")
            created.append(destination)
            destination.write_text(template.read_text().replace("@WORKFLOW_NAME@", name))
        license_path = target / "LICENSE"
        created.append(license_path)
        shutil.copyfile(PACKAGE / "LICENSE", license_path)
    except OSError:
        for path in created:
            path.unlink(missing_ok=True)
        target.rmdir()
        raise
    return {"status": "source-created", "backend": backend, "path": str(target),
            "files": [p.name for p in created], "native_validated": False, "executed": False,
            "next": "Adapt the runnable example to the actual requested procedure, install/lock its runtime, then validate and execute its real cases."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("scaffold", "inspect", "check"):
        child = sub.add_parser(command)
        child.add_argument("--backend", choices=("maf", "rhai"), required=True)
        if command == "scaffold":
            child.add_argument("--target", type=Path, required=True)
            child.add_argument("--name", required=True)
        else:
            child.add_argument("--file", type=Path, required=True)
            if command == "check":
                child.add_argument("--grok-source", type=Path)
    args = parser.parse_args()
    try:
        status = 0
        if args.command == "scaffold":
            result = scaffold(args.backend, args.target, args.name)
        elif args.command == "inspect":
            result = inspect_source(args.backend, args.file)
        else:
            with redirect_stdout(sys.stderr):
                result, status = native_check(args.backend, args.file, args.grok_source)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return status
    except Exception as error:
        print(f"flowify: {type(error).__name__}: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

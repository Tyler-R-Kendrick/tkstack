#!/usr/bin/env python3
"""Configure native hooks and MCP servers; download runtimes only when requested."""

import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import shlex
import shutil
import subprocess
import sys
sys.dont_write_bytecode = True
import tarfile
import tomllib
import urllib.request

from tool import runtime_path
from runtime_environment import with_paths
from harness_paths import codex_directory
from tkstack_state import ensure_state


ROOT = Path(__file__).resolve().parent.parent
BEGIN, END = "# tkstack:mcp:start", "# tkstack:mcp:end"


def ready(root, name):
    manifest = json.loads((root / "harnesses/integrations.json").read_text())
    tool = manifest["tools"].get(name, {})
    if tool.get("kind") == "vendored-node":
        return bool(shutil.which("node") and (root / tool["source"] / tool["entrypoint"]).is_file())
    if tool.get("kind") == "locked-python":
        from python_runtime import package_ready
        return package_ready(root, name, tool)
    if tool.get("kind") == "npm":
        from npm_runtime import package_ready
        return package_ready(root, name, tool)
    if name == "wikiskill":
        return (root / "vendor/wikiskill/wikiskill/cli.py").is_file()
    try:
        path = runtime_path(root, name)
        return bool(path and path.is_file() and os.access(path, os.X_OK))
    except ValueError:
        return False


def hook_entries(root, harness, repo_docs=False):
    def command(integration, event):
        return shlex.join([sys.executable, str(root / "scripts/run_hook.py"), integration, harness, event])

    result = {}
    def add(event, integration, operation, matcher=None):
        leaf = {"type": "command", "command": command(integration, operation), "timeout": 45}
        if harness == "cursor":
            item = {"command": leaf["command"], "timeout": 45}
            if matcher:
                item["matcher"] = matcher
        else:
            item = {"hooks": [leaf]}
            if matcher:
                item["matcher"] = matcher
        result.setdefault(event, []).append(item)

    if harness == "cursor":
        add("sessionStart", "ponytail", "activate")
        add("sessionStart", "caveman", "activate")
        add("beforeSubmitPrompt", "ponytail", "prompt")
        add("preToolUse", "rtk", "rewrite")
        add("postToolUse", "impeccable", "detect", "^Write$")
    else:
        add("SessionStart", "ponytail", "activate", "startup|resume|clear|compact")
        add("SessionStart", "caveman", "activate", "startup|resume" if harness == "codex" else None)
        if harness == "claude":
            add("SubagentStart", "caveman", "subagent")
            add("UserPromptSubmit", "caveman", "prompt")
            add("SessionEnd", "caveman", "record")
        add("UserPromptSubmit", "ponytail", "prompt")
        add("SubagentStart", "ponytail", "subagent")
        add("PreToolUse", "rtk", "rewrite", "Bash")
        if harness == "claude" and ready(root, "graphify"):
            add("PreToolUse", "graphify", "search", "Bash|Grep")
            add("PreToolUse", "graphify", "read", "Read|Glob")
        if harness == "claude":
            add("SessionStart", "impeccable", "detect")
        add("PostToolUse", "impeccable", "detect", "Edit|Write|apply_patch")
        add("Stop", "impeccable", "detect")
    if repo_docs:
        add('stop' if harness == 'cursor' else 'Stop', 'repo-docs', 'check')
        if harness == 'cursor':
            result['stop'][-1]['loop_limit'] = 1
    return result


def mcp_entries(root, manifest, harness):
    result = {}
    for name, server in manifest["mcp"].items():
        if server.get("tool") and not ready(root, server["tool"]):
            continue
        headers = server.get("env_headers", {})
        if any(not os.environ.get(variable) for variable in headers.values()):
            continue
        if server["type"] == "http":
            item = {"url": server["url"]}
            if harness == "claude":
                item["type"] = "http"
            if headers:
                if harness == "codex":
                    item["env_http_headers"] = headers
                else:
                    item["headers"] = {key: ("${env:" + value + "}" if harness == "cursor"
                                              else "${" + value + "}") for key, value in headers.items()}
        else:
            arguments = server.get("args_by_harness", {}).get(harness, server["args"])
            item = {"command": sys.executable,
                    "args": [str(root / "scripts/tool.py"), server["tool"], *arguments]}
        result[name] = item
    return result


def owned_hook(item, root):
    return str(root / "scripts/run_hook.py") in json.dumps(item)


def merge_servers(document, desired, previous, uninstall):
    servers = document.setdefault("mcpServers", {})
    owned = {}
    for name, old in previous.items():
        if servers.get(name) == old:
            del servers[name]
    if not uninstall:
        for name, entry in desired.items():
            if name in servers:
                if servers[name] != entry:
                    raise ValueError(f"Existing MCP server differs: {name}")
                continue  # An identical pre-existing entry stays user-owned.
            servers[name] = entry
            owned[name] = entry
    return owned


def codex_toml(before, entries, uninstall):
    if before.count(BEGIN) != before.count(END) or before.count(BEGIN) > 1:
        raise ValueError("Malformed tkstack MCP markers")
    if BEGIN in before:
        start, end = before.index(BEGIN), before.index(END) + len(END)
        if end <= start:
            raise ValueError("Malformed tkstack MCP markers")
        if before[end:end + 1] == "\n":
            end += 1
        base = before[:start] + before[end:]
    else:
        base = before
    parsed = tomllib.loads(base)
    lines = [BEGIN]
    if not uninstall:
        for name, fields in entries.items():
            existing = parsed.get("mcp_servers", {}).get(name)
            if existing is not None:
                if existing != fields:
                    raise ValueError(f"Existing Codex MCP server differs: {name}")
                continue
            lines.extend([f"[mcp_servers.{name}]"])
            for key, value in fields.items():
                if isinstance(value, dict):
                    value = "{ " + ", ".join(json.dumps(k) + " = " + json.dumps(v) for k, v in value.items()) + " }"
                else:
                    value = json.dumps(value)
                lines.append(f"{key} = {value}")
            lines.append("")
    if len(lines) == 1:
        return base
    lines.append(END)
    after = base + ("\n" if base and not base.endswith("\n") else "") + "\n".join(lines) + "\n"
    tomllib.loads(after)
    return after


def configuration_plan(root, target, harnesses, scope, uninstall=False):
    manifest_path = root / "harnesses/integrations.json"
    if not manifest_path.is_file():
        return []
    manifest = json.loads(manifest_path.read_text())
    key = hashlib.sha256(str(target).encode()).hexdigest()[:16]
    state_path = root / ".tkstack/integration-installs" / (key + ".json")
    state = json.loads(state_path.read_text()) if state_path.exists() else {"servers": {}}
    documents = {}
    originals = {}
    def document(path):
        if path not in documents:
            before = path.read_text(encoding="utf-8") if path.exists() else ""
            originals[path] = before
            documents[path] = json.loads(before) if before else {}
        return documents[path]

    new_state = {"servers": dict(state.get("servers", {}))}
    changes = []
    for harness in harnesses:
        desired = mcp_entries(root, manifest, harness)
        if harness == "codex":
            path = codex_directory(target, scope) / "config.toml"
            before = path.read_text(encoding="utf-8") if path.exists() else ""
            after = codex_toml(before, desired, uninstall)
            if before != after:
                changes.append((path, before, after))
        else:
            path = target / (".cursor/mcp.json" if harness == "cursor" else
                             ".claude.json" if scope == "home" else ".mcp.json")
            new_state["servers"][str(path)] = merge_servers(
                document(path), desired, state.get("servers", {}).get(str(path), {}), uninstall)
        path = (codex_directory(target, scope) / "hooks.json" if harness == "codex" else
                target / {"claude": ".claude/settings.json", "cursor": ".cursor/hooks.json"}[harness])
        current = document(path)
        hooks = current.setdefault("hooks", {})
        for event, items in list(hooks.items()):
            hooks[event] = [item for item in items if not owned_hook(item, root)]
            if not hooks[event]:
                del hooks[event]
        if not uninstall:
            repo_docs = scope == 'project' and (root / 'docs/docs-policy.json').is_file() and target.resolve() == root.resolve()
            for event, entries in hook_entries(root, harness, repo_docs).items():
                hooks.setdefault(event, []).extend(entries)
            if harness == "cursor":
                current.setdefault("version", 1)
    for path, value in documents.items():
        after = json.dumps(value, indent=2) + "\n"
        if originals[path] != after:
            changes.append((path, originals[path], after))
    before = state_path.read_text() if state_path.exists() else ""
    after = json.dumps(new_state, indent=2) + "\n"
    if before != after:
        changes.append((state_path, before, after))
    return changes


def apply_configuration(changes, dry_run=False):
    for path, before, _ in changes:
        current = path.read_text(encoding="utf-8") if path.exists() else ""
        if current != before:
            raise ValueError(f"Configuration changed during installation: {path}")
    for path, _, after in changes:
        print(f"{'Would update' if dry_run else 'Updated'} integration config: {path}")
        if not dry_run:
            if ".tkstack" in path.parts:
                ensure_state(path.parent)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(after, encoding="utf-8")
    return len(changes)


def install_runtimes(root, names=None):
    manifest = json.loads((root / "harnesses/integrations.json").read_text())
    if names and set(names) - manifest["tools"].keys():
        raise ValueError("Unknown runtime: " + ", ".join(sorted(set(names) - manifest["tools"].keys())))
    ensure_state(root / ".tkstack/runtime")
    machine = platform.machine().lower()
    machine = {"arm64": "aarch64", "amd64": "x86_64"}.get(machine, machine)
    target = platform.system().lower() + "-" + machine
    for name, tool in manifest["tools"].items():
        if names and name not in names:
            continue
        if tool["kind"] in ("external", "vendored-python", "vendored-node") or ready(root, name):
            continue
        if tool["kind"] == "locked-python":
            from python_runtime import install as install_python
            install_python(root, name, tool)
            continue
        if tool["kind"] == "npm":
            from npm_runtime import install as install_npm
            install_npm(root, name, tool)
            continue
        asset = tool["platforms"].get(target)
        if not asset:
            raise ValueError(f"No pinned {name} runtime for {target}")
        with urllib.request.urlopen(asset["url"], timeout=60) as response:
            data = response.read()
        if hashlib.sha256(data).hexdigest() != asset["sha256"]:
            raise ValueError("Runtime checksum mismatch: " + name)
        if tool["kind"] == "archive":
            with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
                members = [member for member in archive.getmembers()
                           if member.isfile() and Path(member.name).name == asset["archive_member"]]
                if len(members) != 1:
                    raise ValueError("Runtime archive does not contain one expected binary: " + name)
                data = archive.extractfile(members[0]).read()
        path = runtime_path(root, name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        path.chmod(0o755)
        print(f"Installed {name} {tool['version']} with verified download checksum")


def status(root):
    manifest = json.loads((root / "harnesses/integrations.json").read_text())
    result = {name: {"runtime": "available" if ready(root, name) else "missing",
                     "version": tool.get("version")} for name, tool in manifest["tools"].items()}
    result["ponytail"] = {"runtime": "available" if shutil.which("node") else "node-missing", "version": "5.3.3"}
    result["fal"] = {"connection": "OAuth sign-in required or managed by the host; not verified here"}
    result["stitch"] = {"credential_environment": "present" if os.environ.get("STITCH_API_KEY") else "missing"}
    return result


def main():
    os.environ.update(with_paths(ROOT))
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", type=Path, default=Path.home())
    parser.add_argument("--harness", action="append", choices=("codex", "claude", "cursor"))
    parser.add_argument("--scope", choices=("home", "project"))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--uninstall", action="store_true")
    parser.add_argument("--install-runtimes", action="store_true")
    parser.add_argument("--runtimes-only", action="store_true", help="Install selected runtimes without applying host configuration")
    parser.add_argument("--runtime", action="append", help="Limit --install-runtimes to named tools (repeatable)")
    parser.add_argument("--status", action="store_true")
    args = parser.parse_args()
    try:
        if args.runtimes_only and not args.install_runtimes:
            raise ValueError("--runtimes-only requires --install-runtimes")
        if args.status:
            print(json.dumps(status(ROOT), indent=2))
            return 0
        if args.install_runtimes:
            if args.dry_run or args.uninstall:
                raise ValueError("--install-runtimes requires an actual installation")
            install_runtimes(ROOT, args.runtime)
            if args.runtimes_only:
                return 0
        elif args.runtime:
            raise ValueError("--runtime requires --install-runtimes")
        target = args.target.expanduser().resolve()
        scope = args.scope or ("home" if target == Path.home().resolve() else "project")
        changes = configuration_plan(ROOT, target, args.harness or ["codex", "claude", "cursor"], scope, args.uninstall)
        apply_configuration(changes, args.dry_run)
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        print(f"tkstack integrations: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

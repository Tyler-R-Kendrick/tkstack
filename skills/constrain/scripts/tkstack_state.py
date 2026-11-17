"""Portable tkstack state paths and private-data ignore policy (bundled unchanged in skills)."""

import os
from pathlib import Path
import re
import tempfile
import time
import argparse
from contextlib import contextmanager
import uuid
import sys
sys.dont_write_bytecode = True

BEGIN, END = "# tkstack:private-state:start", "# tkstack:private-state:end"
DEFAULT = "# Ignore generated/local state; keep explicit repository metadata.\n*\n!.gitignore\n!reuse/\n!reuse/catalog.json\n"
PRIVATE = {"sessions", "runs", "evidence", "state", "cache", "runtime", "steering", "locks",
           "sdlc", "hill-climb", "instructify", "skillify", "evolution", "openwiki", "wikiskill",
           "integration-installs", "worktrees", "tmp", "build", "learnings"}


def project_root(start=None):
    current = Path(start if start is not None else Path.cwd()).absolute()
    if current.is_file():
        current = current.parent
    boundaries = {Path.home(), Path(tempfile.gettempdir()), Path(current.anchor)}
    for parent in (current, *current.parents):
        if parent != current and parent in boundaries:
            break
        if (parent / ".git").exists() or (parent / "sources.lock.json").is_file():
            return parent
        if parent.name == "skills":
            return parent.parent
    return current


SCOPES = ("workspace", "user", "global")
SESSION_LOCAL = {"runs", "evidence", "tmp", "sdlc", "hill-climb", "instructify", "skillify", "evolution"}


def state_root(scope="workspace", project=None):
    """Resolve one write scope, never by existence or permission fallback."""
    if scope not in SCOPES:
        raise ValueError("Scope must be workspace, user, or global")
    if project is not None and scope != "workspace":
        raise ValueError("--project only selects a workspace scope")
    defaults = {"global": Path("/etc/.tkstack"), "user": Path.home() / ".tkstack"}
    if scope == "workspace" and project is not None:
        root = Path(project).expanduser().absolute() / ".tkstack"
    else:
        override = os.environ.get("TKSTACK_" + scope.upper() + "_DIR")
        if override:
            root = Path(override).expanduser().absolute()
        elif scope == "workspace":
            root = project_root() / ".tkstack"
        else:
            root = defaults[scope].absolute()
    if root.name != ".tkstack":
        raise ValueError("A scoped root must be named .tkstack")
    state_container(root)
    return root


def state_roots(project=None):
    """Nearest scope first; callers deduplicate coincident roots when reading."""
    return {scope: state_root(scope, project if scope == "workspace" else None) for scope in SCOPES}


def session_path(session=None, project=None, scope="workspace"):
    identity = session or os.environ.get("TKSTACK_SESSION_ID")
    if not isinstance(identity, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", identity):
        raise ValueError("Supply a literal session ID (1..128 letters, digits, dot, underscore, or dash)")
    root = state_root(scope, project)
    directory = root / "sessions" / identity
    if (root / "sessions").is_symlink() or directory.is_symlink():
        raise ValueError("Session paths must not be symlinks")
    state_container(directory)
    return directory


def state_path(namespace, project=None, scope="workspace", session=None):
    if not re.fullmatch(r"[a-z0-9]+(?:[._-][a-z0-9]+)*", namespace):
        raise ValueError("Use a literal tkstack state namespace")
    identity = session or (os.environ.get("TKSTACK_SESSION_ID") if namespace in SESSION_LOCAL else None)
    if identity:
        base = session_path(identity, project, scope)
        return base if namespace == "sessions" else base / namespace
    return state_root(scope, project) / namespace


@contextmanager
def session_tempdir(prefix="tmp-", session=None, project=None, scope="workspace"):
    """Own only one scratch child; leave named sessions for Learn to consolidate."""
    if not isinstance(prefix, str) or not re.fullmatch(r"[A-Za-z0-9._-]{1,64}", prefix):
        raise ValueError("Use a literal scratch-directory prefix")
    identity = session or os.environ.get("TKSTACK_SESSION_ID")
    ephemeral = not identity
    base = ensure_state(session_path(identity or ("tmp-" + uuid.uuid4().hex), project, scope))
    try:
        with tempfile.TemporaryDirectory(prefix=prefix, dir=base) as temporary:
            yield Path(temporary)
    finally:
        if ephemeral:
            try:
                base.rmdir()
            except OSError:
                pass  # Preserve any independently recorded evidence.


def steering_store(scope=None, project=None):
    if scope is not None:
        return state_path("steering", project, scope)
    if os.environ.get("TKSTACK_STEERING_DIR"):
        return Path(os.environ["TKSTACK_STEERING_DIR"]).expanduser()
    if project is not None or os.environ.get("TKSTACK_WORKSPACE_DIR"):
        return state_path("steering", project)
    current = Path.cwd()
    boundaries = {Path.home(), Path(tempfile.gettempdir()), Path(current.anchor)}
    for parent in (current, *current.parents):
        # Machine-wide home/temp/root directories are not implicit project stores.
        if parent != current and parent in boundaries:
            break
        local = parent / ".tkstack/steering"
        if local.is_dir():
            return local.resolve()
        alias = parent / ".agents/steering"
        if alias.is_dir():
            state_container(alias.resolve())
            return alias.resolve()
        if (parent / ".git").exists():
            break
    return state_path("steering", project_root(current))


def state_container(path):
    path = Path(path).absolute()
    container = next((p for p in (path, *path.parents) if p.name == ".tkstack"), None)
    if container is None:
        raise ValueError("Skill state must be inside a .tkstack directory")
    if container.is_symlink() or not path.resolve().is_relative_to(container.resolve()):
        raise ValueError("Skill state must not escape .tkstack through symlinks")
    return container


def policy_plan(project, namespaces=()):
    container = Path(project).absolute() / ".tkstack"
    state_container(container)
    path = container / ".gitignore"
    if path.is_symlink():
        raise ValueError("State ignore policy must be a regular file")
    before = path.read_text() if path.exists() else ""
    base = before or DEFAULT
    names = set(PRIVATE) | set(namespaces)
    if base.count(BEGIN) != base.count(END) or base.count(BEGIN) > 1:
        raise ValueError("Malformed tkstack state policy markers")
    if BEGIN in base:
        start, end = base.index(BEGIN), base.index(END) + len(END)
        if end <= start:
            raise ValueError("Malformed tkstack state policy markers")
        names.update(re.findall(r"^/([a-z0-9][a-z0-9._-]*)/$", base[start:end], re.M))
        if base[end:end + 1] == "\n":
            end += 1
        base = base[:start] + base[end:]
    if any(not re.fullmatch(r"[a-z0-9][a-z0-9._-]*", name) for name in names):
        raise ValueError("State namespace cannot contain Git ignore metacharacters")
    after = base + ("\n" if base and not base.endswith("\n") else "")
    after += BEGIN + "\n" + "\n".join("/" + name + "/" for name in sorted(names))
    after += "\n/.state-policy.lock/\n/.state-policy-*\n" + END + "\n"
    return path, before, after


def ensure_state(path):
    """Prepare one private state namespace without touching read-only operations."""
    path = Path(path).absolute()
    container = state_container(path)
    relative = path.relative_to(container)
    namespace = relative.parts[0] if relative.parts else None
    container.mkdir(parents=True, exist_ok=True)
    lock = container / ".state-policy.lock"
    for attempt in range(100):
        try:
            lock.mkdir()
            break
        except FileExistsError:
            if attempt == 99:
                raise ValueError("State policy is busy; retry after its writer finishes")
            time.sleep(0.01)
    temporary = None
    try:
        policy, before, after = policy_plan(container.parent, [namespace] if namespace else [])
        if before != after:
            with tempfile.NamedTemporaryFile(dir=container, prefix=".state-policy-", delete=False) as output:
                temporary = Path(output.name)
                output.write(after.encode())
            if (policy.read_text() if policy.exists() else "") != before:
                raise ValueError("State ignore policy changed during update")
            temporary.replace(policy)
            temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        lock.rmdir()
    path.mkdir(parents=True, exist_ok=True)
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("path", "init", "locations"))
    parser.add_argument("--project", type=Path)
    parser.add_argument("--scope", choices=SCOPES, default="workspace")
    parser.add_argument("--session", help="Session ID; selects sessions/<session>/<namespace>")
    parser.add_argument("--namespace", default="sessions")
    args = parser.parse_args()
    try:
        if args.operation == "locations":
            import json
            print(json.dumps({scope: str(path) for scope, path in state_roots(args.project).items()}, indent=2))
            return 0
        path = state_path(args.namespace, args.project, args.scope, args.session)
        if args.operation == "init":
            ensure_state(path)
        print(path)
    except (OSError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

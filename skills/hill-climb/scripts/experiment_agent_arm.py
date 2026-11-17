"""Apply an isolated proposal to one controller-owned Git experiment arm.

Call under the controller's exclusive lock after all other arm writers stop.
Provider registries are constructed by trusted host code, not imported from
request data. Git worktrees do not themselves sandbox an external coding agent.
"""
import base64
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import tempfile

from experiment_git import _name, _paths, _run


_MAX_BYTES = 32 * 1024 * 1024


def _write_record(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.parent.is_symlink():
        raise ValueError("proposal evidence directory cannot be a symlink")
    encoded = json.dumps(value, sort_keys=True, allow_nan=False, separators=(",", ":")).encode("utf-8") + b"\n"
    with path.open("xb") as output:
        output.write(encoded)
        output.flush()
        os.fsync(output.fileno())
    directory = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)
    return hashlib.sha256(encoded).hexdigest()


def _require_clean(git, experiment, arm, expected):
    worktree, _, _ = git._arm(experiment, arm)
    if git.resolve(experiment, arm) != expected:
        raise ValueError("arm identity changed since proposal was planned")
    status = _run(["-C", worktree, "status", "--porcelain=v1", "-z",
                   "--untracked-files=all", "--ignored=matching"], text=False)
    if status.stdout:
        raise ValueError("arm must be clean before applying a proposal")
    return worktree


def _preflight(worktree, changes, paths):
    if not isinstance(changes, list):
        raise ValueError("proposal changes must be an array")
    scopes = _paths(paths)
    prepared = []
    seen = set()
    total = 0
    for change in changes:
        if not isinstance(change, dict):
            raise ValueError("proposal change must be an object")
        name = change.get("path")
        if not isinstance(name, str) or not name or "\\" in name or "\x00" in name:
            raise ValueError("invalid proposal path")
        relative = PurePosixPath(name)
        if (relative.is_absolute() or str(relative) != name or
                any(part in ("..", ".git") for part in relative.parts) or str(relative) == "."):
            raise ValueError("proposal path escapes the arm")
        if name in seen:
            raise ValueError("duplicate proposal path")
        seen.add(name)
        if not any(scope == "." or name == scope or name.startswith(scope + "/") for scope in scopes):
            raise ValueError("proposal path is outside allowed scope")
        destination = worktree
        for part in relative.parts:
            destination /= part
            if destination.is_symlink():
                raise ValueError("proposal path crosses a symlink")
        if not destination.resolve().is_relative_to(worktree.resolve()):
            raise ValueError("proposal path escapes the arm")
        if destination.exists() and not destination.is_file():
            raise ValueError("proposal target is not a regular file")
        old = destination.read_bytes() if destination.exists() else None
        before = hashlib.sha256(old).hexdigest() if old is not None else None
        if change.get("before_sha256") != before:
            raise ValueError("proposal preimage differs from the frozen source")
        operation = change.get("operation")
        if operation == "delete":
            if old is None or set(change) != {"path", "operation", "before_sha256"}:
                raise ValueError("invalid deletion")
            prepared.append((destination, None, None))
            continue
        if operation != "write" or set(change) != {"path", "operation", "before_sha256", "content_base64", "sha256", "executable"}:
            raise ValueError("invalid write")
        if type(change["executable"]) is not bool or not isinstance(change["content_base64"], str):
            raise ValueError("invalid write content or mode")
        try:
            data = base64.b64decode(change["content_base64"], validate=True)
        except (ValueError, UnicodeEncodeError) as error:
            raise ValueError("invalid base64 proposal content") from error
        total += len(data)
        if total > _MAX_BYTES or hashlib.sha256(data).hexdigest() != change["sha256"]:
            raise ValueError("proposal content size or digest is invalid")
        prepared.append((destination, data, change["executable"]))
    return prepared


def _apply(prepared):
    for destination, data, executable in prepared:
        if data is None:
            destination.unlink()
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temp = tempfile.mkstemp(prefix=".tkstack-proposal-", dir=destination.parent)
        try:
            with os.fdopen(descriptor, "wb") as output:
                output.write(data)
                output.flush()
                os.fsync(output.fileno())
            os.chmod(temp, 0o755 if executable else 0o644)
            os.replace(temp, destination)
        finally:
            if os.path.exists(temp):
                os.unlink(temp)


def propose_to_arm(*, git, ledger, experiment, arm, expected, paths, runner, provider,
                   prompt, run_key, max_tokens, timeout, message, freeze, writers_stopped):
    """Propose from an exact clean arm, retain evidence, then use the scoped freeze.

    The caller must hold its controller lock through this operation and supply a
    freeze callback that registers scoped approval. ``runner`` is created by
    trusted host code with an approved provider registry. Caller-provided JSON
    must never be resolved to a Python class or arbitrary command.

    Interruption after proposal receipt retains that receipt for review, and may
    leave a dirty arm or a frozen commit. Recovery must inspect these artifacts;
    the same run key is never dispatched a second time automatically.
    """
    experiment, arm, run_key = _name(experiment), _name(arm), _name(run_key)
    if writers_stopped is not True:
        raise ValueError("all arm writers must be stopped before proposing")
    if runner.ledger.database.resolve() != ledger.database.resolve():
        raise ValueError("proposal runner uses a different budget ledger")
    if not callable(freeze):
        raise ValueError("controller scoped-freeze callback is required")
    _paths(paths)
    worktree = _require_clean(git, experiment, arm, expected)
    evidence_dir = git.root / "proposals"
    evidence_dir.mkdir(exist_ok=True)
    if evidence_dir.is_symlink() or evidence_dir.resolve() != evidence_dir:
        raise ValueError("invalid proposal evidence directory")
    evidence_path = evidence_dir / (run_key + ".json")
    complete_path = evidence_dir / (run_key + ".complete.json")
    if evidence_path.exists() or evidence_path.is_symlink() or complete_path.exists() or complete_path.is_symlink():
        raise ValueError("proposal key already has evidence")
    def retain_receipt(result):
        evidence = {"experiment": experiment, "arm": arm, "parent": expected,
                    "paths": list(paths), "provider": provider, "run_key": run_key, "result": result}
        return _write_record(evidence_path, evidence)

    result = runner.run(experiment=experiment, run_key=run_key, repo=git.repo,
                        commit=expected["commit"], tree=expected["tree"], provider=provider,
                        prompt=prompt, allowed_paths=paths, max_tokens=max_tokens, timeout=timeout,
                        receipt_writer=retain_receipt)
    digest = hashlib.sha256(evidence_path.read_bytes()).hexdigest()
    if result["status"] != "proposed":
        return {"status": "rejected", "reason": result.get("reason"), "evidence": str(evidence_path),
                "evidence_sha256": digest}
    if not result["changes"]:
        return {"status": "inconclusive", "reason": "provider proposed no changes",
                "evidence": str(evidence_path), "evidence_sha256": digest}
    # Check both the Git ref and working files again after the agent has run.
    worktree = _require_clean(git, experiment, arm, expected)
    prepared = _preflight(worktree, result["changes"], paths)
    _apply(prepared)
    identity = freeze(arm, message)
    if git.resolve(experiment, arm) != identity:
        raise ValueError("controller freeze returned a stale arm identity")
    completed = {"experiment": experiment, "arm": arm, "parent": expected,
                 "identity": identity, "evidence_sha256": digest}
    _write_record(complete_path, completed)
    return {"status": "frozen", "identity": identity, "evidence": str(evidence_path),
            "evidence_sha256": digest, "completion": str(complete_path)}

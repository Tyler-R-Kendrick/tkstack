"""Budget-aware coding proposer boundary for frozen Git trees.

Only ScriptedProvider is supplied as an executable, zero-model provider.
CommandProvider requires an operator-supplied enforcing broker. The broker is
trusted to isolate the child, enforce a total token ceiling *before usage*,
and terminate all its descendants at the deadline. A mere JSON usage report or
an environment variable passed to an unbounded agent does not enforce a cap.
"""
from abc import ABC, abstractmethod
import base64
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import tempfile
import threading
import time

from experiment_runner import _git, _materialize


_OBJECT = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")
_MAX_FILES = 100000
_MAX_BYTES = 32 * 1024 * 1024


def _safe_path(value):
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        raise ValueError("path must be a nonempty relative POSIX path")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in ("..", ".git") for part in path.parts) or str(path) == ".":
        raise ValueError("path must stay inside the source tree")
    return path


def _snapshot(root):
    """Snapshot regular files without following links; cap collection size."""
    entries = {}
    total = 0
    for current, dirs, files in os.walk(root, followlinks=False):
        dirs.sort()
        files.sort()
        for name in list(dirs):
            item = Path(current) / name
            if item.is_symlink():
                dirs.remove(name)
                files.append(name)
        for name in sorted(files):
            item = Path(current) / name
            relative = item.relative_to(root).as_posix()
            _safe_path(relative)
            if len(entries) >= _MAX_FILES:
                raise ValueError("source snapshot exceeds file limit")
            if item.is_symlink():
                entries[relative] = {"kind": "symlink", "target": os.readlink(item)}
            elif item.is_file():
                size = item.stat().st_size
                total += size
                if total > _MAX_BYTES:
                    raise ValueError("source snapshot exceeds byte limit")
                data = item.read_bytes()
                if len(data) != size:
                    raise ValueError("source changed while collecting proposal")
                entries[relative] = {"kind": "file", "content": data,
                                     "executable": bool(item.stat().st_mode & 0o111)}
            else:
                raise ValueError("special files are not permitted in proposals")
    return entries


def _changes(before, after, allowed):
    result = []
    for name in sorted(before.keys() | after.keys()):
        old = before.get(name)
        new = after.get(name)
        if old == new:
            continue
        path = PurePosixPath(name)
        if not any(path == scope or scope in path.parents for scope in allowed):
            raise ValueError(f"change outside allowed paths: {name}")
        if (old and old["kind"] == "symlink") or (new and new["kind"] == "symlink"):
            raise ValueError("symlink changes require a separately reviewed integration")
        entry = {"path": name, "operation": "delete" if new is None else "write",
                 "before_sha256": hashlib.sha256(old["content"]).hexdigest() if old else None}
        if new is not None:
            entry.update(content_base64=base64.b64encode(new["content"]).decode("ascii"),
                         sha256=hashlib.sha256(new["content"]).hexdigest(), executable=new["executable"])
        result.append(entry)
    return result


class ScriptedProvider:
    """Deterministic in-process edits for local fixtures; never calls a model."""

    def __init__(self, edits):
        if not isinstance(edits, dict):
            raise ValueError("edits must map relative paths to bytes or None")
        self.edits = {}
        for name, value in edits.items():
            path = _safe_path(name)
            if value is not None and not isinstance(value, bytes):
                raise ValueError("scripted edit must be bytes or None")
            self.edits[str(path)] = value

    def validate(self, max_tokens):
        return None

    def execute(self, *, root, prompt, max_tokens, timeout):
        deadline = time.monotonic() + timeout
        for name, content in self.edits.items():
            if time.monotonic() >= deadline:
                raise TimeoutError("scripted proposal timed out")
            path = root.joinpath(*PurePosixPath(name).parts)
            resolved_parent = path.parent.resolve(strict=False)
            if not resolved_parent.is_relative_to(root.resolve()) or path.is_symlink():
                raise ValueError("scripted edit follows a symlink outside the source tree")
            if content is None:
                path.unlink()
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(content)
        return {"usage_tokens": 0, "provider_receipt": {"provider": "scripted", "usage_tokens": 0}}


class EnforcingBroker(ABC):
    """Trusted integration seam for real agents.

    An implementation must independently cap all model input/output/cache tokens
    including retries and descendants, confine writes, execute fixed argv without
    a shell, and kill descendant processes at timeout. It returns an authoritative
    usage receipt for this invocation. No such broker ships with this module.
    """

    @abstractmethod
    def execute(self, *, argv, cwd, prompt, max_tokens, timeout):
        raise NotImplementedError


class CommandProvider:
    """A pinned command executable run solely through a trusted broker.

    ``allowlist`` maps absolute executable paths to SHA-256 hashes, established
    outside candidate-controlled config. Arguments are fixed at registration.
    The broker, not this class, must enforce limits and sandbox policy.
    """

    def __init__(self, argv, allowlist, *, broker):
        if (not isinstance(argv, (list, tuple)) or not argv or
                any(not isinstance(arg, str) or "\x00" in arg for arg in argv)):
            raise ValueError("provider argv must be a nonempty argument array")
        if not isinstance(allowlist, dict):
            raise ValueError("provider command allowlist must be a mapping")
        self.argv = tuple(argv)
        self.allowlist = dict(allowlist)
        self.broker = broker

    def validate(self, max_tokens):
        if not isinstance(self.broker, EnforcingBroker):
            raise ValueError("a trusted enforcing broker is required for command providers")
        path = Path(self.argv[0])
        if not path.is_absolute() or str(path.resolve()) != str(path):
            raise ValueError("provider executable must be an absolute canonical path")
        expected = self.allowlist.get(str(path))
        if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
            raise ValueError("provider executable is not on the pinned allowlist")
        try:
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError as exc:
            raise ValueError("provider executable cannot be read") from exc
        if actual != expected:
            raise ValueError("provider executable differs from the pinned allowlist")

    def execute(self, *, root, prompt, max_tokens, timeout):
        # Recheck immediately before handing fixed argv to the trusted broker.
        self.validate(max_tokens)
        return self.broker.execute(argv=self.argv, cwd=root, prompt=prompt,
                                   max_tokens=max_tokens, timeout=timeout)


class ProposalRunner:
    """Run registered providers in independent snapshots under one local limit.

    ``max_concurrency`` bounds callers sharing this runner instance. A controller
    running multiple processes must additionally enforce a shared worker limit.
    The temporary tree prevents ordinary cross-candidate edits; it is not an OS
    sandbox. External brokers must supply the actual isolation boundary.
    """

    def __init__(self, ledger, providers, *, max_concurrency=1):
        if type(max_concurrency) is not int or not 1 <= max_concurrency <= 64:
            raise ValueError("max_concurrency must be 1..64")
        if not isinstance(providers, dict) or not providers:
            raise ValueError("providers must be a nonempty trusted registry")
        self.ledger = ledger
        self.providers = dict(providers)
        self.slots = threading.BoundedSemaphore(max_concurrency)

    def run(self, *, experiment, run_key, repo, commit, tree, provider, prompt,
            allowed_paths, max_tokens, timeout, receipt_writer=None):
        if not isinstance(commit, str) or not _OBJECT.fullmatch(commit):
            raise ValueError("commit must be a full lowercase Git object ID")
        if not isinstance(tree, str) or not _OBJECT.fullmatch(tree):
            raise ValueError("tree must be a full lowercase Git object ID")
        if type(max_tokens) is not int or max_tokens < 0:
            raise ValueError("max_tokens must be a nonnegative integer")
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("timeout must be positive and finite")
        if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 1024 * 1024:
            raise ValueError("prompt must be nonempty and bounded")
        if not isinstance(allowed_paths, (list, tuple)) or not allowed_paths:
            raise ValueError("allowed_paths must contain at least one scope")
        scopes = tuple(_safe_path(item) for item in allowed_paths)
        if not isinstance(provider, str) or provider not in self.providers:
            raise ValueError("unknown provider")
        adapter = self.providers[provider]
        if type(adapter) not in (ScriptedProvider, CommandProvider):
            raise ValueError("provider type is not registered")
        deadline = time.monotonic() + timeout
        adapter.validate(max_tokens)
        repo = Path(repo).resolve(strict=True)
        if (_git(repo, "rev-parse", "--verify", commit + "^{commit}").decode("ascii").strip() != commit or
                _git(repo, "rev-parse", "--verify", commit + "^{tree}").decode("ascii").strip() != tree):
            raise ValueError("frozen commit/tree mismatch")
        remaining = deadline - time.monotonic()
        if remaining <= 0 or not self.slots.acquire(timeout=remaining):
            raise TimeoutError("proposal timed out waiting for a worker slot")
        try:
            with tempfile.TemporaryDirectory(prefix="tkstack-proposal-") as temp:
                root = Path(temp) / "source"
                root.mkdir()
                _materialize(repo, commit, root)
                before = _snapshot(root)
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError("proposal timed out before dispatch")
                reservation = self.ledger.reserve(experiment, run_key, tokens=max_tokens, trial_units=0, proposal=True)
                if reservation["status"] != "reserved":
                    raise ValueError("proposal key already used; reconcile before retrying")
                granted = self.ledger.dispatch(experiment, run_key)
                if not granted["dispatch_granted"]:
                    raise ValueError("proposal already dispatched; reconcile before retrying")
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    self.ledger.cancel(experiment, run_key, reason="deadline before provider call",
                                       non_execution_evidence="provider call was not invoked")
                    raise TimeoutError("proposal timed out before provider call")
                try:
                    outcome = adapter.execute(root=root, prompt=prompt, max_tokens=max_tokens, timeout=remaining)
                    if (not isinstance(outcome, dict) or type(outcome.get("usage_tokens")) is not int
                            or outcome["usage_tokens"] < 0 or not isinstance(outcome.get("provider_receipt"), dict)):
                        raise ValueError("provider returned an invalid usage receipt")
                    try:
                        receipt = json.dumps(outcome["provider_receipt"], allow_nan=False).encode("utf-8")
                    except (TypeError, ValueError) as exc:
                        raise ValueError("provider receipt must be valid JSON") from exc
                    if len(receipt) > 1024 * 1024:
                        raise ValueError("provider receipt exceeds size limit")
                except BaseException:
                    self.ledger.uncertain(experiment, run_key, "provider outcome requires reconciliation")
                    raise
                used = outcome["usage_tokens"]
                try:
                    if used > max_tokens:
                        raise ValueError("provider exceeded reserved token limit")
                    changes = _changes(before, _snapshot(root), scopes)
                    result = {"status": "proposed", "commit": commit, "tree": tree,
                              "usage_tokens": used, "changes": changes,
                              "provider_receipt": outcome["provider_receipt"]}
                except (OSError, ValueError) as exc:
                    result = {"status": "rejected", "reason": str(exc), "usage_tokens": used,
                              "changes": [], "provider_receipt": outcome["provider_receipt"]}
                try:
                    receipt_sha256 = receipt_writer(result) if receipt_writer is not None else None
                    self.ledger.settle(experiment, run_key, actual_tokens=used, receipt_sha256=receipt_sha256)
                except BaseException:
                    self.ledger.uncertain(experiment, run_key, "proposal receipt or settlement needs reconciliation")
                    raise
                return result
        finally:
            self.slots.release()

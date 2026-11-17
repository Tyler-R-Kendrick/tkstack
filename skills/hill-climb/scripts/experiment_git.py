"""Private Git repositories for attributable experiment arms.

Worktrees provide separate files and indexes, not a security boundary or a
promise of copy-on-write. The caller must stop writers before freeze or retire.
This module never publishes a ref to the source repository.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import secrets
import subprocess
import tempfile


_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
_MARKER = "tkstack-git-experiment-v1"


def _environment():
    return {
        **{key: value for key, value in os.environ.items() if not key.startswith("GIT_")},
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_NO_REPLACE_OBJECTS": "1",
    }


def _run(args, *, cwd=None, text=True, check=True):
    completed = subprocess.run(
        ["git", "-c", f"core.hooksPath={os.devnull}", "-c", "core.fsmonitor=false",
         "-c", "credential.helper=", *map(str, args)],
        cwd=cwd if cwd is not None else os.path.abspath(os.sep), env=_environment(),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=text, check=False,
    )
    if check and completed.returncode:
        detail = completed.stderr if text else completed.stderr.decode("utf-8", "replace")
        raise RuntimeError(f"Git command failed: {detail.strip()}")
    return completed


def _name(value):
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise ValueError("experiment and arm IDs must contain only letters, numbers, - or _")
    return value


def _paths(items):
    if not isinstance(items, (tuple, list)) or not items:
        raise ValueError("at least one allowed path is required")
    paths = []
    for item in items:
        if not isinstance(item, str) or not item or "\x00" in item or "\\" in item:
            raise ValueError("allowed paths must be nonempty repository-relative paths")
        path = PurePosixPath(item)
        if path.is_absolute() or ".." in path.parts or item.startswith(":"):
            raise ValueError("allowed paths must be repository-relative")
        paths.append(path.as_posix().rstrip("/") or ".")
    return paths


def _inside_scope(path, scope):
    return any(item == "." or path == item or path.startswith(item + "/") for item in scope)


def _names(data):
    return [part.decode("utf-8", "surrogateescape") for part in data.split(b"\x00") if part]


class GitExperiment:
    """Manage a controller-owned private Git clone and its experiment arms."""

    def __init__(self, root):
        self.root = Path(root).resolve()
        self.repo = self.root / "repo.git"
        self._verify_repository()

    def _verify_repository(self):
        owner = self.root / "owner.json"
        try:
            if owner.is_symlink() or self.repo.is_symlink() or not self.repo.is_dir():
                raise ValueError("managed repository or owner record was replaced")
            marker = json.loads(owner.read_text())
            identity = self.repo.stat()
        except (OSError, ValueError) as error:
            raise ValueError("root is not a managed experiment repository") from error
        if (not isinstance(marker, dict) or marker.get("kind") != _MARKER or
                marker.get("repo_dev") != identity.st_dev or marker.get("repo_ino") != identity.st_ino):
            raise ValueError("managed repository identity does not match its owner record")

    def _owned_parent(self, group, experiment=None):
        base = self.root / group
        if base.is_symlink() or not base.is_dir() or base.resolve() != base:
            raise ValueError("managed directory has been replaced or redirected")
        if experiment is None:
            return base
        child = base / _name(experiment)
        if child.is_symlink() or child.resolve() != child:
            raise ValueError("managed directory has been replaced or redirected")
        return child

    @classmethod
    def create(cls, source, root):
        source = Path(source).resolve(strict=True)
        root = Path(root).resolve()
        if root.exists():
            raise ValueError("experiment root must not already exist")
        source_top = Path(_run(["-C", source, "rev-parse", "--show-toplevel"]).stdout.rstrip("\n")).resolve()
        common = Path(_run(["-C", source, "rev-parse", "--path-format=absolute",
                            "--git-common-dir"]).stdout.rstrip("\n")).resolve()
        listing = _run(["-C", source, "worktree", "list", "--porcelain", "-z"], text=False)
        worktrees = [Path(os.fsdecode(item[len(b"worktree "):])).resolve()
                     for item in listing.stdout.split(b"\0") if item.startswith(b"worktree ")]
        for protected in [source_top, common, *worktrees]:
            if root == protected or root.is_relative_to(protected) or protected.is_relative_to(root):
                raise ValueError("experiment root must not overlap any source worktree or common Git directory")
        root.mkdir(parents=True, exist_ok=False)
        try:
            _run(["clone", "--bare", "--no-local", "--", source_top, root / "repo.git"])
            _run(["--git-dir", root / "repo.git", "remote", "remove", "origin"])
            (root / "worktrees").mkdir()
            (root / "metadata").mkdir()
            (root / "archives").mkdir()
            identity = (root / "repo.git").stat()
            (root / "owner.json").write_text(json.dumps({
                "kind": _MARKER, "repo_dev": identity.st_dev, "repo_ino": identity.st_ino,
            }) + "\n")
        except Exception:
            # Keep partial state for inspection; it cannot be opened without the marker.
            raise
        return cls(root)

    @classmethod
    def open(cls, root):
        return cls(root)

    def _git(self, *args, text=True, check=True):
        self._verify_repository()
        return _run(["--git-dir", self.repo, *args], text=text, check=check)

    def _check_filters(self, worktree=None):
        location = ["-C", worktree] if worktree is not None else ["--git-dir", self.repo]
        result = _run([*location, "config", "--includes", "--get-regexp",
                       r"^filter\..*\.(clean|smudge|process)$"], check=False)
        if result.returncode == 0 and result.stdout.strip():
            raise ValueError("configured external Git filter drivers are not allowed")
        if result.returncode not in (0, 1):
            raise RuntimeError("could not check Git filter configuration")

    def _worktree(self, experiment, arm):
        return self._owned_parent("worktrees", experiment) / _name(arm)

    def _ref(self, experiment, arm):
        return f"refs/heads/exp/{_name(experiment)}/{_name(arm)}"

    def _metadata(self, experiment, arm):
        return self._owned_parent("metadata", experiment) / (f"{_name(arm)}.json")

    def _commit(self, value):
        fmt = self._git("rev-parse", "--show-object-format").stdout.strip()
        length = {"sha1": 40, "sha256": 64}.get(fmt)
        if not isinstance(value, str) or length is None or not re.fullmatch(rf"[0-9a-f]{{{length}}}", value):
            raise ValueError("a full lowercase Git commit ID is required")
        result = self._git("rev-parse", "--verify", "--end-of-options", value + "^{commit}").stdout.strip()
        if result != value:
            raise ValueError("value must name a commit directly")
        return result

    def _arm(self, experiment, arm):
        worktree, ref = self._worktree(experiment, arm), self._ref(experiment, arm)
        metadata_path = self._metadata(experiment, arm)
        try:
            if metadata_path.is_symlink():
                raise ValueError("arm ownership record was replaced")
            metadata = json.loads(metadata_path.read_text())
        except (OSError, ValueError) as error:
            raise ValueError("arm does not have a managed record") from error
        if metadata.get("ref") != ref or metadata.get("worktree") != str(worktree):
            raise ValueError("arm ownership record mismatch")
        if worktree.is_symlink() or not worktree.is_dir() or worktree.resolve() != worktree:
            raise ValueError("managed worktree is missing or has been replaced")
        if not self._registered_worktree(worktree):
            raise ValueError("managed worktree is not registered")
        common_dir = _run(["-C", worktree, "rev-parse", "--git-common-dir"]).stdout.strip()
        if Path(common_dir).resolve() != self.repo.resolve():
            raise ValueError("worktree is not attached to the managed repository")
        head_ref = _run(["-C", worktree, "symbolic-ref", "--quiet", "HEAD"]).stdout.strip()
        if head_ref != ref:
            raise ValueError("worktree is not on the expected arm")
        return worktree, ref, metadata

    def allocate(self, experiment, arm, base):
        base = self._commit(base)
        worktree, ref = self._worktree(experiment, arm), self._ref(experiment, arm)
        metadata = self._metadata(experiment, arm)
        if worktree.exists() or worktree.is_symlink() or metadata.exists():
            raise ValueError("arm already exists")
        worktree.parent.mkdir(parents=True, exist_ok=True)
        metadata.parent.mkdir(parents=True, exist_ok=True)
        self._check_filters()
        self._git("worktree", "add", "-b", ref.removeprefix("refs/heads/"), worktree, base)
        metadata.write_text(json.dumps({"ref": ref, "base": base, "worktree": str(worktree)}) + "\n")
        return worktree

    def resolve(self, experiment, arm):
        _, ref, _ = self._arm(experiment, arm)
        commit = self._commit(self._git("rev-parse", "--verify", ref + "^{commit}").stdout.strip())
        tree = self._git("rev-parse", "--verify", commit + "^{tree}").stdout.strip()
        return {"commit": commit, "tree": tree}

    def freeze(self, experiment, arm, paths, message):
        scope = _paths(paths)
        if not isinstance(message, str) or not message.strip() or "\x00" in message:
            raise ValueError("a commit message is required")
        worktree, _, metadata = self._arm(experiment, arm)
        base = self._commit(metadata["base"])
        self._check_filters(worktree)
        committed = _run(["-C", worktree, "diff", "--name-only", "--no-renames", "-z", base, "HEAD"],
                         text=False)
        modified = _run(["-C", worktree, "diff", "--name-only", "--no-renames", "-z", "HEAD"],
                        text=False)
        untracked = _run(["-C", worktree, "ls-files", "--others", "--exclude-standard", "-z"],
                         text=False)
        ignored = _run(["-C", worktree, "ls-files", "--others", "--ignored",
                        "--exclude-standard", "-z"], text=False)
        if ignored.stdout:
            raise ValueError("ignored files must be removed from the worktree before freezing")
        changed = _names(committed.stdout) + _names(modified.stdout) + _names(untracked.stdout)
        outside = [name for name in changed if not _inside_scope(name, scope)]
        if outside:
            raise ValueError(f"changes outside allowed scope: {outside!r}")
        _run(["-C", worktree, "add", "-A", "--", "."])
        staged = _run(["-C", worktree, "diff", "--cached", "--name-only", "--no-renames", "-z"],
                      text=False)
        if staged.stdout:
            _run(["-C", worktree, "-c", "user.name=tkstack experiment",
                  "-c", "user.email=experiment@invalid", "-c", "commit.gpgsign=false",
                  "-c", f"core.hooksPath={os.devnull}", "commit", "-m", message])
        return self.resolve(experiment, arm)

    def initialize_integration(self, experiment, base):
        ref = f"refs/heads/integration/{_name(experiment)}"
        base = self._commit(base)
        self._git("update-ref", ref, base, "0" * len(base))
        generation = self.new_generation()
        self._git("update-ref", f"refs/tkstack/generation/{_name(experiment)}",
                  generation, "0" * len(generation))
        return base

    def resolve_integration(self, experiment):
        ref = f"refs/heads/integration/{_name(experiment)}"
        return self._commit(self._git("rev-parse", "--verify", ref + "^{commit}").stdout.strip())

    def promote(self, experiment, expected, candidate):
        expected, candidate = self._commit(expected), self._commit(candidate)
        ref = f"refs/heads/integration/{_name(experiment)}"
        if self._git("merge-base", "--is-ancestor", expected, candidate, check=False).returncode:
            raise ValueError("candidate must descend from the expected integration commit")
        self._git("update-ref", ref, candidate, expected)
        return candidate

    def new_generation(self):
        self._verify_repository()
        result = subprocess.run(
            ["git", "-c", f"core.hooksPath={os.devnull}", "-c", "core.fsmonitor=false",
             "-c", "credential.helper=", "--git-dir", str(self.repo),
             "hash-object", "-w", "--stdin"],
            input=secrets.token_hex(32), text=True, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, env=_environment(), check=False,
        )
        if result.returncode:
            raise RuntimeError(f"Git generation creation failed: {result.stderr.strip()}")
        return result.stdout.strip()

    def generation(self, experiment):
        ref = f"refs/tkstack/generation/{_name(experiment)}"
        return self._git("rev-parse", "--verify", ref).stdout.strip()

    def promote_with_marker(self, experiment, expected, candidate, operation,
                            expected_generation, new_generation):
        """Use a guarded Git ref transaction with a unique operation marker.

        Multi-ref visibility and crash recovery depend on the Git ref backend.
        A marker/head mismatch requires quarantine, not an assumed outcome.
        """
        expected, candidate = self._commit(expected), self._commit(candidate)
        experiment, operation = _name(experiment), _name(operation)
        ref = f"refs/heads/integration/{experiment}"
        marker = f"refs/tkstack/promotions/{experiment}/{operation}"
        generation = f"refs/tkstack/generation/{experiment}"
        fmt = self._git("rev-parse", "--show-object-format").stdout.strip()
        length = {"sha1": 40, "sha256": 64}[fmt]
        if any(not isinstance(value, str) or not re.fullmatch(rf"[0-9a-f]{{{length}}}", value)
               for value in (expected_generation, new_generation)):
            raise ValueError("full generation object IDs are required")
        if self._git("merge-base", "--is-ancestor", expected, candidate, check=False).returncode:
            raise ValueError("candidate must descend from the expected integration commit")
        commands = (f"start\nupdate {ref} {candidate} {expected}\n"
                    f"update {generation} {new_generation} {expected_generation}\n"
                    f"create {marker} {candidate}\nprepare\ncommit\n")
        self._verify_repository()
        result = subprocess.run(
            ["git", "-c", f"core.hooksPath={os.devnull}", "-c", "credential.helper=",
             "--git-dir", str(self.repo), "update-ref", "--stdin"],
            input=commands, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            env=_environment(), check=False,
        )
        if result.returncode:
            raise RuntimeError(f"Git ref transaction failed: {result.stderr.strip()}")
        return candidate

    def promotion_marker(self, experiment, operation):
        marker = f"refs/tkstack/promotions/{_name(experiment)}/{_name(operation)}"
        result = self._git("rev-parse", "--verify", marker + "^{commit}", check=False)
        return result.stdout.strip() if result.returncode == 0 else None

    def _archive_path(self, experiment, arm, expected):
        return self._owned_parent("archives") / f"{_name(experiment)}-{_name(arm)}-{expected}.bundle"

    def _verify_archive(self, archive, ref, expected):
        if archive.is_symlink() or not archive.is_file():
            raise ValueError("archive is missing or has been replaced")
        with tempfile.TemporaryDirectory(prefix="verify-", dir=self.root) as tmp:
            restored = Path(tmp) / "restore.git"
            object_format = self._git("rev-parse", "--show-object-format").stdout.strip()
            _run(["init", "--bare", "--quiet", f"--object-format={object_format}", restored])
            _run(["--git-dir", restored, "bundle", "verify", archive])
            _run(["--git-dir", restored, "fetch", "--no-tags", archive,
                  ref + ":refs/heads/archived"])
            actual = _run(["--git-dir", restored, "rev-parse",
                           "refs/heads/archived^{commit}"]).stdout.strip()
            if actual != expected:
                raise ValueError("archive restored an unexpected commit")
            with archive.open("rb") as source:
                digest = hashlib.file_digest(source, "sha256").hexdigest()
        return {"bundle": str(archive), "sha256": digest, "commit": expected, "ref": ref}

    def _archive(self, experiment, arm, ref, expected):
        archive = self._archive_path(experiment, arm, expected)
        if archive.exists() or archive.is_symlink():
            return self._verify_archive(archive, ref, expected)
        with tempfile.TemporaryDirectory(prefix="bundle-", dir=self.root) as tmp:
            bundle = Path(tmp) / "arm.bundle"
            self._git("bundle", "create", bundle, ref)
            receipt = self._verify_archive(bundle, ref, expected)
            os.link(bundle, archive)  # fail rather than overwrite an existing archive
        receipt["bundle"] = str(archive)
        return receipt

    def _registered_worktree(self, worktree):
        listing = self._git("worktree", "list", "--porcelain", "-z", text=False)
        paths = [os.fsdecode(item[len(b"worktree "):]) for item in
                 listing.stdout.split(b"\0") if item.startswith(b"worktree ")]
        return str(worktree) in paths

    @staticmethod
    def _write_record(path, record):
        # Exclusive creation prevents two owners from silently replacing intent.
        with path.open("x", encoding="utf-8") as stream:
            json.dump(record, stream, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)

    def retire(self, experiment, arm, expected, archive=False):
        """Retire an arm after writers have stopped; rerun with identical arguments.

        The caller must hold the controller's exclusive lease during this operation.
        An absent ref without a completion record is ambiguous and fails closed.
        """
        if type(archive) is not bool:
            raise ValueError("archive must be a boolean")
        experiment, arm = _name(experiment), _name(arm)
        expected = self._commit(expected)
        worktree, ref = self._worktree(experiment, arm), self._ref(experiment, arm)
        metadata = self._metadata(experiment, arm)
        intent_path = metadata.with_name(arm + ".retirement.json")
        completed_path = metadata.with_name(arm + ".retired.json")
        removing_path = metadata.with_name(arm + ".removing.json")
        wanted = {"version": 1, "ref": ref, "worktree": str(worktree),
                  "expected": expected, "archive": archive}

        if intent_path.exists():
            if intent_path.is_symlink() or json.loads(intent_path.read_text()) != wanted:
                raise ValueError("retirement intent does not match")
        else:
            self._arm(experiment, arm)
            if self.resolve(experiment, arm)["commit"] != expected:
                raise ValueError("arm tip changed")
            status = _run(["-C", worktree, "status", "--porcelain=v1", "-z",
                           "--untracked-files=all", "--ignored=matching"], text=False)
            if status.stdout:
                raise ValueError("refusing to retire a dirty worktree")
            archive_path = self._archive_path(experiment, arm, expected)
            if archive and (archive_path.exists() or archive_path.is_symlink()):
                raise ValueError("archive already exists before retirement intent")
            self._write_record(intent_path, wanted)

        if completed_path.exists():
            if completed_path.is_symlink():
                raise ValueError("retirement completion has been replaced")
            complete = json.loads(completed_path.read_text())
            if complete.get("intent") != wanted:
                raise ValueError("retirement completion does not match intent")
            if self._registered_worktree(worktree) or worktree.exists() or worktree.is_symlink():
                raise ValueError("retired worktree has reappeared")
            present = self._git("show-ref", "--verify", "--quiet", ref, check=False)
            if present.returncode != 1:
                raise ValueError("retired ref has reappeared or cannot be checked")
            receipt = self._verify_archive(
                self._archive_path(experiment, arm, expected), ref, expected) if archive else None
            if complete.get("receipt") != receipt:
                raise ValueError("retirement archive does not match completed receipt")
            return receipt

        # Keep the ownership record as a tombstone so this arm ID cannot be reused.
        try:
            owner = json.loads(metadata.read_text())
        except (OSError, ValueError) as error:
            raise ValueError("arm ownership record missing") from error
        if owner.get("ref") != ref or owner.get("worktree") != str(worktree):
            raise ValueError("arm ownership record mismatch")
        current = self._git("rev-parse", "--verify", ref + "^{commit}", check=False)
        if current.returncode or current.stdout.strip() != expected:
            raise ValueError("arm ref missing or changed; retirement is ambiguous")
        registered = self._registered_worktree(worktree)
        if worktree.is_symlink():
            raise ValueError("managed worktree was replaced by a symlink")
        if worktree.exists():
            if not registered:
                raise ValueError("unregistered worktree path; retirement is ambiguous")
            self._arm(experiment, arm)
            status = _run(["-C", worktree, "status", "--porcelain=v1", "-z",
                           "--untracked-files=all", "--ignored=matching"], text=False)
            if status.stdout:
                raise ValueError("refusing to retire a dirty worktree")
        elif registered:
            raise ValueError("registered worktree is missing; retirement is ambiguous")
        elif (not removing_path.exists() or removing_path.is_symlink() or
              json.loads(removing_path.read_text()) != wanted):
            raise ValueError("worktree removed without a matching removal intent")

        receipt = self._archive(experiment, arm, ref, expected) if archive else None
        if registered:
            if removing_path.exists():
                if removing_path.is_symlink() or json.loads(removing_path.read_text()) != wanted:
                    raise ValueError("worktree removal intent does not match")
            else:
                self._write_record(removing_path, wanted)
            self._git("worktree", "remove", worktree)
        self._git("update-ref", "-d", ref, expected)
        self._write_record(completed_path, {"intent": wanted, "receipt": receipt})
        return receipt

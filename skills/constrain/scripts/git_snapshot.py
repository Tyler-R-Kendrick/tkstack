"""Bounded reads of Git's index or working tree, including sparse paths."""
import json
import os
from pathlib import Path
import subprocess

LIMIT = 4 * 1024 * 1024


def git(root, *args, data=None):
    result = subprocess.run(["git", "-C", str(root), *args], input=data, capture_output=True, timeout=20)
    if result.returncode:
        raise ValueError(result.stderr.decode(errors="replace").strip())
    return result.stdout


def unique(items):
    value = {}
    for name, item in items:
        if name in value:
            raise ValueError("Duplicate JSON key: " + name)
        value[name] = item
    return value


class GitSnapshot:
    allow_links = False

    def __init__(self, root, staged=False):
        self.root = Path(git(root, "rev-parse", "--show-toplevel").decode().rstrip("\n")).resolve()
        self.staged = staged
        self.index = {}
        for row in git(self.root, "ls-files", "--stage", "-z").split(b"\0"):
            if row:
                header, name = row.split(b"\t", 1)
                mode, oid, stage = header.decode().split()
                if stage != "0":
                    raise ValueError("Resolve index conflicts before review")
                self.index[name.decode()] = {"mode": mode, "oid": oid}
        self.sparse = set()
        names = set(self.index)
        if not staged:
            self.sparse = {r[2:].decode() for r in git(self.root, "ls-files", "-t", "-z").split(b"\0") if r.startswith(b"S ")}
            names.update(r.decode() for r in git(self.root, "ls-files", "--others", "--exclude-standard", "-z").split(b"\0") if r)
            names = {name for name in names if name in self.sparse or os.path.lexists(self.root / name)}
        self.files = sorted(names)
        self._names = names
        self._sizes = None

    def indexed(self, name):
        return self.staged or (name in self.sparse and not os.path.lexists(self.root / name))

    def size(self, name):
        if name not in self._names:
            raise ValueError("Missing constraint input: " + name)
        path = self.root / name
        if self.indexed(name):
            record = self.index[name]
            mode = record["mode"]
            if mode == "160000":
                raise ValueError("Cannot read submodule as a file: " + name)
            if self._sizes is None:
                oids = sorted({obj["oid"] for obj in self.index.values() if obj["mode"] != "160000"})
                sizes = git(self.root, "cat-file", "--batch-check=%(objectname) %(objectsize)", data="\n".join(oids).encode() + b"\n")
                self._sizes = {oid: int(n) for oid, n in (row.split() for row in sizes.decode().splitlines())}
            size = self._sizes[record["oid"]]
            link = mode == "120000"
        else:
            if any(parent.is_symlink() for parent in path.parents if self.root in parent.parents):
                raise ValueError("Refusing symlinked parent: " + name)
            link = path.is_symlink()
            size = path.lstat().st_size
        if link and not self.allow_links:
            raise ValueError("Constraint inputs cannot be symlinks: " + name)
        if size > LIMIT:
            raise ValueError("Input exceeds 4 MiB: " + name)
        return size

    def read(self, name):
        self.size(name)
        if self.indexed(name):
            return git(self.root, "cat-file", "blob", self.index[name]["oid"])
        path = self.root / name
        if path.is_symlink():
            return os.fsencode(os.readlink(path))
        with path.open("rb") as source:
            data = source.read(LIMIT + 1)
        if len(data) > LIMIT:
            raise ValueError("Input exceeds 4 MiB: " + name)
        return data

    def json(self, name):
        return json.loads(self.read(name), object_pairs_hook=unique)

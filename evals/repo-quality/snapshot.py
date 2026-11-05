#!/usr/bin/env python3
"""Print a bounded repository snapshot for the repo-quality promptfoo provider.

Promptfoo's exec provider cwd is the config directory, and it appends the
rendered prompt, provider options, and call context as extra arguments. Those
arguments are ignored. The repository root comes from this file's location, so
the snapshot does not depend on the process working directory. Output is capped
at 60_000 characters.
"""

import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
LIMIT = 60_000
SKIP_NAMES = {".git", "__pycache__", "node_modules"}
INTERESTING_FILES = {
    "SKILL.md", "README.md", "AGENTS.md", "CLAUDE.md",
    "plugin.json", "marketplace.json", "install.sh",
}
MANIFESTS = (
    ".claude-plugin/marketplace.json",
    ".claude-plugin/plugin.json",
    "harnesses/skills.json",
    "harnesses/integrations.json",
)


def _count_files(directory):
    total = 0
    for dirpath, dirnames, filenames in os.walk(directory, followlinks=False):
        dirnames[:] = [name for name in dirnames if name not in SKIP_NAMES]
        total += len(filenames)
    return total


def _nonblank_lines(path):
    if path.is_symlink():
        return None
    try:
        if path.stat().st_size > 2_000_000:
            return None
        data = path.read_bytes()
    except OSError:
        return None
    if b"\0" in data:
        return None
    return sum(1 for line in data.decode("utf-8", "replace").splitlines() if line.strip())


def _loc_report():
    lines = []
    root_files = 0
    for path in sorted(ROOT.iterdir(), key=lambda item: item.name.lower()):
        if path.name in SKIP_NAMES:
            continue
        if path.is_file() and not path.is_symlink():
            count = _nonblank_lines(path)
            if count:
                root_files += count
            continue
        if not path.is_dir() or path.is_symlink():
            continue
        total = 0
        per_file = []
        for dirpath, dirnames, filenames in os.walk(path, followlinks=False):
            dirnames[:] = [name for name in dirnames if name not in SKIP_NAMES]
            for name in filenames:
                file_path = Path(dirpath) / name
                count = _nonblank_lines(file_path)
                if count:
                    total += count
                    per_file.append((file_path.relative_to(ROOT).as_posix(), count))
        lines.append(f"{path.name}/: {total} non-blank lines")
        if path.name == "scripts":
            for relative, count in sorted(per_file, key=lambda item: (-item[1], item[0])):
                lines.append(f"  {relative}: {count}")
    lines.insert(0, f"(top-level files): {root_files} non-blank lines")
    return "\n".join(lines)


def _tree():
    lines = []

    def walk(directory):
        children = sorted(directory.iterdir(), key=lambda item: (item.is_file(), item.name.lower()))
        for child in children:
            if child.name in SKIP_NAMES:
                continue
            relative = child.relative_to(ROOT).as_posix()
            if child.is_symlink():
                lines.append(f"{relative} -> {os.readlink(child)}")
                continue
            if child.is_dir():
                # Vendor snapshots dominate the tree. Keep one line per package.
                if child.name == "vendor" and directory == ROOT:
                    lines.append(f"{relative}/ ({_count_files(child)} files, packages only)")
                    packages = sorted(
                        (entry for entry in child.iterdir() if entry.is_dir() and not entry.is_symlink()),
                        key=lambda entry: entry.name.lower(),
                    )
                    for package in packages:
                        lines.append(
                            f"{relative}/{package.name}/ ({_count_files(package)} files)"
                        )
                    continue
                lines.append(f"{relative}/ ({_count_files(child)} files)")
                walk(child)
            elif child.name in INTERESTING_FILES or directory == ROOT:
                lines.append(relative)

    walk(ROOT)
    return "\n".join(lines)


def _read(relative, cap=20_000):
    path = ROOT / relative
    if not path.is_file():
        return f"ABSENT: {relative}"
    text = path.read_text(encoding="utf-8", errors="replace")
    if len(text) > cap:
        return text[:cap] + f"\n[truncated {relative}]\n"
    return text


def _docs():
    docs = ROOT / "docs"
    if not docs.is_dir():
        return "ABSENT: docs/"
    lines = []
    for path in sorted(item for item in docs.rglob("*") if item.is_file()):
        if any(part in SKIP_NAMES for part in path.parts):
            continue
        relative = path.relative_to(ROOT).as_posix()
        title = ""
        if path.suffix.lower() == ".md":
            try:
                for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
                    if line.startswith("#"):
                        title = " — " + line.lstrip("#").strip()
                        break
            except OSError:
                title = ""
        lines.append(relative + title)
    return "\n".join(lines)


def _manifests():
    parts = []
    for relative in MANIFESTS:
        parts.append(f"### {relative}\n{_read(relative, cap=12_000)}")
    return "\n\n".join(parts)


def snapshot():
    priority = [
        "Repository snapshot. Paths are relative to the repo root. "
        "Use only paths and text that appear below as evidence.",
        "## LOC per top-level directory\n" + _loc_report(),
        "## README.md\n" + _read("README.md"),
        "## install.sh\n" + _read("install.sh"),
        "## AGENTS.md\n" + _read("AGENTS.md"),
        "## harnesses/README.md\n" + _read("harnesses/README.md"),
        "## Manifests\n" + _manifests(),
        "## Docs\n" + _docs(),
    ]
    body = "\n\n".join(priority)
    tree = "## File tree\n" + _tree()
    marker = "\n[truncated]\n"
    if len(body) + 2 + len(tree) <= LIMIT:
        text = body + "\n\n" + tree
    elif len(body) + len(marker) >= LIMIT:
        text = body[: LIMIT - len(marker)] + marker
    else:
        room = LIMIT - len(body) - 2 - len(marker)
        text = body + "\n\n" + tree[:room] + marker
    if len(text) > LIMIT:
        text = text[: LIMIT - len(marker)] + marker
    return text


def main(argv=None):
    # argv is the promptfoo prompt plus options and context JSON. The snapshot
    # is the provider output, so none of those arguments are read.
    del argv
    text = snapshot()
    sys.stdout.write(text)
    if not text.endswith("\n"):
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

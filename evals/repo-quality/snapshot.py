#!/usr/bin/env python3
"""Print a bounded repository snapshot for the repo-quality promptfoo provider.

Promptfoo's exec provider cwd is the config directory, and it appends the
rendered prompt, provider options, and call context as extra arguments. Those
arguments are ignored. The repository root is this file's parents[2], so the
snapshot does not depend on the process working directory. Output is capped
at 60_000 characters. Home directories and secret-like values are redacted.
"""

import os
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
LIMIT = 60_000
READ_CAP = 8_000
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
OWNED_SKILL_ROOTS = ("skills", ".agents/skills")
_ASSIGNED_SECRET = re.compile(
    r"(?i)\b(api[_-]?key|secret|token|password|passwd|authorization|bearer)"
    r"(\s*[:=]\s*)([^\s,;\"']{8,})"
)
_KEYLIKE = re.compile(
    r"\b(?:sk-[A-Za-z0-9]{16,}|ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}"
    r"|AKIA[0-9A-Z]{16}|xai-[A-Za-z0-9_-]{16,})\b"
)
_PRIVATE_KEY = re.compile(
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----",
    re.S,
)


def redact(text):
    """Replace home-directory prefixes and secret-like values."""
    homes = []
    for key in ("HOME", "USERPROFILE"):
        value = os.environ.get(key, "")
        if len(value) > 1:
            homes.append(value)
    try:
        homes.append(str(Path.home()))
    except (OSError, RuntimeError):
        pass
    for home in sorted(set(homes), key=len, reverse=True):
        text = text.replace(home, "$HOME")
    text = _PRIVATE_KEY.sub("[redacted]", text)
    text = _ASSIGNED_SECRET.sub(r"\1\2[redacted]", text)
    text = _KEYLIKE.sub("[redacted]", text)
    return text


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
                if child.name == "vendor" and directory == ROOT:
                    lines.append(f"{relative}/ ({_count_files(child)} files, packages only)")
                    packages = sorted(
                        (entry for entry in child.iterdir() if entry.is_dir() and not entry.is_symlink()),
                        key=lambda entry: entry.name.lower(),
                    )
                    for package in packages:
                        lines.append(f"{relative}/{package.name}/ ({_count_files(package)} files)")
                    continue
                lines.append(f"{relative}/ ({_count_files(child)} files)")
                walk(child)
            elif child.name in INTERESTING_FILES or directory == ROOT:
                lines.append(relative)

    walk(ROOT)
    return "\n".join(lines)


def _read(relative, cap=READ_CAP):
    path = ROOT / relative
    if not path.is_file():
        return f"ABSENT: {relative}"
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as error:
        return f"UNREADABLE: {relative} ({error})"
    if len(text) > cap:
        return text[:cap] + f"\n[truncated {relative}]\n"
    return text


def _read_ends(relative, cap=READ_CAP):
    """Keep the start and the end so a long file's closing sections survive."""
    path = ROOT / relative
    if not path.is_file():
        return f"ABSENT: {relative}"
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as error:
        return f"UNREADABLE: {relative} ({error})"
    if len(text) <= cap:
        return text
    head = cap * 2 // 3
    marker = f"\n[truncated middle of {relative}]\n"
    tail = cap - head - len(marker)
    if tail < 200:
        return text[:cap] + f"\n[truncated {relative}]\n"
    return text[:head] + marker + text[-tail:]


def _frontmatter_fields(text):
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    end = None
    for index, line in enumerate(lines[1:], 1):
        if line.strip() == "---":
            end = index
            break
    if end is None:
        return None
    fields = {}
    for line in lines[1:end]:
        match = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if match and match.group(1) not in fields:
            fields[match.group(1)] = match.group(2).strip()
    return fields


def _skill_frontmatter():
    blocks = []
    for relative_root in OWNED_SKILL_ROOTS:
        base = ROOT / relative_root
        if not base.is_dir():
            blocks.append(f"ABSENT: {relative_root}")
            continue
        paths = sorted(
            path for path in base.rglob("SKILL.md")
            if path.is_file() and not any(part in SKIP_NAMES for part in path.parts)
        )
        if not paths:
            blocks.append(f"none under {relative_root}")
            continue
        for path in paths:
            relative = path.relative_to(ROOT).as_posix()
            try:
                fields = _frontmatter_fields(path.read_text(encoding="utf-8", errors="replace"))
            except OSError:
                fields = None
            if not fields:
                blocks.append(f"### {relative}\nno frontmatter")
                continue
            name = fields.get("name", "")
            description = fields.get("description", "")[:240]
            blocks.append(f"### {relative}\nname: {name}\ndescription: {description}")
    return "\n\n".join(blocks)


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
        parts.append(f"### {relative}\n{_read(relative, cap=READ_CAP)}")
    return "\n\n".join(parts)


def _fit(required, extras):
    """Keep required sections. Add later sections only while under LIMIT."""
    text = redact(required)
    marker = "\n[truncated]\n"
    if len(text) > LIMIT:
        return text[: LIMIT - len(marker)] + marker
    for extra in extras:
        piece = redact(extra)
        candidate = text + "\n\n" + piece
        if len(candidate) <= LIMIT:
            text = candidate
            continue
        room = LIMIT - len(text) - 2 - len(marker)
        if room > 200:
            text = text + "\n\n" + piece[:room] + marker
        break
    if len(text) > LIMIT:
        text = text[: LIMIT - len(marker)] + marker
    return text


def snapshot():
    required = "\n\n".join([
        "Repository snapshot. Paths are relative to the repo root. "
        "Use only paths and text that appear below as evidence. "
        "Home directories and secret-like values are redacted.",
        "## LOC per top-level directory\n" + _loc_report(),
        "## File tree\n" + _tree(),
        "## Manifests\n" + _manifests(),
        "## SKILL.md frontmatter\n"
        "Owned skills under skills/ and .agents/skills/. "
        "Each block is that file's name and description.\n" + _skill_frontmatter(),
        "## docs/skill-marketplace.md\n" + _read("docs/skill-marketplace.md"),
        "## install.sh\n" + _read("install.sh"),
        "## harnesses/README.md\n" + _read("harnesses/README.md"),
    ])
    extras = [
        "## README.md\n" + _read_ends("README.md"),
        "## AGENTS.md\n" + _read_ends("AGENTS.md"),
        "## Docs\n" + _docs(),
    ]
    return _fit(required, extras)


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

#!/usr/bin/env python3
"""Print a bounded repository snapshot for the repo-quality promptfoo provider.

Promptfoo's exec provider cwd is the config directory, and it appends the
rendered prompt, provider options, and call context as extra arguments. Those
arguments are ignored. The repository root is this file's parents[2], so the
snapshot does not depend on the process working directory. Home directories
and secret-like values are redacted.

Promptfoo's exec grader (`exec:python3 judge.py`) passes the rendered grading
prompt as one argv string and a context JSON as another. That context embeds
the snapshot twice: inside the grading prompt, and again as `vars.output`.
JSON escaping makes the context about 2.2 times the snapshot. Linux
MAX_ARG_STRLEN is 131072 bytes, so a 60_000 character snapshot overflows the
context argument (`spawn E2BIG`). Output stays at or below LIMIT encoded
bytes, safely under 100 KiB.

The snapshot lists git-tracked files (`git ls-files`). A generated tree such
as `.tkstack/runtime` is omitted. When git cannot be run, a walk skips `.git`,
`__pycache__`, `node_modules`, `.tkstack`, `.venv`, and `venv`. README.md is
placed before the file tree so truncating a long tree keeps the README.
Long file excerpts are capped. Generated lock JSON is summarized instead of
inlined, and download records (urls, hashes) inside manifests are omitted.
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
# Encoded-byte ceiling. A snapshot at this size keeps promptfoo's doubled,
# JSON-escaped context argument under MAX_ARG_STRLEN with margin. See the
# module docstring. The public test also requires the snapshot itself to stay
# under 100_000 bytes.
LIMIT = 52_000
READ_CAP = 5_000
# Head includes ## Install options through --uninstall and the verify-first
# alternative. The file's later ## Maintain section does not fit this cap;
# ## Develop, which is inside the head, already shows preview, test, and docs.
README_CAP = 10_800
README_HEAD = 10_800
README_TAIL = 0
# Head keeps the uv pin and archive checks. Tail keeps main() and the call
# on the last line, inside the same encoded budget as a flat 5_000 excerpt.
INSTALL_CAP = 5_000
INSTALL_HEAD = 4_550
INSTALL_TAIL = 400
AGENTS_CAP = 4_200
AGENTS_HEAD = 1_700
AGENTS_TAIL = 2_300
MANIFEST_CAP = 1_600
DOC_CAP = 2_100
HARNESS_README_CAP = 2_000
JSON_STRING_CAP = 180
_LOCK_NAMES = {
    "package-lock.json",
    "npm-shrinkwrap.json",
    "sources.lock.json",
    "workflow.lock.json",
}
_OMIT_JSON_KEYS = {"sha256", "integrity", "resolved", "archive_member"}
_DOWNLOAD_KEYS = {"url", "sha256", "integrity", "resolved", "archive_member"}
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
# Used only when `git ls-files` cannot be run. `.tkstack` is skipped whole
# because a CI venv is created at `.tkstack/runtime` before the tests.
FALLBACK_SKIP = {".git", "__pycache__", "node_modules", ".tkstack", ".venv", "venv"}
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


def _git_ls_files():
    try:
        completed = subprocess.run(
            ["git", "-C", str(ROOT), "ls-files", "-z"],
            capture_output=True,
            timeout=60,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if completed.returncode != 0:
        return None
    paths = []
    for item in completed.stdout.split(b"\0"):
        if item:
            paths.append(item.decode("utf-8", "surrogateescape"))
    return paths


def _fallback_files():
    paths = []
    for dirpath, dirnames, filenames in os.walk(ROOT, followlinks=False):
        dirnames[:] = [name for name in dirnames if name not in FALLBACK_SKIP]
        for name in filenames:
            path = Path(dirpath) / name
            if name in FALLBACK_SKIP:
                continue
            paths.append(path.relative_to(ROOT).as_posix())
    return paths


def _tracked_files():
    """Repo-relative paths of files the snapshot may mention."""
    listed = _git_ls_files()
    if listed is not None:
        return listed
    return _fallback_files()


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


def _loc_report(paths):
    per_top = {}
    root_files = 0
    for relative in paths:
        path = ROOT / relative
        if path.is_symlink():
            count = 0
        else:
            count = _nonblank_lines(path) or 0
        if "/" not in relative:
            root_files += count
            continue
        top = relative.split("/", 1)[0]
        per_top.setdefault(top, []).append((relative, count))
    lines = [f"(top-level files): {root_files} non-blank lines"]
    for name in sorted(per_top, key=str.lower):
        entries = per_top[name]
        total = sum(count for _, count in entries)
        lines.append(f"{name}/: {total} non-blank lines")
        if name in ("scripts", "src"):
            for relative, count in sorted(entries, key=lambda item: (-item[1], item[0])):
                if count:
                    lines.append(f"  {relative}: {count}")
    return "\n".join(lines)


def _tree(paths):
    file_set = set(paths)
    counts = {}
    child_names = {}
    for relative in paths:
        parts = relative.split("/")
        for index in range(len(parts)):
            parent = "/".join(parts[:index])
            counts[parent] = counts.get(parent, 0) + 1
            child_names.setdefault(parent, set()).add(parts[index])

    lines = []

    def walk(directory):
        names = child_names.get(directory, ())

        def sort_key(name):
            relative = f"{directory}/{name}" if directory else name
            return (relative not in child_names, name.lower())

        for name in sorted(names, key=sort_key):
            relative = f"{directory}/{name}" if directory else name
            path = ROOT / relative
            if path.is_symlink():
                try:
                    target = os.readlink(path)
                except OSError as error:
                    target = f"unreadable ({error})"
                lines.append(f"{relative} -> {target}")
                continue
            if relative in child_names or path.is_dir():
                if name == "vendor" and directory == "":
                    lines.append(f"{relative}/ ({counts.get(relative, 0)} files, packages only)")
                    packages = sorted(
                        (
                            package for package in child_names.get(relative, ())
                            if (ROOT / relative / package).is_dir()
                            and not (ROOT / relative / package).is_symlink()
                        ),
                        key=str.lower,
                    )
                    for package in packages:
                        package_relative = f"{relative}/{package}"
                        lines.append(
                            f"{package_relative}/ ({counts.get(package_relative, 0)} files)"
                        )
                    continue
                lines.append(f"{relative}/ ({counts.get(relative, 0)} files)")
                # Deep package internals are counts only. Every SKILL.md path is
                # listed in its own section, including paths below this cutoff.
                if relative.count("/") >= 2:
                    continue
                walk(relative)
            elif name in INTERESTING_FILES or directory == "":
                if relative in file_set:
                    lines.append(relative)

    walk("")
    return "\n".join(lines)


def _is_lockfile(relative):
    name = relative.rsplit("/", 1)[-1]
    return name in _LOCK_NAMES or name.endswith(".lock")


def _compact_json_value(value):
    """Drop lockfile bodies, download hashes, and very long strings."""
    if isinstance(value, dict):
        if "packages" in value and ("lockfileVersion" in value or "dependencies" in value):
            summary = {"_excerpt": "lockfile omitted"}
            for key in ("name", "version"):
                if key in value and not isinstance(value[key], (dict, list)):
                    summary[key] = value[key]
            return summary
        if "sha256" in value and "url" in value and set(value) <= _DOWNLOAD_KEYS:
            return "[download record omitted]"
        compacted = {}
        for key, item in value.items():
            if key in _OMIT_JSON_KEYS:
                continue
            compacted[key] = _compact_json_value(item)
        return compacted
    if isinstance(value, list):
        return [_compact_json_value(item) for item in value]
    if isinstance(value, str) and len(value) > JSON_STRING_CAP:
        return value[:JSON_STRING_CAP] + "…"
    return value


def _compact_json(text):
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        return text
    compacted = json.dumps(_compact_json_value(value), indent=2, ensure_ascii=False) + "\n"
    return compacted if len(compacted) < len(text) else text


def _load_text(relative):
    path = ROOT / relative
    try:
        return path.read_text(encoding="utf-8", errors="replace"), None
    except OSError as error:
        return None, f"UNREADABLE: {relative} ({error})"


def _read(relative, tracked, cap=READ_CAP):
    if relative not in tracked:
        return f"ABSENT: {relative}"
    text, error = _load_text(relative)
    if error:
        return error
    if _is_lockfile(relative):
        return f"[omitted generated lockfile {relative}, {len(text.encode())} bytes]\n"
    if relative.endswith(".json"):
        text = _compact_json(text)
    if len(text) > cap:
        return text[:cap] + f"\n[truncated {relative}]\n"
    return text


def _read_ends(relative, tracked, cap, head, tail):
    """Keep the start and end of a long file inside cap."""
    if relative not in tracked:
        return f"ABSENT: {relative}"
    text, error = _load_text(relative)
    if error:
        return error
    if len(text) <= cap:
        return text
    marker = f"\n[truncated middle of {relative}]\n"
    if head + len(marker) + tail > cap:
        tail = max(0, cap - head - len(marker))
    if tail <= 0:
        return text[:cap] + f"\n[truncated {relative}]\n"
    return text[:head] + marker + text[-tail:]


def _skill_paths(paths):
    """Every tracked SKILL.md, including paths the file tree collapses."""
    names = sorted(
        relative for relative in paths
        if relative == "SKILL.md" or relative.endswith("/SKILL.md")
    )
    return "\n".join(names) if names else "none"


def _source_pins():
    """name, version, and revision for each sources.lock.json source."""
    relative = "sources.lock.json"
    text, error = _load_text(relative)
    if error:
        return error
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        return f"UNREADABLE: {relative}"
    sources = value.get("sources") if isinstance(value, dict) else None
    if not isinstance(sources, dict):
        return "ABSENT: sources.lock.json sources"
    lines = ["name version revision"]
    for name in sorted(sources):
        source = sources[name]
        if not isinstance(source, dict):
            continue
        version = source.get("version") or "-"
        revision = source.get("revision") or "-"
        lines.append(f"{name} {version} {revision}")
    return "\n".join(lines)


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


def _skill_frontmatter(paths):
    blocks = []
    path_set = set(paths)
    for relative_root in OWNED_SKILL_ROOTS:
        base = ROOT / relative_root
        if not base.is_dir():
            blocks.append(f"ABSENT: {relative_root}")
            continue
        prefix = relative_root + "/"
        matched = sorted(
            relative for relative in path_set
            if relative.rsplit("/", 1)[-1] == "SKILL.md"
            and (relative == prefix + "SKILL.md" or relative.startswith(prefix))
        )
        if not matched:
            blocks.append(f"none under {relative_root}")
            continue
        for relative in matched:
            path = ROOT / relative
            try:
                fields = _frontmatter_fields(path.read_text(encoding="utf-8", errors="replace"))
            except OSError:
                fields = None
            if not fields:
                blocks.append(f"### {relative}\nno frontmatter")
                continue
            name = fields.get("name", "")
            description = fields.get("description", "")[:80]
            blocks.append(f"### {relative}\nname: {name}\ndescription: {description}")
    return "\n\n".join(blocks)


def _docs(paths):
    docs = ROOT / "docs"
    if not docs.is_dir():
        return "ABSENT: docs/"
    lines = []
    for relative in sorted(path for path in paths if path == "docs" or path.startswith("docs/")):
        path = ROOT / relative
        if not path.is_file() or path.is_symlink():
            continue
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


def _manifests(tracked):
    parts = []
    for relative in MANIFESTS:
        cap = READ_CAP if relative.endswith("skills.json") or relative.endswith("plugin.json") else MANIFEST_CAP
        parts.append(f"### {relative}\n{_read(relative, tracked, cap)}")
    return "\n\n".join(parts)


def _within(text):
    """True when both the character count and the encoded size fit LIMIT."""
    return len(text) <= LIMIT and len(text.encode()) <= LIMIT


def _cut(text):
    marker = "\n[truncated]\n"
    if _within(text):
        return text
    lo, hi = 0, len(text)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if _within(text[:mid] + marker):
            lo = mid
        else:
            hi = mid - 1
    return text[:lo] + marker


def _fit(required, extras):
    """Keep required sections. Add later sections only while under LIMIT."""
    text = redact(required)
    if not _within(text):
        return _cut(text)
    marker = "\n[truncated]\n"
    for extra in extras:
        piece = redact(extra)
        candidate = text + "\n\n" + piece
        if _within(candidate):
            text = candidate
            continue
        room = LIMIT - len(text) - 2 - len(marker)
        if room > 200:
            chunk = piece[:room]
            newline = chunk.rfind("\n")
            if newline > 200:
                chunk = chunk[:newline]
            trimmed = text + "\n\n" + chunk + marker
            text = trimmed if _within(trimmed) else _cut(trimmed)
        break
    if not _within(text):
        text = _cut(text)
    return text


def snapshot():
    paths = _tracked_files()
    tracked = set(paths)
    # README, install.sh, manifests, docs headings, and the LOC table are
    # required and come before the file tree. A long tree is truncated from
    # the end of this blob, so that evidence stays in the prefix.
    required = "\n\n".join([
        "Repository snapshot. Paths are relative to the repo root. "
        "Use only paths and text that appear below as evidence. "
        "Home directories and secret-like values are redacted. "
        "Only git-tracked files are listed. "
        "Generated lockfiles are omitted and long excerpts are capped.",
        "## LOC per top-level directory\n" + _loc_report(paths),
        "## README.md\n" + _read_ends("README.md", tracked, README_CAP, README_HEAD, README_TAIL),
        "## install.sh\n" + _read_ends("install.sh", tracked, INSTALL_CAP, INSTALL_HEAD, INSTALL_TAIL),
        "## Source pins\n" + _source_pins(),
        "## Manifests\n" + _manifests(tracked),
        "## Docs\n" + _docs(paths),
        "## SKILL.md paths\n" + _skill_paths(paths),
        "## File tree\n" + _tree(paths),
        "## SKILL.md frontmatter\n"
        "Owned skills under skills/ and .agents/skills/. "
        "Each block is that file's name and description.\n" + _skill_frontmatter(paths),
        "## docs/skill-marketplace.md\n" + _read("docs/skill-marketplace.md", tracked, DOC_CAP),
        "## harnesses/README.md\n" + _read("harnesses/README.md", tracked, HARNESS_README_CAP),
    ])
    extras = [
        "## AGENTS.md\n" + _read_ends("AGENTS.md", tracked, AGENTS_CAP, AGENTS_HEAD, AGENTS_TAIL),
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

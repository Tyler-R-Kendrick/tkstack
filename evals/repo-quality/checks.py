#!/usr/bin/env python3
"""Deterministic repo-quality checks.

Each check returns one JSON object. The process prints a JSON array and exits
1 when any check fails. Limits are best-practice ceilings, so a healthy
checkout can still fail them.
"""

import json
import re
import sys
from pathlib import Path


SCRIPTS_LOC_LIMIT = 1500
TOP_LEVEL_FILE_LIMIT = 12
QUICKSTART_COMMAND_LIMIT = 1
HARNESSES = (
    "claude",
    "codex",
    "cursor",
    "copilot",
    "grok",
    "kimi",
    "muse",
    "opencode",
    "t3code",
)
# "T3 Code" and "open-code" are the same harnesses as the metric tokens.
HARNESS_PATTERNS = {
    "claude": r"\bclaude\b",
    "codex": r"\bcodex\b",
    "cursor": r"\bcursor\b",
    "copilot": r"\bcopilot\b",
    "grok": r"\bgrok\b",
    "kimi": r"\bkimi\b",
    "muse": r"\bmuse\b",
    "opencode": r"\bopen-?code\b",
    "t3code": r"\bt3code\b|\bt3-code\b|\bt3 code\b",
}
OWNED_SKILL_ROOTS = ("skills", ".agents/skills")
MANIFESTS = (
    ".claude-plugin/marketplace.json",
    ".claude-plugin/plugin.json",
)
SKIP_NAMES = {".git", "__pycache__", "node_modules"}


def repo_root():
    return Path(__file__).resolve().parents[2]


def result(name, metric, ok, value, limit, explanation, evidence):
    return {
        "name": name,
        "metric": metric,
        "pass": ok,
        "value": value,
        "limit": limit,
        "explanation": explanation,
        "evidence": evidence,
    }


def _nonblank_lines(path):
    """Count non-blank lines. Skip binaries and files over 2 MB."""
    if path.is_symlink():
        return None
    try:
        size = path.stat().st_size
    except OSError:
        return None
    if size > 2_000_000:
        return None
    try:
        data = path.read_bytes()
    except OSError:
        return None
    if b"\0" in data:
        return None
    return sum(1 for line in data.decode("utf-8", "replace").splitlines() if line.strip())


def _iter_files(directory):
    if not directory.is_dir():
        return
    for path in sorted(directory.rglob("*")):
        if not path.is_file() or any(part in SKIP_NAMES for part in path.parts):
            continue
        yield path


def scripts_loc(root):
    """Ceiling on glue under scripts/. Comments stay in the count."""
    directory = root / "scripts"
    per_file = []
    for path in _iter_files(directory):
        count = _nonblank_lines(path)
        if count is None:
            continue
        per_file.append((path.relative_to(root).as_posix(), count))
    total = sum(count for _, count in per_file)
    largest = sorted(per_file, key=lambda item: (-item[1], item[0]))[:8]
    evidence = [f"{path}: {count} non-blank lines" for path, count in largest]
    if not directory.is_dir():
        evidence = ["scripts/ is absent"]
    ok = total <= SCRIPTS_LOC_LIMIT
    explanation = (
        f"scripts/ has {total} non-blank lines. "
        f"The best-practice ceiling for dotfiles glue is {SCRIPTS_LOC_LIMIT}."
    )
    return result(
        "scripts_loc", "minimal_code", ok, total, SCRIPTS_LOC_LIMIT, explanation, evidence
    )


def _section(text, heading):
    lines = text.splitlines()
    start = None
    level = None
    pattern = re.compile(heading, re.I)
    for index, line in enumerate(lines):
        match = re.match(r"^(#+)\s+(.*\S)\s*$", line)
        if match and pattern.search(match.group(2)):
            start = index
            level = len(match.group(1))
            break
    if start is None:
        return None
    body = []
    for line in lines[start + 1:]:
        match = re.match(r"^(#+)\s+", line)
        if match and len(match.group(1)) <= level:
            break
        body.append(line)
    return "\n".join(body)


def _shell_commands(block):
    commands = []
    pending = ""
    for raw in block.splitlines():
        stripped = raw.strip()
        if pending:
            pending = pending[:-1].rstrip() + " " + re.sub(r"^[$>]\s*", "", stripped)
            if not stripped.endswith("\\"):
                if pending.strip():
                    commands.append(pending.strip())
                pending = ""
            continue
        if not stripped or stripped.startswith("#"):
            continue
        stripped = re.sub(r"^[$>]\s*", "", stripped)
        if not stripped:
            continue
        if stripped.endswith("\\"):
            pending = stripped
        else:
            commands.append(stripped)
    if pending:
        commands.append(pending[:-1].strip())
    return commands


def _first_shell_block(section):
    fence = re.compile(r"^```([^\n]*)\n(.*?)^```[ \t]*$", re.M | re.S)
    for match in fence.finditer(section):
        info = match.group(1).strip().split()
        language = info[0].lower() if info else ""
        if language in {"", "sh", "bash", "shell", "console", "zsh"}:
            return match.group(2)
    return None


def quickstart_commands(root):
    """The first shell block of the install/quickstart section is the happy path."""
    readme = root / "README.md"
    if not readme.is_file():
        return result(
            "quickstart_commands", "minimal_setup", False, None, QUICKSTART_COMMAND_LIMIT,
            "README.md has no install quickstart.", ["README.md is absent"],
        )
    text = readme.read_text(encoding="utf-8", errors="replace")
    section = _section(text, r"quickstart|getting started|install")
    if section is None:
        return result(
            "quickstart_commands", "minimal_setup", False, None, QUICKSTART_COMMAND_LIMIT,
            "README.md has no Install, Quickstart, or Getting started section.",
            ["README.md"],
        )
    block = _first_shell_block(section)
    commands = _shell_commands(block) if block is not None else []
    count = len(commands)
    ok = count <= QUICKSTART_COMMAND_LIMIT
    explanation = (
        f"The README quickstart has {count} commands. "
        f"Best practice is a single install command (limit {QUICKSTART_COMMAND_LIMIT})."
    )
    evidence = [f"README.md: {command}" for command in commands] or [
        "README.md: no shell block in the install/quickstart section"
    ]
    return result(
        "quickstart_commands", "minimal_setup", ok, count, QUICKSTART_COMMAND_LIMIT,
        explanation, evidence,
    )


def _frontmatter(text):
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
    key = None
    chunks = []

    def finish():
        if key is not None:
            value = "\n".join(chunks).strip()
            if value in {"|", ">", "|-", ">-", "|+", ">+"}:
                value = ""
            fields[key] = value

    for line in lines[1:end]:
        if key is not None and (line.startswith(" ") or line.startswith("\t")):
            chunks.append(line.strip())
            continue
        match = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if not match:
            key = None
            continue
        finish()
        key = match.group(1)
        chunks = [match.group(2)]
    finish()
    return fields


def _json_object(path):
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        return None, f"invalid JSON ({error.msg} at line {error.lineno})"
    except OSError as error:
        return None, str(error)
    if not isinstance(loaded, dict):
        return None, "JSON value is not an object"
    return loaded, "valid JSON object"


def marketplace_manifests(root):
    """Marketplace and plugin manifests, plus owned skill frontmatter."""
    evidence = []
    problems = []
    for relative in MANIFESTS:
        path = root / relative
        if not path.is_file():
            problems.append(f"missing {relative}")
            evidence.append(f"absent: {relative}")
            continue
        _, detail = _json_object(path)
        if detail != "valid JSON object":
            problems.append(f"{relative}: {detail}")
        evidence.append(f"{relative}: {detail}")
    skill_files = []
    for relative in OWNED_SKILL_ROOTS:
        base = root / relative
        if base.is_dir():
            skill_files.extend(
                path for path in base.rglob("SKILL.md")
                if path.is_file() and not any(part in SKIP_NAMES for part in path.parts)
            )
    missing = []
    for path in sorted(skill_files):
        try:
            fields = _frontmatter(path.read_text(encoding="utf-8", errors="replace"))
        except OSError:
            fields = None
        name = (fields or {}).get("name", "").strip()
        description = (fields or {}).get("description", "").strip()
        if not name or not description:
            missing.append(path.relative_to(root).as_posix())
    if not skill_files:
        problems.append("no owned SKILL.md files")
        evidence.append("scope: skills/**/SKILL.md and .agents/skills/**/SKILL.md")
    elif missing:
        problems.append(f"{len(missing)} SKILL.md files lack name and description frontmatter")
        evidence.extend(missing[:30])
    else:
        evidence.append(
            f"{len(skill_files)} SKILL.md files under skills/ and .agents/skills/ "
            "have name and description"
        )
    ok = not problems
    explanation = (
        "Marketplace install needs valid .claude-plugin/marketplace.json and "
        ".claude-plugin/plugin.json, and name plus description frontmatter on every owned skill. "
        + ("Those files are present." if ok else " ".join(problems) + ".")
    )
    return result(
        "marketplace_manifests", "marketplace_install", ok,
        "ok" if ok else "; ".join(problems),
        "valid marketplace.json, valid plugin.json, skill name+description frontmatter",
        explanation, evidence,
    )


def _mention_files(root):
    paths = []
    readme = root / "harnesses" / "README.md"
    if readme.is_file():
        paths.append(readme)
    docs = root / "docs"
    if docs.is_dir():
        paths.extend(
            path for path in sorted(docs.rglob("*"))
            if path.is_file() and not any(part in SKIP_NAMES for part in path.parts)
        )
    return paths


def harness_coverage(root):
    """Each of the nine harnesses is named in harnesses/README.md or docs/."""
    files = _mention_files(root)
    texts = []
    for path in files:
        try:
            data = path.read_bytes()
        except OSError:
            continue
        if b"\0" in data[:1024]:
            continue
        texts.append((path.relative_to(root).as_posix(), data.decode("utf-8", "replace")))
    evidence = []
    found = 0
    for name in HARNESSES:
        pattern = re.compile(HARNESS_PATTERNS[name], re.I)
        hit = next((relative for relative, text in texts if pattern.search(text)), None)
        if hit:
            found += 1
            evidence.append(f"{name}: {hit}")
        else:
            evidence.append(f"{name}: not mentioned in harnesses/README.md or docs/")
    ok = found == len(HARNESSES)
    explanation = (
        f"{found} of {len(HARNESSES)} harnesses "
        "(claude, codex, cursor, copilot, grok, kimi, muse, opencode, t3code) "
        "are mentioned in harnesses/README.md or docs/."
    )
    return result(
        "harness_coverage", "cross_harness", ok, found, len(HARNESSES), explanation, evidence
    )


def _dispatched_python(root, text):
    match = re.search(r"scripts/([A-Za-z0-9_]+\.py)", text)
    if not match:
        return None
    path = root / "scripts" / match.group(1)
    return path if path.is_file() else None


def install_flags(root):
    """install.sh supports --dry-run and --uninstall, directly or via the script it execs."""
    install = root / "install.sh"
    blobs = []
    evidence = []
    if not install.is_file():
        return result(
            "install_flags", "dotfiles", False, [], ["--dry-run", "--uninstall"],
            "install.sh is absent, so it has neither --dry-run nor uninstall.",
            ["absent: install.sh"],
        )
    text = install.read_text(encoding="utf-8", errors="replace")
    blobs.append(text)
    evidence.append("install.sh")
    dispatched = _dispatched_python(root, text)
    if dispatched is not None:
        blobs.append(dispatched.read_text(encoding="utf-8", errors="replace"))
        evidence.append(dispatched.relative_to(root).as_posix())
    blob = "\n".join(blobs)
    supported = []
    if "--dry-run" in blob:
        supported.append("--dry-run")
    else:
        evidence.append("missing --dry-run")
    if "--uninstall" in blob:
        supported.append("--uninstall")
    else:
        evidence.append("missing --uninstall")
    ok = supported == ["--dry-run", "--uninstall"]
    found = ", ".join(supported) if supported else "none"
    explanation = (
        "install.sh must accept --dry-run and --uninstall, in that file or in the "
        f"Python entrypoint it execs. Supported flags: {found}."
    )
    return result(
        "install_flags", "dotfiles", ok, supported, ["--dry-run", "--uninstall"],
        explanation, evidence,
    )


def top_level_files(root):
    """Countable root files. The worktree git pointer is not a source file."""
    names = sorted(
        path.name for path in root.iterdir()
        if path.is_file() and path.name not in SKIP_NAMES
    )
    count = len(names)
    ok = count <= TOP_LEVEL_FILE_LIMIT
    explanation = (
        f"The repository root has {count} files. "
        f"Best practice for a scannable dotfiles root is at most {TOP_LEVEL_FILE_LIMIT}."
    )
    return result(
        "top_level_files", "conventions", ok, count, TOP_LEVEL_FILE_LIMIT, explanation, names
    )


CHECKS = (
    scripts_loc,
    quickstart_commands,
    marketplace_manifests,
    harness_coverage,
    install_flags,
    top_level_files,
)


def run_checks(root=None):
    root = repo_root() if root is None else Path(root)
    return [check(root) for check in CHECKS]


def main():
    results = run_checks()
    json.dump(results, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0 if all(item["pass"] for item in results) else 1


if __name__ == "__main__":
    sys.exit(main())

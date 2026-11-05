#!/usr/bin/env python3
"""Deterministic repo-quality checks.

Each check returns one JSON object. The process prints a JSON array and exits
1 when any check fails. Limits are best-practice ceilings, so a healthy
checkout can still fail them.
"""

import json
import os
import re
import subprocess
import sys
import tempfile
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
# Path components that name a harness. "open-code" and "t3-code" are the same
# harnesses as the metric tokens. A prose mention is not placement.
HARNESS_PATH_NAMES = {
    "claude": "claude",
    "codex": "codex",
    "cursor": "cursor",
    "copilot": "copilot",
    "grok": "grok",
    "kimi": "kimi",
    "muse": "muse",
    "opencode": "opencode",
    "open-code": "opencode",
    "t3code": "t3code",
    "t3-code": "t3code",
}
_HEADING = re.compile(
    r"(?i)(?<!un)(?<!un-)(?<!un )\b(?:quickstart|getting started|install)\b"
)
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


def _heading_text(line, following):
    """Return (level, text) for an ATX or Setext heading, else None."""
    match = re.match(r"^(#+)[ \t]*(.*\S)[ \t]*$", line)
    if match:
        return len(match.group(1)), match.group(2)
    if following and line.strip() and re.match(r"^(=+|-+)[ \t]*$", following):
        return (1 if following.lstrip().startswith("=") else 2), line.strip()
    return None


def _section(text, heading=_HEADING):
    pattern = heading if hasattr(heading, "search") else re.compile(heading, re.I)
    lines = text.splitlines()
    start = None
    level = None
    for index, line in enumerate(lines):
        following = lines[index + 1] if index + 1 < len(lines) else ""
        parsed = _heading_text(line, following)
        if parsed and pattern.search(parsed[1]):
            start, level = index, parsed[0]
            break
    if start is None:
        return None
    body = []
    body_start = start + 1
    if start + 1 < len(lines) and re.match(r"^(=+|-+)[ \t]*$", lines[start + 1]):
        body_start = start + 2
    index = body_start
    while index < len(lines):
        following = lines[index + 1] if index + 1 < len(lines) else ""
        parsed = _heading_text(lines[index], following)
        if parsed and parsed[0] <= level:
            break
        body.append(lines[index])
        index += 1
    return "\n".join(body)


def _split_shell(command):
    """Split one logical line on && and ; outside quotes."""
    parts = []
    buf = []
    quote = None
    index = 0
    while index < len(command):
        char = command[index]
        if quote:
            buf.append(char)
            if char == quote and command[index - 1] != "\\":
                quote = None
            index += 1
            continue
        if char in "\"'":
            quote = char
            buf.append(char)
            index += 1
            continue
        if command.startswith("&&", index):
            piece = "".join(buf).strip()
            if piece:
                parts.append(piece)
            buf = []
            index += 2
            continue
        if char == ";":
            piece = "".join(buf).strip()
            if piece:
                parts.append(piece)
            buf = []
            index += 1
            continue
        buf.append(char)
        index += 1
    piece = "".join(buf).strip()
    if piece:
        parts.append(piece)
    return parts


def _shell_commands(block):
    commands = []
    pending = ""
    for raw in block.splitlines():
        stripped = raw.strip()
        if pending:
            pending = pending[:-1].rstrip() + " " + re.sub(r"^[$>]\s*", "", stripped)
            if not stripped.endswith("\\"):
                commands.extend(_split_shell(pending.strip()))
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
            commands.extend(_split_shell(stripped))
    if pending:
        commands.extend(_split_shell(pending[:-1].strip()))
    return [command for command in commands if command]


def _looks_like_shell(body):
    return any(re.match(r"^[ \t]*\$[ \t]+\S", line) for line in body.splitlines())


def _shell_blocks(section):
    fence = re.compile(r"^```([^\n]*)\n(.*?)^```[ \t]*$", re.M | re.S)
    blocks = []
    for match in fence.finditer(section):
        info = match.group(1).strip().split()
        language = info[0].lower() if info else ""
        body = match.group(2)
        if language in {"sh", "bash", "shell", "console", "zsh"}:
            blocks.append(body)
        elif language in {"", "text", "txt"} and _looks_like_shell(body):
            blocks.append(body)
    return blocks


def quickstart_commands(root):
    """Every shell command in the install/quickstart section is the happy path."""
    readme = root / "README.md"
    if not readme.is_file():
        return result(
            "quickstart_commands", "minimal_setup", False, None, QUICKSTART_COMMAND_LIMIT,
            "README.md has no install quickstart.", ["README.md is absent"],
        )
    text = readme.read_text(encoding="utf-8", errors="replace")
    section = _section(text)
    if section is None:
        return result(
            "quickstart_commands", "minimal_setup", False, None, QUICKSTART_COMMAND_LIMIT,
            "README.md has no Install, Quickstart, or Getting started section.",
            ["README.md"],
        )
    commands = []
    for block in _shell_blocks(section):
        commands.extend(_shell_commands(block))
    count = len(commands)
    ok = count == QUICKSTART_COMMAND_LIMIT
    explanation = (
        f"The README quickstart has {count} commands. "
        f"Best practice is exactly {QUICKSTART_COMMAND_LIMIT} install command."
    )
    evidence = [f"README.md: {command}" for command in commands] or [
        "README.md: no shell commands in the install/quickstart section"
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
    except UnicodeDecodeError:
        return None, "invalid UTF-8"
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


def _record_harness(hits, name, evidence):
    if name in hits and not hits[name]:
        hits[name] = evidence


def _record_name_list(hits, value, label):
    if not isinstance(value, list):
        return
    for item in value:
        if isinstance(item, str):
            _record_harness(hits, item, label)


def _walk_args_by_harness(value, hits):
    if isinstance(value, dict):
        args = value.get("args_by_harness")
        if isinstance(args, dict):
            for name in args:
                _record_harness(hits, name, "harnesses/integrations.json args_by_harness." + name)
        for child in value.values():
            _walk_args_by_harness(child, hits)
    elif isinstance(value, list):
        for child in value:
            _walk_args_by_harness(child, hits)


def _placement_from_manifests(root, hits):
    skills, _detail = _json_object(root / "harnesses" / "skills.json")
    if isinstance(skills, dict):
        placement = skills.get("placement")
        if isinstance(placement, dict):
            _record_name_list(hits, placement.get("default"), "harnesses/skills.json placement.default")
            sources = placement.get("sources")
            if isinstance(sources, dict):
                for source, names in sources.items():
                    _record_name_list(
                        hits, names, f"harnesses/skills.json placement.sources.{source}"
                    )
    integrations, _detail = _json_object(root / "harnesses" / "integrations.json")
    if isinstance(integrations, dict):
        _walk_args_by_harness(integrations, hits)


def _placement_from_paths(root, hits):
    if all(hits.values()):
        return
    skip = SKIP_NAMES | {"vendor"}
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        dirnames[:] = [name for name in dirnames if name not in skip]
        relative = Path(dirpath).relative_to(root)
        for part in relative.parts:
            name = HARNESS_PATH_NAMES.get(part.lower())
            if name:
                _record_harness(hits, name, relative.as_posix() + "/")
        for filename in filenames:
            name = HARNESS_PATH_NAMES.get(filename.lower())
            if name:
                _record_harness(hits, name, (relative / filename).as_posix())
        if all(hits.values()):
            return


def harness_coverage(root):
    """Each harness has a placement entry, args_by_harness key, or config path."""
    hits = {name: "" for name in HARNESSES}
    _placement_from_manifests(root, hits)
    _placement_from_paths(root, hits)
    evidence = []
    found = 0
    for name in HARNESSES:
        if hits[name]:
            found += 1
            evidence.append(f"{name}: {hits[name]}")
        else:
            evidence.append(f"{name}: no placement, args_by_harness entry, or config path")
    ok = found == len(HARNESSES)
    explanation = (
        f"{found} of {len(HARNESSES)} harnesses "
        "(claude, codex, cursor, copilot, grok, kimi, muse, opencode, t3code) "
        "have a skills.json placement, an integrations.json args_by_harness entry, "
        "or a config path whose component is that harness."
    )
    return result(
        "harness_coverage", "cross_harness", ok, found, len(HARNESSES), explanation, evidence
    )


def _lists_option(text, flag):
    escaped = re.escape(flag)
    if re.search(rf"(?m)^\s*{escaped}(?:[\s,=\[|]|$)", text):
        return True
    return re.search(rf"(?m)^usage:.*{escaped}\b", text) is not None


def _porcelain(root):
    completed = subprocess.run(
        ["git", "-C", str(root), "status", "--porcelain"],
        capture_output=True, text=True, timeout=20, check=False,
    )
    if completed.returncode != 0:
        return None
    return completed.stdout


def _sandbox_env(home, temporary):
    return {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": str(home),
        "TMPDIR": str(temporary),
        "LANG": os.environ.get("LANG", "C.UTF-8"),
        "PYTHONDONTWRITEBYTECODE": "1",
        "TKSTACK_PYTHON": sys.executable,
    }


def install_flags(root):
    """install.sh --help lists both flags, and a sandboxed --dry-run writes nothing outside."""
    install = root / "install.sh"
    if not install.is_file():
        return result(
            "install_flags", "dotfiles", False, [], ["--dry-run", "--uninstall"],
            "install.sh is absent, so it has neither --dry-run nor uninstall.",
            ["absent: install.sh"],
        )
    evidence = ["install.sh"]
    supported = []
    try:
        help_run = subprocess.run(
            [str(install), "--help"],
            cwd=root, capture_output=True, text=True, timeout=30, check=False,
            env=_sandbox_env(Path(tempfile.gettempdir()), tempfile.gettempdir()),
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return result(
            "install_flags", "dotfiles", False, [], ["--dry-run", "--uninstall"],
            f"install.sh --help failed: {error}", evidence,
        )
    help_text = help_run.stdout or ""
    if help_run.returncode == 0 and _lists_option(help_text, "--uninstall"):
        supported.append("--uninstall")
    else:
        evidence.append("install.sh --help does not list --uninstall")
    dry_ok = False
    try:
        with tempfile.TemporaryDirectory(prefix="repo-quality-dry-") as temporary:
            sandbox = Path(temporary)
            home = sandbox / "home"
            target = sandbox / "target"
            home.mkdir()
            target.mkdir()
            before = _porcelain(root)
            dry_run = subprocess.run(
                [
                    str(install), "--dry-run", "--offline", "--no-toolchains", "--no-shell",
                    "--target", str(target), "--workspace", str(target),
                ],
                cwd=root, capture_output=True, text=True, timeout=60, check=False,
                env=_sandbox_env(home, sandbox),
            )
            after = _porcelain(root)
    except (OSError, subprocess.TimeoutExpired) as error:
        evidence.append(f"sandboxed --dry-run failed: {error}")
        dry_run = None
        before = after = None
    if dry_run is not None and dry_run.returncode == 0 and before is not None and before == after:
        dry_ok = True
        evidence.append("sandboxed install.sh --dry-run exited 0 and left the checkout unchanged")
    else:
        code = dry_run.returncode if dry_run is not None else "error"
        evidence.append(f"sandboxed install.sh --dry-run did not stay read-only (exit {code})")
    if dry_ok and help_run.returncode == 0 and _lists_option(help_text, "--dry-run"):
        supported.insert(0, "--dry-run")
    elif "--dry-run" not in supported:
        evidence.append("install.sh --dry-run is not an advertised read-only flag")
    ok = supported == ["--dry-run", "--uninstall"]
    found = ", ".join(supported) if supported else "none"
    explanation = (
        "install.sh --help must list --dry-run and --uninstall, and "
        f"install.sh --dry-run --offline --target <tmpdir> must exit 0 without "
        f"changing the checkout. Supported flags: {found}."
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

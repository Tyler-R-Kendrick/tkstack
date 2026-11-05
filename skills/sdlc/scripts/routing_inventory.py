#!/usr/bin/env python3
"""Generate and check the SDLC skill-routing inventory.

The inventory is the installed skill set plus Learn subskills, vendored skills
that are intentionally not placed, and any SKILL.md under harnesses/. Routing
entries live in skills/sdlc/references/routing.json. The rendered table is the
marked region of skills/sdlc/references/skill-routing.md.
"""

import json
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SCRIPTS = ROOT / "scripts"
for directory in (HERE, SCRIPTS, ROOT / "src"):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))
from skill_roots import load  # noqa: E402
import skill_roots  # noqa: E402
CATALOG = Path("skills/sdlc/references/routing.json")
GUIDE = Path("skills/sdlc/references/skill-routing.md")
START = "<!-- tkstack:routing-inventory:start -->"
END = "<!-- tkstack:routing-inventory:end -->"
PHASES = (
    "discovery/requirements",
    "design & UI polish",
    "architecture",
    "implementation",
    "TDD/clean-code discipline",
    "review",
    "debugging",
    "docs",
    "release/ops",
    "learning",
)
# Same declared name, different path, one skill. The installer view, Caveman's
# plugin mirror, and Impeccable's per-harness builds are not extra skills.
# Any other collision is an error so an unplaced skill cannot hide.
DUPLICATE_SKILL_PATHS = frozenset({
    "vendor/caveman/plugins/caveman/skills/cavecrew/SKILL.md",
    "vendor/caveman/plugins/caveman/skills/caveman-compress/SKILL.md",
    "vendor/caveman/plugins/caveman/skills/caveman-stats/SKILL.md",
    "vendor/caveman/plugins/caveman/skills/caveman/SKILL.md",
    "vendor/caveman/plugins/caveman/skills/megacave/SKILL.md",
    "vendor/caveman/plugins/caveman/skills/ultracave/SKILL.md",
    "vendor/emil-kowalski/skills/animate-expo/SKILL.md",
    "vendor/emil-kowalski/skills/animate/SKILL.md",
    "vendor/emil-kowalski/skills/animation-performance/SKILL.md",
    "vendor/emil-kowalski/skills/animation-vocabulary/SKILL.md",
    "vendor/emil-kowalski/skills/apple-design/SKILL.md",
    "vendor/emil-kowalski/skills/ask-sonner/SKILL.md",
    "vendor/emil-kowalski/skills/break-ui/SKILL.md",
    "vendor/emil-kowalski/skills/choreograph/SKILL.md",
    "vendor/emil-kowalski/skills/emil-design-eng/SKILL.md",
    "vendor/emil-kowalski/skills/find-animation-opportunities/SKILL.md",
    "vendor/emil-kowalski/skills/improve-animations/SKILL.md",
    "vendor/emil-kowalski/skills/mobile-native/SKILL.md",
    "vendor/emil-kowalski/skills/pick-ui-library/SKILL.md",
    "vendor/emil-kowalski/skills/prototype/SKILL.md",
    "vendor/emil-kowalski/skills/remove-animations/SKILL.md",
    "vendor/emil-kowalski/skills/review-animations/SKILL.md",
    "vendor/emil-kowalski/skills/write-swift/SKILL.md",
    "vendor/impeccable/.claude/skills/impeccable/SKILL.md",
    "vendor/impeccable/.cursor/skills/impeccable/SKILL.md",
    "vendor/matt-pocock/skills/engineering/ask-matt/SKILL.md",
    "vendor/matt-pocock/skills/engineering/code-review/SKILL.md",
    "vendor/matt-pocock/skills/engineering/codebase-design/SKILL.md",
    "vendor/matt-pocock/skills/engineering/diagnosing-bugs/SKILL.md",
    "vendor/matt-pocock/skills/engineering/domain-modeling/SKILL.md",
    "vendor/matt-pocock/skills/engineering/grill-with-docs/SKILL.md",
    "vendor/matt-pocock/skills/engineering/implement-spec/SKILL.md",
    "vendor/matt-pocock/skills/engineering/implement/SKILL.md",
    "vendor/matt-pocock/skills/engineering/improve-codebase-architecture/SKILL.md",
    "vendor/matt-pocock/skills/engineering/pr/SKILL.md",
    "vendor/matt-pocock/skills/engineering/prototype/SKILL.md",
    "vendor/matt-pocock/skills/engineering/research/SKILL.md",
    "vendor/matt-pocock/skills/engineering/retro/SKILL.md",
    "vendor/matt-pocock/skills/engineering/setup-matt-pocock-skills/SKILL.md",
    "vendor/matt-pocock/skills/engineering/tdd/SKILL.md",
    "vendor/matt-pocock/skills/engineering/to-spec/SKILL.md",
    "vendor/matt-pocock/skills/engineering/to-tickets/SKILL.md",
    "vendor/matt-pocock/skills/engineering/triage/SKILL.md",
    "vendor/matt-pocock/skills/engineering/wayfinder/SKILL.md",
    "vendor/matt-pocock/skills/engineering/wizard/SKILL.md",
    "vendor/matt-pocock/skills/in-progress/chief-of-staff/SKILL.md",
    "vendor/matt-pocock/skills/in-progress/claude-handoff/SKILL.md",
    "vendor/matt-pocock/skills/in-progress/loop-me/SKILL.md",
    "vendor/matt-pocock/skills/in-progress/setup-ts-deep-modules/SKILL.md",
    "vendor/matt-pocock/skills/in-progress/writing-beats/SKILL.md",
    "vendor/matt-pocock/skills/in-progress/writing-fragments/SKILL.md",
    "vendor/matt-pocock/skills/in-progress/writing-shape/SKILL.md",
    "vendor/matt-pocock/skills/misc/git-guardrails-claude-code/SKILL.md",
    "vendor/matt-pocock/skills/misc/migrate-to-shoehorn/SKILL.md",
    "vendor/matt-pocock/skills/misc/scaffold-exercises/SKILL.md",
    "vendor/matt-pocock/skills/misc/setup-pre-commit/SKILL.md",
    "vendor/matt-pocock/skills/productivity/grill-me/SKILL.md",
    "vendor/matt-pocock/skills/productivity/grilling/SKILL.md",
    "vendor/matt-pocock/skills/productivity/handoff/SKILL.md",
    "vendor/matt-pocock/skills/productivity/teach/SKILL.md",
    "vendor/matt-pocock/skills/productivity/to-questionnaire/SKILL.md",
    "vendor/matt-pocock/skills/productivity/wait-what/SKILL.md",
    "vendor/matt-pocock/skills/productivity/writing-for-agents/SKILL.md",
    "vendor/pstack/skills/unslop/SKILL.md",
})


install = load("tkstack_install", ROOT / "scripts" / "install.py")


def _unescape_double_quoted(value):
    """Undo YAML \\\\ and \\\" escapes. Other backslash sequences stay literal."""
    out = []
    index = 0
    while index < len(value):
        if value[index] == "\\" and index + 1 < len(value) and value[index + 1] in '\\"':
            out.append(value[index + 1])
            index += 2
        else:
            out.append(value[index])
            index += 1
    return "".join(out)


def description(text):
    """Return the skill's frontmatter description as one line."""
    if not text.startswith("---"):
        return ""
    front = text.split("---", 2)[1]
    lines = front.splitlines()
    for index, line in enumerate(lines):
        if not line.startswith("description:"):
            continue
        rest = line[len("description:"):].strip()
        if rest in {">", "|", ">-", "|-", ">+", "|+"}:
            chunks = []
            for nxt in lines[index + 1:]:
                if nxt.startswith((" ", "\t")):
                    chunks.append(nxt.strip())
                elif not nxt.strip():
                    continue
                else:
                    break
            rest = " ".join(chunks)
        if len(rest) >= 2 and rest[0] == rest[-1] and rest[0] in {'"', "'"}:
            inner = rest[1:-1]
            if rest[0] == '"':
                inner = _unescape_double_quoted(inner)
            rest = inner
        return re.sub(r"\s+", " ", rest).strip()
    return ""


def reject_unlisted_duplicate(relative, declared):
    """Allow known repackaging. A distinct skill that reuses a name is an error."""
    if relative in DUPLICATE_SKILL_PATHS:
        return
    raise ValueError(
        "Vendored skill declares an existing name and is not an allowed duplicate: "
        + relative + " (" + declared + ")")


def _declared_name(path):
    match = re.search(r"^name:\s*(.+)$", path.read_text(errors="replace"), re.M)
    return match.group(1).strip().strip("\"'") if match else path.parent.name


def _upstream_text(root, source, installed):
    """Read the pinned skill text, not a generated alias or Graphify view."""
    if source == "graphify":
        lock = json.loads((root / "sources.lock.json").read_text())
        relative = lock["sources"]["graphify"]["skill_templates"]["default"]["entrypoint"]
        return (root / "vendor" / "graphify" / relative).read_text(errors="replace")
    view = root / ".tkstack" / str(source) / "skills"
    try:
        relative = installed.relative_to(view)
    except ValueError:
        return (installed / "SKILL.md").read_text(errors="replace")
    return (root / "vendor" / source / "skills" / relative / "SKILL.md").read_text(errors="replace")


_HARNESS_LABELS = (
    ("codex", "Codex"),
    ("claude", "Claude Code"),
    ("cursor", "Cursor"),
    ("grok", "Grok"),
    ("kimi", "Kimi"),
    ("muse", "Muse"),
    ("opencode", "OpenCode"),
    ("copilot", "Copilot"),
)


def _join_labels(names):
    if len(names) == 1:
        return names[0]
    if len(names) == 2:
        return names[0] + " and " + names[1]
    return ", ".join(names[:-1]) + ", and " + names[-1]


def _placement(rules, source):
    """Describe install.placement. None means every harness the user selected."""
    selected = install.placement(rules, "skills", source)
    if selected is None:
        return "every selected harness"
    if selected == {"cursor"}:
        return "Cursor only"
    if selected == {"codex"}:
        return "shared .agents/skills only"
    labels = dict(_HARNESS_LABELS)
    ordered = [labels[name] for name, _label in _HARNESS_LABELS if name in selected]
    ordered.extend(sorted(selected - set(labels)))
    return _join_labels(ordered)


def discover(root=ROOT):
    """Map every routed skill name to its stack, purpose, and placement.

    This read does not generate alias or Graphify views. The root skills gate
    (src/check_skills.py) runs this check read-only. The installer writes those
    views. Generating them here would change the checkout the check reads.
    """
    root = Path(root)
    rules_path = root / "harnesses/skills.json"
    rules = json.loads(rules_path.read_text()).get("placement", {}) if rules_path.is_file() else {}
    found = {}

    def add(name, record):
        if name in found:
            raise ValueError("Duplicate routing skill name: " + name)
        purpose = description(record.pop("text"))
        if not purpose:
            raise ValueError("Skill has no description: " + name)
        record["purpose"] = purpose
        found[name] = record

    for name, (source, path) in install.sourced(root, "skills").items():
        group = "developed" if source is None else source
        add(name, {
            "group": group,
            "stack": "skills/" if source is None else source,
            "placement": _placement(rules, source),
            "text": _upstream_text(root, source, path),
            "path": path,
        })
    for parent_name, parent in skill_roots.all_packages(root).items():
        for name, path in skill_roots.subskills(parent).items():
            add(name, {
                "group": "developed",
                "stack": parent_name + " subskill",
                "placement": "installed only through " + parent_name,
                "text": (path / "SKILL.md").read_text(errors="replace"),
                "path": path,
            })
    known_names = set(found)
    known_dirs = {record["path"].resolve() for record in found.values()}
    seen_duplicates = set()
    for skill in sorted((root / "vendor").rglob("SKILL.md")):
        if skill.parent.resolve() in known_dirs:
            continue
        declared = _declared_name(skill)
        if declared in known_names or declared in found:
            relative = skill.relative_to(root).as_posix()
            reject_unlisted_duplicate(relative, declared)
            seen_duplicates.add(relative)
            continue
        source = skill.relative_to(root / "vendor").parts[0]
        add(declared, {
            "group": source,
            "stack": source,
            "placement": "vendored, not installed",
            "text": skill.read_text(errors="replace"),
            "path": skill.parent,
        })
    harnesses = root / "harnesses"
    if harnesses.is_dir():
        for skill in sorted(harnesses.rglob("SKILL.md")):
            if skill.parent.resolve() in known_dirs:
                continue
            declared = _declared_name(skill)
            add(declared, {
                "group": "harness",
                "stack": "harnesses/",
                "placement": "harness package",
                "text": skill.read_text(errors="replace"),
                "path": skill.parent,
            })
    stale_allowance = sorted(DUPLICATE_SKILL_PATHS - seen_duplicates)
    if stale_allowance:
        raise ValueError("Duplicate skill allowlist is stale: " + ", ".join(stale_allowance))
    return found


def load_catalog(root=ROOT):
    return json.loads((Path(root) / CATALOG).read_text())


def stack_names(root=ROOT, skills=None):
    root = Path(root)
    names = set(json.loads((root / "sources.lock.json").read_text())["sources"])
    names.update(("developed", "adopted"))
    if skills and any(item["group"] == "harness" for item in skills.values()):
        names.add("harness")
    return names


def inventory_errors(skills, catalog, stacks):
    """Return human-readable mismatches. Empty means the catalog matches."""
    if catalog.get("version") != 1 or tuple(catalog.get("phases", ())) != PHASES:
        return ["routing catalog phases or version do not match the SDLC phase list"]
    errors = []
    names = set(skills)
    entries = set(catalog.get("skills", {}))
    missing = sorted(names - entries)
    extra = sorted(entries - names)
    if missing:
        errors.append("skills without a routing entry: " + ", ".join(missing))
    if extra:
        errors.append("routing entries with no skill: " + ", ".join(extra))
    allowed = set(PHASES)
    bad_phase, empty = [], []
    for name, entry in catalog.get("skills", {}).items():
        if not isinstance(entry, dict) or entry.get("phase") not in allowed:
            bad_phase.append(name)
        elif not str(entry.get("strengths", "")).strip():
            empty.append(name)
    if bad_phase:
        errors.append("routing entries with an unknown phase: " + ", ".join(sorted(bad_phase)))
    if empty:
        errors.append("routing entries with empty strengths: " + ", ".join(sorted(empty)))
    recorded = set(catalog.get("stacks", {}))
    if missing_stacks := sorted(stacks - recorded):
        errors.append("stacks without an overview: " + ", ".join(missing_stacks))
    if extra_stacks := sorted(recorded - stacks):
        errors.append("stack overviews with no source: " + ", ".join(extra_stacks))
    for name, entry in catalog.get("stacks", {}).items():
        if not isinstance(entry, dict) or not str(entry.get("title", "")).strip() or not str(entry.get("summary", "")).strip():
            errors.append("incomplete stack overview: " + name)
    return errors


def _cell(text):
    text = re.sub(r"\s+", " ", str(text)).strip()
    if len(text) > 420:
        text = text[:417].rstrip() + "..."
    return text.replace("|", "\\|")


def render_inventory(skills, catalog):
    """Markdown for the marked region: stack overviews, then one row per skill."""
    order = list(catalog["stacks"])
    rank = {name: index for index, name in enumerate(order)}
    lines = [
        "Generated from the installed skill set, Learn subskills, unplaced vendored",
        "skills, and `harnesses/` packages. Do not edit this region by hand. Run",
        "`python3 skills/sdlc/scripts/routing_inventory.py render` after adding a skill and its",
        "routing entry.",
        "",
        "| Stack | Best starting point | What this stack is for |",
        "| --- | --- | --- |",
    ]
    for name, entry in catalog["stacks"].items():
        lines.append("| " + " | ".join(_cell(value) for value in (entry["title"], entry.get("best_for", ""), entry["summary"])) + " |")
    lines.extend([
        "",
        "| Skill | Stack | What it is for | Strengths | Best SDLC phase | Placement |",
        "| --- | --- | --- | --- | --- | --- |",
    ])
    def sort_key(item):
        name, record = item
        return (rank.get(record["group"], len(rank)), record["stack"], name)
    for name, record in sorted(skills.items(), key=sort_key):
        entry = catalog["skills"][name]
        lines.append("| " + " | ".join(_cell(value) for value in (
            f"`{name}`", record["stack"], record["purpose"], entry["strengths"], entry["phase"], record["placement"],
        )) + " |")
    return "\n".join(lines) + "\n"


def guide_text(root=ROOT):
    return (Path(root) / GUIDE).read_text()


def split_guide(text):
    if text.count(START) != 1 or text.count(END) != 1 or text.index(START) > text.index(END):
        raise ValueError("skill-routing.md must contain one routing inventory region")
    head, rest = text.split(START, 1)
    body, tail = rest.split(END, 1)
    return head, body, tail


def rendered_guide(text, inventory):
    head, _body, tail = split_guide(text)
    return head + START + "\n" + inventory + END + tail


def check(root=ROOT):
    root = Path(root)
    skills = discover(root)
    catalog = load_catalog(root)
    errors = inventory_errors(skills, catalog, stack_names(root, skills))
    if errors:
        raise ValueError("; ".join(errors))
    inventory = render_inventory(skills, catalog)
    _head, body, _tail = split_guide(guide_text(root))
    if body.strip() != inventory.strip():
        raise ValueError("skill-routing.md inventory is stale; run python3 skills/sdlc/scripts/routing_inventory.py render")
    return {"skills": len(skills), "stacks": len(catalog["stacks"])}


def render(root=ROOT):
    root = Path(root)
    skills = discover(root)
    catalog = load_catalog(root)
    errors = inventory_errors(skills, catalog, stack_names(root, skills))
    if errors:
        raise ValueError("; ".join(errors))
    path = root / GUIDE
    path.write_text(rendered_guide(path.read_text(), render_inventory(skills, catalog)))
    return check(root)


def main(argv=None):
    command = (argv or sys.argv[1:] or ["check"])[0]
    try:
        if command == "check":
            result = check()
        elif command == "render":
            result = render()
        else:
            raise ValueError("Use check or render")
    except (OSError, ValueError, KeyError, TypeError) as error:
        print("routing: " + str(error), file=sys.stderr)
        return 1
    print(json.dumps({"status": "pass", **result}))
    return 0


if __name__ == "__main__":
    sys.exit(main())

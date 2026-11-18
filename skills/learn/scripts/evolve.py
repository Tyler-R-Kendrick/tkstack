#!/usr/bin/env python3
"""Prepare authored evolution cases for the invoking agent without launching a model."""

import argparse
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace
ROOT = Path(__file__).resolve().parents[3]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "src"))
from tkstack_state import ensure_state
from skill_roots import owned

sys.path.insert(0, str(ROOT / "vendor/skillopt"))

from skillopt_sleep.tasks_file import load_tasks_file


PREFERENCES = (
    "Preserve the skill name, metadata, relative links, and original user obligations. "
    "Make at most one bounded instruction edit, or return no edits when justified. "
    "Do not hardcode answer labels, task IDs, checks, or evaluation-specific rules. "
    "Preserve correction provenance, narrow rule scope, and instruction precedence. "
    "Preserve BDD/contracts, workload evidence, isolated concurrent worktrees, independent "
    "review, and protected stacked PR delivery. Do not modify memory or steering data."
)


def identity(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


@contextmanager
def run_lock(directory):
    ensure_state(directory)
    lock = directory / ".driver.lock"
    try:
        lock.mkdir()
    except FileExistsError as error:
        raise ValueError("Evolution driver is already running in this directory") from error
    try:
        yield
    finally:
        lock.rmdir()


def prepare(skill, run_dir):
    ensure_state(run_dir)
    packages = owned(ROOT)
    if not isinstance(skill, str) or skill not in packages:
        raise ValueError('Select an existing owned skill or subskill')
    target = packages[skill] / "SKILL.md"
    source = ROOT / "evals" / skill / "tasks.json"
    tasks, meta = load_tasks_file(str(source))
    if meta.get("reviewed") is not True:
        raise ValueError("Inspect the task file and mark it reviewed before replay")
    if meta.get("provenance") != "author-created decision regression scenarios":
        raise ValueError("Evaluation provenance must be explicit")
    identifiers = [task.id for task in tasks]
    if len(identifiers) != len(set(identifiers)) or not tasks:
        raise ValueError("Task IDs must be unique and nonempty")
    if {task.split for task in tasks} != {"train", "val", "test"}:
        raise ValueError("Keep separate train, validation, and final test scenarios")
    if any(task.origin != "authored" for task in tasks):
        raise ValueError("These fixtures must not impersonate mined real-session tasks")
    for task in tasks:
        checks = task.judge.get("checks", [])
        if (task.reference_kind != "rule" or len(checks) != 1
                or checks[0].get("op") != "regex"
                or checks[0].get("arg") not in (r"\A\s*A\s*\Z", r"\A\s*B\s*\Z", r"\A\s*C\s*\Z")):
            raise ValueError("Decision regressions require a strict anchored action grader")
    cfg = SimpleNamespace(evolve_memory=False, auto_adopt=False,
                          gate_no_regression=True, gate_mode="on", edit_budget=1,
                          managed_skill_path=lambda: str(target))
    lock = json.loads((ROOT / "sources.lock.json").read_text())["sources"]["skillopt"]
    frozen = {"version": 2, "skill": skill, "target": str(target),
              "skill_sha256": identity(target), "tasks_sha256": identity(source),
              "engine_revision": lock["revision"], "mode": "invoking-agent",
              "preferences": PREFERENCES}
    pinned = run_dir / "inputs.json"
    if pinned.exists() and json.loads(pinned.read_text()) != frozen:
        raise ValueError("Evolution inputs changed; use a new --run-dir rather than relabeling old proof")
    pinned.write_text(json.dumps(frozen, indent=2) + "\n")
    return cfg, tasks, meta


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("skill", choices=sorted(owned(ROOT)))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--run-dir", type=Path)
    args = parser.parse_args()
    directory = (args.run_dir or ROOT / ".tkstack/evolution" / args.skill).resolve()
    try:
        with run_lock(directory):
            cfg, tasks, _ = prepare(args.skill, directory)
            print(json.dumps({"status": "ready-for-invoking-agent", "skill": args.skill,
                              "cases": len(tasks), "run_dir": str(directory),
                              "automatic_model_calls": False,
                              "limits": "The current agent must perform evaluation; same-context cases are not blind."},
                             indent=2))
            return 0
    except (OSError, ValueError) as error:
        print(f"evolve: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())

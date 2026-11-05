#!/usr/bin/env python3
"""Run pinned SkillOpt-Sleep on an owned skill with isolated state and strict gates."""

import argparse
from contextlib import contextmanager
import hashlib
from contextlib import redirect_stdout
from io import StringIO
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace
sys.path.insert(0, str(Path(__file__).resolve().parent))
from tkstack_state import ensure_state
from skill_roots import owned

ROOT = Path(__file__).resolve().parent.parent
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "vendor/skillopt"))

from skillopt_sleep.__main__ import _run_handoff, _print_run_report
from skillopt_sleep.config import DEFAULTS, SleepConfig
from skillopt_sleep.cycle import run_sleep_cycle
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


def prepare(skill, run_dir, backend):
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
    cfg = SleepConfig({**DEFAULTS, "backend": backend, "invoked_project": str(run_dir),
                       "state_dir": str(run_dir / "state"), "target_skill_path": str(target),
                       "managed_skill_name": skill, "target_task_filter": False,
                       "gate_mode": "on", "gate_metric": "hard", "gate_no_regression": True,
                       "evolve_memory": False, "evolve_skill": True, "auto_adopt": False,
                       "edit_budget": 1, "max_tasks_per_night": len(tasks),
                       "max_tokens_per_night": 120000, "preferences": PREFERENCES,
                       "progress": False, "replay_mode": "fresh-context-decision",
                       "recall_k": 0, "dream_factor": 0,
                       "multi_skill_fanout": False})
    lock = json.loads((ROOT / "sources.lock.json").read_text())["sources"]["skillopt"]
    frozen = {"version": 1, "skill": skill, "target": str(target),
              "skill_sha256": identity(target), "tasks_sha256": identity(source),
              "engine_revision": lock["revision"], "backend": backend,
              "preferences": PREFERENCES}
    pinned = run_dir / "inputs.json"
    if pinned.exists() and json.loads(pinned.read_text()) != frozen:
        raise ValueError("Evolution inputs changed; use a new --run-dir rather than relabeling old proof")
    pinned.write_text(json.dumps(frozen, indent=2) + "\n")
    return cfg, tasks, meta


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("skill", choices=sorted(owned(ROOT)))
    parser.add_argument("--backend", choices=["handoff", "mock", "codex"], default="handoff")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--run-dir", type=Path)
    args = parser.parse_args()
    suffix = "-mock-smoke" if args.backend == "mock" else ""
    directory = (args.run_dir or ROOT / ".tkstack/evolution" / (args.skill + suffix)).resolve()
    try:
        with run_lock(directory):
            cfg, tasks, meta = prepare(args.skill, directory, args.backend)
            result_path = directory / "result.json"
            if result_path.exists() and not args.dry_run:
                print(result_path.read_text(), end="")
                return 0
            native_args = SimpleNamespace(json=True)
            if args.backend == "handoff":
                key = "SKILLOPT_SLEEP_HANDOFF_DIR"
                previous = os.environ.get(key)
                try:
                    os.environ[key] = str(directory / "handoff")
                    output = StringIO()
                    with redirect_stdout(output):
                        status = _run_handoff(cfg, native_args, seed_tasks=tasks, task_meta=meta, dry=args.dry_run)
                    if status == 0 and not args.dry_run:
                        result_path.write_text(output.getvalue())
                    print(output.getvalue(), end="")
                    return status
                finally:
                    if previous is None:
                        os.environ.pop(key, None)
                    else:
                        os.environ[key] = previous
            outcome = run_sleep_cycle(cfg, seed_tasks=tasks, dry_run=args.dry_run)
            _print_run_report(outcome, native_args, meta)
            return 0
    except (OSError, ValueError) as error:
        print(f"evolve: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())

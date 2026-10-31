#!/usr/bin/env python3
"""Install Lever's documented per-project Copilot layout and initial repo dials."""

import argparse
from pathlib import Path
import sys
sys.dont_write_bytecode = True

import install

ROOT = Path(__file__).resolve().parent.parent


def link_plan(root, target):
    source = root / "vendor/lever"
    skills = sorted(path.parent for path in (source / "skills").glob("*/SKILL.md"))
    if not skills:
        raise ValueError("Pinned Lever skills are missing")
    plan = [(path.resolve(), target / ".github/skills" / path.name) for path in skills]
    plan.extend(((source / name).resolve(), target / ".github" / name)
                for name in ("docs", "templates", "config", "automations"))
    return plan


def contained_parents(target, destinations):
    for destination in destinations:
        if not destination.parent.resolve().is_relative_to(target):
            raise ValueError("Refusing to install through a directory outside the project: " + str(destination))


def configure(root, target, dry_run=False):
    destination = target / ".github/lever.yml"
    if destination.exists() or destination.is_symlink():
        if not destination.is_file():
            raise ValueError("Lever repository configuration is not a readable file")
        return False
    print(f"{'Would create' if dry_run else 'create'}: {destination}")
    if not dry_run:
        destination.parent.mkdir(parents=True, exist_ok=True)
        try:
            with destination.open("x", encoding="utf-8") as handle:
                handle.write((root / "harnesses/copilot/lever.yml").read_text())
        except FileExistsError:
            if not destination.is_file():
                raise ValueError("Lever configuration changed during setup")
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", type=Path, default=ROOT, help="Project directory (default: this checkout)")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--uninstall", action="store_true", help="Remove owned links; retain repository dials")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check and (args.dry_run or args.uninstall):
        parser.error("--check cannot be combined with --dry-run or --uninstall")
    try:
        target = args.target.expanduser().resolve()
        if not args.uninstall:
            install.verify_vendor(ROOT)
        plan = link_plan(ROOT, target)
        configuration = target / ".github/lever.yml"
        contained_parents(target, [destination for _, destination in plan] + [configuration])
        if args.check:
            missing = [str(destination) for source, destination in plan
                       if not source.exists() or not install.matches(destination, source)]
            if missing or not configuration.is_file():
                raise ValueError("Lever Copilot setup is missing or stale; rerun setup_lever.py")
            skills = sum(destination.parent == target / ".github/skills" for _, destination in plan)
            print(f"Verified {skills} Lever skills, {len(plan)} Copilot links, and repository dials at {target}.")
            return 0
        if not args.uninstall:
            install.preflight(plan)
            if (configuration.exists() or configuration.is_symlink()) and not configuration.is_file():
                raise ValueError("Lever repository configuration is not a readable file")
            configure(ROOT, target, dry_run=args.dry_run)
        count = install.apply(plan, dry_run=args.dry_run, uninstall=args.uninstall)
        print(f"{count} Lever Copilot link(s) {'would change' if args.dry_run else 'changed'}.")
        return 0
    except (OSError, ValueError, KeyError) as error:
        print(f"lever: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

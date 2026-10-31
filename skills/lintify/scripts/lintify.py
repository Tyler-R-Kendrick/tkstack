#!/usr/bin/env python3
"""Scaffold isolated native linter examples; do not install engines or activate rules."""

import argparse
import json
from pathlib import Path
import shutil
import sys
sys.dont_write_bytecode = True


PACKAGE = Path(__file__).resolve().parent.parent
FILES = {
    "eslint": ("package.json", "package-lock.json", "eslint.config.mjs", "require-audit-reason.mjs", "rule.test.mjs",
               "fixtures/good.js", "fixtures/bad.js", "README.md"),
    "lintbook": ("lintbook.toml", ".lintbook/rules/no-dbg.md", ".lintbook/gen/no-dbg.df",
                 "fixtures/good.rs", "fixtures/bad.rs", "README.md"),
    "gptlint": ("package.json", "package-lock.json", "gptlint.config.mjs", ".gptlint/comment-implementation-agreement.md",
                "fixtures/good.js", "fixtures/bad.js", "README.md"),
}


def scaffold(backend, target):
    if backend not in FILES:
        raise ValueError("Unsupported backend: " + backend)
    source = PACKAGE / "templates" / backend
    files = [(source / name, Path(name)) for name in FILES[backend]]
    files.append((PACKAGE / "LICENSE", Path("LICENSE")))
    for path, _ in files:
        if not path.is_file() or not path.resolve().is_relative_to(PACKAGE):
            raise ValueError("Missing or escaping packaged template: " + str(path))
    target = Path(target).expanduser().absolute()
    target.mkdir(parents=True, exist_ok=False)
    created = []
    directories = set()
    try:
        for path, relative in files:
            destination = target / relative
            parent = destination.parent
            while parent != target:
                directories.add(parent)
                parent = parent.parent
            destination.parent.mkdir(parents=True, exist_ok=True)
            with destination.open("xb") as output, path.open("rb") as input_file:
                created.append(destination)
                shutil.copyfileobj(input_file, output)
    except BaseException:
        for destination in reversed(created):
            destination.unlink(missing_ok=True)
        for directory in sorted(directories, key=lambda path: len(path.parts), reverse=True):
            try:
                directory.rmdir()
            except OSError:
                pass
        try:
            target.rmdir()
        except OSError:
            pass
        raise
    return {"path": str(target), "backend": backend, "status": "example",
            "native_validated": False, "policy_activated": False,
            "next": "Adapt the example to the actual standard and run the real native linter and fixtures."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    create = sub.add_parser("scaffold")
    create.add_argument("--backend", choices=tuple(FILES), required=True)
    create.add_argument("--target", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(scaffold(args.backend, args.target), indent=2))
    except (OSError, ValueError) as error:
        print("lintify: " + str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

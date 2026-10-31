#!/usr/bin/env python3
"""Build/check Skillify's standalone release copy of the Codify engine."""
import argparse
import os
from pathlib import Path
import sys
sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parent.parent


def inventory():
    source = ROOT / 'skills/codify'
    paths = [source / 'LICENSE', source / 'references/command-definitions.md', *[source / 'scripts' / name for name in
        ('codify.py', 'workflow_authoring.py', 'tkstack_state.py', 'command_schema.py', 'command.schema.json', 'command_manual.py', 'json_contract.py', 'package_runtime.py')]]
    for directory in (source / 'templates', source / 'scripts/ai-runtime', source / 'requirements'):
        for parent, dirs, files in os.walk(directory, followlinks=False):
            dirs[:] = sorted(name for name in dirs if name not in ('node_modules', '__pycache__', '.git', '.tkstack'))
            paths.extend(Path(parent) / name for name in sorted(files))
    return {path.relative_to(source): path.read_bytes() for path in paths}


def sync(check=False):
    destination = ROOT / 'skills/skillify/scripts/codify_runtime'
    expected = inventory()
    actual = {path.relative_to(destination): path.read_bytes() for path in destination.rglob('*') if path.is_file()}
    changed = sorted(str(path) for path in set(expected) | set(actual) if expected.get(path) != actual.get(path))
    if check and changed:
        raise ValueError('Codify release copy is stale: ' + ', '.join(changed))
    if not check:
        for path in set(actual) - set(expected):
            (destination / path).unlink()
        for path, data in expected.items():
            target = destination / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
    return changed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    try:
        changes = sync(args.check)
    except (OSError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 1
    print(f'Codify standalone release: {len(changes)} differences' if args.check else f'Updated {len(changes)} bundled files')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

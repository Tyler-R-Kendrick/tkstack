#!/usr/bin/env python3
"""Repository-scoped, read-only documentation completion hook adapters."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
sys.dont_write_bytecode = True
from check_docs import Snapshot, check, git

ROOT = Path(__file__).resolve().parent.parent


def same_repository(root, cwd):
    try:
        source = Path(git(root, 'rev-parse', '--path-format=absolute', '--git-common-dir').decode().strip()).resolve()
        current = Path(git(cwd, 'rev-parse', '--path-format=absolute', '--git-common-dir').decode().strip()).resolve()
        return source == current
    except (OSError, ValueError, subprocess.SubprocessError):
        return False


def evaluate(root, harness, event, cwd):
    if not isinstance(event, dict):
        raise ValueError('Documentation hook input must be an object')
    selected = event.get('cwd') or next(iter(event.get('workspace_roots', [])), str(cwd))
    if not isinstance(selected, str) or not same_repository(root, Path(selected)):
        return {}
    if harness == 'cursor':
        if type(event.get('loop_count')) is not int or event['loop_count'] < 0 or event.get('status') not in ('completed', 'aborted', 'error'):
            raise ValueError('Cursor Stop requires status and an integer loop_count')
        if event['status'] != 'completed' or event['loop_count'] != 0:
            return {}
    else:
        if type(event.get('stop_hook_active')) is not bool:
            raise ValueError('Stop requires an actual boolean stop_hook_active')
        if event['stop_hook_active']:
            return {}
    snapshot = Snapshot(Path(selected))
    errors = check(snapshot)
    if not errors:
        return {}
    reason = 'Update this repository documentation before finishing.\n' + '\n'.join(errors[:12]) + '\nRun python3 scripts/check_docs.py check after reviewing/refreshing the named areas. Do not refresh without reviewing the docs.'
    return {'followup_message': reason} if harness == 'cursor' else {'decision': 'block', 'reason': reason}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--harness', choices=['codex', 'claude', 'cursor'], required=True)
    args = parser.parse_args()
    try:
        raw = sys.stdin.read(1024 * 1024 + 1)
        if len(raw.encode()) > 1024 * 1024:
            raise ValueError('Hook input exceeds 1 MiB')
        result = evaluate(ROOT, args.harness, json.loads(raw), Path.cwd())
        print(json.dumps(result))
        return 0
    except (OSError, ValueError, TypeError, KeyError, subprocess.SubprocessError) as error:
        print('Documentation hook: ' + str(error), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())

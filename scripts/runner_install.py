"""Publish ownership-checked, repeatable entrypoints in explicitly selected state roots."""
import hashlib
import fcntl
import argparse
import json
import os
from pathlib import Path
import shlex
import tempfile
import sys
import time

from tkstack_state import ensure_state, state_root, SCOPES


def launcher_text(root):
    return ('#!/usr/bin/env bash\nset -euo pipefail\n' +
        '# Generated tkstack runner; source ' + hashlib.sha256(str(root).encode()).hexdigest()[:16] + '\n' +
        'tkstack_python=' + shlex.quote(str(root / '.tkstack/runtime/command-schema/bin/python')) + '\n' +
        'if [ ! -x "$tkstack_python" ]; then tkstack_python="${TKSTACK_PYTHON:-python3}"; fi\n' +
        'exec "$tkstack_python" -B ' + shlex.quote(str(root / 'scripts/tkstack.py')) + ' "$@"\n')


def plan(root, state):
    target, receipt = state / 'tkstack', state / 'runner-owner.json'
    text = launcher_text(root)
    expected = {'version': 1, 'source': str(root), 'sha256': hashlib.sha256(text.encode()).hexdigest()}
    for path in (state, target, receipt):
        if path.is_symlink():
            raise ValueError('Runner ownership paths must not be symlinks: ' + str(path))
    previous = json.loads(receipt.read_text()) if receipt.exists() else None
    if previous is not None and (not isinstance(previous, dict) or previous.get('source') != str(root)):
        raise ValueError('Runner belongs to another source checkout: ' + str(state))
    if target.exists():
        if not target.is_file():
            raise ValueError('Runner path is not a regular file: ' + str(target))
        observed = hashlib.sha256(target.read_bytes()).hexdigest()
        if previous is None or previous.get('sha256') != observed:
            raise ValueError('Refusing to replace a foreign or modified runner: ' + str(target))
    changed = previous != expected or not target.exists() or target.read_text() != text or target.stat().st_mode & 0o777 != 0o755
    return target, receipt, text, expected, changed


def check(root, state):
    if plan(root, state)[-1]:
        raise ValueError('Scoped tkstack executable is missing or stale: ' + str(state / 'tkstack'))


def publish(root, state):
    plan(root, state)
    ensure_state(state)
    lock = state / '.runner-install.lock'
    if lock.is_symlink():
        raise ValueError('Runner lock must not be a symlink')
    with lock.open('a+') as stream:
        deadline = time.monotonic() + 5
        while True:
            try:
                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError as error:
                if time.monotonic() >= deadline:
                    raise ValueError('Another setup owns this runner; retry after it finishes') from error
                time.sleep(0.01)
        return _publish_owned(root, state)


def _publish_owned(root, state):
    target, receipt, text, expected, changed = plan(root, state)
    if not changed:
        return target
    for path, content, mode in [(target, text, 0o755), (receipt, json.dumps(expected, sort_keys=True) + '\n', 0o600)]:
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(dir=state, prefix='.runner-', delete=False, mode='w') as stream:
                temporary = Path(stream.name)
                stream.write(content)
                os.fchmod(stream.fileno(), mode)
            temporary.replace(path)
            temporary = None
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
    return target


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--scope', choices=SCOPES, default='workspace')
    cli.add_argument('--project', type=Path)
    mode = cli.add_mutually_exclusive_group()
    mode.add_argument('--check', action='store_true')
    mode.add_argument('--dry-run', action='store_true')
    args = cli.parse_args()
    root = Path(__file__).resolve().parent.parent
    try:
        state = state_root(args.scope, args.project)
        if args.check:
            check(root, state)
        elif args.dry_run:
            plan(root, state)
        elif not args.dry_run:
            publish(root, state)
        print(json.dumps({'path': str(state / 'tkstack'), 'scope': args.scope,
            'status': 'verified' if args.check else 'planned' if args.dry_run else 'installed'}))
        return 0
    except (OSError, ValueError) as error:
        print('tkstack runner setup: ' + str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())

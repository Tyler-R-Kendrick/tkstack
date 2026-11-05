#!/usr/bin/env python3
"""Install this source repository's Git docs gate without replacing foreign hooks."""
import argparse
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'src'))
from check_docs import git
from tkstack_state import ensure_state

ROOT = Path(__file__).resolve().parent.parent
MARKER = '# tkstack Git docs hook'


def tkstack_owned(path):
    """True when path is one of our dispatchers. Never chain one of those."""
    try:
        if not os.path.lexists(path):
            return False
        target = path.resolve() if path.is_symlink() else path
        if not target.is_file():
            return False
        return MARKER in target.read_text(errors='replace')
    except OSError:
        return False


def wrapper(root, backup, chain):
    lines = ['#!/usr/bin/env bash', 'set -euo pipefail', MARKER]
    if chain:
        lines += [
            'tkstack_previous=' + shlex.quote(str(backup)),
            'if [ -x "$tkstack_previous" ] && ! grep -F -q ' + shlex.quote(MARKER) + ' "$tkstack_previous"; then',
            '  "$tkstack_previous" "$@"',
            'fi',
        ]
    lines.append('exec ' + shlex.quote(str(root / '.githooks/pre-commit')) + ' "$@"')
    return '\n'.join(lines) + '\n'


def plan(root):
    try:
        top = Path(git(root, 'rev-parse', '--show-toplevel').decode().strip()).resolve()
    except ValueError:
        return {'status': 'not-a-git-checkout'}
    if top != root.resolve():
        return {'status': 'not-a-git-checkout'}
    directory = Path(git(root, 'rev-parse', '--path-format=absolute', '--git-path', 'hooks').decode().strip())
    source = root / '.githooks/pre-commit'
    if not source.is_file() or not os.access(source, os.X_OK):
        raise ValueError('Versioned pre-commit handler is missing or not executable')
    hook = directory / 'pre-commit'
    if directory.resolve() == source.parent.resolve():
        return {'status': 'managed-path', 'hook': str(hook)}
    common = Path(git(root, 'rev-parse', '--path-format=absolute', '--git-common-dir').decode().strip())
    if directory.resolve() != (common / 'hooks').resolve():
        raise ValueError('Existing core.hooksPath is managed elsewhere; preserve it and call ' + str(source) + ' from its pre-commit hook')
    backup = directory / 'pre-commit.tkstack-previous'
    receipt = root / '.tkstack/git-hooks/ownership.json'
    state = json.loads(receipt.read_text()) if receipt.is_file() else None
    if receipt.is_symlink():
        raise ValueError('Git hook receipt must not be a symlink')
    if state is not None and (not isinstance(state, dict) or type(state.get('version')) is not int or state.get('version') != 1 or state.get('source') != str(root) or state.get('hook') != str(hook)):
        raise ValueError('Existing Git hook installation belongs to another checkout')
    existing = os.path.lexists(hook)
    hook_owned = existing and tkstack_owned(hook)
    backup_exists = os.path.lexists(backup)
    backup_owned = backup_exists and tkstack_owned(backup)
    if state is not None and existing:
        if hook.is_symlink() or not hook.is_file() or hashlib.sha256(hook.read_bytes()).hexdigest() != state.get('sha256'):
            raise ValueError('Installed Git hook was modified; preserve it before reinstalling')
    # A tkstack backup is the fork-bomb case (another worktree's dispatcher, or a
    # previous install that renamed our hook onto the path it then calls). Drop it.
    if state is None and backup_exists and not backup_owned:
        raise ValueError('Unowned previous-hook backup already exists')
    preserve = state is None and existing and not hook_owned
    chain = preserve or (backup_exists and not backup_owned)
    expected = wrapper(root, backup, chain)
    changed = state is None or not existing or hook_owned and backup_owned or hook.read_text() != expected or hook.stat().st_mode & 0o777 != 0o755
    return {'status': 'planned' if changed else 'installed', 'hook': str(hook), 'backup': str(backup),
            'receipt': str(receipt), 'text': expected, 'preserve': preserve, 'drop_backup': backup_owned}


@contextmanager
def writer(root):
    directory = ensure_state(root / '.tkstack/git-hooks')
    lock = directory / 'install.lock'
    if lock.is_symlink():
        raise ValueError('Git hook lock must not be a symlink')
    with lock.open('a+') as stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise ValueError('Another Git hook setup is running; retry after it finishes') from error
        yield


def setup(root, dry_run=False, check=False, uninstall=False):
    result = plan(root)
    if result['status'] in ('not-a-git-checkout', 'managed-path'):
        return {key: value for key, value in result.items() if key != 'text'}
    if uninstall:
        receipt = Path(result['receipt'])
        if not receipt.is_file():
            return {'status': 'not-installed'}
        if not dry_run:
            with writer(root):
                result = plan(root)
                hook, backup = Path(result['hook']), Path(result['backup'])
                if os.path.lexists(backup) and not tkstack_owned(backup):
                    backup.replace(hook)
                else:
                    if os.path.lexists(hook):
                        hook.unlink()
                    if os.path.lexists(backup):
                        backup.unlink()
                receipt.unlink()
        return {'status': 'removed', 'hook': result['hook']}
    if check:
        if result['status'] != 'installed':
            raise ValueError('Repository Git docs hook is missing or stale; rerun setup')
    elif not dry_run:
        with writer(root):
            result = plan(root)
            if result['status'] != 'installed':
                hook, backup, receipt = [Path(result[name]) for name in ('hook', 'backup', 'receipt')]
                hook.parent.mkdir(parents=True, exist_ok=True)
                if result['preserve']:
                    shutil.copy2(hook, backup, follow_symlinks=False)
                temporary = None
                try:
                    with tempfile.NamedTemporaryFile(dir=hook.parent, prefix='.pre-commit-', mode='w', delete=False) as output:
                        temporary = Path(output.name)
                        output.write(result['text'])
                        os.fchmod(output.fileno(), 0o755)
                    temporary.replace(hook)
                    temporary = None
                    if result.get('drop_backup') and os.path.lexists(backup) and tkstack_owned(backup):
                        backup.unlink()
                    state = {'version': 1, 'source': str(root), 'hook': str(hook), 'sha256': hashlib.sha256(result['text'].encode()).hexdigest()}
                    receipt.write_text(json.dumps(state, sort_keys=True) + '\n')
                finally:
                    if temporary is not None:
                        temporary.unlink(missing_ok=True)
        result['status'] = 'installed'
    return {key: value for key, value in result.items() if key in ('status', 'hook', 'backup')}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--dry-run', action='store_true')
    group.add_argument('--check', action='store_true')
    group.add_argument('--uninstall', action='store_true')
    args = parser.parse_args()
    try:
        print(json.dumps(setup(ROOT, args.dry_run, args.check, args.uninstall)))
        return 0
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        print('Repository hook setup: ' + str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())

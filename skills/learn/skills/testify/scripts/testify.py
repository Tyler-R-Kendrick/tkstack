#!/usr/bin/env python3
"""Plan, create, or run a focused Python CLI contract test from explicit evidence."""
import argparse
from dataclasses import dataclass
import json
import locale
import os
from pathlib import Path, PurePosixPath
import re
import signal
import subprocess
import sys
import tempfile
import threading
import time
sys.dont_write_bytecode = True
from package_runtime import can_wait_unreaped, reap_owned, wait_unreaped

RUN_TIMEOUT = 120
OUTPUT_LIMIT = 1024 * 1024


class RunInterrupted(Exception):
    def __init__(self, signum):
        self.signum = signum
        super().__init__(f'Test run interrupted by signal {signum}')


@dataclass(frozen=True)
class Case:
    name: str
    args: tuple[str, ...]
    exit_code: int
    stdout_text: str | None
    stdout_json: str | None  # Canonical serialized JSON, including a literal null.
    stderr_contains: str | None


@dataclass(frozen=True)
class Spec:
    entrypoint: str
    risk: str
    distinction: str
    timeout: int
    cases: tuple[Case, ...]


def pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError('Duplicate JSON key: ' + key)
        result[key] = value
    return result


def relative(value):
    if not isinstance(value, str) or not value or '\\' in value:
        raise ValueError('Use repository-relative POSIX paths')
    path = PurePosixPath(value)
    if path.is_absolute() or '..' in path.parts or str(path) != value:
        raise ValueError('Use literal repository-relative paths without traversal')
    return path


def contained(root, name, existing):
    path = root / relative(name)
    for item in (path, *path.parents):
        if item == root:
            break
        if item.is_symlink():
            raise ValueError('Symlinked test/entrypoint paths are not permitted: ' + str(item))
    if not path.resolve().is_relative_to(root):
        raise ValueError('Path escapes the project')
    if existing and not path.is_file():
        raise ValueError('Python entrypoint or test does not exist: ' + str(path))
    return path


def parse(path, root):
    raw = path.read_bytes()
    if len(raw) > 256 * 1024:
        raise ValueError('Test specification exceeds 256 KiB')
    data = json.loads(raw, object_pairs_hook=pairs, parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Nonfinite JSON')))
    required = {'version', 'entrypoint', 'risk', 'distinction', 'cases'}
    if not isinstance(data, dict) or not required <= set(data) or set(data) - (required | {'timeout'}) or type(data['version']) is not int or data['version'] != 1:
        raise ValueError('Specification requires version 1, entrypoint, risk, distinction, cases, and an optional timeout')
    entry = relative(data['entrypoint'])
    if entry.suffix != '.py':
        raise ValueError('This backend tests Python CLI entrypoints only')
    contained(root, str(entry), True)
    if any(not isinstance(data[k], str) or len(data[k].strip()) < 20 for k in ('risk', 'distinction')):
        raise ValueError('Explain the concrete regression risk and distinct coverage')
    timeout = data.get('timeout', 30)
    if type(timeout) is not int or not 1 <= timeout <= 60:
        raise ValueError('Case timeout must be 1..60 seconds')
    if not isinstance(data['cases'], list) or not 1 <= len(data['cases']) <= 32:
        raise ValueError('Supply 1..32 concrete contract cases')
    cases, names, signatures = [], set(), set()
    for item in data['cases']:
        if not isinstance(item, dict) or set(item) - {'name', 'args', 'exit', 'stdout_text', 'stdout_json', 'stderr_contains'} or not {'name', 'args', 'exit'} <= set(item):
            raise ValueError('Each case needs name, args, exit, and an independent output oracle')
        name, args, code = item['name'], item['args'], item['exit']
        if not isinstance(name, str) or not re.fullmatch(r'[a-z][a-z0-9_-]{0,63}', name) or name in names:
            raise ValueError('Case names must be unique lowercase identifiers')
        names.add(name)
        if not isinstance(args, list) or len(args) > 64 or any(not isinstance(x, str) or '\x00' in x for x in args):
            raise ValueError('Case arguments must be an array of strings')
        if type(code) is not int or not 0 <= code <= 255:
            raise ValueError('Expected exit must be an integer in 0..255')
        outputs = {'stdout_text', 'stdout_json', 'stderr_contains'} & set(item)
        if not outputs or {'stdout_text', 'stdout_json'} <= outputs:
            raise ValueError('Supply a text or JSON output oracle and/or a nonempty stderr fragment')
        for key in ('stdout_text', 'stderr_contains'):
            if key in item and (not isinstance(item[key], str) or (key == 'stderr_contains' and not item[key])):
                raise ValueError(key + ' must be text; stderr fragments must not be empty')
        encoded = json.dumps(item['stdout_json'], ensure_ascii=False, sort_keys=True, allow_nan=False) if 'stdout_json' in item else None
        signature = (tuple(args), code, item.get('stdout_text'), encoded, item.get('stderr_contains'))
        if signature in signatures:
            raise ValueError('Duplicate contract case: ' + name)
        signatures.add(signature)
        cases.append(Case(name, *signature))
    return Spec(str(entry), data['risk'].strip(), data['distinction'].strip(), timeout, tuple(cases))


def render(spec, target):
    rows = []
    for case in spec.cases:
        row = {'name': case.name, 'args': case.args, 'exit': case.exit_code}
        if case.stdout_text is not None:
            row['stdout_text'] = case.stdout_text
        if case.stdout_json is not None:
            row['stdout_json'] = json.loads(case.stdout_json)
        if case.stderr_contains is not None:
            row['stderr_contains'] = case.stderr_contains
        rows.append(row)
    # repr produces inert Python literals; test input is passed as argv, never shell text.
    return f'''"""Behavioral CLI contract generated from reviewed case evidence."""
import json
import locale
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[{len(target.parts) - 1}]
ENTRYPOINT = ROOT / {spec.entrypoint!r}
RISK = {spec.risk!r}
DISTINCTION = {spec.distinction!r}
CASES = {rows!r}


def run_case(args, cwd, timeout):
    # Direct POSIX runs own a process group so a timed-out CLI cannot leave
    # ordinary descendants behind. The compiled runner owns its outer group.
    own_group = os.name == 'posix' and os.environ.get('TKSTACK_CODIFY_EXECUTION') != '1'
    if own_group and (signal.getsignal(signal.SIGCHLD) != signal.SIG_DFL or
            not hasattr(signal, 'pthread_sigmask') or
            not all(hasattr(os, name) for name in ('waitid', 'P_PID', 'WEXITED', 'WNOHANG', 'WNOWAIT'))):
        raise ValueError('Cases require non-reaping POSIX process supervision')
    with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
        process = subprocess.Popen(args, cwd=cwd, stdout=out, stderr=err,
                                   start_new_session=own_group)
        try:
            if own_group:
                deadline = time.monotonic() + timeout
                while True:
                    try:
                        if os.waitid(os.P_PID, process.pid, os.WEXITED | os.WNOHANG | os.WNOWAIT):
                            break
                    except ChildProcessError as error:
                        process.returncode = 255
                        raise ValueError('Case process ownership was lost') from error
                    if time.monotonic() >= deadline:
                        raise subprocess.TimeoutExpired(process.args, timeout)
                    time.sleep(.01)
            else:
                process.wait(timeout=timeout)
        finally:
            if own_group and process.returncode is None:
                mask = signal.pthread_sigmask(signal.SIG_BLOCK, {{signal.SIGINT, signal.SIGTERM, signal.SIGCHLD}})
                try:
                    try:
                        os.waitid(os.P_PID, process.pid, os.WEXITED | os.WNOHANG | os.WNOWAIT)
                    except ChildProcessError as error:
                        process.returncode = 255
                        raise ValueError('Case process ownership was lost') from error
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    process.wait()
                finally:
                    signal.pthread_sigmask(signal.SIG_SETMASK, mask)
            elif process.returncode is None:
                process.kill()
                process.wait(timeout=2)
        out.seek(0)
        err.seek(0)
        stdout, stderr = out.read(1048577), err.read(1048577)
        if len(stdout) > 1048576 or len(stderr) > 1048576:
            raise ValueError('Case output exceeds 1 MiB per stream')
        encoding = locale.getpreferredencoding(False)
        return subprocess.CompletedProcess(args, process.returncode, stdout.decode(encoding), stderr.decode(encoding))


class CliContractTests(unittest.TestCase):
    def test_contract_cases(self):
        for case in CASES:
            with self.subTest(case=case['name']), tempfile.TemporaryDirectory(prefix='testify-') as temp:
                args = [arg.replace('{{root}}', str(ROOT)).replace('{{tmp}}', temp) for arg in case['args']]
                result = run_case([sys.executable, str(ENTRYPOINT), *args], cwd=temp, timeout={spec.timeout})
                self.assertEqual(result.returncode, case['exit'], result.stderr)
                if 'stdout_text' in case:
                    self.assertEqual(result.stdout, case['stdout_text'])
                if 'stdout_json' in case:
                    self.assertEqual(json.loads(result.stdout), case['stdout_json'])
                if 'stderr_contains' in case:
                    self.assertIn(case['stderr_contains'], result.stderr)


if __name__ == '__main__':
    unittest.main()
'''


def run_test(path, root):
    own_group = os.name == 'posix' and os.environ.get('TKSTACK_CODIFY_EXECUTION') != '1'
    if own_group and (not can_wait_unreaped() or threading.current_thread() is not threading.main_thread()):
        raise ValueError('Test execution requires non-reaping POSIX process supervision')
    env = {**os.environ, 'TKSTACK_CODIFY_EXECUTION': '1'}
    with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
        command = [sys.executable, '-B', str(path)]
        process, pending = None, None
        def interrupt(signum, _frame):
            nonlocal pending
            if process is None:
                pending = signum
            else:
                raise RunInterrupted(signum)
        previous = {sig: signal.signal(sig, interrupt) for sig in (signal.SIGTERM, signal.SIGINT)} if own_group else {}
        try:
            try:
                if pending is not None:
                    raise RunInterrupted(pending)
                process = subprocess.Popen(command, cwd=root, env=env, stdout=out, stderr=err,
                                           start_new_session=own_group)
                if pending is not None:
                    raise RunInterrupted(pending)
                if own_group:
                    wait_unreaped(process, RUN_TIMEOUT)
                else:
                    process.wait(timeout=RUN_TIMEOUT)
            except RunInterrupted:
                for sig in previous:
                    signal.signal(sig, signal.SIG_IGN)
                raise
            finally:
                if process is not None and own_group and process.returncode is None:
                    reap_owned(process, kill_group=True)
                elif process is not None and process.returncode is None:
                    process.kill()
                    process.wait(timeout=2)
        finally:
            for sig, handler in previous.items():
                signal.signal(sig, handler)
        out.seek(0)
        err.seek(0)
        stdout, stderr = out.read(OUTPUT_LIMIT + 1), err.read(OUTPUT_LIMIT + 1)
        if len(stdout) > OUTPUT_LIMIT or len(stderr) > OUTPUT_LIMIT:
            raise ValueError('Test output exceeds 1 MiB per stream')
        encoding = locale.getpreferredencoding(False)
        return subprocess.CompletedProcess(command, process.returncode,
                                           stdout.decode(encoding), stderr.decode(encoding))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('plan', 'create', 'run'))
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--target', required=True, help='Project-relative tests/test_*.py')
    parser.add_argument('--spec', type=Path, help='Reviewed JSON specification, required for plan/create')
    args = parser.parse_args(argv)
    try:
        root = args.project.resolve(strict=True)
        target = relative(args.target)
        if len(target.parts) < 2 or target.parts[0] != 'tests' or not target.name.startswith('test_') or target.suffix != '.py':
            raise ValueError('Target must be a tests/.../test_*.py path')
        path = contained(root, str(target), args.command == 'run')
        if args.command == 'run':
            if args.spec is not None:
                raise ValueError('Run accepts no specification')
            started = time.monotonic()
            try:
                run = run_test(path, root)
            except subprocess.TimeoutExpired as error:
                print(json.dumps({'status': 'timeout', 'returncode': None, 'stdout': '', 'stderr': str(error),
                                  'elapsed_ms': round((time.monotonic() - started) * 1000, 3),
                                  'timeout_seconds': RUN_TIMEOUT}))
                return 124
            except RunInterrupted as error:
                print(json.dumps({'status': 'interrupted', 'returncode': None, 'stdout': '', 'stderr': str(error),
                                  'elapsed_ms': round((time.monotonic() - started) * 1000, 3),
                                  'timeout_seconds': RUN_TIMEOUT, 'signal': error.signum}))
                return 128 + error.signum
            print(json.dumps({'status': 'pass' if run.returncode == 0 else 'fail', 'returncode': run.returncode,
                              'stdout': run.stdout, 'stderr': run.stderr,
                              'elapsed_ms': round((time.monotonic() - started) * 1000, 3),
                              'timeout_seconds': RUN_TIMEOUT}))
            return 0 if run.returncode == 0 else 1
        if args.spec is None:
            raise ValueError('Plan/create require --spec')
        if path.exists() or path.is_symlink():
            raise ValueError('Refusing to overwrite existing target: ' + str(path))
        if not path.parent.is_dir():
            raise ValueError('Test parent directory must already exist')
        spec = parse(args.spec, root)
        content = render(spec, target)
        if args.command == 'plan':
            print(json.dumps({'status': 'planned', 'target': str(path), 'risk': spec.risk,
                              'distinction': spec.distinction, 'cases': len(spec.cases), 'content': content}))
            return 0
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0), 0o644)
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as output:
                output.write(content)
        except BaseException:
            path.unlink(missing_ok=True)
            raise
        print(json.dumps({'status': 'created', 'target': str(path), 'cases': len(spec.cases)}))
        return 0
    except (OSError, ValueError, TypeError, KeyError, subprocess.TimeoutExpired) as error:
        print('testify: ' + str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())

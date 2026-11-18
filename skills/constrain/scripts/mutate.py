#!/usr/bin/env python3
"""Run selected Cosmic Ray mutations against individually selected unittest cases."""
import argparse
import difflib
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import select
import shutil
import signal
import subprocess
import sys
import tarfile
import time

import json_contract
import tkstack_state


ENGINE_VERSION = 'cosmic-ray, version 8.9.0'
TEST_ID = re.compile(r'^[A-Za-z_]\w*(?:\.[A-Za-z_]\w*){2,}$')
OPERATOR = re.compile(r'^core/[A-Za-z][A-Za-z0-9_]*$')
ACTIVE = None
GIT_ENVIRONMENT = {'GIT_DIR', 'GIT_WORK_TREE', 'GIT_COMMON_DIR', 'GIT_INDEX_FILE',
                   'GIT_OBJECT_DIRECTORY', 'GIT_ALTERNATE_OBJECT_DIRECTORIES',
                   'GIT_CEILING_DIRECTORIES', 'GIT_DISCOVERY_ACROSS_FILESYSTEM'}


def clean_git_environment():
    return {key: value for key, value in os.environ.items() if key not in GIT_ENVIRONMENT}


def stop_group(process):
    if process.returncode is not None:
        return
    mask = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGINT, signal.SIGTERM, signal.SIGCHLD})
    try:
        try:
            # A reaped leader may have had its PID reused; do not signal it.
            os.waitid(os.P_PID, process.pid, os.WEXITED | os.WNOHANG | os.WNOWAIT)
        except ChildProcessError as error:
            process.returncode = 255
            raise ValueError('Lost child ownership; process group was not signaled') from error
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait()
    finally:
        signal.pthread_sigmask(signal.SIG_SETMASK, mask)


def interrupted(signum, frame):
    if ACTIVE is not None:
        stop_group(ACTIVE)
    raise SystemExit(128 + signum)


def invoke(argv, cwd, timeout, env=None):
    """Bound a local process and retain limited diagnostics, including elapsed time."""
    global ACTIVE
    start = time.monotonic()
    with io.BytesIO() as output:
        process = subprocess.Popen(argv, cwd=cwd, stdin=subprocess.DEVNULL,
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                   env=env, start_new_session=(os.name == 'posix'))
        ACTIVE = process
        timed_out = False
        try:
            if os.name == 'posix':
                # Leave the leader unreaped until its group is killed: this
                # prevents PID reuse and cleans ordinary children even if the
                # leader exited before its deadline.
                deadline = time.monotonic() + timeout
                while not os.waitid(os.P_PID, process.pid, os.WEXITED | os.WNOHANG | os.WNOWAIT):
                    if select.select([process.stdout], [], [], .01)[0]:
                        data = os.read(process.stdout.fileno(), 65536)
                        if output.tell() < 65537:
                            output.write(data[:65537 - output.tell()])
                    if time.monotonic() >= deadline:
                        timed_out = True
                        break
            else:
                try:
                    data, _ = process.communicate(timeout=timeout)
                    output.write(data[:65537])
                except subprocess.TimeoutExpired:
                    timed_out = True
        finally:
            stop_group(process)
            ACTIVE = None
        if os.name == 'posix':
            os.set_blocking(process.stdout.fileno(), False)
            while True:
                try:
                    data = os.read(process.stdout.fileno(), 65536)
                except BlockingIOError:
                    break
                if not data:
                    break
                if output.tell() < 65537:
                    output.write(data[:65537 - output.tell()])
        process.stdout.close()
        output.seek(0)
        text = output.read(65537)
    return {'exit': process.returncode, 'timeout': timed_out,
            'elapsed_ms': round((time.monotonic() - start) * 1000, 3),
            'output': text[:65536].decode('utf-8', errors='replace'),
            'output_truncated': len(text) > 65536}


def git(repo, *args):
    result = invoke(['git', '-C', str(repo), *args], repo, 15, clean_git_environment())
    if result['exit'] != 0 or result['timeout']:
        raise ValueError('git failed: ' + result['output'])
    return result['output'].strip()


def load_plan(raw):
    if len(raw) > 1024 * 1024:
        raise ValueError('Plan exceeds 1 MiB')
    plan = json_contract.loads(raw)
    if not isinstance(plan, dict) or set(plan) != {'version', 'tests', 'mutants'} or type(plan['version']) is not int or plan['version'] != 1:
        raise ValueError('Plan needs version 1, tests and mutants')
    tests, mutants = plan['tests'], plan['mutants']
    if not isinstance(tests, list) or not 1 <= len(tests) <= 64 or any(not isinstance(t, str) or not TEST_ID.fullmatch(t) for t in tests):
        raise ValueError('Select 1-64 fully qualified unittest test IDs')
    if len(set(tests)) != len(tests):
        raise ValueError('Test IDs must be unique')
    if not isinstance(mutants, list) or not 1 <= len(mutants) <= 64 or len(mutants) * len(tests) > 512:
        raise ValueError('Select 1-64 mutants and at most 512 test/mutant cells')
    ids = set()
    for item in mutants:
        required = {'id', 'module', 'operator', 'occurrence'}
        if not isinstance(item, dict) or set(item) not in (required, required | {'source_sha256'}):
            raise ValueError('Each mutant needs id, module, operator and occurrence')
        if not isinstance(item['id'], str) or not item['id'].strip() or item['id'] in ids:
            raise ValueError('Mutant IDs must be nonempty and unique')
        ids.add(item['id'])
        module = item['module']
        if not isinstance(module, str) or not module or PurePosixPath(module).is_absolute() or '..' in PurePosixPath(module).parts or not module.endswith('.py'):
            raise ValueError('Mutant module must be a contained Python path')
        if not isinstance(item['operator'], str) or not OPERATOR.fullmatch(item['operator']):
            raise ValueError('Use a Cosmic Ray core operator')
        if type(item['occurrence']) is not int or not 0 <= item['occurrence'] <= 100000:
            raise ValueError('Mutant occurrence must be a nonnegative integer')
        if 'source_sha256' in item and (not isinstance(item['source_sha256'], str) or not re.fullmatch(r'[0-9a-f]{64}', item['source_sha256'])):
            raise ValueError('source_sha256 must be a lowercase SHA-256 digest')
    return plan


def classify(result):
    text = result['output']
    if result['timeout']:
        return 'timeout'
    if not re.search(r'Ran 1 test in ', text) or 'skipped=' in text or 'SKIP:' in text:
        return 'not_run_or_skipped'
    if result['exit'] == 0 and re.search(r'^OK\s*$', text, re.M):
        return 'passed'
    if result['exit'] != 0 and re.search(r'^FAIL: ', text, re.M) and not re.search(r'^ERROR: ', text, re.M) and re.search(r'^FAILED \(failures=\d+\)', text, re.M):
        return 'assertion_failure'
    return 'error'


def experiment(repo, plan_path, engine, output, test_timeout, total_timeout, repetitions):
    repo = repo.resolve(strict=True)
    plan_path = plan_path.resolve(strict=True)
    engine = engine.resolve(strict=True)
    if not engine.is_file() or not os.access(engine, os.X_OK):
        raise ValueError('Cosmic Ray executable is unavailable')
    with plan_path.open('rb') as stream:
        plan_bytes = stream.read(1024 * 1024 + 1)
    plan = load_plan(plan_bytes)
    version = invoke([str(engine), '--version'], repo, 15)
    if version['exit'] != 0 or version['output'].strip() != ENGINE_VERSION:
        raise ValueError('Expected ' + ENGINE_VERSION)
    commit = git(repo, 'rev-parse', '--verify', 'HEAD^{commit}')
    if git(repo, 'status', '--porcelain', '--untracked-files=no'):
        raise ValueError('Commit tracked changes before measuring; the snapshot is HEAD')
    for mutant in plan['mutants']:
        git(repo, 'cat-file', '-e', commit + ':' + mutant['module'])
    started = time.monotonic()
    report = {'version': 1, 'commit': commit, 'plan_sha256': hashlib.sha256(plan_bytes).hexdigest(),
              'runner_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'json_contract_sha256': hashlib.sha256(Path(json_contract.__file__).read_bytes()).hexdigest(),
              'state_helper_sha256': hashlib.sha256(Path(tkstack_state.__file__).read_bytes()).hexdigest(),
              'engine': ENGINE_VERSION, 'engine_launcher_sha256': hashlib.sha256(engine.read_bytes()).hexdigest(),
              'python': sys.version, 'python_executable': sys.executable, 'test_timeout_seconds': test_timeout,
              'total_timeout_seconds': total_timeout, 'baseline': [], 'mutants': [], 'status': 'incomplete'}
    output.parent.mkdir(parents=True, exist_ok=True)
    # Reserve the receipt before executing any project code; never overwrite an earlier run.
    with output.open('x', encoding='utf-8') as receipt:
        try:
            with tkstack_state.session_tempdir(prefix='constrain-mutation-', project=repo) as temp:
                if os.pathsep in str(temp):
                    raise ValueError('Mutation scratch path cannot contain the Git ceiling separator')
                archive = temp / 'snapshot.tar'
                result = invoke(['git', '-C', str(repo), 'archive', '--format=tar', '--output', str(archive), commit], repo, 30, clean_git_environment())
                if result['exit'] != 0 or result['timeout']:
                    raise ValueError('Could not export frozen Git tree: ' + result['output'])

                def snapshot(name):
                    target = temp / name
                    target.mkdir()
                    with tarfile.open(archive) as tar:
                        tar.extractall(target, filter='data')
                    return target

                def remaining():
                    return total_timeout - (time.monotonic() - started)

                def run_test(root, test):
                    if remaining() <= 0:
                        return {'status': 'not_run', 'reason': 'total deadline'}
                    env = {**clean_git_environment(), 'PYTHONPATH': str(root), 'PYTHONDONTWRITEBYTECODE': '1',
                           'GIT_CEILING_DIRECTORIES': str(temp)}
                    result = invoke([sys.executable, '-B', '-m', 'unittest', test], root,
                                    min(test_timeout, remaining()), env)
                    result['status'] = classify(result)
                    return result

                for rep in range(repetitions):
                    for index, test in enumerate(plan['tests']):
                        if remaining() <= 0:
                            report['baseline'].append({'test': test, 'repetition': rep, 'status': 'not_run', 'reason': 'total deadline'})
                            continue
                        root = snapshot(f'baseline-{rep}-{index}')
                        report['baseline'].append({'test': test, 'repetition': rep, **run_test(root, test)})
                        shutil.rmtree(root)
                if any(row['status'] != 'passed' for row in report['baseline']):
                    report['status'] = 'baseline_invalid'
                    return report
                for index, mutant in enumerate(plan['mutants']):
                    row = {'id': mutant['id'], 'module': mutant['module'], 'operator': mutant['operator'],
                           'occurrence': mutant['occurrence'], 'tests': []}
                    report['mutants'].append(row)
                    if remaining() <= 0:
                        row['status'] = 'not_run'
                        continue
                    root = snapshot('mutant-' + str(index))
                    module = root / mutant['module']
                    if module.is_symlink() or not module.is_file() or not module.resolve().is_relative_to(root):
                        raise ValueError('Mutant module must be a contained regular file')
                    original = module.read_text()
                    row['source_sha256'] = hashlib.sha256(module.read_bytes()).hexdigest()
                    if 'source_sha256' in mutant and mutant['source_sha256'] != row['source_sha256']:
                        raise ValueError('Mutation source no longer matches the plan: ' + mutant['id'])
                    applied = invoke([str(engine), 'apply', str(module), mutant['operator'], str(mutant['occurrence'])],
                                     root, min(15, remaining()))
                    row['apply'] = applied
                    changed = module.read_text()
                    row['diff'] = ''.join(difflib.unified_diff(original.splitlines(keepends=True), changed.splitlines(keepends=True), fromfile='original', tofile='mutant'))
                    if applied['timeout']:
                        row['status'] = 'engine_timeout'
                    elif applied['exit'] != 0 or original == changed:
                        row['status'] = 'invalid_mutation'
                    else:
                        try:
                            compile(changed, str(module), 'exec')
                        except SyntaxError:
                            row['status'] = 'invalid_mutation'
                        else:
                            row['status'] = 'tested'
                            for test_index, test in enumerate(plan['tests']):
                                if remaining() <= 0:
                                    row['tests'].append({'test': test, 'status': 'not_run', 'reason': 'total deadline'})
                                    continue
                                cell = temp / f'cell-{index}-{test_index}'
                                shutil.copytree(root, cell, symlinks=True)
                                row['tests'].append({'test': test, **run_test(cell, test)})
                                shutil.rmtree(cell)
                    shutil.rmtree(root)
                report['status'] = 'complete' if all(row['status'] == 'tested' and all(t['status'] != 'not_run' for t in row['tests']) for row in report['mutants']) else 'incomplete'
        except Exception as error:
            report['status'] = 'error'
            report['error'] = str(error)
            raise
        finally:
            report['elapsed_ms'] = round((time.monotonic() - started) * 1000, 3)
            json.dump(report, receipt, indent=2, sort_keys=True, allow_nan=False)
            receipt.write('\n')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--engine', type=Path, required=True, help='Cosmic Ray 8.9.0 executable')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--test-timeout', type=int, default=15)
    parser.add_argument('--total-timeout', type=int, default=300)
    parser.add_argument('--baseline-repetitions', type=int, default=2)
    args = parser.parse_args()
    try:
        if (os.name != 'posix' or not hasattr(signal, 'pthread_sigmask') or
                signal.getsignal(signal.SIGCHLD) != signal.SIG_DFL or
                not all(hasattr(os, name) for name in ('waitid', 'P_PID', 'WEXITED', 'WNOHANG', 'WNOWAIT'))):
            raise ValueError('Mutation experiments require POSIX process-group and non-reaping wait support')
        if not 1 <= args.test_timeout <= 120 or not 1 <= args.total_timeout <= 540 or not 1 <= args.baseline_repetitions <= 5:
            raise ValueError('Timeouts or baseline repetitions exceed supported bounds')
        for sig in (signal.SIGTERM, signal.SIGINT):
            signal.signal(sig, interrupted)
        report = experiment(args.repo, args.plan, args.engine, args.output, args.test_timeout,
                            args.total_timeout, args.baseline_repetitions)
        print(json.dumps({'status': report['status'], 'receipt': str(args.output)}))
        return 0 if report['status'] == 'complete' else 1
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())

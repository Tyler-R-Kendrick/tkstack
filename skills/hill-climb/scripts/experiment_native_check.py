#!/usr/bin/env python3
"""Adapt a trusted native test command to structured experiment evidence.

The caller supplies argv and a reviewed regex with one named ``count`` group
matching the command's test-summary line. This process runs in the controller's
frozen snapshot and inherits its environment. It is not an isolation boundary,
and the supplied command and regex must be trusted to count real test work.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import selectors
import shutil
import signal
import subprocess
import sys
import time
import threading

from json_contract import loads

MAX_OUTPUT = 8192  # JSON-escaped output stays within the controller's capture limit.
MAX_TIMEOUT = 3600


def validate(config):
    if not isinstance(config, dict):
        raise ValueError('config must be an object')
    allowed = {'argv', 'work_regex', 'gate', 'metric', 'timeout_seconds', 'max_output_bytes', 'failure_exit_codes', 'quality'}
    if set(config) - allowed or not {'argv', 'work_regex', 'gate', 'metric'} <= set(config):
        raise ValueError('invalid native-check config fields')
    argv = config['argv']
    if not isinstance(argv, list) or not argv or any(not isinstance(a, str) or '\0' in a for a in argv) or not argv[0]:
        raise ValueError('argv must be a nonempty array of strings')
    regex = config['work_regex']
    if not isinstance(regex, str) or not regex or len(regex) > 512:
        raise ValueError('work_regex must be a nonempty bounded regex')
    try:
        pattern = re.compile(regex, re.MULTILINE)
    except re.error as error:
        raise ValueError(f'invalid work_regex: {error}') from error
    if set(pattern.groupindex) != {'count'} or pattern.groups != 1:
        raise ValueError('work_regex must have exactly one named count group')
    for name in ('gate', 'metric'):
        value = config[name]
        if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_.-]{0,63}', value):
            raise ValueError(f'{name} must be an identifier')
    timeout = config.get('timeout_seconds', 30)
    limit = config.get('max_output_bytes', 4096)
    codes = config.get('failure_exit_codes', [1])
    if type(timeout) not in (int, float) or not math.isfinite(timeout) or not 0 < timeout <= MAX_TIMEOUT:
        raise ValueError('timeout_seconds must be finite and positive')
    if type(limit) is not int or not 1 <= limit <= MAX_OUTPUT:
        raise ValueError(f'max_output_bytes must be between 1 and {MAX_OUTPUT}')
    if (not isinstance(codes, list) or not codes or len(set(codes)) != len(codes) or
            any(type(code) is not int or not 1 <= code <= 255 for code in codes)):
        raise ValueError('failure_exit_codes must contain distinct positive exit codes')
    if 'quality' in config:
        validate_quality(config['quality'])
        if limit > 4096:
            raise ValueError('combined checks require max_output_bytes at most 4096')
    return argv, pattern, timeout, limit, codes



def file_hash(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def validate_quality(config):
    if not isinstance(config, dict):
        raise ValueError('quality must be an object')
    required = {'argv', 'judge_file', 'judge_sha256', 'executable_sha256'}
    if set(config) - (required | {'dependencies', 'timeout_seconds'}) or not required <= set(config):
        raise ValueError('invalid quality judge config')
    argv = config['argv']
    if not isinstance(argv, list) or not argv or any(not isinstance(a, str) or '\0' in a for a in argv):
        raise ValueError('quality argv must be a string array')
    executable = Path(argv[0])
    judge = Path(config['judge_file'])
    if not executable.is_absolute() or not judge.is_absolute():
        raise ValueError('quality executable and judge must have absolute paths')
    executable = executable.resolve(strict=True)
    judge = judge.resolve(strict=True)
    root_value = os.environ.get('TKSTACK_EXPERIMENT_SNAPSHOT_ROOT')
    if not root_value or not Path(root_value).is_absolute():
        raise ValueError('quality checks require the runner-owned snapshot root')
    snapshot_root = Path(root_value).resolve(strict=True)
    if not snapshot_root.is_dir() or not Path.cwd().resolve().is_relative_to(snapshot_root):
        raise ValueError('working directory is outside the runner-owned snapshot root')
    if not executable.is_file() or not judge.is_file() or judge.is_relative_to(snapshot_root):
        raise ValueError('quality judge must be a trusted file outside the candidate snapshot')
    direct = executable == judge
    if not direct and (len(argv) < 2 or not Path(argv[1]).is_absolute() or Path(argv[1]).resolve(strict=True) != judge):
        raise ValueError('quality executable must directly invoke the trusted judge')
    if '{{case_file}}' not in argv:
        raise ValueError('quality judge must receive the case file')
    # Execute the resolved paths that were checked, not mutable symlink aliases.
    argv = list(argv)
    argv[0] = str(executable)
    if not direct:
        argv[1] = str(judge)
    pinned = [(executable, config['executable_sha256']), (judge, config['judge_sha256'])]
    dependencies = config.get('dependencies', [])
    if not isinstance(dependencies, list):
        raise ValueError('quality dependencies must be a list')
    for item in dependencies:
        if not isinstance(item, dict) or set(item) != {'path', 'sha256'}:
            raise ValueError('invalid quality dependency')
        dependency = Path(item['path'])
        if not dependency.is_absolute():
            raise ValueError('quality dependency must have an absolute path')
        dependency = dependency.resolve(strict=True)
        if not dependency.is_file() or dependency.is_relative_to(snapshot_root):
            raise ValueError('quality dependencies must be trusted files outside the candidate snapshot')
        pinned.append((dependency, item['sha256']))
    for path, expected in pinned:
        if not isinstance(expected, str) or not re.fullmatch(r'[0-9a-f]{64}', expected) or file_hash(path) != expected:
            raise ValueError('quality judge executable or dependency changed')
    timeout = config.get('timeout_seconds', 30)
    if type(timeout) not in (int, float) or not math.isfinite(timeout) or not 0 < timeout <= MAX_TIMEOUT:
        raise ValueError('invalid quality timeout')
    return argv, pinned, timeout


def apply_quality(result, config, case_file, case, case_sha, native_metric):
    argv, pinned, timeout = validate_quality(config)
    if '{{case}}' in argv and case is None:
        raise ValueError('quality command requires --case')
    argv = [str(case_file) if arg == '{{case_file}}' else case if arg == '{{case}}' else arg for arg in argv]
    judge = execute(argv, timeout, 4096)
    if judge['outcome'] is not None or judge['exit_code'] != 0:
        raise ValueError('quality judge did not complete successfully')
    for path, expected in pinned:
        if file_hash(path) != expected:
            raise ValueError('quality judge executable or dependency changed')
    if file_hash(case_file) != case_sha:
        raise ValueError('case file changed during quality judgment')
    payload = loads(judge['evidence']['output'])
    if (not isinstance(payload, dict) or set(payload) - {'case_sha256', 'metrics', 'qualitative', 'evidence'} or
            payload.get('case_sha256') != case_sha):
        raise ValueError('quality judge did not attest the case input')
    metrics = payload.get('metrics')
    if not isinstance(metrics, dict) or not metrics or native_metric in metrics:
        raise ValueError('quality judge must supply distinct numeric metrics')
    for name, value in metrics.items():
        if (not isinstance(name, str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_.-]{0,63}', name) or
                type(value) not in (int, float) or not math.isfinite(value)):
            raise ValueError('quality metrics must be finite numbers')
    qualitative = payload.get('qualitative', {})
    if not isinstance(qualitative, dict):
        raise ValueError('qualitative judgments must be an object')
    if qualitative and payload.get('evidence') in (None, '', [], {}):
        raise ValueError('qualitative judgment must include observed evidence')
    for name, judgment in qualitative.items():
        if (not isinstance(name, str) or not isinstance(judgment, dict) or
                type(judgment.get('rating')) not in (int, float) or
                not math.isfinite(judgment['rating']) or
                not isinstance(judgment.get('rationale'), str) or not judgment['rationale'].strip() or
                judgment.get('evidence') != ['self']):
            raise ValueError('qualitative judgment requires rating, rationale and self evidence')
        if name in metrics and judgment['rating'] != metrics[name]:
            raise ValueError('qualitative rating differs from its metric')
    result['metrics'].update(metrics)
    if qualitative:
        result['qualitative'] = qualitative
    result['evidence']['quality'] = payload


# Each native stage owns a process group. The runner signals this wrapper on
# timeout; the wrapper then terminates every active stage group. A supervisor
# handshake prevents a stage from starting before its PID is registered.
_ACTIVE_GROUPS = set()


def _kill_group(pid):
    try:
        os.killpg(pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


def _handle_termination(signum, frame):
    for pid in tuple(_ACTIVE_GROUPS):
        _kill_group(pid)
    raise SystemExit(128 + signum)


def _can_observe_unreaped():
    return os.name == 'posix' and all(hasattr(os, name) for name in ('waitid', 'P_PID', 'WEXITED', 'WNOHANG', 'WNOWAIT'))


def _exited_without_reaping(process):
    if _can_observe_unreaped():
        return os.waitid(os.P_PID, process.pid, os.WEXITED | os.WNOHANG | os.WNOWAIT) is not None
    return process.poll() is not None


def _stop_stage(process):
    if os.name == 'posix':
        _kill_group(process.pid)
    elif process.poll() is None:
        process.kill()
    # Remove registration before reaping, while the leader PID is still held.
    _ACTIVE_GROUPS.discard(process.pid)
    process.wait()


def _supervise_stage(argv):
    """Wait for parent registration before replacing this group leader."""
    if len(argv) < 2:
        return 125
    try:
        fd = int(argv[0])
        token = os.read(fd, 1)
        os.close(fd)
        if token != b'1':
            return 125
        os.execvpe(argv[1], argv[1:], os.environ)
    except (OSError, ValueError) as error:
        print(f'stage launch failed: {error}', file=sys.stderr)
        return 127


def execute(argv, timeout, limit):
    start = time.monotonic()
    # Python delivers signal handlers only in the main thread. The CLI uses
    # one main-thread wrapper; library callers in other threads should supply
    # their own external supervisor for abrupt wrapper termination.
    install_handler = os.name == 'posix' and threading.current_thread() is threading.main_thread()
    previous = signal.getsignal(signal.SIGTERM) if install_handler else None
    if install_handler:
        signal.signal(signal.SIGTERM, _handle_termination)
    read_fd = write_fd = None
    process = None
    try:
        if shutil.which(argv[0]) is None:
            raise FileNotFoundError(f'executable not found: {argv[0]}')
        if os.name == 'posix':
            read_fd, write_fd = os.pipe()
            command = [sys.executable, str(Path(__file__).resolve()), '--stage-exec', str(read_fd), *argv]
            process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                       stderr=subprocess.STDOUT, start_new_session=True,
                                       pass_fds=(read_fd,))
            os.close(read_fd)
            read_fd = None
            _ACTIVE_GROUPS.add(process.pid)
            os.write(write_fd, b'1')
            os.close(write_fd)
            write_fd = None
        else:
            process = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                       stderr=subprocess.STDOUT)
    except OSError as error:
        if process is not None:
            _stop_stage(process)
            _ACTIVE_GROUPS.discard(process.pid)
        if read_fd is not None:
            os.close(read_fd)
        if write_fd is not None:
            os.close(write_fd)
        if install_handler:
            signal.signal(signal.SIGTERM, previous)
        return {'outcome': 'infrastructure_error', 'error': str(error),
                'evidence': {'output': '', 'bytes_seen': 0}}
    except BaseException:
        # If Popen was interrupted before returning, the supervisor receives
        # EOF on this pipe and exits without executing the target.
        if read_fd is not None:
            os.close(read_fd)
        if write_fd is not None:
            os.close(write_fd)
        if process is not None:
            _stop_stage(process)
            _ACTIVE_GROUPS.discard(process.pid)
        if install_handler:
            signal.signal(signal.SIGTERM, previous)
        raise
    output = bytearray()
    seen = 0
    selector = selectors.DefaultSelector()
    try:
        os.set_blocking(process.stdout.fileno(), False)
        selector.register(process.stdout, selectors.EVENT_READ)
        outcome = None
        while selector.get_map() or not _exited_without_reaping(process):
            remaining = timeout - (time.monotonic() - start)
            if remaining <= 0:
                outcome = 'timeout'
                break
            for key, _ in selector.select(min(remaining, 0.1)):
                try:
                    chunk = os.read(key.fileobj.fileno(), 65536)
                except BlockingIOError:
                    continue
                if not chunk:
                    selector.unregister(key.fileobj)
                    continue
                seen += len(chunk)
                output.extend(chunk[:max(0, limit - len(output))])
                if seen > limit:
                    outcome = 'incomplete_output'
                    break
            if outcome:
                break
        if outcome or _can_observe_unreaped():
            _stop_stage(process)
        else:
            process.wait()
        return {'outcome': outcome, 'exit_code': process.returncode,
                'duration_seconds': time.monotonic() - start,
                'evidence': {'output': output.decode('utf-8', 'replace'), 'bytes_seen': seen}}
    finally:
        selector.close()
        if process.returncode is None:
            _stop_stage(process)
        _ACTIVE_GROUPS.discard(process.pid)
        process.stdout.close()
        if install_handler:
            signal.signal(signal.SIGTERM, previous)


def evaluate(config, case_file, case=None):
    argv, pattern, timeout, limit, failure_codes = validate(config)
    case_file = Path(case_file).resolve(strict=True)
    if not case_file.is_file():
        raise ValueError('case_file must identify a file')
    case_sha = hashlib.sha256(case_file.read_bytes()).hexdigest()
    if case is not None and (not isinstance(case, str) or not case.strip()):
        raise ValueError('case must be nonempty text')
    if '{{case}}' in argv and case is None:
        raise ValueError('native command requires --case')
    argv = [str(case_file) if arg == '{{case_file}}' else case if arg == '{{case}}' else arg for arg in argv]
    result = execute(argv, timeout, limit)
    try:
        actual = hashlib.sha256(case_file.read_bytes()).hexdigest()
    except OSError:
        actual = None
    if actual != case_sha:
        result['outcome'] = 'infrastructure_error'
        result['error'] = 'case file changed during native check'
    result['case_sha256'] = case_sha
    if case is not None:
        result['case'] = case
    if result['outcome'] is not None:
        return result
    matches = list(pattern.finditer(result['evidence']['output']))
    if len(matches) != 1 or not re.fullmatch(r'[0-9]+', matches[0].group('count') or ''):
        result['outcome'] = 'invalid_work'
        result['error'] = 'expected exactly one valid test-count summary'
        return result
    count = int(matches[0].group('count'))
    if count < 1 or count > 1_000_000_000:
        result['outcome'] = 'invalid_work'
        result['error'] = 'test count must be positive and bounded'
        return result
    if result['exit_code'] not in [0, *failure_codes]:
        result['outcome'] = 'infrastructure_error'
        result['error'] = 'command exited with an unrecognized or signaled status'
        return result
    passed = result['exit_code'] == 0
    result.update(outcome='passed' if passed else 'test_failure',
                  gates={config['gate']: passed}, metrics={config['metric']: int(passed)},
                  work_count=count)
    if 'quality' in config:
        apply_quality(result, config['quality'], case_file, case, case_sha, config['metric'])
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True)
    parser.add_argument('--case-file', required=True)
    parser.add_argument('--case')
    args = parser.parse_args()
    try:
        result = evaluate(loads(Path(args.config).read_text(encoding='utf-8')), args.case_file, args.case)
    except (OSError, ValueError, TypeError, KeyError) as error:
        result = {'outcome': 'infrastructure_error', 'error': str(error)}
    print(json.dumps(result, ensure_ascii=False, allow_nan=False, separators=(',', ':')))
    return 0 if result['outcome'] in ('passed', 'test_failure') else 2


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--stage-exec':
        raise SystemExit(_supervise_stage(sys.argv[2:]))
    raise SystemExit(main())

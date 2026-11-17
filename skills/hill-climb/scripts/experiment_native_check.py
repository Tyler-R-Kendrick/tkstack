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
import signal
import subprocess
import sys
import time

from json_contract import loads

MAX_OUTPUT = 8192  # JSON-escaped output stays within the controller's capture limit.
MAX_TIMEOUT = 3600


def validate(config):
    if not isinstance(config, dict):
        raise ValueError('config must be an object')
    allowed = {'argv', 'work_regex', 'gate', 'metric', 'timeout_seconds', 'max_output_bytes', 'failure_exit_codes'}
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
    return argv, pattern, timeout, limit, codes


def stop(process):
    if os.name == 'posix':
        # Descendants may still hold the output pipe after the leader exits.
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    elif process.poll() is None:
        process.kill()
    if process.poll() is None:
        process.wait()


def execute(argv, timeout, limit):
    start = time.monotonic()
    try:
        process = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT, start_new_session=os.name == 'posix')
    except OSError as error:
        return {'outcome': 'infrastructure_error', 'error': str(error),
                'evidence': {'output': '', 'bytes_seen': 0}}
    output = bytearray()
    seen = 0
    selector = selectors.DefaultSelector()
    try:
        os.set_blocking(process.stdout.fileno(), False)
        selector.register(process.stdout, selectors.EVENT_READ)
        outcome = None
        while selector.get_map() or process.poll() is None:
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
        if outcome:
            stop(process)
        else:
            process.wait()
        result = {'outcome': outcome, 'exit_code': process.returncode,
                  'duration_seconds': time.monotonic() - start,
                  'evidence': {'output': output.decode('utf-8', 'replace'), 'bytes_seen': seen}}
        return result
    finally:
        selector.close()
        if process.poll() is None:
            stop(process)
        process.stdout.close()


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
    raise SystemExit(main())

#!/usr/bin/env python3
"""Validate host judgments and score calibration without selecting a model."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from tkstack_state import ensure_state

LIMIT = 1024 * 1024
FRAMEWORK_VERSION = '0.125.1'
CASE_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}\Z')


def pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError('Duplicate JSON key: ' + key)
        result[key] = value
    return result


def within(root, value, existing):
    path = Path(value)
    path = path if path.is_absolute() else root / path
    resolved = path.resolve(strict=existing)
    if not resolved.is_relative_to(root) or resolved == root:
        raise ValueError('Path must be inside the selected project')
    if existing and not resolved.is_file():
        raise ValueError('Cases must be an existing file')
    if not existing and (path.exists() or path.is_symlink() or not path.parent.is_dir()):
        raise ValueError('Output must be absent and its parent must exist')
    return resolved


def read_cases(path):
    with path.open('rb') as source:
        raw = source.read(LIMIT + 1)
    if len(raw) > LIMIT:
        raise ValueError('Cases exceed 1 MiB')
    data = json.loads(raw, object_pairs_hook=pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError('Nonfinite JSON')))
    if (not isinstance(data, dict) or set(data) != {'version', 'source', 'cases'}
            or type(data['version']) is not int or data['version'] != 1
            or data['source'] != 'invoking-agent'):
        raise ValueError('Cases must identify the invoking-agent source and version 1')
    cases = data['cases']
    if not isinstance(cases, list) or not 1 <= len(cases) <= 256:
        raise ValueError('Supply 1..256 host-judged cases')
    seen = set()
    for case in cases:
        if not isinstance(case, dict) or set(case) != {'id', 'judgment', 'reference', 'elapsed_ms'}:
            raise ValueError('Each case needs id, judgment, reference and elapsed_ms')
        identity = case['id']
        if not isinstance(identity, str) or not CASE_ID.fullmatch(identity) or identity in seen:
            raise ValueError('Case IDs must be unique and bounded')
        seen.add(identity)
        if type(case['judgment']) is not bool or (case['reference'] is not None and type(case['reference']) is not bool):
            raise ValueError('Judgment and labeled reference must be boolean')
        elapsed = case['elapsed_ms']
        if elapsed is not None and (isinstance(elapsed, bool) or not isinstance(elapsed, (int, float)) or not math.isfinite(elapsed) or elapsed < 0):
            raise ValueError('Elapsed milliseconds must be null or a nonnegative finite number')
    return raw, data


def reserve(path):
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0)
    return os.open(path, flags, 0o600)


def write_reserved(fd, value):
    with os.fdopen(os.dup(fd), 'w', encoding='utf-8') as output:
        json.dump(value, output, sort_keys=True, allow_nan=False)
        output.write('\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('validate', 'run'))
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--cases', required=True)
    parser.add_argument('--receipt', required=True)
    parser.add_argument('--output')
    parser.add_argument('--timeout', type=int, default=20)
    args = parser.parse_args()
    reserved, dispatched = [], False
    try:
        if not 1 <= args.timeout <= 25:
            raise ValueError('Timeout must be 1..25 seconds')
        root = args.project.resolve(strict=True)
        if not root.is_dir():
            raise ValueError('Project must be a directory')
        source = within(root, args.cases, True)
        raw, cases = read_cases(source)
        receipt = within(root, args.receipt, False)
        if args.operation == 'run':
            if not args.output:
                raise ValueError('Run needs an absent JSON output path')
            result_path = within(root, args.output, False)
            if result_path.suffix.lower() != '.json' or result_path == receipt:
                raise ValueError('Use distinct JSON result and receipt paths')
            modules = root / '.tkstack/runtime/evalify/node_modules'
            manifest = modules / 'promptfoo/package.json'
            if not manifest.is_file() or json.loads(manifest.read_text()).get('version') != FRAMEWORK_VERSION:
                raise ValueError('Install the packaged Promptfoo lock in .tkstack/runtime/evalify')
            node = shutil.which('node')
            if node is None:
                raise ValueError('Node.js is required for offline framework scoring')
        else:
            if args.output:
                raise ValueError('Validate does not take an output path')
            result_path = None
        receipt_fd = reserve(receipt)
        reserved.append((receipt, receipt_fd))
        if result_path is not None:
            result_fd = reserve(result_path)
            reserved.append((result_path, result_fd))
        started_at = datetime.now(timezone.utc).isoformat()
        start = time.monotonic()
        code, diagnostic, status = 0, '', 'pass'
        result = None
        if args.operation == 'run':
            runtime = ensure_state(root / '.tkstack/runs/evalify')
            script = Path(__file__).resolve().parent / 'calibrate.cjs'
            with tempfile.TemporaryDirectory(prefix='promptfoo-', dir=runtime) as temp, \
                    tempfile.TemporaryFile() as output, tempfile.TemporaryFile() as errors:
                env = {**os.environ, 'PROMPTFOO_CONFIG_DIR': temp,
                       'PROMPTFOO_DISABLE_TELEMETRY': '1', 'PROMPTFOO_DISABLE_UPDATE': '1'}
                own_group = os.name == 'posix' and os.environ.get('TKSTACK_CODIFY_EXECUTION') != '1'
                process = subprocess.Popen([node, str(script)], cwd=root, env=env, stdin=subprocess.PIPE,
                                           stdout=output, stderr=errors, start_new_session=own_group)
                dispatched = True
                try:
                    try:
                        process.communicate(json.dumps(cases, allow_nan=False).encode(), timeout=args.timeout)
                        code = process.returncode
                        status = 'pass' if code == 0 else 'error'
                    except subprocess.TimeoutExpired:
                        try:
                            if own_group:
                                os.killpg(process.pid, signal.SIGKILL)
                            else:
                                process.kill()
                        except ProcessLookupError:
                            pass
                        process.wait()
                        code, status = None, 'timeout'
                finally:
                    if own_group:
                        try:
                            os.killpg(process.pid, signal.SIGKILL)
                        except ProcessLookupError:
                            pass
                output.seek(0)
                errors.seek(0)
                stdout, stderr = output.read(LIMIT + 1), errors.read(4096)
                diagnostic = stderr.decode('utf-8', errors='replace')
                if status == 'pass':
                    try:
                        if len(stdout) > LIMIT:
                            raise ValueError('Framework result exceeds 1 MiB')
                        result = json.loads(stdout, object_pairs_hook=pairs)
                        if not isinstance(result, dict) or set(result) != {'calibration', 'current', 'timing'}:
                            raise ValueError('Invalid offline framework result')
                        write_reserved(result_fd, result)
                    except (ValueError, TypeError) as error:
                        status, diagnostic = 'error', str(error)
        elapsed = round((time.monotonic() - start) * 1000, 3)
        record = {'version': 1, 'operation': args.operation, 'status': status,
                  'started_at': started_at, 'elapsed_ms': elapsed, 'timeout_seconds': args.timeout,
                  'exit_code': code, 'cases_sha256': hashlib.sha256(raw).hexdigest(),
                  'case_count': len(cases['cases']), 'source': 'invoking-agent',
                  'framework': 'promptfoo assertions' if args.operation == 'run' else None,
                  'framework_version': FRAMEWORK_VERSION if args.operation == 'run' else None,
                  'output': str(result_path) if result_path else None, 'receipt': str(receipt),
                  'limits': 'Source and per-case timings are supplied records, not authenticated host provenance.'}
        write_reserved(receipt_fd, record)
        if status != 'pass':
            print(diagnostic[-4096:], file=sys.stderr)
        print(json.dumps(record, sort_keys=True))
        return 0 if status == 'pass' else (124 if status == 'timeout' else 1)
    except (OSError, ValueError, TypeError) as error:
        print('evalify: ' + str(error), file=sys.stderr)
        return 1
    finally:
        for path, fd in reversed(reserved):
            if not dispatched and args.operation == 'run':
                try:
                    current, original = path.lstat(), os.fstat(fd)
                    if (current.st_dev, current.st_ino) == (original.st_dev, original.st_ino):
                        path.unlink()
                except FileNotFoundError:
                    pass
            os.close(fd)


if __name__ == '__main__':
    raise SystemExit(main())

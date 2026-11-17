#!/usr/bin/env python3
"""Invoke an existing Promptfoo installation with a bounded, timed receipt."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from tkstack_state import ensure_state


def in_project(root, value, existing):
    path = Path(value)
    path = path if path.is_absolute() else root / path
    resolved = path.resolve(strict=existing)
    if not resolved.is_relative_to(root) or resolved == root:
        raise ValueError('Path must be inside the selected project')
    if existing and not resolved.is_file():
        raise ValueError('Configuration must be an existing file')
    if not existing and (path.exists() or path.is_symlink() or not path.parent.is_dir()):
        raise ValueError('Output must be absent and its parent must exist')
    return resolved


def write_receipt(path, payload):
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0)
    with os.fdopen(os.open(path, flags, 0o600), 'w', encoding='utf-8') as stream:
        json.dump(payload, stream, sort_keys=True, allow_nan=False)
        stream.write('\n')


def grader_error(row):
    grading = row.get('gradingResult', {})
    if not isinstance(grading, dict) or not isinstance(grading.get('componentResults', []), list):
        raise ValueError('Invalid Promptfoo grading result')
    for part in grading.get('componentResults', []):
        if not isinstance(part, dict) or not isinstance(part.get('metadata', {}), dict):
            raise ValueError('Invalid Promptfoo assertion metadata')
        if part.get('metadata', {}).get('graderError') is True:
            return True
    return False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('validate', 'run'))
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--config', required=True)
    parser.add_argument('--executable', type=Path, required=True)
    parser.add_argument('--receipt', required=True)
    parser.add_argument('--output')
    parser.add_argument('--timeout', type=int, default=20)
    args = parser.parse_args()
    try:
        if not 1 <= args.timeout <= 25:
            raise ValueError('Timeout must be 1..25 seconds; use the native CLI for longer runs')
        root = args.project.resolve(strict=True)
        if not root.is_dir():
            raise ValueError('Project must be a directory')
        config = in_project(root, args.config, True)
        receipt = in_project(root, args.receipt, False)
        executable = args.executable.resolve(strict=True)
        if not executable.is_file() or not os.access(executable, os.X_OK):
            raise ValueError('Use an existing executable Promptfoo CLI')
        with executable.open('rb') as source:
            executable_sha256 = hashlib.file_digest(source, 'sha256').hexdigest()
        if args.operation == 'run':
            if not args.output:
                raise ValueError('Run needs an explicit absent JSON output path')
            output = in_project(root, args.output, False)
            if output.suffix.lower() != '.json' or output == receipt:
                raise ValueError('Use distinct JSON output and receipt paths')
            command = [str(executable), 'eval', '-c', str(config), '-o', str(output),
                       '--no-cache', '--no-share', '--no-progress-bar', '--no-table']
        else:
            if args.output:
                raise ValueError('Validate does not take an output path')
            output = None
            command = [str(executable), 'validate', 'config', '-c', str(config)]
        digest = hashlib.sha256(config.read_bytes()).hexdigest()
        runtime = ensure_state(root / '.tkstack/runs/evalify')
        started_at = datetime.now(timezone.utc).isoformat()
        start = time.monotonic()
        with tempfile.TemporaryDirectory(prefix='promptfoo-', dir=runtime) as temp, \
             tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
            env = {**os.environ, 'PROMPTFOO_CONFIG_DIR': temp,
                   'PROMPTFOO_DISABLE_TELEMETRY': '1', 'PROMPTFOO_DISABLE_UPDATE': '1'}
            own_group = os.name == 'posix' and os.environ.get('TKSTACK_CODIFY_EXECUTION') != '1'
            process = subprocess.Popen(command, cwd=root, env=env, stdout=stdout, stderr=stderr,
                                       start_new_session=own_group)
            try:
                try:
                    code = process.wait(timeout=args.timeout)
                    status = 'pass' if code == 0 else 'fail'
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
                    if process.poll() is None:
                        process.wait()
            elapsed = round((time.monotonic() - start) * 1000, 3)
            stdout.seek(0); stderr.seek(0)
            diagnostic = (stdout.read(4096) + stderr.read(4096)).decode('utf-8', errors='replace')
        count = passed = failed = grader_errors = None
        if status != 'timeout' and output is not None and (code == 0 or output.is_file()):
            try:
                data = json.loads(output.read_text())
                rows = data['results']['results']
                if not isinstance(rows, list) or not rows or any(not isinstance(row, dict) or type(row.get('success')) is not bool for row in rows):
                    raise ValueError('Promptfoo returned no complete result rows')
                count = len(rows)
                passed = sum(row['success'] for row in rows)
                failed = count - passed
                grader_errors = sum(grader_error(row) for row in rows)
                if failed:
                    status = 'fail'
            except (OSError, ValueError, TypeError, KeyError) as error:
                status, diagnostic = 'error', str(error)
        result = {'version': 1, 'operation': args.operation, 'status': status,
                  'started_at': started_at, 'elapsed_ms': elapsed, 'timeout_seconds': args.timeout,
                  'exit_code': code, 'config_sha256': digest, 'executable': str(executable),
                  'executable_sha256': executable_sha256,
                  'config': str(config), 'output': str(output) if output else None,
                  'result_count': count, 'passed': passed, 'failed': failed, 'grader_errors': grader_errors,
                  'receipt': str(receipt)}
        write_receipt(receipt, result)
        if status != 'pass':
            print(diagnostic[-4096:], file=sys.stderr)
        print(json.dumps(result, sort_keys=True))
        return 0 if status == 'pass' else (124 if status == 'timeout' else 1)
    except (OSError, ValueError, TypeError) as error:
        print('evalify: ' + str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())

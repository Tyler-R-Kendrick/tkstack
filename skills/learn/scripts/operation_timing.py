"""Record bounded compiled operations without retaining prompts or payloads."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import stat
import sys
import time
from tkstack_state import ensure_state

def record(state, kind, name, timeout, elapsed, status, code, artifact):
    directory = ensure_state(Path(state) / 'runs' / 'timing')
    path = directory / 'operations.jsonl'
    row = {'version': 1, 'time': datetime.now(timezone.utc).isoformat(),
           'kind': kind, 'name': name,
           'timeout_seconds': timeout, 'elapsed_ms': round(elapsed * 1000, 3),
           'status': status, 'exit_code': code, 'artifact_sha256': artifact,
           'environment': {'platform': sys.platform, 'architecture': platform.machine(),
                           'python': platform.python_version()}}
    data = (json.dumps(row, sort_keys=True, allow_nan=False) + '\n').encode()
    flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND | getattr(os, 'O_NOFOLLOW', 0)
    fd = os.open(path, flags, 0o600)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise ValueError('Timing trace is not a regular file')
        if os.write(fd, data) != len(data):
            raise OSError('Incomplete timing trace write')
    finally:
        os.close(fd)


def invoke(runner, lock, payload, project, timeout, dependencies, config, environment, state, kind, name):
    start = time.monotonic()
    status, exit_code = 'error', None
    try:
        result = runner(lock, payload, project, timeout, dependencies, config, environment=environment)
        exit_code = result[0]
        status = 'pass' if exit_code == 0 else 'fail'
        return result
    except ValueError as error:
        if str(error) == 'Workflow deadline exceeded or invocation interrupted':
            status = 'deadline_or_interrupt'
        raise
    finally:
        try:
            record(state, kind, name, timeout, time.monotonic() - start,
                   status, exit_code, lock.get('artifact_sha256'))
        except (OSError, ValueError) as error:
            print('tkstack: timing trace unavailable: ' + str(error), file=sys.stderr)

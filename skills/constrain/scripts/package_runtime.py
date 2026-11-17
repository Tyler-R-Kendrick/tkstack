"""Shared execution for skill contract models, retained proof, and native tools."""

import hashlib
import json
import os
import signal
from pathlib import Path
import subprocess
import sys
import tempfile

from tkstack_state import state_root, session_tempdir
from json_contract import loads


LIMIT = 1024 * 1024


class NativeFailure(Exception):
    def __init__(self, code, stdout, stderr):
        self.code, self.stdout, self.stderr = code, stdout, stderr


def read_json(path):
    with Path(path).open('rb') as stream:
        data = stream.read(LIMIT + 1)
    if len(data) > LIMIT:
        raise ValueError('Contract/report exceeds 1 MiB')
    return loads(data)


def validator(schema, value):
    try:
        from jsonschema import Draft202012Validator
    except ImportError as error:
        raise ValueError('Use the installed private command-schema runtime') from error
    Draft202012Validator.check_schema(schema)
    errors = sorted(Draft202012Validator(schema).iter_errors(value), key=lambda error: str(error.path))
    if errors:
        raise ValueError('Contract violation: ' + errors[0].message)


def workspace_path(value, workspace):
    if not isinstance(value, str) or not value or value == '-':
        raise ValueError('Supply an explicit file/path, not stdin')
    return (workspace / Path(value).expanduser()).absolute()


def verify(model, report, workspace):
    fields = {'skill', 'objective', 'facts', 'criteria', 'evidence', 'review'}
    if not isinstance(report, dict) or set(report) != fields or report['skill'] != model['name']:
        raise ValueError('Report must match the skill and exact report fields')
    if not isinstance(report['objective'], str) or not report['objective'].strip():
        raise ValueError('A real workload objective is required')
    validator(model['facts_schema'], report['facts'])
    if (report['facts'].get('provider_requested') is not None and
            report['facts'].get('provider_requested') != report['facts'].get('provider_used')):
        raise ValueError('An explicit provider selection must be preserved')
    artifacts = {}
    if not isinstance(report['evidence'], list) or not report['evidence']:
        raise ValueError('Retained evidence is required')
    for item in report['evidence']:
        if not isinstance(item, dict) or set(item) != {'id', 'path', 'sha256', 'kind'}:
            raise ValueError('Evidence needs id/path/sha256/kind')
        if any(not isinstance(item[key], str) or not item[key].strip() for key in item):
            raise ValueError('Evidence fields must be nonempty strings')
        if item['id'] in artifacts:
            raise ValueError('Duplicate evidence ID')
        path = workspace_path(item['path'], workspace).resolve(strict=True)
        if not path.is_file():
            raise ValueError('Evidence must be a retained regular file')
        with path.open('rb') as stream:
            actual = hashlib.file_digest(stream, 'sha256').hexdigest()
        if actual != item['sha256']:
            raise ValueError('Evidence bytes changed: ' + item['id'])
        artifacts[item['id']] = item
    criteria = {}
    if not isinstance(report['criteria'], list):
        raise ValueError('Criteria must be an array')
    for item in report['criteria']:
        if not isinstance(item, dict) or set(item) != {'id', 'status', 'evidence', 'reason'}:
            raise ValueError('Criterion needs id/status/evidence/reason')
        if not isinstance(item['id'], str) or item['id'] in criteria:
            raise ValueError('Criterion IDs must be unique strings')
        if item['status'] != 'pass' or not isinstance(item['reason'], str) or not item['reason'].strip():
            raise ValueError('Missing, failed, or unreviewed criteria block verification')
        if (not isinstance(item['evidence'], list) or not item['evidence']
                or any(not isinstance(key, str) or key not in artifacts for key in item['evidence'])):
            raise ValueError('Criterion must refer to retained evidence')
        criteria[item['id']] = item
    expected = {item['id'] for item in model['criteria']}
    if set(criteria) != expected:
        raise ValueError('Account for every modeled criterion, without additions or omissions')
    review = report['review']
    if (not isinstance(review, dict) or set(review) != {'reviewer', 'semantic_inspection', 'limitations'}
            or any(not isinstance(review[key], str) or not review[key].strip() for key in review)
            or review['semantic_inspection'] != 'performed'):
        raise ValueError('Actual semantic inspection and its limits must be recorded')
    return {'skill': model['name'], 'structural_gate': 'pass', 'criteria': len(criteria),
            'evidence': len(artifacts), 'semantic_review': 'recorded-not-authenticated',
            'limits': 'Checks validate recorded facts, coverage and actual file bytes; they do not authenticate authority, remote state, or semantic quality.'}


def native(root, model, operation, payload, workspace):
    binding = model.get('native', {}).get(operation)
    if binding is None:
        delegate = model.get('delegate')
        if delegate is None:
            raise ValueError('Unknown skill operation')
        arguments = ['--input', '-']
        source = json.dumps(payload, allow_nan=False)
        entrypoint = delegate
    else:
        entrypoint = binding['entrypoint']
        before, after = [], []
        source = None
        expected = {'operation', *binding['parameters']}
        if set(payload) != expected:
            raise ValueError('Native tool arguments do not match its signature')
        properties = {'operation': {'type': 'string', 'const': operation},
                      **{key: parameter['schema'] for key, parameter in binding['parameters'].items()}}
        validator({'type': 'object', 'properties': properties, 'required': list(properties), 'additionalProperties': False}, payload)
        for name, parameter in binding['parameters'].items():
            value = payload[name]
            if value is None or value is False:
                continue
            values = value if parameter.get('repeat') else [value]
            for item in values:
                if parameter.get('path'):
                    item = str(workspace_path(item, workspace))
                if parameter['schema'].get('type') == 'integer':
                    item = int(item)
                arguments = before if parameter.get('global') else after
                arguments.extend(parameter.get('flags', []))
                if item is not True:
                    arguments.append(str(item))
        arguments = before + list(binding.get('prefix', [])) + after + list(binding.get('suffix', []))
    entrypoint = root / entrypoint
    if (not entrypoint.resolve().is_relative_to(root.resolve()) or entrypoint.is_symlink()
            or not entrypoint.is_file() or entrypoint.suffix != '.py'):
        raise ValueError('Native entrypoint must be a contained Python source file')
    with session_tempdir(prefix='native-', project=workspace) as scratch, \
            tempfile.TemporaryFile(dir=scratch) as output, tempfile.TemporaryFile(dir=scratch) as errors:
        shared_group = os.environ.get('TKSTACK_CODIFY_EXECUTION') == '1'
        process = subprocess.Popen([sys.executable, '-B', str(entrypoint), *arguments], cwd=workspace,
            stdin=subprocess.PIPE, stdout=output, stderr=errors, start_new_session=not shared_group,
            env={**os.environ, 'TKSTACK_WORKSPACE_DIR': str(workspace / '.tkstack'), 'TKSTACK_CODIFY_EXECUTION': '1'})
        try:
            try:
                process.communicate(source.encode() if source is not None else None, timeout=60)
            except (subprocess.TimeoutExpired, KeyboardInterrupt):
                if shared_group:
                    process.kill()
                else:
                    os.killpg(process.pid, signal.SIGKILL)
                process.communicate()
                raise ValueError('Native helper deadline exceeded or invocation interrupted')
        finally:
            if not shared_group:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
        output.seek(0)
        errors.seek(0)
        stdout, stderr = output.read(LIMIT + 1), errors.read(LIMIT + 1)
    if len(stdout) > LIMIT or len(stderr) > LIMIT:
        raise ValueError('Native output exceeds 1 MiB')
    stdout, stderr = stdout.decode(), stderr.decode()
    if process.returncode:
        raise NativeFailure(process.returncode, stdout, stderr)
    try:
        return loads(stdout)
    except json.JSONDecodeError:
        return {'text': stdout.strip()}


def execute(payload, root):
    root = Path(root).resolve(strict=True)
    model = read_json(root / 'scripts/contract.json')
    if not isinstance(payload, dict) or not isinstance(payload.get('operation'), str):
        raise ValueError('A typed skill operation is required')
    operation = payload['operation']
    if operation == 'model':
        if set(payload) != {'operation'}:
            raise ValueError('Model takes no extra parameters')
        return {key: value for key, value in model.items() if key not in ('native', 'delegate')}
    workspace = state_root().parent
    if operation == 'verify':
        if set(payload) != {'operation', 'report'}:
            raise ValueError('Verify requires exactly one report path')
        path = workspace_path(payload['report'], workspace)
        return verify(model, read_json(path), workspace)
    return native(root, model, operation, payload, workspace)

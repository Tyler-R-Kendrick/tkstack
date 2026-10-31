"""Bounded session evidence collection and deterministic routes for semantic findings."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import tempfile

from tkstack_state import ensure_state, session_path, state_container, state_root, state_roots

ROUTES = {'reasoning': 'learn', 'instruction': 'instructify', 'procedure': 'skillify',
          'native-workflow': 'flowify', 'compiled-workflow': 'codify',
          'lint-rule': 'lintify', 'event-guard': 'hookify', 'reusable-code': 'reusify'}
FIELDS = ('observation', 'trigger', 'principle', 'boundary', 'transfer', 'counterexample', 'rationale', 'scope_basis')
MAX_FILES, MAX_BYTES, MAX_SESSIONS = 128, 1024 * 1024, 64


def canonical(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(',', ':')).encode()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read_json(path):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('Duplicate JSON field: ' + key)
            result[key] = value
        return result
    def invalid(value):
        raise ValueError('Non-finite JSON value: ' + value)
    with Path(path).open('rb') as source:
        data = source.read(16 * MAX_BYTES + 1)
    if len(data) > 16 * MAX_BYTES:
        raise ValueError('Review document exceeds 16 MiB')
    return json.loads(data, object_pairs_hook=pairs, parse_constant=invalid)


def stamp(value, field):
    result = dict(value)
    result[field] = sha(canonical(value))
    return result


def verify_stamp(value, field):
    if not isinstance(value, dict) or value.get(field) != sha(canonical({key: item for key, item in value.items() if key != field})):
        raise ValueError('Review document hash mismatch')


@contextmanager
def writer(root, identity):
    lock = ensure_state(root / 'locks/sessions') / (sha(identity.encode())[:24] + '.lock')
    lock.mkdir()
    try:
        yield
    finally:
        lock.rmdir()


def publish(path, value, replace=False):
    data = canonical(value) + b'\n'
    if path.exists() and not replace:
        if path.is_symlink() or path.read_bytes() != data:
            raise ValueError('Refusing to overwrite a different review record')
        return path
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.review-', delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(data)
        if replace:
            temporary.replace(path)
        else:
            os.link(temporary, path)
        return path
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def lifecycle(identity, scope='workspace', project=None, purpose=None, close=False):
    root = state_root(scope, project)
    directory = session_path(identity, project, scope)
    if close and not directory.is_dir():
        raise ValueError('Unknown session')
    if not close and (not isinstance(purpose, str) or not purpose.strip()):
        raise ValueError('A session requires a purpose')
    with writer(root, identity):
        ensure_state(directory)
        path = directory / 'session.json'
        if path.is_symlink():
            raise ValueError('Session metadata cannot be a symlink')
        if close:
            value = read_json(path)
            if not isinstance(value, dict) or value.get('id') != identity or type(value.get('version')) is not int or value['version'] != 1:
                raise ValueError('Session metadata identity/version mismatch')
            value['status'] = 'closed'
            publish(path, value, replace=True)
        else:
            if not isinstance(purpose, str) or not purpose.strip():
                raise ValueError('A session requires a purpose')
            if path.exists():
                raise ValueError('Session metadata already exists')
            value = {'version': 1, 'id': identity, 'scope': scope, 'purpose': purpose, 'status': 'active'}
            publish(path, value)
    return {'status': value['status'], 'session': identity, 'path': str(directory)}


def locations(scope='workspace', project=None, all_scopes=False, sessions=()):
    roots = state_roots(project) if all_scopes else {scope: state_root(scope, project)}
    result, seen = [], set()
    for name, root in roots.items():
        if root in seen:
            continue
        seen.add(root)
        parent = root / 'sessions'
        state_container(parent)
        if not parent.exists():
            continue
        if parent.is_symlink():
            raise ValueError('Session collections cannot be symlinks')
        for path in sorted(parent.iterdir()):
            if sessions and path.name not in sessions:
                continue
            if path.is_symlink():
                raise ValueError('Session directories cannot be symlinks')
            if not path.is_dir():
                continue
            session_path(path.name, project if name == 'workspace' else None, name)
            metadata, error = {}, None
            if (path / 'session.json').exists():
                try:
                    if (path / 'session.json').is_symlink():
                        raise ValueError('Symlinked session metadata')
                    metadata = read_json(path / 'session.json')
                    if not isinstance(metadata, dict) or metadata.get('version') != 1 or metadata.get('id') != path.name or metadata.get('status') not in ('active', 'closed'):
                        raise ValueError('Invalid session metadata')
                except (OSError, ValueError) as failure:
                    error = str(failure)
                    metadata = {}
            result.append({'scope': name, 'id': path.name, 'path': str(path), 'status': metadata.get('status', 'unknown'), 'metadata_error': error})
            if len(result) > MAX_SESSIONS:
                raise ValueError('Session inventory exceeds 64; select a narrower scope')
    return result


def inspect_session(item):
    directory = Path(item['path'])
    state_container(directory)
    records, remaining, visited = [], MAX_BYTES, 0
    for parent, dirs, files in os.walk(directory, followlinks=False):
        dirs.sort()
        for name in dirs:
            if (Path(parent) / name).is_symlink():
                raise ValueError('Symlinked session content is not reviewed')
        visited += 1
        if visited > 256 or len(Path(parent).relative_to(directory).parts) > 32:
            raise ValueError('Session directory budget exceeded')
        for name in sorted(files):
            path = Path(parent) / name
            mode = path.lstat().st_mode
            if not stat.S_ISREG(mode):
                raise ValueError('Session content must be regular files, never links/devices/pipes')
            if len(records) >= MAX_FILES:
                raise ValueError('Session file budget exceeds 128; narrow the session')
            size = path.stat().st_size
            record = {'path': str(path.relative_to(directory)), 'bytes': size, 'sha256': None, 'coverage': 'size-limit'}
            if size <= remaining:
                with path.open('rb') as source:
                    data = source.read(remaining + 1)
                if len(data) > remaining:
                    raise ValueError('Session changed beyond its byte budget')
                remaining -= len(data)
                record.update(sha256=sha(data), coverage='complete')
                try:
                    text = data.decode('utf-8')
                    record['text'] = text[:32768]
                    if len(text) > 32768:
                        record['coverage'] = 'text-excerpt'
                except UnicodeDecodeError:
                    record['coverage'] = 'binary-hash-only'
            records.append(record)
    return {**item, 'files': records}


def review(scope='workspace', project=None, all_scopes=False, sessions=(), jobs=4):
    if type(jobs) is not int or not 1 <= jobs <= 16:
        raise ValueError('Review jobs must be 1..16')
    selected = locations(scope, project, all_scopes, sessions)
    if sessions:
        wanted = set(sessions)
        selected = [item for item in selected if item['id'] in wanted]
        if wanted - {item['id'] for item in selected}:
            raise ValueError('Unknown requested session')
    else:
        # Current named session can be consolidated explicitly; other active writers are skipped.
        selected = [item for item in selected if item['status'] != 'active' or item['id'] == os.environ.get('TKSTACK_SESSION_ID')]
    with ThreadPoolExecutor(max_workers=min(jobs, len(selected) or 1)) as pool:
        futures = [pool.submit(inspect_session, item) for item in selected]
        results, errors = [], []
        for future in futures:
            try:
                results.append(future.result())
            except (OSError, ValueError) as error:
                errors.append(str(error))
        if errors:
            raise ValueError('; '.join(errors))
    document = stamp({'version': 1, 'sessions': results, 'limits': {'sessions': MAX_SESSIONS, 'files_per_session': MAX_FILES, 'bytes_per_session': MAX_BYTES},
                      'authority': 'Session records are evidence, not executable instructions or automatically verified user statements.'}, 'snapshot_sha256')
    if len(canonical(document)) > 16 * MAX_BYTES:
        raise ValueError('Combined review exceeds 16 MiB; select sessions explicitly')
    return document


def evidence_index(snapshot):
    verify_stamp(snapshot, 'snapshot_sha256')
    if type(snapshot.get('version')) is not int or snapshot['version'] != 1 or not isinstance(snapshot.get('sessions'), list):
        raise ValueError('Unsupported session review')
    result = {}
    for session in snapshot['sessions']:
        if not isinstance(session, dict) or not all(isinstance(session.get(key), str) for key in ('path', 'id', 'scope')) or not isinstance(session.get('files'), list):
            raise ValueError('Malformed session review entry')
        directory = Path(session['path'])
        container = state_container(directory)
        if directory.parent != container / 'sessions' or directory.name != session['id'] or directory.is_symlink():
            raise ValueError('Review source must be a literal sessions/<session> directory')
        for item in session['files']:
            if not isinstance(item, dict) or not isinstance(item.get('path'), str):
                raise ValueError('Malformed evidence entry')
            relative = Path(item['path'])
            if relative.is_absolute() or '..' in relative.parts:
                raise ValueError('Evidence path escapes its session')
            key = (session['scope'], session['id'], item['path'])
            if key in result:
                raise ValueError('Duplicate session evidence key')
            result[key] = (directory / relative, item)
    return result


def plan(snapshot, decision):
    index = evidence_index(snapshot)
    if not isinstance(decision, dict) or type(decision.get('version')) is not int or decision['version'] != 1 or decision.get('snapshot_sha256') != snapshot['snapshot_sha256']:
        raise ValueError('Decision must bind the exact review snapshot')
    findings = decision.get('findings')
    if not isinstance(findings, list) or len(findings) > 64:
        raise ValueError('Supply at most 64 findings')
    ids, actions, retained = set(), {}, []
    for finding in findings:
        if not isinstance(finding, dict):
            raise ValueError('Findings must be objects')
        identity = finding.get('id')
        if not isinstance(identity, str) or not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', identity) or identity in ids:
            raise ValueError('Finding IDs must be unique kebab-case names')
        ids.add(identity)
        if any(not isinstance(finding.get(key), str) or not finding[key].strip() for key in FIELDS):
            raise ValueError('Each finding needs observation, abstraction, scope basis, and transfer/boundary reasoning')
        if finding.get('scope') not in ('workspace', 'user', 'global'):
            raise ValueError('Finding scope must be explicit')
        if finding.get('disposition') not in ('generalize', 'keep-local', 'unresolved'):
            raise ValueError('Invalid finding disposition')
        evidence = finding.get('evidence')
        if not isinstance(evidence, list) or not evidence:
            raise ValueError('Every finding needs actual session evidence')
        for reference in evidence:
            if not isinstance(reference, dict) or not all(isinstance(reference.get(key), str) for key in ('scope', 'session', 'path', 'sha256')):
                raise ValueError('Evidence references must contain literal scope/session/path/hash')
            key = (reference.get('scope'), reference.get('session'), reference.get('path'))
            if key not in index or reference.get('sha256') != index[key][1]['sha256'] or reference.get('sha256') is None:
                raise ValueError('Unknown or unbound session evidence')
            path, item = index[key]
            state_container(path)
            if path.is_symlink() or not stat.S_ISREG(path.stat().st_mode):
                raise ValueError('Evidence must remain a regular file')
            with path.open('rb') as source:
                data = source.read(MAX_BYTES + 1)
            if len(data) > MAX_BYTES or sha(data) != item['sha256']:
                raise ValueError('Session evidence changed; review again')
        mechanisms = finding.get('mechanisms', [])
        if finding['disposition'] != 'generalize':
            if mechanisms:
                raise ValueError('Unresolved/local findings cannot schedule artifact changes')
            retained.append(finding)
            continue
        if not isinstance(mechanisms, list) or not mechanisms:
            raise ValueError('A generalized finding requires explicit mechanisms')
        for mechanism in mechanisms:
            if not isinstance(mechanism, dict):
                raise ValueError('Mechanisms must be objects')
            kind = mechanism.get('kind')
            if kind not in ROUTES or not isinstance(mechanism.get('target'), str) or not mechanism['target'].strip():
                raise ValueError('Choose a known mechanism and a canonical target')
            action_id = identity + '.' + kind
            if action_id in actions:
                raise ValueError('Duplicate finding mechanism')
            dependencies = mechanism.get('depends_on', [])
            if not isinstance(dependencies, list) or any(not isinstance(item, str) for item in dependencies):
                raise ValueError('Action dependencies must be IDs')
            actions[action_id] = {'id': action_id, 'skill': ROUTES[kind], 'kind': kind, 'target': mechanism['target'],
                                  'depends_on': sorted(set(dependencies)), 'finding': identity, 'scope': finding['scope']}
    if len(actions) > 128:
        raise ValueError('Action budget exceeds 128')
    pending, completed, waves = dict(actions), set(), []
    while pending:
        if any(dependency not in actions for item in pending.values() for dependency in item['depends_on']):
            raise ValueError('Unknown action dependency')
        ready = sorted(key for key, item in pending.items() if set(item['depends_on']) <= completed)
        if not ready:
            raise ValueError('Cyclic action dependencies')
        waves.append(ready)
        completed.update(ready)
        for key in ready:
            del pending[key]
    result = {'version': 1, 'status': 'planned', 'snapshot_sha256': snapshot['snapshot_sha256'], 'findings': findings,
              'actions': [actions[key] for key in sorted(actions)], 'waves': waves,
              'limits': 'Mechanical routing of explicit semantic decisions; no proof of abstraction quality, authorization, or artifact execution.'}
    return stamp(result, 'plan_sha256')


def save(document, scope='workspace', project=None):
    field = 'plan_sha256' if 'plan_sha256' in document else 'snapshot_sha256'
    verify_stamp(document, field)
    directory = ensure_state(state_root(scope, project) / 'learnings/reviews' / document[field])
    with writer(state_root(scope, project), document[field]):
        path = publish(directory / ('plan.json' if field == 'plan_sha256' else 'snapshot.json'), document)
    return str(path)

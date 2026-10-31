"""Normalize an existing owned package without replacing its native helpers."""

import hashlib
import fcntl
import json
from pathlib import Path
import re
import tempfile
from tkstack_state import ensure_state, state_path, project_root


RUNNER = '''#!/usr/bin/env python3
"""Skillify-generated contract tool; native skill procedures retain their scope."""
import argparse
import json
from pathlib import Path
import sys
sys.dont_write_bytecode = True
from package_runtime import execute, NativeFailure, read_json, loads

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True)
    args = parser.parse_args()
    try:
        if args.input == '-':
            raw = sys.stdin.read(1024 * 1024 + 1)
            if len(raw) > 1024 * 1024:
                raise ValueError('Input exceeds 1 MiB')
            payload = loads(raw)
        else:
            payload = read_json(args.input)
        print(json.dumps(execute(payload, Path(__file__).resolve().parent.parent), sort_keys=True, allow_nan=False))
        return 0
    except NativeFailure as error:
        sys.stdout.write(error.stdout)
        sys.stderr.write(error.stderr)
        return error.code if 0 < error.code <= 125 else 1
    except (OSError, ValueError, TypeError, KeyError) as error:
        print(str(error), file=sys.stderr)
        return 1

if __name__ == '__main__':
    raise SystemExit(main())
'''


def object_schema(properties):
    return {'type': 'object', 'properties': properties, 'required': list(properties), 'additionalProperties': False}


def normalize(directory, profile, engine, dry_run=False):
    directory = Path(directory).resolve(strict=True)
    profile_bytes = engine.read_bytes(Path(profile))
    if len(profile_bytes) > 1024 * 1024:
        raise ValueError('Contract profile exceeds 1 MiB')
    model = engine.parse_json(profile_bytes)
    identity = engine.command_schema.package_identity(directory)
    if model.get('name') != identity['name'] or model.get('version') != 1:
        raise ValueError('A version 1 contract must match the owned skill name')
    if set(model) - {'version', 'name', 'purpose', 'criteria', 'facts_schema', 'native', 'subskills', 'delegate', 'limits'}:
        raise ValueError('Unknown contract fields')
    if not (directory / 'LICENSE').is_file() or not model.get('criteria') or not model.get('purpose') or not model.get('limits'):
        raise ValueError('Preserve the license and supply actual criteria/purpose/limits')
    _, validator = engine.command_schema.schema_libraries()
    validator.check_schema(model['facts_schema'])
    identifiers = [item['id'] for item in model['criteria']]
    if len(set(identifiers)) != len(identifiers) or any(set(item) != {'id', 'description'} for item in model['criteria']):
        raise ValueError('Criteria need unique IDs and actual descriptions')
    package = Path(engine.__file__).resolve().parent.parent
    files = {'scripts/package_runtime.py': (package / 'scripts/package_runtime.py').read_bytes(),
             'scripts/json_contract.py': (package / 'scripts/json_contract.py').read_bytes(),
             'scripts/run.py': RUNNER.encode(), 'scripts/contract.json': (json.dumps(model, indent=2) + '\n').encode()}
    yaml, _ = engine.command_schema.schema_libraries()
    definitions = []
    def command(name, route, description, parameters=None):
        parameters = parameters or {}
        properties = {'operation': {'type': 'string', 'enum': [name]}, **{key: value['schema'] for key, value in parameters.items()}}
        defaults = {'operation': name, **{key: value['default'] for key, value in parameters.items() if 'default' in value}}
        document = {'schema': 'tkstack.command/v1', 'tool': {'type': 'function',
            'name': identity['name'].replace('-', '_') + '_' + name,
            'description': description, 'strict': True, 'parameters': object_schema(properties)},
            'cli': {'path': route, 'flags': {key: ['--' + key.replace('_', '-')] for key in parameters}, 'defaults': defaults},
            'run': {'artifact': 'scripts/workflow.lock.json'}}
        engine.command_schema.validate_document(document)
        front = yaml.safe_dump(document, sort_keys=False)
        body = f'# {" ".join(route).capitalize()}\n\n{description}\n\n'
        body += '[Execution contract](../references/execution.md) describes effects, paths, evidence, and limitations. Frontmatter defines the exact typed signature.\n'
        files['commands/' + name + '.md'] = ('---\n' + front + '---\n\n' + body).encode()
        definitions.append((' '.join(route), 'commands/' + name + '.md'))
    command('model', ['model'], 'Read the skill contract model, required evidence and explicit semantic/native boundaries without executing the procedure.')
    command('verify', ['verify'], 'Validate a retained workload report against the skill contract, criterion coverage and actual evidence hashes. Semantic review is recorded, not authenticated.',
            {'report': {'schema': {'type': 'string', 'minLength': 1}}})
    for name, binding in model.get('native', {}).items():
        if not re.fullmatch(r'native_[a-z][a-z0-9_]*', name):
            raise ValueError('Native bindings need a native_ operation name')
        if 'operation' in binding['parameters']:
            raise ValueError('The operation parameter is reserved for deterministic dispatch')
        engine.command_schema.regular(directory, binding['entrypoint'])
        for key, parameter in binding['parameters'].items():
            if set(parameter) - {'schema', 'default', 'flags', 'path', 'repeat', 'global'}:
                raise ValueError('Unknown native parameter binding')
            if parameter.get('repeat') and parameter['schema'].get('type') != 'array':
                raise ValueError('Repeated flags require an array')
        command(name, binding['cli_path'], binding['description'], binding['parameters'])
    for name, mount in model.get('subskills', {}).items():
        if not re.fullmatch(r'[a-z][a-z0-9-]*', name) or set(mount) != {'path', 'description'}:
            raise ValueError('Subskills map a command name to a contained path and description')
        child = engine.command_schema.mounted(directory, mount['path'])
        if engine.command_schema.package_identity(child)['name'] != name:
            raise ValueError('A subskill command must use its package name: ' + name)
        document = {'schema': 'tkstack.command/v1', 'tool': {'type': 'function',
            'name': identity['name'].replace('-', '_') + '_' + name.replace('-', '_'), 'description': mount['description'],
            'strict': True, 'parameters': engine.command_schema.MOUNT},
            'cli': {'path': [name], 'defaults': {'argv': []}}, 'run': {'skill': mount['path']}}
        engine.command_schema.validate_document(document)
        body = f'# {name.capitalize()}\n\n{mount["description"]}\n\n'
        body += f'Routes `{name} [command ...]` and `{name} --help` to the packaged [{name} subskill](../{mount["path"]}/SKILL.md). '
        body += 'Its own command files define the typed signatures, and its own lock binds execution.\n'
        files['commands/' + name + '.md'] = ('---\n' + yaml.safe_dump(document, sort_keys=False) + '---\n\n' + body).encode()
        definitions.append((name, 'commands/' + name + '.md'))
    if model.get('delegate'):
        engine.command_schema.regular(directory, model['delegate'])
    for name in ('help', 'version'):
        path = directory / 'commands' / (name + '.md')
        if path.exists():
            engine.command_schema.read_command(path)
            files['commands/' + name + '.md'] = path.read_bytes()
        else:
            files['commands/' + name + '.md'] = (package / 'templates/commands' / (name + '.md.tmpl')).read_bytes()
    invocation = '.tkstack/tkstack skills ' + identity['name'] + ' --'
    body = '# Execution contract\n\n' + model['purpose'] + '\n\n'
    body += f'Use `{invocation} help`, `{invocation} version`, and `{invocation} model`.\n'
    body += f'Run `{invocation} verify --report /path/to/report.json` for mechanical evidence verification.\n\n'
    body += 'The executable artifact is `scripts/workflow.lock.json`, built from the actual native code and command contracts. '
    body += 'The skill index routes residual judgment to its focused references. It does not replay a deterministic algorithm through inference.\n\n'
    body += '## Required criteria\n\n' + '\n'.join('- ' + item['id'] + ': ' + item['description'] for item in model['criteria']) + '\n\n'
    body += '## Report and validation\n\nRead `scripts/contract.json` for the exact JSON Schema of `facts`. A report has exactly '
    body += '`skill`, nonempty `objective`, `facts`, `criteria`, `evidence`, and `review`. '
    body += 'Each criterion has `id`, `status: pass`, nonempty evidence ID array and a reason. '
    body += 'Every modeled criterion is required. Evidence entries have unique `id`, `path`, SHA-256 `sha256`, and `kind`; actual files are hashed. '
    body += 'Review records have `reviewer`, `semantic_inspection: performed`, and explicit `limitations`. '
    body += 'The gate checks these records and file bytes; it cannot authenticate their truth or replace semantic inspection. Missing evidence blocks it.\n\n'
    body += '## Effects, scope, and native tools\n\nModel and verify do not mutate application/learning records; compiled invocation uses the shared runner\'s ignored .tkstack temporary materialization. Reserved help/version and direct metadata checks initialize no state. '
    body += 'Relative report/evidence/native paths resolve against the selected workspace, never Codify staging. '
    body += 'Native bindings execute the existing named helper with typed parameters, preserved output/exit status, a bounded timeout, and no shell strings. '
    body += 'Their documented effects retain the user\'s authorization boundary; invoking a verification operation does not authorize publication, generation, or configuration changes. '
    body += 'All temporary state stays in scoped `.tkstack/sessions/`; durable data follows the owned state helper. '
    body += 'Chat/Responses, Decisions, and harness inference remain explicit Vercel AI SDK profiles when an actual workflow needs them. These mechanical operations request no inference.\n\n'
    body += '## Limits\n\n' + '\n'.join('- ' + item for item in model['limits']) + '\n'
    files['references/execution.md'] = body.encode()
    receipt_path = directory / 'scripts/normalization.json'
    receipt = engine.parse_json(engine.read_bytes(receipt_path)) if receipt_path.exists() else {'version': 1, 'files': {}}
    if receipt.get('version') != 1 or not isinstance(receipt.get('files'), dict):
        raise ValueError('Invalid source-generation manifest')
    before = {}
    for name, data in files.items():
        path = engine.command_schema.regular(directory, name, exists=False)
        before[name] = path.read_bytes() if path.exists() else None
        if directory.name == 'codify' and name in ('scripts/package_runtime.py', 'scripts/json_contract.py') and before[name] != data:
            raise ValueError('Canonical Codify runtime differs from the release copy; sync the release before normalization')
        if before[name] is not None and before[name] != data:
            owned = receipt['files'].get(name) == hashlib.sha256(before[name]).hexdigest()
            if name != 'scripts/contract.json' and not owned:
                raise ValueError('Preserve the existing native implementation: ' + name)
    stale = {}
    for name, sha in receipt['files'].items():
        if name not in files:
            path = engine.command_schema.regular(directory, name, exists=False)
            if path.exists():
                stale[name] = path.read_bytes()
                if hashlib.sha256(stale[name]).hexdigest() != sha:
                    raise ValueError('Preserve modified generated content: ' + name)
    # This relative manifest belongs to the authored package/build, like its lock;
    # machine/session execution records remain in .tkstack.
    files['scripts/normalization.json'] = (json.dumps({'version': 1, 'files': {name: hashlib.sha256(data).hexdigest() for name, data in sorted(files.items())}}, indent=2) + '\n').encode()
    before['scripts/normalization.json'] = receipt_path.read_bytes() if receipt_path.exists() else None
    modes = {name: (directory / name).stat().st_mode & 0o777 if (directory / name).exists() else 0o644 for name in files}
    changed = [name for name in sorted(files) if before[name] != files[name]]
    if not dry_run:
        lock = ensure_state(state_path('locks', project=project_root(directory)) / 'skillify') / (hashlib.sha256(str(directory).encode()).hexdigest()[:16] + '.normalize.lock')
        with lock.open('a') as owner:
            try:
                fcntl.flock(owner, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as error:
                raise ValueError('Another normalizer owns this package') from error
            for name in changed:
                path = directory / name
                path.parent.mkdir(parents=True, exist_ok=True)
                if (path.read_bytes() if path.exists() else None) != before[name]:
                    raise ValueError('Source changed during normalization: ' + name)
                temporary = None
                try:
                    with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.normalize-', delete=False) as output:
                        temporary = Path(output.name)
                        output.write(files[name])
                    temporary.chmod(modes[name])
                    temporary.replace(path)
                finally:
                    if temporary is not None:
                        temporary.unlink(missing_ok=True)
            for name, expected in stale.items():
                path = directory / name
                if path.read_bytes() != expected:
                    raise ValueError('Generated source changed before removal: ' + name)
                path.unlink()
    return {'status': 'planned' if dry_run else 'normalized', 'skill': model['name'], 'changed': changed, 'removed': sorted(stale),
            'commands': definitions, 'profile_sha256': hashlib.sha256(Path(profile).read_bytes()).hexdigest()}

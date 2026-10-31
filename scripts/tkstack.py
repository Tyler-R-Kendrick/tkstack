#!/usr/bin/env python3
"""Run compiled skills/workflows through Codify, without interpreting their prompts."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
from types import SimpleNamespace
sys.dont_write_bytecode = True

from runtime_environment import with_paths
from tkstack_state import state_roots
from skill_roots import owned

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('tkstack_codify_runner', ROOT / 'skills/learn/skills/codify/scripts/codify.py')
codify = importlib.util.module_from_spec(spec)
spec.loader.exec_module(codify)
NAME = re.compile(r'[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}')


def read_json(path):
    with path.open('rb') as source:
        raw = source.read(1024 * 1024 + 1)
    if len(raw) > 1024 * 1024:
        raise ValueError('Runner JSON input exceeds 1 MiB')
    return codify.parse_json(raw)


def read_input(location):
    if location != '-':
        return read_json(Path(location))
    raw = sys.stdin.read(1024 * 1024 + 1)
    if len(raw.encode('utf-8')) > 1024 * 1024:
        raise ValueError('Runner JSON input exceeds 1 MiB')
    return codify.parse_json(raw)


def resolve_path(value, base):
    if not isinstance(value, str) or not value.strip():
        raise ValueError('Registry paths must be nonempty strings')
    path = Path(value).expanduser()
    return (path if path.is_absolute() else base / path).resolve()


def discover(project=None):
    scopes = state_roots(project)
    workspace = scopes['workspace'].parent
    import install
    entries = {'skills': install.collect(ROOT, 'skills'), 'workflows': {}}
    # Packaged subskills stay directly addressable; harnesses see only their parent.
    for name, path in owned(ROOT).items():
        entries['skills'].setdefault(name, path.resolve())
    settings = {}
    source = ROOT / 'harnesses/runner.json'
    files = [(source, 'source'), *[(scopes[scope] / 'runner.json', scope) for scope in ('global', 'user', 'workspace')]]
    for path, scope in files:
        if scope != 'source':
            for kind in entries:
                folders = [path.parent / kind]
                if path.parent == scopes['workspace']:
                    folders = [workspace / kind, workspace / '.agents' / kind, *folders]
                for folder in folders:
                    if not folder.is_dir():
                        continue
                    children = sorted(folder.iterdir())
                    if len(children) > 512:
                        raise ValueError('Runner discovery exceeds 512 entries in ' + str(folder))
                    for child in children:
                        name = child.name.removesuffix('.lock.json')
                        valid = (child / 'SKILL.md').is_file() if kind == 'skills' else child.is_dir() or child.name.endswith('.lock.json')
                        if valid and NAME.fullmatch(name):
                            entries[kind][name] = child.resolve()
        if not path.exists():
            continue
        value = read_json(path)
        if not isinstance(value, dict) or type(value.get('version')) is not int or value.get('version') != 1 or set(value) - {'version', 'skills', 'workflows', 'config', 'dependencies'}:
            raise ValueError('Expected a version 1 runner registry: ' + str(path))
        for kind in entries:
            mapping = value.get(kind, {})
            if not isinstance(mapping, dict) or len(mapping) > 256:
                raise ValueError('Registry skills/workflows require at most 256 named paths')
            for name, target in mapping.items():
                if not isinstance(name, str) or not NAME.fullmatch(name):
                    raise ValueError('Invalid registry name')
                entries[kind][name] = resolve_path(target, path.parent)
        for key in ('config', 'dependencies'):
            if key in value:
                settings[key] = resolve_path(value[key], path.parent)
                settings[key + '_scope'] = scope
    return workspace, scopes, entries, settings


def target(entries, kind, name, workspace):
    if name in entries[kind]:
        path = entries[kind][name]
    elif '/' in name or name in ('.', '..') or Path(name).is_absolute():
        path = resolve_path(name, workspace)
    else:
        raise ValueError('Unknown ' + kind + ' name: ' + name)
    path = path.resolve(strict=True)
    if kind == 'skills' and (not path.is_dir() or not (path / 'SKILL.md').is_file()):
        raise ValueError('A skill requires a package directory containing SKILL.md')
    if not path.is_dir() and not (kind == 'workflows' and path.is_file() and path.name.endswith('.lock.json')):
        raise ValueError('Select a command package or a compiled *.lock.json workflow')
    return path


def inspect(path):
    if path.is_file():
        lock = codify.check(path)
        return {'status': 'ready', 'artifact_sha256': lock['artifact_sha256'], 'inference': lock['inference']}
    items = codify.command_schema.catalog(path)
    if not items:
        raise ValueError('No compiled command interface; use Skillify/Codify explicitly. There is no prompt/inference fallback.')
    artifacts = [codify.command_schema.bound_lock(codify, path, item) for item in items if 'artifact' in item['run']]
    return {'status': 'ready' if artifacts else 'help-only', 'commands': [item['cli']['path'] for item in items],
            'inference_profiles': sorted({name for lock in artifacts for name in lock['inference']['profiles']})}


def configuration(lock, explicit, scopes, settings, environment):
    if lock['inference']['mode'] == 'none':
        if explicit is not None:
            raise ValueError('This lock declares no inference; --config is not accepted')
        return None
    selected = explicit or environment.get('TKSTACK_CONFIG')
    if selected is None:
        for scope in ('workspace', 'user', 'global'):
            candidate = scopes[scope] / 'profiles.json'
            if settings.get('config_scope') == scope:
                selected = settings['config']
                break
            if candidate.is_file():
                selected = candidate
                break
        if selected is None:
            selected = settings.get('config')
    if selected is None:
        files = codify.decode_files(lock)
        name = str(Path(lock['entrypoint']).parent / 'profiles.json')
        if name not in files:
            raise ValueError('Declared inference needs --config or scoped profiles.json')
        value = codify.parse_json(files[name])
    else:
        value = read_json(Path(selected).expanduser().absolute())
    if not isinstance(value, dict) or type(value.get('version')) is not int or value.get('version') != 1 or not isinstance(value.get('profiles'), dict) or not isinstance(value.get('providers'), dict):
        raise ValueError('Expected the existing version 1 Vercel AI SDK providers/profiles configuration')
    required = set(lock['inference']['profiles'])
    if not required <= set(value['profiles']):
        raise ValueError('Configuration is missing declared profiles: ' + ', '.join(sorted(required - set(value['profiles']))))
    result = deepcopy(value)
    result['profiles'] = {name: result['profiles'][name] for name in sorted(required)}
    providers = set()
    for name, profile in result['profiles'].items():
        if not isinstance(profile, dict):
            raise ValueError('Invalid named inference profile: ' + name)
        if profile.get('kind') != 'harness':
            provider = profile.get('provider')
            if not isinstance(provider, str) or provider not in value['providers']:
                raise ValueError('Missing provider for declared profile: ' + name)
            providers.add(provider)
    result['providers'] = {name: value['providers'][name] for name in sorted(providers)}
    return result


def parser():
    result = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    result.add_argument('--project', type=Path, help='Exact active workspace; defaults to scoped workspace discovery')
    commands = result.add_subparsers(dest='command')
    help_command = commands.add_parser('help', help='Read-only help')
    help_command.add_argument('topic', nargs='?', choices=['skills', 'workflows', 'list', 'tools', 'check'])
    listing = commands.add_parser('list', help='List names and observed compilation readiness without executing code')
    listing.add_argument('kind', nargs='?', choices=['skills', 'workflows'])
    for kind in ('skills', 'workflows'):
        run = commands.add_parser(kind, aliases=[kind[:-1]], help='Invoke ' + kind + ' by name or explicit path')
        run.add_argument('name')
        source = run.add_mutually_exclusive_group()
        source.add_argument('--call', help='OpenAI tool-call JSON file, or - for stdin')
        source.add_argument('--input', help='Raw JSON for a directly selected *.lock.json workflow, or - for stdin')
        run.add_argument('--config', type=Path, help='Existing Vercel AI SDK version 1 profile configuration')
        run.add_argument('--dependencies', type=Path, help='Explicit locked node_modules reuse')
        run.add_argument('--timeout', type=int, default=30)
    for name in ('tools', 'check'):
        command = commands.add_parser(name, help='Read-only ' + name)
        command.add_argument('kind', choices=['skills', 'workflows'])
        command.add_argument('name')
        if name == 'tools':
            command.add_argument('--format', choices=['responses', 'chat'], default='responses')
    return result, commands


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    command_argv = []
    if '--' in argv:
        split = argv.index('--')
        command_argv, argv = argv[split + 1:], argv[:split]
    cli, commands = parser()
    args = cli.parse_args(argv)
    if args.command in (None, 'help'):
        topic = getattr(args, 'topic', None)
        (commands.choices[topic] if topic else cli).print_help()
        return 0
    invoking = args.command in ('skill', 'skills', 'workflow', 'workflows')
    if command_argv and not invoking:
        cli.error('Only skills/workflows accept -- <command> [arguments]')
    try:
        workspace, scopes, entries, settings = discover(args.project)
        if args.command == 'list':
            kinds = [args.kind] if args.kind else entries
            tasks = [(kind, name, path) for kind in kinds for name, path in sorted(entries[kind].items())]
            def observe(task):
                kind, name, path = task
                try:
                    readiness = inspect(target(entries, kind, name, workspace))
                except (OSError, ValueError, TypeError, KeyError) as error:
                    readiness = {'status': 'unavailable', 'reason': str(error)}
                return {'kind': kind, 'name': name, 'path': str(path), **readiness}
            with ThreadPoolExecutor(max_workers=4) as pool:
                result = list(pool.map(observe, tasks))
        else:
            kind = ('skills' if args.command in ('skill', 'skills') else 'workflows') if invoking else args.kind
            selected = target(entries, kind, args.name, workspace)
            if args.command == 'check':
                result = inspect(selected)
            elif args.command == 'tools':
                if selected.is_file():
                    raise ValueError('Tool exports require Markdown command definitions; select the workflow package')
                result = codify.command_schema.export(selected, args.format)
            else:
                environment = with_paths(ROOT)
                environment['TKSTACK_WORKSPACE_DIR'] = str(scopes['workspace'])
                def invoke(lock, payload, _project, timeout, _dependencies, _config):
                    config = configuration(lock, args.config, scopes, settings, environment)
                    dependencies = args.dependencies or (settings.get('dependencies') if lock['runtime'] == 'node' else None)
                    return codify.invoke(lock, payload, workspace, timeout, dependencies, config, environment=environment)
                engine = SimpleNamespace(check=codify.check, invoke=invoke, project_root=lambda: workspace)
                if selected.is_file():
                    if args.input is None or args.call is not None or command_argv:
                        raise ValueError('A direct lock requires --input JSON and accepts no command/tool-call arguments')
                    raw = read_input(args.input)
                    code, out, err = invoke(codify.check(selected), raw, workspace, args.timeout, None, None)
                else:
                    if args.input is not None:
                        raise ValueError('Package invocation uses Markdown commands or --call; --input selects a direct lock')
                    call = None
                    if args.call is not None:
                        if command_argv:
                            raise ValueError('Select a tool call or CLI arguments, not both')
                        call = read_input(args.call)
                    if not codify.command_schema.catalog(selected):
                        raise ValueError('No compiled command interface; compile explicitly with Skillify/Codify. No inference fallback is available.')
                    code, out, err = codify.command_schema.execute(engine, selected, command_argv, call, workspace, args.timeout)
                sys.stdout.write(out)
                sys.stderr.write(err)
                return code if 0 <= code <= 125 else 1
        print(json.dumps(result, indent=2))
        return 0
    except (OSError, ValueError, TypeError, KeyError) as error:
        print('tkstack: ' + str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())

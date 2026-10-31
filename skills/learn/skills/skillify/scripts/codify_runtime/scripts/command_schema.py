"""Markdown command signatures, API exports, CLI parsing, and verified-lock dispatch."""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
import command_manual
from json_contract import loads as json_value

LIMIT = 256 * 1024
TOKEN = r'[a-zA-Z0-9_][a-zA-Z0-9_-]{0,63}'
SCHEMA_KEYS = {'type', 'description', 'title', 'properties', 'required', 'additionalProperties',
    'items', 'anyOf', 'enum', 'const', 'minimum', 'maximum', 'exclusiveMinimum',
    'exclusiveMaximum', 'multipleOf', 'minLength', 'maxLength', 'pattern',
    'minItems', 'maxItems'}
RESERVED = ('help', 'version')
# A mounted subskill receives the remaining CLI tokens verbatim; its own catalog types them.
MOUNT = {'type': 'object', 'properties': {'argv': {'type': 'array', 'items': {'type': 'string'}}},
         'required': ['argv'], 'additionalProperties': False}


def builtin(name, legacy=False):
    if name == 'help':
        properties = {'topic': {'type': ['string', 'null'], 'description': 'Command path, or null for the package manual.'}}
        cli = {'path': ['help'], 'positionals': ['topic'], 'defaults': {'topic': None}}
        if not legacy:
            properties['format'] = {'type': 'string', 'enum': ['text', 'man'], 'description': 'Fixed console text or generated man(1) source.'}
            cli['flags'] = {'format': ['--format']}
            cli['defaults']['format'] = 'text'
        description = 'Generate and render a read-only command manual.'
        body = '# Help\n\nUse help [command ...] or <command> --help. Default text uses fixed rendering. Use help --format man for generated man(1) roff source. No workflow, model, pager, or state initialization runs.'
    else:
        properties, cli = {}, {'path': ['version']}
        description = 'Show the package name and declared version without execution.'
        body = '# Version\n\nUse version or --version. Returns metadata.version from SKILL.md; a workflow without a declared skill version reports unversioned. Discovery never runs a workflow or initializes state.'
    return {'schema': 'tkstack.command/v1', 'tool': {'type': 'function', 'name': name, 'description': description,
        'strict': True, 'parameters': {'type': 'object', 'properties': properties, 'required': list(properties), 'additionalProperties': False}},
        'cli': cli, 'run': {'builtin': name}, 'body': body}


def schema_libraries():
    try:
        import yaml
        from jsonschema import Draft202012Validator
    except ImportError as error:
        raise ValueError('Command signatures require the pinned PyYAML/jsonschema dependencies. '
            'Use the managed codify/skillify launcher after install.sh, or install '
            'requirements/requirements.lock in an isolated environment with --require-hashes.') from error
    return yaml, Draft202012Validator




def regular(root, name, exists=True):
    if not isinstance(name, str) or '\\' in name or Path(name).is_absolute() or any(
            part in ('', '.', '..') for part in name.split('/')):
        raise ValueError('Command paths must be contained relative POSIX paths')
    path = root / name
    if not path.resolve().is_relative_to(root):
        raise ValueError('Command path escapes its package')
    if any(item.is_symlink() for item in (path, *path.parents) if item.is_relative_to(root)):
        raise ValueError('Command paths must not be symlinked')
    if exists and not path.is_file():
        raise ValueError('Missing command file: ' + name)
    return path


def validate_schema(schema, depth=0):
    """An explicit, inline subset of OpenAI strict function parameter schemas."""
    if depth > 10 or not isinstance(schema, dict) or set(schema) - SCHEMA_KEYS:
        raise ValueError('Unsupported strict parameter schema; use inline schemas within 10 levels')
    if 'anyOf' in schema:
        if not isinstance(schema['anyOf'], list) or not schema['anyOf']:
            raise ValueError('anyOf requires nonempty alternatives')
        for child in schema['anyOf']:
            validate_schema(child, depth + 1)
    kinds = schema.get('type', [])
    kinds = [kinds] if isinstance(kinds, str) else kinds
    if not isinstance(kinds, list) or any(kind not in ('string', 'number', 'integer', 'boolean', 'object', 'array', 'null') for kind in kinds):
        raise ValueError('Unsupported parameter type')
    if not kinds and 'anyOf' not in schema:
        raise ValueError('Every parameter needs type or anyOf')
    if 'object' in kinds:
        properties = schema.get('properties')
        required = schema.get('required')
        if not isinstance(properties, dict) or not isinstance(required, list) or len(set(required)) != len(required) or set(required) != set(properties) or schema.get('additionalProperties') is not False:
            raise ValueError('Strict objects require all properties and additionalProperties: false')
        for child in properties.values():
            validate_schema(child, depth + 1)
    if 'array' in kinds:
        validate_schema(schema.get('items'), depth + 1)


def validate_document(value):
    _, validator = schema_libraries()
    document_schema = json_value(Path(__file__).with_name('command.schema.json').read_text())
    errors = list(validator(document_schema).iter_errors(value))
    if errors:
        raise ValueError('Invalid command frontmatter: ' + errors[0].message)
    if not isinstance(value, dict) or set(value) != {'schema', 'tool', 'cli', 'run'} or value['schema'] != 'tkstack.command/v1':
        raise ValueError('Expected tkstack.command/v1 with tool, cli, and run')
    tool = value['tool']
    if not isinstance(tool, dict) or set(tool) != {'type', 'name', 'description', 'strict', 'parameters'} or tool['type'] != 'function' or tool['strict'] is not True or not isinstance(tool['name'], str) or not re.fullmatch(TOKEN, tool['name']) or not isinstance(tool['description'], str) or not tool['description'].strip():
        raise ValueError('Expected an OpenAI Responses function tool with name, description, strict: true, and parameters')
    schema = tool['parameters']
    validate_schema(schema)
    if schema.get('type') != 'object' or 'anyOf' in schema:
        raise ValueError('Function parameters must have an object root')
    try:
        validator.check_schema(schema)
    except Exception as error:
        raise ValueError('Invalid parameter JSON Schema: ' + str(error).splitlines()[0]) from error
    cli, run = value['cli'], value['run']
    if not isinstance(cli, dict) or set(cli) - {'path', 'aliases', 'positionals', 'flags', 'defaults'} or 'path' not in cli:
        raise ValueError('CLI metadata requires path and optional aliases/positionals/flags/defaults')
    for path in [cli['path'], *cli.get('aliases', [])]:
        if not isinstance(path, list) or not path or any(not isinstance(part, str) or not re.fullmatch(TOKEN, part) for part in path):
            raise ValueError('Command paths and aliases must be nonempty token arrays')
    positionals, flags, defaults = cli.get('positionals', []), cli.get('flags', {}), cli.get('defaults', {})
    properties = schema['properties']
    if not isinstance(positionals, list) or any(not isinstance(name, str) for name in positionals) or len(set(positionals)) != len(positionals) or not isinstance(flags, dict) or not isinstance(defaults, dict) or (set(positionals) | set(flags) | set(defaults)) - set(properties) or set(positionals) & set(flags):
        raise ValueError('Bind existing parameters once as positionals or flags; defaults must name parameters')
    names = {'--help', '-h', '--version', '-V'}
    for name, binding in flags.items():
        if not isinstance(binding, list) or not binding:
            raise ValueError('Flags must map parameter names to nonempty spelling arrays')
        for flag in binding:
            if not isinstance(flag, str) or not re.fullmatch(r'--[a-zA-Z][a-zA-Z0-9-]*|-[a-zA-Z]', flag):
                raise ValueError('Flag spellings must be unique; --help/-h and --version/-V are reserved')
            spellings = [flag, '--no-' + flag[2:]] if properties[name].get('type') == 'boolean' and flag.startswith('--') else [flag]
            if names.intersection(spellings):
                raise ValueError('Flag spellings must be unique, including automatic --no- flags')
            names.update(spellings)
    for name, default in defaults.items():
        if not validator(properties[name]).is_valid(default):
            raise ValueError('Invalid CLI default: ' + name)
    if set(positionals) | set(flags) | set(defaults) != set(properties):
        raise ValueError('Every parameter needs a CLI binding or a default')
    if not isinstance(run, dict) or (set(run) not in ({'artifact'}, {'skill'}) and run not in [{'builtin': name} for name in RESERVED]):
        raise ValueError('Run binds one artifact, a mounted subskill, or a reserved read-only builtin')
    if 'skill' in run:
        argv = properties.get('argv', {})
        if ({key: value for key, value in schema.items() if key != 'description'} !=
                {**MOUNT, 'properties': {'argv': {**MOUNT['properties']['argv'], **({'description': argv['description']} if 'description' in argv else {})}}}
                or set(cli) - {'path', 'aliases', 'defaults'} or cli.get('defaults') != {'argv': []}):
            raise ValueError('A mounted subskill takes only argv, with CLI default []')
    if 'builtin' in run:
        name = run['builtin']
        expected = builtin(name, legacy=name == 'help' and set(properties) == {'topic'})
        expected_properties = expected['tool']['parameters']['properties']
        if (tool['name'] != name or cli != expected['cli'] or set(properties) != set(expected_properties)
                or any({k: v for k, v in properties[key].items() if k != 'description'} !=
                       {k: v for k, v in expected_properties[key].items() if k != 'description'} for key in properties)):
            raise ValueError('Reserved ' + name + ' must use its standard name, signature, CLI binding, and builtin')
    elif tool['name'] in RESERVED:
        raise ValueError('Reserved tool name: ' + tool['name'])
    for route in [cli['path'], *cli.get('aliases', [])]:
        if route[0] in RESERVED and run != {'builtin': route[0]}:
            raise ValueError('Reserved command route: ' + ' '.join(route))
    return value


def frontmatter(path):
    yaml, _ = schema_libraries()
    with path.open('rb') as stream:
        data = stream.read(LIMIT + 1)
    if len(data) > LIMIT:
        raise ValueError('Command Markdown exceeds 256 KiB')
    text = data.decode('utf-8')
    lines = text.splitlines()
    if not lines or lines[0] != '---' or '---' not in lines[1:]:
        raise ValueError('Command Markdown needs closed YAML frontmatter')
    end = lines.index('---', 1)
    front = '\n'.join(lines[1:end])
    class Loader(yaml.SafeLoader):
        pass
    def mapping(loader, node):
        result = {}
        for key_node, value_node in node.value:
            key = loader.construct_object(key_node)
            if not isinstance(key, str) or key in result:
                raise ValueError('YAML keys must be unique strings')
            result[key] = loader.construct_object(value_node)
        return result
    Loader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, mapping)
    try:
        if any(isinstance(token, yaml.tokens.AliasToken) for token in yaml.scan(front)):
            raise ValueError('YAML aliases are not supported in command signatures')
        value = yaml.load(front, Loader=Loader)
        json.dumps(value, allow_nan=False)
    except (yaml.YAMLError, TypeError) as error:
        raise ValueError('Command frontmatter must be safe, JSON-compatible YAML') from error
    body = '\n'.join(lines[end + 1:]).strip()
    return value, body, data


def read_command(path):
    value, body, data = frontmatter(path)
    if not body:
        raise ValueError('Command Markdown needs usage/procedure content')
    return {**validate_document(value), 'body': body, 'sha256': hashlib.sha256(data).hexdigest()}


def package_identity(directory):
    root = directory.resolve(strict=True)
    skill = root / 'SKILL.md'
    if not skill.exists():
        return {'name': root.name, 'version': 'unversioned', 'description': 'Command interface for ' + root.name + '.'}
    regular(root, 'SKILL.md')
    info, _, _ = frontmatter(skill)
    if not isinstance(info, dict):
        raise ValueError('Skill frontmatter must be an object')
    metadata = info.get('metadata', {})
    if not isinstance(metadata, dict):
        raise ValueError('Skill metadata must be an object')
    result = {'name': info.get('name', root.name), 'version': metadata.get('version', 'unversioned'),
              'description': info.get('description', 'Command interface for ' + root.name + '.')}
    if any(not isinstance(value, str) or not value.strip() for value in result.values()):
        raise ValueError('Skill name, description, and metadata.version must be nonempty strings')
    return result


def mounted(root, name):
    path = regular(root, name, exists=False)
    if path == root or not path.is_dir():
        raise ValueError('Mounted subskill must be a contained package directory: ' + name)
    regular(root, name + '/SKILL.md')
    return path


def catalog(directory):
    root = directory.resolve(strict=True)
    commands = root / 'commands'
    if commands.is_symlink():
        raise ValueError('Command directory must not be symlinked')
    paths = sorted(commands.rglob('*.md')) if commands.is_dir() else []
    if len(paths) > 128:
        raise ValueError('At most 128 command definitions are supported')
    result, names, routes = [], set(), set()
    for path in paths:
        relative = path.relative_to(root).as_posix()
        regular(root, relative)
        item = {**read_command(path), 'file': relative}
        if 'artifact' in item['run']:
            regular(root, item['run']['artifact'], exists=False)
        if 'skill' in item['run']:
            mounted(root, item['run']['skill'])
        name = item['tool']['name']
        if name in names:
            raise ValueError('Duplicate tool name: ' + name)
        names.add(name)
        for route in [item['cli']['path'], *item['cli'].get('aliases', [])]:
            route = tuple(route)
            if route in routes or (route[0] == 'help' and item['run'] != {'builtin': 'help'}):
                raise ValueError('Duplicate or reserved command route: ' + ' '.join(route))
            routes.add(route)
        result.append(item)
    for item in result:
        if 'skill' in item['run']:
            for route in [item['cli']['path'], *item['cli'].get('aliases', [])]:
                if any(other != route and other[:len(route)] == route for other in map(list, routes)):
                    raise ValueError('A mounted subskill owns every route below ' + ' '.join(route))
    if paths or commands.is_dir():
        for name in RESERVED:
            if name not in names:
                result.append({**builtin(name), 'file': None, 'sha256': None})
    return result


def export(directory, api='responses'):
    tools = [deepcopy(item['tool']) for item in catalog(directory)]
    return tools if api == 'responses' else [{'type': 'function', 'function': {k: v for k, v in tool.items() if k != 'type'}} for tool in tools]


def help_text(items, identity=None, topic=(), format='text'):
    identity = identity or {'name': 'workflow', 'version': 'unversioned', 'description': 'Deterministic command interface.'}
    return command_manual.render(identity, items, topic, format)['help']


def cli_payload(items, argv, identity=None):
    identity = identity or {'name': 'workflow', 'version': 'unversioned', 'description': 'Deterministic command interface.'}
    if argv and argv[0] in ('version', '--version', '-V'):
        if argv == ['version', '--help'] or argv == ['version', '-h']:
            return None, help_text(items, identity, ('version',))
        if len(argv) != 1 and argv not in (['version', '--version'], ['version', '-V']):
            raise ValueError('Version takes no arguments')
        return None, command_manual.clean(identity['name'] + ' ' + identity['version']) + '\n'
    if not argv or argv[0] in ('--help', '-h', 'help'):
        if argv in (['help', '--help'], ['help', '-h']):
            return None, help_text(items, identity, ('help',))
        if argv in (['help', '--version'], ['help', '-V']):
            return None, command_manual.clean(identity['name'] + ' ' + identity['version']) + '\n'
        parser = argparse.ArgumentParser(prog='help', add_help=False, allow_abbrev=False)
        parser.add_argument('topic', nargs='*')
        parser.add_argument('--format', choices=('text', 'man'), default='text')
        args = parser.parse_intermixed_args(argv[1:])
        return None, help_text(items, identity, args.topic, args.format)
    candidates = [(len(route), item, route) for item in items for route in
        [item['cli']['path'], *item['cli'].get('aliases', [])] if argv[:len(route)] == route]
    if not candidates:
        prefix = argv[:-1] if argv[-1:] in (['--help'], ['-h']) else argv
        children = [item for item in items if any(route[:len(prefix)] == prefix for route in
            [item['cli']['path'], *item['cli'].get('aliases', [])])]
        if children:
            return None, help_text(items, identity, prefix)
        raise ValueError('Unknown command: ' + ' '.join(argv))
    size, item, route = max(candidates, key=lambda candidate: candidate[0])
    tail = argv[size:]
    if 'skill' in item['run']:
        return item, {'argv': tail}
    options = tail[:tail.index('--')] if '--' in tail else tail
    if '--help' in options or '-h' in options:
        return None, help_text(items, identity, route)
    if '--version' in options or '-V' in options:
        return None, command_manual.clean(identity['name'] + ' ' + identity['version']) + '\n'
    parser = argparse.ArgumentParser(prog=' '.join(route), description=item['tool']['description'], add_help=False, allow_abbrev=False)
    cli, properties = item['cli'], item['tool']['parameters']['properties']
    for name in cli.get('positionals', []):
        parser.add_argument(name, nargs='?', default=argparse.SUPPRESS)
    for name, flags in cli.get('flags', {}).items():
        kwargs = {'dest': name, 'default': argparse.SUPPRESS}
        if properties[name].get('type') == 'boolean':
            kwargs['action'] = argparse.BooleanOptionalAction
        parser.add_argument(*flags, **kwargs)
    supplied = vars(parser.parse_args(tail))
    payload = deepcopy(cli.get('defaults', {}))
    for name, raw in supplied.items():
        kind = properties[name].get('type')
        nullable_text = isinstance(kind, list) and set(kind) == {'string', 'null'}
        if kind == 'string' or isinstance(raw, bool):
            payload[name] = raw
        elif nullable_text and raw != 'null' and not raw.startswith('"'):
            payload[name] = raw
        else:
            payload[name] = json_value(raw)
    return item, payload


def call_payload(items, call):
    if not isinstance(call, dict):
        raise ValueError('Tool call must be an object')
    function = call.get('function', call)
    if not isinstance(function, dict) or not isinstance(function.get('name'), str) or 'arguments' not in function:
        raise ValueError('Tool call needs name and arguments')
    item = next((item for item in items if item['tool']['name'] == function['name']), None)
    if item is None:
        raise ValueError('Unknown tool name: ' + function['name'])
    arguments = function['arguments']
    return item, json_value(arguments) if isinstance(arguments, str) else arguments


def bound_lock(engine, directory, item):
    root = directory.resolve(strict=True)
    artifact = regular(root, item['run']['artifact'])
    lock = engine.check(artifact)
    lock_root = (artifact.parent / lock['root']).resolve()
    if lock_root != root or item['file'] not in lock['files'] or lock['files'][item['file']]['sha256'] != item['sha256']:
        raise ValueError('Command definition is not bound to this lock; compile with commands/ included')
    return lock


def execute(engine, directory, argv=(), call=None, project=None, timeout=30, dependencies=None, config=None):
    root = directory.resolve(strict=True)
    items = catalog(root)
    identity = package_identity(root)
    item, payload = call_payload(items, call) if call is not None else cli_payload(items, list(argv), identity)
    if item is None:
        return 0, payload, ''
    _, validator = schema_libraries()
    errors = list(validator(item['tool']['parameters']).iter_errors(payload))
    if errors:
        raise ValueError('Invalid command arguments: ' + errors[0].message)
    if item['run'] == {'builtin': 'help'}:
        topic = payload.get('topic')
        result = command_manual.render(identity, items, topic.split() if topic else (), payload.get('format', 'text'))
        return 0, json.dumps(result, ensure_ascii=False, sort_keys=True) + '\n', ''
    if item['run'] == {'builtin': 'version'}:
        return 0, json.dumps({key: identity[key] for key in ('name', 'version')}, sort_keys=True) + '\n', ''
    if 'skill' in item['run']:
        # The subskill is a complete package: its own catalog, identity, and lock bind the call.
        return execute(engine, mounted(root, item['run']['skill']), payload['argv'], None, project, timeout, dependencies, config)
    lock = bound_lock(engine, root, item)
    return engine.invoke(lock, payload, project or engine.project_root(), timeout, dependencies, config)


def add_parsers(commands):
    listing = commands.add_parser('commands', help='Validate/list Markdown signatures or export OpenAI tools')
    listing.add_argument('directory', type=Path)
    listing.add_argument('--format', choices=['index', 'responses', 'chat'], default='index')
    invoke = commands.add_parser('invoke', help='Invoke a bound lock from a CLI command or API tool call')
    invoke.add_argument('directory', type=Path)
    invoke.add_argument('--call', help='Tool-call JSON file, or - for stdin; otherwise use -- <command> [args]')
    invoke.add_argument('--project', type=Path)
    invoke.add_argument('--timeout', type=int, default=30)
    invoke.add_argument('--config', type=Path)
    invoke.add_argument('--dependencies', type=Path)
    # parse_known_args in the frontend preserves only tokens after an explicit --.
    return listing, invoke


def operation(engine, args, argv=(), call=None):
    if args.command == 'commands':
        result = export(args.directory, args.format) if args.format != 'index' else [
            {'path': item['cli']['path'], 'aliases': item['cli'].get('aliases', []),
             'name': item['tool']['name'], 'file': item['file']} for item in catalog(args.directory)]
        return 0, json.dumps(result, indent=2) + '\n', ''
    if args.call is not None:
        if argv:
            raise ValueError('Select a tool call or CLI arguments, not both')
        call = json_value(call)
    return execute(engine, args.directory, argv, call, args.project, args.timeout, args.dependencies, args.config)

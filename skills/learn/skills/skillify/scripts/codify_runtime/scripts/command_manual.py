"""Generate man(1) source and deterministic plain console pages from one model."""

import json
import re
import textwrap


def clean(value):
    value = str(value).replace('\r\n', '\n').replace('\r', '\n').expandtabs(4)
    return ''.join(char if char == '\n' or ord(char) >= 32 and not 127 <= ord(char) < 160
                   else f'\\x{ord(char):02x}' for char in value)


def plain_markdown(value):
    lines = []
    fenced = False
    for line in clean(value).splitlines():
        if re.match(r'^\s*(`{3,}|~{3,})', line):
            fenced = not fenced
            continue
        if not fenced:
            line = re.sub(r'^\s{0,3}#{1,6}\s+', '', line)
            line = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'\1 (\2)', line)
            line = re.sub(r'`([^`]+)`', r'\1', line)
        lines.append(line)
    return '\n'.join(lines).strip()


def json_text(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'))


def parameter_text(schema):
    kind = schema.get('type')
    result = ' | '.join(kind) if isinstance(kind, list) else kind or 'anyOf'
    constraints = {key: value for key, value in schema.items()
                   if key not in ('type', 'description', 'title')}
    if constraints:
        result += '; ' + json_text(constraints)
    if schema.get('description'):
        result += '. ' + schema['description']
    return result


def manual(identity, items, topic=()):
    """A section contains paragraphs or tagged entries, in a stable order."""
    topic = tuple(topic)
    selected = next((item for item in items if topic in [tuple(item['cli']['path']),
                    *(tuple(route) for route in item['cli'].get('aliases', []))]), None) if topic else None
    children = [item for item in items if any(tuple(route[:len(topic)]) == topic for route in
                [item['cli']['path'], *item['cli'].get('aliases', [])])]
    if topic and selected is None and not children:
        raise ValueError('Unknown help topic: ' + ' '.join(topic))
    name, version = identity['name'], identity['version']
    route = selected['cli']['path'] if selected else list(topic)
    invocation = ' '.join([name, *route])
    description = selected['tool']['description'] if selected else identity['description']
    sections = [('NAME', [('paragraph', invocation + ' - ' + description)])]
    if selected:
        cli = selected['cli']
        properties = selected['tool']['parameters']['properties']
        synopsis = invocation
        for key in cli.get('positionals', []):
            placeholder = key.upper()
            synopsis += ' ' + ('[' + placeholder + ']' if key in cli.get('defaults', {}) else placeholder)
        if cli.get('flags'):
            synopsis += ' [OPTIONS]'
        sections += [('SYNOPSIS', [('paragraph', synopsis)]),
                     ('DESCRIPTION', [('paragraph', description), ('paragraph', plain_markdown(selected['body']))])]
        aliases = cli.get('aliases', [])
        if aliases:
            sections.append(('ALIASES', [('paragraph', ' '.join([name, *alias])) for alias in aliases]))
        options = []
        for key, flags in cli.get('flags', {}).items():
            schema = properties[key]
            spellings = list(flags)
            if schema.get('type') == 'boolean':
                spellings.extend('--no-' + flag[2:] for flag in flags if flag.startswith('--'))
            label = ', '.join(spellings)
            if schema.get('type') != 'boolean':
                label += ' ' + key.upper()
            detail = parameter_text(schema)
            detail += '. Default: ' + json_text(cli['defaults'][key]) if key in cli.get('defaults', {}) else '. Required.'
            options.append(('entry', label, detail))
        options += [('entry', '-h, --help', 'Render this command as a deterministic console man page.'),
                    ('entry', '-V, --version', 'Show the package name and declared version without execution.')]
        sections.append(('OPTIONS', options))
        sections.append(('TOOL PARAMETERS', [('entry', key, parameter_text(schema)) for key, schema in sorted(properties.items())]))
    else:
        sections += [('SYNOPSIS', [('paragraph', invocation + ' [COMMAND] [OPTIONS]'),
                                   ('paragraph', name + ' help [COMMAND ...] [--format text|man]'),
                                   ('paragraph', name + ' version')]),
                     ('DESCRIPTION', [('paragraph', description),
                                      ('paragraph', 'Omitting a command shows this manual. Help and version are reserved read-only commands; neither runs a workflow or initializes state.')]),
                     ('COMMANDS', [('entry', ' '.join(item['cli']['path']), item['tool']['description'])
                                   for item in sorted(children, key=lambda item: item['cli']['path'])]),
                     ('OPTIONS', [('entry', '-h, --help', 'Render this manual as plain console text.'),
                                  ('entry', '-V, --version', 'Show the package name and declared version.'),
                                  ('entry', 'help --format man', 'Emit generated man(1) roff source instead of console text.')])]
    sections += [('EXIT STATUS', [('entry', '0', 'Successful discovery or workflow execution.'),
                                  ('entry', '1', 'Invalid metadata, arguments, stale artifact, or workflow failure.'),
                                  ('entry', '2', 'Command-line parsing error. Other workflow exit codes propagate.')]),
                 ('VERSION', [('paragraph', name + ' ' + version)])]
    return {'name': invocation, 'version': version, 'package': name, 'sections': sections}


def roff_escape(value):
    lines = clean(value).replace('\\', r'\e').replace('-', r'\-').splitlines()
    return '\n'.join((r'\&' if line.startswith(('.', "'")) else '') + line for line in lines)


def roff(page):
    def quoted(value):
        return roff_escape(value).replace('"', r'\(dq').replace('\n', ' ')
    lines = [f'.TH "{quoted(page["name"].upper())}" "1" "" "{quoted(page["package"] + " " + page["version"])}" "User Commands"']
    for heading, blocks in page['sections']:
        lines.append('.SH ' + heading)
        for block in blocks:
            if block[0] == 'entry':
                lines.extend(['.TP', roff_escape(block[1]), roff_escape(block[2])])
            elif block[1]:
                for paragraph in block[1].split('\n\n'):
                    lines.extend(['.PP', roff_escape(paragraph)])
    return '\n'.join(lines) + '\n'


def console(page):
    """Fixed wrapping; no terminal probes, date, color, pager, or host formatter."""
    lines = [clean(page['name']).upper() + '(1)', '']
    for heading, blocks in page['sections']:
        lines.append(heading)
        for block in blocks:
            if block[0] == 'entry':
                lines.extend(textwrap.wrap(clean(block[1]), width=78, initial_indent='    ', subsequent_indent='    ', break_long_words=False, break_on_hyphens=False))
                lines.extend(textwrap.wrap(clean(block[2]), width=78, initial_indent='        ', subsequent_indent='        ', break_long_words=False, break_on_hyphens=False))
            else:
                for paragraph in clean(block[1]).split('\n\n'):
                    for line in paragraph.splitlines():
                        lines.extend(textwrap.wrap(line, width=78, initial_indent='    ', subsequent_indent='    ', break_long_words=False, break_on_hyphens=False))
            lines.append('')
    return '\n'.join(lines).rstrip() + '\n'


def render(identity, items, topic=(), format='text'):
    if format not in ('text', 'man'):
        raise ValueError('Help format must be text or man')
    page = manual(identity, items, topic)
    source = roff(page)
    return {'help': console(page) if format == 'text' else source, 'man': source,
            'format': format, 'name': identity['name'], 'version': identity['version']}

from concurrent.futures import ThreadPoolExecutor
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

import yaml

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / 'skills/codify/scripts/codify.py'
spec = importlib.util.spec_from_file_location('command_contract_codify', SCRIPT)
engine = importlib.util.module_from_spec(spec)
spec.loader.exec_module(engine)
commands = engine.command_schema


class CommandSchemaTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.project = Path(self.temporary.name)
        source = self.project / 'source.md'
        source.write_text('Repeat text a bounded number of times, optionally uppercasing it.')
        self.root = self.project / 'repeat-text'
        engine.scaffold(source, self.root)
        (self.root / 'scripts/workflow.py').write_text('''def execute(value):
    if set(value) != {'text', 'count', 'loud'} or not isinstance(value['text'], str) or type(value['count']) is not int or not 1 <= value['count'] <= 4 or type(value['loud']) is not bool:
        raise ValueError('Invalid repetition input')
    text = value['text'].upper() if value['loud'] else value['text']
    return {'result': '|'.join([text] * value['count'])}
''')
        (self.root / 'cases.json').write_text(json.dumps({'version': 1, 'cases': [
            {'id': 'repeat', 'input': {'text': 'go', 'count': 2, 'loud': False}, 'exit': 0, 'output': {'result': 'go|go'}},
            {'id': 'transfer', 'input': {'text': 'é', 'count': 1, 'loud': True}, 'exit': 0, 'output': {'result': 'É'}},
            {'id': 'reject', 'input': {'text': 'go', 'count': 0, 'loud': False}, 'exit': 1}]}))
        self.document = {'schema': 'tkstack.command/v1', 'tool': {
            'type': 'function', 'name': 'repeat_text', 'description': 'Repeat bounded text.', 'strict': True,
            'parameters': {'type': 'object', 'properties': {'text': {'type': 'string'},
                'count': {'type': 'integer', 'minimum': 1, 'maximum': 4}, 'loud': {'type': 'boolean'}},
                'required': ['text', 'count', 'loud'], 'additionalProperties': False}},
            'cli': {'path': ['text', 'repeat'], 'aliases': [['repeat'], ['text', 'again']],
                'positionals': ['text'], 'flags': {'count': ['--count', '-n'], 'loud': ['--loud']},
                'defaults': {'count': 1, 'loud': False}},
            'run': {'artifact': 'scripts/workflow.lock.json'}}
        self.definition = self.root / 'commands/run.md'
        self.write_document()
        self.artifact = self.root / 'scripts/workflow.lock.json'

    def write_document(self):
        self.definition.write_text('---\n' + yaml.safe_dump(self.document, sort_keys=False) +
            '---\n\n# Repeat text\n\nUse `text repeat TEXT [-n COUNT] [--loud]`.\n')

    def compile(self):
        return engine.compile_workflow(self.root / 'PROMPT.md', self.root / 'scripts/run.py',
            self.root / 'cases.json', self.artifact, root=self.root, project=self.project)

    def cli(self, *args, script=SCRIPT, call=None, expected=0):
        result = subprocess.run([sys.executable, '-B', str(script), *map(str, args)],
            input=json.dumps(call) if call is not None else None, cwd=self.project,
            capture_output=True, text=True, timeout=30, env={**os.environ, 'TKSTACK_WORKSPACE_DIR': str(self.project / '.tkstack')})
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return result.stdout

    def test_nested_command_alias_flags_defaults_and_api_calls_have_same_outcome(self):
        self.compile()
        expected = {'result': 'GO|GO'}
        for argv in [('text', 'repeat', 'go', '-n', '2', '--loud'), ('repeat', 'go', '--count=2', '--loud'),
                     ('text', 'again', 'go', '--loud', '-n', '2')]:
            with self.subTest(argv=argv):
                self.assertEqual(json.loads(self.cli('invoke', self.root, '--', *argv)), expected)
        arguments = {'text': 'go', 'count': 2, 'loud': True}
        for call in [{'type': 'function_call', 'name': 'repeat_text', 'arguments': json.dumps(arguments), 'call_id': 'fixture'},
                     {'type': 'function', 'id': 'fixture', 'function': {'name': 'repeat_text', 'arguments': json.dumps(arguments)}}]:
            self.assertEqual(json.loads(self.cli('invoke', self.root, '--call', '-', call=call)), expected)
        self.assertEqual(json.loads(self.cli('invoke', self.root, '--', 'repeat', 'x')), {'result': 'x'})
        self.assertEqual(json.loads(self.cli('invoke', self.root, '--', 'repeat', 'go', '--loud', '--no-loud')), {'result': 'go'})

    def test_nullable_text_accepts_paths_and_preserves_explicit_null(self):
        self.document['tool']['parameters']['properties']['text'] = {'type': ['string', 'null']}
        self.write_document()
        items = commands.catalog(self.root)
        for raw, expected in [('/repo/path with spaces', '/repo/path with spaces'),
                              ('null', None), ('"null"', 'null'), ('"quoted text"', 'quoted text')]:
            with self.subTest(raw=raw):
                _, payload = commands.cli_payload(items, ['repeat', raw])
                self.assertEqual(payload['text'], expected)
        _, payload = commands.call_payload(items, {'name': 'repeat_text', 'arguments':
            {'text': None, 'count': 1, 'loud': False}})
        self.assertIsNone(payload['text'])

    def test_exports_are_openai_shapes_without_cli_or_binding_extensions(self):
        responses = json.loads(self.cli('commands', self.root, '--format', 'responses'))
        chat = json.loads(self.cli('commands', self.root, '--format', 'chat'))
        target = next(tool for tool in responses if tool['name'] == 'repeat_text')
        self.assertEqual(target, self.document['tool'])
        self.assertEqual(chat, [{'type': 'function', 'function': {k: v for k, v in tool.items() if k != 'type'}} for tool in responses])
        self.assertFalse((self.project / '.tkstack').exists())

    def test_help_group_help_and_builtin_tool_do_not_need_lock_or_write_state(self):
        self.assertIn('text repeat', self.cli('invoke', self.root))
        self.assertIn('text repeat', self.cli('invoke', self.root, '--', 'text'))
        self.assertIn('Repeat text', self.cli('invoke', self.root, '--', 'help', 'repeat'))
        self.assertIn('--count', self.cli('invoke', self.root, '--', 'repeat', '--help'))
        output = self.cli('invoke', self.root, '--call', '-', call={'name': 'help', 'arguments': {'topic': None, 'format': 'text'}})
        self.assertIn('text repeat', json.loads(output)['help'])
        self.assertFalse((self.project / '.tkstack').exists())

    def test_reserved_defaults_are_injected_and_version_uses_declared_metadata(self):
        (self.root / 'SKILL.md').write_text('---\nname: repeat-text\ndescription: Repeat bounded text.\nmetadata:\n  version: "3.2.1"\n---\n# Repeat\n')
        (self.root / 'commands/help.md').unlink()
        (self.root / 'commands/version.md').unlink()
        catalog = commands.catalog(self.root)
        self.assertEqual({item['tool']['name'] for item in catalog}, {'help', 'version', 'repeat_text'})
        for route in [('version',), ('--version',), ('-V',), ('repeat', '--version')]:
            self.assertEqual(self.cli('invoke', self.root, '--', *route), 'repeat-text 3.2.1\n')
        response = self.cli('invoke', self.root, '--call', '-', call={'name': 'version', 'arguments': {}})
        self.assertEqual(json.loads(response), {'name': 'repeat-text', 'version': '3.2.1'})
        self.assertIn('VERSION', self.cli('invoke', self.root, '--', 'version', '--help'))
        self.assertFalse((self.project / '.tkstack').exists())

    def test_console_and_man_help_share_aliases_flags_types_and_api_content(self):
        self.assertEqual(self.cli('invoke', self.root, '--', 'help', '--help'),
                         self.cli('invoke', self.root, '--', 'help', 'help'))
        self.assertEqual(self.cli('invoke', self.root, '--', 'version', '--version'),
                         self.cli('invoke', self.root, '--', 'version'))
        canonical = self.cli('invoke', self.root, '--', 'help', 'text', 'repeat')
        for route in [('help', 'repeat'), ('text', 'repeat', '--help'), ('repeat', '-h')]:
            self.assertEqual(self.cli('invoke', self.root, '--', *route), canonical)
        for fragment in ('SYNOPSIS', 'DESCRIPTION', 'ALIASES', '--count, -n COUNT', 'integer', 'Default: 1', 'TOOL PARAMETERS'):
            self.assertIn(fragment, canonical)
        source = self.cli('invoke', self.root, '--', 'help', 'repeat', '--format', 'man')
        self.assertTrue(source.startswith('.TH "REPEAT\\-TEXT TEXT REPEAT" "1" ""'))
        self.assertIn('.SH SYNOPSIS\n', source)
        self.assertNotIn(str(self.root), source)
        response = json.loads(self.cli('invoke', self.root, '--call', '-', call={
            'name': 'help', 'arguments': {'topic': 'repeat', 'format': 'text'}}))
        self.assertEqual(response['help'], canonical)
        self.assertEqual(response['man'], source)
        response = json.loads(self.cli('invoke', self.root, '--call', '-', call={
            'type': 'function', 'function': {'name': 'help', 'arguments': {'topic': 'text repeat', 'format': 'man'}}}))
        self.assertEqual(response['help'], source)
        self.assertFalse((self.project / '.tkstack').exists())

    def test_rendering_is_stable_across_terminal_environment_and_package_relocation(self):
        (self.root / 'SKILL.md').write_text('---\nname: repeat-text\ndescription: Repeat bounded text.\nmetadata:\n  version: "3.2.1"\n---\n# Repeat\n')
        other = self.project / 'different directory name'
        shutil.copytree(self.root, other)
        results = []
        for root, width, term, locale in [(self.root, '24', 'dumb', 'C'), (other, '240', 'xterm-256color', 'C.UTF-8')]:
            for format in ('text', 'man'):
                process = subprocess.run([sys.executable, str(SCRIPT), 'invoke', str(root), '--', 'help', '--format', format],
                    env={**os.environ, 'COLUMNS': width, 'TERM': term, 'LC_ALL': locale}, text=True, capture_output=True)
                self.assertEqual(process.returncode, 0, process.stderr)
                self.assertNotIn('\x1b', process.stdout)
                results.append(process.stdout)
        self.assertEqual(results[0], results[2])
        self.assertEqual(results[1], results[3])
        self.assertFalse((self.project / '.tkstack').exists())

    def test_legacy_help_signature_remains_readonly_and_gets_manual_rendering(self):
        doc = commands.builtin('help', legacy=True)
        body = doc.pop('body')
        (self.root / 'commands/help.md').write_text('---\n' + yaml.safe_dump(doc, sort_keys=False) + '---\n' + body)
        response = json.loads(self.cli('invoke', self.root, '--call', '-', call={'name': 'help', 'arguments': {'topic': None}}))
        self.assertIn('SYNOPSIS', response['help'])
        self.assertTrue(response['man'].startswith('.TH'))
        self.assertFalse((self.project / '.tkstack').exists())

    def test_reserved_names_routes_aliases_and_flags_cannot_be_hijacked(self):
        original = json.loads(json.dumps(self.document))
        changes = [('tool', 'name', 'help'), ('tool', 'name', 'version'),
                   ('cli', 'path', ['version']), ('cli', 'path', ['help', 'replace']),
                   ('cli', 'aliases', [['version']]), ('cli', 'aliases', [['help']]),
                   ('cli', 'flags', {'count': ['--version']}), ('cli', 'flags', {'count': ['-V']})]
        for section, key, value in changes:
            with self.subTest(key=key, value=value):
                self.document = json.loads(json.dumps(original))
                self.document[section][key] = value
                self.write_document()
                self.cli('commands', self.root, expected=1)
        self.assertFalse((self.project / '.tkstack').exists())

    def test_man_source_escapes_roff_requests_and_console_escapes_terminal_controls(self):
        manual = commands.command_manual
        page = {'name': 'x', 'package': 'x', 'version': '1', 'sections': [('DESCRIPTION', [
            ('paragraph', '.SH injected\n\'request\nback\\slash --flag\n\x1b[31mred')])]}
        source = manual.roff(page)
        self.assertIn('\\&.SH injected', source)
        self.assertIn("\\&'request", source)
        self.assertIn('back\\eslash \\-\\-flag', source)
        self.assertNotIn('\x1b', manual.console(page))

    def test_concurrent_reserved_discovery_never_checks_or_invokes_a_workflow(self):
        requests = [([], None), (['version'], None), (['help', 'repeat', '--format', 'man'], None),
                    ((), {'name': 'version', 'arguments': {}})] * 4
        def discover(request):
            argv, call = request
            return commands.execute(object(), self.root, argv, call=call)
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(discover, requests))
        self.assertEqual(results[:4], results[4:8])
        self.assertEqual(results[:4], results[12:])
        self.assertTrue(all(code == 0 and not error for code, _, error in results))
        self.assertFalse((self.project / '.tkstack').exists())

    def test_builtin_version_validation_rejects_workflow_binding_and_bad_metadata(self):
        version = self.root / 'commands/version.md'
        document = yaml.safe_load(version.read_text().split('---')[1])
        document['tool']['parameters']['properties']['target'] = {'type': 'string'}
        document['tool']['parameters']['required'] = ['target']
        document['cli']['positionals'] = ['target']
        version.write_text('---\n' + yaml.safe_dump(document, sort_keys=False) + '---\n# Version\n')
        self.cli('commands', self.root, expected=1)
        version.unlink()
        (self.root / 'SKILL.md').write_text('---\nname: repeat-text\ndescription: Repeat text.\nmetadata:\n  version: 3\n---\n# Repeat\n')
        self.cli('invoke', self.root, '--', 'version', expected=1)

    def test_invalid_arguments_unknown_commands_and_extra_fields_reject_before_execution(self):
        self.compile()
        shutil.rmtree(self.project / '.tkstack')
        for call in [{'name': 'repeat_text', 'arguments': {'text': 'go', 'count': 2}},
                     {'name': 'repeat_text', 'arguments': {'text': 'go', 'count': 0, 'loud': False}},
                     {'name': 'repeat_text', 'arguments': {'text': 'go', 'count': 1, 'loud': False, 'extra': True}},
                     {'name': 'absent', 'arguments': {}},
                     {'name': 'repeat_text', 'arguments': '{"text":"x","text":"y"}'}]:
            self.cli('invoke', self.root, '--call', '-', call=call, expected=1)
        self.cli('invoke', self.root, '--', 'absent', expected=1)
        self.cli('invoke', self.root, '--', 'repeat', 'x', '--unknown', expected=2)
        self.assertFalse((self.project / '.tkstack').exists())

    def test_signature_body_and_alias_drift_require_explicit_recompile(self):
        self.compile()
        self.document['cli']['aliases'].append(['again'])
        self.write_document()
        self.cli('invoke', self.root, '--', 'again', 'x', expected=1)
        self.compile()
        self.assertEqual(json.loads(self.cli('invoke', self.root, '--', 'again', 'x')), {'result': 'x'})

    def test_unbound_metadata_cannot_invoke_a_lock_built_without_the_definition(self):
        hidden = self.root / 'hidden'
        (self.root / 'commands').rename(hidden)
        self.compile()
        hidden.rename(self.root / 'commands')
        self.assertIn('not bound', self.cli_error('invoke', self.root, '--', 'repeat', 'x'))

    def cli_error(self, *args):
        result = subprocess.run([sys.executable, '-B', str(SCRIPT), *map(str, args)],
            cwd=self.project, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 1)
        return result.stderr

    def test_duplicate_routes_flags_bad_defaults_and_unsafe_artifacts_are_rejected(self):
        original = json.loads(json.dumps(self.document))
        changes = [('cli', 'aliases', [['repeat'], ['repeat']]), ('cli', 'flags', {'count': ['--help']}),
                   ('cli', 'defaults', {'count': 0}), ('run', 'artifact', '../foreign.lock.json')]
        for section, key, value in changes:
            with self.subTest(key=key):
                self.document = json.loads(json.dumps(original))
                self.document[section][key] = value
                self.write_document()
                self.cli('commands', self.root, expected=1)
        self.assertFalse((self.project / '.tkstack').exists())

    def test_yaml_duplicate_keys_aliases_and_unsupported_strict_schema_reject(self):
        valid = self.definition.read_text()
        for front in [valid.replace('schema: tkstack.command/v1', 'schema: tkstack.command/v1\nschema: tkstack.command/v1'),
                      '---\na: &a {x: y}\nb: *a\n---\nBody',
                      '---\n!!python/object/apply:os.system ["touch should-not-exist"]\n---\nBody']:
            self.definition.write_text(front)
            self.cli('commands', self.root, expected=1)
        self.document['tool']['parameters']['required'] = ['text']
        self.write_document()
        self.cli('commands', self.root, expected=1)
        self.assertFalse((self.project / '.tkstack').exists())
        self.assertFalse((self.project / 'should-not-exist').exists())

    def test_symlinked_definitions_and_external_schema_references_reject(self):
        self.definition.rename(self.root / 'outside.md')
        self.definition.symlink_to(self.root / 'outside.md')
        self.cli('commands', self.root, expected=1)
        self.definition.unlink()
        self.document['tool']['parameters']['properties']['text'] = {'$ref': 'https://example.invalid/schema'}
        self.write_document()
        self.cli('commands', self.root, expected=1)
        self.assertFalse((self.project / '.tkstack').exists())

    def test_standalone_generated_runner_and_skillify_frontend_share_dispatch(self):
        self.compile()
        script = self.root / 'scripts/codify.py'
        self.assertEqual(json.loads(self.cli('invoke', self.root, '--', 'repeat', 'é', '--loud', script=script)), {'result': 'É'})
        copied = self.project / 'plugin cache/skillify'
        shutil.copytree(ROOT / 'skills/skillify', copied)
        frontend = copied / 'scripts/skillify.py'
        self.assertEqual(json.loads(self.cli('invoke', self.root, '--', 'repeat', 'go', script=frontend)), {'result': 'go'})
        self.assertEqual(json.loads(self.cli('commands', self.root, '--format', 'responses', script=frontend)), commands.export(self.root))

    def test_parallel_invocations_keep_inputs_and_outputs_isolated(self):
        self.compile()
        def run(value):
            code, out, err = commands.execute(engine, self.root, ['repeat', value, '-n', '2'], project=self.project)
            self.assertEqual((code, err), (0, ''))
            return json.loads(out)['result']
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(list(pool.map(run, ['a', 'b'])), ['a|a', 'b|b'])

    def test_boolean_positional_values_use_json_types(self):
        self.document['cli']['positionals'].append('loud')
        del self.document['cli']['flags']['loud']
        self.write_document()
        self.compile()
        self.assertEqual(json.loads(self.cli('invoke', self.root, '--', 'repeat', 'go', 'true')), {'result': 'GO'})

    def test_missing_dependencies_are_reported_without_implicit_installation(self):
        result = subprocess.run([sys.executable, '-S', '-B', str(SCRIPT), 'commands', str(self.root)],
            cwd=self.project, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 1)
        self.assertIn('pinned PyYAML/jsonschema', result.stderr)
        self.assertFalse((self.project / '.tkstack').exists())

    def test_oversized_definition_is_rejected_before_state_initialization(self):
        self.definition.write_bytes(b'x' * (commands.LIMIT + 1))
        self.cli('commands', self.root, expected=1)
        self.assertFalse((self.project / '.tkstack').exists())


if __name__ == '__main__':
    unittest.main()

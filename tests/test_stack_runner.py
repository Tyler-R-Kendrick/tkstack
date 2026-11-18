import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'src'))
spec = importlib.util.spec_from_file_location('test_stack_runner_cli', ROOT / 'src/tkstack.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class StackRunnerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.workspace = self.base / 'project with spaces'
        self.workspace.mkdir()
        self.scopes = {kind: self.base / kind / '.tkstack' for kind in ('global', 'user')}
        self.scopes['workspace'] = self.workspace / '.tkstack'
        self.environment = {**os.environ, **{'TKSTACK_' + name.upper() + '_DIR': str(path) for name, path in self.scopes.items()}}
        self.env_patch = patch.dict(os.environ, self.environment)
        self.env_patch.start()
        self.addCleanup(self.env_patch.stop)
        self.command = [sys.executable, '-B', str(ROOT / 'src/tkstack.py')]

    def fixture(self, directory=None):
        directory = directory or self.workspace / 'skills/labels'
        shutil.copytree(ROOT / 'skills/learn/skills/codify/examples/normalize-labels', directory,
            ignore=shutil.ignore_patterns('workflow.lock.json'))
        (directory / 'SKILL.md').write_text('---\nname: labels\ndescription: Normalize labels.\n---\nUse the compiled command.\n')
        runner.codify.compile_workflow(directory / 'PROMPT.md', directory / 'scripts/run.py',
            directory / 'cases.json', directory / 'scripts/workflow.lock.json', root=directory, project=self.workspace)
        return directory

    def registry(self, scope, value):
        root = self.scopes[scope]
        root.mkdir(parents=True, exist_ok=True)
        (root / 'runner.json').write_text(json.dumps({'version': 1, **value}))

    def invoke(self, *args, payload=None, expected=0):
        result = subprocess.run([*self.command, *map(str, args)], cwd=self.workspace, env=self.environment,
            input=json.dumps(payload) if payload is not None else None, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return result

    def test_generated_executable_runs_named_skill_workflow_aliases_and_tool_calls(self):
        skill = self.fixture()
        self.registry('workspace', {'workflows': {'labels': str(skill)}})
        for kind in ('skills', 'workflows', 'skill', 'workflow'):
            self.assertEqual(json.loads(self.invoke(kind, 'labels', '--', 'normalize', '-l', '[" b ","a"]').stdout), {'labels': ['a', 'b']})
        call = {'type': 'function_call', 'name': 'normalize_labels', 'arguments': '{"labels":["b","a"]}'}
        self.assertEqual(json.loads(self.invoke('skills', 'labels', '--call', '-', payload=call).stdout), {'labels': ['a', 'b']})
        self.invoke('skills', 'labels', '--', 'normalize', '-l', '["private-payload-example"]')
        trace = self.scopes['workspace'] / 'runs/timing/operations.jsonl'
        entries = [json.loads(line) for line in trace.read_text().splitlines()]
        self.assertTrue(any(row['status'] == 'pass' and row['timeout_seconds'] == 30 and row['elapsed_ms'] >= 0 for row in entries))
        self.assertTrue(all(row['environment']['python'] and row['environment']['platform'] for row in entries))
        self.assertNotIn('private-payload-example', trace.read_text())
        runner.timing.invoke(lambda *args, **kwargs: (0, '', ''), {'artifact_sha256': 'fixture'},
            {'operation': 'private-operation-example'}, self.workspace, 30, None, None, {},
            self.scopes['workspace'], 'skills', 'fixture')
        self.assertNotIn('private-operation-example', trace.read_text())
        tools = json.loads(self.invoke('tools', 'skills', 'labels', '--format', 'chat').stdout)
        self.assertIn('normalize_labels', [item['function']['name'] for item in tools])

    def test_runner_records_a_real_deadline_without_recording_payload(self):
        skill = self.fixture()
        workflow = skill / 'scripts/workflow.py'
        text = workflow.read_text().replace('def execute(payload):',
            'def execute(payload):\n    if payload.get("labels") == ["slow-private"]:\n        import time\n        time.sleep(10)')
        workflow.write_text(text)
        runner.codify.compile_workflow(skill / 'PROMPT.md', skill / 'scripts/run.py',
            skill / 'cases.json', skill / 'scripts/workflow.lock.json', root=skill, project=self.workspace)
        result = self.invoke('skills', 'labels', '--timeout', '1', '--', 'normalize', '-l', '["slow-private"]', expected=1)
        self.assertIn('deadline', result.stderr)
        trace = self.scopes['workspace'] / 'runs/timing/operations.jsonl'
        record = json.loads(trace.read_text().splitlines()[-1])
        self.assertEqual((record['status'], record['timeout_seconds']), ('deadline_or_interrupt', 1))
        self.assertGreaterEqual(record['elapsed_ms'], 500)
        self.assertNotIn('slow-private', trace.read_text())

    def test_direct_lock_reuses_verified_runner_and_rejects_mixed_interfaces(self):
        skill = self.fixture()
        lock = skill / 'scripts/workflow.lock.json'
        self.assertEqual(json.loads(self.invoke('workflows', lock, '--input', '-', payload={'labels': [' b ', 'a']}).stdout), {'labels': ['a', 'b']})
        self.invoke('workflows', lock, '--', 'normalize', expected=1)
        self.invoke('skills', skill, '--input', '-', payload={'labels': []}, expected=1)
        self.invoke('skills', skill, '--call', '-', '--', 'normalize', payload={}, expected=1)

    def test_direct_workflow_payload_cannot_hide_timing(self):
        skill = self.fixture()
        workflow = skill / 'scripts/workflow.py'
        workflow.write_text(workflow.read_text().replace('set(payload) != {"labels"}',
            'set(payload) - {"labels", "operation"} or "labels" not in payload'))
        lock = skill / 'scripts/workflow.lock.json'
        runner.codify.compile_workflow(skill / 'PROMPT.md', skill / 'scripts/run.py',
            skill / 'cases.json', lock, root=skill, project=self.workspace)
        trace = self.scopes['workspace'] / 'runs/timing/operations.jsonl'
        for operation in ('model', 'verify', 'native_plan'):
            with self.subTest(operation=operation):
                result = self.invoke('workflows', lock, '--input', '-', payload={'labels': ['a'], 'operation': operation})
                self.assertEqual(json.loads(result.stdout), {'labels': ['a']})
        contents = trace.read_text() if trace.exists() else ''
        entries = [json.loads(line) for line in contents.splitlines()]
        self.assertEqual([entry['status'] for entry in entries], ['pass'] * 3)
        self.assertNotIn('native_plan', contents)

    def test_help_list_tools_check_and_setup_preview_preserve_all_state_bytes(self):
        self.fixture()
        before = {str(p): p.read_bytes() for p in self.base.rglob('*') if p.is_file()}
        for args in [(), ('help',), ('help', 'skills'), ('list', 'skills'), ('tools', 'skills', 'labels'),
                     ('check', 'skills', 'labels'), ('skills', 'labels', '--', 'normalize', '--help')]:
            self.invoke(*args)
        self.assertEqual(before, {str(p): p.read_bytes() for p in self.base.rglob('*') if p.is_file()})
        self.assertFalse(self.scopes['user'].exists())
        self.assertFalse(self.scopes['global'].exists())

    def test_scope_precedence_and_installed_user_launcher_keep_active_workspace(self):
        skill = self.fixture()
        second = self.fixture(self.workspace / 'other')
        self.registry('global', {'workflows': {'choice': str(second)}})
        self.registry('user', {'workflows': {'choice': str(second)}})
        self.registry('workspace', {'workflows': {'choice': str(skill)}})
        records = json.loads(self.invoke('list', 'workflows').stdout)
        self.assertEqual(next(x for x in records if x['name'] == 'choice')['path'], str(skill))
        self.assertEqual(json.loads(self.invoke('workflows', 'choice', '--', 'normalize', '-l', '["a"]').stdout), {'labels': ['a']})

    def test_uncompiled_unknown_stale_and_invalid_inputs_never_fall_back_to_inference(self):
        skill = self.fixture()
        uncompiled = self.workspace / 'skills/plain'
        uncompiled.mkdir()
        (uncompiled / 'SKILL.md').write_text('---\nname: plain\n---\nDo this with a model.')
        result = self.invoke('skills', 'plain', '--', 'run', expected=1)
        self.assertIn('No inference fallback', result.stderr)
        self.invoke('skills', 'unknown', expected=1)
        self.invoke('skills', 'labels', '--', 'normalize', '-l', '[1]', expected=1)
        self.invoke('skills', 'labels', '--', 'normalize', '--invented', expected=2)
        (skill / 'commands/normalize.md').write_text((skill / 'commands/normalize.md').read_text() + '\nChanged\n')
        self.invoke('skills', 'labels', '--', 'normalize', '-l', '[]', expected=1)

    def test_pure_workflow_ignores_ambient_profiles_and_node_cache_but_rejects_explicit_config(self):
        self.fixture()
        self.registry('workspace', {'dependencies': 'absent-node-modules'})
        self.assertEqual(json.loads(self.invoke('skills', 'labels', '--', 'normalize', '-l', '["a"]').stdout), {'labels': ['a']})
        self.invoke('skills', 'labels', '--config', self.workspace / 'absent.json', '--', 'normalize', '-l', '[]', expected=2)

    def test_invalid_registry_and_oversized_stdin_fail_without_workspace_initialization(self):
        self.registry('workspace', {'version': True})
        self.invoke('list', expected=1)
        self.registry('workspace', {})
        result = subprocess.run([*self.command, 'workflows', 'normalize-labels', '--call', '-'],
            cwd=self.workspace, env=self.environment, input='{}' + ' ' * (1024 * 1024),
            capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 1)
        self.assertIn('exceeds 1 MiB', result.stderr)
        self.assertFalse((self.scopes['workspace'] / 'sessions').exists())

    def test_explicit_project_overrides_ambient_workspace_without_modifying_other_roots(self):
        skill = self.fixture()
        other = self.base / 'other project'
        other.mkdir()
        self.environment['TKSTACK_WORKSPACE_DIR'] = str(other / '.tkstack')
        result = self.invoke('--project', self.workspace, 'skills', 'labels', '--', 'normalize', '-l', '["a"]')
        self.assertEqual(json.loads(result.stdout), {'labels': ['a']})
        self.assertFalse((other / '.tkstack').exists())

    def test_separate_model_profiles_are_rejected_before_execution(self):
        lock = {'inference': {'mode': 'explicit', 'profiles': ['other']}}
        with self.assertRaisesRegex(ValueError, 'invoking agent'):
            runner.configuration(lock, None, self.scopes, {}, self.environment)
        self.assertIsNone(runner.configuration({'inference': {'mode': 'none', 'profiles': []}},
                                                None, self.scopes, {}, self.environment))


if __name__ == '__main__':
    unittest.main()

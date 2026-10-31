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
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
import runner_install
spec = importlib.util.spec_from_file_location('test_stack_runner_cli', ROOT / 'scripts/tkstack.py')
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
        self.executable = self.scopes['workspace'] / 'tkstack'

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

    def invoke(self, *args, payload=None, expected=0, executable=None):
        command = [str(executable or self.executable), *map(str, args)]
        result = subprocess.run(command, cwd=self.workspace, env=self.environment,
            input=json.dumps(payload) if payload is not None else None, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return result

    def install(self, scope='workspace'):
        return runner_install.publish(ROOT, self.scopes[scope])

    def test_generated_executable_runs_named_skill_workflow_aliases_and_tool_calls(self):
        skill = self.fixture()
        self.registry('workspace', {'workflows': {'labels': str(skill)}})
        self.install()
        for kind in ('skills', 'workflows', 'skill', 'workflow'):
            self.assertEqual(json.loads(self.invoke(kind, 'labels', '--', 'normalize', '-l', '[" b ","a"]').stdout), {'labels': ['a', 'b']})
        call = {'type': 'function_call', 'name': 'normalize_labels', 'arguments': '{"labels":["b","a"]}'}
        self.assertEqual(json.loads(self.invoke('skills', 'labels', '--call', '-', payload=call).stdout), {'labels': ['a', 'b']})
        tools = json.loads(self.invoke('tools', 'skills', 'labels', '--format', 'chat').stdout)
        self.assertIn('normalize_labels', [item['function']['name'] for item in tools])

    def test_direct_lock_reuses_verified_runner_and_rejects_mixed_interfaces(self):
        skill = self.fixture()
        self.install()
        lock = skill / 'scripts/workflow.lock.json'
        self.assertEqual(json.loads(self.invoke('workflows', lock, '--input', '-', payload={'labels': [' b ', 'a']}).stdout), {'labels': ['a', 'b']})
        self.invoke('workflows', lock, '--', 'normalize', expected=1)
        self.invoke('skills', skill, '--input', '-', payload={'labels': []}, expected=1)
        self.invoke('skills', skill, '--call', '-', '--', 'normalize', payload={}, expected=1)

    def test_help_list_tools_check_and_setup_preview_preserve_all_state_bytes(self):
        self.fixture()
        self.install()
        before = {str(p): p.read_bytes() for p in self.base.rglob('*') if p.is_file()}
        for args in [(), ('help',), ('help', 'skills'), ('list', 'skills'), ('tools', 'skills', 'labels'),
                     ('check', 'skills', 'labels'), ('skills', 'labels', '--', 'normalize', '--help')]:
            self.invoke(*args)
        runner_install.check(ROOT, self.scopes['workspace'])
        self.assertEqual(before, {str(p): p.read_bytes() for p in self.base.rglob('*') if p.is_file()})
        self.assertFalse(self.scopes['user'].exists())
        self.assertFalse(self.scopes['global'].exists())

    def test_scope_precedence_and_installed_user_launcher_keep_active_workspace(self):
        skill = self.fixture()
        second = self.fixture(self.workspace / 'other')
        self.registry('global', {'workflows': {'choice': str(second)}})
        self.registry('user', {'workflows': {'choice': str(second)}})
        self.registry('workspace', {'workflows': {'choice': str(skill)}})
        exe = self.install('user')
        records = json.loads(self.invoke('list', 'workflows', executable=exe).stdout)
        self.assertEqual(next(x for x in records if x['name'] == 'choice')['path'], str(skill))
        self.assertEqual(json.loads(self.invoke('workflows', 'choice', '--', 'normalize', '-l', '["a"]', executable=exe).stdout), {'labels': ['a']})

    def test_uncompiled_unknown_stale_and_invalid_inputs_never_fall_back_to_inference(self):
        skill = self.fixture()
        self.install()
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
        self.registry('workspace', {'config': 'does-not-exist.json', 'dependencies': 'absent-node-modules'})
        self.install()
        self.assertEqual(json.loads(self.invoke('skills', 'labels', '--', 'normalize', '-l', '["a"]').stdout), {'labels': ['a']})
        self.invoke('skills', 'labels', '--config', self.workspace / 'absent.json', '--', 'normalize', '-l', '[]', expected=1)

    def test_foreign_modified_and_symlinked_executables_are_preserved(self):
        root = self.scopes['workspace']
        root.mkdir()
        self.executable.write_text('user-owned command')
        with self.assertRaisesRegex(ValueError, 'foreign'):
            self.install()
        self.assertEqual(self.executable.read_text(), 'user-owned command')
        self.executable.unlink()
        self.install()
        self.executable.write_text('modified command')
        with self.assertRaisesRegex(ValueError, 'modified'):
            self.install()
        self.executable.unlink()
        self.executable.symlink_to(ROOT / 'install.sh')
        with self.assertRaisesRegex(ValueError, 'symlink'):
            self.install()

    def test_repeated_and_parallel_setup_publish_identical_owned_executables(self):
        self.install()
        before = self.executable.read_bytes()
        with ThreadPoolExecutor(max_workers=2) as pool:
            result = list(pool.map(lambda _: self.install(), range(2)))
        self.assertEqual(result, [self.executable, self.executable])
        self.assertEqual(self.executable.read_bytes(), before)
        self.assertEqual(self.executable.stat().st_mode & 0o777, 0o755)
        runner_install.check(ROOT, self.scopes['workspace'])

    def test_launcher_quotes_source_paths_with_newlines_and_shell_metacharacters(self):
        source = self.base / "source\nfalse # ' $(false)"
        (source / 'scripts').mkdir(parents=True)
        (source / 'scripts/tkstack.py').write_text("print('quoted source executed')\n")
        executable = runner_install.publish(source, self.scopes['workspace'])
        result = self.invoke(executable=executable)
        self.assertEqual(result.stdout.strip(), 'quoted source executed')

    def test_explicit_user_global_setup_and_preview_honor_scoped_roots(self):
        command = [sys.executable, '-B', str(ROOT / 'scripts/runner_install.py')]
        for scope in ('user', 'global'):
            preview = subprocess.run([*command, '--scope', scope, '--dry-run'], env=self.environment, capture_output=True, text=True)
            self.assertEqual(preview.returncode, 0, preview.stderr)
            self.assertEqual(json.loads(preview.stdout)['status'], 'planned')
            self.assertFalse(self.scopes[scope].exists())
            install = subprocess.run([*command, '--scope', scope], env=self.environment, capture_output=True, text=True)
            self.assertEqual(install.returncode, 0, install.stderr)
            self.invoke('help', executable=self.scopes[scope] / 'tkstack')

    def test_invalid_registry_and_oversized_stdin_fail_without_workspace_initialization(self):
        self.install()
        self.registry('workspace', {'version': True})
        self.invoke('list', expected=1)
        self.registry('workspace', {})
        result = subprocess.run([str(self.executable), 'workflows', 'normalize-labels', '--call', '-'],
            cwd=self.workspace, env=self.environment, input='{}' + ' ' * (1024 * 1024),
            capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 1)
        self.assertIn('exceeds 1 MiB', result.stderr)
        self.assertFalse((self.scopes['workspace'] / 'sessions').exists())

    def test_explicit_project_overrides_ambient_workspace_without_modifying_other_roots(self):
        skill = self.fixture()
        self.install()
        other = self.base / 'other project'
        other.mkdir()
        self.environment['TKSTACK_WORKSPACE_DIR'] = str(other / '.tkstack')
        result = self.invoke('--project', self.workspace, 'skills', 'labels', '--', 'normalize', '-l', '["a"]')
        self.assertEqual(json.loads(result.stdout), {'labels': ['a']})
        self.assertFalse((other / '.tkstack').exists())

    def test_config_selection_projects_declared_profiles_without_mutating_source(self):
        profiles = {'version': 1, 'providers': {'api': {'kind': 'openai', 'apiKeyEnv': 'KEY'}, 'unused': {'kind': 'gateway', 'apiKeyEnv': 'OTHER'}},
            'profiles': {'selected': {'kind': 'language', 'provider': 'api', 'api': 'responses', 'model': 'chosen'}, 'unused': {'kind': 'language', 'provider': 'unused', 'api': 'gateway', 'model': 'other'}}}
        path = self.scopes['user'] / 'profiles.json'
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps(profiles))
        before = path.read_bytes()
        lock = {'inference': {'mode': 'explicit', 'profiles': ['selected']}}
        actual = runner.configuration(lock, None, self.scopes, {}, self.environment)
        self.assertEqual(list(actual['profiles']), ['selected'])
        self.assertEqual(list(actual['providers']), ['api'])
        self.assertEqual(actual['profiles']['selected']['model'], 'chosen')
        self.assertEqual(path.read_bytes(), before)
        local = self.scopes['workspace'] / 'profiles.json'
        local.parent.mkdir(parents=True, exist_ok=True)
        profiles['profiles']['selected']['model'] = 'workspace-model'
        local.write_text(json.dumps(profiles))
        actual = runner.configuration(lock, None, self.scopes, {'config': path, 'config_scope': 'user'}, self.environment)
        self.assertEqual(actual['profiles']['selected']['model'], 'workspace-model')
        with self.assertRaisesRegex(ValueError, 'missing declared profiles'):
            runner.configuration({'inference': {'mode': 'explicit', 'profiles': ['missing']}}, path, self.scopes, {}, self.environment)

    @unittest.skipUnless(os.environ.get('TKSTACK_AI_SDK_DEPENDENCIES'), 'Native SDK dependencies optional')
    def test_native_sdk_honors_selected_provider_model_and_workspace_without_model_calls(self):
        dependencies = Path(os.environ['TKSTACK_AI_SDK_DEPENDENCIES'])
        package = self.workspace / 'workflows/profile-contract'
        source = self.workspace / 'profile-prompt.md'
        source.write_text('Report configured profile metadata and normalize labels; perform no model calls.')
        runner.codify.scaffold(source, package, 'ai-sdk')
        (package / 'scripts/workflow.ts').write_text('''import { z } from 'zod';
import { readFile } from 'node:fs/promises';
export const inputSchema = z.object({labels: z.array(z.string())}).strict();
export const outputSchema = z.object({labels: z.array(z.string()), model: z.string(), provider: z.string(), profiles: z.array(z.string()), workspace: z.string()}).strict();
export type Inference = unknown;
export async function execute(input: z.infer<typeof inputSchema>, _inference: Inference) {
  const config = JSON.parse(await readFile(process.argv[process.argv.indexOf('--config') + 1], 'utf8'));
  const profile = config.profiles.rewrite;
  return {labels: [...new Set(input.labels)].sort(), model: profile.model, provider: config.providers[profile.provider].kind, profiles: Object.keys(config.profiles), workspace: process.env.TKSTACK_WORKSPACE_DIR!};
}
''')
        (package / 'commands/run.md').write_bytes((ROOT / 'skills/learn/skills/codify/examples/normalize-labels/commands/normalize.md').read_bytes())
        config = {'version': 1, 'providers': {'api': {'kind': 'openai', 'apiKeyEnv': 'NOT_CALLED_KEY'}},
            'profiles': {'rewrite': {'kind': 'language', 'provider': 'api', 'api': 'responses', 'model': 'baseline-model'}}}
        compile_config = self.workspace / 'compile-profiles.json'
        compile_config.write_text(json.dumps(config))
        output = {'labels': ['a', 'b'], 'model': 'baseline-model', 'provider': 'openai', 'profiles': ['rewrite'], 'workspace': str(self.scopes['workspace'])}
        (package / 'cases.json').write_text(json.dumps({'version': 1, 'cases': [
            {'id': 'positive', 'input': {'labels': ['b', 'a']}, 'exit': 0, 'output': output},
            {'id': 'negative', 'input': {'labels': [1]}, 'exit': 1}]}))
        runner.codify.compile_workflow(package / 'PROMPT.md', package / 'scripts/run.ts', package / 'cases.json',
            package / 'scripts/workflow.lock.json', root=package, profiles=['rewrite'], dependencies=dependencies,
            config=compile_config, project=self.workspace)
        config['providers']['api']['kind'] = 'gateway'
        config['providers']['unused'] = {'kind': 'openai', 'apiKeyEnv': 'ALSO_NOT_CALLED'}
        config['profiles']['rewrite'].update({'model': 'workspace-model', 'api': 'gateway'})
        config['profiles']['unrelated'] = {'kind': 'language', 'provider': 'unused', 'api': 'responses', 'model': 'unused-model'}
        (self.scopes['workspace'] / 'profiles.json').write_text(json.dumps(config))
        self.registry('workspace', {'dependencies': str(dependencies)})
        self.install()
        actual = json.loads(self.invoke('workflows', 'profile-contract', '--', 'normalize', '-l', '["b","a"]').stdout)
        self.assertEqual(actual, {**output, 'model': 'workspace-model', 'provider': 'gateway'})
        config['profiles']['rewrite']['api'] = 'chat'  # The native schema rejects this gateway mismatch.
        (self.scopes['workspace'] / 'profiles.json').write_text(json.dumps(config))
        self.invoke('workflows', 'profile-contract', '--', 'normalize', '-l', '[]', expected=1)


if __name__ == '__main__':
    unittest.main()

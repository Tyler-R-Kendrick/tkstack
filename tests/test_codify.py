"""Public compilation, locked execution, invalidation, and standalone reuse contracts."""
from concurrent.futures import ThreadPoolExecutor
import base64
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
SPEC = importlib.util.spec_from_file_location('codify_test_engine', ROOT / 'skills/learn/skills/codify/scripts/codify.py')
codify = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(codify)


class CodifyTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        (self.root / '.git').mkdir()
        self.source = self.root / 'Normalize.md'
        self.source.write_text('Trim labels, remove duplicates, and sort by Unicode code point. Reject non-text labels.\n')
        self.scripts = self.root / 'scripts'
        self.scripts.mkdir()
        (self.scripts / 'json_contract.py').write_bytes((ROOT / 'skills/learn/skills/codify/scripts/json_contract.py').read_bytes())
        self.entry = self.scripts / 'run.py'
        self.entry.write_bytes((ROOT / 'skills/learn/skills/codify/templates/python/run.py').read_bytes())
        (self.scripts / 'workflow.py').write_text('''def execute(payload):
    if set(payload) != {'labels'} or not isinstance(payload['labels'], list) or any(not isinstance(x, str) for x in payload['labels']):
        raise ValueError('Expected text labels')
    return {'labels': sorted(set(x.strip() for x in payload['labels']))}
''')
        self.cases = self.root / 'cases.json'
        self.cases.write_text(json.dumps({'version': 1, 'cases': [
            {'id': 'normalize', 'input': {'labels': [' b ', 'a', 'a']}, 'exit': 0, 'output': {'labels': ['a', 'b']}},
            {'id': 'empty', 'input': {'labels': []}, 'exit': 0, 'output': {'labels': []}},
            {'id': 'reject', 'input': {'labels': [1]}, 'exit': 1}]}))
        self.output = self.scripts / 'workflow.lock.json'

    def compile(self, **kwargs):
        return codify.compile_workflow(self.source, self.entry, self.cases, self.output, self.root, project=self.root, **kwargs)

    def cli(self, *args, payload=None, executable=None):
        return subprocess.run([sys.executable, str(executable or ROOT / 'skills/learn/skills/codify/scripts/codify.py'), *map(str, args)],
                              input=json.dumps(payload) if payload is not None else None, capture_output=True, text=True, cwd=self.root)

    def test_compilation_replays_cached_code_without_a_provider_and_is_byte_reproducible(self):
        result = self.compile()
        self.assertEqual(result['inference'], {'mode': 'none', 'profiles': []})
        before = self.output.read_bytes()
        self.assertEqual(self.compile()['artifact_sha256'], result['artifact_sha256'])
        self.assertEqual(self.output.read_bytes(), before)
        for labels in ([' z ', 'a', 'a'], ['😀', 'é', 'quote"', '\n x \t'], []):
            run = self.cli('run', self.output, '--input', '-', payload={'labels': labels})
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertEqual(json.loads(run.stdout), {'labels': sorted(set(x.strip() for x in labels))})
        self.assertTrue((self.root / '.tkstack/.gitignore').is_file())
        self.assertEqual(list((self.root / '.tkstack/sessions').iterdir()), [])
        self.assertFalse((self.scripts / '__pycache__').exists())

    def test_preview_and_check_are_read_only_and_drafts_cannot_compile(self):
        self.assertEqual(self.compile(dry_run=True)['status'], 'planned')
        self.assertFalse((self.root / '.tkstack').exists())
        self.assertFalse(self.output.exists())
        self.compile()
        shutil.rmtree(self.root / '.tkstack')
        before = self.output.read_bytes()
        self.assertEqual(self.cli('check', self.output).returncode, 0)
        self.assertFalse((self.root / '.tkstack').exists())
        self.assertEqual(self.output.read_bytes(), before)
        (self.scripts / 'workflow.py').write_text("raise NotImplementedError('WORKFLOW_NOT_IMPLEMENTED')")
        with self.assertRaisesRegex(ValueError, 'Implement'):
            self.compile()
        self.assertEqual(self.output.read_bytes(), before)

    def test_unimplemented_templates_can_ship_as_resources_but_not_as_the_entry_workflow(self):
        template = self.root / 'templates/python/workflow.py'
        template.parent.mkdir(parents=True)
        template.write_text("raise NotImplementedError('WORKFLOW_NOT_IMPLEMENTED')")
        result = self.compile(includes=[self.root / 'templates'])
        self.assertEqual(result['status'], 'compiled')
        self.assertIn('templates/python/workflow.py', codify.check(self.output)['files'])
        (self.scripts / 'workflow.py').write_bytes(template.read_bytes())
        with self.assertRaisesRegex(ValueError, 'Implement'):
            self.compile(includes=[self.root / 'templates'])

    def test_stale_prompt_code_and_cases_fail_before_state_or_execution(self):
        self.compile()
        for path in (self.source, self.scripts / 'workflow.py', self.cases):
            original = path.read_bytes()
            path.write_bytes(original + b'\n')
            shutil.rmtree(self.root / '.tkstack', ignore_errors=True)
            run = self.cli('run', self.output, '--input', '-', payload={'labels': ['a']})
            self.assertEqual(run.returncode, 1)
            self.assertIn('Stale', run.stderr)
            self.assertFalse((self.root / '.tkstack').exists())
            path.write_bytes(original)

    def test_bad_contract_cannot_replace_a_previous_artifact(self):
        self.compile()
        before = self.output.read_bytes()
        cases = json.loads(self.cases.read_text())
        cases['cases'][0]['output'] = {'labels': ['invented']}
        self.cases.write_text(json.dumps(cases))
        with self.assertRaisesRegex(ValueError, 'output mismatch'):
            self.compile()
        self.assertEqual(self.output.read_bytes(), before)
        self.assertEqual(list((self.root / '.tkstack/locks/codify').iterdir()) if (self.root / '.tkstack/locks/codify').exists() else [], [])

    def test_snapshot_is_the_executable_even_if_live_workflow_changes_after_validation(self):
        self.compile()
        lock = codify.check(self.output)
        (self.scripts / 'workflow.py').write_text("raise RuntimeError('live code must not run')")
        code, out, _ = codify.invoke(lock, {'labels': ['b', 'a']}, self.root)
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out), {'labels': ['a', 'b']})

    def test_corrupt_and_path_traversal_artifacts_are_rejected(self):
        self.compile()
        before = self.output.read_bytes()
        lock = json.loads(before)
        lock['files']['scripts/workflow.py']['base64'] = base64.b64encode(b'changed').decode()
        with self.assertRaisesRegex(ValueError, 'digest'):
            codify.validate_lock(lock)
        lock = json.loads(before)
        lock['files']['../escape.py'] = lock['files'].pop('scripts/workflow.py')
        lock['artifact_sha256'] = codify.digest(codify.canonical({k: v for k, v in lock.items() if k != 'artifact_sha256'}))
        with self.assertRaisesRegex(ValueError, 'Unsafe'):
            codify.validate_lock(lock)
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            codify.parse_json('{"x":1,"x":2}')

    def test_external_and_symlinked_inputs_are_rejected_before_execution(self):
        (self.scripts / 'foreign.py').symlink_to(self.source)
        with self.assertRaisesRegex(ValueError, 'Symlinked'):
            self.compile()
        self.assertFalse(self.output.exists())
        self.assertFalse((self.root / '.tkstack').exists())

    def test_concurrent_builds_publish_one_complete_identical_artifact(self):
        def build(_):
            try:
                return self.compile()['status']
            except (FileExistsError, ValueError):
                return 'collision'
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(build, range(2)))
        self.assertIn('compiled', results)
        self.assertEqual(codify.check(self.output)['format'], codify.FORMAT)
        self.assertEqual(list((self.root / '.tkstack/locks/codify').iterdir()), [])

    def test_input_drift_during_verification_does_not_publish(self):
        actual = codify.invoke
        def mutate(*args, **kwargs):
            result = actual(*args, **kwargs)
            self.source.write_text('Changed while compiling')
            return result
        with patch.object(codify, 'invoke', side_effect=mutate):
            with self.assertRaisesRegex(ValueError, 'changed during verification'):
                self.compile(jobs=1)
        self.assertFalse(self.output.exists())

    def test_standalone_codify_and_skillify_copy_have_no_original_repository_dependency(self):
        for name in ('codify', 'skillify'):
            copy = self.root / 'plugin cache' / name
            shutil.copytree(ROOT / 'skills/learn/skills' / name, copy)
            command = copy / 'scripts' / (name + '.py')
            result = self.cli('--help', executable=command)
            self.assertEqual(result.returncode, 0, result.stderr)
        result = self.cli('compile', self.source, '--entrypoint', self.entry, '--cases', self.cases,
                          '--output', self.output, executable=self.root / 'plugin cache/codify/scripts/codify.py')
        self.assertEqual(result.returncode, 0, result.stderr)
        result = self.cli('run', self.output, '--input', '-', payload={'labels': ['b', 'a']},
                          executable=self.root / 'plugin cache/skillify/scripts/codify_runtime/scripts/codify.py')
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_explicit_profiles_cannot_be_added_to_a_no_inference_lock(self):
        self.compile()
        config = self.root / 'profiles.json'
        config.write_text('{"version":1,"providers":{},"profiles":{}}')
        result = self.cli('run', self.output, '--input', '-', '--config', config, payload={'labels': []})
        self.assertEqual(result.returncode, 1)
        self.assertIn('declares no inference', result.stderr)

    def test_deadline_terminates_execution_and_removes_private_run(self):
        self.compile()
        lock = codify.check(self.output)
        data = b'while True: pass\n'
        lock['files']['scripts/run.py'] = {'sha256': codify.digest(data), 'mode': 0o644, 'base64': base64.b64encode(data).decode()}
        with self.assertRaisesRegex(ValueError, 'deadline exceeded'):
            codify.invoke(lock, {}, self.root, timeout=1)
        self.assertEqual(list((self.root / '.tkstack/sessions').iterdir()), [])

    def test_private_checkout_permissions_do_not_hide_executable_drift(self):
        self.compile()
        self.entry.chmod(0o600)
        self.assertEqual(codify.check(self.output)['files']['scripts/run.py']['mode'], 0o644)
        self.entry.chmod(0o700)
        with self.assertRaisesRegex(ValueError, 'Stale workflow input'):
            codify.check(self.output)

    def test_relocating_source_tree_preserves_freshness_and_executable_file_modes(self):
        helper = self.scripts / 'native-helper'
        helper.write_text('#!/bin/sh\nprintf native-helper')
        helper.chmod(0o755)
        self.compile()
        lock = codify.check(self.output)
        self.assertEqual(lock['files']['scripts/native-helper']['mode'], 0o755)
        destination = self.root.parent / (self.root.name + '-relocated')
        self.addCleanup(shutil.rmtree, destination, True)
        shutil.copytree(self.root, destination, ignore=shutil.ignore_patterns('.tkstack'))
        moved = destination / 'scripts/workflow.lock.json'
        self.assertEqual(codify.check(moved)['artifact_sha256'], lock['artifact_sha256'])
        helper.chmod(0o644)
        with self.assertRaisesRegex(ValueError, 'Stale workflow input'):
            codify.check(self.output)

    def test_skillify_compilation_uses_the_same_engine_and_keeps_the_package_standalone(self):
        spec = importlib.util.spec_from_file_location('codify_skillify_integration', ROOT / 'skills/learn/skills/skillify/scripts/skillify.py')
        skillify = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(skillify)
        target = self.root / 'skills/normalize-labels'
        skillify.scaffold(target, target.name, 'Normalize text labels.')
        shutil.copy2(self.scripts / 'workflow.py', target / 'scripts/workflow.py')
        shutil.copy2(self.cases, target / 'cases.json')
        (target / 'commands/run.md').write_bytes((ROOT / 'skills/learn/skills/codify/examples/normalize-labels/commands/normalize.md').read_bytes())
        for path in [target / 'SKILL.md', *(target / 'references').glob('*.md')]:
            path.write_text(path.read_text().replace('TODO(SKILLIFY):', 'Completed:'))
        compiled = skillify.compile_skill(target, target / 'cases.json')
        artifact = target / 'scripts/workflow.lock.json'
        self.assertEqual(compiled['status'], 'compiled')
        result = self.cli('run', artifact, '--input', '-', payload={'labels': ['b', 'a']})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {'labels': ['a', 'b']})

    @unittest.skipUnless(os.environ.get('TKSTACK_AI_SDK_DEPENDENCIES'), 'Native SDK dependencies optional')
    def test_native_ai_sdk_artifact_executes_with_locked_external_dependencies(self):
        target = self.root / 'sdk'
        codify.scaffold(self.source, target, 'ai-sdk')
        (target / 'scripts/workflow.ts').write_text('''import { z } from 'zod';
export const inputSchema = z.object({labels: z.array(z.string())}).strict();
export const outputSchema = inputSchema;
export type Inference = unknown;
export async function execute(input: z.infer<typeof inputSchema>, _inference: Inference) {
  return {labels: [...new Set(input.labels.map(x => x.trim()))].sort()};
}
''')
        shutil.copy2(self.cases, target / 'cases.json')
        deps = Path(os.environ['TKSTACK_AI_SDK_DEPENDENCIES'])
        artifact = target / 'scripts/workflow.lock.json'
        codify.compile_workflow(target / 'PROMPT.md', target / 'scripts/run.ts', target / 'cases.json', artifact,
                                root=target, dependencies=deps, project=self.root)
        run = self.cli('run', artifact, '--dependencies', deps, '--input', '-', payload={'labels': ['z', 'a']})
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(json.loads(run.stdout), {'labels': ['a', 'z']})


if __name__ == '__main__':
    unittest.main()

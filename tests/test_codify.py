"""Public compilation, locked execution, invalidation, and standalone reuse contracts."""
from concurrent.futures import ThreadPoolExecutor
import base64
import importlib.util
import json
import os
from pathlib import Path
import signal
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
import zlib
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
        (self.scripts / 'lock-runtime.json').write_text(json.dumps({'version': 1, 'files': ['scripts/json_contract.py', 'scripts/workflow.py']}))

    def compile(self, **kwargs):
        return codify.compile_workflow(self.source, self.entry, self.cases, self.output, self.root, project=self.root, **kwargs)

    def cli(self, *args, payload=None, executable=None):
        return subprocess.run([sys.executable, str(executable or ROOT / 'skills/learn/skills/codify/scripts/codify.py'), *map(str, args)],
                              input=json.dumps(payload) if payload is not None else None, capture_output=True, text=True, cwd=self.root)

    def test_compilation_replays_cached_code_without_a_provider_and_is_byte_reproducible(self):
        result = self.compile()
        self.assertEqual(result['inference'], {'mode': 'none', 'profiles': []})
        self.assertEqual(json.loads(self.output.read_text())['includes'], [])
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

    def test_contract_package_compiles_its_default_inventory_and_rejects_drift(self):
        (self.scripts / 'contract.json').write_text('{}')
        (self.scripts / 'lock-runtime.json').write_text(json.dumps({'version': 1, 'files': ['scripts/contract.json', 'scripts/json_contract.py', 'scripts/workflow.py']}))
        reference = self.root / 'references/guide.md'
        reference.parent.mkdir()
        reference.write_text('Stable behavioral contract.')
        self.compile(includes=[reference])
        artifact = codify.check(self.output)
        self.assertIn('references/guide.md', artifact['files'])
        reference.write_text('Changed behavioral contract.')
        with self.assertRaisesRegex(ValueError, 'Stale'):
            codify.check(self.output)

    def test_explicit_runtime_inventory_limits_snapshot_and_detects_missing_dependencies(self):
        (self.scripts / 'contract.json').write_text('{}')
        manifest = self.scripts / 'lock-runtime.json'
        dependencies = ['scripts/contract.json', 'scripts/json_contract.py', 'scripts/workflow.py']
        manifest.write_text(json.dumps({'version': 1, 'files': dependencies}))
        guide = self.root / 'references/guide.md'
        guide.parent.mkdir()
        guide.write_text('Agent-facing guidance, not executable data.')
        self.compile()
        lock = codify.check(self.output)
        self.assertEqual(lock['format'], 'tkstack.codify/v3')
        self.assertNotIn('references/guide.md', lock['files'])
        self.assertIn('scripts/workflow.py', lock['files'])
        incomplete = json.loads(json.dumps(lock))
        del incomplete['files']['scripts/workflow.py']
        incomplete['artifact_sha256'] = codify.digest(codify.canonical({k: v for k, v in incomplete.items() if k != 'artifact_sha256'}))
        with self.assertRaisesRegex(ValueError, 'missing artifact'):
            codify.validate_lock(incomplete)
        guide.write_text('Changed guidance.')
        codify.check(self.output)
        workflow = self.scripts / 'workflow.py'
        original = workflow.read_bytes()
        workflow.write_bytes(original + b'\n')
        with self.assertRaisesRegex(ValueError, 'Stale'):
            codify.check(self.output)
        workflow.write_bytes(original)
        manifest.write_text(json.dumps({'version': 1, 'files': ['scripts/contract.json', 'scripts/json_contract.py']}))
        with self.assertRaisesRegex(ValueError, 'Stale'):
            codify.check(self.output)
        before = self.output.read_bytes()
        with self.assertRaisesRegex(ValueError, 'missing local import'):
            self.compile()
        self.assertEqual(self.output.read_bytes(), before)
        manifest.write_text(json.dumps({'version': 1, 'files': ['../escape']}))
        with self.assertRaisesRegex(ValueError, 'Unsafe'):
            self.compile()

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
        result = self.compile(includes=[template])
        self.assertEqual(result['status'], 'compiled')
        self.assertIn('templates/python/workflow.py', codify.check(self.output)['files'])
        (self.scripts / 'workflow.py').write_bytes(template.read_bytes())
        with self.assertRaisesRegex(ValueError, 'Implement'):
            self.compile(includes=[template])

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

    def test_compressed_snapshots_preserve_execution_legacy_compatibility_and_limits(self):
        resource = self.scripts / 'repeated.txt'
        resource.write_bytes(b'representative frozen data\n' * 2000)
        manifest = self.scripts / 'lock-runtime.json'
        manifest.write_text(json.dumps({'version': 1, 'files': ['scripts/json_contract.py', 'scripts/repeated.txt', 'scripts/workflow.py']}))
        self.compile()
        lock = codify.check(self.output)
        self.assertEqual(lock['format'], 'tkstack.codify/v3')
        self.assertEqual(lock['files']['scripts/repeated.txt']['encoding'], 'zlib')
        self.assertEqual(codify.decode_files(lock)['scripts/repeated.txt'], resource.read_bytes())
        run = self.cli('run', self.output, '--input', '-', payload={'labels': [' b ', 'a']})
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(json.loads(run.stdout), {'labels': ['a', 'b']})
        legacy = json.loads(self.output.read_text())
        legacy['format'] = 'tkstack.codify/v1'
        legacy.pop('runtime_manifest')
        for item in legacy['files'].values():
            if item.pop('encoding', None) == 'zlib':
                item['base64'] = base64.b64encode(zlib.decompress(base64.b64decode(item['base64']))).decode()
        legacy['artifact_sha256'] = codify.digest(codify.canonical({k: v for k, v in legacy.items() if k != 'artifact_sha256'}))
        self.output.write_bytes(codify.canonical(legacy) + b'\n')
        self.assertEqual(codify.check(self.output)['format'], 'tkstack.codify/v1')
        for compressed in (zlib.compress(b'x' * (codify.LIMIT // 4 * 3 + 1)), zlib.compress(resource.read_bytes()) + b'trailing', b'broken'):
            bad = json.loads(json.dumps(lock))
            bad['files']['scripts/repeated.txt']['base64'] = base64.b64encode(compressed).decode()
            bad['artifact_sha256'] = codify.digest(codify.canonical({k: v for k, v in bad.items() if k != 'artifact_sha256'}))
            with self.assertRaisesRegex(ValueError, 'encoding'):
                codify.validate_lock(bad)

    def test_external_and_symlinked_inputs_are_rejected_before_execution(self):
        (self.scripts / 'foreign.py').symlink_to(self.source)
        with self.assertRaisesRegex(ValueError, 'Symlinked'):
            self.compile(includes=[self.scripts / 'foreign.py'])
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
        self.assertEqual(codify.check(self.output)['format'], codify.SCOPED_FORMAT)
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
        self.assertEqual(result.returncode, 2)
        self.assertIn('unrecognized arguments', result.stderr)

    def test_deadline_terminates_execution_and_removes_private_run(self):
        self.compile()
        lock = codify.check(self.output)
        data = b'while True: pass\n'
        lock['files']['scripts/run.py'] = {'sha256': codify.digest(data), 'mode': 0o644, 'base64': base64.b64encode(data).decode()}
        with self.assertRaisesRegex(ValueError, 'deadline exceeded'):
            codify.invoke(lock, {}, self.root, timeout=1)
        self.assertEqual(list((self.root / '.tkstack/sessions').iterdir()), [])
        if os.name != 'posix':
            return
        old = signal.signal(signal.SIGCHLD, signal.SIG_IGN)
        try:
            with patch.object(os, 'killpg') as killed, self.assertRaisesRegex(ValueError, 'non-reaping'):
                codify.invoke(lock, {}, self.root, timeout=1)
            killed.assert_not_called()
        finally:
            signal.signal(signal.SIGCHLD, old)
        started, release, escaped = (self.root / name for name in ('started', 'release', 'escaped'))
        data = ("from pathlib import Path\nimport time\n"
                f"Path({str(started)!r}).touch()\n"
                f"p=Path({str(release)!r}); deadline=time.monotonic()+10\n"
                "while not p.exists() and time.monotonic()<deadline: time.sleep(.01)\n"
                f"Path({str(escaped)!r}).touch()\n").encode()
        lock['files']['scripts/run.py'] = {'sha256': codify.digest(data), 'mode': 0o644, 'base64': base64.b64encode(data).decode()}
        original = subprocess.Popen._execute_child
        def interrupt_spawn(process, *args, **kwargs):
            original(process, *args, **kwargs)
            for _ in range(500):
                if started.exists():
                    break
                time.sleep(.01)
            self.assertTrue(started.exists())
            os.kill(os.getpid(), signal.SIGINT)
        try:
            with patch.object(subprocess.Popen, '_execute_child', interrupt_spawn), \
                    self.assertRaisesRegex(ValueError, 'interrupted'):
                codify.invoke(lock, {}, self.root)
        finally:
            release.touch()
        time.sleep(.2)
        self.assertFalse(escaped.exists())

    def test_private_checkout_permissions_do_not_hide_executable_drift(self):
        self.compile()
        self.entry.chmod(0o600)
        self.assertEqual(codify.check(self.output)['files']['scripts/run.py']['mode'], 0o644)
        self.entry.chmod(0o700)
        with self.assertRaisesRegex(ValueError, 'Stale workflow input'):
            codify.check(self.output)

    def test_new_locks_reject_missing_manifest_and_directory_includes(self):
        manifest = self.scripts / 'lock-runtime.json'
        saved = manifest.read_bytes()
        manifest.unlink()
        with self.assertRaisesRegex(ValueError, 'lock-runtime.json'):
            self.compile()
        self.assertFalse(self.output.exists())
        manifest.write_bytes(saved)
        for directory in (self.root, self.scripts):
            with self.subTest(directory=directory), self.assertRaises(ValueError):
                self.compile(includes=[directory])
        self.assertFalse(self.output.exists())
        self.compile()
        extra = self.scripts / 'notes.md'
        extra.write_text('not a runtime input')
        codify.check(self.output)
        workflow = self.scripts / 'workflow.py'
        workflow.write_bytes(workflow.read_bytes() + b'\n')
        with self.assertRaisesRegex(ValueError, 'Stale'):
            codify.check(self.output)

    def test_existing_v1_lock_checks_drift_and_ignores_nested_packages(self):
        legacy = self.root / 'legacy-write'
        shutil.copytree(ROOT / 'skills/write', legacy)
        lock = legacy / 'scripts/workflow.lock.json'
        self.assertEqual(codify.check(lock)['format'], 'tkstack.codify/v1')
        nested = legacy / 'skills/child'
        nested.mkdir(parents=True)
        (nested / 'SKILL.md').write_text('---\nname: child\n---\n')
        for index in range(520):
            (nested / f'{index}.txt').write_text('x')
        codify.check(lock)
        extra = legacy / 'references/new-file.md'
        extra.write_text('unexpected')
        with self.assertRaisesRegex(ValueError, 'Stale workflow inventory'):
            codify.check(lock)
        extra.unlink()
        source = legacy / 'scripts/run.py'
        source.write_bytes(source.read_bytes() + b'\n')
        with self.assertRaisesRegex(ValueError, 'Stale workflow input'):
            codify.check(lock)

    def test_missing_local_import_and_native_entrypoint_fail_before_publication(self):
        helper = self.scripts / 'needed_helper.py'
        helper.write_text('VALUE = 1\n')
        workflow = self.scripts / 'workflow.py'
        workflow.write_text('import needed_helper\n' + workflow.read_text())
        with self.assertRaisesRegex(ValueError, 'missing local import'):
            self.compile()
        self.assertFalse(self.output.exists())
        self.compile(includes=[helper])
        before = self.output.read_bytes()
        contract = self.scripts / 'contract.json'
        contract.write_text(json.dumps({'native': {'optional': {'entrypoint': 'scripts/native_tool.py'}}}))
        native = self.scripts / 'native_tool.py'
        native.write_text('print(1)\n')
        manifest = self.scripts / 'lock-runtime.json'
        manifest.write_text(json.dumps({'version': 1, 'files': ['scripts/contract.json', 'scripts/json_contract.py', 'scripts/workflow.py']}))
        with self.assertRaisesRegex(ValueError, 'missing native entrypoint'):
            self.compile(includes=[helper])
        self.assertEqual(self.output.read_bytes(), before)
        contract.write_text(json.dumps({'native': {'optional': {'entrypoint': 'scripts/native_tool.py'}}, 'delegate': None}))
        self.compile(includes=[helper, native])
        native.write_text('print(2)\n')
        with self.assertRaisesRegex(ValueError, 'Stale'):
            codify.check(self.output)

    def test_new_scaffold_compiles_only_its_runtime_inputs(self):
        target = self.root / 'small-workflow'
        codify.scaffold(self.source, target)
        (target / 'scripts/workflow.py').write_bytes((self.scripts / 'workflow.py').read_bytes())
        (target / 'commands/unused.dat').write_bytes(b'unrelated' * 500)
        shutil.copy2(self.cases, target / 'cases.json')
        output = target / 'scripts/workflow.lock.json'
        codify.compile_workflow(target / 'PROMPT.md', target / 'scripts/run.py', target / 'cases.json', output, target, project=self.root)
        lock = codify.check(output)
        self.assertEqual(lock['format'], codify.SCOPED_FORMAT)
        self.assertNotIn('scripts/codify.py', lock['files'])
        self.assertNotIn('references/tool.md', lock['files'])
        self.assertNotIn('commands/unused.dat', lock['files'])
        self.assertLess(output.stat().st_size, (target / 'scripts/codify.py').stat().st_size)
        self.assertEqual(json.loads(self.cli('run', output, '--input', '-', payload={'labels': [' b ', 'a']}).stdout), {'labels': ['a', 'b']})

    def test_relocating_source_tree_preserves_freshness_and_executable_file_modes(self):
        helper = self.scripts / 'native-helper'
        helper.write_text('#!/bin/sh\nprintf native-helper')
        helper.chmod(0o755)
        self.compile(includes=[helper])
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

    def test_alternate_model_runtime_and_profiles_cannot_be_scaffolded_or_compiled(self):
        with self.assertRaisesRegex(ValueError, 'deterministic Python'):
            codify.scaffold(self.source, self.root / 'sdk', 'ai-sdk')
        self.assertFalse((self.root / 'sdk').exists())
        with self.assertRaisesRegex(ValueError, 'invoking agent'):
            self.compile(profiles=['other'])
        self.assertFalse(self.output.exists())


class CodifyReleaseTests(unittest.TestCase):
    def test_sync_check_passes_on_the_tree(self):
        sys.path.insert(0, str(ROOT / 'src'))
        from skill_roots import load
        sync_codify = load('sync_codify_release', ROOT / 'skills/learn/skills/skillify/scripts/sync_codify.py')
        self.assertEqual(sync_codify.sync(check=True), [])


if __name__ == '__main__':
    unittest.main()

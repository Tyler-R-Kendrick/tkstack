"""Actual compiled skill interfaces, adversarial proof, and native helper behavior."""

import copy
import hashlib
import importlib.util
import json
import os
import shutil
import select
import signal
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parent.parent
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / 'skills/codify/scripts'))
import package_runtime as runtime
sys.path.insert(0, str(ROOT / 'scripts'))
from skill_roots import all_packages  # noqa: E402
PACKAGES = all_packages(ROOT)


class SkillNormalizationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='tkstack-normalized-')
        self.addCleanup(temporary.cleanup)
        self.project = Path(temporary.name)
        self.evidence = self.project / 'actual-evidence.txt'
        self.evidence.write_text('Synthetic contract fixture: actual retained bytes, not a production provider or semantic-quality claim.\n')
        self.models = {name: json.loads((path / 'scripts/contract.json').read_text()) for name, path in PACKAGES.items()}

    def call(self, skill, command, args=(), expected=0, raw=None):
        if raw is not None:
            entry = PACKAGES.get(skill, ROOT / 'skills' / skill) / 'scripts/run.py'
            argv = [sys.executable, '-B', str(entry), '--input', '-']
        else:
            argv = [sys.executable, '-B', str(ROOT / 'skills/codify/scripts/codify.py'), 'invoke', str(PACKAGES.get(skill, ROOT / 'skills' / skill)), '--', *command, *args]
        process = subprocess.run(argv, input=raw, capture_output=True, text=True, timeout=90,
            env={**os.environ, 'TKSTACK_WORKSPACE_DIR': str(self.project / '.tkstack')})
        self.assertEqual(process.returncode, expected, process.stdout + process.stderr)
        return json.loads(process.stdout) if process.stdout.strip() else None

    def facts(self, name):
        facts = {}
        for key, schema in self.models[name]['facts_schema']['properties'].items():
            if 'const' in schema:
                facts[key] = schema['const']
            elif 'enum' in schema:
                facts[key] = schema['enum'][0]
            elif schema['type'] == 'boolean':
                facts[key] = False
            elif schema['type'] == 'integer':
                facts[key] = 3
            elif isinstance(schema['type'], list):
                facts[key] = None
            else:
                facts[key] = 'fixture'
        if name == 'tkstack-principles':
            facts['code_sufficient'] = True
        if name in ('fal-ai', 'open-design'):
            facts.update(provider_requested=name, provider_used=name)
        return facts

    def report(self, name):
        return {'skill': name, 'objective': 'Adversarial structural contract fixture, not actual provider execution.',
            'facts': self.facts(name), 'criteria': [{'id': item['id'], 'status': 'pass', 'evidence': ['proof'],
                'reason': 'The fixture records this contract boundary; semantic/provider truth is not authenticated.'} for item in self.models[name]['criteria']],
            'evidence': [{'id': 'proof', 'path': str(self.evidence), 'sha256': hashlib.sha256(self.evidence.read_bytes()).hexdigest(), 'kind': 'contract-fixture'}],
            'review': {'reviewer': 'fixture-reviewer', 'semantic_inspection': 'performed',
                       'limitations': 'Authored schema/coverage fixture only; no production quality or service execution claim.'}}

    def test_every_owned_skill_runs_its_compiled_model_and_real_report_verifier(self):
        expected = set(PACKAGES)
        self.assertEqual(len(expected), 19)
        for name in sorted(expected):
            with self.subTest(skill=name):
                self.assertEqual(self.call(name, ['model'])['name'], name)
                path = self.project / (name + '-report.json')
                path.write_text(json.dumps(self.report(name)))
                result = self.call(name, ['verify'], ['--report', str(path)])
                self.assertEqual(result['structural_gate'], 'pass')
                self.assertEqual(result['semantic_review'], 'recorded-not-authenticated')

    def test_every_skill_rejects_tampered_evidence_missing_criteria_and_unreviewed_claims(self):
        for name, model in self.models.items():
            with self.subTest(skill=name):
                report = self.report(name)
                bad = copy.deepcopy(report)
                bad['evidence'][0]['sha256'] = '0' * 64
                with self.assertRaisesRegex(ValueError, 'bytes changed'):
                    runtime.verify(model, bad, self.project)
                bad = copy.deepcopy(report)
                bad['criteria'].pop()
                with self.assertRaisesRegex(ValueError, 'every modeled'):
                    runtime.verify(model, bad, self.project)
                bad = copy.deepcopy(report)
                bad['review']['semantic_inspection'] = 'not performed'
                with self.assertRaisesRegex(ValueError, 'Actual semantic'):
                    runtime.verify(model, bad, self.project)
                # Transfer through a different retained file and objective.
                alternate = self.project / 'transfer-evidence.txt'
                alternate.write_text('Distinct transfer fixture with different UTF-8 bytes: café.\n')
                report['objective'] = 'A distinct transfer workload'
                report['evidence'][0].update(path=str(alternate), sha256=hashlib.sha256(alternate.read_bytes()).hexdigest())
                self.assertEqual(runtime.verify(model, report, self.project)['structural_gate'], 'pass')

    def test_skill_specific_boundary_models_reject_contradictory_claims(self):
        examples = [('learn', {'evidence_as_instructions': True}),
            ('sdlc', {'stale_evidence_accepted': True}), ('codify', {'implicit_inference': True}),
            ('skillify', {'workflow_implemented': False}), ('reusify', {'observed_occurrences': 2}),
            ('instructify', {'stale_input_applied': True}), ('hookify', {'claim_activation': True}),
            ('lintify', {'semantic_backend': True, 'claim_deterministic': True}),
            ('flowify', {'claim_executed': True}), ('hill-climb', {'claim_improvement': True}),
            ('unslop', {'missing_evidence_graded_pass': True}), ('investigate', {'diagnose_only': True, 'product_code_changed': True}),
            ('document', {'claim_openwiki_guarantees': True}), ('write', {'published': True}),
            ('open-design', {'provider_used': 'different-provider'}), ('fal-ai', {'claim_complete': True}),
            ('headroom', {'exact_content_needed': True}), ('rtk', {'billing_claim_from_ratio': True}),
            ('tkstack-principles', {'mechanism': 'llm'})]
        for name, facts in examples:
            with self.subTest(skill=name):
                report = self.report(name)
                report['facts'].update(facts)
                with self.assertRaises(ValueError):
                    runtime.verify(self.models[name], report, self.project)

    def test_shared_json_contract_rejects_duplicate_fields_and_nonfinite_values_before_execution(self):
        for name in ('learn', 'write', 'codify'):
            for raw in ('{"operation":"model","operation":"native_capture"}', '{"operation":"model","extra":NaN}', '{"operation":"model","extra":1e999}'):
                self.call(name, [], expected=1, raw=raw)
        self.assertFalse((self.project / '.tkstack').exists())

    def test_real_native_code_generators_preserve_scope_and_existing_targets(self):
        skill = self.project / 'generated-skill'
        result = self.call('skillify', ['native', 'scaffold'], ['--name', skill.name, '--description', 'Inspect the actual requested contract.', '--target', str(skill)])
        self.assertEqual(result['status'], 'draft')
        self.assertTrue((skill / 'commands/version.md').is_file())
        before = (skill / 'SKILL.md').read_bytes()
        self.call('skillify', ['native', 'scaffold'], ['--name', skill.name, '--description', 'A conflicting request.', '--target', str(skill)], expected=1)
        self.assertEqual((skill / 'SKILL.md').read_bytes(), before)
        prompt = self.project / 'prompt.md'
        prompt.write_text('Normalize a supplied set of labels with a native contract.')
        result = self.call('codify', ['native', 'scaffold'], ['--source', str(prompt), '--target', str(self.project / 'workflow')])
        self.assertEqual(result['status'], 'workflow-draft')
        lint = self.project / 'lint-example'
        self.call('lintify', ['native', 'scaffold'], ['--backend', 'eslint', '--target', str(lint)])
        self.assertTrue((lint / 'package.json').is_file())

    def test_real_learning_adapter_writes_only_the_explicit_fixture_store(self):
        store = self.project / '.tkstack/steering'
        payload = {'source': {'conversation': 'synthetic test', 'message': 'fixture user'},
                   'user_text': 'Synthetic fixture preference.', 'context': 'Native adapter test only.', 'kind': 'preference'}
        source = self.project / 'correction.json'
        source.write_text(json.dumps(payload))
        result = self.call('learn', ['native', 'capture'], ['--input', str(source), '--store', str(store)])
        self.assertTrue(result['text'].startswith('correction-'))
        state = self.call('learn', ['native', 'show'], ['--store', str(store)])
        self.assertEqual(len(state['corrections']), 1)
        self.assertEqual(next(iter(state['corrections'].values()))['user_text'], payload['user_text'])

    def test_hook_replay_runs_native_cases_and_preserves_failure_exit_and_output(self):
        policy = ROOT / 'skills/hookify/examples/policy.json'
        cases = ROOT / 'skills/hookify/examples/cases.json'
        result = self.call('hookify', ['native', 'replay'], ['--rules', str(policy), '--cases', str(cases), '--jobs', '1.0'])
        self.assertTrue(result['passed'])
        bad = json.loads(cases.read_text())
        original = bad[0]['expected']['decision']
        bad[0]['expected']['decision'] = 'block' if original != 'block' else 'allow'
        path = self.project / 'bad-cases.json'
        path.write_text(json.dumps(bad))
        result = self.call('hookify', ['native', 'replay'], ['--rules', str(policy), '--cases', str(path)], expected=2)
        self.assertFalse(result['passed'])

    def test_native_instruction_planner_and_native_workflow_inspector(self):
        manifest = self.project / 'instructions.json'
        manifest.write_bytes((ROOT / 'skills/instructify/examples/manifest.json').read_bytes())
        result = self.call('instructify', ['native', 'plan'], ['--project', str(self.project), '--input', str(manifest)])
        self.assertTrue(result['changes'])
        self.assertFalse((self.project / 'AGENTS.md').exists())
        workflow = self.project / 'example-flow'
        self.call('flowify', ['native', 'scaffold'], ['--backend', 'maf', '--name', workflow.name, '--target', str(workflow)])
        result = self.call('flowify', ['native', 'inspect'], ['--backend', 'maf', '--file', str(workflow / 'workflow.yaml')])
        self.assertFalse(result.get('executed', False))

    def test_native_reuse_lookup_and_unslop_catalog_do_not_invent_observations(self):
        catalog = self.project / '.tkstack/reuse/catalog.json'
        catalog.parent.mkdir(parents=True)
        catalog.write_text(json.dumps({'version': 1, 'entries': []}))
        result = self.call('reusify', ['native', 'check'], ['--project', str(self.project)])
        self.assertEqual(result['entries'], 0)
        result = self.call('unslop', ['native', 'show'])
        self.assertTrue(result)

    def test_compiled_package_survives_real_git_commit_and_clone(self):
        source = self.project / 'source'
        shutil.copytree(ROOT / 'skills/write', source, ignore=shutil.ignore_patterns('__pycache__'))
        def git(*args):
            process = subprocess.run(['git', '-C', str(source), *args], capture_output=True, text=True)
            self.assertEqual(process.returncode, 0, process.stderr)
        git('init', '-q')
        git('add', '.')
        git('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '-qm', 'actual package snapshot')
        clone = self.project / 'clone/write'
        process = subprocess.run(['git', 'clone', '-q', str(source), str(clone)], capture_output=True, text=True)
        self.assertEqual(process.returncode, 0, process.stderr)
        process = subprocess.run([sys.executable, str(ROOT / 'skills/codify/scripts/codify.py'), 'check', str(clone / 'scripts/workflow.lock.json')], capture_output=True, text=True)
        self.assertEqual(process.returncode, 0, process.stderr)

    def test_native_compiler_and_runner_execute_the_real_code_contract(self):
        package = self.project / 'arithmetic'
        scripts = package / 'scripts'
        scripts.mkdir(parents=True)
        prompt = package / 'prompt.md'
        prompt.write_text('Add a supplied integer to itself with no inference.')
        entry = scripts / 'run.py'
        entry.write_text('import argparse,json\np=argparse.ArgumentParser();p.add_argument("--input");a=p.parse_args();v=json.load(open(a.input));print(json.dumps({"value":v["value"]*2}))\n')
        cases = package / 'cases.json'
        cases.write_text(json.dumps({'version': 1, 'cases': [
            {'id': 'double', 'input': {'value': 3}, 'output': {'value': 6}, 'exit': 0},
            {'id': 'transfer', 'input': {'value': -2}, 'output': {'value': -4}, 'exit': 0},
            {'id': 'missing-value', 'input': {}, 'exit': 1}]}))
        output = scripts / 'compiled.lock.json'
        result = self.call('codify', ['native', 'compile'], ['--source', str(prompt), '--entrypoint', str(entry), '--cases', str(cases), '--root', str(package), '--output', str(output)])
        self.assertEqual(result['status'], 'compiled')
        actual_input = package / 'input.json'
        actual_input.write_text('{"value":7}')
        self.assertEqual(self.call('codify', ['native', 'run'], ['--artifact', str(output), '--input', str(actual_input)]), {'value': 14})

    def test_skillify_compiler_preserves_normalized_native_resources(self):
        package = self.project / 'flowify'
        shutil.copytree(ROOT / 'skills/flowify', package)
        result = self.call('skillify', ['native', 'compile'], ['--target', str(package), '--cases', str(package / 'scripts/workflow.cases.json'), '--project', str(self.project), '--timeout', '5'])
        self.assertEqual(result['status'], 'compiled')
        target = self.project / 'scoped-flow'
        result = self.call(str(package), ['native', 'scaffold'], ['--backend', 'maf', '--name', target.name, '--target', str(target)])
        self.assertEqual(result['status'], 'source-created')
        self.assertTrue((target / 'workflow.yaml').is_file())

    def test_native_measurement_adapter_uses_real_paired_receipt_gate(self):
        import test_hill_climb as fixtures
        fixture = fixtures.HillClimbTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        arguments = ['--plan', str(fixture.plan_path), '--baseline', str(fixture.baseline), '--candidate', str(fixture.candidate)]
        result = self.call('hill-climb', ['native', 'compare'], arguments)
        self.assertEqual(result['decision'], 'eligible')
        fixture.changed[0]['work_count'] = 49
        fixture.save()
        result = self.call('hill-climb', ['native', 'compare'], arguments, expected=2)
        self.assertEqual(result['decision'], 'reject')

    def test_normalizer_dry_run_idempotence_and_generated_ownership(self):
        spec = importlib.util.spec_from_file_location('normalize_fixture', ROOT / 'skills/skillify/scripts/skillify.py')
        skillify = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(skillify)
        package = self.project / 'write'
        shutil.copytree(ROOT / 'skills/write', package)
        profile = package / 'scripts/contract.json'
        def snapshot():
            return {str(path.relative_to(package)): path.read_bytes() for path in package.rglob('*') if path.is_file()}
        before = snapshot()
        self.assertEqual(skillify.normalize(package, profile, skillify.codify, True)['changed'], [])
        self.assertEqual(snapshot(), before)
        command = package / 'commands/model.md'
        command.write_text(command.read_text() + '\nAn authored edit that must not be discarded.\n')
        authored = snapshot()
        with self.assertRaisesRegex(ValueError, 'Preserve'):
            skillify.normalize(package, profile, skillify.codify)
        self.assertEqual(snapshot(), authored)

    def test_raw_native_arguments_are_validated_before_any_execution(self):
        model = self.models['codify']['native']['native_compile']
        payload = {'operation': 'native_compile'}
        for key, field in model['parameters'].items():
            payload[key] = field.get('default', 'fixture')
        payload['jobs'] = True
        with patch.object(runtime.subprocess, 'Popen') as process:
            with self.assertRaisesRegex(ValueError, 'Contract violation'):
                runtime.execute(payload, ROOT / 'skills/codify')
            process.assert_not_called()

    def test_strict_json_rejects_overflow_without_conflating_valid_finite_numbers(self):
        with self.assertRaisesRegex(ValueError, 'Non-finite'):
            runtime.loads('{"value":1e999}')
        self.assertEqual(runtime.loads('{"value":1.5}'), {'value': 1.5})

    @unittest.skipUnless(Path('/proc').is_dir() and hasattr(os, 'pidfd_open'), 'Linux process-state observation')
    def test_native_helper_cleanup_stops_its_remaining_process_group(self):
        root = self.project / 'package'
        scripts = root / 'scripts'
        scripts.mkdir(parents=True)
        helper = scripts / 'helper.py'
        helper.write_text('import subprocess,sys,json\n'
            'p=subprocess.Popen([sys.executable,"-c","import os,time;print(os.getpid(),flush=True);time.sleep(30)"],stdout=subprocess.PIPE,text=True)\n'
            'pid=int(p.stdout.readline());print(json.dumps({"pid":pid}))\n')
        binding = {'entrypoint': 'scripts/helper.py', 'prefix': [], 'parameters': {}, 'suffix': []}
        with patch.dict(os.environ, {'TKSTACK_CODIFY_EXECUTION': ''}):
            result = runtime.native(root, {'native': {'native_probe': binding}}, 'native_probe', {'operation': 'native_probe'}, self.project)
        try:
            descriptor = os.pidfd_open(result['pid'])
        except ProcessLookupError:
            return
        try:
            events = select.poll()
            events.register(descriptor, select.POLLIN)
            self.assertTrue(events.poll(5000), 'Native descendant outlived its owned invocation')
        finally:
            try:
                signal.pidfd_send_signal(descriptor, signal.SIGKILL)
            except ProcessLookupError:
                pass
            finally:
                os.close(descriptor)
        state = Path('/proc') / str(result['pid']) / 'stat'
        try:
            observed = state.read_text()
        except (FileNotFoundError, ProcessLookupError):
            return
        # A killed orphan may remain a zombie until the host init reaps it.
        self.assertIn(observed.split(') ', 1)[1].split()[0], ('Z', 'X'))


if __name__ == '__main__':
    unittest.main()

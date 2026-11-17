"""Exercise the real native adapter through the strict Git experiment CLI."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'skills/hill-climb/scripts/experiment.py'
ADAPTER = ROOT / 'skills/hill-climb/scripts/experiment_native_check.py'
JSON_CONTRACT = ROOT / 'skills/hill-climb/scripts/json_contract.py'


class NativeExperimentIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.source = self.directory / 'product'
        self.source.mkdir()
        self.git('init', '-q')
        (self.source / 'product.py').write_text('VALUE = 0\n')
        (self.source / 'test_product.py').write_text(
            'import json,sys,unittest\nfrom pathlib import Path\nimport product\n'
            'case=json.loads(Path(sys.argv.pop()).read_text())\n'
            'class ProductTests(unittest.TestCase):\n'
            ' def test_expected_value(self): self.assertEqual(product.VALUE,case["expected"])\n'
            'if __name__ == "__main__": unittest.main()\n')
        self.git('add', '.')
        self.git('-c', 'user.name=Test', '-c', 'user.email=test@example.invalid',
                 'commit', '-qm', 'baseline')
        self.base = self.git('rev-parse', 'HEAD')
        self.root = self.directory / 'private-experiment'
        self.case = self.directory / 'case.json'
        self.case.write_text('{"expected": 1}')
        self.contract = self.directory / 'contract.txt'
        self.contract.write_text('The product value must satisfy the case.')
        self.config = self.directory / 'native-config.json'
        self.config.write_text(json.dumps({
            'argv': [sys.executable, 'test_product.py', '{{case_file}}'],
            'work_regex': r'Ran (?P<count>\d+) tests? in',
            'gate': 'tests', 'metric': 'success',
            'timeout_seconds': 10, 'max_output_bytes': 4096,
        }))

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.source), *args], text=True).strip()

    def call(self, action, **kwargs):
        request = self.directory / 'request.json'
        request.write_text(json.dumps({'action': action, 'root': str(self.root), **kwargs}))
        result = subprocess.run([sys.executable, str(SCRIPT), '--request', str(request)],
                                text=True, capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def initialize(self, dependencies=None, extra_args=None):
        return self.call('init', source=str(self.source), experiment='native', base=self.base,
                         paths=['product.py'], target='check',
                         registry={'check': {'argv': [sys.executable, str(ADAPTER),
                                   '--config', str(self.config), '--case-file', '{{case_file}}',
                                   '--case', '{{case}}', *(extra_args or [])], 'cwd': '.'}},
                         trusted_interpreter=sys.executable,
                         contract_file=str(self.contract), evaluator_file=str(ADAPTER),
                         evaluator_dependencies=([str(self.config), str(JSON_CONTRACT)] if dependencies is None else dependencies),
                         case_files={'selection': str(self.case)},
                         evaluation={'cases': ['selection'], 'repetitions': 1,
                                     'required_gates': [], 'candidate_only_gates': ['tests'],
                                     'metric': 'success', 'direction': 'higher', 'min_gain': 1,
                                     'noise_floor': 0, 'deterministic': True},
                         max_trials=2, max_tokens=0)

    def test_native_configuration_must_be_frozen_at_init(self):
        with self.assertRaisesRegex(AssertionError, "native.*config"):
            self.initialize([])

    def test_native_parser_must_be_frozen_at_init(self):
        with self.assertRaisesRegex(AssertionError, "native.*json_contract"):
            self.initialize([str(self.config)])

    def test_native_rejects_argparse_alias_overriding_frozen_config(self):
        with self.assertRaisesRegex(AssertionError, "native-check"):
            self.initialize(extra_args=['--config=' + str(self.config)])

    def test_native_configuration_must_be_frozen_at_calibration_and_revision(self):
        self.initialize()
        registry = {'check': {'argv': [sys.executable, str(ADAPTER), '--config', str(self.config),
                                      '--case-file', '{{case_file}}'], 'cwd': '.'}}
        with self.assertRaisesRegex(AssertionError, "native.*config"):
            self.call('calibration-run', run_key='bad', commit=self.base, case='selection',
                      case_file=str(self.case), evaluator_file=str(ADAPTER), registry=registry,
                      trusted_interpreter=sys.executable, evaluator_dependencies=[])
        old = hashlib.sha256(self.contract.read_bytes()).hexdigest()
        self.call('feedback', id='F1', observation='Improve', interpretation='Use the same checks',
                  counterexample='Missing checks', old_contract=old, new_contract=old, changes=['workflow'])
        with self.assertRaisesRegex(AssertionError, "native.*config"):
            self.call('revise', feedback='F1', contract_file=str(self.contract), evaluator_file=str(ADAPTER),
                      registry=registry, trusted_interpreter=sys.executable,
                      evaluator_dependencies=[], calibration=[])

    def test_native_unittest_baseline_and_candidate_compare_real_cases(self):
        self.initialize()
        arm = self.call('allocate', arm='fix')
        (Path(arm['worktree']) / 'product.py').write_text('VALUE = 1\n')
        frozen = self.call('freeze', arm='fix', message='Satisfy the case', writers_stopped=True)
        baseline = self.call('run', side='baseline', rep=0, run_key='baseline')
        candidate = self.call('run', side='candidate', arm='fix', rep=0, run_key='candidate')
        baseline_output = json.loads(baseline['result']['stdout'])
        candidate_output = json.loads(candidate['result']['stdout'])
        self.assertEqual(baseline_output['outcome'], 'test_failure')
        self.assertEqual(candidate_output['outcome'], 'passed')
        self.assertEqual(baseline_output['work_count'], 1)
        self.assertEqual(candidate_output['work_count'], 1)
        self.assertEqual(candidate_output['case_sha256'], hashlib.sha256(self.case.read_bytes()).hexdigest())
        comparison = self.call('compare', arm='fix', baseline=['baseline'], candidate=['candidate'], decision='choice')
        self.assertEqual(comparison['decision'], 'eligible')
        self.assertEqual(self.call('promote', arm='fix', decision='choice')['commit'], frozen['commit'])
        self.assertEqual(self.git('rev-parse', 'HEAD'), self.base)
        self.assertEqual((self.source / 'product.py').read_text(), 'VALUE = 0\n')

    def test_changed_native_config_is_rejected_before_start(self):
        self.initialize()
        self.config.write_text('{}')
        request = self.directory / 'bad-request.json'
        request.write_text(json.dumps({'action': 'run', 'root': str(self.root),
                                       'side': 'baseline', 'rep': 0, 'run_key': 'bad'}))
        result = subprocess.run([sys.executable, str(SCRIPT), '--request', str(request)],
                                text=True, capture_output=True, timeout=30)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('dependency changed', result.stderr)
        self.assertEqual(self.call('status')['ledger']['reserved_trials'], 0)


if __name__ == '__main__':
    unittest.main()

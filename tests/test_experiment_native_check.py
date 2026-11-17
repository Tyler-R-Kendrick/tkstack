"""Execute real native test commands through the generic evaluator adapter."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'skills/hill-climb/scripts/experiment_native_check.py'


class NativeCheckTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config = self.root / 'config.json'
        self.case = self.root / 'case.json'
        self.case.write_text('{\"id\": \"fixture\"}')
        self.target = self.root / 'test_target.py'
        self.base = {'argv': [sys.executable, '-m', 'unittest', 'test_target'],
                     'work_regex': r'Ran (?P<count>\d+) tests? in',
                     'gate': 'tests', 'metric': 'test_success',
                     'timeout_seconds': 10, 'max_output_bytes': 4096}

    def run_check(self, **updates):
        self.config.write_text(json.dumps({**self.base, **updates}))
        return subprocess.run([sys.executable, str(SCRIPT), '--config', str(self.config), '--case-file', str(self.case)],
                              cwd=self.root, capture_output=True, text=True, timeout=20)

    def test_real_passing_suite_reports_observed_work(self):
        self.target.write_text('import unittest\nclass T(unittest.TestCase):\n def test_a(self): self.assertEqual(1, 1)\n def test_b(self): self.assertTrue(True)\n')
        result = self.run_check()
        self.assertEqual(result.returncode, 0, result.stderr)
        record = json.loads(result.stdout)
        self.assertEqual(record['outcome'], 'passed')
        self.assertEqual(record['case_sha256'], hashlib.sha256(self.case.read_bytes()).hexdigest())
        self.assertEqual(record['gates'], {'tests': True})
        self.assertEqual(record['metrics'], {'test_success': 1})
        self.assertEqual(record['work_count'], 2)
        self.assertIn('Ran 2 tests', record['evidence']['output'])

    def test_real_test_failure_is_a_valid_negative_gate(self):
        self.target.write_text('import unittest\nclass T(unittest.TestCase):\n def test_failure(self): self.assertTrue(False)\n')
        result = self.run_check()
        self.assertEqual(result.returncode, 0, result.stderr)
        record = json.loads(result.stdout)
        self.assertEqual(record['outcome'], 'test_failure')
        self.assertEqual(record['gates'], {'tests': False})
        self.assertEqual(record['work_count'], 1)

    def test_empty_missing_summary_and_ambiguous_work_fail_closed(self):
        self.target.write_text('import unittest\n')
        for argv in ([sys.executable, '-m', 'unittest', 'test_target'],
                     [sys.executable, '-c', 'pass'],
                     [sys.executable, '-c', "print('Ran 1 test in');print('Ran 5 tests in')"]):
            with self.subTest(argv=argv):
                result = self.run_check(argv=argv)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(json.loads(result.stdout)['outcome'], 'invalid_work')

    def test_timeout_and_launch_error_are_not_test_failures(self):
        result = self.run_check(argv=[sys.executable, '-c', 'import time; time.sleep(1)'], timeout_seconds=0.1)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(json.loads(result.stdout)['outcome'], 'timeout')
        result = self.run_check(argv=['/no/such/executable'])
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(json.loads(result.stdout)['outcome'], 'infrastructure_error')

    def test_case_identifier_is_passed_as_an_argument(self):
        command = "import sys; assert sys.argv[1] == 'case id'; print('Ran 1 test in')"
        self.config.write_text(json.dumps({**self.base, 'argv': [sys.executable, '-c', command, '{{case}}']}))
        result = subprocess.run([sys.executable, str(SCRIPT), '--config', str(self.config),
                                 '--case-file', str(self.case), '--case', 'case id'],
                                cwd=self.root, capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['case'], 'case id')

    def test_case_file_placeholder_and_mutation_detection(self):
        command = "import sys; from pathlib import Path; Path(sys.argv[1]).write_text('changed'); print('Ran 1 test in')"
        result = self.run_check(argv=[sys.executable, '-c', command, '{{case_file}}'])
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(json.loads(result.stdout)['outcome'], 'infrastructure_error')

    def test_output_truncation_never_becomes_pass(self):
        result = self.run_check(argv=[sys.executable, '-c', "print('Ran 1 test in'); print('x'*10000)"], max_output_bytes=128)
        self.assertNotEqual(result.returncode, 0)
        record = json.loads(result.stdout)
        self.assertEqual(record['outcome'], 'incomplete_output')
        self.assertLessEqual(len(record['evidence']['output'].encode()), 128)

    def test_unrecognized_exit_with_summary_is_infrastructure_error(self):
        result = self.run_check(argv=[sys.executable, '-c', "print('Ran 1 test in'); raise SystemExit(42)"])
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(json.loads(result.stdout)['outcome'], 'infrastructure_error')
        recognized = self.run_check(argv=[sys.executable, '-c', "print('Ran 1 test in'); raise SystemExit(42)"],
                                    failure_exit_codes=[42])
        self.assertEqual(json.loads(recognized.stdout)['outcome'], 'test_failure')

    def test_invalid_contract_never_launches(self):
        marker = self.root / 'ran'
        argv = [sys.executable, '-c', f'open({str(marker)!r}, "w").write("yes")']
        result = self.run_check(argv=argv, work_regex='no named group')
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(marker.exists())


if __name__ == '__main__':
    unittest.main()

"""Execute real native test commands through the generic evaluator adapter."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
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
                              cwd=self.root, capture_output=True, text=True, timeout=20,
                              env={**os.environ, 'TKSTACK_EXPERIMENT_SNAPSHOT_ROOT': str(self.root)})

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

    @unittest.skipUnless(sys.platform.startswith('linux') and hasattr(os, 'waitid') and hasattr(os, 'WNOWAIT'), 'requires Linux non-reaping wait')
    def test_standalone_success_kills_closed_pipe_descendant(self):
        ready, release, escaped = self.root / 'child.pid', self.root / 'release', self.root / 'escaped'
        self.addCleanup(release.touch)
        child = ("import os,time; from pathlib import Path; "
                 f"Path({str(ready)!r}).write_text(str(os.getpid())); "
                 f"p=Path({str(release)!r}); "
                 "exec('while not p.exists():\\n time.sleep(0.01)'); "
                 f"Path({str(escaped)!r}).write_text('alive')")
        parent = ("import subprocess,sys,time; from pathlib import Path; "
                  f"subprocess.Popen([sys.executable,'-c',{child!r}],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); "
                  f"p=Path({str(ready)!r}); "
                  "exec('while not p.exists():\\n time.sleep(0.01)'); "
                  "print('Ran 1 test in 0.01s')")
        result = self.run_check(argv=[sys.executable, '-c', parent])
        self.assertEqual(result.returncode, 0, result.stderr)
        pid = int(ready.read_text())
        release.write_text('go')
        deadline = time.monotonic() + 2
        stopped = False
        while time.monotonic() < deadline:
            stat = Path(f'/proc/{pid}/stat')
            try:
                state = stat.read_text().split()[2]
            except FileNotFoundError:
                stopped = True
                break
            if state == 'Z':
                stopped = True
                break
            time.sleep(0.01)
        self.assertTrue(stopped, 'background process remained live after standalone native check')
        self.assertFalse(escaped.exists())

    def test_timeout_and_launch_error_are_not_test_failures(self):
        result = self.run_check(argv=[sys.executable, '-c', 'import time; time.sleep(1)'], timeout_seconds=0.1)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(json.loads(result.stdout)['outcome'], 'timeout')
        result = self.run_check(argv=['/no/such/executable'])
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(json.loads(result.stdout)['outcome'], 'infrastructure_error')

    def quality(self):
        external = tempfile.TemporaryDirectory()
        self.addCleanup(external.cleanup)
        judge = Path(external.name) / 'judge.py'
        judge.write_text(
            "import json,sys,hashlib\nfrom pathlib import Path\n"
            "case_hash=hashlib.sha256(Path(sys.argv[1]).read_bytes()).hexdigest()\n"
            "quality=float(Path('quality.txt').read_text())\n"
            "print(json.dumps({'case_sha256':case_hash,'metrics':{'quality':quality,'latency':4},"
            "'qualitative':{'quality':{'rating':quality,'rationale':'Read quality evidence',"
            "'evidence':['self']}},'evidence':'inspected rendered output'}))\n")
        interpreter = Path(sys.executable).resolve()
        return {'argv': [str(interpreter), str(judge), '{{case_file}}'], 'judge_file': str(judge),
                'executable_sha256': hashlib.sha256(interpreter.read_bytes()).hexdigest(),
                'judge_sha256': hashlib.sha256(judge.read_bytes()).hexdigest()}, judge

    def test_native_gate_and_trusted_qualitative_metric_compose(self):
        self.target.write_text('import unittest\nclass T(unittest.TestCase):\n def test_a(self): self.assertEqual(1, 1)\n')
        (self.root / 'quality.txt').write_text('3')
        quality, _ = self.quality()
        result = self.run_check(quality=quality)
        self.assertEqual(result.returncode, 0, result.stderr)
        record = json.loads(result.stdout)
        self.assertEqual(record['gates'], {'tests': True})
        self.assertEqual(record['metrics'], {'test_success': 1, 'quality': 3, 'latency': 4})
        self.assertEqual(record['qualitative']['quality']['evidence'], ['self'])
        self.assertEqual(record['qualitative']['quality']['rating'], 3)
        self.assertEqual(record['evidence']['quality']['evidence'], 'inspected rendered output')

    def test_failing_gate_does_not_hide_independent_quality_evidence(self):
        self.target.write_text('import unittest\nclass T(unittest.TestCase):\n def test_a(self): self.assertTrue(False)\n')
        (self.root / 'quality.txt').write_text('2')
        quality, _ = self.quality()
        result = self.run_check(quality=quality)
        self.assertEqual(result.returncode, 0, result.stderr)
        record = json.loads(result.stdout)
        self.assertFalse(record['gates']['tests'])
        self.assertEqual(record['metrics']['quality'], 2)

    def test_nested_cwd_cannot_treat_candidate_sibling_as_trusted_judge(self):
        quality, _ = self.quality()
        local = self.root / 'judge.py'
        local.write_text('print(42)')
        quality['argv'][1] = str(local)
        quality['judge_file'] = str(local)
        quality['judge_sha256'] = hashlib.sha256(local.read_bytes()).hexdigest()
        nested = self.root / 'nested'
        nested.mkdir()
        config = {**self.base, 'quality': quality}
        self.config.write_text(json.dumps(config))
        result = subprocess.run([sys.executable, str(SCRIPT), '--config', str(self.config),
                                 '--case-file', str(self.case)], cwd=nested, capture_output=True,
                                text=True, timeout=20,
                                env={**os.environ, 'TKSTACK_EXPERIMENT_SNAPSHOT_ROOT': str(self.root)})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('outside the candidate snapshot', json.loads(result.stdout)['error'])

    def test_quality_without_runner_owned_snapshot_root_fails_closed(self):
        quality, _ = self.quality()
        self.config.write_text(json.dumps({**self.base, 'quality': quality}))
        env = {key: value for key, value in os.environ.items() if key != 'TKSTACK_EXPERIMENT_SNAPSHOT_ROOT'}
        result = subprocess.run([sys.executable, str(SCRIPT), '--config', str(self.config),
                                 '--case-file', str(self.case)], cwd=self.root, capture_output=True,
                                text=True, timeout=20, env=env)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('runner-owned snapshot root', json.loads(result.stdout)['error'])

    def test_quality_uses_verified_resolved_judge_path(self):
        self.target.write_text('import unittest\nclass T(unittest.TestCase):\n def test_a(self): self.assertTrue(True)\n')
        (self.root / 'quality.txt').write_text('2')
        quality, judge = self.quality()
        judge.write_text(judge.read_text().replace("'evidence':'inspected rendered output'", "'evidence':__file__"))
        quality['judge_sha256'] = hashlib.sha256(judge.read_bytes()).hexdigest()
        alias = judge.parent / 'alias.py'
        alias.symlink_to(judge)
        quality['argv'][1] = str(alias)
        quality['judge_file'] = str(alias)
        result = self.run_check(quality=quality)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['evidence']['quality']['evidence'], str(judge.resolve()))

    def test_quality_judge_drift_or_candidate_owned_judge_fails_closed(self):
        self.target.write_text('import unittest\nclass T(unittest.TestCase):\n def test_a(self): self.assertTrue(True)\n')
        (self.root / 'quality.txt').write_text('2')
        quality, judge = self.quality()
        judge.write_text(judge.read_text() + '# changed\n')
        self.assertNotEqual(self.run_check(quality=quality).returncode, 0)
        local = self.root / 'judge.py'
        local.write_text('print(42)')
        quality['argv'][1] = str(local)
        quality['judge_file'] = str(local)
        quality['judge_sha256'] = hashlib.sha256(local.read_bytes()).hexdigest()
        self.assertNotEqual(self.run_check(quality=quality).returncode, 0)

    def test_case_identifier_is_passed_as_an_argument(self):
        command = "import sys; assert sys.argv[1] == 'case id'; print('Ran 1 test in')"
        self.config.write_text(json.dumps({**self.base, 'argv': [sys.executable, '-c', command, '{{case}}']}))
        result = subprocess.run([sys.executable, str(SCRIPT), '--config', str(self.config),
                                 '--case-file', str(self.case), '--case', 'case id'],
                                cwd=self.root, capture_output=True, text=True, timeout=20,
                                env={**os.environ, 'TKSTACK_EXPERIMENT_SNAPSHOT_ROOT': str(self.root)})
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

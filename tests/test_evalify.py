"""Host-judged evaluation records and bounded offline framework analysis."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent
HELPER = ROOT / 'skills/learn/skills/evalify/scripts/evalify.py'
PROMPTFOO = os.environ.get('TKSTACK_PROMPTFOO_BIN')


class EvalifyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='evalify-test-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        package = self.root / '.tkstack/runtime/evalify/node_modules/promptfoo'
        package.mkdir(parents=True)
        (package / 'package.json').write_text(json.dumps({'version': '0.125.1'}))
        (package / 'index.js').write_text('''
const fs = require('fs'), cp = require('child_process');
module.exports = {assertions: {runAssertion: async ({assertion, providerResponse}) => {
  fs.appendFileSync('calls', 'call\\n');
  if (fs.existsSync('hang')) {
    const child = cp.spawn(process.execPath, ['-e', 'setTimeout(()=>{}, 30000)'], {stdio: 'ignore'});
    fs.writeFileSync('child.pid', String(child.pid));
    await new Promise(() => {});
  }
  if (fs.existsSync('slow')) await new Promise(resolve => setTimeout(resolve, 700));
  return {pass: assertion.value === providerResponse.output};
}}};
''')
        self.data = {'version': 1, 'source': 'invoking-agent', 'cases': [
            {'id': 'good', 'judgment': True, 'reference': True, 'elapsed_ms': 10},
            {'id': 'bad', 'judgment': False, 'reference': False, 'elapsed_ms': None},
            {'id': 'current', 'judgment': True, 'reference': None, 'elapsed_ms': 4}]}
        self.save()

    def save(self):
        (self.root / 'cases.json').write_text(json.dumps(self.data))

    def cli(self, operation, receipt, extra=()):
        return subprocess.run([sys.executable, str(HELPER), operation, '--project', str(self.root),
            '--cases', 'cases.json', '--receipt', receipt, *extra], capture_output=True, text=True, timeout=30)

    def test_validated_host_judgments_are_scored_without_model_selection(self):
        valid = self.cli('validate', 'validate.time.json')
        self.assertEqual(valid.returncode, 0, valid.stderr)
        self.assertFalse((self.root / 'calls').exists())
        result = self.cli('run', 'run.time.json', ['--output', 'result.json'])
        self.assertEqual(result.returncode, 0, result.stderr)
        receipt = json.loads((self.root / 'run.time.json').read_text())
        scores = json.loads((self.root / 'result.json').read_text())
        self.assertEqual(scores['calibration']['matched'], 2)
        self.assertEqual(scores['calibration']['total'], 2)
        self.assertEqual(scores['current'], {'passed': 1, 'total': 1})
        self.assertEqual((receipt['source'], receipt['framework'], receipt['status']),
                         ('invoking-agent', 'promptfoo assertions', 'pass'))
        self.assertGreaterEqual(receipt['elapsed_ms'], 0)
        self.data['cases'][0]['judgment'] = False
        self.save()
        self.assertEqual(self.cli('run', 'mismatch.time.json', ['--output', 'mismatch.json']).returncode, 0)
        self.assertEqual(json.loads((self.root / 'mismatch.json').read_text())['calibration']['matched'], 1)

    def test_calibration_distinguishes_false_positives_from_false_negatives(self):
        self.data['cases'] = [
            {'id': 'true-positive', 'judgment': True, 'reference': True, 'elapsed_ms': 1},
            {'id': 'true-negative', 'judgment': False, 'reference': False, 'elapsed_ms': 1},
            {'id': 'false-positive', 'judgment': True, 'reference': False, 'elapsed_ms': 1},
            {'id': 'false-negative', 'judgment': False, 'reference': True, 'elapsed_ms': 1}]
        self.save()
        result = self.cli('run', 'confusion.time.json', ['--output', 'confusion.json'])
        self.assertEqual(result.returncode, 0, result.stderr)
        calibration = json.loads((self.root / 'confusion.json').read_text())['calibration']
        self.assertEqual(calibration['confusion'], {'true_positive': 1, 'true_negative': 1,
                                                    'false_positive': 1, 'false_negative': 1})

    def test_host_timing_summary_preserves_unknown_observations(self):
        self.data['cases'][0]['elapsed_ms'] = 10
        self.data['cases'][1]['elapsed_ms'] = None
        self.data['cases'][2]['elapsed_ms'] = 4
        self.save()
        result = self.cli('run', 'timing.time.json', ['--output', 'timing.json'])
        self.assertEqual(result.returncode, 0, result.stderr)
        summary = json.loads((self.root / 'timing.json').read_text())['timing']
        self.assertEqual(summary, {'observed': 2, 'missing': 1, 'median_ms': 7, 'max_ms': 10})
        for case in self.data['cases']:
            case['elapsed_ms'] = None
        self.save()
        result = self.cli('run', 'unknown.time.json', ['--output', 'unknown.json'])
        self.assertEqual(result.returncode, 0, result.stderr)
        summary = json.loads((self.root / 'unknown.json').read_text())['timing']
        self.assertEqual(summary, {'observed': 0, 'missing': 3, 'median_ms': None, 'max_ms': None})

    def test_alternate_model_executable_and_malformed_records_are_rejected_before_dispatch(self):
        for flag in ('--model', '--provider', '--executable', '--config'):
            with self.subTest(flag=flag):
                result = self.cli('run', 'blocked.json', ['--output', 'blocked-result.json', flag, 'other'])
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse((self.root / 'calls').exists())
        for bad in ('wrong-source', 'duplicate', 'invalid-time', 'oversized'):
            with self.subTest(bad=bad):
                data = json.loads(json.dumps(self.data))
                if bad == 'wrong-source': data['source'] = 'external'
                if bad == 'duplicate': data['cases'].append(data['cases'][0])
                if bad == 'invalid-time': data['cases'][0]['elapsed_ms'] = -1
                (self.root / 'cases.json').write_text(' ' * (1024 * 1024 + 1) if bad == 'oversized' else json.dumps(data))
                result = self.cli('validate', 'bad.time.json')
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse((self.root / 'bad.time.json').exists())
        self.assertFalse((self.root / 'calls').exists())

    def test_extreme_host_duration_fails_cleanly_before_dispatch(self):
        self.data['cases'][0]['elapsed_ms'] = 10 ** 1000
        self.save()
        result = self.cli('run', 'extreme.time.json', ['--output', 'extreme.json'])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Elapsed milliseconds', result.stderr)
        self.assertNotIn('Traceback', result.stderr)
        self.assertFalse((self.root / 'calls').exists())

    @unittest.skipUnless(os.name == 'posix' and Path('/proc').is_dir(), 'POSIX process cleanup fixture')
    def test_timeout_stops_offline_analysis_group_and_records_elapsed_time(self):
        (self.root / 'hang').touch()
        result = self.cli('run', 'timeout.json', ['--output', 'timeout-result.json', '--timeout', '1'])
        self.assertEqual(result.returncode, 124, result.stderr)
        receipt = json.loads((self.root / 'timeout.json').read_text())
        self.assertEqual((receipt['status'], receipt['timeout_seconds']), ('timeout', 1))
        self.assertGreaterEqual(receipt['elapsed_ms'], 500)
        child = int((self.root / 'child.pid').read_text())
        try:
            state = Path(f'/proc/{child}/stat')
            alive = state.exists() and state.read_text().split(') ', 1)[1].split()[0] != 'Z'
            self.assertFalse(alive, 'Timed-out analysis left its child process running')
        finally:
            try:
                os.kill(child, signal.SIGKILL)
            except ProcessLookupError:
                pass

    def test_concurrent_analysis_reserves_receipt_and_output_before_dispatch(self):
        (self.root / 'slow').touch()
        self.data['cases'] = self.data['cases'][:1]
        self.save()
        for collision in ('receipt', 'output'):
            with self.subTest(collision=collision):
                calls = self.root / 'calls'
                calls.unlink(missing_ok=True)
                commands = []
                for index in range(2):
                    receipt = 'same-receipt.json' if collision == 'receipt' else f'receipt-{index}.json'
                    output = 'same-output.json' if collision == 'output' else f'output-{index}.json'
                    commands.append([sys.executable, str(HELPER), 'run', '--project', str(self.root),
                        '--cases', 'cases.json', '--receipt', receipt, '--output', output])
                processes = [subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for command in commands]
                results = [process.communicate(timeout=10) for process in processes]
                self.assertEqual(sorted(process.returncode for process in processes), [0, 1], results)
                self.assertEqual(calls.read_text().splitlines(), ['call'])
                for path in self.root.glob('*.json'):
                    if path.name != 'cases.json': path.unlink()

    @unittest.skipUnless(PROMPTFOO, 'set TKSTACK_PROMPTFOO_BIN for real Promptfoo assertions')
    def test_real_promptfoo_scores_preexisting_host_judgments_without_a_model(self):
        modules = next(path for path in Path(PROMPTFOO).resolve().parents if path.name == 'node_modules')
        local_modules = self.root / '.tkstack/runtime/evalify/node_modules'
        import shutil
        shutil.rmtree(local_modules)
        local_modules.symlink_to(modules, target_is_directory=True)
        result = self.cli('run', 'native.time.json', ['--output', 'native.json'])
        self.assertEqual(result.returncode, 0, result.stderr)
        scores = json.loads((self.root / 'native.json').read_text())
        self.assertEqual(scores['calibration']['matched'], 2)
        self.assertEqual(scores['calibration']['total'], 2)
        self.assertEqual(scores['current'], {'passed': 1, 'total': 1})


if __name__ == '__main__':
    unittest.main()

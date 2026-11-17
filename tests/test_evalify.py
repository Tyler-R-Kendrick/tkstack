"""The evaluation adapter preserves real runner outcomes and timeout evidence."""
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
        (self.root / 'config.yaml').write_text('fixture: true\n')
        self.runner = self.root / 'runner'
        self.runner.write_text('''#!/usr/bin/env python3
import json, os, pathlib, subprocess, sys, time
root = pathlib.Path.cwd()
(root / 'pid').write_text(str(os.getpid()))
if (root / 'hang').exists():
    child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'])
    (root / 'childpid').write_text(str(child.pid))
    time.sleep(30)
if 'eval' in sys.argv:
    rows = [] if (root / 'empty').exists() else [{'success': not (root / 'fail').exists()}]
    pathlib.Path(sys.argv[sys.argv.index('-o') + 1]).write_text(json.dumps({'results': {'results': rows}}))
    (root / 'argv.json').write_text(json.dumps(sys.argv))
    sys.exit(100 if (root / 'fail').exists() else 0)
''')
        self.runner.chmod(0o755)

    def cli(self, op, receipt, extra=()):
        return subprocess.run([sys.executable, str(HELPER), op, '--project', str(self.root),
            '--config', 'config.yaml', '--executable', str(self.runner), '--receipt', receipt,
            *extra], capture_output=True, text=True, timeout=15)

    def test_runner_results_are_bounded_retained_and_fail_closed(self):
        result = self.cli('run', 'pass.time.json', ['--output', 'pass.json'])
        self.assertEqual(result.returncode, 0, result.stderr)
        receipt = json.loads((self.root / 'pass.time.json').read_text())
        self.assertEqual((receipt['status'], receipt['result_count'], receipt['passed']), ('pass', 1, 1))
        self.assertGreaterEqual(receipt['elapsed_ms'], 0)
        self.assertEqual(len(receipt['executable_sha256']), 64)
        argv = json.loads((self.root / 'argv.json').read_text())
        self.assertIn('--no-cache', argv)
        self.assertIn('--no-share', argv)
        (self.root / 'fail').touch()
        result = self.cli('run', 'fail.time.json', ['--output', 'fail.json'])
        self.assertNotEqual(result.returncode, 0)
        receipt = json.loads((self.root / 'fail.time.json').read_text())
        self.assertEqual((receipt['status'], receipt['failed']), ('fail', 1))
        (self.root / 'fail').unlink()
        (self.root / 'empty').touch()
        result = self.cli('run', 'empty.time.json', ['--output', 'empty.json'])
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(json.loads((self.root / 'empty.time.json').read_text())['status'], 'error')
        self.assertNotEqual(self.cli('run', 'new.time.json', ['--output', 'pass.json']).returncode, 0)

    def test_timeout_stops_direct_runner_and_records_elapsed_time(self):
        (self.root / 'hang').touch()
        result = self.cli('validate', 'timeout.json', ['--timeout', '1'])
        self.assertEqual(result.returncode, 124, result.stderr)
        receipt = json.loads((self.root / 'timeout.json').read_text())
        self.assertEqual((receipt['status'], receipt['timeout_seconds']), ('timeout', 1))
        self.assertGreaterEqual(receipt['elapsed_ms'], 500)
        self.assertLess(receipt['elapsed_ms'], 12000)
        pid = int((self.root / 'pid').read_text())
        with self.assertRaises(ProcessLookupError):
            os.kill(pid, 0)
        child = int((self.root / 'childpid').read_text())
        try:
            state = Path(f'/proc/{child}/stat')
            alive = state.exists() and state.read_text().split(') ', 1)[1].split()[0] != 'Z'
            self.assertFalse(alive, 'Timed-out runner left its child process running')
        finally:
            try:
                os.kill(child, signal.SIGKILL)
            except ProcessLookupError:
                pass

    @unittest.skipUnless(PROMPTFOO, 'set TKSTACK_PROMPTFOO_BIN for the real Promptfoo integration')
    def test_real_promptfoo_calls_a_fixture_judge_and_reports_mixed_results(self):
        (self.root / 'judge.cjs').write_text('''module.exports = class Judge {
  id() { return 'fixture'; }
  async callApi(prompt) { const pass = prompt.includes('GOOD-CANDIDATE');
    return {output: JSON.stringify({pass, score: pass ? 1 : 0, reason: 'fixture'})}; }
};''')
        (self.root / 'config.yaml').write_text('''prompts: ['{{answer}}']
providers: [echo]
defaultTest:
  options: {provider: 'file://judge.cjs'}
tests:
  - vars: {answer: GOOD-CANDIDATE}
    assert: [{type: llm-rubric, value: A good answer}]
  - vars: {answer: BAD-CANDIDATE}
    assert: [{type: llm-rubric, value: A good answer}]
''')
        self.runner = Path(PROMPTFOO)
        result = self.cli('run', 'native.time.json', ['--output', 'native.json'])
        self.assertNotEqual(result.returncode, 0)
        receipt = json.loads((self.root / 'native.time.json').read_text())
        self.assertEqual((receipt['result_count'], receipt['passed'], receipt['failed']), (2, 1, 1))
        self.assertEqual(receipt['grader_errors'], 0)
        self.assertEqual(receipt['status'], 'fail')
        (self.root / 'judge.cjs').write_text("module.exports = class Judge { id(){return 'error'} async callApi(){return {error:'grader unavailable'}} };\n")
        result = self.cli('run', 'judge-error.time.json', ['--output', 'judge-error.json'])
        self.assertNotEqual(result.returncode, 0)
        receipt = json.loads((self.root / 'judge-error.time.json').read_text())
        self.assertEqual(receipt['grader_errors'], 2)


if __name__ == '__main__':
    unittest.main()

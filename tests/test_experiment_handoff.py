"""Run the documented private-champion handoff against real Git repositories."""
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest

import test_experiment_native_integration as fixture


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'skills/hill-climb/scripts/experiment.py'


class HandoffTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixture.NativeExperimentIntegrationTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.t = self.fixture
        self.t.initialize()
        arm = self.t.call('allocate', arm='fix')
        (Path(arm['worktree']) / 'product.py').write_text('VALUE = 1\n')
        self.candidate = self.t.call('freeze', arm='fix', message='fix', writers_stopped=True)
        self.t.call('run', side='baseline', rep=0, run_key='baseline')
        self.t.call('run', side='candidate', arm='fix', rep=0, run_key='candidate')
        self.t.call('compare', arm='fix', baseline=['baseline'], candidate=['candidate'], decision='choice')
        self.t.call('promote', arm='fix', decision='choice')
        self.delivery = self.t.directory / 'delivery'
        self.t.git('worktree', 'add', '-b', 'delivery', str(self.delivery), self.t.base)

    def run_handoff(self):
        request = self.t.directory / 'handoff-request.json'
        request.write_text(json.dumps({'action': 'handoff', 'root': str(self.t.root), 'delivery': str(self.delivery),
                                       'decision': 'choice', 'writers_stopped': True}))
        return subprocess.run([sys.executable, str(SCRIPT), '--request', str(request)],
                              capture_output=True, text=True, timeout=30)

    def test_handoff_requires_explicit_quiescence(self):
        request = self.t.directory / 'not-quiesced.json'
        request.write_text(json.dumps({'action': 'handoff', 'root': str(self.t.root),
                                       'delivery': str(self.delivery), 'decision': 'choice'}))
        result = subprocess.run([sys.executable, str(SCRIPT), '--request', str(request)],
                                capture_output=True, text=True, timeout=30)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('writers have stopped', result.stderr)
        self.assertEqual((self.delivery / 'product.py').read_text(), 'VALUE = 0\n')

    def test_unbound_or_modified_intent_cannot_be_handed_off(self):
        path = self.t.root / 'promotions' / 'choice.json'
        intent = json.loads(path.read_text())
        intent['expected'] = intent['candidate']
        path.write_text(json.dumps(intent))
        result = self.run_handoff()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('differs from the ledger', result.stderr)
        self.assertEqual((self.delivery / 'product.py').read_text(), 'VALUE = 0\n')

    def test_stages_exact_evaluated_tree_without_mutating_source_checkout(self):
        before = subprocess.run(['git', '-C', str(self.delivery), 'cat-file', '-e',
                                 self.candidate['commit'] + '^{commit}'], capture_output=True)
        self.assertNotEqual(before.returncode, 0)
        result = self.run_handoff()
        self.assertEqual(result.returncode, 0, result.stderr)
        receipt = json.loads(result.stdout)
        self.assertEqual(receipt['tree'], self.candidate['tree'])
        staged = subprocess.check_output(['git', '-C', str(self.delivery), 'write-tree'], text=True).strip()
        self.assertEqual(staged, self.candidate['tree'])
        self.assertEqual(self.t.git('rev-parse', 'HEAD'), self.t.base)
        self.assertEqual((self.t.source / 'product.py').read_text(), 'VALUE = 0\n')

    def test_dirty_worktree_and_moved_head_fail_before_applying(self):
        dirty = self.delivery / 'notes.txt'
        dirty.write_text('preserve me')
        result = self.run_handoff()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('must be clean', result.stderr)
        self.assertEqual(dirty.read_text(), 'preserve me')
        dirty.unlink()
        subprocess.run(['git', '-C', str(self.delivery), '-c', 'user.name=Test',
                        '-c', 'user.email=test@example.invalid', '-c', 'core.hooksPath=/dev/null',
                        'commit', '-q', '--allow-empty', '-m', 'advance'], check=True)
        result = self.run_handoff()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('HEAD changed', result.stderr)
        self.assertEqual((self.delivery / 'product.py').read_text(), 'VALUE = 0\n')

    def test_confirmation_must_match_the_promoted_decision(self):
        t = fixture.NativeExperimentIntegrationTests()
        t.setUp()
        self.addCleanup(t.doCleanups)
        t.case.write_text('{"expected": 1, "name": "selection"}')
        holdout = t.directory / 'confirmation.json'
        holdout.write_text('{"expected": 1, "name": "confirmation"}')
        t.call('init', source=str(t.source), experiment='confirmed', base=t.base,
               paths=['product.py'], target='check',
               registry={'check': {'argv': [sys.executable, str(fixture.ADAPTER), '--config', str(t.config),
                         '--case-file', '{{case_file}}', '--case', '{{case}}'], 'cwd': '.'}},
               trusted_interpreter=sys.executable, contract_file=str(t.contract),
               evaluator_file=str(fixture.ADAPTER), evaluator_dependencies=[str(t.config), str(fixture.JSON_CONTRACT)],
               case_files={'selection': str(t.case), 'holdout': str(holdout)},
               evaluation={'cases': ['selection'], 'repetitions': 1, 'required_gates': [],
                           'candidate_only_gates': ['tests'], 'metric': 'success', 'direction': 'higher',
                           'min_gain': 1, 'noise_floor': 0, 'deterministic': True},
               confirmation={'cases': ['holdout'], 'repetitions': 1}, max_trials=4, max_tokens=0)
        arm = t.call('allocate', arm='fix')
        (Path(arm['worktree']) / 'product.py').write_text('VALUE = 1\n')
        frozen = t.call('freeze', arm='fix', message='fix', writers_stopped=True)
        t.call('run', side='baseline', rep=0, run_key='old')
        t.call('run', side='candidate', arm='fix', rep=0, run_key='new')
        t.call('compare', arm='fix', baseline=['old'], candidate=['new'], decision='pick')
        t.call('select', decision='pick')
        t.call('run', side='baseline', split='confirmation', rep=0, run_key='hold-old')
        t.call('run', side='candidate', arm='fix', split='confirmation', rep=0, run_key='hold-new')
        t.call('confirm', baseline=['hold-old'], candidate=['hold-new'])
        t.call('promote', arm='fix', decision='pick')
        delivery = t.directory / 'delivery-confirmed'
        t.git('worktree', 'add', '-b', 'delivery-confirmed', str(delivery), t.base)
        receipt = t.call('handoff', delivery=str(delivery), decision='pick', writers_stopped=True)
        self.assertEqual(receipt['tree'], frozen['tree'])

    def test_external_filter_driver_blocks_before_staging(self):
        marker = self.t.directory / 'filter-ran'
        subprocess.run(['git', '-C', str(self.delivery), 'config', 'filter.demo.smudge',
                        'sh -c "touch ' + str(marker) + '"'], check=True)
        result = self.run_handoff()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('filter drivers', result.stderr)
        self.assertFalse(marker.exists())
        self.assertEqual((self.delivery / 'product.py').read_text(), 'VALUE = 0\n')

    def test_changed_evaluator_input_fails_before_applying(self):
        self.t.contract.write_text('modified contract')
        result = self.run_handoff()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('contract file changed', result.stderr)
        self.assertEqual((self.delivery / 'product.py').read_text(), 'VALUE = 0\n')

    def test_changed_evidence_receipt_fails_before_applying(self):
        (self.t.root / 'runs' / 'baseline.json').write_text('{}')
        result = self.run_handoff()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('not bound to a settled ledger', result.stderr)
        self.assertEqual((self.delivery / 'product.py').read_text(), 'VALUE = 0\n')

    def test_configured_scope_is_rechecked_at_handoff(self):
        config_path = self.t.root / 'experiment.json'
        original = config_path.read_text()
        config = json.loads(original)
        config['paths'] = ['different-file.py']
        config_path.write_text(json.dumps(config))
        import hashlib
        revised_digest = hashlib.sha256(config_path.read_bytes()).hexdigest()
        with sqlite3.connect(self.t.root / 'ledger.sqlite3') as db:
            db.execute('UPDATE controller_config SET digest=? WHERE id=1', (revised_digest,))
            # Make the synthetic records internally consistent so the test
            # exercises the scope guard independently of the receipt guard.
            for key in ('baseline', 'candidate'):
                path = self.t.root / 'runs' / (key + '.json')
                run = json.loads(path.read_text())
                run['config_digest'] = revised_digest
                path.write_text(json.dumps(run))
                row = db.execute('SELECT details FROM events WHERE run_key=? AND operation=?',
                                 (key, 'settle')).fetchone()
                details = json.loads(row[0])
                details['receipt_sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
                db.execute('UPDATE events SET details=? WHERE run_key=? AND operation=?',
                           (json.dumps(details), key, 'settle'))
        result = self.run_handoff()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('promotion configuration changed', result.stderr)
        self.assertEqual((self.delivery / 'product.py').read_text(), 'VALUE = 0\n')


if __name__ == '__main__':
    unittest.main()

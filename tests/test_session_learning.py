"""Session lifetimes, bounded evidence, abstract findings, and reusable mechanism routing."""
from concurrent.futures import ThreadPoolExecutor
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'skills/learn/scripts'))
import session_learning as learning
import tkstack_state as state


class SessionLearningTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.workspace = self.root / 'workspace'
        self.workspace.mkdir()
        (self.workspace / '.git').mkdir()
        self.scopes = {scope: self.root / scope / '.tkstack' for scope in state.SCOPES}
        environment = {'TKSTACK_' + scope.upper() + '_DIR': str(path) for scope, path in self.scopes.items()}
        environment['TKSTACK_SESSION_ID'] = ''
        self.environment = patch.dict(os.environ, environment)
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def create(self, identity='one', scope='workspace', closed=True):
        result = learning.lifecycle(identity, scope, purpose='Fixture with actual workflow observations')
        path = Path(result['path'])
        (path / 'notes.md').write_text('Repeated conversion rebuilt the procedure; preserve its executable artifact instead.\n')
        if closed:
            learning.lifecycle(identity, scope, close=True)
        return path

    def decision(self, snapshot, mechanisms=None, disposition='generalize'):
        source = snapshot['sessions'][0]
        item = next(item for item in source['files'] if item['path'] == 'notes.md')
        return {'version': 1, 'snapshot_sha256': snapshot['snapshot_sha256'], 'findings': [{
            'id': 'compile-once', 'scope': 'workspace', 'disposition': disposition,
            'observation': 'The captured procedure was repeatedly reconstructed.',
            'trigger': 'A stable repeatable procedure is being executed.',
            'principle': 'Resolve semantics once and execute reusable code.',
            'boundary': 'Subjective generation can retain explicit inference.',
            'transfer': 'Reuse the same compiler for a second prompt.',
            'counterexample': 'An unimplemented scaffold is not a compiled procedure.',
            'rationale': 'The repeated interpretation is removable by compiling the actual algorithm.',
            'scope_basis': 'Evidence concerns this workspace; no personal preference is inferred.',
            'evidence': [{'scope': source['scope'], 'session': source['id'], 'path': item['path'], 'sha256': item['sha256']}],
            'mechanisms': mechanisms if mechanisms is not None else [
                {'kind': 'reusable-code', 'target': 'scripts/existing-library.py'},
                {'kind': 'procedure', 'target': 'skills/existing', 'depends_on': ['compile-once.reusable-code']},
                {'kind': 'compiled-workflow', 'target': 'skills/existing/scripts/workflow.lock.json', 'depends_on': ['compile-once.procedure']}
            ]}]}

    def cli(self, *args):
        return subprocess.run([sys.executable, str(ROOT / 'skills/learn/scripts/learn.py'), *args],
                              capture_output=True, text=True, cwd=self.workspace)

    def test_empty_reviews_are_read_only_and_never_initialize_other_scopes(self):
        snapshot = learning.review(all_scopes=True)
        self.assertEqual(snapshot['sessions'], [])
        self.assertFalse(any(path.exists() for path in self.scopes.values()))
        result = self.cli('sessions', 'list', '--all-scopes')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), [])
        self.assertFalse(any(path.exists() for path in self.scopes.values()))

    def test_closed_session_review_preserves_content_and_all_scopes_are_explicit(self):
        self.create('same-id', 'workspace')
        self.create('same-id', 'user')
        self.create('same-id', 'global')
        self.assertEqual(len(learning.review()['sessions']), 1)
        snapshot = learning.review(all_scopes=True)
        self.assertEqual([item['scope'] for item in snapshot['sessions']], ['workspace', 'user', 'global'])
        self.assertTrue(all(item['status'] == 'closed' for item in snapshot['sessions']))
        self.assertEqual(len({item['path'] for item in snapshot['sessions']}), 3)
        self.assertIn('Repeated conversion', snapshot['sessions'][0]['files'][0]['text'])

    def test_active_sessions_are_skipped_unless_explicit_or_current(self):
        self.create(closed=False)
        self.assertEqual(learning.review()['sessions'], [])
        self.assertEqual(len(learning.review(sessions=['one'])['sessions']), 1)
        with patch.dict(os.environ, {'TKSTACK_SESSION_ID': 'one'}):
            self.assertEqual(len(learning.review()['sessions']), 1)

    def test_routing_forms_a_stable_dependency_graph_and_does_not_run_skills(self):
        self.create()
        snapshot = learning.review()
        plan = learning.plan(snapshot, self.decision(snapshot))
        self.assertEqual(plan['waves'], [['compile-once.reusable-code'], ['compile-once.procedure'], ['compile-once.compiled-workflow']])
        self.assertEqual({item['skill'] for item in plan['actions']}, {'reusify', 'skillify', 'codify'})
        self.assertFalse((self.workspace / 'skills').exists())
        self.assertEqual(plan, learning.plan(snapshot, self.decision(snapshot)))

    def test_all_durable_mechanisms_are_supported_without_keyword_classification(self):
        self.create()
        snapshot = learning.review()
        mechanisms = [{'kind': kind, 'target': 'canonical/' + kind} for kind in learning.ROUTES]
        plan = learning.plan(snapshot, self.decision(snapshot, mechanisms))
        self.assertEqual({action['skill'] for action in plan['actions']}, {'learn', 'instructify', 'skillify', 'codify', 'flowify', 'lintify', 'hookify', 'reusify'})
        self.assertEqual(len(plan['waves']), 1)

    def test_unresolved_findings_cannot_schedule_artifact_changes(self):
        self.create()
        snapshot = learning.review()
        decision = self.decision(snapshot, disposition='unresolved')
        with self.assertRaisesRegex(ValueError, 'cannot schedule'):
            learning.plan(snapshot, decision)
        decision['findings'][0]['mechanisms'] = []
        self.assertEqual(learning.plan(snapshot, decision)['actions'], [])

    def test_missing_abstraction_stale_evidence_and_cyclic_routes_are_rejected(self):
        directory = self.create()
        snapshot = learning.review()
        decision = self.decision(snapshot)
        del decision['findings'][0]['counterexample']
        with self.assertRaisesRegex(ValueError, 'abstraction'):
            learning.plan(snapshot, decision)
        decision = self.decision(snapshot)
        decision['findings'][0]['mechanisms'][0]['depends_on'] = ['compile-once.compiled-workflow']
        with self.assertRaisesRegex(ValueError, 'Cyclic'):
            learning.plan(snapshot, decision)
        (directory / 'notes.md').write_text('Changed after inspection')
        with self.assertRaisesRegex(ValueError, 'changed'):
            learning.plan(snapshot, self.decision(snapshot))

    def test_saved_reviews_survive_session_expiry_and_are_gitignored(self):
        directory = self.create()
        snapshot = learning.review()
        saved = Path(learning.save(snapshot))
        self.assertIn('/.tkstack/learnings/reviews/', str(saved))
        self.assertEqual(saved, Path(learning.save(snapshot)))
        before = saved.read_bytes()
        (directory / 'notes.md').unlink()
        self.assertEqual(saved.read_bytes(), before)
        subprocess.run(['git', 'init', '-q', str(self.scopes['workspace'].parent)], check=True)
        result = subprocess.run(['git', '-C', str(self.scopes['workspace'].parent), 'check-ignore', str(saved)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_binary_and_oversized_evidence_has_explicit_coverage(self):
        directory = self.create()
        (directory / 'image.bin').write_bytes(b'\xff\xfe\x00')
        (directory / 'large.log').write_bytes(b'x' * (learning.MAX_BYTES + 1))
        files = {item['path']: item for item in learning.review()['sessions'][0]['files']}
        self.assertEqual(files['image.bin']['coverage'], 'binary-hash-only')
        self.assertEqual(files['large.log']['coverage'], 'size-limit')
        self.assertIsNone(files['large.log']['sha256'])

    def test_symlinked_session_content_is_not_followed(self):
        directory = self.create()
        (directory / 'outside.md').symlink_to(self.workspace / 'unknown')
        with self.assertRaisesRegex(ValueError, 'regular files'):
            learning.review()

    def test_cli_start_close_review_plan_and_saved_evidence(self):
        result = self.cli('sessions', 'start', 'cli-one', '--purpose', 'Test actual CLI lifecycle')
        self.assertEqual(result.returncode, 0, result.stderr)
        directory = Path(json.loads(result.stdout)['path'])
        (directory / 'notes.md').write_text('Actual fixture evidence')
        result = self.cli('sessions', 'close', 'cli-one')
        self.assertEqual(result.returncode, 0, result.stderr)
        result = self.cli('sessions', 'review', '--session', 'cli-one', '--save')
        self.assertEqual(result.returncode, 0, result.stderr)
        result = json.loads(result.stdout)
        decision_path = directory / 'decision.json'
        decision_path.write_text(json.dumps(self.decision(result['document'])))
        planned = self.cli('sessions', 'plan', '--snapshot', result['saved'], '--input', str(decision_path), '--save')
        self.assertEqual(planned.returncode, 0, planned.stderr)
        self.assertEqual(json.loads(planned.stdout)['document']['status'], 'planned')


    def test_layered_steering_candidate_shadows_active_global_rule_without_writes(self):
        spec = importlib.util.spec_from_file_location('scoped_learning_rules', ROOT / 'skills/learn/scripts/learn.py')
        learn = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(learn)
        for scope in ('global', 'user', 'workspace'):
            store = self.scopes[scope] / 'steering'
            evidence = learn.capture(store, {'source': {'conversation': 'scope-fixture', 'message': scope},
                                           'user_text': 'Use the exact fixture scope.', 'context': 'Test fixture', 'kind': 'preference'})
            learn.write_rule(store, {'id': 'same-rule', 'status': 'candidate' if scope == 'workspace' else 'active',
                'scope': {'kind': 'personal', 'value': '*'}, 'evidence': [evidence],
                'trigger': 'Fixture routing', 'assumption': 'Any broader record wins', 'principle': 'Nearest record wins',
                'action': 'Keep the explicitly selected rule', 'boundary': 'Fixture only', 'transfer': 'Another scope',
                'counterexample': 'A workspace candidate must not reactivate the global rule'})
        before = {str(path): path.read_bytes() for root in self.scopes.values() for path in root.rglob('*') if path.is_file()}
        result = self.cli('show', '--all-scopes')
        self.assertEqual(result.returncode, 0, result.stderr)
        result = json.loads(result.stdout)
        self.assertEqual(result['precedence'], ['workspace', 'user', 'global'])
        self.assertNotIn('same-rule', result['active_rules'])
        scoped_result = self.cli('--scope', 'user', 'show', '--all-scopes')
        self.assertEqual(scoped_result.returncode, 0, scoped_result.stderr)
        self.assertNotIn('same-rule', json.loads(scoped_result.stdout)['active_rules'])
        after = {str(path): path.read_bytes() for root in self.scopes.values() for path in root.rglob('*') if path.is_file()}
        self.assertEqual(before, after)


if __name__ == '__main__':
    unittest.main()

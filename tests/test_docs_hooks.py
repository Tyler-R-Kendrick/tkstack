import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
import check_docs as docs
import docs_hook
import setup_repo_hooks
import setup_integrations


class DocumentationHookTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / 'repo with spaces'
        self.root.mkdir()
        self.git('init', '-q')
        self.git('config', 'user.name', 'Docs fixture')
        self.git('config', 'user.email', 'docs-fixture@example.invalid')
        for folder in ['scripts', 'docs', 'src', 'harnesses/bootstrap', '.githooks']:
            (self.root / folder).mkdir(parents=True, exist_ok=True)
        for name in ['check_docs.py', 'docs_hook.py', 'setup_repo_hooks.py', 'tkstack_state.py', 'bootstrap_profiles.py']:
            shutil.copy2(ROOT / 'scripts' / name, self.root / 'scripts' / name)
        shutil.copy2(ROOT / '.githooks/pre-commit', self.root / '.githooks/pre-commit')
        for name in ['profiles.json', 'toolchains.json']:
            shutil.copyfile(ROOT / 'harnesses/bootstrap' / name, self.root / 'harnesses/bootstrap' / name)
        (self.root / 'src/cli.py').write_text("print('version one')\n")
        (self.root / 'docs/use.md').write_text('# Usage\n\nUse [the command](../src/cli.py).\n')
        (self.root / 'README.md').write_text('# Fixture\n\n[Usage](docs/use.md)\n\n' + docs.START + '\n' + docs.END + '\n')
        self.rules = {'version': 1, 'areas': {
            'cli': {'inputs': ['src/**'], 'docs': ['README.md', 'docs/use.md']},
            'maintenance': {'inputs': ['scripts/**', '.githooks/**', 'docs/docs-policy.json'], 'docs': ['README.md']}}}
        self.write_policy()
        snapshot = docs.Snapshot(self.root)
        (self.root / 'README.md').write_text('# Fixture\n\n[Usage](docs/use.md)\n\n' + docs.profile_block(snapshot) + '\n')
        docs.refresh(docs.Snapshot(self.root), ['cli', 'maintenance'], 'Reviewed initial fixture interfaces and commands')
        self.git('add', '.')
        self.git('commit', '-qm', 'Fixture baseline')

    def git(self, *args, expected=0):
        result = subprocess.run(['git', '-C', str(self.root), *args], capture_output=True, text=True)
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return result.stdout

    def write_policy(self):
        (self.root / docs.POLICY).write_text(json.dumps(self.rules))

    def snapshot(self, staged=False):
        return docs.Snapshot(self.root, staged)

    def change_source(self):
        (self.root / 'src/cli.py').write_text("print('version two')\n")

    def review(self):
        (self.root / 'docs/use.md').write_text('# Usage\n\n[The command](../src/cli.py) now prints version two.\n')
        docs.refresh(self.snapshot(), ['cli'], 'Verified the new command output and updated its usage')

    def test_worktree_source_drift_touches_and_explicit_review(self):
        self.assertEqual(docs.check(self.snapshot()), [])
        before = (self.root / docs.LEDGER).read_bytes()
        self.change_source()
        self.assertTrue(any('cli' in error for error in docs.check(self.snapshot())))
        os.utime(self.root / 'docs/use.md')
        with self.assertRaisesRegex(ValueError, 'without a documentation edit'):
            docs.refresh(self.snapshot(), ['cli'], 'A timestamp touch is not documentation review')
        self.assertEqual((self.root / docs.LEDGER).read_bytes(), before)
        self.review()
        self.assertEqual(docs.check(self.snapshot()), [])

    def test_internal_only_change_requires_an_explicit_reasoned_exception(self):
        self.change_source()
        docs.refresh(self.snapshot(), ['cli'], 'Internal implementation change with unchanged documented invocation and output contract', no_doc_impact=True)
        self.assertEqual(docs.check(self.snapshot()), [])
        self.assertTrue(docs.load(self.snapshot(), docs.LEDGER)['areas']['cli']['no_doc_impact'])

    def test_staged_source_cannot_use_unstaged_documentation_or_receipts(self):
        self.change_source()
        self.git('add', 'src/cli.py')
        self.review()
        self.assertEqual(docs.check(self.snapshot()), [])
        self.assertTrue(docs.check(self.snapshot(True)))
        self.git('add', 'docs/use.md', docs.LEDGER)
        self.assertEqual(docs.check(self.snapshot(True)), [])
        (self.root / 'docs/use.md').write_text('[broken](missing.md)\n')
        self.assertTrue(docs.check(self.snapshot()))
        self.assertEqual(docs.check(self.snapshot(True)), [])

    def test_staged_policy_cannot_be_replaced_by_a_looser_unstaged_policy(self):
        self.change_source()
        self.git('add', 'src/cli.py')
        self.rules['areas']['cli']['inputs'] = ['does-not-exist/**']
        self.write_policy()
        with self.assertRaisesRegex(ValueError, 'refresh --all'):
            docs.refresh(self.snapshot(), ['cli'], 'A policy edit must review all areas')
        docs.refresh(self.snapshot(), ['cli', 'maintenance'], 'Reviewed the fixture policy modification', no_doc_impact=True)
        self.assertTrue(docs.check(self.snapshot(True)))

    def test_generated_readme_block_and_local_links_are_checked_from_the_snapshot(self):
        path = self.root / 'harnesses/bootstrap/toolchains.json'
        value = json.loads(path.read_text())
        value['node_version'] = '99.0.0'
        path.write_text(json.dumps(value))
        self.assertTrue(any('versions are stale' in error for error in docs.check(self.snapshot())))
        (self.root / 'README.md').write_text((self.root / 'README.md').read_text().replace('[Usage](docs/use.md)', '[Usage](docs/missing.md)'))
        self.assertTrue(any('missing local link' in error for error in docs.check(self.snapshot())))

    def test_add_delete_and_executable_mode_changes_affect_the_source_snapshot(self):
        path = self.root / 'src/cli.py'
        path.chmod(0o755)
        self.assertTrue(docs.check(self.snapshot()))
        path.chmod(0o644)
        path.unlink()
        self.assertTrue(docs.check(self.snapshot()))
        path.write_text("print('version one')\n")
        (self.root / 'src/second.py').write_text("print('new public command')\n")
        self.assertTrue(docs.check(self.snapshot()))

    def test_real_precommit_blocks_stale_index_and_accepts_reviewed_staged_content(self):
        setup_repo_hooks.setup(self.root)
        self.change_source()
        self.git('add', 'src/cli.py')
        self.git('commit', '-qm', 'Stale docs must fail', expected=1)
        self.review()
        self.git('commit', '-qm', 'Unstaged repair must still fail', expected=1)
        self.git('add', 'docs/use.md', docs.LEDGER)
        self.git('commit', '-qm', 'Reviewed docs and implementation')
        self.assertEqual(docs.check(self.snapshot(True)), [])

    def test_existing_precommit_is_chained_and_restored_without_touching_other_hooks(self):
        directory = self.root / '.git/hooks'
        previous = '#!/bin/sh\nprintf previous > "$(git rev-parse --show-toplevel)/previous-ran"\n'
        (directory / 'pre-commit').write_text(previous)
        (directory / 'pre-commit').chmod(0o755)
        (directory / 'post-commit').write_text('unrelated')
        setup_repo_hooks.setup(self.root)
        self.git('commit', '--allow-empty', '-qm', 'Chained hook')
        self.assertEqual((self.root / 'previous-ran').read_text(), 'previous')
        setup_repo_hooks.setup(self.root, uninstall=True)
        self.assertEqual((directory / 'pre-commit').read_text(), previous)
        self.assertEqual((directory / 'post-commit').read_text(), 'unrelated')

    def test_other_hook_managers_and_modified_dispatchers_are_preserved(self):
        self.git('config', 'core.hooksPath', '.another-manager')
        with self.assertRaisesRegex(ValueError, 'managed elsewhere'):
            setup_repo_hooks.setup(self.root)
        self.assertEqual(self.git('config', '--get', 'core.hooksPath').strip(), '.another-manager')
        self.git('config', '--unset', 'core.hooksPath')
        setup_repo_hooks.setup(self.root)
        hook = self.root / '.git/hooks/pre-commit'
        hook.write_text('operator modified hook')
        with self.assertRaisesRegex(ValueError, 'modified'):
            setup_repo_hooks.setup(self.root)
        self.assertEqual(hook.read_text(), 'operator modified hook')

    def test_native_protocols_are_scoped_bounded_and_do_not_modify_docs(self):
        self.change_source()
        before = (self.root / docs.LEDGER).read_bytes()
        for harness in ('codex', 'claude', 'cursor'):
            event = {'cwd': str(self.root), 'status': 'completed', 'loop_count': 0, 'stop_hook_active': False}
            response = docs_hook.evaluate(self.root, harness, event, self.root)
            self.assertIn('followup_message' if harness == 'cursor' else 'decision', response)
            response = docs_hook.evaluate(self.root, harness, {**event, 'loop_count': 1, 'stop_hook_active': True}, self.root)
            self.assertEqual(response, {})
            self.assertEqual(docs_hook.evaluate(self.root, harness, {'cwd': str(self.root.parent)}, self.root.parent), {})
        self.assertEqual((self.root / docs.LEDGER).read_bytes(), before)
        self.review()
        self.assertEqual(docs_hook.evaluate(self.root, 'codex', {'cwd': str(self.root), 'stop_hook_active': False}, self.root), {})

    def test_malformed_ledgers_profiles_and_loop_fields_fail_closed(self):
        for harness, event in [('codex', {'stop_hook_active': 'false'}), ('cursor', {'status': 'completed', 'loop_count': False})]:
            with self.assertRaises(ValueError):
                docs_hook.evaluate(self.root, harness, {'cwd': str(self.root), **event}, self.root)
        path = self.root / docs.LEDGER
        path.write_text('{"version":1,"areas":{"cli":null}}')
        with self.assertRaisesRegex(ValueError, 'Invalid documentation review record'):
            docs.check(self.snapshot())
        profiles = self.root / 'harnesses/bootstrap/profiles.json'
        profiles.write_text('{"version":true,"profiles":{}}')
        with self.assertRaises(ValueError):
            docs.profile_block(self.snapshot())

    def test_native_registrations_are_opt_in_to_source_project_not_home_or_other_projects(self):
        for harness in ('codex', 'claude', 'cursor'):
            ordinary = setup_integrations.hook_entries(ROOT, harness)
            scoped = setup_integrations.hook_entries(ROOT, harness, repo_docs=True)
            self.assertNotIn('repo-docs', json.dumps(ordinary))
            self.assertIn('repo-docs', json.dumps(scoped))
            self.assertIn('stop' if harness == 'cursor' else 'Stop', scoped)

    def test_sparse_worktree_check_uses_only_index_fallback_for_skipped_paths(self):
        self.git('sparse-checkout', 'init', '--cone')
        self.git('sparse-checkout', 'set', 'src')
        self.assertFalse((self.root / 'docs/use.md').exists())
        self.assertEqual(docs.check(self.snapshot()), [])
        self.assertEqual(docs.check(self.snapshot(True)), [])
        self.change_source()
        self.assertTrue(docs.check(self.snapshot()))

    def test_installer_owned_paths_normalize_but_authored_instructions_still_drift(self):
        self.rules['areas']['cli']['inputs'].append('AGENTS.md')
        path = self.root / 'AGENTS.md'
        body = '# Authored policy\n<!-- tkstack:steering:start -->\nRead /old/clone/.agents/rules.md\n<!-- tkstack:steering:end -->\n'
        path.write_text(body)
        self.write_policy()
        docs.refresh(self.snapshot(), ['cli', 'maintenance'], 'Reviewed authored policy and installer-owned path normalization', no_doc_impact=True)
        self.git('add', 'AGENTS.md', docs.POLICY, docs.LEDGER)
        path.write_text(body.replace('/old/clone', '/fresh/clone'))
        self.assertEqual(docs.check(self.snapshot()), [])
        self.git('add', 'AGENTS.md')
        self.assertEqual(docs.check(self.snapshot(True)), [])
        path.write_text(path.read_text().replace('# Authored policy', '# Changed authored policy'))
        self.assertTrue(docs.check(self.snapshot()))

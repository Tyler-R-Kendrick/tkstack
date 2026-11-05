import contextlib
import io
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
sys.path.insert(0, str(ROOT / 'src'))
import check_docs as docs
import install


class DocumentationHookTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / 'repo with spaces'
        self.root.mkdir()
        self.git('init', '-q')
        self.git('config', 'user.name', 'Docs fixture')
        self.git('config', 'user.email', 'docs-fixture@example.invalid')
        for folder in ['scripts', 'docs', 'src', '.githooks']:
            (self.root / folder).mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / 'src/check_docs.py', self.root / 'src/check_docs.py')
        shutil.copy2(ROOT / 'install.sh', self.root / 'install.sh')
        shutil.copy2(ROOT / '.githooks/pre-commit', self.root / '.githooks/pre-commit')
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
        path = self.root / 'install.sh'
        path.write_text(path.read_text().replace('PYTHON_VERSION=3.12.15', 'PYTHON_VERSION=9.9.9', 1))
        self.assertTrue(any('install pins are stale' in error for error in docs.check(self.snapshot())))
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
        install.repo_hooks(self.root)
        self.change_source()
        self.git('add', 'src/cli.py')
        self.git('commit', '-qm', 'Stale docs must fail', expected=1)
        self.review()
        self.git('commit', '-qm', 'Unstaged repair must still fail', expected=1)
        self.git('add', 'docs/use.md', docs.LEDGER)
        self.git('commit', '-qm', 'Reviewed docs and implementation')
        self.assertEqual(docs.check(self.snapshot(True)), [])

    def test_malformed_ledger_and_install_pins_fail_closed(self):
        path = self.root / docs.LEDGER
        path.write_text('{"version":1,"areas":{"cli":null}}')
        with self.assertRaisesRegex(ValueError, 'Invalid documentation review record'):
            docs.check(self.snapshot())
        script = self.root / 'install.sh'
        script.write_text(script.read_text().replace('PYTHON_VERSION=3.12.15\n', '', 1))
        with self.assertRaisesRegex(ValueError, 'install.sh is missing PYTHON_VERSION'):
            docs.profile_block(self.snapshot())

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

    def test_missing_git_uninstall_is_not_a_checkout(self):
        empty = self.root.parent / 'no-git'
        empty.mkdir()
        saved = os.environ.get('PATH')
        os.environ['PATH'] = str(empty)
        captured = io.StringIO()
        try:
            with contextlib.redirect_stdout(captured):
                result = install.repo_hooks(self.root, uninstall=True)
        finally:
            if saved is None:
                os.environ.pop('PATH', None)
            else:
                os.environ['PATH'] = saved
        self.assertIsNone(result)
        self.assertIn('skip git docs hook: not a git checkout', captured.getvalue())

    def test_dry_run_uninstall_plans_the_hook_and_leaves_it_in_place(self):
        with contextlib.redirect_stdout(io.StringIO()):
            install.repo_hooks(self.root)
        self.assertEqual(self.git('config', '--get', 'core.hooksPath').strip(), '.githooks')
        planned = io.StringIO()
        with contextlib.redirect_stdout(planned):
            install.repo_hooks(self.root, dry_run=True, uninstall=True)
        self.assertIn('Would unset', planned.getvalue())
        self.assertEqual(self.git('config', '--get', 'core.hooksPath').strip(), '.githooks')
        with contextlib.redirect_stdout(io.StringIO()):
            install.repo_hooks(self.root, uninstall=True)
        shown = subprocess.run(['git', '-C', str(self.root), 'config', '--get', 'core.hooksPath'], capture_output=True, text=True)
        self.assertNotEqual(shown.returncode, 0)
        skipped = io.StringIO()
        with contextlib.redirect_stdout(skipped):
            install.repo_hooks(self.root, dry_run=True, uninstall=True)
        self.assertIn('core.hooksPath is not .githooks', skipped.getvalue())

import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / 'skills/learn/scripts/learn.py'


class LearnHelpTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.project = Path(self.temporary.name)
        self.roots = [self.project / name / '.tkstack' for name in ('workspace', 'user', 'global')]
        self.environment = {**os.environ,
            'TKSTACK_WORKSPACE_DIR': str(self.roots[0]),
            'TKSTACK_USER_DIR': str(self.roots[1]),
            'TKSTACK_GLOBAL_DIR': str(self.roots[2]),
            'TKSTACK_STEERING_DIR': str(self.roots[0] / 'steering')}

    def invoke(self, *arguments, script=SCRIPT, expected=0):
        result = subprocess.run([sys.executable, '-B', str(script), *arguments],
            cwd=self.project, env=self.environment, text=True, capture_output=True, timeout=10)
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return result.stdout

    def assert_no_state(self):
        self.assertFalse(any(path.exists() for path in self.roots))

    def test_no_command_and_explicit_help_show_same_read_only_discovery(self):
        output = self.invoke()
        self.assertEqual(output, self.invoke('help'))
        self.assertIn('/learn help reusify', output)
        self.assertIn('$learn <command>', output)
        self.assertIn('reusify init [scope]', output)
        self.assert_no_state()

    def test_focused_help_covers_every_existing_authoring_route(self):
        sys.path.insert(0, str(SCRIPT.parent))
        import session_learning
        for name in sorted(set(session_learning.ROUTES.values()) - {'learn'}):
            with self.subTest(skill=name):
                output = self.invoke('help', name)
                self.assertTrue(output.startswith('## ' + name + '\n'))
                self.assertIn('/learn ' + name, output)
                self.assertIn('read-only', output)
                self.assertEqual(output.count('\n## '), 0)
        self.assert_no_state()

    def test_native_command_help_preserves_actual_parser_contracts(self):
        for command in ('sessions', 'capture', 'show'):
            with self.subTest(command=command):
                self.assertEqual(self.invoke('help', command), self.invoke(command, '--help'))
        self.assertIn('--input', self.invoke('help', 'capture'))
        self.assertIn('--all-scopes', self.invoke('help', 'show'))
        self.assert_no_state()

    def test_help_does_not_read_or_rewrite_existing_ledgers_or_session_data(self):
        store = self.roots[0] / 'steering'
        store.mkdir(parents=True)
        (store / 'events.jsonl').write_text('Malformed ledger that must not be parsed by help\n')
        session = self.roots[0] / 'sessions/active'
        session.mkdir(parents=True)
        (session / 'session.json').write_text('Malformed session that must not be reviewed\n')
        before = {str(path): path.read_bytes() for path in self.project.rglob('*') if path.is_file()}
        self.invoke('help')
        self.invoke('--store', str(store), 'help', 'reusify')
        self.invoke('--scope', 'global', 'help', 'codify')
        after = {str(path): path.read_bytes() for path in self.project.rglob('*') if path.is_file()}
        self.assertEqual(before, after)
        self.assertFalse(self.roots[1].exists())
        self.assertFalse(self.roots[2].exists())

    def test_unknown_topics_and_extra_arguments_fail_without_creating_state(self):
        self.invoke('help', 'inventify', expected=2)
        self.invoke('help', '../skillify', expected=2)
        self.invoke('help', 'reusify', 'init', expected=2)
        self.assert_no_state()

    def test_standalone_package_provides_guidance_without_siblings_or_repository(self):
        package = self.project / 'standalone learn'
        shutil.copytree(SCRIPT.parent.parent, package)
        script = package / 'scripts/learn.py'
        output = self.invoke('help', 'reusify', script=script)
        self.assertIn('/learn reusify init [scope]', output)
        self.assertIn('catalog helper has no `init` execution command', output)
        self.assertIn('scripts/release.lock.json', self.invoke('help', 'codify', script=script))
        self.assertFalse((package.parent / 'reusify').exists())
        self.assert_no_state()


if __name__ == '__main__':
    unittest.main()

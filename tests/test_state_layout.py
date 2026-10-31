"""Git visibility, workspace ownership, portable copies, and read-only paths."""
from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import tkstack_state as state


class StateLayoutTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.project = Path(temporary.name)
        subprocess.run(["git", "init", "-q", str(self.project)], check=True)

    def visible(self):
        result = subprocess.run(["git", "-C", str(self.project), "ls-files", "--others", "--exclude-standard"],
                                capture_output=True, text=True, check=True)
        return set(result.stdout.splitlines())

    def test_private_session_data_is_ignored_but_policy_and_catalog_are_visible(self):
        for namespace in ("sessions", "steering", "evidence", "cache", "locks"):
            directory = state.ensure_state(self.project / ".tkstack" / namespace)
            (directory / "private.json").write_text('{"session":"fixture"}')
        reuse = self.project / ".tkstack/reuse"
        reuse.mkdir()
        (reuse / "catalog.json").write_text('{"version":1,"entries":[]}')
        (reuse / "scan-session.json").write_text('{}')
        self.assertEqual(self.visible(), {".tkstack/.gitignore", ".tkstack/reuse/catalog.json"})
        policy = self.project / ".tkstack/.gitignore"
        before = policy.read_bytes()
        state.ensure_state(self.project / ".tkstack/sessions")
        self.assertEqual(policy.read_bytes(), before)

    def test_existing_ignore_rules_survive_and_private_exceptions_cannot_expose_sessions(self):
        root = self.project / ".tkstack"
        root.mkdir()
        original = "# Existing repository policy\n!notes.json\n!sessions/**\n"
        (root / ".gitignore").write_text(original)
        state.ensure_state(root / "sessions")
        (root / "sessions/raw.txt").write_text('private fixture')
        self.assertTrue((root / ".gitignore").read_text().startswith(original))
        self.assertNotIn(".tkstack/sessions/raw.txt", self.visible())
        (root / ".state-policy.lock").mkdir()
        (root / ".state-policy.lock/pid").write_text('fixture')
        self.assertNotIn(".tkstack/.state-policy.lock/pid", self.visible())

    def test_parallel_initialization_has_one_complete_stable_policy(self):
        directories = [self.project / ".tkstack" / name for name in ("sessions", "steering", "cache", "evidence")]
        with ThreadPoolExecutor(max_workers=4) as pool:
            self.assertEqual(list(pool.map(state.ensure_state, directories)), directories)
        text = (self.project / ".tkstack/.gitignore").read_text()
        self.assertEqual(text.count(state.BEGIN), 1)
        self.assertEqual(text.count(state.END), 1)
        self.assertFalse((self.project / ".tkstack/.state-policy.lock").exists())

    def test_unsafe_state_paths_fail_before_creating_data(self):
        with self.assertRaises(ValueError):
            state.ensure_state(self.project / "session-outside")
        self.assertFalse((self.project / "session-outside").exists())
        root = self.project / ".tkstack"
        root.mkdir()
        outside = self.project / "outside"
        outside.mkdir()
        (root / "escape").symlink_to(outside, target_is_directory=True)
        with self.assertRaises(ValueError):
            state.ensure_state(root / "escape/private")
        self.assertEqual(list(outside.iterdir()), [])

    def test_path_command_is_read_only_and_explicit_projects_are_exact(self):
        nested = self.project / "nested"
        nested.mkdir()
        result = subprocess.run([sys.executable, str(ROOT / "scripts/tkstack_state.py"), "path",
                                 "--project", str(nested), "--namespace", "sessions"],
                                capture_output=True, text=True, check=True)
        self.assertEqual(result.stdout.strip(), str(nested / ".tkstack/sessions"))
        self.assertFalse((nested / ".tkstack").exists())

    def test_every_custom_skill_has_the_same_storage_primitive_and_reference(self):
        canonical = (ROOT / "scripts/tkstack_state.py").read_bytes()
        for entry in (ROOT / "skills").glob("*/SKILL.md"):
            with self.subTest(skill=entry.parent.name):
                self.assertEqual((entry.parent / "scripts/tkstack_state.py").read_bytes(), canonical)
                self.assertTrue((entry.parent / "references/storage.md").is_file())

    def test_default_store_uses_current_repository_without_writing_or_home_fallback(self):
        nested = self.project / "src"
        nested.mkdir()
        with patch.object(Path, "cwd", return_value=nested), patch.dict(os.environ, {"TKSTACK_STEERING_DIR": ""}):
            self.assertEqual(state.steering_store(), self.project / ".tkstack/steering")
        self.assertFalse((self.project / ".tkstack").exists())

    def test_scoped_locations_are_explicit_and_never_fall_back(self):
        roots = {scope: self.project / scope / '.tkstack' for scope in state.SCOPES}
        overrides = {'TKSTACK_' + scope.upper() + '_DIR': str(path) for scope, path in roots.items()}
        with patch.dict(os.environ, overrides):
            self.assertEqual(state.state_roots(), roots)
            for scope, root in roots.items():
                self.assertEqual(state.state_path('steering', scope=scope), root / 'steering')
            exact = self.project / 'explicit'
            self.assertEqual(state.state_path('sessions', exact), exact / '.tkstack/sessions')
            self.assertFalse(any(root.exists() for root in roots.values()))
            with self.assertRaisesRegex(ValueError, 'only selects a workspace'):
                state.state_path('steering', exact, 'user')
        with patch.dict(os.environ, {'TKSTACK_USER_DIR': str(self.project / 'wrong-name')}):
            with self.assertRaisesRegex(ValueError, 'named .tkstack'):
                state.state_path('sessions', scope='user')

    def test_sessions_are_isolated_ignored_and_have_owned_temporary_children(self):
        with patch.dict(os.environ, {'TKSTACK_SESSION_ID': 'session-123'}):
            directory = state.session_path(project=self.project)
            self.assertEqual(state.state_path('evidence', self.project), directory / 'evidence')
            self.assertEqual(state.state_path('locks', self.project), self.project / '.tkstack/locks')
            self.assertEqual(state.state_path('cache', self.project), self.project / '.tkstack/cache')
            with state.session_tempdir(project=self.project, prefix='proof-') as scratch:
                (scratch / 'output.json').write_text('{}')
                self.assertEqual(scratch.parent, directory)
                self.assertNotIn(str((scratch / 'output.json').relative_to(self.project)), self.visible())
            self.assertFalse(scratch.exists())
            self.assertTrue(directory.is_dir())
        for identity in ('../escape', '/absolute', '.', 'x/y', 'x*', 'x' * 129):
            with self.assertRaises(ValueError):
                state.session_path(identity, self.project)

    def test_scoped_cli_and_session_paths_are_read_only_until_initialized(self):
        scoped = self.project / 'user/.tkstack'
        environment = {**os.environ, 'TKSTACK_USER_DIR': str(scoped)}
        command = [sys.executable, str(ROOT / 'scripts/tkstack_state.py'), 'path', '--scope', 'user', '--session', 'one', '--namespace', 'sessions']
        result = subprocess.run(command, env=environment, capture_output=True, text=True, check=True)
        self.assertEqual(result.stdout.strip(), str(scoped / 'sessions/one'))
        self.assertFalse(scoped.exists())
        command[2] = 'init'
        subprocess.run(command, env=environment, capture_output=True, text=True, check=True)
        self.assertTrue((scoped / '.gitignore').is_file())
        self.assertIn('/sessions/', (scoped / '.gitignore').read_text())

    def test_session_symlink_cannot_redirect_writes_into_another_namespace(self):
        root = self.project / '.tkstack'
        state.ensure_state(root / 'steering')
        (root / 'sessions').symlink_to(root / 'steering', target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'symlinks'):
            state.session_path('one', self.project)

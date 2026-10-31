"""Dotfiles startup, source-only replay, scoped configs, and bounded failure handling."""
from contextlib import redirect_stdout
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import shlex
import subprocess
import sys
import tarfile
import tempfile
import threading
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
import bootstrap
import bootstrap_shell
import bootstrap_toolchains
import harness_paths
import setup_integrations
import steering_adapter


def report(output):
    decoder = json.JSONDecoder()
    for index, char in enumerate(output):
        if char == '{':
            try:
                value, end = decoder.raw_decode(output[index:])
                if isinstance(value, dict) and 'profile' in value:
                    return value
            except ValueError:
                pass
    raise AssertionError(output[-3000:])


class BootstrapTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.target = self.base / 'home with spaces'
        self.workspace = self.base / 'workspace with spaces'

    def invoke(self, *arguments, expected=0):
        result = subprocess.run([str(ROOT / 'install.sh'), '--target', str(self.target), '--workspace', str(self.workspace),
                                 '--offline', *arguments], cwd=self.base, env={**os.environ, 'STITCH_API_KEY': '', 'OPEN_DESIGN_CLI': ''}, capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return report(result.stdout)

    def test_shell_entrypoint_finds_checkout_from_other_cwd_and_preview_is_read_only(self):
        result = self.invoke('--profile', 'codex-cloud', '--dry-run')
        self.assertEqual(result['harnesses'], ['codex'])
        self.assertFalse(result['copilot'])
        self.assertEqual(result['status'], 'planned')
        self.assertFalse(self.target.exists())
        self.assertFalse(self.workspace.exists())

    def test_dotfiles_install_is_repeatable_preserves_settings_and_initializes_state(self):
        (self.target / '.codex').mkdir(parents=True)
        (self.target / '.codex/config.toml').write_text('model = "existing-model"\n')
        (self.target / '.bashrc').write_text('# Existing user shell\nexport KEEP_ME=yes\n')
        first = self.invoke()
        self.assertEqual(first['status'], 'configured-with-requirements')
        self.assertEqual(first['stages']['verification'], 'passed')
        self.assertTrue((self.target / '.agents/skills/graphify').is_symlink())
        self.assertTrue((self.target / '.claude/skills/learn').is_symlink())
        self.assertTrue((self.target / '.cursor/rules/graphify.mdc').is_symlink())
        self.assertTrue((self.workspace / '.github/skills/lever').is_symlink())
        self.assertTrue((self.target / '.tkstack/steering/rules.md').is_file())
        self.assertTrue((self.workspace / '.tkstack/.gitignore').is_file())
        for state in (self.target / '.tkstack', self.workspace / '.tkstack'):
            runner = state / 'tkstack'
            self.assertTrue(os.access(runner, os.X_OK))
            result = subprocess.run([str(runner), 'help'], cwd=self.base, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('compiled skills/workflows', result.stdout)
        self.assertIn('existing-model', (self.target / '.codex/config.toml').read_text())
        before = {str(path.relative_to(self.target)): path.read_bytes() for path in self.target.rglob('*') if path.is_file() and not path.is_symlink()}
        second = self.invoke()
        self.assertEqual(second['stages']['verification'], 'passed')
        after = {str(path.relative_to(self.target)): path.read_bytes() for path in self.target.rglob('*') if path.is_file() and not path.is_symlink()}
        self.assertEqual(before, after)
        self.assertEqual((self.target / '.bashrc').read_text().count(bootstrap_shell.BEGIN), 1)
        self.assertTrue((self.target / '.bashrc').read_text().startswith('# Existing user shell\n'))
        self.invoke('--check')

    def test_codex_cloud_installs_only_selected_host_and_check_detects_shell_drift(self):
        self.invoke('--profile', 'codex-cloud')
        self.assertTrue((self.target / '.codex/AGENTS.md').is_file())
        self.assertFalse((self.target / '.claude').exists())
        self.assertFalse((self.target / '.cursor').exists())
        self.assertFalse((self.workspace / '.github').exists())
        (self.target / '.bashrc').write_text('Foreign replacement\n')
        result = self.invoke('--profile', 'codex-cloud', '--check', expected=1)
        self.assertIn('Shell startup pointers are missing or stale', result['verification_errors'])
        self.assertEqual((self.target / '.bashrc').read_text(), 'Foreign replacement\n')

    def test_fresh_dotfiles_copy_bootstraps_without_any_existing_state_or_generated_views(self):
        source = self.base / 'fresh dotfiles'
        def ignored(directory, names):
            if Path(directory).is_relative_to(ROOT / 'vendor'):
                return set()
            skip = {'__pycache__', 'node_modules'}
            if Path(directory) == ROOT:
                skip |= {'.git', '.tkstack', '.agents', '.claude', '.cursor', '.codex', '.mcp.json'}
            if Path(directory) == ROOT / '.github':
                skip |= {'skills', 'docs', 'templates', 'config', 'automations'}
            return set(names) & skip
        shutil.copytree(ROOT, source, symlinks=True, ignore=ignored)
        (source / '.tkstack/reuse').mkdir(parents=True)
        shutil.copyfile(ROOT / '.tkstack/.gitignore', source / '.tkstack/.gitignore')
        shutil.copyfile(ROOT / '.tkstack/reuse/catalog.json', source / '.tkstack/reuse/catalog.json')
        environment = {**os.environ, 'STITCH_API_KEY': '', 'OPEN_DESIGN_CLI': ''}
        command = [str(source / 'install.sh'), '--profile', 'codex-cloud', '--target', str(self.target),
                   '--workspace', str(self.workspace), '--offline']
        result = subprocess.run(command, cwd=self.base, env=environment, capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(report(result.stdout)['stages']['verification'], 'passed')
        link = self.target / '.agents/skills/graphify'
        self.assertTrue(link.is_symlink())
        self.assertTrue(link.resolve().is_relative_to(source))
        self.assertTrue((link / 'references/query.md').is_file())
        self.assertIn(str(source), (self.target / '.codex/AGENTS.md').read_text())
        checked = subprocess.run([*command, '--check'], cwd=self.base, env=environment, capture_output=True, text=True, timeout=60)
        self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)

    def test_collision_fails_before_initialization_or_shell_changes(self):
        collision = self.target / '.agents/skills/learn'
        collision.mkdir(parents=True)
        marker = collision / 'mine.txt'
        marker.write_text('Keep this')
        result = subprocess.run([str(ROOT / 'install.sh'), '--target', str(self.target), '--workspace', str(self.workspace),
                                 '--profile', 'codex-cloud', '--offline'], cwd=self.base, capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn('Refusing to replace', result.stderr)
        self.assertEqual(marker.read_text(), 'Keep this')
        self.assertFalse(self.workspace.exists())
        self.assertFalse((self.target / '.bashrc').exists())

    def test_strict_reports_known_missing_requirements_without_interactive_auth(self):
        self.invoke('--profile', 'codex-cloud')
        result = self.invoke('--profile', 'codex-cloud', '--check', '--strict', expected=1)
        self.assertEqual(result['status'], 'invalid')
        self.assertTrue(any(item['integration'] in ('stitch', 'open-design') for item in result['requirements']))
        fal = next(item for item in result['requirements'] if item['integration'] == 'fal')
        self.assertFalse(fal['blocking'])

    def test_codex_home_is_honored_only_for_the_real_home_scope(self):
        configured = self.base / 'managed codex'
        with patch.object(Path, 'home', return_value=self.target), patch.dict(os.environ, {'CODEX_HOME': str(configured)}):
            self.assertEqual(harness_paths.codex_directory(self.target, 'home'), configured)
            self.assertEqual(harness_paths.codex_directory(self.workspace, 'home'), self.workspace / '.codex')
            self.assertEqual(harness_paths.codex_directory(self.target, 'project'), self.target / '.codex')
            plan = setup_integrations.configuration_plan(ROOT, self.target, ['codex'], 'home')
            paths = {path for path, _, _ in plan}
            self.assertIn(configured / 'config.toml', paths)
            self.assertIn(configured / 'hooks.json', paths)
            instructions = steering_adapter.instruction_plan(ROOT, self.target, ['codex'], 'home')
            self.assertIn(configured / 'AGENTS.md', {path for path, _, _ in instructions})
        self.assertFalse(configured.exists())

    def test_user_state_override_applies_to_real_home_without_leaking_into_isolated_targets(self):
        configured = self.base / 'personal/.tkstack'
        with patch.object(Path, 'home', return_value=self.target), patch.dict(os.environ, {'TKSTACK_USER_DIR': str(configured)}):
            roots = bootstrap.initialization_roots(self.target, self.workspace, 'home')
            self.assertEqual(roots, [configured, self.workspace / '.tkstack'])
            alternate = self.base / 'isolated-home'
            self.assertEqual(bootstrap.initialization_roots(alternate, self.workspace, 'home')[0], alternate / '.tkstack')
            self.assertEqual(bootstrap.initialization_roots(self.target, self.workspace, 'project')[0], self.target / '.tkstack')
        self.assertFalse(configured.exists())

    def test_shell_environment_is_safe_idempotent_and_does_not_shadow_system_od(self):
        environment, _ = bootstrap_toolchains.resolve(ROOT, install=False)
        root = self.base / 'dotfiles with spaces'
        env_file = bootstrap_shell.publish(root, environment)
        self.assertFalse((root / '.tkstack/bin/od').exists())
        self.assertTrue((root / '.tkstack/bin/hf').is_file())
        source = '. ' + shlex.quote(str(env_file))
        program = source + '\n' + source + '\nprintf "%s" "$PATH"'
        result = subprocess.run(['bash', '-c', program], env=environment, capture_output=True, text=True, check=True)
        self.assertEqual(result.stdout.split(os.pathsep).count(str(root / '.tkstack/bin')), 1)
        bootstrap_shell.check(root)
        (root / '.tkstack/bin/graphify').chmod(0o644)
        with self.assertRaisesRegex(ValueError, 'missing or stale'):
            bootstrap_shell.check(root)

    def test_bootstrap_lock_releases_after_process_death(self):
        root = self.base / 'lock-owner'
        program = "import sys;from pathlib import Path;sys.path.insert(0,sys.argv[1]);import bootstrap;bootstrap.ROOT=Path(sys.argv[2]);\nwith bootstrap.ownership():\n print('locked',flush=True);sys.stdin.read()"
        child = subprocess.Popen([sys.executable, '-B', '-c', program, str(ROOT / 'scripts'), str(root)],
                                 stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            self.assertEqual(child.stdout.readline().strip(), 'locked')
            with patch.object(bootstrap, 'ROOT', root):
                with self.assertRaisesRegex(ValueError, 'Another bootstrap'):
                    with bootstrap.ownership():
                        pass
            child.terminate()
            child.wait(timeout=5)
            with patch.object(bootstrap, 'ROOT', root), bootstrap.ownership():
                self.assertTrue((root / '.tkstack/locks/bootstrap.lock').is_file())
        finally:
            if child.poll() is None:
                child.kill()
                child.wait()
            child.stdin.close()
            child.stdout.close()
            child.stderr.close()

    def test_runtime_failure_does_not_skip_other_workers_or_config_verification(self):
        root = self.base / 'mini-source'
        (root / 'harnesses').mkdir(parents=True)
        (root / 'vendor').mkdir()
        (root / 'sources.lock.json').write_text('{"version":1,"sources":{}}')
        (root / 'harnesses/integrations.json').write_text(json.dumps({'tools': {'rtk': {'kind': 'binary'}, 'graphify': {'kind': 'binary'}}, 'mcp': {}}))
        args = bootstrap.parser().parse_args(['--target', str(self.target), '--workspace', str(self.workspace), '--no-toolchains', '--no-copilot', '--no-shell', '--jobs', '2'])
        barrier = threading.Barrier(2)
        finished, configured = set(), []
        mutex = threading.Lock()
        def execute(arguments, environment, log=None, timeout=120):
            if '--runtimes-only' in arguments:
                name = arguments[arguments.index('--runtime') + 1]
                barrier.wait(timeout=5)
                with mutex: finished.add(name)
                if name == 'rtk': raise ValueError('fixture runtime failure')
            elif Path(arguments[2]).name == 'install.py' and '--dry-run' not in arguments:
                configured.append(set(finished))
            return subprocess.CompletedProcess(arguments, 0, stdout='')
        statuses = {'rtk': {'runtime': 'missing'}, 'graphify': {'runtime': 'available'}}
        with patch.object(bootstrap, 'ROOT', root), patch.object(bootstrap_toolchains, 'resolve', return_value=(dict(os.environ), {})), \
             patch.object(bootstrap, 'execute', side_effect=execute), patch.object(bootstrap, 'runtime_status', return_value=statuses), \
             redirect_stdout(io.StringIO()) as output:
            code = bootstrap.run(args)
        value = report(output.getvalue())
        self.assertEqual(code, 1)
        self.assertEqual(set(value['runtime_failures']), {'rtk'})
        self.assertEqual(configured, [{'rtk', 'graphify'}])
        self.assertEqual(value['stages']['verification'], 'passed')
        with patch.object(bootstrap, 'ROOT', root), bootstrap.ownership():
            self.assertTrue((root / '.tkstack/locks/bootstrap.lock').is_file())


class ToolchainTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        (self.root / 'harnesses/bootstrap').mkdir(parents=True)
        self.recipe = json.loads((ROOT / 'harnesses/bootstrap/toolchains.json').read_text())
        self.bin = self.root / 'provided-bin'
        self.bin.mkdir()
        uv = self.bin / 'uv'
        uv.write_text('#!/bin/sh\nprintf "uv 0.12.23\\n"\n')
        uv.chmod(0o755)
        self.environment = {**os.environ, 'PATH': str(self.bin), 'TASK_TEST_SELECTOR': 'unchanged'}

    def archive(self, malicious=False):
        stream = io.BytesIO()
        prefix = 'node-fixture'
        with tarfile.open(fileobj=stream, mode='w:gz') as archive:
            for name, payload in [('bin/node', b'#!/bin/sh\nprintf "v24.19.0\\n"\n'), ('bin/npm', b'#!/bin/sh\nprintf "11.9.0\\n"\n')]:
                path = '../escape' if malicious else prefix + '/' + name
                item = tarfile.TarInfo(path)
                item.size, item.mode = len(payload), 0o755
                archive.addfile(item, io.BytesIO(payload))
        raw = stream.getvalue()
        import platform
        host = platform.system().lower() + '-' + {'arm64': 'aarch64', 'amd64': 'x86_64'}.get(platform.machine().lower(), platform.machine().lower())
        self.recipe['node_platforms'] = {host: {'url': 'https://nodejs.org/fixture', 'sha256': hashlib.sha256(raw).hexdigest(), 'prefix': prefix}}
        return raw

    def write_recipe(self):
        (self.root / 'harnesses/bootstrap/toolchains.json').write_text(json.dumps(self.recipe))

    def test_absent_toolchain_discovery_does_not_initialize_state(self):
        self.write_recipe()
        environment, status = bootstrap_toolchains.resolve(self.root, self.environment, install=False)
        self.assertEqual(status['node']['status'], 'missing')
        self.assertEqual(environment['TASK_TEST_SELECTOR'], 'unchanged')
        self.assertFalse((self.root / '.tkstack').exists())

    def test_verified_node_archive_installs_privately_and_is_reused_without_download(self):
        raw = self.archive()
        self.write_recipe()
        with patch('urllib.request.urlopen', return_value=io.BytesIO(raw)) as fetch:
            environment, status = bootstrap_toolchains.resolve(self.root, self.environment, install=True)
            self.assertEqual(fetch.call_count, 1)
        self.assertEqual(status['node']['status'], 'available')
        self.assertEqual(environment['TASK_TEST_SELECTOR'], 'unchanged')
        self.assertEqual(self.environment['PATH'], str(self.bin))
        with patch('urllib.request.urlopen', side_effect=AssertionError('no second download')):
            _, repeated = bootstrap_toolchains.resolve(self.root, self.environment, install=True)
        self.assertEqual(repeated['node']['status'], 'available')

    def test_checksum_and_traversal_fail_without_publishing_a_toolchain(self):
        raw = self.archive()
        for item in self.recipe['node_platforms'].values(): item['sha256'] = '0' * 64
        self.write_recipe()
        with patch('urllib.request.urlopen', return_value=io.BytesIO(raw)):
            with self.assertRaisesRegex(ValueError, 'checksum'):
                bootstrap_toolchains.resolve(self.root, self.environment, install=True)
        self.assertFalse((self.root / '.tkstack/runtime/toolchains/node-24.19.0').exists())
        raw = self.archive(malicious=True)
        self.write_recipe()
        with patch('urllib.request.urlopen', return_value=io.BytesIO(raw)):
            with self.assertRaisesRegex(ValueError, 'Unexpected path'):
                bootstrap_toolchains.resolve(self.root, self.environment, install=True)
        self.assertFalse((self.root / 'escape').exists())


if __name__ == '__main__':
    unittest.main()

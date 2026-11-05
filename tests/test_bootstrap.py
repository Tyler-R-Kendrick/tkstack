"""install.sh obtains a checkout before it links skills."""
import os
from pathlib import Path
import subprocess
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from installer_stubs import GIT_CLONE_STUB  # noqa: E402


ROOT = Path(__file__).resolve().parent.parent


class InstallerCheckoutTests(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)

    def test_downloaded_installer_clones_into_the_user_share_directory(self):
        home = self.base / 'remote-home'
        home.mkdir()
        bin_dir = self.base / 'fake-bin'
        bin_dir.mkdir()
        log = self.base / 'git.log'
        script = self.base / 'downloaded-install.sh'
        script.write_text((ROOT / 'install.sh').read_text())
        script.chmod(0o755)
        (bin_dir / 'git').write_text(GIT_CLONE_STUB)
        (bin_dir / 'git').chmod(0o755)
        env = {**os.environ, 'HOME': str(home), 'GIT_LOG': str(log), 'PATH': str(bin_dir) + os.pathsep + os.environ['PATH']}
        result = subprocess.run(['bash', str(script), '--dry-run'], cwd=self.base, env=env, capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('local-install --dry-run', result.stdout)
        self.assertIn('clone', log.read_text())
        self.assertTrue((home / '.local/share/tkstack/install.sh').is_file())
        result = subprocess.run(['bash', str(script), '--check'], cwd=self.base, env=env, capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('pull --ff-only', log.read_text())
        self.assertIn('remote get-url origin', log.read_text())
        self.assertIn('local-install --check', result.stdout)

    def test_git_pull_failure_stops_with_a_fast_forward_message(self):
        home = self.base / 'remote-home'
        home.mkdir()
        bin_dir = self.base / 'fake-bin'
        bin_dir.mkdir()
        log = self.base / 'git.log'
        script = self.base / 'downloaded-install.sh'
        script.write_text((ROOT / 'install.sh').read_text())
        script.chmod(0o755)
        (bin_dir / 'git').write_text(GIT_CLONE_STUB)
        (bin_dir / 'git').chmod(0o755)
        env = {**os.environ, 'HOME': str(home), 'GIT_LOG': str(log), 'PATH': str(bin_dir) + os.pathsep + os.environ['PATH']}
        first = subprocess.run(['bash', str(script), '--dry-run'], cwd=self.base, env=env, capture_output=True, text=True, timeout=20)
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        failed = subprocess.run(['bash', str(script), '--check'], cwd=self.base, env={**env, 'GIT_PULL_STATUS': '1'}, capture_output=True, text=True, timeout=20)
        self.assertNotEqual(failed.returncode, 0)
        self.assertIn('git pull --ff-only failed', failed.stderr)
        self.assertIn('stash', failed.stderr)
        self.assertNotIn('--dry-run', failed.stderr)
        self.assertNotIn('local-install', failed.stdout)

    def test_planted_checkout_is_refused(self):
        home = self.base / 'remote-home'
        dest = home / '.local/share/tkstack'
        (dest / 'scripts').mkdir(parents=True)
        (dest / 'scripts/install.py').write_text('print(1)\n')
        (dest / 'install.sh').write_text('#!/bin/sh\necho PLANTED\n')
        (dest / 'install.sh').chmod(0o755)
        script = self.base / 'downloaded-install.sh'
        script.write_text((ROOT / 'install.sh').read_text())
        script.chmod(0o755)
        env = {**os.environ, 'HOME': str(home)}
        result = subprocess.run(['bash', str(script)], cwd=self.base, env=env, capture_output=True, text=True, timeout=20)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Refusing to run it', result.stderr)
        self.assertNotIn('PLANTED', result.stdout)


if __name__ == '__main__':
    unittest.main()

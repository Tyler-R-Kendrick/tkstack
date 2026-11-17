import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch


MODULE = Path(__file__).resolve().parents[1] / "skills/hill-climb/scripts/experiment_runner.py"
spec = importlib.util.spec_from_file_location("experiment_runner", MODULE)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class LocalTrialTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name) / "repo"
        self.repo.mkdir()
        self.git("init", "-q")
        (self.repo / "run.py").write_text("from pathlib import Path\nprint(Path('value.txt').read_text())\n")
        (self.repo / "value.txt").write_text("original")
        self.git("add", "run.py", "value.txt")
        self.git("-c", "user.name=Test", "-c", "user.email=t@example.invalid", "commit", "-qm", "baseline")
        self.commit = self.git("rev-parse", "HEAD")
        self.tree = self.git("rev-parse", "HEAD^{tree}")
        self.registry = {"component": {"argv": [sys.executable, "run.py"], "cwd": "."}}

    def git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.repo), *args], text=True).strip()

    def run_target(self, **overrides):
        values = dict(repo=self.repo, commit=self.commit, expected_tree=self.tree,
                      registry=self.registry, allowed_targets=["component"], target="component")
        values.update(overrides)
        return runner.run_trial(**values)

    def test_frozen_tree_executes_and_preserves_dirty_source(self):
        (self.repo / "value.txt").write_text("dirty")
        first = self.run_target()
        second = self.run_target()
        self.assertEqual(first["status"], "passed")
        self.assertEqual(first["stdout"], "original\n")
        self.assertEqual(second["stdout"], first["stdout"])
        self.assertEqual(first["commit"], self.commit)
        self.assertEqual(first["tree"], self.tree)
        self.assertEqual((self.repo / "value.txt").read_text(), "dirty")

    def test_export_uses_raw_tree_despite_archive_attributes(self):
        (self.repo / ".gitattributes").write_text("value.txt export-ignore\n")
        self.git("add", ".gitattributes")
        self.git("-c", "user.name=Test", "-c", "user.email=t@example.invalid", "commit", "-qm", "attributes")
        self.commit = self.git("rev-parse", "HEAD")
        self.tree = self.git("rev-parse", "HEAD^{tree}")
        result = self.run_target()
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["stdout"], "original\n")

    def test_lfs_pointer_is_an_explicit_infrastructure_error(self):
        (self.repo / "value.txt").write_text("version https://git-lfs.github.com/spec/v1\noid sha256:abc\nsize 3\n")
        self.git("add", "value.txt")
        self.git("-c", "user.name=Test", "-c", "user.email=t@example.invalid", "commit", "-qm", "pointer")
        self.commit = self.git("rev-parse", "HEAD")
        self.tree = self.git("rev-parse", "HEAD^{tree}")
        result = self.run_target()
        self.assertEqual(result["status"], "infra_error")
        self.assertIn("LFS", result["error"])

    def test_only_declared_known_target_can_run(self):
        self.registry["other"] = {"argv": [sys.executable, "-c", "print('other')"], "cwd": "."}
        with self.assertRaises(ValueError):
            self.run_target(target="other")
        with self.assertRaises(ValueError):
            self.run_target(target="unknown", allowed_targets=["unknown"])
        with self.assertRaises(ValueError):
            self.run_target(registry={"component": {"argv": [sys.executable], "cwd": "../outside"}})
        with self.assertRaises(ValueError):
            self.run_target(registry={"component": {"argv": [""], "cwd": "."}})

    def test_different_tree_is_never_executed(self):
        result = self.run_target(expected_tree="0" * len(self.tree))
        self.assertEqual(result["status"], "infra_error")
        self.assertIsNone(result["exit_code"])
        self.assertIn("tree", result["error"].lower())

    def test_failure_timeout_and_launch_errors_are_distinct(self):
        self.registry["component"]["argv"] = [sys.executable, "-c", "import sys; print('bad'); sys.exit(7)"]
        failed = self.run_target()
        self.assertEqual((failed["status"], failed["exit_code"], failed["stdout"]), ("failed", 7, "bad\n"))
        self.registry["component"]["argv"] = [sys.executable, "-c", "import time; time.sleep(5)"]
        self.assertEqual(self.run_target(timeout=0.1)["status"], "timeout")
        self.registry["component"]["argv"] = ["executable-that-does-not-exist-23"]
        self.assertEqual(self.run_target()["status"], "infra_error")

    @unittest.skipUnless(sys.platform.startswith("linux") and hasattr(os, "waitid") and hasattr(os, "WNOWAIT"), "requires POSIX non-reaping wait")
    def test_success_kills_closed_pipe_descendant_before_return(self):
        root = Path(self.temp.name)
        ready, release, escaped = root / "child.pid", root / "release", root / "escaped"
        self.addCleanup(release.touch)
        child = ("import os,time; from pathlib import Path; "
                 f"Path({str(ready)!r}).write_text(str(os.getpid())); "
                 f"p=Path({str(release)!r}); "
                 "exec('while not p.exists():\\n time.sleep(0.01)'); "
                 f"Path({str(escaped)!r}).write_text('alive')")
        parent = ("import subprocess,sys,time; from pathlib import Path; "
                  f"subprocess.Popen([sys.executable,'-c',{child!r}],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); "
                  f"p=Path({str(ready)!r}); "
                  "exec('while not p.exists():\\n time.sleep(0.01)')")
        self.registry["component"]["argv"] = [sys.executable, "-c", parent]
        result = self.run_target(timeout=5)
        self.assertEqual(result["status"], "passed")
        pid = int(ready.read_text())
        release.write_text("go")
        deadline = time.monotonic() + 2
        stopped = False
        while time.monotonic() < deadline:
            stat = Path(f"/proc/{pid}/stat")
            try:
                state = stat.read_text().split()[2]
            except FileNotFoundError:
                stopped = True
                break
            if state == "Z":
                stopped = True
                break
            time.sleep(0.01)
        self.assertTrue(stopped, "background process remained live after successful trial")
        self.assertFalse(escaped.exists())

    def test_output_capture_is_bounded_with_total_counts(self):
        self.registry["component"]["argv"] = [sys.executable, "-c", "import sys; sys.stdout.write('A'*10000); sys.stderr.write('B'*10000)"]
        result = self.run_target(max_output_bytes=64)
        self.assertEqual(result["status"], "passed")
        self.assertEqual(len(result["stdout"]), 64)
        self.assertEqual(len(result["stderr"]), 64)
        self.assertEqual(result["stdout_bytes"], 10000)
        self.assertTrue(result["stdout_truncated"])
        self.assertTrue(result["stderr_truncated"])

    @unittest.skipUnless(hasattr(os, "symlink"), "symlinks unavailable")
    def test_escaping_symlink_is_rejected(self):
        (self.repo / "unsafe").symlink_to("../../outside")
        self.git("add", "unsafe")
        self.git("-c", "user.name=Test", "-c", "user.email=t@example.invalid", "commit", "-qm", "unsafe")
        self.commit = self.git("rev-parse", "HEAD")
        self.tree = self.git("rev-parse", "HEAD^{tree}")
        result = self.run_target()
        self.assertEqual(result["status"], "infra_error")
        self.assertIn("symlink", result["error"].lower())

    def test_expiry_during_export_never_spawns_target(self):
        clock = [100.0]
        def export(repo, commit, root):
            clock[0] = 106.0
        with patch.object(runner.time, "monotonic", side_effect=lambda: clock[0]), \
             patch.object(runner, "_materialize", side_effect=export), \
             patch.object(runner, "_execute") as execute:
            result = self.run_target(deadline=105.0)
        self.assertEqual(result["status"], "timeout")
        self.assertIn("before dispatch", result["error"])
        execute.assert_not_called()

    def test_deadline_caps_execution_timeout(self):
        clock = [100.0]
        def execute(argv, cwd, home, timeout, maximum, snapshot_root):
            self.assertEqual(timeout, 5.0)
            return {"status": "passed", "exit_code": 0}
        with patch.object(runner.time, "monotonic", side_effect=lambda: clock[0]), \
             patch.object(runner, "_materialize"), \
             patch.object(runner, "_execute", side_effect=execute):
            result = self.run_target(deadline=105.0, timeout=30)
        self.assertEqual(result["status"], "passed")

    def test_invalid_limits_and_abbreviated_objects_are_rejected(self):
        for kwargs in ({"timeout": 0}, {"timeout": float("nan")}, {"max_output_bytes": -1}, {"commit": self.commit[:7]}, {"deadline": float("nan")}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                self.run_target(**kwargs)


if __name__ == "__main__":
    unittest.main()

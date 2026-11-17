"""Real local Git behavior for isolated experiment arms."""
import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile
import threading
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location(
    "experiment_git", ROOT / "skills/hill-climb/scripts/experiment_git.py"
)
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


def git(path, *args):
    return subprocess.check_output(
        ["git", "-C", str(path), *args],
        text=True, stderr=subprocess.PIPE
    ).strip()


class GitExperimentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / "source"
        self.source.mkdir()
        git(self.source, "init", "-q", "-b", "main")
        (self.source / "feature.txt").write_text("baseline\n")
        (self.source / "outside.txt").write_text("unchanged\n")
        git(self.source, "add", ".")
        git(self.source, "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
            "commit", "-qm", "initial")
        self.base = git(self.source, "rev-parse", "HEAD")
        self.experiment = module.GitExperiment.create(
            self.source, self.root / "experiments"
        )

    def candidate(self, arm, value):
        worktree = self.experiment.allocate("trial", arm, self.base)
        (worktree / "feature.txt").write_text(value)
        candidate = self.experiment.freeze("trial", arm, ["feature.txt"], "candidate")
        return worktree, candidate

    def test_source_is_unmodified_and_arm_commits_are_immutable(self):
        (self.source / "outside.txt").write_text("local user work\n")
        path, result = self.candidate("one", "first\n")
        self.assertEqual(git(self.source, "rev-parse", "HEAD"), self.base)
        self.assertEqual((self.source / "outside.txt").read_text(), "local user work\n")
        self.assertEqual(git(path, "show", result["commit"] + ":feature.txt"), "first")
        self.assertEqual(git(path, "rev-parse", result["commit"] + "^{tree}"), result["tree"])
        self.assertEqual(module.GitExperiment.open(self.root / "experiments").repo,
                         self.experiment.repo)

    def test_freeze_rejects_out_of_scope_and_ignored_files(self):
        path = self.experiment.allocate("trial", "one", self.base)
        (path / "outside.txt").write_text("bad\n")
        with self.assertRaisesRegex(ValueError, "scope"):
            self.experiment.freeze("trial", "one", ["feature.txt"], "candidate")
        git(path, "checkout", "--", "outside.txt")
        (path / ".gitignore").write_text("ignored\n")
        git(path, "add", ".gitignore")
        git(path, "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
            "commit", "-qm", "change index")
        (path / "ignored").write_text("unexpected\n")
        with self.assertRaisesRegex(ValueError, "scope|ignored"):
            self.experiment.freeze("trial", "one", ["feature.txt"], "candidate")

    def test_guarded_promotion_rejects_stale_and_unrelated_history(self):
        _, one = self.candidate("one", "one\n")
        _, two = self.candidate("two", "two\n")
        self.experiment.initialize_integration("trial", self.base)
        self.experiment.promote("trial", self.base, one["commit"])
        with self.assertRaises((ValueError, RuntimeError)):
            self.experiment.promote("trial", self.base, two["commit"])
        self.assertEqual(self.experiment.resolve_integration("trial"), one["commit"])
        with self.assertRaises((ValueError, RuntimeError)):
            self.experiment.promote("trial", one["commit"], two["commit"])

    def test_competing_promotions_have_one_winner(self):
        _, one = self.candidate("one", "one\n")
        _, two = self.candidate("two", "two\n")
        self.experiment.initialize_integration("trial", self.base)
        barrier = threading.Barrier(2)
        outcomes = []
        def promote(candidate):
            barrier.wait()
            try:
                self.experiment.promote("trial", self.base, candidate)
                outcomes.append("won")
            except (ValueError, RuntimeError):
                outcomes.append("lost")
        threads = [threading.Thread(target=promote, args=(candidate["commit"],))
                   for candidate in (one, two)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertCountEqual(outcomes, ["won", "lost"])

    def test_retirement_archives_restorable_source_and_rejects_dirty(self):
        path, candidate = self.candidate("one", "one\n")
        (path / "untracked").write_text("important")
        with self.assertRaises((ValueError, RuntimeError)):
            self.experiment.retire("trial", "one", candidate["commit"], archive=True)
        self.assertTrue(path.exists())
        (path / "untracked").unlink()
        receipt = self.experiment.retire("trial", "one", candidate["commit"], archive=True)
        self.assertFalse(path.exists())
        self.assertTrue(Path(receipt["bundle"]).is_file())
        restore = self.root / "restore"
        restore.mkdir()
        git(restore, "init", "-q")
        git(restore, "fetch", receipt["bundle"], receipt["ref"])
        self.assertEqual(git(restore, "rev-parse", "FETCH_HEAD"), candidate["commit"])
        self.assertEqual(git(restore, "show", "FETCH_HEAD:feature.txt"), "one")

    def test_retire_resumes_after_archive_published(self):
        path, candidate = self.candidate("one", "one\n")
        original = self.experiment._archive
        def interrupted(*args, **kwargs):
            original(*args, **kwargs)
            raise RuntimeError("simulated interruption after archive")
        with patch.object(self.experiment, "_archive", side_effect=interrupted):
            with self.assertRaisesRegex(RuntimeError, "simulated"):
                self.experiment.retire("trial", "one", candidate["commit"], archive=True)
        self.assertTrue(path.exists())
        receipt = module.GitExperiment.open(self.root / "experiments").retire(
            "trial", "one", candidate["commit"], archive=True)
        self.assertTrue(Path(receipt["bundle"]).is_file())
        self.assertFalse(path.exists())
        self.assertEqual(receipt, self.experiment.retire(
            "trial", "one", candidate["commit"], archive=True))

    def test_retire_resumes_after_worktree_removal(self):
        path, candidate = self.candidate("one", "one\n")
        original = self.experiment._git
        def interrupted(*args, **kwargs):
            result = original(*args, **kwargs)
            if args[:2] == ("worktree", "remove"):
                raise RuntimeError("simulated interruption after removal")
            return result
        with patch.object(self.experiment, "_git", side_effect=interrupted):
            with self.assertRaisesRegex(RuntimeError, "simulated"):
                self.experiment.retire("trial", "one", candidate["commit"], archive=True)
        self.assertFalse(path.exists())
        receipt = module.GitExperiment.open(self.root / "experiments").retire(
            "trial", "one", candidate["commit"], archive=True)
        self.assertTrue(Path(receipt["bundle"]).is_file())

    def test_resume_rejects_changed_ref_and_mismatched_intent(self):
        _, candidate = self.candidate("one", "one\n")
        original = self.experiment._git
        def interrupted(*args, **kwargs):
            result = original(*args, **kwargs)
            if args[:2] == ("worktree", "remove"):
                raise RuntimeError("simulated interruption after removal")
            return result
        with patch.object(self.experiment, "_git", side_effect=interrupted):
            with self.assertRaisesRegex(RuntimeError, "simulated"):
                self.experiment.retire("trial", "one", candidate["commit"], archive=True)
        with self.assertRaises((ValueError, RuntimeError)):
            self.experiment.retire("trial", "one", candidate["commit"], archive=False)
        self.experiment._git("update-ref", "refs/heads/exp/trial/one", self.base,
                             candidate["commit"])
        with self.assertRaises((ValueError, RuntimeError)):
            self.experiment.retire("trial", "one", candidate["commit"], archive=True)
        self.assertEqual(self.experiment._git(
            "rev-parse", "refs/heads/exp/trial/one").stdout.strip(), self.base)

    def test_resume_rejects_external_removal_before_removal_intent(self):
        path, candidate = self.candidate("one", "one\n")
        original = self.experiment._archive
        def interrupted(*args, **kwargs):
            original(*args, **kwargs)
            raise RuntimeError("simulated interruption after archive")
        with patch.object(self.experiment, "_archive", side_effect=interrupted):
            with self.assertRaisesRegex(RuntimeError, "simulated"):
                self.experiment.retire("trial", "one", candidate["commit"], archive=True)
        self.experiment._git("worktree", "remove", path)
        with self.assertRaisesRegex(ValueError, "without a matching removal intent"):
            self.experiment.retire("trial", "one", candidate["commit"], archive=True)
        self.assertEqual(self.experiment._git(
            "rev-parse", "refs/heads/exp/trial/one").stdout.strip(), candidate["commit"])

    def test_resume_refuses_missing_ref(self):
        _, candidate = self.candidate("one", "one\n")
        original = self.experiment._git
        def interrupted(*args, **kwargs):
            result = original(*args, **kwargs)
            if args[:2] == ("worktree", "remove"):
                raise RuntimeError("simulated interruption after removal")
            return result
        with patch.object(self.experiment, "_git", side_effect=interrupted):
            with self.assertRaisesRegex(RuntimeError, "simulated"):
                self.experiment.retire("trial", "one", candidate["commit"], archive=True)
        self.experiment._git("update-ref", "-d", "refs/heads/exp/trial/one", candidate["commit"])
        with self.assertRaisesRegex(ValueError, "ambiguous"):
            self.experiment.retire("trial", "one", candidate["commit"], archive=True)

    def test_rejects_path_traversal_wrong_tip_and_nested_root(self):
        for bad in ("../x", "x/y", "-oops", "a..b"):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                self.experiment.allocate("trial", bad, self.base)
        with self.assertRaises(ValueError):
            module.GitExperiment.create(self.source, self.source / "nested")
        path, candidate = self.candidate("one", "one\n")
        with self.assertRaises((ValueError, RuntimeError)):
            self.experiment.retire("trial", "one", self.base)
        self.assertTrue(path.exists())
        self.assertNotEqual(candidate["commit"], self.base)


if __name__ == "__main__":
    unittest.main()

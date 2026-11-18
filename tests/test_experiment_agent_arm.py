"""Behavior tests for applying a budgeted proposal to a private Git arm."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/hill-climb/scripts"))
from experiment_agent_arm import propose_to_arm
from experiment_git import GitExperiment
from experiment_ledger import Ledger
from experiment_proposer import ProposalRunner, ScriptedProvider


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], check=True,
                          capture_output=True, text=True).stdout.strip()


class AgentArmTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "source"
        self.source.mkdir()
        git(self.source, "init", "-q")
        git(self.source, "config", "user.name", "Test")
        git(self.source, "config", "user.email", "test@example.invalid")
        (self.source / "app.txt").write_text("before\n")
        (self.source / "protected.txt").write_text("protected\n")
        git(self.source, "add", ".")
        git(self.source, "commit", "-qm", "baseline")
        self.base = git(self.source, "rev-parse", "HEAD")
        self.git = GitExperiment.create(self.source, self.root / "experiment")
        self.arm = self.git.allocate("trial", "candidate", self.base)
        self.ledger = Ledger(self.git.root / "ledger.sqlite3")
        self.ledger.initialize("trial", max_trials=2, max_tokens=0)
        self.ledger.configure_proposals("trial", max_proposals=8)

    def execute(self, edits, **extra):
        runner = ProposalRunner(self.ledger, {"scripted": ScriptedProvider(edits)})
        kwargs = dict(git=self.git, ledger=self.ledger, experiment="trial", arm="candidate",
                      expected=self.git.resolve("trial", "candidate"), paths=["app.txt"],
                      runner=runner, provider="scripted", prompt="improve", run_key="proposal1",
                      max_tokens=0, timeout=5, message="proposal",
                      writers_stopped=True,
                      freeze=lambda arm, message: self.git.freeze("trial", arm, ["app.txt"], message))
        kwargs.update(extra)
        return propose_to_arm(**kwargs)

    def test_proposal_commits_private_arm_and_retains_evidence(self):
        result = self.execute({"app.txt": b"after\n"})
        self.assertEqual(result["status"], "frozen")
        self.assertNotEqual(result["identity"]["commit"], self.base)
        self.assertEqual(git(self.arm, "show", "HEAD:app.txt"), "after")
        self.assertEqual(git(self.source, "show", "HEAD:app.txt"), "before")
        self.assertEqual(git(self.source, "status", "--porcelain"), "")
        self.assertEqual(self.ledger.status("trial")["settled_tokens"], 0)
        self.assertTrue((self.git.root / "proposals/proposal1.json").is_file())
        self.assertTrue((self.git.root / "proposals/proposal1.complete.json").is_file())
        self.assertFalse((self.arm / "proposals").exists())

    def test_rejected_scope_has_no_arm_changes_or_commit(self):
        result = self.execute({"protected.txt": b"nope"})
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(self.git.resolve("trial", "candidate")["commit"], self.base)
        self.assertEqual(git(self.arm, "status", "--porcelain"), "")
        self.assertEqual(self.ledger.status("trial")["runs"][0]["status"], "settled")

    def test_dirty_arm_refused_before_proposer_or_budget(self):
        (self.arm / "app.txt").write_text("owned user work")
        with self.assertRaisesRegex(ValueError, "clean"):
            self.execute({"app.txt": b"after"})
        self.assertEqual(self.ledger.status("trial")["runs"], [])
        self.assertEqual((self.arm / "app.txt").read_text(), "owned user work")

    def test_stale_expected_commit_refused_before_proposer(self):
        expected = {"commit": "0" * len(self.base), "tree": self.git.resolve("trial", "candidate")["tree"]}
        with self.assertRaisesRegex(ValueError, "changed"):
            self.execute({"app.txt": b"after"}, expected=expected)
        self.assertEqual(self.ledger.status("trial")["runs"], [])

    def test_empty_proposal_is_inconclusive_and_does_not_freeze(self):
        result = self.execute({})
        self.assertEqual(result["status"], "inconclusive")
        self.assertEqual(self.git.resolve("trial", "candidate")["commit"], self.base)

    def test_export_has_no_common_git_and_freeze_remains_coordinator_owned(self):
        def execute(*, root, **kwargs):
            if (root / ".git").exists():
                raise AssertionError("proposal must not get a Git metadata mount")
            (root / "app.txt").write_text("scripted edit")
            return {"usage_tokens": 0, "provider_receipt": {"fixture": True}}
        with patch.object(ScriptedProvider, 'execute', side_effect=execute):
            result = self.execute({})
        self.assertEqual(result["status"], "frozen")
        self.assertEqual(git(self.arm, "show", "HEAD:app.txt"), "scripted edit")

    def test_concurrent_arm_mutation_detected_and_preserved_before_apply(self):
        def execute(*, root, **kwargs):
            (root / "app.txt").write_text("proposal")
            (self.arm / "app.txt").write_text("concurrent user work")
            return {"usage_tokens": 0, "provider_receipt": {"fixture": True}}
        with patch.object(ScriptedProvider, 'execute', side_effect=execute):
            with self.assertRaisesRegex(ValueError, "clean"):
                self.execute({})
        self.assertEqual((self.arm / "app.txt").read_text(), "concurrent user work")
        self.assertTrue((self.git.root / "proposals/proposal1.json").is_file())
        self.assertEqual(self.git.resolve("trial", "candidate")["commit"], self.base)

    def test_failed_freeze_retains_patch_and_receipt_for_recovery(self):
        def failed_freeze(arm, message):
            raise RuntimeError("freeze interrupted")

        with self.assertRaisesRegex(RuntimeError, "interrupted"):
            self.execute({"app.txt": b"after\n"}, freeze=failed_freeze)
        self.assertEqual((self.arm / "app.txt").read_text(), "after\n")
        self.assertTrue((self.git.root / "proposals/proposal1.json").is_file())
        self.assertFalse((self.git.root / "proposals/proposal1.complete.json").exists())
        self.assertEqual(self.ledger.status("trial")["runs"][0]["status"], "settled")
        self.assertEqual(self.git.resolve("trial", "candidate")["commit"], self.base)


if __name__ == "__main__":
    unittest.main()

"""Test the proposer against frozen source, real ledger and deterministic providers."""
import base64
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/hill-climb/scripts"))
from experiment_ledger import Ledger
from experiment_proposer import ProposalRunner, ScriptedProvider


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], check=True,
                          capture_output=True, text=True).stdout.strip()


class ProposerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        git(self.repo, "init", "-q")
        git(self.repo, "config", "user.name", "Test")
        git(self.repo, "config", "user.email", "test@example.invalid")
        (self.repo / "app.txt").write_text("before\n")
        (self.repo / "protected.txt").write_text("unchanged\n")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-qm", "base")
        self.commit = git(self.repo, "rev-parse", "HEAD")
        self.tree = git(self.repo, "rev-parse", "HEAD^{tree}")
        self.ledger = Ledger(self.root / "ledger.sqlite3")
        self.ledger.initialize("demo", max_trials=0, max_tokens=200)
        self.ledger.configure_proposals("demo", max_proposals=8)

    def run_agent(self, provider, *, key="proposal", paths=("app.txt",), tokens=0):
        runner = ProposalRunner(self.ledger, {"agent": provider}, max_concurrency=2)
        return runner.run(experiment="demo", run_key=key, repo=self.repo,
                          commit=self.commit, tree=self.tree, provider="agent",
                          prompt="Improve the task", allowed_paths=paths,
                          max_tokens=tokens, timeout=5)

    def test_frozen_tree_is_edited_and_original_checkout_is_untouched(self):
        provider = ScriptedProvider({"app.txt": b"after\n"})
        result = self.run_agent(provider)
        self.assertEqual(result["status"], "proposed")
        self.assertEqual(result["usage_tokens"], 0)
        self.assertEqual(base64.b64decode(result["changes"][0]["content_base64"]), b"after\n")
        self.assertEqual((self.repo / "app.txt").read_text(), "before\n")
        self.assertEqual(git(self.repo, "status", "--porcelain"), "")
        self.assertEqual(self.ledger.status("demo")["runs"][0]["status"], "settled")

    def test_scope_escape_rejected_and_usage_retained(self):
        result = self.run_agent(ScriptedProvider({"protected.txt": b"changed"}))
        self.assertEqual(result["status"], "rejected")
        self.assertIn("outside", result["reason"])
        self.assertEqual(result["changes"], [])
        self.assertEqual(self.ledger.status("demo")["runs"][0]["actual_tokens"], 0)

    def test_alternative_agent_provider_is_rejected_before_reservation(self):
        class Alternative:
            def execute(self, **kwargs):
                raise AssertionError("must not execute")
        with self.assertRaisesRegex(ValueError, "not registered"):
            self.run_agent(Alternative(), tokens=50)
        self.assertEqual(self.ledger.status("demo")["runs"], [])

    def test_interrupted_scripted_proposal_keeps_the_reservation_uncertain(self):
        with patch.object(ScriptedProvider, 'execute', side_effect=TimeoutError("lost result")):
            with self.assertRaises(TimeoutError):
                self.run_agent(ScriptedProvider({}), tokens=60)
        status = self.ledger.status("demo")
        self.assertEqual(status["reserved_tokens"], 60)
        self.assertEqual(status["runs"][0]["status"], "uncertain")

    def test_reported_overrun_cannot_produce_a_candidate(self):
        outcome = {"usage_tokens": 31, "provider_receipt": {"fixture": True}}
        with patch.object(ScriptedProvider, 'execute', return_value=outcome):
            result = self.run_agent(ScriptedProvider({}), tokens=30)
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["changes"], [])
        self.assertTrue(self.ledger.status("demo")["overrun"])

    def test_local_concurrency_limit_applies_before_reservation(self):
        started, release = threading.Event(), threading.Event()
        def execute(**kwargs):
            started.set()
            if not release.wait(5):
                raise TimeoutError("test worker did not get released")
            return {"usage_tokens": 0, "provider_receipt": {"fixture": True}}
        runner = ProposalRunner(self.ledger, {"agent": ScriptedProvider({})}, max_concurrency=1)
        def invoke(key, timeout):
            return runner.run(experiment="demo", run_key=key, repo=self.repo,
                              commit=self.commit, tree=self.tree, provider="agent", prompt="x",
                              allowed_paths=["app.txt"], max_tokens=10, timeout=timeout)
        with patch.object(ScriptedProvider, 'execute', side_effect=execute), ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(invoke, "first", 5)
            self.assertTrue(started.wait(5))
            try:
                with self.assertRaisesRegex(TimeoutError, "worker slot"):
                    invoke("second", 0.05)
                self.assertEqual(len(self.ledger.status("demo")["runs"]), 1)
            finally:
                release.set()
            self.assertEqual(first.result()["status"], "proposed")

    def test_duplicate_run_key_never_executes_provider_twice(self):
        provider = ScriptedProvider({"app.txt": b"after"})
        self.assertEqual(self.run_agent(provider)["status"], "proposed")
        with self.assertRaisesRegex(ValueError, "already"):
            self.run_agent(provider)
        self.assertEqual(len(self.ledger.status("demo")["runs"]), 1)

    def test_invalid_commit_or_budget_does_not_reserve(self):
        runner = ProposalRunner(self.ledger, {"stub": ScriptedProvider({})})
        for commit, limit in (("HEAD", 0), (self.commit, True), (self.commit, -1)):
            with self.subTest(commit=commit, limit=limit), self.assertRaises(ValueError):
                runner.run(experiment="demo", run_key="bad", repo=self.repo, commit=commit,
                           tree=self.tree, provider="stub", prompt="x", allowed_paths=["app.txt"],
                           max_tokens=limit, timeout=2)
        self.assertEqual(self.ledger.status("demo")["runs"], [])

    def test_each_independent_proposal_uses_separate_snapshot(self):
        runner = ProposalRunner(self.ledger, {"a": ScriptedProvider({"app.txt": b"a"}),
                                             "b": ScriptedProvider({"app.txt": b"b"})}, max_concurrency=2)
        def invoke(name):
            return runner.run(experiment="demo", run_key=name, repo=self.repo,
                              commit=self.commit, tree=self.tree, provider=name, prompt="x",
                              allowed_paths=["app.txt"], max_tokens=0, timeout=2)
        with ThreadPoolExecutor(max_workers=2) as pool:
            a, b = list(pool.map(invoke, ("a", "b")))
        self.assertEqual(base64.b64decode(a["changes"][0]["content_base64"]), b"a")
        self.assertEqual(base64.b64decode(b["changes"][0]["content_base64"]), b"b")


if __name__ == "__main__":
    unittest.main()

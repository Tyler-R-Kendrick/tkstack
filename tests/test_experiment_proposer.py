"""Test the proposer against frozen source, real ledger and deterministic providers."""
import base64
from concurrent.futures import ThreadPoolExecutor
import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/hill-climb/scripts"))
from experiment_ledger import Ledger
from experiment_proposer import ProposalRunner, ScriptedProvider, CommandProvider, EnforcingBroker


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

    def test_direct_agent_without_enforcing_broker_is_not_dispatched(self):
        executable = Path(sys.executable).resolve()
        digest = hashlib.sha256(executable.read_bytes()).hexdigest()
        provider = CommandProvider([str(executable)], {str(executable): digest}, broker=None)
        with self.assertRaisesRegex(ValueError, "enforcing broker"):
            self.run_agent(provider, tokens=50)
        self.assertEqual(self.ledger.status("demo")["runs"], [])

    def test_registered_broker_receives_fixed_command_and_budget(self):
        class Broker(EnforcingBroker):
            def execute(self, *, argv, cwd, prompt, max_tokens, timeout):
                self.request = argv, cwd, prompt, max_tokens, timeout
                (cwd / "app.txt").write_text("proposed")
                return {"usage_tokens": 12, "provider_receipt": {"request_id": "test", "tokens": 12}}

        executable = Path(sys.executable).resolve()
        digest = hashlib.sha256(executable.read_bytes()).hexdigest()
        broker = Broker()
        provider = CommandProvider([str(executable), "--fixed"], {str(executable): digest}, broker=broker)
        result = self.run_agent(provider, tokens=50)
        self.assertEqual(result["status"], "proposed")
        self.assertEqual(broker.request[0], (str(executable), "--fixed"))
        self.assertEqual(broker.request[3], 50)
        self.assertEqual(result["usage_tokens"], 12)
        self.assertEqual(self.ledger.status("demo")["settled_tokens"], 12)

    def test_broker_failure_is_uncertain_and_keeps_reservation(self):
        class Broker(EnforcingBroker):
            def execute(self, **kwargs):
                raise TimeoutError("lost agent response")

        executable = Path(sys.executable).resolve()
        digest = hashlib.sha256(executable.read_bytes()).hexdigest()
        provider = CommandProvider([str(executable)], {str(executable): digest}, broker=Broker())
        with self.assertRaises(TimeoutError):
            self.run_agent(provider, tokens=60)
        status = self.ledger.status("demo")
        self.assertEqual(status["reserved_tokens"], 60)
        self.assertEqual(status["runs"][0]["status"], "uncertain")

    def test_mismatched_allowlist_is_rejected_before_reservation(self):
        class Broker(EnforcingBroker):
            def execute(self, **kwargs):
                self.fail("must not execute")

        executable = Path(sys.executable).resolve()
        provider = CommandProvider([str(executable)], {str(executable): "0" * 64}, broker=Broker())
        with self.assertRaisesRegex(ValueError, "differs"):
            self.run_agent(provider, tokens=30)
        self.assertEqual(self.ledger.status("demo")["runs"], [])

    def test_provider_overrun_cannot_produce_a_candidate(self):
        class Broker(EnforcingBroker):
            def execute(self, *, cwd, **kwargs):
                (cwd / "app.txt").write_text("discard")
                return {"usage_tokens": 31, "provider_receipt": {"request_id": "test"}}

        executable = Path(sys.executable).resolve()
        digest = hashlib.sha256(executable.read_bytes()).hexdigest()
        provider = CommandProvider([str(executable)], {str(executable): digest}, broker=Broker())
        result = self.run_agent(provider, tokens=30)
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["changes"], [])
        self.assertTrue(self.ledger.status("demo")["overrun"])

    def test_local_concurrency_limit_applies_before_reservation(self):
        started = threading.Event()
        release = threading.Event()

        class Broker(EnforcingBroker):
            def execute(self, **kwargs):
                started.set()
                if not release.wait(5):
                    raise TimeoutError("test worker did not get released")
                return {"usage_tokens": 0, "provider_receipt": {"request_id": "first"}}

        executable = Path(sys.executable).resolve()
        digest = hashlib.sha256(executable.read_bytes()).hexdigest()
        provider = CommandProvider([str(executable)], {str(executable): digest}, broker=Broker())
        runner = ProposalRunner(self.ledger, {"agent": provider}, max_concurrency=1)

        def invoke(key, timeout):
            return runner.run(experiment="demo", run_key=key, repo=self.repo,
                              commit=self.commit, tree=self.tree, provider="agent", prompt="x",
                              allowed_paths=["app.txt"], max_tokens=10, timeout=timeout)

        with ThreadPoolExecutor(max_workers=2) as pool:
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

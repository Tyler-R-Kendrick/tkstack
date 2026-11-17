"""Exercise scripted proposals through the native experiment request CLI."""
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/hill-climb/scripts/experiment.py"


class ProposerIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)
        self.repo = self.path / "source"
        self.repo.mkdir()
        self.git("init", "-q")
        (self.repo / "product.txt").write_text("bad")
        (self.repo / "protected.txt").write_text("unchanged")
        self.git("add", ".")
        self.git("-c", "user.name=T", "-c", "user.email=t@e", "commit", "-qm", "base")
        self.base = self.git("rev-parse", "HEAD")
        self.experiment = self.path / "experiment"
        self.contract = self.path / "contract.txt"
        self.contract.write_text("preserve fields")
        self.case = self.path / "case.txt"
        self.case.write_text("selection case")
        self.grader = self.path / "grader.py"
        self.grader.write_text(
            "import hashlib,json,sys\nfrom pathlib import Path\n"
            "good=Path('product.txt').read_text()=='good'\n"
            "case=hashlib.sha256(Path(sys.argv[1]).read_bytes()).hexdigest()\n"
            "print(json.dumps({'case_sha256':case, 'gates':{'preserves':good},"
            "'metrics':{'quality':3 if good else 1}, 'work_count':1}))\n")
        self.request = self.path / "request.json"
        self.call("init", source=str(self.repo), experiment="demo", base=self.base,
                  paths=["product.txt"], target="check",
                  registry={"check": {"argv": [sys.executable, str(self.grader), "{{case_file}}"], "cwd": "."}},
                  trusted_interpreter=sys.executable, contract_file=str(self.contract),
                  evaluator_file=str(self.grader), case_files={"selection": str(self.case)},
                  evaluation={"cases": ["selection"], "repetitions": 1,
                              "required_gates": [], "candidate_only_gates": ["preserves"],
                              "metric": "quality", "direction": "higher", "min_gain": 1,
                              "noise_floor": 0, "deterministic": True},
                  max_trials=2, max_tokens=0, max_proposals=1)
        self.arm = self.call("allocate", arm="fix")

    def git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.repo), *args], text=True).strip()

    def call(self, action, **fields):
        self.request.write_text(json.dumps({"action": action, "root": str(self.experiment), **fields}))
        process = subprocess.run([sys.executable, str(SCRIPT), "--request", str(self.request)],
                                 capture_output=True, text=True, timeout=30)
        if process.returncode:
            self.fail(f"{action}: {process.stderr}")
        return json.loads(process.stdout)

    def fail_call(self, action, **fields):
        self.request.write_text(json.dumps({"action": action, "root": str(self.experiment), **fields}))
        process = subprocess.run([sys.executable, str(SCRIPT), "--request", str(self.request)],
                                 capture_output=True, text=True, timeout=30)
        self.assertNotEqual(process.returncode, 0)
        return process.stderr

    def propose(self, **changes):
        request = {"arm": "fix", "expected": self.arm["identity"], "run_key": "proposal1",
                   "edits": [{"path": "product.txt", "content": "good"}],
                   "message": "fix", "writers_stopped": True}
        request.update(changes)
        return self.call("propose", **request)

    def test_scripted_proposal_is_scoped_recorded_frozen_and_evaluated(self):
        proposal = self.propose()
        self.assertEqual(proposal["status"], "frozen")
        self.assertNotEqual(proposal["identity"]["commit"], self.base)
        receipt = Path(proposal["evidence"])
        digest = hashlib.sha256(receipt.read_bytes()).hexdigest()
        self.assertEqual(digest, proposal["evidence_sha256"])
        ledger = self.call("status")["ledger"]
        settlement = next(event for event in ledger["events"] if event["run_key"] == "proposal1" and event["operation"] == "settle")
        self.assertEqual(settlement["details"]["receipt_sha256"], digest)
        self.assertEqual(ledger["settled_tokens"], 0)
        self.call("run", side="baseline", rep=0, run_key="baseline")
        self.call("run", side="candidate", arm="fix", rep=0, run_key="candidate")
        decision = self.call("compare", arm="fix", baseline=["baseline"], candidate=["candidate"], decision="compare")
        self.assertEqual(decision["decision"], "eligible")
        self.assertEqual(self.git("rev-parse", "HEAD"), self.base)
        self.assertEqual((self.repo / "product.txt").read_text(), "bad")

    def test_scope_rejection_and_untrusted_provider_do_not_edit_arm(self):
        error = self.fail_call("propose", arm="fix", expected=self.arm["identity"], run_key="badprovider",
                               edits=[{"path": "product.txt", "content": "good"}], message="bad",
                               writers_stopped=True, provider="module:unsafe")
        self.assertIn("untrusted provider", error)
        self.assertEqual(self.call("status")["ledger"]["runs"], [])
        result = self.propose(edits=[{"path": "protected.txt", "content": "unsafe"}])
        self.assertEqual(result["status"], "rejected")
        self.assertEqual((Path(self.arm["worktree"]) / "protected.txt").read_text(), "unchanged")
        self.assertEqual(self.call("status")["ledger"]["runs"][0]["status"], "settled")

    def test_stale_or_dirty_arm_does_not_spend_budget(self):
        worktree = Path(self.arm["worktree"])
        (worktree / "product.txt").write_text("user work")
        error = self.fail_call("propose", arm="fix", expected=self.arm["identity"], run_key="dirty",
                               edits=[{"path": "product.txt", "content": "good"}],
                               message="fix", writers_stopped=True)
        self.assertIn("clean", error)
        self.assertEqual((worktree / "product.txt").read_text(), "user work")
        self.assertEqual(self.call("status")["ledger"]["runs"], [])

    def test_exhaustion_is_separate_from_trial_budget(self):
        proposal = self.propose()
        error = self.fail_call("propose", arm="fix", expected=proposal["identity"], run_key="second",
                               edits=[{"path": "product.txt", "content": "better"}],
                               message="second", writers_stopped=True)
        self.assertIn("proposal budget", error)
        status = self.call("status")["ledger"]
        self.assertEqual((status["max_proposals"], status["proposal_count"]), (1, 1))
        self.assertEqual(status["settled_trials"], 0)
        self.call("run", side="baseline", rep=0, run_key="trial")
        self.assertEqual(self.call("status")["ledger"]["settled_trials"], 1)

    def test_concurrent_controller_calls_cannot_exceed_frozen_limit(self):
        other = self.call("allocate", arm="other")
        def invoke(arm, identity):
            path = self.path / (arm + "-request.json")
            path.write_text(json.dumps({"action": "propose", "root": str(self.experiment),
                "arm": arm, "expected": identity, "run_key": arm + "-run",
                "edits": [{"path": "product.txt", "content": "good"}],
                "message": arm, "writers_stopped": True}))
            return subprocess.run([sys.executable, str(SCRIPT), "--request", str(path)],
                                  capture_output=True, text=True, timeout=30)
        with ThreadPoolExecutor(max_workers=2) as pool:
            left = pool.submit(invoke, "fix", self.arm["identity"])
            right = pool.submit(invoke, "other", other["identity"])
            results = [left.result(), right.result()]
        self.assertEqual(sum(result.returncode == 0 for result in results), 1)
        self.assertIn("proposal budget", next(result.stderr for result in results if result.returncode))
        self.assertEqual(self.call("status")["ledger"]["proposal_count"], 1)

    def test_proposal_timeout_cannot_exceed_experiment_deadline(self):
        error = self.fail_call("propose", arm="fix", expected=self.arm["identity"], run_key="late",
                               edits=[{"path": "product.txt", "content": "good"}],
                               message="fix", writers_stopped=True, timeout=999999)
        self.assertIn("experiment deadline", error)
        self.assertEqual(self.call("status")["ledger"]["proposal_count"], 0)


if __name__ == "__main__":
    unittest.main()

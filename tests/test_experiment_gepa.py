"""Real GEPA and bounded experiment-adapter integration."""
import hashlib
import importlib.util
import json
import os
import sqlite3
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/hill-climb/scripts/experiment_gepa.py"
CONTROLLER = ROOT / "skills/hill-climb/scripts/experiment.py"


class GepaAdapterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name)
        self.source = self.path / "source"
        self.source.mkdir()
        self.git("init", "-q")
        (self.source / "instructions.txt").write_text("bad")
        self.git("add", "instructions.txt")
        self.git("-c", "user.name=Test", "-c", "user.email=t@example.invalid", "commit", "-qm", "base")
        self.base = self.git("rev-parse", "HEAD")
        self.contract = self.path / "contract.txt"
        self.contract.write_text("Improve the selected quality metric")
        self.evaluator = self.path / "grader.py"
        self.evaluator.write_text(
            "import hashlib,json,sys\nfrom pathlib import Path\n"
            "text=Path('instructions.txt').read_text()\n"
            "print(json.dumps({'gates':{'safe':True},"
            "'metrics':{'quality': 0.8 if text == 'better' else 0.2},'work_count':1,"
            "'case_sha256':hashlib.sha256(Path(sys.argv[2]).read_bytes()).hexdigest()}))\n"
        )
        self.case_train = self.path / "train.txt"
        self.case_train.write_text("development example")
        self.case_selection = self.path / "selection.txt"
        self.case_selection.write_text("different validation example")
        self.root = self.path / "experiment"
        self.command = self.path / "request.json"
        self.init()

    def git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.source), *args], text=True).strip()

    def invoke(self, script, payload, python=sys.executable):
        self.command.write_text(json.dumps(payload))
        return subprocess.run([python, str(script), "--request", str(self.command)], text=True, capture_output=True)

    def init(self, max_proposals=5):
        payload = {
            "action": "init", "root": str(self.root), "source": str(self.source),
            "experiment": "test", "base": self.base, "paths": ["instructions.txt"],
            "target": "check", "registry": {"check": {
                "argv": [sys.executable, str(self.evaluator), "{{case}}", "{{case_file}}"], "cwd": "."}},
            "contract_file": str(self.contract), "evaluator_file": str(self.evaluator),
            "trusted_interpreter": sys.executable,
            "case_files": {"train": str(self.case_train), "selection": str(self.case_selection)},
            "evaluation": {"cases": ["train", "selection"], "repetitions": 1,
                "required_gates": ["safe"], "metric": "quality", "direction": "higher",
                "min_gain": 0.1, "noise_floor": 0, "deterministic": True},
            "max_trials": 10, "max_tokens": 0, "max_proposals": max_proposals,
        }
        result = self.invoke(CONTROLLER, payload)
        self.assertEqual(result.returncode, 0, result.stderr)

    def request(self):
        return {"root": str(self.root), "search": "first", "artifact_path": "instructions.txt",
                "training_cases": ["train"], "selection_cases": ["selection"],
                "proposals": ["better"], "max_evaluations": 4, "max_proposals": 1,
                "max_model_tokens": 0, "metric_range": [0, 1]}

    def test_candidate_writer_rejects_links(self):
        sys.path.insert(0, str(SCRIPT.parent))
        self.addCleanup(sys.path.pop, 0)
        spec = importlib.util.spec_from_file_location("experiment_gepa", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        worktree = self.path / "private-tree"
        worktree.mkdir()
        outside = self.path / "outside.txt"
        outside.write_text("untouched")
        (worktree / "link.txt").symlink_to(outside)
        with self.assertRaisesRegex(ValueError, "escapes"):
            module._write_candidate(worktree, "link.txt", "modified")
        os.link(outside, worktree / "hard.txt")
        with self.assertRaisesRegex(ValueError, "unshared"):
            module._write_candidate(worktree, "hard.txt", "modified")
        self.assertEqual(outside.read_text(), "untouched")

    def test_rejects_paid_budget_before_any_search_effect(self):
        request = self.request()
        request["max_model_tokens"] = 100
        result = self.invoke(SCRIPT, request)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("provider", result.stderr.lower())
        self.assertFalse((self.root / "optimizer").exists())

    def test_overlapping_cases_and_outside_scope_fail_before_search(self):
        request = self.request()
        request["selection_cases"] = ["train"]
        result = self.invoke(SCRIPT, request)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("disjoint", result.stderr)
        request = self.request()
        request["artifact_path"] = "outside.txt"
        result = self.invoke(SCRIPT, request)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("scope", result.stderr)
        self.assertFalse((self.root / "optimizer").exists())

    @unittest.skipIf(importlib.util.find_spec("gepa") is not None, "GEPA installed in test interpreter")
    def test_missing_optional_dependency_fails_before_search(self):
        result = self.invoke(SCRIPT, self.request())
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("gepa is unavailable", result.stderr.lower())
        self.assertFalse((self.root / "optimizer").exists())

    @unittest.skipUnless(os.environ.get("TKSTACK_GEPA_PYTHON"), "set TKSTACK_GEPA_PYTHON for native GEPA")
    def test_real_gepa_search_uses_real_git_arms_and_budget(self):
        result = self.invoke(SCRIPT, self.request(), os.environ["TKSTACK_GEPA_PYTHON"])
        self.assertEqual(result.returncode, 0, result.stderr)
        value = json.loads(result.stdout)
        self.assertEqual(value["status"], "complete")
        self.assertEqual(value["suggestion"]["candidate"], "better")
        self.assertLessEqual(value["evaluations"], 4)
        self.assertEqual(self.git("rev-parse", "HEAD"), self.base)
        self.assertEqual((self.source / "instructions.txt").read_text(), "bad")
        self.assertTrue(Path(value["trace"]).is_file())
        status = self.invoke(CONTROLLER, {"action": "status", "root": str(self.root)})
        self.assertEqual(status.returncode, 0, status.stderr)
        state = json.loads(status.stdout)
        self.assertEqual(state["ledger"]["settled_trials"], value["evaluations"])
        self.assertEqual(state["integration"], self.base)
        if os.name == 'posix':
            started, release, escaped = (self.path / name for name in ('started', 'release', 'escaped'))
            self.evaluator.write_text(
                "import signal,time\nfrom pathlib import Path\n"
                "signal.signal(signal.SIGTERM, signal.SIG_IGN)\n"
                f"Path({str(started)!r}).touch()\n"
                f"while not Path({str(release)!r}).exists(): time.sleep(.01)\n"
                f"Path({str(escaped)!r}).touch()\n")
            self.root = self.path / 'cancelled-experiment'
            self.init()
            self.command.write_text(json.dumps(self.request()))
            process = subprocess.Popen([os.environ['TKSTACK_GEPA_PYTHON'], str(SCRIPT), '--request', str(self.command)],
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            self.addCleanup(lambda: process.kill() if process.poll() is None else None)
            for _ in range(160):
                if started.exists() or process.poll() is not None:
                    break
                time.sleep(.05)
            self.assertTrue(started.exists(), 'GEPA evaluator did not start')
            process.send_signal(signal.SIGTERM)
            _, stderr = process.communicate(timeout=15)
            self.assertEqual(process.returncode, 130, stderr)
            release.touch()
            time.sleep(1)
            self.assertFalse(escaped.exists(), 'GEPA evaluator survived cancellation')

    @unittest.skipUnless(os.environ.get("TKSTACK_GEPA_PYTHON"), "set TKSTACK_GEPA_PYTHON for native GEPA")
    def test_missing_case_attestation_never_becomes_score(self):
        self.evaluator.write_text(
            "import json\nprint(json.dumps({'gates': {'safe': True}, "
            "'metrics': {'quality': 0.8}, 'work_count': 1}))\n")
        self.root = self.path / "other-experiment"
        self.init()
        result = self.invoke(SCRIPT, self.request(), os.environ["TKSTACK_GEPA_PYTHON"])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("attest", result.stderr)
        events = (self.root / "optimizer" / "first" / "trace.jsonl").read_text()
        self.assertIn('"event": "error"', events)
        status = self.invoke(CONTROLLER, {"action": "status", "root": str(self.root)})
        self.assertEqual(json.loads(status.stdout)["ledger"]["settled_trials"], 1)

    @unittest.skipUnless(os.environ.get("TKSTACK_GEPA_PYTHON"), "set TKSTACK_GEPA_PYTHON for native GEPA")
    def test_searches_share_proposal_limit_and_receipts_are_hashed(self):
        self.root = self.path / "one-proposal"
        self.init(max_proposals=1)
        first = self.invoke(SCRIPT, self.request(), os.environ["TKSTACK_GEPA_PYTHON"])
        self.assertEqual(first.returncode, 0, first.stderr)
        state_result = self.invoke(CONTROLLER, {"action": "status", "root": str(self.root)})
        ledger = json.loads(state_result.stdout)["ledger"]
        self.assertEqual(ledger["proposal_count"], 1)
        events = [event for event in ledger["events"]
                  if event["operation"] == "settle" and event["run_key"].startswith("gp-")]
        self.assertEqual(len(events), 1)
        receipt = self.root / "optimizer/first/proposals/1.json"
        self.assertEqual(events[0]["details"]["receipt_sha256"],
                         hashlib.sha256(receipt.read_bytes()).hexdigest())
        request = self.request()
        request["search"] = "second"
        second = self.invoke(SCRIPT, request, os.environ["TKSTACK_GEPA_PYTHON"])
        self.assertNotEqual(second.returncode, 0)
        self.assertIn("proposal budget", second.stderr.lower())
        self.assertFalse((self.root / "optimizer/second").exists())

    @unittest.skipUnless(os.environ.get("TKSTACK_GEPA_PYTHON"), "set TKSTACK_GEPA_PYTHON for native GEPA")
    def test_older_config_gets_five_proposals_without_resetting_trial_budget(self):
        config_path = self.root / "experiment.json"
        config = json.loads(config_path.read_text())
        del config["max_proposals"]
        config_path.write_text(json.dumps(config) + "\n")
        with sqlite3.connect(self.root / "ledger.sqlite3") as db:
            db.execute("UPDATE controller_config SET digest=? WHERE id=1",
                       (hashlib.sha256(config_path.read_bytes()).hexdigest(),))
            db.execute("DELETE FROM proposal_limits WHERE experiment=?", ("test",))
        result = self.invoke(SCRIPT, self.request(), os.environ["TKSTACK_GEPA_PYTHON"])
        self.assertEqual(result.returncode, 0, result.stderr)
        state = self.invoke(CONTROLLER, {"action": "status", "root": str(self.root)})
        ledger = json.loads(state.stdout)["ledger"]
        self.assertEqual(ledger["max_proposals"], 5)
        self.assertEqual(ledger["proposal_count"], 1)
        self.assertEqual(ledger["settled_trials"], json.loads(result.stdout)["evaluations"])

    @unittest.skipUnless(os.environ.get("TKSTACK_GEPA_PYTHON"), "set TKSTACK_GEPA_PYTHON for native GEPA")
    def test_searches_with_same_prefix_get_distinct_arms_and_ledger_keys(self):
        request = self.request()
        request["search"] = "abcdefghijkl-first"
        first = self.invoke(SCRIPT, request, os.environ["TKSTACK_GEPA_PYTHON"])
        self.assertEqual(first.returncode, 0, first.stderr)
        request["search"] = "abcdefghijkl-second"
        second = self.invoke(SCRIPT, request, os.environ["TKSTACK_GEPA_PYTHON"])
        self.assertEqual(second.returncode, 0, second.stderr)
        left, right = json.loads(first.stdout), json.loads(second.stdout)
        self.assertNotEqual(left["suggestion"]["arm"], right["suggestion"]["arm"])
        state = self.invoke(CONTROLLER, {"action": "status", "root": str(self.root)})
        ledger = json.loads(state.stdout)["ledger"]
        self.assertEqual(ledger["proposal_count"], 2)
        self.assertEqual(ledger["settled_trials"], left["evaluations"] + right["evaluations"])

    @unittest.skipUnless(os.environ.get("TKSTACK_GEPA_PYTHON"), "set TKSTACK_GEPA_PYTHON for native GEPA")
    def test_expired_experiment_does_not_dispatch_evaluations(self):
        config_path = self.root / "experiment.json"
        config = json.loads(config_path.read_text())
        config["deadline_epoch"] = 1
        config_path.write_text(json.dumps(config) + "\n")
        with sqlite3.connect(self.root / "ledger.sqlite3") as db:
            db.execute("UPDATE controller_config SET digest=? WHERE id=1",
                       (hashlib.sha256(config_path.read_bytes()).hexdigest(),))
        result = self.invoke(SCRIPT, self.request(), os.environ["TKSTACK_GEPA_PYTHON"])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("deadline", result.stderr)
        state = self.invoke(CONTROLLER, {"action": "status", "root": str(self.root)})
        self.assertEqual(json.loads(state.stdout)["ledger"]["settled_trials"], 0)

    @unittest.skipUnless(os.environ.get("TKSTACK_GEPA_PYTHON"), "set TKSTACK_GEPA_PYTHON for native GEPA")
    def test_hard_evaluation_guard_stops_gepa_overshoot(self):
        request = self.request()
        request["max_evaluations"] = 3
        result = self.invoke(SCRIPT, request, os.environ["TKSTACK_GEPA_PYTHON"])
        self.assertEqual(result.returncode, 0, result.stderr)
        value = json.loads(result.stdout)
        self.assertEqual(value["status"], "budget_exhausted")
        self.assertEqual(value["evaluations"], 3)
        self.assertIsNone(value["suggestion"])
        status = self.invoke(CONTROLLER, {"action": "status", "root": str(self.root)})
        self.assertEqual(json.loads(status.stdout)["ledger"]["settled_trials"], 3)


if __name__ == "__main__":
    unittest.main()

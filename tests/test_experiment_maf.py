"""Tests of the MAF binding and, when available, the native workflow."""
import asyncio
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / "skills/hill-climb/workflows/experiment-cycle"
spec = importlib.util.spec_from_file_location("experiment_maf_bindings", WORKFLOW / "bindings.py")
bindings = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bindings)


class BindingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name)
        self.root = self.path / "experiment"
        self.requests = self.path / "requests"
        self.requests.mkdir()
        self.log = self.path / "calls.txt"
        self.controller = self.path / "stub.py"
        self.controller.write_text(
            "import json,sys\n"
            "data=json.load(open(sys.argv[2]))\n"
            f"open({str(self.log)!r},'a').write(data['action']+'\\n')\n"
            "print(json.dumps({'decision': 'reject'} if data['action']=='compare' else {'ok': True}))\n"
        )

    def request(self, filename, action, **kwargs):
        payload = {"action": action, "root": str(self.root), **kwargs}
        (self.requests / filename).write_text(json.dumps(payload))

    def invoke(self, files):
        return asyncio.run(bindings.execute_requests(
            self.requests, self.root, "check", files, self.controller, 120))

    def test_ordered_actions_return_exact_receipts_and_hashes(self):
        self.request("a.json", "init", target="check")
        self.request("b.json", "status")
        result = self.invoke(["a.json", "b.json"])
        self.assertEqual(self.log.read_text().splitlines(), ["init", "status"])
        self.assertEqual([r["action"] for r in result], ["init", "status"])
        self.assertEqual(result[0]["request_sha256"],
                         hashlib.sha256((self.requests / "a.json").read_bytes()).hexdigest())
        bindings._outcome("calibrate", {"qualified": True, "scope": {"kind": "boolean_examples"}})
        with self.assertRaisesRegex(ValueError, "calibration"):
            bindings._outcome("calibrate", {"qualified": True, "scope": {"kind": "gate", "name": "x"}})
        for action in ("host-start", "host-uncertain", "host-finish"):
            self.request("host.json", action)
            self.assertEqual(self.invoke(["host.json"])[0]["action"], action)

    def test_compare_rejection_stops_later_effects(self):
        self.request("a.json", "init", target="check")
        self.request("b.json", "compare")
        self.request("c.json", "status")
        with self.assertRaisesRegex(ValueError, "comparison is not eligible"):
            self.invoke(["a.json", "b.json", "c.json"])
        self.assertEqual(self.log.read_text().splitlines(), ["init", "compare"])

    def test_validation_happens_before_any_stage(self):
        self.request("a.json", "init", target="check")
        self.request("b.json", "status", root=str(self.path / "different"))
        with self.assertRaisesRegex(ValueError, "root"):
            self.invoke(["a.json", "b.json"])
        self.assertFalse(self.log.exists())
        with self.assertRaisesRegex(ValueError, "inside"):
            self.invoke(["../outside.json"])
        with self.assertRaisesRegex(ValueError, "duplicates"):
            self.invoke(["a.json", "a.json"])
        with self.assertRaisesRegex(ValueError, "selected target"):
            bindings.prepare(self.requests, self.root, "../escape", ["a.json"])

    def test_run_requires_long_timeout_and_timeout_reports_unknown_descendants(self):
        self.request("a.json", "run")
        with self.assertRaisesRegex(ValueError, "at least 120"):
            asyncio.run(bindings.execute_requests(
                self.requests, self.root, "check", ["a.json"], self.controller, 1))
        with patch.object(bindings.subprocess, "run", side_effect=subprocess.TimeoutExpired("controller", 120)):
            with self.assertRaisesRegex(ValueError, "inspect descendant processes"):
                self.invoke(["a.json"])

    def test_parallel_partial_and_failed_proposal_stop_workflow(self):
        with self.assertRaisesRegex(ValueError, "parallel batch is incomplete"):
            bindings._outcome("parallel", {"status": "partial"})
        bindings._outcome("parallel", {"status": "complete"})
        with self.assertRaisesRegex(ValueError, "proposal did not freeze"):
            bindings._outcome("propose", {"status": "rejected"})
        bindings._outcome("propose", {"status": "frozen"})

    def test_incomplete_capture_or_handoff_stops_workflow(self):
        with self.assertRaisesRegex(ValueError, "regrade capture is incomplete"):
            bindings._outcome("regrade-capture", {"result": {"decision": "inconclusive"}})
        with self.assertRaisesRegex(ValueError, "handoff did not stage"):
            bindings._outcome("handoff", {"state": "unresolved"})
        bindings._outcome("regrade-capture", {"result": {"decision": "complete"}})
        bindings._outcome("handoff", {"state": "staged"})

    def test_confirmation_rejection_fails(self):
        with self.assertRaisesRegex(ValueError, "confirmation is not eligible"):
            bindings._outcome("confirm", {"decision": "inconclusive"})
        bindings._outcome("confirm", {"decision": "eligible"})


@unittest.skipUnless(os.environ.get("TKSTACK_MAF_PYTHON") and os.environ.get("DOTNET_ROOT"),
                     "set TKSTACK_MAF_PYTHON and DOTNET_ROOT for real MAF execution")
class NativeWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name)
        self.root = self.path / "experiment"
        self.requests = self.path / "requests"
        self.requests.mkdir()
        self.source = self.path / "source"
        self.source.mkdir()
        self.git("init", "-q")
        (self.source / "product.txt").write_text("baseline")
        self.git("add", "product.txt")
        self.git("-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-qm", "base")
        self.base = self.git("rev-parse", "HEAD")
        self.evaluator = self.path / "evaluator.py"
        self.evaluator.write_text(
            "import hashlib,json,sys\nfrom pathlib import Path\n"
            "print(json.dumps({'gates': {'pass': True}, 'metrics': {'quality': 1}, "
            "'work_count': 1, 'case_sha256': hashlib.sha256(Path(sys.argv[1]).read_bytes()).hexdigest()}))\n")
        self.case_file = self.path / "selection.txt"
        self.case_file.write_text("selection input")
        self.contract = self.path / "contract.txt"
        self.contract.write_text("test contract")
        self.request("init.json", "init", source=str(self.source), experiment="native",
                     base=self.base, paths=["product.txt"], target="check",
                     registry={"check": {"argv": [sys.executable, str(self.evaluator), "{{case_file}}"], "cwd": "."}},
                     contract_file=str(self.contract), evaluator_file=str(self.evaluator),
                     trusted_interpreter=sys.executable, case_files={"test": str(self.case_file)},
                     evaluation={"case": "test", "repetitions": 1, "required_gates": ["pass"],
                                 "metric": "quality", "direction": "higher", "min_gain": 1,
                                 "noise_floor": 0, "deterministic": True},
                     max_trials=2, max_tokens=0)

    def git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.source), *args], text=True).strip()

    def request(self, filename, action, **kwargs):
        (self.requests / filename).write_text(json.dumps({"action": action, "root": str(self.root), **kwargs}))

    def run_workflow(self, files):
        inputs = self.path / "inputs.json"
        inputs.write_text(json.dumps({"request_paths": files}))
        return subprocess.run([
            os.environ["TKSTACK_MAF_PYTHON"], str(WORKFLOW / "run.py"),
            "--request-dir", str(self.requests), "--root", str(self.root),
            "--target", "check", "--input", str(inputs)],
            text=True, capture_output=True)

    def test_native_graph_executes_real_controller_in_order(self):
        self.request("status.json", "status")
        result = self.run_workflow(["init.json", "status.json"])
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "succeeded")
        self.assertEqual([r["action"] for r in payload["results"]], ["init", "status"])
        self.assertEqual(payload["results"][1]["response"]["integration"], self.base)

    def test_native_graph_executes_selection_and_confirmation(self):
        self.evaluator.write_text(
            "import hashlib,json,sys\nfrom pathlib import Path\n"
            "good = Path('product.txt').read_text() == 'fixed'\n"
            "print(json.dumps({'gates': {'pass': True}, "
            "'metrics': {'quality': 3 if good else 1}, 'work_count': 1, "
            "'case_sha256': hashlib.sha256(Path(sys.argv[2]).read_bytes()).hexdigest()}))\n")
        init = json.loads((self.requests / "init.json").read_text())
        init["max_trials"] = 4
        init["registry"]["check"]["argv"] = [sys.executable, str(self.evaluator), "{{case}}", "{{case_file}}"]
        held = self.path / "held-out.txt"
        held.write_text("different held-out input")
        init["case_files"]["held-out"] = str(held)
        init["confirmation"] = {"cases": ["held-out"], "repetitions": 1}
        (self.requests / "init.json").write_text(json.dumps(init))
        self.request("allocate.json", "allocate", arm="fix")
        initial = self.run_workflow(["init.json", "allocate.json"])
        self.assertEqual(initial.returncode, 0, initial.stderr)
        arm = json.loads(initial.stdout)["results"][1]["response"]["worktree"]
        (Path(arm) / "product.txt").write_text("fixed")
        self.request("freeze.json", "freeze", arm="fix", message="fix", writers_stopped=True)
        self.request("old.json", "run", side="baseline", rep=0, run_key="old")
        self.request("new.json", "run", side="candidate", arm="fix", rep=0, run_key="new")
        self.request("compare.json", "compare", arm="fix", baseline=["old"],
                     candidate=["new"], decision="winner")
        self.request("select.json", "select", decision="winner")
        self.request("old-held.json", "run", side="baseline", split="confirmation",
                     case="held-out", rep=0, run_key="old-held")
        self.request("new-held.json", "run", side="candidate", arm="fix",
                     split="confirmation", case="held-out", rep=0, run_key="new-held")
        self.request("confirm.json", "confirm", baseline=["old-held"], candidate=["new-held"])
        self.request("promote.json", "promote", arm="fix", decision="winner")
        result = self.run_workflow(["freeze.json", "old.json", "new.json", "compare.json",
                                    "select.json", "old-held.json", "new-held.json",
                                    "confirm.json", "promote.json"])
        self.assertEqual(result.returncode, 0, result.stderr)
        receipts = json.loads(result.stdout)["results"]
        self.assertEqual(receipts[-2]["response"]["decision"], "eligible")
        self.assertNotEqual(receipts[-1]["response"]["commit"], self.base)

    def test_native_graph_executes_parallel_batch(self):
        init = json.loads((self.requests / "init.json").read_text())
        init["evaluation"]["repetitions"] = 2
        (self.requests / "init.json").write_text(json.dumps(init))
        self.request("batch.json", "parallel", batch="paired", max_workers=2, trials=[
            {"side": "baseline", "rep": 0, "run_key": "rep-0"},
            {"side": "baseline", "rep": 1, "run_key": "rep-1"},
        ])
        self.request("batch-status.json", "parallel-status", batch="paired")
        result = self.run_workflow(["init.json", "batch.json", "batch-status.json"])
        self.assertEqual(result.returncode, 0, result.stderr)
        receipts = json.loads(result.stdout)["results"]
        self.assertEqual(receipts[1]["response"]["status"], "complete")
        self.assertEqual([r["status"] for r in receipts[2]["response"]["runs"]],
                         ["settled", "settled"])

    def test_native_graph_runs_real_calibration_stage(self):
        self.request("calibrate-run.json", "calibration-run",
                     evaluator_file=str(self.evaluator), trusted_interpreter=sys.executable,
                     registry={"check": {"argv": [sys.executable, str(self.evaluator), "{{case_file}}"], "cwd": "."}},
                     case="labeled", case_file=str(self.case_file), commit=self.base, run_key="cal-1")
        self.request("status.json", "status")
        result = self.run_workflow(["init.json", "calibrate-run.json", "status.json"])
        self.assertEqual(result.returncode, 0, result.stderr)
        receipts = json.loads(result.stdout)["results"]
        self.assertEqual(receipts[1]["response"]["result"]["status"], "passed")
        self.assertEqual(receipts[2]["response"]["ledger"]["settled_trials"], 1)

    def test_native_graph_stops_on_unqualified_calibration(self):
        self.request("bad.json", "calibrate", records=[
            {"id": "wrong", "expected": True, "observed": False},
            {"id": "bad", "expected": False, "observed": False}])
        self.request("allocate.json", "allocate", arm="later")
        result = self.run_workflow(["init.json", "bad.json", "allocate.json"])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("calibration is not qualified", result.stderr)
        self.assertFalse((self.root / "worktrees/native/later").exists())


if __name__ == "__main__":
    unittest.main()

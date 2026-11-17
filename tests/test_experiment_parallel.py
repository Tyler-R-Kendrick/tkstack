"""Behavioral tests for bounded, preallocated concurrent trial execution."""
import concurrent.futures
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills/hill-climb/scripts"
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location("experiment_parallel", SCRIPTS / "experiment_parallel.py")
parallel = importlib.util.module_from_spec(spec)
spec.loader.exec_module(parallel)
import experiment
import test_experiment_integrity as integrity


class ParallelTrialsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name)
        self.repo = self.path / "source"
        self.repo.mkdir()
        self.git("init", "-q")
        (self.repo / "product.txt").write_text("old")
        self.git("add", "product.txt")
        self.git("-c", "user.name=T", "-c", "user.email=t@example.invalid", "commit", "-qm", "base")
        self.base = self.git("rev-parse", "HEAD")
        self.root = self.path / "experiment"
        self.contract = self.path / "contract.txt"
        self.contract.write_text("preserve behavior")
        self.cases = {}
        for label in ("one", "two"):
            path = self.path / (label + ".txt")
            path.write_text("distinct case " + label)
            self.cases[label] = str(path)
        self.barrier = self.path / "barrier"
        self.barrier.mkdir()
        self.evaluator = self.path / "evaluator.py"
        self.evaluator.write_text(
            "import hashlib,json,sys,time\nfrom pathlib import Path\n"
            "barrier,case,case_file=Path(sys.argv[1]),sys.argv[2],Path(sys.argv[3])\n"
            "if (barrier / 'block').exists():\n"
            " import signal\n"
            " signal.signal(signal.SIGTERM, signal.SIG_IGN)\n"
            " (barrier / case).touch()\n"
            " while not (barrier / 'release').exists(): time.sleep(.01)\n"
            " (barrier / ('escaped-'+case)).touch()\n"
            " sys.exit(0)\n"
            "(barrier / case).write_text('ready')\n"
            "deadline=time.monotonic()+5\n"
            "while len(list(barrier.iterdir())) < 2 and time.monotonic() < deadline: time.sleep(.01)\n"
            "overlap=len(list(barrier.iterdir())) >= 2\n"
            "print(json.dumps({'gates':{'overlap':overlap}, 'metrics':{'quality':1},"
            "'work_count':1,'case_sha256':hashlib.sha256(case_file.read_bytes()).hexdigest()}))\n"
        )
        self.call("init", source=str(self.repo), experiment="parallel", base=self.base,
                  paths=["product.txt"], target="check",
                  registry={"check":{"argv":[sys.executable,str(self.evaluator),str(self.barrier),
                                              "{{case}}","{{case_file}}"],"cwd":"."}},
                  trusted_interpreter=sys.executable,
                  contract_file=str(self.contract), evaluator_file=str(self.evaluator),
                  case_files=self.cases,
                  evaluation={"cases":["one","two"],"repetitions":1,
                              "required_gates":["overlap"],"metric":"quality",
                              "direction":"higher","min_gain":0.1,"noise_floor":0,"deterministic":True},
                  max_trials=4,max_tokens=0)
        for arm in ("a", "b"):
            allocation = self.call("allocate", arm=arm)
            (Path(allocation["worktree"]) / "product.txt").write_text(arm)
            self.call("freeze", arm=arm, message=arm, writers_stopped=True)

    def git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.repo), *args], text=True).strip()

    def call(self, action, **fields):
        return experiment.execute({"action":action, "root":str(self.root), **fields})

    def request(self):
        return {"root":str(self.root), "batch":"batch1", "max_workers":2, "trials":[
            {"side":"candidate","arm":"a","case":"one","rep":0,"run_key":"a-one"},
            {"side":"candidate","arm":"b","case":"two","rep":0,"run_key":"b-two"}]}

    def test_real_trials_overlap_with_stable_receipts_and_budget(self):
        result = parallel.run_batch(self.request())
        self.assertEqual(result["status"], "complete")
        self.assertEqual([x["run_key"] for x in result["trials"]], ["a-one", "b-two"])
        self.assertTrue(all(json.loads(x["result"]["stdout"])["gates"]["overlap"] for x in result["trials"]))
        state = self.call("status")
        self.assertEqual(state["ledger"]["settled_trials"], 2)
        manifest = parallel.batch_status(self.root, "batch1")
        self.assertEqual([a["run_key"] for a in manifest["manifest"]["assignments"]], ["a-one", "b-two"])
        self.assertEqual([a["status"] for a in manifest["runs"]], ["settled", "settled"])
        self.assertEqual((self.repo / "product.txt").read_text(), "old")
        self.assertEqual(state["integration"], self.base)

    def test_cli_runs_the_actual_batch_entry_point(self):
        request_path = self.path / "batch.json"
        request_path.write_text(json.dumps(self.request()))
        completed = subprocess.run(
            [sys.executable, str(SCRIPTS / "experiment_parallel.py"), "--request", str(request_path)],
            text=True, capture_output=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(json.loads(completed.stdout)["status"], "complete")
        self.assertEqual(self.call("status")["ledger"]["settled_trials"], 2)

    def test_controller_dispatches_batch_and_exposes_status(self):
        request = self.request()
        request.pop("root")
        self.assertEqual(self.call("parallel", **request)["status"], "complete")
        status = self.call("parallel-status", batch="batch1")
        self.assertEqual([row["status"] for row in status["runs"]], ["settled", "settled"])
        self.assertEqual(self.call("parallel-recover", batch="batch1")["released"], [])

    def test_compiled_native_command_runs_parallel_batch(self):
        request_path = self.path / "public-batch.json"
        request_path.write_text(json.dumps({"action": "parallel", **self.request()}))
        result = subprocess.run([
            sys.executable, str(ROOT / "skills/learn/skills/skillify/scripts/skillify.py"),
            "invoke", str(ROOT / "skills/hill-climb"), "--", "native", "experiment",
            "--request", str(request_path),
        ], text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "complete")
        if os.name != 'posix':
            return
        self.setUp()
        (self.barrier / 'block').touch()
        request_path = self.path / 'cancel.json'
        request_path.write_text(json.dumps({'action': 'parallel', **self.request()}))
        process = subprocess.Popen([
            sys.executable, str(ROOT / 'src/tkstack.py'), '--project', str(self.path),
            'skills', 'hill-climb', '--', 'native', 'experiment', '--request', str(request_path),
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.addCleanup(lambda: process.kill() if process.poll() is None else None)
        for _ in range(160):
            if all((self.barrier / name).exists() for name in ('one', 'two')) or process.poll() is not None:
                break
            time.sleep(.05)
        self.assertTrue(all((self.barrier / name).exists() for name in ('one', 'two')))
        process.send_signal(signal.SIGTERM)
        _, stderr = process.communicate(timeout=15)
        self.assertNotEqual(process.returncode, 0, stderr)
        (self.barrier / 'release').touch()
        time.sleep(1)
        self.assertFalse(any(self.barrier.glob('escaped-*')))

    def test_batch_receipts_are_accepted_by_existing_comparison(self):
        request = {"root":str(self.root), "batch":"comparison", "max_workers":2, "trials":[
            {"side":"baseline","case":"one","rep":0,"run_key":"base-one"},
            {"side":"baseline","case":"two","rep":0,"run_key":"base-two"},
            {"side":"candidate","arm":"a","case":"one","rep":0,"run_key":"a-one"},
            {"side":"candidate","arm":"a","case":"two","rep":0,"run_key":"a-two"}]}
        result = parallel.run_batch(request)
        self.assertEqual(result["status"], "complete")
        decision = self.call("compare", arm="a", baseline=["base-one","base-two"],
                             candidate=["a-one","a-two"], decision="comparison")
        self.assertEqual(decision["decision"], "reject")
        self.assertEqual(self.call("status")["ledger"]["settled_trials"], 4)

    def test_ledger_batch_reservation_is_atomic_under_competition(self):
        ledger = parallel.Ledger(self.root / "ledger.sqlite3")
        barrier = threading.Barrier(2)
        def reserve(key):
            barrier.wait()
            try:
                parallel.reserve_batch(ledger, "parallel", key, [key+"1",key+"2",key+"3"])
                return True
            except ValueError:
                return False
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(reserve, ["left","right"]))
        self.assertEqual(sorted(outcomes), [False,True])
        self.assertEqual(ledger.status("parallel")["reserved_trials"], 3)

    def test_recovery_releases_only_never_dispatched_reservations(self):
        ledger = parallel.Ledger(self.root / "ledger.sqlite3")
        parallel.reserve_batch(ledger, "parallel", "interrupted", ["never", "lost"])
        ledger.dispatch("parallel", "lost")
        recovered = parallel.recover_reserved(self.root, "interrupted")
        self.assertEqual(recovered["released"], ["never"])
        self.assertEqual(recovered["retained_for_reconciliation"], ["lost"])
        states = {row["run_key"]: row["status"] for row in ledger.status("parallel")["runs"]}
        self.assertEqual(states, {"never": "cancelled", "lost": "dispatched"})
        self.assertEqual(parallel.recover_reserved(self.root, "interrupted")["released"], [])

    def test_duplicate_keys_or_unapproved_scope_rejects_before_budget(self):
        request = self.request()
        request["trials"][1]["run_key"] = request["trials"][0]["run_key"]
        with self.assertRaisesRegex(ValueError, "duplicate"):
            parallel.run_batch(request)
        request = self.request()
        request["target"] = "unapproved-language-or-target"
        with self.assertRaisesRegex(ValueError, "undeclared"):
            parallel.run_batch(request)
        request = self.request()
        request["trials"][1]["arm"] = "unknown"
        with self.assertRaises(ValueError):
            parallel.run_batch(request)
        self.assertEqual(self.call("status")["ledger"]["reserved_trials"], 0)

    def test_status_is_readable_while_worker_is_dispatched(self):
        started, release = threading.Event(), threading.Event()
        request = self.request()
        request["trials"] = request["trials"][:1]
        request["max_workers"] = 1
        def slow_runner(*args, **kwargs):
            started.set()
            if not release.wait(5):
                raise RuntimeError("test timeout")
            raise RuntimeError("lost response")
        with patch.object(parallel, "run_trial", side_effect=slow_runner):
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(parallel.run_batch, request)
                self.assertTrue(started.wait(5))
                try:
                    status = parallel.batch_status(self.root, "batch1")
                    self.assertEqual(status["runs"][0]["status"], "dispatched")
                finally:
                    release.set()
                self.assertEqual(future.result(timeout=5)["status"], "partial")
        self.assertEqual(parallel.batch_status(self.root, "batch1")["runs"][0]["status"], "uncertain")

    def test_parallel_confirmation_uses_selected_finalist_once(self):
        self.root = self.path / "confirmation-experiment"
        grader = self.path / "confirmation-grader.py"
        grader.write_text(
            "import hashlib,json,sys\nfrom pathlib import Path\n"
            "case_file=Path(sys.argv[2])\n"
            "good=Path('product.txt').read_text() == 'good'\n"
            "print(json.dumps({'gates':{'safe':True},'metrics':{'quality':2 if good else 1},"
            "'work_count':1,'case_sha256':hashlib.sha256(case_file.read_bytes()).hexdigest()}))\n")
        self.call("init", source=str(self.repo), experiment="confirm", base=self.base,
                  paths=["product.txt"], target="check",
                  registry={"check":{"argv":[sys.executable,str(grader),"{{case}}","{{case_file}}"],"cwd":"."}},
                  trusted_interpreter=sys.executable, contract_file=str(self.contract),
                  evaluator_file=str(grader), case_files=self.cases,
                  evaluation={"cases":["one"],"repetitions":1,"required_gates":["safe"],
                              "metric":"quality","direction":"higher","min_gain":0.1,
                              "noise_floor":0,"deterministic":True},
                  confirmation={"cases":["two"],"repetitions":1},
                  max_trials=4,max_tokens=0)
        arm = self.call("allocate", arm="fixed")
        (Path(arm["worktree"]) / "product.txt").write_text("good")
        frozen = self.call("freeze", arm="fixed", message="fix", writers_stopped=True)
        result = parallel.run_batch({"root":str(self.root),"batch":"select","max_workers":2,"trials":[
            {"side":"baseline","case":"one","rep":0,"run_key":"old"},
            {"side":"candidate","arm":"fixed","case":"one","rep":0,"run_key":"new"}]})
        self.assertEqual(result["status"], "complete")
        self.assertEqual(self.call("compare",arm="fixed",baseline=["old"],candidate=["new"],
                                   decision="winner")["decision"], "eligible")
        self.call("select", decision="winner")
        confirm_request = {"root":str(self.root),"batch":"confirm","max_workers":2,"trials":[
            {"side":"baseline","split":"confirmation","case":"two","rep":0,"run_key":"hold-old"},
            {"side":"candidate","arm":"fixed","split":"confirmation","case":"two","rep":0,"run_key":"hold-new"}]}
        self.assertEqual(parallel.run_batch(confirm_request)["status"],"complete")
        self.assertEqual(self.call("confirm",baseline=["hold-old"],candidate=["hold-new"])["decision"],"eligible")
        self.assertEqual(self.call("promote",arm="fixed",decision="winner")["commit"],frozen["commit"])

    def test_worker_exception_keeps_dispatch_uncertain_and_no_retry(self):
        request = self.request()
        request["trials"] = request["trials"][:1]
        with patch.object(parallel, "run_trial", side_effect=RuntimeError("lost response")):
            outcome = parallel.run_batch(request)
        self.assertEqual(outcome["status"], "partial")
        state = self.call("status")["ledger"]
        self.assertEqual(state["reserved_trials"], 1)
        self.assertEqual(state["runs"][0]["status"], "uncertain")
        recovery = parallel.recover_reserved(self.root, "batch1")
        self.assertEqual(recovery["released"], [])
        self.assertEqual(recovery["retained_for_reconciliation"], ["a-one"])
        request["batch"] = "retry"
        with self.assertRaisesRegex(ValueError, "already"):
            parallel.run_batch(request)


class SelectionBatchTests(unittest.TestCase):
    setUp = integrity.ProductionProtocolTests.setUp
    git = integrity.ProductionProtocolTests.git
    call = integrity.ProductionProtocolTests.call
    init = integrity.ProductionProtocolTests.init
    freeze = integrity.ProductionProtocolTests.freeze

    def test_serial_and_parallel_share_durable_assignment_claims(self):
        self.init()
        self.freeze()
        self.call("run", side="baseline", rep=0, run_key="first")
        req = {"root":str(self.root), "batch":"b", "max_workers":1, "trials":[
            {"side":"baseline", "case":"sel", "rep":0, "run_key":"second"}]}
        with self.assertRaisesRegex(ValueError, "selection assignment"):
            parallel.run_batch(req)
        self.assertEqual(self.call("status")["ledger"]["settled_trials"], 1)

    def test_two_parallel_batches_cannot_reuse_assignment(self):
        self.init()
        self.freeze()
        def req(batch, run):
            return {"root":str(self.root), "batch":batch, "max_workers":1, "trials":[
                {"side":"baseline", "case":"sel", "rep":0, "run_key":run}]}
        self.assertEqual(parallel.run_batch(req("b1", "one"))["status"], "complete")
        with self.assertRaisesRegex(ValueError, "selection assignment"):
            parallel.run_batch(req("b2", "two"))


if __name__ == "__main__":
    unittest.main()

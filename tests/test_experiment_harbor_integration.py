"""Controller/Harbor integration using an executable fake Harbor process."""
import hashlib
import importlib.util
import json
import sqlite3
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/hill-climb/scripts"))
spec = importlib.util.spec_from_file_location("harbor_experiment", ROOT / "skills/hill-climb/scripts/experiment.py")
from experiment_harbor import verifier_digest
experiment = importlib.util.module_from_spec(spec)
spec.loader.exec_module(experiment)


FAKE = r'''#!/usr/bin/env python3
import hashlib,json,pathlib,sys,tarfile,tomllib
if sys.argv[1:] == ['--version']:
    print('0.26.0'); raise SystemExit(0)
config=json.loads(pathlib.Path(sys.argv[-1]).read_text())
task=pathlib.Path(config['tasks'][0]['path'])
assert tomllib.loads((task/'task.toml').read_text())['verifier']['environment_mode']=='separate'
with tarfile.open(task/'solution/source.tar') as archive:
    product=archive.extractfile('product').read().decode()
case=(task/'tests/case.input').read_bytes()
case_sha=hashlib.sha256(case).hexdigest()
trial=pathlib.Path(config['jobs_dir'])/'candidate'/'trial-1'
(trial/'verifier').mkdir(parents=True); (trial/'artifacts').mkdir()
(trial/'verifier/case_sha256.txt').write_text(case_sha+'\n')
(trial/'artifacts/manifest.json').write_text(json.dumps([{'source':'/app/submission','status':'ok'}]))
(trial/'result.json').write_text(json.dumps({'schema_version':1,'id':'trial-1',
 'finished_at':'now','task_id':{'path':str(task)},'agent_info':{'name':'oracle'},
 'verifier_environment_mode':'separate','exception_info':None,'reward_valid':True,
 'agent_result':{},'verifier_result':{'rewards':{'submit':1,'preserves':int(product=='good'),
 'quality':3 if product=='good' else 1,'work_count':1}}}))
'''


class HarborControllerIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        self.repo = self.dir / "repo"
        self.repo.mkdir()
        self.git("init", "-q")
        (self.repo / "product").write_text("bad")
        self.git("add", "product")
        self.git("-c", "user.name=T", "-c", "user.email=t@e", "commit", "-qm", "base")
        self.base = self.git("rev-parse", "HEAD")
        self.contract = self.dir / "contract"
        self.contract.write_text("preserve")
        self.verifier = self.dir / "verifier"
        self.verifier.mkdir()
        (self.verifier / "test.sh").write_text("#!/bin/sh\nexit 0\n")
        self.bin = self.dir / "harbor"
        self.bin.write_text(FAKE)
        self.bin.chmod(0o755)
        self.selection = self.dir / "selection"
        self.selection.write_text("selection")
        self.confirmation = self.dir / "confirmation"
        self.confirmation.write_text("holdout")
        self.root = self.dir / "run"
        self.backend = self.make_backend(self.verifier)

    @staticmethod
    def sha(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def make_backend(self, verifier):
        return {"kind":"harbor", "verifier_dir":str(verifier),
                "verifier_sha256":verifier_digest(verifier),
                "image":"python@sha256:" + "a"*64, "harbor_bin":str(self.bin),
                "harbor_bin_sha256":self.sha(self.bin), "network_mode":"no-network", "timeout_seconds":10}

    def git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.repo), *args], text=True).strip()

    def call(self, action, **kwargs):
        return experiment.execute({"action":action,"root":str(self.root),**kwargs})

    def init(self):
        return self.call("init", source=str(self.repo),experiment="e",base=self.base,paths=["product"],target="check",
          backend=self.backend,contract_file=str(self.contract),evaluator_file=str(self.verifier/"test.sh"),
          case_files={"sel":str(self.selection),"hold":str(self.confirmation)},
          evaluation={"cases":["sel"],"repetitions":1,"required_gates":["submit"],
                      "candidate_only_gates":["preserves"],"metric":"quality","direction":"higher",
                      "min_gain":1,"noise_floor":0,"deterministic":True},
          confirmation={"cases":["hold"],"repetitions":1},max_trials=12,max_tokens=0)

    def freeze(self):
        arm=self.call("allocate",arm="fix")
        (Path(arm["worktree"])/"product").write_text("good")
        return self.call("freeze",arm="fix",message="fix",writers_stopped=True)

    @unittest.skipUnless(os.environ.get("TKSTACK_GEPA_PYTHON"), "set TKSTACK_GEPA_PYTHON to run GEPA")
    def test_tampered_harbor_manifest_cannot_influence_later_gepa_search(self):
        training = self.dir / "training"
        training.write_text("distinct training case")
        self.call("init", source=str(self.repo), experiment="e", base=self.base, paths=["product"], target="check",
                  backend=self.backend, contract_file=str(self.contract), evaluator_file=str(self.verifier / "test.sh"),
                  case_files={"sel": str(self.selection), "train": str(training)},
                  evaluation={"cases": ["sel", "train"], "repetitions": 1,
                              "required_gates": ["submit"], "candidate_only_gates": ["preserves"],
                              "metric": "quality", "direction": "higher", "min_gain": 1,
                              "noise_floor": 0, "deterministic": True},
                  max_trials=12, max_tokens=0)
        request = {"root": str(self.root), "search": "first", "artifact_path": "product",
                   "training_cases": ["train"], "selection_cases": ["sel"], "proposals": ["good"],
                   "max_evaluations": 4, "max_proposals": 1, "max_model_tokens": 0, "metric_range": [0, 4]}
        request_path = self.dir / "search.json"
        def search():
            request_path.write_text(json.dumps(request))
            return subprocess.run([os.environ["TKSTACK_GEPA_PYTHON"], str(ROOT / "skills/hill-climb/scripts/experiment_gepa.py"), "--request", str(request_path)],
                                  capture_output=True, text=True, timeout=60)
        first = search()
        self.assertEqual(first.returncode, 0, first.stderr)
        for path in (self.root / "runs").glob("*.json"):
            record = json.loads(path.read_text())
            Path(record["result"]["harbor"]["artifact_manifest"]).write_text("[]")
        request["search"] = "second"
        second = search()
        self.assertNotEqual(second.returncode, 0, "GEPA reused a tampered Harbor trial")
        self.assertIn("manifest changed", second.stderr)

    def test_full_selection_confirmation_promotion_and_replay(self):
        self.init()
        chosen=self.freeze()
        for key, side in (("old","baseline"),("new","candidate")):
            record=self.call("run",side=side,arm="fix",rep=0,run_key=key)
            self.assertEqual(record["result"]["status"],"passed",record["result"].get("error"))
        self.assertEqual(self.call("compare",arm="fix",baseline=["old"],candidate=["new"],decision="pick")["decision"],"eligible")
        self.call("select",decision="pick")
        for key, side in (("h-old","baseline"),("h-new","candidate")):
            self.call("run",side=side,arm="fix",split="confirmation",rep=0,run_key=key)
        self.assertEqual(self.call("confirm",baseline=["h-old"],candidate=["h-new"])["decision"],"eligible")
        self.assertEqual(self.call("promote",arm="fix",decision="pick")["commit"],chosen["commit"])
        self.assertEqual(self.call("status")["ledger"]["settled_trials"],4)

    def test_same_tree_reuse_preserves_harbor_run_identity(self):
        self.init()
        first = self.freeze()
        second_arm = self.call("allocate", arm="second")
        (Path(second_arm["worktree"]) / "product").write_text("good")
        second = self.call("freeze", arm="second", message="second", writers_stopped=True)
        self.assertEqual(first["tree"], second["tree"])
        self.assertNotEqual(first["commit"], second["commit"])
        self.call("run", side="baseline", rep=0, run_key="old")
        receipt = self.call("run", side="candidate", arm="fix", rep=0, run_key="new")
        self.assertEqual(receipt["result"]["harbor"]["commit"], first["commit"])
        path = self.root / "runs" / "new.json"
        original = path.read_text()
        changed = json.loads(original)
        changed["result"]["commit"] = second["commit"]
        path.write_text(json.dumps(changed))
        with sqlite3.connect(self.root / "ledger.sqlite3") as db:
            event = db.execute("SELECT details FROM events WHERE run_key='new' AND operation='settle'").fetchone()
            details = json.loads(event[0])
            details["receipt_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
            db.execute("UPDATE events SET details=? WHERE run_key='new' AND operation='settle'",
                       (json.dumps(details),))
        with self.assertRaises(ValueError):
            self.call("compare", arm="second", baseline=["old"],
                      candidate=["new"], decision="bad-origin")
        path.write_text(original)
        with sqlite3.connect(self.root / "ledger.sqlite3") as db:
            db.execute("UPDATE events SET details=? WHERE run_key='new' AND operation='settle'",
                       (event[0],))
        self.assertEqual(self.call("compare", arm="second", baseline=["old"],
                                  candidate=["new"], decision="reuse")["decision"], "eligible")
        saved = json.loads((self.root / "decisions/reuse.json").read_text())
        self.assertEqual(saved["candidate"][0]["commit"], second["commit"])
        self.assertEqual(saved["candidate"][0]["provenance"],
                         {"kind": "same-tree", "run_key": "new", "source": first})
        self.call("select", decision="reuse")
        self.call("run", side="baseline", split="confirmation", rep=0, run_key="hold-old")
        self.call("run", side="candidate", arm="second", split="confirmation", rep=0, run_key="hold-new")
        self.assertEqual(self.call("confirm", baseline=["hold-old"], candidate=["hold-new"])["decision"], "eligible")
        self.assertEqual(self.call("promote", arm="second", decision="reuse")["commit"], second["commit"])

    def test_tampered_harbor_artifact_refuses_comparison(self):
        self.init();self.freeze()
        old=self.call("run",side="baseline",rep=0,run_key="old")
        self.call("run",side="candidate",arm="fix",rep=0,run_key="new")
        Path(old["result"]["harbor"]["artifact_manifest"]).write_text("[]")
        with self.assertRaisesRegex(ValueError,"manifest changed"):
            self.call("compare",arm="fix",baseline=["old"],candidate=["new"],decision="pick")
        with self.assertRaisesRegex(ValueError,"manifest changed"):
            self.call("recover-run",run_key="old")

    def test_ambiguous_harbor_run_stays_uncertain_and_cannot_recover(self):
        self.bin.write_text("#!/bin/sh\nif [ \\\"$1\\\" = --version ]; then echo 0.26.0; exit 0; fi\nexit 9\n".replace('\\\"','"'))
        self.bin.chmod(0o755)
        self.backend["harbor_bin_sha256"]=self.sha(self.bin)
        self.init()
        result=self.call("run",side="baseline",rep=0,run_key="old")
        self.assertEqual(result["result"]["status"],"unknown")
        ledger=self.call("status")["ledger"]
        self.assertEqual(ledger["reserved_trials"],1)
        self.assertEqual(ledger["runs"][0]["status"],"uncertain")
        with self.assertRaisesRegex(ValueError,"independent reconciliation"):
            self.call("recover-run",run_key="old")

    def test_calibration_and_revision_use_proposed_harbor_verifier(self):
        self.init(); good=self.freeze()
        new=self.dir/"new-verifier";new.mkdir()
        (new/"test.sh").write_text("#!/bin/sh\n# revised verifier\nexit 0\n")
        backend=self.make_backend(new)
        for key,commit in (("bad-cal",self.base),("good-cal",good["commit"])):
            self.call("calibration-run",run_key=key,commit=commit,case="sel",case_file=str(self.selection),
                      evaluator_file=str(new/"test.sh"),backend=backend)
        new_contract=self.dir/"contract2";new_contract.write_text("revised")
        self.call("feedback",id="F1",observation="preserve fields",interpretation="measure recovery",
                  counterexample="clears data",old_contract=self.sha(self.contract),new_contract=self.sha(new_contract),changes=["contract"])
        labels=[{"id":"bad","run_key":"bad-cal","gate":"preserves","expected":False},
                {"id":"good","run_key":"good-cal","gate":"preserves","expected":True}]
        uncalibrated=self.dir/"uncalibrated-verifier";uncalibrated.mkdir()
        (uncalibrated/"test.sh").write_text((new/"test.sh").read_text())
        (uncalibrated/"helper").write_text("different verifier dependency")
        with self.assertRaisesRegex(ValueError, "different evaluator"):
            self.call("revise",feedback="F1",contract_file=str(new_contract),
                      evaluator_file=str(uncalibrated/"test.sh"),
                      backend=self.make_backend(uncalibrated),calibration=labels)
        result=self.call("revise",feedback="F1",contract_file=str(new_contract),evaluator_file=str(new/"test.sh"),
                         backend=backend,calibration=labels)
        self.assertTrue(result["calibration"]["qualified"])
        self.assertEqual(experiment.config_for(self.root)["backend"]["verifier_sha256"],backend["verifier_sha256"])

    def test_flat_rewards_reject_gate_metric_name_collision_at_init(self):
        with self.assertRaisesRegex(ValueError, "distinct"):
            self.call("init", source=str(self.repo),experiment="e",base=self.base,paths=["product"],target="check",
                      backend=self.backend,contract_file=str(self.contract),evaluator_file=str(self.verifier/"test.sh"),
                      case_files={"sel":str(self.selection)},evaluation={"cases":["sel"],"repetitions":1,
                      "required_gates":["submit"],"metric":"submit","direction":"higher","min_gain":1,
                      "noise_floor":0,"deterministic":True},max_trials=4,max_tokens=0)

    def test_backend_evaluator_mismatch_is_rejected_at_init(self):
        wrong=self.dir/"wrong.sh";wrong.write_text((self.verifier/"test.sh").read_text())
        with self.assertRaisesRegex(ValueError,"verifier_dir/test.sh"):
            self.call("init",source=str(self.repo),experiment="e",base=self.base,paths=["product"],target="check",
                      backend=self.backend,contract_file=str(self.contract),evaluator_file=str(wrong),
                      case_files={"sel":str(self.selection)},evaluation={"cases":["sel"],"repetitions":1,
                      "required_gates":["submit"],"metric":"quality","direction":"higher","min_gain":1,
                      "noise_floor":0,"deterministic":True},max_trials=4,max_tokens=0)


if __name__ == "__main__":
    unittest.main()

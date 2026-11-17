import hashlib
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPTS = Path(__file__).resolve().parents[1] / "skills/hill-climb/scripts"
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location("experiment_harbor_controller", SCRIPTS / "experiment_harbor_controller.py")
controller = importlib.util.module_from_spec(spec)
spec.loader.exec_module(controller)


FAKE_HARBOR = r'''#!/usr/bin/env python3
import hashlib, json, pathlib, sys, tarfile, tomllib
if sys.argv[1:] == ['--version']:
    print('0.26.0')
    raise SystemExit(0)
assert sys.argv[1:3] == ['run', '-c']
config = json.loads(pathlib.Path(sys.argv[3]).read_text())
task = pathlib.Path(config['tasks'][0]['path'])
task_config = tomllib.loads((task / 'task.toml').read_text())
assert task_config['verifier']['environment_mode'] == 'separate'
assert task_config['artifacts'] == ['/app/submission']
with tarfile.open(task / 'solution' / 'source.tar') as archive:
    source = archive.extractfile('source.txt').read()
case = (task / 'tests' / 'case.input').read_bytes()
case_sha = hashlib.sha256(case).hexdigest()
trial = pathlib.Path(config['jobs_dir']) / 'candidate' / 'trial-1'
(trial / 'verifier').mkdir(parents=True)
(trial / 'artifacts').mkdir()
(trial / 'verifier' / 'case_sha256.txt').write_text(case_sha + '\n')
(trial / 'artifacts' / 'manifest.json').write_text(json.dumps([{'source':'/app/submission','status':'ok'}]))
record = {'schema_version': 1, 'id':'trial-1', 'finished_at':'now',
  'task_id':{'path':str(task)}, 'agent_info':{'name':'oracle'},
  'verifier_environment_mode':'separate', 'exception_info':None,
  'reward_valid':True, 'agent_result':{},
  'verifier_result':{'rewards':{'correct':int(source == case),'quality':0.75,'work_count':1}}}
(trial / 'result.json').write_text(json.dumps(record))
'''


class ControllerBridgeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.git("init", "-q")
        (self.repo / "source.txt").write_text("baseline")
        self.git("add", "source.txt")
        self.git("-c", "user.name=Test", "-c", "user.email=t@example.invalid", "commit", "-qm", "base")
        self.commit = self.git("rev-parse", "HEAD")
        self.tree = self.git("rev-parse", "HEAD^{tree}")
        self.verifier = self.root / "verifier"
        self.verifier.mkdir()
        (self.verifier / "test.sh").write_text("#!/bin/sh\nexit 0\n")
        self.case = self.root / "case"
        self.case.write_text("baseline")
        self.case_sha = self.hash(self.case)
        self.bin = self.root / "harbor"
        self.bin.write_text(FAKE_HARBOR)
        self.bin.chmod(0o755)
        self.backend = {
            "kind": "harbor", "verifier_dir": str(self.verifier),
            "verifier_sha256": controller.verifier_digest(self.verifier),
            "image": "python@sha256:" + "a" * 64, "harbor_bin": str(self.bin),
            "harbor_bin_sha256": self.hash(self.bin), "network_mode": "no-network",
            "timeout_seconds": 10,
        }
        self.evaluator = {"path": str(self.verifier / "test.sh"),
                          "sha256": self.hash(self.verifier / "test.sh")}

    @staticmethod
    def hash(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.repo), *args], text=True).strip()

    def run_trial(self):
        return controller.run_controller_harbor(
            self.repo, self.commit, self.tree, self.backend, self.evaluator,
            ["component"], "component", self.case, self.case_sha, self.root / "run",
            ["correct"], ["quality"])

    def verify(self, result):
        return controller.verify_controller_harbor(
            result, self.backend, self.evaluator, case_sha256=self.case_sha,
            required_gates=["correct"], metric_names=["quality"])

    def test_mocked_harbor_end_to_end_binds_and_replays_measurement(self):
        (self.repo / "source.txt").write_text("dirty ignored working copy")
        result = self.run_trial()
        self.assertEqual(result["status"], "passed", result.get("error"))
        self.assertTrue(self.verify(result))
        measurement = controller.strict_loads(result["stdout"])
        self.assertEqual(measurement, {"case_sha256": self.case_sha, "gates": {"correct": True},
                                       "metrics": {"quality": 0.75}, "work_count": 1})
        self.assertEqual((self.repo / "source.txt").read_text(), "dirty ignored working copy")

    def test_drift_or_tampered_receipt_is_rejected(self):
        result = self.run_trial()
        self.assertTrue(self.verify(result))
        Path(result["harbor"]["artifact_manifest"]).write_text("[]")
        with self.assertRaises(ValueError):
            self.verify(result)

    def test_authoritative_evaluator_and_full_directory_are_pinned(self):
        other = self.root / "other.sh"
        other.write_text((self.verifier / "test.sh").read_text())
        with self.assertRaisesRegex(ValueError, "evaluator must"):
            controller.validate_controller_harbor(self.backend, {"path": str(other), "sha256": self.hash(other)})
        (self.verifier / "helper").write_text("new")
        result = self.run_trial()
        self.assertEqual(result["status"], "infra_error")
        self.assertFalse((self.root / "run").exists())

    def test_failed_harbor_launch_is_unknown_and_no_local_fallback_runs(self):
        self.bin.write_text("#!/bin/sh\nif [ \\\"$1\\\" = --version ]; then echo 0.26.0; exit 0; fi\nexit 9\n".replace('\\\"', '"'))
        self.bin.chmod(0o755)
        self.backend["harbor_bin_sha256"] = self.hash(self.bin)
        result = self.run_trial()
        self.assertEqual(result["status"], "unknown")
        self.assertEqual(result["stdout"], "")
        self.assertTrue((self.root / "run/dispatch-intent.json").exists())
        with self.assertRaises(ValueError):
            self.verify(result)


if __name__ == "__main__":
    unittest.main()

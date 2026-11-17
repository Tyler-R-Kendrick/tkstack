import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


SCRIPTS = Path(__file__).resolve().parents[1] / "skills/hill-climb/scripts"
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location("experiment_harbor", SCRIPTS / "experiment_harbor.py")
harbor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(harbor)


class HarborAdapterTests(unittest.TestCase):
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
        self.case.write_bytes(b"case one")
        self.case_digest = hashlib.sha256(self.case.read_bytes()).hexdigest()
        self.image = "python@sha256:" + "a" * 64

    def git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.repo), *args], text=True).strip()

    def args(self):
        return (self.repo, self.commit, self.tree, self.verifier,
                harbor.verifier_digest(self.verifier), self.image, self.root / "run")

    def fake_execute(self, argv, cwd, home, timeout, limit, snapshot_root):
        if argv[-1] == "--version":
            return {"status": "passed", "stdout": "0.26.0\n"}
        config = json.loads(Path(argv[-1]).read_text())
        task = Path(config["tasks"][0]["path"])
        self.assertEqual(hashlib.sha256((task / "tests/case.input").read_bytes()).hexdigest(), self.case_digest)
        self.assertIn('environment_mode = "separate"', (task / "task.toml").read_text())
        trial = Path(config["jobs_dir"]) / "candidate" / "trial-1"
        (trial / "verifier").mkdir(parents=True)
        (trial / "artifacts").mkdir()
        (trial / "verifier/case_sha256.txt").write_text(self.case_digest + "\n")
        (trial / "artifacts/manifest.json").write_text(json.dumps([
            {"source": "/app/submission", "status": "ok"}
        ]))
        (trial / "result.json").write_text(json.dumps({
            "schema_version": 1, "id": "trial-1", "finished_at": "now",
            "task_id": {"path": str(task)}, "agent_info": {"name": "oracle"},
            "verifier_environment_mode": "separate", "exception_info": None,
            "reward_valid": True, "verifier_result": {"rewards": {"gate": 1, "quality": 0.75, "work_count": 1}},
            "agent_result": {"n_input_tokens": None},
        }))
        return {"status": "passed", "exit_code": 0, "stdout": "", "stderr": ""}

    def test_separate_verifier_receipt_binds_case_and_candidate(self):
        with patch.object(harbor.shutil, "which", return_value="/bin/harbor"), patch.object(harbor, "_execute", side_effect=self.fake_execute):
            result = harbor.run_harbor_trial(*self.args(), case_file=self.case, expected_case_sha256=self.case_digest)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["rewards"], {"gate": 1, "quality": 0.75, "work_count": 1})
        self.assertEqual((result["commit"], result["tree"], result["case_sha256"]), (self.commit, self.tree, self.case_digest))
        self.assertEqual(hashlib.sha256(Path(result["trial_result"]).read_bytes()).hexdigest(), result["trial_result_sha256"])
        self.assertTrue((self.root / "run/dispatch-intent.json").exists())
        self.assertFalse((self.repo / "source.txt").read_text() != "baseline")

    def test_case_and_verifier_drift_are_refused_before_dispatch(self):
        args = list(self.args())
        args[4] = "0" * 64
        with patch.object(harbor.shutil, "which", return_value="/bin/harbor"), patch.object(harbor, "_execute") as execute:
            result = harbor.run_harbor_trial(*args, case_file=self.case, expected_case_sha256=self.case_digest)
        self.assertEqual(result["status"], "infra_error")
        execute.assert_not_called()
        self.assertFalse((self.root / "run/dispatch-intent.json").exists())

    def test_missing_executable_is_unavailable_and_run_cannot_be_reused(self):
        with patch.object(harbor.shutil, "which", return_value=None):
            result = harbor.run_harbor_trial(*self.args(), case_file=self.case, expected_case_sha256=self.case_digest)
        self.assertEqual(result["status"], "unavailable")
        with self.assertRaises(FileExistsError):
            harbor.run_harbor_trial(*self.args(), case_file=self.case, expected_case_sha256=self.case_digest)

    def test_timeout_after_dispatch_is_unknown(self):
        def execute(argv, *rest):
            if argv[-1] == "--version":
                return {"status": "passed", "stdout": "0.26.0\n"}
            return {"status": "timeout"}
        with patch.object(harbor.shutil, "which", return_value="/bin/harbor"), patch.object(harbor, "_execute", side_effect=execute):
            result = harbor.run_harbor_trial(*self.args(), case_file=self.case, expected_case_sha256=self.case_digest)
        self.assertEqual(result["status"], "unknown")
        self.assertIn("may still be running", result["error"])
        self.assertTrue((self.root / "run/dispatch-intent.json").exists())

    def test_deadline_expiring_during_staging_never_dispatches(self):
        clock = [100.0]
        def materialize(repo, commit, root):
            clock[0] = 106.0
        with patch.object(harbor.time, "monotonic", side_effect=lambda: clock[0]), \
             patch.object(harbor.shutil, "which", return_value="/bin/harbor"), \
             patch.object(harbor, "_materialize", side_effect=materialize), \
             patch.object(harbor, "_execute") as execute:
            result = harbor.run_harbor_trial(*self.args(), case_file=self.case,
                                             expected_case_sha256=self.case_digest, deadline=105.0)
        self.assertEqual(result["status"], "timeout")
        self.assertFalse((self.root / "run/dispatch-intent.json").exists())
        execute.assert_not_called()

    def test_missing_case_attestation_does_not_complete(self):
        def execute(argv, cwd, home, timeout, limit, snapshot_root):
            result = self.fake_execute(argv, cwd, home, timeout, limit, snapshot_root)
            if argv[-1] != "--version":
                config = json.loads(Path(argv[-1]).read_text())
                receipt = Path(config["jobs_dir"]) / "candidate/trial-1/verifier/case_sha256.txt"
                receipt.write_text("0" * 64)
            return result
        with patch.object(harbor.shutil, "which", return_value="/bin/harbor"), patch.object(harbor, "_execute", side_effect=execute):
            result = harbor.run_harbor_trial(*self.args(), case_file=self.case, expected_case_sha256=self.case_digest)
        self.assertEqual(result["status"], "unknown")
        self.assertIn("case digest", result["error"])

    def test_bridge_requires_case_bound_finite_complete_measurement(self):
        with patch.object(harbor.shutil, "which", return_value="/bin/harbor"), patch.object(harbor, "_execute", side_effect=self.fake_execute):
            result = harbor.run_harbor_trial(*self.args(), case_file=self.case, expected_case_sha256=self.case_digest)
        result["rewards"] = {"gate": 1, "quality": 0.75, "work_count": 1}
        expected = {"case_sha256": self.case_digest, "gates": {"gate": True},
                    "metrics": {"quality": 0.75}, "work_count": 1}
        self.assertEqual(harbor.measurement_from_rewards(result, ["gate"], ["quality"]), expected)
        for bad_rewards in ({"gate": True, "quality": 1, "work_count": 1},
                            {"gate": 2, "quality": 1, "work_count": 1},
                            {"gate": 1, "quality": float("nan"), "work_count": 1},
                            {"gate": 1, "quality": 10 ** 400, "work_count": 1},
                            {"gate": 1, "quality": 1, "work_count": 0},
                            {"gate": 1, "work_count": 1}):
            with self.subTest(rewards=bad_rewards), self.assertRaises(ValueError):
                trial_path = Path(result["trial_result"])
                trial = json.loads(trial_path.read_text())
                trial["verifier_result"]["rewards"] = bad_rewards
                trial_path.write_text(json.dumps(trial))
                changed = {**result, "rewards": bad_rewards,
                           "trial_result_sha256": hashlib.sha256(trial_path.read_bytes()).hexdigest()}
                harbor.measurement_from_rewards(changed, ["gate"], ["quality"])
        Path(result["case_receipt"]).write_text("0" * 64)
        with self.assertRaises(ValueError):
            harbor.measurement_from_rewards(result, ["gate"], ["quality"])
        with self.assertRaises(ValueError):
            harbor.measurement_from_rewards({**result, "status": "unknown"}, ["gate"], ["quality"])

    def test_run_directory_cannot_be_inside_verifier(self):
        args = list(self.args())
        args[6] = self.verifier / "new-run"
        with self.assertRaises(ValueError):
            harbor.run_harbor_trial(*args, case_file=self.case, expected_case_sha256=self.case_digest)

    def test_verifier_cannot_use_symlink_or_build_definition(self):
        (self.verifier / "link").symlink_to("test.sh")
        with self.assertRaises(ValueError):
            harbor.verifier_digest(self.verifier)
        (self.verifier / "link").unlink()
        (self.verifier / "Dockerfile").write_text("FROM scratch")
        with self.assertRaises(ValueError):
            harbor.verifier_digest(self.verifier)

    def test_empty_verifier_directories_affect_digest(self):
        before = harbor.verifier_digest(self.verifier)
        folder = self.verifier / "expected-empty-dir"
        folder.mkdir()
        with_folder = harbor.verifier_digest(self.verifier)
        self.assertNotEqual(before, with_folder)
        folder.chmod((folder.stat().st_mode & 0o777) ^ 0o100)
        self.assertNotEqual(with_folder, harbor.verifier_digest(self.verifier))

    def test_invalid_pinning_is_rejected(self):
        args = list(self.args())
        args[5] = "python:latest"
        with self.assertRaises(ValueError):
            harbor.run_harbor_trial(*args, case_file=self.case, expected_case_sha256=self.case_digest)


if __name__ == "__main__":
    unittest.main()

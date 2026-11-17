"""End-to-end behavior of the scoped Git experiment entry point."""
import hashlib
import json
import os
import sqlite3
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/hill-climb/scripts/experiment.py"


class ExperimentIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.source = self.directory / "source"
        self.source.mkdir()
        self.git("init", "-q")
        (self.source / "product.txt").write_text("loses fields")
        self.git("add", "product.txt")
        self.git("-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                 "commit", "-qm", "initial")
        self.base = self.git("rev-parse", "HEAD")
        self.contract = self.directory / "contract.txt"
        self.contract.write_text("preserve all fields")
        self.grader = self.directory / "grader.py"
        self.grader.write_text(
            "import json\nfrom pathlib import Path\n"
            "text = Path('product.txt').read_text()\n"
            "print(json.dumps({'gates': {'submit': True}, "
            "'metrics': {'recovery': 3 if text == 'preserves fields' else 1}, "
            "'work_count': 1}))\n"
        )
        self.root = self.directory / "experiment"

    def git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.source), *args], text=True).strip()

    def _prepare(self, action, fields):
        if action not in ("init", "revise", "calibration-run"):
            return fields
        fields = dict(fields)
        grader = Path(fields["evaluator_file"])
        marker = "# fixture-verifier-attestation\n"
        body = grader.read_text()
        if not body.startswith(marker):
            grader.write_text(marker + '''import builtins as _b, hashlib as _h, json as _j, sys as _s
from pathlib import Path as _P
def print(*args, **kwargs):
    if len(args) == 1:
        try:
            data = _j.loads(args[0])
            if isinstance(data, dict) and 'gates' in data:
                data['case_sha256'] = _h.sha256(_P(_s.argv[-1]).read_bytes()).hexdigest()
                data['gates']['preserves'] = _P('product.txt').read_text() == 'preserves fields'
                args = (_j.dumps(data),)
        except (ValueError, TypeError):
            pass
    return _b.print(*args, **kwargs)
''' + body)
        fields["trusted_interpreter"] = sys.executable
        entry = fields["registry"]["check"]
        args = list(entry["argv"])
        if "{{case_file}}" not in args:
            args.append("{{case_file}}")
        fields["registry"] = {"check": {"argv": args, "cwd": entry["cwd"]}}
        if action == "calibration-run":
            return fields
        if action == "init":
            evaluation = fields["evaluation"]
            confirmation = fields.get("confirmation")
        else:
            with sqlite3.connect(self.root / "ledger.sqlite3") as db:
                path = db.execute("SELECT path FROM controller_config WHERE id=1").fetchone()[0]
            current = json.loads((self.root / path).read_text())
            evaluation = fields.get("evaluation", current["evaluation"])
            confirmation = fields.get("confirmation", current.get("confirmation"))
        cases = evaluation.get("cases", [evaluation.get("case")])
        cases = [case for case in cases if isinstance(case, str)]
        if isinstance(confirmation, dict):
            cases += confirmation["cases"]
        files = {}
        for case in cases:
            path = self.directory / ("case-" + hashlib.sha256(case.encode()).hexdigest())
            if not path.exists():
                path.write_text(case)
            files[case] = str(path)
        fields["case_files"] = files
        return fields

    def call(self, action, **fields):
        fields = self._prepare(action, fields)
        request = self.directory / "request.json"
        request.write_text(json.dumps({"action": action, "root": str(self.root), **fields}))
        result = subprocess.run([sys.executable, str(SCRIPT), "--request", str(request)],
                                text=True, capture_output=True)
        if result.returncode:
            self.fail(f"{action} failed: {result.stderr}")
        return json.loads(result.stdout)


    def confirmation_setup(self, max_trials=4):
        self.call("init", source=str(self.source), experiment="confirm", base=self.base,
                  paths=["product.txt"], target="check",
                  registry={"check": {"argv": [sys.executable, str(self.grader), "{{case}}"], "cwd": "."}},
                  contract_file=str(self.contract), evaluator_file=str(self.grader),
                  evaluation={"cases": ["selection"], "repetitions": 1,
                              "required_gates": ["submit"], "metric": "recovery",
                              "direction": "higher", "min_gain": 1, "noise_floor": 0,
                              "deterministic": True},
                  confirmation={"cases": ["holdout"], "repetitions": 1},
                  max_trials=max_trials, max_tokens=0)
        arm = self.call("allocate", arm="fix")
        (Path(arm["worktree"]) / "product.txt").write_text("preserves fields")
        frozen = self.call("freeze", arm="fix", message="fix", writers_stopped=True)
        self.call("run", side="baseline", rep=0, run_key="old")
        self.call("run", side="candidate", arm="fix", rep=0, run_key="new")
        self.call("compare", arm="fix", baseline=["old"], candidate=["new"], decision="pick")
        return frozen

    def assert_call_fails(self, action, **fields):
        fields = self._prepare(action, fields)
        request = self.directory / "failed-request.json"
        request.write_text(json.dumps({"action": action, "root": str(self.root), **fields}))
        result = subprocess.run([sys.executable, str(SCRIPT), "--request", str(request)],
                                text=True, capture_output=True)
        self.assertNotEqual(result.returncode, 0, result.stdout)
        return result.stderr

    def _calibration(self, grader, registry):
        with sqlite3.connect(self.root / "ledger.sqlite3") as db:
            path = db.execute("SELECT path FROM controller_config WHERE id=1").fetchone()[0]
        config = json.loads((self.root / path).read_text())
        case = config["evaluation"]["cases"][0]
        commit = subprocess.check_output(["git", "--git-dir", str(self.root / "repo.git"),
            "rev-parse", f"refs/heads/exp/{config['experiment']}/fix"], text=True).strip()
        for key, revision in (("cal-bad", self.base), ("cal-good", commit)):
            self.call("calibration-run", run_key=key, commit=revision, case=case,
                      case_file=config["case_files"][case]["path"], evaluator_file=str(grader), registry=registry)
        return [{"id": "good", "run_key": "cal-good", "gate": "preserves", "expected": True},
                {"id": "bad", "run_key": "cal-bad", "gate": "preserves", "expected": False}]

    def test_confirmation_locks_winner_and_requires_disjoint_trials(self):
        frozen = self.confirmation_setup()
        self.assert_call_fails("promote", arm="fix", decision="pick")
        self.call("select", decision="pick")
        self.assert_call_fails("retire", arm="fix", expected=frozen["commit"], writers_stopped=True)
        self.assert_call_fails("run", side="baseline", rep=0, run_key="extra")
        self.assert_call_fails("compare", arm="fix", baseline=["old"], candidate=["new"], decision="extra")
        self.assert_call_fails("run", side="baseline", split="confirmation", case="selection", rep=0, run_key="bad")
        self.assert_call_fails("run", side="candidate", arm="other", split="confirmation", rep=0, run_key="wrong")
        self.assert_call_fails("freeze", arm="fix", message="change", writers_stopped=True)
        self.call("run", side="baseline", split="confirmation", rep=0, run_key="hold-old")
        self.assert_call_fails("run", side="baseline", split="confirmation", rep=0, run_key="repeat")
        self.call("run", side="candidate", arm="fix", split="confirmation", rep=0, run_key="hold-new")
        self.assertEqual(self.call("confirm", baseline=["hold-old"], candidate=["hold-new"])["decision"], "eligible")
        self.assert_call_fails("run", side="baseline", split="confirmation", rep=0, run_key="again")
        self.assertEqual(self.call("promote", arm="fix", decision="pick")["commit"], frozen["commit"])
        self.assertEqual(self.call("status")["ledger"]["settled_trials"], 4)

    def test_confirmation_rejects_regression_and_reused_selection(self):
        self.grader.write_text(
            "import json,sys\nfrom pathlib import Path\n"
            "good = Path('product.txt').read_text() == 'preserves fields'\n"
            "case = sys.argv[1]\n"
            "print(json.dumps({'gates': {'submit': case != 'holdout' or not good}, "
            "'metrics': {'recovery': 3 if good else 1}, 'work_count': 1}))\n")
        self.confirmation_setup()
        self.call("select", decision="pick")
        self.assert_call_fails("confirm", baseline=["old"], candidate=["new"])
        self.call("run", side="baseline", split="confirmation", rep=0, run_key="hold-old")
        self.call("run", side="candidate", arm="fix", split="confirmation", rep=0, run_key="hold-new")
        self.assertEqual(self.call("confirm", baseline=["hold-old"], candidate=["hold-new"])["decision"], "reject")
        self.assert_call_fails("promote", arm="fix", decision="pick")

    def test_confirmation_cases_must_be_disjoint(self):
        error = self.assert_call_fails("init", source=str(self.source), experiment="overlap", base=self.base,
                  paths=["product.txt"], target="check",
                  registry={"check": {"argv": [sys.executable, str(self.grader), "{{case}}"], "cwd": "."}},
                  contract_file=str(self.contract), evaluator_file=str(self.grader),
                  evaluation={"case": "same", "repetitions": 1,
                              "required_gates": ["submit"], "metric": "recovery",
                              "direction": "higher", "min_gain": 1, "noise_floor": 0,
                              "deterministic": True},
                  confirmation={"cases": ["same"], "repetitions": 1},
                  max_trials=4, max_tokens=0)
        self.assertIn("disjoint", error)

    def test_revision_before_selection_cannot_relabel_holdout(self):
        self.confirmation_setup(max_trials=6)
        current = hashlib.sha256(self.contract.read_bytes()).hexdigest()
        self.call("feedback", id="scope", observation="adjust cases", interpretation="check history",
                  counterexample="leaked holdout", old_contract=current, new_contract=current, changes=["cases"])
        registry = {"check": {"argv": [sys.executable, str(self.grader), "{{case}}"], "cwd": "."}}
        calibration = self._calibration(self.grader, registry)
        evaluation = {"cases": ["holdout"], "repetitions": 1, "required_gates": ["submit"],
                      "candidate_only_gates": ["preserves"],
                      "metric": "recovery", "direction": "higher", "min_gain": 1,
                      "noise_floor": 0, "deterministic": True}
        error = self.assert_call_fails("revise", feedback="scope", contract_file=str(self.contract),
            evaluator_file=str(self.grader), registry=registry, evaluation=evaluation, calibration=calibration)
        self.assertIn("selection and confirmation cases contain the same input bytes", error)

    def test_promoted_generation_requires_fresh_confirmation(self):
        self.confirmation_setup(max_trials=10)
        self.call("select", decision="pick")
        self.call("run", side="baseline", split="confirmation", rep=0, run_key="hold-old")
        self.call("run", side="candidate", arm="fix", split="confirmation", rep=0, run_key="hold-new")
        self.call("confirm", baseline=["hold-old"], candidate=["hold-new"])
        self.call("promote", arm="fix", decision="pick")
        self.assert_call_fails("run", side="baseline", rep=0, run_key="next-old")
        current = hashlib.sha256(self.contract.read_bytes()).hexdigest()
        self.call("feedback", id="next", observation="new round", interpretation="fresh holdout",
                  counterexample="previously used", old_contract=current, new_contract=current, changes=["cases"])
        registry = {"check": {"argv": [sys.executable, str(self.grader), "{{case}}"], "cwd": "."}}
        calibration = self._calibration(self.grader, registry)
        evaluation = {"cases": ["selection"], "repetitions": 1, "required_gates": ["submit"],
                      "candidate_only_gates": ["preserves"], "metric": "recovery", "direction": "higher",
                      "min_gain": 1, "noise_floor": 0, "deterministic": True}
        args = dict(feedback="next", contract_file=str(self.contract), evaluator_file=str(self.grader),
                    registry=registry, calibration=calibration, evaluation=evaluation)
        self.assert_call_fails("revise", **args, confirmation={"cases": ["holdout"], "repetitions": 1})
        self.assert_call_fails("revise", **args, confirmation={"cases": ["selection"], "repetitions": 1})
        self.call("revise", **args, confirmation={"cases": ["fresh"], "repetitions": 1})
        self.call("run", side="baseline", rep=0, run_key="next-old")

    def test_revision_rechecks_case_binding(self):
        self.confirmation_setup(max_trials=6)
        current = hashlib.sha256(self.contract.read_bytes()).hexdigest()
        self.call("feedback", id="args", observation="more cases", interpretation="bind inputs",
                  counterexample="same input repeated", old_contract=current, new_contract=current, changes=["cases"])
        registry = {"check": {"argv": [sys.executable, str(self.grader)], "cwd": "."}}
        calibration = self._calibration(self.grader, registry)
        evaluation = {"cases": ["one", "two"], "repetitions": 1, "required_gates": ["submit"],
                      "candidate_only_gates": ["preserves"],
                      "metric": "recovery", "direction": "higher", "min_gain": 1,
                      "noise_floor": 0, "deterministic": True}
        error = self.assert_call_fails("revise", feedback="args", contract_file=str(self.contract),
            evaluator_file=str(self.grader), registry=registry, evaluation=evaluation, calibration=calibration)
        self.assertIn("multi-case targets must pass {{case}}", error)

    def test_failed_confirmation_requires_fresh_cases_with_same_budget(self):
        self.grader.write_text(
            "import json,sys\nfrom pathlib import Path\n"
            "good = Path('product.txt').read_text() == 'preserves fields'\n"
            "case = sys.argv[1]\n"
            "print(json.dumps({'gates': {'submit': case != 'holdout' or not good}, "
            "'metrics': {'recovery': 3 if good else 1}, 'work_count': 1}))\n")
        self.confirmation_setup(max_trials=10)
        self.call("select", decision="pick")
        self.call("run", side="baseline", split="confirmation", rep=0, run_key="h-old")
        self.call("run", side="candidate", arm="fix", split="confirmation", rep=0, run_key="h-new")
        self.assertEqual(self.call("confirm", baseline=["h-old"], candidate=["h-new"])["decision"], "reject")
        self.assertEqual(self.call("status")["confirmation"]["decision"], "reject")
        self.assert_call_fails("run", side="baseline", split="confirmation", rep=0, run_key="retry")
        revised = self.directory / "contract-next.txt"
        revised.write_text("updated recovery contract")
        old = hashlib.sha256(self.contract.read_bytes()).hexdigest()
        new = hashlib.sha256(revised.read_bytes()).hexdigest()
        self.call("feedback", id="F2", observation="holdout failed", interpretation="recheck",
                  counterexample="holdout regression", old_contract=old, new_contract=new,
                  changes=["contract"])
        registry = {"check": {"argv": [sys.executable, str(self.grader), "{{case}}"], "cwd": "."}}
        calibration = self._calibration(self.grader, registry)
        evaluation = {"cases": ["selection"], "repetitions": 1, "required_gates": ["submit"],
                      "candidate_only_gates": ["preserves"], "metric": "recovery", "direction": "higher",
                      "min_gain": 1, "noise_floor": 0, "deterministic": True}
        args = dict(feedback="F2", contract_file=str(revised), evaluator_file=str(self.grader),
                    registry=registry, evaluation=evaluation, calibration=calibration)
        self.assert_call_fails("revise", **args, confirmation={"cases": ["holdout"], "repetitions": 1})
        self.call("revise", **args, confirmation={"cases": ["fresh"], "repetitions": 1})
        self.call("run", side="baseline", rep=0, run_key="rev-old")
        self.call("run", side="candidate", arm="fix", rep=0, run_key="rev-new")
        self.call("compare", arm="fix", baseline=["rev-old"], candidate=["rev-new"], decision="rev-pick")
        self.call("select", decision="rev-pick")
        self.call("run", side="baseline", split="confirmation", rep=0, run_key="fresh-old")
        self.call("run", side="candidate", arm="fix", split="confirmation", rep=0, run_key="fresh-new")
        self.assertEqual(self.call("confirm", baseline=["fresh-old"], candidate=["fresh-new"])["decision"], "eligible")
        self.call("promote", arm="fix", decision="rev-pick")
        self.assertEqual(self.call("status")["ledger"]["settled_trials"], 10)

    def test_same_contract_evaluator_revision_rebaselines_old_runs(self):
        self.call("init", source=str(self.source), experiment="same", base=self.base,
                  paths=["product.txt"], target="check",
                  registry={"check": {"argv": [sys.executable, str(self.grader)], "cwd": "."}},
                  contract_file=str(self.contract), evaluator_file=str(self.grader),
                  evaluation={"case": "one", "repetitions": 1, "required_gates": ["submit"],
                              "metric": "recovery", "direction": "higher", "min_gain": 1,
                              "noise_floor": 0, "deterministic": True}, max_trials=6, max_tokens=0)
        arm = self.call("allocate", arm="fix")
        (Path(arm["worktree"]) / "product.txt").write_text("preserves fields")
        self.call("freeze", arm="fix", message="fix", writers_stopped=True)
        self.call("run", side="baseline", rep=0, run_key="old")
        self.call("run", side="candidate", arm="fix", rep=0, run_key="new")
        old = hashlib.sha256(self.contract.read_bytes()).hexdigest()
        self.call("feedback", id="F3", observation="evaluation omitted a case",
                  interpretation="improve evaluator", counterexample="faulty result", old_contract=old,
                  new_contract=old, changes=["evaluator"])
        revised = self.directory / "grader-next.py"
        revised.write_text(self.grader.read_text() + "# revised evaluator\n")
        registry = {"check": {"argv": [sys.executable, str(revised)], "cwd": "."}}
        calibration = self._calibration(revised, registry)
        evaluation = {"cases": ["one"], "repetitions": 1, "required_gates": ["submit"],
                      "candidate_only_gates": ["preserves"], "metric": "recovery", "direction": "higher",
                      "min_gain": 1, "noise_floor": 0, "deterministic": True}
        self.call("revise", feedback="F3", contract_file=str(self.contract), evaluator_file=str(revised),
                  registry=registry, evaluation=evaluation, calibration=calibration)
        self.assert_call_fails("compare", arm="fix", baseline=["old"], candidate=["new"], decision="old-runs")
        self.call("run", side="baseline", rep=0, run_key="next-old")
        self.call("run", side="candidate", arm="fix", rep=0, run_key="next-new")
        self.assertEqual(self.call("compare", arm="fix", baseline=["next-old"], candidate=["next-new"],
                                   decision="next")["decision"], "eligible")
        self.assertEqual(self.call("status")["ledger"]["settled_trials"], 6)

    def test_finalist_cannot_change_after_selection(self):
        self.confirmation_setup()
        self.call("select", decision="pick")
        worktree = self.root / "worktrees" / "confirm" / "fix"
        (worktree / "product.txt").write_text("changed after selection")
        subprocess.run(["git", "-C", str(worktree), "add", "product.txt"], check=True)
        subprocess.run(["git", "-C", str(worktree), "-c", "user.name=Test", "-c",
                        "user.email=test@example.invalid", "commit", "-qm", "alter"], check=True)
        self.assert_call_fails("run", side="candidate", arm="fix", split="confirmation", rep=0, run_key="changed")

    def test_duplicate_json_requests_are_rejected(self):
        request = self.directory / "duplicate.json"
        request.write_text('{"action":"status","action":"init","root":"unused"}')
        result = subprocess.run([sys.executable, str(SCRIPT), "--request", str(request)],
                                text=True, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Duplicate JSON field", result.stderr)

    def test_missing_ledger_read_does_not_create_file(self):
        self.root.mkdir()
        self.assert_call_fails("status")
        self.assertFalse((self.root / "ledger.sqlite3").exists())

    def test_feature_experiment_and_evidence_revalidation(self):
        self.call("init", source=str(self.source), experiment="recovery", base=self.base,
                  paths=["product.txt"], target="check",
                  registry={"check": {"argv": [sys.executable, str(self.grader)], "cwd": "."}},
                  contract_file=str(self.contract), evaluator_file=str(self.grader),
                  evaluation={"case": "invalid-field", "repetitions": 1,
                              "required_gates": ["submit"], "metric": "recovery",
                              "direction": "higher", "min_gain": 1, "noise_floor": 0,
                              "deterministic": True},
                  max_trials=2, max_tokens=0)
        arm = self.call("allocate", arm="fix")
        (Path(arm["worktree"]) / "product.txt").write_text("preserves fields")
        frozen = self.call("freeze", arm="fix", message="Preserve fields", writers_stopped=True)
        self.call("run", side="baseline", rep=0, run_key="old")
        self.call("run", side="candidate", arm="fix", rep=0, run_key="new")
        compared = self.call("compare", arm="fix", baseline=["old"], candidate=["new"],
                             decision="choice")
        self.assertEqual(compared["decision"], "eligible")
        promoted = self.call("promote", arm="fix", decision="choice")
        self.assertEqual(promoted["commit"], frozen["commit"])
        (self.root / "promotions" / "choice.completed.json").unlink()
        self.assertEqual(self.call("recover", decision="choice")["state"], "completed")
        self.assertEqual(self.git("rev-parse", "HEAD"), self.base)
        self.assertEqual((self.source / "product.txt").read_text(), "loses fields")
        self.assertEqual(self.call("status")["ledger"]["settled_trials"], 2)

    def test_feedback_revision_rebaselines_and_uses_same_trial_budget(self):
        self.grader.write_text(
            "import json\nprint(json.dumps({'gates': {'submit': True}, "
            "'metrics': {'recovery': 1}, 'work_count': 1}))\n")
        self.call("init", source=str(self.source), experiment="feedback", base=self.base,
                  paths=["product.txt"], target="check",
                  registry={"check": {"argv": [sys.executable, str(self.grader)], "cwd": "."}},
                  contract_file=str(self.contract), evaluator_file=str(self.grader),
                  evaluation={"case": "invalid-field", "repetitions": 1,
                              "required_gates": ["submit"], "metric": "recovery",
                              "direction": "higher", "min_gain": 1, "noise_floor": 0,
                              "deterministic": True}, max_trials=6, max_tokens=0)
        arm = self.call("allocate", arm="fix")
        (Path(arm["worktree"]) / "product.txt").write_text("preserves fields")
        self.call("freeze", arm="fix", message="fix", writers_stopped=True)
        self.call("run", side="baseline", rep=0, run_key="old-a")
        self.call("run", side="candidate", arm="fix", rep=0, run_key="old-b")
        old = self.call("compare", arm="fix", baseline=["old-a"], candidate=["old-b"], decision="old")
        self.assertEqual(old["decision"], "reject")
        revised_contract = self.directory / "contract-v2.txt"
        revised_contract.write_text("preserve valid entries and explain correction")
        revised_grader = self.directory / "grader-v2.py"
        revised_grader.write_text(
            "import json\nfrom pathlib import Path\n"
            "good = Path('product.txt').read_text() == 'preserves fields'\n"
            "print(json.dumps({'gates': {'submit': True, 'preserves': good}, "
            "'metrics': {'recovery': 3 if good else 1}, 'work_count': 1}))\n")
        old_hash = hashlib.sha256(self.contract.read_bytes()).hexdigest()
        new_hash = hashlib.sha256(revised_contract.read_bytes()).hexdigest()
        self.call("feedback", id="F1", observation="I must re-enter valid fields",
                  interpretation="Preserve valid entries", counterexample="Shorter flow drops values",
                  old_contract=old_hash, new_contract=new_hash, changes=["recovery rubric"])
        new_evaluation = {"cases": ["invalid-field"], "repetitions": 1,
                          "required_gates": ["submit"], "candidate_only_gates": ["preserves"],
                          "metric": "recovery", "direction": "higher", "min_gain": 1,
                          "noise_floor": 0, "deterministic": True}
        registry = {"check": {"argv": [sys.executable, str(revised_grader)], "cwd": "."}}
        calibration = self._calibration(revised_grader, registry)
        self.call("revise", feedback="F1", contract_file=str(revised_contract),
                  evaluator_file=str(revised_grader),
                  registry=registry,
                  evaluation=new_evaluation,
                  calibration=calibration)
        self.call("run", side="baseline", rep=0, run_key="new-a")
        self.call("run", side="candidate", arm="fix", rep=0, run_key="new-b")
        new = self.call("compare", arm="fix", baseline=["new-a"], candidate=["new-b"], decision="new")
        self.assertEqual(new["decision"], "eligible")
        with sqlite3.connect(self.root / "ledger.sqlite3") as db:
            config_path = db.execute("SELECT path FROM controller_config WHERE id=1").fetchone()[0]
        case_path = Path(json.loads((self.root / config_path).read_text())["case_files"]["invalid-field"]["path"])
        case_bytes = case_path.read_bytes()
        case_path.unlink()
        capture = self.call("regrade-capture", capture="feedback-matrix", old_decision="old", new_decision="new")
        self.assertEqual(capture["result"]["decision"], "complete")
        self.assertEqual(capture["result"]["old"]["decision"], "reject")
        self.assertEqual(capture["result"]["new"]["decision"], "eligible")
        matrix = json.loads(Path(capture["matrix"]).read_text())
        self.assertNotEqual(matrix["old_candidate"][0]["artifacts"], matrix["new_candidate"][0]["artifacts"])
        self.assertEqual(matrix["old_candidate"][0]["submission_artifacts"], matrix["new_candidate"][0]["submission_artifacts"])
        submission_path = self.root / matrix["old_candidate"][0]["submission_artifacts"][0]["path"]
        with tarfile.open(submission_path) as archive:
            self.assertEqual(archive.extractfile("product.txt").read(), b"preserves fields")
        self.assertEqual(self.call("regrade", **matrix)["decision"], "complete")
        original_archive = submission_path.read_bytes()
        submission_path.write_bytes(b"tampered")
        self.assertEqual(self.call("regrade", **matrix)["decision"], "inconclusive")
        submission_path.write_bytes(original_archive)
        case_path.write_bytes(case_bytes)
        self.assertEqual(self.call("status")["ledger"]["settled_trials"], 6)
        self.assertEqual(self.call("promote", arm="fix", decision="new")["commit"],
                         self.call("status")["integration"])

    def test_second_round_uses_current_champion_and_budget(self):
        self.grader.write_text(
            "import json\nfrom pathlib import Path\n"
            "value = int(Path('product.txt').read_text())\n"
            "print(json.dumps({'gates': {'submit': True}, "
            "'metrics': {'recovery': value}, 'work_count': 1}))\n")
        (self.source / "product.txt").write_text("0")
        self.git("add", "product.txt")
        self.git("-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                 "commit", "-qm", "numeric")
        self.base = self.git("rev-parse", "HEAD")
        self.call("init", source=str(self.source), experiment="rounds", base=self.base,
                  paths=["product.txt"], target="check",
                  registry={"check": {"argv": [sys.executable, str(self.grader)], "cwd": "."}},
                  contract_file=str(self.contract), evaluator_file=str(self.grader),
                  evaluation={"case": "one", "repetitions": 1, "required_gates": ["submit"],
                              "metric": "recovery", "direction": "higher", "min_gain": 1,
                              "noise_floor": 0, "deterministic": True}, max_trials=4, max_tokens=0)
        champion = self.base
        for i in (1, 2):
            arm = self.call("allocate", arm=f"round{i}")
            self.assertEqual(arm["identity"]["commit"], champion)
            (Path(arm["worktree"]) / "product.txt").write_text(str(i))
            candidate = self.call("freeze", arm=f"round{i}", message=f"Round {i}", writers_stopped=True)
            self.call("run", side="baseline", rep=0, run_key=f"base{i}")
            self.call("run", side="candidate", arm=f"round{i}", rep=0, run_key=f"candidate{i}")
            result = self.call("compare", arm=f"round{i}", baseline=[f"base{i}"],
                               candidate=[f"candidate{i}"], decision=f"decision{i}")
            self.assertEqual(result["decision"], "eligible")
            champion = self.call("promote", arm=f"round{i}", decision=f"decision{i}")["commit"]
            self.assertEqual(champion, candidate["commit"])
        self.assertEqual(self.call("status")["ledger"]["settled_trials"], 4)

    def test_recover_pretransaction_intent_revalidates_and_retries(self):
        self.call("init", source=str(self.source), experiment="recover", base=self.base,
                  paths=["product.txt"], target="check",
                  registry={"check": {"argv": [sys.executable, str(self.grader)], "cwd": "."}},
                  contract_file=str(self.contract), evaluator_file=str(self.grader),
                  evaluation={"case": "one", "repetitions": 1, "required_gates": ["submit"],
                              "metric": "recovery", "direction": "higher", "min_gain": 1,
                              "noise_floor": 0, "deterministic": True}, max_trials=2, max_tokens=0)
        arm = self.call("allocate", arm="fix")
        (Path(arm["worktree"]) / "product.txt").write_text("preserves fields")
        candidate = self.call("freeze", arm="fix", message="fix", writers_stopped=True)
        self.call("run", side="baseline", rep=0, run_key="old")
        self.call("run", side="candidate", arm="fix", rep=0, run_key="new")
        self.call("compare", arm="fix", baseline=["old"], candidate=["new"], decision="choose")
        repo = self.root / "repo.git"
        generation = subprocess.check_output(["git", "--git-dir", str(repo), "rev-parse",
                         "refs/tkstack/generation/recover"], text=True).strip()
        new_generation = subprocess.run(["git", "--git-dir", str(repo), "hash-object", "-w", "--stdin"],
                             input="new generation", text=True, capture_output=True, check=True).stdout.strip()
        intents = self.root / "promotions"
        intents.mkdir()
        intent = {"expected": self.base, "candidate": candidate["commit"],
                  "expected_generation": generation, "new_generation": new_generation,
                  "state": "intent",
                  "decision_sha256": hashlib.sha256((self.root / "decisions/choose.json").read_bytes()).hexdigest(),
                  "config_sha256": hashlib.sha256((self.root / "experiment.json").read_bytes()).hexdigest()}
        payload = json.dumps(intent, sort_keys=True, separators=(",", ":"))
        with sqlite3.connect(self.root / "ledger.sqlite3") as db:
            db.execute("CREATE TABLE controller_promotion_intents "
                       "(decision TEXT PRIMARY KEY, payload TEXT NOT NULL, sha256 TEXT NOT NULL)")
            db.execute("INSERT INTO controller_promotion_intents VALUES (?, ?, ?)",
                       ("choose", payload, hashlib.sha256(payload.encode()).hexdigest()))
        # A crash between the database commit and readable file publication is recoverable.
        self.assertEqual(self.call("recover", decision="choose")["state"], "unresolved")
        self.assertEqual(json.loads((intents / "choose.json").read_text()), intent)
        (intents / "choose.json").write_text(json.dumps({**intent, "candidate": self.base}))
        self.assert_call_fails("recover", decision="choose", retry=True)
        (intents / "choose.json").write_text(json.dumps(intent))
        for key, value in (("expected", candidate["commit"]),
                           ("candidate", self.base),
                           ("expected_generation", new_generation),
                           ("new_generation", generation),
                           ("config_sha256", "0" * 64),
                           ("decision_sha256", "0" * 64)):
            changed = {**intent, key: value}
            tampered = json.dumps(changed, sort_keys=True, separators=(",", ":"))
            with sqlite3.connect(self.root / "ledger.sqlite3") as db:
                db.execute("UPDATE controller_promotion_intents SET payload=?, sha256=? WHERE decision='choose'",
                           (tampered, hashlib.sha256(tampered.encode()).hexdigest()))
            (intents / "choose.json").write_text(json.dumps(changed))
            self.assert_call_fails("recover", decision="choose", retry=True)
            self.assertEqual(self.call("status")["integration"], self.base)
        with sqlite3.connect(self.root / "ledger.sqlite3") as db:
            db.execute("UPDATE controller_promotion_intents SET payload=?, sha256=? WHERE decision='choose'",
                       (payload, hashlib.sha256(payload.encode()).hexdigest()))
        (intents / "choose.json").write_text(json.dumps(intent))
        self.assertEqual(self.call("recover", decision="choose", retry=True)["state"], "completed")
        self.assertEqual(self.call("status")["integration"], candidate["commit"])

    def test_recovery_rejects_intent_not_bound_to_saved_decision(self):
        self.call("init", source=str(self.source), experiment="recover", base=self.base,
                  paths=["product.txt"], target="check",
                  registry={"check": {"argv": [sys.executable, str(self.grader)], "cwd": "."}},
                  contract_file=str(self.contract), evaluator_file=str(self.grader),
                  evaluation={"case": "one", "repetitions": 1, "required_gates": ["submit"],
                              "metric": "recovery", "direction": "higher", "min_gain": 1,
                              "noise_floor": 0, "deterministic": True}, max_trials=2, max_tokens=0)
        arm = self.call("allocate", arm="fix")
        (Path(arm["worktree"]) / "product.txt").write_text("preserves fields")
        good = self.call("freeze", arm="fix", message="fix", writers_stopped=True)
        bad_arm = self.call("allocate", arm="bad")
        (Path(bad_arm["worktree"]) / "product.txt").write_text("loses more fields")
        bad = self.call("freeze", arm="bad", message="bad", writers_stopped=True)
        self.call("run", side="baseline", rep=0, run_key="old")
        self.call("run", side="candidate", arm="fix", rep=0, run_key="new")
        self.call("compare", arm="fix", baseline=["old"], candidate=["new"], decision="choose")
        repo = self.root / "repo.git"
        gen = subprocess.check_output(["git", "--git-dir", str(repo), "rev-parse",
            "refs/tkstack/generation/recover"], text=True).strip()
        new_gen = subprocess.run(["git", "--git-dir", str(repo), "hash-object", "-w", "--stdin"],
            input="next generation", text=True, capture_output=True, check=True).stdout.strip()
        intent = {"expected": self.base, "candidate": bad["commit"], "expected_generation": gen,
                  "new_generation": new_gen, "state": "intent",
                  "decision_sha256": hashlib.sha256((self.root / "decisions/choose.json").read_bytes()).hexdigest(),
                  "config_sha256": hashlib.sha256((self.root / "experiment.json").read_bytes()).hexdigest()}
        payload = json.dumps(intent, sort_keys=True, separators=(",", ":"))
        with sqlite3.connect(self.root / "ledger.sqlite3") as db:
            db.execute("CREATE TABLE controller_promotion_intents "
                       "(decision TEXT PRIMARY KEY, payload TEXT NOT NULL, sha256 TEXT NOT NULL)")
            db.execute("INSERT INTO controller_promotion_intents VALUES (?, ?, ?)",
                       ("choose", payload, hashlib.sha256(payload.encode()).hexdigest()))
        (self.root / "promotions").mkdir()
        (self.root / "promotions/choose.json").write_text(json.dumps(intent))
        self.assert_call_fails("recover", decision="choose", retry=True)
        self.assertEqual(self.call("status")["integration"], self.base)
        self.assertNotEqual(good["commit"], bad["commit"])

    def test_completed_recovery_rejects_changed_decision_and_config(self):
        self.call("init", source=str(self.source), experiment="recover", base=self.base,
                  paths=["product.txt"], target="check",
                  registry={"check": {"argv": [sys.executable, str(self.grader)], "cwd": "."}},
                  contract_file=str(self.contract), evaluator_file=str(self.grader),
                  evaluation={"case": "one", "repetitions": 1, "required_gates": ["submit"],
                              "metric": "recovery", "direction": "higher", "min_gain": 1,
                              "noise_floor": 0, "deterministic": True}, max_trials=2, max_tokens=0)
        arm = self.call("allocate", arm="fix")
        (Path(arm["worktree"]) / "product.txt").write_text("preserves fields")
        self.call("freeze", arm="fix", message="fix", writers_stopped=True)
        self.call("run", side="baseline", rep=0, run_key="old")
        self.call("run", side="candidate", arm="fix", rep=0, run_key="new")
        self.call("compare", arm="fix", baseline=["old"], candidate=["new"], decision="choose")
        self.call("promote", arm="fix", decision="choose")
        (self.root / "promotions/choose.completed.json").unlink()
        decision = self.root / "decisions/choose.json"
        original = decision.read_text()
        content = json.loads(original)
        content["arm"] = "other"
        decision.write_text(json.dumps(content))
        self.assert_call_fails("recover", decision="choose")
        decision.write_text(original)
        with sqlite3.connect(self.root / "ledger.sqlite3") as db:
            old = db.execute("SELECT digest, path FROM controller_config WHERE id=1").fetchone()
            configuration = json.loads((self.root / old[1]).read_text())
            configuration["max_proposals"] = configuration.get("max_proposals", 5) + 1
            revised = self.root / "changed-config.json"
            revised.write_text(json.dumps(configuration))
            revised_digest = hashlib.sha256(revised.read_bytes()).hexdigest()
            db.execute("UPDATE controller_config SET digest=?, path=? WHERE id=1",
                       (revised_digest, revised.name))
        self.assert_call_fails("recover", decision="choose")
        with sqlite3.connect(self.root / "ledger.sqlite3") as db:
            db.execute("UPDATE controller_config SET digest=?, path=? WHERE id=1", old)
        self.contract.write_text("altered contract")
        self.assert_call_fails("recover", decision="choose")

    def test_multiple_cases_reach_the_registered_evaluator(self):
        self.grader.write_text(
            "import json, sys\nfrom pathlib import Path\n"
            "good = Path('product.txt').read_text() == 'preserves fields'\n"
            "print(json.dumps({'gates': {'submit': True}, 'metrics': "
            "{'recovery': (3 if good else 1) + (1 if sys.argv[1] == 'second' else 0)}, "
            "'work_count': 1}))\n")
        self.call("init", source=str(self.source), experiment="cases", base=self.base,
                  paths=["product.txt"], target="check",
                  registry={"check": {"argv": [sys.executable, str(self.grader), "{{case}}"], "cwd": "."}},
                  contract_file=str(self.contract), evaluator_file=str(self.grader),
                  evaluation={"cases": ["first", "second"], "repetitions": 1,
                              "required_gates": ["submit"], "metric": "recovery",
                              "direction": "higher", "min_gain": 1, "noise_floor": 0,
                              "deterministic": True}, max_trials=4, max_tokens=0)
        arm = self.call("allocate", arm="fix")
        (Path(arm["worktree"]) / "product.txt").write_text("preserves fields")
        self.call("freeze", arm="fix", message="fix", writers_stopped=True)
        for case in ("first", "second"):
            self.call("run", side="baseline", case=case, rep=0, run_key="old-" + case)
            self.call("run", side="candidate", arm="fix", case=case, rep=0, run_key="new-" + case)
        result = self.call("compare", arm="fix", baseline=["old-first", "old-second"],
                           candidate=["new-first", "new-second"], decision="choice")
        self.assertEqual(result["decision"], "eligible")
        self.assertEqual(result["target"]["independent_cases"], 2)

    def test_modified_receipt_cannot_inflate_result(self):
        self.call("init", source=str(self.source), experiment="receipts", base=self.base,
                  paths=["product.txt"], target="check",
                  registry={"check": {"argv": [sys.executable, str(self.grader)], "cwd": "."}},
                  contract_file=str(self.contract), evaluator_file=str(self.grader),
                  evaluation={"case": "one", "repetitions": 1, "required_gates": ["submit"],
                              "metric": "recovery", "direction": "higher", "min_gain": 1,
                              "noise_floor": 0, "deterministic": True}, max_trials=2, max_tokens=0)
        arm = self.call("allocate", arm="fix")
        (Path(arm["worktree"]) / "product.txt").write_text("preserves fields")
        self.call("freeze", arm="fix", message="fix", writers_stopped=True)
        self.call("run", side="baseline", rep=0, run_key="old")
        self.call("run", side="candidate", arm="fix", rep=0, run_key="new")
        receipt = self.root / "runs" / "new.json"
        record = json.loads(receipt.read_text())
        record["result"]["stdout"] = '{"gates":{"submit":true},"metrics":{"recovery":100},"work_count":1}'
        artifact = self.root / "evidence" / "new.json"
        artifact.write_text(record["result"]["stdout"])
        record["artifact_sha256"] = hashlib.sha256(artifact.read_bytes()).hexdigest()
        receipt.write_text(json.dumps(record))
        request = self.directory / "bad-receipt.json"
        request.write_text(json.dumps({"action":"compare", "root":str(self.root), "arm":"fix",
                                       "baseline":["old"], "candidate":["new"], "decision":"bad"}))
        result = subprocess.run([sys.executable, str(SCRIPT), "--request", str(request)],
                                text=True, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("settled ledger", result.stderr)

    def test_manual_commit_outside_scope_cannot_be_trialed(self):
        self.call("init", source=str(self.source), experiment="scope", base=self.base,
                  paths=["product.txt"], target="check",
                  registry={"check": {"argv": [sys.executable, str(self.grader)], "cwd": "."}},
                  contract_file=str(self.contract), evaluator_file=str(self.grader),
                  evaluation={"case": "one", "repetitions": 1, "required_gates": ["submit"],
                              "metric": "recovery", "direction": "higher", "min_gain": 1,
                              "noise_floor": 0, "deterministic": True}, max_trials=2, max_tokens=0)
        arm = self.call("allocate", arm="fix")
        worktree = Path(arm["worktree"])
        (worktree / "product.txt").write_text("preserves fields")
        (worktree / "OUTSIDE.txt").write_text("unauthorized")
        subprocess.run(["git", "-C", str(worktree), "add", "."], check=True)
        subprocess.run(["git", "-C", str(worktree), "-c", "user.name=T",
                        "-c", "user.email=t@example.invalid", "commit", "-qm", "outside"], check=True)
        request = self.directory / "scope.json"
        request.write_text(json.dumps({"action":"run", "root":str(self.root), "side":"candidate",
                                       "arm":"fix", "rep":0, "run_key":"bad"}))
        result = subprocess.run([sys.executable, str(SCRIPT), "--request", str(request)],
                                text=True, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("scoped freeze", result.stderr)
        self.assertEqual(self.call("status")["ledger"]["reserved_trials"], 0)

    def test_declared_evaluator_dependency_drift_stops_execution(self):
        dependency = self.directory / "fixture.txt"
        dependency.write_text("original")
        self.call("init", source=str(self.source), experiment="dependency", base=self.base,
                  paths=["product.txt"], target="check",
                  registry={"check": {"argv": [sys.executable, str(self.grader)], "cwd": "."}},
                  contract_file=str(self.contract), evaluator_file=str(self.grader),
                  evaluator_dependencies=[str(dependency)],
                  evaluation={"case": "one", "repetitions": 1, "required_gates": ["submit"],
                              "metric": "recovery", "direction": "higher", "min_gain": 1,
                              "noise_floor": 0, "deterministic": True}, max_trials=2, max_tokens=0)
        dependency.write_text("changed")
        request = self.directory / "dependency.json"
        request.write_text(json.dumps({"action":"run", "root":str(self.root), "side":"baseline",
                                       "rep":0, "run_key":"bad"}))
        result = subprocess.run([sys.executable, str(SCRIPT), "--request", str(request)],
                                text=True, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("dependency changed", result.stderr)
        self.assertEqual(self.call("status")["ledger"]["reserved_trials"], 0)

    def test_completed_receipt_can_recover_interrupted_settlement(self):
        self.call("init", source=str(self.source), experiment="run-recovery", base=self.base,
                  paths=["product.txt"], target="check",
                  registry={"check": {"argv": [sys.executable, str(self.grader)], "cwd": "."}},
                  contract_file=str(self.contract), evaluator_file=str(self.grader),
                  evaluation={"case": "one", "repetitions": 1, "required_gates": ["submit"],
                              "metric": "recovery", "direction": "higher", "min_gain": 1,
                              "noise_floor": 0, "deterministic": True}, max_trials=2, max_tokens=0)
        self.call("run", side="baseline", rep=0, run_key="old")
        # Model the durable receipt having landed just before the settlement transaction.
        with sqlite3.connect(self.root / "ledger.sqlite3") as db:
            db.execute("DELETE FROM events WHERE experiment=? AND run_key=? AND operation='settle'",
                       ("run-recovery", "old"))
            db.execute("UPDATE runs SET status='dispatched', actual_tokens=NULL "
                       "WHERE experiment=? AND run_key=?", ("run-recovery", "old"))
        recovered = self.call("recover-run", run_key="old")
        self.assertEqual(recovered["status"], "settled")
        self.assertEqual(self.call("status")["ledger"]["settled_trials"], 1)

    def test_tampered_frozen_configuration_is_rejected(self):
        self.call("init", source=str(self.source), experiment="config", base=self.base,
                  paths=["product.txt"], target="check",
                  registry={"check": {"argv": [sys.executable, str(self.grader)], "cwd": "."}},
                  contract_file=str(self.contract), evaluator_file=str(self.grader),
                  evaluation={"case": "one", "repetitions": 1, "required_gates": ["submit"],
                              "metric": "recovery", "direction": "higher", "min_gain": 5,
                              "noise_floor": 0, "deterministic": True}, max_trials=2, max_tokens=0)
        path = self.root / "experiment.json"
        config = json.loads(path.read_text())
        config["evaluation"]["min_gain"] = 1
        path.write_text(json.dumps(config))
        request = self.directory / "tamper.json"
        request.write_text(json.dumps({"action": "status", "root": str(self.root)}))
        result = subprocess.run([sys.executable, str(SCRIPT), "--request", str(request)],
                                text=True, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("configuration changed", result.stderr)

    def test_compiled_skill_exposes_real_experiment_command(self):
        request = self.directory / "public.json"
        prepared = self._prepare("init", {
            "source": str(self.source),
            "experiment": "public", "base": self.base, "paths": ["product.txt"],
            "target": "check", "registry": {
                "check": {"argv": [sys.executable, str(self.grader)], "cwd": "."}},
            "contract_file": str(self.contract), "evaluator_file": str(self.grader),
            "evaluation": {"case": "one", "repetitions": 1, "required_gates": ["submit"],
                           "metric": "recovery", "direction": "higher", "min_gain": 1,
                           "noise_floor": 0, "deterministic": True},
            "max_trials": 2, "max_tokens": 0})
        request.write_text(json.dumps({"action": "init", "root": str(self.root), **prepared}))
        result = subprocess.run([
            sys.executable, str(ROOT / "skills/learn/skills/skillify/scripts/skillify.py"),
            "invoke", str(ROOT / "skills/hill-climb"), "--",
            "native", "experiment", "--request", str(request)],
            text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.root / "experiment.json").is_file())

    def test_evaluator_drift_stops_execution(self):
        self.call("init", source=str(self.source), experiment="drift", base=self.base,
                  paths=["product.txt"], target="check",
                  registry={"check": {"argv": [sys.executable, str(self.grader)], "cwd": "."}},
                  contract_file=str(self.contract), evaluator_file=str(self.grader),
                  evaluation={"case": "one", "repetitions": 1, "required_gates": ["submit"],
                              "metric": "recovery", "direction": "higher", "min_gain": 1,
                              "noise_floor": 0, "deterministic": True}, max_trials=2, max_tokens=0)
        self.grader.write_text("print('changed')")
        request = self.directory / "bad.json"
        request.write_text(json.dumps({"action":"run", "root":str(self.root), "side":"baseline",
                                       "rep":0, "run_key":"attempt"}))
        result = subprocess.run([sys.executable, str(SCRIPT), "--request", str(request)],
                                text=True, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("changed", result.stderr)
        self.assertEqual(self.call("status")["ledger"]["reserved_trials"], 0)


if __name__ == "__main__":
    unittest.main()

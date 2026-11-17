"""Adversarial contracts for evaluator provenance and held-out fixtures."""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/hill-climb/scripts"))
SPEC = importlib.util.spec_from_file_location("experiment_integrity", ROOT / "skills/hill-climb/scripts/experiment.py")
experiment = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(experiment)


class IntegrityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.grader = self.root / "grader.py"
        self.grader.write_text("raise RuntimeError('actual grader')\n")

    def test_evaluator_cannot_be_an_unused_argument(self):
        bad = {"check": {"argv": [sys.executable, "-c", "print(1)", str(self.grader)], "cwd": "."}}
        with self.assertRaisesRegex(ValueError, "evaluator"):
            experiment.validate_target(bad, "check", str(self.grader), sys.executable)
        good = {"check": {"argv": [sys.executable, str(self.grader)], "cwd": "."}}
        _, executable = experiment.validate_target(good, "check", str(self.grader), sys.executable)
        self.assertEqual(executable["sha256"], experiment.digest(executable["path"]))

    def test_alias_cases_cannot_share_frozen_input(self):
        case = self.root / "case"
        case.write_text("same case")
        with self.assertRaisesRegex(ValueError, "same input"):
            experiment.freeze_cases({"selection": str(case), "holdout": str(case)},
                                    ["selection"], ["holdout"])

    def test_reserved_evaluation_fields_rejected(self):
        evaluation = {"cases": ["good", "bad"], "assignments": [{"case": "good", "rep": 0}]}
        with self.assertRaisesRegex(ValueError, "reserved"):
            experiment.check_evaluation_fields(evaluation)

    def test_qualify_calibration_requires_run_backed_evidence(self):
        with self.assertRaisesRegex(ValueError, "run"):
            experiment.calibration_from_runs(self.root, "e", [{"id": "good", "expected": True, "observed": True},
                                                              {"id": "bad", "expected": False, "observed": False}],
                                             "a" * 64, "b" * 64)


class ProductionProtocolTests(unittest.TestCase):
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
        self.grader = self.dir / "grader.py"
        self.grader.write_text(
            "import sys,json,hashlib\nfrom pathlib import Path\n"
            "good=Path('product').read_text() == 'good'\n"
            "case_hash=hashlib.sha256(Path(sys.argv[2]).read_bytes()).hexdigest()\n"
            "print(json.dumps({'case_sha256':case_hash,'gates':{'submit':True,'preserves':good},"
            "'metrics':{'quality':3 if good else 1},'work_count':1}))\n")
        self.sel = self.dir / "sel"
        self.sel.write_text("selection input")
        self.hold = self.dir / "hold"
        self.hold.write_text("heldout input")
        self.root = self.dir / "run"
        self.registry = {"check": {"argv": [sys.executable, str(self.grader), "{{case}}", "{{case_file}}"], "cwd": "."}}

    def git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.repo), *args], text=True).strip()

    def call(self, action, **kwargs):
        return experiment.execute({"action": action, "root": str(self.root), **kwargs})

    def init(self, **overrides):
        request = dict(source=str(self.repo), experiment="e", base=self.base, paths=["product"], target="check",
            registry=self.registry, trusted_interpreter=sys.executable,
            contract_file=str(self.contract), evaluator_file=str(self.grader),
            case_files={"sel": str(self.sel), "hold": str(self.hold)},
            evaluation={"cases": ["sel"], "repetitions": 1, "required_gates": ["submit"],
                        "candidate_only_gates": ["preserves"], "metric": "quality", "direction": "higher",
                        "min_gain": 1, "noise_floor": 0, "deterministic": True},
            confirmation={"cases": ["hold"], "repetitions": 1}, max_trials=12, max_tokens=0)
        request.update(overrides)
        return self.call("init", **request)

    def freeze(self):
        arm = self.call("allocate", arm="fix")
        (Path(arm["worktree"]) / "product").write_text("good")
        return self.call("freeze", arm="fix", message="fix", writers_stopped=True)

    def test_real_verifier_attests_bound_cases_and_confirms(self):
        self.init()
        chosen = self.freeze()
        self.call("run", side="baseline", rep=0, run_key="old")
        self.call("run", side="candidate", arm="fix", rep=0, run_key="new")
        result = self.call("compare", arm="fix", baseline=["old"], candidate=["new"], decision="pick")
        self.assertEqual(result["decision"], "eligible")
        self.call("select", decision="pick")
        self.call("run", side="baseline", split="confirmation", rep=0, run_key="h-old")
        self.call("run", side="candidate", arm="fix", split="confirmation", rep=0, run_key="h-new")
        self.assertEqual(self.call("confirm", baseline=["h-old"], candidate=["h-new"])["decision"], "eligible")
        self.assertEqual(self.call("promote", arm="fix", decision="pick")["commit"], chosen["commit"])

    def test_modified_case_input_stops_trial(self):
        self.init()
        self.sel.write_text("changed")
        with self.assertRaisesRegex(ValueError, "case input changed"):
            self.call("run", side="baseline", rep=0, run_key="old")

    def test_expired_or_rewound_clock_rejects_before_reserving(self):
        with patch.object(experiment.time, "time", return_value=1000.0):
            self.init(max_elapsed_seconds=2)
        with patch.object(experiment.time, "time", return_value=1001.0):
            self.assertEqual(experiment.remaining_time(self.root, experiment.config_for(self.root)), 1.0)
        with patch.object(experiment.time, "time", return_value=999.0):
            with self.assertRaisesRegex(ValueError, "backwards"):
                self.call("run", side="baseline", rep=0, run_key="old")
        with patch.object(experiment.time, "time", return_value=1003.0):
            with self.assertRaisesRegex(ValueError, "deadline"):
                self.call("run", side="baseline", rep=0, run_key="old")
        self.assertEqual(self.call("status")["ledger"]["settled_trials"], 0)

    def test_calibration_deadline_rejects_before_reserving(self):
        with patch.object(experiment.time, "time", return_value=1000.0):
            self.init(max_elapsed_seconds=1)
        with patch.object(experiment.time, "time", return_value=1002.0):
            with self.assertRaisesRegex(ValueError, "deadline"):
                self.call("calibration-run", run_key="late", commit=self.base, case="sel", case_file=str(self.sel),
                          evaluator_file=str(self.grader), registry=self.registry, trusted_interpreter=sys.executable)
        self.assertEqual(self.call("status")["ledger"]["settled_trials"], 0)

    def test_unattested_verifier_output_is_inconclusive(self):
        self.grader.write_text("import json\nprint(json.dumps({'gates':{'submit':True,'preserves':True},'metrics':{'quality':3},'work_count':1}))\n")
        self.init()
        self.freeze()
        self.call("run", side="baseline", rep=0, run_key="old")
        self.call("run", side="candidate", arm="fix", rep=0, run_key="new")
        result = self.call("compare", arm="fix", baseline=["old"], candidate=["new"], decision="pick")
        self.assertEqual(result["decision"], "inconclusive")

    def test_init_rejects_spoofed_evaluator_and_assignment_override(self):
        registry = {"check": {"argv": [sys.executable, "-c", "print(1)", str(self.grader), "{{case_file}}"], "cwd": "."}}
        with self.assertRaisesRegex(ValueError, "evaluator"):
            self.init(registry=registry)
        evaluation = {"cases": ["sel"], "repetitions": 1, "assignments": [{"case": "sel", "rep": 0}],
                      "required_gates": ["submit"], "metric": "quality", "direction": "higher",
                      "min_gain": 1, "noise_floor": 0, "deterministic": True}
        with self.assertRaisesRegex(ValueError, "reserved"):
            self.init(evaluation=evaluation)

    def test_calibration_requires_executed_labeled_reference_runs(self):
        self.init()
        good = self.freeze()
        old = experiment.digest(self.contract)
        self.call("feedback", id="F1", observation="improve verifier", interpretation="calibrate",
                  counterexample="always passes", old_contract=old, new_contract=old, changes=["verifier"])
        for key, commit in (("known-bad", self.base), ("known-good", good["commit"])):
            self.call("calibration-run", run_key=key, commit=commit, case="sel", case_file=str(self.sel),
                      evaluator_file=str(self.grader), registry=self.registry, trusted_interpreter=sys.executable)
        labels = [{"id": "good", "run_key": "known-good", "gate": "preserves", "expected": True},
                  {"id": "bad", "run_key": "known-bad", "gate": "preserves", "expected": False}]
        labels[0]["metrics"], labels[1]["metrics"] = {"quality": 3}, {"quality": 1}
        revised = self.dir / "contract2"
        revised.write_text("new contract")
        new = experiment.digest(revised)
        self.call("feedback", id="F2", observation="improve contract", interpretation="calibrate",
                  counterexample="always passes", old_contract=old, new_contract=new, changes=["contract"])
        self.call("revise", feedback="F2", contract_file=str(revised), evaluator_file=str(self.grader),
                  registry=self.registry, trusted_interpreter=sys.executable, calibration=labels)
        self.assertEqual(self.call("status")["ledger"]["settled_trials"], 2)

    def test_calibration_cannot_consume_a_holdout_under_an_alias(self):
        self.init()
        with self.assertRaisesRegex(ValueError, "confirmation input"):
            self.call("calibration-run", run_key="leak", commit=self.base, case="alias", case_file=str(self.hold),
                      evaluator_file=str(self.grader), registry=self.registry, trusted_interpreter=sys.executable)

    def test_calibration_detects_always_pass_and_wrong_evaluator(self):
        self.init()
        good = self.freeze()
        twin = subprocess.check_output(["git", "--git-dir", str(self.root / "repo.git"), "-c", "user.name=T",
                "-c", "user.email=t@e", "commit-tree", good["tree"], "-p", good["commit"]], input="x", text=True).strip()
        for key, commit in (("bad-run", self.base), ("good-run", good["commit"]), ("twin", twin)):
            self.call("calibration-run", run_key=key, commit=commit, case="sel", case_file=str(self.sel),
                      evaluator_file=str(self.grader), registry=self.registry, trusted_interpreter=sys.executable)
        wrong = [{"id": "good", "run_key": "good-run", "gate": "submit", "expected": True},
                 {"id": "bad", "run_key": "bad-run", "gate": "submit", "expected": False}]
        command = experiment.target_digest(*experiment.validate_target(self.registry, "check", str(self.grader), sys.executable))
        evidence = experiment.calibration_from_runs(self.root, "e", wrong, experiment.digest(self.grader), command)
        self.assertFalse(evidence["gate_qualified"])
        labels = [wrong[0], dict(wrong[1], run_key="twin")]
        with self.assertRaisesRegex(ValueError, "distinct"):
            experiment.calibration_from_runs(self.root, "e", labels, experiment.digest(self.grader), command)
        with self.assertRaisesRegex(ValueError, "different evaluator"):
            experiment.calibration_from_runs(self.root, "e", wrong, "f" * 64, command)

    def test_changed_evaluator_requires_score_anchors_from_settled_runs(self):
        evaluation = {"cases": ["sel"], "repetitions": 1, "required_gates": ["submit"],
                      "candidate_only_gates": ["preserves"], "metric": "quality", "direction": "higher",
                      "min_gain": 1, "noise_floor": 0, "deterministic": True,
                      "guardrails": [{"metric": "retained", "direction": "higher", "tolerance": 0}],
                      "required_qualitative": ["clarity"]}
        self.init(evaluation=evaluation)
        good = self.freeze()
        current = experiment.digest(self.contract)
        self.call("feedback", id="quality", observation="reversed quality",
                  interpretation="calibrate scores", counterexample="good scores lower",
                  old_contract=current, new_contract=current, changes=["evaluator"])

        def labels_for(verifier, prefix):
            registry = {"check": {"argv": [sys.executable, str(verifier), "{{case}}", "{{case_file}}"], "cwd": "."}}
            for suffix, commit in (("bad", self.base), ("good", good["commit"])):
                self.call("calibration-run", run_key=f"{prefix}-{suffix}", commit=commit, case="sel",
                          case_file=str(self.sel), evaluator_file=str(verifier), registry=registry,
                          trusted_interpreter=sys.executable)
            labels = [{"id": suffix, "run_key": f"{prefix}-{suffix}", "gate": "preserves",
                       "expected": suffix == "good"} for suffix in ("bad", "good")]
            return registry, labels

        correct = self.grader.read_text().replace("'quality':3 if good else 1", "'quality':3 if good else 1,"
                    "'retained':10 if good else 9").replace("'work_count':1", "'qualitative':{'clarity':"
                    "{'rating':3 if good else 1,'rationale':'explanation','evidence':['self']}},'work_count':1")
        biased = self.dir / "biased.py"
        biased.write_text(correct.replace("3 if good else 1", "1 if good else 3", 1))
        registry, labels = labels_for(biased, "biased")
        args = dict(feedback="quality", contract_file=str(self.contract), evaluator_file=str(biased),
                    registry=registry, trusted_interpreter=sys.executable)
        with self.assertRaisesRegex(ValueError, "metric"):
            self.call("revise", **args, calibration=labels)
        labels[0]["metrics"], labels[1]["metrics"] = {"quality": 1, "retained": 9}, {"quality": 3, "retained": 10}
        with self.assertRaisesRegex(ValueError, "metric"):
            self.call("revise", **args, calibration=labels)
        self.assertEqual(experiment.config_for(self.root)["evaluator"]["sha256"], experiment.digest(self.grader))

        rubric = self.dir / "rubric.py"
        rubric.write_text(correct.replace("'rating':3 if good else 1", "'rating':1 if good else 3"))
        registry, labels = labels_for(rubric, "rubric")
        args.update(evaluator_file=str(rubric), registry=registry)
        labels[0]["metrics"], labels[1]["metrics"] = {"quality": 1}, {"quality": 3}
        with self.assertRaisesRegex(ValueError, "metric"):
            self.call("revise", **args, calibration=labels)
        labels[0]["metrics"]["retained"], labels[1]["metrics"]["retained"] = 9, 10
        with self.assertRaisesRegex(ValueError, "qualitative"):
            self.call("revise", **args, calibration=labels)
        labels[0]["qualitative"], labels[1]["qualitative"] = {"clarity": 1}, {"clarity": 3}
        with self.assertRaisesRegex(ValueError, "qualitative"):
            self.call("revise", **args, calibration=labels)

        corrected = self.dir / "corrected.py"
        corrected.write_text(correct)
        registry, labels = labels_for(corrected, "corrected")
        labels[0]["metrics"], labels[1]["metrics"] = {"quality": 1, "retained": 9}, {"quality": 3, "retained": 10}
        labels[0]["qualitative"], labels[1]["qualitative"] = {"clarity": 1}, {"clarity": 3}
        args.update(evaluator_file=str(corrected), registry=registry)
        revised = self.call("revise", **args, calibration=labels)
        self.assertEqual(revised["calibration"]["scope"], {"kind": "gate", "name": "preserves"})
        self.assertTrue(revised["calibration"]["qualitative"]["clarity"]["qualified"])


    def test_same_case_and_repetition_cannot_be_cherry_picked(self):
        self.init()
        self.freeze()
        self.call("run", side="baseline", rep=0, run_key="one")
        with self.assertRaisesRegex(ValueError, "selection assignment"):
            self.call("run", side="baseline", rep=0, run_key="two")
        self.assertEqual(self.call("status")["ledger"]["settled_trials"], 1)

    def test_identical_trees_on_different_branches_share_measurement(self):
        self.init()
        first = self.freeze()
        other = self.call("allocate", arm="other")
        (Path(other["worktree"]) / "product").write_text("good")
        second = self.call("freeze", arm="other", message="different commit", writers_stopped=True)
        self.assertNotEqual(first["commit"], second["commit"])
        self.assertEqual(first["tree"], second["tree"])
        self.call("run", side="baseline", rep=0, run_key="old")
        self.call("run", side="candidate", arm="fix", rep=0, run_key="new")
        with self.assertRaisesRegex(ValueError, "selection assignment"):
            self.call("run", side="candidate", arm="other", rep=0, run_key="repeat")
        result = self.call("compare", arm="other", baseline=["old"], candidate=["new"], decision="reuse")
        self.assertEqual(result["decision"], "eligible")

    def test_identical_baseline_cannot_be_claimed_as_improvement(self):
        self.init()
        self.call("allocate", arm="same")
        self.call("freeze", arm="same", message="no change", writers_stopped=True)
        with self.assertRaisesRegex(ValueError, "identical to baseline"):
            self.call("compare", arm="same", baseline=[], candidate=[], decision="no")


if __name__ == "__main__":
    unittest.main()

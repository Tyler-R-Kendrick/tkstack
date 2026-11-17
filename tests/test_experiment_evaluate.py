"""Contracts for deterministic, attributable experiment evaluation."""

import copy
import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parent.parent
PATH = ROOT / "skills/hill-climb/scripts/experiment_evaluate.py"
SPEC = importlib.util.spec_from_file_location("experiment_evaluate", PATH)
evaluation = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(evaluation)


class EvaluationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for name, value in (("base.txt", "lost fields"), ("fixed.txt", "values retained")):
            (self.root / name).write_text(value)
        self.spec = {
            "version": 1, "contract": "a" * 64, "evaluator": "b" * 64,
            "baseline": {"commit": "1" * 40, "tree": "2" * 40},
            "candidate": {"commit": "3" * 40, "tree": "4" * 40},
            "assignments": [{"case": "invalid-last-field", "rep": 0}],
            "required_gates": ["valid-submit"], "metric": "recovery",
            "direction": "higher", "min_gain": 1, "noise_floor": 0,
            "deterministic": True, "required_qualitative": ["recovery"],
        }
        self.baseline = [self.row("baseline", "base.txt", 1)]
        self.candidate = [self.row("candidate", "fixed.txt", 3)]

    def row(self, which, name, score):
        return {
            **self.spec[which], "contract": self.spec["contract"],
            "evaluator": self.spec["evaluator"], "case": "invalid-last-field", "rep": 0,
            "status": "completed", "gates": {"valid-submit": True},
            "metrics": {"recovery": score}, "work_count": 1,
            "qualitative": {"recovery": {"rating": score, "evidence": [name], "rationale": "Observed interaction"}},
            "artifacts": [{"path": name, "sha256": hashlib.sha256((self.root / name).read_bytes()).hexdigest()}],
        }

    def compare(self):
        return evaluation.compare(self.spec, self.baseline, self.candidate, self.root)

    def test_feedback_and_qualifying_recovery(self):
        change = evaluation.feedback_revision("F-1", "I have to re-enter valid fields.",
            "Correction should preserve valid values.", "A shorter flow that discards input is poor.",
            "a" * 64, "c" * 64, ["recovery-rubric"])
        self.assertEqual(change["observation"], "I have to re-enter valid fields.")
        calibration = [{"id": "good", "expected": True, "observed": True},
                       {"id": "loss", "expected": False, "observed": False},
                       {"id": "shorter-loss", "expected": False, "observed": False}]
        self.assertTrue(evaluation.validate_calibration(calibration)["qualified"])
        self.assertEqual(self.compare()["decision"], "eligible")
        self.assertEqual(self.compare()["target"]["gain"], 2)
        calibration[2]["observed"] = True
        self.assertFalse(evaluation.validate_calibration(calibration)["qualified"])

    def test_candidate_required_failure_rejects(self):
        self.candidate[0]["gates"]["valid-submit"] = False
        self.assertEqual(self.compare()["decision"], "reject")

    def test_new_candidate_gate_can_fail_baseline_but_must_pass_candidate(self):
        self.spec["candidate_only_gates"] = ["preserves-input"]
        self.baseline[0]["gates"]["preserves-input"] = False
        self.candidate[0]["gates"]["preserves-input"] = True
        self.assertEqual(self.compare()["decision"], "eligible")
        self.candidate[0]["gates"]["preserves-input"] = False
        self.assertEqual(self.compare()["decision"], "reject")
        self.candidate[0]["gates"]["preserves-input"] = True
        del self.baseline[0]["gates"]["preserves-input"]
        self.assertEqual(self.compare()["decision"], "inconclusive")

    def test_preservation_gate_still_requires_baseline(self):
        self.baseline[0]["gates"]["valid-submit"] = False
        self.assertEqual(self.compare()["decision"], "inconclusive")

    def test_gate_classes_must_be_disjoint(self):
        self.spec["candidate_only_gates"] = ["valid-submit"]
        with self.assertRaisesRegex(ValueError, "disjoint"):
            self.compare()

    def test_incomplete_unknown_or_wrong_identity_never_eligible(self):
        for mutation in (lambda x: x.clear(),
                         lambda x: x[0].update(status="error"),
                         lambda x: x[0].update(tree="9" * 40),
                         lambda x: x[0].update(contract="9" * 64),
                         lambda x: x[0].update(evaluator="9" * 64),
                         lambda x: x[0]["gates"].update({"valid-submit": None}),
                         lambda x: x[0].update(qualitative={}),
                         lambda x: x[0]["qualitative"]["recovery"].update(rating=None)):
            rows = copy.deepcopy(self.candidate)
            mutation(rows)
            self.assertEqual(evaluation.compare(self.spec, self.baseline, rows, self.root)["decision"], "inconclusive")

    def test_changed_or_missing_evidence_is_inconclusive(self):
        (self.root / "fixed.txt").write_text("changed")
        self.assertEqual(self.compare()["decision"], "inconclusive")

    def test_wrong_assignments_duplicates_and_nonfinite_are_inconclusive(self):
        for rows in ([self.candidate[0], self.candidate[0]],
                     [dict(self.candidate[0], rep=9)],
                     [dict(self.candidate[0], metrics={"recovery": float("nan")})]):
            self.assertEqual(evaluation.compare(self.spec, self.baseline, rows, self.root)["decision"], "inconclusive")

    def test_score_below_meaningful_change_rejects(self):
        self.candidate[0]["metrics"]["recovery"] = 1.5
        self.candidate[0]["qualitative"]["recovery"]["rating"] = 1.5
        self.assertEqual(self.compare()["decision"], "reject")

    def test_different_amount_of_work_is_not_a_valid_comparison(self):
        self.candidate[0]["work_count"] = 2
        self.assertEqual(self.compare()["decision"], "inconclusive")

    def test_guardrail_regression_rejects_quality_gain(self):
        self.spec["guardrails"] = [{"metric": "latency", "direction": "lower", "tolerance": 2}]
        self.baseline[0]["metrics"]["latency"] = 100
        self.candidate[0]["metrics"]["latency"] = 103
        self.assertEqual(self.compare()["decision"], "reject")
        self.candidate[0]["metrics"]["latency"] = 101
        self.assertEqual(self.compare()["decision"], "eligible")

    def test_guardrail_regression_cannot_hide_behind_better_other_case(self):
        self.spec["guardrails"] = [{"metric": "latency", "direction": "lower", "tolerance": 1}]
        self.spec["assignments"].append({"case": "other", "rep": 0})
        for rows in (self.baseline, self.candidate):
            other = copy.deepcopy(rows[0])
            other["case"] = "other"
            rows.append(other)
        self.baseline[0]["metrics"]["latency"] = 100
        self.baseline[1]["metrics"]["latency"] = 100
        self.candidate[0]["metrics"]["latency"] = 102
        self.candidate[1]["metrics"]["latency"] = 98
        result = self.compare()
        self.assertNotEqual(result["decision"], "eligible")
        self.assertIn("invalid-last-field", " ".join(result["reasons"]))

    def test_new_measurement_regrades_same_artifacts_in_four_cells(self):
        new_spec = copy.deepcopy(self.spec)
        new_spec["contract"], new_spec["evaluator"] = "c" * 64, "d" * 64
        new_base, new_fixed = copy.deepcopy(self.baseline), copy.deepcopy(self.candidate)
        for row in new_base + new_fixed:
            row.update(contract=new_spec["contract"], evaluator=new_spec["evaluator"])
        matrix = evaluation.regrade_matrix(self.spec, new_spec, self.baseline, self.candidate,
                                            new_base, new_fixed, self.root)
        self.assertEqual(matrix["decision"], "complete")
        (self.root / "other.txt").write_text("substitution")
        new_fixed[0]["artifacts"] = [{"path": "other.txt", "sha256": hashlib.sha256(b"substitution").hexdigest()}]
        self.assertEqual(evaluation.regrade_matrix(self.spec, new_spec, self.baseline,
            self.candidate, new_base, new_fixed, self.root)["decision"], "inconclusive")


if __name__ == "__main__":
    unittest.main()

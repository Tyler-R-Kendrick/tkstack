"""Synthetic numeric/evidence contracts, not actual optimization benchmarks."""

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location("hill_climb_helper", ROOT / "skills/hill-climb/scripts/hill_climb.py")
hill = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(hill)


class HillClimbTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        frozen = self.root / "runner.py"
        frozen.write_text("# Synthetic frozen-runner receipt.\n")
        trace = self.root / "trace.json"
        trace.write_text('{"fixture": true}')
        self.receipt = {"path": "trace.json", "sha256": hashlib.sha256(trace.read_bytes()).hexdigest()}
        self.plan = {"version": 1, "metric": "latency", "direction": "lower", "min_gain": 2,
            "noise_floor": 1, "noise_evidence": "Synthetic unchanged-baseline test fixture.", "reps": 2,
            "splits": {"train": ["a"], "selection": ["b", "c"], "confirm": ["d", "e"]},
            "frozen_files": [{"path": "runner.py", "sha256": hill.hashed(frozen)}],
            "guardrails": [{"metric": "quality", "direction": "higher", "tolerance": 0}], "model_based": False}
        self.plan_path = self.root / "plan.json"
        self.baseline = self.root / "baseline.jsonl"
        self.candidate = self.root / "candidate.jsonl"
        self.rows = [{"case": case, "rep": rep, "metrics": {"latency": 100, "quality": 1},
            "gate_passed": True, "work_count": 50, "error_count": 0, "evidence": self.receipt}
            for case in ["b", "c", "d", "e"] for rep in range(2)]
        self.changed = copy.deepcopy(self.rows)
        for r in self.changed:
            r["metrics"]["latency"] = 90
        self.save()

    def save(self):
        self.plan_path.write_text(json.dumps(self.plan))
        for path, rows in [(self.baseline, self.rows), (self.candidate, self.changed)]:
            path.write_text("".join(json.dumps(row) + "\n" for row in rows))

    def compare(self, split="selection"):
        return hill.compare(self.plan_path, self.baseline, self.candidate, split)

    def test_paired_gain_and_untouched_claim_boundary(self):
        result = self.compare()
        self.assertEqual(result["decision"], "eligible")
        self.assertEqual(result["target"]["gain"], 10)
        self.assertEqual(result["target"]["independent_cases"], 2)
        self.assertIn("independently checked", self.compare("confirm")["claim"])

    def test_gain_inside_noise_or_at_threshold_is_rejected(self):
        for r in self.changed:
            r["metrics"]["latency"] = 98
        self.save()
        self.assertEqual(self.compare()["decision"], "reject")
        self.changed[0]["metrics"]["latency"] = 60
        self.save()
        self.assertEqual(self.compare()["decision"], "reject")

    def test_quality_regression_gate_and_omitted_work_reject_fast_candidate(self):
        for key, value in [("gate_passed", False), ("work_count", 49), ("error_count", 1)]:
            original = self.changed[0][key]
            self.changed[0][key] = value
            self.save()
            self.assertEqual(self.compare()["decision"], "reject")
            self.changed[0][key] = original
        self.changed[0]["metrics"]["quality"] = 0
        self.save()
        self.assertIn("quality", " ".join(self.compare()["reasons"]))

    def test_changed_frozen_runner_and_trace_fail_closed(self):
        (self.root / "runner.py").write_text("changed grader")
        with self.assertRaisesRegex(ValueError, "Missing or changed evidence"):
            self.compare()
        self.plan["frozen_files"][0]["sha256"] = hill.hashed(self.root / "runner.py")
        self.save()
        (self.root / "trace.json").write_text("changed trace")
        with self.assertRaisesRegex(ValueError, "Missing or changed evidence"):
            self.compare()

    def test_missing_and_duplicate_repetitions_and_split_leakage_are_invalid(self):
        self.changed.pop(0)
        self.save()
        with self.assertRaisesRegex(ValueError, "Incomplete"):
            self.compare()
        self.changed.append(copy.deepcopy(self.changed[0]))
        self.save()
        with self.assertRaisesRegex(ValueError, "duplicate case"):
            self.compare()
        self.plan["splits"]["confirm"] = ["b"]
        self.save()
        with self.assertRaisesRegex(ValueError, "disjoint"):
            self.compare()

    def test_invalid_measurements_and_unmeasurable_margin_are_invalid(self):
        self.changed[0]["metrics"]["latency"] = float("nan")
        self.save()
        with self.assertRaisesRegex(ValueError, "finite numbers"):
            self.compare()
        self.plan["min_gain"] = self.plan["noise_floor"]
        self.save()
        with self.assertRaisesRegex(ValueError, "Actionable gain"):
            self.compare()

    def test_model_receipts_need_real_identity_usage_and_grade(self):
        self.plan["model_based"] = True
        self.save()
        with self.assertRaisesRegex(ValueError, "served model"):
            self.compare()
        for r in self.rows + self.changed:
            r.update(model="fixture-model", usage={"input_tokens": 10, "output_tokens": 5,
                "cache_read_tokens": 0, "cache_write_tokens": 0}, grade={"quality": 1})
        self.save()
        self.assertEqual(self.compare()["decision"], "eligible")


if __name__ == "__main__":
    unittest.main()

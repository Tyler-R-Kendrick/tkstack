"""Registry and report-contract tests; no claim of automated creative judgment."""

import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


unslop = load("unslop_helper", ROOT / "skills/unslop/scripts/unslop.py")
learn = load("shared_learn_helper", ROOT / "skills/learn/scripts/learn.py")


class UnslopTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.store = self.root / ".tkstack/steering"
        self.feedback = {"source": {"conversation": "fixture", "message": "user-one"},
            "user_text": "These badges have no meaning. Remove the decorative badges.",
            "context": "Synthetic feedback fixture for persistence tests.", "kind": "correction",
            "confirmed": True, "patterns": [{"id": "badge-spam", "status": "active"}]}

    def report(self, domains=("code",)):
        snapshot = unslop.catalog(self.store, list(domains))
        artifact = self.root / "artifact.txt"
        artifact.write_text("Synthetic report-contract fixture; not a real UI or model evaluation.")
        methods = {"code": "source", "tests": "source", "writing": "source", "web": "render",
                   "image": "image", "video": "video", "audio": "audio"}
        return {"brief": "Exercise supplied review receipts only.", "domains": list(domains),
            "catalog_sha256": snapshot["sha256"],
            "artifacts": [{"id": "fixture", "path": str(artifact),
                "sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
                "domains": list(domains), "inspections": sorted({methods[d] for d in domains})}],
            "judgments": [{"pattern": p["id"], "status": "clear", "reason": "Synthetic reviewer attestation.",
                "evidence": [{"artifact": "fixture", "location": "fixture", "observation": "Contract fixture, not semantic proof."}]}
                for p in snapshot["patterns"]]}

    def test_seed_examples_have_boundaries_and_user_requested_patterns(self):
        patterns, _ = unslop.state(self.store)
        self.assertEqual(len(patterns), 32)
        for identity in ("decorative-eyebrows", "badge-spam", "narration-comments", "meaningless-tests"):
            self.assertEqual(patterns[identity]["origin"], "user-seeded")
        for p in patterns.values():
            self.assertTrue(p["exception"])
            self.assertNotEqual(p["example"], p["counterexample"])
        self.assertIn("live states", patterns["badge-spam"]["exception"])
        self.assertIn("invariants", patterns["narration-comments"]["fix"])

    def test_shared_learn_dedup_and_recurrence_retain_all_evidence(self):
        first = learn.capture(self.store, {k: self.feedback[k] for k in ("source", "user_text", "context", "kind")})
        self.assertEqual(unslop.record(self.store, self.feedback), first)
        before = (self.store / "events.jsonl").read_bytes()
        self.assertEqual(unslop.record(self.store, self.feedback), first)
        self.assertEqual((self.store / "events.jsonl").read_bytes(), before)
        second = unslop.record(self.store, {**self.feedback, "source": {"conversation": "fixture", "message": "user-two"}})
        patterns, observations = unslop.state(self.store)
        self.assertEqual(set(patterns["badge-spam"]["evidence"]), {first, second})
        self.assertEqual(len(observations), 2)
        self.assertEqual(len(learn.read_state(self.store)["slop_patterns"]), 1)
        learn.render(self.store, learn.read_state(self.store))
        self.assertNotIn(self.feedback["user_text"], (self.store / "rules.md").read_text())

    def test_uncertain_new_rule_is_stored_but_not_graded(self):
        p = copy.deepcopy(unslop.state(self.store)[0]["badge-spam"])
        for field in ("origin", "evidence"):
            p.pop(field)
        p.update(id="possible-pill-pattern", status="candidate")
        unslop.record(self.store, {**self.feedback, "confirmed": False, "patterns": [p]})
        self.assertNotIn(p["id"], {p["id"] for p in unslop.catalog(self.store, ["web"])["patterns"]})
        with self.assertRaisesRegex(ValueError, "candidate amendment"):
            unslop.record(self.store, {**self.feedback, "confirmed": False, "patterns": [{"id": "badge-spam", "status": "candidate"}]})

    def test_invalid_batch_does_not_capture_half_a_correction(self):
        with self.assertRaises(ValueError):
            unslop.record(self.store, {**self.feedback, "patterns": [self.feedback["patterns"][0], {"id": "incomplete"}]})
        self.assertFalse((self.store / "events.jsonl").exists())
        with self.assertRaisesRegex(ValueError, "user identification"):
            unslop.record(self.store, {**self.feedback, "confirmed": False})
        with self.assertRaisesRegex(ValueError, "user provenance"):
            unslop.record(self.store, {**self.feedback, "source": {**self.feedback["source"], "kind": "tool"}})

    def test_scope_is_explicit_and_cannot_silently_expand(self):
        p = copy.deepcopy(unslop.state(self.store)[0]["badge-spam"])
        for field in ("origin", "evidence"):
            p.pop(field)
        p.update(id="project-pills", scope={"kind": "repository", "value": "owner/project"})
        unslop.record(self.store, {**self.feedback, "patterns": [p]})
        self.assertNotIn(p["id"], {p["id"] for p in unslop.catalog(self.store, ["web"])["patterns"]})
        self.assertIn(p["id"], {p["id"] for p in unslop.catalog(self.store, ["web"], "owner/project")["patterns"]})
        with self.assertRaisesRegex(ValueError, "Changing scope"):
            unslop.record(self.store, {**self.feedback, "patterns": [{"id": p["id"], "status": "active", "scope": {"kind": "personal", "value": "*"}}]})

    def test_retirement_and_reactivation_preserve_history(self):
        first = unslop.record(self.store, self.feedback)
        reversal = {**self.feedback, "source": {"conversation": "fixture", "message": "user-reversal"},
                    "id": "badge-spam", "reason": "User changes their prior preference."}
        unslop.retire(self.store, reversal)
        self.assertNotIn("badge-spam", {p["id"] for p in unslop.catalog(self.store, ["web"])["patterns"]})
        self.assertEqual(learn.read_state(self.store)["slop_patterns"]["badge-spam"]["status"], "retired")
        unslop.record(self.store, self.feedback)
        p = unslop.state(self.store)[0]["badge-spam"]
        self.assertEqual(p["status"], "active")
        self.assertIn(first, p["evidence"])
        self.assertEqual(len(p["evidence"]), 2)

    def test_standalone_package_uses_project_store_without_changing_cache(self):
        cached = self.root / "cache/unslop"
        shutil.copytree(ROOT / "skills/unslop", cached, ignore=shutil.ignore_patterns("__pycache__"))
        helper = load("standalone_unslop", cached / "scripts/unslop.py")
        project = self.root / "project"
        project.mkdir()
        before = {p.relative_to(cached): p.read_bytes() for p in cached.rglob("*") if p.is_file()}
        with patch.object(Path, "cwd", return_value=project), patch.object(Path, "home", return_value=self.root / "home"), patch.dict(os.environ, {"TKSTACK_STEERING_DIR": ""}):
            store = helper.default_store()
            self.assertEqual(store, project / ".tkstack/steering")
            self.assertEqual(len(helper.catalog(store, ["web"])["patterns"]) > 0, True)
            self.assertFalse(store.exists())
            helper.record(store, self.feedback)
        after = {p.relative_to(cached): p.read_bytes() for p in cached.rglob("*") if p.is_file()}
        self.assertEqual(before, after)

    def test_grade_requires_coverage_and_actual_visual_inspection_attestation(self):
        report = self.report(("image",))
        self.assertEqual(unslop.grade(self.store, report, self.root)["status"], "pass")
        report["artifacts"][0]["inspections"] = ["source"]
        grade = unslop.grade(self.store, report, self.root)
        self.assertEqual(grade["status"], "incomplete")
        self.assertIsNone(grade["score"])
        report["judgments"].pop()
        self.assertTrue(unslop.grade(self.store, report, self.root)["missing_patterns"])

    def test_report_rejects_changed_artifacts_and_changed_catalog(self):
        report = self.report(("web",))
        unslop.record(self.store, self.feedback)
        with self.assertRaisesRegex(ValueError, "Catalog changed"):
            unslop.grade(self.store, report, self.root)
        report = self.report()
        Path(report["artifacts"][0]["path"]).write_text("changed after review")
        with self.assertRaisesRegex(ValueError, "Artifact missing or changed"):
            unslop.grade(self.store, report, self.root)

    def test_an_inspected_image_does_not_cover_an_uninspected_second_image(self):
        report = self.report(("image",))
        second = copy.deepcopy(report["artifacts"][0])
        second.update(id="second-image", inspections=[])
        report["artifacts"].append(second)
        grade = unslop.grade(self.store, report, self.root)
        self.assertEqual(grade["status"], "incomplete")
        self.assertEqual(grade["uninspected_artifacts"][0]["artifact"], "second-image")

    def test_findings_block_pass_and_floor_is_not_taste_exception(self):
        report = self.report(("writing",))
        row = next(r for r in report["judgments"] if r["pattern"] == "verification-overclaim")
        row.update(status="finding", fix="State only the actual checks run.")
        result = unslop.grade(self.store, report, self.root)
        self.assertEqual(result["status"], "needs-work")
        self.assertIn("verification-overclaim", result["floor_blockers"])
        row["status"] = "exception"
        with self.assertRaisesRegex(ValueError, "cannot be waived"):
            unslop.grade(self.store, report, self.root)

    def test_legitimate_badge_exception_and_duplicate_judgment(self):
        report = self.report(("web",))
        row = next(r for r in report["judgments"] if r["pattern"] == "badge-spam")
        row.update(status="exception", reason="In this supplied fixture, badges represent meaningful independent deployment states.")
        self.assertEqual(unslop.grade(self.store, report, self.root)["status"], "pass")
        report["judgments"].append(copy.deepcopy(row))
        with self.assertRaisesRegex(ValueError, "duplicate review pattern"):
            unslop.grade(self.store, report, self.root)


if __name__ == "__main__":
    unittest.main()

"""Procedural evidence stays separate from authority; Grok discovery is read-only."""

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "skills/learn/scripts/learn.py"
SPEC = importlib.util.spec_from_file_location("grok_learn_helper", SCRIPT)
learn = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(learn)


class GrokLearnTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="tkstack-grok-learn-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.store = self.root / ".tkstack/steering"
        self.grok = self.root / "grok"
        self.experience = {
            "source": {"kind": "tool", "conversation": "test-run", "message": "actual-fixture-output"},
            "target_skill": "learn", "result": "failure",
            "observation": "Synthetic regression fixture: a check found a missing generated reference.",
            "lesson": "Keep package references self-contained and validate copied installations.",
        }

    def test_experience_deduplicates_without_entering_user_evidence_or_active_steering(self):
        identity = learn.capture_experience(self.store, self.experience)
        before = (self.store / "events.jsonl").read_bytes()
        self.assertEqual(learn.capture_experience(self.store, self.experience), identity)
        self.assertEqual((self.store / "events.jsonl").read_bytes(), before)
        state = learn.read_state(self.store)
        self.assertIn(identity, state["experiences"])
        self.assertEqual(state["corrections"], {})
        self.assertEqual(state["rules"], {})
        self.assertNotIn(self.experience["lesson"], (self.store / "rules.md").read_text())
        self.assertIn(self.experience["lesson"], (self.store / "experiences" / (identity + ".md")).read_text())

    def test_task_evidence_cannot_authorize_an_active_reasoning_rule(self):
        identity = learn.capture_experience(self.store, self.experience)
        rule = {"id": "unsupported-authority", "status": "active",
                "scope": {"kind": "personal", "value": "*"}, "evidence": [identity],
                **{field: "synthetic rule field" for field in learn.RULE_FIELDS}}
        with self.assertRaisesRegex(ValueError, "missing user evidence"):
            learn.write_rule(self.store, rule)
        self.assertEqual(learn.read_state(self.store)["rules"], {})

    def test_invalid_experience_does_not_create_a_ledger(self):
        for field, value in [("result", "invented"), ("target_skill", "../elsewhere"), ("lesson", "")]:
            with self.subTest(field=field), self.assertRaises(ValueError):
                learn.capture_experience(self.store, {**self.experience, field: value})
        invalid = copy.deepcopy(self.experience)
        invalid["source"]["kind"] = "user"
        with self.assertRaisesRegex(ValueError, "user corrections use capture"):
            learn.capture_experience(self.store, invalid)
        self.assertFalse((self.store / "events.jsonl").exists())

    def test_experience_views_are_checked_and_rebuilt_by_the_existing_cli(self):
        identity = learn.capture_experience(self.store, self.experience)
        page = self.store / "experiences" / (identity + ".md")
        page.write_text("stale candidate lesson")
        command = [sys.executable, str(SCRIPT), "--store", str(self.store)]
        check = subprocess.run(command + ["check"], capture_output=True, text=True)
        self.assertEqual(check.returncode, 1)
        self.assertIn("stale", check.stderr)
        subprocess.run(command + ["render"], check=True, capture_output=True)
        subprocess.run(command + ["check"], check=True, capture_output=True)
        snapshot = json.loads(subprocess.run(command + ["show", "--json"], check=True,
                                             capture_output=True, text=True).stdout)
        self.assertEqual(snapshot["corrections"], {})
        self.assertIn(identity, snapshot["experiences"])

    def test_locator_reports_managed_bundle_and_user_override_without_exporting_bodies(self):
        cached = self.grok / "bundled/skills/learn/SKILL.md"
        cached.parent.mkdir(parents=True)
        cached.write_text("---\nname: learn\n---\nSynthetic bundled body\n")
        expected = hashlib.sha256(cached.read_bytes()).hexdigest()
        manifest = self.grok / "bundled/manifest.json"
        manifest.write_text(json.dumps({"version": "fixture-v1", "checksums": {"skills/learn/SKILL.md": expected}}))
        override = self.grok / "skills/learn/SKILL.md"
        override.parent.mkdir(parents=True)
        override.write_text("Synthetic user override")
        result = learn.locate_grok_learn(self.grok)
        self.assertEqual(result["bundle_version"], "fixture-v1")
        self.assertEqual([item["scope"] for item in result["found"]], ["bundled", "user-override"])
        self.assertTrue(result["found"][0]["bundle_manifest_match"])
        self.assertIsNone(result["found"][1]["bundle_manifest_match"])
        self.assertNotIn("Synthetic bundled body", json.dumps(result))
        cached.write_text("A local edit")
        self.assertFalse(learn.locate_grok_learn(self.grok)["found"][0]["bundle_manifest_match"])

    def test_missing_cache_lookup_does_not_create_grok_or_steering_directories(self):
        result = subprocess.run([sys.executable, str(SCRIPT), "--store", str(self.store),
                                 "locate-grok", "--grok-home", str(self.grok)],
                                capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(result.stdout)["found"], [])
        self.assertFalse(self.grok.exists())
        self.assertFalse(self.store.exists())

    def test_locator_preserves_malformed_manifest_and_reports_unknown_integrity(self):
        cached = self.grok / "bundled/skills/learn/SKILL.md"
        cached.parent.mkdir(parents=True)
        cached.write_text("Synthetic body")
        manifest = self.grok / "bundled/manifest.json"
        manifest.write_text("{broken")
        result = learn.locate_grok_learn(self.grok)
        self.assertTrue(result["manifest_error"])
        self.assertIsNone(result["found"][0]["bundle_manifest_match"])
        self.assertEqual(manifest.read_text(), "{broken")

    def test_locator_skips_a_skill_link_resolving_outside_the_selected_home(self):
        outside = self.root / "outside.md"
        outside.write_text("Do not export this body")
        cached = self.grok / "bundled/skills/learn/SKILL.md"
        cached.parent.mkdir(parents=True)
        cached.symlink_to(outside)
        result = learn.locate_grok_learn(self.grok)
        self.assertEqual(result["found"], [])
        self.assertEqual(len(result["skipped"]), 1)
        self.assertNotIn("Do not export this body", json.dumps(result))


if __name__ == "__main__":
    unittest.main()

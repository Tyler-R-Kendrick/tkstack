"""The SDLC routing catalog matches the real skill inventory."""

import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location("routing_inventory", ROOT / "src/routing_inventory.py")
routing = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(routing)


class RoutingInventoryTests(unittest.TestCase):
    def test_catalog_matches_installed_skills_and_rendered_guide(self):
        result = routing.check(ROOT)
        self.assertGreater(result["skills"], 200)
        self.assertIn("emil-kowalski", json.loads((ROOT / routing.CATALOG).read_text())["stacks"])
        self.assertIn("ub-mode", json.loads((ROOT / routing.CATALOG).read_text())["stacks"])

    def test_missing_and_stale_entries_fail(self):
        skills = {"present": {"group": "developed"}}
        catalog = {"version": 1, "phases": list(routing.PHASES),
                   "stacks": {"developed": {"title": "Developed", "summary": "Owned skills."}},
                   "skills": {"present": {"phase": "implementation", "strengths": "Owns the change."},
                              "gone": {"phase": "review", "strengths": "Already removed."}}}
        errors = routing.inventory_errors(skills, catalog, {"developed"})
        self.assertTrue(any("gone" in error and "no skill" in error for error in errors))
        catalog["skills"].pop("gone")
        catalog["skills"].pop("present")
        errors = routing.inventory_errors(skills, catalog, {"developed"})
        self.assertTrue(any("present" in error and "without a routing entry" in error for error in errors))

    def test_double_quoted_descriptions_unescape_quotes_and_backslashes(self):
        text = '---\ndescription: "say \\"automate me\\" and \\\\path"\n---\n'
        self.assertEqual(routing.description(text), 'say "automate me" and \\path')
        self.assertNotIn('\\"', routing.discover(ROOT)["automate-me"]["purpose"])

    def test_unlisted_duplicate_declared_name_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "not an allowed duplicate"):
            routing.reject_unlisted_duplicate("vendor/example/skills/animate/SKILL.md", "animate")
        routing.reject_unlisted_duplicate("vendor/emil-kowalski/skills/animate/SKILL.md", "animate")

    def test_strengths_contrast_with_the_generated_purpose(self):
        skills = routing.discover(ROOT)
        catalog = routing.load_catalog(ROOT)
        weak = []
        for name, record in skills.items():
            purpose = re.sub(r"\s+", " ", record["purpose"]).strip()
            strength = re.sub(r"\s+", " ", catalog["skills"][name]["strengths"]).strip()
            if purpose.startswith(strength):
                weak.append(name)
        self.assertEqual(weak, [])

    def test_module_imports_without_a_preseeded_scripts_path(self):
        env = os.environ.copy()
        env.pop("PYTHONPATH", None)
        result = subprocess.run(
            [sys.executable, "-c",
             "import importlib.util; from pathlib import Path; "
             "p = Path('src/routing_inventory.py'); "
             "spec = importlib.util.spec_from_file_location('routing_inventory_fresh', p); "
             "module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module); "
             "print(module.install.sourced.__name__)"],
            cwd=ROOT, capture_output=True, text=True, env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("sourced", result.stdout)

    def test_unknown_phase_fails(self):
        skills = {"present": {"group": "developed"}}
        catalog = {"version": 1, "phases": list(routing.PHASES),
                   "stacks": {"developed": {"title": "Developed", "summary": "Owned skills."}},
                   "skills": {"present": {"phase": "whenever", "strengths": "No."}}}
        errors = routing.inventory_errors(skills, catalog, {"developed"})
        self.assertTrue(any("unknown phase" in error for error in errors))


if __name__ == "__main__":
    unittest.main()

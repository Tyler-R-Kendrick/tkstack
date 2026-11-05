"""The SDLC routing catalog matches the real skill inventory."""

import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location("routing_inventory", ROOT / "scripts/routing_inventory.py")
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

    def test_unknown_phase_fails(self):
        skills = {"present": {"group": "developed"}}
        catalog = {"version": 1, "phases": list(routing.PHASES),
                   "stacks": {"developed": {"title": "Developed", "summary": "Owned skills."}},
                   "skills": {"present": {"phase": "whenever", "strengths": "No."}}}
        errors = routing.inventory_errors(skills, catalog, {"developed"})
        self.assertTrue(any("unknown phase" in error for error in errors))


if __name__ == "__main__":
    unittest.main()

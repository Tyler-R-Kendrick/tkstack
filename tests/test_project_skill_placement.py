"""The project catalog exposes portable skills to shared Codex and Muse paths."""
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))
from skill_roots import load  # noqa: E402

install = load("install_project_placement", ROOT / "scripts/install.py")


class ProjectSkillPlacementTests(unittest.TestCase):
    def test_catalog_reconciles_shared_hosts_without_removing_foreign_links(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            install.prepare_aliases(ROOT)
            plan = install.link_plan(ROOT, target, ["codex"], "project", "catalog")
            destinations = {dest for _, dest in plan}
            expected = {target / ".agents/skills/architect", target / ".agents/skills/check-compiler-errors"}
            self.assertLessEqual(expected, destinations)
            install.apply(plan)
            foreign = target / ".agents/skills/external"
            foreign.symlink_to(target, target_is_directory=True)
            receipt = {dest.relative_to(target).as_posix(): str(src) for src, dest in plan}
            repeat = install.link_plan(ROOT, target, ["muse"], "project", "catalog")
            graphify = target / ".agents/skills/graphify"
            self.assertEqual(dict((dest, src) for src, dest in repeat)[graphify], graphify.resolve())
            self.assertTrue((graphify / "SKILL.md").is_file())
            self.assertFalse(set(install.stale_links(ROOT, target, ["muse"], repeat, "project", receipt)) & expected)
            personal = install.link_plan(ROOT, target, ["codex"], "project", "personal")
            stale = install.stale_links(ROOT, target, ["codex"], personal, "project", receipt)
            self.assertLessEqual(expected, set(stale))
            install.remove_stale(stale)
            self.assertTrue(foreign.is_symlink())

    def test_home_and_personal_profiles_keep_host_placement(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            for scope, profile in (("home", "catalog"), ("project", "personal")):
                with self.subTest(scope=scope, profile=profile):
                    plan = install.link_plan(ROOT, target, ["codex"], scope, profile)
                    self.assertNotIn(target / ".agents/skills/architect", {dest for _, dest in plan})
            cursor = install.link_plan(ROOT, target, ["cursor"], "project", "catalog")
            self.assertIn(target / ".cursor/skills/architect", {dest for _, dest in cursor})


if __name__ == "__main__":
    unittest.main()

"""Exercise Lever packaging without running its remote delivery workflows."""

from contextlib import redirect_stdout, redirect_stderr
from io import StringIO
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import install
import setup_lever


class LeverTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="tkstack-lever-test-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.target = self.root / "project"
        self.plan = setup_lever.link_plan(ROOT, self.target)

    def cli(self, *args):
        with patch.object(sys, "argv", ["setup_lever.py", "--target", str(self.target), *args]), redirect_stdout(StringIO()), redirect_stderr(StringIO()):
            return setup_lever.main()

    def test_native_copilot_install_preserves_all_relative_resources(self):
        self.assertEqual(self.cli(), 0)
        self.assertEqual(len(self.plan), 20)
        for source, destination in self.plan:
            self.assertTrue(install.matches(destination, source))
        router = self.target / ".github/skills/lever"
        self.assertTrue((router / "../../docs/autonomy.md").is_file())
        self.assertTrue((router / "../../templates/loop-card.md").is_file())
        self.assertTrue((router / "../../automations/pr-shepherd/prompt.md").is_file())
        self.assertEqual(self.cli(), 0)
        self.assertEqual(self.cli("--check"), 0)

    def test_shared_harness_links_resolve_lever_siblings_and_support_files(self):
        plan = install.link_plan(ROOT, self.target, ["codex", "claude", "cursor"])
        selected = [(source, destination) for source, destination in plan
                    if source.is_relative_to(ROOT / "vendor/lever")]
        self.assertEqual(len(selected), 48)
        with redirect_stdout(StringIO()):
            install.apply(selected)
        for prefix in install.SKILL_PATHS.values():
            router = self.target / prefix / "lever"
            self.assertTrue((router / "../find-the-loop/SKILL.md").is_file())
            self.assertTrue((router / "../../docs/spend.md").is_file())
            self.assertTrue((router / "../../config/personal.example.yml").is_file())

    def test_foreign_resource_collision_stops_before_dials_or_links(self):
        collision = self.target / ".github/docs"
        collision.mkdir(parents=True)
        (collision / "existing.md").write_text("user documentation\n")
        self.assertEqual(self.cli(), 1)
        self.assertFalse((self.target / ".github/lever.yml").exists())
        self.assertFalse((self.target / ".github/skills").exists())
        self.assertEqual((collision / "existing.md").read_text(), "user documentation\n")

    def test_existing_dials_and_unrelated_skills_survive_install_and_removal(self):
        config = self.target / ".github/lever.yml"
        config.parent.mkdir(parents=True)
        config.write_text("autonomy:\n  default: L1\nspend:\n  tier: standard\n")
        before = config.read_bytes()
        self.assertEqual(self.cli(), 0)
        unrelated = self.target / ".github/skills/my-own"
        unrelated.mkdir()
        self.assertEqual(self.cli("--uninstall"), 0)
        self.assertEqual(config.read_bytes(), before)
        self.assertTrue(unrelated.is_dir())
        self.assertEqual(self.cli("--check"), 1)

    def test_dry_run_and_check_do_not_create_a_project(self):
        self.assertEqual(self.cli("--dry-run"), 0)
        self.assertFalse(self.target.exists())
        self.assertEqual(self.cli("--check"), 1)
        self.assertFalse(self.target.exists())

    def test_symlinked_parent_cannot_redirect_setup_outside_target(self):
        outside = self.root / "outside"
        outside.mkdir()
        self.target.mkdir()
        (self.target / ".github").symlink_to(outside, target_is_directory=True)
        self.assertEqual(self.cli(), 1)
        self.assertEqual(list(outside.iterdir()), [])

    def test_paired_statistics_helper_runs_and_enforces_minimum_evidence(self):
        samples = self.root / "samples.jsonl"
        script = ROOT / "vendor/lever/skills/experiment-arms/scripts/arm_stats.py"
        for rounds, expected in [(6, "KEEP"), (3, "INCONCLUSIVE")]:
            with self.subTest(rounds=rounds):
                rows = [{"round": number, "arm": arm, "value": value}
                        for number in range(rounds) for arm, value in [("control", 100), ("treatment", 80)]]
                samples.write_text("".join(json.dumps(row) + "\n" for row in rows))
                result = subprocess.run([sys.executable, str(script), str(samples),
                                         "--control", "control", "--bar-pct", "5", "--boot", "100"],
                                        capture_output=True, text=True, check=True)
                self.assertIn(expected, result.stdout)


if __name__ == "__main__":
    unittest.main()

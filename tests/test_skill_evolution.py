"""Portable marketplace copies and fail-closed evolution integration."""

from contextlib import redirect_stdout
import importlib.util
from io import StringIO
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.dont_write_bytecode = True


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


evolve = load("tkstack_evolve", ROOT / "scripts/evolve.py")
from skillopt_sleep.judges import score_rule_judge


class SkillEvolutionTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="tkstack-evolve-test-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.fixture = self.root / "repository"
        self.fixture.mkdir()
        for name in ["skills/learn", "skills/sdlc", "evals/learn", "evals/sdlc"]:
            shutil.copytree(ROOT / name, self.fixture / name, ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copyfile(ROOT / "sources.lock.json", self.fixture / "sources.lock.json")
        self.run_dir = self.root / ".tkstack/evolution"
        self.run_dir.mkdir(parents=True)

    def test_marketplace_packages_have_root_skills_and_bundled_licenses(self):
        marketplace = json.loads((ROOT / ".claude-plugin/marketplace.json").read_text())
        self.assertEqual({plugin["name"] for plugin in marketplace["plugins"]},
                         {"learn", "sdlc", "unslop", "hill-climb", "tkstack-principles", "skillify", "hookify", "instructify", "flowify", "investigate", "write", "document", "fal-ai", "headroom", "open-design", "rtk", "lintify", "reusify", "codify"})
        adopted = {"fal-ai", "headroom", "open-design", "rtk"}
        for plugin in marketplace["plugins"]:
            root = ".agents/skills" if plugin["name"] in adopted else "skills"
            directory = ROOT / root / plugin["name"]
            self.assertEqual((ROOT / plugin["source"]).resolve(), directory)
            self.assertEqual(plugin["skills"], ["./"])
            self.assertFalse(plugin["strict"])
            content = (directory / "SKILL.md").read_text()
            name = re.search(r"^name: (.+)$", content, re.M)[1]
            description = re.search(r"^description: (.+)$", content, re.M)[1]
            self.assertEqual(name, directory.name)
            self.assertRegex(name, r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
            self.assertLessEqual(len(description), 1024)
            self.assertIn("license: MIT", content)
            self.assertEqual((directory / "LICENSE").read_bytes(), (ROOT / "LICENSE").read_bytes())

    def test_standalone_learning_writes_project_store_and_leaves_plugin_cache_alone(self):
        cached = self.root / "plugin-cache/learn"
        shutil.copytree(self.fixture / "skills/learn", cached)
        helper = load("standalone_learn", cached / "scripts/learn.py")
        project = self.root / "project"
        project.mkdir()
        before = {str(path.relative_to(cached)): path.read_bytes() for path in cached.rglob("*") if path.is_file()}
        with patch.object(Path, "cwd", return_value=project), patch.object(Path, "home", return_value=self.root / "user"), patch.dict(os.environ, {"TKSTACK_STEERING_DIR": ""}):
            store = helper.default_store()
            self.assertEqual(store, project / ".tkstack/steering")
            helper.capture(store, {"source": {"conversation": "portable-test", "message": "one"},
                                   "user_text": "Use the named maintainer's package.",
                                   "context": "A source identity correction.", "kind": "correction"})
        self.assertTrue((store / "events.jsonl").is_file())
        self.assertTrue((store / "rules.md").is_file())
        after = {str(path.relative_to(cached)): path.read_bytes() for path in cached.rglob("*") if path.is_file()}
        self.assertEqual(before, after)

    def test_nested_learning_finds_existing_ancestor_store_before_home(self):
        helper = load("nested_learn", self.fixture / "skills/learn/scripts/learn.py")
        project = self.root / "project"
        (project / ".tkstack/steering").mkdir(parents=True)
        home = self.root / "user"
        (home / ".tkstack/steering").mkdir(parents=True)
        nested = project / "src/deep"
        nested.mkdir(parents=True)
        with patch.object(Path, "cwd", return_value=nested), patch.object(Path, "home", return_value=home), patch.dict(os.environ, {"TKSTACK_STEERING_DIR": ""}):
            self.assertEqual(helper.default_store(), project / ".tkstack/steering")
            with patch.dict(os.environ, {"TKSTACK_STEERING_DIR": str(self.root / ".tkstack/explicit")}):
                self.assertEqual(helper.default_store(), self.root / ".tkstack/explicit")

    def test_evolution_scopes_memory_and_gates_without_global_config(self):
        with patch.object(evolve, "ROOT", self.fixture):
            cfg, tasks, _ = evolve.prepare("learn", self.run_dir, "handoff")
        self.assertFalse(cfg.evolve_memory)
        self.assertFalse(cfg.auto_adopt)
        self.assertTrue(cfg.gate_no_regression)
        self.assertEqual(cfg.gate_mode, "on")
        self.assertEqual(cfg.edit_budget, 1)
        self.assertEqual(Path(cfg.managed_skill_path()), self.fixture / "skills/learn/SKILL.md")
        self.assertEqual({task.split for task in tasks}, {"train", "val", "test"})
        self.assertTrue(all(task.origin == "authored" for task in tasks))

    def test_changed_live_skill_cannot_reuse_old_evolution_proof(self):
        with patch.object(evolve, "ROOT", self.fixture):
            evolve.prepare("learn", self.run_dir, "handoff")
            target = self.fixture / "skills/learn/SKILL.md"
            target.write_text(target.read_text() + "\nA changed live obligation.\n")
            with self.assertRaisesRegex(ValueError, "inputs changed"):
                evolve.prepare("learn", self.run_dir, "handoff")

    def test_choice_graders_reject_pending_markers_and_embedded_answers(self):
        with patch.object(evolve, "ROOT", self.fixture):
            _, tasks, _ = evolve.prepare("learn", self.run_dir, "handoff")
        for task in tasks:
            for response in ["[[SKILLOPT-SLEEP-PENDING:abcdef0123456789]]", "A or B or C", "", "The answer is A"]:
                with self.subTest(task=task.id, response=response):
                    hard, _, _ = score_rule_judge(task.judge, response)
                    self.assertEqual(hard, 0)

    def test_unanchored_or_substring_scorer_is_rejected(self):
        source = self.fixture / "evals/learn/tasks.json"
        original = json.loads(source.read_text())
        original["tasks"][0]["judge"]["checks"][0]["arg"] = "B"
        source.write_text(json.dumps(original))
        with patch.object(evolve, "ROOT", self.fixture), self.assertRaisesRegex(ValueError, "anchored action grader"):
            evolve.prepare("learn", self.run_dir, "handoff")

    def test_unanswered_handoff_does_not_publish_completion_or_mutate_skill(self):
        target = self.fixture / "skills/learn/SKILL.md"
        before = target.read_bytes()
        args = ["evolve.py", "learn", "--run-dir", str(self.run_dir)]
        with patch.object(evolve, "ROOT", self.fixture), patch.object(sys, "argv", args), redirect_stdout(StringIO()):
            status = evolve.main()
        self.assertEqual(status, 3)
        self.assertTrue((self.run_dir / "handoff/pending.json").is_file())
        self.assertFalse((self.run_dir / "result.json").exists())
        self.assertFalse((self.run_dir / "state/state.json").exists())
        self.assertEqual(target.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()

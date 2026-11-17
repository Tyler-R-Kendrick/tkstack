"""Behavioral tests for the task-specific harness draft action."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/hill-climb/scripts/experiment.py"
TEMPLATE = ROOT / "skills/hill-climb/templates/task-harness.json"


class ExperimentFactoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.source = self.directory / "product"
        self.source.mkdir()
        self.git("init", "-q")
        (self.source / "feature.txt").write_text("initial\n")
        self.git("add", "feature.txt")
        self.git("-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                 "commit", "-qm", "initial")
        self.base = self.git("rev-parse", "HEAD")
        self.output = self.directory / "draft" / "brief.json"
        self.request = {
            "action": "draft",
            "source": str(self.source),
            "goal": "Retain valid entries after a validation error",
            "paths": ["feature.txt"],
            "target": "web.form.interaction",
            "reason": "It covers the changed user interaction",
            "output": str(self.output),
        }

    def git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.source), *args],
                                       text=True).strip()

    def call(self, **changes):
        request = {**self.request, **changes}
        request_path = self.directory / "request.json"
        request_path.write_text(json.dumps(request))
        return subprocess.run([sys.executable, str(SCRIPT), "--request", str(request_path)],
                              text=True, capture_output=True)

    def test_draft_populates_only_facts_and_keeps_quality_blanks(self):
        result = self.call()
        self.assertEqual(result.returncode, 0, result.stderr)
        reply = json.loads(result.stdout)
        self.assertEqual(reply["draft"], str(self.output))
        draft = json.loads(self.output.read_text())
        template = json.loads(TEMPLATE.read_text())
        self.assertEqual(draft["status"], "draft")
        self.assertEqual(draft["outcome"]["user_goal"], self.request["goal"])
        self.assertEqual(draft["integration"]["repository"], str(self.source))
        self.assertEqual(draft["integration"]["base_commit"], self.base)
        self.assertEqual(draft["integration"]["editable_paths"], ["feature.txt"])
        self.assertEqual(draft["integration"]["targets"], [{
            "id": self.request["target"], "reason": self.request["reason"]}])
        self.assertEqual(draft["search"]["incumbent"], self.base)
        self.assertEqual(draft["quality"], template["quality"])
        self.assertEqual(draft["feedback"], template["feedback"])
        self.assertEqual(draft["evaluation"], template["evaluation"])
        self.assertEqual(self.git("status", "--porcelain"), "")
        self.assertEqual(self.git("rev-parse", "HEAD"), self.base)

    def test_compiled_skill_generates_draft_with_packaged_template(self):
        request_path = self.directory / "public-request.json"
        request_path.write_text(json.dumps(self.request))
        result = subprocess.run([
            sys.executable, str(ROOT / "skills/learn/skills/skillify/scripts/skillify.py"),
            "invoke", str(ROOT / "skills/hill-climb"), "--",
            "native", "experiment", "--request", str(request_path)],
            text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(self.output.read_text())["integration"]["base_commit"], self.base)

    def test_explicit_base_is_used_even_when_head_moves(self):
        (self.source / "feature.txt").write_text("newer\n")
        self.git("add", "feature.txt")
        self.git("-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                 "commit", "-qm", "newer")
        result = self.call(base=self.base)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(self.output.read_text())["integration"]["base_commit"], self.base)

    def test_invalid_scope_cannot_write_a_draft(self):
        for paths in (["../other"], ["/tmp/not-repository-relative"], [".git/config"], []):
            with self.subTest(paths=paths):
                result = self.call(paths=paths)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(self.output.exists())
        result = self.call(output=str(self.source / "brief.json"))
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.source / "brief.json").exists())
        self.assertEqual(self.git("status", "--porcelain"), "")

    def test_existing_file_is_never_overwritten(self):
        self.output.parent.mkdir()
        self.output.write_text("original")
        result = self.call()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.output.read_text(), "original")

    def test_symlinks_cannot_escape_scope_or_redirect_output_into_source(self):
        outside = self.directory / "outside"
        outside.mkdir()
        (self.source / "escape").symlink_to(outside, target_is_directory=True)
        result = self.call(paths=["escape/new.txt"])
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.output.exists())
        (self.source / "escape").unlink()
        (self.directory / "link").symlink_to(self.source, target_is_directory=True)
        result = self.call(output=str(self.directory / "link" / "draft.json"))
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.source / "draft.json").exists())
        self.assertEqual(self.git("status", "--porcelain"), "")

    def test_missing_values_and_non_full_commit_are_rejected(self):
        for changes in ({"goal": " "}, {"target": ""}, {"reason": ""},
                        {"base": self.base[:8]}, {"paths": [".."]}):
            with self.subTest(changes=changes):
                result = self.call(**changes)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()

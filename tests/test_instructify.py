"""Instruction ownership, scope, native rendering, and write lifecycle contracts."""

import copy
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "skills/learn/skills/instructify/scripts/instructify.py"
sys.dont_write_bytecode = True


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


instructify = load("instructify_helper", SCRIPT)


class InstructifyTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.project = Path(temporary.name) / "project"
        self.project.mkdir()
        self.source = self.project / "harnesses/instructions/policy.json"
        self.source.parent.mkdir(parents=True)
        self.manifest = json.loads((ROOT / "skills/learn/skills/instructify/examples/manifest.json").read_text())
        self.save()

    def save(self):
        self.source.write_text(json.dumps(self.manifest))

    def plan(self, remove=False):
        return instructify.build_plan(self.project, self.source, remove)

    def test_apply_update_remove_preserves_existing_content_and_imports(self):
        self.manifest["targets"] = ["agents", "claude", "cursor", "copilot"]
        self.save()
        agents = self.project / "AGENTS.md"
        agents.write_text("Existing instructions without final newline")
        claude = self.project / "CLAUDE.md"
        claude.write_text("@AGENTS.md\n")
        github = self.project / ".github/copilot-instructions.md"
        github.parent.mkdir()
        github.write_text("Existing Copilot instructions\n")
        initial = {p: p.read_bytes() for p in (agents, claude, github)}
        instructify.apply(self.project, self.plan())
        self.assertEqual(claude.read_text(), "@AGENTS.md\n")
        self.assertTrue(agents.read_text().startswith(initial[agents].decode()))
        self.assertEqual(self.plan()["changes"], [])
        self.manifest["instructions"][0]["instruction"] = "Name the exact contract command and its observed exit status."
        self.save()
        instructify.apply(self.project, self.plan())
        self.assertIn("observed exit status", agents.read_text())
        self.assertEqual(agents.read_text().count("<!-- instructify:contract-evidence:start -->"), 1)
        instructify.apply(self.project, self.plan(remove=True))
        for path, original in initial.items():
            self.assertEqual(path.read_bytes(), original)
        self.assertFalse((self.project / ".cursor/rules/instructify-contract-evidence.mdc").exists())

    def test_new_shared_body_and_owned_claude_import_remove_to_original_absence(self):
        instructify.apply(self.project, self.plan())
        agents = self.project / "AGENTS.md"
        claude = self.project / "CLAUDE.md"
        self.assertIn("observed results", agents.read_text())
        self.assertIn("\n@AGENTS.md\n", claude.read_text())
        self.assertNotIn("consumer/provider", claude.read_text())
        self.assertEqual(instructify.apply(self.project, self.plan())["changed"], 0)
        instructify.apply(self.project, self.plan(remove=True))
        self.assertFalse(agents.exists())
        self.assertFalse(claude.exists())

    def test_directory_bindings_render_explicit_native_scopes(self):
        self.manifest.update(scope="packages/api", targets=["agents", "claude", "cursor", "copilot"])
        self.save()
        instructify.apply(self.project, self.plan())
        self.assertFalse((self.project / "AGENTS.md").exists())
        self.assertTrue((self.project / "packages/api/AGENTS.md").exists())
        cursor = (self.project / ".cursor/rules/instructify-contract-evidence.mdc").read_text()
        self.assertTrue(cursor.startswith("---\n"))
        self.assertIn('globs: "packages/api/**/*"', cursor)
        self.assertIn("alwaysApply: false", cursor)
        copilot = (self.project / ".github/instructions/instructify-contract-evidence.instructions.md").read_text()
        self.assertIn('applyTo: "packages/api/**/*"', copilot)

    def test_stale_source_or_target_and_tampered_plan_fail_before_any_write(self):
        self.manifest["targets"] = ["agents", "cursor"]
        self.save()
        plan = self.plan()
        agents = self.project / "AGENTS.md"
        agents.write_text("Concurrent user edit\n")
        with self.assertRaisesRegex(ValueError, "stale or modified"):
            instructify.apply(self.project, plan)
        self.assertFalse((self.project / ".cursor").exists())
        self.assertEqual(agents.read_text(), "Concurrent user edit\n")
        plan = self.plan()
        plan["changes"][0]["after"] += "Injected plan edit"
        with self.assertRaisesRegex(ValueError, "stale or modified"):
            instructify.apply(self.project, plan)
        plan = self.plan()
        self.manifest["title"] = "Changed source"
        self.save()
        with self.assertRaisesRegex(ValueError, "stale or modified"):
            instructify.apply(self.project, plan)

    def test_manual_managed_edit_and_foreign_manifest_owner_are_not_overwritten(self):
        instructify.apply(self.project, self.plan())
        original = (self.project / "AGENTS.md").read_text()
        (self.project / "AGENTS.md").write_text(original.replace("observed results", "made-up results"))
        with self.assertRaisesRegex(ValueError, "reconcile manual edits"):
            self.plan()
        (self.project / "AGENTS.md").write_text(original)
        other = self.source.with_name("other.json")
        other.write_text(json.dumps(self.manifest))
        with self.assertRaisesRegex(ValueError, "another manifest"):
            instructify.build_plan(self.project, other)

    def test_native_header_edits_and_unowned_native_files_are_preserved(self):
        self.manifest["targets"] = ["cursor"]
        self.save()
        rule = self.project / ".cursor/rules/instructify-contract-evidence.mdc"
        rule.parent.mkdir(parents=True)
        rule.write_text("User-owned native rule")
        with self.assertRaisesRegex(ValueError, "not owned"):
            self.plan()
        rule.unlink()
        instructify.apply(self.project, self.plan())
        rule.write_text(rule.read_text().replace("alwaysApply: true", "alwaysApply: false"))
        with self.assertRaisesRegex(ValueError, "content/header changed"):
            self.plan(remove=True)

    def test_existing_empty_file_and_foreign_trailing_text_survive_removal(self):
        agents = self.project / "AGENTS.md"
        agents.write_text("")
        instructify.apply(self.project, self.plan())
        instructify.apply(self.project, self.plan(remove=True))
        self.assertTrue(agents.is_file())
        self.assertEqual(agents.read_bytes(), b"")
        instructify.apply(self.project, self.plan())
        with agents.open("a") as handle:
            handle.write("Unrelated trailing guidance\n")
        instructify.apply(self.project, self.plan(remove=True))
        self.assertEqual(agents.read_text(), "Unrelated trailing guidance\n")
        instructify.apply(self.project, self.plan())
        instructify.apply(self.project, self.plan(remove=True))
        self.assertEqual(agents.read_text(), "Unrelated trailing guidance\n")

    def test_codex_override_is_checked_and_empty_override_presence_is_snapshotted(self):
        plan = self.plan()
        override = self.project / "AGENTS.override.md"
        override.write_text("")
        with self.assertRaisesRegex(ValueError, "stale or modified"):
            instructify.apply(self.project, plan)
        self.assertTrue(self.plan()["changes"])
        override.write_text("Active override guidance")
        with self.assertRaisesRegex(ValueError, "shadows AGENTS.md"):
            self.plan()
        self.assertFalse((self.project / "AGENTS.md").exists())

    def test_fenced_import_is_not_reused_and_managed_imports_have_independent_owners(self):
        claude = self.project / "CLAUDE.md"
        claude.write_text("Example only:\n```md\n@AGENTS.md\n```\n")
        instructify.apply(self.project, self.plan())
        self.assertIn("<!-- instructify:contract-evidence:start -->", claude.read_text())
        second_manifest = copy.deepcopy(self.manifest)
        second_manifest["id"] = "second-policy"
        second_source = self.source.with_name("second.json")
        second_source.write_text(json.dumps(second_manifest))
        second_plan = instructify.build_plan(self.project, second_source)
        instructify.apply(self.project, second_plan)
        instructify.apply(self.project, self.plan(remove=True))
        self.assertIn("<!-- instructify:second-policy:start -->", claude.read_text())
        self.assertEqual(instructify.build_plan(self.project, second_source)["changes"], [])

    def test_read_only_preview_and_busy_writer_have_no_write_side_effects(self):
        before = sorted(str(p.relative_to(self.project)) for p in self.project.rglob("*"))
        plan = self.plan()
        self.assertGreater(instructify.apply(self.project, plan, dry_run=True)["changed"], 0)
        self.assertEqual(before, sorted(str(p.relative_to(self.project)) for p in self.project.rglob("*")))
        lock = self.project / ".tkstack/locks/instructify.lock"
        lock.mkdir(parents=True)
        with self.assertRaisesRegex(ValueError, "busy"):
            instructify.apply(self.project, plan)
        self.assertTrue(lock.is_dir())
        self.assertFalse((self.project / "AGENTS.md").exists())

    def test_mid_batch_write_error_restores_completed_files(self):
        agents = self.project / "AGENTS.md"
        claude = self.project / "CLAUDE.md"
        agents.write_text("Existing project notes\n")
        claude.write_text("Existing Claude notes\n")
        original = {p: p.read_bytes() for p in (agents, claude)}
        write = instructify.atomic_write
        calls = []
        def fail_second(path, content):
            calls.append(path)
            if len(calls) == 2:
                raise OSError("Simulated write failure")
            return write(path, content)
        with patch.object(instructify, "atomic_write", side_effect=fail_second):
            with self.assertRaisesRegex(ValueError, r"rollback gaps: \[\]"):
                instructify.apply(self.project, self.plan())
        for path, content in original.items():
            self.assertEqual(path.read_bytes(), content)
        self.assertFalse((self.project / ".tkstack/locks/instructify.lock").exists())

    def test_symlink_paths_and_glob_scopes_are_rejected(self):
        outside = self.project.parent / "outside"
        outside.mkdir()
        (outside / "AGENTS.md").write_text("External notes")
        (self.project / "AGENTS.md").symlink_to(outside / "AGENTS.md")
        with self.assertRaisesRegex(ValueError, "symlinked"):
            self.plan()
        self.assertEqual((outside / "AGENTS.md").read_text(), "External notes")
        self.manifest["scope"] = "packages/*"
        self.save()
        with self.assertRaisesRegex(ValueError, "literal directory"):
            self.plan()

    def test_standalone_copy_and_cli_check_preserve_plugin_cache(self):
        cache = self.project.parent / "plugin-cache/instructify"
        shutil.copytree(ROOT / "skills/learn/skills/instructify", cache, ignore=shutil.ignore_patterns("__pycache__"))
        helper = load("standalone_instructify", cache / "scripts/instructify.py")
        before = {p.relative_to(cache): p.read_bytes() for p in cache.rglob("*") if p.is_file()}
        helper.apply(self.project, helper.build_plan(self.project, self.source))
        self.assertEqual(before, {p.relative_to(cache): p.read_bytes() for p in cache.rglob("*") if p.is_file()})
        result = subprocess.run([sys.executable, str(cache / "scripts/instructify.py"), "check", "--project", str(self.project), "--input", str(self.source)],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(json.loads(result.stdout)["aligned"])

    def test_parent_file_collision_is_found_during_read_only_preflight(self):
        self.manifest["targets"] = ["cursor", "copilot"]
        self.save()
        (self.project / ".github").write_text("Existing user file")
        with self.assertRaisesRegex(ValueError, "parent is not a directory"):
            self.plan()
        self.assertFalse((self.project / ".cursor").exists())


if __name__ == "__main__":
    unittest.main()

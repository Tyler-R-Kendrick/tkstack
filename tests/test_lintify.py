"""Publication boundaries for self-contained native linter example packages."""

from concurrent.futures import ThreadPoolExecutor
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parent.parent
sys.dont_write_bytecode = True


def load(path):
    spec = importlib.util.spec_from_file_location("lintify_helper", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


lintify = load(ROOT / "skills/learn/skills/lintify/scripts/lintify.py")


class LintifyTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def test_native_packages_are_examples_with_hidden_rules_and_real_locks(self):
        for backend in ("eslint", "lintbook", "gptlint"):
            target = self.root / backend
            result = lintify.scaffold(backend, target)
            self.assertEqual(result["status"], "example")
            self.assertFalse(result["native_validated"])
            self.assertFalse(result["policy_activated"])
            self.assertEqual((target / "LICENSE").read_bytes(), (ROOT / "LICENSE").read_bytes())
        self.assertTrue((self.root / "gptlint/.gptlint/comment-implementation-agreement.md").is_file())
        self.assertTrue((self.root / "lintbook/.lintbook/gen/no-dbg.df").is_file())
        self.assertFalse(list((self.root / "lintbook/.lintbook/gen").glob("*.json")))
        for backend, version in (("eslint", "9.39.1"), ("gptlint", "1.6.0")):
            lock = json.loads((self.root / backend / "package-lock.json").read_text())
            self.assertEqual(lock["packages"]["node_modules/" + backend]["version"], version)

    def test_existing_directory_file_and_dangling_link_are_preserved(self):
        directory = self.root / "directory"
        directory.mkdir()
        content = directory / "mine.txt"
        content.write_text("existing user work")
        file = self.root / "file"
        file.write_text("keep")
        link = self.root / "link"
        link.symlink_to(self.root / "missing")
        for target in (directory, file, link):
            with self.assertRaises(FileExistsError):
                lintify.scaffold("eslint", target)
        self.assertEqual(content.read_text(), "existing user work")
        self.assertEqual(file.read_text(), "keep")
        self.assertTrue(link.is_symlink())

    def test_copy_failure_removes_only_its_partial_output(self):
        destination = self.root / "example"
        copy = lintify.shutil.copyfileobj
        count = 0
        def fail(source, target):
            nonlocal count
            count += 1
            if count == 3:
                target.write(b"partial")
                raise OSError("fixture disk failure")
            return copy(source, target)
        with patch.object(lintify.shutil, "copyfileobj", side_effect=fail):
            with self.assertRaisesRegex(OSError, "fixture disk failure"):
                lintify.scaffold("eslint", destination)
        self.assertFalse(destination.exists())

    def test_missing_or_escaping_template_is_rejected_before_creation(self):
        package = self.root / "package"
        shutil.copytree(ROOT / "skills/learn/skills/lintify", package, ignore=shutil.ignore_patterns("__pycache__"))
        template = package / "templates/eslint/eslint.config.mjs"
        template.unlink()
        target = self.root / "example"
        with patch.object(lintify, "PACKAGE", package):
            with self.assertRaisesRegex(ValueError, "Missing or escaping"):
                lintify.scaffold("eslint", target)
            self.assertFalse(target.exists())
            foreign = self.root / "foreign.mjs"
            foreign.write_text("foreign config")
            template.symlink_to(foreign)
            with self.assertRaisesRegex(ValueError, "Missing or escaping"):
                lintify.scaffold("eslint", target)
        self.assertFalse(target.exists())
        self.assertEqual(foreign.read_text(), "foreign config")

    def test_same_target_has_exactly_one_writer_under_concurrent_calls(self):
        barrier = threading.Barrier(2)
        destination = self.root / "example"
        def create(_):
            barrier.wait(timeout=3)
            try:
                lintify.scaffold("gptlint", destination)
                return "created"
            except FileExistsError:
                return "collision"
        with ThreadPoolExecutor(max_workers=2) as workers:
            results = list(workers.map(create, range(2)))
        self.assertCountEqual(results, ["created", "collision"])
        self.assertTrue((destination / "gptlint.config.mjs").is_file())
        self.assertTrue((destination / "LICENSE").is_file())

    def test_standalone_package_does_not_copy_cache_or_change_its_source(self):
        cache = self.root / "plugin-cache/lintify"
        shutil.copytree(ROOT / "skills/learn/skills/lintify", cache, ignore=shutil.ignore_patterns("__pycache__"))
        junk = cache / "templates/eslint/node_modules/accidental"
        junk.mkdir(parents=True)
        (junk / "do-not-copy.txt").write_text("cache")
        helper = load(cache / "scripts/lintify.py")
        target = self.root / "project/rule"
        before = {str(path.relative_to(cache)): path.read_bytes() for path in cache.rglob("*") if path.is_file()}
        helper.scaffold("eslint", target)
        self.assertFalse((target / "node_modules").exists())
        after = {str(path.relative_to(cache)): path.read_bytes() for path in cache.rglob("*") if path.is_file()}
        self.assertEqual(before, after)

    def test_unknown_engine_has_no_filesystem_effect(self):
        target = self.root / "example"
        with self.assertRaisesRegex(ValueError, "Unsupported backend"):
            lintify.scaffold("not-a-linter", target)
        self.assertFalse(target.exists())


if __name__ == "__main__":
    unittest.main()

"""Native-source authoring and real deterministic binding checks, not SDK emulation."""

import asyncio
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


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


flowify = load("flowify_helper", ROOT / "skills/flowify/scripts/flowify.py")
bindings = load("flowify_bindings", ROOT / "skills/flowify/templates/maf/bindings.py")


class FlowifyTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.project = self.root / "project"
        self.project.mkdir()
        (self.project / "abc.txt").write_bytes(b"abc")
        (self.project / "empty.txt").write_bytes(b"")

    def test_native_scaffolds_keep_real_formats_and_never_overwrite(self):
        for backend, filename in (("maf", "workflow.yaml"), ("rhai", "workflow.rhai")):
            target = self.root / backend
            result = flowify.scaffold(backend, target, backend)
            self.assertFalse(result["native_validated"])
            self.assertFalse(result["executed"])
            source = (target / filename).read_bytes()
            with self.assertRaises(FileExistsError):
                flowify.scaffold(backend, target, backend)
            self.assertEqual((target / filename).read_bytes(), source)
            inspected = flowify.inspect_source(backend, target / filename)
            self.assertFalse(inspected["native_validated"])
            self.assertFalse(inspected["executed"])
        self.assertTrue((self.root / "rhai/workflow.rhai").read_text().startswith("let meta = #{"))
        self.assertEqual(flowify.inspect_source("maf", self.root / "maf/workflow.yaml")["action_kinds"],
                         ["InvokeFunctionTool", "SendActivity"])

    def test_maf_profile_rejects_bad_yaml_duplicates_cycles_and_action_ids(self):
        path = self.root / "invalid.yaml"
        invalid = [
            "name: [\n",
            "name: one\nname: two\nactions: []\n",
            "name: cyclic\nactions: &loop [*loop]\n",
            "name: duplicate\nactions:\n  - {kind: EndWorkflow, id: same}\n  - {kind: EndWorkflow, id: same}\n",
            "name: empty\nactions: []\n"]
        for source in invalid:
            with self.subTest(source=source):
                path.write_text(source)
                with self.assertRaises(ValueError):
                    flowify.inspect_source("maf", path)

    def test_rhai_source_record_is_not_a_parser_or_validation_pass(self):
        path = self.root / "invalid.rhai"
        path.write_text("This is deliberately not valid Rhai source.")
        result = flowify.inspect_source("rhai", path)
        self.assertEqual(result["status"], "source-recorded")
        self.assertFalse(result["native_validated"])
        self.assertIn("No Rhai parser", result["limits"])

    def test_missing_native_runtimes_remain_unavailable(self):
        maf = self.root / "maf"
        rhai = self.root / "rhai"
        flowify.scaffold("maf", maf, "maf")
        flowify.scaffold("rhai", rhai, "rhai")
        with patch.object(flowify.importlib.util, "find_spec", return_value=None):
            result, status = flowify.native_check("maf", maf / "workflow.yaml")
        self.assertEqual(status, 3)
        self.assertFalse(result["native_validated"])
        with patch.object(flowify.shutil, "which", return_value=None):
            result, status = flowify.native_check("rhai", rhai / "workflow.rhai")
        self.assertEqual(status, 3)
        self.assertFalse(result["executed"])

    def test_binding_hashes_actual_files_against_known_vectors(self):
        result = asyncio.run(bindings.hash_files(self.project, ["abc.txt", "empty.txt"]))
        self.assertEqual(result, {"count": 2, "files": [
            {"path": "abc.txt", "sha256": "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"},
            {"path": "empty.txt", "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"}]})

    def test_binding_rejects_missing_escaping_and_duplicate_inputs(self):
        outside = self.root / "outside.txt"
        outside.write_text("outside")
        (self.project / "alias.txt").symlink_to(self.project / "abc.txt")
        for paths in (["missing"], [str(outside)], ["../outside.txt"], ["abc.txt", "alias.txt"], []):
            with self.subTest(paths=paths), self.assertRaises(ValueError):
                asyncio.run(bindings.hash_files(self.project, paths))
        with self.assertRaises(ValueError):
            asyncio.run(bindings.hash_files(self.project, ["abc.txt"], jobs=0))

    def test_bounded_overlap_and_stable_order_with_controlled_completion(self):
        (self.project / "third.txt").write_text("third")
        release_first = threading.Event()
        first_started = threading.Event()
        state_lock = threading.Lock()
        counts = {"active": 0, "peak": 0}
        fingerprint = bindings.fingerprint
        def controlled(path):
            with state_lock:
                counts["active"] += 1
                counts["peak"] = max(counts["peak"], counts["active"])
            try:
                if path.name == "abc.txt":
                    first_started.set()
                    if not release_first.wait(2):
                        raise AssertionError("Second independent read did not start")
                elif path.name == "empty.txt":
                    if not first_started.wait(2):
                        raise AssertionError("First read did not start")
                    release_first.set()
                return fingerprint(path)
            finally:
                with state_lock:
                    counts["active"] -= 1
        with patch.object(bindings, "fingerprint", side_effect=controlled):
            result = asyncio.run(bindings.hash_files(self.project, ["abc.txt", "empty.txt", "third.txt"], jobs=2))
        self.assertEqual(counts, {"active": 0, "peak": 2})
        self.assertEqual([r["path"] for r in result["files"]], ["abc.txt", "empty.txt", "third.txt"])

    def test_cancellation_joins_thread_backed_read_before_returning(self):
        started, release, finished = threading.Event(), threading.Event(), threading.Event()
        fingerprint = bindings.fingerprint
        def controlled(path):
            started.set()
            if not release.wait(2):
                raise AssertionError("Read was never released")
            try:
                return fingerprint(path)
            finally:
                finished.set()
        async def exercise():
            task = asyncio.create_task(bindings.hash_files(self.project, ["abc.txt"], jobs=1))
            self.assertTrue(await asyncio.to_thread(started.wait, 2))
            task.cancel()
            checkpoint = asyncio.get_running_loop().create_future()
            asyncio.get_running_loop().call_soon(checkpoint.set_result, None)
            await checkpoint
            self.assertFalse(task.done())
            release.set()
            with self.assertRaises(asyncio.CancelledError):
                await task
            self.assertTrue(finished.is_set())
        with patch.object(bindings, "fingerprint", side_effect=controlled):
            asyncio.run(exercise())

    def test_read_failure_never_returns_partial_success(self):
        fingerprint = bindings.fingerprint
        def fail_one(path):
            if path.name == "empty.txt":
                raise OSError("Controlled unreadable file")
            return fingerprint(path)
        with patch.object(bindings, "fingerprint", side_effect=fail_one):
            with self.assertRaisesRegex(OSError, "Controlled unreadable"):
                asyncio.run(bindings.hash_files(self.project, ["abc.txt", "empty.txt"]))

    def test_standalone_scaffolding_keeps_plugin_cache_unchanged(self):
        cache = self.root / "plugin-cache/flowify"
        shutil.copytree(ROOT / "skills/flowify", cache, ignore=shutil.ignore_patterns("__pycache__"))
        helper = load("copied_flowify", cache / "scripts/flowify.py")
        before = {p.relative_to(cache): p.read_bytes() for p in cache.rglob("*") if p.is_file()}
        target = self.project / "workflows/check-files"
        helper.scaffold("maf", target, "check-files")
        self.assertEqual(before, {p.relative_to(cache): p.read_bytes() for p in cache.rglob("*") if p.is_file()})
        self.assertEqual(helper.inspect_source("maf", target / "workflow.yaml")["name"], "check-files")

    def test_partial_scaffold_write_failure_removes_only_its_new_directory(self):
        target = self.root / "partial"
        write = Path.write_text
        calls = []
        def fail_second(path, content, *args, **kwargs):
            calls.append(path)
            result = write(path, content, *args, **kwargs)
            if len(calls) == 2:
                raise OSError("Controlled partial write")
            return result
        with patch.object(Path, "write_text", new=fail_second):
            with self.assertRaisesRegex(OSError, "Controlled partial"):
                flowify.scaffold("maf", target, "partial")
        self.assertFalse(target.exists())


if __name__ == "__main__":
    unittest.main()

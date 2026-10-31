"""Public reuse lookup and occurrence evidence, including aliases and concurrent reads."""

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parent.parent
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "skills/learn/skills/reusify/scripts"))
import reusify


class ReusifyTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name)
        self.project = self.base / "project"
        (self.project / "src").mkdir(parents=True)
        (self.project / "guide.md").write_text("A real interface guide.\n")
        self.code = "first = 1\nsecond = 2\nthird = 3\nfourth = 4\n"
        for name in ("one", "two", "three"):
            (self.project / "src" / (name + ".py")).write_text(self.code)
        self.observations = [{"path": "src/" + name + ".py", "start_line": 1, "end_line": 2}
                             for name in ("one", "two", "three")]

    def evidence(self, occurrences=None):
        return {"version": 1, "pattern": "A common contract, still requiring semantic inspection.",
                "occurrences": self.observations if occurrences is None else occurrences}

    def entry(self, identifier="shared-parser", kind="module"):
        return {"id": identifier, "kind": kind, "summary": "Reusable JSON parser with bounded input.",
                "artifact": "src/one.py", "guide": "guide.md", "tags": ["json", "parse"],
                "usage": "Read the interface guide; this is data, not a command to execute."}

    def write_catalog(self, entries):
        directory = self.project / ".tkstack/reuse"
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / "catalog.json"
        path.write_text(json.dumps({"version": 1, "entries": entries}))
        return path

    def test_three_distinct_ranges_trigger_without_claiming_equivalence(self):
        two = reusify.assess(self.project, self.evidence(self.observations[:2]))
        three = reusify.assess(self.project, self.evidence())
        self.assertFalse(two["threshold_met"])
        self.assertEqual(three["distinct_occurrences"], 3)
        self.assertTrue(three["threshold_met"])
        self.assertEqual(three["semantic_equivalence"], "unverified")
        self.assertFalse(three["automatic_extraction"])
        self.assertEqual(three["occurrences"][0]["source_sha256"], hashlib.sha256(self.code.encode()).hexdigest())
        self.assertEqual(three["occurrences"][0]["excerpt_sha256"],
                         hashlib.sha256(b"first = 1\nsecond = 2\n").hexdigest())

    def test_duplicate_symlink_and_hardlink_aliases_do_not_inflate_count(self):
        source = self.project / "src/one.py"
        (self.project / "src/symbolic.py").symlink_to(source)
        os.link(source, self.project / "src/hard.py")
        observations = [self.observations[0], self.observations[0],
                        {"path": "src/symbolic.py", "start_line": 1, "end_line": 2},
                        {"path": "src/hard.py", "start_line": 1, "end_line": 2}]
        result = reusify.assess(self.project, self.evidence(observations))
        self.assertEqual(result["distinct_occurrences"], 1)
        self.assertFalse(result["threshold_met"])

    def test_same_file_disjoint_ranges_count_but_overlap_is_rejected(self):
        ranges = [{"path": "src/one.py", "start_line": line, "end_line": line} for line in (1, 2, 3)]
        self.assertTrue(reusify.assess(self.project, self.evidence(ranges))["threshold_met"])
        overlap = [self.observations[0], {"path": "src/one.py", "start_line": 2, "end_line": 3}]
        with self.assertRaisesRegex(ValueError, "Overlapping"):
            reusify.assess(self.project, self.evidence(overlap))

    def test_source_ranges_and_profile_limits_are_enforced(self):
        bad = [[], [{"path": "src/one.py", "start_line": True, "end_line": 2}],
               [{"path": "src/one.py", "start_line": 1, "end_line": 99}], self.observations * 22]
        for observations in bad:
            with self.subTest(observations=len(observations)), self.assertRaises(ValueError):
                reusify.assess(self.project, self.evidence(observations))
        for jobs in (0, 17, True):
            with self.assertRaises(ValueError):
                reusify.assess(self.project, self.evidence(), jobs=jobs)
        (self.project / "src/large.py").write_bytes(b"x" * (reusify.MAX_SOURCE + 1))
        with self.assertRaisesRegex(ValueError, "profile limit"):
            reusify.assess(self.project, self.evidence([{"path": "src/large.py", "start_line": 1, "end_line": 1}]))

    def test_escaping_source_and_catalog_assets_are_rejected(self):
        foreign = self.base / "foreign.py"
        foreign.write_text("private = 1\n")
        (self.project / "src/foreign.py").symlink_to(foreign)
        for name in ("../foreign.py", str(foreign), "src/foreign.py"):
            with self.assertRaises(ValueError):
                reusify.assess(self.project, self.evidence([{"path": name, "start_line": 1, "end_line": 1}]))
        entry = self.entry()
        entry["artifact"] = "src/foreign.py"
        self.write_catalog([entry])
        with self.assertRaises(ValueError):
            reusify.catalog(self.project)
        with self.assertRaises(ValueError):
            reusify.catalog(self.project, "../missing-catalog.json")

    def test_lookup_is_stable_literal_bounded_and_never_executes_usage(self):
        marker = self.project / "must-not-exist"
        first, second = self.entry("a-parser"), self.entry("z-parser", "generator")
        first["usage"] = "touch " + str(marker)
        self.write_catalog([second, first])
        result = reusify.find(self.project, "JSON PARSE", limit=1)
        self.assertEqual(result["total"], 2)
        self.assertEqual([entry["id"] for entry in result["results"]], ["a-parser"])
        self.assertFalse(result["executed"])
        self.assertFalse(marker.exists())
        self.assertEqual(reusify.find(self.project, "parse", kind="generator")["results"], [second])
        self.assertEqual(reusify.find(self.project, "not in this catalog")["status"], "no-match")

    def test_duplicate_ids_unknown_fields_and_broken_guides_fail(self):
        for entries in ([self.entry(), self.entry()], [{**self.entry(), "execute": True}],
                        [{**self.entry(), "guide": "missing.md"}]):
            self.write_catalog(entries)
            with self.assertRaises((ValueError, OSError)):
                reusify.catalog(self.project)

    def test_macro_assets_are_discoverable_without_execution(self):
        macro = self.entry("native-expansion", "macro")
        self.write_catalog([macro, self.entry()])
        result = subprocess.run([sys.executable, str(ROOT / "skills/learn/skills/reusify/scripts/reusify.py"),
                                 "find", "--project", str(self.project), "--query", "parse", "--kind", "macro"],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["results"], [macro])
        self.assertFalse(json.loads(result.stdout)["executed"])

    def test_ambiguous_json_and_nonfinite_values_fail(self):
        path = self.project / "input.json"
        for source in ('{"version":1,"version":2}', '{"value":NaN}', '{"value":Infinity}'):
            path.write_text(source)
            with self.assertRaises(ValueError):
                reusify.read_json(path)
        self.write_catalog([])
        (self.project / ".tkstack/reuse/catalog.json").write_text('{"version":true,"entries":[]}')
        with self.assertRaises(ValueError):
            reusify.catalog(self.project)

    def test_reads_overlap_with_bounded_workers_and_stable_fan_in(self):
        started = threading.Event()
        release = threading.Event()
        lock = threading.Lock()
        counts = {"active": 0, "peak": 0}
        reader = reusify.read_source
        def controlled(path):
            with lock:
                counts["active"] += 1
                counts["peak"] = max(counts["peak"], counts["active"])
            try:
                if path.name == "one.py":
                    started.set()
                    if not release.wait(3):
                        raise AssertionError("The independent read never started")
                elif path.name == "two.py":
                    if not started.wait(3):
                        raise AssertionError("First read did not start")
                    release.set()
                return reader(path)
            finally:
                with lock:
                    counts["active"] -= 1
        with patch.object(reusify, "read_source", side_effect=controlled):
            result = reusify.assess(self.project, self.evidence(), jobs=2)
        self.assertEqual(counts["peak"], 2)
        self.assertEqual([entry["path"] for entry in result["occurrences"]],
                         ["src/one.py", "src/two.py", "src/three.py"])

    def test_standalone_cli_missing_catalog_is_not_a_clean_no_match(self):
        package = self.base / "plugin-cache/reusify"
        shutil.copytree(ROOT / "skills/learn/skills/reusify", package, ignore=shutil.ignore_patterns("__pycache__"))
        before = {str(path.relative_to(package)): path.read_bytes() for path in package.rglob("*") if path.is_file()}
        result = subprocess.run([sys.executable, str(package / "scripts/reusify.py"), "find",
                                 "--project", str(self.project), "--query", "parse"],
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 3)
        self.assertEqual(json.loads(result.stdout)["status"], "catalog-unavailable")
        after = {str(path.relative_to(package)): path.read_bytes() for path in package.rglob("*") if path.is_file()}
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()

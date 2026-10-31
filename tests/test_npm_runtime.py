"""Local npm publication, failure isolation, and native MCP host selection."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import npm_runtime
import setup_integrations


class NpmRuntimeTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.recipe = self.root / "harnesses/openwiki"
        self.recipe.mkdir(parents=True)
        for name in ("package.json", "package-lock.json"):
            (self.recipe / name).write_text('{"fixture":true}\n')
        self.tool = {"kind": "npm", "package": "openwiki", "bin": "openwiki",
                     "version": "0.7.2", "minimum_node": "22.22.0", "recipe": "harnesses/openwiki"}
        self.destination = self.root / ".tkstack/runtime/openwiki"

    def build_package(self, directory):
        package = directory / "node_modules/openwiki"
        package.mkdir(parents=True)
        (package / "package.json").write_text(json.dumps({"version": "0.7.2"}))
        binary = directory / "node_modules/.bin/openwiki"
        binary.parent.mkdir()
        binary.write_text("#!/bin/sh\nexit 0\n")
        binary.chmod(0o755)

    def test_success_is_published_once_and_detects_a_changed_lock(self):
        def install_package(*args, cwd, **kwargs):
            self.assertFalse(self.destination.exists())
            self.build_package(cwd)
        with patch.object(npm_runtime, "node_ready", return_value=True), \
                patch.object(npm_runtime.shutil, "which", return_value="npm"), \
                patch.object(npm_runtime.subprocess, "run", side_effect=install_package) as command:
            npm_runtime.install(self.root, "openwiki", self.tool)
            self.assertTrue(npm_runtime.package_ready(self.root, "openwiki", self.tool))
            npm_runtime.install(self.root, "openwiki", self.tool)
            self.assertEqual(command.call_count, 1)
            (self.recipe / "package-lock.json").write_text('{"fixture":"changed"}\n')
            self.assertFalse(npm_runtime.package_ready(self.root, "openwiki", self.tool))
            with self.assertRaisesRegex(ValueError, "existing runtime differs"):
                npm_runtime.install(self.root, "openwiki", self.tool)
            self.assertTrue((self.destination / "node_modules/.bin/openwiki").is_file())

    def test_failed_install_cleans_staging_and_publishes_nothing(self):
        with patch.object(npm_runtime, "node_ready", return_value=True), \
                patch.object(npm_runtime.shutil, "which", return_value="npm"), \
                patch.object(npm_runtime.subprocess, "run", side_effect=subprocess.CalledProcessError(1, "npm")):
            with self.assertRaises(subprocess.CalledProcessError):
                npm_runtime.install(self.root, "openwiki", self.tool)
        self.assertFalse(self.destination.exists())
        self.assertEqual(list(self.destination.parent.iterdir()), [])

    def test_competing_install_cannot_replace_the_writer_lock(self):
        lock = self.destination.parent / ".openwiki-install.lock"
        lock.mkdir(parents=True)
        (lock / "owner").write_text("existing writer")
        with patch.object(npm_runtime, "node_ready", return_value=True), \
                patch.object(npm_runtime.shutil, "which", return_value="npm"):
            with self.assertRaisesRegex(ValueError, "another install owns"):
                npm_runtime.install(self.root, "openwiki", self.tool)
        self.assertEqual((lock / "owner").read_text(), "existing writer")
        self.assertFalse(self.destination.exists())

    def test_unsupported_node_fails_before_writing(self):
        with patch.object(npm_runtime, "node_ready", return_value=False):
            with self.assertRaisesRegex(ValueError, "Node.js >= 22.22.0"):
                npm_runtime.install(self.root, "openwiki", self.tool)
        self.assertFalse((self.root / ".tkstack").exists())

    def test_each_native_host_receives_its_exact_identity_only_when_ready(self):
        manifest = json.loads((ROOT / "harnesses/integrations.json").read_text())
        with patch.object(setup_integrations, "ready", return_value=False):
            self.assertNotIn("openwiki", setup_integrations.mcp_entries(ROOT, manifest, "codex"))
        with patch.object(setup_integrations, "ready", return_value=True):
            for host in ("codex", "claude", "cursor"):
                entry = setup_integrations.mcp_entries(ROOT, manifest, host)["openwiki"]
                self.assertEqual(entry["args"], [str(ROOT / "scripts/tool.py"), "openwiki", "mcp", "--host", host])
                self.assertEqual(entry["command"], sys.executable)


if __name__ == "__main__":
    unittest.main()

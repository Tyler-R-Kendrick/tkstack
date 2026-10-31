from contextlib import redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import setup_integrations as setup
import install
import run_hook


class IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "dotfiles"
        (self.root / "harnesses").mkdir(parents=True)
        self.manifest = json.loads((ROOT / "harnesses/integrations.json").read_text())
        (self.root / "harnesses/integrations.json").write_text(json.dumps(self.manifest))
        self.target = Path(self.temporary.name) / "project"
        redirect = redirect_stdout(io.StringIO())
        redirect.__enter__()
        self.addCleanup(redirect.__exit__, None, None, None)

    def plan(self, uninstall=False):
        return setup.configuration_plan(self.root, self.target,
                                        ["codex", "claude", "cursor"], "project", uninstall)

    def test_native_configs_are_repeatable_and_preserve_unrelated_settings(self):
        (self.target / ".claude").mkdir(parents=True)
        settings = self.target / ".claude/settings.json"
        settings.write_text(json.dumps({"permissions": {"deny": ["Bash(git push*)"]},
                                        "hooks": {"PreToolUse": [{"hooks": [{"type": "command", "command": "my-existing-hook"}]}]}}))
        mcp = self.target / ".mcp.json"
        mcp.write_text(json.dumps({"mcpServers": {"existing": {"command": "my-server"}}}))
        plan = self.plan()
        setup.apply_configuration(plan, dry_run=True)
        self.assertFalse((self.target / ".codex").exists())
        setup.apply_configuration(plan)
        self.assertEqual(self.plan(), [])
        current = json.loads(settings.read_text())
        self.assertEqual(current["permissions"]["deny"], ["Bash(git push*)"])
        self.assertEqual(current["hooks"]["PreToolUse"][0]["hooks"][0]["command"], "my-existing-hook")
        self.assertIn("fal", json.loads(mcp.read_text())["mcpServers"])
        setup.apply_configuration(self.plan(uninstall=True))
        self.assertEqual(json.loads(mcp.read_text())["mcpServers"], {"existing": {"command": "my-server"}})
        self.assertEqual(json.loads(settings.read_text())["hooks"]["PreToolUse"],
                         [{"hooks": [{"type": "command", "command": "my-existing-hook"}]}])

    def test_foreign_server_collision_is_reported_before_any_write(self):
        self.target.mkdir()
        path = self.target / ".mcp.json"
        original = '{"mcpServers":{"fal":{"url":"https://my-existing-server"}}}'
        path.write_text(original)
        with self.assertRaisesRegex(ValueError, "Existing MCP server differs"):
            self.plan()
        self.assertEqual(path.read_text(), original)
        self.assertFalse((self.target / ".codex").exists())

    def test_stitch_uses_environment_references_without_writing_the_key(self):
        with patch.dict("os.environ", {"STITCH_API_KEY": "test-value-that-must-not-be-written"}):
            for harness in ("codex", "claude", "cursor"):
                entries = setup.mcp_entries(self.root, self.manifest, harness)
                text = json.dumps(entries)
                self.assertIn("STITCH_API_KEY", text)
                self.assertNotIn("test-value-that-must-not-be-written", text)
                self.assertIn("stitch", entries)

    def test_missing_binary_hooks_leave_tool_calls_unmodified(self):
        for name in ("rtk", "impeccable"):
            command, _ = run_hook.hook_command(self.root, name, "codex", "detect")
            self.assertIsNone(command)
        self.assertNotIn("headroom", setup.mcp_entries(self.root, self.manifest, "codex"))
        self.assertNotIn("open-design", setup.mcp_entries(self.root, self.manifest, "codex"))

    def test_checked_archive_installs_only_the_expected_binary(self):
        archive_data = io.BytesIO()
        with tarfile.open(fileobj=archive_data, mode="w:gz") as archive:
            info = tarfile.TarInfo("release/rtk")
            payload = b"a verified fixture binary"
            info.size = len(payload)
            archive.addfile(info, io.BytesIO(payload))
        raw = archive_data.getvalue()
        platform_key = setup.platform.system().lower() + "-" + {"arm64": "aarch64", "amd64": "x86_64"}.get(setup.platform.machine().lower(), setup.platform.machine().lower())
        manifest = {"tools": {"rtk": {"kind": "archive", "version": "fixture",
                    "platforms": {platform_key: {"url": "https://github.com/fixture/archive.tar.gz",
                    "sha256": hashlib.sha256(raw).hexdigest(), "archive_member": "rtk"}}}}}
        (self.root / "harnesses/integrations.json").write_text(json.dumps(manifest))
        with patch("urllib.request.urlopen", return_value=io.BytesIO(raw)):
            setup.install_runtimes(self.root)
        self.assertEqual((self.root / ".tkstack/runtime/bin/rtk").read_bytes(), payload)

    def test_download_checksum_mismatch_leaves_no_executable(self):
        platform_key = setup.platform.system().lower() + "-" + {"arm64": "aarch64", "amd64": "x86_64"}.get(setup.platform.machine().lower(), setup.platform.machine().lower())
        manifest = {"tools": {"impeccable": {"kind": "binary", "version": "fixture",
                    "platforms": {platform_key: {"url": "https://github.com/fixture/binary",
                    "sha256": "0" * 64}}}}}
        (self.root / "harnesses/integrations.json").write_text(json.dumps(manifest))
        with patch("urllib.request.urlopen", return_value=io.BytesIO(b"wrong download")):
            with self.assertRaisesRegex(ValueError, "checksum mismatch"):
                setup.install_runtimes(self.root)
        self.assertFalse((self.root / ".tkstack/runtime/bin/impeccable").exists())

    def test_wikiskill_runs_from_the_pinned_source_without_mutating_it(self):
        result = subprocess.run([sys.executable, str(ROOT / "scripts/tool.py"), "wikiskill", "--help"],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("evolve", result.stdout)
        install.verify_vendor(ROOT)

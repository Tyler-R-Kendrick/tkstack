"""Exercise pinned Caveman hooks directly, without a model or native host session."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import install
import run_hook
import setup_integrations as setup


@unittest.skipUnless(shutil.which("node"), "Official Caveman hooks require Node 18+")
class CavemanTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        (self.root / "vendor").mkdir()
        (self.root / "vendor/caveman").symlink_to(ROOT / "vendor/caveman", target_is_directory=True)
        self.environment = {**os.environ, "CAVEMAN_DEFAULT_MODE": "caveman",
                            "XDG_CONFIG_HOME": str(self.root / "config")}

    def hook(self, harness, event, payload, mode="caveman"):
        with patch.dict(os.environ, {**self.environment, "CAVEMAN_DEFAULT_MODE": mode}):
            command, environment = run_hook.hook_command(self.root, "caveman", harness, event)
        result = subprocess.run(command, env=environment, input=json.dumps(payload),
                                cwd=self.root, capture_output=True, text=True, timeout=8)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def test_official_codex_and_cursor_protocols_respect_opt_out(self):
        for harness in ("codex", "cursor"):
            output = self.hook(harness, "activate", {"workspace_roots": [str(self.root)]})
            if harness == "cursor":
                output = json.loads(output)["additional_context"]
            self.assertIn("CAVEMAN MODE ACTIVE", output)
            self.assertIn("Payload verbatim", output)
            silent = self.hook(harness, "activate", {}, "off")
            self.assertEqual(json.loads(silent) if harness == "cursor" else silent,
                             {} if harness == "cursor" else "")

    def test_claude_stop_survives_compaction_without_affecting_another_session(self):
        first = {"session_id": "one", "source": "startup", "cwd": str(self.root)}
        second = {**first, "session_id": "two"}
        self.assertIn("CAVEMAN MODE ACTIVE", self.hook("claude", "activate", first))
        self.assertIn("CAVEMAN MODE ACTIVE", self.hook("claude", "activate", second))
        self.hook("claude", "prompt", {**first, "prompt": "stop caveman"})
        self.assertEqual(self.hook("claude", "activate", {**first, "source": "compact"}), "OK")
        self.assertIn("CAVEMAN MODE ACTIVE", self.hook("claude", "activate", {**second, "source": "resume"}))
        state = self.root / ".tkstack/state/caveman/claude/.caveman-sessions"
        self.assertEqual((state / "one.mode").read_text().strip(), "off")
        self.assertEqual((state / "two.mode").read_text().strip(), "caveman")
        install.verify_vendor(ROOT)

    def test_adapters_keep_pins_immutable_and_missing_node_fails_open(self):
        with patch.dict(os.environ, {"CAVECREW_BUILDER_MODEL": "example-model"}):
            _, environment = run_hook.hook_command(self.root, "caveman", "claude", "activate")
        self.assertNotIn("CAVECREW_BUILDER_MODEL", environment)
        self.assertEqual(environment["CLAUDE_CONFIG_DIR"], str(self.root / ".tkstack/state/caveman/claude"))
        with patch("run_hook.shutil.which", return_value=None):
            self.assertIsNone(run_hook.hook_command(self.root, "caveman", "claude", "activate")[0])

    def test_registrations_match_each_official_host_surface(self):
        for harness, events in {"codex": {"SessionStart"}, "cursor": {"sessionStart"},
                                "claude": {"SessionStart", "SubagentStart", "UserPromptSubmit", "SessionEnd"}}.items():
            hooks = setup.hook_entries(ROOT, harness)
            actual = {event for event, items in hooks.items() if any("caveman " in json.dumps(item) for item in items)}
            self.assertEqual(actual, events)

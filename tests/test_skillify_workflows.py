"""Executable skill packaging and safe migration, without model calls."""
from concurrent.futures import ThreadPoolExecutor
import importlib.util
import json
import hashlib
import os
import shutil
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location("workflow_skillify", ROOT / "skills/learn/skills/skillify/scripts/skillify.py")
skillify = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(skillify)


class SkillifyWorkflowTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.target = self.root / "project with spaces/skills/normalize-labels"

    def snapshot(self):
        return {str(path.relative_to(self.target)): path.read_bytes()
                for path in self.target.rglob("*") if path.is_file()}

    def existing(self):
        self.target.mkdir(parents=True)
        (self.target / "LICENSE").write_bytes((ROOT / "LICENSE").read_bytes())
        (self.target / "SKILL.md").write_text('---\nname: normalize-labels\ndescription: "Normalize labels when asked."\n---\n\n# Normalize\n\nSort distinct labels, preserving spelling.\n')
        return (self.target / "SKILL.md").read_bytes()

    def invoke(self, payload=None, raw=None):
        return subprocess.run([sys.executable, str(self.target / "scripts/run.py"), "--input", "-"],
                              input=raw if raw is not None else json.dumps(payload),
                              capture_output=True, text=True, cwd=self.root)

    def complete(self):
        (self.target / 'commands/run.md').write_bytes((ROOT / 'skills/learn/skills/codify/examples/normalize-labels/commands/normalize.md').read_bytes())
        for path in [self.target / "SKILL.md", *(self.target / "references").glob("*.md")]:
            path.write_text(path.read_text().replace("TODO(SKILLIFY):", "Completed:"))

    def test_draft_is_executable_but_does_not_claim_the_procedure_is_implemented(self):
        skillify.scaffold(self.target, self.target.name, "Normalize labels.")
        result = self.invoke({})
        self.assertEqual(result.returncode, 3)
        self.assertEqual(result.stdout, "")
        self.assertIn("WORKFLOW_NOT_IMPLEMENTED", result.stderr)
        self.complete()
        with self.assertRaisesRegex(ValueError, "Implement the executable workflow"):
            skillify.validate(self.target, require_tool=True)

    def test_real_python_tool_preserves_contracts_and_repeatability(self):
        skillify.scaffold(self.target, self.target.name, "Normalize labels.")
        (self.target / "scripts/workflow.py").write_text('''def execute(payload):
    if set(payload) != {"labels"} or not isinstance(payload["labels"], list):
        raise ValueError("Expected labels array")
    if not all(isinstance(item, str) for item in payload["labels"]):
        raise ValueError("Expected text labels")
    return {"labels": sorted(set(payload["labels"]))}
''')
        self.complete()
        self.assertEqual(skillify.validate(self.target, require_tool=True)["tool_entrypoint"], "scripts/run.py")
        for labels in (["b", "a", "a"], ['quote"', "emoji 😀", "line\nbreak"], []):
            first, second = self.invoke({"labels": labels}), self.invoke({"labels": labels})
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(json.loads(first.stdout), {"labels": sorted(set(labels))})
            self.assertEqual(first.stdout, second.stdout)
        self.assertEqual(self.invoke({"labels": [1]}).returncode, 1)
        self.assertEqual(self.invoke(raw="not json").returncode, 1)
        self.assertEqual(self.invoke([]).returncode, 1)

    def test_conversion_preview_is_read_only_and_real_conversion_preserves_source(self):
        before = self.existing()
        snapshot = self.snapshot()
        plan = skillify.convert(self.target, dry_run=True)
        self.assertEqual(plan["status"], "planned")
        self.assertEqual(self.snapshot(), snapshot)
        result = skillify.convert(self.target)
        self.assertEqual(result["status"], "workflow-draft")
        self.assertEqual((self.target / "references/source-skill.txt").read_bytes(), before)
        self.assertNotEqual((self.target / "SKILL.md").read_bytes(), before)
        self.assertEqual(self.invoke({}).returncode, 3)

    def test_scaffold_and_conversion_supply_reserved_discovery_without_a_lock(self):
        for mode in ('python', 'ai-sdk', 'convert'):
            with self.subTest(mode=mode):
                if self.target.exists():
                    shutil.rmtree(self.target)
                if mode == 'convert':
                    self.existing()
                    skillify.convert(self.target)
                    expected_version = 'unversioned'
                else:
                    skillify.scaffold(self.target, self.target.name, 'Normalize labels.', backend=mode)
                    expected_version = '0.1.0'
                self.assertTrue((self.target / 'commands/help.md').is_file())
                self.assertTrue((self.target / 'commands/version.md').is_file())
                self.assertTrue((self.target / 'scripts/command_manual.py').is_file())
                source = (self.target / 'SKILL.md').read_text()
                self.assertIn('(commands/help.md)', source)
                self.assertIn('(commands/version.md)', source)
                before = self.snapshot()
                cli = [sys.executable, str(self.target / 'scripts/codify.py'), 'invoke', str(self.target)]
                environment = {**os.environ, 'TKSTACK_WORKSPACE_DIR': str(self.root / 'uninitialized/.tkstack')}
                for args in ([], ['help'], ['--help'], ['help', '--format', 'man'], ['version']):
                    result = subprocess.run([*cli, '--', *args], text=True, capture_output=True, env=environment)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    if args == ['version']:
                        self.assertEqual(result.stdout, self.target.name + ' ' + expected_version + '\n')
                    elif args[-1:] == ['man']:
                        self.assertTrue(result.stdout.startswith('.TH '))
                    else:
                        self.assertIn('SYNOPSIS', result.stdout)
                self.assertEqual(self.snapshot(), before)
                self.assertFalse((self.root / 'uninitialized').exists())

    def test_conversion_rejects_collisions_and_does_not_overwrite_helpers(self):
        self.existing()
        (self.target / "scripts").mkdir()
        (self.target / "scripts/run.py").write_text("a user-owned entrypoint")
        before = self.snapshot()
        with self.assertRaises(FileExistsError):
            skillify.convert(self.target)
        self.assertEqual(self.snapshot(), before)

    def test_conversion_rejects_symlinked_resource_directories(self):
        self.existing()
        outside = self.root / "outside"
        outside.mkdir()
        (self.target / "scripts").symlink_to(outside, target_is_directory=True)
        before = (self.target / "SKILL.md").read_bytes()
        with self.assertRaises(ValueError):
            skillify.convert(self.target)
        self.assertEqual(list(outside.iterdir()), [])
        self.assertEqual((self.target / "SKILL.md").read_bytes(), before)

    def test_failed_publication_rolls_back_and_can_be_retried(self):
        before = self.existing()
        original = skillify.os.link
        calls = 0
        def fail_second(source, target):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("fixture publication failure")
            return original(source, target)
        with patch.object(skillify.os, "link", side_effect=fail_second):
            with self.assertRaisesRegex(OSError, "fixture publication failure"):
                skillify.convert(self.target)
        self.assertEqual((self.target / "SKILL.md").read_bytes(), before)
        self.assertEqual(set(self.snapshot()), {"LICENSE", "SKILL.md"})
        self.assertFalse((self.target / ".skillify-convert.lock").exists())
        self.assertEqual(skillify.convert(self.target)["status"], "workflow-draft")

    def test_competing_conversion_has_one_publisher(self):
        self.existing()
        def attempt(_):
            try:
                return skillify.convert(self.target)["status"]
            except (OSError, ValueError):
                return "collision"
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertCountEqual(list(pool.map(attempt, range(2))), ["workflow-draft", "collision"])

    def test_ai_sdk_scaffold_is_standalone_locked_and_escapes_description(self):
        description = "Use quotes ' and \" literally; ${notCode}, @TITLE@, @COMMAND@, @ENTRYPOINT@."
        skillify.scaffold(self.target, self.target.name, description, "ai-sdk")
        self.assertEqual(skillify.metadata((self.target / "SKILL.md").read_text())[0]["description"], description)
        package = json.loads((self.target / "scripts/package.json").read_text())
        self.assertEqual(package["dependencies"]["ai"], "7.0.158")
        self.assertTrue((self.target / "scripts/package-lock.json").is_file())
        self.assertIn(json.dumps(description), (self.target / "scripts/tool.ts").read_text())
        config = json.loads((self.target / "scripts/profiles.json").read_text())
        self.assertEqual(config["profiles"], {})
        self.assertEqual(config["providers"], {})
        self.assertIn("node scripts/run.ts --input", (self.target / "references/tool.md").read_text())

    @unittest.skipUnless(os.environ.get("TKSTACK_AI_SDK_DEPENDENCIES"), "Set TKSTACK_AI_SDK_DEPENDENCIES to the locked runtime's node_modules for native checks")
    def test_native_ai_sdk_cli_tool_export_and_bundled_contracts(self):
        dependencies = Path(os.environ["TKSTACK_AI_SDK_DEPENDENCIES"]).resolve(strict=True)
        self.assertEqual(json.loads((dependencies / "ai/package.json").read_text())["version"], "7.0.158")
        skillify.scaffold(self.target, self.target.name, "Normalize labels.", "ai-sdk")
        scripts = self.target / "scripts"
        (scripts / "node_modules").symlink_to(dependencies, target_is_directory=True)
        (scripts / "workflow.ts").write_text('''import { z } from 'zod';
import { createHash } from 'node:crypto';
export const inputSchema = z.object({labels: z.array(z.string().max(1024)).max(64)}).strict();
export const outputSchema = z.object({labels: z.array(z.string()), sha256: z.string().length(64)}).strict();
export type Inference = unknown;
export async function execute(input: z.infer<typeof inputSchema>, _inference: Inference) {
  const labels = [...new Set(input.labels.map(label => label.trim()))].sort();
  return {labels, sha256: createHash('sha256').update(JSON.stringify(labels)).digest('hex')};
}
''')
        (scripts / "verify-tool.mjs").write_text('''import assert from 'node:assert/strict';
import { createWorkflowTool } from './tool.ts';
import { createInference } from './inference.ts';
const tool = createWorkflowTool(createInference({version: 1, providers: {}, profiles: {}}));
const context = {toolCallId: 'fixture', messages: []};
assert.deepEqual((await tool.execute({labels: [' b ', 'a', 'a']}, context)).labels, ['a', 'b']);
await assert.rejects(tool.execute({labels: [1]}, context));
console.log('Native AI SDK tool invocation and input/output contracts passed.');
''')
        for command in ([str(dependencies / ".bin/tsc"), "--noEmit", "--pretty", "false"],
                        ["node", "--test", "--test-isolation=none", "runtime.test.ts"],
                        ["node", "verify-tool.mjs"]):
            result = subprocess.run(command, cwd=scripts, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        input_path = self.root / "input.json"
        payload = {"labels": ['quote"', '😀', ' b ', 'a', 'a']}
        input_path.write_text(json.dumps(payload))
        command = ["node", str(scripts / "run.ts"), "--input", str(input_path)]
        first = subprocess.run(command, cwd=self.root, capture_output=True, text=True)
        second = subprocess.run(command, cwd=self.root, capture_output=True, text=True)
        self.assertEqual(first.returncode, 0, first.stderr)
        labels = ['a', 'b', 'quote"', '😀']
        digest = hashlib.sha256(json.dumps(labels, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()
        self.assertEqual(json.loads(first.stdout), {"labels": labels, "sha256": digest})
        self.assertEqual(first.stdout, second.stdout)
        input_path.write_text('{"labels":[1]}')
        self.assertEqual(subprocess.run(command, cwd=self.root, capture_output=True).returncode, 1)
        self.complete()
        self.assertEqual(skillify.validate(self.target, require_tool=True)["tool_entrypoint"], "scripts/run.ts")
